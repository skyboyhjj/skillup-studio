#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
arXiv AI 子领域月度采集器 (W2)
================================
参考：docs/arxiv_ai_collect.py（11 分类白名单 + 分页 + 去重 + 双输出）
增强：指数退避重试 + 五行分类 + 统一 schema 节点树

功能：
  1. 11 个 AI 子领域白名单自动采集（单月）
  2. 分页拉全（MAX_PER_PAGE=2000, MAX_PER_CATEGORY=5000）
  3. arxiv_id 全局去重 + primary category 白名单匹配
  4. 输出三份：
     - papers-YYYYMM.json  论文明细（参考论文采集器格式）
     - arxiv_tree_YYYYMM.json 节点树（四源统一 schema，含五行标注）
     - arxiv_ai_tree_YYYYMM.json 节点树（ai_tree 格式，兼容参考实现）
  5. 合规：≥3 秒间隔 + User-Agent + 指数退避重试
  6. 关键词标注接口（可选：摘要关键词统计 → 子方向下钻）

用法（PowerShell）：
  python arxiv_collect.py --month 2026-07                    # 默认 11 分类
  python arxiv_collect.py --month 2026-07 --categories cs.AI cs.LG  # 自定义
  python arxiv_collect.py --month 2026-06 --backfill         # 历史回填
  python arxiv_collect.py --month 2026-07 --annotate         # 启用关键词标注

零依赖：urllib + xml.etree（Python 标准库）
"""

import argparse
import json
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, date
from pathlib import Path

# ============ 配置 ============
ARXIV_API_URL = "http://export.arxiv.org/api/query"
USER_AGENT = "wuxing-flowengine-arxiv-collector/0.3 (monthly snapshot; non-commercial research)"
MIN_INTERVAL = 3.0          # 合规：请求最小间隔（秒）
MAX_PER_PAGE = 2000         # arXiv API 单页上限
MAX_PER_CATEGORY = 5000     # 每分类每月采集上限（保护）
CONNECT_TIMEOUT_S = 10      # 连接超时（秒）
READ_TIMEOUT_S = 30         # 读取超时（秒）
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom",
           "arxiv": "http://arxiv.org/schemas/atom",
           "opensearch": "http://a9.com/-/spec/opensearch/1.1/"}

# 输出目录
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

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

# 11 分类 → 五行 canonical 标注（仲裁确认：docs/arXiv五行标注仲裁确认文档.md）
# 统一标注源：AI_CATEGORY_WUXING 为唯一权威映射
# 标注版本：v1（2026-08-09），语义映射原则：土=承载/水=流动/木=生发/金=结构/火=活跃
AI_CATEGORY_WUXING = {
    "cs.AI":   "火",   # 人工智能：综合、扩散、显性
    "cs.LG":   "土",   # 机器学习：基础承载（方法底座）
    "cs.CL":   "水",   # 计算语言：语言流动、理解
    "cs.CV":   "木",   # 计算机视觉：感知生发
    "cs.NE":   "水",   # 神经进化：神经流动、演化
    "cs.MA":   "木",   # 多智能体：多体协作、生发
    "cs.RO":   "金",   # 机器人：执行、结构、控制
    "cs.HC":   "火",   # 人机交互：交互活跃
    "cs.IR":   "金",   # 信息检索：筛选精确
    "cs.MM":   "火",   # 多媒体：多模态活跃
    "stat.ML": "土",   # 统计学习：统计基础
}

# 五行关键词映射（复用 phase1_pipeline 的 WUXING_KW，保留供非白名单分类使用）
WUXING_KW = {
    "木": {
        "kw": ["生成", "具身", "机器人", "多模态", "跨模态", "迁移", "生成式",
               "图像生成", "视频生成", "语音合成", "风格迁移", "3D", "扩散模型",
               "GAN", "世界模型", "神经辐射场", "视觉语言模型", "视觉问答"],
        "domains": ["cs.CV", "cs.RO", "cs.MM", "cs.GR", "cs.CG"],
    },
    "火": {
        "kw": ["推荐", "检索", "智能体", "协作", "社会模拟", "交互", "对话",
               "搜索", "排序", "个性化", "评估", "评测", "基准", "任务规划",
               "推理决策", "工具调用", "多智能体", "自动化", "人机协作"],
        "domains": ["cs.IR", "cs.HC", "cs.MA", "cs.SI", "cs.CY"],
    },
    "土": {
        "kw": ["基础", "架构", "系统", "硬件", "工程", "编译器", "分布式",
               "优化器", "并行", "框架", "平台", "软件", "MLP", "CNN", "RNN",
               "Transformer", "归一化", "正则化", "监督学习", "无监督学习",
               "持续学习", "图神经网络", "贝叶斯", "元学习", "迁移学习",
               "分布式训练", "模型压缩", "代码自动补全", "程序漏洞", "自动修复"],
        "domains": ["cs.LG", "cs.NE", "cs.SE", "cs.SY", "cs.DC", "cs.PL",
                    "cs.AR", "cs.ET", "cs.SC", "cs.CE", "cs.GT"],
    },
    "金": {
        "kw": ["安全", "可信", "伦理", "公平", "隐私", "对抗", "可解释", "鲁棒",
               "后门", "水印", "溯源", "审计", "逻辑", "推理", "知识表示",
               "知识图谱", "因果", "定理证明", "符号", "神经符号", "联邦学习",
               "加密", "差分隐私", "幻觉检测", "置信度", "模型量化"],
        "domains": ["cs.CR", "cs.IT", "cs.LO", "cs.DB", "cs.CC", "cs.DS"],
    },
    "水": {
        "kw": ["语言", "文本", "翻译", "摘要", "语义", "视觉", "图像", "视频",
               "目标检测", "分割", "识别", "科学", "蛋白质", "药物", "基因",
               "量子", "气象", "材料", "大语言模型", "预训练", "微调", "RLHF",
               "DPO", "思维链", "幻觉", "MoE", "量化", "RAG", "检索增强",
               "强化学习", "策略梯度", "扩散", "生成式模型", "状态空间",
               "数学", "优化", "统计", "概率", "数值", "动力系统"],
        "domains": ["cs.AI", "cs.CL", "math.OC", "math.ST", "math.PR",
                    "math.IT", "math.NA", "math.CO", "math.LO", "math.DS",
                    "math.FA", "math.CA", "math.MP", "stat.ML", "stat.ME",
                    "stat.AP", "stat.CO", "stat.TH"],
    },
}

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


# ============ 合规请求器（指数退避重试） ============
class PoliteFetcher:
    """合规请求器：间隔控制 + User-Agent + 指数退避重试 + 请求日志"""

    def __init__(self, min_interval=MIN_INTERVAL, user_agent=USER_AGENT,
                 max_retries=3, retry_base_delay=5.0):
        self.min_interval = min_interval
        self.user_agent = user_agent
        self.last_request_time = 0.0
        self.request_log = []
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay
        self.retry_stats = {"total_retries": 0, "retry_successes": 0}

    def fetch(self, url):
        """带指数退避重试 + 超时拆分（连接 10s + 读取 30s）的请求（v0.3）"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)

        last_error = None
        for attempt in range(1 + self.max_retries):  # 1 次初始 + N 次重试
            self.last_request_time = time.time()
            req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
            t0 = time.time()
            old_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(CONNECT_TIMEOUT_S)  # 连接超时 10s
            try:
                with urllib.request.urlopen(req, timeout=READ_TIMEOUT_S) as resp:  # 读取超时 30s
                    body = resp.read().decode("utf-8")
                dt = time.time() - t0
                self.request_log.append({
                    "url": url[:100] + "..." if len(url) > 100 else url,
                    "status": 200,
                    "latency_s": round(dt, 2),
                    "interval_ok": elapsed >= self.min_interval - 0.1,
                    "attempts": attempt + 1,
                })
                if attempt > 0:
                    self.retry_stats["retry_successes"] += 1
                return body
            except urllib.error.HTTPError as e:
                last_error = f"HTTP {e.code}: {e.reason}"
                self.retry_stats["total_retries"] += 1
            except Exception as e:
                last_error = str(e)
                self.retry_stats["total_retries"] += 1
            finally:
                socket.setdefaulttimeout(old_timeout)

            # 指数退避：5s → 10s → 20s
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
            "interval_compliant": ok,
            "avg_latency_s": round(sum(lat) / len(lat), 2) if lat else None,
            "min_interval_s": self.min_interval,
            "retry": {
                "total_retries": self.retry_stats["total_retries"],
                "retry_successes": self.retry_stats["retry_successes"],
                "requests_retried": len(retried),
                "max_retries": self.max_retries,
                "retry_base_delay_s": self.retry_base_delay,
            },
            "timeout": {
                "connect_s": CONNECT_TIMEOUT_S,
                "read_s": READ_TIMEOUT_S,
            },
            "note": "间隔合规" if ok else "存在间隔不足或请求错误",
            "error_details": [e["error"] for e in errors] if errors else [],
        }


# ============ 查询与解析 ============
def _last_day_of_month(year: int, month: int) -> int:
    """返回指定月份的最后一天"""
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
    """解析 Atom XML → 论文条目列表"""
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
            "published": published[:10] if published else "",
            "categories": categories,
            "authors": authors,
            "link": link,
            "summary": summary,
        })
    return entries


# ============ 五行分类 ============
def classify_wuxing(category: str) -> str:
    """五行分类：AI_CATEGORY_WUXING 优先 → WUXING_KW.domains 兜底 → 默认水"""
    if category in AI_CATEGORY_WUXING:
        return AI_CATEGORY_WUXING[category]
    for wx, cfg in WUXING_KW.items():
        if category in cfg["domains"]:
            return wx
    return "水"


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
    parser.add_argument("--categories", nargs="+", default=None,
                        help=f"分类白名单（默认 11 类：{', '.join(AI_CATEGORIES)}）")
    parser.add_argument("--annotate", action="store_true", help="启用关键词子方向标注")
    parser.add_argument("--backfill", action="store_true", help="历史回填模式")
    parser.add_argument("--verbose", action="store_true", help="详细输出")
    args = parser.parse_args()

    # 月份解析
    if args.month:
        year, month = map(int, args.month.split("-"))
    else:
        today = date.today()
        year, month = (today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12)
    month_str = f"{year}-{month:02d}"

    # 分类列表
    categories = args.categories if args.categories else AI_CATEGORIES

    fetcher = PoliteFetcher()
    print("=" * 64)
    print(f"arXiv AI 子领域采集 | 月份={month_str} | 分类数={len(categories)}")
    print("=" * 64)

    papers = {}           # arxiv_id → paper（全局去重）
    cat_counter = Counter()  # primary category 计数
    cat_errors = {}       # 分类级错误

    for ci, cat in enumerate(categories, 1):
        query = build_query(cat, year, month)
        start = 0
        cat_count = 0
        page = 0
        print(f"\n[{ci}/{len(categories)}] {cat} ...", end="", flush=True)
        try:
            while start < MAX_PER_CATEGORY:
                url = build_url(query, start, MAX_PER_PAGE)
                body = fetcher.fetch(url)
                if body is None:
                    cat_errors[cat] = "API 请求失败（含重试）"
                    print(f" ERROR")
                    break
                entries = parse_feed(body)
                if not entries:
                    break
                for e in entries:
                    if not e["arxiv_id"]:
                        continue
                    is_new = e["arxiv_id"] not in papers
                    if is_new:
                        papers[e["arxiv_id"]] = e
                    # primary category：白名单内匹配（仅首次计入分布）
                    if is_new:
                        primary = next(
                            (c for c in e["categories"] if c in categories),
                            e["categories"][0] if e["categories"] else cat
                        )
                        cat_counter[primary] += 1
                cat_count += len(entries)
                page += 1
                start += MAX_PER_PAGE
                if len(entries) < MAX_PER_PAGE:
                    break
            if cat not in cat_errors:
                print(f" {cat_count:5d} 篇（{page} 页）-> 累计 {len(papers)} 篇")
        except Exception as e:
            cat_errors[cat] = str(e)
            print(f" ERROR: {e}")

    # ===== 关键词标注（可选） =====
    if args.annotate:
        for p in papers.values():
            p["topics"] = annotate_topics(p)
        topic_counter = Counter(t for p in papers.values() for t in p.get("topics", []))
        print(f"\n[子方向标注] 热点分布（Top 5）:")
        for t, c in topic_counter.most_common(5):
            print(f"  {t}: {c}")

    # ===== 输出 1：论文明细 =====
    paper_list = sorted(papers.values(), key=lambda p: p["published"], reverse=True)
    papers_path = OUTPUT_DIR / f"papers_{year}{month:02d}.json"
    papers_path.parent.mkdir(parents=True, exist_ok=True)
    papers_path.write_text(
        json.dumps(paper_list, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    # ===== 输出 2：节点树（四源统一 schema，含五行） =====
    nodes = []
    for cat in categories:
        weight = cat_counter.get(cat, 0)
        nodes.append({
            "id": cat,
            "name": cat,
            "parent": cat.split(".")[0],
            "wuxing": classify_wuxing(cat),
            "weight": weight,
        })
    tree = {
        "schema_version": "1.0",
        "source": "arxiv",
        "timestamp": month_str,
        "nodes": nodes,
        "meta": {
            "node_count": len(nodes),
            "total_weight": sum(cat_counter.values()),
            "unique_papers": len(papers),
            "categories_used": len(categories),
            "categories_zero": sum(1 for cat in categories if cat_counter.get(cat, 0) == 0),
            "api_used": "export.arxiv.org/api/query",
            "collector_version": "0.3",
            "timeout": {"connect_s": CONNECT_TIMEOUT_S, "read_s": READ_TIMEOUT_S},
        },
    }
    tree_path = OUTPUT_DIR / f"arxiv_tree_{year}{month:02d}.json"
    tree_path.write_text(
        json.dumps(tree, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # ===== 输出 3：ai_tree 兼容格式（参考实现） =====
    ai_tree = {
        "schema_version": "1.0",
        "source": "arxiv_ai",
        "timestamp": datetime.now().strftime("%Y-%m-%d"),
        "month": month_str,
        "nodes": [{"id": cat, "name": cat, "parent": cat.split(".")[0],
                    "wuxing": classify_wuxing(cat),
                    "weight": cat_counter.get(cat, 0)} for cat in categories],
        "meta": {
            "node_count": len(categories),
            "total_weight": sum(cat_counter.values()),
            "unique_papers": len(papers),
            "categories_used": len(categories),
        },
    }
    ai_tree_path = OUTPUT_DIR / f"arxiv_ai_tree_{year}{month:02d}.json"
    ai_tree_path.write_text(
        json.dumps(ai_tree, ensure_ascii=False, indent=2), encoding="utf-8"
    )

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

    # ===== 控制台摘要 =====
    print(f"\n{'='*64}")
    print(f"采集完成 | 月份={month_str}")
    print(f"  去重论文数 : {len(papers)}")
    print(f"  分类分布   :")
    for cat, count in cat_counter.most_common():
        wx = classify_wuxing(cat)
        print(f"    [{wx}] {cat:12s} {count:5d} 篇")
    if cat_errors:
        print(f"  错误分类   : {len(cat_errors)}")
        for cat, err in cat_errors.items():
            print(f"    ⚠ {cat}: {err}")
    print(f"  输出文件   :")
    print(f"    {papers_path.name}（论文明细 {len(paper_list)} 篇）")
    print(f"    {tree_path.name}（节点树 {len(nodes)} 分类，含五行）")
    print(f"    {ai_tree_path.name}（ai_tree 兼容格式）")
    print(f"{'='*64}")

    # 五行分布
    wx_dist = Counter()
    for node in nodes:
        wx_dist[node["wuxing"]] += node["weight"]
    total = tree["meta"]["total_weight"]
    if total > 0:
        print(f"\n[五行分布]")
        for wx in ["木", "火", "土", "金", "水"]:
            count = wx_dist.get(wx, 0)
            pct = count / total * 100
            bar = "█" * int(pct / 2)
            print(f"  {wx}: {count:5d} 篇 ({pct:5.1f}%) {bar}")


if __name__ == "__main__":
    main()