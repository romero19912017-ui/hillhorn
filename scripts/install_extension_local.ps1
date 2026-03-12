# Hillhorn: Build and install extension into VS Code or Cursor

$ErrorActionPreference = "Stop"
$base = if ($env:HILLHORN_ROOT) { $env:HILLHORN_ROOT } else { (Get-Item $PSScriptRoot).Parent.FullName }

# Build first
& "$base\scripts\build_extension.ps1"

$extFolder = "$base\dist\hillhorn-chat"
$extName = "hillhorn.hillhorn-chat-0.1.0"

# Detect editor
$useCursor = $false
if ($args -contains "--cursor") { $useCursor = $true }
if (Get-Command cursor -ErrorAction SilentlyContinue) { $useCursor = $true }

$extDir = if ($useCursor) {
    "$env:USERPROFILE\.cursor\extensions\$extName"
} else {
    "$env:USERPROFILE\.vscode\extensions\$extName"
}

if (Test-Path $extDir) { Remove-Item $extDir -Recurse -Force }
Copy-Item $extFolder $extDir -Recurse -Force

Write-Host "`nInstalled to: $extDir" -ForegroundColor Green
Write-Host "Restart VS Code or Cursor to activate." -ForegroundColor Yellow
Write-Host "`nStart services: .\scripts\start_all.ps1" -ForegroundColor Gray
