# Hillhorn: Рапорт о готовности к сборке среды разработки (форк VS Code)

**Дата:** 2026-03-11  
**Цель:** Собрать среду разработки на базе форка VS Code с Hillhorn (DeepSeek + NWF-JEPA).

---

## 1. Итоговый вердикт

| Статус | Описание |
|--------|----------|
| **Частично готово** | Python-ядро и расширение работают. Сборка форка VS Code **не проходит** из-за несовместимости Node.js 24 с TypeScript. |

---

## 2. Компоненты: готовность

### 2.1 Python-ядро (готово)

| Компонент | Статус | Путь |
|-----------|--------|------|
| DeepSeek Gateway | OK | `deepseek_gateway.py` |
| Агенты (Coder, Planner, Reviewer, Architect, Documenter, TesterMath) | OK | `agents.py` |
| Function calling (tools) | OK | `tools.py`, интеграция в gateway |
| NWF-память, auto_agent | OK | `deepseek_gateway.py` |
| embeddings.py | OK | `embeddings.py` |
| code_indexer.py | OK | `code_indexer.py` |
| nwf_memory_utils (prune, export, import) | OK | `nwf_memory_utils.py` |
| NWF Memory Adapter | OK | `nwf_memory_adapter.py` |
| nwf-core | OK | `pip install -e nwf-core[faiss]` |

**Тесты:** `.\scripts\test.ps1` — все 6 шагов проходят.

---

### 2.2 Расширение Hillhorn Chat (готово)

| Элемент | Статус |
|---------|--------|
| package.json | OK |
| WebviewView в сайдбаре | OK |
| HTTP к Gateway (localhost:8001) | OK |
| Конфиг gatewayUrl, workspaceId, agentType, autoAgent | OK |
| Компиляция `npm run compile` | OK |
| Копирование в vscode/extensions/hillhorn-chat | OK (скрипт install_all.ps1) |

**Расширение** лежит в `vscode/extensions/hillhorn-chat/` и будет загружаться при запуске форка.

---

### 2.3 Форк VS Code (не готов)

| Элемент | Статус | Проблема |
|---------|--------|----------|
| node_modules | OK | npm install выполнен |
| gulp-cli | OK | Установлен |
| build/ (ternary-stream и др.) | OK | npm install в build/ |
| npm run compile | **FAIL** | TypeScript/Node несовместимость |
| out/main.js | **Нет** | Сборка не завершается |

**Ошибка при `npm run compile`:**
```
SyntaxError: missing ) after argument list
    at wrapSafe (node:internal/modules/cjs/loader:1692:18)
```
Происходит при загрузке `typescript.js` — типично для Node.js 24.x и более старых версий TypeScript в VS Code.

---

### 2.4 Инфраструктура

| Элемент | Статус |
|---------|--------|
| .env (DEEPSEEK_API_KEY) | OK |
| venv_hillhorn | OK |
| workspace | OK |
| scripts/build.ps1 | OK |
| scripts/install_all.ps1 | OK |
| scripts/start_all.ps1 | OK |
| scripts/test.ps1 | OK |

---

## 3. Что нужно для полной сборки

### 3.1 Критично: Node.js 20

**Проблема:** Текущий Node.js 24.x вызывает ошибку при сборке TypeScript/VS Code.

**Решение:**
1. Установить Node.js 20 LTS:
   ```powershell
   winget install OpenJS.NodeJS.20
   ```
2. Или использовать fnm/nvm:
   ```powershell
   fnm install 20
   fnm use 20
   ```
3. Перезапустить терминал, проверить:
   ```powershell
   node -v   # v20.x.x
   ```
4. Запустить сборку:
   ```powershell
   cd c:\Hillhorn\vscode
   npm run compile
   ```

**Примечание:** `winget install OpenJS.NodeJS.20` может конфликтовать с уже установленным Node 24 (код 1603). В этом случае использовать fnm/nvm или переустановить Node 20 вручную.

---

### 3.2 После успешной сборки VS Code

1. **Запуск в режиме web:**
   ```powershell
   cd c:\Hillhorn\vscode
   npm run watch-web   # терминал 1
   npm run compile-web # или gulp web
   ```

2. **Или Electron (desktop):**
   ```powershell
   npm run watch
   npm run electron
   ```

3. **Запуск бэкенда Hillhorn:**
   ```powershell
   .\scripts\start_all.ps1
   ```

4. **Проверка:** Открыть Hillhorn Chat в сайдбаре (иконка Hillhorn в Activity Bar).

---

### 3.3 Опционально: Spectre-mitigated libs

Если при сборке появится MSB8040:
- Установить компонент **Spectre-mitigated libraries** в Visual Studio Build Tools.

---

## 4. План действий (чеклист)

- [ ] Переключиться на Node.js 20 (fnm/nvm или установка)
- [ ] `cd vscode && npm run compile` — должна пройти без ошибок
- [ ] Проверить наличие `vscode/out/main.js`
- [ ] Запустить `npm run watch-web` + `npm run compile-web` (или `gulp web`)
- [ ] Запустить `.\scripts\start_all.ps1` (Gateway + Adapter)
- [ ] Открыть среду в браузере/Electron и проверить панель Hillhorn Chat

---

## 5. Альтернатива: использование без сборки форка

Можно работать **без сборки форка VS Code**:

1. Использовать **обычный VS Code** (установленный).
2. Открыть папку `vscode-ext-hillhorn` и нажать F5 (Extension Development Host).
3. Запустить Gateway: `.\scripts\start_all.ps1`.
4. Hillhorn Chat будет доступен в Development Host.

---

## 6. Резюме

| Что готово | Что не готово |
|------------|---------------|
| Python-ядро (Gateway, агенты, tools, память) | Сборка форка VS Code (Node 24) |
| Расширение Hillhorn Chat (скомпилировано, скопировано) | — |
| Скрипты установки и тестов | — |
| Интеграция расширения в форк (папка extensions) | — |

**Блокер:** переход на Node.js 20 для успешной сборки форка VS Code.
