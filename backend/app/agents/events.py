"""
SSE Event factory module.

Single responsibility: build well-typed SSE event dicts for every
event emitted by the pipeline. No business logic — pure data construction.

Event types:
  orchestration     — LLM routing plan (intent, complexity, sub-queries)
  routing           — legacy agent list for Sidebar highlighting
  agent_reasoning   — "Agent X is thinking..." indicator
  validation        — quality check result (pass/fail, score, critique)
  agent_response    — final agent response content
  synthesis_start   — synthesis underway indicator
  synthesis         — merged boardroom briefing
  error             — pipeline error
  done              — stream terminated
"""

from app.agents.prompts import AGENTS
from app.agents.orchestrator import OrchestratorPlan


def orchestration_event(plan: OrchestratorPlan, unique_agents: list[str]) -> dict:
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
        "content": _routing_summary(plan),
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
    agent_name = AGENTS[agent_key]["name"] if agent_key in AGENTS else agent_key
    if is_retry:
        icon = "✅" if passed else "⚠️"
        content = f"{icon} Retry result: {agent_name} scored {score:.1f}/10"
    elif passed:
        content = f"✅ Quality check: {agent_name} passed ({score:.1f}/10)"
    else:
        content = f"🔍 Quality check: {agent_name} scored {score:.1f}/10 — refining..."

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


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _routing_summary(plan: OrchestratorPlan) -> str:
    intent_emoji = {
        "decision": "⚖️",
        "analysis": "📊",
        "planning": "🗺️",
        "brainstorm": "💡",
        "check-in": "📋",
    }.get(plan.intent, "🎯")
    complexity_label = {
        "simple": "Direct query",
        "compound": "Compound query",
        "complex": "Complex query",
    }.get(plan.complexity, plan.complexity)
    parts = [f"{intent_emoji} {plan.intent.title()} · {complexity_label}"]
    if len(plan.sub_queries) > 1:
        parts.append(f"· {len(plan.sub_queries)} sub-queries decomposed")
    return " ".join(parts)
