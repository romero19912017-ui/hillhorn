# Hillhorn — план установки и запуска

![Hillhorn](emblem.png)

## 0. Структура

```
C:\Hillhorn\
├── nwf_jepa.py, agents.py, app.py, deepseek_gateway.py, nwf_memory_adapter.py
├── venv_hillhorn\          # Python venv
├── workspace\              # OpenClaw workspace
├── moltbot\                # OpenClaw
├── openclaw\               # OpenClaw (зеркало)
├── vscode\                 # VS Code исходники
├── jepa-reference\         # JEPA
├── jepa-wms\               # JEPA World Models (Facebook)
└── nwf-core\               # NWF-core исходники
```

---

## 1. Python-окружение

```powershell
cd C:\Hillhorn
python -m venv venv_hillhorn
.\venv_hillhorn\Scripts\activate
pip install -r requirements.txt
```

Убедитесь, что в requirements.txt есть: torch, fastapi, uvicorn, httpx, python-dotenv, nwf-core[faiss], watchdog.

---

## 2. OpenClaw (Moltbot)

### 2.1. Сборка из клона
```powershell
cd C:\Hillhorn\moltbot
pnpm install
pnpm build   # требует bash (WSL2 или Git Bash) - OpenClaw рекомендует WSL2 на Windows
```

### 2.2. Глобальная установка CLI
```powershell
npm install -g @moltbot/cli
# или openclaw
npm install -g openclaw
```

### 2.3. Onboarding
```powershell
moltbot onboard
# или openclaw onboard
```

При onboard:
- Provider: Skip (настроим DeepSeek вручную)
- Channel: Skip
- Workspace: C:\Hillhorn\workspace

### 2.4. Конфиг DeepSeek
Создать `~/.config/openclaw/config.yaml`:
```yaml
llm:
  provider: openai
  api_key: "sk-xxxxxxxx"  # ваш DeepSeek ключ
  base_url: "https://api.deepseek.com/v1"
  model: deepseek-chat
workspace: C:\Hillhorn\workspace
```

---

## 3. VS Code (форк)

VS Code перешёл на npm (yarn не поддерживается):

```powershell
cd C:\Hillhorn\vscode
npm install
npm run compile
# yarn watch + yarn web заменены на:
npx gulp watch-web   # в одном терминале
npx gulp web         # в другом
```

Если вносите изменения — своя ветка:
```powershell
git remote set-url origin https://github.com/ВАШ_АККАУНТ/vscode.git
git checkout -b hillhorn-integration
```

---

## 4. .env и workspace

Скопировать `.env.example` в `.env`, заполнить ключи.

**MOLTBOT_WORKSPACE** должен указывать на ту же папку, что и в OpenClaw: `C:\Hillhorn\workspace`

---

## 5. Порядок запуска

### Терминал 1: OpenClaw Gateway
```powershell
moltbot gateway start
# или openclaw gateway start
```
Проверка: `moltbot gateway status`

### Терминал 2: NWF Memory Adapter
```powershell
cd C:\Hillhorn
.\venv_hillhorn\Scripts\activate
python nwf_memory_adapter.py --watch
```

### Терминал 3: DeepSeek Gateway
```powershell
cd C:\Hillhorn
.\venv_hillhorn\Scripts\activate
uvicorn deepseek_gateway:app --reload --port 8001
```

### Терминал 4 (опционально): JEPA demo
```powershell
.\venv_hillhorn\Scripts\activate
python app.py --demo --steps 100
```

---

## 6. Проверка

- DeepSeek health: http://127.0.0.1:8001/health
- OpenClaw UI: http://127.0.0.1:18789/
- Поиск в NWF: `python nwf_memory_adapter.py --search "тестовый запрос" -k 5`

---

## 7. Скрипт запуска

```powershell
.\scripts\start_all.ps1   # DeepSeek Gateway + NWF Adapter в новых окнах
```

## 8. Ошибки и ограничения

- **openclaw/moltbot** — переустановить CLI, перезапустить терминал
- **watchdog** — `pip install watchdog`
- **Node < 22** — обновить Node.js
- **nwf-core** — `pip install "C:\nwf\libraries\nwf-core[faiss]"`
- **Moltbot pnpm build** — требует bash (WSL2 или Git Bash), OpenClaw рекомендует WSL2
- **VS Code npm install** — требует Visual Studio Build Tools с Spectre-mitigated libs; сборка сложная на Windows
- Логи OpenClaw: `moltbot logs`
