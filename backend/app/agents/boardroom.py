"""
Boardroom orchestrator using CrewAI + Gemini with Mem0 persistent memory.

Gold-standard flow:
  1. Fetch Mem0 memories for context
  2. Call orchestrator LLM → intent / decompose / rewrite / route
  3. Yield "orchestration" SSE event (intent, complexity, sub-queries)
  4. Run each sub-query's agents in parallel via asyncio.gather
  5. Yield individual agent_response events
  6. Synthesise all results into one Boardroom briefing
  7. Store memory, yield "done"
"""

import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from typing import AsyncGenerator

from crewai import Agent, Task, Crew, Process, LLM

from app.agents.prompts import AGENTS
from app.agents.orchestrator import orchestrate_sync, OrchestratorPlan, SubQuery
from app.memory.service import search_memory, add_memory

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=8)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_llm() -> LLM:
    model = os.getenv("LLM_MODEL", "gemini/gemini-2.0-flash")
    api_key = os.getenv("GOOGLE_API_KEY")
    return LLM(model=model, api_key=api_key)


def build_user_context_string(user) -> str:
    if user is None:
        return "No user context available."
    if hasattr(user, "__dict__"):
        ctx = {
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
        ctx = user
    parts = [f"{k}: {v}" for k, v in ctx.items() if v]
    return "\n".join(parts) if parts else "No user context available."


def build_history_string(conversation_history: list) -> str:
    if not conversation_history:
        return "No previous conversation."
    recent = conversation_history[-6:]
    return "\n".join(
        f"{m.get('role', 'user').upper()}: {m.get('content', '')}" for m in recent
    )


# ---------------------------------------------------------------------------
# Agent execution — run ONE sub-query through its assigned agents
# ---------------------------------------------------------------------------


def _run_sub_query_sync(
    sq: SubQuery,
    context_str: str,
    memories_str: str,
    history_str: str,
) -> dict[str, str]:
    """
    Run a single sub-query through its assigned CXO agents.
    Each agent receives the rewritten (context-enriched) query.
    Returns {agent_key: response_text}.
    """
    llm = _get_llm()
    results: dict[str, str] = {}

    user_block = f"""USER PROFILE:
{context_str}

PERSISTENT MEMORY (past decisions & context):
{memories_str}

RECENT CONVERSATION:
{history_str}

QUERY (enriched & focused):
{sq.rewritten_query}

FOCUS AREA: {sq.focus}"""

    for key in sq.agents:
        if key not in AGENTS:
            continue
        spec = AGENTS[key]
        agent = Agent(
            role=spec["role"],
            goal=spec["goal"],
            backstory=spec["backstory"],
            llm=llm,
            verbose=False,
            allow_delegation=False,
        )
        task = Task(
            description=f"""As the {spec["name"]}, analyse the following executive query and provide your authoritative perspective.

{user_block}

Stay laser-focused on your domain as {spec["role"]}. Reference the persistent memory to maintain continuity.""",
            expected_output=f"""Structured executive response from {spec["name"]}:
- **Situation Assessment**: What you see given the user context
- **Recommendation**: Your specific, actionable recommendation
- **Rationale**: 2-3 key reasons why
- **Next Steps**: 3-5 concrete, prioritized actions""",
            agent=agent,
        )
        crew = Crew(
            agents=[agent], tasks=[task], process=Process.sequential, verbose=False
        )
        result = crew.kickoff()
        results[key] = str(result.raw)

    return results


# ---------------------------------------------------------------------------
# Synthesis
# ---------------------------------------------------------------------------


def _synthesize_sync(
    original_message: str,
    plan: OrchestratorPlan,
    context_str: str,
    all_responses: dict[str, str],
) -> str:
    """Weave all agent responses into one Boardroom Executive Briefing."""
    if len(all_responses) == 1:
        return list(all_responses.values())[0]

    llm = _get_llm()
    responses_text = "\n\n".join(
        f"=== {AGENTS[k]['emoji']} {AGENTS[k]['name']} ===\n{v}"
        for k, v in all_responses.items()
        if k in AGENTS
    )

    intent_context = f"Intent: {plan.intent} | Complexity: {plan.complexity} | Strategy: {plan.response_strategy}"
    sub_query_summary = "\n".join(
        f"• {sq.focus}: answered by {', '.join(sq.agents)}" for sq in plan.sub_queries
    )

    boardroom_agent = Agent(
        role="Boardroom Orchestrator",
        goal="Synthesise multiple CXO perspectives into one unified, actionable executive briefing",
        backstory="""You are the ExecOS Boardroom — the final synthesiser.
You receive specialist perspectives from multiple CXOs and weave them into one cohesive response.
Lead with the single most critical insight. Surface tensions and trade-offs between CXO views honestly.
Give ONE clear recommendation with clear ownership. Close with 5 prioritized Next Steps.
Be executive-level concise — every sentence must earn its place.""",
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )
    task = Task(
        description=f"""Synthesise for: "{original_message}"

{intent_context}
Sub-queries addressed:
{sub_query_summary}

User context: {context_str}

CXO perspectives:
{responses_text}""",
        expected_output="""Unified Boardroom Executive Briefing:
- **Executive Summary** (3 sentences max)
- **Key Insights** (from CXO perspectives, including tensions/trade-offs)
- **The Recommendation** (one clear decision path)
- **Next Steps** (5 items, prioritized, with ownership hints)""",
        agent=boardroom_agent,
    )
    crew = Crew(
        agents=[boardroom_agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )
    return str(crew.kickoff().raw)


def _store_memory_sync(
    user_id: str, message: str, response_summary: str, agents_used: list[str]
):
    memory_content = (
        f"User asked: {message}\n"
        f"Agents: {', '.join(agents_used)}\n"
        f"Key advice: {response_summary[:600]}"
    )
    add_memory(user_id, memory_content, metadata={"agents": agents_used})


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


async def run_boardroom(
    message: str,
    user,
    conversation_history: list,
) -> AsyncGenerator[dict, None]:
    loop = asyncio.get_event_loop()
    user_id = str(user.id) if hasattr(user, "id") else str(user)
    context_str = build_user_context_string(user)
    history_str = build_history_string(conversation_history)

    # ── 1. Fetch memories ────────────────────────────────────────────────────
    memories: list[str] = await loop.run_in_executor(
        _executor, search_memory, user_id, message
    )
    memories_str = (
        "\n".join(f"- {m}" for m in memories)
        if memories
        else "No relevant memories yet."
    )

    # ── 2. Orchestrate (intent → decompose → rewrite → route) ────────────────
    plan: OrchestratorPlan = await loop.run_in_executor(
        _executor,
        orchestrate_sync,
        message,
        context_str,
        memories_str,
        history_str,
    )

    # ── 3. Emit orchestration event (shows intent + decomposition in UI) ──────
    all_agents: list[str] = []
    for sq in plan.sub_queries:
        all_agents.extend(sq.agents)
    unique_agents = list(dict.fromkeys(all_agents))  # preserve order, deduplicate

    yield {
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
        "content": _build_routing_summary(plan),
    }

    # Also emit the legacy routing event so Sidebar still lights up correctly
    agent_names = [
        f"{AGENTS[k]['emoji']} {AGENTS[k]['name']}"
        for k in unique_agents
        if k in AGENTS
    ]
    yield {
        "type": "routing",
        "content": f"Routing to: {', '.join(agent_names)}",
        "agents": unique_agents,
    }

    # Announce thinking for each unique agent
    for key in unique_agents:
        if key not in AGENTS:
            continue
        spec = AGENTS[key]
        yield {
            "type": "agent_reasoning",
            "agent": key,
            "agent_name": spec["name"],
            "agent_emoji": spec["emoji"],
            "agent_color": spec["color"],
            "content": f"{spec['name']} is analysing your request...",
        }

    # ── 4. Run sub-queries in parallel ───────────────────────────────────────
    async def run_sub_query(sq: SubQuery) -> dict[str, str]:
        return await loop.run_in_executor(
            _executor,
            _run_sub_query_sync,
            sq,
            context_str,
            memories_str,
            history_str,
        )

    try:
        sub_results: list[dict[str, str]] = await asyncio.gather(
            *[run_sub_query(sq) for sq in plan.sub_queries],
            return_exceptions=False,
        )
    except Exception as e:
        logger.error("Agent execution error: %s", e)
        yield {"type": "error", "content": f"Agent error: {str(e)}"}
        yield {"type": "done", "content": ""}
        return

    # Merge all sub-query results into one flat dict (agent_key → response)
    all_responses: dict[str, str] = {}
    for sub_resp in sub_results:
        for agent_key, text in sub_resp.items():
            if agent_key not in all_responses:
                all_responses[agent_key] = text
            else:
                # Agent appeared in multiple sub-queries — append both perspectives
                all_responses[agent_key] += f"\n\n---\n\n{text}"

    # ── 5. Emit individual agent responses ───────────────────────────────────
    for key, response_text in all_responses.items():
        if key not in AGENTS:
            continue
        spec = AGENTS[key]
        yield {
            "type": "agent_response",
            "agent": key,
            "agent_name": spec["name"],
            "agent_emoji": spec["emoji"],
            "agent_color": spec["color"],
            "content": response_text,
        }

    # ── 6. Synthesise ────────────────────────────────────────────────────────
    final_response = ""
    if len(all_responses) > 1 or plan.response_strategy == "synthesis":
        yield {
            "type": "synthesis_start",
            "content": "Boardroom synthesising perspectives...",
        }
        try:
            synthesis = await loop.run_in_executor(
                _executor,
                _synthesize_sync,
                message,
                plan,
                context_str,
                all_responses,
            )
            final_response = synthesis
            yield {"type": "synthesis", "content": synthesis}
        except Exception as exc:
            logger.warning("Synthesis failed: %s", exc)
            final_response = list(all_responses.values())[0]
            yield {"type": "synthesis", "content": final_response}
    else:
        final_response = list(all_responses.values())[0] if all_responses else ""

    # ── 7. Store memory ───────────────────────────────────────────────────────
    agents_used = list(all_responses.keys())
    asyncio.create_task(
        loop.run_in_executor(
            _executor,
            _store_memory_sync,
            user_id,
            message,
            final_response,
            agents_used,
        )
    )

    yield {"type": "done", "content": "", "memory_count": len(memories)}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_routing_summary(plan: OrchestratorPlan) -> str:
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
