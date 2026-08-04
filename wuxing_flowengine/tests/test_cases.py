"""
自动化验证脚本 — 对比 spec 预期输出 (Phase C1)

测试用例:
  - 小禾案例: 初级研究者，积累阶段，预期"生"
  - 孔子案例: 成熟研究者，贯通阶段，预期"通"
  - 道德经概念: 三层 Spinor 结构验证

用法:
    python tests/test_cases.py
"""

import json
import os
import sys
import math
from collections import Counter

# 确保路径正确
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
sys.path.insert(0, os.path.join(BASE_DIR, 'diagnose'))

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))

PASS = '✓'
FAIL = '✗'


def colorize(status, text):
    """简单标记"""
    return f'{status} {text}'


def build_rings(nodes):
    """从节点列表构建三层 rings"""
    seed = [n for n in nodes if n.get('cognitive_depth') == 'L1']
    curr = [n for n in nodes if n.get('cognitive_depth') == 'L2']
    tran = [n for n in nodes if n.get('cognitive_depth') in ('L3', 'L4')]
    return [
        {'label': '种子层', 'concepts': seed},
        {'label': '现行层', 'concepts': curr},
        {'label': '超越层', 'concepts': tran}
    ]


def compute_entropy(freq):
    """计算熵"""
    H = 0.0
    for wx in ['木', '火', '土', '金', '水']:
        p = freq.get(wx, {}).get('pct', 0)
        if p > 0:
            H -= p * math.log2(p)
    return H, H / math.log2(5) if H > 0 else 0


def run_case(name, case_data, expected):
    """运行单个测试用例"""
    print(f'\n{"─" * 50}')
    print(f'  测试用例: {name}')
    print(f'{"─" * 50}')

    nodes = case_data['nodes']
    edges = case_data.get('edges', [])

    # 构建 rings
    rings = build_rings(nodes)

    # 统计
    seed = [n for n in nodes if n.get('cognitive_depth') == 'L1']
    curr = [n for n in nodes if n.get('cognitive_depth') == 'L2']
    tran = [n for n in nodes if n.get('cognitive_depth') in ('L3', 'L4')]
    print(f'  节点: {len(nodes)} (种子层={len(seed)}, 现行层={len(curr)}, 超越层={len(tran)})')

    # 诊断
    from diagnose.wuxing_diagnose_v2 import diagnose
    result = diagnose(rings)

    # 频率分布
    freq = result['dim1_freq']
    wx_dist = {wx: round(freq[wx]['pct'] * 100, 1) for wx in ['木', '火', '土', '金', '水']}
    print(f'  五行分布: {wx_dist}')

    H, H_ratio = compute_entropy(freq)
    print(f'  熵: H={H:.4f}, H/H_max={H_ratio:.4f}')

    # 四维计算
    w = {wx: freq[wx]['pct'] for wx in ['木', '火', '土', '金', '水']}
    ent = result['dim4_entropy']
    comp = result['dim5_compass']
    path = result['dim3_edges']

    O_t = w['土'] * 0.6 + w['金'] * 0.3 + (1 - ent['ratio']) * 0.1
    E_u = (1 - 0.5 * abs(w['木'] - 0.25) - 0.5 * abs(w['水'] - 0.25)
           - 0.3 * math.sqrt(comp['cx'] ** 2 + comp['cy'] ** 2))
    C_k = w['水'] * 0.5 + w['火'] * 0.3 + w['木'] * 0.2
    ke_count = sum(1 for p in path if p['type'] == '相克')
    E_relation = ke_count / 2 if ke_count > 0 else 0.29
    K_y = w['火'] * 0.4 + w['土'] * 0.3 + E_relation * 0.3

    O_t = max(0, min(1, O_t))
    E_u = max(0, min(1, E_u))
    C_k = max(0, min(1, C_k))
    K_y = max(0, min(1, K_y))
    S = O_t * E_u * C_k * K_y * 100

    print(f'  四维: O_t={O_t:.4f} E_u={E_u:.4f} C_k={C_k:.4f} K_y={K_y:.4f}')
    print(f'  存在度 S: {S:.1f}')

    # 阶段判定
    from scripts.stage_engine import determine_stage
    stage, details = determine_stage(result, S, mode='static')
    print(f'  阶段判定: {stage}')
    print(f'  判定原因: {details["reason"]}')

    # 导航建议
    from scripts.guidance import generate_guidance
    guidance = generate_guidance(stage, freq, O_t, E_u, C_k, K_y, details)
    print(f'  导航建议: {guidance["summary"]}')

    # ── 验证 ──
    checks = []

    # 1. 阶段匹配
    expected_stage = expected.get('stage')
    if expected_stage:
        if stage == expected_stage:
            checks.append((True, f'阶段匹配: {stage} == {expected_stage}'))
        else:
            checks.append((False, f'阶段不匹配: {stage} != {expected_stage}'))

    # 2. 熵范围
    H_range = expected.get('H_ratio_range')
    if H_range:
        if H_range[0] <= H_ratio <= H_range[1]:
            checks.append((True, f'熵在范围内: {H_ratio:.4f} ∈ [{H_range[0]}, {H_range[1]}]'))
        else:
            checks.append((False, f'熵超出范围: {H_ratio:.4f} ∉ [{H_range[0]}, {H_range[1]}]'))

    # 3. S 范围
    S_range = expected.get('S_range')
    if S_range:
        if S_range[0] <= S <= S_range[1]:
            checks.append((True, f'S 在范围内: {S:.1f} ∈ [{S_range[0]}, {S_range[1]}]'))
        else:
            checks.append((False, f'S 超出范围: {S:.1f} ∉ [{S_range[0]}, {S_range[1]}]'))

    # 4. 主导行
    expected_dominant = expected.get('dominant_wx')
    if expected_dominant:
        dominant = max(freq, key=lambda k: freq[k]['pct'])
        if dominant == expected_dominant:
            checks.append((True, f'主导行匹配: {dominant} == {expected_dominant}'))
        else:
            checks.append((False, f'主导行不匹配: {dominant} != {expected_dominant}'))

    # 5. 导航关键词
    keywords = expected.get('guidance_keywords', [])
    if keywords:
        guidance_text = guidance['summary'] + guidance['direction'] + guidance['next_step']
        matched = [kw for kw in keywords if kw in guidance_text]
        if matched:
            checks.append((True, f'导航关键词匹配: {matched}'))
        else:
            checks.append((False, f'导航关键词未匹配: {keywords}'))
            print(f'    [调试] 导航文本: {guidance_text}')

    # 输出结果
    passed = 0
    failed = 0
    for ok, msg in checks:
        status = PASS if ok else FAIL
        print(f'  {status} {msg}')
        if ok:
            passed += 1
        else:
            failed += 1

    print(f'  结果: {passed}/{passed+failed} 通过')
    return passed, failed, stage


def test_daodejing_spinor():
    """测试道德经概念的三层 Spinor 结构"""
    print(f'\n{"─" * 50}')
    print(f'  测试用例: 道德经三层 Spinor')
    print(f'{"─" * 50}')

    path = os.path.join(TESTS_DIR, 'daodejing_concepts.json')
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    concepts = data['concepts']
    print(f'  概念数: {len(concepts)}')

    # 三层统计
    seed_wx = Counter()
    curr_wx = Counter()
    tran_wx = Counter()
    for c in concepts:
        seed_wx[c.get('seed_layer', '土')] += 1
        curr_wx[c.get('current_layer', '土')] += 1
        tran_wx[c.get('transcend_layer', '土')] += 1

    print(f'  种子层: {dict(seed_wx)}')
    print(f'  现行层: {dict(curr_wx)}')
    print(f'  超越层: {dict(tran_wx)}')

    # 验证: 层间有合理的五行流动
    # 检查种子层→现行层→超越层的五行转换
    transitions = 0
    for c in concepts:
        sl = c.get('seed_layer', '')
        cl = c.get('current_layer', '')
        tl = c.get('transcend_layer', '')
        if sl != cl:
            transitions += 1
        if cl != tl:
            transitions += 1

    print(f'  层间五行转换次数: {transitions} (概念数={len(concepts)}×2={len(concepts)*2})')

    checks = []
    # 验证基本结构
    if len(concepts) == 16:
        checks.append((True, '概念数正确: 16'))
    else:
        checks.append((False, f'概念数错误: {len(concepts)} != 16'))

    # 水深占主导（种子层）
    if seed_wx['水'] >= 5:
        checks.append((True, f'种子层水主导: {seed_wx["水"]} >= 5'))
    else:
        checks.append((False, f'种子层水不足: {seed_wx["水"]} < 5'))

    # 有 L4 概念
    l4_count = sum(1 for c in concepts if c.get('cognitive_depth') == 'L4')
    if l4_count >= 5:
        checks.append((True, f'L4 概念充足: {l4_count} >= 5'))
    else:
        checks.append((False, f'L4 概念不足: {l4_count} < 5'))

    passed = 0
    failed = 0
    for ok, msg in checks:
        status = PASS if ok else FAIL
        print(f'  {status} {msg}')
        if ok:
            passed += 1
        else:
            failed += 1

    print(f'  结果: {passed}/{passed+failed} 通过')
    return passed, failed


def main():
    print('=' * 60)
    print('  Phase C1: 自动化验证测试')
    print('=' * 60)

    total_passed = 0
    total_failed = 0

    # 小禾案例
    with open(os.path.join(TESTS_DIR, 'xiaohe_case.json'), 'r', encoding='utf-8') as f:
        xiaohe = json.load(f)
    p, f, _ = run_case('小禾案例 (积累期)', xiaohe, xiaohe['_expected'])
    total_passed += p
    total_failed += f

    # 孔子案例
    with open(os.path.join(TESTS_DIR, 'kongzi_case.json'), 'r', encoding='utf-8') as f:
        kongzi = json.load(f)
    p, f, _ = run_case('孔子案例 (贯通期)', kongzi, kongzi['_expected'])
    total_passed += p
    total_failed += f

    # 道德经 Spinor
    p, f = test_daodejing_spinor()
    total_passed += p
    total_failed += f

    print(f'\n{"=" * 60}')
    print(f'  总计: {total_passed} 通过, {total_failed} 失败')
    if total_failed == 0:
        print(f'  全部测试通过!')
    else:
        print(f'  存在 {total_failed} 个失败项')
    print(f'{"=" * 60}')

    return 0 if total_failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())