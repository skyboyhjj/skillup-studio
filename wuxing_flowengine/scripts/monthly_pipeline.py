"""
五行道境月度自动追踪流水线
============================
编排器入口：串行执行 Phase 1 → Phase 2 → Phase 3+ → Phase B (道境导航) → Phase C (领域校准)

V1.2 增强:
  Phase B: 道境诊断引擎 (阶段判定 + 嵌入阶段 + 导航建议)
  Phase C1: 领域基准校准 (Ch6, 跨领域 S 值归一化)
  Phase C2: K_y 缘位增强 (Phase 4, 图密度混合 E_relation)

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
from wrl_loader import load_wrl_rules, generate_loading_report


def get_default_base():
    """获取默认项目根目录"""
    return os.environ.get(
        'WUXING_BASE_DIR',
        r'E:\00-TRAEWK\6a59e217b55e181ea97f0df3\wuxing_flowengine'
    )


def run_pipeline(base_dir, month_label=None, skip_phases=None):
    """
    执行完整的月度追踪流水线

    Phase 1: 认知深度估算 + 五行映射 + 三层构建 + 道境诊断
    Phase 2: 双层标注 + Spinor层构建 + 领域追踪
    Phase 3+: 论文五行分类 + 领域对比
    Phase B: 道境诊断引擎 (阶段判定 + 嵌套阶段 + 导航建议)
    Phase C: K_y 缘位增强 + 领域基准校准
    时间序列: 多月份趋势分析
    验证: 输出合法性检查
    """
    if month_label is None:
        now = datetime.now()
        month_label = now.strftime('%Y-%m')

    if skip_phases is None:
        skip_phases = set()

    print(f'\n{"=" * 70}')
    print(f'  五行道境月度自动追踪流水线 (V1.2)')
    print(f'  月份: {month_label}')
    print(f'  项目: {base_dir}')
    print(f'{"=" * 70}\n')

    # 确保 scripts 和 diagnose 目录在路径中
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)
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
    # Phase 0: WRL 规则加载与验证 (P1#4)
    # ============================================================
    if 'phase0' not in skip_phases:
        print(f'\n{"─" * 60}')
        print(f'  Phase 0: WRL 规则加载与验证 (P1#4)')
        print(f'{"─" * 60}')
        try:
            # 加载配置获取 rules_dir
            config_path = os.path.join(base_dir, 'config', 'config_default.json')
            wrl_config = {}
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                wrl_config = config.get('wrl', {})

            rules_dir = os.path.join(base_dir, wrl_config.get('rules_dir', 'rules'))
            validate_on_load = wrl_config.get('validate_on_load', True)

            registry, report = load_wrl_rules(rules_dir, validate=validate_on_load)

            # 生成并保存报告
            md_report = generate_loading_report(registry, report)
            report_dir = os.path.join(output_dir, wrl_config.get('report_output', 'reports').strip('/'))
            os.makedirs(report_dir, exist_ok=True)
            report_path = os.path.join(report_dir, f'wrl_loader_report_{month_label}.md')
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(md_report)

            # 保存 JSON 报告
            json_path = os.path.join(report_dir, f'wrl_loader_report_{month_label}.json')
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

            results['phase0'] = {
                'loaded': registry.rule_count,
                'category_counts': registry.category_counts,
                'validation_passed': report['passed'] if report else None,
                'report_md': report_path,
                'report_json': json_path
            }

            # 打印摘要
            if report and report['passed']:
                print(f'  ✓ Phase 0 完成: {registry.rule_count} 条规则全部通过验证')
                for cat, count in sorted(registry.category_counts.items()):
                    print(f'    {cat}: {count} 条')
            else:
                errors = report.get('errors', []) if report else []
                warnings = report.get('warnings', []) if report else []
                print(f'  ⚠ Phase 0 完成: {len(errors)} 错误, {len(warnings)} 警告')
                if errors:
                    for err in errors[:3]:
                        print(f'    ❌ {err}')
                    if len(errors) > 3:
                        print(f'    ... 共 {len(errors)} 个错误')
        except Exception as e:
            print(f'  ✗ Phase 0 失败: {e}')
            import traceback
            traceback.print_exc()
            results['phase0'] = None

    # ============================================================
    # Phase 1
    # ============================================================
    if 'phase1' not in skip_phases:
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
    if 'phase2' not in skip_phases:
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
    if 'phase3' not in skip_phases:
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
    # Phase B: 道境诊断引擎 (V1.2)
    # ============================================================
    if 'phaseB' not in skip_phases:
        print(f'\n{"─" * 60}')
        print(f'  Phase B: 道境诊断引擎 (V1.2)')
        print(f'{"─" * 60}')
        try:
            from dao_realm_engine import diagnose_dao_realm
            phase1_result = results.get('phase1')

            # 如果 Phase 1 被跳过，尝试从磁盘加载已有数据
            if phase1_result is None:
                phase1_diag_path = os.path.join(
                    archive_dir, f'phase1_diagnosis_{month_label}.json'
                )
                if os.path.exists(phase1_diag_path):
                    with open(phase1_diag_path, 'r', encoding='utf-8') as f:
                        phase1_result = json.load(f)
                    print(f'  从磁盘加载 Phase 1 结果')
                else:
                    print(f'  Phase 1 结果不存在，运行 Phase 1...')
                    from phase1_pipeline import run as phase1_run
                    phase1_result = phase1_run(
                        base_dir, month_label=month_label, output_dir=output_dir
                    )

            if phase1_result:
                dao_report = diagnose_dao_realm(
                    base_dir,
                    phase1_result=phase1_result,
                    month_label=month_label
                )
                results['phaseB'] = dao_report

                # 保存精简报告
                report_path = os.path.join(archive_dir, f'dao_realm_report_{month_label}.json')
                save_report = {k: v for k, v in dao_report.items() if k != 'phase1'}
                save_report['phase1_summary'] = {
                    'four_dims': dao_report['phase1'].get('four_dims', {}),
                    'tracks': dao_report['phase1'].get('tracks', {}),
                    'stats': dao_report['phase1'].get('stats', {}),
                    'edge_quality': dao_report['phase1'].get('edge_quality', {})
                }
                with open(report_path, 'w', encoding='utf-8') as f:
                    json.dump(save_report, f, ensure_ascii=False, indent=2)

                print(f'  ✓ Phase B 完成')
                print(f'    阶段: {dao_report["stage"]}')
                print(f'    存在度 S: {dao_report["dao_realm_readings"]["S"]:.1f}')
                print(f'    导航: {dao_report["guidance"]["summary"]}')
            else:
                print(f'  ✗ Phase B 跳过: Phase 1 结果不可用')
                results['phaseB'] = None
        except Exception as e:
            print(f'  ✗ Phase B 失败: {e}')
            import traceback
            traceback.print_exc()
            results['phaseB'] = None

    # ============================================================
    # Phase C2: K_y 缘位增强 (Phase 4)
    # ============================================================
    if 'phaseC2' not in skip_phases:
        print(f'\n{"─" * 60}')
        print(f'  Phase C2: K_y 缘位增强 (Phase 4)')
        print(f'{"─" * 60}')
        try:
            from k_y_enhancer import compare_ky_methods
            phase1_result = results.get('phase1')

            # 如果 Phase 1 被跳过，尝试从磁盘加载
            if phase1_result is None:
                phase1_diag_path = os.path.join(
                    archive_dir, f'phase1_diagnosis_{month_label}.json'
                )
                if os.path.exists(phase1_diag_path):
                    with open(phase1_diag_path, 'r', encoding='utf-8') as f:
                        phase1_result = json.load(f)
                    print(f'  从磁盘加载 Phase 1 结果')

            if phase1_result:
                ky_comparison = compare_ky_methods(phase1_result)
                results['phaseC2'] = ky_comparison
                print(f'  ✓ Phase C2 完成')
                print(f'    原始 K_y: {ky_comparison["original"]["K_y"]:.4f} → S: {ky_comparison["original"]["S"]:.1f}')
                print(f'    增强 K_y: {ky_comparison["enhanced"]["K_y"]:.4f} → S: {ky_comparison["enhanced"]["S"]:.1f}')
                print(f'    ΔK_y: {ky_comparison["delta_K_y"]:+.4f}')
                print(f'    E_relation 模式: {ky_comparison["E_relation_detail"]["mode"]}')
            else:
                print(f'  ✗ Phase C2 跳过: Phase 1 结果不可用')
                results['phaseC2'] = None
        except Exception as e:
            print(f'  ✗ Phase C2 失败: {e}')
            import traceback
            traceback.print_exc()
            results['phaseC2'] = None

    # ============================================================
    # 时间序列分析
    # ============================================================
    if 'timeseries' not in skip_phases:
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
    # Phase C1: 领域基准校准 (Ch6)
    # ============================================================
    if 'phaseC1' not in skip_phases:
        print(f'\n{"─" * 60}')
        print(f'  Phase C1: 领域基准校准 (Ch6)')
        print(f'{"─" * 60}')
        try:
            from domain_calibration import DomainCalibrator
            cal = DomainCalibrator(base_dir)
            cal.build_baseline()
            cal.save_baseline(output_dir)

            # 输出校准表摘要
            table = cal.get_calibration_table()
            results['phaseC1'] = {
                'calibrator': cal,
                'table': table,
                'domain_count': len(table)
            }
            print(f'  ✓ Phase C1 完成 ({len(table)} 个领域)')
            for row in table[:5]:
                print(f'    {row["domain"]}: mean_S={row["mean_S"]:.4f}')
            if len(table) > 5:
                print(f'    ... 共 {len(table)} 个领域')
        except Exception as e:
            print(f'  ✗ Phase C1 失败: {e}')
            import traceback
            traceback.print_exc()
            results['phaseC1'] = None

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
    # Phase D: 领域漂移可视化与报告 (P1#3)
    # ============================================================
    if 'phaseD' not in skip_phases:
        print(f'\n{"─" * 60}')
        print(f'  Phase D: 领域漂移可视化 & 报告 (P1#3)')
        print(f'{"─" * 60}')
        try:
            from drift_visualization import generate_all_charts
            from drift_report import generate_drift_report

            phase3_result = results.get('phase3')

            # 如果 Phase 3+ 被跳过，尝试从磁盘加载
            if phase3_result is None:
                phase3_path = os.path.join(
                    archive_dir, f'phase3_plus_diagnosis_{month_label}.json'
                )
                if os.path.exists(phase3_path):
                    with open(phase3_path, 'r', encoding='utf-8') as f:
                        phase3_result = json.load(f)
                    print(f'  从磁盘加载 Phase 3+ 结果')

            if phase3_result and phase3_result.get('domains'):
                chart_dir = os.path.join(output_dir, 'charts')
                report_dir = os.path.join(output_dir, 'reports')

                # 生成图表
                chart_paths = generate_all_charts(
                    phase3_result, chart_dir, month_label=month_label
                )

                # 生成报告
                report_path = generate_drift_report(
                    phase3_result, report_dir, month_label=month_label,
                    chart_paths=chart_paths
                )

                results['phaseD'] = {
                    'charts': chart_paths,
                    'report': report_path,
                    'chart_count': len(chart_paths)
                }

                print(f'  ✓ Phase D 完成 ({len(chart_paths)} 张图表 + 1 份报告)')
            else:
                print(f'  ⚠ Phase D 跳过: Phase 3+ 无领域数据')
                results['phaseD'] = None
        except Exception as e:
            print(f'  ✗ Phase D 失败: {e}')
            import traceback
            traceback.print_exc()
            results['phaseD'] = None

    # ============================================================
    # 汇总
    # ============================================================
    print(f'\n{"=" * 70}')
    print(f'  流水线执行完成')
    print(f'{"=" * 70}')

    summary = {
        'pipeline': 'wuxing_monthly_v1.3',
        'month': month_label,
        'executed_at': datetime.now().isoformat(),
        'base_dir': base_dir,
        'phases': {
            'phase0': '✓' if results.get('phase0') else '✗',
            'phase1': '✓' if results.get('phase1') else '✗',
            'phase2': '✓' if results.get('phase2') else '✗',
            'phase3': '✓' if results.get('phase3') else '✗',
            'phaseB': '✓' if results.get('phaseB') else '✗',
            'phaseC2': '✓' if results.get('phaseC2') else '✗',
            'phaseC1': '✓' if results.get('phaseC1') else '✗',
            'timeseries': '✓' if results.get('timeseries') else '✗',
            'phaseD': '✓' if results.get('phaseD') else '✗',
            'validation': '✓' if results.get('validation', {}).get('passed') else '✗'
        }
    }

    # 道境诊断摘要
    phaseB = results.get('phaseB')
    if phaseB:
        summary['dao_realm'] = {
            'stage': phaseB.get('stage'),
            'S': phaseB.get('dao_realm_readings', {}).get('S'),
            'guidance': phaseB.get('guidance', {}).get('summary')
        }

    # K_y 增强摘要
    phaseC2 = results.get('phaseC2')
    if phaseC2:
        summary['ky_enhancement'] = {
            'K_y_original': phaseC2['original']['K_y'],
            'K_y_enhanced': phaseC2['enhanced']['K_y'],
            'delta_K_y': phaseC2['delta_K_y']
        }

    summary_path = os.path.join(archive_dir, f'pipeline_summary_{month_label}.json')
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f'\n摘要: {summary_path}')
    for phase, status in summary['phases'].items():
        print(f'  {phase}: {status}')

    if 'dao_realm' in summary:
        dr = summary['dao_realm']
        print(f'\n  道境: 阶段={dr["stage"]} S={dr["S"]}')
        print(f'  导航: {dr["guidance"]}')

    return results


def main():
    parser = argparse.ArgumentParser(description='五行道境月度自动追踪流水线 (V1.2)')
    parser.add_argument('--month', type=str, default=None,
                        help='月份标签 (e.g. 2026-08), 默认当前月份')
    parser.add_argument('--base-dir', type=str, default=None,
                        help='项目根目录')
    parser.add_argument('--skip', type=str, default='',
                        help='跳过的阶段，逗号分隔 (e.g. phase3,phaseC1)')
    args = parser.parse_args()

    base_dir = args.base_dir or get_default_base()
    month_label = args.month

    skip_phases = set()
    if args.skip:
        skip_phases = set(s.strip() for s in args.skip.split(','))

    results = run_pipeline(base_dir, month_label, skip_phases)

    # 返回退出码
    if results.get('validation', {}).get('passed', True):
        return 0
    return 1


if __name__ == '__main__':
    sys.exit(main())