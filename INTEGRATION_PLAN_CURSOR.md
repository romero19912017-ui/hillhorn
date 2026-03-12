# Hillhorn — План интеграции в Cursor для помощи агентам

**Цель:** Интегрировать Hillhorn в Cursor так, чтобы агенты Cursor могли совещаться с агентами Hillhorn (Planner, Coder, Reviewer и др.) для более эффективного решения задач. Hillhorn может стать заменой или дополнением к NWF-расширению.

---

## 1. Текущее состояние

### 1.1 NWF Framework (расширение nwf.nwf-framework)

| Инструмент | Назначение |
|------------|------------|
| `nwf_search` | Семантический поиск в памяти проекта |
| `nwf_add_turn` | Добавление диалога/факта в память |
| `nwf_index_file` | Индексация файла в память |

**Ограничения:** Только память + поиск. Нет консультаций с агентами, нет планирования, code review, специализированных моделей.

### 1.2 Hillhorn

| Компонент | Возможности |
|-----------|-------------|
| **DeepSeek Gateway** | API `/v1/agent/query`, agents: coder, planner, reviewer, chat, architect, documenter |
| **Tools** | search_memory, add_to_memory, read_file, write_file, execute_command, call_agent, search_code, git_* |
| **NWF память** | data/deepseek_memory (логи запросов), data/nwf_opencloud (workspace markdown) |
| **Hillhorn Chat** | Расширение VS Code/Cursor — webview чат к Gateway |

**Преимущества:** Специализированные агенты (reasoner для planner, coder-v2 для кода), function calling, единая память.

---

## 2. Концепция «совещания» агентов

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Cursor Agent (встроенный)                                               │
│  - Получает задачу от пользователя                                       │
│  - Имеет свои MCP: read_file, grep, terminal и т.д.                      │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               │ Консультация (при необходимости)
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Hillhorn MCP Tools (новый слой)                                         │
│  - hillhorn_consult_planner  → план по задаче                            │
│  - hillhorn_consult_coder    → код/рефакторинг                           │
│  - hillhorn_consult_reviewer → code review                               │
│  - hillhorn_search_memory    → поиск в NWF (аналог nwf_search)           │
│  - hillhorn_add_memory       → сохранить в память (аналог nwf_add_turn)  │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  DeepSeek Gateway (localhost:8001)                                       │
│  - /v1/agent/query                                                       │
│  - NWF memory, tools (search_memory, read_file, ...)                     │
└─────────────────────────────────────────────────────────────────────────┘
```

**Сценарий:** Cursor Agent получает задачу «рефакторинг модуля auth». Вместо того чтобы сразу писать код, он:
1. Вызывает `hillhorn_consult_planner` → получает пошаговый план.
2. При необходимости вызывает `hillhorn_search_memory` → находит похожие прошлые задачи.
3. Пишет код, используя свои MCP (read_file, edit).
4. Вызывает `hillhorn_consult_reviewer` → получает замечания.
5. Вызывает `hillhorn_add_memory` → сохраняет результат для будущего контекста.

---

## 3. Детальный план интеграции

### Фаза 1: Hillhorn MCP Server

**Цель:** Expose Hillhorn как MCP-сервер, который Cursor подключает наравне с nwf-memory.

| Шаг | Задача | Оценка |
|-----|--------|--------|
| 1.1 | Создать `hillhorn_mcp_server.py` — MCP сервер на базе FastMCP или stdio | 4–6 ч |
| 1.2 | Реализовать инструменты: consult_planner, consult_coder, consult_reviewer, consult_chat | 2–3 ч |
| 1.3 | Реализовать: search_memory, add_to_memory (обёртки над Gateway/tools) | 2 ч |
| 1.4 | Опционально: index_file (если нужна совместимость с NWF) | 2 ч |
| 1.5 | Конфигурация: gateway_url, workspace_path через env/settings | 1 ч |
| 1.6 | Упаковать как npm-пакет или Python-скрипт для Cursor MCP | 2 ч |

**Структура MCP-инструментов:**

```
hillhorn_consult_agent(agent_type, prompt, context?)
  → POST /v1/agent/query
  → Возвращает content, reasoning?, model_used

hillhorn_search_memory(query, top_k?, workspace_id?)
  → Вызов tools.search_memory через Gateway или напрямую
  → Возвращает [{text, agent_type, success}, ...]

hillhorn_add_memory(text, kind?, role?)
  → Вызов tools.add_to_memory или логирование в NWF
  → Возвращает status

hillhorn_index_file(file_path?, content?)  // опционально
  → Семантическая индексация в NWF
```

### Фаза 2: Cursor Rules и конфигурация

| Шаг | Задача | Оценка |
|-----|--------|--------|
| 2.1 | Создать `.cursor/rules/hillhorn.mdc` — когда и как вызывать Hillhorn | 1–2 ч |
| 2.2 | Обновить `.cursorrules` — приоритет Hillhorn vs встроенные возможности | 0.5 ч |
| 2.3 | Документация: настройка MCP в Cursor, добавление hillhorn-mcp | 1 ч |

**Пример правил (hillhorn.mdc):**

```markdown
# Hillhorn Consultation Rules

## Когда вызывать hillhorn_consult_planner
- Задача сложная (много шагов, неочевидная архитектура)
- Нужно разбить на подзадачи
- Перед началом кодирования при неясном scope

## Когда вызывать hillhorn_consult_reviewer
- После написания/изменения кода
- Перед коммитом (по желанию)
- При рефакторинге

## Когда вызывать hillhorn_search_memory
- Перед чтением файлов (аналог nwf_search)
- Для поиска похожих решений
- При повторяющихся задачах

## Когда вызывать hillhorn_add_memory
- После важных решений
- После решения проблемы
- После изучения кода (kind=code)
```

### Фаза 3: Совместимость с NWF extension

**Вариант A — Hillhorn как замена NWF**

| Шаг | Задача |
|-----|--------|
| 3.1 | Обеспечить семантическую совместимость: hillhorn_search_memory ≈ nwf_search по контракту |
| 3.2 | hillhorn_add_memory поддерживает kind, role как nwf_add_turn |
| 3.3 | Использовать одно NWF-поле (или связать nwf_opencloud + deepseek_memory) |
| 3.4 | Документация: «Отключите nwf.nwf-framework, используйте hillhorn-mcp» |

**Вариант B — Hillhorn + NWF работают вместе**

| Шаг | Задача |
|-----|--------|
| 3.1 | NWF — для workspace/проектной памяти (SOUL, USER, MEMORY) |
| 3.2 | Hillhorn — для консультаций агентов + memory API-вызовов |
| 3.3 | Правила: nwf_search для проектного контекста, hillhorn_search_memory для истории запросов |
| 3.4 | Синхронизация: NWF Adapter пишет в nwf_opencloud, Gateway — в deepseek_memory |

### Фаза 4: Расширение Hillhorn Chat

| Шаг | Задача | Оценка |
|-----|--------|--------|
| 4.1 | Добавить в панель Chat кнопку «Поделиться с Cursor» (копирует ответ в буфер/чат) | 1 ч |
| 4.2 | Контекст из редактора: передавать открытые файлы, выделение в prompt | 2 ч |
| 4.3 | Настройка: использовать ли Hillhorn MCP для агентов Cursor (вкл/выкл) | 0.5 ч |

### Фаза 5: Дополнительные улучшения

| Задача | Описание |
|--------|----------|
| Единый workspace_path | Cursor workspace path → workspace_path в Gateway, чтобы tools работали в нужной папке |
| Auto-agent в консультациях | При consult без указания agent_type — select_agent_from_memory |
| Стриминг | hillhorn_consult_agent с stream=true для длинных ответов |
| Логирование | Все вызовы Hillhorn MCP логировать в NWF для аналитики |

---

## 4. Технические детали

### 4.1 MCP Server (Python)

Рекомендуемый стек: **FastMCP** (или MCP SDK для Python).

```python
# Псевдокод
from mcp import FastMCP
import httpx

mcp = FastMCP("hillhorn", url="http://localhost:8001")

@mcp.tool()
async def hillhorn_consult_agent(
    agent_type: str,  # planner | coder | reviewer | chat | architect | documenter
    prompt: str,
    context: list[dict] | None = None,
) -> str:
    r = await httpx.post(
        f"{mcp.url}/v1/agent/query",
        json={"agent_type": agent_type, "prompt": prompt, "context": context},
    )
    data = r.json()
    return data.get("content", "") or data.get("detail", str(r.text))

@mcp.tool()
async def hillhorn_search_memory(query: str, top_k: int = 5) -> list[dict]:
    # Прямой вызов tools.search_memory или новый endpoint в Gateway
    ...
```

### 4.2 Новые endpoint в Gateway (опционально)

Для удобства MCP можно добавить:

- `GET /v1/memory/search?q=...&k=5` — поиск в NWF
- `POST /v1/memory/add` — добавление в память

Тогда MCP не зависит от внутренней реализации tools.

### 4.3 Конфигурация Cursor MCP

```json
// .cursor/mcp.json или Cursor Settings
{
  "mcpServers": {
    "hillhorn": {
      "command": "python",
      "args": ["-m", "hillhorn_mcp"],
      "env": {
        "HILLHORN_GATEWAY_URL": "http://localhost:8001",
        "HILLHORN_WORKSPACE_PATH": "${workspaceFolder}"
      }
    }
  }
}
```

---

## 5. Сравнение: NWF extension vs Hillhorn MCP

| Критерий | NWF extension | Hillhorn MCP |
|----------|---------------|--------------|
| Поиск в памяти | nwf_search (семантика) | hillhorn_search_memory (NWF deepseek_memory) |
| Добавление в память | nwf_add_turn | hillhorn_add_memory |
| Индексация файлов | nwf_index_file | hillhorn_index_file (опц.) |
| Консультации агентов | Нет | planner, coder, reviewer, chat |
| Специализированные модели | Нет | deepseek-reasoner, coder-v2 |
| Function calling | Нет | Да (в агентах Gateway) |
| Зависимости | nwf-core, своё хранилище | Gateway (локальный), DeepSeek API |

**Вывод:** Hillhorn MCP может заменить NWF extension, если:
- Память Hillhorn (deepseek_memory + nwf_opencloud) достаточна для проектного контекста;
- Добавлена индексация файлов (аналог nwf_index_file);
- Cursor rules настроены на приоритет hillhorn_*.

---

## 6. Порядок внедрения (рекомендуемый)

1. **Неделя 1:** Фаза 1 — Hillhorn MCP Server (consult_agent, search_memory, add_memory)
2. **Неделя 2:** Фаза 2 — Cursor rules, конфигурация, тестирование
3. **Неделя 3:** Фаза 3 — Решение: замена или сосуществование с NWF
4. **Неделя 4:** Фаза 4–5 — Улучшения расширения, документация

---

## 7. Критерии успеха

- [ ] Cursor Agent при сложной задаче вызывает hillhorn_consult_planner
- [ ] Cursor Agent может получить code review через hillhorn_consult_reviewer
- [ ] hillhorn_search_memory возвращает релевантные прошлые запросы
- [ ] hillhorn_add_memory сохраняет контекст для будущих сессий
- [ ] При отключённом NWF extension workflow остаётся работоспособным
- [ ] Документация: установка, настройка, примеры использования

---

## 8. Риски и митигации

| Риск | Митигация |
|------|-----------|
| Gateway не запущен | MCP проверяет /health при старте, понятная ошибка |
| Разные форматы памяти NWF vs Hillhorn | Унифицировать через общий Field или адаптер |
| Дублирование вызовов (Cursor + Hillhorn оба делают одно) | Правила: чётко разделить «когда Cursor, когда Hillhorn» |
| Латентность (два hop: Cursor→MCP→Gateway→DeepSeek) | Кэш частых запросов, асинхронность |
