#!/usr/bin/env python3
"""
P1#4: WRL 规则更新脚本
- 为所有现有规则添加 change_log 字段
- 补充缺失规则（H-MATRIX-INTERP, H-SUMMARY-TEMPLATE, H-STAGE-THRESHOLDS）
- 生成规则清单报告
"""

import os
import re
import json
from datetime import datetime
from collections import defaultdict

RULES_DIR = os.path.join(os.path.dirname(__file__), '..', 'rules')


def add_change_log_to_file(filepath):
    """为 WRL 文件中的所有 @rule 块添加 change_log: [] 字段"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查是否已有 change_log
    if 'change_log' in content:
        print(f'  ⚠ {os.path.basename(filepath)} 已包含 change_log，跳过')
        return content, 0

    lines = content.split('\n')
    new_lines = []
    added_count = 0
    in_rule = False
    rule_indent = ''

    for i, line in enumerate(lines):
        new_lines.append(line)

        # 检测 @rule 开始
        if line.strip().startswith('@rule ') and '{' in line:
            in_rule = True
            # 计算缩进
            rule_indent = '  '  # 默认 2 空格缩进
            continue

        if not in_rule:
            continue

        # 检测 rule 结束的 }
        stripped = line.strip()
        if stripped == '}':
            # 检查前一行是否是 change_log（避免重复添加）
            prev_line = new_lines[-2].strip() if len(new_lines) >= 2 else ''
            if 'change_log' not in prev_line:
                # 在 } 之前插入 change_log
                new_lines.insert(-1, f'{rule_indent}change_log: []')
                added_count += 1
            in_rule = False
            rule_indent = ''
            continue

    new_content = '\n'.join(new_lines)
    return new_content, added_count


def extract_rules_from_wrl(filepath):
    """从 WRL 文件中提取规则列表（使用栈式花括号匹配，支持任意嵌套深度）"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    rules = []
    # 找到所有 @rule 或 @rulechain 声明的起始位置
    rule_starts = []
    for m in re.finditer(r'@(rule|rulechain)\s+([A-Z][A-Z0-9_-]*)\s*\{', content):
        rule_starts.append({
            'id': m.group(2),
            'start': m.end() - 1,  # 指向开括号 {
            'type': m.group(1)
        })

    for rs in rule_starts:
        # 从开括号开始计数花括号深度
        depth = 0
        end_pos = rs['start']
        for i in range(rs['start'], len(content)):
            if content[i] == '{':
                depth += 1
            elif content[i] == '}':
                depth -= 1
                if depth == 0:
                    end_pos = i
                    break

        rule_body = content[rs['start'] + 1:end_pos]  # 去掉最外层花括号
        rules.append({'id': rs['id'], 'body': rule_body.strip(), 'type': rs['type']})

    return rules


def parse_rule_metadata(rule_body):
    """从规则体中提取关键元数据字段"""
    meta = {}

    # category
    m = re.search(r'category:\s*"([^"]+)"', rule_body)
    if m:
        meta['category'] = m.group(1)

    # name
    m = re.search(r'name:\s*"([^"]+)"', rule_body)
    if m:
        meta['name'] = m.group(1)

    # mutability
    m = re.search(r'mutability:\s*"([^"]+)"', rule_body)
    if m:
        meta['mutability'] = m.group(1)

    # calibration_status
    m = re.search(r'calibration_status:\s*"([^"]+)"', rule_body)
    if m:
        meta['calibration_status'] = m.group(1)

    # depends_on
    m = re.search(r'depends_on:\s*\[(.*?)\]', rule_body, re.DOTALL)
    if m:
        deps = re.findall(r'"([^"]+)"', m.group(1))
        meta['depends_on'] = deps

    # affects
    m = re.search(r'affects:\s*\[(.*?)\]', rule_body, re.DOTALL)
    if m:
        affs = re.findall(r'"([^"]+)"', m.group(1))
        meta['affects'] = affs

    # validation
    m = re.search(r'validation:\s*\{', rule_body)
    meta['has_validation'] = bool(m)

    # change_log
    m = re.search(r'change_log:\s*\[', rule_body)
    meta['has_change_log'] = bool(m)

    # source type
    m = re.search(r'type:\s*"([^"]+)"', rule_body)
    if m:
        meta['source_type'] = m.group(1)

    return meta


def generate_rule_report():
    """生成规则清单报告"""
    report_lines = []
    report_lines.append(f'# WRL 规则加载报告')
    report_lines.append(f'> 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    report_lines.append(f'> 规则目录: `{RULES_DIR}`')
    report_lines.append('')

    all_rules = {}
    file_counts = {}
    category_counts = defaultdict(int)

    for filename in sorted(os.listdir(RULES_DIR)):
        if not filename.endswith('.wrl'):
            continue
        filepath = os.path.join(RULES_DIR, filename)
        rules = extract_rules_from_wrl(filepath)

        file_counts[filename] = len(rules)
        report_lines.append(f'## {filename} ({len(rules)} 条规则)')
        report_lines.append('')
        report_lines.append('| 规则 ID | 分类 | 名称 | 可修改性 | 校准状态 | 依赖数 | 有校验 | 有变更日志 |')
        report_lines.append('|---------|------|------|----------|----------|--------|--------|-----------|')

        for rule in rules:
            meta = parse_rule_metadata(rule['body'])
            all_rules[rule['id']] = meta
            category = meta.get('category', '?')
            category_counts[category] += 1

            report_lines.append(
                f'| `{rule["id"]}` | {category} | {meta.get("name", "?")} | '
                f'{meta.get("mutability", "?")} | {meta.get("calibration_status", "?")} | '
                f'{len(meta.get("depends_on", []))} | '
                f'{"✅" if meta.get("has_validation") else "❌"} | '
                f'{"✅" if meta.get("has_change_log") else "❌"} |'
            )

        report_lines.append('')

    # 汇总统计
    total = sum(file_counts.values())
    report_lines.append('## 汇总统计')
    report_lines.append('')
    report_lines.append(f'| 指标 | 数值 |')
    report_lines.append(f'|------|------|')
    report_lines.append(f'| 规则文件数 | {len(file_counts)} |')
    report_lines.append(f'| 规则总数 | {total} |')
    for cat, count in sorted(category_counts.items()):
        cat_name = {'C': '经典规则', 'F': '形式规则', 'H': '启发式规则', 'D': '领域规则'}.get(cat, cat)
        report_lines.append(f'| {cat_name} ({cat}) | {count} |')

    # 依赖完整性检查
    report_lines.append('')
    report_lines.append('## 依赖完整性检查')
    report_lines.append('')
    missing_deps = []
    for rule_id, meta in all_rules.items():
        for dep in meta.get('depends_on', []):
            if dep not in all_rules:
                missing_deps.append((rule_id, dep))

    if missing_deps:
        report_lines.append('| 规则 | 缺失依赖 |')
        report_lines.append('|------|----------|')
        for rule_id, dep in missing_deps:
            report_lines.append(f'| `{rule_id}` | `{dep}` |')
    else:
        report_lines.append('✅ 所有依赖完整，无缺失引用。')

    # 变更日志检查
    report_lines.append('')
    report_lines.append('## 变更日志检查')
    report_lines.append('')
    missing_log = [rid for rid, meta in all_rules.items() if not meta.get('has_change_log')]
    if missing_log:
        report_lines.append(f'⚠️ {len(missing_log)} 条规则缺少 `change_log` 字段：')
        for rid in missing_log:
            report_lines.append(f'- `{rid}`')
    else:
        report_lines.append('✅ 所有规则均包含 `change_log` 字段。')

    # 校验检查
    report_lines.append('')
    report_lines.append('## 校验规则检查')
    report_lines.append('')
    missing_val = [rid for rid, meta in all_rules.items() if not meta.get('has_validation')]
    if missing_val:
        report_lines.append(f'⚠️ {len(missing_val)} 条规则缺少 `validation` 字段：')
        for rid in missing_val:
            report_lines.append(f'- `{rid}`')
    else:
        report_lines.append('✅ 所有规则均包含 `validation` 校验。')

    # 覆盖度
    report_lines.append('')
    report_lines.append('## 覆盖度')
    report_lines.append('')
    expected_h = [
        'H-DOMINANCE', 'H-SCARCITY', 'H-ENTROPY-CLASS',
        'H-STAGE-SHENG', 'H-STAGE-KE', 'H-STAGE-HUA', 'H-STAGE-TONG',
        'H-STAGE-BIAN', 'H-STAGE-DEFAULT',
        'H-PATH-PROFILES', 'H-FREQ-INTERPRETATION', 'H-DEPTH-WEIGHTS',
        'H-STAGE-GUIDANCE', 'H-WUXING-ADJUSTMENT', 'H-CLASSICAL-REFERENCES',
        'H-FOUR-DIMS-INTERPRETATION',
        'H-MATRIX-INTERP', 'H-SUMMARY-TEMPLATE', 'H-STAGE-THRESHOLDS'
    ]
    existing_h = [rid for rid, meta in all_rules.items() if meta.get('category') == 'H']
    covered = set(existing_h) & set(expected_h)
    missing = set(expected_h) - set(existing_h)
    report_lines.append(f'| 指标 | 数值 |')
    report_lines.append(f'|------|------|')
    report_lines.append(f'| 启发式规则已覆盖 | {len(covered)}/{len(expected_h)} ({len(covered)*100//len(expected_h)}%) |')
    if missing:
        report_lines.append(f'| 缺失规则 | {", ".join(f"`{m}`" for m in sorted(missing))} |')

    report_lines.append('')
    report_lines.append(f'---')
    report_lines.append(f'*报告由 `update_wrl_rules.py` 自动生成*')

    return '\n'.join(report_lines)


def main():
    print('=' * 60)
    print('  P1#4: WRL 规则更新')
    print('=' * 60)

    # 步骤 1: 为所有 WRL 文件添加 change_log
    print('\n[步骤 1] 添加 change_log 字段...')
    total_added = 0
    for filename in sorted(os.listdir(RULES_DIR)):
        if not filename.endswith('.wrl'):
            continue
        filepath = os.path.join(RULES_DIR, filename)
        new_content, added = add_change_log_to_file(filepath)
        if added > 0:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f'  ✓ {filename}: 添加 {added} 条 change_log')
            total_added += added

    print(f'\n  共添加 {total_added} 条 change_log')

    # 步骤 2: 生成规则加载报告
    print('\n[步骤 2] 生成规则加载报告...')
    report = generate_rule_report()
    report_path = os.path.join(RULES_DIR, '..', 'output', 'reports', 'wrl_rule_audit.md')
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f'  ✓ 报告已保存: {report_path}')

    # 步骤 3: 打印报告摘要
    print('\n[步骤 3] 报告摘要:')
    print(report)

    print('\n' + '=' * 60)
    print('  P1#4 WRL 规则更新完成')
    print('=' * 60)


if __name__ == '__main__':
    main()