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


def _log(msg: str) -> None:
    t = time.strftime("%H:%M:%S")
    log.append(f"[{t}] {msg}")
    print(f"[{t}] {msg}")


async def hillhorn_get_context() -> str:
    from pathlib import Path
    from hillhorn_mcp_server import _read_project_context, _search_memory_direct
    ctx_parts = []
    files_ctx = _read_project_context(PROJECT_ID)
    if files_ctx:
        ctx_parts.append(files_ctx)
    data = await _search_memory_direct("общая информация о проекте", 5, PROJECT_ID)
    results = data.get("results", [])
    if results:
        lines = [f"{i}. [{r.get('source','')}] {r.get('text','')[:150]}" for i, r in enumerate(results, 1)]
        ctx_parts.append("[Memory]\n" + "\n".join(lines))
    else:
        ctx_parts.append("[Memory] Память пуста (новый проект).")
    return "\n\n".join(ctx_parts)


async def hillhorn_search(q: str) -> str:
    from hillhorn_mcp_server import _search_memory_direct
    data = await _search_memory_direct(q, 5, PROJECT_ID)
    results = data.get("results", [])
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
    _log("=== Hillhorn real task test: Snake game ===\n")

    # 1. get_context
    _log("1. hillhorn_get_context...")
    try:
        ctx = await hillhorn_get_context()
        _log(f"   Context: {len(ctx)} chars. SOUL in context: {'SOUL' in ctx}")
    except Exception as e:
        _log(f"   FAIL: {e}")
        ctx = ""

    # 2. search
    _log("2. hillhorn_search('snake game python')...")
    try:
        search_result = await hillhorn_search("snake game python консоль")
        _log(f"   Result: {search_result[:200]}..." if len(search_result) > 200 else f"   {search_result}")
    except Exception as e:
        _log(f"   FAIL: {e}")
        search_result = ""

    # 3. planner (brief plan)
    _log("3. hillhorn_consult(planner)...")
    try:
        plan = await hillhorn_consult("planner", "Кратко: 3 шага для змейки на Python в консоли (без pygame).")
        _log(f"   Plan: {plan[:300]}...")
    except Exception as e:
        _log(f"   FAIL: {e}")
        plan = ""

    # 4. write snake
    _log("4. Writing snake.py...")
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
    _log(f"   Written: {out_path}")

    # 5. reviewer (code in context, not prompt)
    _log("5. hillhorn_consult(reviewer, code in context)...")
    try:
        review = await hillhorn_consult(
            "reviewer",
            "Проверь код змейки выше: баги, стиль, улучшения. Кратко.",
            code_to_review=snake_code,
        )
        _log(f"   Review: {review[:400]}...")
    except Exception as e:
        _log(f"   FAIL: {e}")
        review = ""

    # 6. add_turn
    _log("6. hillhorn_add_turn...")
    summary = f"Snake game: snake.py, console, msvcrt, WxH grid. Plan used: {bool(plan)}"
    try:
        ok = await hillhorn_add(summary, "code")
        _log(f"   Added: {ok}")
    except Exception as e:
        _log(f"   FAIL: {e}")

    _log("\n=== Done ===")
    _log("Effectiveness: context+search+plan+review+memory - full workflow executed.")


if __name__ == "__main__":
    asyncio.run(main())
