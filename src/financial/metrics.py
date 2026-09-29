"""财务指标计算引擎：盈利能力、偿债能力、运营能力、成长性。

所有函数对缺失数据返回 None（而非抛错），保证解析鲁棒性。
数值一律以解析得到的原始数据为准（LLM 不参与算数）。
"""
from __future__ import annotations

from typing import Dict, Optional

from .parser import Financials


def _safe_div(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b in (None, 0):
        return None
    return a / b


def compute_ratios(f: Financials) -> Dict[str, Optional[float]]:
    bs, is_ = f.balance_sheet, f.income_statement
    cf = f.cash_flow

    roe = _safe_div(is_.get("net_profit"), bs.get("total_equity"))
    roa = _safe_div(is_.get("net_profit"), bs.get("total_assets"))
    gross_margin = _safe_div(is_.get("gross_profit"), is_.get("revenue"))
    net_margin = _safe_div(is_.get("net_profit"), is_.get("revenue"))
    op_margin = _safe_div(is_.get("operating_profit"), is_.get("revenue"))

    asset_liab_ratio = _safe_div(bs.get("total_liabilities"), bs.get("total_assets"))
    current_ratio = _safe_div(bs.get("current_assets"), bs.get("current_liabilities"))
    quick_ratio = _safe_div(
        (bs.get("current_assets") or 0) - (bs.get("inventory") or 0),
        bs.get("current_liabilities"),
    )
    interest_coverage = _safe_div(is_.get("ebit"), is_.get("interest_expense"))

    inv_turnover = _safe_div(is_.get("cost_of_goods_sold"), bs.get("inventory"))
    ar_turnover = _safe_div(is_.get("revenue"), bs.get("accounts_receivable"))

    return {
        "ROE": roe,
        "ROA": roa,
        "毛利率": gross_margin,
        "净利率": net_margin,
        "营业利润率": op_margin,
        "资产负债率": asset_liab_ratio,
        "流动比率": current_ratio,
        "速动比率": quick_ratio,
        "利息保障倍数": interest_coverage,
        "存货周转率": inv_turnover,
        "应收账款周转率": ar_turnover,
    }


def compare_yoy(current: Financials, prior: Financials) -> Dict[str, Optional[float]]:
    """计算同比（本期 vs 上期）增长率，覆盖三大表核心科目。"""
    keys = set(current.balance_sheet) | set(current.income_statement) | set(current.cash_flow)
    out: Dict[str, Optional[float]] = {}
    for k in keys:
        a = (current.balance_sheet.get(k) or current.income_statement.get(k)
             or current.cash_flow.get(k))
        b = (prior.balance_sheet.get(k) or prior.income_statement.get(k)
             or prior.cash_flow.get(k))
        g = _safe_div((a - b) if (a is not None and b is not None) else None, b)
        if g is not None:
            out[k] = g
    return out
