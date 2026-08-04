"""
时间序列分析 — 多月份趋势对比与可视化
"""

import json
import os
import math
from collections import Counter, defaultdict


def compare_months(archive_dirs):
    """比较多个月份的追踪指标"""
    timeline = []
    for month_label, dir_path in sorted(archive_dirs.items()):
        diag_path = os.path.join(dir_path, f'phase1_diagnosis_{month_label}.json')
        if not os.path.exists(diag_path):
            continue

        with open(diag_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        timeline.append({
            'month': month_label,
            'total_nodes': data.get('stats', {}).get('total', 0),
            'four_dims': data.get('four_dims', {}),
            'tracks': data.get('tracks', {}),
            'wuxing_dist': data.get('wuxing_dist', {})
        })

    return timeline


def compute_trends(timeline):
    """计算全月对比趋势，含逐月 delta 链"""
    if len(timeline) < 2:
        return {'status': 'insufficient_data', 'message': '需要至少两个月数据'}

    # 首尾对比 (最新 vs 最早)
    first = timeline[0]
    last = timeline[-1]
    overall = {}
    for dim in ['O_t', 'E_u', 'C_k', 'K_y']:
        first_val = first['four_dims'].get(dim, 0)
        last_val = last['four_dims'].get(dim, 0)
        delta = last_val - first_val
        overall[dim] = {
            'first': round(first_val, 4),
            'last': round(last_val, 4),
            'delta': round(delta, 4),
            'direction': '↑' if delta > 0 else '↓' if delta < 0 else '→'
        }

    # 逐月 delta 链
    chain = []
    for i in range(1, len(timeline)):
        prev = timeline[i - 1]
        curr = timeline[i]
        step = {'from': prev['month'], 'to': curr['month'], 'deltas': {}}
        for dim in ['O_t', 'E_u', 'C_k', 'K_y']:
            pv = prev['four_dims'].get(dim, 0)
            cv = curr['four_dims'].get(dim, 0)
            step['deltas'][dim] = round(cv - pv, 4)
        chain.append(step)

    return {
        'overall': overall,
        'chain': chain
    }


def run(base_dir, output_dir=None, month_label=None):
    """时间序列分析主流程"""
    if output_dir is None:
        output_dir = os.path.join(base_dir, 'output')

    archive_base = os.path.join(output_dir, 'archive')
    if not os.path.exists(archive_base):
        print(f'归档目录不存在: {archive_base}')
        return None

    archives = {}
    for item in sorted(os.listdir(archive_base)):
        item_path = os.path.join(archive_base, item)
        if os.path.isdir(item_path):
            archives[item] = item_path

    if not archives:
        print('没有找到归档数据')
        return None

    print(f'找到 {len(archives)} 个月份的归档数据: {list(archives.keys())}')

    timeline = compare_months(archives)
    trends = compute_trends(timeline)

    if month_label:
        archive_dir = os.path.join(archive_base, month_label)
        ts_path = os.path.join(archive_dir, f'phase3_timeseries_diagnosis_{month_label}.json')
    else:
        ts_path = os.path.join(output_dir, 'timeseries_diagnosis.json')

    output = {
        'timeline': timeline,
        'trends': trends or {},
        'months_analyzed': len(timeline)
    }

    with open(ts_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f'\n时间序列分析完成: {ts_path}')
    if trends and 'overall' in trends:
        print('\n首尾趋势:')
        for dim, t in trends['overall'].items():
            print(f'  {dim}: {t["first"]:.4f} → {t["last"]:.4f} ({t["direction"]}{abs(t["delta"]):.4f})')
        if trends.get('chain'):
            print('\n逐月 delta 链:')
            for step in trends['chain']:
                parts = ', '.join(
                    f'{dim}: {v:+.4f}' for dim, v in step['deltas'].items()
                )
                print(f'  {step["from"]} → {step["to"]}: {parts}')

    return output


if __name__ == '__main__':
    DEFAULT_BASE = r'C:\Users\hejij\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a59e217b55e181ea97f0df3\wuxing_flowengine'
    run(DEFAULT_BASE)