#!/usr/bin/env bash
# start.sh — start backend + frontend dev servers
set -e

echo "🏛️ Starting ExecOS..."

# Backend
cd backend
if [ ! -f .env ]; then
  echo "⚠️  No .env found! Copying from .env.example..."
  cp .env.example .env
  echo "👉 Edit backend/.env and add your ANTHROPIC_API_KEY, then re-run."
  exit 1
fi

if [ ! -d venv ]; then
  echo "📦 Creating Python virtualenv..."
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt -q
else
  source venv/bin/activate
fi

echo "🚀 Starting backend on http://localhost:8000"
uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!

cd ../frontend
echo "🎨 Starting frontend on http://localhost:5173"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ ExecOS running!"
echo "   Frontend: http://localhost:5173"
echo "   Backend:  http://localhost:8000"
echo "   API docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers."

trap "kill $BACKEND_PID $FRONTEND_PID" SIGINT SIGTERM
wait
