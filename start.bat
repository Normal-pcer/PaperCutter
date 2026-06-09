@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ──────────────────────────────────────────────
::  PaperCutter — Windows 一键启动脚本
::  同时启动后端 (FastAPI) + 前端 (Vite dev server)
::  用法: 双击 start.bat 即可
:: ──────────────────────────────────────────────

set "ROOT=%~dp0"
cd /d "%ROOT%"

echo ╔══════════════════════════════════════╗
echo ║     PaperCutter — 正在启动...       ║
echo ╚══════════════════════════════════════╝
echo.

:: ── 检查后端依赖 ──
echo [1/4] 检查后端依赖...
pip show fastapi >nul 2>&1
if !errorlevel! neq 0 (
    echo [!] 安装后端依赖...
    pip install -r backend\requirements.txt
    if !errorlevel! neq 0 (
        echo [错误] 后端依赖安装失败，请手动执行: pip install -r backend\requirements.txt
        pause
        exit /b 1
    )
) else (
    echo [✓] 后端依赖已就绪
)

:: ── 检查前端依赖 ──
echo [2/4] 检查前端依赖...
if not exist "frontend\node_modules" (
    echo [!] 安装前端依赖...
    cd frontend && npm install && cd ..
    if !errorlevel! neq 0 (
        echo [错误] 前端依赖安装失败，请手动执行: cd frontend ^&^& npm install
        pause
        exit /b 1
    )
) else (
    echo [✓] 前端依赖已就绪
)

:: ── 启动后端 (新窗口) ──
echo [3/4] 启动后端服务 (http://localhost:8000)...
start "PaperCutter Backend" cmd /c "cd /d "%ROOT%backend" && python server.py"
if !errorlevel! neq 0 (
    echo [错误] 后端启动失败
    pause
    exit /b 1
)
echo [✓] 后端服务已启动

:: ── 启动前端 (新窗口) ──
echo [4/4] 启动前端开发服务器 (http://localhost:5173)...
start "PaperCutter Frontend" cmd /c "cd /d "%ROOT%frontend" && npm run dev"
if !errorlevel! neq 0 (
    echo [错误] 前端启动失败
    pause
    exit /b 1
)
echo [✓] 前端开发服务器已启动

echo.
echo ╔══════════════════════════════════════╗
echo ║           启动完成 ✨                ║
echo ║                                      ║
echo ║   后端:  http://localhost:8000       ║
echo ║   前端:  http://localhost:5173       ║
echo ║   文档:  http://localhost:8000/docs   ║
echo ║                                      ║
echo ║   关闭窗口即可停止服务               ║
echo ╚══════════════════════════════════════╝
echo.
pause
