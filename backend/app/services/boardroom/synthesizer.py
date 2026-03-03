"""
Synthesizer — merges multiple CXO responses into one boardroom briefing.

Single responsibility: synthesis only. No SSE, no DB, no validation.
"""

from crewai import Agent, Task, Crew, Process

from app.services.boardroom.orchestrator import OrchestratorPlan
from app.services.boardroom.prompts import AGENTS
from app.utils.llm import get_llm

_BACKSTORY = """You are the ExecOS Boardroom — the final voice of the executive team.
Your job is to distil one or more CXO perspectives into a single, clear executive response.
Lead with the most critical insight. When multiple perspectives exist, surface trade-offs honestly.
Give ONE clear recommendation with ownership. Be concise — every sentence earns its place."""

_OUTPUT = (
    "Boardroom Final Answer:\n"
    "- **Executive Summary** (2-3 sentences)\n"
    "- **Key Insights** (main findings; highlight trade-offs if multiple perspectives)\n"
    "- **The Recommendation** (one clear decision path with ownership)\n"
    "- **Next Steps** (3-5 prioritized actions)"
)


def synthesize(
    original_message: str,
    plan: OrchestratorPlan,
    context_str: str,
    agent_responses: dict[str, str],
) -> str:
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
