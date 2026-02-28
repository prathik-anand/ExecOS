"""
Response Validation Layer — Self-Critique & Revise.

After each sub-query's agents respond, a Validator LLM evaluates the response on
4 dimensions:
  1. Relevance    — Did it actually answer the sub-query?
  2. Specificity  — Are recommendations concrete (not generic advice)?
  3. Context Use  — Did the agent use the user's profile / memories?
  4. Actionability — Are next steps clear, prioritized, and ownable?

If the overall score is below threshold, the validator emits:
  - A structured critique describing what is weak
  - A "revised query" — the original rewritten_query + critic feedback injected

boardroom.py then re-runs just that sub-query once with the revised prompt.
Max 1 retry per sub-query to avoid infinite loops.

SSE: yields a "validation" event so the frontend can show a "🔍 Reviewing…" badge.
"""

import json
import logging
import os
import re

logger = logging.getLogger(__name__)

# Minimum acceptable score (0-10) to pass without revision
PASS_THRESHOLD = 6.5
MAX_RETRIES = 1


# ---------------------------------------------------------------------------
# Validation result
# ---------------------------------------------------------------------------
class ValidationResult:
    def __init__(
        self,
        passed: bool,
        overall_score: float,
        scores: dict[str, float],
        critique: str,
        revised_query: str,
        reasoning: str,
    ):
        self.passed = passed
        self.overall_score = overall_score
        self.scores = scores  # {relevance, specificity, context_use, actionability}
        self.critique = critique  # human-readable critique
        self.revised_query = revised_query  # enriched query for retry
        self.reasoning = reasoning  # validator's reasoning


# ---------------------------------------------------------------------------
# Validator prompt
# ---------------------------------------------------------------------------
_VALIDATOR_SYSTEM = """You are the ExecOS Quality Validator — a rigorous executive advisor who reviews AI-generated responses.

Your job is to evaluate whether a CXO agent's response actually serves the user well.

Score each dimension 0-10:
- relevance: Does the response directly answer the specific query? (0=completely off-topic, 10=perfectly on-point)
- specificity: Are recommendations concrete and specific vs generic advice? (0=pure platitudes, 10=highly specific)
- context_use: Does the agent use the user's actual profile, stage, industry, goals? (0=ignored context, 10=deeply personalized)
- actionability: Are next steps clear, prioritized, realistic, and ownable? (0=vague, 10=crystal clear)

Return ONLY valid JSON:
{
  "scores": {
    "relevance": <0-10>,
    "specificity": <0-10>,
    "context_use": <0-10>,
    "actionability": <0-10>
  },
  "overall_score": <0-10 weighted average>,
  "passed": <true if overall_score >= 6.5>,
  "critique": "<2-3 sentences on what is weak or missing>",
  "revised_query": "<if not passed: original query + specific instructions to fix the weaknesses. If passed: empty string>",
  "reasoning": "<1 sentence on why it passed or failed>"
}"""

_VALIDATOR_USER = """ORIGINAL SUB-QUERY:
{sub_query}

USER CONTEXT:
{user_context}

AGENT RESPONSE TO EVALUATE:
{agent_response}

Evaluate this response strictly. Users deserve highly personalized, actionable advice — not generic startup wisdom."""


# ---------------------------------------------------------------------------
# Main validator call (synchronous — run in executor)
# ---------------------------------------------------------------------------
def validate_response_sync(
    sub_query: str,
    agent_response: str,
    user_context: str,
) -> ValidationResult:
    """
    Evaluate agent response quality. Returns ValidationResult.
    Falls back to pass=True on LLM error (fail-open to avoid blocking the user).
    """
    try:
        import google.generativeai as genai  # type: ignore

        api_key = os.getenv("GOOGLE_API_KEY")
        model_name = os.getenv("LLM_MODEL", "gemini-2.0-flash").replace("gemini/", "")

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)

        user_prompt = _VALIDATOR_USER.format(
            sub_query=sub_query,
            user_context=user_context,
            agent_response=agent_response[:2000],  # cap to save tokens
        )

        response = model.generate_content(
            f"{_VALIDATOR_SYSTEM}\n\n{user_prompt}",
            generation_config=genai.GenerationConfig(
                temperature=0.05,  # very deterministic scoring
                max_output_tokens=512,
            ),
        )

        raw = response.text.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        data = json.loads(raw)
        scores = data.get("scores", {})
        overall = float(data.get("overall_score", 5.0))
        passed = bool(data.get("passed", overall >= PASS_THRESHOLD))

        return ValidationResult(
            passed=passed,
            overall_score=overall,
            scores=scores,
            critique=data.get("critique", ""),
            revised_query=data.get("revised_query", ""),
            reasoning=data.get("reasoning", ""),
        )

    except Exception as exc:
        logger.warning("Validator LLM call failed, defaulting to pass: %s", exc)
        # Fail-open: don't block the response if validator errors
        return ValidationResult(
            passed=True,
            overall_score=7.0,
            scores={},
            critique="",
            revised_query="",
            reasoning="Validation skipped (LLM unavailable)",
        )
