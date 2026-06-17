from backend.services.vector_store import VectorStoreService


async def search_contract_clause(
    question: str,
    user_id: int,
    top_k: int = 5,
    contract_id: int | None = None,
) -> list[dict]:
    return await VectorStoreService().search(
        question,
        user_id=user_id,
        top_k=top_k,
        contract_id=contract_id,
    )
