"""
Chat API controller — thin HTTP handler + SSE streaming.
All pipeline logic is in services/boardroom. All DB writes go through repository layer.
"""

import json
from datetime import datetime
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.database import get_db
from app.utils.security import get_current_user
from app.schemas.chat_schemas import ChatRequest
from app.repository.session_repository import SessionRepository
from app.repository.message_repository import MessageRepository
from app.services.boardroom import run_pipeline
from app.models.user import User

router = APIRouter(prefix="/chat", tags=["chat"])


async def _event_stream(generator):
    async for event in generator:
        yield f"data: {json.dumps(event)}\n\n"


@router.post("")
async def chat(
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session_repo = SessionRepository(db)
    msg_repo = MessageRepository(db)

    # Get or create session
    session = None
    if body.session_id:
        try:
            from uuid import UUID

            session = await session_repo.get_by_id(
                UUID(body.session_id), current_user.id
            )
        except Exception:
            pass
    if session is None:
        session = await session_repo.create(current_user.id)

    # Persist user message
    msg_repo.add_user_message(session.id, current_user.id, body.message)
    history = list(session.conversation_history or [])
    history.append(
        {
            "role": "user",
            "content": body.message,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )
    await db.commit()

    async def stream():
        async for event in run_pipeline(
            message=body.message,
            user=current_user,
            conversation_history=history,
        ):
            event_type = event.get("type")

            if event_type == "orchestration":
                msg_repo.add_routing(
                    session.id,
                    current_user.id,
                    content=event.get("content", ""),
                    extra_data={
                        "intent": event.get("intent"),
                        "complexity": event.get("complexity"),
                        "response_strategy": event.get("response_strategy"),
                        "reasoning": event.get("reasoning"),
                        "sub_queries": event.get("sub_queries"),
                        "agents": event.get("agents"),
                    },
                )
            elif event_type == "agent_response":
                msg_repo.add_agent_response(
                    session.id,
                    current_user.id,
                    content=event.get("content", ""),
                    agent_key=event.get("agent", ""),
                    agent_name=event.get("agent_name", ""),
                )
            elif event_type == "validation":
                msg_repo.add_validation(
                    session.id,
                    current_user.id,
                    agent_key=event.get("agent", ""),
                    content=event.get("content", ""),
                    score=event.get("score", 0.0),
                    passed=event.get("passed", False),
                    extra_data={
                        "scores": event.get("scores"),
                        "critique": event.get("critique", ""),
                    },
                )
            elif event_type == "synthesis":
                synthesis_text = event.get("content", "")
                msg_repo.add_synthesis(session.id, current_user.id, synthesis_text)
                history.append(
                    {
                        "role": "assistant",
                        "content": synthesis_text,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
            elif event_type == "done":
                # If no synthesis (single agent path), capture agent response as assistant turn
                if not any(m.get("role") == "assistant" for m in history[-2:]):
                    agent_responses = event.get("agent_responses", {})
                    if agent_responses:
                        history.append(
                            {
                                "role": "assistant",
                                "content": list(agent_responses.values())[0],
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        )
                await session_repo.update_history(session, history)
                await db.commit()

            yield event

    return StreamingResponse(
        _event_stream(stream()),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Session-ID": str(session.id)},
    )
