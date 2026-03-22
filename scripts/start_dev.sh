#!/bin/bash
# =============================================================================
# Avantika Language AI — One-command local dev startup
# Usage: bash scripts/start_dev.sh
# =============================================================================

set -e

echo "Starting Avantika Local Dev Stack..."

# Check .env exists
if [ ! -f .env ]; then
  echo "ERROR: .env file not found. Copy .env.example to .env and fill in values."
  exit 1
fi

# Start infrastructure (postgres + redis)
echo "Starting infrastructure..."
docker-compose up -d postgres redis
sleep 3

# Run DB migrations + seed (backend must be able to reach postgres)
echo "Running migrations..."
cd backend
python -m alembic upgrade head 2>/dev/null || echo "Alembic not initialized yet — run scripts/alembic_setup.py first"
cd ..

echo "Seeding database..."
python scripts/seed_db.py 2>/dev/null || echo "Seed already done or failed — continuing"

# Start agent service in background
echo "Starting agent service..."
cd agents && python main.py &
AGENT_PID=$!
cd ..
sleep 2

# Start backend in background
echo "Starting backend..."
cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd ..
sleep 2

# Start frontend
echo "Starting frontend..."
cd frontend && npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "============================================"
echo "Avantika is running!"
echo "  Frontend:      http://localhost:3000"
echo "  Backend API:   http://localhost:8000/docs"
echo "  Agent Service: http://localhost:8001/docs"
echo "============================================"
echo "Press Ctrl+C to stop all services"

# Wait and cleanup on exit
trap "kill $AGENT_PID $BACKEND_PID $FRONTEND_PID 2>/dev/null; docker-compose down; exit" INT TERM
wait
