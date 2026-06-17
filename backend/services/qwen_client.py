import asyncio
import json
import urllib.error
import urllib.request

from backend.config import settings


_STREAM_DONE = object()


def _next_stream_chunk(iterator):
    try:
        return next(iterator)
    except StopIteration:
        return _STREAM_DONE


class QwenConfigError(RuntimeError):
    pass


class QwenClient:
    def __init__(self):
        if not settings.qwen_api_key:
            raise QwenConfigError(
                "Missing Qwen API key. Set DASHSCOPE_API_KEY, ALIYUN_ACCESS_KEY_SECRET, "
                "QWEN_API_KEY, or OPENAI_API_KEY in system env or .env."
            )
        self.api_key = settings.qwen_api_key
        self.model = settings.qwen_model
        self.base_url = settings.qwen_base_url.rstrip("/")

    async def chat(self, question: str) -> str:
        system_prompt = "你是一个合同审查 RAG Agent，用清晰、谨慎的中文回答。"
        return await self.complete(system_prompt, question)

    async def complete(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        return await asyncio.to_thread(self._chat_sync, system_prompt, user_prompt, temperature)

    async def complete_stream(self, system_prompt: str, user_prompt: str, temperature: float = 0.2):
        iterator = self._chat_stream_sync(system_prompt, user_prompt, temperature)
        while True:
            chunk = await asyncio.to_thread(_next_stream_chunk, iterator)
            if chunk is _STREAM_DONE:
                break
            yield chunk

    def _chat_sync(self, system_prompt: str, user_prompt: str, temperature: float) -> str:
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
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
            raise RuntimeError(f"Qwen API HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Qwen API request failed: {exc.reason}") from exc

        data = json.loads(body)
        return data["choices"][0]["message"]["content"]

    def _chat_stream_sync(self, system_prompt: str, user_prompt: str, temperature: float):
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "temperature": temperature,
            "stream": True,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
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
                for raw_line in response:
                    line = raw_line.decode("utf-8", errors="ignore").strip()
                    if not line or line.startswith(":") or not line.startswith("data:"):
                        continue
                    data_text = line.removeprefix("data:").strip()
                    if data_text == "[DONE]":
                        break
                    try:
                        data = json.loads(data_text)
                    except json.JSONDecodeError:
                        continue
                    choices = data.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    content = delta.get("content")
                    if content:
                        yield content
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Qwen API HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Qwen API request failed: {exc.reason}") from exc
