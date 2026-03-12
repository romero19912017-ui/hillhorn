# -*- coding: utf-8 -*-
"""Hillhorn integration test: snake game. Workflow get_context -> search -> write snake -> add."""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECT_ID = str(ROOT)
SNAKE_CODE = '''# -*- coding: utf-8 -*-
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

def draw(grid, score=0):
    clear()
    for row in grid:
        print("".join(row))
    print("WASD - move, Q - quit | Score:", score)

def main():
    grid, snake, food, dxdy = init()
    dx, dy = dxdy
    score = 0
    while True:
        draw(grid, score)
        if msvcrt.kbhit():
            c = msvcrt.getch().decode("utf-8", errors="ignore").lower()
            if c == "q":
                break
            if c == "w": dx, dy = 0, -1
            elif c == "s": dx, dy = 0, 1
            elif c == "a": dx, dy = -1, 0
            elif c == "d": dx, dy = 1, 0
        nx, ny = snake[0][0] + dx, snake[0][1] + dy
        if (nx, ny) in snake[:-1]:
            print("Game Over - self collision")
            break
        cell = grid[ny][nx] if 0 <= ny < H and 0 <= nx < W else WALL
        if cell == WALL:
            print("Game Over")
            break
        if cell == FOOD:
            score += 1
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


async def task_snake() -> dict:
    """Snake: get_context -> search -> write -> add."""
    from tools import search_memory, add_to_memory
    timings = {}
    t0 = time.perf_counter()
    # 1. get_context (files + search)
    base = Path(PROJECT_ID)
    ctx_parts = []
    for name in ("SOUL.md", "USER.md", "MEMORY.md"):
        p = base / name
        if p.exists():
            try:
                t = p.read_text(encoding="utf-8", errors="replace").strip()[:500]
                if t:
                    ctx_parts.append(t)
            except Exception:
                pass
    timings["files"] = time.perf_counter() - t0
    t0 = time.perf_counter()
    data = await search_memory("змейка игра консоль python", k=5, workspace_id=PROJECT_ID)
    timings["search"] = time.perf_counter() - t0
    results = data.get("results", [])
    try:
        from nwf_memory_adapter import search_similar
        nwf_path = Path(os.getenv("NWF_MEMORY_ADAPTER_PATH", str(Path(os.getenv("HILLHORN_DATA_ROOT", "C:/hillhorn_data")) / "nwf_opencloud")))
        if (nwf_path / "meta.json").exists():
            for s in search_similar("змейка игра", k=3, field_path=nwf_path):
                results.append({"text": s.get("text", ""), "source": s.get("source", "workspace")})
    except Exception:
        pass
    t0 = time.perf_counter()
    (ROOT / "snake.py").write_text(SNAKE_CODE, encoding="utf-8")
    timings["write"] = time.perf_counter() - t0
    t0 = time.perf_counter()
    r = await add_to_memory("Snake game: snake.py, console, msvcrt, WASD, score, self-collision", tags=["code", "summary"], project_id=PROJECT_ID)
    timings["add"] = time.perf_counter() - t0
    return {
        "time": sum(timings.values()),
        "timings": timings,
        "search_results": len(results),
        "add_ok": r.get("status") == "ok",
        "calls": 4,
    }


async def main():
    print("=== Hillhorn Snake Test ===\n")
    try:
        result = await task_snake()
        print("OK:", result)
        out = ROOT / "hillhorn_checks" / "results.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nResults: {out}")
    except Exception as e:
        print("FAIL:", e)
        raise


if __name__ == "__main__":
    asyncio.run(main())
