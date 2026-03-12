# -*- coding: utf-8 -*-
"""DeepSeek agents: BaseAgent, CoderAgent, PlannerAgent, ChatAgent."""

from __future__ import annotations

from abc import ABC
from typing import Any, List, Optional

import httpx

# -----------------------------------------------------------------------------
# BaseAgent
# -----------------------------------------------------------------------------


class BaseAgent(ABC):
    """Базовый агент для запросов в DeepSeek через MCP Gateway."""

    def __init__(self, agent_type: str, gateway_url: str = "http://localhost:8001"):
        self.agent_type = agent_type
        self.gateway_url = gateway_url.rstrip("/")
        self.conversation_history: List[dict] = []

    async def query(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        tools: Optional[list] = None,
        auto_agent: bool = False,
    ) -> str:
        """Отправить запрос в DeepSeek через MCP Gateway."""
        self.conversation_history.append({"role": "user", "content": prompt})
        context = self.conversation_history[-6:-1] if len(self.conversation_history) > 1 else None
        payload = {
            "agent_type": self.agent_type,
            "prompt": prompt,
            "context": context,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "auto_agent": auto_agent,
        }
        if tools is not None:
            payload["tools"] = tools
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                r = await client.post(
                    f"{self.gateway_url}/v1/agent/query",
                    json=payload,
                )
            if r.status_code == 200:
                data = r.json()
                reply = data.get("content", "")
                self.conversation_history.append({"role": "assistant", "content": reply})
                return reply
            err = f"Agent error: {r.status_code} - {r.text[:200]}"
            self.conversation_history.append({"role": "system", "content": err})
            return err
        except Exception as e:
            err = f"Agent error: {e}"
            self.conversation_history.append({"role": "system", "content": err})
            return err

    def clear_history(self) -> None:
        self.conversation_history.clear()


# -----------------------------------------------------------------------------
# Concrete agents
# -----------------------------------------------------------------------------


class CoderAgent(BaseAgent):
    """Агент для генерации кода (deepseek-chat)."""

    def __init__(self, gateway_url: str = "http://localhost:8001"):
        super().__init__("coder", gateway_url)

    async def generate_function(
        self,
        specification: str,
        language: str = "python",
        temperature: float = 0.3,
    ) -> str:
        prompt = (
            f"Write a {language} function that: {specification}\n"
            "Include docstring and type hints."
        )
        return await self.query(prompt, temperature=temperature)


class PlannerAgent(BaseAgent):
    """Агент для планирования (deepseek-reasoner)."""

    def __init__(self, gateway_url: str = "http://localhost:8001"):
        super().__init__("planner", gateway_url)

    async def create_plan(self, task: str, temperature: float = 0.5, use_tools: bool = True) -> str:
        prompt = f"""Create a step-by-step implementation plan for: {task}

Format:
1. Overview
2. Prerequisites
3. Steps (with dependencies)
4. Testing strategy
5. Potential pitfalls

You can use search_memory to find similar past plans, read_file to inspect the codebase."""
        tools = None
        if use_tools:
            try:
                from tools import TOOL_DEFINITIONS
                tools = TOOL_DEFINITIONS
            except Exception:
                pass
        return await self.query(prompt, temperature=temperature, tools=tools)


class ReviewerAgent(BaseAgent):
    """Агент для code review (deepseek-chat)."""

    def __init__(self, gateway_url: str = "http://localhost:8001"):
        super().__init__("reviewer", gateway_url)

    async def review_code(self, code: str, focus: Optional[str] = None) -> str:
        prompt = f"Review this code for bugs, security, and improvements:\n\n```\n{code}\n```"
        if focus:
            prompt += f"\nFocus especially on: {focus}"
        return await self.query(prompt, temperature=0.3)


class ChatAgent(BaseAgent):
    """Агент для общего общения (deepseek-chat)."""

    def __init__(self, gateway_url: str = "http://localhost:8001"):
        super().__init__("chat", gateway_url)


class ArchitectAgent(BaseAgent):
    """Агент для проектирования архитектуры (deepseek-reasoner)."""

    def __init__(self, gateway_url: str = "http://localhost:8001"):
        super().__init__("architect", gateway_url)

    async def design_architecture(self, description: str, temperature: float = 0.5) -> str:
        prompt = f"Design system architecture for: {description}\n\nProvide: components, interfaces, data flow."
        return await self.query(prompt, temperature=temperature)


class DocumenterAgent(BaseAgent):
    """Агент для документации (deepseek-chat)."""

    def __init__(self, gateway_url: str = "http://localhost:8001"):
        super().__init__("documenter", gateway_url)

    async def document_code(self, code: str, fmt: str = "markdown") -> str:
        prompt = f"Document this code in {fmt}:\n\n```\n{code}\n```"
        return await self.query(prompt, temperature=0.3)


class TesterMathAgent(BaseAgent):
    """Агент для проверки математики и логики (deepseek-reasoner)."""

    def __init__(self, gateway_url: str = "http://localhost:8001"):
        super().__init__("tester_math", gateway_url)

    async def verify_math(self, expression: str) -> str:
        prompt = f"Verify correctness and explain: {expression}"
        return await self.query(prompt, temperature=0.2)


# -----------------------------------------------------------------------------
# AgentSelector (NWF-based)
# -----------------------------------------------------------------------------


def _text_embedding_simple(text: str, dim: int = 32):
    """Единый эмбеддинг через модуль embeddings."""
    from embeddings import get_embedding
    return get_embedding(text, dim=dim)


def select_agent_from_memory(memory_path: str, user_request: str, k: int = 10) -> str:
    """
    Выбрать наиболее подходящего агента из NWF-памяти по похожим прошлым запросам.
    Возвращает agent_type: coder, planner, reviewer, chat.
    """
    try:
        from nwf import Field
        from pathlib import Path
        p = Path(memory_path)
        if not (p / "meta.json").exists():
            return "chat"
        field = Field()
        field.load(p)
        if len(field) == 0:
            return "chat"
        import numpy as np
        req_z = _text_embedding_simple(user_request)
        charges = field.get_charges()
        z_all = np.stack([c.z for c in charges], axis=0)
        d = np.linalg.norm(req_z - z_all, axis=1)
        idx = np.argsort(d)[:k]
        counts = {"coder": 0.0, "planner": 0.0, "reviewer": 0.0, "chat": 0.0, "architect": 0.0, "documenter": 0.0, "tester_math": 0.0}
        for i in idx:
            lab = field.get_labels()[int(i)]
            if isinstance(lab, dict) and lab.get("success", False):
                at = lab.get("agent_type", "chat")
                if at in counts:
                    c = charges[int(i)]
                    w = c.alpha / (np.mean(c.sigma) + 0.01)
                    counts[at] += w
        return max(counts, key=counts.get)
    except Exception:
        return "chat"
