# Hillhorn: запуск в фоне (без лишних окон)
# Gateway + NWF Adapter в скрытых процессах

$base = "c:\Hillhorn"
$gatewayPort = 8001
$venv = "$base\venv_hillhorn\Scripts"
$python = "$venv\python.exe"

# Optional: -Force to restart even if running
$force = $args -contains "-Force"
if (-not $force) {
    $check = try {
    (Invoke-WebRequest -Uri "http://127.0.0.1:$gatewayPort/health" -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200
} catch { $false }
    if ($check) {
        Write-Host "Hillhorn already running. Use -Force to restart."
        exit 0
    }
} else {
    & "$base\scripts\stop_hillhorn.ps1"
}

# Start Gateway (hidden)
Start-Process -FilePath $python -ArgumentList "-m", "uvicorn", "deepseek_gateway:app", "--port", "$gatewayPort" `
    -WorkingDirectory $base -WindowStyle Hidden -PassThru | Out-Null

# Start NWF Adapter (hidden) - workspace = project root for SOUL/USER/MEMORY
# Skip if HILLHORN_AUTO_INDEX=0
$autoIndex = $env:HILLHORN_AUTO_INDEX
if ($autoIndex -eq "" -or $autoIndex -eq "1") {
    $env:MOLTBOT_WORKSPACE = $base
    Start-Process -FilePath $python -ArgumentList "nwf_memory_adapter.py", "--watch" `
        -WorkingDirectory $base -WindowStyle Hidden -PassThru | Out-Null
}

Start-Sleep -Seconds 2
$health = try {
    (Invoke-WebRequest -Uri "http://127.0.0.1:$gatewayPort/health" -UseBasicParsing -TimeoutSec 5).Content
} catch { $null }

if ($health) {
    Write-Host "Hillhorn OK. Gateway: $gatewayPort"
} else {
    Write-Host "Gateway starting... check http://127.0.0.1:$gatewayPort/health"
}
