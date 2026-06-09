#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "[PaperCutter] Starting..."
echo ""

# Backend - nohup + disown, truly detached
echo "[1/2] Starting backend http://localhost:7652 ..."
cd backend
nohup python server.py > /dev/null 2>&1 &
BACKEND_PID=$!
cd "$ROOT"
echo $BACKEND_PID > .backend.pid
echo "[OK] Backend started (PID: $BACKEND_PID)"

# Frontend - nohup + disown, truly detached
echo "[2/2] Starting frontend http://localhost:5173 ..."
cd frontend
nohup npm run dev > /dev/null 2>&1 &
FRONTEND_PID=$!
cd "$ROOT"
echo $FRONTEND_PID > .frontend.pid
echo "[OK] Frontend started (PID: $FRONTEND_PID)"

echo ""
echo "[PaperCutter] Started"
echo "  Backend:  http://localhost:7652"
echo "  Frontend: http://localhost:5173"
echo "  Docs:     http://localhost:7652/docs"
echo ""
echo "  Run stop.sh to stop services"
echo ""
