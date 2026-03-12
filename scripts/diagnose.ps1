# Hillhorn full diagnostic: Gateway, MCP, ports, activity
# Usage: .\scripts\diagnose.ps1

$ErrorActionPreference = "Continue"
$dataRoot = $env:HILLHORN_DATA_ROOT
if (-not $dataRoot) { $dataRoot = "C:\hillhorn_data" }
$dataDir = $dataRoot
$activityPath = Join-Path $dataRoot "hillhorn_activity.json"
$errorsPath = Join-Path $dataRoot "hillhorn_errors.log"

Write-Host "=== Hillhorn Diagnostic ===" -ForegroundColor Cyan
Write-Host ""

# 1. Gateway health
Write-Host "1. Gateway (port 8001)" -ForegroundColor Yellow
try {
    $r = Invoke-RestMethod -Uri "http://127.0.0.1:8001/health" -TimeoutSec 3 -ErrorAction Stop
    Write-Host "   [OK] Status: $($r.status), memory_charges: $($r.memory_charges)" -ForegroundColor Green
} catch {
    Write-Host "   [FAIL] Not reachable: $($_.Exception.Message)" -ForegroundColor Red
}

# 2. Port 8001
Write-Host ""
Write-Host "2. Port 8001" -ForegroundColor Yellow
$listeners = netstat -ano 2>$null | Select-String ":8001.*LISTENING"
if ($listeners) {
    Write-Host "   [OK] Listening" -ForegroundColor Green
} else {
    Write-Host "   [WARN] Not in use (Gateway may be stopped)" -ForegroundColor Yellow
}

# 3. MCP process (hillhorn)
Write-Host ""
Write-Host "3. MCP Server (hillhorn)" -ForegroundColor Yellow
$mcpProcs = Get-Process -Name "python*" -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -and $_.Path -like "*hillhorn*"
}
if ($mcpProcs) {
    Write-Host "   [OK] Process found: $($mcpProcs.Count) python process(es)" -ForegroundColor Green
} else {
    Write-Host "   [INFO] MCP runs inside Cursor; no separate hillhorn process" -ForegroundColor Gray
}

# 4. Activity file
Write-Host ""
Write-Host "4. Activity file" -ForegroundColor Yellow
if (Test-Path $activityPath) {
    $act = Get-Content $activityPath -Raw | ConvertFrom-Json -ErrorAction SilentlyContinue
    if ($act) {
        $ts = [DateTimeOffset]::FromUnixTimeSeconds([long]$act.last_use).LocalDateTime
        Write-Host "   [OK] Path: $activityPath" -ForegroundColor Green
        Write-Host "        Last tool: $($act.last_tool), at: $ts" -ForegroundColor Gray
    } else {
        Write-Host "   [OK] Path exists (format issue)" -ForegroundColor Yellow
    }
} else {
    Write-Host "   [WARN] Not found: $activityPath" -ForegroundColor Yellow
}

# 5. Error log
Write-Host ""
Write-Host "5. Error log" -ForegroundColor Yellow
if (Test-Path $errorsPath) {
    $lines = Get-Content $errorsPath -Tail 5 -ErrorAction SilentlyContinue
    Write-Host "   [OK] Path: $errorsPath (last 5 lines below)" -ForegroundColor Green
    $lines | ForEach-Object { Write-Host "        $_" -ForegroundColor Gray }
} else {
    Write-Host "   [OK] No errors logged yet" -ForegroundColor Green
}

# 6. Data directory
Write-Host ""
Write-Host "6. Data directory (C:\hillhorn_data)" -ForegroundColor Yellow
if (Test-Path $dataRoot) {
    Write-Host "   [OK] $dataRoot exists" -ForegroundColor Green
} else {
    Write-Host "   [WARN] $dataRoot not found (will be created on first use)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "--- End diagnostic ---" -ForegroundColor Cyan
