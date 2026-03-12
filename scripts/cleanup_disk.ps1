# Hillhorn: очистка диска от временных файлов
# Запуск: .\scripts\cleanup_disk.ps1

$ErrorActionPreference = "Continue"

Write-Host "=== Очистка диска ===" -ForegroundColor Cyan

# 1. Temp
Write-Host "1. Temp..." -ForegroundColor Yellow
$tempCount = (Get-ChildItem $env:TEMP -ErrorAction SilentlyContinue | Measure-Object).Count
Remove-Item "$env:TEMP\*" -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "   Temp: очищено" -ForegroundColor Green

# 2. pip cache
Write-Host "2. pip cache..." -ForegroundColor Yellow
pip cache purge 2>$null
Write-Host "   pip: очищено" -ForegroundColor Green

# 3. Python __pycache__
Write-Host "3. __pycache__..." -ForegroundColor Yellow
$base = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Get-ChildItem $base -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "   __pycache__: очищено" -ForegroundColor Green

# 4. Windows Temp (если есть права)
if (Test-Path "C:\Windows\Temp") {
    Write-Host "4. C:\Windows\Temp (запусти от админа для полной очистки)..." -ForegroundColor Gray
}

Write-Host ""
Write-Host "Готово. Запускай раз в неделю или при нехватке места." -ForegroundColor Cyan
