# Задача 3: Planner (сложная задача)

## Описание

Многошаговая задача. Проверяем качество плана от hillhorn_consult_with_memory(planner).

## Задание для Agent

Спроектируй и реализуй простой CLI-калькулятор:
- Операции: +, -, *, /
- Ввод: `python calc.py 2 + 3`
- Вывод: 5

## Workflow

1. hillhorn_get_context
2. hillhorn_consult_with_memory("planner", "План для CLI калькулятора: аргументы, парсинг, операции. 3-4 шага.")
3. Реализовать по плану
4. hillhorn_add_turn("calc.py - CLI калькулятор, план от planner", kind="doc")

## Чеклист проверки

- [ ] planner вызван
- [ ] План структурирован (шаги)
- [ ] calc.py работает: `python calc.py 2 + 3` => 5
- [ ] add_turn вызван

## Метрики

- План полезен (0-3): ___
- Время consult: ___ сек
- Ошибки при реализации: ___
