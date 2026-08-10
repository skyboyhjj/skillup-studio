#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HuggingFace 模型月度采集器（W3）v0.2
=====================================
按 pipeline_tag + createdAt 月份统计新模型数 → hf_tree_YYYYMM.json（四源 schema）

v0.2 新增（2026-08-10）：
  - 端点 failover：官方优先 → 镜像兜底（hf-mirror.com），HF_API_BASE 环境变量可覆盖
  - 超时拆分：连接超时 10s + 读取超时 30s（原单一 30s 让连接黑洞拖满）
  - 每端点重试：3 次指数退避（1s/2s/4s），全部失败才切下一端点
  - 可操作错误提示：全部端点失败时提示检查网络 / 设 HF_API_BASE / 检查 DNS
  - 端点审计：meta.api 记录实际成功端点 + compliance_report 带 endpoint

设计要点：
  - HF API 无"created 区间"参数 → 拉模型列表（createdAt 降序）后按月份过滤计数
  - 分页：limit=1000/页，逐页拉直到早于目标月份（createdAt 降序可提前终止）
  - 速率：未认证亦较宽松（保留 1 秒间隔 + 友好 UA）

用法（PowerShell）：
  python hf_collect.py                          # 默认最近完整月
  python hf_collect.py --month 2026-07          # 指定月份
  $env:HF_API_BASE="https://your-proxy"         # 自定义端点
  python hf_collect.py --month 2026-08

零依赖：urllib + json（标准库）
"""

import argparse
import json
import os
import socket
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

# ============ 配置 ============
# 端点列表：按序尝试，首个成功即用（官方优先，镜像兜底）
HF_API_ENDPOINTS = [
    "https://huggingface.co",
    "https://hf-mirror.com",
]

USER_AGENT = "wuxing-flowengine-hf-collector/0.2 (monthly snapshot; non-commercial)"
MIN_INTERVAL = 1.0        # HF API 较宽松，1 秒间隔
PAGE_SIZE = 1000          # HF 单页上限

# 超时配置
CONNECT_TIMEOUT_S = 10    # 连接超时（不可达快速切换端点）
READ_TIMEOUT_S = 30       # 读取超时（大数据响应）
RETRY_ATTEMPTS = 3        # 每端点重试次数（含首次）
RETRY_BACKOFF = [1, 2, 4] # 指数退避（秒）

# pipeline_tag 白名单（AI 模型生态，与 arXiv 11 分类对应）
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
    "text2text-generation",           # ↔ cs.CL（原 text-to-text，HF 已重命名）
]


def get_endpoints():
    """解析端点列表：HF_API_BASE 环境变量优先，否则用默认列表"""
    env_base = os.environ.get("HF_API_BASE", "").strip().rstrip("/")
    if env_base:
        # 自定义端点置顶，默认端点兜底
        endpoints = [env_base]
        for ep in HF_API_ENDPOINTS:
            if ep not in endpoints:
                endpoints.append(ep)
        return endpoints
    return list(HF_API_ENDPOINTS)


class HFFetcher:
    """HuggingFace API 合规请求器（v0.2：端点 failover + 重试 + 超时拆分）"""

    def __init__(self, endpoints=None):
        self.endpoints = endpoints or get_endpoints()
        self.active_endpoint = None   # 首次成功后记录
        self.last_request_time = 0.0
        self.request_log = []
        self._failed_endpoints = []   # 记录所有失败的端点

    def _do_single_request(self, url):
        """单次 HTTP 请求（带超时拆分：connect 10s + read 30s）"""
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        # 用 socket 默认超时控制连接阶段，urlopen timeout 控制读取阶段
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(CONNECT_TIMEOUT_S)
        try:
            with urllib.request.urlopen(req, timeout=READ_TIMEOUT_S) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data, 200
        finally:
            socket.setdefaulttimeout(old_timeout)

    def fetch_json(self, path):
        """
        请求 API path（如 /api/models?...），按端点列表顺序尝试。
        每端点最多重试 RETRY_ATTEMPTS 次（指数退避），全部失败才切下一端点。
        """
        # 速率控制
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()

        last_errors = []
        for ep in self.endpoints:
            url = f"{ep}{path}"
            for attempt in range(RETRY_ATTEMPTS):
                t0 = time.time()
                try:
                    data, status = self._do_single_request(url)
                    dt = time.time() - t0
                    # 成功：记录端点 + 请求日志
                    if self.active_endpoint is None:
                        self.active_endpoint = ep
                    self.request_log.append({
                        "url": url[:80] + "...",
                        "endpoint": ep,
                        "status": status,
                        "latency_s": round(dt, 2),
                        "interval_ok": elapsed >= self.min_interval - 0.1,
                        "attempt": attempt + 1,
                    })
                    return data
                except (urllib.error.URLError, urllib.error.HTTPError,
                        socket.timeout, OSError, ConnectionError) as e:
                    dt = time.time() - t0
                    err_msg = str(e)[:120]
                    if attempt < RETRY_ATTEMPTS - 1:
                        backoff = RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)]
                        time.sleep(backoff)
                    last_errors.append({
                        "endpoint": ep,
                        "attempt": attempt + 1,
                        "error": err_msg,
                        "latency_s": round(dt, 2),
                    })
                except Exception as e:
                    # 非网络错误（如 JSON 解析失败）不重试
                    self.request_log.append({
                        "url": url[:80],
                        "status": "ERROR",
                        "error": str(e)[:120],
                    })
                    raise

            # 当前端点全部重试失败，标记并切下一端点
            self._failed_endpoints.append(ep)

        # 全部端点失败 → 可操作错误提示
        self._raise_all_failed(last_errors)

    def _raise_all_failed(self, errors):
        """生成可操作的错误提示"""
        tried = ", ".join(self._failed_endpoints)
        msg_lines = [
            f"所有 HF API 端点均不可达（已尝试: {tried}）",
            "",
            "请按以下步骤排查：",
            "  ① 检查网络连通性：ping huggingface.co",
            "  ② 设置环境变量指定可用端点：$env:HF_API_BASE=\"https://your-proxy\"",
            "  ③ 检查 DNS 解析：nslookup huggingface.co",
            "  ④ 当前可用端点列表：" + ", ".join(self.endpoints),
        ]
        if errors:
            msg_lines.append("")
            msg_lines.append("最近错误：")
            for e in errors[-3:]:
                msg_lines.append(f"  [{e['endpoint']}] #{e['attempt']}: {e['error']}")
        raise ConnectionError("\n".join(msg_lines))

    min_interval = MIN_INTERVAL

    def compliance_report(self):
        """生成合规报告（含端点审计）"""
        n = len(self.request_log)
        if n == 0:
            return {"requests": 0, "active_endpoint": None}
        ok = all(r.get("status") == 200 and r.get("interval_ok", True) for r in self.request_log)
        return {
            "requests": n,
            "interval_compliant": ok,
            "min_interval_s": MIN_INTERVAL,
            "active_endpoint": self.active_endpoint,
            "endpoints_tried": list(self.endpoints),
            "failed_endpoints": self._failed_endpoints,
        }


def build_models_path(pipeline_tag: str, page: int, page_size: int = PAGE_SIZE) -> str:
    """构建 API 路径（按 pipeline_tag 拉模型列表，createdAt 降序，分页）"""
    params = urllib.parse.urlencode({
        "pipeline_tag": pipeline_tag,
        "sort": "createdAt",
        "direction": "-1",
        "limit": page_size,
        "full": "false",
    })
    return f"/api/models?{params}&page={page}"


def created_month(model: dict) -> str:
    """从模型元数据提取 createdAt 月份（YYYY-MM）"""
    t = model.get("createdAt", "") or model.get("lastModified", "")
    return t[:7] if t else ""


def main():
    parser = argparse.ArgumentParser(description="HuggingFace 模型月度采集器 v0.2")
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

    endpoints = get_endpoints()
    fetcher = HFFetcher(endpoints)
    print("=" * 64)
    print(f"HuggingFace 采集 v0.2 | 月份={month_str} | tags={len(args.tags)} | 每 tag ≤{args.max_pages} 页")
    print(f"端点列表: {endpoints}")
    print("=" * 64)

    nodes = []
    tag_errors = 0
    for i, tag in enumerate(args.tags, 1):
        count = 0
        pages_used = 0
        try:
            for page in range(1, args.max_pages + 1):
                path = build_models_path(tag, page)
                models = fetcher.fetch_json(path)
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
        except ConnectionError as e:
            # 全部端点不可达 → 致命错误，终止采集
            print(f"\n{'='*64}")
            print(f"❌ 致命错误：HF API 全部端点不可达，采集终止")
            print(f"{'='*64}")
            print(str(e))
            print(f"{'='*64}")
            nodes.append({"id": f"hf:{tag}", "name": tag, "parent": "huggingface",
                          "wuxing": None, "weight": 0, "error": str(e)})
            tag_errors += 1
            # 首个 tag 就全部失败 → 后续 tag 也不会成功，直接跳出
            break
        except Exception as e:
            print(f"[{i}/{len(args.tags)}] {tag}: ❌ {e}")
            nodes.append({"id": f"hf:{tag}", "name": tag, "parent": "huggingface",
                          "wuxing": None, "weight": 0, "error": str(e)})
            tag_errors += 1

    # 补全未采集的 tag（采集中断时）
    if tag_errors > 0 and len(nodes) < len(args.tags):
        for tag in args.tags[len(nodes):]:
            nodes.append({"id": f"hf:{tag}", "name": tag, "parent": "huggingface",
                          "wuxing": None, "weight": 0,
                          "error": "采集因端点不可达提前终止，此 tag 未执行"})

    comp = fetcher.compliance_report()
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
            "api": f"{comp.get('active_endpoint', 'unknown')}/api/models (createdAt 过滤)",
            "max_pages_per_tag": args.max_pages,
            "collector_version": "0.2",
            "endpoints_tried": comp.get("endpoints_tried", []),
            "failed_endpoints": comp.get("failed_endpoints", []),
            "tag_errors": tag_errors,
        },
    }
    out = Path(f"hf_tree_{month_str}.json")
    out.write_text(json.dumps(tree, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n[合规] requests={comp['requests']}, 间隔合规={comp['interval_compliant']}")
    print(f"[端点] active={comp.get('active_endpoint', 'N/A')}")
    if comp.get("failed_endpoints"):
        print(f"[端点] 失败={comp['failed_endpoints']}")
    print(f"[输出] {out}（{len(nodes)} tags，总权重 {tree['meta']['total_weight']}）")


if __name__ == "__main__":
    main()