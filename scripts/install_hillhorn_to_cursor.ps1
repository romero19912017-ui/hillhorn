# Hillhorn - установка в Cursor (расширение + проверка MCP)
# Запуск: .\scripts\install_hillhorn_to_cursor.ps1

$base = "c:\Hillhorn"
$cursorExt = "$env:USERPROFILE\.cursor\extensions"
$extName = "hillhorn-status"
$extSrc = "$base\extensions\$extName"
$extDst = "$cursorExt\$extName"

Write-Host "=== Hillhorn: установка в Cursor ===" -ForegroundColor Cyan

# 1. Расширение Hillhorn Status
if (Test-Path $extSrc) {
    New-Item -ItemType Directory -Force -Path $cursorExt | Out-Null
    if (Test-Path $extDst) {
        Remove-Item -Recurse -Force $extDst
    }
    Copy-Item -Recurse $extSrc $extDst
    Write-Host "[OK] Extension: $extName -> $extDst" -ForegroundColor Green
} else {
    Write-Host "[SKIP] Extension source not found: $extSrc" -ForegroundColor Yellow
}

# 2. MCP в глобальном конфиге (merge, сохраняем остальные серверы)
$mcpPath = "$env:USERPROFILE\.cursor\mcp.json"
$hillhornEntry = @{
    command = "$base\venv_hillhorn\Scripts\python.exe"
    type = "stdio"
    args = @("$base\hillhorn_mcp_server.py")
    cwd = $base
    env = @{
        HILLHORN_GATEWAY_URL = "http://localhost:8001"
        HILLHORN_PROJECT_ID = $base
        PYTHONIOENCODING = "utf-8"
    }
}

$servers = @{}
if (Test-Path $mcpPath) {
    try {
        $raw = Get-Content $mcpPath -Raw -Encoding UTF8
        $cfg = $raw | ConvertFrom-Json
        if ($cfg.mcpServers) {
            $cfg.mcpServers.PSObject.Properties | ForEach-Object { $servers[$_.Name] = $_.Value }
        }
    } catch { }
}
$servers["hillhorn"] = $hillhornEntry
$out = @{ mcpServers = $servers }
$out | ConvertTo-Json -Depth 10 | Set-Content $mcpPath -Encoding UTF8
Write-Host "[OK] MCP: hillhorn in $mcpPath" -ForegroundColor Green

# 3. Startup (опционально)
$addStartup = $args -contains "-Startup"
if ($addStartup) {
    & "$base\scripts\add_to_windows_startup.ps1"
}

Write-Host ""
Write-Host "Done. Перезапусти Cursor." -ForegroundColor Cyan
Write-Host "Extension: Hillhorn Status (status bar)"
Write-Host "MCP: hillhorn (global)"
Write-Host "Auto-start: .\scripts\start_all_background.ps1 (or -Startup for Windows Startup)"
