#!/usr/bin/env bash
# ──────────────────────────────────────────────
#  PaperCutter — Linux/macOS 一键启动脚本
#  同时启动后端 (FastAPI) + 前端 (Vite dev server)
#  用法: chmod +x start.sh && ./start.sh
# ──────────────────────────────────────────────
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

GREEN='\033[92m'
YELLOW='\033[93m'
CYAN='\033[96m'
RED='\033[91m'
RESET='\033[0m'

echo -e ""
echo -e "${CYAN}╔══════════════════════════════════════╗${RESET}"
echo -e "${CYAN}║     PaperCutter — 正在启动...       ║${RESET}"
echo -e "${CYAN}╚══════════════════════════════════════╝${RESET}"
echo -e ""

# ── 检查后端依赖 ──
echo -e "${GREEN}[1/4]${RESET} 检查后端依赖..."
if ! python -c "import fastapi" 2>/dev/null; then
    echo -e "${YELLOW}[!] 安装后端依赖...${RESET}"
    pip install -r backend/requirements.txt
    echo -e "${GREEN}[✓] 后端依赖安装完成${RESET}"
else
    echo -e "${GREEN}[✓] 后端依赖已就绪${RESET}"
fi

# ── 检查前端依赖 ──
echo -e "${GREEN}[2/4]${RESET} 检查前端依赖..."
if [[ ! -d "frontend/node_modules" ]]; then
    echo -e "${YELLOW}[!] 安装前端依赖...${RESET}"
    cd frontend && npm install && cd "$ROOT"
    echo -e "${GREEN}[✓] 前端依赖安装完成${RESET}"
else
    echo -e "${GREEN}[✓] 前端依赖已就绪${RESET}"
fi

# ── 清理函数 ──
cleanup() {
    echo -e "\n${YELLOW}[!] 正在关闭服务...${RESET}"
    [[ -n "$BACKEND_PID" ]] && kill "$BACKEND_PID" 2>/dev/null && echo "   后端已停止"
    [[ -n "$FRONTEND_PID" ]] && kill "$FRONTEND_PID" 2>/dev/null && echo "   前端已停止"
    exit 0
}
trap cleanup SIGINT SIGTERM

# ── 启动后端 (后台) ──
echo -e "${GREEN}[3/4]${RESET} 启动后端服务 (http://localhost:8000)..."
cd backend
python server.py &
BACKEND_PID=$!
cd "$ROOT"
echo -e "${GREEN}[✓]${RESET} 后端服务已启动 (PID: $BACKEND_PID)"

# 等待后端就绪
sleep 2

# ── 启动前端 (后台) ──
echo -e "${GREEN}[4/4]${RESET} 启动前端开发服务器 (http://localhost:5173)..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd "$ROOT"
echo -e "${GREEN}[✓]${RESET} 前端开发服务器已启动 (PID: $FRONTEND_PID)"

# ── 完成 ──
echo -e ""
echo -e "${CYAN}╔══════════════════════════════════════╗${RESET}"
echo -e "${CYAN}║           启动完成 ✨                ║${RESET}"
echo -e "${CYAN}║                                      ║${RESET}"
echo -e "${CYAN}║   后端:  http://localhost:8000       ║${RESET}"
echo -e "${CYAN}║   前端:  http://localhost:5173       ║${RESET}"
echo -e "${CYAN}║   文档:  http://localhost:8000/docs   ║${RESET}"
echo -e "${CYAN}║                                      ║${RESET}"
echo -e "${CYAN}║   按 Ctrl+C 停止所有服务             ║${RESET}"
echo -e "${CYAN}╚══════════════════════════════════════╝${RESET}"
echo -e ""

# 等待任意子进程退出
wait
