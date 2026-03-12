# Hillhorn status - Gateway, memory, MCP
$base = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not $base) { $base = "c:\Hillhorn" }

Write-Host "=== Hillhorn Status ===" -ForegroundColor Cyan

# Gateway
try {
    $r = Invoke-RestMethod -Uri "http://127.0.0.1:8001/health" -TimeoutSec 3 -ErrorAction Stop
    Write-Host "[OK] Gateway: $($r.status), memory_charges=$($r.memory_charges)" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] Gateway not running" -ForegroundColor Red
}

# Memory API
try {
    $r = Invoke-RestMethod -Uri "http://127.0.0.1:8001/v1/memory/health" -TimeoutSec 3 -ErrorAction Stop
    Write-Host "[OK] Memory API: $($r.version)" -ForegroundColor Green
} catch {
    Write-Host "[WARN] Memory API: $($_.Exception.Message)" -ForegroundColor Yellow
}

# Port 8001
$listeners = netstat -ano 2>$null | Select-String ":8001.*LISTENING"
if ($listeners) {
    Write-Host "[OK] Port 8001 listening (Gateway)" -ForegroundColor Green
} else {
    Write-Host "[INFO] Port 8001 not in use" -ForegroundColor Gray
}
