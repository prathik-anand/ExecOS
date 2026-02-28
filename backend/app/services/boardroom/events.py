"""
SSE Event factory — pure data construction, no business logic.
One function per event type. Every SSE dict shape is defined here.
"""

from app.services.boardroom.prompts import AGENTS
from app.services.boardroom.orchestrator import OrchestratorPlan


def orchestration_event(plan: OrchestratorPlan, unique_agents: list[str]) -> dict:
    icons = {
        "decision": "⚖️",
        "analysis": "📊",
        "planning": "🗺️",
        "brainstorm": "💡",
        "check-in": "📋",
    }
    labels = {
        "simple": "Direct query",
        "compound": "Compound query",
        "complex": "Complex query",
    }
    summary = f"{icons.get(plan.intent, '🎯')} {plan.intent.title()} · {labels.get(plan.complexity, plan.complexity)}"
    if len(plan.sub_queries) > 1:
        summary += f" · {len(plan.sub_queries)} sub-queries"
    return {
        "type": "orchestration",
        "intent": plan.intent,
        "complexity": plan.complexity,
        "response_strategy": plan.response_strategy,
        "reasoning": plan.reasoning,
        "sub_queries": [
            {"id": sq.id, "focus": sq.focus, "agents": sq.agents}
            for sq in plan.sub_queries
        ],
        "agents": unique_agents,
        "content": summary,
    }


def routing_event(unique_agents: list[str]) -> dict:
    names = [
        f"{AGENTS[k]['emoji']} {AGENTS[k]['name']}"
        for k in unique_agents
        if k in AGENTS
    ]
    return {
        "type": "routing",
        "content": f"Routing to: {', '.join(names)}",
        "agents": unique_agents,
    }


def agent_reasoning_event(agent_key: str) -> dict | None:
    spec = AGENTS.get(agent_key)
    if not spec:
        return None
    return {
        "type": "agent_reasoning",
        "agent": agent_key,
        "agent_name": spec["name"],
        "agent_emoji": spec["emoji"],
        "agent_color": spec["color"],
        "content": f"{spec['name']} is analysing your request...",
    }


def validation_event(
    agent_key: str,
    passed: bool,
    score: float,
    scores: dict,
    critique: str = "",
    is_retry: bool = False,
) -> dict:
    name = AGENTS[agent_key]["name"] if agent_key in AGENTS else agent_key
    if is_retry:
        content = f"{'✅' if passed else '⚠️'} Retry: {name} scored {score:.1f}/10"
    elif passed:
        content = f"✅ Quality check: {name} passed ({score:.1f}/10)"
    else:
        content = f"🔍 Quality check: {name} scored {score:.1f}/10 — refining..."
    return {
        "type": "validation",
        "agent": agent_key,
        "passed": passed,
        "score": score,
        "scores": scores,
        "critique": critique,
        "content": content,
    }


def agent_response_event(agent_key: str, response_text: str) -> dict | None:
    spec = AGENTS.get(agent_key)
    if not spec:
        return None
    return {
        "type": "agent_response",
        "agent": agent_key,
        "agent_name": spec["name"],
        "agent_emoji": spec["emoji"],
        "agent_color": spec["color"],
        "content": response_text,
    }


def synthesis_start_event() -> dict:
    return {
        "type": "synthesis_start",
        "content": "Boardroom synthesising perspectives...",
    }


def synthesis_event(content: str) -> dict:
    return {"type": "synthesis", "content": content}


def error_event(message: str) -> dict:
    return {"type": "error", "content": message}


def done_event(memory_count: int = 0) -> dict:
    return {"type": "done", "content": "", "memory_count": memory_count}
