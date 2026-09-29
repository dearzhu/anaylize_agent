"""报告生成与可视化测试（三期 c2，无需 Ollama）。

覆盖：Markdown 报告落盘（含合规免责声明）、可视化生成、analyze 串联协作闭环。
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from seed_data import ensure_sample_data
ensure_sample_data()

from orchestrator.message import AgentMessage, FusedResult
from report.generator import generate_report
from report.visualize import make_figures
from report import analyze


def _messages():
    return [
        AgentMessage(agent="financial_agent", task="t", success=True,
                     output={"company": "示例科技", "health": "关注",
                             "ratios": {"ROE": 0.2}, "summary": "财报健康度【关注】"}),
        AgentMessage(agent="risk_agent", task="t", success=True,
                     output={"risk_level": "高", "findings": ["流动性预警（评分 20）"],
                             "compliance": {"passed": False, "issues": []}}),
        AgentMessage(agent="strategy_agent", task="t", success=True,
                     output={"allocation_suggestion": "低配", "sharpe": 1.2,
                             "summary": "基于风险等级【高】给出低配建议。"}),
    ]


def _fused():
    return FusedResult(query="测试", summary="融合结论", messages=_messages(),
                       overall_confidence=0.7, human_in_the_loop=True,
                       conflicts=[{"type": "配置-风险背离",
                                  "detail": "策略建议低配但风险高"}], plan=["financial_agent", "risk_agent"])


def test_generate_report_disclaimer():
    path = generate_report("测试问题", _messages(), _fused(), figures=[])
    assert os.path.exists(path)
    text = open(path, encoding="utf-8").read()
    assert "免责声明" in text
    assert "不构成任何投资建议" in text
    assert "综合结论" in text
    os.remove(path)


def test_make_figures_runs():
    figs = make_figures(_messages(), _fused())
    assert isinstance(figs, list)
    for f in figs:
        assert os.path.exists(f)
        os.remove(f)


def test_analyze_pipeline():
    res, report_path, figures = analyze("评估某公司是否可纳入投资组合，给策略建议")
    assert isinstance(res, FusedResult)
    names = {m.agent for m in res.messages}
    assert "financial_agent" in names
    assert "risk_agent" in names
    assert "strategy_agent" in names
    assert res.human_in_the_loop is True  # 策略/风控需人工复核
    # 报告与图表（图表需 matplotlib，可能为空列表但不应报错）
    assert report_path is None or os.path.exists(report_path)
