"""
边生成器 — 基于五行生克关系生成概念边
"""

import json
import os
from collections import Counter

# 相生关系
SHENG = {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'}
# 相克关系
KE = {'木': '土', '土': '水', '水': '火', '火': '金', '金': '木'}


def generate_edges(nodes, edge_type='sheng'):
    """基于节点五行生成边"""
    edges = []
    wx_map = {n.get('id', ''): n.get('wuxing', '土') for n in nodes}

    node_ids = list(wx_map.keys())
    pair_map = SHENG if edge_type == 'sheng' else KE
    edge_label = '相生' if edge_type == 'sheng' else '相克'

    for i, sid in enumerate(node_ids):
        src_wx = wx_map.get(sid, '土')
        target_wx = pair_map.get(src_wx, '土')

        for j, tid in enumerate(node_ids[i + 1:], i + 1):
            if wx_map.get(tid, '土') == target_wx:
                edges.append({
                    'source_id': sid,
                    'target_id': tid,
                    'type': edge_label,
                    'source_wx': src_wx,
                    'target_wx': target_wx
                })
                break

    return edges


def run(base_dir, nodes_path=None, output_dir=None, month_label=None):
    """边生成器主流程"""
    if output_dir is None:
        output_dir = os.path.join(base_dir, 'output')

    if month_label:
        archive_dir = os.path.join(output_dir, 'archive', month_label)
    else:
        archive_dir = output_dir

    if nodes_path is None:
        nodes_path = os.path.join(archive_dir, f'wuxing_classification_{month_label}.json')

    with open(nodes_path, 'r', encoding='utf-8') as f:
        nodes = json.load(f)

    sheng_edges = generate_edges(nodes, 'sheng')
    ke_edges = generate_edges(nodes, 'ke')
    all_edges = sheng_edges + ke_edges

    print(f'生成 {len(sheng_edges)} 条相生边, {len(ke_edges)} 条相克边, 共 {len(all_edges)} 条')

    return all_edges


if __name__ == '__main__':
    DEFAULT_BASE = r'C:\Users\hejij\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a59e217b55e181ea97f0df3\wuxing_flowengine'
    run(DEFAULT_BASE)