# Hillhorn workflow

## Режимы (HILLHORN_MODE)

- full: get_context, search, consult, add_turn
- minimal: только search, add_turn
- consult_only: search не обязателен перед read_file

## Порядок

1. hillhorn_get_context
2. hillhorn_search - по теме
3. hillhorn_consult_with_memory (planner при сложной задаче)
4. read_file / edit
5. hillhorn_consult_with_memory (reviewer) - после кода
6. hillhorn_add_turn - сохранить

## Напоминание

Если не вызывал hillhorn_search в первых 2 сообщениях - вызови перед read_file.
