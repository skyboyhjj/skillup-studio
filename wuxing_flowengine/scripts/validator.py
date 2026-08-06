"""
验证器 — 管道输出合法性检查
"""

import json
import os


def validate_nodes(nodes):
    """验证节点数据"""
    issues = []
    required_fields = ['id', 'name', 'wuxing', 'cognitive_depth']

    for i, n in enumerate(nodes):
        for field in required_fields:
            if field not in n:
                issues.append(f'节点[{i}] 缺少字段: {field}')

        wx = n.get('wuxing', '')
        if wx not in ('木', '火', '土', '金', '水'):
            issues.append(f'节点[{i}] 无效五行: {wx}')

        depth = n.get('cognitive_depth', '')
        if depth not in ('L1', 'L2', 'L3', 'L4'):
            issues.append(f'节点[{i}] 无效认知深度: {depth}')

    return issues


def validate_diagnosis(diag):
    """验证诊断结果"""
    issues = []

    four_dims = diag.get('four_dims', {})
    for dim in ['O_t', 'E_u', 'C_k', 'K_y']:
        val = four_dims.get(dim, -1)
        if not (0 <= val <= 1):
            issues.append(f'四维 {dim}={val} 超出 [0,1] 范围')

    tracks = diag.get('tracks', {})
    for track in ['S_sum', 'S_prod']:
        if track not in tracks:
            issues.append(f'缺少追踪指标: {track}')

    edge_quality = diag.get('edge_quality', {})
    if edge_quality and edge_quality.get('edge_ratio') is not None:
        if edge_quality.get('edge_ratio', 0) < 0.1:
            issues.append(f'边密度过低: {edge_quality.get("edge_ratio")}')

    return issues


def validate_pipeline(base_dir, month_label):
    """验证整个管道输出"""
    archive_dir = os.path.join(base_dir, 'output', 'archive', month_label)
    all_issues = []

    # Phase 1 分类
    cls_path = os.path.join(archive_dir, f'wuxing_classification_{month_label}.json')
    if os.path.exists(cls_path):
        with open(cls_path, 'r', encoding='utf-8') as f:
            nodes = json.load(f)
        issues = validate_nodes(nodes)
        if issues:
            all_issues.extend([f'[Phase 1 分类] {i}' for i in issues])
        print(f'Phase 1 分类: {len(nodes)} 个节点, {len(issues)} 个问题')

    # Phase 1 诊断
    diag1_path = os.path.join(archive_dir, f'phase1_diagnosis_{month_label}.json')
    if os.path.exists(diag1_path):
        with open(diag1_path, 'r', encoding='utf-8') as f:
            diag = json.load(f)
        issues = validate_diagnosis(diag)
        if issues:
            all_issues.extend([f'[Phase 1 诊断] {i}' for i in issues])
        print(f'Phase 1 诊断: {len(issues)} 个问题')

    # Phase 2
    diag2_path = os.path.join(archive_dir, f'phase2_diagnosis_{month_label}.json')
    if os.path.exists(diag2_path):
        with open(diag2_path, 'r', encoding='utf-8') as f:
            diag = json.load(f)
        issues = validate_diagnosis(diag)
        if issues:
            all_issues.extend([f'[Phase 2] {i}' for i in issues])
        print(f'Phase 2: {len(issues)} 个问题')

    # Phase 3+
    diag3_path = os.path.join(archive_dir, f'phase3_plus_diagnosis_{month_label}.json')
    if os.path.exists(diag3_path):
        print(f'Phase 3+: 存在')

    if all_issues:
        print(f'\n⚠ 共发现 {len(all_issues)} 个问题:')
        for issue in all_issues:
            print(f'  - {issue}')
    else:
        print('\n✓ 验证通过')

    return all_issues


if __name__ == '__main__':
    DEFAULT_BASE = r'E:\00-TRAEWK\6a59e217b55e181ea97f0df3\wuxing_flowengine'
    validate_pipeline(DEFAULT_BASE, '2026-07')