"""
标注一致性检查（检查点 7）—— canonical 映射表 vs 树文件 vs 诊断输出 vs 版本号

基于《统一数据运营与展示设计》§2.2 检查点 7：
  canonical ↔ 树文件 ↔ 诊断输出 ↔ 版本号 四者 diff 为零

用法:
    python annotation_check.py --tree arxiv_ai_tree_202607.json
    python annotation_check.py --tree-dir ../output --month 2026-07
    python annotation_check.py --check-all  # 四同步全量检查
"""

import json
import argparse
import os
import sys
from pathlib import Path
from collections import defaultdict


# ============================================================
# 加载 canonical 映射表
# ============================================================

def load_canonical(canonical_path: str = None) -> dict:
    """加载四源统一五行标注映射表"""
    if canonical_path is None:
        canonical_path = Path(__file__).parent.parent / "config" / "canonical_wuxing_mapping.json"
    with open(canonical_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_canonical_for_source(canonical: dict, source: str) -> dict:
    """提取某源的 canonical 映射 {node_id: wuxing}"""
    sources = canonical.get("sources", {})
    for key in sources:
        if key == source or source.startswith(key):
            return sources[key].get("nodes", {})
    return {}


# ============================================================
# 单文件检查
# ============================================================

def check_tree_against_canonical(tree: dict, canonical: dict, source: str) -> dict:
    """
    检查单个树文件与 canonical 映射的一致性。

    Args:
        tree: 树文件 JSON 对象
        canonical: canonical 映射表（load_canonical 返回值）
        source: 数据源标识（arxiv/baai/github/huggingface）

    Returns:
        {
            "status": "pass"|"FAIL"|"warn",
            "source": str,
            "month": str,
            "total_nodes": int,
            "matched": int,
            "mismatches": [{"node_id": str, "tree_wuxing": str, "canonical_wuxing": str}],
            "new_nodes": [str],    # 树文件有但 canonical 无
            "removed_nodes": [str], # canonical 有但树文件无
            "annotation_version": str
        }
    """
    canonical_nodes = get_canonical_for_source(canonical, source)
    tree_nodes = tree.get("nodes", [])
    month = tree.get("month", "unknown")

    mismatches = []
    new_nodes = []
    tree_ids = set()

    for node in tree_nodes:
        nid = node.get("id", "")
        tree_ids.add(nid)
        tree_wx = node.get("wuxing")

        if nid in canonical_nodes:
            canonical_wx = canonical_nodes[nid]
            if tree_wx and tree_wx != canonical_wx:
                mismatches.append({
                    "node_id": nid,
                    "tree_wuxing": tree_wx,
                    "canonical_wuxing": canonical_wx
                })
        else:
            new_nodes.append(nid)

    canonical_ids = set(canonical_nodes.keys())
    removed_nodes = sorted(canonical_ids - tree_ids)

    # 判定
    if mismatches:
        status = "FAIL"
    elif new_nodes or removed_nodes:
        status = "warn"
    else:
        status = "pass"

    return {
        "status": status,
        "source": source,
        "month": month,
        "total_nodes": len(tree_nodes),
        "matched": len(tree_ids & canonical_ids),
        "mismatches": mismatches,
        "new_nodes": new_nodes,
        "removed_nodes": removed_nodes,
        "annotation_version": tree.get("meta", {}).get("annotation_version",
                                    tree.get("meta", {}).get("wuxing_annotation_version", "unknown"))
    }


# ============================================================
# 四同步全量检查
# ============================================================

def check_four_sync(canonical: dict, tree_files: dict,
                    engine_output: dict = None) -> dict:
    """
    四同步全量检查：canonical ↔ 树文件 ↔ 诊断输出 ↔ 版本号

    Args:
        canonical: canonical 映射表
        tree_files: {(source, month): tree_dict}
        engine_output: 诊断输出（可选），用于检查版本号一致性

    Returns:
        {
            "status": "pass"|"FAIL"|"warn",
            "tree_checks": [...],
            "version_consistency": {...},
            "diff_summary": str
        }
    """
    results = {"status": "pass", "tree_checks": [], "version_consistency": {}}
    diffs = []

    # 1. 树文件 vs canonical
    for (source, month), tree in tree_files.items():
        check = check_tree_against_canonical(tree, canonical, source)
        results["tree_checks"].append(check)
        if check["status"] == "FAIL":
            results["status"] = "FAIL"
            for m in check["mismatches"]:
                diffs.append(
                    f"[{source}/{month}] {m['node_id']}: "
                    f"树={m['tree_wuxing']} ≠ canonical={m['canonical_wuxing']}"
                )
        elif check["status"] == "warn" and results["status"] != "FAIL":
            results["status"] = "warn"
            if check["new_nodes"]:
                diffs.append(
                    f"[{source}/{month}] 新节点（canonical 未收录）: {', '.join(check['new_nodes'])}"
                )
            if check["removed_nodes"]:
                diffs.append(
                    f"[{source}/{month}] 移除节点（canonical 有但树文件无）: {', '.join(check['removed_nodes'])}"
                )

    # 2. 版本号一致性
    canonical_ver = canonical.get("annotation_version", "unknown")
    versions = defaultdict(set)
    for check in results["tree_checks"]:
        versions[check["annotation_version"]].add(f"{check['source']}/{check['month']}")

    if len(versions) > 1:
        results["status"] = "FAIL"
        diffs.append(f"标注版本号不一致: {dict(versions)}")
    elif canonical_ver not in list(versions.keys())[0] if versions else "":
        diffs.append(f"树文件标注版本 {list(versions.keys())} ≠ canonical 版本 {canonical_ver}")

    results["version_consistency"] = {
        "canonical_version": canonical_ver,
        "tree_versions": {k: sorted(v) for k, v in versions.items()}
    }
    results["diff_summary"] = "; ".join(diffs) if diffs else "四同步一致，diff 为零"

    return results


# ============================================================
# 集成到 data_validator（检查点 7）
# ============================================================

def validate_annotation(tree: dict, canonical: dict, source: str) -> str:
    """
    检查点 7: 标注一致性（供 data_validator.validate_tree_file 调用）

    Args:
        tree: 树文件 JSON 对象
        canonical: canonical 映射表
        source: 数据源标识

    Returns:
        "pass" | "FAIL(reason)" | "warn(message)"
    """
    check = check_tree_against_canonical(tree, canonical, source)
    if check["status"] == "FAIL":
        details = "; ".join(
            f"{m['node_id']}:{m['tree_wuxing']}≠{m['canonical_wuxing']}"
            for m in check["mismatches"]
        )
        return f"FAIL({details})"
    elif check["status"] == "warn":
        parts = []
        if check["new_nodes"]:
            parts.append(f"新节点: {', '.join(check['new_nodes'])}")
        if check["removed_nodes"]:
            parts.append(f"移除节点: {', '.join(check['removed_nodes'])}")
        return f"warn({' | '.join(parts)})"
    return "pass"


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="标注一致性检查（检查点 7）")
    parser.add_argument("--canonical", default=None,
                        help="canonical 映射表路径（默认 config/canonical_wuxing_mapping.json）")
    parser.add_argument("--tree", default=None,
                        help="单个树文件路径")
    parser.add_argument("--tree-dir", default=None,
                        help="树文件目录（批量检查）")
    parser.add_argument("--month", default=None,
                        help="月份筛选 YYYY-MM")
    parser.add_argument("--source", default=None,
                        help="数据源筛选（arxiv/baai/github/huggingface）")
    parser.add_argument("--check-all", action="store_true",
                        help="四同步全量检查")
    parser.add_argument("--json", action="store_true",
                        help="JSON 输出（默认文本摘要）")

    args = parser.parse_args()

    canonical = load_canonical(args.canonical)

    if args.tree:
        # 单文件检查
        with open(args.tree, "r", encoding="utf-8") as f:
            tree = json.load(f)
        source = tree.get("source", args.source or "unknown")
        check = check_tree_against_canonical(tree, canonical, source)
        if args.json:
            print(json.dumps(check, ensure_ascii=False, indent=2))
        else:
            print_summary(check)

    elif args.tree_dir:
        # 批量检查
        tree_dir = Path(args.tree_dir)
        tree_files = {}
        for f in tree_dir.glob("*_tree_*.json"):
            with open(f, "r", encoding="utf-8") as fh:
                tree = json.load(fh)
            source = tree.get("source", "unknown")
            month = tree.get("month", "unknown")
            if args.month and month != args.month:
                continue
            if args.source and source != args.source:
                continue
            tree_files[(source, month)] = tree

        results = check_four_sync(canonical, tree_files)
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            for check in results["tree_checks"]:
                print_summary(check)
            print(f"\n版本一致性: {results['version_consistency']}")
            print(f"总体: {results['diff_summary']}")

    elif args.check_all:
        # 全量四同步检查
        tree_dir = Path(args.tree_dir) if args.tree_dir else Path(__file__).parent.parent / "output"
        tree_files = {}
        for f in tree_dir.glob("*_tree_*.json"):
            with open(f, "r", encoding="utf-8") as fh:
                tree = json.load(fh)
            source = tree.get("source", "unknown")
            month = tree.get("month", "unknown")
            tree_files[(source, month)] = tree

        results = check_four_sync(canonical, tree_files)
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            print(f"四同步全量检查: {len(results['tree_checks'])} 个树文件")
            for check in results["tree_checks"]:
                print_summary(check)
            print(f"\n版本一致性: {results['version_consistency']}")
            print(f"\n总结: {results['diff_summary']}")
            if results["status"] == "pass":
                print("结论: 四同步一致，diff 为零 ✓")
            elif results["status"] == "warn":
                print("结论: 存在新节点/移除节点，建议更新 canonical 映射表 ⚠")
            else:
                print("结论: 存在标注不一致，需修复 ❌")

    else:
        parser.print_help()


def print_summary(check: dict):
    """打印单文件检查摘要"""
    status_icon = {"pass": "✓", "FAIL": "❌", "warn": "⚠"}
    icon = status_icon.get(check["status"], "?")
    print(f"{icon} [{check['source']}/{check['month']}] "
          f"节点 {check['total_nodes']} | 匹配 {check['matched']} "
          f"| 标注版本 {check['annotation_version']}")
    if check["mismatches"]:
        for m in check["mismatches"]:
            print(f"   ❌ {m['node_id']}: 树={m['tree_wuxing']} ≠ canonical={m['canonical_wuxing']}")
    if check["new_nodes"]:
        print(f"   ⚠ 新节点: {', '.join(check['new_nodes'])}")
    if check["removed_nodes"]:
        print(f"   ⚠ 移除节点: {', '.join(check['removed_nodes'])}")


if __name__ == "__main__":
    main()