# Hillhorn — как работает система после сборки

## Готовность к сборке

| Компонент | Статус | Примечание |
|-----------|--------|------------|
| Python-ядро (JEPA, Gateway, агенты, Adapter) | Готово | Код написан и проверен |
| Скрипт сборки `scripts\build.ps1` | Готово | Проверяет окружение, venv, vscode |
| OpenClaw/Moltbot | Собран | pnpm build выполнен |
| VS Code | Зависит от Spectre | npm install + compile после Spectre libs |
| .env | Создастся при сборке | Или ввести ключ в http://127.0.0.1:8001/settings |
| nwf-core | Внешняя зависимость | pip install из локального пути |

**Вывод:** Проект готов к сборке. Запустите `.\scripts\build.ps1`. После сборки — ввести API ключ в http://127.0.0.1:8001/settings (после запуска Gateway) и выполнить `moltbot onboard`.

---

## Как работает система после сборки

### 1. Запуск (порядок)

```
Терминал 1: DeepSeek Gateway      (порт 8001)
Терминал 2: NWF Memory Adapter    (--watch)
Терминал 3: OpenClaw Gateway      (порт 18789)
Терминал 4+5: VS Code             (gulp watch-web + gulp web)
```

**Одна команда для Python-сервисов:**
```powershell
.\scripts\start_all.ps1
```
Запустит Gateway и Adapter. OpenClaw — отдельно: `moltbot gateway start`.

### 2. Поток данных: пользовательский запрос

```
1. Пользователь пишет в чат (OpenClaw UI или будущее расширение VS Code)
         │
2. OpenClaw Gateway (18789) принимает сообщение
         │
3. OpenClaw вызывает LLM:
   • Если настроен base_url на localhost:8001 — идёт в наш DeepSeek Gateway
   • Иначе — напрямую в DeepSeek API
         │
4. DeepSeek Gateway (8001):
   • Определяет agent_type (chat/coder/planner/reviewer)
   • Выбирает модель: deepseek-chat, deepseek-coder-v2, deepseek-reasoner
   • Отправляет запрос в api.deepseek.com
   • Логирует вызов в NWF-поле (data/deepseek_memory)
         │
5. Ответ возвращается пользователю
```

### 3. Память (NWF)

**Два источника зарядов:**

| Источник | Путь | Как наполняется |
|----------|------|-----------------|
| Вызовы DeepSeek | data/deepseek_memory | Gateway логирует каждый запрос |
| Markdown OpenClaw | data/nwf_opencloud | Adapter синхронизирует SOUL.md, USER.md, MEMORY.md, memory/*.md |

**Выбор агента:** `select_agent_from_memory(memory_path, user_request)` — по похожим прошлым запросам в NWF выбирает coder/planner/reviewer/chat. Пока вызывается вручную; автоматическая интеграция — следующий шаг.

### 4. Использование агентов из кода

```python
from agents import CoderAgent, PlannerAgent, select_agent_from_memory

# Прямой вызов
coder = CoderAgent()
code = await coder.generate_function("сортировка списка", language="python")

# Или выбор по памяти
agent_type = select_agent_from_memory("data/deepseek_memory", "спроектируй архитектуру")
# agent_type = "planner"
```

### 5. Эндпоинты

| URL | Метод | Назначение |
|-----|-------|------------|
| http://127.0.0.1:8001/health | GET | Проверка работы Gateway |
| http://127.0.0.1:8001/v1/agent/query | POST | Запрос к агенту (JSON: agent_type, prompt, context, temperature, max_tokens) |
| http://127.0.0.1:18789/ | — | OpenClaw Web UI |

### 6. Файлы и папки после сборки

```
C:\Hillhorn\
├── data\
│   ├── deepseek_memory\    # Заряды от вызовов Gateway
│   └── nwf_opencloud\      # Заряды из workspace OpenClaw
├── workspace\              # OpenClaw workspace (SOUL.md, USER.md, MEMORY.md)
├── .env                    # DEEPSEEK_API_KEY и др.
└── venv_hillhorn\          # Python-окружение
```

### 7. Типовой рабочий сценарий

1. Запустить `.\scripts\start_all.ps1` и `moltbot gateway start`.
2. Открыть http://127.0.0.1:18789/ (OpenClaw UI).
3. Написать запрос в чат.
4. OpenClaw отправит его в DeepSeek (через наш Gateway, если настроен base_url).
5. Gateway залогирует вызов в NWF.
6. NWF Adapter в фоне синхронизирует workspace → data/nwf_opencloud.
7. При следующем запросе `select_agent_from_memory` может использовать накопленную память.

### 8. Что пока не работает автоматически

- **Function calling** — Planner не может сам вызывать search_memory, call_agent и т.п.
- **Автовыбор агента** — `select_agent_from_memory` не вызывается из OpenClaw.
- **Расширение VS Code** — чат-панель в редакторе ещё не реализована.
- **Прямая маршрутизация OpenClaw → наш Gateway** — нужно прописать base_url в config.yaml.
