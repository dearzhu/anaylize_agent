"""Ollama 本地模型客户端封装。

统一封装三类模型调用：
  - chat：文本对话（通用编排 / 深度推理）
  - embed：向量化（RAG 入库与检索）
  - vision_chat：多模态图片理解（财报 OCR 兜底）

所有外部依赖（ollama SDK）均延迟导入，未安装或 Ollama 未启动时不阻塞导入。
"""
from __future__ import annotations

import base64
from typing import Any, List, Optional

from ..config import settings


class OllamaClient:
    def __init__(self, base_url: Optional[str] = None, llm_model: Optional[str] = None,
                 embed_model: Optional[str] = None, vlm_model: Optional[str] = None,
                 temperature: Optional[float] = None, num_ctx: Optional[int] = None):
        self.base_url = base_url or settings.ollama.base_url
        self.llm_model = llm_model or settings.ollama.llm_model
        self.embed_model = embed_model or settings.ollama.embed_model
        self.vlm_model = vlm_model or settings.ollama.vlm_model
        self.temperature = temperature if temperature is not None else settings.ollama.temperature
        self.num_ctx = num_ctx or settings.ollama.num_ctx
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import ollama
            except ImportError as e:  # pragma: no cover
                raise RuntimeError(
                    "未安装 ollama SDK，请执行 `pip install ollama` 并确保 Ollama 服务已启动"
                ) from e
            self._client = ollama.Client(host=self.base_url)
        return self._client

    # ---------- 文本对话 ----------
    def chat(self, messages: List[dict], model: Optional[str] = None,
             temperature: Optional[float] = None, num_ctx: Optional[int] = None) -> str:
        """messages: [{"role": "system"/"user"/"assistant", "content": "..."}]"""
        model = model or self.llm_model
        client = self._get_client()
        resp = client.chat(
            model=model,
            messages=messages,
            options={
                "temperature": temperature if temperature is not None else self.temperature,
                "num_ctx": num_ctx or self.num_ctx,
            },
        )
        return resp["message"]["content"]

    # ---------- 向量化 ----------
    def embed(self, texts: List[str], model: Optional[str] = None) -> List[List[float]]:
        model = model or self.embed_model
        client = self._get_client()
        # ollama SDK embed 接口返回 {"embeddings": [[...], ...]}
        resp = client.embed(model=model, input=texts)
        return resp["embeddings"]

    def embed_query(self, text: str) -> List[float]:
        return self.embed([text])[0]

    # ---------- 多模态（图片直读） ----------
    def vision_chat(self, text_prompt: str, image_paths: List[str],
                    model: Optional[str] = None, temperature: Optional[float] = None) -> str:
        model = model or self.vlm_model
        images_b64 = [self._encode_image(p) for p in image_paths]
        messages = [
            {
                "role": "user",
                "content": text_prompt,
                "images": images_b64,
            }
        ]
        client = self._get_client()
        resp = client.chat(
            model=model,
            messages=messages,
            options={
                "temperature": temperature if temperature is not None else self.temperature,
                "num_ctx": self.num_ctx,
            },
        )
        return resp["message"]["content"]

    @staticmethod
    def _encode_image(path: str) -> str:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")


# 全局默认客户端实例
default_client = OllamaClient()
