# -*- coding: utf-8 -*-
"""Hillhorn MCP Server - smart memory with DeepSeek. Replacement for NWF extension."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import time

import httpx
from fastmcp import FastMCP

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
GATEWAY_URL = os.getenv("HILLHORN_GATEWAY_URL", "http://localhost:8001")
DEFAULT_PROJECT_ID = os.getenv("HILLHORN_PROJECT_ID", str(ROOT))
DEFAULT_MAX_TOKENS = int(os.getenv("HILLHORN_MAX_TOKENS", "1200"))
ACTIVITY_FILE = ROOT / "data" / "hillhorn_activity.json"
ERRORS_LOG = ROOT / "data" / "hillhorn_errors.log"
CALLS_LOG = ROOT / "data" / "hillhorn_calls.jsonl"

# Retry: 2 attempts, 2 sec delay (ConnectError)
POST_RETRIES = 2
POST_RETRY_DELAY = 2.0


def _log_activity(tool_name: str) -> None:
    """Write last tool use for status indicator."""
    try:
        ACTIVITY_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {"last_use": time.time(), "last_tool": tool_name}
        ACTIVITY_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _log_call(tool_name: str, duration_ms: float) -> None:
    """Append tool call to hillhorn_calls.jsonl for history."""
    try:
        CALLS_LOG.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps({"tool": tool_name, "ts": time.time(), "duration_ms": round(duration_ms, 0)}) + "\n"
        with open(CALLS_LOG, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


def _log_error(tool_name: str, exc: Exception) -> None:
    """Append error to hillhorn_errors.log."""
    try:
        ERRORS_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        line = f"{ts} [{tool_name}] {type(exc).__name__}: {exc}\n"
        with open(ERRORS_LOG, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


def _wrap(tool_name: str, content: str) -> str:
    """Prefix response for visibility in agent chat: Hillhorn | tool_name."""
    return f"[Hillhorn | {tool_name}]\n{content}"


async def _post(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """POST JSON to Gateway with retry on ConnectError."""
    url = f"{GATEWAY_URL.rstrip('/')}{path}"
    last_err: Optional[Exception] = None
    for attempt in range(POST_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                r = await client.post(url, json=payload)
                r.raise_for_status()
                return r.json()
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            last_err = e
            if attempt < POST_RETRIES - 1:
                await asyncio.sleep(POST_RETRY_DELAY)
    raise last_err  # type: ignore[misc]


mcp = FastMCP(
    "hillhorn",
    instructions="Hillhorn - smart memory with DeepSeek. Search, add, index, consult agents.",
)


async def _search_memory_direct(
    query: str,
    top_k: int,
    project_id: Optional[str],
    kind_filter: Optional[List[str]] = None,
    recency_boost: bool = False,
) -> Dict[str, Any]:
    """Call tools.search_memory and nwf_adapter directly, no Gateway HTTP."""
    try:
        from tools import search_memory
        result = await search_memory(
            query, k=top_k, workspace_id=project_id,
            kind_filter=kind_filter, recency_boost=recency_boost,
        )
        items = [{"text": r.get("text", ""), "source": r.get("agent_type", "memory")}
                 for r in result.get("results", [])]
        try:
            from nwf_memory_adapter import search_similar
            nwf_path = ROOT / os.getenv("NWF_MEMORY_ADAPTER_PATH", "data/nwf_opencloud")
            if (nwf_path / "meta.json").exists():
                for s in search_similar(query, k=min(5, top_k), field_path=nwf_path):
                    items.append({"text": s.get("text", ""), "source": s.get("source", "workspace")})
        except Exception:
            pass
        return {"results": items[:top_k]}
    except Exception as e:
        return {"results": [], "error": str(e)}


async def _add_memory_direct(
    text: str, kind: str, role: str, file_path: Optional[str], project_id: Optional[str] = None
) -> Dict[str, Any]:
    try:
        from tools import add_to_memory
        tags = [kind, role]
        if file_path:
            tags.append(f"file:{file_path}")
        return await add_to_memory(text, tags=tags, project_id=project_id)
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _read_project_context(project_id: str) -> str:
    """Read SOUL.md, USER.md, MEMORY.md from project root."""
    parts = []
    base = Path(project_id) if project_id else ROOT
    for name in ("SOUL.md", "USER.md", "MEMORY.md"):
        p = base / name
        if p.exists():
            try:
                text = p.read_text(encoding="utf-8", errors="replace").strip()
                if text:
                    parts.append(f"[{name}]\n{text[:1500]}")
            except Exception:
                pass
    return "\n\n".join(parts) if parts else ""


@mcp.tool
async def hillhorn_get_context(
    project_id: str = DEFAULT_PROJECT_ID,
    include_memory_search: bool = True,
    memory_top_k: int = 5,
) -> str:
    """Get project context: SOUL, USER, MEMORY + recent memory. Call at start of session."""
    t0 = time.perf_counter()
    ctx_parts = []
    files_ctx = _read_project_context(project_id)
    if files_ctx:
        ctx_parts.append(files_ctx)
    if include_memory_search:
        data = await _search_memory_direct("общая информация о проекте", memory_top_k, project_id)
        results = data.get("results", [])
        if results:
            lines = []
            for i, r in enumerate(results, 1):
                text = r.get("text", "")[:300]
                source = r.get("source", "")
                lines.append(f"{i}. [{source}] {text}")
            ctx_parts.append("[Memory]\n" + "\n".join(lines))
        else:
            ctx_parts.append("[Memory] Память пуста (новый проект).")
    if not ctx_parts:
        return _wrap("hillhorn_get_context", "Контекст проекта не найден (нет SOUL/USER/MEMORY, память пуста).")
    _log_activity("hillhorn_get_context")
    _log_call("hillhorn_get_context", (time.perf_counter() - t0) * 1000)
    return _wrap("hillhorn_get_context", "\n\n---\n\n".join(ctx_parts))


@mcp.tool
async def hillhorn_search(
    query: str,
    project_id: str = DEFAULT_PROJECT_ID,
    top_k: int = 10,
    kind_filter: Optional[List[str]] = None,
    recency_boost: bool = False,
) -> str:
    """Semantic search in Hillhorn memory. kind_filter: doc, code, conversation. recency_boost for recent items."""
    t0 = time.perf_counter()
    try:
        data = await _search_memory_direct(
            query, top_k, project_id,
            kind_filter=kind_filter, recency_boost=recency_boost,
        )
        results = data.get("results", [])
        if data.get("error"):
            _log_call("hillhorn_search", (time.perf_counter() - t0) * 1000)
            return _wrap("hillhorn_search", f"Search error: {data['error']}")
        if not results:
            _log_activity("hillhorn_search")
            _log_call("hillhorn_search", (time.perf_counter() - t0) * 1000)
            return _wrap("hillhorn_search", f"Память пуста (новый проект). project_id={project_id}")
        lines = []
        for i, r in enumerate(results, 1):
            text = r.get("text", "")[:400]
            source = r.get("source", "")
            lines.append(f"{i}. [{source}] {text}")
        _log_activity("hillhorn_search")
        _log_call("hillhorn_search", (time.perf_counter() - t0) * 1000)
        return _wrap("hillhorn_search", "\n".join(lines))
    except Exception as e:
        _log_call("hillhorn_search", (time.perf_counter() - t0) * 1000)
        return _wrap("hillhorn_search", f"Error: {e}")


@mcp.tool
async def hillhorn_add_turn(
    text: str,
    project_id: str = DEFAULT_PROJECT_ID,
    role: str = "system",
    kind: str = "conversation",
    file_path: Optional[str] = None,
) -> str:
    """Add fact or dialog turn to Hillhorn memory. Use after important decisions or studying code."""
    t0 = time.perf_counter()
    try:
        data = await _add_memory_direct(text, kind, role, file_path, project_id)
        _log_call("hillhorn_add_turn", (time.perf_counter() - t0) * 1000)
        if data.get("status") == "ok":
            _log_activity("hillhorn_add_turn")
            return _wrap("hillhorn_add_turn", "Added to memory.")
        return _wrap("hillhorn_add_turn", f"Error: {data.get('error', 'Unknown')}")
    except Exception as e:
        _log_call("hillhorn_add_turn", (time.perf_counter() - t0) * 1000)
        return _wrap("hillhorn_add_turn", f"Error: {e}")


@mcp.tool
async def hillhorn_index_file(
    file_path: str,
    content: str,
    project_id: str = DEFAULT_PROJECT_ID,
) -> str:
    """Index file content into memory. For critical project files."""
    t0 = time.perf_counter()
    try:
        data = await _add_memory_direct(f"[{file_path}]\n{content}", "code", "file", file_path, project_id)
        _log_call("hillhorn_index_file", (time.perf_counter() - t0) * 1000)
        if data.get("status") == "ok":
            _log_activity("hillhorn_index_file")
            return _wrap("hillhorn_index_file", f"Indexed {file_path}.")
        return _wrap("hillhorn_index_file", f"Error: {data.get('error', 'Unknown')}")
    except Exception as e:
        _log_call("hillhorn_index_file", (time.perf_counter() - t0) * 1000)
        return _wrap("hillhorn_index_file", f"Error: {e}")


_PROMPT_MAX_LEN = 6000
_CODE_IN_CONTEXT_MAX = 8000


@mcp.tool
async def hillhorn_consult_agent(
    agent_type: str,
    prompt: str,
    project_id: str = DEFAULT_PROJECT_ID,
    context: Optional[List[Dict[str, str]]] = None,
    code_to_review: Optional[str] = None,
    extra_context: Optional[List[str]] = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> str:
    """Consult Hillhorn agent: planner, coder, reviewer, chat. extra_context: list of text fragments for context."""
    allowed = ("planner", "coder", "reviewer", "chat", "architect", "documenter")
    if agent_type not in allowed:
        return _wrap("hillhorn_consult_agent", f"Unknown agent. Use: {', '.join(allowed)}")
    t0 = time.perf_counter()
    try:
        agent = agent_type
        prompt_use = prompt
        if agent_type == "reviewer":
            agent = "chat"
            prompt_use = "As a code reviewer, analyze the code. " + prompt
        msgs = list(context) if context else []
        if extra_context:
            for txt in extra_context[:5]:
                if txt and isinstance(txt, str):
                    msgs.append({"role": "user", "content": txt[:2000]})
        if code_to_review:
            code = code_to_review[: _CODE_IN_CONTEXT_MAX]
            if len(code_to_review) > _CODE_IN_CONTEXT_MAX:
                code += "\n\n[... truncated]"
            msgs.append({"role": "user", "content": f"Code to review:\n\n```\n{code}\n```"})
        prompt_trimmed = prompt_use[: _PROMPT_MAX_LEN]
        if len(prompt_use) > _PROMPT_MAX_LEN:
            prompt_trimmed += "\n[...]"
        payload = {
            "agent_type": agent,
            "prompt": prompt_trimmed,
            "workspace_path": project_id,
            "max_tokens": min(max_tokens, 2048),
        }
        if msgs:
            payload["context"] = msgs
        data = await _post("/v1/agent/query", payload)
        content = data.get("content", "")
        reasoning = data.get("reasoning", "")
        _log_activity("hillhorn_consult_agent")
        _log_call("hillhorn_consult_agent", (time.perf_counter() - t0) * 1000)
        body = f"[Reasoning]\n{reasoning}\n\n[Answer]\n{content}" if reasoning else (content or "Empty response.")
        return _wrap("hillhorn_consult_agent", body)
    except (httpx.ConnectError, httpx.ConnectTimeout) as e:
        _log_error("hillhorn_consult_agent", e)
        _log_call("hillhorn_consult_agent", (time.perf_counter() - t0) * 1000)
        return _wrap("hillhorn_consult_agent", "Error: Hillhorn Gateway not running. Start: .\\scripts\\start_all_background.ps1")
    except httpx.HTTPStatusError as e:
        _log_call("hillhorn_consult_agent", (time.perf_counter() - t0) * 1000)
        return _wrap("hillhorn_consult_agent", f"Gateway error: {e.response.status_code} - {e.response.text[:200]}")
    except Exception as e:
        _log_call("hillhorn_consult_agent", (time.perf_counter() - t0) * 1000)
        return _wrap("hillhorn_consult_agent", f"Error: {e}")


@mcp.tool
async def hillhorn_consult_with_memory(
    agent_type: str,
    prompt: str,
    project_id: str = DEFAULT_PROJECT_ID,
    memory_query: Optional[str] = None,
    memory_top_k: int = 3,
    code_to_review: Optional[str] = None,
    extra_context: Optional[List[str]] = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> str:
    """Consult DeepSeek agent with project memory. Use planner only for complex tasks. Saves API cost."""
    allowed = ("planner", "coder", "reviewer", "chat", "architect", "documenter")
    if agent_type not in allowed:
        return _wrap("hillhorn_consult_with_memory", f"Unknown agent. Use: {', '.join(allowed)}")
    agent = "chat" if agent_type == "reviewer" else agent_type
    prompt_use = f"As a code reviewer, analyze the code. {prompt}" if agent_type == "reviewer" else prompt
    t0 = time.perf_counter()
    try:
        query = memory_query or "общая информация о проекте, решения, контекст"
        data = await _search_memory_direct(query, memory_top_k, project_id)
        results = data.get("results", [])
        context = []
        if results:
            lines = []
            for r in results:
                text = r.get("text", "")[:200]
                source = r.get("source", "memory")
                lines.append(f"[{source}] {text}")
            context.append({"role": "system", "content": "Context from project memory:\n" + "\n".join(lines)})
        files_ctx = _read_project_context(project_id)
        if files_ctx:
            context.append({"role": "system", "content": "Project files (SOUL/USER/MEMORY):\n" + files_ctx[:1000]})
        if extra_context:
            for txt in extra_context[:5]:
                if txt and isinstance(txt, str):
                    context.append({"role": "system", "content": txt[:2000]})
        if code_to_review:
            code = code_to_review[: _CODE_IN_CONTEXT_MAX]
            context.append({"role": "user", "content": f"Code to review:\n\n```\n{code}\n```"})
        prompt_trimmed = prompt_use[: _PROMPT_MAX_LEN]
        payload = {
            "agent_type": agent,
            "prompt": prompt_trimmed,
            "workspace_path": project_id,
            "max_tokens": min(max_tokens, 2048),
            "context": context if context else None,
        }
        resp = await _post("/v1/agent/query", payload)
        content = resp.get("content", "")
        reasoning = resp.get("reasoning", "")
        _log_activity("hillhorn_consult_with_memory")
        _log_call("hillhorn_consult_with_memory", (time.perf_counter() - t0) * 1000)
        body = f"[Reasoning]\n{reasoning}\n\n[Answer]\n{content}" if reasoning else (content or "Empty response.")
        return _wrap("hillhorn_consult_with_memory", body)
    except (httpx.ConnectError, httpx.ConnectTimeout) as e:
        _log_error("hillhorn_consult_with_memory", e)
        _log_call("hillhorn_consult_with_memory", (time.perf_counter() - t0) * 1000)
        return _wrap("hillhorn_consult_with_memory", "Error: Hillhorn Gateway not running.")
    except Exception as e:
        _log_call("hillhorn_consult_with_memory", (time.perf_counter() - t0) * 1000)
        return _wrap("hillhorn_consult_with_memory", f"Error: {e}")


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
