# Hillhorn - тест на реальной задаче (змейка)

## Задача

Написать змейку на Python в консоли, проверить работу Hillhorn на полном workflow.

## Результаты теста

| Шаг | Инструмент | Результат |
|-----|------------|-----------|
| 1 | hillhorn_get_context | OK, 188 chars, SOUL в контексте |
| 2 | hillhorn_search("snake game python") | OK, нашел SOUL/workspace |
| 3 | hillhorn_consult(planner) | OK, план получен |
| 4 | snake.py | Создан, синтаксис OK |
| 5 | hillhorn_consult(reviewer) | OK (code in context, agent=chat) |
| 6 | hillhorn_add_turn | OK, сохранено в память |

## Файлы

- `snake.py` - консольная змейка (Windows: msvcrt, Unix: select/termios)
- Управление: WASD, Q - выход
- Запуск: `python snake.py`

## Эффективность Hillhorn

### Что сработало

1. **get_context** - SOUL + память в одном вызове, быстрый старт
2. **search** - семантический поиск нашел релевантное (SOUL)
3. **planner** - DeepSeek дал план (reasoner)
4. **add_turn** - решение записано в память

### Решено

1. **reviewer** - передавать код через `code_to_review` (в context), не в prompt. reviewer -> chat на Gateway (deepseek-coder-v2 недоступен)
2. **Память** - search возвращает SOUL (workspace), а не прошлые решения по змейке - память еще пуста

### Рекомендации

- Для reviewer передавать короткий фрагмент кода (до 500 символов)
- Накапливать память: add_turn после каждой задачи
- get_context + search перед чтением файлов - экономит время
