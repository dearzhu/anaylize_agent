"""RapidOCR 引擎：基于 ONNX 的 PP-OCR 实现，无需 PaddlePaddle，跨平台易装。

适合：无 GPU / 不想安装庞大的 paddlepaddle 的环境。
注意：RapidOCR 仅做文字检测+识别，不做表格结构还原（tables 为空），
复杂表格可依赖 VLM 兜底（config.ocr.use_vlm_fallback）。
"""
from __future__ import annotations

import numpy as np

from .base import BaseOCREngine, OCRResult, TextBlock


class RapidOCREngine(BaseOCREngine):
    def __init__(self):
        self._engine = None

    def _lazy(self):
        if self._engine is None:
            try:
                from rapidocr_onnxruntime import RapidOCR
            except ImportError as e:  # pragma: no cover
                raise RuntimeError(
                    "未安装 rapidocr-onnxruntime，请执行 `pip install rapidocr-onnxruntime`"
                ) from e
            self._engine = RapidOCR()

    @staticmethod
    def _to_bgr(image) -> np.ndarray:
        if getattr(image, "mode", None) != "RGB":
            image = image.convert("RGB")
        return np.array(image)[..., ::-1].copy()  # RGB -> BGR

    def recognize(self, image) -> OCRResult:
        self._lazy()
        result = OCRResult()
        out, _ = self._engine(self._to_bgr(image))
        if not out:
            return result
        for line in out:
            box, text, score = line
            result.blocks.append(TextBlock(text=text, box=box, confidence=float(score)))
        return result
