"""
五行道境月度自动追踪流水线
============================
编排器入口：串行执行 Phase 1 → Phase 2 → Phase 3+ → 时间序列分析 → 验证

用法:
    python monthly_pipeline.py [--month 2026-08] [--base-dir PATH]

环境变量:
    WUXING_BASE_DIR: 项目根目录 (默认当前目录)
"""

import json
import os
import sys
import argparse
from datetime import datetime


def get_default_base():
    """获取默认项目根目录"""
    return os.environ.get(
        'WUXING_BASE_DIR',
        r'C:\Users\hejij\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a59e217b55e181ea97f0df3\wuxing_flowengine'
    )


def run_pipeline(base_dir, month_label=None):
    """
    执行完整的月度追踪流水线

    Phase 1: 认知深度估算 + 五行映射 + 三层构建 + 道境诊断
    Phase 2: 双层标注 + Spinor层构建 + 领域追踪
    Phase 3+: 论文五行分类 + 领域对比
    时间序列: 多月份趋势分析
    验证: 输出合法性检查
    """
    if month_label is None:
        now = datetime.now()
        month_label = now.strftime('%Y-%m')

    print(f'\n{"=" * 70}')
    print(f'  五行道境月度自动追踪流水线')
    print(f'  月份: {month_label}')
    print(f'  项目: {base_dir}')
    print(f'{"=" * 70}\n')

    # 确保 scripts 目录在路径中
    scripts_dir = os.path.join(base_dir, 'scripts')
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    diagnose_dir = os.path.join(base_dir, 'diagnose')
    if diagnose_dir not in sys.path:
        sys.path.insert(0, diagnose_dir)

    output_dir = os.path.join(base_dir, 'output')
    archive_dir = os.path.join(output_dir, 'archive', month_label)
    os.makedirs(archive_dir, exist_ok=True)

    papers_path = os.path.join(output_dir, f'papers_{month_label}.json')

    results = {}

    # ============================================================
    # Phase 1
    # ============================================================
    print(f'\n{"─" * 60}')
    print(f'  Phase 1: 数据采集 & 静态诊断')
    print(f'{"─" * 60}')
    try:
        from phase1_pipeline import run as phase1_run
        results['phase1'] = phase1_run(
            base_dir,
            month_label=month_label,
            output_dir=output_dir
        )
        print(f'  ✓ Phase 1 完成')
    except Exception as e:
        print(f'  ✗ Phase 1 失败: {e}')
        import traceback
        traceback.print_exc()
        results['phase1'] = None

    # ============================================================
    # Phase 2
    # ============================================================
    print(f'\n{"─" * 60}')
    print(f'  Phase 2: 双层标注 & Spinor')
    print(f'{"─" * 60}')
    try:
        from phase2_pipeline import run as phase2_run
        results['phase2'] = phase2_run(
            base_dir,
            month_label=month_label,
            output_dir=output_dir
        )
        print(f'  ✓ Phase 2 完成')
    except Exception as e:
        print(f'  ✗ Phase 2 失败: {e}')
        import traceback
        traceback.print_exc()
        results['phase2'] = None

    # ============================================================
    # Phase 3+
    # ============================================================
    print(f'\n{"─" * 60}')
    print(f'  Phase 3+: 论文五行分类 & 领域对比')
    print(f'{"─" * 60}')
    try:
        from phase3_plus_pipeline import run as phase3_run
        results['phase3'] = phase3_run(
            base_dir,
            papers_path=papers_path,
            month_label=month_label,
            output_dir=output_dir
        )
        print(f'  ✓ Phase 3+ 完成')
    except Exception as e:
        print(f'  ✗ Phase 3+ 失败: {e}')
        import traceback
        traceback.print_exc()
        results['phase3'] = None

    # ============================================================
    # 时间序列分析
    # ============================================================
    print(f'\n{"─" * 60}')
    print(f'  时间序列分析')
    print(f'{"─" * 60}')
    try:
        from timeseries_analysis import run as ts_run
        results['timeseries'] = ts_run(
            base_dir,
            month_label=month_label,
            output_dir=output_dir
        )
        print(f'  ✓ 时间序列分析完成')
    except Exception as e:
        print(f'  ✗ 时间序列分析失败: {e}')
        results['timeseries'] = None

    # ============================================================
    # 验证
    # ============================================================
    print(f'\n{"─" * 60}')
    print(f'  验证')
    print(f'{"─" * 60}')
    try:
        from validator import validate_pipeline
        issues = validate_pipeline(base_dir, month_label)
        results['validation'] = {
            'passed': len(issues) == 0,
            'issues': issues
        }
    except Exception as e:
        print(f'  ✗ 验证失败: {e}')
        results['validation'] = {'passed': False, 'issues': [str(e)]}

    # ============================================================
    # 汇总
    # ============================================================
    print(f'\n{"=" * 70}')
    print(f'  流水线执行完成')
    print(f'{"=" * 70}')

    summary = {
        'pipeline': 'wuxing_monthly',
        'month': month_label,
        'executed_at': datetime.now().isoformat(),
        'base_dir': base_dir,
        'phases': {
            'phase1': '✓' if results.get('phase1') else '✗',
            'phase2': '✓' if results.get('phase2') else '✗',
            'phase3': '✓' if results.get('phase3') else '✗',
            'timeseries': '✓' if results.get('timeseries') else '✗',
            'validation': '✓' if results.get('validation', {}).get('passed') else '✗'
        }
    }

    summary_path = os.path.join(archive_dir, f'pipeline_summary_{month_label}.json')
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f'\n摘要: {summary_path}')
    for phase, status in summary['phases'].items():
        print(f'  {phase}: {status}')

    return results


def main():
    parser = argparse.ArgumentParser(description='五行道境月度自动追踪流水线')
    parser.add_argument('--month', type=str, default=None,
                        help='月份标签 (e.g. 2026-08), 默认当前月份')
    parser.add_argument('--base-dir', type=str, default=None,
                        help='项目根目录')
    args = parser.parse_args()

    base_dir = args.base_dir or get_default_base()
    month_label = args.month

    results = run_pipeline(base_dir, month_label)

    # 返回退出码
    if results.get('validation', {}).get('passed', True):
        return 0
    return 1


if __name__ == '__main__':
    sys.exit(main())