import asyncio
import json
import urllib.error
import urllib.request
from typing import Any

from backend.config import settings
from backend.services.qwen_client import QwenConfigError


class DashScopeReranker:
    def __init__(self):
        if not settings.qwen_api_key:
            raise QwenConfigError(
                "Missing DashScope API key. Set DASHSCOPE_API_KEY, ALIYUN_ACCESS_KEY_SECRET, "
                "QWEN_API_KEY, or OPENAI_API_KEY."
            )
        self.api_key = settings.qwen_api_key
        self.model = settings.dashscope_rerank_model
        self.base_url = settings.dashscope_base_url.rstrip("/")
        self.timeout = settings.rerank_timeout_seconds
        self.instruct = settings.rerank_instruct

    async def rerank(self, query: str, hits: list[dict[str, Any]], top_n: int) -> list[dict[str, Any]]:
        if not hits or top_n <= 0:
            return []

        documents = [hit.get("content", "") for hit in hits]
        rerank_top_n = min(top_n, len(documents))
        results = await asyncio.to_thread(self._rerank_sync, query, documents, rerank_top_n)
        return _merge_rerank_results(hits, results, rerank_top_n)

    def _rerank_sync(
        self,
        query: str,
        documents: list[str],
        top_n: int,
    ) -> list[dict[str, Any]]:
        request = urllib.request.Request(
            url=self._endpoint_url(),
            data=json.dumps(self._payload(query, documents, top_n), ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"DashScope rerank API HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"DashScope rerank API request failed: {exc.reason}") from exc

        data = json.loads(body)
        if data.get("code"):
            message = data.get("message", "unknown error")
            raise RuntimeError(f"DashScope rerank API error {data['code']}: {message}")
        return _extract_results(data)

    def _endpoint_url(self) -> str:
        if self.model == "qwen3-rerank":
            return f"{self.base_url}/compatible-api/v1/reranks"
        return f"{self.base_url}/api/v1/services/rerank/text-rerank/text-rerank"

    def _payload(self, query: str, documents: list[str], top_n: int) -> dict[str, Any]:
        if self.model == "qwen3-rerank":
            payload = {
                "model": self.model,
                "query": query,
                "documents": documents,
                "top_n": top_n,
            }
            if self.instruct:
                payload["instruct"] = self.instruct
            return payload

        parameters: dict[str, Any] = {
            "return_documents": False,
            "top_n": top_n,
        }
        if self.model == "qwen3-vl-rerank" and self.instruct:
            parameters["instruct"] = self.instruct

        return {
            "model": self.model,
            "input": {
                "query": query,
                "documents": documents,
            },
            "parameters": parameters,
        }


def _extract_results(data: dict[str, Any]) -> list[dict[str, Any]]:
    if "results" in data:
        return data["results"] or []
    output = data.get("output") or {}
    return output.get("results") or []


def _merge_rerank_results(
    hits: list[dict[str, Any]],
    results: list[dict[str, Any]],
    top_n: int,
) -> list[dict[str, Any]]:
    ranked_hits: list[dict[str, Any]] = []
    ranked_indexes: set[int] = set()

    for item in results:
        index = item.get("index")
        if not isinstance(index, int) or index < 0 or index >= len(hits):
            continue

        score = _optional_float(item.get("relevance_score"))
        hit = dict(hits[index])
        hit["vector_score"] = hit.get("score")
        hit["rerank_score"] = score
        if score is not None:
            hit["score"] = round(score, 4)
        ranked_hits.append(hit)
        ranked_indexes.add(index)

        if len(ranked_hits) >= top_n:
            return ranked_hits

    for index, hit in enumerate(hits):
        if index in ranked_indexes:
            continue
        fallback_hit = dict(hit)
        fallback_hit["vector_score"] = fallback_hit.get("score")
        fallback_hit["rerank_score"] = None
        ranked_hits.append(fallback_hit)
        if len(ranked_hits) >= top_n:
            break

    return ranked_hits


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
