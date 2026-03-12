# -*- coding: utf-8 -*-
"""Hillhorn - анализ результатов snake test."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "hillhorn_checks" / "results.json"
REPORT = ROOT / "hillhorn_checks" / "REPORT.md"


def main() -> None:
    print("=== Hillhorn Snake Test Analysis ===\n")
    if not RESULTS.exists():
        print("No results.json. Run: python hillhorn_checks/run_tasks.py")
        return
    data = json.loads(RESULTS.read_text(encoding="utf-8"))
    total_time = data.get("time", 0)
    total_calls = data.get("calls", 0)
    timings = data.get("timings", {})
    out = [
        "# Hillhorn Check Report",
        "",
        f"Total time: {total_time:.2f}s",
        f"Calls: {total_calls}",
        f"Search results: {data.get('search_results', 0)}",
        f"Add OK: {data.get('add_ok', False)}",
        "",
        "## Timings",
    ]
    for k, v in timings.items():
        out.append(f"- {k}: {v:.3f}s")
    out.append("")
    REPORT.write_text("\n".join(out), encoding="utf-8")
    print(f"Report: {REPORT}")
    print(f"Total: {total_time:.2f}s, calls: {total_calls}")


if __name__ == "__main__":
    main()
