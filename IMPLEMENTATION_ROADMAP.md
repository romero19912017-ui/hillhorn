# Hillhorn — детальный план внедрения всех функций

**Версия:** 1.0  
**Дата:** 2025-03-10

---

## Оглавление

1. [Фаза 1: Агенты и инструменты (Function Calling)](#фаза-1-агенты-и-инструменты-function-calling)
2. [Фаза 2: Управление памятью (NWF)](#фаза-2-управление-памятью-nwf)
3. [Фаза 3: Семантические эмбеддинги](#фаза-3-семантические-эмбеддинги)
4. [Фаза 4: Индексирование кодовой базы](#фаза-4-индексирование-кодовой-базы)
5. [Фаза 5: Расширение VS Code (Hillhorn Chat)](#фаза-5-расширение-vs-code-hillhorn-chat)
6. [Фаза 6: UI — стриминг, контекст, Apply edits](#фаза-6-ui--стриминг-контекст-apply-edits)
7. [Фаза 7: Git и терминал](#фаза-7-git-и-терминал)
8. [Фаза 8: Надёжность и производительность](#фаза-8-надёжность-и-производительность)
9. [Фаза 9: Проекты и workspace](#фаза-9-проекты-и-workspace)
10. [Фаза 10: Наблюдаемость и настройки](#фаза-10-наблюдаемость-и-настройки)
11. [Фаза 11: Дополнительно (уровень выше Cursor)](#фаза-11-дополнительно-уровень-выше-cursor)

---

## Фаза 1: Агенты и инструменты (Function Calling)

**Цель:** Planner и другие агенты могут вызывать search_memory, read_file, call_agent и т.д.

**Оценка:** 12–16 часов

### 1.1. Модуль tools.py

| Шаг | Действие | Файл | Детали |
|-----|----------|------|--------|
| 1.1.1 | Создать `tools.py` | `c:\Hillhorn\tools.py` | Модуль с async-функциями: `search_memory`, `add_to_memory`, `read_file`, `write_file`, `execute_command`, `call_agent` |
| 1.1.2 | `search_memory(query, k)` | tools.py | Загрузить Field из NWF_MEMORY_PATH, get_embedding(query), L2 поиск, вернуть список {text, source, score} |
| 1.1.3 | `add_to_memory(content, tags)` | tools.py | Charge из content, field.add(), field.save() |
| 1.1.4 | `read_file(path)` | tools.py | Path(workspace)/path, read_text(utf-8), вернуть {content, path}. Ограничить path внутри workspace |
| 1.1.5 | `write_file(path, content)` | tools.py | Проверка path в workspace, write_text. Возврат {status, path}. Не перезаписывать без флага |
| 1.1.6 | `execute_command(command)` | tools.py | subprocess.run, whitelist: `python`, `npm`, `pnpm`, `pip`, `node`, `git status`, `git diff`, `pytest`, `cargo`. Без shell=True или с ограниченным shell |
| 1.1.7 | `call_agent(agent_type, prompt)` | tools.py | httpx.post localhost:8001/v1/agent/query, вернуть {content, model_used} |
| 1.1.8 | TOOL_DEFINITIONS | tools.py | Список dict для OpenAI/DeepSeek tools format: type=function, function={name, description, parameters{type, properties, required}} |

**Зависимости:** nwf, pathlib, httpx, subprocess. Workspace path из env.

### 1.2. Интеграция tools в deepseek_gateway.py

| Шаг | Действие | Файл | Детали |
|-----|----------|------|--------|
| 1.2.1 | Добавить tools, tool_choice в AgentRequest | deepseek_gateway.py | Optional[List[Dict]], Optional[str]="auto" |
| 1.2.2 | Передавать tools в payload DeepSeek | deepseek_gateway.py | if tools: payload["tools"]=tools; payload["tool_choice"]=tool_choice |
| 1.2.3 | Обработка tool_calls в ответе | deepseek_gateway.py | Проверить finish_reason=="tool_calls", извлечь tool_calls, для каждого: execute_tool(name, args), append {role:"tool", tool_call_id, content}, повторить запрос (рекурсия или цикл, макс 5 итераций) |
| 1.2.4 | execute_tool(name, args) | deepseek_gateway.py | Импорт из tools, маппинг name->async func, await func(**args) |
| 1.2.5 | Удаление reasoning_content из messages при tool loop | deepseek_gateway.py | При добавлении tool message в history — только role, content |

**Ограничения:** DeepSeek API поддерживает tools аналогично OpenAI. Проверить документацию DeepSeek.

### 1.3. Безопасность execute_command

| Шаг | Действие | Файл | Детали |
|-----|----------|------|--------|
| 1.3.1 | Whitelist команд | tools.py | ALLOWED_CMDS = ["python", "npm", "pnpm", "pip", "node", "npx", "git", "pytest", "cargo", "uvicorn"] |
| 1.3.2 | Парсинг command | tools.py | Split по пробелам, первый токен — команда. Проверить in whitelist |
| 1.3.3 | Запрет опасных аргументов | tools.py | Блокировать: `rm -rf /`, `del /f`, `format`, `> /dev/sd`, пути вне workspace |
| 1.3.4 | Опция confirm_dangerous | tools.py | Для команд с side effects — возвращать {needs_confirm: true, preview: "..."}. Клиент подтверждает, повторный вызов с confirm=true |
| 1.3.5 | timeout | tools.py | subprocess.run(timeout=60) |

### 1.4. ArchitectAgent, DocumenterAgent, TesterMathAgent

| Шаг | Действие | Файл | Детали |
|-----|----------|------|--------|
| 1.4.1 | ArchitectAgent | agents.py | class ArchitectAgent(BaseAgent): __init__("architect"), async def design_architecture(description) |
| 1.4.2 | DocumenterAgent | agents.py | class DocumenterAgent(BaseAgent): __init__("documenter"), async def document_code(code, format) |
| 1.4.3 | TesterMathAgent | agents.py | class TesterMathAgent(BaseAgent): __init__("tester_math"), async def verify_math(expression) |
| 1.4.4 | select_agent_from_memory | agents.py | Добавить architect, documenter, tester_math в counts |

---

## Фаза 2: Управление памятью (NWF)

**Цель:** Очистка, экспорт/импорт, раздельная память по проектам.

**Оценка:** 8–10 часов

### 2.1. Очистка памяти (Pruning)

| Шаг | Действие | Файл | Детали |
|-----|----------|------|--------|
| 2.1.1 | Добавить timestamp в labels при _log_to_nwf | deepseek_gateway.py | label["timestamp"] = time.time() |
| 2.1.2 | nwf_memory_utils.py | Новый файл | prune_field(field_path, max_charges=10000, max_age_days=90): загрузить Field, отсортировать по timestamp, удалить старые (Field.remove или пересоздать), сохранить |
| 2.1.3 | prune_field — по alpha | nwf_memory_utils.py | Удалять заряды с alpha < 0.1 (неуспешные, низкий приоритет) |
| 2.1.4 | CLI | nwf_memory_adapter.py или отдельный | `--prune --max-charges 10000 --max-age 90` |
| 2.1.5 | Автопрунинг | deepseek_gateway.py | После каждого _log_to_nwf проверить len(field) > 15000, вызвать prune_field в фоне (asyncio.create_task) |
| 2.1.6 | Конфиг | .env | NWF_MAX_CHARGES=10000, NWF_MAX_AGE_DAYS=90 |

**Зависимости:** nwf-core должен поддерживать remove. Если нет — пересоздавать Field с отфильтрованными зарядами.

### 2.2. Экспорт/импорт памяти

| Шаг | Действие | Файл | Детали |
|-----|----------|------|--------|
| 2.2.1 | export_field(path, out_path) | nwf_memory_utils.py | field.load(path), field.save(out_path) или копировать папку |
| 2.2.2 | import_field(src_path, dest_path) | nwf_memory_utils.py | Загрузить из src, merge или replace в dest, save |
| 2.2.3 | API /memory/export | deepseek_gateway.py | GET /memory/export?path=...&format=json. Сериализовать заряды в JSON (z, sigma, alpha, labels) |
| 2.2.4 | API /memory/import | deepseek_gateway.py | POST /memory/import, multipart file или JSON body |
| 2.2.5 | UI кнопки в Settings | deepseek_gateway.py | Добавить в /settings форму: Export, Import (file input) |

### 2.3. Раздельная память по проектам

| Шаг | Действие | Файл | Детали |
|-----|----------|------|--------|
| 2.3.1 | workspace_id в запросе | deepseek_gateway.py | AgentRequest: Optional[str] workspace_id. По умолчанию "default" |
| 2.3.2 | Путь к полю | deepseek_gateway.py | NWF_MEMORY_PATH / workspace_id (например data/deepseek_memory/default, data/deepseek_memory/project_a) |
| 2.3.3 | _load_nwf_memory(workspace_id) | deepseek_gateway.py | Динамическая загрузка поля по workspace_id. Кэш {workspace_id: Field} |
| 2.3.4 | API /workspaces | deepseek_gateway.py | GET список workspace_id (по подпапкам data/deepseek_memory) |
| 2.3.5 | Выбор workspace в UI | Settings | Dropdown или поле ввода workspace_id |

### 2.4. Приоритизация зарядов при поиске

| Шаг | Действие | Файл | Детали |
|-----|----------|------|--------|
| 2.4.1 | Вес при ранжировании | deepseek_gateway.py, agents.py | При L2 поиске: score = distance * (1 / (alpha + 0.1)) * recency_factor. recency = exp(-age_days / 30) |
| 2.4.2 | Учёт success | agents.py select_agent_from_memory | Уже есть: lab.get("success"). Усилить вес успешных |
| 2.4.3 | Опция sort_by | search_similar | sort_by: "relevance" | "recent" | "priority" |

---

## Фаза 3: Семантические эмбеддинги

**Цель:** Один энкодер (sentence-transformers) во всех компонентах.

**Оценка:** 6–8 часов

### 3.1. Модуль embeddings.py

| Шаг | Действие | Файл | Детали |
|-----|----------|------|--------|
| 3.1.1 | Создать embeddings.py | c:\Hillhorn\embeddings.py | Единая точка: get_embedding(text, dim=384) -> np.ndarray |
| 3.1.2 | Загрузка модели | embeddings.py | Lazy load SentenceTransformer(all-MiniLM-L6-v2). Кэш в переменной модуля |
| 3.1.3 | Fallback на хэш | embeddings.py | Если sentence_transformers не установлен — _hash_embedding |
| 3.1.4 | Поддержка dim | embeddings.py | Модель 384. Для dim<384 — slice. Для dim>384 — pad zeros (совместимость с NWF 32) или проекция |
| 3.1.5 | Конфиг | .env | EMBED_MODEL, HF_TOKEN (для gated models) |

### 3.2. Замена в компонентах

| Шаг | Действие | Файл | Детали |
|-----|----------|------|--------|
| 3.2.1 | deepseek_gateway.py | Заменить _text_to_embedding | from embeddings import get_embedding |
| 3.2.2 | nwf_memory_adapter.py | Заменить get_embedding | from embeddings import get_embedding; удалить локальные _hash, _hf |
| 3.2.3 | agents.py | select_agent_from_memory | Использовать embeddings.get_embedding. Проверить совместимость dim с Field |
| 3.2.4 | nwf_jepa.py | Опционально | JEPA embed_dim может отличаться. Для retrieve_similar — использовать embeddings для query если подключаем к Gateway |
| 3.2.5 | requirements.txt | Добавить | sentence-transformers (опционально, с [cpu] или без) |

**Важно:** EMBED_DIM в NWF — 32. Sentence-transformers — 384. Варианты: (a) хранить 384 в Field если nwf поддерживает; (b) проекция 384->32 через линейный слой; (c) оставить 32 в Gateway/Adapter для совместимости, использовать 384 только для семантического поиска в отдельном индексе.

**Рекомендация:** Создать code_index с dim=384 отдельно. NWF deepseek_memory оставить 32 для обратной совместимости, но новые заряды можно с 384 если Field поддерживает.

---

## Фаза 4: Индексирование кодовой базы

**Цель:** Семантический поиск по коду, автоиндексация, codebase graph.

**Оценка:** 16–20 часов

### 4.1. Модуль code_indexer.py

| Шаг | Действие | Файл | Детали |
|-----|----------|------|--------|
| 4.1.1 | Создать code_indexer.py | c:\Hillhorn\code_indexer.py | Класс CodeIndexer(workspace_path, index_path) |
| 4.1.2 | Сканирование файлов | code_indexer.py | Рекурсивно glob *.py, *.ts, *.tsx, *.js, *.jsx, *.go, *.rs, *.java. Исключения: node_modules, venv, __pycache__, .git, dist, build |
| 4.1.3 | Парсинг блоков | code_indexer.py | По языку: Python — ast (functions, classes, modules); JS/TS — regex или tree-sitter; fallback — разбить по def/class/function |
| 4.1.4 | Эмбеддинг блока | code_indexer.py | Текст: "file:path\nname: func_name\n\ncode". get_embedding из embeddings.py |
| 4.1.5 | Хранение | code_indexer.py | Field или отдельная структура (JSON + vectors.npy). Label: {file, name, start_line, end_line, code_snippet} |
| 4.1.6 | search_code(query, k) | code_indexer.py | get_embedding(query), L2 поиск, вернуть [{file, name, snippet, score}] |

### 4.2. Исключения (.gitignore)

| Шаг | Действие | Файл | Детали |
|-----|----------|------|--------|
| 4.2.1 | DEFAULT_IGNORE | code_indexer.py | ["node_modules", "venv", "__pycache__", ".git", "dist", "build", ".next", "target", "*.min.js"] |
| 4.2.2 | Чтение .gitignore | code_indexer.py | Если есть .gitignore — парсить, добавить в ignore list. Использовать pathspec или простой regex |
| 4.2.3 | Конфиг | .env или config | CODE_INDEX_IGNORE — дополнительный список |

### 4.3. Автоиндексация при сохранении

| Шаг | Действие | Файл | Детали |
|-----|----------|------|--------|
| 4.3.1 | File watcher | code_indexer.py | Watchdog на workspace. on_modified для *.py, *.ts и т.д. |
| 4.3.2 | Обновление одного файла | code_indexer.py | Удалить старые заряды этого файла из индекса, переиндексировать файл |
| 4.3.3 | Дебаунс | code_indexer.py | 1–2 сек после последнего события |
| 4.3.4 | CLI --watch | code_indexer.py | python code_indexer.py --watch --workspace path |

### 4.4. Codebase graph

| Шаг | Действие | Файл | Детали |
|-----|----------|------|--------|
| 4.4.1 | Парсинг импортов | code_indexer.py | Из ast: import X, from Y import Z. Словарь {file: [imported_modules]} |
| 4.4.2 | Граф | code_indexer.py | networkx или dict: nodes=files, edges=imports. Дополнительно: вызовы функций (сложнее, нужен deeper parsing) |
| 4.4.3 | who_uses(symbol) | code_indexer.py | Обратный граф: кто импортирует этот модуль |
| 4.4.4 | API /code/graph | deepseek_gateway.py | GET /code/graph?file=... — вернуть граф для визуализации (JSON nodes, edges) |

### 4.5. Интеграция в tools

| Шаг | Действие | Файл | Детали |
|-----|----------|------|--------|
| 4.5.1 | search_code в tools.py | tools.py | Новый tool: search_code(query, k). Вызов code_indexer.search_code |
| 4.5.2 | TOOL_DEFINITIONS | tools.py | Добавить search_code в список tools для Planner |

---

## Фаза 5: Расширение VS Code (Hillhorn Chat)

**Цель:** Панель чата в сайдбаре VS Code, WebSocket к Gateway.

**Оценка:** 20–24 часа

### 5.1. Создание расширения

| Шаг | Действие | Путь | Детали |
|-----|----------|------|--------|
| 5.1.1 | Создать папку | c:\Hillhorn\vscode-ext-hillhorn\ | Стандартная структура VS Code extension |
| 5.1.2 | package.json | package.json | name: hillhorn-chat, activationEvents: onView:hillhornChat, contributes: viewsContainers, views |
| 5.1.3 | extension.ts | src/extension.ts | activate: register TreeView или Webview для чата |
| 5.1.4 | Конфигурация | package.json | contributes.configuration: hillhorn.gatewayUrl, hillhorn.workspaceId |

### 5.2. Webview Chat UI

| Шаг | Действие | Файл | Детали |
|-----|----------|------|--------|
| 5.2.1 | ChatWebview | src/chatWebview.ts | vscode.WebviewPanel, html с textarea + кнопка Send, область сообщений |
| 5.2.2 | Стили | inline в html или отдельный css | Минималистичный чат: сообщения user/assistant, скролл |
| 5.2.3 | Отправка запроса | chatWebview.ts | fetch POST http://gatewayUrl/v1/agent/query с JSON {agent_type, prompt, context} |
| 5.2.4 | Отображение ответа | chatWebview.ts | Парсинг JSON, добавление в DOM. Поддержка markdown (marked или vscode.markdownString) |

### 5.3. WebSocket для стриминга (опционально в этой фазе)

| Шаг | Действие | Файл | Детали |
|-----|----------|------|--------|
| 5.3.1 | SSE endpoint | deepseek_gateway.py | POST /v1/agent/query/stream — возвращает StreamResponse с SSE. То же что /query но stream=True для всех моделей |
| 5.3.2 | Чтение SSE в расширении | chatWebview.ts | fetch с ReadableStream, парсинг data: строк, обновление UI по мере поступления |

### 5.4. Интеграция в форк VS Code

| Шаг | Действие | Путь | Детали |
|-----|----------|------|--------|
| 5.4.1 | Копирование в extensions | vscode/extensions/hillhorn-chat/ | Или разработка как отдельное расширение, устанавливаемое в собранный VS Code |
| 5.4.2 | Добавить в product.json | vscode/ | extensions: ["hillhorn-chat"] если встраиваем |
| 5.4.3 | Тестирование | — | F5 launch Extension Development Host, открыть Hillhorn Chat в сайдбаре |

---

## Фаза 6: UI — стриминг, контекст, Apply edits

**Оценка:** 10–12 часов

### 6.1. Стриминг в API

| Шаг | Действие | Файл | Детали |
|-----|----------|------|--------|
| 6.1.1 | Параметр stream в AgentRequest | deepseek_gateway.py | stream: bool = False |
| 6.1.2 | Эндпоинт для стриминга | deepseek_gateway.py | При stream=True — не ждать полный ответ, отдать StreamResponse. Для non-reasoner — включить stream в DeepSeek, итерировать chunks, yield SSE |
| 6.1.3 | Формат SSE | deepseek_gateway.py | data: {"content": "chunk", "done": false}\n\n |
| 6.1.4 | Интеграция в расширение | chatWebview.ts | При вызове — stream=true, обрабатывать SSE, обновлять сообщение по мере поступления |

### 6.2. Контекст из редактора

| Шаг | Действие | Файл | Детали |
|-----|----------|------|--------|
| 6.2.1 | Сбор контекста | chatWebview.ts или extension | vscode.window.activeTextEditor — document.getText(), selection. Список открытых редакторов |
| 6.2.2 | Передача в запрос | extension | context: [{role: "user", content: "Current file:\n```\n"+text+"\n```\nSelection: "+selection}] или system message |
| 6.2.3 | Параметр include_context | AgentRequest | include_context: bool. Если true — Gateway ожидает context от клиента; иначе — пусто |

### 6.3. Apply edits

| Шаг | Действие | Файл | Детали |
|-----|----------|------|--------|
| 6.3.1 | Кнопка "Apply" в UI | chatWebview | При наличии code block в ответе — кнопка "Insert at cursor" |
| 6.3.2 | vscode.WorkspaceEdit | extension | Получить активный editor, applyEdit с заменой selection на код или insert в позицию курсора |
| 6.3.3 | Парсинг code block | extension | Из markdown извлечь ```lang\ncode\n``` |

### 6.4. Inline-подсказки (Copilot-like)

| Шаг | Действие | Файл | Детали |
|-----|----------|------|--------|
| 6.4.1 | InlineCompletionItemProvider | extension | vscode.languages.registerInlineCompletionItemProvider. При triggered — отправить контекст (строки выше курсора) в Gateway, модель chat, prompt "complete this", вернуть InlineCompletionItem |
| 6.4.2 | Дебаунс | extension | 300–500 ms после последнего ввода |
| 6.4.3 | Ограничение контекста | extension | Передавать последние 20–30 строк, ~1k токенов |

**Сложность:** Inline completion требует низкой латентности. DeepSeek API может быть медленнее Copilot. Рассмотреть локальную модель (Ollama) для inline.

---

## Фаза 7: Git и терминал

**Оценка:** 8–10 часов

### 7.1. Git-контекст

| Шаг | Действие | Файл | Детали |
|-----|----------|------|--------|
| 7.1.1 | git_status(), git_diff(), git_log() | tools.py или git_context.py | subprocess.run(["git", "status"], cwd=workspace), git diff, git log -5 --oneline |
| 7.1.2 | Tool git_context | tools.py | get_git_context() -> {status, diff, recent_commits}. Возвращать текст для промпта |
| 7.1.3 | Автодобавление в промпт | deepseek_gateway.py или extension | При agent_type=chat/coder — опционально добавлять git_context в system message |
| 7.1.4 | API /git/context | deepseek_gateway.py | GET /git/context?workspace=... — для расширения |

### 7.2. Commit message generation

| Шаг | Действие | Файл | Детали |
|-----|----------|------|--------|
| 7.2.1 | Tool generate_commit_message | tools.py | Вход: diff. Вызов call_agent("chat", "Generate conventional commit message for:\n"+diff) |
| 7.2.2 | Команда в VS Code | extension | "Hillhorn: Generate commit message" — показать diff, вызвать tool, вставить в git input |

### 7.3. Терминал в UI

| Шаг | Действие | Файл | Детали |
|-----|----------|------|--------|
| 7.3.1 | Панель Terminal в расширении | extension | vscode.window.createTerminal или создать Webview с псевдо-терминалом (сложнее) |
| 7.3.2 | Простой вариант | extension | Кнопка "Run in terminal" — vscode.commands.executeCommand("workbench.action.terminal.new"), затем sendText |
| 7.3.3 | Execute command от агента | tools.py | execute_command уже есть. Добавить в UI отображение вывода — нужен способ передать stdout обратно в чат. Tool возвращает {stdout, stderr}, агент может включить в ответ |

---

## Фаза 8: Надёжность и производительность

**Оценка:** 10–12 часов

### 8.1. Fallback-модели

| Шаг | Действие | Файл | Детали |
|-----|----------|------|--------|
| 8.1.1 | При ошибке reasoner | deepseek_gateway.py | except в _call_deepseek_stream: retry с model=CHAT_MODEL, messages без reasoning |
| 8.1.2 | Конфиг | .env | DEEPSEEK_FALLBACK_MODEL=deepseek-chat |
| 8.1.3 | Логирование fallback | _log_to_nwf | label["fallback_used"] = True |

### 8.2. Кэш запросов

| Шаг | Действие | Файл | Детали |
|-----|----------|------|--------|
| 8.2.1 | Кэш | deepseek_gateway.py | lru_cache или dict: key=hash(agent_type+last_user_message), value=response. TTL 5 мин |
| 8.2.2 | Параметр skip_cache | AgentRequest | skip_cache: bool. Для стриминга — skip_cache |
| 8.2.3 | Размер кэша | Конфиг | CACHE_MAX_SIZE=100 |

### 8.3. Очередь при rate limit

| Шаг | Действие | Файл | Детали |
|-----|----------|------|--------|
| 8.3.1 | asyncio.Queue | deepseek_gateway.py | Очередь запросов. Worker берет из очереди, при 429 — put обратно с delay |
| 8.3.2 | Семафор | deepseek_gateway.py | Ограничить параллельные запросы к API (например 3) |
| 8.3.3 | Конфиг | .env | DEEPSEEK_MAX_CONCURRENT=3 |

### 8.4. Автовыбор агента

| Шаг | Действие | Файл | Детали |
|-----|----------|------|--------|
| 8.4.1 | Параметр auto_agent | AgentRequest | auto_agent: bool = False. Если True — игнорировать agent_type, вызвать select_agent_from_memory |
| 8.4.2 | В agent_query | deepseek_gateway.py | if req.auto_agent: agent_type = select_agent_from_memory(NWF_MEMORY_PATH, req.prompt) |
| 8.4.3 | Расширение | extension | Чекбокс "Auto-select agent" в UI |

---

## Фаза 9: Проекты и workspace

**Оценка:** 6–8 часов

### 9.1. Multi-workspace

| Шаг | Действие | Файл | Детали |
|-----|----------|------|--------|
| 9.1.1 | Список workspaces | Конфиг или API | Хранить в data/workspaces.json: [{id, path, name}] |
| 9.1.2 | API /workspaces | deepseek_gateway.py | CRUD workspaces |
| 9.1.3 | Выбор workspace в расширении | extension | vscode.workspace.workspaceFolders или настройка hillhorn.workspacePath |
| 9.1.4 | Переключение | extension | Команда "Hillhorn: Switch workspace" |

### 9.2. Правила проекта (.cursorrules)

| Шаг | Действие | Файл | Детали |
|-----|----------|------|--------|
| 9.2.1 | Чтение .cursorrules | tools.py или отдельный | При workspace — прочитать .cursorrules, .cursor/rules/*.md |
| 9.2.2 | Добавление в system prompt | deepseek_gateway.py | SYSTEM_PROMPTS[agent] + "\n\nProject rules:\n" + rules_content |
| 9.2.3 | Конфиг | .env | CURSOR_RULES_PATH (по умолчанию .cursorrules) |

### 9.3. Профили

| Шаг | Действие | Файл | Детали |
|-----|----------|------|--------|
| 9.3.1 | PROFILES | deepseek_gateway.py | {"backend": "...", "frontend": "...", "docs": "..."} — доп. system prompts |
| 9.3.2 | Параметр profile | AgentRequest | profile: Optional[str] |
| 9.3.3 | Выбор в UI | Settings | Dropdown profile |

---

## Фаза 10: Наблюдаемость и настройки

**Оценка:** 8–10 часов

### 10.1. Логи запросов

| Шаг | Действие | Файл | Детали |
|-----|----------|------|--------|
| 10.1.1 | In-memory log | deepseek_gateway.py | deque(maxlen=500): [{timestamp, agent_type, prompt_preview, model, tokens, latency, success}] |
| 10.1.2 | API /logs | deepseek_gateway.py | GET /logs?limit=50&agent=... |
| 10.1.3 | Страница /logs в Settings | deepseek_gateway.py | HTML таблица с логами |

### 10.2. Выбор модели в настройках

| Шаг | Действие | Файл | Детали |
|-----|----------|------|--------|
| 10.2.1 | Форма в /settings | deepseek_gateway.py | Поля: DEEPSEEK_CHAT_MODEL, DEEPSEEK_CODER_MODEL (опционально переопределить) |
| 10.2.2 | Сохранение в .env | _save_api_key_to_env | Расширить до _save_settings — записывать все настройки |

### 10.3. Метрики

| Шаг | Действие | Файл | Детали |
|-----|----------|------|--------|
| 10.3.1 | Подсчёт по дням | deepseek_gateway.py | Словарь date -> {requests, tokens, by_agent} |
| 10.3.2 | API /metrics | deepseek_gateway.py | GET /metrics — агрегированная статистика |
| 10.3.3 | Дашборд HTML | deepseek_gateway.py | /metrics/page — простой HTML с цифрами |

### 10.4. Расширенный health check

| Шаг | Действие | Файл | Детали |
|-----|----------|------|--------|
| 10.4.1 | GET /health/detailed | deepseek_gateway.py | Проверить: Gateway OK, NWF field loadable, при возможности — ping OpenClaw 18789, Adapter (нет API — пропуск) |
| 10.4.2 | Статус каждого сервиса | Ответ JSON | {gateway: "ok", nwf: "ok", openclaw: "reachable"|"unreachable"} |

---

## Фаза 11: Дополнительно (уровень выше Cursor)

**Оценка:** 16–24 часа

### 11.1. JEPA uncertainty в UI

| Шаг | Действие | Файл | Детали |
|-----|----------|------|--------|
| 11.1.1 | Возврат sigma, alpha в ответе | deepseek_gateway.py | Для запросов через JEPA — predict() возвращает z, sigma, alpha. Добавить в AgentResponse: uncertainty: {sigma_mean, alpha_mean} |
| 11.1.2 | Интеграция JEPA в цепочку | deepseek_gateway.py | Опционально: перед запросом — jepa.predict(), если sigma высокий — добавить в system "Low confidence, consider asking for clarification" |
| 11.1.3 | Отображение в UI | extension | Badge "High uncertainty" если sigma > threshold |
| 11.1.4 | Визуализация | extension | Индикатор уверенности (цвет, иконка) |

### 11.2. Локальные модели (Ollama)

| Шаг | Действие | Файл | Детали |
|-----|----------|------|--------|
| 11.2.1 | Ollama-клиент | ollama_gateway.py или в deepseek_gateway | Отдельный роут или fallback. API Ollama: POST localhost:11434/api/generate |
| 11.2.2 | Конфиг | .env | OLLAMA_MODEL=codellama, OLLAMA_ENABLED=true. Использовать для inline completion, простых запросов |
| 11.2.3 | Маршрутизация | deepseek_gateway.py | При запросе с flag use_local или для inline — Ollama. Иначе DeepSeek |
| 11.2.4 | Оценка размера | — | codellama ~4GB, маленькие модели 1–2GB |

### 11.3. Командная память (Shared NWF)

| Шаг | Действие | Файл | Детали |
|-----|----------|------|--------|
| 11.3.1 | Shared storage | Конфиг | NWF_SHARED_PATH — сетевая папка или S3-совместимое хранилище |
| 11.3.2 | Merge при загрузке | nwf_memory_utils | Загружать local + shared, merge по id или по timestamp |
| 11.3.3 | Синхронизация | Отдельный сервис | Периодический push/pull в shared. Конфликты — last-write-wins |
| 11.3.4 | Права доступа | — | Только чтение shared для рядовых, запись для админов |

**Сложность:** Требует инфраструктуры (NFS, S3, или свой sync-сервер).

### 11.4. Плагины

| Шаг | Действие | Файл | Детали |
|-----|----------|------|--------|
| 11.4.1 | Plugin API | plugins/ | Интерфейс: class HillhornPlugin: async def register_tools() -> List[ToolDef], async def on_request(ctx) |
| 11.4.2 | Загрузка плагинов | deepseek_gateway.py | Сканировать plugins/*.py или config plugins: ["plugin_a"], import, register |
| 11.4.3 | Custom tools | plugins | Плагин возвращает свои tool definitions, execute_tool вызывает plugin.handle_tool_call |
| 11.4.4 | Custom encoders | plugins | Плагин может предоставить get_embedding_override |
| 11.4.5 | Пример плагина | plugins/example/ | Минимальный плагин с одним tool |

---

## Сводная таблица по фазам

| Фаза | Название | Часы | Зависимости |
|------|----------|------|-------------|
| 1 | Function Calling | 12–16 | — |
| 2 | Управление памятью | 8–10 | — |
| 3 | Семантические эмбеддинги | 6–8 | sentence-transformers |
| 4 | Индексирование кода | 16–20 | Фаза 3 |
| 5 | VS Code расширение | 20–24 | — |
| 6 | UI стриминг, контекст, Apply | 10–12 | Фаза 5 |
| 7 | Git и терминал | 8–10 | Фаза 5 |
| 8 | Надёжность | 10–12 | — |
| 9 | Проекты и workspace | 6–8 | — |
| 10 | Наблюдаемость | 8–10 | — |
| 11 | Дополнительно | 16–24 | Фазы 1–5 |
| **Итого** | | **130–166** | |

---

## Рекомендуемый порядок внедрения

1. **Фаза 1** (Function Calling) — база автономности
2. **Фаза 2** (Очистка памяти) — предотвращение разрастания
3. **Фаза 8** (Fallback, кэш) — стабильность
4. **Фаза 5** (Расширение VS Code) — основной UI
5. **Фаза 6** (Стриминг, Apply edits) — UX
6. **Фаза 3** (Эмбеддинги) — качество
7. **Фаза 4** (Индексация кода) — codebase intelligence
8. **Фаза 7** (Git) — workflow
9. **Фаза 9** (Workspace) — мультипроект
10. **Фаза 10** (Наблюдаемость) — операционная зрелость
11. **Фаза 11** (Дополнительно) — дифференциация
