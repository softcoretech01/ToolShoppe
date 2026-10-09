@echo off
title ToolShoppe ERP - Launcher
echo ========================================================
echo       ToolShoppe ERP - Starting Services...
echo ========================================================
echo.

cd /d "%~dp0"

echo [1/3] Checking Python backend environment...
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

echo [2/3] Starting FastAPI backend on http://localhost:8000 ...
start "ToolShoppe Backend (Port 8000)" cmd /k "cd /d "%~dp0backend" && "%~dp0.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --port 8000"

echo [3/3] Starting Frontend on http://localhost:5173 ...
start "ToolShoppe Frontend (Port 5173)" cmd /k "cd /d "%~dp0frontend" && npm run dev"

timeout /t 3 /nobreak >nul

echo.
echo ========================================================
echo   Services are running! Opening ToolShoppe ERP in browser...
echo   URL:   http://localhost:5173
echo   Login: admin / admin123
echo ========================================================
start http://localhost:5173

pause
