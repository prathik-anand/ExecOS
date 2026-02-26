"""
Agent Executor module.

Single responsibility: run a SubQuery through its assigned CrewAI agents
and return raw response strings. No validation, no synthesis, no SSE.

Public API:
    run_sub_query(sq, context_str, memories_str, history_str) -> dict[str, str]
"""

from crewai import Agent, Task, Crew, Process

from app.agents.prompts import AGENTS
from app.agents.orchestrator import SubQuery
from app.agents.utils import get_llm


def run_sub_query(
    sq: SubQuery,
    context_str: str,
    memories_str: str,
    history_str: str,
) -> dict[str, str]:
    """
    Execute a single SubQuery through its assigned CXO agents synchronously.
    Each agent receives the orchestrator-rewritten (context-enriched) query.

    Returns:
        {agent_key: response_text} for every agent in sq.agents.

    Designed to be called via loop.run_in_executor — NOT called directly in async code.
    """
    llm = get_llm()
    results: dict[str, str] = {}

    prompt_block = _build_prompt_block(sq, context_str, memories_str, history_str)

    for key in sq.agents:
        spec = AGENTS.get(key)
        if not spec:
            continue

        agent = Agent(
            role=spec["role"],
            goal=spec["goal"],
            backstory=spec["backstory"],
            llm=llm,
            verbose=False,
            allow_delegation=False,
        )
        task = Task(
            description=_build_task_description(spec, prompt_block),
            expected_output=_build_expected_output(spec),
            agent=agent,
        )
        crew = Crew(
            agents=[agent], tasks=[task], process=Process.sequential, verbose=False
        )
        results[key] = str(crew.kickoff().raw)

    return results


# ---------------------------------------------------------------------------
# Private prompt builders — kept here because they are executor-specific
# ---------------------------------------------------------------------------


def _build_prompt_block(
    sq: SubQuery,
    context_str: str,
    memories_str: str,
    history_str: str,
) -> str:
    return (
        f"USER PROFILE:\n{context_str}\n\n"
        f"PERSISTENT MEMORY (past decisions & context):\n{memories_str}\n\n"
        f"RECENT CONVERSATION:\n{history_str}\n\n"
        f"QUERY (enriched & focused):\n{sq.rewritten_query}\n\n"
        f"FOCUS AREA: {sq.focus}"
    )


def _build_task_description(spec: dict, prompt_block: str) -> str:
    return (
        f"As the {spec['name']}, analyse the following executive query and provide "
        f"your authoritative perspective.\n\n"
        f"{prompt_block}\n\n"
        f"Stay laser-focused on your domain as {spec['role']}. "
        f"Reference the persistent memory to maintain continuity."
    )


def _build_expected_output(spec: dict) -> str:
    return (
        f"Structured executive response from {spec['name']}:\n"
        "- **Situation Assessment**: What you see given the user context\n"
        "- **Recommendation**: Your specific, actionable recommendation\n"
        "- **Rationale**: 2-3 key reasons why\n"
        "- **Next Steps**: 3-5 concrete, prioritized actions"
    )
