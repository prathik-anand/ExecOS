# ExecOS

> **Your Cloud C-Suite — 42 AI CXO agents, always on, always aligned.**

ExecOS is a Boardroom AI with 10+ Cloud CXO agents that collaborate to deliver executive-grade advice to founders, solopreneurs, and leaders.

## Monorepo Structure

```
execsOS/
├── backend/          # FastAPI + SQLite + Anthropic
└── frontend/         # React + Vite + Tailwind
```

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- An Anthropic API key

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) — the onboarding flow starts automatically.

## Phase 1 CXO Agents (Hackathon MVP)

| Agent | Role |
|-------|------|
| CEO   | Vision, strategy, prioritization |
| CFO   | Financials, runway, unit economics |
| CTO   | Tech stack, architecture, engineering |
| CPO   | Product, roadmap, PMF |
| CMO   | Marketing, GTM, brand |
| CSO   | Sales, pipeline, revenue |
| CHRO  | Hiring, culture, org design |
| CCO   | Customer success, retention |
| CLO   | Legal, compliance, contracts |
| COO   | Operations, process, execution |

## Architecture

- **Boardroom Orchestrator**: Classifies intent → routes to 1–N agents → synthesizes response
- **SSE Streaming**: Real-time agent reasoning streams to the UI
- **Session Management**: No auth — UUID stored in `localStorage`, sent as `X-Session-ID` header
- **Onboarding**: 8 adaptive conversational questions before first Boardroom access
