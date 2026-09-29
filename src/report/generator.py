"""报告自动生成（三期 c2）。

把 Supervisor 的融合结论与各 Worker Agent 输出，渲染为结构化 Markdown 报告，
含图表引用、风险提示、数据来源溯源与合规免责声明（设计文档 6）。
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List

from core.config import settings


def _resolve_out(path: str) -> str:
    if not os.path.isabs(path):
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        path = os.path.join(root, path.lstrip("./").lstrip("/"))
    return path


def generate_report(query: str, messages: List[Any], fused: Any,
                    figures: List[str] | None = None) -> str:
    """生成 Markdown 报告并落盘，返回文件路径。"""
    out_dir = _resolve_out(settings.report.output_dir)
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(out_dir, f"report_{ts}.md")

    lines: List[str] = []
    lines.append("# 金融数据分析报告\n")
    lines.append(f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- 用户问题：{query}")
    lines.append(f"- 整体置信度：{getattr(fused, 'overall_confidence', 'N/A')}")
    lines.append("")

    # 摘要（融合结论）
    lines.append("## 一、综合结论\n")
    lines.append(getattr(fused, "summary", "（无结论）") or "（无结论）")
    if getattr(fused, "human_in_the_loop", False):
        lines.append("\n> ⚠️ **需人工复核**：结论涉及交易建议 / 合规结论，或存在 Agent 间冲突 / 低置信度，"
                     "请人工确认后方可用于决策。")
    lines.append("")

    # 各 Agent 结论
    lines.append("## 二、各智能体分析结论\n")
    for m in messages:
        tag = "OK" if getattr(m, "success", True) else "ERR"
        notes = getattr(m, "notes", "") or (m.output.get("summary", "") if isinstance(getattr(m, "output", None), dict) else "")
        sources = getattr(m, "sources", []) or []
        lines.append(f"### {m.agent}（{tag} | 置信度 {getattr(m, 'confidence', 'N/A')}）\n")
        lines.append(notes or "（无结论）")
        if sources:
            lines.append("\n来源：" + "; ".join(str(s) for s in sources))
        lines.append("")

    # 冲突检测
    conflicts = getattr(fused, "conflicts", []) or []
    lines.append("## 三、冲突检测与复核\n")
    if conflicts:
        for c in conflicts:
            lines.append(f"- 【{c.get('type')}】{c.get('detail')}")
    else:
        lines.append("未发现 Agent 间结论冲突。")
    lines.append("")

    # 风险提示（来自风控 Agent）
    risk_msg = next((m for m in messages if getattr(m, "agent", "") == "risk_agent"), None)
    risk_out = getattr(risk_msg, "output", {}) if risk_msg else {}
    alerts = risk_out.get("findings") if isinstance(risk_out, dict) else []
    lines.append("## 四、风险提示\n")
    if alerts:
        for a in alerts:
            lines.append(f"- {a}")
    else:
        lines.append("未触发显著风险预警。")
    lines.append("")

    # 图表
    if figures:
        lines.append("## 五、可视化图表\n")
        for fig in figures:
            rel = os.path.relpath(fig, out_dir)
            lines.append(f"![{os.path.basename(fig)}]({rel})")
        lines.append("")

    # 免责声明
    lines.append("----\n")
    lines.append("> **免责声明**：本报告由 AI 智能体自动生成，仅供研究参考，**不构成任何投资建议**。"
                 "涉及交易决策与合规结论须由具备资质的人员人工复核确认。")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path
