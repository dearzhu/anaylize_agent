"""二期编排层与 Worker Agent 单元测试（无需 Ollama，可直接 pytest 运行）。"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from seed_data import ensure_sample_data

ensure_sample_data()

from agents.financial_agent import FinancialAgent
from agents.flow_agent import FlowAgent
from agents.risk_agent import RiskAgent
from agents.strategy_agent import StrategyAgent
from agents import build_registry
from orchestrator.supervisor import Supervisor
from orchestrator.base import AgentContext
from orchestrator.intent import IntentClassifier
from orchestrator.message import AgentMessage, FusedResult


def test_intent_financial():
    sel = IntentClassifier().classify("解读某公司最新季报，找出异常科目")
    assert "financial_agent" in sel


def test_intent_risk_strategy():
    sel = IntentClassifier().classify("评估某公司可投资性，给策略建议")
    assert "strategy_agent" in sel


def test_financial_agent():
    ctx = AgentContext()
    msg = FinancialAgent().run({"query": "解读财报"}, ctx)
    assert msg.success
    assert "ratios" in msg.output and msg.output["company"]
    assert isinstance(msg.output["ratios"], dict)


def test_flow_agent():
    ctx = AgentContext()
    msg = FlowAgent().run({"query": "分析流水"}, ctx)
    assert msg.success
    assert msg.output["n_txn"] > 0
    assert "anomalies" in msg.output
    assert "net_flow" in msg.output


def test_risk_depends_on_financial():
    ctx = AgentContext()
    fin = FinancialAgent().run({"query": "财报"}, ctx)
    ctx.set("result:financial_agent", fin)
    msg = RiskAgent().run({"query": "风险评估"}, ctx)
    assert msg.success
    assert msg.output["risk_level"] in {"低", "中", "高", "极高"}
    assert "findings" in msg.output


def test_strategy_depends_on_risk():
    ctx = AgentContext()
    fin = FinancialAgent().run({"query": "财报"}, ctx)
    ctx.set("result:financial_agent", fin)
    risk = RiskAgent().run({"query": "风险"}, ctx)
    ctx.set("result:risk_agent", risk)
    msg = StrategyAgent().run({"query": "策略"}, ctx)
    assert msg.success
    assert "sharpe" in msg.output
    assert isinstance(msg.output["suggested_allocation_pct"], int)
    # 配置建议应随风险等级下降（样本财报触发盈利质量风险 -> 高 -> 30%）
    assert msg.output["suggested_allocation_pct"] in (10, 30, 60, 80)


def test_supervisor_invest():
    sup = Supervisor()
    res = sup.handle("评估某公司可投资性，给策略建议")
    names = {m.agent for m in res.messages}
    assert "strategy_agent" in names
    assert "risk_agent" in names
    assert "financial_agent" in names
    assert res.human_in_the_loop is True
    assert res.disclaimer


def test_supervisor_financial_only():
    sup = Supervisor()
    res = sup.handle("解读某公司最新季报，找出异常科目")
    assert any(m.agent == "financial_agent" and m.success for m in res.messages)
    assert res.overall_confidence > 0


def test_registry_complete():
    reg = build_registry()
    for name in ["financial_agent", "rag_agent", "flow_agent", "risk_agent", "strategy_agent"]:
        assert name in reg


def test_message_serialization():
    m = AgentMessage(agent="x", task="t", output={"a": 1})
    d = m.to_dict()
    assert d["agent"] == "x" and d["output"]["a"] == 1
    fr = FusedResult(query="q", messages=[m])
    assert fr.to_dict()["messages"][0]["agent"] == "x"
