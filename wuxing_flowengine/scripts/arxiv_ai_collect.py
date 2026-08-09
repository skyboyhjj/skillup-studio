#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
arXiv AI 子领域月度采集器（W2）
================================
参考：hui-skill-product-matrix 论文采集器（11 个 AI 子领域）
     数据格式：arxiv_id/title/published/categories/authors/link/summary

功能：
  1. 11 个 AI 子领域白名单自动采集（单月）
  2. 分页拉全 + arxiv_id 全局去重
  3. 输出两份：
     - papers-YYYYMM.json  论文明细（参考原论文采集器格式）
     - ai_tree_YYYYMM.json 节点树（四源统一 schema，喂五行诊断）
  4. 合规：≥3 秒间隔 + User-Agent + 请求日志
  5. 关键词标注接口（可选：摘要关键词统计 → 子方向下钻）

用法（PowerShell）：
  python arxiv_ai_collect.py                    # 默认：最近月份 / 11 分类
  python arxiv_ai_collect.py --month 2026-07     # 指定月份
  python arxiv_ai_collect.py --categories cs.AI cs.LG   # 自定义分类

零依赖：urllib + xml.etree（Python 标准库）
"""

import argparse
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, date
from pathlib import Path

# ============ 配置 ============
ARXIV_API_URL = "http://export.arxiv.org/api/query"
USER_AGENT = "wuxing-flowengine-arxiv-collector/0.2 (monthly snapshot; non-commercial research)"
MIN_INTERVAL = 3.0          # 合规：请求最小间隔（秒）
MAX_PER_PAGE = 2000         # arXiv API 单页上限
MAX_PER_CATEGORY = 5000     # 每分类每月采集上限（保护）
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom",
           "arxiv": "http://arxiv.org/schemas/atom"}

# 11 个 AI 子领域白名单（参考论文采集器）
AI_CATEGORIES = [
    "cs.AI",   # 人工智能
    "cs.LG",   # 机器学习（含深度学习/LLM）
    "cs.CL",   # 计算与语言（NLP）
    "cs.CV",   # 计算机视觉
    "cs.NE",   # 神经与进化计算
    "cs.MA",   # 多智能体系统
    "cs.RO",   # 机器人
    "cs.HC",   # 人机交互
    "cs.IR",   # 信息检索
    "cs.MM",   # 多媒体
    "stat.ML", # 统计学习
]

# 关键词标注字典（子方向下钻用，可扩展）
KEYWORD_TOPICS = {
    "LLM/大模型": ["llm", "large language model", "gpt", "transformer"],
    "Agent/智能体": ["agent", "multi-agent", "autonomous agent"],
    "强化学习": ["reinforcement learning", "rlhf", "policy gradient"],
    "扩散模型": ["diffusion", "denoising"],
    "多模态": ["multimodal", "vision-language", "text-to-image"],
    "检索增强": ["retrieval-augmented", "rag", "retrieval augmented"],
    "图神经网络": ["graph neural", "gnn", "graph transformer"],
    "联邦学习": ["federated learning"],
    "可解释性": ["interpretab", "explainab", "xai"],
    "对齐/安全": ["alignment", "safety", "guardrail"],
}


# ============ 合规请求器（复用 test_arxiv.py 逻辑） ============
class PoliteFetcher:
    def __init__(self, min_interval=MIN_INTERVAL, user_agent=USER_AGENT):
        self.min_interval = min_interval
        self.user_agent = user_agent
        self.last_request_time = 0.0
        self.request_log = []

    def fetch(self, url):
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()
        req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
        except Exception as e:
            self.request_log.append({"url": url[:100], "status": "ERROR", "error": str(e)})
            raise
        dt = time.time() - t0
        self.request_log.append({
            "url": url[:100] + "...",
            "status": 200,
            "latency_s": round(dt, 2),
            "interval_ok": elapsed >= self.min_interval - 0.1,
        })
        return body

    def compliance_report(self):
        n = len(self.request_log)
        if n == 0:
            return {"requests": 0}
        ok = all(r.get("status") == 200 and r.get("interval_ok", True) for r in self.request_log)
        lat = [r.get("latency_s", 0) for r in self.request_log if r.get("status") == 200]
        return {
            "requests": n,
            "interval_compliant": ok,
            "avg_latency_s": round(sum(lat) / len(lat), 2) if lat else None,
            "min_interval_s": MIN_INTERVAL,
            "note": "间隔合规" if ok else "存在间隔不足或请求错误",
        }


# ============ 查询与解析 ============
def _last_day_of_month(year: int, month: int) -> int:
    import calendar
    return calendar.monthrange(year, month)[1]


def build_query(category: str, year: int, month: int) -> str:
    start = f"{year}{month:02d}010000"
    last_day = _last_day_of_month(year, month)
    end = f"{year}{month:02d}{last_day:02d}2359"
    return f'cat:{category} AND submittedDate:[{start} TO {end}]'


def build_url(query: str, start: int, max_results: int) -> str:
    params = urllib.parse.urlencode({
        "search_query": query,
        "start": start,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    })
    return f"{ARXIV_API_URL}?{params}"


def parse_feed(xml_body: str):
    root = ET.fromstring(xml_body)
    entries = []
    for entry in root.findall("atom:entry", ATOM_NS):
        arxiv_id = ""
        id_el = entry.find("atom:id", ATOM_NS)
        if id_el is not None and id_el.text:
            m = re.search(r"abs/([^v]+)", id_el.text)
            if m:
                arxiv_id = m.group(1)
        title = entry.findtext("atom:title", default="", namespaces=ATOM_NS).strip()
        published = entry.findtext("atom:published", default="", namespaces=ATOM_NS)
        summary = entry.findtext("atom:summary", default="", namespaces=ATOM_NS).strip()
        categories = [c.get("term") for c in entry.findall("atom:category", ATOM_NS)]
        authors = [a.findtext("atom:name", default="", namespaces=ATOM_NS)
                   for a in entry.findall("atom:author", ATOM_NS)]
        link = ""
        for l in entry.findall("atom:link", ATOM_NS):
            if l.get("type") == "application/pdf" or "pdf" in (l.get("title") or ""):
                link = l.get("href", "")
                break
        entries.append({
            "arxiv_id": arxiv_id,
            "title": title,
            "published": published[:10] if published else "",   # YYYY-MM-DD
            "categories": categories,
            "authors": authors,
            "link": link,
            "summary": summary,
        })
    return entries


# ============ 关键词标注（子方向下钻） ============
def annotate_topics(paper):
    """按摘要+标题关键词统计论文所属子方向（可多标签）"""
    text = (paper["title"] + " " + paper["summary"]).lower()
    topics = []
    for topic, kws in KEYWORD_TOPICS.items():
        if any(kw in text for kw in kws):
            topics.append(topic)
    return topics


# ============ 主流程 ============
def main():
    parser = argparse.ArgumentParser(description="arXiv AI 子领域月度采集器")
    parser.add_argument("--month", default=None, help="月份 YYYY-MM（默认最近月份）")
    parser.add_argument("--categories", nargs="+", default=AI_CATEGORIES,
                        help=f"分类白名单（默认 11 类：{', '.join(AI_CATEGORIES)}）")
    parser.add_argument("--annotate", action="store_true", help="启用关键词子方向标注")
    args = parser.parse_args()

    # 月份解析（默认最近完整月）
    if args.month:
        year, month = map(int, args.month.split("-"))
    else:
        today = date.today()
        year, month = (today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12)
    month_str = f"{year}-{month:02d}"

    fetcher = PoliteFetcher()
    print("=" * 64)
    print(f"arXiv AI 子领域采集 | 月份={month_str} | 分类数={len(args.categories)}")
    print("=" * 64)

    papers = {}          # arxiv_id → paper（全局去重）
    cat_counter = Counter()  # primary category 计数

    for ci, cat in enumerate(args.categories, 1):
        query = build_query(cat, year, month)
        start = 0
        cat_count = 0
        print(f"\n[{ci}/{len(args.categories)}] {cat} ...")
        while start < MAX_PER_CATEGORY:
            url = build_url(query, start, MAX_PER_PAGE)
            body = fetcher.fetch(url)
            entries = parse_feed(body)
            if not entries:
                break
            for e in entries:
                if not e["arxiv_id"]:
                    continue
                if e["arxiv_id"] not in papers:
                    papers[e["arxiv_id"]] = e
                # primary category：论文第一个 category 或白名单内匹配
                primary = next((c for c in e["categories"] if c in args.categories), e["categories"][0] if e["categories"] else cat)
                cat_counter[primary] += 1
            cat_count += len(entries)
            start += MAX_PER_PAGE
            if len(entries) < MAX_PER_PAGE:
                break
        print(f"  本分类新增去重论文: {cat_count}（累计全局 {len(papers)}）")

    # ===== 关键词标注（可选） =====
    if args.annotate:
        for p in papers.values():
            p["topics"] = annotate_topics(p)
        topic_counter = Counter(t for p in papers.values() for t in p.get("topics", []))
        print(f"\n[子方向标注] 热点分布（Top 5）:")
        for t, c in topic_counter.most_common(5):
            print(f"  {t}: {c}")

    # ===== 输出 1：论文明细（参考论文采集器格式） =====
    paper_list = sorted(papers.values(), key=lambda p: p["published"], reverse=True)
    papers_path = Path(f"papers-{month_str}.json")
    papers_path.write_text(json.dumps(paper_list, ensure_ascii=False, indent=1), encoding="utf-8")

    # ===== 输出 2：节点树（四源统一 schema） =====
    nodes = []
    for cat in args.categories:
        nodes.append({
            "id": cat,
            "name": cat,
            "parent": cat.split(".")[0],
            "wuxing": None,              # 五行标注待诊断引擎
            "weight": cat_counter.get(cat, 0),
        })
    tree = {
        "schema_version": "1.0",
        "source": "arxiv_ai",
        "timestamp": datetime.now().strftime("%Y-%m-%d"),
        "month": month_str,
        "nodes": nodes,
        "meta": {
            "node_count": len(nodes),
            "total_weight": sum(cat_counter.values()),
            "unique_papers": len(papers),
            "categories_used": len(args.categories),
        },
    }
    tree_path = Path(f"arxiv_ai_tree_{month_str}.json")
    tree_path.write_text(json.dumps(tree, ensure_ascii=False, indent=2), encoding="utf-8")

    # ===== 合规报告 =====
    comp = fetcher.compliance_report()
    print(f"\n[合规报告] requests={comp['requests']}, 间隔合规={comp['interval_compliant']}, "
          f"平均延迟={comp['avg_latency_s']}s")

    # ===== 控制台摘要 =====
    print(f"\n{'='*64}")
    print(f"采集完成 | 月份={month_str}")
    print(f"  去重论文数 : {len(papers)}")
    print(f"  分类分布   : {dict(cat_counter.most_common())}")
    print(f"  输出文件   : {papers_path}（论文明细 {len(paper_list)} 篇）")
    print(f"              {tree_path}（节点树 {len(nodes)} 分类）")
    print(f"{'='*64}")


if __name__ == "__main__":
    main()
