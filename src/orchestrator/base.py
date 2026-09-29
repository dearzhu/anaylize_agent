"""Agent 基类与共享上下文。

BaseAgent 约定：
  - name / description / capabilities / requires_llm / depends_on 描述能力边界；
  - run(task, ctx) -> AgentMessage 为唯一入口；
  - 所有计算由工具/规则引擎完成，LLM 只做解读（数值一致性原则）。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .message import AgentMessage


class AgentContext:
    """跨 Agent 共享上下文，Supervisor 在调度时注入上游结果。"""

    def __init__(self) -> None:
        self._store: Dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        self._store[key] = value

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        return self._store.get(key, default)

    def has(self, key: str) -> bool:
        return key in self._store


class BaseAgent(ABC):
    name: str = "base"
    description: str = ""
    capabilities: List[str] = []
    requires_llm: bool = False
    depends_on: List[str] = []

    @abstractmethod
    def run(self, task: Dict[str, Any], ctx: AgentContext) -> AgentMessage:
        ...

    # ---- 便捷构造 ----
    def _ok(self, output: Dict[str, Any], confidence: float = 1.0,
            sources: Optional[List[str]] = None, notes: str = "",
            task: str = "") -> AgentMessage:
        return AgentMessage(
            agent=self.name, task=task, success=True,
            output=output, confidence=confidence,
            sources=sources or [], notes=notes or output.get("summary", ""),
        )

    def _fail(self, reason: str, task: str = "") -> AgentMessage:
        return AgentMessage(
            agent=self.name, task=task, success=False,
            output={}, confidence=0.0, notes=reason,
        )
