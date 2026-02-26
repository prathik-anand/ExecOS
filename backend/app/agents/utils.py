"""
Shared utilities for the agents package.

Provides:
- get_llm()              — returns a configured CrewAI LLM instance
- build_user_context()   — serialises User ORM → readable string
- build_history()        — formats recent conversation turns for prompt injection
"""

import os

from crewai import LLM


def get_llm() -> LLM:
    """Return a configured Gemini LLM for CrewAI agents."""
    model = os.getenv("LLM_MODEL", "gemini/gemini-2.0-flash")
    api_key = os.getenv("GOOGLE_API_KEY")
    return LLM(model=model, api_key=api_key)


def build_user_context(user) -> str:
    """
    Serialise a User ORM object (or dict) into a readable context block
    for injection into agent prompts.
    """
    if user is None:
        return "No user context available."

    if hasattr(user, "__dict__"):
        fields = {
            "Name": getattr(user, "name", None),
            "Role": getattr(user, "role", None),
            "Company": getattr(user, "company_name", None),
            "Stage": getattr(user, "company_stage", None),
            "Industry": getattr(user, "industry", None),
            "Team size": getattr(user, "team_size", None),
            "Challenges": getattr(user, "current_challenges", None),
            "90-day goal": getattr(user, "goals", None),
        }
    else:
        fields = dict(user)

    lines = [f"{k}: {v}" for k, v in fields.items() if v]
    return "\n".join(lines) if lines else "No user context available."


def build_history(conversation_history: list, max_turns: int = 6) -> str:
    """
    Format the most recent N conversation turns into a readable string
    for prompt injection.
    """
    if not conversation_history:
        return "No previous conversation."

    recent = conversation_history[-max_turns:]
    return "\n".join(
        f"{m.get('role', 'user').upper()}: {m.get('content', '')}" for m in recent
    )
