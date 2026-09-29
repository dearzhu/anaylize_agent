"""编排层：意图识别、任务路由、结果融合（Supervisor + Worker 模式）。

设计原则（来自设计文档第 2/3.2 节）：
  - Supervisor 不自己算数，只做调度 + 汇总；
  - 单一职责 Agent，通过统一结构化消息（AgentMessage）通信；
  - 涉及风险/交易建议的结论需人工复核（Human-in-the-loop）。
"""
from .message import AgentMessage, FusedResult
from .base import AgentContext, BaseAgent
from .intent import IntentClassifier
from .supervisor import Supervisor

__all__ = ["AgentMessage", "FusedResult", "AgentContext", "BaseAgent",
           "IntentClassifier", "Supervisor"]
