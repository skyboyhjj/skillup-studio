#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
arXiv API 小规模测试脚本（W1）
==============================
验证目标：
  1. 提取逻辑：title / published / category / author 字段提取正确
  2. 合规性：请求间隔 ≥3 秒、User-Agent 标识、分页控制
  3. 数据形态：输出与四源统一 schema 兼容的样例 JSON

用法（PowerShell）：
  python test_arxiv.py                       # 默认：cs.AI / 2026-07 / 100 条
  python test_arxiv.py --category cs.LG --month 2026-06 --max 50

零依赖：urllib + xml.etree（Python 标准库）
"""

import argparse
import json
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

# ============ 配置 ============
ARXIV_API_URL = "http://export.arxiv.org/api/query"
USER_AGENT = "wuxing-flowengine-test/0.1 (harmless verification; contact: local research)"
MIN_INTERVAL = 3.0  # 合规：请求最小间隔（秒）
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom",
           "arxiv": "http://arxiv.org/schemas/atom"}


# ============ 合规工具 ============
class PoliteFetcher:
    """合规请求器：间隔控制 + User-Agent 标识 + 请求日志"""

    def __init__(self, min_interval=MIN_INTERVAL, user_agent=USER_AGENT):
        self.min_interval = min_interval
        self.user_agent = user_agent
        self.last_request_time = 0.0
        self.request_log = []

    def fetch(self, url):
        # 间隔控制
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()

        # 请求（带 UA 标识）
        req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
        dt = time.time() - t0

        self.request_log.append({
            "url": url[:120] + "..." if len(url) > 120 else url,
            "status": 200,
            "latency_s": round(dt, 2),
            "interval_ok": elapsed >= self.min_interval - 0.1,
        })
        return body

    def compliance_report(self):
        """合规报告：请求数、间隔检查、平均延迟"""
        n = len(self.request_log)
        if n == 0:
            return {"requests": 0, "note": "无请求"}
        intervals_ok = all(r["interval_ok"] for r in self.request_log)
        avg_latency = sum(r["latency_s"] for r in self.request_log) / n
        return {
            "requests": n,
            "interval_compliant": intervals_ok,
            "avg_latency_s": round(avg_latency, 2),
            "min_interval_s": MIN_INTERVAL,
            "user_agent": USER_AGENT,
            "note": "间隔合规" if intervals_ok else "存在间隔不足，需检查",
        }


# ============ 查询构建 ============
def build_query(category: str, year: int, month: int) -> str:
    """构建 arXiv API 查询：单分类单月"""
    start = f"{year}{month:02d}010000"
    end = f"{year}{month:02d}312359"
    query = f'cat:{category} AND submittedDate:[{start} TO {end}]'
    return query


def build_url(query: str, start: int, max_results: int) -> str:
    """构建分页 URL"""
    params = urllib.parse.urlencode({
        "search_query": query,
        "start": start,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    })
    return f"{ARXIV_API_URL}?{params}"


# ============ XML 解析 ============
def parse_feed(xml_body: str):
    """解析 Atom XML → 论文条目列表"""
    root = ET.fromstring(xml_body)
    entries = []
    for entry in root.findall("atom:entry", ATOM_NS):
        title = entry.findtext("atom:title", default="", namespaces=ATOM_NS).strip()
        published = entry.findtext("atom:published", default="", namespaces=ATOM_NS)
        summary = entry.findtext("atom:summary", default="", namespaces=ATOM_NS).strip()
        # 分类（多个 category）
        categories = [c.get("term") for c in entry.findall("atom:category", ATOM_NS)]
        # 作者（多个 author）
        authors = [a.findtext("atom:name", default="", namespaces=ATOM_NS)
                   for a in entry.findall("atom:author", ATOM_NS)]
        entries.append({
            "title": title,
            "published": published,
            "month": published[:7] if published else "",   # YYYY-MM
            "categories": categories,
            "primary_category": categories[0] if categories else "",
            "author_count": len(authors),
            "summary_len": len(summary),
        })
    return entries


# ============ 主流程 ============
def main():
    parser = argparse.ArgumentParser(description="arXiv API 小规模测试（单分类单月）")
    parser.add_argument("--category", default="cs.AI", help="arXiv 分类（默认 cs.AI）")
    parser.add_argument("--month", default="2026-07", help="月份 YYYY-MM（默认 2026-07）")
    parser.add_argument("--max", type=int, default=100, help="单页条数（默认 100，测试用小规模）")
    args = parser.parse_args()

    year, month = map(int, args.month.split("-"))
    query = build_query(args.category, year, month)
    fetcher = PoliteFetcher()

    print("=" * 60)
    print(f"arXiv API 测试 | 分类={args.category} | 月份={args.month} | 单页={args.max}")
    print("=" * 60)

    # 请求第一页（小规模测试：单页即可）
    url = build_url(query, start=0, max_results=args.max)
    print(f"[请求 1/1] {url[:100]}...")
    body = fetcher.fetch(url)
    entries = parse_feed(body)

    # ===== 验证 1：提取逻辑 =====
    total_found = len(entries)
    field_complete = sum(
        1 for e in entries
        if e["title"] and e["published"] and e["categories"] and e["author_count"] > 0
    )
    month_matched = sum(1 for e in entries if e["month"] == args.month)
    primary_cat_matched = sum(1 for e in entries if e["primary_category"] == args.category)

    print(f"\n[提取验证]")
    print(f"  条目数        : {total_found}")
    print(f"  字段完整      : {field_complete}/{total_found}（title+published+category+author 齐全）")
    print(f"  月份匹配      : {month_matched}/{total_found}（published == {args.month}）")
    print(f"  主分类匹配    : {primary_cat_matched}/{total_found}（primary == {args.category}）")

    extract_ok = (total_found > 0 and field_complete == total_found
                  and month_matched == total_found and primary_cat_matched == total_found)

    # ===== 验证 2：样例输出 =====
    sample = entries[:5] if entries else []
    print(f"\n[样例（前 {len(sample)} 条）]")
    for i, e in enumerate(sample, 1):
        print(f"  {i}. [{e['primary_category']}] {e['title'][:50]}... ({e['month']})")

    # ===== 验证 3：合规报告 =====
    comp = fetcher.compliance_report()
    print(f"\n[合规报告]")
    for k, v in comp.items():
        print(f"  {k}: {v}")

    # ===== 输出文件（四源统一 schema 兼容） =====
    output = {
        "schema_version": "1.0",
        "source": "arxiv",
        "timestamp": datetime.now().strftime("%Y-%m-%d"),
        "query": {
            "category": args.category,
            "month": args.month,
            "max_results": args.max,
        },
        "nodes": [
            {
                "id": args.category,
                "name": args.category,
                "parent": args.category.split(".")[0] if "." in args.category else "",
                "wuxing": None,          # 五行标注待诊断引擎
                "weight": total_found,   # 当月论文数
            }
        ],
        "sample_entries": sample,
        "extract_validation": {
            "total": total_found,
            "field_complete": field_complete,
            "month_matched": month_matched,
            "primary_cat_matched": primary_cat_matched,
            "extract_ok": extract_ok,
        },
        "compliance": comp,
    }

    out_path = Path(f"arxiv_test_{args.category.replace('.', '_')}_{args.month}.json")
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[输出] {out_path}")

    # ===== 结论 =====
    print("\n" + "=" * 60)
    if extract_ok and comp["interval_compliant"]:
        print("结论: ✅ 提取逻辑正确 + 合规通过——可进入 W2 全分类脚本开发")
    elif extract_ok and not comp["interval_compliant"]:
        print("结论: ⚠️ 提取逻辑正确，但请求间隔不足——检查间隔配置")
    else:
        print("结论: ❌ 提取逻辑存在问题——检查分类名/月份格式/网络")
    print("=" * 60)


if __name__ == "__main__":
    main()
