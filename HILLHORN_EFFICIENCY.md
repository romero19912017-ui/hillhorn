# Hillhorn - повышение эффективности

## Новые инструменты (применены)

| Инструмент | Описание |
|------------|----------|
| hillhorn_get_context | SOUL + USER + MEMORY + память. Вызывать в начале сессии. |
| hillhorn_consult_with_memory | planner/reviewer с памятью проекта как context |
| (hillhorn_search) | При пустом результате: явно "Память пуста (новый проект)" |

## Исправление reviewer

- `code_to_review` - длинный код в context (до 12000 символов)
- reviewer использует agent=chat (deepseek-coder-v2 недоступен)
- prompt ограничен 8000 символов

## Экономия API (DeepSeek)

| Параметр | Было | Стало |
|----------|------|-------|
| max_tokens | 2048 | 1200 (HILLHORN_MAX_TOKENS) |
| code_to_review | 12000 | 8000 |
| prompt | 8000 | 6000 |
| memory_top_k | 5 | 3 |
| SOUL/USER | 2000 | 1500 |
| memory item | 250 | 200 |

**planner** - использовать только при сложной задаче (reasoner дороже chat в ~4 раза).

## Результаты теста (scripts/run_hillhorn_snake_test.py)

- hillhorn_search: OK (результаты зависят от наполненности памяти)
- hillhorn_add_turn: OK
- hillhorn_consult_agent: OK (требует Gateway + DEEPSEEK_API_KEY)

## Изменения

### 1. Исправлен hillhorn_mcp_server.py

- Добавлена функция `_post()` (была вызов без определения - ошибка при consult_agent)
- Сообщение об ошибке: start_all_background.ps1 вместо start_all.ps1

### 2. Обновлены системные промпты DeepSeek (deepseek_gateway.py)

| Агент | Было | Стало |
|-------|------|-------|
| planner | Короткий | Формат шагов: цель, действия, зависимости. Язык по промпту |
| reviewer | Короткий | Формат: [Critical/Important/Minor] Issue. Русский/EN по промпту |
| coder | Базовый | KISS, DRY, язык по промпту |
| chat | Базовый | Лаконичность, язык = язык промпта |

### 3. Тестовый скрипт

```
python scripts/test_hillhorn.py
```

## Рекомендации по эффективности

### Для агента Cursor (.cursorrules уже настроены)

1. **Сначала search** - перед чтением файлов вызывай hillhorn_search по теме
2. **Planner для сложных задач** - разбивает на шаги, экономит итерации
3. **Reviewer после кода** - catch багов до коммита
4. **add_turn после важного** - фиксируй решения в памяти

### Для промптов hillhorn_consult_agent

- `planner`: "Составь план для [задача]. Укажи шаги и зависимости."
- `reviewer`: "Проверь код: [вставь код или путь]. Список проблем по приоритету."

### Опционально (если нужна кастомизация)

- Добавить SOUL.md/ USER.md в project root - Adapter подтянет в контекст
- Индексировать критичные файлы: hillhorn_index_file(path, content)
- В .env: DEEPSEEK_CHAT_MODEL, DEEPSEEK_TIMEOUT под твою сеть
