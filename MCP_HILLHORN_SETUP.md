# Hillhorn - установка и настройка

## Быстрая установка в Cursor

```powershell
.\scripts\install_hillhorn_to_cursor.ps1
```

Устанавливает:
- Extension **Hillhorn Status** (status bar) в `%USERPROFILE%\.cursor\extensions\`
- MCP **hillhorn** в глобальный `%USERPROFILE%\.cursor\mcp.json`

Перезапусти Cursor после установки.

С автозапуском при входе в Windows:
```powershell
.\scripts\install_hillhorn_to_cursor.ps1 -Startup
```

### Альтернатива: собрать .vsix
```powershell
npm i -g @vscode/vsce
.\scripts\build_extension.ps1
```
Будет создан `dist\hillhorn-status.vsix`. Установка: Cursor -> Extensions -> ... -> Install from VSIX.

---

## Автозапуск при открытии Cursor

## Автозапуск при открытии Cursor

1. **При открытии папки Hillhorn**  
   В `.vscode/tasks.json` настроена задача `Hillhorn: Start Background` с `runOn: folderOpen`.  
   При открытии `c:\Hillhorn` в Cursor задача запускает Gateway и NWF Adapter.

2. **Разрешить автоматические задачи**  
   При первом открытии папки Cursor может спросить: «Allow Automatic Tasks in Folder?»  
   Выберите **Allow**.  
   Либо в Settings: `task.allowAutomaticTasks` = `on`.

3. **Автозапуск при входе в Windows**  
   ```powershell
   .\scripts\add_to_windows_startup.ps1
   ```  
   Hillhorn будет запускаться при входе в систему (до запуска Cursor).

## Использование только в Agent

MCP‑инструменты Hillhorn доступны в Cursor Agent/Composer.  
В Chat они обычно недоступны.  
Статус подключения: **Settings > Tools & MCP** — индикатор Hillhorn (зелёный = подключён).

## Видимость обращений к Hillhorn

### В диалоге Agent
Каждый ответ инструмента Hillhorn начинается с `[Hillhorn | имя_инструмента]`:
```
[Hillhorn | hillhorn_search]
1. [memory] ...
```

В чате Agent это отображается и показывает обращение к Hillhorn.

### Индикатор в статус-баре

### Вариант 1: встроенный статус MCP

**Settings > Tools & MCP** — статус Hillhorn (зелёный/жёлтый/красный).

### Вариант 2: задача «Hillhorn: Status»

- `Ctrl+Shift+P` → «Tasks: Run Task» → **Hillhorn: Status**  
- Показывает состояние Gateway и время последнего вызова инструмента.

### Вариант 3: расширение «Hillhorn Status»

Расширение добавляет в правый нижний угол строку:
```
Hillhorn: hillhorn_search 2m ago
```

**Установка:**
1. Скопировать папку `extensions/hillhorn-status` в `%USERPROFILE%\.cursor\extensions\hillhorn-status`
2. Или: **Extensions** → **Install from VSIX** (предварительно собрать vsix)
3. Перезапустить Cursor

Лог активности: `data/hillhorn_activity.json` (обновляется при каждом вызове инструмента Hillhorn).
