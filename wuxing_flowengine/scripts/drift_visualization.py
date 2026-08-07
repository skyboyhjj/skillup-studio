"""
漂移分析可视化模块（P1#3）
============================
从 Phase 3+ 诊断输出生成领域漂移图表。

图表类型：
1. 漂移柱状图 — 按可靠性着色
2. 漂移信度区间图 — 误差棒 + 方向标签
3. 样本量散点图 — 节点/论文二维分布
4. 五行分布对比图 — 节点 vs 论文雷达图（多领域）

用法:
    from drift_visualization import generate_all_charts
    generate_all_charts(phase3_output, output_dir, month_label='2026-07')
"""

import json
import os
import math
import matplotlib
matplotlib.use('Agg')  # 非交互式后端
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
from collections import OrderedDict


# ============================================================
# 中文字体配置
# ============================================================

def _setup_chinese_font():
    """配置 matplotlib 中文字体"""
    try:
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
    except Exception:
        pass


_setup_chinese_font()

# 颜色方案
COLOR_RELIABLE = '#2ecc71'       # 绿色 - 可靠
COLOR_GUARDED = '#f39c12'        # 橙色 - 需谨慎
COLOR_UNRELIABLE = '#e74c3c'     # 红色 - 不可靠
COLOR_NEUTRAL = '#95a5a6'        # 灰色 - 中性
WUXING_COLORS = {
    '木': '#27ae60', '火': '#e74c3c',
    '土': '#f39c12', '金': '#f1c40f',
    '水': '#3498db'
}


def _get_domain_color(reliability_level, is_guarded):
    """根据可靠性等级返回颜色"""
    if reliability_level in ('不可用', '无'):
        return COLOR_UNRELIABLE
    if is_guarded:
        return COLOR_GUARDED
    return COLOR_RELIABLE


def _get_direction_emoji(direction):
    """方向标签 → 简短符号"""
    if '显著漂移' in direction:
        return '!!'
    if '可能漂移' in direction:
        return '!?'
    if '轻度漂移' in direction or '轻微漂移' in direction:
        return '~'
    if '数据不足' in direction:
        return '??'
    return 'ok'


# ============================================================
# 图表 1: 漂移柱状图
# ============================================================

def plot_drift_bars(domains_data, output_path, title=None):
    """
    水平柱状图：各领域漂移值，按可靠性着色。
    
    Args:
        domains_data: Phase 3+ 输出的 domains 字典
        output_path: 图表保存路径
        title: 图表标题
    """
    # 过滤和排序：排除不可比较的领域，按漂移值降序
    items = []
    for domain, d in domains_data.items():
        comp = d.get('comparison', {})
        drift = comp.get('drift', 0)
        reliability = d.get('reliability', {})
        level = reliability.get('level', '未知')
        is_guarded = comp.get('is_guarded', False)
        
        items.append({
            'domain': domain,
            'drift': drift,
            'direction': comp.get('direction', ''),
            'is_guarded': is_guarded,
            'level': level,
            'node_count': d.get('node_count', 0),
            'paper_count': d.get('paper_count', 0)
        })
    
    # 按漂移降序
    items.sort(key=lambda x: x['drift'], reverse=True)
    
    domains = [it['domain'] for it in items]
    drifts = [it['drift'] for it in items]
    colors = [_get_domain_color(it['level'], it['is_guarded']) for it in items]
    
    fig, ax = plt.subplots(figsize=(12, max(6, len(domains) * 0.35)))
    
    bars = ax.barh(range(len(domains)), drifts, color=colors, edgecolor='white', linewidth=0.5)
    
    # 标注方向和样本量
    for i, it in enumerate(items):
        label = f"{_get_direction_emoji(it['direction'])} {it['drift']:.2f}"
        if it['level'] == '不可用':
            label = f"?? 不可比较"
        ax.text(it['drift'] + 0.02, i, label, va='center', fontsize=9,
                color='#555' if it['drift'] < 0.6 else '#333')
    
    # 阈值线
    ax.axvline(x=0.15, color='#bdc3c7', linestyle='--', linewidth=0.8, alpha=0.7)
    ax.axvline(x=0.40, color='#e74c3c', linestyle='--', linewidth=0.8, alpha=0.5)
    ax.text(0.15, -0.6, '轻度', fontsize=8, color='#bdc3c7', ha='center')
    ax.text(0.40, -0.6, '显著', fontsize=8, color='#e74c3c', ha='center')
    
    ax.set_yticks(range(len(domains)))
    ax.set_yticklabels(domains, fontsize=10)
    ax.set_xlabel('漂移值 (余弦距离)', fontsize=11)
    ax.set_xlim(0, 1.15)
    ax.invert_yaxis()
    
    if title:
        ax.set_title(title, fontsize=14, fontweight='bold', pad=15)
    
    # 图例
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=COLOR_RELIABLE, label='可靠判定'),
        Patch(facecolor=COLOR_GUARDED, label='信度守卫（需谨慎）'),
        Patch(facecolor=COLOR_UNRELIABLE, label='数据不足'),
    ]
    ax.legend(handles=legend_elements, loc='lower right', fontsize=9, framealpha=0.9)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'  ✓ 漂移柱状图: {output_path}')


# ============================================================
# 图表 2: 漂移信度区间图
# ============================================================

def plot_drift_confidence(domains_data, output_path, title=None):
    """
    误差棒图：各领域漂移值 + 信度区间。
    只展示可比较的领域。
    
    Args:
        domains_data: Phase 3+ 输出的 domains 字典
        output_path: 图表保存路径
        title: 图表标题
    """
    items = []
    for domain, d in domains_data.items():
        comp = d.get('comparison', {})
        drift_ci = d.get('drift_confidence_interval', {})
        reliability = d.get('reliability', {})
        
        if not reliability.get('can_compare', False):
            continue  # 跳过不可比较的
        
        items.append({
            'domain': domain,
            'drift': comp.get('drift', 0),
            'ci_low': drift_ci.get('ci_low', 0),
            'ci_high': drift_ci.get('ci_high', 1),
            'direction': comp.get('direction', ''),
            'is_guarded': comp.get('is_guarded', False),
            'level': reliability.get('level', '中')
        })
    
    if not items:
        print('  ⚠ 无可比较的领域，跳过信度区间图')
        return
    
    items.sort(key=lambda x: x['drift'])
    
    domains = [it['domain'] for it in items]
    drifts = [it['drift'] for it in items]
    ci_lows = [it['ci_low'] for it in items]
    ci_highs = [it['ci_high'] for it in items]
    errors_low = [d - l for d, l in zip(drifts, ci_lows)]
    errors_high = [h - d for d, h in zip(drifts, ci_highs)]
    colors = [_get_domain_color(it['level'], it['is_guarded']) for it in items]
    
    fig, ax = plt.subplots(figsize=(12, max(5, len(domains) * 0.35)))
    
    y_pos = range(len(domains))
    # 逐条绘制误差棒，支持不同颜色
    for i, (drift, err_low, err_high, color) in enumerate(zip(drifts, errors_low, errors_high, colors)):
        ax.errorbar([drift], [i], xerr=[[err_low], [err_high]],
                    fmt='none', ecolor=color, capsize=4,
                    elinewidth=2, alpha=0.7)
        ax.scatter([drift], [i], color=color, s=80, zorder=5,
                   edgecolors='white', linewidth=1)
    
    # 标注
    for i, it in enumerate(items):
        label = f"{it['drift']:.2f} [{it['ci_low']:.2f}-{it['ci_high']:.2f}]"
        ax.text(it['ci_high'] + 0.03, i, label, va='center', fontsize=8, color='#555')
    
    ax.axvline(x=0.15, color='#bdc3c7', linestyle='--', linewidth=0.8, alpha=0.5)
    ax.axvline(x=0.40, color='#e74c3c', linestyle='--', linewidth=0.8, alpha=0.5)
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(domains, fontsize=10)
    ax.set_xlabel('漂移值 + 95% 信度区间', fontsize=11)
    ax.set_xlim(-0.05, 1.25)
    ax.invert_yaxis()
    
    if title:
        ax.set_title(title, fontsize=14, fontweight='bold', pad=15)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'  ✓ 信度区间图: {output_path}')


# ============================================================
# 图表 3: 样本量散点图
# ============================================================

def plot_sample_scatter(domains_data, output_path, title=None):
    """
    散点图：X=节点数, Y=论文数, 颜色=漂移, 大小=可靠性。
    
    Args:
        domains_data: Phase 3+ 输出的 domains 字典
        output_path: 图表保存路径
        title: 图表标题
    """
    items = []
    for domain, d in domains_data.items():
        comp = d.get('comparison', {})
        reliability = d.get('reliability', {})
        
        node_count = d.get('node_count', 0)
        paper_count = d.get('paper_count', 0)
        drift = comp.get('drift', 0) if reliability.get('can_compare') else None
        
        items.append({
            'domain': domain,
            'node_count': node_count,
            'paper_count': paper_count,
            'drift': drift,
            'direction': comp.get('direction', ''),
            'can_compare': reliability.get('can_compare', False),
            'score': reliability.get('score', 0)
        })
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    for it in items:
        if it['can_compare'] and it['drift'] is not None:
            # 可比较：按漂移着色
            drift = it['drift']
            if drift > 0.4:
                color = COLOR_UNRELIABLE
            elif drift > 0.15:
                color = COLOR_GUARDED
            else:
                color = COLOR_RELIABLE
            size = 80 + it['score'] * 120
            marker = 'o'
            alpha = 0.8
        else:
            # 不可比较
            color = COLOR_NEUTRAL
            size = 50
            marker = 'x'
            alpha = 0.5
        
        if marker == 'x':
            ax.scatter(it['node_count'], it['paper_count'],
                       c=color, s=size, marker=marker, alpha=alpha, zorder=3)
        else:
            ax.scatter(it['node_count'], it['paper_count'],
                       c=color, s=size, marker=marker, alpha=alpha,
                       edgecolors='white', linewidth=0.5, zorder=3)
        
        # 简短标签
        label = it['domain'][:6]
        ax.annotate(label, (it['node_count'], it['paper_count']),
                    textcoords="offset points", xytext=(5, 5),
                    fontsize=7, color='#555', alpha=0.8)
    
    # 参考线
    max_val = max(max(it['node_count'] for it in items),
                  max(it['paper_count'] for it in items)) * 1.1
    ax.plot([0, max_val], [0, max_val], '--', color='#bdc3c7', alpha=0.5, linewidth=0.8)
    ax.axhline(y=10, color='#e74c3c', linestyle=':', alpha=0.3)
    ax.axvline(x=10, color='#e74c3c', linestyle=':', alpha=0.3)
    
    # 分区标注
    ax.text(3, 3, '数据不足区', fontsize=8, color='#e74c3c', alpha=0.6, ha='center')
    ax.text(max_val * 0.6, max_val * 0.6, '可靠区', fontsize=8, color='#2ecc71', alpha=0.6, ha='center')
    
    ax.set_xlabel('知识树节点数', fontsize=11)
    ax.set_ylabel('论文数', fontsize=11)
    ax.set_xlim(-2, max_val)
    ax.set_ylim(-2, max_val)
    
    if title:
        ax.set_title(title, fontsize=14, fontweight='bold', pad=15)
    
    # 图例
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor=COLOR_RELIABLE,
               markersize=10, label='漂移 < 0.15'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor=COLOR_GUARDED,
               markersize=10, label='漂移 0.15-0.40'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor=COLOR_UNRELIABLE,
               markersize=10, label='漂移 > 0.40'),
        Line2D([0], [0], marker='x', color='w', markerfacecolor=COLOR_NEUTRAL,
               markersize=10, label='不可比较'),
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=9, framealpha=0.9)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'  ✓ 样本量散点图: {output_path}')


# ============================================================
# 图表 4: 五行分布对比雷达图（多领域）
# ============================================================

def plot_wuxing_radar(domains_data, output_path, title=None, max_domains=8):
    """
    雷达图：前 N 个领域（按节点数排序）的节点 vs 论文五行分布。
    
    Args:
        domains_data: Phase 3+ 输出的 domains 字典
        output_path: 图表保存路径
        title: 图表标题
        max_domains: 最多展示的领域数
    """
    # 筛选可比较的领域，按节点数排序取前 N 个
    items = []
    for domain, d in domains_data.items():
        reliability = d.get('reliability', {})
        if not reliability.get('can_compare', False):
            continue
        if d.get('node_count', 0) == 0 and d.get('paper_count', 0) == 0:
            continue
        items.append({
            'domain': domain,
            'node_wx': d.get('node_wx', {}),
            'paper_wx': d.get('paper_wx', {}),
            'node_count': d.get('node_count', 0),
            'paper_count': d.get('paper_count', 0),
            'drift': d.get('comparison', {}).get('drift', 0)
        })
    
    items.sort(key=lambda x: x['node_count'] + x['paper_count'], reverse=True)
    items = items[:max_domains]
    
    if not items:
        print('  ⚠ 无可比较的领域，跳过雷达图')
        return
    
    wuxing_order = ['木', '火', '土', '金', '水']
    n_vars = len(wuxing_order)
    angles = np.linspace(0, 2 * np.pi, n_vars, endpoint=False).tolist()
    angles += angles[:1]  # 闭合
    
    cols = min(3, len(items))
    rows = math.ceil(len(items) / cols)
    
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 5, rows * 4.5),
                             subplot_kw=dict(polar=True))
    if rows * cols == 1:
        axes = np.array([axes])
    axes = axes.flatten()
    
    for idx, it in enumerate(items):
        ax = axes[idx]
        
        node_vals = [it['node_wx'].get(wx, 0) for wx in wuxing_order]
        node_vals += node_vals[:1]
        paper_vals = [it['paper_wx'].get(wx, 0) for wx in wuxing_order]
        paper_vals += paper_vals[:1]
        
        ax.fill(angles, node_vals, alpha=0.25, color='#3498db', label='知识树')
        ax.plot(angles, node_vals, 'o-', color='#3498db', linewidth=1.5, markersize=4)
        ax.fill(angles, paper_vals, alpha=0.25, color='#e74c3c', label='论文')
        ax.plot(angles, paper_vals, 'o-', color='#e74c3c', linewidth=1.5, markersize=4)
        
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(wuxing_order, fontsize=9)
        ax.set_ylim(0, 1)
        ax.set_yticks([0.25, 0.5, 0.75])
        ax.set_yticklabels(['25%', '50%', '75%'], fontsize=7, color='#999')
        
        short_name = it['domain'][:8]
        ax.set_title(f"{short_name}\ndrift={it['drift']:.2f}", fontsize=10, pad=10)
        
        if idx == 0:
            ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=8)
    
    # 隐藏多余的子图
    for idx in range(len(items), len(axes)):
        axes[idx].set_visible(False)
    
    if title:
        fig.suptitle(title, fontsize=14, fontweight='bold', y=1.02)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'  ✓ 五行雷达图: {output_path}')


# ============================================================
# 批量生成
# ============================================================

def generate_all_charts(phase3_output, output_dir, month_label=None):
    """
    从 Phase 3+ 输出批量生成所有图表。
    
    Args:
        phase3_output: Phase 3+ 的 dict 输出
        output_dir: 图表保存目录
        month_label: 月份标签
    
    Returns:
        生成的图表路径列表
    """
    domains = phase3_output.get('domains', {})
    if not domains:
        print('  ⚠ 无领域数据，跳过图表生成')
        return []
    
    os.makedirs(output_dir, exist_ok=True)
    prefix = f'{month_label}_' if month_label else ''
    
    timestamp = month_label or 'latest'
    title_prefix = f'AI知识图谱领域漂移分析 ({timestamp})'
    
    paths = []
    
    # 图表 1: 漂移柱状图
    path1 = os.path.join(output_dir, f'{prefix}drift_bars.png')
    plot_drift_bars(domains, path1, title=f'{title_prefix} — 漂移幅度')
    paths.append(path1)
    
    # 图表 2: 信度区间图
    path2 = os.path.join(output_dir, f'{prefix}drift_confidence.png')
    plot_drift_confidence(domains, path2, title=f'{title_prefix} — 信度区间')
    paths.append(path2)
    
    # 图表 3: 样本量散点图
    path3 = os.path.join(output_dir, f'{prefix}drift_scatter.png')
    plot_sample_scatter(domains, path3, title=f'{title_prefix} — 样本量分布')
    paths.append(path3)
    
    # 图表 4: 五行雷达图
    path4 = os.path.join(output_dir, f'{prefix}wuxing_radar.png')
    plot_wuxing_radar(domains, path4, title=f'{title_prefix} — 五行分布对比')
    paths.append(path4)
    
    return paths


# ============================================================
# 自检
# ============================================================

if __name__ == '__main__':
    print('=' * 60)
    print('漂移可视化模块 — 自检')
    print('=' * 60)
    
    # 加载真实数据
    base_dir = r'E:\00-TRAEWK\6a59e217b55e181ea97f0df3\wuxing_flowengine'
    phase3_path = os.path.join(base_dir, 'output', 'archive', '2026-07',
                                'phase3_plus_diagnosis_2026-07.json')
    
    if os.path.exists(phase3_path):
        with open(phase3_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        output_dir = os.path.join(base_dir, 'output', 'charts')
        paths = generate_all_charts(data, output_dir, month_label='2026-07')
        
        print(f'\n共生成 {len(paths)} 张图表:')
        for p in paths:
            print(f'  {p}')
    else:
        print(f'数据文件不存在: {phase3_path}')