"""
Executor — runs a SubQuery through its CXO agents via CrewAI.

Single responsibility: agent execution only. No validation, no synthesis, no SSE.
"""

from crewai import Agent, Task, Crew, Process

from app.services.boardroom.orchestrator import SubQuery
from app.services.boardroom.prompts import AGENTS
from app.utils.llm import get_llm


def run_sub_query(
    sq: SubQuery,
    context_str: str,
    memories_str: str,
    history_str: str,
) -> dict[str, str]:
    """
    Execute one SubQuery synchronously through assigned CXO agents.
    Returns {agent_key: response_text}. Runs in thread executor.
    """
    llm = get_llm()
    results: dict[str, str] = {}
    prompt_block = (
        f"USER PROFILE:\n{context_str}\n\n"
        f"PERSISTENT MEMORY:\n{memories_str}\n\n"
        f"RECENT CONVERSATION:\n{history_str}\n\n"
        f"QUERY:\n{sq.rewritten_query}\n\n"
        f"FOCUS AREA: {sq.focus}"
    )

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
            description=(
                f"As the {spec['name']}, analyse this executive query:\n\n"
                f"{prompt_block}\n\n"
                f"Stay focused on your domain as {spec['role']}."
            ),
            expected_output=(
                f"Structured response from {spec['name']}:\n"
                "- **Situation Assessment**\n"
                "- **Recommendation**\n"
                "- **Rationale** (2-3 reasons)\n"
                "- **Next Steps** (3-5 actions)"
            ),
            agent=agent,
        )
        crew = Crew(
            agents=[agent], tasks=[task], process=Process.sequential, verbose=False
        )
        results[key] = str(crew.kickoff().raw)

    return results
