"""
POST /api/chat — SSE streaming chat endpoint.
Requires JWT auth. Streams all Boardroom pipeline events to the client.

DB persistence:
  - User message → ChatMessage(role='user')
  - Each agent response → ChatMessage(role='agent', agent_key=...)
  - Each validation event → ChatMessage(role='validation', validation_score=...)
  - Synthesis → ChatMessage(role='synthesis')
  - Orchestration metadata → ChatMessage(role='routing', extra_data={...})
  - Session.conversation_history kept as compact {role, content} list for quick context retrieval
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
from app.db.models import User, Session as ChatSession, ChatMessage
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
    # ── Get or create session ────────────────────────────────────────────────
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

    # ── Persist user message ─────────────────────────────────────────────────
    user_msg_row = ChatMessage(
        id=uuid.uuid4(),
        session_id=session.id,
        user_id=current_user.id,
        role="user",
        content=body.message,
        created_at=datetime.utcnow(),
    )
    db.add(user_msg_row)

    # Add to compact history for agent context injection
    history = list(session.conversation_history or [])
    history.append(
        {
            "role": "user",
            "content": body.message,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )

    await db.commit()

    # ── Stream and persist all pipeline events ───────────────────────────────
    async def boardroom_events():
        async for event in run_boardroom(
            message=body.message,
            user=current_user,
            conversation_history=history,
        ):
            event_type = event.get("type")

            # Persist each meaningful event as a ChatMessage row
            if event_type == "orchestration":
                db.add(
                    ChatMessage(
                        id=uuid.uuid4(),
                        session_id=session.id,
                        user_id=current_user.id,
                        role="routing",
                        content=event.get("content", ""),
                        extra_data={
                            "intent": event.get("intent"),
                            "complexity": event.get("complexity"),
                            "response_strategy": event.get("response_strategy"),
                            "reasoning": event.get("reasoning"),
                            "sub_queries": event.get("sub_queries"),
                            "agents": event.get("agents"),
                        },
                        created_at=datetime.utcnow(),
                    )
                )

            elif event_type == "agent_response":
                db.add(
                    ChatMessage(
                        id=uuid.uuid4(),
                        session_id=session.id,
                        user_id=current_user.id,
                        role="agent",
                        content=event.get("content", ""),
                        agent_key=event.get("agent"),
                        agent_name=event.get("agent_name"),
                        created_at=datetime.utcnow(),
                    )
                )

            elif event_type == "validation":
                db.add(
                    ChatMessage(
                        id=uuid.uuid4(),
                        session_id=session.id,
                        user_id=current_user.id,
                        role="validation",
                        content=event.get("content", ""),
                        agent_key=event.get("agent"),
                        validation_score=event.get("score"),
                        validation_passed=event.get("passed"),
                        extra_data={
                            "scores": event.get("scores"),
                            "critique": event.get("critique", ""),
                        },
                        created_at=datetime.utcnow(),
                    )
                )

            elif event_type == "synthesis":
                synthesis_text = event.get("content", "")
                db.add(
                    ChatMessage(
                        id=uuid.uuid4(),
                        session_id=session.id,
                        user_id=current_user.id,
                        role="synthesis",
                        content=synthesis_text,
                        created_at=datetime.utcnow(),
                    )
                )
                # Update compact history with the synthesis as the assistant turn
                history.append(
                    {
                        "role": "assistant",
                        "content": synthesis_text,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )

            elif event_type == "done":
                # If no synthesis was emitted (single agent), persist the agent response
                # as the assistant turn in compact history
                if not any(
                    m.get("role") == "assistant" for m in history[len(history) - 2 :]
                ):
                    agent_responses = event.get("agent_responses", {})
                    if agent_responses:
                        content = list(agent_responses.values())[0]
                        history.append(
                            {
                                "role": "assistant",
                                "content": content,
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        )

                # Persist updated compact history and timestamp
                session.conversation_history = history
                session.last_active_at = datetime.utcnow()
                await db.commit()

            yield event

    return StreamingResponse(
        event_stream(boardroom_events()),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Session-ID": str(session.id)},
    )
