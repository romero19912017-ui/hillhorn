# Сборка Hillhorn VS Code в Docker (Windows 11)

Сборка VS Code в Linux-контейнере. Результат — платформо-независимый JS; нативные модули пересобираются на хост-машине Windows.

## Требования

- Docker Desktop (бэкенд WSL2)
- Windows 11

## 1. Установка Docker

```powershell
# От имени администратора
.\scripts\install_docker.ps1
```

Перезагрузите ПК, запустите Docker Desktop.

## 2. Подготовка (один раз)

```powershell
.\scripts\prepare_docker.ps1
```

Проверяет: Docker, демон, загружает образ node:22, валидирует проект.

## 3. Сборка VS Code

```powershell
.\scripts\build_vscode_docker.ps1
```

Или через compose:

```powershell
docker compose -f docker/docker-compose.yml run --rm vscode-build
```

Длительность: 15–30 мин (первый запуск).

## 4. Нативные модули на Windows

После сборки в Docker на хост-машине:

```powershell
cd vscode
npm install
```

Пересобирает нативные модули для Windows. Если node-gyp не работает, установите [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) с рабочей нагрузкой C++.

## 5. Запуск

```powershell
.\scripts\code.bat
```
