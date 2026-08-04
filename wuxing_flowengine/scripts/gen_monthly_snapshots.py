"""
生成各月度独立快照，模拟知识图谱月度演化
基于 2026-07-30 真实快照，按月份回溯/推进生成变体
"""
import json
import copy
import os
import random
from collections import Counter

BASE_PATH = r'C:\Users\hejij\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a59e217b55e181ea97f0df3\wuxing_flowengine\data\snapshots\2026-07-30_snapshot.json'
SNAP_DIR = os.path.dirname(BASE_PATH)

# 月度演化参数 (基于 2026-07 为基准)
# 模拟 05→06→07→08 的渐进演化
MONTHLY_CONFIG = {
    '2026-05': {
        'collect_time': '2026-05-31T23:00:00+08:00',
        'node_removal_pct': 0.08,      # 移除 8% 节点
        'edge_removal_pct': 0.10,       # 移除 10% 边
        'wuxing_shift': {               # 五行分布偏移
            '木': 1.12,  # 早期木更旺盛（具身/生成方向）
            '火': 0.92,
            '土': 0.95,
            '金': 0.88,  # 安全/伦理方向早期较少
            '水': 0.90,  # LLM 方向早期略少
        },
        'depth_demote': 0.12,  # 12% 的 L3 降为 L2
    },
    '2026-06': {
        'collect_time': '2026-06-30T23:00:00+08:00',
        'node_removal_pct': 0.04,
        'edge_removal_pct': 0.05,
        'wuxing_shift': {
            '木': 1.06,
            '火': 0.96,
            '土': 0.98,
            '金': 0.94,
            '水': 0.95,
        },
        'depth_demote': 0.06,
    },
    '2026-07': {
        'collect_time': '2026-07-30T13:50:00+08:00',
        'node_removal_pct': 0.0,   # 基准快照，不做修改
        'edge_removal_pct': 0.0,
        'wuxing_shift': {'木': 1.0, '火': 1.0, '土': 1.0, '金': 1.0, '水': 1.0},
        'depth_demote': 0.0,
    },
    '2026-08': {
        'collect_time': '2026-08-01T00:00:00+08:00',
        'node_removal_pct': -0.03,  # 负值表示新增节点
        'edge_removal_pct': -0.04,
        'wuxing_shift': {
            '木': 0.97,
            '火': 1.02,
            '土': 1.01,
            '金': 1.04,  # 安全/伦理方向持续增长
            '水': 1.03,  # LLM 方向持续增长
        },
        'depth_demote': -0.04,  # 负值表示 L2→L3 提升
    },
}

WX_ORDER = ['木', '火', '土', '金', '水']


def generate_snapshot(base_snapshot, month_label, config):
    """生成指定月份的独立快照"""
    snap = copy.deepcopy(base_snapshot)
    nodes = snap['nodes']
    edges = snap.get('edges', [])

    seed = sum(ord(c) for c in month_label)  # 确定性种子
    rng = random.Random(seed)

    # 1. 更新采集时间
    snap['collect_time'] = config['collect_time']

    # 2. 移除/新增节点 (基于 ID 哈希确定性选择)
    node_ids = [n['id'] for n in nodes]
    removal_count = int(len(nodes) * abs(config['node_removal_pct']))
    if config['node_removal_pct'] > 0:
        # 移除节点
        rng.shuffle(node_ids)
        remove_ids = set(node_ids[:removal_count])
        nodes[:] = [n for n in nodes if n['id'] not in remove_ids]
        edges[:] = [e for e in edges
                    if e['source_id'] not in remove_ids
                    and e['target_id'] not in remove_ids]
    elif config['node_removal_pct'] < 0:
        # 新增节点：复制已有节点稍作修改
        new_nodes = []
        for i in range(removal_count):
            src = nodes[rng.randint(0, len(nodes) - 1)]
            new = copy.deepcopy(src)
            new_id = f'node_{len(nodes) + len(new_nodes) + 1:04d}'
            new['id'] = new_id
            new['name'] = src['name'] + ' (新)'
            new_nodes.append(new)
        nodes.extend(new_nodes)

    # 3. 移除/新增边
    edge_removal = int(len(edges) * abs(config['edge_removal_pct']))
    if config['edge_removal_pct'] > 0:
        rng.shuffle(edges)
        edges[:] = edges[edge_removal:]
    elif config['edge_removal_pct'] < 0:
        # 新增边
        valid_ids = [n['id'] for n in nodes]
        for _ in range(edge_removal):
            src = rng.choice(valid_ids)
            tgt = rng.choice(valid_ids)
            if src != tgt:
                edges.append({'source_id': src, 'target_id': tgt, 'relation': 'related_to'})

    # 4. 五元分布偏移
    for wx in WX_ORDER:
        factor = config['wuxing_shift'].get(wx, 1.0)
        if abs(factor - 1.0) < 0.001:
            continue
        # 找到目标五元节点和目标外节点
        target_nodes = [n for n in nodes if n.get('wuxing') == wx]
        other_nodes = [n for n in nodes if n.get('wuxing') != wx]
        if not target_nodes or not other_nodes:
            continue
        shift_count = int(len(target_nodes) * abs(factor - 1.0))
        if factor > 1.0:
            # 从其他五元转换到目标五元
            for _ in range(min(shift_count, len(other_nodes))):
                idx = rng.randint(0, len(other_nodes) - 1)
                other_nodes[idx]['wuxing'] = wx
        elif factor < 1.0:
            # 从目标五元转换到其他五元
            for _ in range(min(shift_count, len(target_nodes))):
                idx = rng.randint(0, len(target_nodes) - 1)
                new_wx = rng.choice([w for w in WX_ORDER if w != wx])
                target_nodes[idx]['wuxing'] = new_wx

    # 5. 认知深度偏移 (模拟知识深化)
    depth_demote = config['depth_demote']
    if depth_demote > 0:
        # L3 → L2 降级
        l3_nodes = [n for n in nodes if n.get('cognitive_depth') == 'L3']
        demote_count = int(len(l3_nodes) * depth_demote)
        rng.shuffle(l3_nodes)
        for n in l3_nodes[:demote_count]:
            n['cognitive_depth'] = 'L2'
    elif depth_demote < 0:
        # L2 → L3 提升
        l2_nodes = [n for n in nodes if n.get('cognitive_depth') == 'L2']
        promote_count = int(len(l2_nodes) * abs(depth_demote))
        rng.shuffle(l2_nodes)
        for n in l2_nodes[:promote_count]:
            n['cognitive_depth'] = 'L3'

    return snap


def main():
    with open(BASE_PATH, 'r', encoding='utf-8') as f:
        base = json.load(f)

    for month in ['2026-05', '2026-06', '2026-07', '2026-08']:
        cfg = MONTHLY_CONFIG[month]
        snap = generate_snapshot(base, month, cfg)

        out_path = os.path.join(SNAP_DIR, f'{month}-30_snapshot.json')
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(snap, f, ensure_ascii=False, indent=2)

        nodes = snap['nodes']
        edges = snap.get('edges', [])
        wc = Counter(n.get('wuxing', '?') for n in nodes)
        dc = Counter(n.get('cognitive_depth', '?') for n in nodes)

        print(f'{month}: {len(nodes)} nodes, {len(edges)} edges')
        print(f'  Wuxing: {dict(sorted(wc.items()))}')
        print(f'  Depth: {dict(sorted(dc.items()))}')
        print()

    print('Done. Files created:')
    for f in sorted(os.listdir(SNAP_DIR)):
        if f.endswith('_snapshot.json'):
            print(f'  {f}')


if __name__ == '__main__':
    main()