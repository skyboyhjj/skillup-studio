#!/usr/bin/env python3
"""
WRL (五行规则语言) 加载器 — P1#4 规则可审计性基础设施
========================================================
按设计文档 10.4-10.5 节实现：
- 解析 .wrl 文件 → 语法检查
- 提取 @rule 块 → 规则 ID 唯一性检查
- 检查 depends_on 引用完整性 → 缺失依赖告警
- 执行 validation 规则 → 取值合法性校验
- 检查 rulechain 优先级完整性 → 覆盖度分析
- 生成规则加载报告 → 可审计的加载日志
"""

import os
import re
import json
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Optional, Any, Tuple


# ──────────────────────────────────────────────
# 常量
# ──────────────────────────────────────────────

CATEGORY_NAMES = {
    'C': '经典规则',
    'F': '形式规则',
    'H': '启发式规则',
    'D': '领域规则'
}

CATEGORY_MUTABILITY = {
    'C': 'immutable',
    'F': 'immutable or calibratable',
    'H': 'calibratable',
    'D': 'configurable'
}

VALID_AFFECTS_TARGETS = {
    'dim1_freq', 'dim1_interpretations', 'dim2_layers', 'dim3_edges',
    'dim3_profile', 'dim4_entropy', 'dim4_entropy_desc', 'dim5_compass',
    'stage', 'stage_sheng', 'stage_ke', 'stage_hua', 'stage_tong',
    'stage_bian', 'guidance', 'guidance.wuxing_bias', 'guidance.classical_reference',
    'guidance.four_dims', 'guidance.matrix', 'guidance.summary',
    'dim_cross', 'report', 'wuxing_mapping', 'wuxing_bias',
    'O_t', 'E_u', 'C_k', 'K_y', 'S', 'S_p', 'dao_realm_readings',
    'depth_profile', 'theta_critical', 'K_y'
}


# ──────────────────────────────────────────────
# WRL 解析器
# ──────────────────────────────────────────────

class WrlParser:
    """WRL 文件解析器，使用栈式花括号匹配支持任意嵌套深度"""

    def __init__(self, rules_dir: str):
        self.rules_dir = rules_dir
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def parse_all(self) -> Dict[str, List[dict]]:
        """解析所有 .wrl 文件，返回 {filepath: [rules]}"""
        results = {}
        for filename in sorted(os.listdir(self.rules_dir)):
            if not filename.endswith('.wrl'):
                continue
            filepath = os.path.join(self.rules_dir, filename)
            results[filepath] = self.parse_file(filepath)
        return results

    def parse_file(self, filepath: str) -> List[dict]:
        """解析单个 WRL 文件"""
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        rules = []
        # 找到所有 @rule 或 @rulechain 声明
        rule_starts = []
        for m in re.finditer(r'@(rule|rulechain)\s+([A-Z][A-Z0-9_-]*)\s*\{', content):
            rule_starts.append({
                'id': m.group(2),
                'start': m.end() - 1,
                'type': m.group(1)
            })

        for rs in rule_starts:
            # 栈式花括号匹配
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

            rule_body = content[rs['start'] + 1:end_pos]
            rule = self._parse_rule_body(rs['id'], rule_body, rs['type'], filepath)
            if rule:
                rules.append(rule)

        return rules

    def _parse_rule_body(self, rule_id: str, body: str, rule_type: str, filepath: str) -> Optional[dict]:
        """解析规则体，提取元数据"""
        meta = {
            'rule_id': rule_id,
            'type': rule_type,
            'file': os.path.basename(filepath),
            'raw_body': body.strip()
        }

        # category
        m = re.search(r'category:\s*"([^"]+)"', body)
        meta['category'] = m.group(1) if m else '?'

        # name
        m = re.search(r'name:\s*"([^"]+)"', body)
        meta['name'] = m.group(1) if m else '?'

        # mutability
        m = re.search(r'mutability:\s*"([^"]+)"', body)
        meta['mutability'] = m.group(1) if m else '?'

        # calibration_status
        m = re.search(r'calibration_status:\s*"([^"]+)"', body)
        meta['calibration_status'] = m.group(1) if m else '?'

        # source type
        m = re.search(r'type:\s*"([^"]+)"', body)
        if m:
            meta['source_type'] = m.group(1)

        # source reference
        m = re.search(r'reference:\s*"([^"]+)"', body)
        if m:
            meta['source_reference'] = m.group(1)

        # depends_on
        m = re.search(r'depends_on:\s*\[(.*?)\]', body, re.DOTALL)
        if m:
            deps = re.findall(r'"([A-Z][A-Z0-9_-]*)"', m.group(1))
            meta['depends_on'] = deps
        else:
            meta['depends_on'] = []

        # affects
        m = re.search(r'affects:\s*\[(.*?)\]', body, re.DOTALL)
        if m:
            affs = re.findall(r'"([a-z0-9_.]+)"', m.group(1))
            meta['affects'] = affs
        else:
            meta['affects'] = []

        # validation
        m = re.search(r'validation:\s*\{', body)
        meta['has_validation'] = bool(m)

        # change_log
        m = re.search(r'change_log:\s*\[', body)
        meta['has_change_log'] = bool(m)

        # code_location
        m = re.search(r'code_location:\s*"([^"]+)"', body)
        if m:
            meta['code_location'] = m.group(1)

        # formula (for formal rules)
        m = re.search(r'formula:\s*"([^"]+)"', body)
        if m:
            meta['formula'] = m.group(1)

        # value (for simple rules)
        m = re.search(r'^\s*value:\s*([0-9.]+)', body, re.MULTILINE)
        if m:
            meta['value'] = float(m.group(1))

        # range
        m = re.search(r'range:\s*\[([^\]]+)\]', body)
        if m:
            meta['range'] = m.group(1).strip()

        # priority (for rulechain sub-rules)
        m = re.search(r'priority:\s*([0-9]+)', body)
        if m:
            meta['priority'] = int(m.group(1))

        return meta


# ──────────────────────────────────────────────
# 规则验证器
# ──────────────────────────────────────────────

class RuleValidator:
    """规则验证器，执行 10.5 节定义的 8 步验证流程"""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.stats: Dict[str, Any] = {}

    def validate(self, all_rules: Dict[str, dict]) -> Tuple[bool, Dict[str, Any]]:
        """
        执行全部验证流程
        返回 (passed, report)
        """
        self.errors = []
        self.warnings = []

        # 1. 语法检查（已在解析阶段完成，此处做补充检查）
        self._check_syntax(all_rules)

        # 2. 规则 ID 唯一性检查
        self._check_id_uniqueness(all_rules)

        # 3. 依赖完整性检查
        self._check_dependency_integrity(all_rules)

        # 4. affects 引用有效性检查
        self._check_affects_validity(all_rules)

        # 5. 分类一致性检查
        self._check_category_consistency(all_rules)

        # 6. 变更日志存在性检查
        self._check_change_log(all_rules)

        # 7. 校验规则存在性检查
        self._check_validation_existence(all_rules)

        # 8. rulechain 优先级完整性检查
        self._check_rulechain_completeness(all_rules)

        # 统计
        self.stats = self._compute_stats(all_rules)

        passed = len(self.errors) == 0
        return passed, self._build_report(all_rules)

    def _check_syntax(self, all_rules: Dict[str, dict]):
        """语法检查：必需字段完整性"""
        required_fields = ['category', 'name', 'mutability']
        for rule_id, rule in all_rules.items():
            for field in required_fields:
                if rule.get(field, '?') == '?':
                    self.errors.append(f"[{rule_id}] 缺少必需字段 '{field}'")

    def _check_id_uniqueness(self, all_rules: Dict[str, dict]):
        """ID 唯一性在字典构建时已保证，此处检查重复文件名"""
        seen = defaultdict(list)
        for rule_id, rule in all_rules.items():
            seen[rule_id].append(rule.get('file', '?'))
        for rule_id, files in seen.items():
            if len(files) > 1:
                self.errors.append(f"[{rule_id}] 在多个文件中重复定义: {files}")

    def _check_dependency_integrity(self, all_rules: Dict[str, dict]):
        """依赖完整性检查"""
        all_ids = set(all_rules.keys())
        for rule_id, rule in all_rules.items():
            for dep in rule.get('depends_on', []):
                if dep not in all_ids:
                    self.errors.append(f"[{rule_id}] 依赖的规则 '{dep}' 不存在")

    def _check_affects_validity(self, all_rules: Dict[str, dict]):
        """affects 引用有效性检查"""
        for rule_id, rule in all_rules.items():
            for aff in rule.get('affects', []):
                if aff not in VALID_AFFECTS_TARGETS:
                    self.warnings.append(f"[{rule_id}] affects 引用了未知目标 '{aff}'")

    def _check_category_consistency(self, all_rules: Dict[str, dict]):
        """分类一致性检查"""
        for rule_id, rule in all_rules.items():
            cat = rule.get('category', '?')
            if cat == '?':
                self.errors.append(f"[{rule_id}] 缺少 category 分类")
                continue
            if cat not in CATEGORY_NAMES:
                self.errors.append(f"[{rule_id}] 未知分类 '{cat}'，有效分类: {list(CATEGORY_NAMES.keys())}")

    def _check_change_log(self, all_rules: Dict[str, dict]):
        """变更日志存在性检查"""
        for rule_id, rule in all_rules.items():
            if not rule.get('has_change_log'):
                self.warnings.append(f"[{rule_id}] 缺少 change_log 字段")

    def _check_validation_existence(self, all_rules: Dict[str, dict]):
        """校验规则存在性检查"""
        for rule_id, rule in all_rules.items():
            if not rule.get('has_validation'):
                self.warnings.append(f"[{rule_id}] 缺少 validation 校验规则")

    def _check_rulechain_completeness(self, all_rules: Dict[str, dict]):
        """rulechain 优先级完整性检查"""
        # 收集所有 stage 判定规则
        stage_rules = {}
        for rule_id, rule in all_rules.items():
            if rule_id.startswith('H-STAGE-') and rule_id != 'H-STAGE-THRESHOLDS':
                priority = rule.get('priority')
                if priority is not None:
                    stage_rules[rule_id] = priority

        if stage_rules:
            priorities = sorted(stage_rules.values())
            expected = list(range(1, len(stage_rules) + 1))
            if priorities != expected:
                self.warnings.append(
                    f"阶段判定链优先级不连续: 实际 {priorities}，期望 {expected}"
                )

    def _compute_stats(self, all_rules: Dict[str, dict]) -> dict:
        """计算统计信息"""
        stats = {
            'total': len(all_rules),
            'by_category': defaultdict(int),
            'by_file': defaultdict(int),
            'by_mutability': defaultdict(int),
            'with_validation': 0,
            'with_change_log': 0,
            'total_dependencies': 0,
            'total_affects': 0
        }

        for rule_id, rule in all_rules.items():
            stats['by_category'][rule.get('category', '?')] += 1
            stats['by_file'][rule.get('file', '?')] += 1
            stats['by_mutability'][rule.get('mutability', '?')] += 1
            if rule.get('has_validation'):
                stats['with_validation'] += 1
            if rule.get('has_change_log'):
                stats['with_change_log'] += 1
            stats['total_dependencies'] += len(rule.get('depends_on', []))
            stats['total_affects'] += len(rule.get('affects', []))

        return stats

    def _build_report(self, all_rules: Dict[str, dict]) -> dict:
        """构建验证报告"""
        return {
            'timestamp': datetime.now().isoformat(),
            'passed': len(self.errors) == 0,
            'errors': self.errors,
            'warnings': self.warnings,
            'stats': {
                'total_rules': self.stats['total'],
                'by_category': dict(self.stats['by_category']),
                'by_file': dict(self.stats['by_file']),
                'with_validation': self.stats['with_validation'],
                'with_change_log': self.stats['with_change_log'],
                'total_dependencies': self.stats['total_dependencies'],
                'total_affects': self.stats['total_affects'],
                'error_count': len(self.errors),
                'warning_count': len(self.warnings)
            }
        }


# ──────────────────────────────────────────────
# 规则注册表
# ──────────────────────────────────────────────

class RuleRegistry:
    """规则注册表：统一管理所有已加载的 WRL 规则"""

    def __init__(self):
        self._rules: Dict[str, dict] = {}
        self._by_category: Dict[str, List[str]] = defaultdict(list)
        self._by_file: Dict[str, List[str]] = defaultdict(list)
        self._loaded_at: Optional[str] = None
        self._validation_report: Optional[dict] = None

    def register(self, rules: List[dict]):
        """注册规则"""
        for rule in rules:
            rule_id = rule['rule_id']
            self._rules[rule_id] = rule
            self._by_category[rule.get('category', '?')].append(rule_id)
            self._by_file[rule.get('file', '?')].append(rule_id)

    def get(self, rule_id: str) -> Optional[dict]:
        """获取单条规则"""
        return self._rules.get(rule_id)

    def get_all(self) -> Dict[str, dict]:
        """获取所有规则"""
        return self._rules.copy()

    def get_by_category(self, category: str) -> List[dict]:
        """按分类获取规则"""
        return [self._rules[rid] for rid in self._by_category.get(category, [])]

    def get_by_file(self, filename: str) -> List[dict]:
        """按文件获取规则"""
        return [self._rules[rid] for rid in self._by_file.get(filename, [])]

    def get_dependents(self, rule_id: str) -> List[str]:
        """获取依赖某规则的所有规则"""
        deps = []
        for rid, rule in self._rules.items():
            if rule_id in rule.get('depends_on', []):
                deps.append(rid)
        return deps

    def get_dependency_graph(self) -> Dict[str, List[str]]:
        """获取依赖图"""
        graph = {}
        for rid, rule in self._rules.items():
            graph[rid] = rule.get('depends_on', [])
        return graph

    @property
    def rule_count(self) -> int:
        return len(self._rules)

    @property
    def category_counts(self) -> Dict[str, int]:
        return {cat: len(ids) for cat, ids in self._by_category.items()}

    def set_validation_report(self, report: dict):
        self._validation_report = report

    def get_validation_report(self) -> Optional[dict]:
        return self._validation_report


# ──────────────────────────────────────────────
# 主加载函数
# ──────────────────────────────────────────────

def load_wrl_rules(rules_dir: str = None, validate: bool = True) -> Tuple[RuleRegistry, dict]:
    """
    加载所有 WRL 规则并验证

    Args:
        rules_dir: WRL 规则目录路径，默认为 ../rules
        validate: 是否执行验证

    Returns:
        (RuleRegistry, validation_report)
    """
    if rules_dir is None:
        rules_dir = os.path.join(os.path.dirname(__file__), '..', 'rules')

    if not os.path.isdir(rules_dir):
        raise FileNotFoundError(f"规则目录不存在: {rules_dir}")

    # 解析
    parser = WrlParser(rules_dir)
    files_rules = parser.parse_all()

    # 注册
    registry = RuleRegistry()
    for filepath, rules in files_rules.items():
        registry.register(rules)

    # 验证
    report = None
    if validate:
        validator = RuleValidator()
        passed, report = validator.validate(registry.get_all())
        registry.set_validation_report(report)

    registry._loaded_at = datetime.now().isoformat()
    return registry, report


def generate_loading_report(registry: RuleRegistry, report: dict) -> str:
    """生成格式化的规则加载报告 (Markdown)"""
    lines = []
    lines.append('# WRL 规则加载报告')
    lines.append(f'> 加载时间: {registry._loaded_at}')
    lines.append(f'> 规则总数: {registry.rule_count}')
    lines.append('')

    # 验证状态
    if report:
        passed = report['passed']
        lines.append(f'## 验证状态: {"✅ 全部通过" if passed else "❌ 存在错误"}')
        lines.append('')
        if report['errors']:
            lines.append('### 错误')
            for err in report['errors']:
                lines.append(f'- ❌ {err}')
            lines.append('')
        if report['warnings']:
            lines.append('### 警告')
            for warn in report['warnings']:
                lines.append(f'- ⚠️ {warn}')
            lines.append('')

    # 统计
    stats = report['stats'] if report else {}
    lines.append('## 统计')
    lines.append('')
    lines.append('| 指标 | 数值 |')
    lines.append('|------|------|')
    lines.append(f'| 规则总数 | {registry.rule_count} |')
    for cat, count in sorted(registry.category_counts.items()):
        cat_name = CATEGORY_NAMES.get(cat, cat)
        lines.append(f'| {cat_name} ({cat}) | {count} |')
    lines.append(f'| 含 validation | {stats.get("with_validation", "?")} |')
    lines.append(f'| 含 change_log | {stats.get("with_change_log", "?")} |')
    lines.append(f'| 总依赖数 | {stats.get("total_dependencies", "?")} |')
    lines.append(f'| 总 affects | {stats.get("total_affects", "?")} |')
    lines.append('')

    # 按文件列出规则
    lines.append('## 规则清单')
    lines.append('')
    for filename in sorted(set(r.get('file', '?') for r in registry.get_all().values())):
        file_rules = registry.get_by_file(filename)
        lines.append(f'### {filename} ({len(file_rules)} 条)')
        lines.append('')
        lines.append('| 规则 ID | 分类 | 名称 | 可修改性 | 依赖数 | 有校验 | 有变更日志 |')
        lines.append('|---------|------|------|----------|--------|--------|-----------|')
        for rule in file_rules:
            lines.append(
                f'| `{rule["rule_id"]}` | {rule.get("category", "?")} | '
                f'{rule.get("name", "?")} | {rule.get("mutability", "?")} | '
                f'{len(rule.get("depends_on", []))} | '
                f'{"✅" if rule.get("has_validation") else "❌"} | '
                f'{"✅" if rule.get("has_change_log") else "❌"} |'
            )
        lines.append('')

    # 依赖图
    lines.append('## 依赖关系')
    lines.append('')
    graph = registry.get_dependency_graph()
    for rid, deps in sorted(graph.items()):
        if deps:
            dep_names = [f'`{d}`' for d in deps]
            lines.append(f'- `{rid}` → {", ".join(dep_names)}')
    lines.append('')

    lines.append('---')
    lines.append(f'*报告由 `wrl_loader.py` 自动生成*')

    return '\n'.join(lines)


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────

if __name__ == '__main__':
    import sys

    rules_dir = sys.argv[1] if len(sys.argv) > 1 else None

    print('=' * 60)
    print('  WRL 规则加载器')
    print('=' * 60)

    # 加载
    registry, report = load_wrl_rules(rules_dir)

    # 打印报告
    md_report = generate_loading_report(registry, report)
    print(md_report)

    # 保存报告
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'output', 'reports')
    os.makedirs(output_dir, exist_ok=True)
    report_path = os.path.join(output_dir, 'wrl_loader_report.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(md_report)
    print(f'\n报告已保存: {report_path}')

    # 保存 JSON 格式
    json_path = os.path.join(output_dir, 'wrl_loader_report.json')
    json_report = {
        'loaded_at': registry._loaded_at,
        'rule_count': registry.rule_count,
        'category_counts': registry.category_counts,
        'validation': report
    }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_report, f, ensure_ascii=False, indent=2)
    print(f'JSON 报告已保存: {json_path}')

    # 退出码
    if report and not report['passed']:
        print(f'\n❌ 验证失败: {len(report["errors"])} 个错误, {len(report["warnings"])} 个警告')
        sys.exit(1)
    else:
        print(f'\n✅ 全部通过 ({registry.rule_count} 条规则)')
        sys.exit(0)