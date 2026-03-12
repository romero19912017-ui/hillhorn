# -*- coding: utf-8 -*-
"""DeepSeek MCP Gateway - единая точка входа для агентов с NWF-логированием."""

from __future__ import annotations

import asyncio
import json


try:
    from dotenv import load_dotenv
    load_dotenv()
    _has_dotenv = True
except ImportError:
    _has_dotenv = False
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


import httpx
import numpy as np
from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from nwf import Charge, Field

# -----------------------------------------------------------------------------
# Конфигурация
# -----------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"

# Runtime config: ключ API можно обновить через /settings без перезапуска
_runtime_config: Dict[str, Any] = {"api_key": os.getenv("DEEPSEEK_API_KEY")}


def _get_api_key() -> str:
    return _runtime_config.get("api_key") or os.getenv("DEEPSEEK_API_KEY", "")


def _save_api_key_to_env(api_key: str) -> None:
    """Сохранение DEEPSEEK_API_KEY в .env и обновление runtime config."""
    lines: List[str] = []
    if ENV_PATH.exists():
        lines = ENV_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
    elif ENV_EXAMPLE.exists():
        lines = ENV_EXAMPLE.read_text(encoding="utf-8", errors="replace").splitlines()
    found = False
    out: List[str] = []
    for line in lines:
        if line.strip().startswith("DEEPSEEK_API_KEY="):
            out.append(f'DEEPSEEK_API_KEY={api_key}')
            found = True
        else:
            out.append(line)
    if not found:
        out.append(f'DEEPSEEK_API_KEY={api_key}')
    ENV_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")
    _runtime_config["api_key"] = api_key
    os.environ["DEEPSEEK_API_KEY"] = api_key
    if _has_dotenv:
        try:
            load_dotenv(override=True)
        except Exception:
            pass


DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
REQUEST_TIMEOUT = float(os.getenv("DEEPSEEK_TIMEOUT", "60"))
MAX_RETRIES = int(os.getenv("DEEPSEEK_MAX_RETRIES", "3"))
_DATA_ROOT = Path(os.getenv("HILLHORN_DATA_ROOT", "C:/hillhorn_data"))
NWF_MEMORY_PATH = Path(os.getenv("NWF_MEMORY_PATH", str(_DATA_ROOT / "deepseek_memory")))
USAGE_FILE = _DATA_ROOT / "deepseek_usage.json"
EMBED_DIM = 32
CHAT_MODEL = os.getenv("DEEPSEEK_CHAT_MODEL", "deepseek-chat")

# Маппинг агентов на модели DeepSeek
_AGENT_TO_MODEL_BASE = {
    "coder": os.getenv("DEEPSEEK_CODER_MODEL", CHAT_MODEL),
    "reviewer": os.getenv("DEEPSEEK_REVIEWER_MODEL", CHAT_MODEL),
    "planner": "deepseek-reasoner",
    "architect": "deepseek-reasoner",
    "tester_math": "deepseek-reasoner",
    "chat": CHAT_MODEL,
    "documenter": CHAT_MODEL,
}


def _get_model(agent_type: str) -> str:
    return _AGENT_TO_MODEL_BASE.get(agent_type, CHAT_MODEL)


def _log_usage(agent_type: str, input_tokens: int, output_tokens: int, model: str) -> None:
    """Запись использования токенов в data/deepseek_usage.json для учёта расходов."""
    try:
        date_key = time.strftime("%Y-%m-%d", time.localtime())
        data: Dict[str, Any] = {}
        if USAGE_FILE.exists():
            try:
                data = json.loads(USAGE_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        if date_key not in data:
            data[date_key] = {}
        entry = data[date_key].get(agent_type, {"calls": 0, "input_tokens": 0, "output_tokens": 0})
        entry["calls"] = entry.get("calls", 0) + 1
        entry["input_tokens"] = entry.get("input_tokens", 0) + input_tokens
        entry["output_tokens"] = entry.get("output_tokens", 0) + output_tokens
        data[date_key][agent_type] = entry
        USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        USAGE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


AGENT_TO_MODEL = _AGENT_TO_MODEL_BASE

# Системные промпты для агентов DeepSeek (рабочий процесс Hillhorn + Cursor)
SYSTEM_PROMPTS = {
    "coder": (
        "You are an expert software engineer. Use tools: read_file, write_file, execute_command, search_code, search_memory. "
        "Generate clean, efficient, well-documented code. Use write_file to apply changes. "
        "Answer in Russian unless prompt is in English. Keep solutions simple (KISS), avoid duplication (DRY)."
    ),
    "planner": (
        "You are a system architect. Break complex problems into numbered steps. "
        "For each step: goal, actions, dependencies. Output format: 1) Step name - what to do, 2) Next step. "
        "Be concrete. Answer in Russian unless prompt is in English."
    ),
    "reviewer": (
        "You are a senior code reviewer. Check: bugs, security, performance, style. "
        "Output format: [Critical/Important/Minor] Issue - suggestion. Start with critical. "
        "Be specific (file, line, fix). Answer in Russian unless prompt is in English."
    ),
    "chat": (
        "You are a helpful AI assistant in a development environment (Hillhorn + Cursor). "
        "Be concise. Answer in the same language as the prompt (Russian or English)."
    ),
    "documenter": (
        "Create clear technical documentation. Use headers, code blocks, examples. "
        "Answer in the same language as the prompt."
    ),
    "architect": (
        "Design system architecture. Output: components, interfaces, data flow, tech stack. "
        "Be structured. Answer in Russian unless prompt is in English."
    ),
    "tester_math": (
        "Verify mathematical correctness and algorithmic logic. Provide step-by-step reasoning. "
        "Answer in the same language as the prompt."
    ),
}

# -----------------------------------------------------------------------------
# Pydantic-модели запросов и ответов
# -----------------------------------------------------------------------------


class AgentRequest(BaseModel):
    agent_type: str
    prompt: str
    context: Optional[List[Dict[str, str]]] = None
    temperature: float = 0.7
    max_tokens: int = 2048
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[str] = "auto"
    auto_agent: bool = False
    workspace_id: Optional[str] = None
    workspace_path: Optional[str] = None


class AgentResponse(BaseModel):
    content: str
    model_used: str
    tokens_used: int
    request_id: str
    reasoning: Optional[str] = None

# -----------------------------------------------------------------------------
# NWF-память: загрузка и логирование вызовов
# -----------------------------------------------------------------------------


def _text_to_embedding(text: str, dim: int = EMBED_DIM) -> np.ndarray:
    """Единый эмбеддинг через модуль embeddings (hash или sentence-transformers)."""
    from embeddings import get_embedding
    return get_embedding(text, dim=dim)


def _load_nwf_memory() -> Field:
    NWF_MEMORY_PATH.mkdir(parents=True, exist_ok=True)
    field = Field()
    meta = NWF_MEMORY_PATH / "meta.json"
    if meta.exists():
        try:
            field.load(NWF_MEMORY_PATH)
        except Exception:
            pass
    return field


def _log_to_nwf(
    memory: Field,
    agent_type: str,
    prompt: str,
    response: str,
    model: str,
    tokens: int,
    latency: float,
    success: bool,
    error_code: Optional[int] = None,
) -> None:
    """Сохранить вызов API как Charge в NWF-поле. Используется для семантического поиска похожих запросов."""
    try:
        text_for_embed = f"{agent_type}:{prompt[:500]}"
        z = _text_to_embedding(text_for_embed)
        base_sigma = max(0.01, latency * 0.1) if success else 0.5
        sigma = np.full(EMBED_DIM, base_sigma, dtype=np.float64)
        alpha = 0.3 if not success else (1.5 if agent_type == "planner" else 1.0)
        charge = Charge(z=z, sigma=sigma, alpha=alpha)
        label = {
            "agent_type": agent_type,
            "model": model,
            "tokens": tokens,
            "latency": round(latency, 3),
            "success": success,
            "error_code": error_code,
            "response_preview": (response or "")[:200],
            "timestamp": time.time(),
        }
        memory.add(charge, labels=[label])
        if len(memory) > 0:
            memory.save(NWF_MEMORY_PATH)
        # Автоочистка при превышении порога (в фоне, не блокирует)
        prune_threshold = int(os.getenv("NWF_PRUNE_THRESHOLD", "12000"))
        if len(memory) > prune_threshold:
            import threading
            def _bg_prune():
                try:
                    from nwf_memory_utils import prune_field
                    prune_field(max_charges=10000)
                except Exception:
                    pass
            threading.Thread(target=_bg_prune, daemon=True).start()
    except Exception:
        pass

# -----------------------------------------------------------------------------
# DeepSeek API: вызовы, стриминг, retry, tool execution
# -----------------------------------------------------------------------------


def _sanitize_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Убрать reasoning_content из сообщений assistant. Сохранить tool/tool_calls."""
    out: List[Dict[str, Any]] = []
    for m in messages:
        if not isinstance(m, dict):
            continue
        role = m.get("role")
        if role == "assistant":
            msg: Dict[str, Any] = {"role": "assistant", "content": str(m.get("content", "") or "")}
            if m.get("tool_calls"):
                msg["tool_calls"] = m["tool_calls"]
            out.append(msg)
        elif role == "user":
            out.append({"role": "user", "content": str(m.get("content", ""))})
        elif role == "system":
            out.append({"role": "system", "content": str(m.get("content", ""))})
        elif role == "tool":
            out.append({"role": "tool", "tool_call_id": m.get("tool_call_id"), "content": str(m.get("content", ""))})
    return out


async def _execute_tool(
    name: str,
    arguments: Dict[str, Any],
    workspace_id: Optional[str] = None,
    workspace_path: Optional[str] = None,
) -> str:
    """Выполнить инструмент и вернуть результат в виде JSON-строки."""
    try:
        from tools import TOOL_MAP, set_workspace_override
        set_workspace_override(workspace_path)
        fn = TOOL_MAP.get(name)
        if not fn:
            return json.dumps({"error": f"Unknown tool: {name}"})
        args = dict(arguments)
        if workspace_id and "workspace_id" in (arguments or {}):
            args["workspace_id"] = workspace_id
        result = await fn(**args)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e)})
    finally:
        try:
            from tools import set_workspace_override
            set_workspace_override(None)
        except Exception:
            pass


async def _call_deepseek_stream(
    model: str,
    messages: List[Dict[str, str]],
    max_tokens: int,
    memory: Field,
    agent_type: str,
    url: str,
    headers: Dict[str, str],
) -> AgentResponse:
    """Стриминговый вызов для deepseek-reasoner (reasoning_content + content)."""
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "stream": True,
    }
    timeout = max(REQUEST_TIMEOUT, 120)
    start = time.perf_counter()
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream("POST", url, headers=headers, json=payload) as r:
            if r.status_code != 200:
                body = await r.aread()
                raise HTTPException(r.status_code, body.decode("utf-8", errors="replace")[:500])
            reasoning_parts: List[str] = []
            content_parts: List[str] = []
            req_id = "stream"
            async for line in r.aiter_lines():
                if not line.startswith("data: "):
                    continue
                chunk = line[6:].strip()
                if chunk == "[DONE]":
                    break
                try:
                    data = json.loads(chunk)
                except json.JSONDecodeError:
                    continue
                for choice in data.get("choices", []):
                    delta = choice.get("delta", {})
                    if delta.get("reasoning_content"):
                        reasoning_parts.append(delta["reasoning_content"])
                    if delta.get("content"):
                        content_parts.append(delta["content"])
            content = "".join(content_parts)
            reasoning = "".join(reasoning_parts)
            elapsed = time.perf_counter() - start
            tokens = max(0, (len(reasoning) + len(content)) // 4)
            inp = tokens // 2
            out = tokens - inp
            _log_usage(agent_type, inp, out, model)
            _log_to_nwf(
                memory, agent_type,
                messages[-1].get("content", "") if messages else "",
                content[:500], model, tokens, elapsed, True,
            )
            return AgentResponse(
                content=content,
                model_used=model,
                tokens_used=tokens,
                request_id=req_id,
                reasoning=reasoning if reasoning else None,
            )


async def call_deepseek(
    model: str,
    messages: List[Dict[str, Any]],
    temperature: float,
    max_tokens: int,
    memory: Field,
    agent_type: str,
    tools: Optional[List[Dict[str, Any]]] = None,
    tool_choice: Optional[str] = "auto",
    workspace_id: Optional[str] = None,
    workspace_path: Optional[str] = None,
) -> AgentResponse:
    api_key = _get_api_key()
    if not api_key or api_key == "sk-your-key-here":
        raise HTTPException(503, "DEEPSEEK_API_KEY not set. Configure in Settings: http://127.0.0.1:8001/settings")
    url = f"{DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    msgs = _sanitize_messages(messages)
    is_reasoner = model == "deepseek-reasoner"
    use_tools = tools and len(tools) > 0
    if use_tools and is_reasoner:
        is_reasoner = False
    last_error: Optional[Exception] = None
    last_status: Optional[int] = None
    last_text: str = ""
    total_tokens = 0
    max_tool_iter = 5
    tool_iter = 0

    while tool_iter < max_tool_iter:
        for attempt in range(MAX_RETRIES):
            try:
                if is_reasoner and not use_tools:
                    return await _call_deepseek_stream(
                        model, msgs, max_tokens, memory, agent_type, url, headers
                    )
                payload: Dict[str, Any] = {
                    "model": model,
                    "messages": msgs,
                    "temperature": min(2.0, max(0, temperature)),
                    "max_tokens": max_tokens,
                    "stream": False,
                }
                if use_tools:
                    payload["tools"] = tools
                    payload["tool_choice"] = tool_choice
                start = time.perf_counter()
                async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                    r = await client.post(url, headers=headers, json=payload)
                elapsed = time.perf_counter() - start
                last_status = r.status_code
                last_text = r.text

                if r.status_code == 200:
                    data = r.json()
                    choice = data.get("choices", [{}])[0]
                    msg = choice.get("message", {})
                    content = msg.get("content", "") or ""
                    usage = data.get("usage", {})
                    total_tokens += int(usage.get("total_tokens", 0))
                    inp = int(usage.get("prompt_tokens", 0))
                    out = int(usage.get("completion_tokens", 0))
                    _log_usage(agent_type, inp, out, model)
                    req_id = data.get("id", "unknown")
                    tool_calls = msg.get("tool_calls")

                    if tool_calls and use_tools:
                        tool_iter += 1
                        msgs.append(msg)
                        for tc in tool_calls:
                            tid = tc.get("id", "")
                            fn = tc.get("function", {})
                            fname = fn.get("name", "")
                            try:
                                fargs = json.loads(fn.get("arguments", "{}"))
                            except json.JSONDecodeError:
                                fargs = {}
                            result = await _execute_tool(fname, fargs, workspace_id, workspace_path)
                            msgs.append({"role": "tool", "tool_call_id": tid, "content": result})
                        continue

                    _log_to_nwf(
                        memory, agent_type,
                        msgs[-1].get("content", "") if msgs else "",
                        content, model, total_tokens, elapsed, True,
                    )
                    return AgentResponse(
                        content=content,
                        model_used=model,
                        tokens_used=total_tokens,
                        request_id=req_id,
                    )

                if r.status_code == 429:
                    wait = min(2 ** attempt + 1, 10)
                    await asyncio.sleep(wait)
                    continue
            except httpx.TimeoutException as e:
                last_error = e
                if attempt == MAX_RETRIES - 1:
                    _log_to_nwf(
                        memory, agent_type,
                        msgs[-1].get("content", "") if msgs else "",
                        "Timeout", model, 0, REQUEST_TIMEOUT, False, 504,
                    )
                    raise HTTPException(504, "DeepSeek API timeout")
                await asyncio.sleep(2 ** attempt)
            except HTTPException:
                raise
            except Exception as e:
                last_error = e
                if attempt == MAX_RETRIES - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
        break

    _log_to_nwf(
        memory, agent_type,
        msgs[-1].get("content", "") if msgs else "",
        f"Error {last_status}: {last_text[:100]}", model, 0, 0, False, last_status,
    )
    raise HTTPException(
        last_status or 500,
        detail=f"DeepSeek API error: {last_text[:500]}" if last_text else str(last_error),
    )

# -----------------------------------------------------------------------------
# FastAPI приложение: эндпоинты, health, settings
# -----------------------------------------------------------------------------

app = FastAPI(title="DeepSeek MCP Gateway")
memory_field = _load_nwf_memory()


KNOWN_AGENTS = frozenset(_AGENT_TO_MODEL_BASE)

@app.post("/v1/agent/query/stream")
async def agent_query_stream(req: AgentRequest):
    """SSE stream for chat agent (no tools)."""
    agent_type = req.agent_type if req.agent_type != "coder" else "chat"
    if agent_type not in ("chat", "documenter"):
        agent_type = "chat"
    model_name = _get_model(agent_type)
    messages: List[Dict[str, Any]] = []
    if agent_type in SYSTEM_PROMPTS:
        messages.append({"role": "system", "content": SYSTEM_PROMPTS[agent_type]})
    if req.context:
        for m in req.context:
            if isinstance(m, dict) and "role" in m and "content" in m:
                messages.append({"role": m["role"], "content": str(m["content"])})
    messages.append({"role": "user", "content": req.prompt})

    api_key = _get_api_key()
    if not api_key or api_key == "sk-your-key-here":

        async def err_gen():
            yield f"data: {json.dumps({'error': 'DEEPSEEK_API_KEY not set'})}\n\n"

        return StreamingResponse(
            err_gen(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )
    url = f"{DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model_name,
        "messages": _sanitize_messages(messages),
        "max_tokens": req.max_tokens,
        "stream": True,
    }

    async def gen():
        async with httpx.AsyncClient(timeout=max(REQUEST_TIMEOUT, 120)) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as r:
                if r.status_code != 200:
                    body = await r.aread()
                    yield f"data: {json.dumps({'error': body.decode('utf-8', errors='replace')[:500]})}\n\n"
                    return
                async for line in r.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    chunk = line[6:].strip()
                    if chunk == "[DONE]":
                        yield f"data: {json.dumps({'done': True})}\n\n"
                        return
                    try:
                        data = json.loads(chunk)
                    except json.JSONDecodeError:
                        continue
                    for choice in data.get("choices", []):
                        delta = choice.get("delta", {})
                        if delta.get("content"):
                            yield f"data: {json.dumps({'content': delta['content']})}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.post("/v1/agent/query", response_model=AgentResponse)
async def agent_query(req: AgentRequest) -> AgentResponse:
    agent_type = req.agent_type
    model_agent = "chat" if agent_type == "reviewer" else agent_type
    if req.auto_agent:
        try:
            from agents import select_agent_from_memory
            agent_type = select_agent_from_memory(str(NWF_MEMORY_PATH), req.prompt)
        except Exception:
            agent_type = "chat"
    if agent_type not in KNOWN_AGENTS:
        raise HTTPException(400, f"Unknown agent type: {agent_type}")
    model_name = _get_model(model_agent)
    messages: List[Dict[str, Any]] = []
    if agent_type in SYSTEM_PROMPTS:
        messages.append({"role": "system", "content": SYSTEM_PROMPTS[agent_type]})
    if req.context:
        for m in req.context:
            if isinstance(m, dict) and "role" in m and "content" in m:
                messages.append({"role": m["role"], "content": str(m["content"])})
    messages.append({"role": "user", "content": req.prompt})
    tools = req.tools
    if tools is None and agent_type in ("planner", "coder"):
        try:
            from tools import TOOL_DEFINITIONS
            tools = TOOL_DEFINITIONS
        except Exception:
            tools = None
    return await call_deepseek(
        model=model_name,
        messages=messages,
        temperature=req.temperature,
        max_tokens=req.max_tokens,
        memory=memory_field,
        agent_type=agent_type,
        tools=tools,
        tool_choice=req.tool_choice,
        workspace_id=req.workspace_id,
        workspace_path=req.workspace_path,
    )


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "memory_charges": len(memory_field),
        "settings": "http://127.0.0.1:8001/settings",
        "models": {k: _get_model("chat" if k == "reviewer" else k) for k in _AGENT_TO_MODEL_BASE},
    }


@app.get("/debug/reviewer")
async def debug_reviewer() -> Dict[str, Any]:
    return {
        "model_agent": "chat",
        "model": _get_model("chat"),
        "has_tools": False,
    }


# -----------------------------------------------------------------------------
# Memory API для Hillhorn MCP (замена расширения NWF)
# -----------------------------------------------------------------------------


@app.get("/v1/memory/health")
async def memory_health() -> Dict[str, Any]:
    """Health check: NWF, embed, cache stats."""
    out: Dict[str, Any] = {"ok": True, "version": "1.0"}
    try:
        nwf_ok = (NWF_MEMORY_PATH / "meta.json").exists()
        out["nwf"] = "ok" if nwf_ok else "missing"
    except Exception:
        out["nwf"] = "error"
    try:
        from embeddings import get_embedding
        get_embedding("test", dim=32)
        out["embed"] = "ok"
    except Exception as e:
        out["embed"] = "hash" if "HF" not in str(e) else "error"
    try:
        from tools import get_cache_stats
        out["cache"] = get_cache_stats()
    except Exception:
        pass
    return out


class MemorySearchRequest(BaseModel):
    query: str
    top_k: int = 10
    project_id: Optional[str] = None


class MemoryAddRequest(BaseModel):
    text: str
    kind: Optional[str] = "conversation"
    role: Optional[str] = "system"
    file_path: Optional[str] = None
    project_id: Optional[str] = None


class MemoryIndexRequest(BaseModel):
    file_path: str
    content: str
    project_id: Optional[str] = None


@app.post("/v1/memory/search")
async def memory_search(req: MemorySearchRequest) -> Dict[str, Any]:
    """Семантический поиск в NWF-памяти (DeepSeek + workspace)."""
    try:
        from tools import search_memory
        ws_id = req.project_id
        result = await search_memory(req.query, k=req.top_k, workspace_id=ws_id)
        results = result.get("results", [])
        if result.get("error"):
            return {"results": results, "error": result["error"]}
        items = []
        for r in results:
            items.append({
                "text": r.get("text", ""),
                "source": r.get("agent_type", "memory"),
                "success": r.get("success", True),
            })
        try:
            from nwf_memory_adapter import search_similar
            nwf_path = Path(os.getenv("NWF_MEMORY_ADAPTER_PATH", str(_DATA_ROOT / "nwf_opencloud")))
            if (nwf_path / "meta.json").exists():
                similar = search_similar(req.query, k=min(5, req.top_k), field_path=nwf_path)
                for s in similar:
                    items.append({"text": s.get("text", ""), "source": s.get("source", "workspace")})
        except Exception:
            pass
        return {"results": items[: req.top_k]}
    except Exception as e:
        return {"results": [], "error": str(e)}


@app.post("/v1/memory/add")
async def memory_add(req: MemoryAddRequest) -> Dict[str, Any]:
    """Добавить реплику/факт в NWF-память."""
    try:
        from tools import add_to_memory
        tags = [req.kind or "conversation", req.role or "system"]
        if req.file_path:
            tags.append(f"file:{req.file_path}")
        if req.project_id:
            tags.append(f"project:{req.project_id}")
        result = await add_to_memory(req.text, tags=tags)
        return result
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/v1/memory/index_file")
async def memory_index_file(req: MemoryIndexRequest) -> Dict[str, Any]:
    """Проиндексировать содержимое файла в память."""
    try:
        from tools import add_to_memory
        text = f"[{req.file_path}]\n{req.content}"
        tags = ["code", "file", req.file_path]
        if req.project_id:
            tags.append(f"project:{req.project_id}")
        result = await add_to_memory(text, tags=tags)
        return result
    except Exception as e:
        return {"status": "error", "error": str(e)}


# -----------------------------------------------------------------------------
# Настройки: страница для ввода DEEPSEEK_API_KEY
# -----------------------------------------------------------------------------

SETTINGS_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Hillhorn - Settings</title>
    <style>
        * { box-sizing: border-box; }
        body { font-family: system-ui, sans-serif; max-width: 480px; margin: 2rem auto; padding: 0 1rem; }
        h1 { color: #1a3a5c; font-size: 1.5rem; }
        label { display: block; margin-top: 1rem; font-weight: 500; }
        input[type="password"], input[type="text"] { width: 100%; padding: 0.5rem; margin-top: 0.25rem; font-family: monospace; }
        button { margin-top: 1rem; padding: 0.5rem 1.5rem; background: #1a3a5c; color: white; border: none; cursor: pointer; border-radius: 4px; }
        button:hover { background: #2a4a6c; }
        .msg { margin-top: 1rem; padding: 0.5rem; border-radius: 4px; }
        .ok { background: #d4edda; color: #155724; }
        .err { background: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <h1>Hillhorn Settings</h1>
    <p>DeepSeek API key for Gateway. Get key at <a href="https://platform.deepseek.com">platform.deepseek.com</a>.</p>
    <form method="post" action="/settings">
        <label for="api_key">DEEPSEEK_API_KEY</label>
        <input type="password" id="api_key" name="api_key" placeholder="{api_key_placeholder}" autocomplete="off">
        <button type="submit">Save</button>
    </form>
    <div id="msg">{message}</div>
    <p style="margin-top: 2rem; font-size: 0.85rem; color: #666;">
        Key is stored in .env. Changes apply immediately without restart.
    </p>
</body>
</html>
"""


@app.get("/settings", response_class=HTMLResponse)
async def settings_page() -> str:
    key = _get_api_key()
    ph = "Key is set (enter new to replace)" if key and key != "sk-your-key-here" else "sk-your-key-here"
    return SETTINGS_HTML.format(api_key_placeholder=ph, message="")


@app.post("/settings", response_class=HTMLResponse)
async def settings_save(request: Request, api_key: Optional[str] = Form(None)) -> str:
    if not api_key:
        body = await request.body()
        try:
            data = json.loads(body)
            api_key = data.get("api_key", "")
        except Exception:
            api_key = ""
    api_key = (api_key or "").strip()
    key = _get_api_key()
    ph = "Key is set (enter new to replace)" if key and key != "sk-your-key-here" else "sk-your-key-here"
    if not api_key:
        msg = '<div class="msg err">Key cannot be empty</div>'
        return SETTINGS_HTML.format(api_key_placeholder=ph, message=msg)
    try:
        _save_api_key_to_env(api_key)
        msg = '<div class="msg ok">Key saved. Changes apply immediately.</div>'
        return SETTINGS_HTML.format(api_key_placeholder="Key is set (enter new to replace)", message=msg)
    except Exception as e:
        msg = f'<div class="msg err">Error: {e}</div>'
        return SETTINGS_HTML.format(api_key_placeholder=ph, message=msg)


def main() -> None:
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)


if __name__ == "__main__":
    main()
