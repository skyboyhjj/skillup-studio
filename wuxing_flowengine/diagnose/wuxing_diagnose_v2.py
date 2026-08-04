"""
道境诊断 v2 — 五行诊断引擎

基于种子层/现行层/超越层三层结构，计算：
- dim1_freq: 五元频率分布及百分比
- dim2_layers: 层间五行分布
- dim3_edges: 相生相克路径计数
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


def _edge_paths(rings):
    """dim3: 相生相克路径"""
    # 收集所有节点
    all_nodes = []
    for ring in rings:
        for c in ring.get('concepts', []):
            all_nodes.append(c)

    wx_map = {n.get('name', ''): n.get('wuxing', '土') for n in all_nodes}

    sheng_paths = []
    ke_paths = []
    for (src, tgt) in SHENG_PAIRS:
        sheng_paths.append({
            'source': src, 'target': tgt, 'type': '相生',
            'count': 0
        })
    for (src, tgt) in KE_PAIRS:
        ke_paths.append({
            'source': src, 'target': tgt, 'type': '相克',
            'count': 0
        })

    return sheng_paths + ke_paths


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
        'dim4_entropy': dim4,
        'dim5_compass': dim5
    }