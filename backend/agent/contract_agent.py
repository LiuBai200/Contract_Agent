from sqlalchemy.orm import Session

from backend.agent.tools import answer_with_citation
from backend.config import settings
from backend.db.models import User
from backend.schemas import AskRequest, AskResponse, Citation
from backend.services.memory_service import add_message, get_or_create_session, get_recent_messages
from backend.services.retriever_service import search_contract_clause
from backend.services.risk_analyzer import analyze_contract_risk_stream


async def run_contract_agent(request: AskRequest, user: User, db: Session) -> AskResponse:
    session = get_or_create_session(request.session_id, user, db, title=request.question[:40])
    history = get_recent_messages(session.id, user.id, db)
    add_message(session.id, user.id, "user", request.question, db)

    answer, hits = await answer_with_citation(
        question=request.question,
        user_id=user.id,
        history=history,
        top_k=request.top_k,
        contract_id=request.contract_id,
    )
    citations = [_hit_to_citation(hit) for hit in hits]
    add_message(session.id, user.id, "assistant", answer, db, citations=citations)
    return AskResponse(
        answer=answer,
        model=settings.qwen_model,
        session_id=session.id,
        citations=citations,
    )


async def stream_contract_agent(request: AskRequest, user: User, db: Session):
    session = get_or_create_session(request.session_id, user, db, title=request.question[:40])
    history = get_recent_messages(session.id, user.id, db)
    add_message(session.id, user.id, "user", request.question, db)

    yield {
        "type": "session",
        "session_id": session.id,
        "model": settings.qwen_model,
    }
    yield {"type": "thinking", "content": "正在检索与你的问题相关的合同条款。"}

    hits = await search_contract_clause(
        request.question,
        user_id=user.id,
        top_k=request.top_k,
        contract_id=request.contract_id,
    )
    citations = [_hit_to_citation(hit) for hit in hits]
    citation_payload = [_citation_to_dict(citation) for citation in citations]

    yield {"type": "thinking", "content": f"检索完成，找到 {len(hits)} 个相关片段。"}
    yield {"type": "citations", "citations": citation_payload}
    if hits:
        yield {"type": "thinking", "content": "正在结合历史对话和引用条款生成审查意见。"}
    else:
        yield {"type": "thinking", "content": "没有找到可引用条款，正在生成提示信息。"}

    answer_parts: list[str] = []
    async for chunk in analyze_contract_risk_stream(request.question, hits, history):
        answer_parts.append(chunk)
        yield {"type": "answer_delta", "content": chunk}

    answer = "".join(answer_parts)
    add_message(session.id, user.id, "assistant", answer, db, citations=citations)
    yield {"type": "thinking", "content": "本轮对话已保存。"}
    yield {
        "type": "done",
        "answer": answer,
        "model": settings.qwen_model,
        "session_id": session.id,
        "citations": citation_payload,
    }


def _hit_to_citation(hit: dict) -> Citation:
    metadata = hit["metadata"]
    return Citation(
        filename=metadata.get("filename"),
        page=_optional_int(metadata.get("page")),
        paragraph=_optional_int(metadata.get("paragraph")),
        slide=_optional_int(metadata.get("slide")),
        clause_title=metadata.get("clause_title"),
        chunk_index=_optional_int(metadata.get("chunk_index")),
        score=hit.get("score"),
        content=hit["content"],
    )


def _optional_int(value) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _citation_to_dict(citation: Citation) -> dict:
    if hasattr(citation, "model_dump"):
        return citation.model_dump()
    return citation.dict()
