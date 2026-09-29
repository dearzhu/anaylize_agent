"""财务指标引擎单元测试（无需 Ollama，可直接 pytest 运行）。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from financial.metrics import compute_ratios, compare_yoy
from financial.anomaly import detect_anomalies
from financial.parser import load_pair

_SAMPLE = os.path.join(
    os.path.dirname(__file__), "..", "data", "sample_financials", "company_a_2023.json"
)


def test_compute_ratios():
    cur, _ = load_pair(_SAMPLE)
    r = compute_ratios(cur)
    assert abs(r["ROE"] - 150000 / 720000) < 1e-9
    assert abs(r["毛利率"] - 350000 / 950000) < 1e-9
    assert abs(r["资产负债率"] - 480000 / 1200000) < 1e-9
    assert abs(r["流动比率"] - 700000 / 300000) < 1e-9
    assert abs(r["利息保障倍数"] - 200000 / 20000) < 1e-9


def test_compare_yoy():
    cur, prior = load_pair(_SAMPLE)
    yoy = compare_yoy(cur, prior)
    # 营收 950000 vs 800000 -> +18.75%
    assert abs(yoy["revenue"] - (950000 - 800000) / 800000) < 1e-9
    assert yoy["net_profit"] is not None


def test_detect_anomalies_runs():
    cur, prior = load_pair(_SAMPLE)
    findings = detect_anomalies(cur, prior, yoy_threshold=0.30, cash_profit_min=0.70)
    # 经营现金流 90000 / 净利润 150000 = 0.6 < 0.7 -> 触发盈利质量风险
    types = {f.item for f in findings}
    assert "盈利质量" in types
