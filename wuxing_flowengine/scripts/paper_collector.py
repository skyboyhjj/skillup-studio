#!/usr/bin/env python3
"""
月度论文自动采集器：从 arXiv API 抓取上月 AI/ML 领域最新论文。

数据源:
  arXiv API (http://export.arxiv.org/api/query)
  搜索范围: cs.AI, cs.CL, cs.CV, cs.LG, cs.RO, stat.ML

输出:
  output/papers_{YYYY-MM}.json — 论文标题 + 摘要 + arXiv ID + 分类

用法:
  python paper_collector.py                          # 采集上月论文
  python paper_collector.py --month 2026-07          # 指定月份
  python paper_collector.py --max-results 200        # 限制结果数
  python paper_collector.py --dry-run                # 仅预览
"""
import json, os, sys, re, time, argparse, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from collections import Counter

# ============================================================
# 配置
# ============================================================
ARXIV_API = "http://export.arxiv.org/api/query"

# arXiv 分类映射（cs 子领域）
ARXIV_CATEGORIES = [
    "cs.AI",    # 人工智能
    "cs.CL",    # 计算语言学 / NLP
    "cs.CV",    # 计算机视觉
    "cs.HC",    # 人机交互
    "cs.LG",    # 机器学习
    "cs.RO",    # 机器人学
    "cs.CR",    # 密码学与安全
    "cs.IR",    # 信息检索
    "cs.NE",    # 神经与进化计算
    "cs.SE",    # 软件工程
    "stat.ML",  # 统计机器学习
]

# 请求间隔（秒），避免触发 arXiv 限流
REQUEST_DELAY = 3.0
BATCH_SIZE = 100  # 每页结果数


def build_query(month_start, month_end):
    """构建 arXiv API 查询字符串"""
    # 按提交日期范围过滤
    date_range = f"submittedDate:[{month_start} TO {month_end}]"

    # 分类过滤
    cat_filter = " OR ".join(f"cat:{c}" for c in ARXIV_CATEGORIES)
    query = f"({cat_filter}) AND ({date_range})"

    return query


def fetch_papers(query, start=0, max_results=100):
    """调用 arXiv API 获取论文列表"""
    params = {
        "search_query": query,
        "start": start,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    url = f"{ARXIV_API}?{urllib.parse.urlencode(params)}"

    req = urllib.request.Request(url, headers={"User-Agent": "WuxingFlowEngine/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        print(f"  ⚠ arXiv API 请求失败: {e}")
        return None


def parse_response(xml_text):
    """解析 arXiv API XML 响应"""
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        print(f"  ⚠ XML 解析失败: {e}")
        return [], 0

    total_results = 0
    for el in root.findall("atom:totalResults", ns) or root.findall("opensearch:totalResults", {"opensearch": "http://a9.com/-/spec/opensearch/1.1/"}):
        total_results = int(el.text)
        break

    papers = []
    for entry in root.findall("atom:entry", ns):
        paper = {
            "arxiv_id": "",
            "title": "",
            "summary": "",
            "published": "",
            "categories": [],
            "authors": [],
            "link": "",
        }
        # ID
        id_el = entry.find("atom:id", ns)
        if id_el is not None:
            raw_id = id_el.text.strip()
            # 提取纯 arXiv ID (去掉 http://arxiv.org/abs/ 前缀和版本号)
            paper["arxiv_id"] = re.sub(r"^.*/abs/", "", raw_id)
            paper["arxiv_id"] = re.sub(r"v\d+$", "", paper["arxiv_id"])

        # 标题
        title_el = entry.find("atom:title", ns)
        if title_el is not None:
            paper["title"] = " ".join(title_el.text.strip().split())

        # 摘要
        summary_el = entry.find("atom:summary", ns)
        if summary_el is not None:
            paper["summary"] = " ".join(summary_el.text.strip().split())

        # 发布日期
        pub_el = entry.find("atom:published", ns)
        if pub_el is not None:
            paper["published"] = pub_el.text.strip()[:10]

        # 分类
        for cat_el in entry.findall("arxiv:primary_category", ns):
            paper["categories"].append(cat_el.get("term", ""))
        for cat_el in entry.findall("atom:category", ns):
            term = cat_el.get("term", "")
            if term and term not in paper["categories"]:
                paper["categories"].append(term)

        # 作者
        for author_el in entry.findall("atom:author", ns):
            name_el = author_el.find("atom:name", ns)
            if name_el is not None:
                paper["authors"].append(name_el.text.strip())

        # 链接
        for link_el in entry.findall("atom:link", ns):
            if link_el.get("title") == "pdf":
                paper["link"] = link_el.get("href", "")
                break
        if not paper["link"]:
            for link_el in entry.findall("atom:link", ns):
                if link_el.get("rel") == "alternate":
                    paper["link"] = link_el.get("href", "")
                    break

        papers.append(paper)

    return papers, total_results


def collect_papers(month_label, max_results=500, base_dir=None):
    """
    采集指定月份的论文。

    参数:
        month_label: 月份标签，如 "2026-07"
        max_results: 最大论文数
        base_dir:    项目根目录

    返回:
        {"status": "ok", "papers": [...], "count": N, "output_path": "..."}
    """
    if base_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # 计算月份起止日期
    try:
        year, month = month_label.split("-")
        dt = datetime(int(year), int(month), 1)
        month_start = dt.strftime("%Y%m%d")
        # 下个月第一天
        if dt.month == 12:
            next_month = datetime(dt.year + 1, 1, 1)
        else:
            next_month = datetime(dt.year, dt.month + 1, 1)
        month_end = (next_month - timedelta(days=1)).strftime("%Y%m%d")
    except Exception as e:
        print(f"  ⚠ 月份解析失败: {month_label}: {e}")
        return {"status": "error", "error": str(e)}

    print("=" * 70)
    print(f"  月度论文采集器 — {month_label} ({month_start} ~ {month_end})")
    print("=" * 70)

    query = build_query(month_start, month_end)
    print(f"\n  查询: {query[:100]}...")
    print(f"  目标: 最多 {max_results} 篇")

    all_papers = []
    start = 0

    while len(all_papers) < max_results:
        batch_size = min(BATCH_SIZE, max_results - len(all_papers))
        print(f"\n  正在获取 {start}-{start + batch_size}...")

        xml_text = fetch_papers(query, start=start, max_results=batch_size)
        if xml_text is None:
            break

        papers, total = parse_response(xml_text)
        if not papers:
            print(f"  无更多结果（total={total}）")
            break

        all_papers.extend(papers)
        print(f"  已获取 {len(all_papers)} 篇（总计 {total} 篇可用）")

        if len(all_papers) >= total:
            break

        start += batch_size
        time.sleep(REQUEST_DELAY)

    # 去重（按 arxiv_id）
    seen_ids = set()
    deduped = []
    for p in all_papers:
        if p["arxiv_id"] and p["arxiv_id"] not in seen_ids:
            seen_ids.add(p["arxiv_id"])
            deduped.append(p)

    print(f"\n{'─' * 50}")
    print(f"  汇总")
    print(f"{'─' * 50}")
    print(f"  原始获取: {len(all_papers)} 篇")
    print(f"  去重后:   {len(deduped)} 篇")

    # 分类分布
    cat_counter = Counter()
    for p in deduped:
        for c in p["categories"]:
            cat_counter[c] += 1
    print(f"  分类分布:")
    for cat, cnt in cat_counter.most_common(10):
        print(f"    {cat}: {cnt}")

    # 保存
    output_dir = os.path.join(base_dir, "output")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"papers_{month_label}.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(deduped, f, ensure_ascii=False, indent=2)

    print(f"\n  已保存: {output_path}")
    print("=" * 70)

    return {
        "status": "ok",
        "papers": deduped,
        "count": len(deduped),
        "output_path": output_path,
        "categories": dict(cat_counter.most_common()),
    }


def run(base_dir=None, month_label=None, max_results=500, dry_run=False):
    """采集器入口"""
    if month_label is None:
        # 默认采集上月
        now = datetime.now()
        prev = now - timedelta(days=now.day + 1)
        month_label = prev.strftime("%Y-%m")

    if dry_run:
        print(f"[DRY RUN] 将采集 {month_label} 的论文（arXiv API）")
        print(f"  分类: {ARXIV_CATEGORIES}")
        return {"status": "ok", "dry_run": True}

    return collect_papers(month_label, max_results, base_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="月度论文自动采集器")
    parser.add_argument("--month", "-m", type=str, default=None, help="月份标签，如 2026-07")
    parser.add_argument("--base-dir", "-b", type=str, default=None, help="项目根目录")
    parser.add_argument("--max-results", "-n", type=int, default=500, help="最大论文数")
    parser.add_argument("--dry-run", action="store_true", help="仅预览")
    args = parser.parse_args()

    DEFAULT_BASE = r"C:\Users\hejij\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a59e217b55e181ea97f0df3\wuxing_flowengine"
    base_dir = args.base_dir or DEFAULT_BASE

    result = run(
        base_dir=base_dir,
        month_label=args.month,
        max_results=args.max_results,
        dry_run=args.dry_run,
    )
    print(f"\n结果: {result['status']}")