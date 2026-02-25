"""
ExecOS FastAPI application entry point.
- JWT-based user authentication (no anonymous sessions)
- PostgreSQL via asyncpg + SQLAlchemy async
- Mem0 persistent memory for all users
- CrewAI + Gemini multi-agent Boardroom
"""

import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from app.db.database import init_db
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.session import router as session_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="ExecOS API", version="2.0.0", lifespan=lifespan)

# CORS
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(session_router)


@app.get("/")
async def root():
    return {"status": "ok", "app": "ExecOS", "version": "2.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
