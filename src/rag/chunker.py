"""文档切分：基于标题层级的语义切分，避免切断表格/段落。

策略：
  1. 按 Markdown 标题（# / ## / ### ...）切分逻辑段落；
  2. 每个段落内部按 chunk_size 再做滑动窗口切分，保留 overlap；
  3. 每个 chunk 记录来源 doc_id、页码/位置、所属标题路径，便于溯源。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)


@dataclass
class Chunk:
    text: str
    doc_id: str
    page_or_pos: str = ""
    heading_path: str = ""


def _split_by_headings(text: str) -> List[tuple[str, str, str]]:
    """返回 [(heading_path, heading_title, body), ...]"""
    matches = list(_HEADING_RE.finditer(text))
    if not matches:
        return [("", "", text.strip())]

    sections: List[tuple[str, str, str]] = []
    for i, m in enumerate(matches):
        level = len(m.group(1))
        title = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        sections.append((title, title, body))
    return sections


def _sliding_window(body: str, chunk_size: int, overlap: int) -> List[str]:
    if len(body) <= chunk_size:
        return [body] if body.strip() else []
    step = max(1, chunk_size - overlap)
    parts = []
    for s in range(0, len(body), step):
        seg = body[s:s + chunk_size].strip()
        if seg:
            parts.append(seg)
    return parts


def chunk_document(text: str, doc_id: str, chunk_size: int = 800,
                  overlap: int = 120, page_or_pos: str = "") -> List[Chunk]:
    """对单篇文档做标题感知切分，返回带元信息的 chunk 列表。"""
    chunks: List[Chunk] = []
    sections = _split_by_headings(text)
    for title, _title, body in sections:
        if not body:
            continue
        for seg in _sliding_window(body, chunk_size, overlap):
            chunks.append(Chunk(text=seg, doc_id=doc_id,
                                page_or_pos=page_or_pos, heading_path=title))
    return chunks


def chunk_segments(segments: List[str], doc_id: str, chunk_size: int = 800,
                   overlap: int = 120) -> List[Chunk]:
    """对 OCR/解析得到的文本片段列表切分（无标题结构时使用）。"""
    chunks: List[Chunk] = []
    for idx, seg in enumerate(segments):
        if not seg or not seg.strip():
            continue
        for part in _sliding_window(seg.strip(), chunk_size, overlap):
            chunks.append(Chunk(text=part, doc_id=doc_id, page_or_pos=str(idx)))
    return chunks
