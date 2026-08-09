#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HuggingFace 模型月度采集器（W3）
================================
按 pipeline_tag + createdAt 月份统计新模型数 → hf_tree_YYYYMM.json（四源 schema）

设计要点：
  - HF API 无"created 区间"参数 → 拉模型列表（createdAt 降序）后按月份过滤计数
  - 分页：limit=1000/页，逐页拉直到早于目标月份（createdAt 降序可提前终止）
  - 速率：未认证亦较宽松（保留 1 秒间隔 + 友好 UA）

用法（PowerShell）：
  python hf_collect.py                    # 默认最近完整月
  python hf_collect.py --month 2026-07     # 指定月份

零依赖：urllib + json（标准库）
"""

import argparse
import json
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

# ============ 配置 ============
HF_MODELS_URL = "https://huggingface.co/api/models"
USER_AGENT = "wuxing-flowengine-hf-collector/0.1 (monthly snapshot; non-commercial)"
MIN_INTERVAL = 1.0        # HF API 较宽松，1 秒间隔
PAGE_SIZE = 1000          # HF 单页上限

# pipeline_tag 白名单（AI 模型生态，与 arXiv 11 分类对应）
AI_PIPELINE_TAGS = [
    "text-generation",            # ↔ cs.CL（LLM 生成）
    "text-classification",        # ↔ cs.CL
    "token-classification",       # ↔ cs.CL
    "question-answering",         # ↔ cs.CL
    "summarization",              # ↔ cs.CL
    "translation",                # ↔ cs.CL
    "image-classification",       # ↔ cs.CV
    "image-text-to-text",         # ↔ cs.MM（视觉-语言）
    "text-to-image",              # ↔ cs.CV（扩散）
    "automatic-speech-recognition",  # ↔ cs.CL
    "reinforcement-learning",     # ↔ cs.LG
    "text-to-text",               # ↔ cs.CL
]


class HFFetcher:
    """HuggingFace API 合规请求器"""

    def __init__(self):
        self.last_request_time = 0.0
        self.request_log = []

    def fetch_json(self, url):
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
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

    min_interval = MIN_INTERVAL

    def compliance_report(self):
        n = len(self.request_log)
        if n == 0:
            return {"requests": 0}
        ok = all(r.get("status") == 200 and r.get("interval_ok", True) for r in self.request_log)
        return {
            "requests": n,
            "interval_compliant": ok,
            "min_interval_s": MIN_INTERVAL,
        }


def build_models_url(pipeline_tag: str, page: int, page_size: int = PAGE_SIZE) -> str:
    """按 pipeline_tag 拉模型列表（createdAt 降序，分页）"""
    params = urllib.parse.urlencode({
        "pipeline_tag": pipeline_tag,
        "sort": "createdAt",
        "direction": "-1",
        "limit": page_size,
        "full": "false",
    })
    return f"{HF_MODELS_URL}?{params}&page={page}"


def created_month(model: dict) -> str:
    """从模型元数据提取 createdAt 月份（YYYY-MM）"""
    t = model.get("createdAt", "") or model.get("lastModified", "")
    return t[:7] if t else ""


def main():
    parser = argparse.ArgumentParser(description="HuggingFace 模型月度采集器")
    parser.add_argument("--month", default=None, help="月份 YYYY-MM（默认最近完整月）")
    parser.add_argument("--tags", nargs="+", default=AI_PIPELINE_TAGS, help="pipeline_tag 白名单")
    parser.add_argument("--max-pages", type=int, default=5, help="每 tag 最大分页数（默认 5 页=5000 模型）")
    args = parser.parse_args()

    if args.month:
        year, month = map(int, args.month.split("-"))
    else:
        today = date.today()
        year, month = (today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12)
    month_str = f"{year}-{month:02d}"
    month_prefix = f"{year}-{month:02d}"

    fetcher = HFFetcher()
    print("=" * 64)
    print(f"HuggingFace 采集 | 月份={month_str} | tags={len(args.tags)} | 每 tag ≤{args.max_pages} 页")
    print("=" * 64)

    nodes = []
    for i, tag in enumerate(args.tags, 1):
        count = 0
        pages_used = 0
        try:
            for page in range(1, args.max_pages + 1):
                url = build_models_url(tag, page)
                models = fetcher.fetch_json(url)
                if not models:
                    break
                pages_used += 1
                for m in models:
                    if created_month(m) == month_prefix:
                        count += 1
                # createdAt 降序：本页最早日期若已早于目标月份 → 提前终止
                oldest = created_month(models[-1]) if models else ""
                if oldest and oldest < month_prefix:
                    break
            nodes.append({
                "id": f"hf:{tag}",
                "name": tag,
                "parent": "huggingface",
                "wuxing": None,
                "weight": count,
            })
            print(f"[{i}/{len(args.tags)}] {tag}: {count} 个新模型（{pages_used} 页）")
        except Exception as e:
            print(f"[{i}/{len(args.tags)}] {tag}: ❌ {e}")
            nodes.append({"id": f"hf:{tag}", "name": tag, "parent": "huggingface",
                          "wuxing": None, "weight": 0, "error": str(e)})

    tree = {
        "schema_version": "1.0",
        "source": "huggingface",
        "timestamp": date.today().strftime("%Y-%m-%d"),
        "month": month_str,
        "source_type": "real",
        "nodes": nodes,
        "meta": {
            "node_count": len(nodes),
            "total_weight": sum(n.get("weight", 0) for n in nodes),
            "api": "huggingface.co/api/models (createdAt 过滤)",
            "max_pages_per_tag": args.max_pages,
        },
    }
    out = Path(f"hf_tree_{month_str}.json")
    out.write_text(json.dumps(tree, ensure_ascii=False, indent=2), encoding="utf-8")

    comp = fetcher.compliance_report()
    print(f"\n[合规] requests={comp['requests']}, 间隔合规={comp['interval_compliant']}")
    print(f"[输出] {out}（{len(nodes)} tags，总权重 {tree['meta']['total_weight']}）")


if __name__ == "__main__":
    main()
