"""
Boardroom public entry point.

Single responsibility: expose `run_boardroom` as the public API
for the chat endpoint. All logic lives in pipeline.py.
"""

from typing import AsyncGenerator
from app.agents.pipeline import run_pipeline


async def run_boardroom(
    message: str,
    user,
    conversation_history: list,
) -> AsyncGenerator[dict, None]:
    """Stream Boardroom pipeline events for the given user message."""
    async for event in run_pipeline(message, user, conversation_history):
        yield event
