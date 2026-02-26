"""
Agent Pipeline — async coordinator.

Single responsibility: chain the five stages of a Boardroom interaction
and yield SSE events. Contains no prompt logic, no model calls, and no
HTTP concerns. Each stage delegates to its own module.

Stages:
  1. Memory retrieval     (memory.service)
  2. Orchestration        (orchestrator)
  3. Parallel execution   (executor)    ← one coroutine per sub-query
  4. Validation + retry   (validator)
  5. Synthesis            (synthesizer)
  6. Memory persistence   (memory.service)

All database persistence is handled by the caller (chat.py) via the
yielded events — this module never touches the DB directly.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import AsyncGenerator

from app.agents.orchestrator import orchestrate_sync, OrchestratorPlan, SubQuery
from app.agents.executor import run_sub_query
from app.agents.validator import validate_response_sync, MAX_RETRIES
from app.agents.synthesizer import synthesize
from app.agents.events import (
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
from app.agents.utils import build_user_context, build_history
from app.memory.service import search_memory, add_memory

logger = logging.getLogger(__name__)

# Shared thread pool — all sync LLM calls run here
_executor = ThreadPoolExecutor(max_workers=8)


async def run_pipeline(
    message: str,
    user,
    conversation_history: list,
) -> AsyncGenerator[dict, None]:
    """
    Full Boardroom pipeline. Yields SSE event dicts for the caller to stream.
    The caller (chat.py) is responsible for DB persistence of these events.
    """
    loop = asyncio.get_event_loop()
    user_id = str(user.id) if hasattr(user, "id") else str(user)
    context_str = build_user_context(user)
    history_str = build_history(conversation_history)

    # ── Stage 1: Memory Retrieval ────────────────────────────────────────────
    memories: list[str] = await loop.run_in_executor(
        _executor, search_memory, user_id, message
    )
    memories_str = (
        "\n".join(f"- {m}" for m in memories)
        if memories
        else "No relevant memories yet."
    )

    # ── Stage 2: Orchestration ───────────────────────────────────────────────
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

    # ── Stage 3 + 4: Parallel Execution + Validation ─────────────────────────
    try:
        sq_results = await asyncio.gather(
            *[
                _execute_and_validate(loop, sq, context_str, memories_str, history_str)
                for sq in plan.sub_queries
            ],
            return_exceptions=False,
        )
    except Exception as exc:
        logger.error("Pipeline execution error: %s", exc)
        yield error_event(str(exc))
        yield done_event()
        return

    # Flatten results; yield validation events first, then build response map
    all_responses: dict[str, str] = {}
    all_validation_events: list[dict] = []
    all_retry_counts: dict[str, int] = {}

    for sub_resp, val_events, retries in sq_results:
        all_validation_events.extend(val_events)
        for agent_key, text in sub_resp.items():
            if agent_key not in all_responses:
                all_responses[agent_key] = text
            else:
                all_responses[agent_key] += f"\n\n---\n\n{text}"
            all_retry_counts[agent_key] = retries.get(agent_key, 0)

    for val_event in all_validation_events:
        yield val_event

    # ── Stage 5a: Individual Agent Responses ────────────────────────────────
    for agent_key, response_text in all_responses.items():
        event = agent_response_event(agent_key, response_text)
        if event:
            yield event

    # ── Stage 5b: Synthesis ──────────────────────────────────────────────────
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

    # ── Stage 6: Memory Persistence ──────────────────────────────────────────
    asyncio.create_task(
        loop.run_in_executor(
            _executor,
            _store_memory,
            user_id,
            message,
            final_response,
            list(all_responses.keys()),
        )
    )

    # Yield done with pipeline metadata for the caller to persist
    yield {
        **done_event(len(memories)),
        "agent_responses": all_responses,
        "validation_events": all_validation_events,
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


# ---------------------------------------------------------------------------
# Stage helpers
# ---------------------------------------------------------------------------


async def _execute_and_validate(
    loop,
    sq: SubQuery,
    context_str: str,
    memories_str: str,
    history_str: str,
) -> tuple[dict[str, str], list[dict], dict[str, int]]:
    """
    Execute one sub-query, validate each response, retry failing agents once.
    Returns (final_responses, validation_events, retry_counts_per_agent).
    """
    val_events: list[dict] = []
    retry_counts: dict[str, int] = {}

    # First attempt
    responses: dict[str, str] = await loop.run_in_executor(
        _executor, run_sub_query, sq, context_str, memories_str, history_str
    )

    # Validate
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

    # Retry loop (max MAX_RETRIES = 1 by default)
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
            # Accept retry result regardless (avoids infinite loop on final attempt)
            responses[agent_key] = retry_text
            if not vr2.passed and attempt < MAX_RETRIES - 1:
                still_failing[agent_key] = vr2.revised_query or revised_q

        needs_revision = still_failing

    return responses, val_events, retry_counts


def _store_memory(user_id: str, message: str, response: str, agents: list[str]):
    content = (
        f"User asked: {message}\n"
        f"Agents: {', '.join(agents)}\n"
        f"Key advice: {response[:600]}"
    )
    add_memory(user_id, content, metadata={"agents": agents})


def _unique_agents(plan: OrchestratorPlan) -> list[str]:
    """Return all agent keys referenced in the plan, deduplicated, order-preserved."""
    seen: dict[str, None] = {}
    for sq in plan.sub_queries:
        for key in sq.agents:
            seen[key] = None
    return list(seen)
