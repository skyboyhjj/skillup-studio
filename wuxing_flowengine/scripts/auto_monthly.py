"""
月度自动化任务：智源社区数据采集 → 流水线处理 → 模型验证
=============================================================
每月 3 日 09:00 自动执行，由 Schedule 定时任务触发。

执行步骤：
  1. BAAI Hub 论文采集 (baai_scraper.py)
  2. 月度流水线全量 (Phase 1→2→3+→B→C2→C1→时间序列→验证)
  3. p-P忠恕 S_p 模型验证 (validate_p_zhongshu.py)
  4. 生成汇总报告

输出：
  - wuxing_flowengine/output/papers_{month}.json
  - wuxing_flowengine/output/archive/{month}/  (各阶段诊断结果)
  - wuxing_flowengine/output/auto_monthly_report_{month}.md
"""
import os
import sys
import json
import subprocess
from datetime import datetime

BASE_DIR = r'E:\00-TRAEWK\6a59e217b55e181ea97f0df3\wuxing_flowengine'
SCRIPTS_DIR = os.path.join(BASE_DIR, 'scripts')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')

def log(msg):
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f'[{timestamp}] {msg}')

def run_script(script_name, args=None, cwd=SCRIPTS_DIR):
    """运行 Python 脚本，返回 (success, output)"""
    cmd = [sys.executable, script_name]
    if args:
        cmd.extend(args)
    log(f'  执行: python {script_name} {" ".join(args or [])}')
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True,
            encoding='utf-8', timeout=600  # 10 分钟超时
        )
        # 打印关键输出行
        for line in result.stdout.split('\n'):
            stripped = line.strip()
            if stripped and any(kw in stripped for kw in
                ['✓', '✗', '完成', '失败', '阶段', 'S_p', 'S =', '节点', '论文', '验证', 'ERROR', 'WARNING']):
                print(f'    {stripped}')
        if result.returncode != 0:
            log(f'  ✗ 退出码 {result.returncode}')
            if result.stderr:
                for line in result.stderr.split('\n')[-5:]:
                    if line.strip():
                        print(f'    [stderr] {line.strip()}')
        return result.returncode == 0, result.stdout
    except subprocess.TimeoutExpired:
        log(f'  ✗ 超时 (10 分钟)')
        return False, ''
    except Exception as e:
        log(f'  ✗ 异常: {e}')
        return False, ''

def main():
    now = datetime.now()
    month_label = now.strftime('%Y-%m')
    month_num = now.strftime('%m')  # 如 "08"

    print('=' * 70)
    print(f'  月度自动化任务')
    print(f'  执行时间: {now.strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'  目标月份: {month_label}')
    print(f'  项目目录: {BASE_DIR}')
    print('=' * 70)

    results = {}
    report_lines = [
        f'# 月度自动化报告 — {month_label}',
        f'',
        f'> 执行时间: {now.strftime("%Y-%m-%d %H:%M:%S")}',
        f'> 目标月份: {month_label}',
        f'',
    ]

    # ═══════════════════════════════════════════════
    # 步骤 1: BAAI Hub 论文采集
    # ═══════════════════════════════════════════════
    print(f'\n{"─" * 60}')
    print(f'  步骤 1/3: BAAI Hub 论文采集')
    print(f'{"─" * 60}')
    ok, output = run_script('baai_scraper.py', args=[month_num])
    results['scraper'] = ok
    if ok:
        papers_path = os.path.join(OUTPUT_DIR, f'papers_{month_label}.json')
        paper_count = 0
        if os.path.exists(papers_path):
            with open(papers_path, 'r', encoding='utf-8') as f:
                papers = json.load(f)
            paper_count = len(papers) if isinstance(papers, list) else sum(len(v) for v in papers.values() if isinstance(v, list))
        log(f'  论文采集完成: {paper_count} 篇')
        report_lines.append(f'| 论文采集 | ✅ | {paper_count} 篇 |')
    else:
        log(f'  ✗ 论文采集失败')
        report_lines.append(f'| 论文采集 | ❌ | — |')

    # ═══════════════════════════════════════════════
    # 步骤 2: 月度流水线
    # ═══════════════════════════════════════════════
    print(f'\n{"─" * 60}')
    print(f'  步骤 2/3: 月度流水线 (Phase 1→2→3+→B→C2→C1→时间序列→验证)')
    print(f'{"─" * 60}')
    ok, output = run_script('monthly_pipeline.py', args=['--month', month_label])
    results['pipeline'] = ok

    # 提取关键结果
    phase1_diag = os.path.join(OUTPUT_DIR, 'archive', month_label, f'phase1_diagnosis_{month_label}.json')
    if os.path.exists(phase1_diag):
        with open(phase1_diag, 'r', encoding='utf-8') as f:
            diag = json.load(f)
        dims = diag.get('four_dims', {})
        stage = diag.get('diagnosis', {}).get('stage', '?')
        s_prod = diag.get('tracks', {}).get('S_prod', '?')
        s_p = diag.get('tracks', {}).get('S_p', '?')
        log(f'  阶段: {stage} | O_t={dims.get("O_t", "?"):.3f} E_u={dims.get("E_u", "?"):.3f} C_k={dims.get("C_k", "?"):.3f} K_y={dims.get("K_y", "?"):.3f} | S_p={s_p} (旧S={s_prod})')
        report_lines.append(f'| 流水线 | {"✅" if ok else "❌"} | 阶段={stage}, O_t={dims.get("O_t", "?"):.3f}, E_u={dims.get("E_u", "?"):.3f}, C_k={dims.get("C_k", "?"):.3f}, K_y={dims.get("K_y", "?"):.3f} |')
    else:
        report_lines.append(f'| 流水线 | {"✅" if ok else "❌"} | — |')

    # ═══════════════════════════════════════════════
    # 步骤 3: p-P忠恕 S_p 模型验证
    # ═══════════════════════════════════════════════
    print(f'\n{"─" * 60}')
    print(f'  步骤 3/3: p-P忠恕 S_p 模型验证')
    print(f'{"─" * 60}')
    ok, output = run_script('validate_p_zhongshu.py')
    results['validate'] = ok

    # 提取 S_p 验证结果
    s_p_checks = []
    for line in output.split('\n'):
        if '✅' in line or '❌' in line:
            stripped = line.strip()
            if any(kw in stripped for kw in ['平滑性', '宽恕', '排名', '量纲', '全部通过']):
                s_p_checks.append(stripped)
    report_lines.append(f'| S_p 验证 | {"✅" if ok else "❌"} | {"; ".join(s_p_checks[-4:]) if s_p_checks else "—"} |')

    # ═══════════════════════════════════════════════
    # 汇总报告
    # ═══════════════════════════════════════════════
    all_ok = all(results.values())
    report_lines.append('')
    report_lines.append(f'## 汇总')
    report_lines.append(f'')
    report_lines.append(f'| 步骤 | 状态 | 详情 |')
    report_lines.append(f'|------|:---:|------|')
    # 重新整理报告表
    final_report = [
        f'# 月度自动化报告 — {month_label}',
        f'',
        f'> 执行时间: {now.strftime("%Y-%m-%d %H:%M:%S")}',
        f'> 目标月份: {month_label}',
        f'> 最终状态: {"✅ 全部通过" if all_ok else "❌ 存在失败步骤"}',
        f'',
        f'| 步骤 | 状态 | 详情 |',
        f'|------|:---:|------|',
    ]
    scraper_line = [l for l in report_lines if '论文采集' in l]
    pipeline_line = [l for l in report_lines if '流水线' in l]
    validate_line = [l for l in report_lines if 'S_p 验证' in l]
    final_report.extend(scraper_line)
    final_report.extend(pipeline_line)
    final_report.extend(validate_line)

    report_path = os.path.join(OUTPUT_DIR, f'auto_monthly_report_{month_label}.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(final_report))
    log(f'  报告已保存: {report_path}')

    print(f'\n{"=" * 70}')
    print(f'  最终状态: {"✅ 全部通过" if all_ok else "❌ 存在失败步骤"}')
    print(f'{"=" * 70}')

    return 0 if all_ok else 1

if __name__ == '__main__':
    sys.exit(main())