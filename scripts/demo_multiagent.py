"""演示：三期 —— 多智能体协作闭环 + 报告自动生成 + 可视化。

运行：python scripts/demo_multiagent.py
说明：财报/流水/风控/策略 Agent 为纯规则引擎，无需 Ollama 即可联调；
      RAG Agent 在 Ollama 未就绪时自动降级（不阻塞闭环）。
"""
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, SCRIPT_DIR)

from seed_data import ensure_sample_data
from report import analyze

ensure_sample_data()

_QUERIES = [
    "评估示例科技是否可纳入投资组合，并分析其财报、资金流水与风险。",
    "解读示例科技最新财报，找出异常科目。",
    "上市公司年度报告应当在何时披露？（含 RAG 知识库）",
]


def main() -> None:
    for q in _QUERIES:
        print("\n" + "=" * 64)
        print("用户：", q)
        res, report_path, figures = analyze(q)
        print("调度计划：", " -> ".join(res.plan))
        print("整体置信度：", res.overall_confidence)
        print("人工复核：", res.human_in_the_loop)
        print("冲突检测：", res.conflicts or "无")
        print("—— 融合结论 ——")
        print(res.summary)
        for m in res.messages:
            tag = "OK " if m.success else "ERR"
            print(f"  [{tag}] {m.agent} (conf={m.confidence}): {m.notes[:120]}")
        if res.disclaimer:
            print("免责声明：", res.disclaimer)
        if report_path:
            print("报告已生成：", report_path)
        if figures:
            print(f"图表({len(figures)}张)：", ", ".join(os.path.basename(f) for f in figures))


if __name__ == "__main__":
    main()
