# Hillhorn как расширение (без сборки VS Code)

Hillhorn Chat — обычное расширение VS Code. Работает в **VS Code**, **Cursor** и других редакторах на базе VS Code.

## Быстрый старт

### 1. Собрать расширение

```powershell
cd c:\Hillhorn
.\scripts\build_extension.ps1
```

### 2. Установить в редактор

**Вариант A — через палитру (надёжно):**
1. Ctrl+Shift+P → `Developer: Install Extension from Location`
2. Указать путь: `C:\Hillhorn\dist\hillhorn-chat`

**Вариант B — вручную (скопировать папку):**
- VS Code: `dist\hillhorn-chat` → `%USERPROFILE%\.vscode\extensions\hillhorn.hillhorn-chat-0.1.0`
- Cursor: `dist\hillhorn-chat` → `%USERPROFILE%\.cursor\extensions\hillhorn.hillhorn-chat-0.1.0`

Переименовать папку в `hillhorn.hillhorn-chat-0.1.0` (publisher.name-version).

### 3. Запустить сервисы

```powershell
.\scripts\start_all.ps1
```

(DeepSeek Gateway на 8001, NWF Adapter)

### 4. Открыть Hillhorn

В редакторе: боковая панель → иконка Hillhorn (комментарий) → Chat.

## Настройки

- `hillhorn.gatewayUrl` — URL Gateway (по умолчанию http://localhost:8001)
- `hillhorn.workspaceId` — ID рабочего пространства NWF
- `hillhorn.agentType` — тип агента (chat, coder, planner и т.д.)

## Отдельное приложение

Чтобы сделать отдельное приложение без VS Code, нужно было бы собрать свой Electron-обёртку. Проще использовать стандартный VS Code/Cursor с расширением.
