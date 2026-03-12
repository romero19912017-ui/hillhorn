# Hillhorn: Launch VS Code (Code - OSS)
$base = if ($env:HILLHORN_ROOT) { $env:HILLHORN_ROOT } else { (Get-Item $PSScriptRoot).Parent.FullName }
$exe = "$base\vscode\.build\electron\Code - OSS.exe"

if (-not (Test-Path $exe)) {
    Write-Host "ERROR: Code - OSS.exe not found. Run: cd vscode; npm run electron" -ForegroundColor Red
    exit 1
}

$env:NODE_ENV = "development"
$env:VSCODE_DEV = "1"
$env:VSCODE_CLI = "1"
$env:ELECTRON_ENABLE_LOGGING = "1"

$workDir = "$base\vscode"
$args = @(".", "--disable-extension=vscode.vscode-api-tests") + $args

Write-Host "Launching Hillhorn VS Code..." -ForegroundColor Cyan
Start-Process -FilePath $exe -ArgumentList $args -WorkingDirectory $workDir
Write-Host "Started. Check for the Code - OSS window." -ForegroundColor Green
