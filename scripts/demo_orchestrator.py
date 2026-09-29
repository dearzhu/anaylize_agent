"""演示：二期 Supervisor 编排 + 流水/风控/策略/财报/知识库 Agent。

无需 Ollama 即可运行除 RAG 以外的全部链路（财报/流水/风控/策略均为规则 + DataFrame 计算）。
运行：python scripts/demo_orchestrator.py
"""
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, SCRIPT_DIR)

from seed_data import ensure_sample_data
from orchestrator.supervisor import Supervisor

ensure_sample_data()

_QUERIES = [
    "解读某公司最新季报，找出异常科目",
    "分析一下这家公司的资金流水，有没有异常交易？",
    "评估某公司是否可纳入投资组合，给策略建议",
    "上市公司年度报告应当在何时披露？",
]


def main() -> None:
    sup = Supervisor()
    for q in _QUERIES:
        print("\n" + "=" * 64)
        print("用户：", q)
        try:
            res = sup.handle(q)
        except Exception as e:  # noqa: BLE001
            print("处理失败：", e)
            continue
        print("调度计划：", " -> ".join(res.plan))
        print("整体置信度：", res.overall_confidence)
        print("人工复核：", res.human_in_the_loop)
        print("—— 融合结论 ——")
        print(res.summary)
        for m in res.messages:
            tag = "OK " if m.success else "ERR"
            print(f"  [{tag}] {m.agent} (conf={m.confidence}): {m.notes[:140]}")
        if res.disclaimer:
            print("免责声明：", res.disclaimer)


if __name__ == "__main__":
    main()
