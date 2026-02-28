"""
Message Repository — all database operations for the ChatMessage model.

Single responsibility: write individual pipeline events as ChatMessage rows.
Each event type (user, routing, agent, validation, synthesis) maps to one method.
"""

import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_message import ChatMessage


class MessageRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _new(self, session_id: uuid.UUID, user_id: uuid.UUID, **kwargs) -> ChatMessage:
        msg = ChatMessage(
            id=uuid.uuid4(),
            session_id=session_id,
            user_id=user_id,
            created_at=datetime.utcnow(),
            **kwargs,
        )
        self.db.add(msg)
        return msg

    def add_user_message(
        self, session_id: uuid.UUID, user_id: uuid.UUID, content: str
    ) -> ChatMessage:
        return self._new(session_id, user_id, role="user", content=content)

    def add_routing(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        content: str,
        extra_data: dict,
    ) -> ChatMessage:
        return self._new(
            session_id, user_id, role="routing", content=content, extra_data=extra_data
        )

    def add_agent_response(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        content: str,
        agent_key: str,
        agent_name: str,
    ) -> ChatMessage:
        return self._new(
            session_id,
            user_id,
            role="agent",
            content=content,
            agent_key=agent_key,
            agent_name=agent_name,
        )

    def add_validation(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        agent_key: str,
        content: str,
        score: float,
        passed: bool,
        extra_data: dict,
    ) -> ChatMessage:
        return self._new(
            session_id,
            user_id,
            role="validation",
            content=content,
            agent_key=agent_key,
            validation_score=score,
            validation_passed=passed,
            extra_data=extra_data,
        )

    def add_synthesis(
        self, session_id: uuid.UUID, user_id: uuid.UUID, content: str
    ) -> ChatMessage:
        return self._new(session_id, user_id, role="synthesis", content=content)

    async def flush(self) -> None:
        """Flush pending inserts to DB within the current transaction."""
        await self.db.flush()
