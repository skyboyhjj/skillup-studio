#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HuggingFace 模型月度采集器 (W3)
================================
按 pipeline_tag + createdAt 月份统计新模型数 → hf_tree_YYYYMM.json（四源统一 schema）

设计要点（参考 docs/hf_collect.py，翻页改为 cursor 分页）：
  - HF API 原生 cursor 分页（Link header rel="next"），非 page 参数
  - createdAt 降序 → 按月份过滤计数 → 提前终止（早于目标月份时停止）
  - 每页 limit=1000，安全上限 max_pages=20（20,000 模型/tag）
  - 速率：HF API 较宽松，1.5 秒间隔

HuggingFace API：
  - 端点：huggingface.co/api/models
  - 返回：JSON 数组（非对象包裹）
  - 分页：Link header 含 cursor 参数的 next URL
  - 无认证要求

用法（PowerShell）：
  python hf_collect.py                     # 默认最近完整月
  python hf_collect.py --month 2026-07      # 指定月份
  python hf_collect.py --month 2026-06 --backfill  # 历史回填

零依赖：urllib + json（Python 标准库）
"""

import argparse
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import date
from pathlib import Path

# ============ 配置 ============
HF_MODELS_URL = "https://huggingface.co/api/models"
USER_AGENT = "wuxing-flowengine-hf-collector/0.2 (monthly snapshot; non-commercial research)"
MIN_INTERVAL = 1.5        # HF API 较宽松，1.5 秒间隔
PAGE_SIZE = 1000          # HF 单页上限
MAX_PAGES = 20            # 每 tag 最大翻页数（安全上限，20,000 模型）

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

# ============ pipeline_tag 白名单（与 arXiv 11 分类对应） ============
# 参考 docs/hf_collect.py 的 12 标签列表
AI_PIPELINE_TAGS = [
    "text-generation",                # ↔ cs.CL（LLM 生成）
    "text-classification",            # ↔ cs.CL
    "token-classification",           # ↔ cs.CL
    "question-answering",             # ↔ cs.CL
    "summarization",                  # ↔ cs.CL
    "translation",                    # ↔ cs.CL
    "image-classification",           # ↔ cs.CV
    "image-text-to-text",             # ↔ cs.MM（视觉-语言）
    "text-to-image",                  # ↔ cs.CV（扩散）
    "automatic-speech-recognition",   # ↔ cs.CL
    "reinforcement-learning",         # ↔ cs.LG
    "text-to-text",                   # ↔ cs.CL
]

# pipeline_tag → 五行映射（与 arXiv/BAAI 体系一致）
# 原则：水=语言/流动/模型、火=交互/活跃、木=感知/生发/视觉、
#       土=基础/承载、金=结构/精确/分类
TAG_WUXING = {
    "text-generation": "水",
    "text-classification": "金",
    "token-classification": "金",
    "question-answering": "火",
    "summarization": "水",
    "translation": "水",
    "image-classification": "木",
    "image-text-to-text": "木",
    "text-to-image": "木",
    "automatic-speech-recognition": "水",
    "reinforcement-learning": "金",
    "text-to-text": "水",
}


# ============ 合规请求器 ============
class HFFetcher:
    """HuggingFace API 请求器：速率控制 + 指数退避重试"""

    def __init__(self):
        self.last_request_time = 0.0
        self.request_log = []
        self.max_retries = 3
        self.retry_base_delay = 5.0
        self.retry_stats = {"total_retries": 0, "retry_successes": 0}

    def fetch_json(self, url):
        """带速率控制和指数退避重试的请求"""
        elapsed = time.time() - self.last_request_time
        if elapsed < MIN_INTERVAL:
            time.sleep(MIN_INTERVAL - elapsed)

        last_error = None
        for attempt in range(1 + self.max_retries):
            self.last_request_time = time.time()
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            t0 = time.time()
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    link_header = resp.headers.get("Link", "")
                dt = time.time() - t0
                self.request_log.append({
                    "url": url[:100] + "..." if len(url) > 100 else url,
                    "status": 200,
                    "latency_s": round(dt, 2),
                    "interval_ok": elapsed >= MIN_INTERVAL - 0.1,
                    "attempts": attempt + 1,
                })
                if attempt > 0:
                    self.retry_stats["retry_successes"] += 1
                return data, link_header
            except urllib.error.HTTPError as e:
                last_error = f"HTTP {e.code}: {e.reason}"
                self.retry_stats["total_retries"] += 1
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
        return None, None

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
            "interval_compliant": ok,
            "avg_latency_s": round(sum(lat) / len(lat), 2) if lat else None,
            "min_interval_s": MIN_INTERVAL,
            "retry": {
                "total_retries": self.retry_stats["total_retries"],
                "retry_successes": self.retry_stats["retry_successes"],
                "requests_retried": len(retried),
            },
            "error_details": [e["error"] for e in errors] if errors else [],
        }


# ============ 查询构建与分页 ============
def build_models_url(pipeline_tag: str, page_size: int = PAGE_SIZE) -> str:
    """按 pipeline_tag 构建初始查询 URL（createdAt 降序）"""
    params = urllib.parse.urlencode({
        "pipeline_tag": pipeline_tag,
        "sort": "createdAt",
        "direction": "-1",
        "limit": page_size,
        "full": "false",
    })
    return f"{HF_MODELS_URL}?{params}"


def parse_next_link(link_header: str) -> str or None:
    """从 Link header 解析 next URL（RFC 5988）"""
    if not link_header:
        return None
    for part in link_header.split(","):
        m = re.search(r'<([^>]+)>', part)
        rm = re.search(r'rel="(\w+)"', part)
        if m and rm and rm.group(1) == "next":
            return m.group(1)
    return None


# ============ 五行分类 ============
def classify_wuxing(tag: str) -> str:
    return TAG_WUXING.get(tag, "水")


def check_hf_wuxing_consistency(nodes, strict=True):
    """HF 标注一致性校验：输出节点 wuxing vs TAG_WUXING canonical。

    防止采集器内置标注与输出数据不一致。
    参考：docs/arXiv五行标注仲裁确认文档.md 决议 2（扩展至 HF 源）

    Args:
        nodes: 输出节点列表（含 name/wuxing 字段）
        strict: True=不一致时抛 ValueError，False=返回差异列表

    Returns:
        dict: {consistent, mismatches, fix_count, annotation_version}
    """
    mismatches = {}
    for n in nodes:
        tag = n.get("name", "")
        if tag not in TAG_WUXING:
            continue
        actual = n.get("wuxing", "")
        expected = TAG_WUXING[tag]
        if actual != expected:
            mismatches[tag] = (actual, expected)

    result = {
        "consistent": len(mismatches) == 0,
        "mismatches": mismatches,
        "fix_count": len(mismatches),
        "annotation_version": "v2",
    }

    if not result["consistent"] and strict:
        raise ValueError(
            f"HF 标注源分裂 {len(mismatches)} 处: {mismatches}——"
            f"采集器 TAG_WUXING 与输出节点不一致，检查 classify_wuxing() 调用"
        )

    return result


# ============ 主流程 ============
def main():
    parser = argparse.ArgumentParser(description="HuggingFace 模型月度采集器")
    parser.add_argument("--month", default=None, help="月份 YYYY-MM（默认最近完整月）")
    parser.add_argument("--tags", nargs="+", default=None,
                        help=f"pipeline_tag 白名单（默认 {len(AI_PIPELINE_TAGS)} 个标签）")
    parser.add_argument("--max-pages", type=int, default=MAX_PAGES,
                        help=f"每 tag 最大翻页数（默认 {MAX_PAGES}）")
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
    month_prefix = f"{year}-{month:02d}"

    # 标签列表
    tags = args.tags if args.tags else AI_PIPELINE_TAGS

    fetcher = HFFetcher()
    print("=" * 64)
    print(f"HuggingFace 采集 | 月份={month_str} | 标签数={len(tags)} | "
          f"每 tag ≤{args.max_pages} 页")
    print("=" * 64)

    nodes = []
    tag_errors = {}

    for i, tag in enumerate(tags, 1):
        count = 0
        pages_used = 0
        url = build_models_url(tag)
        try:
            while pages_used < args.max_pages:
                data, link_header = fetcher.fetch_json(url)
                if data is None:
                    tag_errors[tag] = "API 请求失败（含重试）"
                    print(f"[{i}/{len(tags)}] {tag}: ❌ API 请求失败")
                    break

                if not isinstance(data, list) or not data:
                    break

                pages_used += 1
                page_count = 0
                oldest = None
                for m in data:
                    created = (m.get("createdAt") or "")[:7]
                    if not oldest or (m.get("createdAt") or "z") < oldest:
                        oldest = (m.get("createdAt") or "z")
                    if created == month_prefix:
                        count += 1
                        page_count += 1

                # createdAt 降序：本页最早日期若已早于目标月份 → 提前终止
                if oldest and oldest[:7] < month_prefix:
                    break

                # 解析 next link 继续翻页
                next_url = parse_next_link(link_header)
                if not next_url:
                    break
                url = next_url

            if tag not in tag_errors:
                print(f"[{i}/{len(tags)}] {tag:35s} {count:>6d} 个新模型（{pages_used} 页）")

        except Exception as e:
            tag_errors[tag] = str(e)
            print(f"[{i}/{len(tags)}] {tag}: ❌ {e}")

        nodes.append({
            "id": f"hf:{tag}",
            "name": tag,
            "parent": "huggingface",
            "wuxing": classify_wuxing(tag),
            "weight": count,
            "pages_used": pages_used,
        })

    # ===== 标注一致性校验（采集器内置标注 vs 输出节点） =====
    consistency = check_hf_wuxing_consistency(nodes, strict=True)
    print(f"[一致性] HF 标注校验: {'通过' if consistency['consistent'] else '不一致'}"
          f"（{consistency['fix_count']} 处差异）")

    # ===== 输出：节点树（四源统一 schema） =====
    tree = {
        "schema_version": "1.0",
        "source": "huggingface",
        "timestamp": date.today().strftime("%Y-%m-%d"),
        "month": month_str,
        "source_type": "real",
        "source_type_note": "HuggingFace API collected (huggingface.co/api/models)",
        "wuxing_annotation_version": "v2",
        "nodes": nodes,
        "meta": {
            "node_count": len(nodes),
            "total_weight": sum(n.get("weight", 0) for n in nodes),
            "tags_used": len(tags),
            "tags_zero": sum(1 for n in nodes if n.get("weight", 0) == 0),
            "api_used": "huggingface.co/api/models (cursor pagination, createdAt filter)",
            "max_pages_per_tag": args.max_pages,
        },
    }

    if not args.dry_run:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        tree_path = OUTPUT_DIR / f"hf_tree_{year}{month:02d}.json"
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
          f"平均延迟 {comp['avg_latency_s']}s")

    if tag_errors:
        print(f"[错误] {len(tag_errors)} 个标签采集失败: {list(tag_errors.keys())}")

    # ===== 控制台摘要 =====
    print(f"\n{'='*64}")
    print(f"采集完成 | 月份={month_str} | 总模型数={tree['meta']['total_weight']}")
    print(f"  标签分布:")
    for n in nodes:
        wx = n.get("wuxing", "?")
        w = n.get("weight", 0)
        pg = n.get("pages_used", 0)
        if w == 0 and pg == 0:
            continue
        print(f"    [{wx}] {n['name']:35s} {w:>6d} 个模型（{pg} 页）")
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
            cnt = wx_dist.get(wx, 0)
            pct = cnt / total * 100
            bar = "█" * int(pct / 2)
            print(f"  {wx}: {cnt:>6d} 个模型 ({pct:5.1f}%) {bar}")


if __name__ == "__main__":
    main()