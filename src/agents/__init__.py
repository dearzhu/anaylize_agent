"""Worker Agent 包（二期/三期）。

导入本包即触发各 Agent 模块的 @register 装饰，完成注册；
Supervisor 随后通过 `build_registry()` 获取全部 Agent 实例。
"""
from .base import register, build_registry, resolve_path, list_agents, _AGENT_REGISTRY
from . import financial_agent  # noqa: F401  注册 financial_agent
from . import rag_agent        # noqa: F401  注册 rag_agent
from . import flow_agent       # noqa: F401  注册 flow_agent
from . import risk_agent       # noqa: F401  注册 risk_agent
from . import strategy_agent   # noqa: F401  注册 strategy_agent

__all__ = [
    "register", "build_registry", "resolve_path", "list_agents",
    "financial_agent", "rag_agent", "flow_agent", "risk_agent", "strategy_agent",
]
