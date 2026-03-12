# Hillhorn - запуск проверок
# Запускает Gateway (если не запущен), затем тестовый скрипт

$base = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$venv = "$base\venv_hillhorn\Scripts\python.exe"

# Проверка Gateway
try {
    $null = Invoke-RestMethod -Uri "http://127.0.0.1:8001/health" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "[OK] Gateway running" -ForegroundColor Green
} catch {
    Write-Host "[!] Starting Gateway..." -ForegroundColor Yellow
    & "$base\scripts\start_all_background.ps1" -Force
    Start-Sleep -Seconds 5
}

# Запуск базового теста
Write-Host "`n=== Hillhorn quick test ===" -ForegroundColor Cyan
& $venv "$base\scripts\test_hillhorn.py"

Write-Host "`n=== Manual tasks ===" -ForegroundColor Cyan
Write-Host "Open tasks in: $PSScriptRoot\tasks\"
Write-Host "Run Agent with .cursorrules - execute TASK.md for each folder"
Write-Host "Fill REPORT_TEMPLATE.md after completion"
