"""
阶段判定引擎 — 生克化通变五阶段判定 (V1.2 Ch4)

基于 wuxing_diagnose_v2 的七维输出，判定当前所处的道境阶段。
支持两种诊断模式：
  - static (静态): 单次快照判定 (生/克/化/通)
  - dynamic (动态): 多次快照判定 (含ΔH陡降 + 重心位移 + 深度突变)

用法:
    from stage_engine import determine_stage, compute_theta_critical
    stage, reason = determine_stage(wuxing_result, S, config, mode='static')
"""

import math
import json
import os

WX_ORDER = ['木', '火', '土', '金', '水']
DEPTH_LEVELS = {'L1': 0, 'L2': 1, 'L3': 2, 'L4': 3}


def compute_entropy(freq):
    """
    从 dim1_freq 计算原始熵 H 和 H/H_max

    Args:
        freq: dim1_freq, {wx: {'count': n, 'pct': 0.xxxx}, ...}

    Returns:
        (H, H_max, H_ratio)
    """
    H = 0.0
    for wx in WX_ORDER:
        p = freq.get(wx, {}).get('pct', 0)
        if p > 0:
            H -= p * math.log2(p)
    H_max = math.log2(5)  # ≈ 2.322
    H_ratio = H / H_max if H_max > 0 else 0
    return H, H_max, H_ratio


def dominant_depth(depth_profile):
    """
    从 dim2_layers 推断主导认知深度

    Args:
        depth_profile: dim2_layers, {'种子层': {'count': n}, '现行层': {...}, '超越层': {...}}

    Returns:
        'L1' | 'L2' | 'L3' | 'L4' | 'L2' (default)
    """
    seed_count = depth_profile.get('种子层', {}).get('count', 0)
    curr_count = depth_profile.get('现行层', {}).get('count', 0)
    tran_count = depth_profile.get('超越层', {}).get('count', 0)

    max_layer = max(seed_count, curr_count, tran_count)
    if max_layer == 0:
        return 'L2'

    if seed_count == max_layer and seed_count > 0:
        return 'L1'
    elif curr_count == max_layer:
        return 'L2'
    else:
        # 超越层主导: 根据 L3/L4 比例判定
        return 'L3'  # 默认 L3，L4 需额外标记


def compute_theta_critical(depth_profile, config=None):
    """
    计算临界阈值 θ_critical (V1.2 Ch4.5)

    θ_critical = θ_base × f(认知深度) × g(案例类型)

    Args:
        depth_profile: dim2_layers
        config: 配置字典 (含 theta_critical 字段)

    Returns:
        float: 临界阈值
    """
    theta_base = 60
    depth_mult = {'L1': 1.0, 'L2': 1.5, 'L3': 2.0, 'L4': 3.0}
    case_mult = {'smooth': 1.0, 'adverse': 0.6}

    if config and 'theta_critical' in config:
        tc = config['theta_critical']
        if isinstance(tc, dict):
            theta_base = tc.get('base', theta_base)
            if 'depth_multiplier' in tc:
                depth_mult.update(tc['depth_multiplier'])
            if 'case_type_multiplier' in tc:
                case_mult.update(tc['case_type_multiplier'])

    depth = dominant_depth(depth_profile)
    case_type = config.get('case_type', 'smooth') if config else 'smooth'

    return theta_base * depth_mult.get(depth, 1.5) * case_mult.get(case_type, 1.0)


def centroid_displacement(prev_compass, curr_compass):
    """
    计算两次快照间的重心位移 (V1.2 Ch4.2.2)

    Args:
        prev_compass: dim5_compass 或 {'cx': x, 'cy': y}
        curr_compass: dim5_compass 或 {'cx': x, 'cy': y}

    Returns:
        float: 欧几里得距离
    """
    cx1 = prev_compass.get('cx', 0)
    cy1 = prev_compass.get('cy', 0)
    cx2 = curr_compass.get('cx', 0)
    cy2 = curr_compass.get('cy', 0)
    return math.sqrt((cx2 - cx1) ** 2 + (cy2 - cy1) ** 2)


def determine_stage(wuxing_result, S, config=None, mode='static'):
    """
    判定生克化通变阶段 (V1.2 Ch4.2)

    Args:
        wuxing_result: wuxing_diagnose_v2.diagnose() 输出
        S: 存在度 (O_t × E_u × C_k × K_y × 100)
        config: 配置字典
        mode: 'static' | 'dynamic'

    Returns:
        (stage: str, details: dict)
    """
    if config is None:
        config = {}

    W = wuxing_result['dim1_freq']
    layers = wuxing_result['dim2_layers']
    path_edges = wuxing_result['dim3_edges']
    _, H_max, H_ratio = compute_entropy(W)
    compass = wuxing_result['dim5_compass']

    theta = compute_theta_critical(layers, config)

    # ── 生: 单极主导 + 低熵聚焦 ──
    for wx in WX_ORDER:
        pct = W.get(wx, {}).get('pct', 0) * 100
        if pct > 30 and H_ratio < 0.50:
            return '生', {
                'reason': f'单极主导·积累期 ({wx}: {pct:.1f}%)',
                'dominant': wx,
                'H_ratio': round(H_ratio, 4),
                'trigger': f'pct({wx})={pct:.1f}% > 30% AND H/H_max={H_ratio:.4f} < 0.50'
            }

    # ── 克: 路径中有相克边 ──
    ke_edges = [e for e in path_edges if e.get('type') == '相克']
    ke_count = len(ke_edges)
    if ke_count >= 1:
        ke_details = [f"{e['source']}→{e['target']}" for e in ke_edges]
        return '克', {
            'reason': f'层间冲突 (路径含{ke_count}条相克边)',
            'ke_count': ke_count,
            'ke_pairs': ke_details,
            'trigger': f'ke_edge_count={ke_count} >= 1'
        }

    if mode == 'dynamic':
        # ── 动态模式: 化 (ΔH陡降 + 重心突变) ──
        prev = config.get('_previous_snapshot', {})
        if prev:
            prev_H = compute_entropy(prev.get('dim1_freq', {}))[0]
            curr_H, _, _ = compute_entropy(W)
            delta_H = prev_H - curr_H  # 正=熵下降
            prev_compass = prev.get('dim5_compass', {})
            c_disp = centroid_displacement(prev_compass, compass)

            if delta_H > 0.3 and c_disp > 0.3:
                return '化', {
                    'reason': '四维同时跃迁',
                    'delta_H': round(delta_H, 4),
                    'centroid_disp': round(c_disp, 4),
                    'trigger': f'ΔH={delta_H:.4f} > 0.3 AND centroid_disp={c_disp:.4f} > 0.3'
                }

            # ── 动态模式: 变 (深度范式转换) ──
            prev_depth = prev.get('_dominant_depth', '')
            curr_depth = dominant_depth(layers)
            depth_shift = DEPTH_LEVELS.get(curr_depth, 1) - DEPTH_LEVELS.get(prev_depth, 1)
            if depth_shift >= 1:
                return '变', {
                    'reason': f'深度范式转换: {prev_depth}→{curr_depth}',
                    'prev_depth': prev_depth,
                    'curr_depth': curr_depth,
                    'depth_shift': depth_shift,
                    'trigger': f'depth_shift={depth_shift} >= 1'
                }

        # ── 动态模式: 通 (路径匹配画像 + 熵适中) ──
        path_profile = wuxing_result.get('dim3_profile', {})
        if path_profile.get('matches_profile', False) and 0.50 < H_ratio < 0.85:
            return '通', {
                'reason': '路径匹配画像·时空直觉迁移',
                'H_ratio': round(H_ratio, 4),
                'path': path_profile.get('path', ''),
                'trigger': f'matches_profile=True AND 0.50 < H/H_max={H_ratio:.4f} < 0.85'
            }

    else:
        # ── 静态模式: 化 (S 跨越临界阈值) ──
        if S > theta:
            return '化', {
                'reason': f'存在度跨越临界阈值',
                'S': round(S, 1),
                'theta': round(theta, 1),
                'trigger': f'S={S:.1f} > θ_critical={theta:.1f}'
            }

        # ── 静态模式: 通 (路径匹配画像 + 熵适中) ──
        path_profile = wuxing_result.get('dim3_profile', {})
        if path_profile.get('matches_profile', False) and 0.50 < H_ratio < 0.85:
            return '通', {
                'reason': '路径匹配画像·时空直觉迁移',
                'H_ratio': round(H_ratio, 4),
                'path': path_profile.get('path', ''),
                'trigger': f'matches_profile=True AND 0.50 < H/H_max={H_ratio:.4f} < 0.85'
            }

    # ── 默认: 回归积累 (生) ──
    return '生', {
        'reason': '未满足其他阶段条件，回归积累',
        'H_ratio': round(H_ratio, 4),
        'trigger': 'default fallback'
    }


def detect_nested_stage(wuxing_result, global_stage):
    """
    检测全局阶段内部的嵌套螺旋 (V1.2 Ch4.4)

    对每个阶段，分析其内部五阶段的子状态。
    返回简化的嵌套状态描述。

    Args:
        wuxing_result: 诊断结果
        global_stage: 全局阶段 ('生'|'克'|'化'|'通'|'变')

    Returns:
        list of nested sub-stage descriptions
    """
    W = wuxing_result['dim1_freq']
    _, H_max, H_ratio = compute_entropy(W)
    path_edges = wuxing_result['dim3_edges']
    layers = wuxing_result['dim2_layers']

    nested = []

    # 检查内部是否有生的萌芽 (层内主导行)
    for layer_name in ['种子层', '现行层', '超越层']:
        layer_wx = layers.get(layer_name, {}).get('wuxing', {})
        if layer_wx:
            dominant = max(layer_wx, key=layer_wx.get)
            nested.append({
                'layer': layer_name,
                'sub_stage': '生的萌芽',
                'dominant_wx': dominant,
                'detail': f'{layer_name}主导行: {dominant}'
            })

    # 检查克的活动 (相克路径数)
    ke_edges = [e for e in path_edges if e.get('type') == '相克']
    if ke_edges:
        nested.append({
            'sub_stage': '克的启动',
            'ke_count': len(ke_edges),
            'detail': f'路径含{len(ke_edges)}条相克边'
        })

    # 检查化的微光 (熵是否在临界附近)
    if 0.40 < H_ratio < 0.55:
        nested.append({
            'sub_stage': '化的微光',
            'H_ratio': round(H_ratio, 4),
            'detail': f'熵在转化临界附近 (H/H_max={H_ratio:.4f})'
        })

    return nested


def load_config(base_dir):
    """加载配置文件"""
    config_path = os.path.join(base_dir, 'config', 'config_default.json')
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            raw = json.load(f)
        # 展平配置
        config = {}
        for k, v in raw.items():
            if k.startswith('_'):
                continue
            if isinstance(v, dict) and 'pct' in v:
                continue
            config[k] = v
        return config
    return {}


if __name__ == '__main__':
    # 独立测试
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from diagnose.wuxing_diagnose_v2 import diagnose

    # 模拟数据
    rings = [
        {'label': '种子层', 'concepts': [
            {'name': 'n1', 'wuxing': '土'},
            {'name': 'n2', 'wuxing': '金'},
        ]},
        {'label': '现行层', 'concepts': [
            {'name': 'n3', 'wuxing': '木'},
            {'name': 'n4', 'wuxing': '水'},
            {'name': 'n5', 'wuxing': '火'},
        ]},
        {'label': '超越层', 'concepts': [
            {'name': 'n6', 'wuxing': '水'},
            {'name': 'n7', 'wuxing': '木'},
        ]}
    ]
    result = diagnose(rings)
    stage, details = determine_stage(result, S=25.0, mode='static')
    print(f'Stage: {stage}')
    print(f'Details: {details}')
    nested = detect_nested_stage(result, stage)
    print(f'Nested: {nested}')