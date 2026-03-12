# Build Hillhorn Status extension to .vsix (optional)
# Requires: npm install -g @vscode/vsce
# Run: .\scripts\build_extension.ps1

$base = "c:\Hillhorn"
$extDir = "$base\extensions\hillhorn-status"
$outDir = "$base\dist"

if (-not (Test-Path $extDir)) {
    Write-Host "Extension not found: $extDir" -ForegroundColor Red
    exit 1
}

# Create package if needed
$pkg = "$extDir\package.json"
if (-not (Test-Path "$extDir\README.md")) {
    @"
# Hillhorn Status
Status bar indicator for Hillhorn MCP usage.
"@ | Set-Content "$extDir\README.md" -Encoding UTF8
}

New-Item -ItemType Directory -Force -Path $outDir | Out-Null
Push-Location $extDir
try {
    $vsix = & npx --yes @vscode/vsce package --out "$outDir\hillhorn-status.vsix" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Built: $outDir\hillhorn-status.vsix" -ForegroundColor Green
        Write-Host "Install: Cursor -> Extensions -> ... -> Install from VSIX"
    } else {
        Write-Host $vsix
        Write-Host "Install: npm i -g @vscode/vsce, then run again" -ForegroundColor Yellow
    }
} catch {
    Write-Host "vsce not found. Run: npm install -g @vscode/vsce" -ForegroundColor Yellow
}
Pop-Location
