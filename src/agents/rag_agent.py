"""RAG 知识库问答 Agent（Worker）。

职责：基于本地知识库做「带溯源」的可信问答。复用一期 `rag` 模块。
Ollama 未就绪时优雅降级为 success=False（不阻塞整条链路）。
"""
from __future__ import annotations

from typing import Any

from orchestrator.base import BaseAgent
from agents.base import register


@register
class RagAgent(BaseAgent):
    name = "rag_agent"
    description = "RAG 知识库问答：检索 + 引用溯源"
    depends_on: list = []
    requires_llm = True

    def run(self, task: Dict[str, Any], ctx) -> Any:
        query = task.get("query", "")
        if not query:
            return self._fail("缺少查询问题，无法执行 RAG 问答。")
        try:
            from rag.qa import answer
            res = answer(query)
        except Exception as e:  # noqa: BLE001  Ollama 未启动 / 模型未拉取
            return self._fail(f"RAG 问答不可用（Ollama 未就绪或知识库未入库）：{e}")

        answer_text = res.get("answer", "")
        sources = res.get("sources", [])
        confidence = 0.8 if answer_text else 0.3
        notes = (answer_text[:140] + "…") if len(answer_text) > 140 else answer_text
        notes = notes or "未检索到相关资料。"
        output = {
            "query": query, "answer": answer_text, "sources": sources,
            "retrieved": res.get("retrieved", []),
        }
        return self._ok(output, confidence=confidence,
                       sources=[f"RAG:{s}" for s in sources], notes=notes,
                       task=query)
