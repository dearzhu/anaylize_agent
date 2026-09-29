"""意图识别：规则（关键词）+ 可选 LLM 增强。

默认走规则分类（无需 Ollama，可离线运行）；可配置 use_llm 调用本地模型做意图扩展。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class _Domain:
    name: str
    keywords: List[str] = field(default_factory=list)


_DOMAINS: List[_Domain] = [
    _Domain("financial_agent", [
        "财报", "季报", "年报", "半年报", "利润表", "资产负债表", "现金流量表",
        "财务指标", "比率", "ROE", "毛利率", "偿债能力", "盈利能力",
        "异常科目", "同比", "环比", "营收", "利润",
    ]),
    _Domain("rag_agent", [
        "规定", "法规", "监管", "披露", "办法", "指引", "条例", "细则",
        "要点", "政策", "是什么", "如何", "要求", "新规",
    ]),
    _Domain("flow_agent", [
        "流水", "资金流", "资金流向", "交易", "收支", "进出账", "账户",
        "客户行为", "转账", "对手方", "入账", "出账",
    ]),
    _Domain("risk_agent", [
        "风险", "合规", "预警", "敞口", "信用", "流动性", "评级", "风控",
        "监管处罚", "承压",
    ]),
    _Domain("strategy_agent", [
        "策略", "回测", "因子", "组合", "配置", "收益", "夏普", "持仓",
        "投资建议", "买入", "卖出", "仓位", "可投资", "配置比例",
    ]),
]


class IntentClassifier:
    def __init__(self, use_llm: bool = False, client=None, fallback: List[str] = None):
        self.use_llm = use_llm
        self.client = client
        self.fallback = fallback or ["rag_agent", "financial_agent"]
        self.domains = _DOMAINS

    def classify(self, query: str) -> List[str]:
        if self.use_llm and self.client is not None:
            try:
                return self._classify_llm(query)
            except Exception:
                pass  # 降级到规则
        return self._classify_rule(query)

    def _classify_rule(self, query: str) -> List[str]:
        scores: Dict[str, int] = {d.name: 0 for d in self.domains}
        for d in self.domains:
            for kw in d.keywords:
                if kw in query:
                    scores[d.name] += 1
        selected = [n for n, s in scores.items() if s > 0]
        if not selected:
            return list(self.fallback)
        selected.sort(key=lambda n: scores[n], reverse=True)
        return selected

    def _classify_llm(self, query: str) -> List[str]:
        valid = [d.name for d in self.domains]
        prompt = (
            "你是金融智能体的意图路由器。请从以下 Agent 列表中选择与用户问题最相关的"
            f"（可多选，按相关性排序），仅返回 JSON 数组：{valid}\n用户问题：{query}"
        )
        resp = self.client.chat(
            [{"role": "user", "content": prompt}],
            model=self.client.llm_model,
        )
        arr = json.loads(resp)
        return [a for a in arr if a in valid] or list(self.fallback)

    def describe(self, names: List[str]) -> str:
        desc = {d.name: d.keywords[:3] for d in self.domains}
        return ", ".join(f"{n}({','.join(desc.get(n, []))})" for n in names)
