"""Agent 注册表（二期/三期）。

收集各 Worker Agent 类，供 `orchestrator.supervisor.Supervisor` 调度。
Agent 自身继承 `orchestrator.base.BaseAgent`，并用 `@register` 装饰后在此登记。
"""
from __future__ import annotations

import os
from typing import Any, Dict, Type

# name -> Agent 类
_AGENT_REGISTRY: Dict[str, Type] = {}


def register(cls: Type) -> Type:
    """类装饰器：将 Worker Agent 注册到全局表（键为 cls.name）。"""
    if not getattr(cls, "name", None):
        raise ValueError(f"Agent {cls.__name__} 必须定义类属性 name")
    _AGENT_REGISTRY[cls.name] = cls
    return cls


def build_registry(client: Any = None) -> Dict[str, Any]:
    """返回 {name: 实例} 字典。client 预留给需要 LLM 的 Agent，当前统一忽略。"""
    return {name: cls() for name, cls in _AGENT_REGISTRY.items()}


def list_agents() -> list:
    return sorted(_AGENT_REGISTRY.keys())


# 项目根目录（src/agents/base.py -> src -> 项目根）
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def resolve_path(path: str) -> str:
    """将配置中的相对路径解析为基于项目根的绝对路径。"""
    if os.path.isabs(path):
        return path
    return os.path.join(_PROJECT_ROOT, path)
