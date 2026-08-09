#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双源时间序列一致性验证器
========================
验证 arXiv + BAAI 三个月（6-8月）数据的：
  1. 文件存在性与格式完整性
  2. 五行分布一致性（跨源对比）
  3. 月度趋势方向一致性
  4. 去重计数自洽性
"""

import json
from collections import Counter
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
MONTHS = ["2026-06", "2026-07", "2026-08"]

# 五行顺序
WX_ORDER = ["木", "火", "土", "金", "水"]


def load_tree(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"_error": str(e)}


def wx_distribution(tree: dict) -> dict:
    """提取五行分布 {wx: weight}"""
    dist = Counter()
    for node in tree.get("nodes", []):
        dist[node.get("wuxing", "未知")] += node.get("weight", 0)
    return dict(dist)


def print_bar(label, count, total):
    pct = count / total * 100 if total else 0
    bar = "█" * int(pct / 2)
    print(f"  {label}: {count:6d} 篇 ({pct:5.1f}%) {bar}")


def main():
    print("=" * 70)
    print("双源时间序列一致性验证 (arXiv + BAAI)")
    print("=" * 70)

    arxiv_data = {}
    baai_data = {}
    issues = []

    # ── 检查点 1: 文件存在性与 total_weight 非零 ──
    print("\n[检查点 1] 文件存在性与数据完整性")
    print("-" * 50)
    for m in MONTHS:
        ym = m.replace("-", "")
        af = OUTPUT_DIR / f"arxiv_ai_tree_{ym}.json"
        bf = OUTPUT_DIR / f"baai_tree_{ym}.json"

        at = load_tree(af)
        bt = load_tree(bf)

        arxiv_data[m] = at
        baai_data[m] = bt

        a_ok = at and at.get("meta", {}).get("total_weight", 0) > 0
        b_ok = bt and bt.get("meta", {}).get("total_weight", 0) > 0

        a_status = f"✓ {at['meta']['total_weight']} 篇" if a_ok else ("✗ 空" if at else "✗ 缺失")
        b_status = f"✓ {bt['meta']['total_weight']} 篇" if b_ok else ("✗ 空" if bt else "✗ 缺失")

        print(f"  {m}: arXiv={a_status}, BAAI={b_status}")

        if not a_ok:
            issues.append(f"[{m}] arXiv 文件缺失或为空")
        if not b_ok and m != "2026-08":
            issues.append(f"[{m}] BAAI 文件缺失或为空")
        if not b_ok and m == "2026-08":
            print(f"    → BAAI 8月报尚未发布，预期为空")

    # ── 检查点 2: 五行分布跨源对比 ──
    print("\n[检查点 2] 五行分布对比 (arXiv vs BAAI)")
    print("-" * 50)

    for m in MONTHS:
        at = arxiv_data.get(m)
        bt = baai_data.get(m)
        if not at or not at.get("meta", {}).get("total_weight", 0):
            continue
        if not bt or not bt.get("meta", {}).get("total_weight", 0):
            if m != "2026-08":
                print(f"  [{m}] BAAI 数据缺失，跳过")
            continue

        awx = wx_distribution(at)
        bwx = wx_distribution(bt)
        a_total = at["meta"]["total_weight"]
        b_total = bt["meta"]["total_weight"]

        print(f"\n  [{m}] arXiv ({a_total} 篇) vs BAAI ({b_total} 篇):")
        print(f"  {'五行':4s} {'arXiv':>8s} {'arXiv%':>7s} {'BAAI':>8s} {'BAAI%':>7s} {'差异':>7s}")

        for wx in WX_ORDER:
            a_count = awx.get(wx, 0)
            b_count = bwx.get(wx, 0)
            a_pct = a_count / a_total * 100
            b_pct = b_count / b_total * 100
            diff = a_pct - b_pct
            flag = " ⚠" if abs(diff) > 15 else ""
            print(f"  {wx:4s} {a_count:8d} {a_pct:6.1f}% {b_count:8d} {b_pct:6.1f}% {diff:+7.1f}%{flag}")

            if abs(diff) > 15:
                issues.append(f"[{m}] 五行'{wx}'跨源差异 {diff:+.1f}% > 15%")

    # ── 检查点 3: 月度趋势方向一致性 ──
    print("\n[检查点 3] 月度趋势方向一致性")
    print("-" * 50)

    for source, data in [("arXiv", arxiv_data), ("BAAI", baai_data)]:
        print(f"\n  [{source}] 月度趋势:")
        months_avail = [m for m in MONTHS if data.get(m) and data[m].get("meta", {}).get("total_weight", 0) > 0]
        if len(months_avail) < 2:
            print(f"    可用月份不足（{len(months_avail)}），跳过趋势分析")
            continue

        print(f"  {'五行':4s}", end="")
        for m in months_avail:
            print(f" {m[5:]:>8s}", end="")
        print(f" {'趋势':>6s}")

        for wx in WX_ORDER:
            print(f"  {wx:4s}", end="")
            values = []
            prev = None
            trend = ""
            for m in months_avail:
                t = data[m]
                total = t["meta"]["total_weight"]
                dist = wx_distribution(t)
                pct = dist.get(wx, 0) / total * 100
                values.append(pct)
                print(f" {pct:7.1f}%", end="")
                if prev is not None:
                    if pct > prev + 2:
                        trend += "↑"
                    elif pct < prev - 2:
                        trend += "↓"
                    else:
                        trend += "→"
                prev = pct
            print(f" {trend:>6s}")

    # ── 检查点 4: 去重自洽性 ──
    print("\n[检查点 4] 去重计数自洽性")
    print("-" * 50)

    for m in MONTHS:
        at = arxiv_data.get(m)
        if not at:
            continue
        meta = at.get("meta", {})
        total_weight = meta.get("total_weight", 0)
        unique = meta.get("unique_papers", 0)
        node_sum = sum(n.get("weight", 0) for n in at.get("nodes", []))

        print(f"  [{m}] arXiv:")
        print(f"    total_weight (meta)    = {total_weight}")
        print(f"    unique_papers (meta)   = {unique}")
        print(f"    sum(node.weight)       = {node_sum}")

        if total_weight != unique:
            issues.append(f"[{m}] arXiv total_weight({total_weight}) != unique_papers({unique})")
            print(f"    ⚠ 不一致!")
        elif total_weight != node_sum:
            issues.append(f"[{m}] arXiv total_weight({total_weight}) != sum(node.weight)({node_sum})")
            print(f"    ⚠ 不一致!")
        else:
            print(f"    ✓ 自洽")

    # ── 检查点 5: 分类数一致性 ──
    print("\n[检查点 5] 分类数一致性")
    print("-" * 50)
    for m in MONTHS:
        at = arxiv_data.get(m)
        if at:
            cats = len(at.get("nodes", []))
            cats_used = at.get("meta", {}).get("categories_used", 0)
            cats_zero = at.get("meta", {}).get("categories_zero", 0)
            print(f"  [{m}] arXiv: {cats} 分类, {cats_used} 有数据, {cats_zero} 零论文")
            if cats != 11:
                issues.append(f"[{m}] arXiv 分类数={cats}，预期 11")

    # ── 汇总 ──
    print("\n" + "=" * 70)
    print("验证汇总")
    print("=" * 70)
    if issues:
        print(f"  ⚠ 发现 {len(issues)} 个问题:")
        for i, iss in enumerate(issues, 1):
            print(f"    {i}. {iss}")
    else:
        print("  ✓ 全部检查通过")

    # 双源时间序列表
    print(f"\n[时间序列表]")
    print(f"  {'月份':10s} {'arXiv(篇)':>10s} {'BAAI(篇)':>10s} {'arXiv/BAAI':>10s}")
    for m in MONTHS:
        at = arxiv_data.get(m, {})
        bt = baai_data.get(m, {})
        a_count = at.get("meta", {}).get("total_weight", 0) if at else 0
        b_count = bt.get("meta", {}).get("total_weight", 0) if bt else 0
        ratio = f"{a_count/b_count:.1f}x" if b_count > 0 else "N/A"
        print(f"  {m:10s} {a_count:10d} {b_count:10d} {ratio:>10s}")

    return len(issues)


if __name__ == "__main__":
    exit(main())