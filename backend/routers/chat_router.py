import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.agent.contract_agent import run_contract_agent, stream_contract_agent
from backend.db.models import User
from backend.db.session import SessionLocal, get_db
from backend.schemas import AskRequest, AskResponse, ChatMessagePublic, SessionDeleteResponse, SessionSummary
from backend.security.dependencies import get_current_user
from backend.services.memory_service import delete_session_for_user, list_session_messages, list_user_sessions

router = APIRouter(tags=["chat"])


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/ask", response_model=AskResponse)
async def ask_contract_agent(
    request: AskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await run_contract_agent(request, current_user, db)


@router.post("/ask/stream")
async def ask_contract_agent_stream(
    request: AskRequest,
    current_user: User = Depends(get_current_user),
):
    user_id = current_user.id

    async def event_generator():
        db = SessionLocal()
        try:
            user = db.get(User, user_id)
            if not user:
                yield _sse({"type": "error", "message": "User not found"})
                return
            async for event in stream_contract_agent(request, user, db):
                yield _sse(event)
        except Exception as exc:
            yield _sse({"type": "error", "message": str(exc)})
        finally:
            db.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/sessions", response_model=list[SessionSummary])
async def get_sessions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list_user_sessions(current_user.id, db)


@router.delete("/sessions/{session_id}", response_model=SessionDeleteResponse)
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = delete_session_for_user(session_id, current_user.id, db)
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")
    return result


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessagePublic])
async def get_session_messages(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_session_messages(session_id, current_user.id, db)
