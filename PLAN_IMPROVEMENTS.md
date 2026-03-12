# Hillhorn - детальный план применения улучшений

## Этапы и зависимости

```
Фаза 1 (фундамент)     Фаза 2 (улучшения)      Фаза 3 (полировка)
     |                        |                        |
  Синхронизация           API cost               Правила
  add/search              Автоиндексация         Режимы
  Диагностика             UI/лог                 Регулярные тесты
  Retry                                   
```

---

## 1. Синхронизация add_turn и search (высокий приоритет)

### Проблема
add_to_memory пишет в NWF_MEMORY_PATH, search_memory ищет по workspace_id — пути/форматы могут расходиться.

### План

| Шаг | Действие | Файлы |
|-----|----------|-------|
| 1.1 | Унифицировать путь: add и search используют один корень (NWF_MEMORY_PATH или workspace) | tools.py |
| 1.2 | add_to_memory: в label писать project_id/workspace_id как обязательный тег | tools.py |
| 1.3 | search_memory: искать по project_id в labels, не только по подпути | tools.py |
| 1.4 | Опция: отдельное хранилище для "conversation/doc" с полным текстом | tools.py, nwf |
| 1.5 | Тест: add_turn → search через 1 сек → должен найти | hillhorn_checks |

### Результат
Warm context (task_02) находит недавно добавленное.

---

## 2. Диагностика и retry (высокий приоритет)

### План

| Шаг | Действие | Файлы |
|-----|----------|-------|
| 2.1 | Скрипт diagnose.ps1: Gateway health, MCP process, порты, путь к activity | scripts/diagnose.ps1 |
| 2.2 | Gateway: retry при 429/5xx (уже есть MAX_RETRIES, проверить) | deepseek_gateway.py |
| 2.3 | hillhorn_mcp_server: retry при ConnectError (2 попытки, 2 сек) | hillhorn_mcp_server.py |
| 2.4 | Лог ошибок в data/hillhorn_errors.log (append) | hillhorn_mcp_server.py |
| 2.5 | Task "Hillhorn: Diagnose" в tasks.json | .vscode/tasks.json |

### Результат
Быстрая диагностика, устойчивость к сбоям сети.

---

## 3. API cost — учёт токенов (средний приоритет)

### План

| Шаг | Действие | Файлы |
|-----|----------|-------|
| 3.1 | Gateway: логировать usage (input_tokens, output_tokens) в data/deepseek_usage.json | deepseek_gateway.py |
| 3.2 | Формат: {date: {agent_type: {calls, input_tokens, output_tokens}}} | - |
| 3.3 | Скрипт scripts/cost_report.ps1: сумма за день/неделю, оценка $ | scripts/cost_report.ps1 |
| 3.4 | Константы цен (deepseek-chat, reasoner) в cost_report или .env | - |
| 3.5 | Опционально: лимит HILLHORN_DAILY_TOKENS, предупреждение при 80% | deepseek_gateway.py |

### Результат
Прозрачность расходов, контроль бюджета.

---

## 4. Автоиндексация (средний приоритет)

### План

| Шаг | Действие | Файлы |
|-----|----------|-------|
| 4.1 | Watch SOUL.md, USER.md, MEMORY.md в project root | nwf_memory_adapter или отдельный watcher |
| 4.2 | При изменении: вызвать add_to_memory с тегом file:SOUL.md | - |
| 4.3 | Реализация: polling каждые 30 сек или inotify/ReadDirectoryChangesW | scripts/watch_memory.ps1 или Python |
| 4.4 | Интеграция в start_all_background: запуск watcher вместе с Adapter | scripts/start_all_background.ps1 |
| 4.5 | Опция HILLHORN_AUTO_INDEX=1 в .env | - |

### Результат
SOUL/USER/MEMORY всегда актуальны в поиске без ручного index_file.

---

## 5. Search — качество и фильтры (средний приоритет)

### План

| Шаг | Действие | Файлы |
|-----|----------|-------|
| 5.1 | hillhorn_search: параметр kind_filter=["doc","code","conversation"] | hillhorn_mcp_server.py |
| 5.2 | tools.search_memory: фильтрация по tags в labels | tools.py |
| 5.3 | Опция recency: приоритет недавним (по timestamp в label) | tools.py |
| 5.4 | BM25/hybrid: добавить keyword-match поверх embedding (опционально, сложнее) | nwf или отдельный модуль |

### Результат
Более точный и управляемый поиск.

---

## 6. Расширенный контекст для consult (средний приоритет)

### План

| Шаг | Действие | Файлы |
|-----|----------|-------|
| 6.1 | hillhorn_consult_with_memory: параметр include_open_files=False | hillhorn_mcp_server.py |
| 6.2 | MCP не имеет доступа к открытым файлам Cursor — оставить как есть или через контекст | - |
| 6.3 | Добавить параметр extra_context: List[str] — пользователь передаёт доп. текст | hillhorn_mcp_server.py |
| 6.4 | Документация: как передавать фрагменты кода через extra_context | MCP_HILLHORN_SETUP.md |

### Результат
Гибкий контекст для planner/reviewer.

---

## 7. Лог вызовов и UI (низкий приоритет)

### План

| Шаг | Действие | Файлы |
|-----|----------|-------|
| 7.1 | _log_activity: дописывать в data/hillhorn_calls.jsonl (tool, ts, duration_ms) | hillhorn_mcp_server.py |
| 7.2 | Extension: команда "Hillhorn: Show History" — Output channel с последними 20 вызовами | extensions/hillhorn-status |
| 7.3 | Extension: счётчик вызовов за сессию в tooltip статус-бара | extension.js |
| 7.4 | Опционально: Webview panel с таблицей вызовов | - |

### Результат
История использования, отладка.

---

## 8. Правила и режимы (низкий приоритет)

### План

| Шаг | Действие | Файлы |
|-----|----------|-------|
| 8.1 | .cursorrules: секция HILLHORN_MODE=full|minimal|consult_only | .cursorrules |
| 8.2 | minimal: только search, add_turn (без consult) | - |
| 8.3 | consult_only: без обязательного search перед read_file | - |
| 8.4 | Проектные правила: .cursor/rules/hillhorn.md (Cursor 0.42+) | .cursor/rules/ |
| 8.5 | Шаблон hillhorn.md с копией основных правил | - |

### Результат
Гибкая настройка под проект.

---

## 9. Регулярные тесты и метрики (низкий приоритет)

### План

| Шаг | Действие | Файлы |
|-----|----------|-------|
| 9.1 | run_tasks.py: замер time_to_first_result, iteration_count | hillhorn_checks/run_tasks.py |
| 9.2 | Сравнение: run_tasks с Hillhorn vs без (мок) | hillhorn_checks/run_tasks_no_hillhorn.py |
| 9.3 | Task "Hillhorn: Run Checks" — еженедельно вручную или по расписанию | .vscode/tasks.json |
| 9.4 | REPORT.md: автоматическое заполнение из results.json | hillhorn_checks/analyze.py |
| 9.5 | Метрики: recall search, полезность planner/reviewer (оценка 0-3) | - |

### Результат
Регрессионное тестирование, тренды.

---

## 10. Умные напоминания (низкий приоритет)

### План

| Шаг | Действие | Файлы |
|-----|----------|-------|
| 10.1 | В .cursorrules: "Если не вызывал hillhorn_search в первых 2 сообщениях — напомни себе" | .cursorrules |
| 10.2 | Опционально: префикс в system prompt Cursor (если доступен) | - |
| 10.3 | Документация: пользователь может написать "сначала hillhorn_search" в первом сообщении | MCP_HILLHORN_SETUP.md |

### Результат
Меньше забытых вызовов search.

---

## Календарный план (оценка)

| Неделя | Фаза | Задачи |
|--------|------|--------|
| 1 | 1 | 1.1–1.4 синхронизация add/search, 2.1–2.4 диагностика и retry |
| 2 | 2 | 3.1–3.5 API cost, 4.1–4.4 автоиндексация |
| 3 | 2 | 5.1–5.3 search фильтры, 6.1–6.4 контекст consult |
| 4 | 3 | 7.1–7.3 лог/UI, 8.1–8.3 правила и режимы |
| 5 | 3 | 9.1–9.5 регулярные тесты, 10.1–10.3 напоминания |

---

## Риски и упрощения

| Риск | Митигация |
|------|-----------|
| Изменение формата NWF | Сохранить обратную совместимость, миграция при первом запуске |
| Рост сложности | Вводить фичи по одной, с флагами в .env |
| Cursor API ограничения | UI делать через Output/Tasks, не через кастомные API |
| BM25/hybrid — сложность | Отложить, сначала фильтры по tags |

---

## Критерии готовности фазы

- **Фаза 1:** task_02 находит greet, diagnose выявляет типичные проблемы, retry срабатывает при 429
- **Фаза 2:** cost_report показывает токены, SOUL автоиндексируется, search поддерживает kind_filter
- **Фаза 3:** история вызовов в Output, режимы в .cursorrules, run_tasks собирает метрики
