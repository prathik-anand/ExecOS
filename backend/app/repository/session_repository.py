"""
Session Repository — all database operations for the Session model.

Single responsibility: CRUD for chat sessions. No HTTP, no business logic.
"""

import uuid
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import Session


class SessionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(
        self, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> Session | None:
        result = await self.db.execute(
            select(Session).where(
                Session.id == session_id,
                Session.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_all_for_user(self, user_id: uuid.UUID) -> list[Session]:
        result = await self.db.execute(
            select(Session)
            .where(Session.user_id == user_id)
            .order_by(Session.last_active_at.desc())
        )
        return list(result.scalars().all())

    async def create(self, user_id: uuid.UUID) -> Session:
        session = Session(id=uuid.uuid4(), user_id=user_id, conversation_history=[])
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def update_history(
        self, session: Session, history: list, last_active_at: datetime | None = None
    ) -> Session:
        session.conversation_history = history
        session.last_active_at = last_active_at or datetime.utcnow()
        await self.db.commit()
        return session
