# Docker Build for Hillhorn VS Code (Windows 11)

Build VS Code in Linux container. Output is platform-agnostic JS; native modules rebuilt on Windows host.

## Prerequisites

- Docker Desktop (WSL2 backend)
- Windows 11

## 1. Install Docker

```powershell
# As Administrator
.\scripts\install_docker.ps1
```

Restart PC, start Docker Desktop.

## 2. Prepare (run once)

```powershell
.\scripts\prepare_docker.ps1
```

Checks: Docker, daemon, pulls node:22 image, validates project.

## 3. Build VS Code

```powershell
.\scripts\build_vscode_docker.ps1
```

Or via compose:
```powershell
docker compose -f docker/docker-compose.yml run --rm vscode-build
```

Duration: 15-30 min (first run).

## 4. Windows Native Modules

After Docker build, on host:

```powershell
cd vscode
npm install
```

Rebuilds native modules for Windows. If node-gyp fails, install [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) with C++ workload.

## 5. Run

```powershell
.\scripts\code.bat
```
