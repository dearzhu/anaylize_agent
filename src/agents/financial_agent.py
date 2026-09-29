"""财报分析 Agent（Worker）。

职责：结构化财报解析 -> 指标计算 -> 同比 -> 异常检测 -> 健康度判定。
底层复用一期 `financial` 模块（规则引擎算数，LLM 不参与）。
"""
from __future__ import annotations

import os
from typing import Any, Dict, List

from orchestrator.base import BaseAgent
from agents.base import register, resolve_path
from core.config import settings

_DEFAULT_FINANCIAL = "./data/sample_financials/company_a_2023.json"


def _classify_health(findings: List[dict], ratios: Dict[str, Any]) -> str:
    risks = [f for f in findings if f.get("level") == "risk"]
    warnings = [f for f in findings if f.get("level") == "warning"]
    if risks:
        return "预警"
    if warnings:
        return "关注"
    return "良好"


@register
class FinancialAgent(BaseAgent):
    name = "financial_agent"
    description = "财报分析：指标计算、同比变动与异常检测"
    depends_on: List[str] = []
    requires_llm = False

    def run(self, task: Dict[str, Any], ctx) -> Any:
        from financial.parser import load_pair
        from financial.metrics import compute_ratios, compare_yoy
        from financial.anomaly import detect_anomalies

        path = task.get("financial_path") or _DEFAULT_FINANCIAL
        abs_path = resolve_path(path)
        if not os.path.exists(abs_path):
            return self._fail(f"未找到财报文件：{abs_path}")

        cur, prior = load_pair(abs_path)
        ratios = compute_ratios(cur)
        yoy = compare_yoy(cur, prior) if prior else {}
        raw_findings = (
            detect_anomalies(
                cur, prior,
                yoy_threshold=settings.financial.anomaly_yoy_threshold,
                cash_profit_min=settings.financial.cash_profit_ratio_min,
            )
            if prior else []
        )
        findings = [
            {"level": f.level, "item": f.item, "message": f.message, "value": f.value}
            for f in raw_findings
        ]
        health = _classify_health(findings, ratios)

        non_null = sum(1 for v in ratios.values() if v is not None)
        completeness = non_null / max(len(ratios), 1)
        confidence = round(0.7 * completeness + 0.3 * (1.0 if prior else 0.4), 3)

        summary = (
            f"{cur.company}（{cur.period}）财报健康度【{health}】："
            f"ROE={ratios.get('ROE')}, 资产负债率={ratios.get('资产负债率')}，"
            f"发现 {len(findings)} 项异常/预警。"
        )
        output = {
            "company": cur.company, "period": cur.period,
            "ratios": ratios, "yoy": yoy, "findings": findings, "health": health,
            "summary": summary,
        }
        return self._ok(output, confidence=confidence, sources=[abs_path], notes=summary,
                       task=task.get("query", ""))
