from backend.db.models import ChatMessage
from backend.services.retriever_service import search_contract_clause
from backend.services.risk_analyzer import analyze_contract_risk


async def answer_with_citation(
    question: str,
    user_id: int,
    history: list[ChatMessage],
    top_k: int = 5,
    contract_id: int | None = None,
    review_rules: str | None = None,
) -> tuple[str, list[dict]]:
    hits = await search_contract_clause(
        question,
        user_id=user_id,
        top_k=top_k,
        contract_id=contract_id,
    )
    answer = await analyze_contract_risk(question, hits, history, review_rules=review_rules)
    return answer, hits
