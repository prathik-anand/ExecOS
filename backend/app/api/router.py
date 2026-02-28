"""
API router — aggregates all v1 routes under /api/v1.
main.py mounts this single router.
"""

from fastapi import APIRouter
from app.api.v1 import auth, chat, session

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(chat.router)
router.include_router(session.router)
