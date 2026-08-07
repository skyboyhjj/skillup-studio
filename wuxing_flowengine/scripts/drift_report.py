"""
领域漂移分析报告生成器（P1#3）
================================
从 Phase 3+ 诊断输出生成结构化 Markdown 报告。

用法:
    from drift_report import generate_drift_report
    generate_drift_report(phase3_output, output_dir, month_label='2026-07')
"""

import json
import os
from datetime import datetime
from collections import OrderedDict


def _format_direction(direction, is_guarded):
    """格式化方向标签"""
    if is_guarded:
        return f"*{direction}*"
    return f"**{direction}**"


def _format_drift_bar(drift, width=20):
    """生成漂移值的 ASCII 条形图"""
    filled = int(drift * width)
    if drift > 0.4:
        bar = '█' * filled + '░' * (width - filled)
    elif drift > 0.15:
        bar = '▓' * filled + '░' * (width - filled)
    else:
        bar = '▒' * filled + '░' * (width - filled)
    return bar


def _domain_table_rows(domains_data):
    """生成领域漂移表行"""
    rows = []
    for domain, d in sorted(domains_data.items(),
                             key=lambda x: x[1].get('comparison', {}).get('drift', 0),
                             reverse=True):
        comp = d.get('comparison', {})
        drift = comp.get('drift', 0)
        direction = comp.get('direction', '')
        is_guarded = comp.get('is_guarded', False)
        rel = d.get('reliability', {})
        drift_ci = d.get('drift_confidence_interval', {})
        
        node_count = d.get('node_count', 0)
        paper_count = d.get('paper_count', 0)
        
        # 信度区间
        if rel.get('can_compare'):
            ci_str = f"[{drift_ci.get('ci_low', 0):.2f}-{drift_ci.get('ci_high', 1):.2f}]"
        else:
            ci_str = "—"
        
        # 状态图标
        if not rel.get('can_compare'):
            status = '🚫'
        elif is_guarded:
            status = '⚠️'
        else:
            status = '✅'
        
        rows.append({
            'status': status,
            'domain': domain,
            'drift': drift,
            'drift_bar': _format_drift_bar(drift),
            'ci': ci_str,
            'direction': direction,
            'is_guarded': is_guarded,
            'node_count': node_count,
            'paper_count': paper_count,
            'reliability': rel.get('level', '未知'),
            'score': rel.get('score', 0)
        })
    
    return rows


def generate_drift_report(phase3_output, output_dir, month_label=None,
                          chart_paths=None):
    """
    生成领域漂移分析 Markdown 报告。
    
    Args:
        phase3_output: Phase 3+ 的 dict 输出
        output_dir: 报告保存目录
        month_label: 月份标签
        chart_paths: 图表路径列表（可选，用于嵌入）
    
    Returns:
        报告文件路径
    """
    domains = phase3_output.get('domains', {})
    drift_quality = phase3_output.get('drift_quality', {})
    total_papers = phase3_output.get('total_papers', 0)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 基础统计
    rows = _domain_table_rows(domains)
    total_domains = len(rows)
    unreliable_count = drift_quality.get('unreliable_count',
                                          sum(1 for r in rows if not r['reliability'] in ('高', '中')))
    guarded_count = sum(1 for r in rows if r['is_guarded'])
    reliable_count = sum(1 for r in rows if r['reliability'] == '高' and not r['is_guarded'])
    
    # 构建报告
    lines = []
    lines.append(f'# 领域漂移分析报告')
    lines.append(f'')
    lines.append(f'> 生成时间: {timestamp}')
    lines.append(f'> 数据月份: {month_label or "最新"}')
    lines.append(f'> 论文总数: {total_papers}')
    lines.append(f'> 分析领域: {total_domains}')
    lines.append(f'')
    
    # ============================================================
    # 1. 摘要
    # ============================================================
    lines.append(f'## 1. 摘要')
    lines.append(f'')
    lines.append(f'| 指标 | 值 |')
    lines.append(f'|------|----|')
    lines.append(f'| 总领域数 | {total_domains} |')
    lines.append(f'| 可靠判定 | {reliable_count} |')
    lines.append(f'| 信度守卫（需谨慎） | {guarded_count} |')
    lines.append(f'| 数据不足/不可比较 | {unreliable_count} |')
    lines.append(f'')
    
    # 漂移质量
    if drift_quality.get('summary'):
        lines.append(f'**{drift_quality["summary"]}**')
        lines.append(f'')
    
    # ============================================================
    # 2. 漂移排名表
    # ============================================================
    lines.append(f'## 2. 领域漂移排名')
    lines.append(f'')
    lines.append(f'| # | 领域 | 漂移 | 可视化 | 95% CI | 判定 | 节点 | 论文 | 可靠性 |')
    lines.append(f'|---|------|------|--------|--------|------|------|------|--------|')
    
    for i, r in enumerate(rows, 1):
        direction_fmt = _format_direction(r['direction'], r['is_guarded'])
        lines.append(
            f'| {i} | {r["status"]} {r["domain"]} | {r["drift"]:.3f} | '
            f'`{r["drift_bar"]}` | {r["ci"]} | {direction_fmt} | '
            f'{r["node_count"]} | {r["paper_count"]} | {r["reliability"]} ({r["score"]:.2f}) |'
        )
    
    lines.append(f'')
    lines.append(f'> 图例: ✅ 可靠  ⚠️ 需谨慎  🚫 数据不足')
    lines.append(f'> 漂移条形: █ 高漂移(>0.4)  ▓ 中漂移(0.15-0.4)  ▒ 低漂移(<0.15)')
    lines.append(f'')
    
    # ============================================================
    # 3. 不可靠领域
    # ============================================================
    unreliable = drift_quality.get('unreliable_domains', [])
    if unreliable:
        lines.append(f'## 3. 不可靠/需谨慎的领域')
        lines.append(f'')
        lines.append(f'以下领域的漂移分析存在数据不足或置信度较低的问题：')
        lines.append(f'')
        lines.append(f'| 领域 | 节点数 | 论文数 | 原因 | 当前判定 |')
        lines.append(f'|------|--------|--------|------|----------|')
        for ud in unreliable:
            direction = ud.get('direction', '数据不足')
            lines.append(
                f'| {ud["domain"]} | {ud["node_count"]} | {ud["paper_count"]} | '
                f'{ud["reason"]} | {direction} |'
            )
        lines.append(f'')
    
    # ============================================================
    # 4. 建议
    # ============================================================
    lines.append(f'## 4. 改进建议')
    lines.append(f'')
    
    # 针对数据不足的领域
    data_insufficient = [ud for ud in unreliable
                         if ud.get('reason', '') == '数据不足']
    if data_insufficient:
        domains_list = ', '.join(ud['domain'] for ud in data_insufficient)
        lines.append(f'### 4.1 补充数据')
        lines.append(f'')
        lines.append(f'以下领域缺少知识树节点或论文数据，无法进行漂移分析：')
        lines.append(f'')
        lines.append(f'- **{domains_list}**')
        lines.append(f'')
        lines.append(f'建议：')
        lines.append(f'1. 对缺少论文的领域，等待 BAAI Hub 月报发布后补充论文数据')
        lines.append(f'2. 对缺少知识树节点的领域，确认知识图谱是否覆盖该领域')
        lines.append(f'')
    
    # 针对低置信度领域
    low_confidence = [ud for ud in unreliable
                      if '置信度不足' in ud.get('reason', '')]
    if low_confidence:
        domains_list = ', '.join(ud['domain'] for ud in low_confidence)
        lines.append(f'### 4.2 提升置信度')
        lines.append(f'')
        lines.append(f'以下领域节点数不足（<10），导致漂移判定置信度低：')
        lines.append(f'')
        lines.append(f'- **{domains_list}**')
        lines.append(f'')
        lines.append(f'建议：')
        lines.append(f'1. 关注这些领域的知识树节点增长，当节点数超过10后可重新判定')
        lines.append(f'2. 考虑使用更细粒度的子领域分析替代当前领域级分析')
        lines.append(f'')
    
    # 针对中置信度领域
    medium_confidence = [ud for ud in unreliable
                         if '置信度中等' in ud.get('reason', '')]
    if medium_confidence:
        lines.append(f'### 4.3 持续监控')
        lines.append(f'')
        lines.append(f'以下领域置信度为中等，漂移判定需谨慎解读。建议持续监控多个月份数据：')
        lines.append(f'')
        for ud in medium_confidence:
            drift_val = ud.get('drift', 0)
            lines.append(f'- **{ud["domain"]}**: drift={drift_val:.2f}, '
                         f'节点{ud["node_count"]}/论文{ud["paper_count"]}')
        lines.append(f'')
    
    # ============================================================
    # 5. 图表
    # ============================================================
    if chart_paths:
        lines.append(f'## 5. 可视化图表')
        lines.append(f'')
        chart_names = {
            'drift_bars': '漂移幅度柱状图',
            'drift_confidence': '漂移信度区间图',
            'drift_scatter': '样本量散点图',
            'wuxing_radar': '五行分布雷达图'
        }
        for path in chart_paths:
            basename = os.path.splitext(os.path.basename(path))[0]
            # 去掉月份前缀
            name_key = basename.replace(f'{month_label}_', '') if month_label else basename
            display_name = '未知图表'
            for key, cn_name in chart_names.items():
                if key in name_key:
                    display_name = cn_name
                    break
            lines.append(f'### {display_name}')
            lines.append(f'')
            lines.append(f'![{display_name}]({path})')
            lines.append(f'')
    
    # ============================================================
    # 6. 元数据
    # ============================================================
    lines.append(f'---')
    lines.append(f'')
    lines.append(f'*报告由 drift_report.py (V1.0) 自动生成*')
    lines.append(f'*数据来源: {phase3_output.get("data_sources", {}).get("phase2", "未知")}*')
    lines.append(f'')
    
    # 保存
    os.makedirs(output_dir, exist_ok=True)
    prefix = f'{month_label}_' if month_label else ''
    report_path = os.path.join(output_dir, f'{prefix}drift_report.md')
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f'  ✓ 漂移报告: {report_path}')
    return report_path


# ============================================================
# 自检
# ============================================================

if __name__ == '__main__':
    print('=' * 60)
    print('漂移报告生成器 — 自检')
    print('=' * 60)
    
    base_dir = r'E:\00-TRAEWK\6a59e217b55e181ea97f0df3\wuxing_flowengine'
    phase3_path = os.path.join(base_dir, 'output', 'archive', '2026-07',
                                'phase3_plus_diagnosis_2026-07.json')
    
    if os.path.exists(phase3_path):
        with open(phase3_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        output_dir = os.path.join(base_dir, 'output', 'reports')
        chart_dir = os.path.join(base_dir, 'output', 'charts')
        chart_paths = [
            os.path.join(chart_dir, '2026-07_drift_bars.png'),
            os.path.join(chart_dir, '2026-07_drift_confidence.png'),
            os.path.join(chart_dir, '2026-07_drift_scatter.png'),
            os.path.join(chart_dir, '2026-07_wuxing_radar.png'),
        ]
        
        report_path = generate_drift_report(
            data, output_dir, month_label='2026-07',
            chart_paths=chart_paths
        )
        print(f'\n报告已生成: {report_path}')
    else:
        print(f'数据文件不存在: {phase3_path}')