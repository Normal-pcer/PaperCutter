@echo off
setlocal enabledelayedexpansion

echo [PaperCutter] Stopping services...
echo.

set /p "confirm=Stop background services? (Y/N): "
if /i "!confirm!" neq "Y" (
    echo [OK] Cancelled
    pause
    exit /b 0
)

:: Kill backend by PID
if exist .backend.pid (
    set /p PID=<.backend.pid
    taskkill /F /T /PID !PID! >nul 2>&1
    if !errorlevel! equ 0 ( echo [OK] Backend stopped ) else ( echo [..] Backend not running )
    del .backend.pid
) else (
    echo [..] No backend PID file
)

:: Kill frontend by PID
if exist .frontend.pid (
    set /p PID=<.frontend.pid
    taskkill /F /T /PID !PID! >nul 2>&1
    if !errorlevel! equ 0 ( echo [OK] Frontend stopped ) else ( echo [..] Frontend not running )
    del .frontend.pid
) else (
    echo [..] No frontend PID file
)

echo.
echo [PaperCutter] All services stopped
pause
