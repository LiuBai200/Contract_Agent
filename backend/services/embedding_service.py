import asyncio
import json
import urllib.error
import urllib.request

from backend.config import settings
from backend.services.qwen_client import QwenConfigError


class QwenEmbeddingClient:
    def __init__(self):
        if not settings.qwen_api_key:
            raise QwenConfigError(
                "Missing Qwen API key. Set DASHSCOPE_API_KEY, ALIYUN_ACCESS_KEY_SECRET, "
                "QWEN_API_KEY, or OPENAI_API_KEY."
            )
        self.api_key = settings.qwen_api_key
        self.model = settings.qwen_embedding_model
        self.base_url = settings.qwen_base_url.rstrip("/")

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return await asyncio.to_thread(self._embed_texts_sync, texts)

    def _embed_texts_sync(self, texts: list[str]) -> list[list[float]]:
        url = f"{self.base_url}/embeddings"
        payload = {
            "model": self.model,
            "input": texts,
        }
        request = urllib.request.Request(
            url=url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Qwen embedding API HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Qwen embedding API request failed: {exc.reason}") from exc

        data = json.loads(body)
        sorted_items = sorted(data["data"], key=lambda item: item["index"])
        return [item["embedding"] for item in sorted_items]
