"""RAG 切分逻辑单元测试（不依赖 Ollama / 向量库）。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from rag.chunker import chunk_document, chunk_segments


def test_chunk_by_heading():
    text = "# 标题一\n这是第一段内容，用于测试切分逻辑是否按标题聚合。\n" * 3
    chunks = chunk_document(text, "doc1", chunk_size=80, overlap=10)
    assert len(chunks) >= 1
    assert all(c.doc_id == "doc1" for c in chunks)
    assert all(c.heading_path == "标题一" for c in chunks)


def test_chunk_long_body_splits():
    big = "数字 " + "数据 " * 500  # 远超 chunk_size
    chunks = chunk_document(big, "doc2", chunk_size=100, overlap=20)
    assert len(chunks) > 1
    # 重叠保证相邻 chunk 有内容延续
    assert all(len(c.text) <= 100 for c in chunks)


def test_chunk_segments_no_heading():
    segs = ["应收账款同比大幅增加，需关注回款风险。", "存货周转天数上升。"]
    chunks = chunk_segments(segs, "img1")
    assert len(chunks) == 2
    assert chunks[0].page_or_pos == "0"
