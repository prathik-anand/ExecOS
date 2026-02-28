"""
Memory Service — Mem0 integration for persistent user memories.

Single responsibility: store and retrieve facts per user_id.
Best-effort: all calls are wrapped in try/except so a Mem0 outage
never breaks the main chat flow.
"""

import logging
import os

logger = logging.getLogger(__name__)

_mem0_client = None


def _get_client():
    global _mem0_client
    if _mem0_client is not None:
        return _mem0_client
    try:
        from mem0 import Memory  # type: ignore

        mem0_api_key = os.getenv("MEM0_API_KEY")
        if mem0_api_key:
            _mem0_client = Memory.from_config({"api_key": mem0_api_key})
        else:
            google_api_key = os.getenv("GOOGLE_API_KEY")
            llm_model = os.getenv("LLM_MODEL", "gemini/gemini-2.0-flash").replace("gemini/", "")
            _mem0_client = Memory.from_config({
                "llm": {
                    "provider": "gemini",
                    "config": {
                        "model": llm_model,
                        "temperature": 0.2,
                        "max_tokens": 2000,
                        "api_key": google_api_key,
                    },
                },
                "embedder": {
                    "provider": "gemini",
                    "config": {
                        "model": "models/gemini-embedding-001",
                        "embedding_dims": 1536,
                        "api_key": google_api_key,
                    },
                },
            })
    except Exception as exc:
        logger.warning("Mem0 init failed: %s", exc)
        _mem0_client = None
    return _mem0_client


def search_memory(user_id: str, query: str, limit: int = 5) -> list[str]:
    """Return relevant memory strings for the query. Never raises."""
    try:
        client = _get_client()
        if client is None:
            return []
        results = client.search(query, user_id=user_id, limit=limit)
        return [r.get("memory", "") for r in (results or []) if r.get("memory")]
    except Exception as exc:
        logger.warning("Memory search failed: %s", exc)
        return []


def add_memory(user_id: str, content: str, metadata: dict | None = None) -> None:
    """Store a memory for the user. Never raises."""
    try:
        client = _get_client()
        if client is None:
            return
        client.add(content, user_id=user_id, metadata=metadata or {})
    except Exception as exc:
        logger.warning("Memory add failed: %s", exc)


def count_memories(user_id: str) -> int:
    """Return number of stored memories for display in the UI."""
    try:
        client = _get_client()
        if client is None:
            return 0
        results = client.get_all(user_id=user_id)
        return len(results or [])
    except Exception:
        return 0
