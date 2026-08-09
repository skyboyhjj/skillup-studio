#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub 主题月度采集器 (W3)
============================
按 topic + created 月份统计新仓库数 → github_tree_YYYYMM.json（四源统一 schema）

设计要点（参考 docs/github_collect.py）：
  - 用 search API 的 total_count（per_page=1）——极简高效，不需分页拉全
  - 速率：search API 未认证 10 req/min、认证 30 req/min → 自动适配间隔
  - token：可选 GITHUB_TOKEN 环境变量（建议设置，速率提升 3 倍）
  - 话题列表：14 个 AI 话题，与 arXiv 11 分类对应

GitHub Search API 限制：
  - 未认证：10 次/分钟；认证：30 次/分钟
  - 建议设置 GITHUB_TOKEN 环境变量

用法（PowerShell）：
  $env:GITHUB_TOKEN = "ghp_xxx"
  python github_collect.py                     # 默认最近完整月
  python github_collect.py --month 2026-07      # 指定月份
  python github_collect.py --month 2026-06 --backfill  # 历史回填

零依赖：urllib + json（Python 标准库）
"""

import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import date
from pathlib import Path

# ============ 配置 ============
GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"
USER_AGENT = "wuxing-flowengine-github-collector/0.2 (monthly snapshot; non-commercial research)"
MIN_INTERVAL_AUTH = 2.0      # 认证：30 req/min → 2 秒
MIN_INTERVAL_ANON = 6.0      # 未认证：10 req/min → 6 秒

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

# ============ AI 话题白名单（与 arXiv 11 分类对应） ============
# 参考 docs/github_collect.py 的 14 话题列表
AI_TOPICS = [
    "llm",                              # ↔ cs.CL（LLM）
    "large-language-models",            # ↔ cs.CL
    "machine-learning",                 # ↔ cs.LG / stat.ML
    "deep-learning",                    # ↔ cs.LG
    "natural-language-processing",      # ↔ cs.CL
    "computer-vision",                  # ↔ cs.CV
    "reinforcement-learning",           # ↔ cs.LG（RL 子方向）
    "multimodal",                       # ↔ cs.MM
    "agents",                           # ↔ cs.MA
    "autonomous-agents",                # ↔ cs.MA
    "retrieval-augmented-generation",   # ↔ cs.IR
    "graph-neural-network",             # ↔ cs.LG（GNN）
    "federated-learning",               # ↔ cs.LG
    "robotics",                         # ↔ cs.RO
]

# 话题 → 五行映射（与 arXiv 体系一致）
# 原则：水=语言/流动/模型、火=交互/活跃/智能体、木=感知/生发/视觉、
#       土=基础/承载/工程、金=结构/安全/精确
TOPIC_WUXING = {
    "llm": "水",
    "large-language-models": "水",
    "machine-learning": "土",
    "deep-learning": "水",
    "natural-language-processing": "水",
    "computer-vision": "木",
    "reinforcement-learning": "金",
    "multimodal": "木",
    "agents": "火",
    "autonomous-agents": "火",
    "retrieval-augmented-generation": "金",
    "graph-neural-network": "土",
    "federated-learning": "金",
    "robotics": "金",
}


# ============ 合规请求器 ============
class GitHubFetcher:
    """GitHub API 请求器：Token 认证 + 速率自适应 + 指数退避重试"""

    def __init__(self, token=None):
        self.token = token or os.environ.get("GITHUB_TOKEN", "")
        self.authenticated = bool(self.token)
        self.min_interval = MIN_INTERVAL_AUTH if self.authenticated else MIN_INTERVAL_ANON
        self.last_request_time = 0.0
        self.request_log = []
        self.rate_limit_remaining = None
        self.rate_limit_reset = None
        # 重试配置
        self.max_retries = 3
        self.retry_base_delay = 10.0
        self.retry_stats = {"total_retries": 0, "retry_successes": 0}

    def _check_rate_limit(self, headers):
        self.rate_limit_remaining = headers.get("X-RateLimit-Remaining", "?")
        self.rate_limit_reset = headers.get("X-RateLimit-Reset", "?")

    def _wait_if_rate_limited(self):
        if self.rate_limit_remaining is not None:
            try:
                remaining = int(self.rate_limit_remaining)
                if remaining <= 2 and self.rate_limit_reset and self.rate_limit_reset != "?":
                    reset_time = int(self.rate_limit_reset)
                    wait = max(reset_time - time.time() + 1, 0)
                    if wait > 0:
                        print(f"\n  [速率限制] 剩余 {remaining} 次，等待 {wait:.0f}s ...")
                        time.sleep(wait)
            except (ValueError, TypeError):
                pass

    def fetch_json(self, url):
        """带认证、速率控制和指数退避重试的请求"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)

        self._wait_if_rate_limited()

        last_error = None
        for attempt in range(1 + self.max_retries):
            self.last_request_time = time.time()
            headers = {
                "Accept": "application/vnd.github+json",
                "User-Agent": USER_AGENT,
            }
            if self.authenticated:
                headers["Authorization"] = f"Bearer {self.token}"

            req = urllib.request.Request(url, headers=headers)
            t0 = time.time()
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    self._check_rate_limit(dict(resp.headers))
                    data = json.loads(resp.read().decode("utf-8"))
                dt = time.time() - t0
                self.request_log.append({
                    "url": url[:100] + "..." if len(url) > 100 else url,
                    "status": 200,
                    "latency_s": round(dt, 2),
                    "interval_ok": elapsed >= self.min_interval - 0.1,
                    "attempts": attempt + 1,
                    "rate_limit_remaining": self.rate_limit_remaining,
                })
                if attempt > 0:
                    self.retry_stats["retry_successes"] += 1
                return data
            except urllib.error.HTTPError as e:
                status = e.code
                last_error = f"HTTP {status}: {e.reason}"
                self.retry_stats["total_retries"] += 1
                if status == 403:
                    self.rate_limit_remaining = "0"
                    self._wait_if_rate_limited()
                if status == 422:
                    break
            except Exception as e:
                last_error = str(e)
                self.retry_stats["total_retries"] += 1

            if attempt < self.max_retries:
                delay = self.retry_base_delay * (2 ** attempt)
                time.sleep(delay)

        self.request_log.append({
            "url": url[:100],
            "status": "ERROR",
            "error": last_error,
            "latency_s": round(time.time() - t0, 2),
            "attempts": 1 + self.max_retries,
        })
        return None

    def compliance_report(self):
        n = len(self.request_log)
        if n == 0:
            return {"requests": 0, "note": "无请求"}
        ok = all(r.get("status") == 200 and r.get("interval_ok", True)
                 for r in self.request_log)
        lat = [r.get("latency_s", 0) for r in self.request_log
               if r.get("status") == 200]
        errors = [r for r in self.request_log if r.get("status") == "ERROR"]
        retried = [r for r in self.request_log if r.get("attempts", 1) > 1]
        return {
            "requests": n,
            "errors": len(errors),
            "authenticated": self.authenticated,
            "interval_compliant": ok,
            "avg_latency_s": round(sum(lat) / len(lat), 2) if lat else None,
            "min_interval_s": self.min_interval,
            "note": "认证模式" if self.authenticated else "未认证模式（建议设置 GITHUB_TOKEN）",
            "retry": {
                "total_retries": self.retry_stats["total_retries"],
                "retry_successes": self.retry_stats["retry_successes"],
                "requests_retried": len(retried),
            },
            "error_details": [e["error"] for e in errors] if errors else [],
        }


# ============ 查询构建 ============
def _last_day_of_month(year: int, month: int) -> int:
    import calendar
    return calendar.monthrange(year, month)[1]


def build_search_url(topic: str, year: int, month: int) -> str:
    """按 topic + created 月份构建 search 查询（per_page=1，仅取 total_count）

    关键：查询字符串中用空格（非 +），urlencode 将空格编码为 +，
    GitHub Search API 将 + 解释为 AND 运算符。
    月末日期动态计算，避免 6 月 31 日等无效日期导致 HTTP 422。
    """
    start = f"{year}-{month:02d}-01"
    last_day = _last_day_of_month(year, month)
    end = f"{year}-{month:02d}-{last_day:02d}"
    q = f"topic:{topic} created:{start}..{end}"
    params = urllib.parse.urlencode({"q": q, "per_page": 1})
    return f"{GITHUB_SEARCH_URL}?{params}"


# ============ 五行分类 ============
def classify_wuxing(topic: str) -> str:
    return TOPIC_WUXING.get(topic, "水")


# ============ 主流程 ============
def main():
    parser = argparse.ArgumentParser(description="GitHub 主题月度采集器")
    parser.add_argument("--month", default=None, help="月份 YYYY-MM（默认最近完整月）")
    parser.add_argument("--topics", nargs="+", default=None,
                        help=f"话题白名单（默认 {len(AI_TOPICS)} 个 AI 话题）")
    parser.add_argument("--token", default=None, help="GitHub Token（也可用 GITHUB_TOKEN 环境变量）")
    parser.add_argument("--backfill", action="store_true", help="历史回填模式")
    parser.add_argument("--dry-run", action="store_true", help="仅查询不保存")
    args = parser.parse_args()

    # 月份解析
    if args.month:
        year, month = map(int, args.month.split("-"))
    else:
        today = date.today()
        year, month = (today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12)
    month_str = f"{year}-{month:02d}"

    # 话题列表
    topics = args.topics if args.topics else AI_TOPICS

    # 初始化请求器
    fetcher = GitHubFetcher(token=args.token)

    print("=" * 64)
    print(f"GitHub 主题采集 | 月份={month_str} | 话题数={len(topics)} | "
          f"{'认证' if fetcher.authenticated else '未认证'}")
    print("=" * 64)

    nodes = []
    topic_errors = {}

    for i, topic in enumerate(topics, 1):
        url = build_search_url(topic, year, month)
        try:
            data = fetcher.fetch_json(url)
            if data is None:
                topic_errors[topic] = "API 请求失败（含重试）"
                print(f"[{i}/{len(topics)}] {topic}: ❌ API 请求失败")
                nodes.append({"id": f"github:{topic}", "name": topic, "parent": "github",
                              "wuxing": classify_wuxing(topic), "weight": 0,
                              "error": "API 请求失败"})
                continue

            total = data.get("total_count", 0)
            nodes.append({
                "id": f"github:{topic}",
                "name": topic,
                "parent": "github",
                "wuxing": classify_wuxing(topic),
                "weight": total,
            })
            print(f"[{i}/{len(topics)}] {topic:35s} {total:>6d} 个新仓库")
        except Exception as e:
            topic_errors[topic] = str(e)
            print(f"[{i}/{len(topics)}] {topic}: ❌ {e}")
            nodes.append({"id": f"github:{topic}", "name": topic, "parent": "github",
                          "wuxing": classify_wuxing(topic), "weight": 0, "error": str(e)})

    # ===== 输出：节点树（四源统一 schema） =====
    tree = {
        "schema_version": "1.0",
        "source": "github",
        "timestamp": date.today().strftime("%Y-%m-%d"),
        "month": month_str,
        "source_type": "real",
        "source_type_note": "GitHub Search API collected (api.github.com/search/repositories)",
        "nodes": nodes,
        "meta": {
            "node_count": len(nodes),
            "total_weight": sum(n.get("weight", 0) for n in nodes),
            "topics_used": len(topics),
            "topics_zero": sum(1 for n in nodes if n.get("weight", 0) == 0),
            "api_used": "api.github.com/search/repositories (total_count, per_page=1)",
            "token_used": fetcher.authenticated,
        },
    }

    if not args.dry_run:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        tree_path = OUTPUT_DIR / f"github_tree_{year}{month:02d}.json"
        tree_path.write_text(
            json.dumps(tree, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    else:
        tree_path = None

    # ===== 合规报告 =====
    comp = fetcher.compliance_report()
    retry_info = comp.get("retry", {})
    retry_str = ""
    if retry_info.get("total_retries", 0) > 0:
        retry_str = (f", 重试 {retry_info['total_retries']} 次"
                     f"（成功 {retry_info['retry_successes']}）")
    print(f"\n[合规] {comp['requests']} 请求, {comp['errors']} 错误{retry_str}, "
          f"间隔{'合规' if comp['interval_compliant'] else '⚠不足'}, "
          f"平均延迟 {comp['avg_latency_s']}s, "
          f"{comp['note']}")

    if topic_errors:
        print(f"[错误] {len(topic_errors)} 个话题采集失败: {list(topic_errors.keys())}")

    # ===== 控制台摘要 =====
    print(f"\n{'='*64}")
    print(f"采集完成 | 月份={month_str} | 去重仓库数={tree['meta']['total_weight']}")
    print(f"  话题分布:")
    for n in nodes:
        wx = n.get("wuxing", "?")
        w = n.get("weight", 0)
        if w == 0 and n.get("error"):
            continue
        print(f"    [{wx}] {n['name']:35s} {w:>6d} 个仓库")
    if not args.dry_run:
        print(f"  输出文件: {tree_path.name}")
    else:
        print(f"  [DRY RUN] 未保存文件")
    print(f"{'='*64}")

    # 五行分布
    wx_dist = Counter()
    for n in nodes:
        wx_dist[n.get("wuxing", "水")] += n.get("weight", 0)
    total = tree["meta"]["total_weight"]
    if total > 0:
        print(f"\n[五行分布]")
        for wx in ["木", "火", "土", "金", "水"]:
            count = wx_dist.get(wx, 0)
            pct = count / total * 100
            bar = "█" * int(pct / 2)
            print(f"  {wx}: {count:>6d} 个仓库 ({pct:5.1f}%) {bar}")


if __name__ == "__main__":
    main()