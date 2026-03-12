# Hillhorn

Интеллектуальная память и AI-помощник для Cursor с DeepSeek MCP Gateway. Использует теорию нейровесовых полей (NWF) для семантического хранения контекста проекта.

**Автор теории NWF: Роман Белоусов.** Статья: [https://doi.org/10.24108/preprints-3113697](https://doi.org/10.24108/preprints-3113697)

## Содержание

- [Описание](#описание)
- [Возможности](#возможности)
- [MCP-инструменты](#mcp-инструменты)
- [Архитектура](#архитектура)
- [Установка](#установка)
- [Конфигурация](#конфигурация)
- [Скрипты](#скрипты)
- [Структура проекта](#структура-проекта)
- [Требования](#требования)
- [Благодарности](#благодарности)
- [Лицензия](#лицензия)

---

## Описание

Hillhorn — это MCP-сервер (Model Context Protocol), который расширяет возможности Cursor:

1. **Семантическая память** — сохраняет факты, решения и контекст диалогов в нейровесовом поле (NWF). Поиск идёт по смыслу, а не по ключевым словам.

2. **Интеграция с DeepSeek** — единая точка входа (Gateway) для агентов: planner (планировщик), coder (код), reviewer (ревью), chat (общение), architect, documenter.

3. **Контекст проекта** — автоматическое чтение SOUL.md, USER.md, MEMORY.md и поиск релевантных записей в памяти при каждом запросе.

---

## Возможности

| Компонент | Описание |
|-----------|----------|
| **NWF Memory** | Семантическое хранилище с эмбеддингами. Добавление и поиск выполняются синхронно. |
| **DeepSeek Gateway** | FastAPI-сервер на порту 8001. Маршрутизирует запросы к агентам DeepSeek. |
| **Retry** | Автоматический повтор при ConnectError (до 2 попыток, задержка 2 сек). |
| **Учёт API** | Запись использования токенов в `data/deepseek_usage.json`. Скрипт `cost_report.ps1` для отчётов. |
| **Диагностика** | `scripts/diagnose.ps1` — проверка Gateway, портов, активности. |
| **История вызовов** | Лог в `data/hillhorn_calls.jsonl`. Команда VS Code «Hillhorn: Show History». |
| **Расширение VS Code** | Статус-бар, счётчик вызовов, быстрый доступ к истории. |

---

## MCP-инструменты

Доступны агенту Cursor через MCP. Вызывать по имени.

### hillhorn_get_context

Получить контекст проекта: SOUL, USER, MEMORY и результаты семантического поиска в памяти. Рекомендуется вызывать в начале сессии.

| Параметр | Описание |
|----------|----------|
| `project_id` | Путь к корню проекта (по умолчанию — корень Hillhorn) |
| `include_memory_search` | Включить поиск в памяти (по умолчанию true) |
| `memory_top_k` | Сколько результатов памяти вернуть (по умолчанию 5) |

### hillhorn_search

Семантический поиск в памяти Hillhorn.

| Параметр | Описание |
|----------|----------|
| `query` | Текст запроса |
| `project_id` | Путь к проекту для фильтрации |
| `top_k` | Количество результатов (по умолчанию 10) |
| `kind_filter` | Фильтр по типу: doc, code, conversation |
| `recency_boost` | Приоритет недавним записям |

### hillhorn_add_turn

Добавить факт или реплику в память. Использовать после важных решений, изучения кода, обсуждений.

| Параметр | Описание |
|----------|----------|
| `text` | Текст для сохранения |
| `project_id` | Путь к проекту |
| `role` | system / assistant / user |
| `kind` | doc, code, conversation |
| `file_path` | Опционально — путь к файлу |

### hillhorn_index_file

Проиндексировать содержимое файла для поиска. Использовать для критически важных файлов (README, конфиги, ключевые модули).

| Параметр | Описание |
|----------|----------|
| `file_path` | Путь к файлу |
| `content` | Содержимое файла |
| `project_id` | Путь к проекту |

### hillhorn_consult_agent

Консультация агента DeepSeek: planner, coder, reviewer, chat, architect, documenter.

| Параметр | Описание |
|----------|----------|
| `agent_type` | planner, coder, reviewer, chat, architect, documenter |
| `prompt` | Текст запроса |
| `project_id` | Путь к проекту |
| `context` | Дополнительные сообщения (role, content) |
| `code_to_review` | Код для ревью (опционально) |
| `extra_context` | Список строк дополнительного контекста |
| `max_tokens` | Макс. токенов ответа (по умолчанию 1200) |

### hillhorn_consult_with_memory

То же, что hillhorn_consult_agent, но перед вызовом агента выполняется поиск в памяти и контекст добавляется в запрос. Экономит API и улучшает качество ответов.

| Параметр | Описание |
|----------|----------|
| `memory_query` | Запрос для поиска в памяти (по умолчанию «общая информация о проекте») |
| `memory_top_k` | Сколько записей памяти включить (по умолчанию 3) |

---

## Архитектура

```
Cursor (IDE)
    |
    v
MCP (Hillhorn) <---> tools.py, nwf_memory_adapter.py
    |                         |
    v                         v
DeepSeek Gateway (FastAPI:8001)
    |                         |
    v                         v
DeepSeek API              NWF Field (data/deepseek_memory)
```

- **hillhorn_mcp_server.py** — точка входа MCP, регистрирует инструменты и обрабатывает вызовы.
- **tools.py** — search_memory, add_to_memory, read_file, write_file, execute_command, call_agent и др.
- **nwf_memory_adapter.py** — синхронизация Markdown-памяти (SOUL, USER, MEMORY) с NWF-полем.
- **deepseek_gateway.py** — Gateway, эндпоинты `/v1/agent/query`, `/v1/memory/*`, страница настроек.

---

## Установка

1. Клонируйте репозиторий или распакуйте архив.
2. Создайте виртуальное окружение и установите зависимости:

```powershell
cd c:\Hillhorn
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

3. Скопируйте `.env.example` в `.env` и укажите `DEEPSEEK_API_KEY`.
4. Установите Hillhorn в Cursor:

```powershell
.\scripts\install_hillhorn_to_cursor.ps1
```

5. Запустите Gateway и NWF Adapter:

```powershell
.\scripts\start_all_background.ps1
```

6. Проверьте:

```powershell
.\scripts\diagnose.ps1
```

---

## Конфигурация

Переменные окружения (файл `.env` или системные):

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `DEEPSEEK_API_KEY` | API-ключ DeepSeek | — |
| `DEEPSEEK_BASE_URL` | URL API DeepSeek | https://api.deepseek.com/v1 |
| `HILLHORN_GATEWAY_URL` | URL Gateway | http://localhost:8001 |
| `HILLHORN_PROJECT_ID` | Путь к проекту по умолчанию | Корень Hillhorn |
| `HILLHORN_DATA_ROOT` | Корень хранилища (на диске C) | C:/hillhorn_data |
| `NWF_MEMORY_PATH` | Путь к NWF-памяти | {DATA_ROOT}/deepseek_memory |
| `NWF_MEMORY_ADAPTER_PATH` | Путь к адаптеру OpenCloud | {DATA_ROOT}/nwf_opencloud |
| `USE_SEMANTIC_EMBEDDINGS` | Использовать sentence-transformers | 0 |
| `NWF_PRUNE_THRESHOLD` | Порог для автоочистки памяти | 12000 |

---

## Скрипты

| Скрипт | Описание |
|--------|----------|
| `install_hillhorn_to_cursor.ps1` | Добавляет Hillhorn в конфиг MCP Cursor |
| `start_all_background.ps1` | Запускает Gateway (8001) и NWF Adapter в фоне |
| `diagnose.ps1` | Проверяет Gateway, порты, логи |
| `cost_report.ps1 day` | Отчёт по использованию токенов за день |
| `run_hillhorn_snake_test.py` | Тест MCP-сервера |

---

## Структура проекта

```
c:\Hillhorn\
  hillhorn_mcp_server.py   # MCP-сервер
  tools.py                 # Инструменты (память, файлы, команды)
  deepseek_gateway.py      # FastAPI Gateway
  nwf_memory_adapter.py    # Адаптер NWF для OpenCloud
  embeddings.py            # Эмбеддинги (hash / sentence-transformers)
  agents.py                # Классы агентов (CoderAgent, PlannerAgent и др.)
  code_indexer.py          # Индексация кода для семантического поиска
  nwf_memory_utils.py      # Очистка, экспорт, импорт NWF-памяти
  scripts/                 # PowerShell и Python скрипты

C:\hillhorn_data\          # Хранилище (вне проекта, на диске C)
  deepseek_memory/         # NWF-память (запросы к DeepSeek)
  nwf_opencloud/           # NWF-память из SOUL/USER/MEMORY
  code_index/              # Индекс кода
  hillhorn_calls.jsonl     # Лог вызовов MCP
  hillhorn_activity.json   # Последняя активность
  deepseek_usage.json      # Использование токенов
```

---

## Требования

- Python 3.10+
- DEEPSEEK_API_KEY в `.env`
- Cursor с настроенным MCP (Hillhorn)

---

## Благодарности

NWF (Neuro-Weight Fields) основана на теории нейровесовых полей. **Автор теории: Роман Белоусов.**  
Статья: [https://doi.org/10.24108/preprints-3113697](https://doi.org/10.24108/preprints-3113697)

---

## Лицензия

MIT — см. [LICENSE](LICENSE)
