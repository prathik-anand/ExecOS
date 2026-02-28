"""Session Pydantic schemas."""

from __future__ import annotations
import uuid
from datetime import datetime
from pydantic import BaseModel


class SessionResponse(BaseModel):
    session_id: uuid.UUID
    created_at: datetime
    last_active_at: datetime
    message_count: int = 0

    model_config = {"from_attributes": True}
