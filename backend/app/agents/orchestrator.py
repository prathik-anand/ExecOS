"""
Gold-standard Boardroom Orchestrator.

Replaces naive keyword routing with a single structured LLM call that does:
  1. Intent Classification  — decision / analysis / planning / brainstorm / check-in
  2. Complexity Assessment  — simple / compound / complex
  3. Query Decomposition    — atomic sub-queries from multi-part questions
  4. Query Rewriting        — enrich each sub-query with user profile + memories + history
  5. Agent Routing          — map each sub-query to the best CXO domain experts

Falls back to keyword matching if the LLM call fails.
"""

import json
import logging
import os
import re
from dataclasses import dataclass

from app.agents.prompts import AGENTS, AGENT_KEYS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Domain expertise map — which CXOs own which business domains
# Used as context injected into the orchestrator prompt so the LLM can route
# ---------------------------------------------------------------------------
DOMAIN_MAP: dict[str, list[str]] = {
    "CEO": [
        "vision",
        "strategy",
        "direction",
        "leadership",
        "mission",
        "pivot",
        "OKRs",
        "company trajectory",
        "board",
        "investors",
        "co-founder",
        "culture",
        "priorities",
    ],
    "CFO": [
        "fundraising",
        "runway",
        "burn rate",
        "revenue",
        "unit economics",
        "valuation",
        "financial model",
        "budget",
        "cash flow",
        "equity",
        "dilution",
        "P&L",
        "EBITDA",
        "pricing strategy",
        "seed round",
        "Series A",
        "venture capital",
    ],
    "CTO": [
        "technology",
        "tech stack",
        "architecture",
        "infrastructure",
        "engineering team",
        "technical debt",
        "APIs",
        "scalability",
        "security",
        "platform",
        "DevOps",
        "cloud",
    ],
    "CPO": [
        "product",
        "roadmap",
        "features",
        "user research",
        "product-market fit",
        "MVP",
        "UX",
        "customer journey",
        "PRD",
        "prioritization",
        "product strategy",
        "SaaS pricing",
        "freemium",
        "tiers",
    ],
    "CMO": [
        "marketing",
        "brand",
        "growth",
        "acquisition",
        "demand gen",
        "content",
        "SEO",
        "social media",
        "campaigns",
        "positioning",
        "GTM",
        "messaging",
        "PR",
    ],
    "CSO": [
        "sales",
        "revenue growth",
        "pipeline",
        "quota",
        "B2B sales",
        "enterprise",
        "outbound",
        "partnerships",
        "channel",
        "CRM",
        "ARR",
        "MRR",
        "churn",
        "expansion",
    ],
    "CPeO": [
        "hiring",
        "team building",
        "culture",
        "performance",
        "OKRs",
        "compensation",
        "equity",
        "remote work",
        "onboarding",
        "talent",
        "HR",
        "firing",
        "org design",
    ],
    "CCO": [
        "customer success",
        "retention",
        "NPS",
        "support",
        "onboarding",
        "churn",
        "customer feedback",
        "CSAT",
        "SLA",
        "account management",
    ],
    "COO": [
        "operations",
        "processes",
        "efficiency",
        "scaling",
        "supply chain",
        "execution",
        "systems",
        "automation",
        "SOPs",
        "workflow",
        "headcount planning",
    ],
    "CLO": [
        "legal",
        "contracts",
        "compliance",
        "IP",
        "patents",
        "GDPR",
        "terms of service",
        "equity agreements",
        "cap table",
        "incorporation",
        "liability",
        "NDAs",
    ],
    "CSci": [
        "research",
        "data science",
        "ML",
        "AI",
        "experimentation",
        "innovation",
        "R&D",
        "algorithms",
        "models",
        "benchmarks",
        "academic",
    ],
    "CIO": [
        "data infrastructure",
        "databases",
        "ERP",
        "enterprise systems",
        "IT",
        "integrations",
        "business intelligence",
        "analytics stack",
    ],
    "CAIO": [
        "AI strategy",
        "AI adoption",
        "LLMs",
        "generative AI",
        "AI ethics",
        "AI product",
        "automation with AI",
        "AI roadmap",
    ],
    "CArch": [
        "system design",
        "technical architecture",
        "microservices",
        "monolith",
        "event-driven",
        "API design",
        "distributed systems",
        "design patterns",
    ],
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass
class SubQuery:
    id: str
    original_intent: str  # what this sub-query is trying to answer
    rewritten_query: str  # context-enriched version sent to agents
    agents: list[str]  # CXO keys e.g. ["CFO", "CEO"]
    focus: str  # one-line summary for routing display


@dataclass
class OrchestratorPlan:
    intent: str  # decision | analysis | planning | brainstorm | check-in
    complexity: str  # simple | compound | complex
    sub_queries: list[SubQuery]  # one or more atomic sub-queries
    response_strategy: str  # direct | multi-perspective | synthesis
    reasoning: str  # brief explanation of why this routing was chosen


# ---------------------------------------------------------------------------
# Orchestrator prompt
# ---------------------------------------------------------------------------
_ORCHESTRATOR_SYSTEM = """You are the ExecOS Boardroom Orchestrator — an elite executive advisor router.

Your job is to analyse incoming user queries and produce a structured routing plan.

You have 14 CXO specialists available:
{agent_list}

Each agent's domain expertise:
{domain_list}

Your analysis must be returned as valid JSON with this exact schema:
{{
  "intent": "<decision|analysis|planning|brainstorm|check-in>",
  "complexity": "<simple|compound|complex>",
  "reasoning": "<1-2 sentences explaining your routing logic>",
  "response_strategy": "<direct|multi-perspective|synthesis>",
  "sub_queries": [
    {{
      "id": "sq1",
      "original_intent": "<what this sub-query answers>",
      "rewritten_query": "<context-enriched full question to send to agents>",
      "focus": "<10-word summary>",
      "agents": ["<AGENT_KEY>", ...]
    }}
  ]
}}

Rules:
- ALWAYS decompose compound/complex queries into multiple sub_queries
- Sub-queries should be focused and atomic — one concern per sub-query
- rewritten_query MUST embed user profile, relevant memory, and conversation context so the agent has everything it needs
- Choose agents based on domain expertise — route to 1-2 agents maximum per sub-query
- For simple queries: 1 sub-query, 1-2 agents, response_strategy = "direct"  
- For compound queries: 2-3 sub-queries, response_strategy = "multi-perspective"
- For complex queries: 3+ sub-queries covering strategic angles, response_strategy = "synthesis"
- @AGENT explicit mentions override your routing for that part
- Always include CEO for purely strategic/directional questions
- Return ONLY valid JSON, no markdown, no explanation outside the JSON"""


_ORCHESTRATOR_USER = """USER PROFILE:
{user_context}

RELEVANT MEMORIES (past decisions & context):
{memories}

RECENT CONVERSATION:
{history}

USER QUERY:
{message}

Available agents: {agent_keys}

Analyse the query and return your routing plan as JSON."""


# ---------------------------------------------------------------------------
# Keyword fallback (used if LLM call fails)
# ---------------------------------------------------------------------------
def _keyword_fallback(message: str) -> OrchestratorPlan:
    msg_lower = message.lower()
    upper_msg = message.upper()

    # Honour explicit @AGENT mentions
    explicit = [k for k in AGENT_KEYS if f"@{k}" in upper_msg]
    if explicit:
        selected = explicit[:3]
    else:
        matches = []
        for key, agent in AGENTS.items():
            if any(kw.lower() in msg_lower for kw in agent.get("trigger_keywords", [])):
                matches.append(key)
            if len(matches) >= 3:
                break
        selected = matches or ["CEO"]

    return OrchestratorPlan(
        intent="analysis",
        complexity="simple",
        response_strategy="direct" if len(selected) == 1 else "multi-perspective",
        reasoning="Keyword-based routing (orchestrator LLM unavailable)",
        sub_queries=[
            SubQuery(
                id="sq1",
                original_intent=message,
                rewritten_query=message,
                agents=selected,
                focus="General analysis",
            )
        ],
    )


# ---------------------------------------------------------------------------
# Main orchestrator call (synchronous — run in executor)
# ---------------------------------------------------------------------------
def orchestrate_sync(
    message: str,
    user_context: str,
    memories: str,
    history: str,
) -> OrchestratorPlan:
    """
    Single structured LLM call → returns OrchestratorPlan.
    Runs synchronously; call via loop.run_in_executor in async context.
    """
    try:
        import google.generativeai as genai  # type: ignore

        api_key = os.getenv("GOOGLE_API_KEY")
        model_name = os.getenv("LLM_MODEL", "gemini-2.0-flash").replace("gemini/", "")

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)

        agent_list = "\n".join(
            f"  {k}: {AGENTS[k]['name']} ({AGENTS[k]['emoji']})" for k in AGENT_KEYS
        )
        domain_list = "\n".join(
            f"  {k}: {', '.join(domains[:6])}"
            for k, domains in DOMAIN_MAP.items()
            if k in AGENTS
        )

        system_prompt = _ORCHESTRATOR_SYSTEM.format(
            agent_list=agent_list,
            domain_list=domain_list,
        )
        user_prompt = _ORCHESTRATOR_USER.format(
            user_context=user_context,
            memories=memories,
            history=history,
            message=message,
            agent_keys=", ".join(AGENT_KEYS),
        )

        response = model.generate_content(
            f"{system_prompt}\n\n{user_prompt}",
            generation_config=genai.GenerationConfig(
                temperature=0.1,  # low temp → deterministic routing
                max_output_tokens=1024,
            ),
        )

        raw = response.text.strip()
        # Strip markdown fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        data = json.loads(raw)
        return _parse_plan(data, message)

    except Exception as exc:
        logger.warning("Orchestrator LLM call failed, using keyword fallback: %s", exc)
        return _keyword_fallback(message)


def _parse_plan(data: dict, original_message: str) -> OrchestratorPlan:
    """Parse raw JSON dict into OrchestratorPlan, validating agent keys."""
    valid_keys = set(AGENT_KEYS)

    sub_queries: list[SubQuery] = []
    for sq in data.get("sub_queries", []):
        raw_agents = [a.upper() for a in sq.get("agents", [])]
        agents = [a for a in raw_agents if a in valid_keys] or ["CEO"]
        sub_queries.append(
            SubQuery(
                id=sq.get("id", f"sq{len(sub_queries) + 1}"),
                original_intent=sq.get("original_intent", original_message),
                rewritten_query=sq.get("rewritten_query", original_message),
                agents=agents,
                focus=sq.get("focus", ""),
            )
        )

    if not sub_queries:
        sub_queries = [
            SubQuery(
                id="sq1",
                original_intent=original_message,
                rewritten_query=original_message,
                agents=["CEO"],
                focus="General analysis",
            )
        ]

    return OrchestratorPlan(
        intent=data.get("intent", "analysis"),
        complexity=data.get("complexity", "simple"),
        response_strategy=data.get("response_strategy", "direct"),
        reasoning=data.get("reasoning", ""),
        sub_queries=sub_queries,
    )
