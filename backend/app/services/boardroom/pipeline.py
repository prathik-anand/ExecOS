"""
Boardroom Pipeline — async coordinator for the full AI response cycle.

Chains: memory retrieval → orchestration → parallel execution → validation → synthesis → memory store.
Yields SSE event dicts. No HTTP, no DB queries — pure pipeline logic.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import AsyncGenerator

from app.services.boardroom.orchestrator import (
    orchestrate_sync,
    OrchestratorPlan,
    SubQuery,
)
from app.services.boardroom.executor import run_sub_query
from app.services.boardroom.validator import validate_response_sync, MAX_RETRIES
from app.services.boardroom.synthesizer import synthesize
from app.services.boardroom.events import (
    orchestration_event,
    routing_event,
    agent_reasoning_event,
    validation_event,
    agent_response_event,
    synthesis_start_event,
    synthesis_event,
    error_event,
    done_event,
)
from app.utils.llm import build_user_context, build_history
from app.services.memory_service import search_memory, add_memory

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=8)


async def run_pipeline(
    message: str,
    user,
    conversation_history: list,
) -> AsyncGenerator[dict, None]:
    """Stream SSE event dicts for the full Boardroom pipeline."""
    loop = asyncio.get_event_loop()
    user_id = str(user.id) if hasattr(user, "id") else str(user)
    context_str = build_user_context(user)
    history_str = build_history(conversation_history)

    # ── 1. Memory Retrieval ───────────────────────────────────────────────────
    memories: list[str] = await loop.run_in_executor(
        _executor, search_memory, user_id, message
    )
    memories_str = (
        "\n".join(f"- {m}" for m in memories)
        if memories
        else "No relevant memories yet."
    )

    # ── 2. Orchestration ─────────────────────────────────────────────────────
    plan: OrchestratorPlan = await loop.run_in_executor(
        _executor, orchestrate_sync, message, context_str, memories_str, history_str
    )
    unique_agents = _unique_agents(plan)
    yield orchestration_event(plan, unique_agents)
    yield routing_event(unique_agents)
    for key in unique_agents:
        event = agent_reasoning_event(key)
        if event:
            yield event

    # ── 3+4. Parallel Execution + Validation ─────────────────────────────────
    try:
        sq_results = await asyncio.gather(
            *[
                _execute_and_validate(loop, sq, context_str, memories_str, history_str)
                for sq in plan.sub_queries
            ],
            return_exceptions=False,
        )
    except Exception as exc:
        logger.error("Pipeline error: %s", exc)
        yield error_event(str(exc))
        yield done_event()
        return

    all_responses: dict[str, str] = {}
    all_val_events: list[dict] = []
    all_retry_counts: dict[str, int] = {}

    for sub_resp, val_events, retries in sq_results:
        all_val_events.extend(val_events)
        for key, text in sub_resp.items():
            all_responses[key] = all_responses.get(key, "") + (
                f"\n\n---\n\n{text}" if key in all_responses else text
            )
            all_retry_counts[key] = retries.get(key, 0)

    for val_event in all_val_events:
        yield val_event

    # ── 5a. Agent Responses ──────────────────────────────────────────────────
    for agent_key, response_text in all_responses.items():
        event = agent_response_event(agent_key, response_text)
        if event:
            yield event

    # ── 5b. Synthesis ────────────────────────────────────────────────────────
    final_response = ""
    if len(all_responses) > 1 or plan.response_strategy == "synthesis":
        yield synthesis_start_event()
        try:
            result = await loop.run_in_executor(
                _executor, synthesize, message, plan, context_str, all_responses
            )
            final_response = result
            yield synthesis_event(result)
        except Exception as exc:
            logger.warning("Synthesis failed: %s", exc)
            final_response = list(all_responses.values())[0]
            yield synthesis_event(final_response)
    else:
        final_response = list(all_responses.values())[0] if all_responses else ""

    # ── 6. Memory Persistence ─────────────────────────────────────────────────
    loop.run_in_executor(
        _executor,
        _store_memory,
        user_id,
        message,
        final_response,
        list(all_responses.keys()),
    )

    yield {
        **done_event(len(memories)),
        "agent_responses": all_responses,
        "validation_events": all_val_events,
        "retry_counts": all_retry_counts,
        "plan": {
            "intent": plan.intent,
            "complexity": plan.complexity,
            "response_strategy": plan.response_strategy,
            "sub_queries": [
                {"id": sq.id, "focus": sq.focus, "agents": sq.agents}
                for sq in plan.sub_queries
            ],
        },
        "synthesis": final_response,
    }


async def _execute_and_validate(
    loop,
    sq: SubQuery,
    context_str: str,
    memories_str: str,
    history_str: str,
) -> tuple[dict[str, str], list[dict], dict[str, int]]:
    val_events: list[dict] = []
    retry_counts: dict[str, int] = {}

    responses: dict[str, str] = await loop.run_in_executor(
        _executor, run_sub_query, sq, context_str, memories_str, history_str
    )

    needs_revision: dict[str, str] = {}
    for agent_key, text in responses.items():
        vr = await loop.run_in_executor(
            _executor, validate_response_sync, sq.rewritten_query, text, context_str
        )
        val_events.append(
            validation_event(
                agent_key, vr.passed, vr.overall_score, vr.scores, vr.critique
            )
        )
        if not vr.passed:
            needs_revision[agent_key] = vr.revised_query or sq.rewritten_query

    for attempt in range(MAX_RETRIES):
        if not needs_revision:
            break
        still_failing: dict[str, str] = {}
        for agent_key, revised_q in needs_revision.items():
            retry_sq = SubQuery(
                id=f"{sq.id}_retry{attempt + 1}",
                original_intent=sq.original_intent,
                rewritten_query=revised_q,
                agents=[agent_key],
                focus=sq.focus,
            )
            retry_resp = await loop.run_in_executor(
                _executor,
                run_sub_query,
                retry_sq,
                context_str,
                memories_str,
                history_str,
            )
            retry_text = retry_resp.get(agent_key, "")
            retry_counts[agent_key] = attempt + 1
            vr2 = await loop.run_in_executor(
                _executor,
                validate_response_sync,
                sq.rewritten_query,
                retry_text,
                context_str,
            )
            val_events.append(
                validation_event(
                    agent_key, vr2.passed, vr2.overall_score, vr2.scores, is_retry=True
                )
            )
            responses[agent_key] = retry_text
            if not vr2.passed and attempt < MAX_RETRIES - 1:
                still_failing[agent_key] = vr2.revised_query or revised_q
        needs_revision = still_failing

    return responses, val_events, retry_counts


def _store_memory(user_id: str, message: str, response: str, agents: list[str]):
    add_memory(
        user_id,
        f"User asked: {message}\nAgents: {', '.join(agents)}\nKey advice: {response[:600]}",
        metadata={"agents": agents},
    )


def _unique_agents(plan: OrchestratorPlan) -> list[str]:
    seen: dict[str, None] = {}
    for sq in plan.sub_queries:
        for key in sq.agents:
            seen[key] = None
    return list(seen)
