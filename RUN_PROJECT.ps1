$ErrorActionPreference = "Stop"

Write-Host "Starting ReSched AI setup..." -ForegroundColor Cyan

if (-not (Test-Path ".venv")) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
}

Write-Host "Installing requirements..." -ForegroundColor Yellow
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\pip.exe install -r requirements.txt

Write-Host ""
Write-Host "ReSched AI will run at: http://127.0.0.1:8002" -ForegroundColor Green
Write-Host "Login: admin / admin123" -ForegroundColor Green
Write-Host ""

.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8002
