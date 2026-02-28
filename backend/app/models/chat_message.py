"""
ChatMessage ORM model — full transaction log.

Every user turn, CXO agent response, validation event, and synthesis
is a separate row. Provides complete auditability for every session.

role values:
  'user'       — user's original message
  'routing'    — orchestrator plan (extra_data holds intent/complexity/sub_queries)
  'agent'      — individual CXO agent response
  'validation' — validator score + critique for one agent response
  'synthesis'  — final merged boardroom briefing
"""

import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Text, ForeignKey, JSON, Integer, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )

    role: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Agent-specific (null for user / routing / synthesis rows)
    agent_key: Mapped[str | None] = mapped_column(String(50), nullable=True)
    agent_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Structured metadata (intent, scores, sub_queries, critique, etc.)
    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Quality tracking
    validation_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    validation_passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )

    session: Mapped["Session"] = relationship("Session", back_populates="messages")  # noqa: F821
