# Hillhorn: Fix native modules on Windows (Spectre libs not installed)
# Disables Spectre mitigation in binding.gyp, then rebuilds.
# Run after npm install if native modules fail with MSB8040.

$ErrorActionPreference = "Stop"
$base = if ($env:HILLHORN_ROOT) { $env:HILLHORN_ROOT } else { (Get-Item $PSScriptRoot).Parent.FullName }
$nm = "$base\vscode\node_modules"

$gypFiles = @(
    "$nm\@vscode\policy-watcher\binding.gyp",
    "$nm\@vscode\spdlog\binding.gyp",
    "$nm\@vscode\deviceid\binding.gyp",
    "$nm\@vscode\windows-registry\binding.gyp",
    "$nm\@vscode\windows-mutex\binding.gyp",
    "$nm\@vscode\windows-ca-certs\binding.gyp",
    "$nm\@vscode\windows-process-tree\binding.gyp",
    "$nm\@vscode\native-watchdog\binding.gyp",
    "$nm\@vscode\sqlite3\binding.gyp",
    "$nm\@vscode\sqlite3\deps\sqlite3.gyp",
    "$nm\node-pty\binding.gyp",
    "$nm\kerberos\binding.gyp",
    "$nm\native-keymap\binding.gyp",
    "$nm\native-is-elevated\binding.gyp",
    "$nm\windows-foreground-love\binding.gyp"
)

$patched = 0
foreach ($gyp in $gypFiles) {
    if (Test-Path $gyp) {
        $content = Get-Content $gyp -Raw -ErrorAction SilentlyContinue
        if ($content -and $content -match "SpectreMitigation.*Spectre") {
            $content = $content -replace "SpectreMitigation['\s:]*['\"]Spectre['\"]", 'SpectreMitigation": "false"'
            $content = $content -replace "SpectreMitigation['\s:]*['\"]Spectre['\"]", "SpectreMitigation': 'false'"
            $content = $content -replace "'SpectreMitigation':\s*'Spectre'", "'SpectreMitigation': 'false'"
            $content = $content -replace '"SpectreMitigation":\s*"Spectre"', '"SpectreMitigation": "false"'
            $content = $content -replace '\{\s*"SpectreMitigation":\s*"Spectre"\s*\}', '{"SpectreMitigation": "false"}'
            Set-Content $gyp $content -NoNewline
            $patched++
        }
    }
}
if ($patched -gt 0) { Write-Host "Patched $patched binding.gyp files" -ForegroundColor Green }

Write-Host "Rebuilding native modules..." -ForegroundColor Cyan
Push-Location "$base\vscode"
$packages = @(
    "@vscode/policy-watcher", "@vscode/spdlog", "@vscode/deviceid",
    "@vscode/windows-registry", "@vscode/windows-mutex", "@vscode/windows-ca-certs",
    "@vscode/windows-process-tree", "@vscode/native-watchdog", "@vscode/sqlite3",
    "node-pty", "kerberos", "native-keymap", "native-is-elevated", "windows-foreground-love"
)
foreach ($pkg in $packages) {
    if (Test-Path "$nm\$($pkg -replace '@vscode/','@vscode\')" -ErrorAction SilentlyContinue) {
        npm rebuild $pkg 2>&1 | Out-Null
    }
}
npm rebuild 2>&1
Pop-Location
Write-Host "Done." -ForegroundColor Green
