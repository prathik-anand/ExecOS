#!/bin/bash

# Coloring
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PORT=8000
FRONTEND_PORT=5173

# Parse arguments
BACKEND_ONLY=false
for arg in "$@"; do
    [ "$arg" == "--backend-only" ] && BACKEND_ONLY=true
done

# ── Kill ports ────────────────────────────────────────────────────────────────
echo -e "${BLUE}[INFO] Cleaning up port $BACKEND_PORT (Backend)...${NC}"
kill -9 $(lsof -t -i:$BACKEND_PORT) 2>/dev/null || true
pkill -f "uvicorn main:app" 2>/dev/null || true

if [ "$BACKEND_ONLY" = false ]; then
    echo -e "${BLUE}[INFO] Cleaning up port $FRONTEND_PORT (Frontend)...${NC}"
    kill -9 $(lsof -t -i:$FRONTEND_PORT) 2>/dev/null || true
fi

# ── Frontend (background) ─────────────────────────────────────────────────────
if [ "$BACKEND_ONLY" = false ]; then
    echo -e "${BLUE}[INFO] Starting Frontend (background)...${NC}"
    cd "$ROOT_DIR/frontend"
    [ ! -d node_modules ] && npm install -q
    npm run dev > /dev/null 2>&1 &
    FRONTEND_PID=$!
    echo -e "${GREEN}[SUCCESS] Frontend running at http://localhost:$FRONTEND_PORT${NC}"
    cd "$ROOT_DIR"
fi

# ── Backend (foreground) ──────────────────────────────────────────────────────
echo -e "${BLUE}[INFO] Starting Backend...${NC}"
cd "$ROOT_DIR/backend"

uv sync -q

if [ -f ".env" ]; then
    echo -e "${BLUE}[INFO] Loading .env...${NC}"
    set -a; source .env; set +a
fi

export PYTHONPATH=$(pwd)

echo -e "${BLUE}[INFO] Running alembic upgrade head...${NC}"
uv run alembic upgrade head

# Cleanup on exit
cleanup() {
    echo -e "\n${BLUE}[INFO] Stopping services...${NC}"
    [ "$BACKEND_ONLY" = false ] && kill $FRONTEND_PID 2>/dev/null || true
}
trap cleanup EXIT

echo -e "${GREEN}[SUCCESS] Backend running at http://localhost:$BACKEND_PORT${NC}"
echo -e "${GREEN}          API docs → http://localhost:$BACKEND_PORT/docs${NC}"
echo ""

uv run uvicorn main:app --host 0.0.0.0 --port $BACKEND_PORT --reload
