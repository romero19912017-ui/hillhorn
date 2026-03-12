# -*- coding: utf-8 -*-
"""Tools for function calling: search_memory, read_file, write_file, execute_command, call_agent."""

from __future__ import annotations

import subprocess
import shlex
import os
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent
WORKSPACE = Path(os.getenv("MOLTBOT_WORKSPACE", str(ROOT / "workspace")))
_workspace_override: ContextVar[Optional[Path]] = ContextVar("workspace_override", default=None)


def _get_workspace() -> Path:
    ov = _workspace_override.get()
    return ov if ov is not None else WORKSPACE


def set_workspace_override(path: Optional[str]) -> None:
    _workspace_override.set(Path(path) if (path and path.strip()) else None)
NWF_MEMORY_PATH = Path(os.getenv("NWF_MEMORY_PATH", str(ROOT / "data" / "deepseek_memory")))
GATEWAY_URL = os.getenv("DEEPSEEK_GATEWAY_URL", "http://localhost:8001")
EMBED_DIM = 32
CMD_TIMEOUT = 60

ALLOWED_CMDS = frozenset([
    "python", "python3", "py", "pip", "npm", "npx", "pnpm", "node", "yarn",
    "git", "pytest", "cargo", "uvicorn", "gulp", "tsc",
])
DANGEROUS_PATTERNS = ("rm -rf", "del /f", "format", "> /dev/sd", "&&", "|", ";", "`")

def _embed(text: str, dim: int = EMBED_DIM):
    """Unified embedding via embeddings module."""
    from embeddings import get_embedding
    return get_embedding(text, dim=dim)


def _safe_path(path: str) -> Path:
    """Resolve path within workspace. Raise if outside."""
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
    """Search similar past requests in NWF memory. add_to_memory and search use same storage."""
    try:
        import numpy as np
        import time as _time
        from nwf import Field
        fp = NWF_MEMORY_PATH
        if not (fp / "meta.json").exists():
            return {"results": [], "error": "Memory not found"}
        field = Field()
        field.load(fp)
        if len(field) == 0:
            return {"results": []}
        qz = _embed(query)
        charges = field.get_charges()
        labels = field.get_labels()
        z_all = np.stack([c.z for c in charges], axis=0)
        d = np.linalg.norm(qz - z_all, axis=1)
        idx = np.argsort(d)[: min(k * 3, len(charges))]
        results = []
        project_tag = f"project:{workspace_id}" if workspace_id else None
        kind_set = frozenset(kind_filter) if kind_filter else None
        now_ts = _time.time()
        for i in idx:
            lab = labels[int(i)]
            if not isinstance(lab, dict):
                continue
            tags = lab.get("tags") or []
            if project_tag:
                has_project = any(t.startswith("project:") for t in tags)
                if has_project and project_tag not in tags:
                    continue
            if kind_set:
                lab_kind = next((t for t in tags if t in ("doc", "code", "conversation")), "conversation")
                if lab_kind not in kind_set:
                    continue
            text = str(lab.get("content", lab.get("response_preview", lab.get("prompt", ""))))[:300]
            item = {"text": text, "agent_type": lab.get("agent_type", "memory"), "success": lab.get("success", True)}
            if recency_boost:
                ts = lab.get("ts", 0)
                score = float(d[i])
                if ts:
                    age_hours = (now_ts - ts) / 3600
                    score *= 1.0 + age_hours * 0.05
                item["_score"] = score
            results.append(item)
        if recency_boost:
            results.sort(key=lambda r: r.get("_score", float("inf")))
            for r in results:
                r.pop("_score", None)
        return {"results": results[:k]}
    except Exception as e:
        return {"results": [], "error": str(e)}


async def add_to_memory(content: str, tags: Optional[List[str]] = None, project_id: Optional[str] = None) -> Dict[str, Any]:
    """Add content to NWF memory. Same storage as search_memory."""
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
        return {"status": "ok", "message": "Added to memory"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def read_file(path: str) -> Dict[str, Any]:
    """Read file content. Path relative to workspace."""
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
    """Write content to file. Path relative to workspace."""
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
    cmd_lower = command.lower()
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
    """Execute shell command. Whitelist: python, npm, git, pytest, etc. No pipes or redirects."""
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
    """Get git status. cwd is path relative to workspace."""
    return await execute_command("git status --short", cwd=cwd)


async def git_diff(cwd: Optional[str] = None, file_path: Optional[str] = None) -> Dict[str, Any]:
    """Get git diff. Optional file_path for specific file."""
    cmd = "git diff" + (f" -- {file_path}" if file_path else "")
    return await execute_command(cmd, cwd=cwd)


async def git_log(cwd: Optional[str] = None, n: int = 10) -> Dict[str, Any]:
    """Get last n git log entries."""
    return await execute_command(f"git log -{n} --oneline", cwd=cwd)


async def search_code(query: str, k: int = 10, workspace_id: Optional[str] = None) -> Dict[str, Any]:
    """Search indexed codebase by semantic similarity."""
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
    """Call another agent (coder, reviewer, chat, planner)."""
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
