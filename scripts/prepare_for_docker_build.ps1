# Hillhorn: Full preparation for Docker build on Windows
# Copies extension, validates structure, checks Docker

$ErrorActionPreference = "Continue"
$base = if ($env:HILLHORN_ROOT) { $env:HILLHORN_ROOT } else { (Get-Item $PSScriptRoot).Parent.FullName }

function Log { param($msg, $color = "White") Write-Host $msg -ForegroundColor $color }

Log "`n=== Prepare for Docker Build (Windows) ===" Cyan
Log "  Project: $base`n" Gray

$allOk = $true

# 1. Copy hillhorn-chat extension
Log "[1/5] Hillhorn extension..." Cyan
$extSrc = "$base\vscode-ext-hillhorn"
$extDst = "$base\vscode\extensions\hillhorn-chat"
if (Test-Path $extSrc) {
    if (Test-Path $extDst) { Remove-Item $extDst -Recurse -Force }
    Copy-Item $extSrc $extDst -Recurse -Force -Exclude node_modules
    Log "  OK (copied to vscode/extensions/hillhorn-chat)" Green
} else {
    Log "  SKIP (vscode-ext-hillhorn not found)" Yellow
}

# 2. Project structure
Log "[2/5] Project structure..." Cyan
$required = @("$base\vscode\package.json", "$base\vscode\build\package.json", "$base\vscode\extensions")
$missing = $required | Where-Object { -not (Test-Path $_) }
if ($missing) {
    Log "  FAIL: $($missing -join ', ')" Red
    $allOk = $false
} else {
    Log "  OK" Green
}

# 3. TypeScript 5.x in package.json
Log "[3/5] TypeScript version..." Cyan
$pkg = Get-Content "$base\vscode\package.json" -Raw | ConvertFrom-Json
$ts = ""; try { if ($pkg.dependencies.typescript) { $ts = $pkg.dependencies.typescript } } catch {}; if (-not $ts -and $pkg.devDependencies.typescript) { $ts = $pkg.devDependencies.typescript }
if ($ts -match "5\.") {
    Log "  OK ($ts)" Green
} else {
    Log "  WARN: expected 5.x, got $ts" Yellow
}

# 4. Docker
Log "[4/5] Docker..." Cyan
$dockerOk = $false
if (Get-Command docker -ErrorAction SilentlyContinue) {
    $di = docker info 2>&1
    if ($LASTEXITCODE -eq 0) { $dockerOk = $true }
}
if ($dockerOk) {
    Log "  OK" Green
} else {
    Log "  NOT RUNNING" Red
    $allOk = $false
}

# 5. Build image
Log "[5/5] node:22 image..." Cyan
if ($dockerOk) {
    docker pull node:22-bookworm-slim 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Log "  OK" Green
    } else {
        Log "  Pull failed" Yellow
    }
} else {
    Log "  SKIP (Docker not running)" Gray
}

Log ""
if ($allOk) {
    Log "[OK] Ready. Run: .\scripts\build_vscode_docker.ps1" Green
} else {
    Log "Docker not running. Try:" Yellow
    Log "  1. Open Docker Desktop from Start menu" Gray
    Log "  2. Wait until icon in tray shows ready" Gray
    Log "  3. If error: wsl --update (in Admin PowerShell)" Gray
    Log "  4. Restart Docker Desktop" Gray
    Log "`nThen run this script again." Yellow
}
Log ""
