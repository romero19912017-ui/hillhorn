# Hillhorn: stop all background processes (port 8001 + venv python)
Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue | ForEach-Object {
    taskkill /F /T /PID $_.OwningProcess 2>$null
    Write-Host "Stopped port 8001"
}
Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -like "*hillhorn*"
} | ForEach-Object {
    taskkill /F /T /PID $_.Id 2>$null
    Write-Host "Stopped python $($_.Id)"
}
Start-Sleep -Seconds 2
Write-Host "Done."
