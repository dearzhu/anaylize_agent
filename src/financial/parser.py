"""科目标准化：将不同来源/命名的财报映射为统一字段，缺失项置 None。

统一字段（简化版，可按需扩展）：
  资产负债表 balance_sheet: total_assets, current_assets, inventory,
      accounts_receivable, total_liabilities, current_liabilities, total_equity
  利润表 income_statement: revenue, cost_of_goods_sold, gross_profit,
      operating_profit, ebit, interest_expense, net_profit
  现金流量表 cash_flow: operating_cash_flow, net_cash_flow
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Dict, Optional

_BS_FIELDS = [
    "total_assets", "current_assets", "inventory", "accounts_receivable",
    "total_liabilities", "current_liabilities", "total_equity",
]
_IS_FIELDS = [
    "revenue", "cost_of_goods_sold", "gross_profit", "operating_profit",
    "ebit", "interest_expense", "net_profit",
]
_CF_FIELDS = ["operating_cash_flow", "net_cash_flow"]


@dataclass
class Financials:
    company: str
    period: str
    balance_sheet: Dict[str, Optional[float]] = field(default_factory=dict)
    income_statement: Dict[str, Optional[float]] = field(default_factory=dict)
    cash_flow: Dict[str, Optional[float]] = field(default_factory=dict)


def _normalize(raw: dict, fields: list) -> Dict[str, Optional[float]]:
    out = {k: None for k in fields}
    for k, v in raw.items():
        if k in out and v is not None:
            try:
                out[k] = float(v)
            except (TypeError, ValueError):
                out[k] = None
    return out


def standardize(raw: dict) -> Financials:
    st = raw.get("statements", raw)
    return Financials(
        company=raw.get("company", ""),
        period=raw.get("period", ""),
        balance_sheet=_normalize(st.get("balance_sheet", {}), _BS_FIELDS),
        income_statement=_normalize(st.get("income_statement", {}), _IS_FIELDS),
        cash_flow=_normalize(st.get("cash_flow", {}), _CF_FIELDS),
    )


def load_financials(json_path: str) -> Financials:
    with open(json_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return standardize(raw)


def load_pair(json_path: str):
    """加载同一文件中的本期与去年同期数据，返回 (current, prior)。

    JSON 结构需含：顶层 statements 为本期的，另含 prior:{period, statements} 为去年同期。
    """
    with open(json_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    current = standardize(raw)
    prior_raw = raw.get("prior")
    prior = standardize(prior_raw) if prior_raw else None
    return current, prior
