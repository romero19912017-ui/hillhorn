# -*- coding: utf-8 -*-
"""Инструменты для вызова: search_memory, read_file, write_file, execute_command, call_agent."""

from __future__ import annotations

import subprocess
import shlex
import os
from contextvars import ContextVar
from pathlib import Path
from collections import OrderedDict
from typing import Any, Dict, List, Optional

# Корень проекта и рабочая директория
ROOT = Path(__file__).resolve().parent
WORKSPACE = Path(os.getenv("MOLTBOT_WORKSPACE", str(ROOT / "workspace")))
_workspace_override: ContextVar[Optional[Path]] = ContextVar("workspace_override", default=None)


def _get_workspace() -> Path:
    ov = _workspace_override.get()
    return ov if ov is not None else WORKSPACE


def set_workspace_override(path: Optional[str]) -> None:
    """Установить переопределение рабочей директории (для Gateway)."""
    _workspace_override.set(Path(path) if (path and path.strip()) else None)

# Хранилище на C:\hillhorn_data (переменная HILLHORN_DATA_ROOT)
_DATA_ROOT = Path(os.getenv("HILLHORN_DATA_ROOT", "C:/hillhorn_data"))
NWF_MEMORY_PATH = Path(os.getenv("NWF_MEMORY_PATH", str(_DATA_ROOT / "deepseek_memory")))
GATEWAY_URL = os.getenv("DEEPSEEK_GATEWAY_URL", "http://localhost:8001")
EMBED_DIM = 32
CMD_TIMEOUT = 60

# Разрешённые команды (белый список)
ALLOWED_CMDS = frozenset([
    "python", "python3", "py", "pip", "npm", "npx", "pnpm", "node", "yarn",
    "git", "pytest", "cargo", "uvicorn", "gulp", "tsc",
])
# Опасные паттерны — запрещены в командах
DANGEROUS_PATTERNS = ("rm -rf", "del /f", "format", "> /dev/sd", "&&", "|", ";", "`")

# Lazy load + session cache (HILLHORN_OPTIMIZATION_PLAN)
_nwf_field_cache: Optional[tuple] = None  # (Field, path_str)
SEARCH_CACHE_MAX = int(os.getenv("HILLHORN_SEARCH_CACHE_MAX", "100"))
_search_cache: OrderedDict = OrderedDict()
_cache_hits = 0
_cache_misses = 0


def _invalidate_nwf_cache() -> None:
    """Сброс кеша NWF при add_to_memory."""
    global _nwf_field_cache, _search_cache
    _nwf_field_cache = None
    _search_cache.clear()


def get_cache_stats() -> Dict[str, Any]:
    """Метрики кеша поиска."""
    total = _cache_hits + _cache_misses
    return {
        "hits": _cache_hits,
        "misses": _cache_misses,
        "hit_rate": _cache_hits / total if total > 0 else 0.0,
        "size": len(_search_cache),
    }


def _get_field(fp: Path):
    """Ленивая загрузка Field. Кеш инвалидируется при add_to_memory."""
    global _nwf_field_cache
    fp_str = str(fp.resolve())
    if _nwf_field_cache is not None and _nwf_field_cache[1] == fp_str:
        return _nwf_field_cache[0]
    from nwf import Field
    field = Field()
    field.load(fp)
    _nwf_field_cache = (field, fp_str)
    return field


def _embed(text: str, dim: int = EMBED_DIM):
    """Единый эмбеддинг через модуль embeddings."""
    from embeddings import get_embedding
    return get_embedding(text, dim=dim)


def _safe_path(path: str) -> Path:
    """Разрешение пути в пределах workspace. Ошибка при выходе за пределы."""
    ws = _get_workspace()
    p = Path(path)
    if not p.is_absolute():
        p = ws / p
    try:
        resolved = p.resolve()
        workspace_resolved = ws.resolve()
        if not str(resolved).startswith(str(workspace_resolved)):
            raise ValueError(f"Path outside workspace: {path}")
        return resolved
    except Exception as e:
        raise ValueError(f"Invalid path: {path}") from e


async def search_memory(
    query: str,
    k: int = 5,
    workspace_id: Optional[str] = None,
    kind_filter: Optional[List[str]] = None,
    recency_boost: bool = False,
) -> Dict[str, Any]:
    """Поиск по NWF-памяти. Симметричный Махаланобис (metric=symmetric)."""
    try:
        import numpy as np
        import time as _time
        from nwf import Charge, Field
        fp = NWF_MEMORY_PATH
        if not (fp / "meta.json").exists():
            return {"results": [], "error": "Memory not found"}
        cache_key = (query, workspace_id or "", k, frozenset(kind_filter or []), recency_boost)
        global _cache_hits, _cache_misses
        if cache_key in _search_cache:
            _search_cache.move_to_end(cache_key)
            _cache_hits += 1
            out = dict(_search_cache[cache_key])
            out["_cache_hit"] = True
            return out
        _cache_misses += 1
        field = _get_field(fp)
        if len(field) == 0:
            return {"results": []}
        # Запрос как Charge(z, sigma) для симметричного Махаланобиса
        qz = _embed(query)
        qsigma = np.full(EMBED_DIM, 0.2, dtype=np.float64)
        query_charge = Charge(z=qz, sigma=qsigma)
        search_k = min(k * 5, len(field))
        dists, indices = np.array([]), np.array([], dtype=np.int64)
        try:
            res = field.search(query_charge, k=search_k, metric="symmetric")
            dists = np.atleast_1d(res[0])
            indices = np.atleast_1d(res[1])
        except Exception:
            # Fallback: L2 при сбое (напр. 1 заряд в nwf)
            charges = field.get_charges()
            z_all = np.stack([c.z for c in charges], axis=0)
            d = np.linalg.norm(qz - z_all, axis=1)
            idx_sort = np.argsort(d)[:search_k]
            dists = d[idx_sort]
            indices = idx_sort
        labels_all = field.get_labels()

        def _get_kind(lab: dict) -> str:
            tags = lab.get("tags") or []
            return next((t for t in tags if t in ("doc", "code", "conversation")), "conversation")

        def _same_project(lab: dict, proj: Optional[str]) -> bool:
            if not proj:
                return True
            tags = lab.get("tags") or []
            has_any = any(t.startswith("project:") for t in tags)
            return not has_any or f"project:{proj}" in tags

        # agreement_ratio: доля k ближайших соседей с тем же kind/project (O(n) с кэшем)
        n_neigh = len(indices)
        agreement_cache: Dict[int, float] = {}
        if n_neigh > 0:
            kind_cache: Dict[int, str] = {}
            same_project_cache: Dict[int, bool] = {}
            for ji in indices:
                j = int(ji)
                if j < len(labels_all) and j not in kind_cache:
                    ll = labels_all[j]
                    if isinstance(ll, dict):
                        kind_cache[j] = _get_kind(ll)
                        same_project_cache[j] = _same_project(ll, workspace_id)
            for idx in indices:
                idx = int(idx)
                if idx >= len(labels_all):
                    continue
                kind_ref = kind_cache.get(idx)
                if kind_ref is None:
                    agreement_cache[idx] = 0.0
                    continue
                same = sum(
                    1
                    for ji in indices
                    if kind_cache.get(int(ji)) == kind_ref and same_project_cache.get(int(ji), False)
                )
                agreement_cache[idx] = same / n_neigh

        results = []
        project_tag = f"project:{workspace_id}" if workspace_id else None
        kind_set = frozenset(kind_filter) if kind_filter else None
        now_ts = _time.time()
        for j, i in enumerate(indices):
            i = int(i)
            if i >= len(labels_all):
                continue
            lab = labels_all[i]
            if not isinstance(lab, dict):
                continue
            tags = lab.get("tags") or []
            if project_tag:
                has_project = any(t.startswith("project:") for t in tags)
                if has_project and project_tag not in tags:
                    continue
            if kind_set:
                lab_kind = _get_kind(lab)
                if lab_kind not in kind_set:
                    continue
            d_val = float(dists[j]) if j < len(dists) else 0.0
            text = str(lab.get("content", lab.get("response_preview", lab.get("prompt", ""))))[:300]
            item = {"text": text, "agent_type": lab.get("agent_type", "memory"), "success": lab.get("success", True)}
            # Потенциал phi(r) = exp(-0.5 * d^2) для интерпретации/калибровки
            item["potential"] = round(float(np.exp(-0.5 * (d_val ** 2))), 4)
            item["agreement_ratio"] = round(agreement_cache.get(i, 0.0), 3)
            if recency_boost:
                ts = lab.get("ts", 0)
                score = d_val
                if ts:
                    age_hours = (now_ts - ts) / 3600
                    score *= 1.0 + age_hours * 0.05
                item["_score"] = score
            results.append(item)
        if recency_boost:
            results.sort(key=lambda r: r.get("_score", float("inf")))
            for r in results:
                r.pop("_score", None)
        out = {"results": results[:k]}
        while len(_search_cache) >= SEARCH_CACHE_MAX:
            _search_cache.popitem(last=False)
        _search_cache[cache_key] = out
        return out
    except Exception as e:
        return {"results": [], "error": str(e)}


async def add_to_memory(content: str, tags: Optional[List[str]] = None, project_id: Optional[str] = None) -> Dict[str, Any]:
    """Добавить контент в NWF-память. То же хранилище, что и search_memory."""
    try:
        from nwf import Charge, Field
        import numpy as np
        NWF_MEMORY_PATH.mkdir(parents=True, exist_ok=True)
        field = Field()
        if (NWF_MEMORY_PATH / "meta.json").exists():
            try:
                field.load(NWF_MEMORY_PATH)
            except Exception:
                pass
        z = _embed(content)
        sigma = np.full(EMBED_DIM, 0.2, dtype=np.float64)
        charge = Charge(z=z, sigma=sigma, alpha=1.0)
        tag_list = list(tags or [])
        if project_id:
            tag_list.append(f"project:{project_id}")
        import time as _t
        label = {"content": content[:500], "tags": tag_list, "ts": _t.time()}
        field.add(charge, labels=[label])
        field.save(NWF_MEMORY_PATH)
        _invalidate_nwf_cache()
        return {"status": "ok", "message": "Added to memory"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def read_file(path: str) -> Dict[str, Any]:
    """Чтение файла. Путь относительно workspace."""
    try:
        p = _safe_path(path)
        if not p.exists():
            return {"error": f"File not found: {path}"}
        if not p.is_file():
            return {"error": f"Not a file: {path}"}
        content = p.read_text(encoding="utf-8", errors="replace")
        return {"content": content, "path": str(p.relative_to(_get_workspace()))}
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}


async def write_file(path: str, content: str, overwrite: bool = False) -> Dict[str, Any]:
    """Запись в файл. Путь относительно workspace."""
    try:
        p = _safe_path(path)
        if p.exists() and not overwrite:
            return {"error": f"File exists. Use overwrite=true to replace."}
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"status": "ok", "path": str(p.relative_to(_get_workspace()))}
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}


def _check_command_safe(command: str) -> bool:
    """Проверить, что команда безопасна: в белом списке, без опасных паттернов."""
    for pat in DANGEROUS_PATTERNS:
        if pat in command:
            return False
    parts = shlex.split(command)
    if not parts:
        return False
    base = parts[0].lower()
    if "/" in base or "\\" in base:
        base = Path(parts[0]).name.lower()
    return base in ALLOWED_CMDS


async def execute_command(command: str, cwd: Optional[str] = None) -> Dict[str, Any]:
    """Выполнение команды в shell. Белый список: python, npm, git, pytest и др. Без пайпов и редиректов."""
    if not _check_command_safe(command):
        return {"error": "Command not allowed. Whitelist: python, npm, git, pytest, pip, node, etc."}
    try:
        work_dir = _get_workspace()
        if cwd:
            work_dir = _safe_path(cwd)
        parts = shlex.split(command)
        result = subprocess.run(
            parts,
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            timeout=CMD_TIMEOUT,
        )
        return {
            "stdout": result.stdout or "",
            "stderr": result.stderr or "",
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Command timed out after {CMD_TIMEOUT}s", "stdout": "", "stderr": "", "returncode": -1}
    except Exception as e:
        return {"error": str(e), "stdout": "", "stderr": "", "returncode": -1}


async def git_status(cwd: Optional[str] = None) -> Dict[str, Any]:
    """Получить статус git. cwd — путь относительно workspace."""
    return await execute_command("git status --short", cwd=cwd)


async def git_diff(cwd: Optional[str] = None, file_path: Optional[str] = None) -> Dict[str, Any]:
    """Получить git diff. Опционально file_path для конкретного файла."""
    cmd = "git diff" + (f" -- {file_path}" if file_path else "")
    return await execute_command(cmd, cwd=cwd)


async def git_log(cwd: Optional[str] = None, n: int = 10) -> Dict[str, Any]:
    """Получить последние n записей git log."""
    return await execute_command(f"git log -{n} --oneline", cwd=cwd)


async def search_code(query: str, k: int = 10, workspace_id: Optional[str] = None) -> Dict[str, Any]:
    """Поиск по индексированному коду по семантическому сходству."""
    try:
        from code_indexer import CodeIndexer
        ws = _get_workspace() if not workspace_id else _get_workspace() / workspace_id
        if not ws.exists():
            return {"results": [], "error": f"Workspace not found"}
        indexer = CodeIndexer(ws)
        results = indexer.search_code(query, k=k)
        return {"results": results}
    except Exception as e:
        return {"results": [], "error": str(e)}


async def call_agent(agent_type: str, prompt: str) -> Dict[str, Any]:
    """Вызов агента (coder, reviewer, chat, planner)."""
    import httpx
    allowed = {"coder", "reviewer", "chat", "planner", "architect", "documenter"}
    if agent_type not in allowed:
        return {"error": f"Unknown agent: {agent_type}"}
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                f"{GATEWAY_URL.rstrip('/')}/v1/agent/query",
                json={"agent_type": agent_type, "prompt": prompt, "max_tokens": 2048},
            )
        if r.status_code != 200:
            return {"error": f"Gateway error: {r.status_code}", "content": ""}
        data = r.json()
        return {"content": data.get("content", ""), "model_used": data.get("model_used", "")}
    except Exception as e:
        return {"error": str(e), "content": ""}


# Сопоставление имён инструментов с функциями
TOOL_MAP = {
    "search_memory": search_memory,
    "add_to_memory": add_to_memory,
    "read_file": read_file,
    "write_file": write_file,
    "execute_command": execute_command,
    "call_agent": call_agent,
    "search_code": search_code,
    "git_status": git_status,
    "git_diff": git_diff,
    "git_log": git_log,
}

# Определения инструментов для DeepSeek (function calling)
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_memory",
            "description": "Search similar past requests in memory. Use before answering to find relevant context.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "k": {"type": "integer", "default": 5},
                    "workspace_id": {"type": "string", "description": "Project/workspace path for scoping search"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_memory",
            "description": "Add information to long-term memory for future reference.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "project_id": {"type": "string", "description": "Project/workspace path for scoping"},
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read file content. Path is relative to workspace.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to file. Path relative to workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                    "overwrite": {"type": "boolean", "default": False},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": "Run shell command (python, npm, git, pytest, etc). No pipes or redirects.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}, "cwd": {"type": "string"}},
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_status",
            "description": "Get git status (short format).",
            "parameters": {"type": "object", "properties": {"cwd": {"type": "string"}}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_diff",
            "description": "Get git diff. Optionally specify file_path for single file.",
            "parameters": {
                "type": "object",
                "properties": {"cwd": {"type": "string"}, "file_path": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_log",
            "description": "Get last n git log entries (oneline).",
            "parameters": {
                "type": "object",
                "properties": {"cwd": {"type": "string"}, "n": {"type": "integer", "default": 10}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": "Search codebase by semantic similarity. Index first via code_indexer.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}, "k": {"type": "integer", "default": 10}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "call_agent",
            "description": "Call another agent: coder (code gen), reviewer (code review), planner (planning), chat (general).",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_type": {"type": "string", "enum": ["coder", "reviewer", "planner", "chat", "architect", "documenter"]},
                    "prompt": {"type": "string"},
                },
                "required": ["agent_type", "prompt"],
            },
        },
    },
]
