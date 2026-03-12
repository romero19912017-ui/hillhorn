# Hillhorn: Запуск всего сразу
# Gateway + NWF Adapter + Cursor

$base = if ($env:HILLHORN_ROOT) { $env:HILLHORN_ROOT } else { (Get-Item $PSScriptRoot).Parent.FullName }
$venv = "$base\venv_hillhorn\Scripts\Activate.ps1"

if (-not (Test-Path $venv)) {
    Write-Host "ERROR: venv not found. Run install_all.ps1" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== Hillhorn - Starting ===" -ForegroundColor Cyan

# 1. Gateway
Write-Host "[1/3] DeepSeek Gateway..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$base'; . '$venv'; uvicorn deepseek_gateway:app --reload --port 8001"

# 2. NWF Adapter
Write-Host "[2/3] NWF Memory Adapter..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$base'; . '$venv'; python nwf_memory_adapter.py --watch"

# 3. Wait for Gateway
Start-Sleep -Seconds 5

# 4. Cursor
Write-Host "[3/3] Cursor..." -ForegroundColor Yellow
if (Get-Command cursor -ErrorAction SilentlyContinue) {
    Start-Process cursor -ArgumentList "$base"
} elseif (Test-Path "$env:LOCALAPPDATA\Programs\Cursor\Cursor.exe") {
    Start-Process "$env:LOCALAPPDATA\Programs\Cursor\Cursor.exe" -ArgumentList "$base"
} else {
    Write-Host "Cursor not found. Open manually." -ForegroundColor Yellow
}

Write-Host "`nDone. Gateway: http://127.0.0.1:8001/health" -ForegroundColor Green
