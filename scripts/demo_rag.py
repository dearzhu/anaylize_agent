"""演示：RAG 知识库入库 + 问答（需要 Ollama 服务已启动）。

运行步骤：
  1) 启动 Ollama 并拉取模型：ollama pull bge-m3 && ollama pull qwen2.5:7b
  2) 安装依赖：pip install -r requirements.txt
  3) 执行：python scripts/demo_rag.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from rag.ingest import ingest_directory
from rag.qa import answer

_KB = os.path.join(os.path.dirname(__file__), "..", "data", "knowledge")


def main():
    print("[1/2] 入库知识库 ...")
    n = ingest_directory(_KB)
    print(f"      已切分并入库 {n} 个 chunk。")

    print("\n[2/2] 问答演示")
    questions = [
        "上市公司年度报告应当在何时披露？",
        "未按时披露定期报告会有什么后果？",
    ]
    for q in questions:
        print(f"\n问题：{q}")
        try:
            res = answer(q)
            print("回答：", res["answer"])
            print("来源：", res["sources"])
        except Exception as e:  # noqa: BLE001
            print(f"调用失败（请确认 Ollama 已启动且模型已拉取）：{e}")


if __name__ == "__main__":
    main()
