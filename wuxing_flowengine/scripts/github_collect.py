#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub 主题月度采集器（W3）
============================
按 topic + created 月份统计新仓库数 → github_tree_YYYYMM.json（四源 schema）

设计要点：
  - 用 search API 的 total_count（不需分页拉全）——高效且合规
  - 速率：search API 未认证 10 req/min、认证 30 req/min → 自动适配间隔
  - token：可选 GITHUB_TOKEN 环境变量（建议设置，速率提升 3 倍）

用法（PowerShell）：
  python github_collect.py                     # 默认最近完整月
  python github_collect.py --month 2026-07      # 指定月份
  $env:GITHUB_TOKEN="ghp_xxx"; python github_collect.py   # 带认证

零依赖：urllib + json（标准库）
"""

import argparse
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

# ============ 配置 ============
GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"
GITHUB_API_URL = "https://api.github.com"
MIN_INTERVAL_AUTH = 2.0      # 认证：30 req/min → 2 秒
MIN_INTERVAL_ANON = 6.0      # 未认证：10 req/min → 6 秒

# AI 主题白名单（与 arXiv 11 分类对应）
AI_TOPICS = [
    "llm",                         # ↔ cs.CL（LLM）
    "large-language-models",       # ↔ cs.CL
    "machine-learning",            # ↔ cs.LG / stat.ML
    "deep-learning",               # ↔ cs.LG
    "natural-language-processing", # ↔ cs.CL
    "computer-vision",             # ↔ cs.CV
    "reinforcement-learning",      # ↔ cs.LG（RL 子方向）
    "multimodal",                  # ↔ cs.MM
    "agents",                      # ↔ cs.MA
    "autonomous-agents",           # ↔ cs.MA
    "retrieval-augmented-generation",  # ↔ cs.IR
    "graph-neural-network",        # ↔ cs.LG（GNN）
    "federated-learning",          # ↔ cs.LG
    "robotics",                    # ↔ cs.RO
]


class GitHubFetcher:
    """GitHub API 合规请求器（认证自动检测）"""

    def __init__(self):
        self.token = os.environ.get("GITHUB_TOKEN", "")
        self.authenticated = bool(self.token)
        self.min_interval = MIN_INTERVAL_AUTH if self.authenticated else MIN_INTERVAL_ANON
        self.last_request_time = 0.0
        self.request_log = []

    def fetch_json(self, url):
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()

        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "wuxing-flowengine-github-collector/0.1 (monthly snapshot; non-commercial)",
        }
        if self.authenticated:
            headers["Authorization"] = f"Bearer {self.token}"

        req = urllib.request.Request(url, headers=headers)
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            status = 200
        except Exception as e:
            self.request_log.append({"url": url[:80], "status": "ERROR", "error": str(e)})
            raise
        dt = time.time() - t0
        self.request_log.append({
            "url": url[:80] + "...",
            "status": status,
            "latency_s": round(dt, 2),
            "interval_ok": elapsed >= self.min_interval - 0.1,
        })
        return data

    def compliance_report(self):
        n = len(self.request_log)
        if n == 0:
            return {"requests": 0}
        ok = all(r.get("status") == 200 and r.get("interval_ok", True) for r in self.request_log)
        return {
            "requests": n,
            "authenticated": self.authenticated,
            "interval_compliant": ok,
            "min_interval_s": self.min_interval,
            "note": "认证模式" if self.authenticated else "未认证模式（建议设置 GITHUB_TOKEN）",
        }


def build_search_url(topic: str, year: int, month: int) -> str:
    """按 topic + created 月份构建 search 查询（取 total_count）"""
    start = f"{year}-{month:02d}-01"
    end = f"{year}-{month:02d}-31"
    q = f"topic:{topic} created:{start}..{end}"
    params = urllib.parse.urlencode({"q": q, "per_page": 1})  # per_page=1 仅取 total_count
    return f"{GITHUB_SEARCH_URL}?{params}"


def main():
    parser = argparse.ArgumentParser(description="GitHub 主题月度采集器")
    parser.add_argument("--month", default=None, help="月份 YYYY-MM（默认最近完整月）")
    parser.add_argument("--topics", nargs="+", default=AI_TOPICS, help="主题白名单")
    args = parser.parse_args()

    if args.month:
        year, month = map(int, args.month.split("-"))
    else:
        today = date.today()
        year, month = (today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12)
    month_str = f"{year}-{month:02d}"

    fetcher = GitHubFetcher()
    print("=" * 64)
    print(f"GitHub 主题采集 | 月份={month_str} | 主题数={len(args.topics)} | "
          f"{'认证' if fetcher.authenticated else '未认证'}")
    print("=" * 64)

    nodes = []
    for i, topic in enumerate(args.topics, 1):
        url = build_search_url(topic, year, month)
        try:
            data = fetcher.fetch_json(url)
            total = data.get("total_count", 0)
            nodes.append({
                "id": f"github:{topic}",
                "name": topic,
                "parent": "github",
                "wuxing": None,          # 五行标注待诊断引擎/标注表
                "weight": total,         # 当月该 topic 新仓库数
            })
            print(f"[{i}/{len(args.topics)}] {topic}: {total} 个新仓库")
        except Exception as e:
            print(f"[{i}/{len(args.topics)}] {topic}: ❌ {e}")
            nodes.append({"id": f"github:{topic}", "name": topic, "parent": "github",
                          "wuxing": None, "weight": 0, "error": str(e)})

    # 输出（四源统一 schema）
    tree = {
        "schema_version": "1.0",
        "source": "github",
        "timestamp": date.today().strftime("%Y-%m-%d"),
        "month": month_str,
        "source_type": "real",
        "nodes": nodes,
        "meta": {
            "node_count": len(nodes),
            "total_weight": sum(n.get("weight", 0) for n in nodes),
            "api": "api.github.com/search/repositories (total_count)",
            "authenticated": fetcher.authenticated,
        },
    }
    out = Path(f"github_tree_{month_str}.json")
    out.write_text(json.dumps(tree, ensure_ascii=False, indent=2), encoding="utf-8")

    comp = fetcher.compliance_report()
    print(f"\n[合规] requests={comp['requests']}, 间隔合规={comp['interval_compliant']}, "
          f"模式={comp['note']}")
    print(f"[输出] {out}（{len(nodes)} 主题，总权重 {tree['meta']['total_weight']}）")


if __name__ == "__main__":
    main()
