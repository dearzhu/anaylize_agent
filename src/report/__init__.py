"""报告自动生成 + 可视化（三期 c2）。

提供：
  - generate_report(query, messages, fused, figures)：落盘 Markdown 报告
  - make_figures(messages, fused)：生成图表
  - analyze(query, params, generate_report=True)：串联 Supervisor 协作闭环 + 报告/图表
"""
from .generator import generate_report as _generate_report
from .visualize import make_figures


def analyze(query: str, params: dict | None = None, do_report: bool = True):
    """运行多智能体协作闭环（Supervisor.handle），并产出报告与图表。

    返回 (FusedResult, report_path, figures)。
    """
    from orchestrator.supervisor import Supervisor
    res = Supervisor().handle(query, params)
    figs = make_figures(res.messages, res)
    path = None
    if do_report:
        path = _generate_report(query, res.messages, res, figures=figs)
    return res, path, figs


__all__ = ["generate_report", "make_figures", "analyze"]
