# Add Hillhorn to Windows Startup - starts when user logs in
$startup = [Environment]::GetFolderPath("Startup")
$shortcut = Join-Path $startup "Hillhorn.vbs"
$script = "c:\Hillhorn\scripts\start_all_background.ps1"
$vbs = @"
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File $script", 0, False
"@
[IO.File]::WriteAllText($shortcut, $vbs)
Write-Host "Added to Startup: $shortcut"
Write-Host "Hillhorn will start when you log in."
