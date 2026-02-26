"""
Response Synthesizer module.

Single responsibility: merge multiple CXO agent responses into one
unified Boardroom Executive Briefing.

Public API:
    synthesize(original_message, plan, context_str, agent_responses) -> str

Returns the raw synthesis string. No SSE, no memory, no validation.
Designed to be called via loop.run_in_executor.
"""

from crewai import Agent, Task, Crew, Process

from app.agents.prompts import AGENTS
from app.agents.orchestrator import OrchestratorPlan
from app.agents.utils import get_llm


def synthesize(
    original_message: str,
    plan: OrchestratorPlan,
    context_str: str,
    agent_responses: dict[str, str],
) -> str:
    """
    Synthesise multiple CXO perspectives into a single executive briefing.

    If only one agent responded, returns that response directly (no LLM call).
    """
    if len(agent_responses) == 1:
        return list(agent_responses.values())[0]

    llm = get_llm()
    description = _build_synthesis_description(
        original_message, plan, context_str, agent_responses
    )

    boardroom_agent = Agent(
        role="Boardroom Orchestrator",
        goal="Synthesise multiple CXO perspectives into one unified, actionable executive briefing",
        backstory=_SYNTHESIZER_BACKSTORY,
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )
    task = Task(
        description=description,
        expected_output=_SYNTHESIS_OUTPUT_FORMAT,
        agent=boardroom_agent,
    )
    crew = Crew(
        agents=[boardroom_agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )
    return str(crew.kickoff().raw)


# ---------------------------------------------------------------------------
# Private constants & prompt builders
# ---------------------------------------------------------------------------

_SYNTHESIZER_BACKSTORY = """You are the ExecOS Boardroom — the final synthesiser.
You receive specialist perspectives from multiple CXOs and weave them into one cohesive response.
Lead with the single most critical insight. Surface tensions and trade-offs between CXO views honestly.
Give ONE clear recommendation with clear ownership. Close with 5 prioritized Next Steps.
Be executive-level concise — every sentence must earn its place."""

_SYNTHESIS_OUTPUT_FORMAT = """Unified Boardroom Executive Briefing:
- **Executive Summary** (3 sentences max)
- **Key Insights** (from CXO perspectives, including tensions/trade-offs)
- **The Recommendation** (one clear decision path)
- **Next Steps** (5 items, prioritized, with ownership hints)"""


def _build_synthesis_description(
    original_message: str,
    plan: OrchestratorPlan,
    context_str: str,
    agent_responses: dict[str, str],
) -> str:
    intent_line = (
        f"Intent: {plan.intent} | Complexity: {plan.complexity} | "
        f"Strategy: {plan.response_strategy}"
    )
    sub_query_lines = "\n".join(
        f"• {sq.focus}: answered by {', '.join(sq.agents)}" for sq in plan.sub_queries
    )
    perspectives = "\n\n".join(
        f"=== {AGENTS[k]['emoji']} {AGENTS[k]['name']} ===\n{v}"
        for k, v in agent_responses.items()
        if k in AGENTS
    )
    return (
        f'Synthesise for: "{original_message}"\n\n'
        f"{intent_line}\n"
        f"Sub-queries addressed:\n{sub_query_lines}\n\n"
        f"User context: {context_str}\n\n"
        f"CXO perspectives:\n{perspectives}"
    )
