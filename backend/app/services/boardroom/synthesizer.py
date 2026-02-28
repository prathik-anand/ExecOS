"""
Synthesizer — merges multiple CXO responses into one boardroom briefing.

Single responsibility: synthesis only. No SSE, no DB, no validation.
"""

from crewai import Agent, Task, Crew, Process

from app.services.boardroom.orchestrator import OrchestratorPlan
from app.services.boardroom.prompts import AGENTS
from app.utils.llm import get_llm

_BACKSTORY = """You are the ExecOS Boardroom — the final synthesiser.
Weave specialist CXO perspectives into one cohesive executive response.
Lead with the single most critical insight. Surface tensions honestly.
Give ONE clear recommendation with clear ownership. Be concise — every sentence earns its place."""

_OUTPUT = (
    "Unified Boardroom Executive Briefing:\n"
    "- **Executive Summary** (3 sentences max)\n"
    "- **Key Insights** (include CXO tensions/trade-offs)\n"
    "- **The Recommendation** (one clear decision path)\n"
    "- **Next Steps** (5 items, prioritized)"
)


def synthesize(
    original_message: str,
    plan: OrchestratorPlan,
    context_str: str,
    agent_responses: dict[str, str],
) -> str:
    if len(agent_responses) == 1:
        return list(agent_responses.values())[0]

    llm = get_llm()
    perspectives = "\n\n".join(
        f"=== {AGENTS[k]['emoji']} {AGENTS[k]['name']} ===\n{v}"
        for k, v in agent_responses.items()
        if k in AGENTS
    )
    sub_lines = "\n".join(
        f"• {sq.focus}: {', '.join(sq.agents)}" for sq in plan.sub_queries
    )
    description = (
        f'Synthesise for: "{original_message}"\n\n'
        f"Intent: {plan.intent} | Complexity: {plan.complexity}\n"
        f"Sub-queries:\n{sub_lines}\n\n"
        f"User context: {context_str}\n\n"
        f"CXO Perspectives:\n{perspectives}"
    )
    boardroom_agent = Agent(
        role="Boardroom Orchestrator",
        goal="Synthesise CXO perspectives into a unified executive briefing",
        backstory=_BACKSTORY,
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )
    task = Task(description=description, expected_output=_OUTPUT, agent=boardroom_agent)
    crew = Crew(
        agents=[boardroom_agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )
    return str(crew.kickoff().raw)
