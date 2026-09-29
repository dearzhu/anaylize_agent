"""流水分析 Agent（Worker）。

职责：交易流水 / 资金流向分析、异常交易识别、客户行为画像。
约定流水 CSV 字段：date, account, counterparty, type(in/out/transfer), amount, category。
纯规则 + 统计（阈值 / 集中度 HHI），无需 LLM。
"""
from __future__ import annotations

import os
from collections import defaultdict
from typing import Any, Dict, List

from orchestrator.base import BaseAgent
from agents.base import register, resolve_path
from core.config import settings


@register
class FlowAgent(BaseAgent):
    name = "flow_agent"
    description = "流水分析：资金流向、异常交易识别、客户行为画像"
    depends_on: List[str] = []
    requires_llm = False

    def _load(self, task: Dict[str, Any]) -> List[Dict[str, Any]] | None:
        path = task.get("transactions_path") or settings.flow.data_path
        abs_path = resolve_path(path)
        if not os.path.exists(abs_path):
            return None
        import pandas as pd
        df = pd.read_csv(abs_path)
        if "txn_id" not in df.columns:
            df["txn_id"] = [f"R{i}" for i in range(len(df))]
        return df.to_dict(orient="records")

    def run(self, task: Dict[str, Any], ctx) -> Any:
        records = self._load(task)
        if records is None:
            path = task.get("transactions_path") or settings.flow.data_path
            return self._fail(f"未找到流水数据：{resolve_path(path)}")

        total_in = sum(r["amount"] for r in records if r.get("type") == "in")
        total_out = sum(r["amount"] for r in records if r.get("type") == "out")
        net = total_in - total_out
        amounts = [abs(float(r["amount"])) for r in records]
        mean_amt = sum(amounts) / len(amounts) if amounts else 0.0

        cp_agg = defaultdict(lambda: {"in": 0.0, "out": 0.0, "count": 0, "amt": 0.0})
        for r in records:
            cp = r.get("counterparty", "未知")
            a = float(r["amount"])
            d = r.get("type", "out")
            cp_agg[cp]["count"] += 1
            cp_agg[cp]["amt"] += abs(a)
            if d == "transfer":
                continue
            cp_agg[cp]["in" if d == "in" else "out"] += a

        top = sorted(cp_agg.items(), key=lambda kv: kv[1]["amt"], reverse=True)[
              : settings.flow.top_n_counterparties]
        top_counterparties = [
            {"counterparty": k, "net": round(v["in"] - v["out"], 2),
             "count": v["count"], "volume": round(v["amt"], 2)}
            for k, v in top
        ]

        total_vol = sum(v["amt"] for v in cp_agg.values()) or 1.0
        hhi = sum((v["amt"] / total_vol) ** 2 for v in cp_agg.values())

        anomalies: List[Dict[str, Any]] = []
        mult = settings.flow.large_txn_multiplier
        for r in records:
            a = abs(float(r["amount"]))
            if a > mean_amt * mult and mean_amt > 0:
                anomalies.append({
                    "txn_id": r.get("txn_id", "?"), "type": "大额异常", "amount": a,
                    "reason": f"单笔 {a:,.0f} 超过均值 {mean_amt:,.0f} 的 {mult} 倍",
                })
        for cp, v in cp_agg.items():
            sub = [r for r in records
                   if r.get("counterparty") == cp and 90000 <= abs(float(r["amount"])) < 100000]
            if len(sub) >= 3 or sum(abs(float(r["amount"])) for r in sub) > 100000:
                anomalies.append({
                    "txn_id": ",".join(str(r.get("txn_id", "?")) for r in sub),
                    "type": "疑似拆分交易",
                    "amount": sum(abs(float(r["amount"])) for r in sub),
                    "reason": f"对手方「{cp}」存在 {len(sub)} 笔处于 9~10 万区间的交易，疑似规避大额上报",
                })

        confidence = round(min(1.0, 0.5 + len(records) / 200), 3)
        compliance_flag = any(a["type"] == "疑似拆分交易" for a in anomalies)
        output = {
            "n_txn": len(records),
            "total_in": round(total_in, 2), "total_out": round(total_out, 2),
            "net_flow": round(net, 2),
            "counterparty_count": len(cp_agg),
            "concentration_hhi": round(hhi, 4),
            "top_counterparties": top_counterparties,
            "anomalies": anomalies,
            "compliance_flag": compliance_flag,
            "summary": (f"资金净流入 {net:,.0f}，涉及 {len(cp_agg)} 个对手方，"
                        f"识别出 {len(anomalies)} 项异常交易"
                        + ("（含合规风险）" if compliance_flag else "") + "。"),
        }
        return self._ok(output, confidence=confidence,
                       sources=[resolve_path(task.get("transactions_path") or settings.flow.data_path)],
                       notes=output["summary"], task=task.get("query", ""))
