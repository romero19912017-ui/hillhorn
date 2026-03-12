# Hillhorn: Launch VS Code with Vite dev server (recommended for development)
# Fixes blank/broken HTML when loading from file://

$base = if ($env:HILLHORN_ROOT) { $env:HILLHORN_ROOT } else { (Get-Item $PSScriptRoot).Parent.FullName }
$exe = "$base\vscode\.build\electron\Code - OSS.exe"

if (-not (Test-Path $exe)) {
    Write-Host "ERROR: Code - OSS.exe not found. Run: cd vscode; npm run electron" -ForegroundColor Red
    exit 1
}

# Ensure Vite deps installed
if (-not (Test-Path "$base\vscode\build\vite\node_modules")) {
    Write-Host "Installing Vite deps..." -ForegroundColor Yellow
    Push-Location "$base\vscode\build\vite"
    npm install 2>&1
    Pop-Location
}

# Start Vite dev server in new window (must stay running)
Write-Host "Starting Vite dev server (new window)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$base\vscode\build\vite'; npm run dev"

# Wait for Vite to be ready
$maxWait = 30
$waited = 0
while ($waited -lt $maxWait) {
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:5199" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        Write-Host "Vite ready." -ForegroundColor Green
        break
    } catch {
        Start-Sleep -Seconds 2
        $waited += 2
    }
}

if ($waited -ge $maxWait) {
    Write-Host "WARN: Vite may not be ready. Launching anyway..." -ForegroundColor Yellow
}

$env:NODE_ENV = "development"
$env:VSCODE_DEV = "1"
$env:VSCODE_SKIP_PRELAUNCH = "1"
$env:VSCODE_DEV_SERVER_URL = "http://localhost:5199/build/vite/workbench-vite-electron.html"

Write-Host "Launching Hillhorn VS Code (Vite)..." -ForegroundColor Cyan
Start-Process -FilePath $exe -ArgumentList ".", "--disable-extension=vscode.vscode-api-tests" -WorkingDirectory "$base\vscode"

Write-Host "Done. Close the Vite window when done." -ForegroundColor Green
