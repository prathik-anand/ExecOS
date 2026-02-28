"""
ExecOS FastAPI Application Entry Point.

Mounts a single router (app/api/router.py) which aggregates all v1 routes.
DB initialisation runs once on startup via the lifespan manager.
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.utils.database import init_db
from app.api.router import router as api_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialise DB tables. Shutdown: nothing to clean up."""
    logger.info("Starting ExecOS backend — initialising database...")
    await init_db()
    logger.info("Database ready.")
    yield


app = FastAPI(
    title="ExecOS API",
    version="2.0.0",
    description="AI-powered executive boardroom — 5-stage LLM orchestration pipeline",
    lifespan=lifespan,
)

# CORS
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all API routes under /api/v1
app.include_router(api_router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}
