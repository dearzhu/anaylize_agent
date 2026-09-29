"""RAG 问答：检索 -> 拼接带溯源上下文 -> 调用本地 LLM 生成答案。"""
from __future__ import annotations

from typing import List, Tuple

from core.llm import default_client
from .retriever import retrieve

_PROMPT_TMPL = """你是一名严谨的金融研究助理。请仅基于下列【参考资料】回答用户问题，
不得编造未提供的信息；若资料不足以回答，请明确说明。

【参考资料】
{context}

【用户问题】
{question}

请输出结构化回答，并在句末用 [来源: doc_id=xxx, 位置=yyy] 标注引用。
"""


def _build_context(results: List[dict]) -> Tuple[str, str]:
    blocks = []
    cites = []
    for r in results:
        meta = r.get("metadata", {})
        doc_id = meta.get("doc_id", "?")
        # 优先用页码/位置；纯文本无页码时回退到标题路径，再缺失用「全文」
        pos = meta.get("page_or_pos") or meta.get("heading_path") or "全文"
        blocks.append(f"[doc_id={doc_id}, 位置={pos}]\n{r['document']}")
        cites.append(f"doc_id={doc_id}, 位置={pos}")
    return "\n\n".join(blocks), "; ".join(cites)


def answer(query: str, model: str | None = None) -> dict:
    results = retrieve(query)
    context, cites = _build_context(results)
    prompt = _PROMPT_TMPL.format(context=context, question=query)
    messages = [
        {"role": "system", "content": "你是金融知识库问答助手，回答必须引用资料来源。"},
        {"role": "user", "content": prompt},
    ]
    content = default_client.chat(messages, model=model)
    return {
        "answer": content,
        "sources": cites,
        "retrieved": results,
    }
