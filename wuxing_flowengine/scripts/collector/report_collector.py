#!/usr/bin/env python3
"""
月度报告采集器：通过 HTTP API 获取当月报告列表和论文标题
"""
import json, os, time, urllib.request, urllib.parse
from datetime import datetime


def fetch_report_list(api_url="https://hub-notion.baai.ac.cn/api_v2/api/reports_graph"):
    """获取报告列表"""
    req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def fetch_report_detail(domain, report_id,
                       api_url="https://hub-notion.baai.ac.cn/api_v2/api/reports_detail"):
    """获取单份报告详情 (Tiptap JSON)"""
    url = "%s?title=%s&id=%s" % (api_url, urllib.parse.quote(domain), report_id)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def extract_papers_from_tiptap(content):
    """从 Tiptap JSON 递归提取 ordered_list / bullet_list 中的文本"""
    papers = []

    def walk(blocks):
        for b in blocks:
            if b.get("type") in ("ordered_list", "bullet_list"):
                for item in b.get("content", []):
                    for p in item.get("content", []):
                        text = "".join(ct.get("text", "") for ct in p.get("content", []))
                        if text.strip():
                            papers.append(text.strip())
            if "content" in b and isinstance(b["content"], list):
                walk(b["content"])

    walk(content)
    return papers


def extract_trend_summary(content):
    """从 Tiptap JSON 提取趋势摘要文本"""
    text_parts = []
    for b in content:
        if b.get("type") == "paragraph":
            for ct in b.get("content", []):
                t = ct.get("text", "")
                if t:
                    text_parts.append(t)
    return "".join(text_parts)


def collect_monthly_papers(domains, report_ids, output_dir, raw_dir, retry_config=None):
    """
    逐领域采集论文标题

    参数:
        domains: 领域名列表
        report_ids: {领域名: report_id} 映射 (从 reports_graph 获取)
        output_dir: 论文标题输出目录
        raw_dir: 原始 API 响应保存目录
        retry_config: {"max_attempts": 3, "backoff_factor": 2.0, "initial_delay_seconds": 2}

    返回:
        {领域名: [论文标题列表]}
    """
    if retry_config is None:
        retry_config = {"max_attempts": 3, "backoff_factor": 2.0, "initial_delay_seconds": 2}

    all_papers = {}
    stats = {"total_calls": 0, "success": 0, "failed": 0, "empty": 0}

    for domain in domains:
        rid = report_ids.get(domain)
        if not rid:
            print(f"  [SKIP] {domain}: 无 report_id")
            stats["failed"] += 1
            all_papers[domain] = []
            continue

        # 带重试的 API 调用
        papers = []
        detail_raw = None
        for attempt in range(1, retry_config["max_attempts"] + 1):
            try:
                stats["total_calls"] += 1
                detail_raw = fetch_report_detail(domain, rid)
                content = detail_raw["info"]["documentInfo"]["data"]["content"]
                papers = extract_papers_from_tiptap(content)
                stats["success"] += 1
                break
            except Exception as e:
                print(f"  [RETRY {attempt}/{retry_config['max_attempts']}] {domain}: {e}")
                if attempt < retry_config["max_attempts"]:
                    delay = retry_config["initial_delay_seconds"] * (retry_config["backoff_factor"] ** (attempt - 1))
                    time.sleep(delay)
                else:
                    stats["failed"] += 1

        if not papers:
            stats["empty"] += 1
            print(f"  [WARN] {domain}: 未提取到论文 ({len(papers)} 篇)")
        else:
            print(f"  [OK] {domain}: {len(papers)} 篇论文")

        all_papers[domain] = papers

        # 保存原始响应
        if detail_raw and raw_dir:
            raw_path = os.path.join(raw_dir, f"{domain}_detail.json")
            with open(raw_path, "w", encoding="utf-8") as f:
                json.dump(detail_raw, f, ensure_ascii=False, indent=2)

        # 领域间延迟
        time.sleep(1)

    print(f"\n  采集统计: {stats['success']}/{stats['total_calls']} 成功, "
          f"{stats['failed']} 失败, {stats['empty']} 领域无数据")

    return all_papers


def get_report_ids_from_list(report_list, domains):
    """
    从 reports_graph 返回的列表提取每个领域的 report_id

    参数:
        report_list: reports_graph API 返回的列表
        domains: 目标领域名列表

    返回:
        {领域名: report_id}
    """
    report_ids = {}
    for item in report_list:
        cat = item.get("categoryName", "")
        if cat in domains:
            report_ids[cat] = item.get("id")
    return report_ids