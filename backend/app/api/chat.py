"""
POST /api/chat — SSE streaming chat endpoint.
Requires JWT auth. Boardroom only (onboarding is now done at signup).
"""

import json
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.database import get_db
from app.db.models import User, Session as ChatSession
from app.agents.boardroom import run_boardroom

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


async def event_stream(generator):
    async for event in generator:
        yield f"data: {json.dumps(event)}\n\n"


@router.post("/chat")
async def chat(
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Get or create a chat session for this user
    session = None
    if body.session_id:
        result = await db.execute(
            select(ChatSession).where(
                ChatSession.id == body.session_id,
                ChatSession.user_id == current_user.id,
            )
        )
        session = result.scalar_one_or_none()

    if session is None:
        session = ChatSession(
            id=uuid.uuid4(),
            user_id=current_user.id,
            conversation_history=[],
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

    # Add user message to history
    history = list(session.conversation_history or [])
    history.append(
        {
            "role": "user",
            "content": body.message,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )

    async def boardroom_events():
        agent_response_content = ""
        async for event in run_boardroom(
            message=body.message,
            user=current_user,
            conversation_history=history,
        ):
            if event.get("type") in ("agent_response", "synthesis"):
                agent_response_content = event.get("content", "")
            yield event

        # Persist updated history
        history.append(
            {
                "role": "assistant",
                "content": agent_response_content,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        session.conversation_history = history
        session.last_active_at = datetime.utcnow()
        await db.commit()

    return StreamingResponse(
        event_stream(boardroom_events()),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Session-ID": str(session.id)},
    )
