"""Supervisor 主编排智能体：意图识别 -> 依赖解析 -> 调度 -> 结果融合。

- 不自己算数，仅调度各 Worker Agent 并汇总；
- 根据 depends_on 自动注入上游 Agent（如风控依赖财报，策略依赖风控）；
- 融合时对风险/交易类结论标记人工复核（Human-in-the-loop）。
"""
from __future__ import annotations

from typing import Dict, List, Optional

from core.config import settings
from .base import AgentContext, BaseAgent
from .intent import IntentClassifier
from .message import AgentMessage, FusedResult


class Supervisor:
    def __init__(self, agents: Optional[Dict[str, BaseAgent]] = None,
                 intent: Optional[IntentClassifier] = None, client=None):
        from agents import build_registry
        self.agents = agents or build_registry(client=client)
        self.intent = intent or IntentClassifier(client=client)
        self.client = client

    # ---------- 对外入口 ----------
    def handle(self, query: str, params: Optional[Dict] = None) -> FusedResult:
        params = params or {}
        selected = self.intent.classify(query)
        if settings.orchestrator.auto_inject_deps:
            selected = self._inject_deps(selected)
        ordered = self._topo_order(selected)
        ctx = AgentContext()

        messages: List[AgentMessage] = []
        for name in ordered:
            agent = self.agents.get(name)
            if agent is None:
                continue
            try:
                msg = agent.run({"query": query, **params}, ctx)
            except Exception as e:  # noqa: BLE001
                msg = AgentMessage(agent=name, task=query, success=False,
                                   notes=f"执行异常: {e}")
            ctx.set(f"result:{name}", msg)
            messages.append(msg)
        return self._fuse(query, messages, ordered)

    # ---------- 依赖与拓扑 ----------
    def _inject_deps(self, selected: List[str]) -> List[str]:
        out = list(selected)
        changed = True
        while changed:
            changed = False
            for name in list(out):
                agent = self.agents.get(name)
                if not agent:
                    continue
                for dep in agent.depends_on:
                    if dep not in out:
                        out.append(dep)
                        changed = True
        return out

    def _topo_order(self, names: List[str]) -> List[str]:
        visited: Dict[str, int] = {}
        order: List[str] = []

        def visit(n: str) -> None:
            state = visited.get(n, 0)
            if state == 2:
                return
            if state == 1:
                return  # 容忍环，跳过
            visited[n] = 1
            agent = self.agents.get(n)
            if agent:
                for dep in agent.depends_on:
                    if dep in self.agents:
                        visit(dep)
            visited[n] = 2
            order.append(n)

        for n in names:
            visit(n)
        return order

    # ---------- 融合 ----------
    def _fuse(self, query: str, messages: List[AgentMessage],
              plan: List[str]) -> FusedResult:
        success = [m for m in messages if m.success]
        conf = (sum(m.confidence for m in success) / len(success)) if success else 0.0

        sources: List[str] = []
        for m in messages:
            for s in m.sources:
                if s not in sources:
                    sources.append(s)

        human = any(
            (m.success and m.agent in settings.orchestrator.human_review_agents)
            for m in messages
        )

        # ---------- 冲突检测（三期：Agent 间结论交叉验证） ----------
        conflicts = self._detect_conflicts(messages)
        if conflicts:
            human = True

        parts = []
        for m in success:
            label = f"【{m.agent}】"
            summary = m.output.get("summary") or m.notes
            if summary:
                parts.append(f"{label} {summary}")
        summary = "\n".join(parts) if parts else "（无可用结果）"
        if conflicts:
            clines = "；".join(f"[{c['type']}]{c['detail']}" for c in conflicts)
            summary += f"\n【冲突检测】{clines}（已标记人工复核）"

        disclaimer = ""
        if human:
            disclaimer = ("【免责声明】本文由 AI 生成，不构成投资建议；涉及风险评级与交易/配置建议"
                          "的结论须由具备资质的人员人工复核后采用。")

        return FusedResult(
            query=query, summary=summary, messages=messages,
            overall_confidence=round(conf, 3), sources=sources,
            human_in_the_loop=human, disclaimer=disclaimer,
            conflicts=conflicts, plan=plan,
        )

    # ---------- 冲突检测 ----------
    def _detect_conflicts(self, messages: List[AgentMessage]) -> List[dict]:
        by_agent = {m.agent: m for m in messages if m.success}
        conflicts: List[dict] = []
        fin = by_agent.get("financial_agent")
        risk = by_agent.get("risk_agent")
        strat = by_agent.get("strategy_agent")

        if fin and risk:
            fh = fin.output.get("health")
            rl = risk.output.get("risk_level")
            if fh in ("预警", "关注") and rl == "低":
                conflicts.append({"type": "基本面-风险背离",
                                  "detail": f"财报健康度【{fh}】但风险等级【{rl}】，结论不一致"})
            if fh == "良好" and rl in ("高", "极高"):
                conflicts.append({"type": "基本面-风险背离",
                                  "detail": f"财报健康度【{fh}】但风险等级【{rl}】，需复核"})

        if strat and risk:
            alloc = strat.output.get("allocation_suggestion")
            rl = risk.output.get("risk_level")
            if alloc in ("超配", "标配") and rl in ("高", "极高"):
                conflicts.append({"type": "配置-风险背离",
                                  "detail": f"策略建议【{alloc}】但综合风险【{rl}】，存在过度配置风险"})

        flow = by_agent.get("flow_agent")
        if flow and risk:
            if flow.output.get("compliance_flag") and risk.output.get("compliance", {}).get("passed"):
                conflicts.append({"type": "合规信号不一致",
                                  "detail": "流水识别到合规风险，但风控合规校验却通过，需人工复核"})
        return conflicts
