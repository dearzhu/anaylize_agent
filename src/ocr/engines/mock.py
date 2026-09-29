"""Mock OCR 引擎：不依赖任何深度学习库。

用于：无 GPU / 未安装 PaddleOCR 环境下的联调与测试。
行为：优先读取与图片同名的 .txt 旁注文件（约定：image.png -> image.png.txt），
否则返回空结果。真实部署请改用 PaddleOCREngine。
"""
from __future__ import annotations

import os

from .base import BaseOCREngine, OCRResult, TextBlock


class MockOCREngine(BaseOCREngine):
    def recognize(self, image) -> OCRResult:
        result = OCRResult()
        # image 可能是路径字符串或 PIL.Image；取旁注文本
        path = getattr(image, "filename", None)
        if path and isinstance(path, str):
            sidecar = path + ".txt"
            if os.path.exists(sidecar):
                with open(sidecar, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read().strip()
                if text:
                    result.blocks.append(TextBlock(text=text, confidence=1.0))
        return result
