# Задача 4: Reviewer

## Описание

Проверка кода через hillhorn_consult_agent(reviewer, code_to_review=...).

## Задание для Agent

1. Возьми код из `../task_03_planner/calc.py` (или создай простой калькулятор)
2. Вызови hillhorn_consult_agent("reviewer", "Проверь код", code_to_review=<код>)
3. Примени замечания, если есть
4. hillhorn_add_turn("Ревью calc.py: [кратко замечания]", kind="summary")

## Workflow

1. Прочитать calc.py
2. hillhorn_consult_agent(agent_type="reviewer", prompt="Проверь на баги и стиль", code_to_review=содержимое)
3. Исправить по замечаниям
4. add_turn с итогом ревью

## Чеклист проверки

- [ ] reviewer вызван с code_to_review
- [ ] Ответ содержит замечания (если есть что улучшить)
- [ ] Замечания конкретны (файл, строка,建议)
- [ ] Правки внесены (если релевантно)

## Метрики

- Замечания полезны (0-3): ___
- Найдены реальные проблемы (да/нет): ___
- Время ответа reviewer: ___ сек
