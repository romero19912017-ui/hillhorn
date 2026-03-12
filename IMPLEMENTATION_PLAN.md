# Hillhorn — детальный план реализации

![Hillhorn](emblem.png)

## MSB8040 (Spectre libs)

Ошибка VS Code: `для этого проекта требуются библиотеки с устранением рисков Spectre`.

Установить в Visual Studio Installer → Изменить → Отдельные компоненты:
- **MSVC v143 - VS 2022 C++ x64/x86 Spectre-mitigated libs**
- Или поиск: Spectre

---

## Этап 1. Сборка компонентов (сейчас)

### 1.1 Moltbot build
```powershell
# Через Git Bash (C:\Program Files\Git\bin\bash.exe):
& "C:\Program Files\Git\bin\bash.exe" -c "cd /c/Hillhorn/moltbot && pnpm run build"
```
Moltbot build завершён успешно.

### 1.2 VS Code
```powershell
cd C:\Hillhorn\vscode
npm install
npm run compile
```

### 1.3 OpenClaw CLI
```powershell
npm install -g openclaw
openclaw onboard
```

---

## Этап 2. Конфигурация

### 2.1 .env (C:\Hillhorn\.env)
```
DEEPSEEK_API_KEY=sk-xxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
NWF_MEMORY_PATH=data/deepseek_memory
NWF_MEMORY_ADAPTER_PATH=data/nwf_opencloud
MOLTBOT_WORKSPACE=C:\Hillhorn\workspace
```

### 2.2 OpenClaw config
Файл: `%USERPROFILE%\.config\openclaw\config.yaml`
```yaml
llm:
  provider: openai
  api_key: "sk-xxxx"
  base_url: "https://api.deepseek.com/v1"
  model: deepseek-chat
workspace: C:\Hillhorn\workspace
```

---

## Этап 3. Запуск сервисов

| # | Сервис | Команда | Порт |
|---|--------|---------|------|
| 1 | OpenClaw Gateway | `openclaw gateway start` | 18789 |
| 2 | DeepSeek Gateway | `uvicorn deepseek_gateway:app --port 8001` | 8001 |
| 3 | NWF Memory Adapter | `python nwf_memory_adapter.py --watch` | - |

---

## Этап 4. Интеграция OpenClaw + DeepSeek

Настроить OpenClaw на использование нашего Gateway вместо прямого вызова API:
- В config OpenClaw указать base_url: `http://localhost:8001` (если Gateway проксирует)
- Либо оставить прямой DeepSeek API в OpenClaw, наш Gateway — для агентов Hillhorn

---

## Этап 5. Интеграция NWF Memory

### 5.1 Workspace
- OpenClaw пишет в `C:\Hillhorn\workspace` (SOUL.md, USER.md, MEMORY.md, memory/*.md)
- NWF Adapter в --watch следит и синхронизирует в data/nwf_opencloud

### 5.2 Поиск
```powershell
python nwf_memory_adapter.py --search "функция сортировки" -k 5
```

---

## Этап 6. VS Code расширение (Hillhorn Chat)

1. Создать расширение в `C:\Hillhorn\vscode-ext-hillhorn\`
2. WebSocket клиент к OpenClaw Gateway (18789)
3. UI: панель чата в боковой панели
4. Отображение предсказаний JEPA (uncertainty)

---

## Этап 7. JEPA-селектор в цепочке

1. При запросе пользователя → CoderAgent/PlannerAgent
2. Перед вызовом DeepSeek: `select_agent_from_memory(request)` → выбирает агента по NWF
3. DeepSeek Gateway логирует в NWF каждый вызов

---

## Чеклист

- [x] Moltbot pnpm build
- [ ] VS Code npm install + compile
- [ ] openclaw onboard
- [ ] .env создан
- [ ] OpenClaw config.yaml
- [ ] Запуск 3 сервисов
- [ ] Тест: чат в OpenClaw UI
- [ ] Тест: nwf_memory_adapter --search
- [ ] VS Code расширение (отдельная задача)
