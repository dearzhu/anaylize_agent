"""策略分析 Agent（Worker）。

职责：因子挖掘、收益风险归因、组合配置建议、回测摘要。
输入：财报 Agent（成长/质量）、风控 Agent（风险等级）、流水 Agent（资金健康）。
纯规则 + 可选行情回测（prices.csv），无需 LLM。
"""
from __future__ import annotations

import os
from typing import Any, Dict

from orchestrator.base import BaseAgent
from agents.base import register, resolve_path


def _backtest(prices_path: str, risk_free: float) -> Dict[str, Any]:
    if not os.path.exists(prices_path):
        return {"available": False, "note": "未提供行情数据，回测为示意。", "cumulative_return": 0.0, "sharpe": 0.0}
    try:
        import pandas as pd
        df = pd.read_csv(prices_path)
        col = df.columns[-1]
        px = df[col].astype(float).tolist()
        if len(px) < 2:
            return {"available": True, "cumulative_return": 0.0, "sharpe": 0.0}
        rets = [(px[i] - px[i - 1]) / px[i - 1] for i in range(1, len(px))]
        cum = (px[-1] / px[0]) - 1
        mean_r = sum(rets) / len(rets)
        var = sum((r - mean_r) ** 2 for r in rets) / max(len(rets) - 1, 1)
        vol = var ** 0.5
        sharpe = ((mean_r * 252) - risk_free) / (vol * (252 ** 0.5)) if vol > 0 else 0.0
        return {"available": True, "cumulative_return": round(cum, 4),
                "annualized_return": round(mean_r * 252, 4),
                "volatility": round(vol * (252 ** 0.5), 4),
                "sharpe": round(sharpe, 3), "periods": len(px)}
    except Exception as e:  # noqa: BLE001
        return {"available": False, "note": str(e), "cumulative_return": 0.0, "sharpe": 0.0}


_PCT_MAP = {"极高": 10, "高": 10, "中": 30, "低": 60}


@register
class StrategyAgent(BaseAgent):
    name = "strategy_agent"
    description = "策略分析：因子、收益风险归因、配置建议与回测"
    depends_on: List[str] = ["financial_agent", "risk_agent", "flow_agent"]
    requires_llm = False

    def run(self, task: Dict[str, Any], ctx) -> Any:
        fin_msg = ctx.get("result:financial_agent")
        risk_msg = ctx.get("result:risk_agent")
        flow_msg = ctx.get("result:flow_agent")
        fin = fin_msg.output if (fin_msg and fin_msg.success) else {}
        risk = risk_msg.output if (risk_msg and risk_msg.success) else {}
        flow = flow_msg.output if (flow_msg and flow_msg.success) else {}
        ratios = fin.get("ratios", {}) or {}
        yoy = fin.get("yoy", {}) or {}
        findings = fin.get("findings", []) or []
        risk_level = risk.get("risk_level", "低")

        cfg = __import__("core.config", fromlist=["settings"]).settings.strategy
        value = 1.0 - (ratios.get("资产负债率") or 0.5)
        quality = (ratios.get("ROE") or 0.0) + (0.1 if not any(
            f.get("item") == "盈利质量" and f.get("level") == "risk" for f in findings) else -0.1)
        growth = yoy.get("revenue") or 0.0
        bt = _backtest(resolve_path(cfg.data_path), cfg.risk_free_rate)
        momentum = bt.get("cumulative_return", 0.0)

        factors = {
            "价值因子(低杠杆)": round(value, 3),
            "质量因子(ROE)": round(quality, 3),
            "成长因子(营收同比)": round(growth, 3),
            "动量因子(区间收益)": round(momentum, 3),
        }

        pct = _PCT_MAP.get(risk_level, 30)
        suggestion = "超配" if pct >= 60 else "标配" if pct >= 30 else "低配"
        rationale = (f"基于风险等级【{risk_level}】给出「{suggestion}」建议"
                     f"（配置比例 {pct}%）。质量{'向好' if quality > 0.1 else '偏弱'}，"
                     f"成长{'向好' if (growth or 0) > 0.1 else '偏弱/未知'}"
                     + ("；存在合规约束，建议下调敞口。" if flow.get("compliance_flag") else "。"))

        confidence = round(0.5 * risk.get("confidence", 0.6)
                          + 0.3 * fin.get("confidence", 0.6)
                          + 0.2 * (1.0 if bt.get("available") else 0.4), 3)

        output = {
            "factors": factors,
            "allocation_suggestion": suggestion,
            "suggested_allocation_pct": int(pct),
            "sharpe": bt.get("sharpe", 0.0),
            "attribution": {
                "风险约束": f"综合风险等级【{risk_level}】",
                "质量贡献": "正" if quality > 0.1 else "负",
                "成长贡献": "正" if (growth or 0) > 0.1 else "负/中性",
                "合规约束": "受限" if flow.get("compliance_flag") else "无",
            },
            "backtest": bt,
            "rationale": rationale,
            "summary": rationale,
        }
        return self._ok(output, confidence=confidence,
                       sources=(fin.get("sources", []) or [])
                       + ([resolve_path(cfg.data_path)] if bt.get("available") else []),
                       notes=rationale, task=task.get("query", ""))
