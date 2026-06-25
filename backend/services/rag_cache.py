import hashlib
import json
import logging
from typing import Any

from backend.config import settings
from backend.services.redis_client import get_redis_client


logger = logging.getLogger(__name__)


async def get_cached_rag_hits(
    question: str,
    user_id: int,
    top_k: int,
    contract_id: int | None = None,
) -> list[dict[str, Any]] | None:
    if not settings.rag_hits_cache_enabled:
        return None

    key = _rag_hits_key(question, user_id, top_k, contract_id)
    try:
        raw = await get_redis_client().get(key)
        if not raw:
            return None
        data = json.loads(raw)
        return data if isinstance(data, list) else None
    except Exception as exc:
        logger.warning("Redis RAG cache read failed: %s", exc)
        return None


async def set_cached_rag_hits(
    question: str,
    user_id: int,
    top_k: int,
    hits: list[dict[str, Any]],
    contract_id: int | None = None,
) -> None:
    if not settings.rag_hits_cache_enabled:
        return

    key = _rag_hits_key(question, user_id, top_k, contract_id)
    try:
        await get_redis_client().set(
            key,
            json.dumps(hits, ensure_ascii=False),
            ex=settings.rag_hits_cache_ttl_seconds,
        )
    except Exception as exc:
        logger.warning("Redis RAG cache write failed: %s", exc)


async def clear_rag_cache_for_user(user_id: int) -> None:
    if not settings.rag_hits_cache_enabled:
        return

    pattern = f"rag:hits:{user_id}:*"
    try:
        redis = get_redis_client()
        batch = []
        async for key in redis.scan_iter(match=pattern, count=100):
            batch.append(key)
            if len(batch) >= 100:
                await redis.delete(*batch)
                batch.clear()
        if batch:
            await redis.delete(*batch)
    except Exception as exc:
        logger.warning("Redis RAG cache clear failed: %s", exc)


def _rag_hits_key(
    question: str,
    user_id: int,
    top_k: int,
    contract_id: int | None = None,
) -> str:
    contract_part = contract_id if contract_id is not None else "all"
    question_hash = hashlib.sha256(question.strip().encode("utf-8")).hexdigest()
    return f"rag:hits:{user_id}:{contract_part}:{top_k}:{question_hash}"
