"""
道境五行融合诊断引擎 — 统一入口 (V1.2 Ch5)

整合 Phase 1 诊断 → 四维映射 → 存在度计算 → 阶段判定 → 导航建议
实现 Ch5 的 5 步算法 pipeline。

用法:
    from dao_realm_engine import diagnose_dao_realm
    result = diagnose_dao_realm(base_dir, month_label='2026-08')

    import json
    from phase1_pipeline import run as phase1_run
    result = diagnose_dao_realm(base_dir, phase1_result=phase1_run(...))
"""

import json
import os
import sys
import math
from datetime import datetime
from dao_math import compute_S_p, compute_S_old, S_P_DEFAULT, p_label


def diagnose_dao_realm(base_dir, phase1_result=None, month_label=None,
                       config=None, mode='static', previous_snapshot=None):
    """
    道境五行融合诊断 — 5 步算法 (V1.2 Ch5.2)

    步骤 1: 五行诊断 (调用 phase1_pipeline)
    步骤 2: 五行→四维映射
    步骤 3: 存在度 S 计算
    步骤 4: 阶段判定 (调用 stage_engine)
    步骤 5: 导航建议 (调用 guidance)

    Args:
        base_dir: 项目根目录 (wuxing_flowengine/)
        phase1_result: 可选的 Phase 1 结果 (若已执行则跳过步骤1)
        month_label: 月份标签
        config: 配置字典
        mode: 'static' | 'dynamic'
        previous_snapshot: 动态模式下的前一快照

    Returns:
        dict with full diagnosis report
    """
    # 确保 scripts 和 diagnose 目录在路径中
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)
    scripts_dir = os.path.join(base_dir, 'scripts')
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    diagnose_dir = os.path.join(base_dir, 'diagnose')
    if diagnose_dir not in sys.path:
        sys.path.insert(0, diagnose_dir)

    # 加载配置
    if config is None:
        from stage_engine import load_config
        config = load_config(base_dir)

    diagnosis_mode = config.get('diagnosis_mode', mode)
    if diagnosis_mode == 'dynamic' or mode == 'dynamic':
        diagnosis_mode = 'dynamic'
        if previous_snapshot:
            config['_previous_snapshot'] = previous_snapshot

    # ── 步骤 1: 五行诊断 ──
    if phase1_result is None:
        from phase1_pipeline import run as phase1_run
        phase1_result = phase1_run(
            base_dir,
            month_label=month_label,
            output_dir=os.path.join(base_dir, 'output')
        )
    else:
        print('  使用已提供的 Phase 1 结果')

    # 提取诊断数据
    diag = phase1_result.get('diagnosis', {})
    if not diag:
        print('  [警告] Phase 1 结果中缺少 diagnosis 字段，使用简化诊断')
        # 从 four_dims 和 stats 重建
        print('  将使用 four_dims 直接计算导航')

    rings = diag.get('rings', [])
    if not rings:
        print('  [警告] Phase 1 结果中缺少 rings 字段，无法进行完整道境诊断')
        return {
            'phase1': phase1_result,
            'stage': None,
            'guidance': None,
            'error': 'Phase 1 结果中缺少 rings 字段'
        }

    from diagnose.wuxing_diagnose_v2 import diagnose as wuxing_diagnose
    wuxing_result = wuxing_diagnose(rings)

    # ── 步骤 2: 五行→四维映射 ──
    four_dims = phase1_result.get('four_dims', {})
    O_t = four_dims.get('O_t', 0)
    E_u = four_dims.get('E_u', 0)
    C_k = four_dims.get('C_k', 0)
    K_y = four_dims.get('K_y', 0)

    # ── 步骤 3: 存在度 S 计算 ──
    # 使用广义平均 S_p (p=0.5, P忠恕中道)，替代旧乘积公式
    S = compute_S_p([O_t, E_u, C_k, K_y], p=S_P_DEFAULT)

    # ── 步骤 4: 阶段判定 ──
    from stage_engine import determine_stage, detect_nested_stage
    stage, stage_details = determine_stage(
        wuxing_result, S, config, mode=diagnosis_mode
    )
    nested = detect_nested_stage(wuxing_result, stage)

    # ── 步骤 5: 导航建议 ──
    from guidance import generate_guidance
    guidance = generate_guidance(
        stage, wuxing_result['dim1_freq'],
        O_t, E_u, C_k, K_y,
        details=stage_details
    )

    # ── 输出 ──
    report = {
        'report_type': 'dao_realm_diagnosis',
        'version': 'V1.2',
        'generated_at': datetime.now().isoformat(),
        'engine': 'dao_realm_engine',
        'diagnosis_mode': diagnosis_mode,
        'month_label': month_label,
        'phase1': phase1_result,
        'wuxing_diagnosis': wuxing_result,
        'dao_realm_readings': {
            'O_t': round(O_t, 4),
            'E_u': round(E_u, 4),
            'C_k': round(C_k, 4),
            'K_y': round(K_y, 4),
            'S': round(S, 1),
            'S_formula': 'power_mean',
            'S_p': round(S, 1),
            'p': S_P_DEFAULT,
            'p_label': p_label(S_P_DEFAULT),
            'S_old': round(compute_S_old(O_t, E_u, C_k, K_y), 1)
        },
        'stage': stage,
        'stage_details': stage_details,
        'nested_stages': nested,
        'guidance': guidance
    }

    return report


def diagnose_and_save(base_dir, month_label=None, output_dir=None):
    """
    完整诊断并保存报告

    Args:
        base_dir: 项目根目录
        month_label: 月份标签
        output_dir: 输出目录 (默认 base_dir/output/archive/{month}/)

    Returns:
        tuple: (report, output_path)
    """
    if output_dir is None:
        if month_label:
            output_dir = os.path.join(base_dir, 'output', 'archive', month_label)
        else:
            output_dir = os.path.join(base_dir, 'output')

    os.makedirs(output_dir, exist_ok=True)

    report = diagnose_dao_realm(base_dir, month_label=month_label)

    # 保存报告
    if month_label:
        report_path = os.path.join(output_dir, f'dao_realm_report_{month_label}.json')
    else:
        report_path = os.path.join(output_dir, 'dao_realm_report.json')

    # 精简保存（去掉 phase1 的完整 rings 以减少文件大小）
    save_report = {k: v for k, v in report.items() if k != 'phase1'}
    save_report['phase1_summary'] = {
        'four_dims': report['phase1'].get('four_dims', {}),
        'tracks': report['phase1'].get('tracks', {}),
        'stats': report['phase1'].get('stats', {}),
        'edge_quality': report['phase1'].get('edge_quality', {})
    }

    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(save_report, f, ensure_ascii=False, indent=2)

    print(f'\n道境诊断报告已保存: {report_path}')
    print(f'  阶段: {report["stage"]}')
    print(f'  存在度 S_p(p={S_P_DEFAULT}): {report["dao_realm_readings"]["S"]:.1f}')
    print(f'  旧乘积 S: {report["dao_realm_readings"]["S_old"]:.1f}')
    print(f'  四维: O_t={report["dao_realm_readings"]["O_t"]:.4f} '
          f'E_u={report["dao_realm_readings"]["E_u"]:.4f} '
          f'C_k={report["dao_realm_readings"]["C_k"]:.4f} '
          f'K_y={report["dao_realm_readings"]["K_y"]:.4f}')

    return report, report_path


if __name__ == '__main__':
    DEFAULT_BASE = r'E:\00-TRAEWK\6a59e217b55e181ea97f0df3\wuxing_flowengine'
    report, path = diagnose_and_save(DEFAULT_BASE, month_label='2026-08')
    print(f'\n导航建议: {report["guidance"]["summary"]}')