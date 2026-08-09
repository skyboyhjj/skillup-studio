#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BAAI 知识树 → 四源统一 schema 适配器
=====================================
将现有 baai_scraper.py 输出的 papers_YYYY-MM.json 转换为
四源统一 schema 的 tree_YYYYMM.json 格式。

转换逻辑：
  - 按 domain 聚合论文数 → node.weight
  - 分配五行（基于 phase1_pipeline 的 WUXING_KW 领域映射）
  - 输出统一 schema（与 arxiv_collect.py 输出格式一致）

用法：
  python baai_to_tree.py --month 2026-07
  python baai_to_tree.py --month 2026-06 --backfill

零依赖：Python 标准库
"""

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

# BAAI 领域 → 五行映射（复用 phase1_pipeline 的 WUXING_KW.domains）
DOMAIN_WUXING = {
    "具身智能与机器人": "木",
    "多模态智能": "木",
    "生成式AI": "木",
    "智能体": "火",
    "推荐系统与信息检索": "火",
    "交叉领域智能应用": "火",
    "机器学习基础": "土",
    "AI系统与硬件": "土",
    "软件工程与编程": "土",
    "安全可信与伦理": "金",
    "知识表示与逻辑推理": "金",
    "安全、可信与伦理": "金",  # 兼容旧命名
    "大语言模型": "水",
    "自然语言处理": "水",
    "计算机视觉": "水",
    "科学AI": "水",
    "科学 AI": "水",  # 兼容空格变体
    "其他AI领域": "水",
    "其他 AI 领域": "水",
}


def classify_wuxing(domain: str) -> str:
    """BAAI 领域 → 五行"""
    # 精确匹配
    if domain in DOMAIN_WUXING:
        return DOMAIN_WUXING[domain]
    # 规范化匹配（去除空格差异）
    normalized = domain.replace(" ", "")
    for key, wx in DOMAIN_WUXING.items():
        if key.replace(" ", "") == normalized:
            return wx
    # 默认：水
    return "水"


def main():
    parser = argparse.ArgumentParser(
        description="BAAI 论文数据 → 四源统一 schema 树快照"
    )
    parser.add_argument(
        "--month", default="2026-07",
        help="月份 YYYY-MM（默认 2026-07）"
    )
    parser.add_argument(
        "--backfill", action="store_true",
        help="历史回填模式"
    )
    args = parser.parse_args()

    year, month_num = map(int, args.month.split("-"))
    month_str = args.month

    # 读取 BAAI 论文数据
    papers_path = OUTPUT_DIR / f"papers_{month_str}.json"
    if not papers_path.exists():
        print(f"错误: 找不到 {papers_path}")
        print("请先运行 baai_scraper.py 采集数据")
        return

    with open(papers_path, "r", encoding="utf-8") as f:
        papers = json.load(f)

    print(f"读取 {papers_path}: {len(papers)} 篇论文")

    # 按 domain 聚合
    domain_counts = Counter()
    for p in papers:
        domain = p.get("domain", "未知")
        domain_counts[domain] += 1

    # 构建节点树
    nodes = []
    for domain, count in domain_counts.most_common():
        wuxing = classify_wuxing(domain)
        nodes.append({
            "id": domain,
            "name": domain,
            "parent": "AI 知识树",
            "wuxing": wuxing,
            "weight": count,
        })

    tree = {
        "schema_version": "1.0",
        "source": "baai",
        "timestamp": month_str,
        "nodes": nodes,
        "meta": {
            "node_count": len(nodes),
            "total_weight": sum(domain_counts.values()),
            "domains_covered": len(domain_counts),
            "api_used": "hub-notion.baai.ac.cn/api_v2/api",
            "papers_file": f"papers_{month_str}.json",
        },
    }

    # 输出
    out_name = f"baai_tree_{year}{month_num:02d}.json"
    out_path = OUTPUT_DIR / out_name
    output = {
        **tree,
        "generated_at": datetime.now().isoformat(),
    }
    out_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 摘要
    print(f"\n{'='*60}")
    print(f"[完成] {out_path}")
    print(f"  领域数      : {len(domain_counts)}")
    print(f"  总论文数    : {sum(domain_counts.values())}")
    for domain, count in domain_counts.most_common():
        wx = classify_wuxing(domain)
        print(f"  [{wx}] {domain}: {count} 篇")
    print(f"{'='*60}")

    # 五行分布
    wx_dist = Counter()
    for node in nodes:
        wx_dist[node["wuxing"]] += node["weight"]
    total = tree["meta"]["total_weight"]
    print(f"\n[五行分布]")
    for wx in ["木", "火", "土", "金", "水"]:
        count = wx_dist.get(wx, 0)
        pct = count / total * 100 if total else 0
        bar = "█" * int(pct / 2)
        print(f"  {wx}: {count:4d} 篇 ({pct:5.1f}%) {bar}")


if __name__ == "__main__":
    main()