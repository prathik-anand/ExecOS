"""
Session API controller — returns session metadata and memory count.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.database import get_db
from app.utils.security import get_current_user
from app.repository.session_repository import SessionRepository
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
