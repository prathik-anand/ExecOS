"""
GET /api/session — return current session details.
"""

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/session")
async def get_session(request: Request):
    session = request.state.session
    if session is None:
        return {"error": "Missing X-Session-ID header"}

    return {
        "id": session.id,
        "onboarding_complete": session.onboarding_complete,
        "onboarding_step": session.onboarding_step,
        "context": session.context or {},
        "conversation_count": len(session.conversation_history or []),
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "last_active_at": session.last_active_at.isoformat()
        if session.last_active_at
        else None,
    }
