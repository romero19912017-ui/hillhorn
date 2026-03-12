# Hillhorn: Добавить в автозагрузку Windows
# Запускает Gateway + NWF + Cursor при входе в систему

# Requires admin for Task Scheduler, or use Startup folder (no admin)
$base = if ($env:HILLHORN_ROOT) { $env:HILLHORN_ROOT } else { (Get-Item $PSScriptRoot).Parent.FullName }
$scriptPath = "$base\scripts\start_hillhorn.ps1"
$startupFolder = [Environment]::GetFolderPath("Startup")

Write-Host "`n=== Hillhorn Autostart ===" -ForegroundColor Cyan

# Create shortcut in Startup folder (simple, no admin)
$shortcutPath = "$startupFolder\Hillhorn.lnk"
$WshShell = New-Object -ComObject WScript.Shell
$shortcut = $WshShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "powershell.exe"
$shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$scriptPath`""
$shortcut.WorkingDirectory = $base
$shortcut.Description = "Hillhorn: Gateway + NWF + Cursor"
$shortcut.Save()
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($WshShell) | Out-Null

Write-Host "Shortcut: $shortcutPath" -ForegroundColor Green
Write-Host "Will run at next Windows login." -ForegroundColor Gray
Write-Host "`nTo remove: delete $shortcutPath" -ForegroundColor Gray
