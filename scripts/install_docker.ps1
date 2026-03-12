# Hillhorn: Install Docker Desktop on Windows 11
# Run as Administrator: .\scripts\install_docker.ps1

$ErrorActionPreference = "Stop"

function Log { param($msg, $color = "White") Write-Host $msg -ForegroundColor $color }

Log "`n=== Docker Desktop Installation ===" Cyan

# Check if already installed
if (Get-Command docker -ErrorAction SilentlyContinue) {
    $ver = docker --version
    Log "[OK] Docker already installed: $ver" Green
    Log "`nRestart Docker Desktop if needed, then run: .\scripts\build_vscode_docker.ps1" Cyan
    exit 0
}

# Check WSL2
Log "`n[1/3] Checking WSL2..." Cyan
$wslOk = $false
try {
    $wsl = wsl --status 2>&1
    if ($LASTEXITCODE -eq 0) { $wslOk = $true; Log "  WSL2 available" Green }
} catch { }
if (-not $wslOk) {
    Log "  WSL2 may not be enabled. Enabling..." Yellow
    dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
    dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
    Log "  Reboot may be required. Run this script again after reboot." Yellow
    exit 1
}

# Install via winget
Log "`n[2/3] Installing Docker Desktop via winget..." Cyan
winget install -e --id Docker.DockerDesktop --accept-package-agreements --accept-source-agreements
if ($LASTEXITCODE -ne 0) {
    Log "  winget failed. Try: https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe" Red
    exit 1
}

Log "`n[3/3] Docker Desktop installed." Green
Log "`nNext steps:" Cyan
Log "  1. Restart computer (or start Docker Desktop from Start menu)" Yellow
Log "  2. Open Docker Desktop and complete setup" Yellow
Log "  3. Run: .\scripts\build_vscode_docker.ps1" Yellow
Log ""
