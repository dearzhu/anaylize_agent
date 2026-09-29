"""异常检测：同比突变预警 + 盈利质量（现金流/利润背离）提示。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .metrics import compare_yoy
from .parser import Financials


@dataclass
class Finding:
    level: str            # "warning" | "risk"
    item: str
    message: str
    value: Optional[float] = None


def detect_anomalies(current: Financials, prior: Financials,
                     yoy_threshold: float = 0.30,
                     cash_profit_min: float = 0.70) -> List[Finding]:
    findings: List[Finding] = []
    yoy = compare_yoy(current, prior)

    # 1) 同比变动超阈值
    for item, g in yoy.items():
        if g is None:
            continue
        if abs(g) >= yoy_threshold:
            findings.append(Finding(
                level="warning",
                item=item,
                message=f"{item} 同比变动 {g:+.1%}，超过阈值 {yoy_threshold:.0%}",
                value=g,
            ))

    # 2) 盈利质量：经营现金流 / 净利润 偏低
    ocf = current.cash_flow.get("operating_cash_flow")
    np_ = current.income_statement.get("net_profit")
    ratio = (ocf / np_) if (ocf is not None and np_ not in (None, 0)) else None
    if ratio is not None and ratio < cash_profit_min:
        findings.append(Finding(
            level="risk",
            item="盈利质量",
            message=(f"经营现金流/净利润 = {ratio:.2f}，低于 {cash_profit_min:.2f}，"
                     f"提示利润含金量不足或应收/存货占用偏高"),
            value=ratio,
        ))
    return findings
