import json
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from backend.db.models import ChatMessage, ChatSession, User
from backend.schemas import ChatMessagePublic, Citation, SessionDeleteResponse, SessionSummary


def get_or_create_session(session_id: str | None, user: User, db: Session, title: str | None = None) -> ChatSession:
    if session_id:
        session = db.get(ChatSession, session_id)
        if session and session.user_id == user.id:
            return session

    session = ChatSession(
        id=session_id or str(uuid.uuid4()),
        user_id=user.id,
        title=(title or "New chat")[:120],
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def add_message(
    session_id: str,
    user_id: int,
    role: str,
    content: str,
    db: Session,
    citations: list[Citation] | None = None,
) -> None:
    message = ChatMessage(
        session_id=session_id,
        user_id=user_id,
        role=role,
        content=content,
        citations_json=_dump_citations(citations),
    )
    session = db.get(ChatSession, session_id)
    if session:
        session.updated_at = datetime.utcnow()
    db.add(message)
    db.commit()


def get_recent_messages(session_id: str, user_id: int, db: Session, limit: int = 8) -> list[ChatMessage]:
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id, ChatMessage.user_id == user_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
        .all()
    )
    return list(reversed(messages))


def list_user_sessions(user_id: int, db: Session) -> list[SessionSummary]:
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user_id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )
    return [SessionSummary(id=session.id, title=session.title) for session in sessions]


def list_session_messages(session_id: str, user_id: int, db: Session) -> list[ChatMessagePublic]:
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id, ChatMessage.user_id == user_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return [
        ChatMessagePublic(
            role=message.role,
            content=message.content,
            citations=_load_citations(message.citations_json),
        )
        for message in messages
    ]


def delete_session_for_user(session_id: str, user_id: int, db: Session) -> SessionDeleteResponse | None:
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
        .first()
    )
    if not session:
        return None

    deleted_messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id, ChatMessage.user_id == user_id)
        .delete(synchronize_session=False)
    )
    db.delete(session)
    db.commit()
    return SessionDeleteResponse(
        session_id=session_id,
        deleted_messages=deleted_messages,
        message="聊天记录已删除",
    )


def _dump_citations(citations: list[Citation] | None) -> str | None:
    if not citations:
        return None
    data = [
        citation.model_dump() if hasattr(citation, "model_dump") else citation.dict()
        for citation in citations
    ]
    return json.dumps(data, ensure_ascii=False)


def _load_citations(raw: str | None) -> list[Citation]:
    if not raw:
        return []
    try:
        return [Citation(**item) for item in json.loads(raw)]
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
