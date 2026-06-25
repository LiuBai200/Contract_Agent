import logging

from backend.config import settings
from backend.services.rag_cache import get_cached_rag_hits, set_cached_rag_hits
from backend.services.reranker_service import DashScopeReranker
from backend.services.vector_store import VectorStoreService


logger = logging.getLogger(__name__)


async def search_contract_clause(
    question: str,
    user_id: int,
    top_k: int = 5,
    contract_id: int | None = None,
) -> list[dict]:
    cached_hits = await get_cached_rag_hits(
        question,
        user_id=user_id,
        top_k=top_k,
        contract_id=contract_id,
    )
    if cached_hits is not None:
        return cached_hits

    candidate_k = top_k
    if settings.rerank_enabled:
        candidate_k = max(top_k, settings.rerank_candidate_k)

    hits = await VectorStoreService().search(
        question,
        user_id=user_id,
        top_k=candidate_k,
        contract_id=contract_id,
    )

    if not settings.rerank_enabled or len(hits) <= 1:
        result = hits[:top_k]
        await set_cached_rag_hits(question, user_id, top_k, result, contract_id)
        return result

    try:
        result = await DashScopeReranker().rerank(question, hits, top_k)
    except RuntimeError as exc:
        logger.warning("DashScope rerank failed; falling back to vector search: %s", exc)
        result = hits[:top_k]

    await set_cached_rag_hits(question, user_id, top_k, result, contract_id)
    return result
