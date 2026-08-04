"""
BAAI Hub 论文采集脚本 V2
从 hub-notion.baai.ac.cn/api_v2/api/ 获取各领域论文数据

七条核心教训（已全部应用）：
1. API 响应 ≠ 期望格式 — Tiptap 富文本 JSON，论文标题埋在嵌套列表结构中，需递归解析
2. 同一 API、不同领域可能返回不同格式 — bullet_list vs ordered_list，英文标题 vs 中文摘要
3. API 返回数量 ≠ 可用数量 — 需过滤非论文文本、去重
4. 中文 URL 参数必须编码 — urllib.parse.quote() 不可省略
5. API 不提供历史回溯 — reports_list 获取历史报告 ID
6. 弹窗是浏览器自动化的第一道坎 — 本脚本使用 API，无此问题
7. 数据验证必须在流水线中 — 语言检测、去重、数量一致性、格式一致性
"""
import json
import urllib.request
import urllib.parse
import os
import sys
import time
import re
from collections import Counter

# 16 个领域
DOMAINS = [
    "大语言模型", "自然语言处理", "具身智能与机器人", "多模态智能",
    "智能体", "生成式 AI", "机器学习基础", "安全、可信与伦理",
    "计算机视觉", "交叉领域智能应用", "知识表示与逻辑推理",
    "推荐系统与信息检索", "AI 系统与硬件", "软件工程与编程",
    "科学 AI", "其他AI领域"
]

API_BASE = "https://hub-notion.baai.ac.cn/api_v2/api"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")

# ============================================================
# 教训 1+2: 识别所有可能的 section header
# "代表性论文：" 和 "代表性论文" 都会被 Tiptap 渲染为段落文本
# ============================================================
SECTION_HEADERS = {
    '关键问题', '关键方法', '核心亮点', '剩余关键问题', '代表性论文',
    '关键问题：', '关键方法：', '核心亮点：', '剩余关键问题：', '代表性论文：',
    '研究的关键问题', '研究的关键问题：',
    '现存关键问题', '现存关键问题：',
}

# 非论文文本特征模式（中文段落，非论文标题）
NON_PAPER_PATTERNS = [
    re.compile(r'^本月研究'), re.compile(r'^当前.*研究'),
    re.compile(r'^研究趋势'), re.compile(r'^本[月季度]'),
    re.compile(r'^AI.*呈现'), re.compile(r'^在.*方面'),
    re.compile(r'^如何'), re.compile(r'^为什么'),
    re.compile(r'^论文.*在.*方面'), re.compile(r'^[^\w]*$'),
]


def fetch_json(url):
    """带重试的 JSON 获取"""
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            print(f"  尝试 {attempt+1}/3 失败: {e}")
            time.sleep(1)
    return None


def get_reports(domain):
    """获取某领域的历史报告列表 (reports_list API)"""
    encoded = urllib.parse.quote(domain)
    url = f"{API_BASE}/reports_list?title={encoded}"
    data = fetch_json(url)
    if not data or 'list' not in data:
        return []
    return data['list']


def fetch_reports_graph():
    """
    获取所有领域最新月报摘要 (reports_graph API)
    文档 §2.1: 返回所有领域最新月报摘要 (id, title, docId, createdAt)
    用作 reports_list 的补充——当 reports_list 返回空时，用此兜底
    """
    url = f"{API_BASE}/reports_graph"
    data = fetch_json(url)
    if not data or 'list' not in data:
        return []
    return data['list']


def find_texts(node):
    """递归提取所有文本"""
    texts = []
    if isinstance(node, dict):
        if node.get('type') == 'text':
            texts.append(node.get('text', ''))
        if 'content' in node:
            for child in node['content']:
                texts.extend(find_texts(child))
    elif isinstance(node, list):
        for child in node:
            texts.extend(find_texts(child))
    return texts


def is_section_header(text):
    """判断文本是否为 section header"""
    t = text.strip().rstrip('：:')
    return t in SECTION_HEADERS or text.strip() in SECTION_HEADERS


def extract_papers_from_list_item(item):
    """
    教训 1+2 核心修复:
    从 list_item 中提取论文标题。
    论文在嵌套的 bullet_list/ordered_list 的子 list_item 中。
    跳过 section header 段落（如 "代表性论文："）。
    """
    result = []
    for child in item.get('content', []):
        ct = child.get('type', '')
        if ct in ('bullet_list', 'ordered_list'):
            # 嵌套列表中的 list_item 是论文
            for si in child.get('content', []):
                if si.get('type') == 'list_item':
                    # 论文标题可能在 paragraph 或文本节点中
                    paper_text = ''.join(find_texts(si)).strip()
                    if paper_text and not is_section_header(paper_text):
                        result.append(paper_text)
        # 注意：不再提取 paragraph 直接子节点，避免 "代表性论文：" 污染
    return result


def extract_papers_from_tiptap(content):
    """
    教训 1+2: 从 Tiptap 富文本 JSON 中递归提取论文标题
    兼容三种格式：

    格式A (嵌套列表): bullet_list -> list_item("代表性论文") -> 嵌套 bullet_list -> 论文
      用于: 大语言模型(05/06月)、具身智能与机器人、安全可信等多数领域

    格式B (平铺段落): paragraph("代表性论文") -> 紧随的 bullet_list -> 论文
      用于: 自然语言处理、机器学习基础

    格式C (兄弟列表项): bullet_list -> list_item("代表性论文") -> 后续兄弟 list_item -> 论文
      用于: 大语言模型(07月)
    """
    papers = []

    # 格式A+格式C: 递归遍历，查找包含 "代表性论文" 的 list_item
    def walk_for_nested(node):
        if isinstance(node, dict):
            t = node.get('type', '')
            if t in ('bullet_list', 'ordered_list'):
                items = node.get('content', [])
                for idx, item in enumerate(items):
                    if item.get('type') == 'list_item':
                        all_text = ''.join(find_texts(item))
                        if '代表性论文' in all_text:
                            # 格式A: 先尝试嵌套列表中的论文
                            nested = extract_papers_from_list_item(item)
                            papers.extend(nested)

                            # 格式C: 如果嵌套列表无结果，检查后续兄弟 list_item
                            if not nested:
                                for j in range(idx + 1, len(items)):
                                    sibling = items[j]
                                    if sibling.get('type') == 'list_item':
                                        sibling_text = ''.join(find_texts(sibling)).strip()
                                        # 检查是否还是论文标题（非 section header）
                                        if sibling_text and not is_section_header(sibling_text):
                                            # 如果遇到下一个 section header，停止
                                            if '关键问题' in sibling_text or '关键方法' in sibling_text or '核心亮点' in sibling_text:
                                                break
                                            papers.append(sibling_text)
                                    else:
                                        break  # 遇到非 list_item 停止
            if 'content' in node:
                for child in node['content']:
                    walk_for_nested(child)
        elif isinstance(node, list):
            for child in node:
                walk_for_nested(child)

    # 格式B: 线性扫描，查找 paragraph("代表性论文") 后紧跟的 bullet_list/ordered_list
    def walk_for_flat(nodes):
        for i, node in enumerate(nodes):
            if isinstance(node, dict):
                t = node.get('type', '')
                # 寻找 "代表性论文" paragraph
                if t == 'paragraph':
                    text = ''.join(find_texts(node)).strip()
                    if text == '代表性论文' or text == '代表性论文：':
                        # 检查后续节点
                        for j in range(i + 1, min(i + 3, len(nodes))):
                            next_node = nodes[j]
                            if isinstance(next_node, dict) and next_node.get('type') in ('bullet_list', 'ordered_list'):
                                for si in next_node.get('content', []):
                                    if si.get('type') == 'list_item':
                                        paper_text = ''.join(find_texts(si)).strip()
                                        if paper_text and not is_section_header(paper_text):
                                            papers.append(paper_text)
                                break  # 只取紧跟的第一个列表
                # 递归处理子节点中的平铺结构
                if 'content' in node:
                    walk_for_flat(node['content'])

    # 先尝试格式A
    walk_for_nested(content)

    # 格式A 没找到论文时，尝试格式B
    if not papers:
        walk_for_flat(content)

    return papers


def is_english_title(title):
    """
    教训 7: 语言检测
    判断是否为英文论文标题（英文论文标题通常以字母为主）
    """
    alpha = sum(1 for c in title if c.isascii() and c.isalpha())
    total = len(title)
    if total == 0:
        return False
    # 英文论文标题：字母占比 > 60%
    return alpha / total > 0.6


def is_likely_paper_title(title):
    """
    教训 7: 格式一致性验证
    判断文本是否像论文标题（而非摘要、段落、列表项说明）
    """
    t = title.strip()

    # 过短（< 10 字符）大概率不是论文标题
    if len(t) < 10:
        return False

    # 过长的中文文本（> 100 字符）大概率是摘要
    if len(t) > 100:
        cn_chars = sum(1 for c in t if '\u4e00' <= c <= '\u9fff')
        if cn_chars > 10:
            return False

    # 匹配非论文文本模式
    for pat in NON_PAPER_PATTERNS:
        if pat.match(t):
            return False

    return True


def clean_title(title):
    """清理论文标题"""
    title = title.strip()
    # 去除开头编号
    title = re.sub(r'^[\d]+[\.\、\)]\s*', '', title)
    title = title.strip('"\'""''')
    return title


def fetch_papers_for_report(domain, report_id):
    """
    获取某报告的论文列表
    教训 4: 中文 URL 参数编码
    """
    encoded = urllib.parse.quote(domain)
    url = f"{API_BASE}/reports_detail?title={encoded}&id={report_id}"
    data = fetch_json(url)
    if not data or 'info' not in data:
        return []

    info = data['info']
    doc_info = info.get('documentInfo', {})
    if not doc_info:
        return []

    tiptap_data = doc_info.get('data', {})
    content = tiptap_data.get('content', [])

    if not content:
        return []

    raw_papers = extract_papers_from_tiptap(content)

    # 教训 3+7: 数据验证流水线
    cleaned = []
    for p in raw_papers:
        p = clean_title(p)
        if len(p) < 10:
            continue
        if is_section_header(p):
            continue
        if not is_likely_paper_title(p):
            continue
        cleaned.append(p)

    return cleaned


def validate_and_dedup(papers, label):
    """
    教训 7: 完整数据验证流水线
    - 语言检测
    - 去重
    - 数量一致性
    """
    print(f"\n[{label}] 验证前: {len(papers)} 篇")

    # 语言分类
    en_papers = [p for p in papers if is_english_title(p['title'])]
    cn_papers = [p for p in papers if not is_english_title(p['title'])]

    # 去重（基于 title 精确匹配）
    seen = set()
    unique = []
    for p in papers:
        key = p['title'].strip().lower()
        if key not in seen:
            seen.add(key)
            unique.append(p)

    dupes = len(papers) - len(unique)

    # 统计
    domain_counts = Counter(p['domain'] for p in unique)
    en_count = sum(1 for p in unique if p['is_english'])
    cn_count = len(unique) - en_count

    print(f"  验证后: {len(unique)} 篇 (去重 {dupes} 个)")
    print(f"  英文: {en_count} | 中文: {cn_count}")
    for d, c in domain_counts.most_common():
        print(f"  {d}: {c} 篇")

    # 教训 3: 标记零论文领域
    covered = set(domain_counts.keys())
    missing = set(DOMAINS) - covered
    if missing:
        print(f"  ⚠ 零论文领域: {', '.join(sorted(missing))}")

    if cn_count > 0:
        print(f"  ⚠ 中文条目 {cn_count} 个（非论文文本，已保留供检查）")

    return unique, dupes, cn_count


def check_cross_month_consistency(all_data):
    """
    文档 §5 检查点 5: 同领域不同月份格式一致性检查

    同一领域的不同月份报告，论文标题的语言/格式应该一致。
    不一致 → 可能是模板切换或数据异常（如软件工程与编程 5 月的中文摘要问题）。

    Args:
        all_data: {month_key: [{title, domain, is_english}, ...]}

    Returns:
        list of (domain, issue) tuples for domains with cross-month inconsistencies
    """
    issues = []
    # 收集每个领域各月份的英文占比
    domain_monthly = defaultdict(lambda: defaultdict(list))
    for month, papers in all_data.items():
        for p in papers:
            domain_monthly[p['domain']][month].append(p['is_english'])

    for domain, months in domain_monthly.items():
        ratios = {}
        for month, flags in months.items():
            if flags:
                ratios[month] = sum(flags) / len(flags)

        if len(ratios) >= 2:
            values = list(ratios.values())
            # 某个月的英文占比与其它月差异超过 50%
            for month, ratio in ratios.items():
                other_ratios = [v for m, v in ratios.items() if m != month]
                if other_ratios:
                    avg_other = sum(other_ratios) / len(other_ratios)
                    if abs(ratio - avg_other) > 0.5:
                        issues.append({
                            'domain': domain,
                            'month': month,
                            'ratio': round(ratio, 3),
                            'other_avg': round(avg_other, 3),
                            'issue': f'{domain} {month}月 英文占比 {ratio:.1%} vs 其他月份 {avg_other:.1%}，差异显著'
                        })

    return issues


def validate_papers_batch(papers):
    """
    文档 §7.1: 可复用的论文验证模板

    对一批论文标题执行完整验证：
    - 语言检测 (英文占比)
    - 数量统计
    - 标记需要人工复核的批次

    Returns:
        dict with total, english_titles, english_ratio, needs_review
    """
    total = len(papers)
    if total == 0:
        return {'total': 0, 'english_titles': 0, 'english_ratio': 0.0, 'needs_review': True}

    english = sum(1 for t in papers if any(c.isascii() and c.isalpha() for c in t[:20]))
    ratio = english / total
    return {
        'total': total,
        'english_titles': english,
        'english_ratio': round(ratio, 4),
        'needs_review': ratio < 0.8
    }


def main():
    targets = sys.argv[1:] if len(sys.argv) > 1 else ['05', '06', '07']
    print("=" * 70)
    print(f"BAAI Hub 论文采集 V2 (2026-{', '.join(targets)})")
    print("=" * 70)

    # ── 文档 §2.1: 先用 reports_graph 获取所有领域最新摘要 ──
    print("\n[0] 获取全局报告摘要 (reports_graph)")
    graph_reports = fetch_reports_graph()
    print(f"  最新报告: {len(graph_reports)} 个领域")
    graph_by_domain = {}
    if graph_reports:
        for r in graph_reports:
            d = r.get('title', '')
            if d:
                graph_by_domain[d] = r
        print(f"  领域索引: {len(graph_by_domain)} 个")

    all_data = {t: [] for t in targets}

    for domain in DOMAINS:
        print(f"\n[{domain}]")
        reports = get_reports(domain)

        # 文档 §2.2: reports_list 返回空时，用 reports_graph 兜底
        if not reports and domain in graph_by_domain:
            fallback = graph_by_domain[domain]
            print(f"  reports_list 为空，使用 reports_graph 兜底: {fallback.get('id', '')[:20]}...")
            reports = [fallback]

        print(f"  历史报告: {len(reports)} 个")

        for r in reports:
            title = r.get('title', '')
            rid = r.get('id', '')

            for t in targets:
                month_key = f'{t}月报'
                if month_key in title:
                    print(f"  → 获取 {month_key}: {rid[:20]}...")
                    papers = fetch_papers_for_report(domain, rid)
                    print(f"    论文: {len(papers)} 篇")

                    # 文档 §7.1: 逐领域验证
                    batch_check = validate_papers_batch(papers)
                    if batch_check['needs_review']:
                        print(f"    ⚠ 需复核: 英文占比 {batch_check['english_ratio']:.1%}")

                    for p in papers[:3]:
                        lang = "EN" if is_english_title(p) else "CN"
                        print(f"      [{lang}] {p[:80]}")
                    if len(papers) > 3:
                        print(f"      ... 共 {len(papers)} 篇")

                    for p in papers:
                        all_data[t].append({
                            'title': p,
                            'domain': domain,
                            'is_english': is_english_title(p)
                        })
                    break  # 已匹配，跳出内层循环

        time.sleep(0.3)

    # ── 文档 §5: 数据验证流水线 ──
    print("\n" + "=" * 70)
    print("数据验证 & 去重")
    print("=" * 70)

    valid = {}
    for t in targets:
        label = f"2026-{t}"
        valid[t], _, _ = validate_and_dedup(all_data[t], label)

    # ── 文档 §5 检查点 5: 跨月格式一致性 ──
    print("\n" + "=" * 70)
    print("跨月格式一致性检查")
    print("=" * 70)
    consistency_issues = check_cross_month_consistency(all_data)
    if consistency_issues:
        for issue in consistency_issues:
            print(f"  ⚠ {issue['issue']}")
    else:
        print("  ✓ 所有领域跨月格式一致")

    # 保存
    for t in targets:
        label = f"2026-{t}"
        papers = valid[t]
        output_path = os.path.join(OUTPUT_DIR, f"papers_{label}.json")
        output_data = []
        for i, p in enumerate(papers):
            output_data.append({
                "arxiv_id": f"baai-{label}-{i+1:04d}",
                "title": p['title'],
                "summary": p['title'],
                "published": f"{label}-30",
                "categories": [],
                "authors": [],
                "link": "",
                "source": "BAAI Hub",
                "domain": p['domain']
            })
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"\n已保存: {output_path} ({len(output_data)} 篇)")

    # 汇总
    print("\n" + "=" * 70)
    print("采集完成")
    total_papers = sum(len(valid[t]) for t in targets)
    print(f"  总计: {total_papers} 篇论文 ({len(targets)} 个月)")
    print(f"  跨月一致性: {'✓ 通过' if not consistency_issues else f'⚠ {len(consistency_issues)} 个问题'}")
    print("=" * 70)


if __name__ == '__main__':
    main()