# Hillhorn Chat

Расширение VS Code для AI-чата на базе Hillhorn (DeepSeek + NWF-JEPA).

## Требования

- Запущенный DeepSeek Gateway на `http://localhost:8001` (или укажите `hillhorn.gatewayUrl`)

## Использование

1. Запустите Gateway: `uvicorn deepseek_gateway:app --port 8001`
2. Нажмите значок Hillhorn на боковой панели
3. Введите сообщение и нажмите Отправить

## Настройки

| Параметр | Описание |
|----------|----------|
| `hillhorn.gatewayUrl` | URL Gateway (по умолчанию http://localhost:8001) |
| `hillhorn.workspaceId` | ID рабочей области для NWF-памяти |
| `hillhorn.agentType` | Агент по умолчанию: chat, coder, planner, reviewer, architect, documenter |
| `hillhorn.autoAgent` | Автовыбор агента по памяти |

## Разработка

```bash
npm install
npm run compile
```

Затем F5 в VS Code для запуска Extension Development Host.
