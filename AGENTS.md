# Hillhorn - инструкция для Cursor Agents

## Обязательный порядок (нарушать нельзя)

1. **hillhorn_get_context** - первым действием в сессии
2. **hillhorn_search** - перед чтением файлов (по теме задачи)
3. read_file / edit - работа с кодом
4. **hillhorn_consult_with_memory** - planner (сложные задачи) или reviewer (после кода)
5. **hillhorn_add_turn** - сохранить важное в память

## Инструменты

| Инструмент | Когда | Обязательность |
|------------|-------|----------------|
| hillhorn_get_context | Начало сессии | ОБЯЗАТЕЛЬНО первым |
| hillhorn_search | Перед read_file по теме | ОБЯЗАТЕЛЬНО перед read |
| hillhorn_add_turn | После решения, изучения кода | ОБЯЗАТЕЛЬНО после важного |
| hillhorn_consult_with_memory | planner/reviewer | По необходимости |
| hillhorn_consult_agent | chat, общие вопросы | По необходимости |
| hillhorn_index_file | README, ключевые файлы | По необходимости |

## Параметры

- project_id: путь к корню проекта (по умолчанию из HILLHORN_PROJECT_ID)
- kind_filter: ["doc", "code", "conversation"] - фильтр типа записей

## Режимы (.env HILLHORN_MODE)

- full: полный workflow
- minimal: только search + add_turn (без consult)
- consult_only: быстрые правки без обязательного search
