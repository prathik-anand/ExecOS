"""
FastAPI application entry point.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from app.db.database import init_db
from app.db import models  # noqa: F401 — ensures models are registered
from app.middleware.session import SessionMiddleware
from app.api.chat import router as chat_router
from app.api.session import router as session_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="ExecOS API",
    description="Boardroom AI — 42 Cloud CXO agents for every founder",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("FRONTEND_URL", "http://localhost:5173"),
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Session middleware (reads X-Session-ID header)
app.add_middleware(SessionMiddleware)

# Routes
app.include_router(chat_router, prefix="/api")
app.include_router(session_router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "ExecOS API running", "agents": 10, "status": "ready"}


@app.get("/health")
async def health():
    return {"status": "ok"}
