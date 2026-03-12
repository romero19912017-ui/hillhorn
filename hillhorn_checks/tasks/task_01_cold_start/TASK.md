# Задача 1: Холодный старт (новая задача)

## Описание

Агент получает задачу в проекте без предзаполненной памяти. Имитация первого входа в проект или новой темы.

## Задание для Agent

Создай утилиту `greet.py` в папке `hillhorn_checks/tasks/task_01_cold_start/`:
- Принимает аргумент (имя)
- Печатает "Hello, {name}!"
- Имеет `if __name__ == "__main__"`

## Workflow (обязательный)

1. hillhorn_get_context(project_id="c:\Hillhorn")
2. hillhorn_search("greet utility hello")
3. Создать greet.py
4. hillhorn_add_turn("Создана greet.py - простая утилита приветствия", kind="code")

## Чеклист проверки

- [ ] get_context вызван первым
- [ ] search выполнен (пусто или есть результаты)
- [ ] greet.py создан
- [ ] add_turn вызван после завершения

## Метрики (заполнить вручную)

- Время: ___ мин
- Вызовов Hillhorn: ___
- Search релевантен (0-3): ___
