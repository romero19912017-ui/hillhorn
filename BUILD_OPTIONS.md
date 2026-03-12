# Варианты прохождения сборки VS Code (без снижения функциональности Hillhorn)

**Цель:** Сборка форка VS Code с расширением Hillhorn Chat при сохранении всех возможностей системы.

---

## Текущая проблема

- **Ошибка:** `SyntaxError: missing ) after argument list` в `typescript.js` при `npm run compile`
- **Причина:** Несовместимость `typescript ^6.0.0-dev.20260306` с текущими версиями Node.js (22, 24)
- **Функциональность Hillhorn:** Не затрагивается — она реализована в Python и в расширении

---

## Вариант 1: Development Container (рекомендуемый)

**Идея:** Сборка в Docker-окружении, заданном VS Code.

| Плюсы | Минусы |
|-------|--------|
| Точное окружение VS Code | Нужен Docker |
| Не нужно трогать систему | Первая сборка ~10–20 мин |
| Функциональность не меняется | |

**Шаги:**
1. Установить [Docker Desktop](https://www.docker.com/products/docker-desktop/) и [Remote - Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers).
2. В VS Code: `Remote-Containers: Open Folder in Container...` → выбрать `c:\Hillhorn\vscode`.
3. В контейнере: `npm run compile`, затем `./scripts/code-web` или `gulp web`.
4. Gateway и расширение Hillhorn продолжают работать как есть.

---

## Вариант 2: Откат TypeScript до стабильного 5.x

**Идея:** Заменить `typescript ^6.0.0-dev` на стабильный `typescript 5.6.x` или `5.7.x`.

| Плюсы | Минусы |
|-------|--------|
| Быстрое решение | Возможны несовместимости с API TS 6 |
| Не требует Docker | Нужно проверить сборку и поведение |

**Шаги:**
1. В `vscode/package.json` заменить:
   ```json
   "typescript": "^5.6.3"
   ```
   и убрать или заменить `@typescript/native-preview`, если он не нужен.
2. `cd vscode && rm -rf node_modules package-lock.json && npm install`
3. `npm run compile`

**Риск:** VS Code может использовать возможности TS 6; тогда появятся ошибки компиляции, которые придётся исправлять.

---

## Вариант 3: Обновление форка до актуального upstream

**Идея:** Синхронизировать форк с `microsoft/vscode` main — upstream может уже исправить проблему.

| Плюсы | Минусы |
|-------|--------|
| Официальные исправления | Возможные конфликты с изменениями Hillhorn |
| Актуальные зависимости | Нужен контроль merge |

**Шаги:**
1. `cd vscode && git remote add upstream https://github.com/microsoft/vscode.git` (если ещё нет).
2. `git fetch upstream && git merge upstream/main`.
3. `npm install && npm run compile`.
4. Проверить, что расширение `hillhorn-chat` остаётся в `extensions/` и компилируется.

---

## Вариант 4: Сборка через WSL2

**Идея:** Собирать VS Code в Linux-окружении WSL2, как в [документации VS Code](https://github.com/microsoft/vscode/wiki/Selfhosting-on-Windows-WSL).

| Плюсы | Минусы |
|-------|--------|
| Окружение, проверенное командой VS Code | Нужна настройка WSL2 |
| Другое поведение Node/TS | Пути и скрипты под Windows нужно адаптировать |

**Шаги:**
1. Установить WSL2 и Ubuntu.
2. В WSL: установить Node 22, клонировать/смонтировать `vscode`.
3. Сборка: `npm run compile`, `gulp web`.
4. Gateway и Python-сервисы Hillhorn — по-прежнему на Windows.

---

## Вариант 5: GitHub Codespaces

**Идея:** Собрать в облачном Codespace с готовым dev-контейнером VS Code.

| Плюсы | Минусы |
|-------|--------|
| Ничего не ставить локально | Нужен GitHub и подписка |
| Стабильное окружение | Работа в облаке |

**Шаги:**
1. Создать репозиторий на GitHub (или форк).
2. Codespaces: Create New Codespace.
3. В Codespace: `npm run compile`, затем нужные скрипты запуска.
4. Локально: только Gateway и Python-часть Hillhorn.

---

## Вариант 6: Отдельный stable-форк VS Code

**Идея:** Взять более старую ветку VS Code (например, 1.85 или 1.90), где ещё используется TypeScript 5.x.

| Плюсы | Минусы |
|-------|--------|
| Меньше шансов на конфликт с TS | Старая версия VS Code |
| Типичная стабильная сборка | Возможные отличия в API расширений |

**Шаги:**
1. Склонировать `https://github.com/microsoft/vscode` и переключиться на тег `1.85.0` или `1.90.0`.
2. Проверить `package.json`: скорее всего `typescript` 5.x.
3. Установить зависимости, собрать, встроить `hillhorn-chat`.

---

## Рекомендуемый порядок действий

1. **Сначала:** Вариант 1 (Development Container) — минимальные изменения в проекте, воспроизводимое окружение.
2. **Если Docker не подходит:** Вариант 2 (откат TypeScript) — быстрый эксперимент.
3. **Если нужна свежая сборка:** Вариант 3 (обновление до upstream).
4. **Для долгосрочной разработки:** Вариант 4 (WSL2) — типичный сценарий для Windows.

---

## Что не меняется при любом варианте

- Python-ядро (Gateway, агенты, tools, память, embeddings, code_indexer)
- Расширение Hillhorn Chat и его логика
- NWF Memory Adapter, OpenClaw
- Скрипты `start_all.ps1`, `test.ps1`, `install_all.ps1`
