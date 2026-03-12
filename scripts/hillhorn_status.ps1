# Hillhorn status - Gateway, last use, MCP
$base = "c:\Hillhorn"
$activityFile = "$base\data\hillhorn_activity.json"

Write-Host "=== Hillhorn Status ===" -ForegroundColor Cyan

# Gateway
try {
    $r = Invoke-RestMethod -Uri "http://127.0.0.1:8001/health" -TimeoutSec 3 -ErrorAction Stop
    Write-Host "[OK] Gateway: $($r.status)" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] Gateway not running" -ForegroundColor Red
}

# Last use
if (Test-Path $activityFile) {
    $act = Get-Content $activityFile -Raw -Encoding UTF8 | ConvertFrom-Json
    $ts = [double]$act.last_use
    $dt = [DateTimeOffset]::FromUnixTimeSeconds([long]$ts).LocalDateTime
    $ago = (Get-Date) - $dt
    $agoStr = if ($ago.TotalMinutes -lt 1) { "just now" } elseif ($ago.TotalMinutes -lt 60) { "$([int]$ago.TotalMinutes)m ago" } else { "$([int]$ago.TotalHours)h ago" }
    Write-Host "[Last use] $($act.last_tool) - $agoStr" -ForegroundColor Gray
} else {
    Write-Host "[Last use] never" -ForegroundColor Gray
}

Write-Host "`nMCP status: Cursor Settings > Tools & MCP > Hillhorn (green = connected)" -ForegroundColor Gray
