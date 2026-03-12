# Hillhorn: запуск компонентов
# Запускает по одному в новых окнах PowerShell

$base = "c:\Hillhorn"

# Терминал 1: DeepSeek Gateway
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd $base; .\venv_hillhorn\Scripts\Activate.ps1; uvicorn deepseek_gateway:app --reload --port 8001"

# Терминал 2: NWF Memory Adapter
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd $base; .\venv_hillhorn\Scripts\Activate.ps1; python nwf_memory_adapter.py --watch"

Write-Host "DeepSeek Gateway и NWF Adapter запущены."
Write-Host "Настройки (API ключ): http://127.0.0.1:8001/settings"
Write-Host "Проверка: http://127.0.0.1:8001/health"
Write-Host "OpenClaw: moltbot gateway start (в отдельном терминале)"
