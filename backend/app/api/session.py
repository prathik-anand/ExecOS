"""
GET /api/session — returns current user's profile + memory count.
"""

from fastapi import APIRouter, Depends
from app.auth.dependencies import get_current_user
from app.db.models import User
from app.memory.service import memory_count

router = APIRouter(prefix="/api", tags=["session"])


@router.get("/session")
async def get_session(current_user: User = Depends(get_current_user)):
    return {
        "user_id": str(current_user.id),
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role,
        "company_name": current_user.company_name,
        "company_stage": current_user.company_stage,
        "industry": current_user.industry,
        "team_size": current_user.team_size,
        "goals": current_user.goals,
        "onboarding_complete": current_user.onboarding_complete,
        "memory_count": memory_count(str(current_user.id)),
    }
