"""
数据验证模块 — 可复用的采集数据验证工具

基于《网站数据采集经验总结》§5 五个检查点 + §7 可复用模板：
1. 语言检测: 检查每条标题是否包含英文字母
2. 数量一致性: 对比 API 返回条数与实际有效条数
3. 领域覆盖: 检查是否所有目标领域都有数据
4. 重复检测: 同一领域内标题去重
5. 格式一致性: 同领域不同月份格式是否一致

用法:
    from data_validator import validate_papers_batch, check_cross_month_consistency
    from data_validator import validate_all, ValidationReport
"""

import re
from collections import Counter, defaultdict


# 非论文文本特征模式（中文段落，非论文标题）
NON_PAPER_PATTERNS = [
    re.compile(r'^本月研究'), re.compile(r'^当前.*研究'),
    re.compile(r'^研究趋势'), re.compile(r'^本[月季度]'),
    re.compile(r'^AI.*呈现'), re.compile(r'^在.*方面'),
    re.compile(r'^如何'), re.compile(r'^为什么'),
    re.compile(r'^论文.*在.*方面'), re.compile(r'^[^\w]*$'),
]


def is_english_title(title):
    """
    检查点 1: 语言检测
    判断是否为英文论文标题（英文论文标题通常以字母为主）
    """
    alpha = sum(1 for c in title if c.isascii() and c.isalpha())
    total = len(title)
    if total == 0:
        return False
    return alpha / total > 0.6


def is_likely_paper_title(title):
    """
    检查点 2: 判断文本是否像论文标题（而非摘要、段落、列表项说明）
    """
    t = title.strip()

    if len(t) < 10:
        return False

    if len(t) > 100:
        cn_chars = sum(1 for c in t if '\u4e00' <= c <= '\u9fff')
        if cn_chars > 10:
            return False

    for pat in NON_PAPER_PATTERNS:
        if pat.match(t):
            return False

    return True


def clean_title(title):
    """清理论文标题"""
    title = title.strip()
    title = re.sub(r'^[\d]+[\.\、\)]\s*', '', title)
    title = title.strip('"\'""''')
    return title


def validate_papers_batch(papers):
    """
    文档 §7.1: 可复用的论文验证模板

    对一批论文标题执行完整验证：
    - 语言检测 (英文占比)
    - 数量统计
    - 标记需要人工复核的批次

    Args:
        papers: list of paper title strings

    Returns:
        dict with total, english_titles, english_ratio, needs_review
    """
    total = len(papers)
    if total == 0:
        return {'total': 0, 'english_titles': 0, 'english_ratio': 0.0, 'needs_review': True}

    english = sum(1 for t in papers if any(c.isascii() and c.isalpha() for c in t[:20]))
    ratio = english / total
    return {
        'total': total,
        'english_titles': english,
        'english_ratio': round(ratio, 4),
        'needs_review': ratio < 0.8
    }


def check_domain_coverage(domains_with_data, expected_domains):
    """
    检查点 3: 领域覆盖检查

    Args:
        domains_with_data: set of domain names that have data
        expected_domains: list of all expected domain names

    Returns:
        dict with covered, missing, coverage_ratio
    """
    covered = set(domains_with_data) & set(expected_domains)
    missing = set(expected_domains) - set(domains_with_data)
    return {
        'covered': sorted(covered),
        'missing': sorted(missing),
        'coverage_ratio': round(len(covered) / max(len(expected_domains), 1), 4)
    }


def check_duplicates(papers, key='title'):
    """
    检查点 4: 重复检测

    Args:
        papers: list of dicts with paper data
        key: the field to use for dedup (default: 'title')

    Returns:
        dict with unique_count, duplicate_count, duplicate_ratio
    """
    seen = set()
    unique = []
    for p in papers:
        val = p.get(key, '').strip().lower()
        if val and val not in seen:
            seen.add(val)
            unique.append(p)

    dupes = len(papers) - len(unique)
    return {
        'unique_count': len(unique),
        'duplicate_count': dupes,
        'duplicate_ratio': round(dupes / max(len(papers), 1), 4),
        'unique_items': unique
    }


def check_cross_month_consistency(all_data):
    """
    检查点 5: 同领域不同月份格式一致性检查

    同一领域的不同月份报告，论文标题的语言/格式应该一致。
    不一致 → 可能是模板切换或数据异常（如软件工程与编程 5 月的中文摘要问题）。

    Args:
        all_data: {month_key: [{title, domain, is_english}, ...]}

    Returns:
        list of issue dicts with domain, month, ratio, other_avg, issue
    """
    issues = []
    domain_monthly = defaultdict(lambda: defaultdict(list))

    for month, papers in all_data.items():
        for p in papers:
            domain_monthly[p['domain']][month].append(p.get('is_english', False))

    for domain, months in domain_monthly.items():
        ratios = {}
        for month, flags in months.items():
            if flags:
                ratios[month] = sum(flags) / len(flags)

        if len(ratios) >= 2:
            for month, ratio in ratios.items():
                other_ratios = [v for m, v in ratios.items() if m != month]
                if other_ratios:
                    avg_other = sum(other_ratios) / len(other_ratios)
                    if abs(ratio - avg_other) > 0.5:
                        issues.append({
                            'domain': domain,
                            'month': month,
                            'ratio': round(ratio, 3),
                            'other_avg': round(avg_other, 3),
                            'issue': f'{domain} {month}月 英文占比 {ratio:.1%} vs 其他月份 {avg_other:.1%}，差异显著'
                        })

    return issues


class ValidationReport:
    """
    完整的验证报告，汇总五个检查点
    """

    def __init__(self, name=''):
        self.name = name
        self.checkpoints = {}

    def add_checkpoint(self, name, result):
        self.checkpoints[name] = result

    @property
    def passed(self):
        return all(self._check_passed(name, result)
                   for name, result in self.checkpoints.items())

    def _check_passed(self, name, result):
        if name == 'language':
            return not result.get('needs_review', True)
        if name == 'coverage':
            return result.get('coverage_ratio', 0) >= 0.8
        if name == 'duplicates':
            return result.get('duplicate_ratio', 0) <= 0.05
        if name == 'consistency':
            return len(result) == 0
        return True

    def summary(self):
        lines = [f"验证报告: {self.name}" if self.name else "验证报告"]
        for name, result in self.checkpoints.items():
            status = '✓' if self._check_passed(name, result) else '⚠'
            lines.append(f"  {status} {name}")
        lines.append(f"  总体: {'✓ 通过' if self.passed else '⚠ 存在问题'}")
        return '\n'.join(lines)


# ============================================================
# 树文件级验证（七检查点 #1-6，Phase B 质量门）
# ============================================================

VALID_WUXING = {"木", "火", "土", "金", "水"}


def validate_tree_file(tree: dict, source: str, month: str,
                       history: dict = None) -> dict:
    """
    树文件级七检查点 #1-6。
    
    Args:
        tree: 树文件 JSON 对象
        source: 数据源标识（arxiv/baai/github/huggingface）
        month: 月份 YYYY-MM
        history: {source: {month: n_nodes}} 近 3 月历史（检查点 4 用）
    
    Returns:
        {checkpoint: "pass"|"FAIL(reason)"|"warn(message)"}
    """
    results = {}
    nodes = tree.get("nodes", [])
    n_nodes = len(nodes)

    # --- 检查点 1: schema 完整性 ---
    schema_ok = True
    missing = []
    if "schema_version" not in tree:
        missing.append("schema_version")
        schema_ok = False
    if "source" not in tree:
        missing.append("source")
        schema_ok = False
    for i, node in enumerate(nodes):
        for field in ["id", "name", "weight"]:
            if field not in node:
                missing.append(f"nodes[{i}].{field}")
                schema_ok = False
    results["schema"] = "pass" if schema_ok else f"FAIL(missing: {missing})"

    # --- 检查点 2: 五行合法性 ---
    bad_wuxing = []
    for i, node in enumerate(nodes):
        wx = node.get("wuxing")
        if wx is not None and wx not in VALID_WUXING:
            bad_wuxing.append(f"nodes[{i}].wuxing={wx}")
    results["wuxing"] = "pass" if not bad_wuxing else f"FAIL({bad_wuxing})"

    # --- 检查点 3: 权重为正 ---
    zero_or_neg = []
    for i, node in enumerate(nodes):
        w = node.get("weight", 0)
        if w <= 0:
            zero_or_neg.append(f"nodes[{i}].weight={w}")
    results["weight"] = "pass" if not zero_or_neg else f"warn({zero_or_neg})"

    # --- 检查点 4: 量级合理性 ---
    if history and source in history:
        hist = history[source]
        if hist:
            avg = sum(hist.values()) / len(hist)
            if avg > 0:
                ratio = n_nodes / avg
                if ratio > 3:
                    results["volume"] = f"warn(n_nodes={n_nodes}, 近3月均值={avg:.0f}, 比率={ratio:.1f}x > 3x)"
                elif ratio < 0.3:
                    results["volume"] = f"warn(n_nodes={n_nodes}, 近3月均值={avg:.0f}, 比率={ratio:.1f}x < 0.3x)"
                else:
                    results["volume"] = "pass"
            else:
                results["volume"] = "pass"
        else:
            results["volume"] = "pass"
    else:
        results["volume"] = "pass"

    # --- 检查点 5: 空月检测 ---
    if n_nodes == 0:
        results["empty"] = "FAIL(n=0, 建议回退至前一有效月)"
    else:
        results["empty"] = "pass"

    # --- 检查点 6: 截断检测 ---
    meta = tree.get("meta", {})
    if meta.get("truncation_warning"):
        results["truncation"] = f"warn({meta['truncation_warning']})"
    elif "MAX_PAGES" in str(meta.get("collector", "")):
        results["truncation"] = "warn(采集器有 MAX_PAGES 限制，可能截断)"
    else:
        results["truncation"] = "pass"

    return results


def validate_tree_files_batch(tree_files: dict) -> dict:
    """
    批量验证多源多月树文件。
    
    Args:
        tree_files: {(source, month): tree_dict}
    
    Returns:
        {(source, month): {checkpoint: result}}
    """
    # 构建历史数据（近 3 月 n_nodes）
    history = {}
    for (source, month), tree in tree_files.items():
        history.setdefault(source, {})[month] = len(tree.get("nodes", []))

    results = {}
    for (source, month), tree in tree_files.items():
        # 近 3 月（不含当前月）
        hist = {m: n for m, n in history.get(source, {}).items() if m < month}
        hist = dict(sorted(hist.items())[-3:])
        results[(source, month)] = validate_tree_file(tree, source, month, {source: hist})

    return results


def validate_all(all_data, expected_domains=None):
    """
    一键执行所有五个检查点的验证

    Args:
        all_data: {month_key: [{title, domain, is_english}, ...]}
        expected_domains: optional list of expected domain names

    Returns:
        ValidationReport
    """
    report = ValidationReport(name='BAAI Hub 论文采集')

    # 1. 语言检测
    all_papers = []
    for month, papers in all_data.items():
        all_papers.extend(papers)
    report.add_checkpoint('language', validate_papers_batch(
        [p['title'] for p in all_papers]
    ))

    # 2. 数量一致性
    total_raw = sum(len(papers) for papers in all_data.values())
    total_clean = sum(1 for p in all_papers if is_likely_paper_title(p['title']))
    report.add_checkpoint('quantity', {
        'raw': total_raw,
        'clean': total_clean,
        'loss_ratio': round(1 - total_clean / max(total_raw, 1), 4)
    })

    # 3. 领域覆盖
    if expected_domains:
        covered_domains = set(p['domain'] for p in all_papers)
        report.add_checkpoint('coverage', check_domain_coverage(covered_domains, expected_domains))

    # 4. 重复检测
    report.add_checkpoint('duplicates', check_duplicates(all_papers))

    # 5. 跨月格式一致性
    report.add_checkpoint('consistency', check_cross_month_consistency(all_data))

    return report


if __name__ == '__main__':
    import json
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # 加载已有数据验证
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output')
    months = ['05', '06', '07']

    all_data = {}
    for m in months:
        label = f'2026-{m}'
        path = os.path.join(output_dir, f'papers_{label}.json')
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                papers = json.load(f)
            all_data[m] = [
                {'title': p['title'], 'domain': p.get('domain', ''), 'is_english': is_english_title(p['title'])}
                for p in papers
            ]
            print(f"加载 {label}: {len(papers)} 篇")

    if all_data:
        report = validate_all(all_data)
        print('\n' + report.summary())
    else:
        print('未找到论文数据文件')