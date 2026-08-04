"""
道境诊断 v2 — 五行诊断引擎

基于种子层/现行层/超越层三层结构，计算：
- dim1_freq: 五元频率分布及百分比
- dim2_layers: 层间五行分布
- dim3_edges: 相生相克路径（基于实际层间主导行）
- dim3_profile: 层间路径画像（主导行、路径串、画像匹配）
- dim4_entropy: 层间熵均衡度
- dim5_compass: 五行质心坐标
"""

import math
from collections import Counter

WX_ORDER = ['木', '火', '土', '金', '水']

# 相生对 (生成关系)
SHENG_PAIRS = [
    ('木', '火'), ('火', '土'), ('土', '金'), ('金', '水'), ('水', '木')
]
# 相克对 (克制关系)
KE_PAIRS = [
    ('木', '土'), ('土', '水'), ('水', '火'), ('火', '金'), ('金', '木')
]


def _count_layer_wx(concepts):
    """统计层内五行分布"""
    wc = Counter()
    for c in concepts:
        wx = c.get('wuxing', '土')
        wc[wx] += 1
    return wc


def _freq_distribution(all_nodes):
    """dim1: 全局五元频率分布"""
    wc = Counter()
    for n in all_nodes:
        wx = n.get('wuxing', '土')
        wc[wx] += 1
    total = len(all_nodes) or 1
    result = {}
    for wx in WX_ORDER:
        count = wc.get(wx, 0)
        result[wx] = {'count': count, 'pct': round(count / total, 4)}
    return result


def _entropy_balance(rings):
    """dim4: 层间熵均衡度"""
    layer_dists = []
    for ring in rings:
        concepts = ring.get('concepts', [])
        wc = _count_layer_wx(concepts)
        total = len(concepts) or 1
        dist = {wx: wc.get(wx, 0) / total for wx in WX_ORDER}
        layer_dists.append(dist)

    ratios = []
    for i in range(len(layer_dists) - 1):
        for wx in WX_ORDER:
            a = layer_dists[i][wx]
            b = layer_dists[i + 1][wx]
            if a + b > 0:
                ratios.append(2 * a * b / (a + b) if (a + b) > 0 else 0)

    if not ratios:
        return {'ratio': 0.0, 'details': []}

    avg_ratio = sum(ratios) / len(ratios)
    return {
        'ratio': round(avg_ratio, 4),
        'details': [round(r, 4) for r in ratios]
    }


def _compass_centroid(rings):
    """dim5: 五行质心坐标"""
    # 五元坐标映射 (角度制)
    angles = {
        '木': 0,    # 东
        '火': 72,   # 东南
        '土': 144,  # 中
        '金': 216,  # 西
        '水': 288   # 北
    }

    all_x, all_y, all_w = [], [], []
    for ring in rings:
        concepts = ring.get('concepts', [])
        wc = _count_layer_wx(concepts)
        for wx, count in wc.items():
            angle = math.radians(angles.get(wx, 0))
            all_x.append(math.cos(angle) * count)
            all_y.append(math.sin(angle) * count)
            all_w.append(count)

    total_w = sum(all_w) or 1
    cx = sum(all_x) / total_w
    cy = sum(all_y) / total_w
    return {
        'cx': round(cx, 4),
        'cy': round(cy, 4),
        'magnitude': round(math.sqrt(cx ** 2 + cy ** 2), 4)
    }


def _layer_dominant(ring):
    """获取层内主导行（频率最高者），空层返回 None"""
    concepts = ring.get('concepts', [])
    if not concepts:
        return None
    wc = _count_layer_wx(concepts)
    if not wc:
        return None
    return wc.most_common(1)[0][0]


def _edge_paths(rings):
    """dim3: 相生相克路径 — 基于实际层间主导行分析 (V1.2 §3.3)

    三层路径最多 2 条边：种子→现行, 现行→超越。
    统计每层主导行，逐对检查是否构成相生/相克关系。
    返回仅包含实际发生的路径（非全量 10 条）。
    """
    layer_order = ['种子层', '现行层', '超越层']
    ring_map = {r.get('label', ''): r for r in rings}

    edges = []
    for i in range(len(layer_order) - 1):
        src_label = layer_order[i]
        tgt_label = layer_order[i + 1]
        src_ring = ring_map.get(src_label)
        tgt_ring = ring_map.get(tgt_label)
        if src_ring is None or tgt_ring is None:
            continue

        src_wx = _layer_dominant(src_ring)
        tgt_wx = _layer_dominant(tgt_ring)
        if src_wx is None or tgt_wx is None:
            continue

        if (src_wx, tgt_wx) in SHENG_PAIRS:
            edges.append({
                'source': src_wx, 'target': tgt_wx,
                'type': '相生',
                'layer_transition': f'{src_label}→{tgt_label}',
                'count': 1
            })
        elif (src_wx, tgt_wx) in KE_PAIRS:
            edges.append({
                'source': src_wx, 'target': tgt_wx,
                'type': '相克',
                'layer_transition': f'{src_label}→{tgt_label}',
                'count': 1
            })

    return edges


def _path_profile(rings):
    """dim3_profile: 层间路径画像

    用于通阶段判定（路径匹配画像）和诊断报告展示。
    返回每层主导行、路径字符串、生克边计数、是否匹配画像。
    """
    layer_order = ['种子层', '现行层', '超越层']
    ring_map = {r.get('label', ''): r for r in rings}

    layer_dominants = {}
    for label in layer_order:
        ring = ring_map.get(label)
        if ring is None:
            layer_dominants[label] = '—'
        else:
            dom = _layer_dominant(ring)
            layer_dominants[label] = dom if dom else '—'

    path_str = '→'.join(layer_dominants.get(l, '—') for l in layer_order)

    edges = _edge_paths(rings)
    sheng_count = sum(1 for e in edges if e['type'] == '相生')
    ke_count = sum(1 for e in edges if e['type'] == '相克')

    # 画像匹配最小条件：至少一条相生边 + 无相克边（层间和谐贯通）
    matches_profile = (sheng_count >= 1 and ke_count == 0)

    return {
        'layer_dominants': layer_dominants,
        'path': path_str,
        'sheng_count': sheng_count,
        'ke_count': ke_count,
        'matches_profile': matches_profile
    }


def diagnose(rings, config=None):
    """
    主诊断函数

    Args:
        rings: [{'label': '种子层', 'concepts': [...]}, ...]
        config: 可选配置字典

    Returns:
        dict with dim1_freq, dim2_layers, dim3_edges, dim4_entropy, dim5_compass
    """
    if config is None:
        config = {}

    # 收集所有节点
    all_nodes = []
    for ring in rings:
        all_nodes.extend(ring.get('concepts', []))

    # dim1: 频率分布
    dim1 = _freq_distribution(all_nodes)

    # dim2: 层间分布
    dim2 = {}
    for ring in rings:
        label = ring.get('label', '')
        concepts = ring.get('concepts', [])
        wc = _count_layer_wx(concepts)
        dim2[label] = {
            'count': len(concepts),
            'wuxing': dict(wc)
        }

    # dim3: 相生相克路径
    dim3 = _edge_paths(rings)

    # dim4: 熵均衡度
    dim4 = _entropy_balance(rings)

    # dim5: 质心坐标
    dim5 = _compass_centroid(rings)

    return {
        'dim1_freq': dim1,
        'dim2_layers': dim2,
        'dim3_edges': dim3,
        'dim3_profile': _path_profile(rings),
        'dim4_entropy': dim4,
        'dim5_compass': dim5
    }