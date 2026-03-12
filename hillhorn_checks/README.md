# Hillhorn - проверки и анализ эффективности

## Цель

Реальные задачи для проверки работы Hillhorn, анализ эффективности, выводы.

## Как использовать

1. **Запуск окружения:**
   ```powershell
   .\run_all.ps1
   ```

2. **Выполнение задач:**  
   Открой в Agent папку `hillhorn_checks` и выполняй задачи по порядку:
   - `tasks/task_01_cold_start/TASK.md`
   - `tasks/task_02_warm_context/TASK.md`
   - и т.д.

3. **Анализ:**
   ```powershell
   python analyze.py
   ```

4. **Отчет:**  
   Заполни `REPORT_TEMPLATE.md` по результатам.

## Файлы

| Файл | Назначение |
|------|------------|
| PLAN.md | План проверок и метрики |
| REPORT_TEMPLATE.md | Шаблон отчета |
| run_all.ps1 | Запуск проверок |
| analyze.py | Краткий анализ активности |
| tasks/task_0X_*/TASK.md | Описание задач |
