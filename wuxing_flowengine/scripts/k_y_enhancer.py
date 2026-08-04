"""
K_y 缘位增强器 — Phase 4 图密度增强 (V1.2 融合设计方案)

增强要点:
  1. E_relation 不再仅依赖 ke_count/2 (总是 2.5)，而是结合图密度
  2. 引入 ke_sheng_ratio: 相克边/相生边的比例，反映实际冲突程度
  3. 混合公式: E_relation = β × ke_density + (1-β) × graph_cohesion
  4. 归一化到 [0, 1] 区间，避免 K_y 总是被 E_relation 主导

用法:
    from k_y_enhancer import enhance_K_y, compute_E_relation
    K_y_enhanced = enhance_K_y(w_fire, w_earth, edge_quality, path_edges, nodes)
"""

import math


def compute_E_relation(edge_quality, path_edges, nodes=None):
    """
    Phase 4 增强 E_relation 计算

    增强策略:
    - ke_density: 基于实际相克边密度的冲突度量
    - graph_cohesion: 基于图连接密度的结构度量
    - 混合: 根据克/生边比例自适应加权

    Args:
        edge_quality: dict with edge_count, node_count, graph_density_ratio, avg_degree, max_degree
        path_edges: dim3_edges from wuxing_diagnose_v2
        nodes: optional, list of nodes for advanced computation

    Returns:
        dict: {E_relation, ke_density, graph_cohesion, ke_sheng_ratio, mode}
    """
    # 基础数据
    edge_count = edge_quality.get('edge_count', 0)
    node_count = edge_quality.get('node_count', 1)
    graph_density_ratio = edge_quality.get('graph_density_ratio', 0.0)
    avg_degree = edge_quality.get('avg_degree', 0.0)

    # 从 path_edges 提取实际克/生边统计
    ke_count = sum(1 for p in path_edges if p.get('type') == '相克')
    sheng_count = sum(1 for p in path_edges if p.get('type') == '相生')

    # ── 1. ke_density: 归一化的相克边密度 ──
    # 原始 ke_count/2 总是 2.5（5条相克路径），改为基于实际图密度
    # ke_density = (ke_count / max_possible_ke) * (edge_count / node_count)
    max_possible_ke = 5  # 5条基本相克路径
    ke_density_raw = ke_count / max_possible_ke if max_possible_ke > 0 else 0

    # 用边密度缩放: 边越多，克关系越显著
    edge_density = edge_count / max(node_count, 1)
    ke_density = min(1.0, ke_density_raw * edge_density * 0.5)

    # ── 2. graph_cohesion: 图结构内聚度 ──
    # graph_density_ratio = avg_degree / max_degree
    graph_cohesion = graph_density_ratio

    # ── 3. ke_sheng_ratio: 克/生比例 ──
    # 反映实际冲突程度 vs 和谐程度
    if sheng_count > 0:
        ke_sheng_ratio = ke_count / (ke_count + sheng_count)
    else:
        ke_sheng_ratio = 1.0 if ke_count > 0 else 0.5

    # ── 4. 自适应混合权重 β ──
    # β 由克/生比例决定: 克越多，越依赖 ke_density
    beta = ke_sheng_ratio

    # ── 5. 混合 E_relation ──
    E_relation = beta * ke_density + (1 - beta) * graph_cohesion

    # 确定模式
    if ke_count > 0 and sheng_count > 0:
        mode = 'hybrid'
    elif ke_count > 0:
        mode = 'ke_dominant'
    else:
        mode = 'graph_cohesion'

    return {
        'E_relation': round(E_relation, 4),
        'ke_density': round(ke_density, 4),
        'graph_cohesion': round(graph_cohesion, 4),
        'ke_sheng_ratio': round(ke_sheng_ratio, 4),
        'beta': round(beta, 4),
        'mode': mode,
        'ke_count': ke_count,
        'sheng_count': sheng_count
    }


def enhance_K_y(w_fire, w_earth, edge_quality, path_edges, nodes=None):
    """
    增强 K_y 计算 (Phase 4)

    K_y = w_火 × 0.4 + w_土 × 0.3 + E_relation × 0.3

    Args:
        w_fire: 火行占比 (0~1)
        w_earth: 土行占比 (0~1)
        edge_quality: 边质量数据
        path_edges: dim3_edges
        nodes: optional, nodes list

    Returns:
        dict: {K_y, E_relation, components, ...}
    """
    E_rel = compute_E_relation(edge_quality, path_edges, nodes)

    K_y_raw = w_fire * 0.4 + w_earth * 0.3 + E_rel['E_relation'] * 0.3
    K_y = max(0, min(1, K_y_raw))

    return {
        'K_y': round(K_y, 4),
        'K_y_raw': round(K_y_raw, 4),
        'E_relation': E_rel,
        'components': {
            'w_fire_term': round(w_fire * 0.4, 4),
            'w_earth_term': round(w_earth * 0.3, 4),
            'E_relation_term': round(E_rel['E_relation'] * 0.3, 4)
        }
    }


def enhance_four_dims(four_dims, edge_quality, path_edges, wuxing_freq, nodes=None):
    """
    增强四维读数 (替换 K_y 为 Phase 4 增强版)

    Args:
        four_dims: 原始四维 {'O_t': ..., 'E_u': ..., 'C_k': ..., 'K_y': ...}
        edge_quality: 边质量数据
        path_edges: dim3_edges
        wuxing_freq: dim1_freq
        nodes: optional

    Returns:
        dict: 增强后的四维 + 元数据
    """
    w_fire = wuxing_freq.get('火', {}).get('pct', 0)
    w_earth = wuxing_freq.get('土', {}).get('pct', 0)

    enhanced = enhance_K_y(w_fire, w_earth, edge_quality, path_edges, nodes)

    return {
        'O_t': four_dims.get('O_t', 0),
        'E_u': four_dims.get('E_u', 0),
        'C_k': four_dims.get('C_k', 0),
        'K_y_original': four_dims.get('K_y', 0),
        'K_y_enhanced': enhanced['K_y'],
        'K_y_enhancement': enhanced,
        'S_original': round(
            four_dims.get('O_t', 0) * four_dims.get('E_u', 0) *
            four_dims.get('C_k', 0) * four_dims.get('K_y', 0) * 100, 1
        ),
        'S_enhanced': round(
            four_dims.get('O_t', 0) * four_dims.get('E_u', 0) *
            four_dims.get('C_k', 0) * enhanced['K_y'] * 100, 1
        )
    }


def compare_ky_methods(phase1_result):
    """
    对比原始 K_y 和 Phase 4 增强 K_y

    Args:
        phase1_result: Phase 1 诊断结果

    Returns:
        dict: comparison results
    """
    four_dims = phase1_result.get('four_dims', {})
    edge_quality = phase1_result.get('edge_quality', {})
    diagnosis = phase1_result.get('diagnosis', {})

    # 从 rings 中提取频率
    rings = diagnosis.get('rings', [])
    wuxing_freq = {}
    all_concepts = []
    for ring in rings:
        all_concepts.extend(ring.get('concepts', []))

    from collections import Counter
    wc = Counter()
    for c in all_concepts:
        wc[c.get('wuxing', '土')] += 1
    total = len(all_concepts) or 1
    for wx in ['木', '火', '土', '金', '水']:
        wuxing_freq[wx] = {'pct': wc.get(wx, 0) / total}

    # 获取 path_edges
    path_edges = []
    from diagnose.wuxing_diagnose_v2 import _edge_paths
    path_edges = _edge_paths(rings)

    enhanced = enhance_four_dims(four_dims, edge_quality, path_edges, wuxing_freq)

    return {
        'original': {
            'K_y': four_dims.get('K_y', 0),
            'S': round(four_dims.get('O_t', 0) * four_dims.get('E_u', 0) *
                       four_dims.get('C_k', 0) * four_dims.get('K_y', 0) * 100, 1)
        },
        'enhanced': {
            'K_y': enhanced['K_y_enhanced'],
            'S': enhanced['S_enhanced']
        },
        'delta_K_y': round(enhanced['K_y_enhanced'] - four_dims.get('K_y', 0), 4),
        'delta_S': round(enhanced['S_enhanced'] - enhanced['S_original'], 1),
        'E_relation_detail': enhanced['K_y_enhancement']['E_relation']
    }


if __name__ == '__main__':
    import json
    import os
    import sys

    BASE = r'C:\Users\hejij\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a59e217b55e181ea97f0df3\wuxing_flowengine'
    sys.path.insert(0, BASE)
    sys.path.insert(0, os.path.join(BASE, 'diagnose'))

    phase1_path = os.path.join(BASE, 'output', 'archive', '2026-08', 'phase1_diagnosis_2026-08.json')
    with open(phase1_path, 'r', encoding='utf-8') as f:
        phase1 = json.load(f)

    comparison = compare_ky_methods(phase1)
    print('=' * 60)
    print('K_y 增强对比 (Phase 4)')
    print('=' * 60)
    print(f'  原始 K_y: {comparison["original"]["K_y"]:.4f} → S: {comparison["original"]["S"]:.1f}')
    print(f'  增强 K_y: {comparison["enhanced"]["K_y"]:.4f} → S: {comparison["enhanced"]["S"]:.1f}')
    print(f'  ΔK_y: {comparison["delta_K_y"]:+.4f}  ΔS: {comparison["delta_S"]:+.1f}')
    print(f'  E_relation 模式: {comparison["E_relation_detail"]["mode"]}')
    print(f'  ke_density: {comparison["E_relation_detail"]["ke_density"]:.4f}')
    print(f'  graph_cohesion: {comparison["E_relation_detail"]["graph_cohesion"]:.4f}')
    print(f'  ke_sheng_ratio: {comparison["E_relation_detail"]["ke_sheng_ratio"]:.4f}')
    print(f'  beta: {comparison["E_relation_detail"]["beta"]:.4f}')