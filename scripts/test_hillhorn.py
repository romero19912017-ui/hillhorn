# -*- coding: utf-8 -*-
"""Test Hillhorn: search, add, consult_agent. Run: python scripts/test_hillhorn.py"""
from __future__ import annotations

import asyncio
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

PROJECT_ID = r"c:\Hillhorn"
GATEWAY = os.getenv("HILLHORN_GATEWAY_URL", "http://localhost:8001")


async def test_search():
    from tools import search_memory
    result = await search_memory("общая информация о проекте", k=5, workspace_id=PROJECT_ID)
    results = result.get("results", [])
    print(f"[search] OK, {len(results)} results" if results else "[search] Empty (memory may be new)")
    return result


async def test_add():
    from tools import add_to_memory
    result = await add_to_memory(
        "Test: Hillhorn memory works.",
        tags=["doc", "system"],
    )
    ok = result.get("status") == "ok"
    print(f"[add] {'OK' if ok else result}")
    return result


async def test_consult():
    import httpx
    payload = {
        "agent_type": "chat",
        "prompt": "Say 'Hillhorn OK' in one sentence.",
        "workspace_path": PROJECT_ID,
        "max_tokens": 100,
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(f"{GATEWAY}/v1/agent/query", json=payload)
        r.raise_for_status()
        data = r.json()
        content = data.get("content", "")
        print(f"[consult] OK: {content[:150]}...")
        return content
    except httpx.ConnectError:
        print("[consult] FAIL: Gateway not running")
        return ""
    except Exception as e:
        print(f"[consult] FAIL: {e}")
        return ""


async def main():
    print("=== Hillhorn Test ===\n")
    await test_search()
    await test_add()
    await test_consult()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
