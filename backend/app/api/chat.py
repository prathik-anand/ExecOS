"""
POST /api/chat — main chat endpoint with SSE streaming.
Handles both onboarding (pre) and Boardroom (post) states.
"""

import json
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.db.models import Session
from app.onboarding.flow import get_next_question, get_completion_message, QUESTIONS
from app.agents.boardroom import run_boardroom

router = APIRouter()


class ChatRequest(BaseModel):
    message: str


async def event_stream(events):
    """Convert async generator of dicts to SSE format."""
    async for event in events:
        data = json.dumps(event)
        yield f"data: {data}\n\n"


async def onboarding_events(session: Session, message: str):
    """Handle onboarding step — store answer, yield next question or completion."""
    step = session.onboarding_step
    context = dict(session.context or {})

    # Store the answer for the current step
    if step < len(QUESTIONS):
        field = QUESTIONS[step]["field"]
        if message.strip().lower() not in ("skip", "skip for now", ""):
            context[field] = message.strip()
        step += 1

    # Check if onboarding is complete
    next_q = get_next_question(step, context)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Session).where(Session.id == session.id))
        db_session = result.scalar_one()
        db_session.context = context
        db_session.onboarding_step = step

        if next_q is None:
            db_session.onboarding_complete = True
            await db.commit()
            completion_msg = get_completion_message(context)
            yield {"type": "onboarding_complete", "content": completion_msg}
        else:
            await db.commit()
            yield {
                "type": "onboarding_question",
                "step": step,
                "total": len(QUESTIONS),
                "question": next_q,
            }

    yield {"type": "done", "content": ""}


async def boardroom_events(session: Session, message: str):
    """Route to Boardroom orchestrator and stream responses."""
    context = dict(session.context or {})
    history = list(session.conversation_history or [])

    # Append user message to history
    history.append({"role": "user", "content": message})

    # Stream Boardroom events
    synthesis_content = ""
    agent_contents = []

    async for event in run_boardroom(message, context, history):
        yield event
        if event["type"] == "synthesis":
            synthesis_content = event["content"]
        elif event["type"] == "agent_response" and not synthesis_content:
            agent_contents.append(event["content"])

    # Save conversation to DB
    final_response = synthesis_content or (agent_contents[0] if agent_contents else "")
    if final_response:
        history.append({"role": "assistant", "content": final_response})

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Session).where(Session.id == session.id))
        db_session = result.scalar_one()
        db_session.conversation_history = history[-20:]  # Keep last 20 messages
        await db.commit()


@router.post("/chat")
async def chat(request: Request, body: ChatRequest):
    session = request.state.session

    if session is None:

        async def no_session():
            yield {"type": "error", "content": "Missing X-Session-ID header"}
            yield {"type": "done", "content": ""}

        return StreamingResponse(
            event_stream(no_session()), media_type="text/event-stream"
        )

    if not session.onboarding_complete:
        # First message triggers first question if step == 0
        if session.onboarding_step == 0 and body.message.strip() == "":

            async def first_question():
                from app.onboarding.flow import get_next_question

                q = get_next_question(0, {})
                yield {
                    "type": "onboarding_question",
                    "step": 0,
                    "total": len(QUESTIONS),
                    "question": q,
                }
                yield {"type": "done", "content": ""}

            return StreamingResponse(
                event_stream(first_question()), media_type="text/event-stream"
            )

        return StreamingResponse(
            event_stream(onboarding_events(session, body.message)),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    return StreamingResponse(
        event_stream(boardroom_events(session, body.message)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/session/start")
async def start_session(request: Request):
    """Trigger onboarding first question for a fresh session."""
    session = request.state.session
    if session is None:
        return {"error": "Missing X-Session-ID header"}

    if session.onboarding_complete:
        context = dict(session.context or {})
        name = context.get("name", "")
        return {
            "status": "returning",
            "onboarding_complete": True,
            "context": context,
            "greeting": f"Welcome back{', ' + name if name else ''}. Your Boardroom is ready.",
        }

    next_q = get_next_question(session.onboarding_step, dict(session.context or {}))
    return {
        "status": "onboarding",
        "onboarding_complete": False,
        "step": session.onboarding_step,
        "total": len(QUESTIONS),
        "question": next_q,
    }
