"""向量库抽象 + Chroma 实现（默认），预留 pgvector 切换。

设计：VectorStore 为接口；ChromaVectorStore 为本地默认实现（无需额外服务）。
后续接入 pgvector 时新增 PgVectorStore 并在 factory 中按配置切换。
"""
from __future__ import annotations

import os
from typing import List, Optional

from core.config import VectorStoreConfig, settings


class VectorStore:
    def add(self, ids: List[str], documents: List[str],
            embeddings: List[List[float]], metadatas: List[dict]) -> None:
        raise NotImplementedError

    def search(self, query_embedding: List[float], top_k: int = 6) -> List[dict]:
        raise NotImplementedError

    def count(self) -> int:
        raise NotImplementedError


class ChromaVectorStore(VectorStore):
    def __init__(self, cfg: Optional[VectorStoreConfig] = None):
        self.cfg = cfg or settings.vectorstore
        try:
            import chromadb
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("未安装 chromadb，请执行 `pip install chromadb`") from e
        os.makedirs(self.cfg.persist_dir, exist_ok=True)
        self._client = chromadb.PersistentClient(path=self.cfg.persist_dir)
        self._col = self._client.get_or_create_collection(
            name=self.cfg.collection, metadata={"hnsw:space": self.cfg.distance}
        )

    def add(self, ids, documents, embeddings, metadatas):
        # chroma 要求 ids 唯一
        self._col.upsert(ids=ids, documents=documents,
                         embeddings=embeddings, metadatas=metadatas)

    def search(self, query_embedding, top_k=6):
        res = self._col.query(query_embeddings=[query_embedding], n_results=top_k)
        out = []
        for doc, meta, dist in zip(
            (res["documents"][0] if res["documents"] else []),
            (res["metadatas"][0] if res["metadatas"] else []),
            (res["distances"][0] if res["distances"] else []),
        ):
            out.append({"document": doc, "metadata": meta, "score": 1 - dist})
        return out

    def count(self):
        return self._col.count()


def get_vectorstore(cfg: Optional[VectorStoreConfig] = None) -> VectorStore:
    cfg = cfg or settings.vectorstore
    if cfg.type == "pgvector":
        # TODO(二期前): 接入 pgvector，复用相同接口
        raise NotImplementedError("pgvector 后端将在生产化阶段接入，当前默认使用 chroma")
    return ChromaVectorStore(cfg)
