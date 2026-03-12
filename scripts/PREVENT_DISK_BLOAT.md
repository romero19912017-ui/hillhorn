# Как не забивать диск

## Быстрая очистка (раз в неделю)

```powershell
.\scripts\cleanup_disk.ps1
```

## Ограничить pip cache

Добавь в `%APPDATA%\pip\pip.ini` или создай:

```ini
[global]
cache-dir = C:\hillhorn_data\.pip_cache
no-cache-dir = 0
```

Либо при установке: `pip install --no-cache-dir <paket>`

## Ограничить Temp

1. **Переменная TMPDIR** — в системе задай TMPDIR на быстрый диск с ограничением
2. **Windows Storage Sense** — Параметры → Система → Память → включить «Контроль памяти», задать «Автоочистка временных файлов»

## Запланировать очистку (Task Scheduler)

```powershell
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -File C:\Hillhorn\scripts\cleanup_disk.ps1"
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 3am
Register-ScheduledTask -TaskName "HillhornDiskCleanup" -Action $action -Trigger $trigger -Description "Weekly disk cleanup"
```

## Кто съедает место

| Источник | Решение |
|----------|---------|
| %TEMP% | Регулярная очистка, Storage Sense |
| pip cache | pip cache purge, --no-cache-dir |
| Cursor/IDE | Очистка кэша в настройках |
| node_modules | Удалять в ненужных проектах |
| Docker | docker system prune -a |
| .mypy_cache | Уже в .gitignore, можно удалять |
