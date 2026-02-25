"""
Onboarding flow — 8 adaptive questions asked one at a time.
Returns the next question or signals completion.
"""

QUESTIONS = [
    {
        "id": "name",
        "question": "Welcome to ExecOS — your Cloud C-Suite. To get started, what's your name?",
        "field": "name",
        "skip_label": "Skip for now",
    },
    {
        "id": "role",
        "question": "Great, {name}! What best describes your current role?",
        "field": "role",
        "placeholder": "e.g. Founder, CEO, Product Manager, Solopreneur, Student...",
        "skip_label": "Skip for now",
    },
    {
        "id": "company",
        "question": "What's the name of your company or project?",
        "field": "company_name",
        "placeholder": "e.g. Acme Corp, my side project...",
        "skip_label": "Skip for now",
    },
    {
        "id": "stage",
        "question": "What stage is your company at right now?",
        "field": "company_stage",
        "options": [
            "Idea / Pre-revenue",
            "Early Stage (0–$500K ARR)",
            "Growth ($500K–$5M ARR)",
            "Scale-Up ($5M+ ARR)",
            "Corporate / Enterprise",
        ],
        "skip_label": "Skip for now",
    },
    {
        "id": "industry",
        "question": "Which industry are you in?",
        "field": "industry",
        "placeholder": "e.g. SaaS, Fintech, Healthcare, E-commerce, Consumer...",
        "skip_label": "Skip for now",
    },
    {
        "id": "team_size",
        "question": "How big is your team?",
        "field": "team_size",
        "options": [
            "Just me",
            "2–5 people",
            "6–20 people",
            "21–100 people",
            "100+ people",
        ],
        "skip_label": "Skip for now",
    },
    {
        "id": "challenges",
        "question": "What are your biggest challenges right now? (feel free to be specific)",
        "field": "current_challenges",
        "placeholder": "e.g. running out of runway, need to hire, struggling with growth...",
        "skip_label": "Skip for now",
    },
    {
        "id": "goals",
        "question": "And what's your primary goal for the next 90 days?",
        "field": "goals",
        "placeholder": "e.g. close a seed round, hit $10K MRR, launch v1, hire first engineer...",
        "skip_label": "Skip for now",
    },
]


def get_next_question(step: int, context: dict) -> dict | None:
    """Return the next question dict for this step, or None if onboarding is complete."""
    if step >= len(QUESTIONS):
        return None
    q = QUESTIONS[step].copy()
    # Interpolate name if available
    if "{name}" in q["question"] and context.get("name"):
        q["question"] = q["question"].format(name=context["name"])
    else:
        q["question"] = q["question"].replace("{name}, ", "").replace("{name}! ", "")
    return q


def get_completion_message(context: dict) -> str:
    name = context.get("name", "there")
    stage = context.get("company_stage", "")
    challenges = context.get("current_challenges", "")

    parts = [
        f"Welcome to the Boardroom, {name}. Your Cloud C-Suite is assembled and ready."
    ]

    if stage or challenges:
        parts.append(
            "Based on what you've shared, your CEO and CFO agents are already thinking about your priorities."
        )

    parts.append("Ask anything — or just describe what's on your mind.")
    return " ".join(parts)
