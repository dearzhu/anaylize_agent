"""FastAPI 服务：封装金融数据分析智能体的前端调用入口。

提供：
  GET  /                      单页前端
  GET  /figures/{name}        报告图表静态资源
  POST /api/analyze           （可选文件 + 问题）分析上传文件 / 知识库查询
  POST /api/report            （问题）生成多智能体完整报告

运行：
  .venv/bin/python -m uvicorn src.api.server:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import hashlib
import os
import sys
import tempfile
import uuid
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

# 将 src 加入 path，使顶层包 financial/rag/... 可导入
_SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from core.config import settings  # noqa: E402
from core.llm import default_client  # noqa: E402
from financial.parser import load_pair  # noqa: E402
from financial.metrics import compute_ratios, compare_yoy  # noqa: E402
from financial.anomaly import detect_anomalies  # noqa: E402
from rag.qa import answer as rag_answer  # noqa: E402
from rag.chunker import chunk_document, chunk_segments  # noqa: E402
from rag.vectorstore import ChromaVectorStore, VectorStoreConfig  # noqa: E402
from rag.retriever import HybridRetriever  # noqa: E402

_ROOT = os.path.dirname(_SRC)
_STATIC = os.path.join(_ROOT, "static")
_UPLOAD_VS_DIR = os.path.join(_ROOT, "data", "vectordb_uploads")

_IMG_EXT = {".png", ".jpg", ".jpeg", ".bmp"}
_TXT_EXT = {".txt", ".md"}

app = FastAPI(title="金融数据分析智能体 API", version="0.1.0")


# ---------- 工具函数 ----------
def _fmt(v):
    return f"{v:.4f}" if isinstance(v, float) else str(v)


def _resolve_fig_dir() -> str:
    d = settings.report.fig_dir
    if not os.path.isabs(d):
        d = os.path.join(_ROOT, d.lstrip("./").lstrip("/"))
    return d


def _build_rag_answer(vs, query: str) -> dict:
    """在指定向量库上做检索 + 本地 LLM 生成（复用 HybridRetriever）。"""
    retriever = HybridRetriever()
    retriever.vs = vs
    results = retriever.retrieve(query)
    if not results:
        return {"answer": "（未在上传内容中找到相关信息）", "sources": [], "retrieved": []}

    blocks, cites = [], []
    for r in results:
        meta = r.get("metadata", {})
        doc_id = meta.get("doc_id", "?")
        pos = meta.get("page_or_pos") or meta.get("heading_path") or "全文"
        blocks.append(f"[doc_id={doc_id}, 位置={pos}]\n{r['document']}")
        cites.append(f"doc_id={doc_id}, 位置={pos}")
    context = "\n\n".join(blocks)

    prompt = (
        "你是一名严谨的金融研究助理。请仅基于下列【参考资料】回答用户问题，"
        "不得编造未提供的信息；若资料不足以回答，请明确说明。\n\n"
        f"【参考资料】\n{context}\n\n【用户问题】\n{query}\n\n"
        "请输出结构化回答，并在句末用 [来源: doc_id=xxx, 位置=yyy] 标注引用。"
    )
    messages = [
        {"role": "system", "content": "你是金融知识库问答助手，回答必须引用资料来源。"},
        {"role": "user", "content": prompt},
    ]
    try:
        content = default_client.chat(messages)
    except Exception as e:  # noqa: BLE001
        content = f"（LLM 生成失败：{e}）\n\n参考资料摘要：\n" + context[:1000]
    return {"answer": content, "sources": cites, "retrieved": results}


def _ingest_to_temp_vs(content, doc_id: str):
    """把文本（或文本列表）写入一次性临时 collection，返回 (vs, cfg)。"""
    os.makedirs(_UPLOAD_VS_DIR, exist_ok=True)
    cfg = VectorStoreConfig(
        type="chroma",
        persist_dir=_UPLOAD_VS_DIR,
        collection=f"up_{uuid.uuid4().hex}",
        distance="cosine",
    )
    vs = ChromaVectorStore(cfg)
    if isinstance(content, list):
        chunks = chunk_segments(content, doc_id)
    else:
        chunks = chunk_document(content, doc_id)
    chunks = [c for c in chunks if c.text.strip()]
    if not chunks:
        raise HTTPException(status_code=400, detail="文档内容为空或无法切分")

    embs = default_client.embed([c.text for c in chunks])
    ids, docs, metas = [], [], []
    for c, emb in zip(chunks, embs):
        cid = hashlib.md5(
            f"{c.doc_id}|{c.page_or_pos}|{c.text[:50]}".encode()
        ).hexdigest()
        ids.append(cid)
        docs.append(c.text)
        metas.append({
            "doc_id": c.doc_id,
            "page_or_pos": c.page_or_pos,
            "heading_path": c.heading_path,
        })
    vs.add(ids=ids, documents=docs, embeddings=embs, metadatas=metas)
    return vs, cfg


# ---------- 页面与静态资源 ----------
@app.get("/", response_class=HTMLResponse)
def index():
    path = os.path.join(_STATIC, "index.html")
    if not os.path.exists(path):
        raise HTTPException(status_code=500, detail="前端页面缺失：static/index.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@app.get("/figures/{name}")
def figure(name: str):
    fp = os.path.join(_resolve_fig_dir(), os.path.basename(name))
    if not os.path.exists(fp):
        raise HTTPException(status_code=404, detail="图表不存在")
    return FileResponse(fp)


# ---------- 核心接口：分析 / 查询 ----------
@app.post("/api/analyze")
async def analyze(file: Optional[UploadFile] = File(None), query: str = Form("")):
    # 1) 无文件 -> 知识库查询
    if file is None or not file.filename:
        if not query.strip():
            raise HTTPException(status_code=400, detail="未上传文件时，问题不能为空")
        try:
            res = rag_answer(query)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=502, detail=f"知识库查询失败：{e}")
        return {
            "mode": "kb",
            "answer": res.get("answer", ""),
            "sources": res.get("sources", []),
            "details": {},
        }

    # 2) 有文件 -> 按扩展名路由
    ext = os.path.splitext(file.filename)[1].lower()
    tmp_dir = tempfile.mkdtemp(prefix="fa_upload_")
    save_path = os.path.join(tmp_dir, f"upload{uuid.uuid4().hex}{ext}")
    with open(save_path, "wb") as f:
        f.write(await file.read())

    try:
        if ext == ".json":
            return _analyze_financial(save_path, file.filename, query)
        if ext in _IMG_EXT:
            return _analyze_image(save_path, file.filename, query)
        if ext in _TXT_EXT:
            with open(save_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            return _analyze_text(text, file.filename, query)
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型：{ext}（支持 .json / 图片 / .txt / .md）",
        )
    finally:
        try:
            os.remove(save_path)
            os.rmdir(tmp_dir)
        except OSError:
            pass


def _analyze_financial(path: str, filename: str, query: str):
    cur, prior = load_pair(path)
    ratios = compute_ratios(cur)
    yoy = compare_yoy(cur, prior) if prior else {}
    anomalies = detect_anomalies(cur, prior) if prior else []

    lines = [f"公司 {cur.company or '?'} 报告期 {cur.period or '?'} 财务分析："]
    for k in ("ROE", "ROA", "毛利率", "净利率", "资产负债率", "流动比率"):
        v = ratios.get(k)
        lines.append(f"  {k}: {_fmt(v) if v is not None else 'N/A'}")
    if anomalies:
        lines.append(f"发现 {len(anomalies)} 项异常/预警：")
        for a in anomalies:
            lines.append(f"  [{a.level}] {a.message}")
    else:
        lines.append("未发现显著异常。")
    if not prior:
        lines.append("（未提供去年同期数据，跳过同比与异常检测）")

    kb_supplement = None
    if query.strip():
        try:
            kb_supplement = rag_answer(query).get("answer", "")
        except Exception:  # noqa: BLE001
            kb_supplement = None

    return {
        "mode": "financial",
        "answer": "\n".join(lines),
        "sources": [filename],
        "details": {
            "ratios": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in ratios.items()},
            "yoy": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in yoy.items()},
            "anomalies": [
                {"level": a.level, "item": a.item, "message": a.message} for a in anomalies
            ],
        },
        "kb_supplement": kb_supplement,
    }


def _analyze_image(path: str, filename: str, query: str):
    from ocr.pipeline import process_image

    doc = process_image(path)
    segments: List[str] = doc.segments or []
    text = "\n".join(segments)
    if not text.strip():
        return {
            "mode": "ocr",
            "answer": "（OCR 未能从图片中提取到文本，可能图片无文字或识别失败）",
            "sources": [filename],
            "details": {"extracted_text": ""},
        }
    vs, cfg = _ingest_to_temp_vs(segments, os.path.splitext(filename)[0])
    q = query.strip() or "请总结这份财报/文档的核心内容。"
    rag = _build_rag_answer(vs, q)
    _safe_drop(vs, cfg)
    return {
        "mode": "ocr",
        "answer": rag["answer"],
        "sources": rag["sources"],
        "details": {"extracted_text": text},
    }


def _analyze_text(text: str, filename: str, query: str):
    vs, cfg = _ingest_to_temp_vs(text, os.path.splitext(filename)[0])
    q = query.strip() or "请总结这份文档的核心内容。"
    rag = _build_rag_answer(vs, q)
    _safe_drop(vs, cfg)
    return {
        "mode": "ingest",
        "answer": rag["answer"],
        "sources": rag["sources"],
        "details": {"char_count": len(text)},
    }


def _safe_drop(vs, cfg):
    try:
        vs._client.delete_collection(cfg.collection)
    except Exception:  # noqa: BLE001
        pass


# ---------- 完整报告 ----------
@app.post("/api/report")
async def report(payload: dict):
    query = (payload or {}).get("query", "")
    if not query.strip():
        raise HTTPException(status_code=400, detail="query 不能为空")
    from report import analyze as run_analyze

    try:
        res, report_path, figures = run_analyze(query)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"报告生成失败：{e}")

    report_text = ""
    if report_path and os.path.exists(report_path):
        with open(report_path, "r", encoding="utf-8") as f:
            report_text = f.read()
    fig_urls = [f"/figures/{os.path.basename(f)}" for f in (figures or [])]
    return {
        "summary": res.summary,
        "overall_confidence": res.overall_confidence,
        "human_in_the_loop": res.human_in_the_loop,
        "disclaimer": res.disclaimer,
        "conflicts": res.conflicts,
        "report_markdown": report_text,
        "figures": fig_urls,
        "report_path": report_path,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
