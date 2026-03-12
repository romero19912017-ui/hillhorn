# Hillhorn: проверка DeepSeek API
# Запуск: .\scripts\test_deepseek_api.ps1

$base = "c:\Hillhorn"
Set-Location $base

if (-not (Test-Path ".env")) {
    Write-Host "[FAIL] .env не найден. Скопируйте .env.example в .env и укажите DEEPSEEK_API_KEY" -ForegroundColor Red
    exit 1
}

& .\venv_hillhorn\Scripts\Activate.ps1

$code = @'
import os
from dotenv import load_dotenv
load_dotenv()
key = os.getenv("DEEPSEEK_API_KEY", "")
if not key or key == "sk-your-key-here":
    print("ERROR: DEEPSEEK_API_KEY не задан в .env")
    exit(1)
import httpx
r = httpx.post(
    "https://api.deepseek.com/v1/chat/completions",
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    json={"model": "deepseek-chat", "messages": [{"role": "user", "content": "Say OK"}], "max_tokens": 5},
    timeout=30
)
if r.status_code == 200:
    print("OK:", r.json()["choices"][0]["message"]["content"].strip())
else:
    print("FAIL:", r.status_code, r.text[:200])
    exit(1)
'@

python -c $code
