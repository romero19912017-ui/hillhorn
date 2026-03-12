# -*- coding: utf-8 -*-
"""Выполнение задач Hillhorn checks с замерами и отчетом."""
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

def _import_mcp():
    from hillhorn_mcp_server import (
        hillhorn_get_context,
        hillhorn_search,
        hillhorn_add_turn,
        hillhorn_consult_agent,
        hillhorn_index_file,
    )
    return hillhorn_get_context, hillhorn_search, hillhorn_add_turn, hillhorn_consult_agent, hillhorn_index_file

async def task_01():
    """Cold start: greet.py"""
    get_ctx, search, add_turn, consult, _ = _import_mcp()
    t0 = time.perf_counter()
    ctx = await get_ctx()
    t_first = time.perf_counter() - t0
    r1 = await search("greet utility hello")
    out = ROOT / "hillhorn_checks" / "tasks" / "task_01_cold_start" / "greet.py"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('# -*- coding: utf-8 -*- """Greet utility."""\nimport sys\ndef greet(name):\n    return f"Hello, {name}!"\nif __name__ == "__main__":\n    print(greet(sys.argv[1] if len(sys.argv) > 1 else "World"))\n', encoding="utf-8")
    await add_turn("Создана greet.py - простая утилита приветствия", kind="code")
    return {"time": time.perf_counter() - t0, "time_to_first_result": t_first, "iteration_count": 3, "search_relevant": "empty" if "пуста" in r1 else "yes", "calls": 3}

async def task_02():
    """Warm context: bye.py"""
    get_ctx, search, add_turn, _, _ = _import_mcp()
    t0 = time.perf_counter()
    await get_ctx()
    t_first = time.perf_counter() - t0
    r = await search("greet.py утилита приветствия")
    found = "пуста" not in r and ("greet" in r.lower() or "приветств" in r.lower())
    out = ROOT / "hillhorn_checks" / "tasks" / "task_02_warm_context" / "bye.py"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('# -*- coding: utf-8 -*- """Bye utility."""\nimport sys\ndef bye(name):\n    return f"Bye, {name}!"\nif __name__ == "__main__":\n    print(bye(sys.argv[1] if len(sys.argv) > 1 else "World"))\n', encoding="utf-8")
    await add_turn("bye.py - прощание, стиль как greet", kind="code")
    return {"time": time.perf_counter() - t0, "time_to_first_result": t_first, "iteration_count": 3, "search_found": found, "calls": 3}

async def task_03():
    """Planner: calc.py"""
    get_ctx, search, add_turn, consult, _ = _import_mcp()
    t0 = time.perf_counter()
    await get_ctx()
    t_first = time.perf_counter() - t0
    plan = await consult(agent_type="planner", prompt="План для CLI калькулятора: аргументы, парсинг, +-*/. 3-4 шага.")
    out = ROOT / "hillhorn_checks" / "tasks" / "task_03_planner" / "calc.py"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('# -*- coding: utf-8 -*- """CLI calc."""\nimport sys\nif len(sys.argv) != 4:\n    print("Usage: calc.py A op B"); sys.exit(1)\na, op, b = float(sys.argv[1]), sys.argv[2], float(sys.argv[3])\nprint({"+":a+b,"-":a-b,"*":a*b,"/":a/b}[op])\n', encoding="utf-8")
    await add_turn("calc.py - CLI калькулятор, план от planner", kind="doc")
    return {"time": time.perf_counter() - t0, "time_to_first_result": t_first, "iteration_count": 3, "plan_len": len(plan), "calls": 3}

async def task_04():
    """Reviewer"""
    get_ctx, search, add_turn, consult, _ = _import_mcp()
    calc = ROOT / "hillhorn_checks" / "tasks" / "task_03_planner" / "calc.py"
    code = calc.read_text(encoding="utf-8") if calc.exists() else "print(1+1)"
    t0 = time.perf_counter()
    review = await consult(agent_type="reviewer", prompt="Проверь на баги и стиль.", code_to_review=code)
    t_first = time.perf_counter() - t0
    t_first = time.perf_counter() - t0
    await add_turn("Ревью calc.py: выполнено", kind="summary")
    return {"time": time.perf_counter() - t0, "time_to_first_result": t_first, "iteration_count": 2, "review_len": len(review), "calls": 2}

async def task_05():
    """Index + Search"""
    get_ctx, search, add_turn, consult, index_file = _import_mcp()
    soul = ROOT / "SOUL.md"
    content = soul.read_text(encoding="utf-8") if soul.exists() else "Agent identity"
    t0 = time.perf_counter()
    await index_file(file_path="SOUL.md", content=content)
    t_first = time.perf_counter() - t0
    t_first = time.perf_counter() - t0
    r = await search("Agent identity NWF-JEPA")
    found = "пуста" not in r and ("Agent" in r or "identity" in r or "NWF" in r)
    return {"time": time.perf_counter() - t0, "time_to_first_result": t_first, "iteration_count": 2, "search_found": found, "calls": 2}

async def main():
    results = {}
    for name, fn in [("01", task_01), ("02", task_02), ("03", task_03), ("04", task_04), ("05", task_05)]:
        try:
            results[name] = await fn()
            print(f"Task {name}: OK {results[name]}")
        except Exception as e:
            results[name] = {"error": str(e)}
            print(f"Task {name}: FAIL {e}")
    out = ROOT / "hillhorn_checks" / "results.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nResults: {out}")

if __name__ == "__main__":
    asyncio.run(main())
