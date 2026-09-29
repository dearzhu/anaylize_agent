"""演示：OCR 图片文字识别（一期能力三：ocr）。

运行：
    python scripts/demo_ocr.py                 # 使用内置样例图
    python scripts/demo_ocr.py /path/to/x.png  # 指定图片

说明：
    - 主引擎为 rapidocr（首次运行会自动下载 ONNX 模型，可能稍慢）。
    - 当 rapidocr 输出为空 / 置信度不足时，自动走 VLM(qwen2.5vl:7b) 兜底，
      需 Ollama 已拉取该模型（run_all.sh 会自动确保；缺失时仅打印提示并跳过）。
"""
from __future__ import annotations

import argparse
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, SCRIPT_DIR)

from core.config import settings
from ocr.pipeline import process_image


def _default_image() -> str:
    return os.path.join(ROOT, "data", "sample_ocr", "sample_report.png")


def main(image_path: str) -> None:
    if not os.path.exists(image_path):
        print("图片不存在：", image_path)
        return

    print("OCR 引擎：", settings.ocr.engine)
    print("图片：", image_path)
    doc = process_image(image_path)

    print("\n—— 识别结果 ——")
    print("段落数：", len(doc.segments))
    for i, s in enumerate(doc.segments, 1):
        print(f"  [{i}] {s}")
    print("\n元数据：", doc.metadata)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="OCR 图片识别演示")
    ap.add_argument("image", nargs="?", default=_default_image(),
                   help="待识别图片路径（默认用内置样例图）")
    args = ap.parse_args()
    main(args.image)
