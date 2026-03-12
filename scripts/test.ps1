# Hillhorn: полный тест всех компонентов
# Запуск: .\scripts\test.ps1
# Или: powershell -ExecutionPolicy Bypass -File c:\Hillhorn\scripts\test.ps1

$ErrorActionPreference = "Continue"
$base = "c:\Hillhorn"
Set-Location $base

function Log { param($msg, $color = "White") Write-Host $msg -ForegroundColor $color }
function Ok { param($msg) Log "  [OK] $msg" Green }
function Warn { param($msg) Log "  [WARN] $msg" Yellow }
function Fail { param($msg) Log "  [FAIL] $msg" Red }

$failed = 0

Log "`n=== Hillhorn: тест компонентов ===" Cyan
Log ""

# 1. Python imports
Log "[1/6] Python модули..." Cyan
& .\venv_hillhorn\Scripts\Activate.ps1
$out = python -c @"
from nwf import Charge, Field
from embeddings import get_embedding
from tools import TOOL_MAP
from agents import select_agent_from_memory
from nwf_memory_utils import prune_field
from code_indexer import CodeIndexer
print('OK')
"@ 2>&1
if ($LASTEXITCODE -eq 0) { Ok "nwf, embeddings, tools, agents, nwf_memory_utils, code_indexer" } else { Fail $out; $failed++ }
Log ""

# 2. Gateway import
Log "[2/6] DeepSeek Gateway..." Cyan
$out = python -c "import deepseek_gateway; print('OK')" 2>&1
if ($LASTEXITCODE -eq 0) { Ok "deepseek_gateway" } else { Fail $out; $failed++ }
Log ""

# 3. Gateway startup + health
Log "[3/6] Gateway /health..." Cyan
$proc = Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "deepseek_gateway:app", "--port", "8001" -PassThru -WindowStyle Hidden -WorkingDirectory $base
Start-Sleep -Seconds 6
try {
    $r = Invoke-RestMethod -Uri "http://127.0.0.1:8001/health" -TimeoutSec 5
    if ($r.status -eq "ok") { Ok "Gateway отвечает, memory_charges=$($r.memory_charges)" }
    else { Fail "status != ok"; $failed++ }
} catch {
    Fail "Gateway не отвечает: $_"; $failed++
} finally {
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
}
Log ""

# 4. Agent query (optional, needs API key)
Log "[4/6] Agent /v1/agent/query..." Cyan
$proc = Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "deepseek_gateway:app", "--port", "8001" -PassThru -WindowStyle Hidden -WorkingDirectory $base
Start-Sleep -Seconds 6
try {
    $body = '{"agent_type":"chat","prompt":"Say hi in one word","max_tokens":10}'
    $r = Invoke-RestMethod -Uri "http://127.0.0.1:8001/v1/agent/query" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 30
    if ($r.content) { Ok "Ответ получен: $($r.content.Substring(0, [Math]::Min(40, $r.content.Length)))..." }
    else { Warn "Пустой ответ (API ключ?)" }
} catch {
    if ($_.Exception.Message -match "401|403|500|429") { Warn "API ключ не настроен или ошибка DeepSeek: $_" }
    else { Fail $_.Exception.Message; $failed++ }
} finally {
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
}
Log ""

# 5. VS Code extension
Log "[5/6] vscode-ext-hillhorn compile..." Cyan
Set-Location "$base\vscode-ext-hillhorn"
$out = npm run compile 2>&1
if ($LASTEXITCODE -eq 0) { Ok "расширение скомпилировано" }
else { Fail "npm run compile: $out"; $failed++ }
Set-Location $base
Log ""

# 6. Code indexer
Log "[6/6] CodeIndexer..." Cyan
$out = python -c @"
from pathlib import Path
from code_indexer import CodeIndexer
p = Path('workspace')
if not p.exists(): p.mkdir()
ci = CodeIndexer(p)
n = ci.index_workspace()
print(n)
"@ 2>&1
if ($LASTEXITCODE -eq 0) { Ok "index_workspace: $out блоков" }
else { Warn "indexer: $out" }
Log ""

# Summary
Log "=== Итог ===" Cyan
if ($failed -gt 0) {
    Log "Провалено: $failed тест(ов)" Red
    exit 1
} else {
    Log "Все тесты пройдены" Green
    Log ""
    Log "Запуск: .\scripts\start_all.ps1" Yellow
    Log "Проверка: http://127.0.0.1:8001/health" Yellow
    exit 0
}
