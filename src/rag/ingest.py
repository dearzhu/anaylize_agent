"""知识库入库：加载文档 -> 切分 -> 向量化 -> 写入向量库。

支持：
  - 文本类：.txt / .md（直接切分）
  - 图片/图片型 PDF：经 OCR 流水线还原为文本后再切分（依赖 src.ocr）
"""
from __future__ import annotations

import hashlib
import os
from typing import List

from core.config import settings
from core.llm import default_client
from .chunker import Chunk, chunk_document, chunk_segments
from .vectorstore import get_vectorstore


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def _ocr_image(path: str) -> List[str]:
    """调用 OCR 流水线，返回文本片段列表。"""
    from ocr.pipeline import process_image
    doc = process_image(path)
    return doc.segments


def _embed_chunks(chunks: List[Chunk]) -> None:
    vs = get_vectorstore()
    client = default_client
    if not chunks:
        return
    texts = [c.text for c in chunks]
    embeddings = client.embed(texts)
    ids, docs, metas = [], [], []
    for c, emb in zip(chunks, embeddings):
        cid = hashlib.md5(f"{c.doc_id}|{c.page_or_pos}|{c.text[:50]}".encode()).hexdigest()
        ids.append(cid)
        docs.append(c.text)
        metas.append({
            "doc_id": c.doc_id,
            "page_or_pos": c.page_or_pos,
            "heading_path": c.heading_path,
        })
    vs.add(ids=ids, documents=docs, embeddings=embeddings, metadatas=metas)


def ingest_text(text: str, doc_id: str, page_or_pos: str = "") -> int:
    chunks = chunk_document(text, doc_id, settings.rag.chunk_size,
                            settings.rag.chunk_overlap, page_or_pos)
    _embed_chunks(chunks)
    return len(chunks)


def ingest_file(path: str) -> int:
    ext = os.path.splitext(path)[1].lower()
    doc_id = os.path.splitext(os.path.basename(path))[0]
    if ext in (".txt", ".md"):
        return ingest_text(_read_text(path), doc_id)
    elif ext in (".png", ".jpg", ".jpeg", ".bmp", ".pdf"):
        # 图片/图片型 PDF 走 OCR
        segments = _ocr_image(path)
        chunks = chunk_segments(segments, doc_id)
        _embed_chunks(chunks)
        return len(chunks)
    else:
        raise ValueError(f"暂不支持的文件类型: {ext}")


def ingest_directory(directory: str) -> int:
    total = 0
    for root, _dirs, files in os.walk(directory):
        for fn in files:
            try:
                total += ingest_file(os.path.join(root, fn))
            except Exception as e:  # noqa: BLE001
                print(f"[ingest] 跳过 {fn}: {e}")
    return total
