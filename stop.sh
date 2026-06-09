#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "[PaperCutter] Stopping services..."
echo ""

read -p "Stop background services? (y/N): " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "[OK] Cancelled"
    exit 0
fi

# Kill backend by PID
if [[ -f .backend.pid ]]; then
    BACKEND_PID=$(cat .backend.pid)
    if kill "$BACKEND_PID" 2>/dev/null; then
        echo "[OK] Backend stopped (PID: $BACKEND_PID)"
    else
        echo "[..] Backend not running"
    fi
    rm -f .backend.pid
else
    echo "[..] No backend PID file"
fi

# Kill frontend by PID
if [[ -f .frontend.pid ]]; then
    FRONTEND_PID=$(cat .frontend.pid)
    # Kill child processes too
    pkill -P "$FRONTEND_PID" 2>/dev/null || true
    if kill "$FRONTEND_PID" 2>/dev/null; then
        echo "[OK] Frontend stopped (PID: $FRONTEND_PID)"
    else
        echo "[..] Frontend not running"
    fi
    rm -f .frontend.pid
else
    echo "[..] No frontend PID file"
fi

echo ""
echo "[PaperCutter] All services stopped"
