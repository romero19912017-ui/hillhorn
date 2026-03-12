# Hillhorn: проверка сборки VS Code после установки Spectre libs
# Запуск: .\scripts\check_vscode_build.ps1

$vscode = "c:\Hillhorn\vscode"
Push-Location $vscode

Write-Host "=== Проверка VS Code build ===" -ForegroundColor Cyan
Write-Host ""

# 1. node_modules
$nm = Test-Path "node_modules"
Write-Host "node_modules: $(if ($nm) { 'PRESENT' } else { 'NOT FOUND' })"
if (-not $nm) {
    Write-Host "Run: npm install" -ForegroundColor Yellow
    Pop-Location
    exit 1
}

# 2. npm run compile
Write-Host ""
Write-Host "Running: npm run compile..." -ForegroundColor Cyan
$out = npm run compile 2>&1
$exitCode = $LASTEXITCODE
$out | Select-Object -First 80

Write-Host ""
if ($exitCode -eq 0) {
    Write-Host "=== COMPILE: SUCCESS ===" -ForegroundColor Green
} else {
    Write-Host "=== COMPILE: FAILED (exit $exitCode) ===" -ForegroundColor Red
    if ($out -match "MSB8040|Spectre") {
        Write-Host "MSB8040/Spectre detected. Install: VS Build Tools -> Spectre-mitigated libs" -ForegroundColor Yellow
    }
}

Pop-Location
