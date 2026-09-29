"""OCR 引擎抽象。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List


@dataclass
class TextBlock:
    text: str
    box: list = field(default_factory=list)   # 四点坐标 [x1,y1,x2,y2,...]
    confidence: float = 0.0


@dataclass
class TableBlock:
    # 还原为 Markdown 表格字符串；保留坐标便于溯源
    markdown: str
    box: list = field(default_factory=list)


@dataclass
class OCRResult:
    blocks: List[TextBlock] = field(default_factory=list)
    tables: List[TableBlock] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(b.text for b in self.blocks)


class BaseOCREngine(ABC):
    @abstractmethod
    def recognize(self, image) -> OCRResult:
        """image 为 PIL.Image 对象。"""
        ...
