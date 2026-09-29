"""通用格式化与工具函数（供编排层与各 Agent 复用）。"""
from __future__ import annotations

from typing import Any, Optional


def fmt_pct(v: Optional[float], nd: int = 1) -> str:
    if v is None:
        return "N/A"
    return f"{v * 100:.{nd}f}%"


def fmt_num(v: Optional[float], nd: int = 2) -> str:
    if v is None:
        return "N/A"
    return f"{v:,.{nd}f}"


def safe_round(v: Any, nd: int = 4) -> Any:
    return round(v, nd) if isinstance(v, float) else v
