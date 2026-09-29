"""PaddleOCR / PP-Structure 引擎实现。

生产环境推荐：PaddleOCR 做文字识别，PP-Structure 做版面分析与表格结构还原。
此处封装：文字识别走 PaddleOCR；表格结构还原走 PP-Structure 的 TableSystem。
依赖较重（paddlepaddle + paddleocr），未安装时会在调用时给出明确提示。
"""
from __future__ import annotations

import os

from .base import BaseOCREngine, OCRResult, TableBlock, TextBlock


class PaddleOCREngine(BaseOCREngine):
    def __init__(self, use_gpu: bool = False, table: bool = True):
        self.use_gpu = use_gpu
        self.table = table
        self._ocr = None
        self._table_engine = None

    def _lazy_init(self):
        if self._ocr is None:
            try:
                from paddleocr import PaddleOCR
            except ImportError as e:  # pragma: no cover
                raise RuntimeError(
                    "未安装 paddleocr，请执行 `pip install paddleocr paddlepaddle`"
                ) from e
            self._ocr = PaddleOCR(use_angle_cls=True, lang="ch",
                                  use_gpu=self.use_gpu, show_log=False)
        if self.table and self._table_engine is None:
            try:
                from paddleocr import PPStructure
            except ImportError:  # pragma: no cover
                self._table_engine = False
                return
            self._table_engine = PPStructure(show_log=False, lang="ch",
                                            use_gpu=self.use_gpu)

    def recognize(self, image) -> OCRResult:
        self._lazy_init()
        result = OCRResult()

        # 表格结构还原（PP-Structure）
        if self._table_engine:
            for region in self._table_engine(image):
                if region["type"] == "table":
                    result.tables.append(TableBlock(
                        markdown=region.get("res", {}).get("html", ""),
                        box=region.get("bbox", []),
                    ))
                else:
                    txt = self._extract_text_region(region)
                    if txt:
                        result.blocks.append(TextBlock(text=txt,
                                                       box=region.get("bbox", [])))

        # 全图文字识别（PaddleOCR）
        ocr_out = self._ocr.ocr(image, cls=True)
        for line in ocr_out[0]:
            box, (text, conf) = line
            result.blocks.append(TextBlock(text=text, box=box, confidence=float(conf)))
        return result

    @staticmethod
    def _extract_text_region(region: dict) -> str:
        res = region.get("res", {})
        if isinstance(res, dict):
            return res.get("text", "")
        return ""
