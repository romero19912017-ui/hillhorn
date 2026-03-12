# -*- coding: utf-8 -*-
"""
Hillhorn - анализ результатов проверок, заполнение REPORT.md из results.json.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "hillhorn_checks" / "results.json"
REPORT_TEMPLATE = ROOT / "hillhorn_checks" / "REPORT_TEMPLATE.md"
REPORT = ROOT / "hillhorn_checks" / "REPORT.md"


def main() -> None:
    print("=== Hillhorn Check Analysis ===\n")
    if not RESULTS.exists():
        print("No results.json. Run: python hillhorn_checks/run_tasks.py")
        return
    data = json.loads(RESULTS.read_text(encoding="utf-8"))

    total_time = 0
    total_calls = 0
    task_names = {"01": "01 Cold Start", "02": "02 Warm Context", "03": "03 Planner", "04": "04 Reviewer", "05": "05 Index+Search"}
    table_rows = []
    for name in ("01", "02", "03", "04", "05"):
        r = data.get(name, {})
        label = task_names.get(name, name)
        err = r.get("error")
        if err:
            table_rows.append(f"| {label} | FAIL | - | - | {str(err)[:40]}... |")
            continue
        total_time += r.get("time", 0)
        total_calls += r.get("calls", 0)
        t_first = r.get("time_to_first_result", r.get("time", 0))
        search = "-"
        if "search_relevant" in r:
            search = r["search_relevant"]
        elif "search_found" in r:
            search = "yes" if r["search_found"] else "no"
        consult = "-"
        if "plan_len" in r:
            consult = f"plan {r['plan_len']}ch"
        elif "review_len" in r:
            consult = f"review {r['review_len']}ch"
        t_str = f"{r.get('time', 0):.1f}s"
        table_rows.append(f"| {label} | OK | {search} | {consult} | {t_str} |")

    lines = REPORT_TEMPLATE.read_text(encoding="utf-8").splitlines() if REPORT_TEMPLATE.exists() else []
    out = []
    in_table = False
    for line in lines:
        if "| 01 Cold Start |" in line:
            in_table = True
            out.extend(table_rows)
            continue
        if in_table and line.strip().startswith("|") and "---" not in line:
            continue
        if in_table and not line.strip().startswith("|"):
            in_table = False
        out.append(line)

    out_str = "\n".join(out)
    out_str = out_str.replace("___________", f"{total_time/60:.1f} min" if total_time else "___")
    out_str = out_str.replace("Всего вызовов Hillhorn: ___", f"Всего вызовов Hillhorn: {total_calls}")
    REPORT.write_text(out_str, encoding="utf-8")
    print(f"Report written: {REPORT}")
    print(f"Total time: {total_time:.1f}s, Total calls: {total_calls}")


if __name__ == "__main__":
    main()
