"""风控分析 Agent（Worker）。

职责：信用/流动性/盈利质量/合规 多维风险评估与预警。
输入：财报 Agent 输出（指标/异常）+ 流水 Agent 输出（异常/合规信号）。
纯规则引擎，阈值来自 RiskConfig。
"""
from __future__ import annotations

from typing import Any, Dict, List

from orchestrator.base import BaseAgent
from agents.base import register


def _band(value, warn, risk, good=85, mid=50, bad=20):
    """越低越危险（比率类）。返回 0~100。"""
    if value is None:
        return 60
    if value <= risk:
        return bad
    if value <= warn:
        return mid
    return good


def _band_high(value, warn, risk, good=85, mid=50, bad=20):
    """越高越危险（资产负债率类）。"""
    if value is None:
        return 60
    if value >= risk:
        return bad
    if value >= warn:
        return mid
    return good


@register
class RiskAgent(BaseAgent):
    name = "risk_agent"
    description = "风控分析：偿付/流动性/盈利质量/合规 多维风险评估"
    depends_on: List[str] = ["financial_agent", "flow_agent"]
    requires_llm = False

    def run(self, task: Dict[str, Any], ctx) -> Any:
        fin_msg = ctx.get("result:financial_agent")
        flow_msg = ctx.get("result:flow_agent")
        fin = fin_msg.output if (fin_msg and fin_msg.success) else {}
        flow = flow_msg.output if (flow_msg and flow_msg.success) else {}
        ratios = fin.get("ratios", {}) or {}
        findings = fin.get("findings", []) or []
        cfg = __import__("core.config", fromlist=["settings"]).settings.risk

        solvency = int(round((
            _band_high(ratios.get("资产负债率"), cfg.asset_liab_warn, cfg.asset_liab_risk)
            + _band(ratios.get("流动比率"), cfg.current_ratio_warn, cfg.current_ratio_risk)
            + _band(ratios.get("速动比率"), 1.0, 0.5)
            + _band(ratios.get("利息保障倍数"), 3.0, 1.0)
        ) / 4))
        liquidity = _band(ratios.get("流动比率"), cfg.current_ratio_warn, cfg.current_ratio_risk)
        has_eq_risk = any(f.get("item") == "盈利质量" and f.get("level") == "risk" for f in findings)
        earn_quality = 25 if has_eq_risk else 85
        compliance_flag = flow.get("compliance_flag", False)
        compliance = 20 if compliance_flag else 90

        scores = {"偿付能力": solvency, "流动性": liquidity,
                  "盈利质量": earn_quality, "合规": compliance}

        alerts: List[str] = []
        risk_level = "低"
        if solvency < 30 or liquidity < 30 or compliance < 30:
            risk_level = "高"
        elif solvency < 55 or liquidity < 55 or earn_quality < 55 or compliance < 55:
            risk_level = "中"
        for dim, sc in scores.items():
            if sc < 55:
                word = "高危" if sc < 30 else "预警"
                alerts.append(f"{dim}{word}（评分 {sc}）")
        if ratios.get("资产负债率") is not None and ratios["资产负债率"] >= cfg.asset_liab_risk:
            alerts.append(f"资产负债率 {ratios['资产负债率']:.1%} 超过高危线 {cfg.asset_liab_risk:.0%}")
        if compliance_flag:
            alerts.append("流水存在疑似拆分交易，触发合规校验")

        fin_conf = fin.get("confidence", 0.6) if isinstance(fin, dict) else 0.6
        flow_conf = flow.get("confidence", 0.6) if isinstance(flow, dict) else 0.3
        confidence = round(0.6 * fin_conf + 0.4 * flow_conf, 3)

        summary = (f"综合风险等级【{risk_level}】；"
                   + ("；".join(alerts) if alerts else "各维度指标均在安全区间") + "。")
        output = {
            "risk_level": risk_level, "scores": scores, "findings": alerts,
            "compliance": {"passed": not compliance_flag,
                           "issues": alerts if compliance_flag else []},
            "summary": summary,
        }
        return self._ok(output, confidence=confidence, notes=summary, task=task.get("query", ""))
