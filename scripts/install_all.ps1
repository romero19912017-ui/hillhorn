# Hillhorn: full install - Python, vscode, extension, build deps
# Run: .\scripts\install_all.ps1

$ErrorActionPreference = "Continue"
$base = "c:\Hillhorn"
Set-Location $base

function Log { param($msg, $color = "White") Write-Host $msg -ForegroundColor $color }
function Ok { param($msg) Log "  [OK] $msg" Green }
function Warn { param($msg) Log "  [WARN] $msg" Yellow }

Log "`n=== Hillhorn Full Install ===" Cyan
Log ""

# 1. Python
Log "[1/6] Python..." Cyan
& .\venv_hillhorn\Scripts\Activate.ps1
pip install -q -r requirements.txt 2>&1 | Out-Null
pip install -e ".\nwf-core[faiss]" -q 2>&1 | Out-Null
pip install python-multipart -q 2>&1 | Out-Null
Ok "pip, nwf-core, python-multipart"
Log ""

# 2. vscode-ext-hillhorn
Log "[2/6] vscode-ext-hillhorn..." Cyan
Set-Location "$base\vscode-ext-hillhorn"
npm install 2>&1 | Out-Null
npm run compile 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) { Ok "extension compiled" }
else { Warn "extension compile failed" }
Set-Location $base
Log ""

# 3. Copy extension to vscode
Log "[3/6] Copy hillhorn-chat to vscode/extensions..." Cyan
$extDest = "$base\vscode\extensions\hillhorn-chat"
if (Test-Path "$base\vscode\extensions") {
    if (Test-Path $extDest) { Remove-Item $extDest -Recurse -Force }
    Copy-Item "$base\vscode-ext-hillhorn" $extDest -Recurse -Exclude node_modules
    Ok "copied"
} else { Warn "vscode/extensions not found" }
Log ""

# 4. vscode build folder
Log "[4/6] vscode/build..." Cyan
if (Test-Path "$base\vscode\build\package.json") {
    Set-Location "$base\vscode\build"
    npm install --ignore-scripts 2>&1 | Out-Null
    Ok "build deps"
    Set-Location $base
} else { Warn "vscode/build not found" }
Log ""

# 5. vscode main (gulp-cli, node_modules)
Log "[5/6] vscode main..." Cyan
if (Test-Path "$base\vscode\package.json") {
    Set-Location "$base\vscode"
    npm install gulp-cli --save-dev --ignore-scripts 2>&1 | Out-Null
    Ok "gulp-cli, deps"
    Set-Location $base
} else { Warn "vscode not found" }
Log ""

# 6. Node + vscode compile
Log "[6/6] Node + vscode compile..." Cyan
$nodeVer = node -v 2>$null
Ok "Node $nodeVer"
if (Test-Path "$base\vscode\package.json") {
    Set-Location "$base\vscode"
    $out = npm run compile 2>&1
    if ($LASTEXITCODE -eq 0) {
        Ok "vscode compiled"
    } else {
        Warn "vscode compile failed (Node $nodeVer). Use fnm/nvm with Node 20 if needed"
        $out | Select-Object -Last 3
    }
    Set-Location $base
}
Log ""

Log "=== Done ===" Cyan
Log ""
Log "Run: .\scripts\start_all.ps1" Yellow
Log "Test: .\scripts\test.ps1" Yellow
Log ""
