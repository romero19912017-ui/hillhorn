# Hillhorn: Fix @vscode/policy-watcher build on Windows (Spectre libs not installed)
# Run after npm install if native modules fail with MSB8040

$ErrorActionPreference = "Stop"
$base = if ($env:HILLHORN_ROOT) { $env:HILLHORN_ROOT } else { (Get-Item $PSScriptRoot).Parent.FullName }
$gyp = "$base\vscode\node_modules\@vscode\policy-watcher\binding.gyp"

if (-not (Test-Path $gyp)) {
    Write-Host "policy-watcher not found, skip" -ForegroundColor Yellow
    exit 0
}

$content = Get-Content $gyp -Raw
if ($content -match '"SpectreMitigation":\s*"Spectre"') {
    $content = $content -replace '"SpectreMitigation":\s*"Spectre"', '"SpectreMitigation": "false"'
    Set-Content $gyp $content -NoNewline
    Write-Host "Patched binding.gyp (Spectre disabled)" -ForegroundColor Green
}

Write-Host "Rebuilding @vscode/policy-watcher..." -ForegroundColor Cyan
Push-Location "$base\vscode"
npm rebuild @vscode/policy-watcher 2>&1
Pop-Location
Write-Host "Done." -ForegroundColor Green
