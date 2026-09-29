"""OCR 流水线编排：预处理 -> 版面/OCR -> 结构化拼接 -> VLM 兜底 -> 缓存。

输出 StructuredDoc：
  - segments: 文本片段列表（用于后续 RAG 切分 / 指标解析）
  - tables:   Markdown 表格列表（财报关键科目表）
  - metadata: 来源、页码、坐标等溯源信息
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from typing import List

from core.config import settings
from core.llm import default_client
from .engines.base import OCRResult
from .engines.mock import MockOCREngine
from .engines.paddle_ocr import PaddleOCREngine
from .preprocess import preprocess


@dataclass
class StructuredDoc:
    source: str
    segments: List[str] = field(default_factory=list)
    tables: List[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


def _get_engine():
    engine_name = settings.ocr.engine
    if engine_name == "mock":
        return MockOCREngine()
    if engine_name == "rapidocr":
        try:
            from .engines.rapid_ocr import RapidOCREngine
            return RapidOCREngine()
        except RuntimeError:
            return MockOCREngine()
    # 默认 paddle
    try:
        return PaddleOCREngine()
    except RuntimeError:
        # 未安装 paddle 时优雅降级到 mock，避免阻塞整条链路
        return MockOCREngine()


def _cache_path(source: str) -> str:
    base = os.path.join(settings.vectorstore.persist_dir, "ocr_cache")
    os.makedirs(base, exist_ok=True)
    key = hashlib.md5(source.encode()).hexdigest()
    return os.path.join(base, f"{key}.json")


def _vlm_fallback(image_path: str, partial_text: str) -> str:
    """对 OCR 结果薄弱处调用本地 VLM 直读，用于复杂表格/手写批注校验。"""
    if not settings.ocr.use_vlm_fallback:
        return ""
    prompt = (
        "这是一张财报页面图片。请提取其中的关键财务数据（科目与数值），"
        "尤其是表格内容。若下方 OCR 文本已完整，请补充其缺失或错误部分；"
        f"否则直接输出。已有 OCR 文本：\n{partial_text}\n"
    )
    try:
        return default_client.vision_chat(prompt, [image_path])
    except Exception as e:  # noqa: BLE001
        print(f"[ocr][vlm] 兜底失败: {e}")
        return ""


def process_image(image_path: str, use_cache: bool = True) -> StructuredDoc:
    if use_cache and os.path.exists(_cache_path(image_path)):
        with open(_cache_path(image_path), "r", encoding="utf-8") as f:
            data = json.load(f)
        return StructuredDoc(**data)

    img = preprocess(image_path, dpi=settings.ocr.dpi)
    engine = _get_engine()
    ocr_result: OCRResult = engine.recognize(img)

    segments = [b.text for b in ocr_result.blocks if b.text.strip()]
    tables = [t.markdown for t in ocr_result.tables if t.markdown.strip()]

    # VLM 兜底：当 OCR 文本过短（可能识别失败）时尝试直读
    if len("".join(segments)) < 50:
        vlm_text = _vlm_fallback(image_path, "".join(segments))
        if vlm_text:
            segments.append(vlm_text)

    doc = StructuredDoc(
        source=image_path,
        segments=segments,
        tables=tables,
        metadata={"engine": settings.ocr.engine, "tables": len(tables)},
    )
    with open(_cache_path(image_path), "w", encoding="utf-8") as f:
        json.dump(doc.__dict__, f, ensure_ascii=False, indent=2)
    return doc


# 兼容 PDF：实际项目中可由 pdf2image 转图片后逐页调用 process_image；
# 此处提供占位以便后续接入。
def process_pdf(pdf_path: str) -> List[StructuredDoc]:
    raise NotImplementedError(
        "PDF 拆分需依赖 pdf2image/pymupdf，将在接入图片型 PDF 时补充；"
        "当前可先用 pdf2image 转 PNG 后逐页调用 process_image。"
    )
