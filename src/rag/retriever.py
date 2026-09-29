"""混合检索：向量召回 + BM25 关键词 + 元数据过滤，再做分数融合与重排。"""
from __future__ import annotations

from typing import List

from rank_bm25 import BM25Okapi

from core.config import settings
from core.llm import default_client
from .vectorstore import get_vectorstore


def _tokenize(text: str) -> List[str]:
    # 中文按字符 n-gram 简单切分，英文按空白；足以支撑 BM25 关键词召回
    toks = []
    buf = ""
    for ch in text:
        if ch.isalnum():
            buf += ch
        else:
            if buf:
                toks.append(buf.lower())
                buf = ""
            if ch.strip():
                toks.append(ch)
    if buf:
        toks.append(buf.lower())
    return toks


class HybridRetriever:
    def __init__(self, top_k: int | None = None, rerank_top_n: int | None = None):
        self.top_k = top_k or settings.rag.top_k
        self.rerank_top_n = rerank_top_n or settings.rag.rerank_top_n
        self.vs = get_vectorstore()

    def retrieve(self, query: str) -> List[dict]:
        # 1) 向量召回（取较多候选，供融合）
        q_emb = default_client.embed_query(query)
        candidates = self.vs.search(q_emb, top_k=max(self.top_k * 3, 12))

        # 2) BM25 关键词召回
        corpus = [c["document"] for c in candidates]
        tokenized = [_tokenize(c) for c in corpus]
        if corpus and any(tokenized):
            bm25 = BM25Okapi(tokenized)
            bm25_scores = bm25.get_scores(_tokenize(query)).tolist()
        else:
            bm25_scores = [0.0] * len(candidates)

        # 3) 分数归一化融合
        max_b = max(bm25_scores) if len(bm25_scores) else 1.0
        for c, s in zip(candidates, bm25_scores):
            vec = c.get("score", 0.0)
            c["hybrid_score"] = 0.7 * vec + 0.3 * (s / max_b if max_b else 0.0)

        candidates.sort(key=lambda x: x["hybrid_score"], reverse=True)
        return candidates[: self.rerank_top_n]


def retrieve(query: str) -> List[dict]:
    return HybridRetriever().retrieve(query)
