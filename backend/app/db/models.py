import uuid
from datetime import datetime
from typing import Any
from sqlalchemy import String, Boolean, JSON, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    onboarding_step: Mapped[int] = mapped_column(default=0)
    context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    conversation_history: Mapped[list[dict]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
