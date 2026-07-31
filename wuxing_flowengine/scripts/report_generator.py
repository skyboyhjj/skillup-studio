#!/usr/bin/env python3
"""
月度诊断报告生成器
从流水线输出 JSON 生成 Markdown 格式的月度报告。
"""
import json, os
from datetime import datetime


def generate_monthly_report(base_dir, month_label, phase1_diag=None, phase2_diag=None, phase3_diag=None, timeseries_diag=None, output_path=None):
    """
    生成月度 Markdown 诊断报告。

    参数:
        base_dir:         项目根目录
        month_label:      月份标签
        phase1_diag:      Phase 1 诊断 JSON 路径
        phase2_diag:      Phase 2 诊断 JSON 路径
        phase3_diag:      Phase 3+ 诊断 JSON 路径
        timeseries_diag:  时间序列诊断 JSON 路径
        output_path:      输出 Markdown 路径

    返回:
        生成的 Markdown 文件路径
    """
    output_dir = os.path.join(base_dir, "output")
    if output_path is None:
        output_path = os.path.join(output_dir, f"monthly_report_{month_label}.md")

    # 加载数据
    data = {}
    for key, path in [("p1", phase1_diag), ("p2", phase2_diag), ("p3", phase3_diag), ("ts", timeseries_diag)]:
        if path and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data[key] = json.load(f)

    lines = []
    lines.append(f"# 道境五行诊断月报 · {month_label}")
    lines.append("")
    lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**数据来源**: BAAI 智源社区知识树 + 月度报告")
    lines.append("")

    # ── 一、静态诊断概览 ──
    if "p1" in data:
        p1 = data["p1"]
        lines.append("---")
        lines.append("")
        lines.append("## 一、静态诊断（知识树结构）")
        lines.append("")
        s = p1.get("stats", {})
        d = p1.get("depth_dist", {})
        w = p1.get("wuxing_dist", {})
        dims = p1.get("four_dims", {})
        tracks = p1.get("tracks", {})
        total = s.get("total", 0)

        lines.append(f"**节点数**: {total}（种子层 {s.get('seed', 0)} | 现行层 {s.get('current', 0)} | 超越层 {s.get('transcend', 0)}）")
        lines.append("")
        lines.append("### 五行频次")
        lines.append("")
        lines.append("| 五行 | 节点数 | 占比 |")
        lines.append("|------|--------|------|")
        for wx in ["木", "火", "土", "金", "水"]:
            cnt = w.get(wx, 0)
            lines.append(f"| {wx} | {cnt} | {cnt/total*100:.1f}% |" if total else f"| {wx} | 0 | 0% |")
        lines.append("")
        lines.append("### 四维读数")
        lines.append("")
        lines.append("| 维度 | 值 |")
        lines.append("|------|------|")
        for dim, val in dims.items():
            lines.append(f"| {dim} | {val:.4f} |")
        lines.append("")
        lines.append("### 四轨 S 值")
        lines.append("")
        lines.append("| 轨道 | S 值 |")
        lines.append("|------|------|")
        for track, val in tracks.items():
            lines.append(f"| {track} | {val} |")
        lines.append(f"\n**阶段判定**: {p1.get('stage', 'N/A')}")
        lines.append("")

    # ── 二、双层标注 ──
    if "p2" in data:
        p2 = data["p2"]
        lines.append("---")
        lines.append("")
        lines.append("## 二、双层标注分析")
        lines.append("")
        lines.append(f"**双层标注节点**: {p2.get('dual_label_count', 0)} 个（实际应用 {p2.get('dual_label_applied', 0)} 个）")
        lines.append("")
        lines.append("### 层间转换效率")
        conv = p2.get("conversion_efficiency", {})
        lines.append(f"- 种子层 → 现行层: {conv.get('seed_to_current', 0):.3f}")
        lines.append(f"- 现行层 → 超越层: {conv.get('current_to_transcend', 0):.3f}")
        lines.append("")
        lines.append("### 领域 S_D 值（Top 5）")
        lines.append("")
        domain_tracks = p2.get("domain_tracks", {})
        sorted_domains = sorted(domain_tracks.items(), key=lambda x: -x[1].get("total", 0))[:5]
        lines.append("| 领域 | 节点数 | S_D(模长) | A(乘积) | B(螺旋) |")
        lines.append("|------|--------|-----------|---------|---------|")
        for domain, tr in sorted_domains:
            lines.append(f"| {domain} | {tr.get('total', 0)} | {tr.get('D', 0):.4f} | {tr.get('A', 0):.2f} | {tr.get('B', 0):.2f} |")
        lines.append("")

    # ── 三、动态分析 ──
    if "p3" in data:
        p3 = data["p3"]
        lines.append("---")
        lines.append("")
        lines.append("## 三、结构-活跃度动态分析")
        lines.append("")
        summary = p3.get("summary", {})
        lines.append(f"**分析领域**: {summary.get('domains_analyzed', 0)} 个")
        lines.append(f"**总论文数**: {summary.get('total_papers', 0)} 篇")
        lines.append(f"**平均漂移幅度**: {summary.get('mean_drift_magnitude', 0):.4f}")
        if summary.get('max_drift_domain'):
            lines.append(f"**最大漂移领域**: {summary['max_drift_domain']}（{summary.get('max_drift_magnitude', 0):.4f}）")
        lines.append("")
        lines.append("### 全领域漂移概览")
        lines.append("")
        lines.append("| 领域 | 节点数 | 论文数 | 漂移幅度 | 判读 |")
        lines.append("|------|--------|--------|----------|------|")
        domains = p3.get("domains", {})
        for domain, info in sorted(domains.items(), key=lambda x: -x[1]["centroid_drift"]["magnitude"]):
            cd = info["centroid_drift"]
            lines.append(f"| {domain} | {info['node_count']} | {info['paper_count']} | {cd['magnitude']:.4f} | {cd['reading'][:15]} |")
        lines.append("")

    # ── 四、时间序列 ──
    if "ts" in data:
        ts = data["ts"]
        lines.append("---")
        lines.append("")
        lines.append("## 四、时间序列分析")
        lines.append("")
        ts_summary = ts.get("summary", {})
        prev = ts.get("prev_label", "上月")
        curr = ts.get("current_label", "当月")
        lines.append(f"**对比区间**: {prev} → {curr}")
        lines.append(f"**平均月际漂移**: {ts_summary.get('mean_monthly_drift', 0):.4f}")
        lines.append(f"**漂移变化趋势**: {ts_summary.get('mean_drift_change', 0):+.4f}")
        lines.append("")
        lines.append("| 领域 | 月际漂移 | 结构漂移变化 | 趋势 |")
        lines.append("|------|----------|--------------|------|")
        for domain, info in sorted(ts.get("time_series", {}).items(), key=lambda x: -x[1]["monthly_drift_magnitude"]):
            lines.append(f"| {domain} | {info['monthly_drift_magnitude']:.4f} | {info.get('drift_magnitude_change', 0):+.4f} | {info.get('reading', '')[:10]} |")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(f"*报告由月度自动追踪流水线生成 · {datetime.now().strftime('%Y-%m-%d %H:%M')}*")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"  月度报告已生成: {output_path}")
    return output_path


if __name__ == "__main__":
    DEFAULT_BASE = r"C:\Users\hejij\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a59e217b55e181ea97f0df3\wuxing_flowengine"
    generate_monthly_report(DEFAULT_BASE, "2026-07")