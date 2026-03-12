# Hillhorn: full build preparation
# Run: .\scripts\build.ps1

$ErrorActionPreference = "Stop"
$base = "c:\Hillhorn"
Set-Location $base

function Log { param($msg, $color = "White") Write-Host $msg -ForegroundColor $color }
function Ok { param($msg) Log "  [OK] $msg" Green }
function Warn { param($msg) Log "  [WARN] $msg" Yellow }
function Fail { param($msg) Log "  [FAIL] $msg" Red; exit 1 }

Log "`n=== Hillhorn Build ===" Cyan
Log ""

Log "[1/7] Prerequisites..." Cyan
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { Fail "Python not found" }
Ok "Python: $((python --version 2>&1))"
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { Fail "Node.js not found" }
Ok "Node: $((node -v 2>&1))"
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { Fail "npm not found" }
Ok "npm: $((npm -v 2>&1))"
Log ""

Log "[2/7] Python venv..." Cyan
if (-not (Test-Path "venv_hillhorn\Scripts\Activate.ps1")) {
    python -m venv venv_hillhorn
    Ok "venv created"
} else { Ok "venv exists" }

& .\venv_hillhorn\Scripts\Activate.ps1
$ErrorActionPreference = "Continue"
pip install -q -r requirements.txt 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { pip install -r requirements.txt }
pip install -e ".\nwf-core[faiss]" 2>&1 | Out-Null
$ErrorActionPreference = "Stop"
Ok "pip install"
Log ""

Log "[3/7] .env..." Cyan
if (-not (Test-Path ".env")) {
    Copy-Item .env.example .env
    Ok ".env created from example"
} else { Ok ".env exists" }
Log ""

Log "[4/7] Workspace..." Cyan
if (-not (Test-Path "workspace")) { New-Item -ItemType Directory -Path workspace | Out-Null; Ok "workspace created" }
else { Ok "workspace exists" }
Log ""

Log "[5/7] VS Code npm install..." Cyan
if (-not (Test-Path "vscode\package.json")) { Warn "vscode not found, skip"; Set-Location $base } else {
Set-Location vscode
if (-not (Test-Path "node_modules")) {
    npm install 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Log "npm install failed, retrying..." Yellow
        npm install
        if ($LASTEXITCODE -ne 0) { Fail "npm install failed" }
    }
    Ok "npm install done"
} else { Ok "node_modules exists" }
Set-Location $base
}
Log ""

Log "[6/7] VS Code compile..." Cyan
if (Test-Path "vscode\package.json") {
Set-Location vscode
$ErrorActionPreference = "Continue"
$compileOut = npm run compile 2>&1
$compileExit = $LASTEXITCODE
if ($compileExit -eq 0) {
    Ok "compile done"
} else {
    Log "compile failed (exit $compileExit)" Red
    if ($compileOut -match "MSB8040|Spectre") {
        Warn "MSB8040: install Spectre-mitigated libs in VS Build Tools"
    }
    $compileOut | Select-Object -Last 20
}
Set-Location $base
$ErrorActionPreference = "Stop"
} else { Warn "vscode not found, skip compile" }
Log ""

Log "[7/7] Python modules..." Cyan
& .\venv_hillhorn\Scripts\Activate.ps1
$test = python -c "import nwf, torch, fastapi" 2>&1
if ($LASTEXITCODE -eq 0) { Ok "nwf, torch, fastapi" }
else { Warn "nwf/torch/fastapi: $test (pip install nwf-core)" }
Log ""

Log "=== Ready ===" Cyan
Log ""
Log "Next:" Yellow
Log "  1. API key in .env"
Log "  2. Run scripts\start_all.ps1"
Log "  3. Check http://127.0.0.1:8001/health"
Log ""
