# Hillhorn: Build VS Code in Docker (Linux container)
# Produces compiled output for Windows - run npm install on host after for native modules
# Prereq: Run .\scripts\prepare_docker.ps1 first

$ErrorActionPreference = "Stop"
$base = if ($env:HILLHORN_ROOT) { $env:HILLHORN_ROOT } else { (Get-Item $PSScriptRoot).Parent.FullName }

function Log { param($msg, $color = "White") Write-Host $msg -ForegroundColor $color }

Log "`n=== VS Code Build via Docker ===" Cyan

# Check Docker
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Log "Docker not found. Run: .\scripts\install_docker.ps1" Red
    exit 1
}
$dockerOk = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Log "Docker not running. Start Docker Desktop and retry." Red
    exit 1
}
Log "[OK] Docker ready" Green

# Ensure vscode exists
if (-not (Test-Path "$base\vscode\package.json")) {
    Log "vscode/package.json not found" Red
    exit 1
}

# Docker Desktop accepts c:\Hillhorn or c:/Hillhorn for Windows paths
$mountHost = $base -replace '\\', '/'

Log "`nBuilding in container (Node 22, Linux)..." Cyan
Log "  Mount: $base -> /workspace" Gray
Log "  This may take 15-30 min on first run." Gray
Log ""

# Docker Desktop requires forward slashes for Windows paths
$mountHost = $base -replace '\\', '/'
docker run --rm `
    -v "${mountHost}:/workspace" `
    -w "/workspace/vscode" `
    node:22-bookworm-slim `
    bash -c "apt-get update -qq && apt-get install -y -qq python3 make g++ git && npm install && npm run compile"

if ($LASTEXITCODE -ne 0) {
    Log "`nBuild failed." Red
    exit 1
}

Log "`n[OK] Compile complete." Green
Log "`nNext: Install Windows native modules (on host):" Cyan
Log "  cd vscode" Yellow
Log "  npm install" Yellow
Log "`nThen run VS Code:" Cyan
Log "  .\scripts\code.bat" Yellow
Log "  or: npm run watch" Yellow
Log ""
