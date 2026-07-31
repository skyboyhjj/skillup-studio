#!/usr/bin/env python3
"""
Phase 3+ 增强流水线：全领域论文五行分类 + 结构-活跃度对比 + 重心漂移
支持参数化调用，可被月度编排器导入。
"""
import json, os, math
from collections import Counter, defaultdict

# ── 论文五行分类器 ──
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

# 领域名映射（论文标题键 → 快照键）
PAPER_TO_SNAP = {
    "大语言模型": "大语言模型",
    "具身智能与机器人": "具身智能与机器人",
    "多模态智能": "多模态智能",
    "智能体": "智能体",
    "生成式 AI": "生成式AI",
    "机器学习基础": "机器学习基础",
    "安全、可信与伦理": "安全可信与伦理",
    "计算机视觉": "计算机视觉",
    "交叉领域智能应用": "交叉领域智能应用",
    "推荐系统与信息检索": "推荐系统与信息检索",
    "AI 系统与硬件": "AI系统与硬件",
    "软件工程与编程": "软件工程与编程",
    "科学 AI": "科学AI",
}

DOMAIN_ORDER = ["大语言模型", "具身智能与机器人", "多模态智能", "智能体", "生成式 AI",
                "机器学习基础", "安全、可信与伦理", "计算机视觉", "交叉领域智能应用",
                "推荐系统与信息检索", "AI 系统与硬件", "软件工程与编程", "科学 AI"]


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


def run(base_dir, snapshot_path=None, phase2_path=None, paper_titles_path=None, output_dir=None, month_label=None):
    """
    运行 Phase 3+ 流水线。

    参数:
        base_dir:           项目根目录
        snapshot_path:      快照 JSON 路径（默认自动找最新）
        phase2_path:        Phase 2 诊断结果路径
        paper_titles_path:  论文标题 JSON 路径（{领域: [标题列表]}）
        output_dir:         输出目录
        month_label:        月度标签

    返回:
        {"status": "ok", "outputs": {"diagnosis": path}, "domains": {...}, "summary": {...}}
    """
    if snapshot_path is None:
        snap_dir = os.path.join(base_dir, "data", "snapshots")
        snap_files = sorted([f for f in os.listdir(snap_dir) if f.endswith("_snapshot.json")], reverse=True)
        snapshot_path = os.path.join(snap_dir, snap_files[0]) if snap_files else os.path.join(base_dir, "data", "snapshots", "2026-07-30_snapshot.json")

    if phase2_path is None:
        phase2_path = os.path.join(base_dir, "output", "phase2_diagnosis.json")

    if paper_titles_path is None:
        paper_titles_path = os.path.join(base_dir, "output", "phase3_paper_titles.json")

    if output_dir is None:
        output_dir = os.path.join(base_dir, "output")

    os.makedirs(output_dir, exist_ok=True)

    # ── 1. 加载数据 ──
    with open(snapshot_path, "r", encoding="utf-8") as f:
        nodes = json.load(f)["nodes"]

    snapshot_domain_wx = defaultdict(Counter)
    snapshot_domain_count = Counter()
    for n in nodes:
        if n["level"] == 3:
            cat = n.get("category", "其他")
            wx = n.get("wuxing", "土")
            snapshot_domain_wx[cat][wx] += 1
            snapshot_domain_count[cat] += 1

    with open(phase2_path, "r", encoding="utf-8") as f:
        p2 = json.load(f)
    domain_sd = {d: v["D"] for d, v in p2["domain_tracks"].items()}

    with open(paper_titles_path, "r", encoding="utf-8") as f:
        paper_titles = json.load(f)

    # ── 2. 全领域分类 ──
    print("=" * 90)
    print(f"  Phase 3+ 增强版：全领域论文五行分类 + 结构-活跃度对比 + 重心漂移{f' ({month_label})' if month_label else ''}")
    print("=" * 90)

    domain_results = {}
    for paper_key in DOMAIN_ORDER:
        if paper_key not in paper_titles:
            print(f"\n  ⚠ {paper_key}: 无论文数据，跳过")
            continue

        papers = paper_titles[paper_key]
        paper_wx = Counter()
        paper_details = []
        for title in papers:
            wx = classify_paper(title)
            paper_wx[wx] += 1
            paper_details.append({"title": title, "wuxing": wx})

        snap_key = PAPER_TO_SNAP.get(paper_key, paper_key)
        node_wx = snapshot_domain_wx.get(snap_key, Counter())
        node_total = snapshot_domain_count.get(snap_key, 1)
        paper_total = len(papers)

        if paper_total == 0:
            continue

        print(f"\n  ── {paper_key} ({node_total}节点, {paper_total}篇) ──")
        print(f"  {'五行':<6s} {'节点':>5s} {'节点%':>7s} {'论文':>5s} {'论文%':>7s} {'差异':>7s} {'判读'}")

        comparison = {}
        for wx in ["木", "火", "土", "金", "水"]:
            n_pct = node_wx.get(wx, 0) / node_total * 100 if node_total else 0
            p_pct = paper_wx.get(wx, 0) / paper_total * 100 if paper_total else 0
            diff = p_pct - n_pct
            if diff > 5: reading = "↑ 论文活跃度高于节点占比"
            elif diff < -5: reading = "↓ 论文活跃度低于节点占比"
            else: reading = "≈ 基本一致"
            comparison[wx] = {
                "node": node_wx.get(wx, 0), "node_pct": round(n_pct, 1),
                "paper": paper_wx.get(wx, 0), "paper_pct": round(p_pct, 1),
                "diff": round(diff, 1), "reading": reading
            }
            print(f"  {wx:<6s} {node_wx.get(wx, 0):>5d} {n_pct:>6.1f}% {paper_wx.get(wx, 0):>5d} {p_pct:>6.1f}% {diff:>+6.1f}% {reading}")

        # 重心漂移
        if node_total == 0:
            node_cx = node_cy = 0
        else:
            node_cx = sum(WX_COORDS[wx][0] * node_wx.get(wx, 0) for wx in ["木", "火", "土", "金", "水"]) / node_total
            node_cy = sum(WX_COORDS[wx][1] * node_wx.get(wx, 0) for wx in ["木", "火", "土", "金", "水"]) / node_total

        paper_cx = sum(WX_COORDS[wx][0] * paper_wx.get(wx, 0) for wx in ["木", "火", "土", "金", "水"]) / paper_total
        paper_cy = sum(WX_COORDS[wx][1] * paper_wx.get(wx, 0) for wx in ["木", "火", "土", "金", "水"]) / paper_total

        drift_x = paper_cx - node_cx
        drift_y = paper_cy - node_cy
        drift_mag = math.sqrt(drift_x**2 + drift_y**2)

        if drift_mag > 0.3: drift_reading = "显著漂移——研究方向与知识结构存在结构性偏移"
        elif drift_mag > 0.1: drift_reading = "轻度漂移——研究方向与知识结构基本一致"
        else: drift_reading = "几乎无漂移——研究方向与知识结构高度吻合"

        print(f"  重心: 节点({node_cx:+.4f},{node_cy:+.4f}) → 论文({paper_cx:+.4f},{paper_cy:+.4f})")
        print(f"  漂移向量: ({drift_x:+.4f},{drift_y:+.4f}) 幅度={drift_mag:.4f} → {drift_reading}")

        # θ_critical
        sd = domain_sd.get(snap_key, 0)
        if sd > 0 and paper_total >= 30:
            est_flow = paper_total / 30 * 5.9
            theta = est_flow * (1 - sd)
        else:
            theta = 0

        domain_results[paper_key] = {
            "node_count": node_total,
            "paper_count": paper_total,
            "node_wx": {wx: node_wx.get(wx, 0) for wx in ["木", "火", "土", "金", "水"]},
            "paper_wx": dict(paper_wx),
            "comparison": comparison,
            "centroid_drift": {
                "node": (round(node_cx, 4), round(node_cy, 4)),
                "paper": (round(paper_cx, 4), round(paper_cy, 4)),
                "drift": (round(drift_x, 4), round(drift_y, 4)),
                "magnitude": round(drift_mag, 4),
                "reading": drift_reading
            },
            "theta_critical": round(theta, 2),
            "S_D": round(sd, 4),
            "paper_details": paper_details
        }

    # ── 3. 全领域汇总 ──
    print(f"\n{'=' * 90}")
    print(f"  全领域重心漂移汇总")
    print(f"{'=' * 90}")
    print(f"  {'领域':<18s} {'节点':>5s} {'论文':>5s} {'S_D':>8s} {'漂移幅':>8s} {'θ_crit':>7s} {'判读'}")
    print(f"  {'-'*18} {'-'*5} {'-'*5} {'-'*8} {'-'*8} {'-'*7} {'-'*20}")

    for d in DOMAIN_ORDER:
        if d not in domain_results:
            continue
        r = domain_results[d]
        cd = r["centroid_drift"]
        print(f"  {d:<18s} {r['node_count']:>5d} {r['paper_count']:>5d} {r['S_D']:>8.4f} {cd['magnitude']:>8.4f} {r['theta_critical']:>7.2f} {cd['reading'][:20]}")

    if domain_results:
        max_drift = max(domain_results.items(), key=lambda x: x[1]["centroid_drift"]["magnitude"])
        all_drifts = [r["centroid_drift"]["magnitude"] for r in domain_results.values()]
        mean_drift = sum(all_drifts) / len(all_drifts)
        print(f"\n  最大漂移领域: {max_drift[0]} (幅度={max_drift[1]['centroid_drift']['magnitude']:.4f})")
        print(f"  全领域平均漂移: {mean_drift:.4f}")
    else:
        max_drift = ("", {"centroid_drift": {"magnitude": 0}})
        mean_drift = 0

    # ── 3.5 SAM: 结构-活跃度错位指数 ──
    print(f"\n{'=' * 90}")
    print(f"  SAM 结构-活跃度错位指数 (Structural-Activity Mismatch)")
    print(f"{'=' * 90}")
    print(f"  {'领域':<18s} {'节点%':>7s} {'论文%':>7s} {'SAM':>7s} {'判读'}")
    print(f"  {'-'*18} {'-'*7} {'-'*7} {'-'*7} {'-'*30}")

    sam_results = {}
    total_nodes_sam = sum(r["node_count"] for r in domain_results.values())
    total_papers_sam = sum(r["paper_count"] for r in domain_results.values())

    for d in DOMAIN_ORDER:
        if d not in domain_results:
            continue
        r = domain_results[d]
        node_pct = r["node_count"] / total_nodes_sam * 100 if total_nodes_sam else 0
        paper_pct = r["paper_count"] / total_papers_sam * 100 if total_papers_sam else 0
        sam = round(paper_pct - node_pct, 2)

        if sam > 0.3:
            reading = "新兴热点（显著上行）"
        elif sam > 0:
            reading = "轻度上行"
        elif sam > -0.3:
            reading = "结构匹配"
        elif sam > -3:
            reading = "结构超前（潜力待释放）"
        else:
            reading = "基础设施（结构主导）"

        sam_results[d] = {
            "node_pct": round(node_pct, 2),
            "paper_pct": round(paper_pct, 2),
            "SAM": sam,
            "reading": reading
        }
        print(f"  {d:<18s} {node_pct:>6.1f}% {paper_pct:>6.1f}% {sam:>+6.1f}% {reading}")

    # 论文总体五行分布 vs 节点总体五行分布
    total_node_wx = Counter()
    total_paper_wx = Counter()
    total_nodes = 0
    total_papers = 0
    for d in DOMAIN_ORDER:
        if d not in domain_results:
            continue
        r = domain_results[d]
        for wx in ["木", "火", "土", "金", "水"]:
            total_node_wx[wx] += r["node_wx"].get(wx, 0)
            total_paper_wx[wx] += r["paper_wx"].get(wx, 0)
        total_nodes += r["node_count"]
        total_papers += r["paper_count"]

    print(f"\n  ── 全领域总体对比 ──")
    print(f"  {'五行':<6s} {'节点%':>7s} {'论文%':>7s} {'差异':>7s}")
    for wx in ["木", "火", "土", "金", "水"]:
        n_pct = total_node_wx[wx] / total_nodes * 100 if total_nodes else 0
        p_pct = total_paper_wx[wx] / total_papers * 100 if total_papers else 0
        print(f"  {wx:<6s} {n_pct:>6.1f}% {p_pct:>6.1f}% {p_pct-n_pct:>+6.1f}%")

    # ── 4. 保存 ──
    suffix = f"_{month_label}" if month_label else ""
    diag_path = os.path.join(output_dir, f"phase3_plus_diagnosis{suffix}.json")

    output = {
        "phase": "3+",
        "month_label": month_label,
        "timestamp": month_label or "2026-07-31",
        "data_sources": {
            "snapshot": os.path.basename(snapshot_path),
            "paper_titles": os.path.basename(paper_titles_path),
            "phase2": os.path.basename(phase2_path)
        },
        "domains": domain_results,
        "summary": {
            "domains_analyzed": len(domain_results),
            "total_nodes": total_nodes,
            "total_papers": total_papers,
            "total_node_wx": dict(total_node_wx),
            "total_paper_wx": dict(total_paper_wx),
            "mean_drift_magnitude": round(mean_drift, 4),
            "max_drift_domain": max_drift[0] if max_drift[0] else "",
            "max_drift_magnitude": round(max_drift[1]["centroid_drift"]["magnitude"], 4) if max_drift[0] else 0,
            "all_drift_magnitudes": [round(r["centroid_drift"]["magnitude"], 4) for r in domain_results.values()],
            "SAM": sam_results,
            "SAM_summary": {
                "hotspots": [d for d, s in sam_results.items() if s["SAM"] > 0.3],
                "matched": [d for d, s in sam_results.items() if -0.3 <= s["SAM"] <= 0.3],
                "lagging": [d for d, s in sam_results.items() if s["SAM"] < -0.3]
            }
        }
    }

    with open(diag_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 90}")
    print(f"  Phase 3+ 完成！结果保存到 {os.path.basename(diag_path)}")
    print(f"{'=' * 90}")

    return {
        "status": "ok",
        "outputs": {"diagnosis": diag_path},
        "domains": domain_results,
        "summary": output["summary"]
    }


if __name__ == "__main__":
    DEFAULT_BASE = r"C:\Users\hejij\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a59e217b55e181ea97f0df3\wuxing_flowengine"
    run(DEFAULT_BASE)