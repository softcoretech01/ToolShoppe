# ToolShoppe ERP - PowerShell Launcher
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "      ToolShoppe ERP - Starting Services...            " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

# 1. Start Backend
Write-Host "`n[1/2] Starting FastAPI Backend on port 8000..." -ForegroundColor Yellow
$PythonCmd = if (Test-Path "$Root\.venv\Scripts\python.exe") { "& '$Root\.venv\Scripts\python.exe'" } else { "python" }
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$Root\backend'; $PythonCmd -m uvicorn app.main:app --reload --port 8000"

# 2. Start Frontend
Write-Host "[2/2] Starting Frontend on port 5173..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$Root\frontend'; npm run dev"

Start-Sleep -Seconds 3

Write-Host "`nServices started! Opening browser..." -ForegroundColor Green
Start-Process "http://localhost:5173"

Write-Host "`nToolShoppe ERP is live at: http://localhost:5173" -ForegroundColor Cyan
Write-Host "Login credentials: admin / admin123" -ForegroundColor White
