# Force restart Hillhorn (full reload)
$base = "c:\Hillhorn"
& "$base\scripts\stop_hillhorn.ps1"
Start-Sleep -Seconds 4
& "$base\scripts\start_all_background.ps1" -Force 2>$null
if (-not $?) {
    & "$base\scripts\start_all_background.ps1"
}
Write-Host "Restarted. Check http://127.0.0.1:8001/health"
