from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.db.models import Session
import uuid


class SessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        session_id = request.headers.get("X-Session-ID")

        if session_id:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Session).where(Session.id == session_id)
                )
                session = result.scalar_one_or_none()

                if session is None:
                    session = Session(id=session_id)
                    db.add(session)
                    await db.commit()
                    await db.refresh(session)

                request.state.session = session
                request.state.session_id = session_id
        else:
            request.state.session = None
            request.state.session_id = None

        response = await call_next(request)
        return response
