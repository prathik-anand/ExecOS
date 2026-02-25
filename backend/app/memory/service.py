"""
Mem0 memory service — local ChromaDB mode by default.
Set MEM0_API_KEY env var to switch to Mem0 cloud.
"""

import os
from mem0 import Memory, MemoryClient

_mem0_instance = None


def _get_mem0():
    global _mem0_instance
    if _mem0_instance is None:
        api_key = os.getenv("MEM0_API_KEY")
        if api_key:
            _mem0_instance = MemoryClient(api_key=api_key)
        else:
            # Local mode — ChromaDB vector store, no API key needed
            _mem0_instance = Memory()
    return _mem0_instance


def add_memory(user_id: str, content: str, metadata: dict | None = None) -> None:
    """Store a new memory for a user."""
    try:
        mem = _get_mem0()
        mem.add(content, user_id=user_id, metadata=metadata or {})
    except Exception:
        pass  # Memory is best-effort — don't block the main flow


def search_memory(user_id: str, query: str, limit: int = 5) -> list[str]:
    """Search relevant memories for a user query."""
    try:
        mem = _get_mem0()
        results = mem.search(query, user_id=user_id, limit=limit)
        # Handle both cloud and local response formats
        if isinstance(results, dict):
            results = results.get("results", [])
        return [r.get("memory", str(r)) for r in results if r]
    except Exception:
        return []


def get_all_memories(user_id: str) -> list[dict]:
    """Get all memories for a user (for sidebar display)."""
    try:
        mem = _get_mem0()
        results = mem.get_all(user_id=user_id)
        if isinstance(results, dict):
            results = results.get("results", [])
        return results or []
    except Exception:
        return []


def memory_count(user_id: str) -> int:
    return len(get_all_memories(user_id))
