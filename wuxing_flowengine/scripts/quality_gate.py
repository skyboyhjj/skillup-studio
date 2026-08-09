"""
质量门 — 七检查点统一质量报告生成

基于《统一数据运营与展示设计》§2.2：
  采集 → 质量门（七检查点）→ 诊断 → 合并 → 验证 → 展示打包

每次月度运行生成 `output/reports/quality_YYYY-MM.json`，包含：
  1. 每源×月 七检查点结果
  2. 标注一致性总览
  3. 整体裁决（是否可进入诊断）

用法:
    python quality_gate.py --month 2026-07
    python quality_gate.py --month 2026-07 --output ../output/reports
    python quality_gate.py --all  # 全量月份
"""

import json
import argparse
import os
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# 确保 scripts/ 在 path 中，以便导入同目录模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_validator import validate_tree_file, VALID_WUXING
from annotation_check import load_canonical, validate_annotation


# ============================================================
# 配置
# ============================================================

OUTPUT_DIR = Path(__file__).parent.parent / "output"
TREE_DIR = OUTPUT_DIR  # 树文件存放目录
REPORT_DIR = OUTPUT_DIR / "reports"


# ============================================================
# 树文件发现
# ============================================================

def discover_tree_files(month: str = None) -> dict:
    """
    发现所有树文件。

    Returns:
        {(source, month): {"path": str, "tree": dict}}
    """
    tree_files = {}
    for f in TREE_DIR.glob("*_tree_*.json"):
        # 跳过 ai_tree 旧格式（arxiv_ai_tree 与 arxiv_tree 重复时取 arxiv_tree）
        with open(f, "r", encoding="utf-8") as fh:
            tree = json.load(fh)

        source = tree.get("source", "unknown")
        tree_month = tree.get("month", "unknown")

        if month and tree_month != month:
            continue

        # 跳过空月（无采集数据）
        if not tree.get("nodes"):
            tree_files[(source, tree_month)] = {"path": str(f), "tree": tree}
        else:
            tree_files[(source, tree_month)] = {"path": str(f), "tree": tree}

    return tree_files


# ============================================================
# 质量门主逻辑
# ============================================================

def run_quality_gate(month: str = None) -> dict:
    """
    执行全量质量门检查。

    Args:
        month: 月份筛选 YYYY-MM（None = 所有月份）

    Returns:
        {
            "month": str,
            "generated": str,
            "checks": {(source, month): {checkpoint: result}},
            "annotation_summary": {...},
            "verdict": str,
            "warnings": [str],
            "failures": [str]
        }
    """
    canonical = load_canonical()
    tree_files = discover_tree_files(month)

    # 构建历史数据（近 3 月 n_nodes）
    history = defaultdict(dict)
    for (source, m), info in tree_files.items():
        history[source][m] = len(info["tree"].get("nodes", []))

    # 执行七检查点
    checks = {}
    all_warnings = []
    all_failures = []

    for (source, m), info in sorted(tree_files.items()):
        tree = info["tree"]

        # 近 3 月历史（不含当前月）
        hist = {k: v for k, v in history.get(source, {}).items() if k < m}
        hist = dict(sorted(hist.items())[-3:])

        # 检查点 1-6
        result = validate_tree_file(tree, source, m, {source: hist})

        # 检查点 7: 标注一致性
        result["annotation"] = validate_annotation(tree, canonical, source)

        checks[f"{source}/{m}"] = result

        # 收集警告和失败
        for ck, r in result.items():
            if r.startswith("FAIL"):
                all_failures.append(f"[{source}/{m}] {ck}: {r}")
            elif r.startswith("warn"):
                all_warnings.append(f"[{source}/{m}] {ck}: {r}")

    # 标注一致性总览
    # 过滤有效源（source 不是 "unknown"）
    annotation_summary = run_annotation_summary(checks, canonical)

    # 整体裁决
    if all_failures:
        verdict = "❌ 存在 FAIL 项，阻断进入诊断——请修复后重跑"
    elif all_warnings:
        verdict = "⚠ 存在 warning 项，建议检查后进入诊断"
    else:
        verdict = "✓ 全部通过，可进入诊断"

    return {
        "month": month or "all",
        "generated": datetime.now().isoformat(),
        "schema_version": "1.1",
        "total_sources": len(set(s for s, _ in tree_files)),
        "total_files": len(tree_files),
        "checks": {".".join(k): v for k, v in checks.items()},
        "annotation_summary": annotation_summary,
        "verdict": verdict,
        "warnings": all_warnings,
        "failures": all_failures
    }


def run_annotation_summary(checks: dict, canonical: dict) -> dict:
    """汇总标注一致性"""
    canonical_ver = canonical.get("annotation_version", "unknown")
    versions = defaultdict(list)
    mismatch_count = 0
    new_node_count = 0

    for key, result in checks.items():
        ann = result.get("annotation", "pass")
        if ann.startswith("FAIL"):
            mismatch_count += 1
        elif ann.startswith("warn"):
            new_node_count += 1

    return {
        "canonical_version": canonical_ver,
        "mismatch_count": mismatch_count,
        "new_node_count": new_node_count,
        "note": "标注版本号不一致（arxiv v1 / canonical v2 / 其他 unknown），待标准化升级"
    }


# ============================================================
# 输出
# ============================================================

def save_report(report: dict, month: str = None):
    """保存质量报告到 output/reports/"""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    month_str = month or "all"
    # 安全文件名
    safe_month = month_str.replace(":", "-").replace("/", "-")
    path = REPORT_DIR / f"quality_{safe_month}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return path


def print_summary(report: dict):
    """打印质量报告摘要"""
    print(f"\n{'='*60}")
    print(f"质量门报告 — {report['month']}")
    print(f"生成时间: {report['generated']}")
    print(f"源×月: {report['total_files']} 个文件（{report['total_sources']} 源）")
    print(f"{'='*60}")

    for key, result in report["checks"].items():
        statuses = []
        for ck in ["schema", "wuxing", "weight", "volume", "empty", "truncation", "annotation"]:
            r = result.get(ck, "?")
            if r == "pass":
                statuses.append(f"  ✓ {ck}")
            elif r.startswith("FAIL"):
                statuses.append(f"  ❌ {ck}: {r}")
            elif r.startswith("warn"):
                statuses.append(f"  ⚠ {ck}: {r}")
            else:
                statuses.append(f"  ? {ck}: {r}")
        print(f"\n[{key}]")
        for s in statuses:
            print(s)

    print(f"\n标注一致性: canonical={report['annotation_summary']['canonical_version']}, "
          f"mismatch={report['annotation_summary']['mismatch_count']}, "
          f"new_nodes={report['annotation_summary']['new_node_count']}")

    if report["warnings"]:
        print(f"\n⚠ Warnings ({len(report['warnings'])}):")
        for w in report["warnings"]:
            print(f"  {w}")

    if report["failures"]:
        print(f"\n❌ Failures ({len(report['failures'])}):")
        for f in report["failures"]:
            print(f"  {f}")

    print(f"\n裁决: {report['verdict']}")


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="质量门 — 七检查点统一质量报告")
    parser.add_argument("--month", default=None,
                        help="月份 YYYY-MM（默认全部月份）")
    parser.add_argument("--all", action="store_true",
                        help="全量月份检查")
    parser.add_argument("--output", default=None,
                        help="输出目录（默认 output/reports/）")
    parser.add_argument("--json", action="store_true",
                        help="仅输出 JSON 到 stdout")

    args = parser.parse_args()

    month = args.month if not args.all else None
    report = run_quality_gate(month)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_summary(report)
        saved = save_report(report, month)
        print(f"\n报告已保存: {saved}")


if __name__ == "__main__":
    main()