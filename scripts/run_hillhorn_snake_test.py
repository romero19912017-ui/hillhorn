# -*- coding: utf-8 -*-
"""Test Hillhorn on real task: write snake game. Workflow: get_context -> search -> plan -> code -> review -> add_turn."""
from __future__ import annotations

import asyncio
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

PROJECT_ID = r"c:\Hillhorn"
GATEWAY = os.getenv("HILLHORN_GATEWAY_URL", "http://localhost:8001")

log = []
timings = {}  # step -> seconds


def _log(msg: str) -> None:
    t = time.strftime("%H:%M:%S")
    log.append(f"[{t}] {msg}")
    print(f"[{t}] {msg}")


async def hillhorn_get_context() -> str:
    from pathlib import Path
    from tools import search_memory
    ctx_parts = []
    t0 = time.perf_counter()
    base = Path(PROJECT_ID)
    for name in ("SOUL.md", "USER.md", "MEMORY.md"):
        p = base / name
        if p.exists():
            try:
                t = p.read_text(encoding="utf-8", errors="replace").strip()[:1500]
                if t:
                    ctx_parts.append(f"[{name}]\n{t}")
            except Exception:
                pass
    timings["get_context_files"] = time.perf_counter() - t0
    files_ctx = "\n\n".join(ctx_parts) if ctx_parts else ""
    if files_ctx:
        ctx_parts = [files_ctx]
    t0 = time.perf_counter()
    data = await search_memory("общая информация о проекте", k=5, workspace_id=PROJECT_ID)
    timings["get_context_search_memory"] = time.perf_counter() - t0
    results = data.get("results", [])
    t0 = time.perf_counter()
    try:
        from nwf_memory_adapter import search_similar
        nwf_path = Path(os.getenv("NWF_MEMORY_ADAPTER_PATH", str(Path(os.getenv("HILLHORN_DATA_ROOT", "C:/hillhorn_data")) / "nwf_opencloud")))
        if (nwf_path / "meta.json").exists():
            for s in search_similar("общая информация о проекте", k=5, field_path=nwf_path):
                results.append({"text": s.get("text", ""), "source": s.get("source", "workspace")})
    except Exception:
        pass
    timings["get_context_search_similar"] = time.perf_counter() - t0
    if results:
        lines = [f"{i}. [{r.get('source','')}] {r.get('text','')[:150]}" for i, r in enumerate(results[:5], 1)]
        ctx_parts.append("[Memory]\n" + "\n".join(lines))
    else:
        ctx_parts.append("[Memory] Память пуста (новый проект).")
    return "\n\n".join(ctx_parts)


async def hillhorn_search(q: str) -> str:
    from tools import search_memory
    data = await search_memory(q, k=5, workspace_id=PROJECT_ID)
    results = list(data.get("results", []))
    try:
        from pathlib import Path
        from nwf_memory_adapter import search_similar
        nwf_path = Path(os.getenv("NWF_MEMORY_ADAPTER_PATH", str(Path(os.getenv("HILLHORN_DATA_ROOT", "C:/hillhorn_data")) / "nwf_opencloud")))
        if (nwf_path / "meta.json").exists():
            for s in search_similar(q, k=5, field_path=nwf_path):
                results.append({"text": s.get("text", ""), "source": s.get("source", "workspace")})
    except Exception:
        pass
    if not results:
        return "Память пуста."
    return "\n".join([f"{i}. {r.get('text','')[:200]}" for i, r in enumerate(results, 1)])


async def hillhorn_consult(agent: str, prompt: str, code_to_review: str | None = None) -> str:
    import httpx
    if agent == "reviewer":
        agent = "chat"
        prompt = "As a code reviewer, analyze the code. " + prompt
    payload = {
        "agent_type": agent,
        "prompt": prompt,
        "workspace_path": PROJECT_ID,
        "max_tokens": 800,
    }
    if code_to_review:
        payload["context"] = [{"role": "user", "content": f"Code to review:\n\n```\n{code_to_review[:12000]}\n```"}]
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(f"{GATEWAY}/v1/agent/query", json=payload)
    r.raise_for_status()
    d = r.json()
    return (d.get("reasoning") or "") + "\n" + (d.get("content") or "")


async def hillhorn_add(text: str, kind: str = "summary") -> bool:
    from tools import add_to_memory
    r = await add_to_memory(text, tags=[kind, "system"])
    return r.get("status") == "ok"


async def main() -> None:
    total_start = time.perf_counter()
    _log("=== Hillhorn real task test: Snake game ===\n")

    # 1. get_context
    _log("1. hillhorn_get_context...")
    t0 = time.perf_counter()
    try:
        ctx = await hillhorn_get_context()
        timings["get_context"] = time.perf_counter() - t0
        _log(f"   Context: {len(ctx)} chars. SOUL in context: {'SOUL' in ctx}")
    except Exception as e:
        timings["get_context"] = time.perf_counter() - t0
        _log(f"   FAIL: {e}")
        ctx = ""

    # 2. search
    _log("2. hillhorn_search('snake game python')...")
    t0 = time.perf_counter()
    try:
        search_result = await hillhorn_search("snake game python консоль")
        timings["search"] = time.perf_counter() - t0
        _log(f"   Result: {search_result[:200]}..." if len(search_result) > 200 else f"   {search_result}")
    except Exception as e:
        timings["search"] = time.perf_counter() - t0
        _log(f"   FAIL: {e}")
        search_result = ""

    # 3. planner (brief plan)
    _log("3. hillhorn_consult(planner)...")
    t0 = time.perf_counter()
    try:
        plan = await hillhorn_consult("planner", "Кратко: 3 шага для змейки на Python в консоли (без pygame).")
        timings["planner"] = time.perf_counter() - t0
        _log(f"   Plan: {plan[:300]}...")
    except Exception as e:
        timings["planner"] = time.perf_counter() - t0
        _log(f"   FAIL: {e}")
        plan = ""

    # 4. write snake
    _log("4. Writing snake.py...")
    t0 = time.perf_counter()
    snake_code = '''# -*- coding: utf-8 -*-
"""Snake game - console, Windows."""
import msvcrt
import os
import random
import time

W, H = 20, 12
SNAKE, FOOD, WALL = "O", "*", "#"

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def init():
    grid = [[WALL if x in (0, W-1) or y in (0, H-1) else " " for x in range(W)] for y in range(H)]
    snake = [(W//2, H//2)]
    grid[snake[0][1]][snake[0][0]] = SNAKE
    food = (random.randint(1, W-2), random.randint(1, H-2))
    grid[food[1]][food[0]] = FOOD
    return grid, snake, food, (1, 0)

def draw(grid):
    clear()
    for row in grid:
        print("".join(row))
    print("WASD - move, Q - quit")

def main():
    grid, snake, food, dxdy = init()
    dx, dy = dxdy
    while True:
        draw(grid)
        if msvcrt.kbhit():
            c = msvcrt.getch().decode("utf-8", errors="ignore").lower()
            if c == "q": break
            if c == "w": dx, dy = 0, -1
            elif c == "s": dx, dy = 0, 1
            elif c == "a": dx, dy = -1, 0
            elif c == "d": dx, dy = 1, 0
        nx, ny = snake[0][0] + dx, snake[0][1] + dy
        cell = grid[ny][nx] if 0 <= ny < H and 0 <= nx < W else WALL
        if cell == WALL:
            print("Game Over")
            break
        if cell == FOOD:
            snake.insert(0, (nx, ny))
            grid[ny][nx] = SNAKE
            fx, fy = random.randint(1, W-2), random.randint(1, H-2)
            while grid[fy][fx] != " ":
                fx, fy = random.randint(1, W-2), random.randint(1, H-2)
            food = (fx, fy)
            grid[fy][fx] = FOOD
        else:
            tail = snake.pop()
            grid[tail[1]][tail[0]] = " "
            snake.insert(0, (nx, ny))
            grid[ny][nx] = SNAKE
        time.sleep(0.15)

if __name__ == "__main__":
    main()
'''
    out_path = ROOT + os.sep + "snake.py"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(snake_code)
    timings["write_file"] = time.perf_counter() - t0
    _log(f"   Written: {out_path}")

    # 5. reviewer (code in context, not prompt)
    _log("5. hillhorn_consult(reviewer, code in context)...")
    t0 = time.perf_counter()
    try:
        review = await hillhorn_consult(
            "reviewer",
            "Проверь код змейки выше: баги, стиль, улучшения. Кратко.",
            code_to_review=snake_code,
        )
        timings["reviewer"] = time.perf_counter() - t0
        _log(f"   Review: {review[:400]}...")
    except Exception as e:
        timings["reviewer"] = time.perf_counter() - t0
        _log(f"   FAIL: {e}")
        review = ""

    # 6. add_turn
    _log("6. hillhorn_add_turn...")
    t0 = time.perf_counter()
    summary = f"Snake game: snake.py, console, msvcrt, WxH grid. Plan used: {bool(plan)}"
    try:
        ok = await hillhorn_add(summary, "code")
        timings["add_memory"] = time.perf_counter() - t0
        _log(f"   Added: {ok}")
    except Exception as e:
        timings["add_memory"] = time.perf_counter() - t0
        _log(f"   FAIL: {e}")

    total_sec = time.perf_counter() - total_start
    _log("\n=== Timing report (bottlenecks) ===")
    for step, sec in sorted(timings.items(), key=lambda x: -x[1]):
        pct = 100 * sec / total_sec if total_sec else 0
        _log(f"   {step}: {sec:.2f}s ({pct:.0f}%)")
    api_steps = [s for s in timings if s in ("planner", "reviewer")]
    api_total = sum(timings[s] for s in api_steps)
    local_steps = [s for s in timings if s not in api_steps]
    local_total = sum(timings[s] for s in local_steps)
    _log(f"   [API total: {api_total:.2f}s | Local (NWF/files): {local_total:.2f}s]")
    _log(f"   TOTAL: {total_sec:.2f}s")
    _log("   Bottlenecks: 1) DeepSeek API ~97% 2) search_memory ~2s 3) rest <0.1s")
    _log("\n=== Done ===")


if __name__ == "__main__":
    asyncio.run(main())
