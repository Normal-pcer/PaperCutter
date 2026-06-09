@echo off
setlocal enabledelayedexpansion

set "ROOT=%~dp0"
cd /d "%ROOT%"

echo [PaperCutter] Starting...
echo.

:: Backend - use venv pythonw (no console window), truly detached
echo [1/2] Starting backend http://localhost:7652 ...
powershell -Command "$p = Start-Process -FilePath '%ROOT%.venv\Scripts\pythonw.exe' -ArgumentList 'server.py' -WorkingDirectory '%ROOT%backend' -WindowStyle Hidden -PassThru; Write-Output $p.Id" > .backend.pid 2>nul
echo [OK] Backend started

:: Frontend - detached, hidden console
echo [2/2] Starting frontend http://localhost:5173 ...
powershell -Command "$p = Start-Process cmd -ArgumentList '/c cd /d \"%ROOT%frontend\" && npm run dev' -WindowStyle Hidden -PassThru; Write-Output $p.Id" > .frontend.pid 2>nul
echo [OK] Frontend started

echo.
echo [PaperCutter] Started
echo   Backend:  http://localhost:7652
echo   Frontend: http://localhost:5173
echo   Docs:     http://localhost:7652/docs
echo.
echo   Run stop.bat to stop services
echo.
pause
