"""
Session API controller — session metadata, history list, and message loader.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.database import get_db
from app.utils.security import get_current_user
from app.repository.session_repository import SessionRepository
from app.repository.message_repository import MessageRepository
from app.services.memory_service import count_memories
from app.models.user import User

router = APIRouter(prefix="/session", tags=["session"])


@router.get("")
async def get_session(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session_repo = SessionRepository(db)
    sessions = await session_repo.get_all_for_user(current_user.id)
    memory_count = count_memories(str(current_user.id))
    return {
        "session_count": len(sessions),
        "memory_count": memory_count,
        "user": {
            "id": str(current_user.id),
            "email": current_user.email,
            "name": current_user.name,
            "role": current_user.role,
            "company_name": current_user.company_name,
            "company_stage": current_user.company_stage,
            "industry": current_user.industry,
            "team_size": current_user.team_size,
            "onboarding_complete": current_user.onboarding_complete,
        },
    }


@router.get("/history")
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all sessions for the current user with a display title."""
    session_repo = SessionRepository(db)
    sessions = await session_repo.get_all_for_user(current_user.id)

    result = []
    for s in sessions:
        # Derive title from first user message in conversation history
        title = "New conversation"
        for entry in (s.conversation_history or []):
            if entry.get("role") == "user" and entry.get("content"):
                raw = entry["content"]
                title = raw[:60] + ("…" if len(raw) > 60 else "")
                break
        result.append({
            "id": str(s.id),
            "title": title,
            "created_at": s.created_at.isoformat(),
            "last_active_at": s.last_active_at.isoformat(),
        })

    return {"sessions": result}


@router.get("/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return messages for a session, mapped to frontend ChatMessage format."""
    try:
        sid = UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID")

    session_repo = SessionRepository(db)
    session = await session_repo.get_by_id(sid, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    msg_repo = MessageRepository(db)
    messages = await msg_repo.get_by_session(sid)

    result = []
    for msg in messages:
        if msg.role == "validation":
            continue  # not shown in UI

        item: dict = {
            "id": str(msg.id),
            "role": msg.role,
            "content": msg.content or "",
        }

        if msg.role == "routing":
            # Map to orchestration event shape
            extra = msg.extra_data or {}
            item["role"] = "orchestration"
            item["intent"] = extra.get("intent")
            item["complexity"] = extra.get("complexity")
            item["sub_queries"] = extra.get("sub_queries")
            item["reasoning"] = extra.get("reasoning")
        elif msg.role == "agent":
            item["role"] = "assistant"
            item["agent"] = msg.agent_key
            item["agent_name"] = msg.agent_name
        elif msg.role == "synthesis":
            item["role"] = "assistant"
            item["isSynthesis"] = True

        result.append(item)

    return {"messages": result, "session_id": session_id}
