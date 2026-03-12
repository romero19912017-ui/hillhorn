# План: умная память + DeepSeek наравне с агентами Cursor

**Цель:** Hillhorn — единая среда: память (search/add/index) + DeepSeek (plan/review/code) работают вместе с агентами Cursor.

---

## 1. Архитектура

```
Cursor Agent
    |
    +---> hillhorn_search     ----+---> tools.search_memory (direct)
    |                             +---> nwf_adapter.search_similar (direct)
    |
    +---> hillhorn_add_turn   ----+---> tools.add_to_memory (direct)
    |
    +---> hillhorn_index_file ----+---> tools.add_to_memory (direct)
    |
    +---> hillhorn_consult_agent --+---> Gateway /v1/agent/query (HTTP)
                                       |
                                       +---> DeepSeek API (planner/coder/reviewer)
                                       +---> Gateway tools (read_file, search_memory, ...)
                                       +---> NWF memory (логирует запросы)
```

**Память:** MCP вызывает tools/nwf_adapter напрямую (без Gateway).
**DeepSeek:** MCP вызывает Gateway → DeepSeek + tools (workspace_path = проект).

---

## 2. Что уже есть

| Компонент | Статус |
|-----------|--------|
| hillhorn_search, add_turn, index_file | Работают (direct) |
| hillhorn_consult_agent | Есть, нужен Gateway |
| Gateway deepseek_gateway.py | Есть, endpoint /v1/agent/query |
| NWF Adapter | Синхронизирует SOUL/USER/MEMORY |
| tools (search_memory, add_to_memory, read_file, ...) | Есть |
| MCP config в Cursor | hillhorn в mcp.json |
| .cursorrules | Есть (Hillhorn + дубли NWF) |

---

## 3. Проблемы и решения

### 3.1 Gateway не отвечает на /v1/memory/* (404)

**Решение:** Память уже идёт через MCP direct — Gateway для памяти не нужен.

### 3.2 Gateway для hillhorn_consult_agent

**Требуется:** Gateway запущен, /v1/agent/query работает.
**Проверка:** `curl -X POST http://127.0.0.1:8001/v1/agent/query -d '{"agent_type":"chat","prompt":"Hi","max_tokens":50}'`
**Настройка:** DEEPSEEK_API_KEY в .env или http://127.0.0.1:8001/settings

### 3.3 Workspace для DeepSeek agents

Gateway передаёт workspace_path в tools. Текущий tools._get_workspace() берёт MOLTBOT_WORKSPACE (default: ~/.openclaw/workspace). Для Hillhorn нужен c:\Hillhorn.

**Решение:** При вызове hillhorn_consult_agent передавать project_id (c:\Hillhorn). Gateway в AgentRequest принимает workspace_path — MCP передаёт project_id как workspace_path. В Gateway tools.set_workspace_override(workspace_path) вызывается перед _execute_tool.

**Проверить:** В deepseek_gateway при обработке /v1/agent/query передаётся workspace_path в call_deepseek → tools.

### 3.4 NWF Adapter workspace

nwf_memory_adapter ищет SOUL.md, USER.md, MEMORY.md в MOLTBOT_WORKSPACE.
SOUL.md в c:\Hillhorn. Нужно MOLTBOT_WORKSPACE=c:\Hillhorn.

**Решение:** В start_all_background или env: `$env:MOLTBOT_WORKSPACE = "c:\Hillhorn"` перед запуском nwf_memory_adapter.

### 3.5 .cursorrules дубли

Сейчас есть правила и для Hillhorn, и для NWF. NWF удалён — убрать дубли.

---

## 4. План внедрения (по шагам)

### Шаг 1. Workspace для Adapter

Установить MOLTBOT_WORKSPACE=c:\Hillhorn при запуске NWF Adapter.

Файл: scripts/start_all_background.ps1
```powershell
$env:MOLTBOT_WORKSPACE = $base
Start-Process ... nwf_memory_adapter.py
```
(или передать через env в Start-Process)

### Шаг 2. Почистить .cursorrules

Удалить секцию NWF, оставить только Hillhorn. Унифицировать project_id.

### Шаг 3. Убедиться что Gateway получает workspace_path

В hillhorn_consult_agent уже передаётся project_id как workspace_path. В Gateway AgentRequest есть workspace_path. Проверить что call_deepseek → _execute_tool вызывают set_workspace_override.

### Шаг 4. Автозапуск и проверка

- start_all_background: Gateway + NWF Adapter
- Task folderOpen или Windows Startup
- После запуска: health, consult (если DEEPSEEK_API_KEY задан)

### Шаг 5. Документация

- MCP_HILLHORN_SETUP.md — актуализировать
- Краткая шпаргалка: когда какой инструмент использовать

---

## 5. Workflow для агента Cursor

1. **Начало задачи:** hillhorn_search("общая информация о проекте")
2. **Сложная задача:** hillhorn_consult_agent("planner", "составь план для ...")
3. **Работа с кодом:** read_file, edit (стандартные MCP Cursor)
4. **После написания кода:** hillhorn_consult_agent("reviewer", "проверь код: ...")
5. **Сохранение контекста:** hillhorn_add_turn("решение: ...", kind="summary")
6. **Индексация важных файлов:** hillhorn_index_file(path, content)

---

## 6. Чеклист готовности

- [x] MOLTBOT_WORKSPACE = c:\Hillhorn для Adapter (в start script)
- [ ] DEEPSEEK_API_KEY настроен
- [ ] Gateway запускается и /v1/agent/query отвечает
- [ ] NWF Adapter sync workspace → data/nwf_opencloud
- [ ] Hillhorn MCP в Cursor (все 4 инструмента)
- [ ] .cursorrules только Hillhorn
- [ ] Автозапуск (task или Startup)
