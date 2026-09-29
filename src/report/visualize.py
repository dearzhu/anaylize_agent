"""可视化生成（三期 c2）。

基于各 Agent 的结构化输出绘制图表，保存为本地图片，供报告引用。
使用 matplotlib（Agg 后端，无需 GUI）。若运行环境无 matplotlib，则优雅返回空列表。
"""
from __future__ import annotations

import os
from typing import Any, List

from core.config import settings


def _resolve_fig_dir() -> str:
    fig_dir = settings.report.fig_dir
    if not os.path.isabs(fig_dir):
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        fig_dir = os.path.join(root, fig_dir.lstrip("./").lstrip("/"))
    os.makedirs(fig_dir, exist_ok=True)
    return fig_dir


def _by_agent(messages: List[Any]) -> dict:
    return {getattr(m, "agent", i): m for i, m in enumerate(messages)}


def make_figures(messages: List[Any], fused: Any = None) -> List[str]:
    """根据 Agent 输出生成图表，返回图片绝对路径列表。"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib import font_manager
        for cand in ["Microsoft YaHei", "SimHei", "PingFang SC", "Noto Sans CJK SC"]:
            if any(cand.lower() in f.name.lower() for f in font_manager.fontManager.ttflist):
                plt.rcParams["font.sans-serif"] = [cand]
                break
        plt.rcParams["axes.unicode_minus"] = False
    except Exception:  # noqa: BLE001  无 matplotlib 环境
        return []

    fig_dir = _resolve_fig_dir()
    paths: List[str] = []
    by = _by_agent(messages)

    # 1) 财务比率
    fin = by.get("financial_agent")
    fin_out = getattr(fin, "output", {}) if fin else {}
    ratios = {k: v for k, v in (fin_out.get("ratios") or {}).items() if v is not None}
    if ratios:
        p = os.path.join(fig_dir, "ratios.png")
        plt.figure(figsize=(8, 4))
        plt.bar(range(len(ratios)), list(ratios.values()), color="#2c7fb8")
        plt.xticks(range(len(ratios)), list(ratios.keys()), rotation=45, ha="right")
        plt.title("财务比率")
        plt.tight_layout(); plt.savefig(p, dpi=100); plt.close()
        paths.append(p)

    # 2) 同比变动
    yoy = {k: v for k, v in (fin_out.get("yoy") or {}).items() if v is not None}
    if yoy:
        p = os.path.join(fig_dir, "yoy.png")
        vals = list(yoy.values())
        plt.figure(figsize=(8, 4))
        plt.bar(range(len(yoy)), vals, color=["#d7301f" if v < 0 else "#1a9641" for v in vals])
        plt.xticks(range(len(yoy)), list(yoy.keys()), rotation=45, ha="right")
        plt.title("同比变动"); plt.axhline(0, color="k", lw=0.8)
        plt.tight_layout(); plt.savefig(p, dpi=100); plt.close()
        paths.append(p)

    # 3) 风险雷达
    risk = by.get("risk_agent")
    risk_out = getattr(risk, "output", {}) if risk else {}
    scores = risk_out.get("scores") or {}
    if scores:
        p = os.path.join(fig_dir, "risk_radar.png")
        import numpy as np
        labels = list(scores.keys()); vals = list(scores.values())
        angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
        vals2 = vals + vals[:1]; angles2 = angles + angles[:1]
        plt.figure(figsize=(5, 5))
        ax = plt.subplot(111, polar=True)
        ax.plot(angles2, vals2, color="#756bb1"); ax.fill(angles2, vals2, alpha=0.25, color="#756bb1")
        ax.set_xticks(angles); ax.set_xticklabels(labels); ax.set_ylim(0, 100)
        plt.title("风险维度评分（越高越安全）")
        plt.tight_layout(); plt.savefig(p, dpi=100); plt.close()
        paths.append(p)

    # 4) 资金流向
    flow = by.get("flow_agent")
    flow_out = getattr(flow, "output", {}) if flow else {}
    if flow_out:
        p = os.path.join(fig_dir, "flow.png")
        plt.figure(figsize=(5, 4))
        plt.bar(["流入", "流出", "净额"],
                [flow_out.get("total_in", 0), flow_out.get("total_out", 0), flow_out.get("net_flow", 0)],
                color=["#1a9641", "#d7301f", "#2c7fb8"])
        plt.title("资金流向")
        plt.tight_layout(); plt.savefig(p, dpi=100); plt.close()
        paths.append(p)

    return paths
