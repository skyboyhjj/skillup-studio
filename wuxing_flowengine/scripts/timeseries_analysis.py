#!/usr/bin/env python3
"""
Phase 3+ 时间序列分析：月际重心漂移对比
支持参数化调用，可被月度编排器导入。
"""
import json, os, math
from collections import Counter

# ── 论文五行分类器（与 Phase 3+ 一致）──
PAPER_WUXING_KEYWORDS = {
    "木": ["generation", "generative", "diffusion", "image", "video", "synthesis",
           "multimodal", "cross-modal", "3d", "point cloud", "nerf", "gaussian",
           "embodied", "robot", "motion", "manipulation", "sim-to-real", "world model",
           "style transfer", "editing", "augmentation", "creative", "vae", "gan",
           "flow model", "music", "speech synthesis", "tts", "protein", "drug",
           "molecule", "material", "design", "grasp", "dexterous", "haptic", "tactile",
           "splat", "slam", "policy", "imitation", "locomotion"],
    "火": ["agent", "multi-agent", "collaboration", "interaction", "dialogue",
           "recommendation", "retrieval", "search", "ranking", "personalization",
           "evaluation", "benchmark", "human", "user", "social", "conversation",
           "assistant", "chat", "preference", "feedback", "rlhf", "alignment",
           "tool", "api", "workflow", "automation", "planning", "decision",
           "coding agent", "software", "developer", "programming", "code",
           "arena", "coordination"],
    "土": ["transformer", "architecture", "framework", "infrastructure", "system",
           "training", "optimization", "scaling", "distributed", "parallel",
           "foundation", "pre-training", "pretraining", "fine-tuning", "finetuning",
           "cnn", "rnn", "mlp", "normalization", "regularization", "compiler",
           "hardware", "efficient", "inference", "quantization", "supervised",
           "unsupervised", "self-supervised", "contrastive", "data", "dataset",
           "curation", "tokenizer", "embedding", "gpu", "kernel", "memory",
           "dram", "compression", "distillation", "pruning", "sparse", "moe",
           "mixture of experts", "load balancing", "latency", "throughput"],
    "金": ["safety", "security", "privacy", "fairness", "bias", "ethics",
           "explainable", "interpretable", "robust", "adversarial", "attack",
           "watermark", "copyright", "verification", "formal", "proof", "theorem",
           "logic", "reasoning", "symbolic", "knowledge graph", "causal",
           "audit", "regulation", "compliance", "detection", "defense", "certified",
           "guarantee", "bound", "provable", "red-teaming", "red team", "hallucination",
           "factuality", "vulnerability", "malicious"],
    "水": ["language", "text", "translation", "summarization", "ner", "semantic",
           "vision", "object detection", "segmentation", "recognition", "depth",
           "slam", "ocr", "medical", "science", "quantum", "llm", "language model",
           "gpt", "chain-of-thought", "understanding", "comprehension", "knowledge",
           "inference", "attention", "memory", "retrieval-augmented", "rag",
           "prediction", "forecasting", "discovery", "exploration", "climate",
           "weather", "pde", "neural operator", "physics", "simulation",
           "molecular", "crystal", "quantum"],
}

WX_COORDS = {"木": (-1, 0), "火": (0, -1), "土": (0, 0), "金": (1, 0), "水": (0, 1)}

PAPER_TO_SNAP = {
    "大语言模型": "大语言模型", "具身智能与机器人": "具身智能与机器人",
    "多模态智能": "多模态智能", "智能体": "智能体",
    "生成式 AI": "生成式AI", "机器学习基础": "机器学习基础",
    "安全、可信与伦理": "安全可信与伦理", "计算机视觉": "计算机视觉",
    "交叉领域智能应用": "交叉领域智能应用", "推荐系统与信息检索": "推荐系统与信息检索",
    "AI 系统与硬件": "AI系统与硬件", "软件工程与编程": "软件工程与编程",
    "科学 AI": "科学AI",
}


def classify_paper(title):
    title_lower = title.lower()
    scores = {wx: 0 for wx in ["木", "火", "土", "金", "水"]}
    for wx, keywords in PAPER_WUXING_KEYWORDS.items():
        for kw in keywords:
            if kw in title_lower:
                scores[wx] += 1
    if max(scores.values()) == 0:
        return "水"
    return max(scores, key=scores.get)


def compute_centroid(paper_wx, total):
    """从论文五行分布计算重心"""
    if total == 0:
        return (0.0, 0.0)
    cx = sum(WX_COORDS[wx][0] * paper_wx.get(wx, 0) for wx in ["木", "火", "土", "金", "水"]) / total
    cy = sum(WX_COORDS[wx][1] * paper_wx.get(wx, 0) for wx in ["木", "火", "土", "金", "水"]) / total
    return (round(cx, 4), round(cy, 4))


def run(base_dir, current_diag_path=None, prev_paper_titles_path=None, output_dir=None, current_label=None, prev_label=None):
    """
    运行时间序列分析：对比两个月论文重心漂移。

    参数:
        base_dir:               项目根目录
        current_diag_path:      当月 Phase 3+ 诊断结果路径
        prev_paper_titles_path: 上月论文标题 JSON 路径
        output_dir:             输出目录
        current_label:          当月标签（如 "2026-07"）
        prev_label:             上月标签（如 "2026-06"）

    返回:
        {"status": "ok", "outputs": {"diagnosis": path}, "time_series": {...}, "summary": {...}}
    """
    if current_diag_path is None:
        current_diag_path = os.path.join(base_dir, "output", "phase3_plus_diagnosis.json")

    if prev_paper_titles_path is None:
        prev_paper_titles_path = os.path.join(base_dir, "output", "phase3_paper_titles.json")

    if output_dir is None:
        output_dir = os.path.join(base_dir, "output")

    os.makedirs(output_dir, exist_ok=True)

    # ── 1. 加载数据 ──
    with open(current_diag_path, "r", encoding="utf-8") as f:
        current_data = json.load(f)

    with open(prev_paper_titles_path, "r", encoding="utf-8") as f:
        prev_papers = json.load(f)

    # ── 2. 分类上月论文 ──
    prev_results = {}
    for domain, papers in prev_papers.items():
        if not papers:
            continue
        paper_wx = Counter()
        paper_details = []
        for title in papers:
            # Skip non-paper-title entries (中文摘要)
            if len(title) > 20 and any('\u4e00' <= c <= '\u9fff' for c in title[:5]):
                if '：' in title[:30] and not any(c.isascii() and c.isalpha() for c in title[:20]):
                    continue
            wx = classify_paper(title)
            paper_wx[wx] += 1
            paper_details.append({"title": title, "wuxing": wx})

        total = len(paper_details)
        if total == 0:
            continue

        cx, cy = compute_centroid(paper_wx, total)

        prev_results[domain] = {
            "paper_count": total,
            "paper_wx": dict(paper_wx),
            "centroid": (cx, cy),
            "paper_details": paper_details
        }

    # ── 3. 计算月际漂移 ──
    print("=" * 100)
    print(f"  Phase 3+ 时间序列分析：{prev_label or '上月'} → {current_label or '当月'} 重心漂移")
    print("=" * 100)
    print(f"  {'领域':<18s} {'上月重心':>16s} {'当月重心':>16s} {'漂移向量':>16s} {'幅度':>8s} {'判读'}")
    print(f"  {'-'*18} {'-'*16} {'-'*16} {'-'*16} {'-'*8} {'-'*25}")

    time_series = {}
    for domain in prev_results:
        prev = prev_results[domain]
        prev_cx, prev_cy = prev["centroid"]

        if domain not in current_data["domains"]:
            continue

        curr = current_data["domains"][domain]
        curr_cx, curr_cy = curr["centroid_drift"]["paper"]

        drift_x = curr_cx - prev_cx
        drift_y = curr_cy - prev_cy
        drift_mag = math.sqrt(drift_x**2 + drift_y**2)

        if drift_mag > 0.3:
            reading = "显著月际漂移——研究方向明显变化"
        elif drift_mag > 0.1:
            reading = "轻度月际漂移——研究方向微调"
        else:
            reading = "几乎无月际变化——研究方向稳定"

        print(f"  {domain:<18s} ({prev_cx:+.4f},{prev_cy:+.4f}) ({curr_cx:+.4f},{curr_cy:+.4f}) ({drift_x:+.4f},{drift_y:+.4f}) {drift_mag:>8.4f} {reading}")

        time_series[domain] = {
            "prev_centroid": [prev_cx, prev_cy],
            "current_centroid": [curr_cx, curr_cy],
            "monthly_drift": [round(drift_x, 4), round(drift_y, 4)],
            "monthly_drift_magnitude": round(drift_mag, 4),
            "reading": reading,
            "prev_paper_count": prev["paper_count"],
            "current_paper_count": curr["paper_count"],
            "prev_paper_wx": prev["paper_wx"],
            "current_paper_wx": curr["paper_wx"]
        }

    # 上月结构-活跃度漂移
    for domain, ts in time_series.items():
        if domain in current_data["domains"]:
            node_cx, node_cy = current_data["domains"][domain]["centroid_drift"]["node"]
            prev_cx, prev_cy = ts["prev_centroid"]
            prev_drift_x = prev_cx - node_cx
            prev_drift_y = prev_cy - node_cy
            prev_drift_mag = math.sqrt(prev_drift_x**2 + prev_drift_y**2)
            ts["prev_structure_drift"] = [round(prev_drift_x, 4), round(prev_drift_y, 4)]
            ts["prev_structure_drift_magnitude"] = round(prev_drift_mag, 4)

            curr_drift_mag = current_data["domains"][domain]["centroid_drift"]["magnitude"]
            ts["current_structure_drift_magnitude"] = curr_drift_mag
            ts["drift_magnitude_change"] = round(curr_drift_mag - prev_drift_mag, 4)

    # ── 4. 汇总 ──
    print(f"\n{'=' * 100}")
    print(f"  时间序列汇总")
    print(f"{'=' * 100}")
    print(f"  {'领域':<18s} {'上月结构漂移':>10s} {'当月结构漂移':>10s} {'漂移变化':>10s} {'月际漂移':>10s} {'趋势'}")
    print(f"  {'-'*18} {'-'*10} {'-'*10} {'-'*10} {'-'*10} {'-'*25}")

    drift_changes = []
    for domain, ts in sorted(time_series.items(), key=lambda x: abs(x[1].get("drift_magnitude_change", 0)), reverse=True):
        prev_sd = ts.get("prev_structure_drift_magnitude", 0)
        curr_sd = ts.get("current_structure_drift_magnitude", 0)
        change = ts.get("drift_magnitude_change", 0)
        monthly = ts["monthly_drift_magnitude"]

        if change > 0.05:
            trend = "↑ 结构-活跃度差距扩大"
        elif change < -0.05:
            trend = "↓ 结构-活跃度差距缩小"
        else:
            trend = "→ 基本稳定"

        drift_changes.append({"domain": domain, "change": change, "trend": trend})
        print(f"  {domain:<18s} {prev_sd:>10.4f} {curr_sd:>10.4f} {change:>+10.4f} {monthly:>10.4f} {trend}")

    # ── 5. 保存 ──
    suffix = f"_{current_label}" if current_label else ""
    diag_path = os.path.join(output_dir, f"phase3_timeseries_diagnosis{suffix}.json")

    if time_series:
        mean_monthly = sum(ts["monthly_drift_magnitude"] for ts in time_series.values()) / len(time_series)
        max_drift_item = max(time_series.items(), key=lambda x: x[1]["monthly_drift_magnitude"])
    else:
        mean_monthly = 0
        max_drift_item = ("", {"monthly_drift_magnitude": 0})

    output = {
        "phase": "3+_timeseries",
        "current_label": current_label,
        "prev_label": prev_label,
        "timestamp": current_label or "2026-07-31",
        "data_sources": {
            "current_diagnosis": os.path.basename(current_diag_path),
            "prev_papers": os.path.basename(prev_paper_titles_path),
        },
        "time_series": time_series,
        "summary": {
            "domains_analyzed": len(time_series),
            "mean_monthly_drift": round(mean_monthly, 4),
            "max_monthly_drift_domain": max_drift_item[0],
            "max_monthly_drift": round(max_drift_item[1]["monthly_drift_magnitude"], 4),
            "drift_trends": drift_changes,
            "mean_drift_change": round(sum(dc["change"] for dc in drift_changes) / len(drift_changes), 4) if drift_changes else 0,
        }
    }

    with open(diag_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n  时间序列分析完成！结果保存到 {os.path.basename(diag_path)}")
    print(f"  平均月际漂移: {output['summary']['mean_monthly_drift']:.4f}")
    if max_drift_item[0]:
        print(f"  最大月际漂移: {max_drift_item[0]} ({output['summary']['max_monthly_drift']:.4f})")

    return {
        "status": "ok",
        "outputs": {"diagnosis": diag_path},
        "time_series": time_series,
        "summary": output["summary"]
    }


if __name__ == "__main__":
    DEFAULT_BASE = r"C:\Users\hejij\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a59e217b55e181ea97f0df3\wuxing_flowengine"
    run(DEFAULT_BASE)