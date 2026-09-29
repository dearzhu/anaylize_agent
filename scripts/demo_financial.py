"""演示：财报指标计算 + 异常检测（无需 Ollama，可直接运行）。

运行：python scripts/demo_financial.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from financial.metrics import compute_ratios, compare_yoy
from financial.anomaly import detect_anomalies
from financial.parser import load_pair

_SAMPLE = os.path.join(
    os.path.dirname(__file__), "..", "data", "sample_financials", "company_a_2023.json"
)


def _fmt(v):
    return f"{v:.4f}" if isinstance(v, float) else str(v)


def main():
    cur, prior = load_pair(_SAMPLE)
    print(f"=== 财报分析：{cur.company} {cur.period} ===\n")

    print("[指标计算]")
    for k, v in compute_ratios(cur).items():
        print(f"  {k}: {_fmt(v) if v is not None else 'N/A'}")

    print("\n[同比变动]")
    for k, v in compare_yoy(cur, prior).items():
        print(f"  {k}: {_fmt(v) if v is not None else 'N/A'}")

    print("\n[异常检测]")
    findings = detect_anomalies(cur, prior)
    if not findings:
        print("  未发现显著异常。")
    for f in findings:
        print(f"  [{f.level}] {f.message}")


if __name__ == "__main__":
    main()
