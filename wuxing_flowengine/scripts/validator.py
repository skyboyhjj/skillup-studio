#!/usr/bin/env python3
"""
数据质量验证器：检查采集数据的完整性和质量
"""
import json, os
from collections import Counter


def validate_snapshot(snapshot, thresholds=None):
    """
    验证知识树快照数据

    参数:
        snapshot: {"nodes": [...], "edges": [...], "stats": {...}}
        thresholds: {"min_nodes": 290, "max_nodes": 350}

    返回:
        {"passed": bool, "checks": [...], "warnings": [...]}
    """
    if thresholds is None:
        thresholds = {"min_nodes": 290, "max_nodes": 350}

    checks = []
    warnings = []
    node_count = len(snapshot.get("nodes", []))

    # 节点数量检查
    if node_count < thresholds["min_nodes"]:
        warnings.append({
            "check": "node_count",
            "status": "FAIL",
            "detail": f"节点数 {node_count} < 最小值 {thresholds['min_nodes']}",
            "level": "CRITICAL"
        })
    elif node_count > thresholds["max_nodes"]:
        warnings.append({
            "check": "node_count",
            "status": "WARN",
            "detail": f"节点数 {node_count} > 最大值 {thresholds['max_nodes']}",
            "level": "WARNING"
        })
    else:
        checks.append({"check": "node_count", "status": "OK", "detail": f"{node_count} 个节点"})

    # 边数量检查
    edge_count = len(snapshot.get("edges", []))
    if edge_count < 500:
        warnings.append({
            "check": "edge_count",
            "status": "WARN",
            "detail": f"边数量 {edge_count} 偏低",
            "level": "WARNING"
        })
    else:
        checks.append({"check": "edge_count", "status": "OK", "detail": f"{edge_count} 条边"})

    # 层级分布检查
    level_counts = Counter()
    for n in snapshot.get("nodes", []):
        level_counts[n.get("level", 0)] += 1
    checks.append({
        "check": "level_distribution",
        "status": "OK",
        "detail": f"Level 1: {level_counts.get(1,0)}, 2: {level_counts.get(2,0)}, 3: {level_counts.get(3,0)}"
    })

    passed = not any(w.get("level") == "CRITICAL" for w in warnings)
    return {"passed": passed, "checks": checks, "warnings": warnings}


def validate_papers(paper_titles, thresholds=None):
    """
    验证论文标题数据质量

    参数:
        paper_titles: {领域名: [论文标题列表]}
        thresholds: {"min_paper_english_ratio": 0.8, "max_missing_domains": 2}

    返回:
        {"passed": bool, "checks": [...], "warnings": [...]}
    """
    if thresholds is None:
        thresholds = {"min_paper_english_ratio": 0.8, "max_missing_domains": 2}

    checks = []
    warnings = []

    total_domains = len(paper_titles)
    empty_domains = 0
    total_papers = 0
    english_papers = 0
    duplicate_papers = 0

    domain_details = []

    for domain, papers in paper_titles.items():
        n = len(papers)
        total_papers += n

        if n == 0:
            empty_domains += 1
            domain_details.append({"domain": domain, "count": 0, "status": "EMPTY"})
            continue

        # 语言检测
        en_count = sum(1 for t in papers if any(c.isascii() and c.isalpha() for c in t[:20]))
        english_papers += en_count
        en_ratio = en_count / n if n > 0 else 0

        # 重复检测
        unique = len(set(papers))
        dup_ratio = (n - unique) / n if n > 0 else 0
        duplicate_papers += (n - unique)

        status = "OK"
        if en_ratio < thresholds["min_paper_english_ratio"]:
            status = "WARN"
            warnings.append({
                "check": "english_ratio",
                "domain": domain,
                "status": "WARN",
                "detail": f"英文率 {en_ratio:.1%} < 阈值 {thresholds['min_paper_english_ratio']:.0%}",
                "level": "WARNING"
            })

        if dup_ratio > 0.05:
            status = "WARN"
            warnings.append({
                "check": "duplicate",
                "domain": domain,
                "status": "WARN",
                "detail": f"重复率 {dup_ratio:.1%}",
                "level": "INFO"
            })

        domain_details.append({
            "domain": domain,
            "count": n,
            "english_count": en_count,
            "english_ratio": round(en_ratio, 3),
            "duplicate_ratio": round(dup_ratio, 3),
            "status": status
        })

    # 领域覆盖检查
    if empty_domains > thresholds["max_missing_domains"]:
        warnings.append({
            "check": "domain_coverage",
            "status": "FAIL",
            "detail": f"{empty_domains} 个领域无数据 > 阈值 {thresholds['max_missing_domains']}",
            "level": "CRITICAL"
        })
    else:
        checks.append({
            "check": "domain_coverage",
            "status": "OK",
            "detail": f"{total_domains - empty_domains}/{total_domains} 领域有数据"
        })

    # 总体统计
    overall_en_ratio = english_papers / total_papers if total_papers > 0 else 0
    checks.append({"check": "total_papers", "status": "OK", "detail": f"{total_papers} 篇论文"})
    checks.append({
        "check": "overall_english_ratio",
        "status": "OK" if overall_en_ratio >= thresholds["min_paper_english_ratio"] else "WARN",
        "detail": f"总体英文率 {overall_en_ratio:.1%}"
    })

    passed = not any(w.get("level") == "CRITICAL" for w in warnings)
    return {
        "passed": passed,
        "checks": checks,
        "warnings": warnings,
        "details": {
            "total_domains": total_domains,
            "total_papers": total_papers,
            "empty_domains": empty_domains,
            "overall_english_ratio": round(overall_en_ratio, 3),
            "domain_details": domain_details
        }
    }


def validate_all(snapshot, paper_titles, output_dir, month_label, thresholds=None):
    """
    运行所有验证，保存结果

    返回:
        {"passed": bool, "snapshot": {...}, "papers": {...}}
    """
    if thresholds is None:
        thresholds = {
            "min_nodes": 290, "max_nodes": 350,
            "min_paper_english_ratio": 0.8, "max_missing_domains": 2
        }

    snap_result = validate_snapshot(snapshot, thresholds)
    paper_result = validate_papers(paper_titles, thresholds)

    overall_passed = snap_result["passed"] and paper_result["passed"]

    result = {
        "passed": overall_passed,
        "month": month_label,
        "snapshot": snap_result,
        "papers": paper_result
    }

    # 保存验证结果
    val_path = os.path.join(output_dir, f"{month_label}_validation.json")
    with open(val_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n  验证结果: {'✓ 通过' if overall_passed else '✗ 未通过'}")
    print(f"  快照: {len(snap_result['warnings'])} 个警告")
    print(f"  论文: {len(paper_result['warnings'])} 个警告")
    print(f"  验证报告: {val_path}")

    return result