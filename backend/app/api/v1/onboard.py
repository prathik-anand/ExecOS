"""
Onboarding API — AI-driven conversational Q&A to build user context.

Flow:
  POST /api/v1/onboard/next   { answers: [{"q": "...", "a": "...", "field": "..."}] }
  → { question, field, options?, step, is_last }  OR  { complete: true }

  POST /api/v1/onboard/complete   { answers: [...] }
  → saves Q&A to user.onboarding_data and extracts flat fields
"""

import asyncio
import json
import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repository.user_repository import UserRepository
from app.utils.database import get_db
from app.utils.security import get_current_user

router = APIRouter(prefix="/onboard", tags=["onboarding"])

# Questions we want to cover — the AI generates the actual phrasing dynamically
REQUIRED_FIELDS = [
    "name",
    "role",
    "company_name",
    "company_stage",
    "industry",
    "team_size",
    "goals",
    "challenges",
]
MIN_QUESTIONS = 6
MAX_QUESTIONS = 10


class QAPair(BaseModel):
    q: str
    a: str
    field: str


class NextQuestionRequest(BaseModel):
    answers: list[QAPair] = []


class CompleteRequest(BaseModel):
    answers: list[QAPair]


def _call_llm(prompt: str) -> str:
    """Call LLM via litellm (bundled with crewai)."""
    import litellm

    response = litellm.completion(
        model=os.getenv("LLM_MODEL", "gemini/gemini-2.0-flash"),
        api_key=os.getenv("GOOGLE_API_KEY"),
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.4,
    )
    return response.choices[0].message.content or "{}"


def _get_next_question(answers: list[QAPair]) -> dict | None:
    """
    Use AI to generate the next onboarding question based on answers so far.
    Returns None when enough data has been collected.
    """
    covered = {a.field for a in answers}
    remaining = [f for f in REQUIRED_FIELDS if f not in covered]

    # Enough data collected
    if len(answers) >= MAX_QUESTIONS or (len(answers) >= MIN_QUESTIONS and not remaining):
        return None

    # Build context of what we know
    context_lines = "\n".join(f"- {a.field}: {a.a}" for a in answers) if answers else "(none yet)"
    remaining_fields = ", ".join(remaining) if remaining else "any deeper follow-up"

    prompt = f"""You are onboarding a new user to ExecOS — an AI-powered executive team platform for startup founders and operators.

What we know so far:
{context_lines}

Still need to learn (if not already covered): {remaining_fields}

Generate the NEXT single onboarding question. Be conversational, warm, and specific based on their previous answers.

Rules:
- Ask only ONE question
- If you know their name, use it naturally
- If they said they're at "Early Stage", ask something specific to that (e.g. ARR, fundraising)
- Adapt to what they've shared — don't ask redundant things
- For company_stage and team_size, provide multiple-choice options
- Keep it short and human, not clinical

Return JSON with exactly these keys:
{{
  "question": "...",
  "field": "name|role|company_name|company_stage|industry|team_size|goals|challenges|other",
  "options": ["option1", "option2"] // only if field is company_stage or team_size, otherwise omit
}}"""

    try:
        raw = _call_llm(prompt)
        data = json.loads(raw)
        # Validate required keys
        if "question" not in data or "field" not in data:
            raise ValueError("Missing keys")
        return data
    except Exception:
        # Fallback to next uncovered required field
        if remaining:
            fallbacks = {
                "name": {"question": "First, what's your name?", "field": "name"},
                "role": {"question": "What's your role or title?", "field": "role"},
                "company_name": {
                    "question": "What's your company or project called?",
                    "field": "company_name",
                },
                "company_stage": {
                    "question": "What stage is your company at?",
                    "field": "company_stage",
                    "options": [
                        "Pre-idea",
                        "Idea / Concept",
                        "MVP / Building",
                        "Early Traction",
                        "PMF Found",
                        "Scaling",
                        "Growth",
                    ],
                },
                "industry": {"question": "Which industry are you in?", "field": "industry"},
                "team_size": {
                    "question": "How big is your team right now?",
                    "field": "team_size",
                    "options": ["Solo founder", "2–5", "6–15", "16–50", "51–200", "200+"],
                },
                "goals": {
                    "question": "What's your primary goal for the next 90 days?",
                    "field": "goals",
                },
                "challenges": {
                    "question": "What's your biggest challenge right now?",
                    "field": "challenges",
                },
            }
            return fallbacks.get(
                remaining[0], {"question": "Anything else you'd like to share?", "field": "other"}
            )
        return None


def _extract_profile(answers: list[QAPair]) -> dict:
    """Use AI to extract structured profile fields from Q&A."""
    qa_text = "\n".join(f"Q: {a.q}\nA: {a.a}" for a in answers)
    prompt = f"""From this onboarding Q&A, extract structured profile data.

{qa_text}

Return JSON with these optional keys (only include if clearly stated):
{{
  "name": "...",
  "role": "...",
  "company_name": "...",
  "company_stage": "...",
  "industry": "...",
  "team_size": "...",
  "current_challenges": "...",
  "goals": "..."
}}

Use null for unknown fields. Keep values concise."""

    try:
        raw = _call_llm(prompt)
        return json.loads(raw)
    except Exception:
        # Fallback: direct field mapping from answers
        field_map = {a.field: a.a for a in answers if a.a and a.a.lower() != "skip"}
        return {
            "name": field_map.get("name"),
            "role": field_map.get("role"),
            "company_name": field_map.get("company_name"),
            "company_stage": field_map.get("company_stage"),
            "industry": field_map.get("industry"),
            "team_size": field_map.get("team_size"),
            "current_challenges": field_map.get("challenges"),
            "goals": field_map.get("goals"),
        }


@router.post("/next")
async def next_question(
    body: NextQuestionRequest,
    current_user: User = Depends(get_current_user),
):
    """Return the next onboarding question, or signal completion."""
    question = await asyncio.to_thread(_get_next_question, body.answers)
    if question is None:
        return {"complete": True, "step": len(body.answers), "total": len(body.answers)}

    return {
        "complete": False,
        "question": question.get("question"),
        "field": question.get("field"),
        "options": question.get("options"),
        "step": len(body.answers),
        "total": MAX_QUESTIONS,
    }


@router.post("/complete")
async def complete_onboarding(
    body: CompleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save Q&A to onboarding_data, extract flat profile fields, mark onboarding done."""
    if not body.answers:
        raise HTTPException(status_code=400, detail="No answers provided")

    extracted = await asyncio.to_thread(_extract_profile, body.answers)

    repo = UserRepository(db)
    update_fields: dict = {
        "onboarding_data": {"qa": [a.model_dump() for a in body.answers]},
        "onboarding_complete": True,
    }
    # Apply extracted flat fields (skip None values)
    for key in (
        "name",
        "role",
        "company_name",
        "company_stage",
        "industry",
        "team_size",
        "current_challenges",
        "goals",
    ):
        val = extracted.get(key)
        if val and val != "null":
            update_fields[key] = val

    await repo.update(current_user, **update_fields)

    return {
        "success": True,
        "message": f"Welcome to the Boardroom{', ' + extracted.get('name') if extracted.get('name') else ''}! Your Cloud C-Suite is ready.",
    }
