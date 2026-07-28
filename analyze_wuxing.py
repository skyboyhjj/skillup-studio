#!/usr/bin/env python3
"""
概念地图五行特征分析器
分析 JSON 数据集中概念的分层结构与五行属性，输出综合特征报告。
用法: python analyze_wuxing.py <json文件或目录>
"""

import json
import os
import sys
import math
from collections import Counter, defaultdict
from pathlib import Path

# ============================================================
# 五行基础定义
# ============================================================

WUXING_ORDER = ["木", "火", "土", "金", "水"]

# 相生关系: 木→火→土→金→水→木
SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}

# 相克关系: 木→土→水→火→金→木
KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

# 五行颜色 (用于可视化)
WUXING_COLORS = {
    "木": "#4CAF50", "火": "#F44336", "土": "#FF9800",
    "金": "#FFC107", "水": "#2196F3"
}

# 五行特征描述
WUXING_DESCRIPTIONS = {
    "木": "生长、创新、发散思维",
    "火": "激情、传播、感染力",
    "土": "务实、系统、结构化",
    "金": "严谨、收敛、批判性",
    "水": "深邃、内省、哲学性"
}

# 特征标签规则
FEATURE_TAGS = [
    ("体系型", lambda s: s["wuxing_pct"]["土"] > 30 and s["depth_index"] > 0.4),
    ("感染型", lambda s: s["wuxing_pct"]["火"] > 30 and s["sheng_ke_ratio"] > 2),
    ("哲思型", lambda s: s["wuxing_pct"]["水"] > 25 and s["depth_index"] > 0.5),
    ("辩证型", lambda s: s["wuxing_pct"]["金"] > 25 and s["sheng_ke_ratio"] < 0.8),
    ("生长型", lambda s: s["wuxing_pct"]["木"] > 30 and s["breadth_index"] > 0.4),
    ("均衡型", lambda s: s["wuxing_balance"] > 0.85),
]


def load_json(path):
    """加载 JSON 文件"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def analyze_wuxing_distribution(concepts):
    """分析五行分布"""
    total = len(concepts)
    if total == 0:
        return {"counts": {}, "pct": {}, "dominant": None, "balance": 0}

    counts = Counter(c.get("wuxing", "未知") for c in concepts)
    pct = {wx: round(counts.get(wx, 0) / total * 100, 1) for wx in WUXING_ORDER}

    # 主导五行
    dominant = max(counts, key=counts.get) if counts else None

    # 均衡度: 1 - 各五行占比的标准差（归一化）
    # 完全均匀时每个=20%, std=0, balance=1
    percentages = [pct[wx] for wx in WUXING_ORDER]
    mean_pct = 20.0
    variance = sum((p - mean_pct) ** 2 for p in percentages) / 5
    std_dev = math.sqrt(variance)
    # 最大可能标准差: 全部集中在1个元素=40, 其余=0 -> sqrt((1600+0+0+0+0)/5)=17.89
    max_std = 40.0
    balance = max(0, 1 - std_dev / max_std)

    return {
        "counts": {wx: counts.get(wx, 0) for wx in WUXING_ORDER},
        "pct": pct,
        "dominant": dominant,
        "dominant_pct": pct.get(dominant, 0),
        "balance": round(balance, 4),
    }


def analyze_layer_structure(rings):
    """分析层次结构特征"""
    total_concepts = sum(len(r["concepts"]) for r in rings)
    if total_concepts == 0:
        return {"depth_index": 0, "breadth_index": 0, "gradient": 0, "density": 0,
                "layer_counts": [], "layer_labels": []}

    n = len(rings)
    layer_counts = [len(rings[i]["concepts"]) for i in range(n)]
    layer_labels = [rings[i]["label"] for i in range(n)]

    # 深度指数: 最深层（第3层）概念占比
    if n >= 3:
        depth_idx = layer_counts[2] / total_concepts
    elif n == 2:
        depth_idx = layer_counts[1] / total_concepts
    else:
        depth_idx = layer_counts[0] / total_concepts

    # 广度指数: 第1层概念占比
    breadth_idx = layer_counts[0] / total_concepts

    # 层次梯度: 正=由浅入深，负=重现象轻理论
    if n >= 3:
        gradient = (layer_counts[2] - layer_counts[0]) / total_concepts
    elif n == 2:
        gradient = (layer_counts[1] - layer_counts[0]) / total_concepts
    else:
        gradient = 0

    return {
        "depth_index": round(depth_idx, 4),
        "breadth_index": round(breadth_idx, 4),
        "gradient": round(gradient, 4),
        "layer_counts": layer_counts,
        "layer_labels": layer_labels,
        "total_concepts": total_concepts,
    }


def analyze_sheng_ke(concepts):
    """分析五行生克关系

    在概念列表中，相邻概念之间形成五行关系边。
    我们统计所有概念按顺序排列时，前一个五行与后一个五行之间的生克关系。
    也统计所有两两概念组合的五行关系分布。
    """
    wuxings = [c.get("wuxing") for c in concepts if c.get("wuxing") in WUXING_ORDER]
    if len(wuxings) < 2:
        return {"sheng_edges": 0, "ke_edges": 0, "total_edges": 0,
                "sheng_ke_ratio": 1.0, "sheng_density": 0, "ke_density": 0}

    # 相邻概念的生克边
    sheng_count = 0
    ke_count = 0
    for i in range(len(wuxings) - 1):
        if SHENG.get(wuxings[i]) == wuxings[i + 1]:
            sheng_count += 1
        if KE.get(wuxings[i]) == wuxings[i + 1]:
            ke_count += 1

    total_edges = len(wuxings) - 1

    # 生克比
    sheng_ke_ratio = sheng_count / ke_count if ke_count > 0 else (sheng_count if sheng_count > 0 else 1.0)

    # 密度
    sheng_density = sheng_count / total_edges if total_edges > 0 else 0
    ke_density = ke_count / total_edges if total_edges > 0 else 0

    return {
        "sheng_edges": sheng_count,
        "ke_edges": ke_count,
        "total_edges": total_edges,
        "sheng_ke_ratio": round(sheng_ke_ratio, 2),
        "sheng_density": round(sheng_density, 4),
        "ke_density": round(ke_density, 4),
    }


def analyze_per_layer_wuxing(rings):
    """逐层分析五行分布"""
    result = []
    for ring in rings:
        concepts = ring["concepts"]
        wuxing_counts = Counter(c.get("wuxing", "未知") for c in concepts)
        total = len(concepts)
        result.append({
            "layer": ring["label"],
            "total": total,
            "wuxing": {wx: {
                "count": wuxing_counts.get(wx, 0),
                "pct": round(wuxing_counts.get(wx, 0) / total * 100, 1) if total > 0 else 0
            } for wx in WUXING_ORDER},
            "dominant": max(wuxing_counts, key=wuxing_counts.get) if wuxing_counts else None,
        })
    return result


def classify_features(stats):
    """根据指标给文章打特征标签"""
    tags = []
    for tag_name, rule in FEATURE_TAGS:
        if rule(stats):
            tags.append(tag_name)
    if not tags:
        tags.append("未分类")
    return tags


def summarize_article(stats):
    """生成一句话总结"""
    dom = stats["wuxing_dist"]["dominant"]
    dom_pct = stats["wuxing_dist"]["dominant_pct"]
    balance = stats["wuxing_dist"]["balance"]
    grad = stats["layer_structure"]["gradient"]

    if dom_pct >= 40:
        focus = f"以{dom}性为主"
    elif balance > 0.85:
        focus = "五行均衡"
    else:
        top2 = sorted(stats["wuxing_dist"]["pct"].items(), key=lambda x: -x[1])[:2]
        focus = "".join(f"{wx}{pct}%" for wx, pct in top2)

    if grad > 0.1:
        depth = "由浅入深"
    elif grad < -0.1:
        depth = "重现象轻理论"
    else:
        depth = "层次均匀"

    tags = stats["feature_tags"]
    tag_str = "、".join(tags) if tags else "暂无标签"

    return f"{focus}，{depth} —— {tag_str}"


def analyze_file(filepath):
    """分析单个 JSON 文件"""
    try:
        data = load_json(filepath)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return {"file": os.path.basename(filepath), "error": str(e)}
    rings = data.get("rings", [])

    # 收集所有概念
    all_concepts = []
    for ring in rings:
        all_concepts.extend(ring["concepts"])

    # 各项分析
    wuxing_dist = analyze_wuxing_distribution(all_concepts)
    layer_structure = analyze_layer_structure(rings)
    sheng_ke = analyze_sheng_ke(
        sorted(all_concepts, key=lambda c: rings.index(
            next(r for r in rings if c in r["concepts"])
        ))
    )
    per_layer = analyze_per_layer_wuxing(rings)

    stats = {
        "wuxing_pct": wuxing_dist["pct"],
        "wuxing_dist": wuxing_dist,
        "layer_structure": layer_structure,
        "sheng_ke": sheng_ke,
        "depth_index": layer_structure["depth_index"],
        "breadth_index": layer_structure["breadth_index"],
        "wuxing_balance": wuxing_dist["balance"],
        "sheng_ke_ratio": sheng_ke["sheng_ke_ratio"],
    }

    tags = classify_features(stats)
    stats["feature_tags"] = tags
    summary = summarize_article(stats)

    return {
        "file": os.path.basename(filepath),
        "title": rings[0]["label"] if rings else "未知",
        "total_concepts": layer_structure["total_concepts"],
        "wuxing_distribution": wuxing_dist,
        "layer_structure": layer_structure,
        "sheng_ke": sheng_ke,
        "per_layer_wuxing": per_layer,
        "feature_tags": tags,
        "summary": summary,
    }


def print_report(results):
    """打印分析报告"""
    for r in results:
        if "error" in r:
            print(f"  ⚠ {r['file']}: 解析失败 ({r['error']})")
            print()
            continue

        print("=" * 72)
        print(f"  📄 {r['file']}")
        print(f"     概念总数: {r['total_concepts']}")
        print()

        # 五行分布
        print("  ── 五行分布 ──")
        wd = r["wuxing_distribution"]
        bar_width = 30
        for wx in WUXING_ORDER:
            cnt = wd["counts"][wx]
            pct = wd["pct"][wx]
            bar = "█" * int(pct / 100 * bar_width) + "░" * (bar_width - int(pct / 100 * bar_width))
            desc = WUXING_DESCRIPTIONS[wx]
            print(f"    {wx}  {bar}  {pct:5.1f}%  ({cnt}个)  {desc}")
        print(f"    主导五行: {wd['dominant']} ({wd['dominant_pct']}%)")
        print(f"    均衡度:   {wd['balance']:.2f}  (1.0=完全均衡)")

        # 层次结构
        print()
        print("  ── 层次结构 ──")
        ls = r["layer_structure"]
        for i, (label, cnt) in enumerate(zip(ls["layer_labels"], ls["layer_counts"])):
            pct = cnt / ls["total_concepts"] * 100
            bar = "▓" * int(pct / 100 * 30) + "▒" * (30 - int(pct / 100 * 30))
            print(f"    {label:8s}  {bar}  {pct:5.1f}%  ({cnt}个)")
        print(f"    深度指数: {ls['depth_index']:.2f}  (越高越偏理论/抽象)")
        print(f"    广度指数: {ls['breadth_index']:.2f}  (越高越偏现象/具体)")
        print(f"    层次梯度: {ls['gradient']:+.2f}  (正=由浅入深, 负=重现象轻理论)")

        # 生克关系
        print()
        print("  ── 五行生克关系 ──")
        sk = r["sheng_ke"]
        print(f"    相生边: {sk['sheng_edges']}  相克边: {sk['ke_edges']}  总边: {sk['total_edges']}")
        print(f"    生克比: {sk['sheng_ke_ratio']:.2f}  (>1偏建构, <1偏解构)")
        print(f"    相生密度: {sk['sheng_density']:.2f}  相克密度: {sk['ke_density']:.2f}")

        # 逐层五行
        print()
        print("  ── 逐层五行分布 ──")
        for layer in r["per_layer_wuxing"]:
            parts = []
            for wx in WUXING_ORDER:
                info = layer["wuxing"][wx]
                if info["count"] > 0:
                    parts.append(f"{wx}:{info['count']}")
            print(f"    {layer['layer']:8s}  ({layer['total']}个)  {'  '.join(parts)}  → 主导: {layer['dominant']}")

        # 特征标签 + 总结
        print()
        print("  ── 综合评定 ──")
        print(f"    特征标签: {'  '.join(r['feature_tags'])}")
        print(f"    一句话总结: {r['summary']}")
        print()


def main():
    if len(sys.argv) < 2:
        print("用法: python analyze_wuxing.py <json文件或目录>")
        sys.exit(1)

    target = sys.argv[1]
    results = []

    if os.path.isfile(target):
        results.append(analyze_file(target))
    elif os.path.isdir(target):
        json_files = sorted(Path(target).glob("*.json"))
        if not json_files:
            print(f"目录 {target} 中没有找到 JSON 文件")
            sys.exit(1)
        for f in json_files:
            results.append(analyze_file(str(f)))
    else:
        print(f"路径不存在: {target}")
        sys.exit(1)

    print_report(results)

    # 对比摘要
    valid_results = [r for r in results if "error" not in r]
    if len(valid_results) > 1:
        print("=" * 72)
        print("  📊 对比摘要")
        print()
        print(f"  {'文件':<30s} {'概念':>4s} {'主导':>4s} {'均衡度':>6s} {'深度':>6s} {'生克比':>6s} {'标签'}")
        print(f"  {'-'*30} {'-'*4} {'-'*4} {'-'*6} {'-'*6} {'-'*6} {'-'*20}")
        for r in valid_results:
            name = r["file"][:28]
            wd = r["wuxing_distribution"]
            ls = r["layer_structure"]
            sk = r["sheng_ke"]
            tags = " ".join(r["feature_tags"])
            print(f"  {name:<30s} {r['total_concepts']:>4d} {wd['dominant']:>4s} "
                  f"{wd['balance']:>6.2f} {ls['depth_index']:>6.2f} {sk['sheng_ke_ratio']:>6.2f} {tags}")
        print()


if __name__ == "__main__":
    main()