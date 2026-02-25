"""
Boardroom orchestrator using CrewAI framework with Google Gemini.

Flow:
1. Receive user message + session context
2. Classify intent → select which CXO agents to invoke
3. Build CrewAI Agents and Tasks dynamically
4. Run Crew (in thread executor, since crewai is synchronous)
5. Yield SSE events: routing, agent_response, synthesis, done
"""

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from typing import AsyncGenerator

from crewai import Agent, Task, Crew, Process, LLM
from app.agents.prompts import AGENTS, AGENT_KEYS

_executor = ThreadPoolExecutor(max_workers=4)


def _get_llm() -> LLM:
    """Return a configured Gemini LLM. Model is configurable via LLM_MODEL env var."""
    model = os.getenv("LLM_MODEL", "gemini/gemini-2.0-flash")
    api_key = os.getenv("GOOGLE_API_KEY")
    return LLM(model=model, api_key=api_key)


def build_user_context_string(context: dict) -> str:
    if not context:
        return "No user context available yet."
    parts = []
    if context.get("name"):
        parts.append(f"Name: {context['name']}")
    if context.get("role"):
        parts.append(f"Role: {context['role']}")
    if context.get("company_name"):
        parts.append(f"Company: {context['company_name']}")
    if context.get("company_stage"):
        parts.append(f"Stage: {context['company_stage']}")
    if context.get("industry"):
        parts.append(f"Industry: {context['industry']}")
    if context.get("team_size"):
        parts.append(f"Team size: {context['team_size']}")
    if context.get("current_challenges"):
        parts.append(f"Challenges: {context['current_challenges']}")
    if context.get("goals"):
        parts.append(f"90-day goal: {context['goals']}")
    return "\n".join(parts) if parts else "No user context available yet."


def build_history_string(conversation_history: list) -> str:
    if not conversation_history:
        return "No previous conversation."
    recent = conversation_history[-6:]
    return "\n".join(
        f"{m.get('role', 'user').upper()}: {m.get('content', '')}" for m in recent
    )


def _classify_by_keyword(message: str) -> list[str]:
    """Fast keyword-based agent selection. Returns up to 3 matches."""
    msg_lower = message.lower()
    upper_msg = message.upper()

    # Explicit @mention
    explicit = [k for k in AGENT_KEYS if f"@{k}" in upper_msg]
    if explicit:
        return explicit[:3]

    # Keyword match
    matches = []
    for key, agent in AGENTS.items():
        if any(kw.lower() in msg_lower for kw in agent["trigger_keywords"]):
            matches.append(key)
        if len(matches) >= 3:
            break
    return matches or ["CEO"]


def _run_crew_sync(
    selected_agent_keys: list[str],
    message: str,
    context: dict,
    conversation_history: list,
) -> dict[str, str]:
    """
    Synchronous function that creates and kicks off a CrewAI Crew.
    Returns dict of {agent_key: response_text}.
    Called from a thread executor.
    """
    llm = _get_llm()
    context_str = build_user_context_string(context)
    history_str = build_history_string(conversation_history)

    user_context_block = f"""USER CONTEXT:
{context_str}

RECENT CONVERSATION:
{history_str}

USER QUERY:
{message}"""

    # Build CrewAI Agents
    crew_agents = []
    crew_tasks = []
    agent_map: dict[str, Agent] = {}

    for key in selected_agent_keys:
        spec = AGENTS[key]
        agent = Agent(
            role=spec["role"],
            goal=spec["goal"],
            backstory=spec["backstory"],
            llm=llm,
            verbose=False,
            allow_delegation=False,
        )
        crew_agents.append(agent)
        agent_map[key] = agent

    # Build a Task per agent
    for key in selected_agent_keys:
        agent = agent_map[key]
        spec = AGENTS[key]
        task = Task(
            description=f"""As the {spec["name"]}, analyze the following and provide your executive perspective:

{user_context_block}

Focus specifically on aspects within your domain as {spec["role"]}.
Be direct, specific, and actionable. Use your signature frameworks and mental models.""",
            expected_output=f"""A structured executive response from the {spec["name"]} including:
- Situation Assessment
- Recommendation  
- Rationale
- Next Steps (3-5 items)""",
            agent=agent,
        )
        crew_tasks.append(task)

    # Add synthesis task if multiple agents
    results: dict[str, str] = {}

    if len(selected_agent_keys) == 1:
        crew = Crew(
            agents=crew_agents,
            tasks=crew_tasks,
            process=Process.sequential,
            verbose=False,
        )
        result = crew.kickoff()
        results[selected_agent_keys[0]] = str(result.raw)
    else:
        # Run agents sequentially, collecting per-agent outputs
        for key, agent, task in zip(selected_agent_keys, crew_agents, crew_tasks):
            single_crew = Crew(
                agents=[agent],
                tasks=[task],
                process=Process.sequential,
                verbose=False,
            )
            single_result = single_crew.kickoff()
            results[key] = str(single_result.raw)

    return results


def _synthesize_sync(
    message: str,
    context: dict,
    agent_responses: dict[str, str],
) -> str:
    """Synthesize multiple agent responses into a unified executive briefing."""
    if len(agent_responses) == 1:
        return list(agent_responses.values())[0]

    llm = _get_llm()
    context_str = build_user_context_string(context)
    responses_text = "\n\n".join(
        f"=== {AGENTS[k]['emoji']} {AGENTS[k]['name']} ===\n{v}"
        for k, v in agent_responses.items()
    )

    boardroom_agent = Agent(
        role="Boardroom Orchestrator",
        goal="Synthesize diverse CXO perspectives into a single, coherent executive briefing",
        backstory="""You are the Boardroom — the master orchestrator of ExecOS.
You receive inputs from multiple CXO agents and synthesize them into one clear executive briefing.
Rules: Start with the most urgent insight. Surface tensions/trade-offs explicitly.
Give ONE clear recommendation. End with 3-5 prioritized next steps. Use markdown headers.""",
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    synthesis_task = Task(
        description=f"""Synthesize these CXO perspectives into a unified Boardroom executive briefing.

User query: "{message}"

User context:
{context_str}

Agent perspectives:
{responses_text}

Create a single, coherent executive briefing that integrates all perspectives.""",
        expected_output="""A unified executive briefing with:
- Opening with the most critical insight
- Key recommendations (with trade-offs if agents disagree)
- 3-5 prioritized Next Steps""",
        agent=boardroom_agent,
    )

    crew = Crew(
        agents=[boardroom_agent],
        tasks=[synthesis_task],
        process=Process.sequential,
        verbose=False,
    )
    result = crew.kickoff()
    return str(result.raw)


async def run_boardroom(
    message: str,
    context: dict,
    conversation_history: list,
) -> AsyncGenerator[dict, None]:
    """
    Async generator that yields SSE-ready event dicts.
    Runs CrewAI in a thread executor to keep FastAPI non-blocking.
    """
    loop = asyncio.get_event_loop()

    # Step 1: Route
    selected_agents = _classify_by_keyword(message)
    agent_names = [f"{AGENTS[k]['emoji']} {AGENTS[k]['name']}" for k in selected_agents]
    yield {
        "type": "routing",
        "content": f"Routing to: {', '.join(agent_names)}",
        "agents": selected_agents,
    }

    # Step 2: Announce agents working
    for key in selected_agents:
        spec = AGENTS[key]
        yield {
            "type": "agent_reasoning",
            "agent": key,
            "agent_name": spec["name"],
            "agent_emoji": spec["emoji"],
            "agent_color": spec["color"],
            "content": f"{spec['name']} is analyzing your request...",
        }

    # Step 3: Run CrewAI in thread executor
    try:
        agent_responses: dict[str, str] = await loop.run_in_executor(
            _executor,
            _run_crew_sync,
            selected_agents,
            message,
            context,
            conversation_history,
        )
    except Exception as e:
        yield {"type": "error", "content": f"Agent error: {str(e)}"}
        yield {"type": "done", "content": ""}
        return

    # Step 4: Emit individual agent responses
    for key, response_text in agent_responses.items():
        spec = AGENTS[key]
        yield {
            "type": "agent_response",
            "agent": key,
            "agent_name": spec["name"],
            "agent_emoji": spec["emoji"],
            "agent_color": spec["color"],
            "content": response_text,
        }

    # Step 5: Synthesize if multiple agents
    if len(agent_responses) > 1:
        yield {
            "type": "synthesis_start",
            "content": "Boardroom synthesizing perspectives...",
        }
        try:
            synthesis = await loop.run_in_executor(
                _executor,
                _synthesize_sync,
                message,
                context,
                agent_responses,
            )
            yield {"type": "synthesis", "content": synthesis}
        except Exception:
            yield {"type": "synthesis", "content": list(agent_responses.values())[0]}

    yield {"type": "done", "content": ""}
