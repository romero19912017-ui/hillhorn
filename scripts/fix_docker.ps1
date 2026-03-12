# Hillhorn: Fix Docker Desktop "unable to start" on Windows
# Run as Administrator if needed

Write-Host "`n=== Docker Desktop Fix ===" -ForegroundColor Cyan

Write-Host "`n[1] Updating WSL2..." -ForegroundColor Yellow
wsl --update
if ($LASTEXITCODE -ne 0) { Write-Host "  Run in Admin PowerShell" -ForegroundColor Red }

Write-Host "`n[2] Restart Docker Desktop..." -ForegroundColor Yellow
Stop-Process -Name "Docker Desktop" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
Write-Host "  Waiting 60 sec for startup..." -ForegroundColor Gray
Start-Sleep -Seconds 60

Write-Host "`n[3] Check status..." -ForegroundColor Yellow
docker info 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "`n[OK] Docker is running." -ForegroundColor Green
    Write-Host "Run: .\scripts\prepare_for_docker_build.ps1" -ForegroundColor Cyan
} else {
    Write-Host "`nStill not working. Try:" -ForegroundColor Red
    Write-Host "  - Reboot" -ForegroundColor Gray
    Write-Host "  - Docker Desktop Settings -> Reset to factory" -ForegroundColor Gray
    Write-Host "  - Enable Virtualization in BIOS" -ForegroundColor Gray
}
Write-Host ""
