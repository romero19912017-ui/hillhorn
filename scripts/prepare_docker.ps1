# Hillhorn: Prepare Docker for VS Code build on Windows
# Run before build_vscode_docker.ps1

$ErrorActionPreference = "Stop"
$base = if ($env:HILLHORN_ROOT) { $env:HILLHORN_ROOT } else { (Get-Item $PSScriptRoot).Parent.FullName }

function Log { param($msg, $color = "White") Write-Host $msg -ForegroundColor $color }

Log "`n=== Prepare Docker for Windows Build ===" Cyan
Log "  Project: $base" Gray
Log ""

# 1. Docker installed
Log "[1/5] Docker..." Cyan
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Log "  NOT FOUND. Run: .\scripts\install_docker.ps1" Red
    exit 1
}
Log "  OK" Green

# 2. Docker running
Log "[2/5] Docker daemon..." Cyan
$info = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Log "  NOT RUNNING. Start Docker Desktop and retry." Red
    exit 1
}
Log "  OK" Green

# 3. WSL2 / Linux containers
Log "[3/5] Container runtime..." Cyan
$runCheck = docker run --rm hello-world 2>&1
if ($LASTEXITCODE -ne 0) {
    Log "  FAILED. Ensure Docker uses WSL2 backend." Yellow
} else {
    Log "  OK (Linux)" Green
}

# 4. Pull build image
Log "[4/5] Pull node:22-bookworm-slim..." Cyan
docker pull node:22-bookworm-slim 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Log "  Pull failed. Check network." Red
    exit 1
}
Log "  OK" Green

# 5. Validate project
Log "[5/5] Project structure..." Cyan
$required = @(
    "$base\vscode\package.json",
    "$base\vscode\build\package.json",
    "$base\vscode\extensions"
)
$missing = $required | Where-Object { -not (Test-Path $_) }
if ($missing) {
    Log "  Missing: $($missing -join ', ')" Red
    exit 1
}
Log "  OK" Green

Log "`n[OK] Docker ready for build." Green
Log "`nRun: .\scripts\build_vscode_docker.ps1" Cyan
Log ""
