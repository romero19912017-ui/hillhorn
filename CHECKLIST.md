# Чек-лист готовности к сборке Hillhorn

**Корень проекта:** `C:\Hillhorn\`  
**Дата:** 2025-03-10

---

## 1. Системные требования

| Пункт | Статус | Примечания |
|-------|--------|------------|
| Node.js 18+ (рекомендуется 22) | | Проверить: `node -v` |
| Python 3.10+ | | Проверить: `python --version` |
| Git | | Проверить: `git --version` |
| Visual Studio Build Tools (для VS Code) | | Spectre-mitigated libs установлены |
| pnpm | | Для Moltbot: `pnpm -v` |
| Bash (Git Bash или WSL2) | | Для `pnpm build` в Moltbot |
| CUDA (опционально) | | Для torch GPU, FAISS GPU |

---

## 2. Наличие репозиториев и кода

| Пункт | Статус | Примечания |
|-------|--------|------------|
| Корень проекта C:\Hillhorn | | |
| nwf_jepa.py | | |
| deepseek_gateway.py | | |
| agents.py | | |
| nwf_memory_adapter.py | | |
| app.py | | |
| requirements.txt | | |
| .env.example | | |
| Папка moltbot\ | | Клон OpenClaw |
| Папка vscode\ | | Клон VS Code |
| Папка workspace\ | | OpenClaw workspace |
| Папка scripts\ | | start_all.ps1 и др. |
| config\ (если есть) | | |
| emblem.png | | Эмблема проекта |

---

## 3. Установка зависимостей

### Python

| Пункт | Статус | Примечания |
|-------|--------|------------|
| venv_hillhorn создан | | `python -m venv venv_hillhorn` |
| venv активирован | | `.\venv_hillhorn\Scripts\Activate.ps1` |
| pip install -r requirements.txt | | |
| nwf-core установлен | | `pip install "path\to\nwf-core[faiss]"` или аналог |
| torch, fastapi, uvicorn, httpx | | |
| watchdog | | Для nwf_memory_adapter --watch |
| Ключевые импорты работают | | `python -c "import nwf, torch, fastapi"` |

### Node.js

| Пункт | Статус | Примечания |
|-------|--------|------------|
| pnpm install в moltbot | | `cd moltbot && pnpm install` |
| pnpm build в moltbot | | Требует bash |
| npm install в vscode | | Проверить после Spectre: `cd vscode && npm install` |
| npm install -g openclaw (или @moltbot/cli) | | Глобальный CLI |

---

## 4. Конфигурационные файлы

| Пункт | Статус | Примечания |
|-------|--------|------------|
| .env создан из .env.example | | |
| DEEPSEEK_API_KEY указан | | Обязательно |
| DEEPSEEK_BASE_URL (опционально) | | По умолчанию api.deepseek.com |
| NWF_MEMORY_PATH | | data/deepseek_memory |
| NWF_MEMORY_ADAPTER_PATH | | data/nwf_opencloud |
| MOLTBOT_WORKSPACE | | C:\Hillhorn\workspace |
| config.yaml OpenClaw | | %USERPROFILE%\.config\openclaw\config.yaml |
| llm.provider: openai в config | | |
| llm.base_url: https://api.deepseek.com/v1 | | |
| llm.api_key в config | | |
| workspace: C:\Hillhorn\workspace в config | | |

---

## 5. Запуск сервисов по отдельности

| Пункт | Статус | Примечания |
|-------|--------|------------|
| DeepSeek Gateway запускается | | `uvicorn deepseek_gateway:app --port 8001` |
| GET /health возвращает 200 | | http://127.0.0.1:8001/health |
| NWF Memory Adapter --sync | | Без ошибок |
| NWF Memory Adapter --watch | | Запускается, Ctrl+C останавливает |
| moltbot gateway start | | |
| moltbot gateway status | | running |
| OpenClaw UI доступен | | http://127.0.0.1:18789/ |
| python app.py --demo --steps 100 | | Без ошибок |

---

## 6. Интеграционные тесты

| Пункт | Статус | Примечания |
|-------|--------|------------|
| POST /v1/agent/query (chat) | | `curl -X POST http://localhost:8001/v1/agent/query -H "Content-Type: application/json" -d "{\"agent_type\":\"chat\",\"prompt\":\"Hello\"}"` |
| Ответ содержит content, model_used | | |
| Логирование в NWF (memory_charges растёт) | | Повторный health после запроса |
| nwf_memory_adapter --search "query" | | Возвращает результаты (если есть данные) |
| sync + search | | После sync данные доступны в search |
| select_agent_from_memory | | `python -c "from agents import select_agent_from_memory; print(select_agent_from_memory('data/deepseek_memory','write code'))"` |

---

## 7. Форк VS Code

| Пункт | Статус | Примечания |
|-------|--------|------------|
| vscode\ склонирован | | |
| npm install выполнен | | Без MSB8040 или после установки Spectre libs |
| npm run compile | | |
| npx gulp watch-web (терминал 1) | | |
| npx gulp web (терминал 2) | | Редактор открывается в браузере |
| Ветка hillhorn-integration создана | | По необходимости |

---

## 8. Общие проверки

| Пункт | Статус | Примечания |
|-------|--------|------------|
| Нет блокирующих ошибок в логах Gateway | | |
| Нет блокирующих ошибок в логах Adapter | | |
| Нет блокирующих ошибок в логах OpenClaw | | moltbot logs |
| Тестовые данные для демо | | workspace с SOUL.md, USER.md, MEMORY.md или memory/*.md |
| Все три сервиса работают одновременно | | Gateway + Adapter --watch + OpenClaw gateway |

---

## 9. Легенда статусов

- **Да** — выполнено, проверено
- **Нет** — не выполнено или не работает
- **Частично** — частично выполнено или с ограничениями

---

## 10. Проверка сборки VS Code (после Spectre)

```powershell
.\scripts\check_vscode_build.ps1
```

Или вручную:
```powershell
cd C:\Hillhorn\vscode
npm install
npm run compile
```

---

## 11. Быстрый прогон (минимальный)

```powershell
# 1. Активация venv
cd C:\Hillhorn
.\venv_hillhorn\Scripts\Activate.ps1

# 2. Проверка импортов
python -c "import nwf, torch, fastapi; print('OK')"

# 3. JEPA демо
python app.py --demo --steps 50

# 4. Запуск Gateway (в отдельном терминале)
uvicorn deepseek_gateway:app --port 8001

# 5. Health
curl http://127.0.0.1:8001/health

# 6. Запрос (при наличии DEEPSEEK_API_KEY в .env)
curl -X POST http://localhost:8001/v1/agent/query -H "Content-Type: application/json" -d "{\"agent_type\":\"chat\",\"prompt\":\"Hi\",\"max_tokens\":50}"
```
