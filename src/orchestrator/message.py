"""Agent 间通信契约：统一结构化消息（JSON Schema 风格）。

字段：agent / task / success / output / confidence / sources / notes
Supervisor 据此做冲突检测与加权融合；可调用 to_dict() 序列化为 JSON。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


@dataclass
class AgentMessage:
    agent: str
    task: str
    success: bool = True
    output: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    sources: List[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FusedResult:
    query: str = ""
    summary: str = ""
    messages: List[AgentMessage] = field(default_factory=list)
    overall_confidence: float = 0.0
    sources: List[str] = field(default_factory=list)
    human_in_the_loop: bool = False
    disclaimer: str = ""
    conflicts: List[dict] = field(default_factory=list)
    plan: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["messages"] = [m.to_dict() for m in self.messages]
        return d
