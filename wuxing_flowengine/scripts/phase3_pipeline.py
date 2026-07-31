#!/usr/bin/env python3
"""
Phase 3 动态诊断流水线：论文级五行分类 + 结构-活跃度对比 + 重心漂移
"""
import json, os, math
from collections import Counter, defaultdict

BASE = r"C:\Users\hejij\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a59e217b55e181ea97f0df3\wuxing_flowengine"
SNAPSHOT = os.path.join(BASE, "data", "snapshots", "2026-07-30_snapshot.json")
PHASE2 = os.path.join(BASE, "output", "phase2_diagnosis.json")
OUTPUT = os.path.join(BASE, "output")

with open(SNAPSHOT, "r", encoding="utf-8") as f:
    nodes = json.load(f)["nodes"]

domain_node_wx = defaultdict(Counter)
domain_node_count = Counter()
for n in nodes:
    if n["level"] == 3:
        domain_node_wx[n.get("category", "其他")][n.get("wuxing", "土")] += 1
        domain_node_count[n.get("category", "其他")] += 1

PAPER_WUXING_KEYWORDS = {
    "木": ["generation", "generative", "diffusion", "image", "video", "synthesis", "multimodal", "cross-modal", "3d", "point cloud", "nerf", "gaussian", "embodied", "robot", "motion", "manipulation", "sim-to-real", "world model", "style transfer", "editing", "augmentation", "creative", "vae", "gan", "flow model", "music", "speech synthesis", "tts", "protein", "drug", "molecule", "material", "design"],
    "火": ["agent", "multi-agent", "collaboration", "interaction", "dialogue", "recommendation", "retrieval", "search", "ranking", "personalization", "evaluation", "benchmark", "human", "user", "social", "conversation", "assistant", "chat", "preference", "feedback", "rlhf", "alignment", "tool", "api", "workflow", "automation", "planning", "decision"],
    "土": ["transformer", "architecture", "framework", "infrastructure", "system", "training", "optimization", "scaling", "distributed", "parallel", "foundation", "pre-training", "pretraining", "fine-tuning", "finetuning", "cnn", "rnn", "mlp", "normalization", "regularization", "compiler", "hardware", "efficient", "inference", "quantization", "supervised", "unsupervised", "self-supervised", "contrastive", "data", "dataset", "curation", "tokenizer", "embedding"],
    "金": ["safety", "security", "privacy", "fairness", "bias", "ethics", "explainable", "interpretable", "robust", "adversarial", "attack", "watermark", "copyright", "verification", "formal", "proof", "theorem", "logic", "reasoning", "symbolic", "knowledge graph", "causal", "audit", "regulation", "compliance", "detection", "defense", "certified", "guarantee", "bound", "provable"],
    "水": ["language", "text", "translation", "summarization", "ner", "semantic", "vision", "object detection", "segmentation", "recognition", "depth", "slam", "ocr", "medical", "science", "quantum", "llm", "language model", "gpt", "reasoning", "chain-of-thought", "understanding", "comprehension", "knowledge", "inference", "hallucination", "factuality", "long-context", "context", "emergence", "exploration", "discovery", "prediction", "attention", "sparse", "memory", "retrieval-augmented"],
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

llm_papers_06 = [
    "SPIRAL: Learning to Search and Aggregate",
    "VIMPO: Value-Implicit Policy Optimization for LLMs",
    "Beyond Uniform Token-Level Trust Region in LLM Reinforcement Learning",
    "MOPD: Multi-Teacher On-Policy Distillation for Capability Integration in LLM Post-Training",
    "DOPD: Dual On-policy Distillation",
    "SAGE-OPD: Selective Agent-Guided Intervention for Multi-Turn On-Policy Distillation",
    "Tapered Language Models",
    "Dynamic Short Convolutions Improve Transformers",
    "Depth-Attention: Cross-Layer Value Mixing for Language Models",
    "MiniMax Sparse Attention",
    "You Only Index Once: Cross-Layer Sparse Attention with Shared Routing",
    "JetSpec: Breaking the Scaling Ceiling of Speculative Decoding with Parallel Tree Drafting",
    "Self-Harness: Harnesses That Improve Themselves",
    "Decentralized Multi-Agent Systems with Shared Context",
    "Connect the Dots: Training LLMs for Long-Lifecycle Agents with Cross-Domain Generalization Via Reinforcement Learning",
    "Explaining Attention with Program Synthesis",
    "ReasoningFlow: Discourse Structures for Understanding LLM Reasoning Traces",
    "Anatomy of Post-Training: Using Interpretability to Characterize Data and Shape the Learning Signal",
    "Smooth Scaling Laws Hide Stepwise Token Learning",
    "Internal Data Repetition Destroys Language Models",
    "q0: Primitives for Hyper-Epoch Pretraining",
    "Large Language Models Hack Rewards, and Society",
    "A Red-Team Study of Anthropic Fable 5 & Opus 4.8 Models",
    "Gender Bias in LLM Hiring Decisions: Evidence from a Japanese Context and Evaluation of Mitigation Strategies",
    "Unlimited OCR Works",
    "Sarashina2.2-TTS: Tackling Kanji Polyphony in Japanese Speech Generation via Data Scaling and Targeted Data Synthesis",
    "LEAP: Supercharging LLMs for Formal Mathematics with Agentic Frameworks",
    "Masked Language Flow Models",
    "Latent Reasoning with Normalizing Flows",
    "Fixed-Point Reasoners: Stable and Adaptive Deep Looped Transformers",
]

trend_summary_llm = (
    "大语言模型研究正围绕推理能力规模化与系统效率双线深入。"
    "强化学习（RLVR）超越监督微调成为推理增强的核心范式；"
    "模型架构从均匀层宽转向锥形、动态卷积与跨层注意力混合；"
    "稀疏注意力与推测解码使长上下文推理加速取得突破；"
    "智能体系统从固定流水线走向自进化、去中心化协作与持续环境学习；"
    "预训练数据重复与缩放定律的研究更加精细；"
    "安全性、可解释性与领域专用化（OCR、语音、形式化数学）持续纵深；"
    "扩散/流模型等新型生成范式也开始挑战推理任务。"
)

print("=" * 80)
print("  Phase 3 动态诊断：论文级五行分类 + 结构-活跃度对比")
print("=" * 80)

paper_wx = Counter()
paper_details = []
for title in llm_papers_06:
    wx = classify_paper(title)
    paper_wx[wx] += 1
    paper_details.append({"title": title, "wuxing": wx})

print(f"\n  大语言模型 06月报：{len(llm_papers_06)} 篇论文")
print(f"  论文五行分布: {dict(paper_wx)}")

node_wx_llm = domain_node_wx.get("大语言模型", Counter())
node_total_llm = domain_node_count.get("大语言模型", 1)
paper_total = len(llm_papers_06)

print(f"\n  ── 大语言模型：节点（静态结构） vs 论文（动态活跃度）──")
print(f"  {'五行':<6s} {'节点数':>5s} {'节点%':>7s} {'论文数':>5s} {'论文%':>7s} {'差异':>7s} {'判读'}")
print(f"  {'-'*6} {'-'*5} {'-'*7} {'-'*5} {'-'*7} {'-'*7} {'-'*20}")

comparison = {}
WX_COORDS = {"木": (-1, 0), "火": (0, -1), "土": (0, 0), "金": (1, 0), "水": (0, 1)}

for wx in ["木", "火", "土", "金", "水"]:
    n_pct = node_wx_llm.get(wx, 0) / node_total_llm * 100
    p_pct = paper_wx.get(wx, 0) / paper_total * 100
    diff = p_pct - n_pct
    if diff > 5: reading = "↑ 论文活跃度高于节点占比"
    elif diff < -5: reading = "↓ 论文活跃度低于节点占比"
    else: reading = "≈ 基本一致"
    comparison[wx] = {"node": node_wx_llm.get(wx, 0), "node_pct": round(n_pct, 1), "paper": paper_wx.get(wx, 0), "paper_pct": round(p_pct, 1), "diff": round(diff, 1), "reading": reading}
    print(f"  {wx:<6s} {node_wx_llm.get(wx, 0):>5d} {n_pct:>6.1f}% {paper_wx.get(wx, 0):>5d} {p_pct:>6.1f}% {diff:>+6.1f}% {reading}")

node_cx = sum(WX_COORDS[wx][0] * node_wx_llm.get(wx, 0) for wx in ["木", "火", "土", "金", "水"]) / node_total_llm
node_cy = sum(WX_COORDS[wx][1] * node_wx_llm.get(wx, 0) for wx in ["木", "火", "土", "金", "水"]) / node_total_llm
paper_cx = sum(WX_COORDS[wx][0] * paper_wx.get(wx, 0) for wx in ["木", "火", "土", "金", "水"]) / paper_total
paper_cy = sum(WX_COORDS[wx][1] * paper_wx.get(wx, 0) for wx in ["木", "火", "土", "金", "水"]) / paper_total

drift_x = paper_cx - node_cx
drift_y = paper_cy - node_cy
drift_magnitude = math.sqrt(drift_x**2 + drift_y**2)

print(f"\n  ── 重心漂移（节点 → 论文）──")
print(f"  节点重心: ({node_cx:.4f}, {node_cy:.4f})")
print(f"  论文重心: ({paper_cx:.4f}, {paper_cy:.4f})")
print(f"  漂移向量: ({drift_x:+.4f}, {drift_y:+.4f})  幅度: {drift_magnitude:.4f}")

if drift_magnitude > 0.3: drift_reading = "显著漂移——研究方向与知识结构存在结构性偏移"
elif drift_magnitude > 0.1: drift_reading = "轻度漂移——研究方向与知识结构基本一致"
else: drift_reading = "几乎无漂移——研究方向与知识结构高度吻合"
print(f"  判读：{drift_reading}")

trend_wx = classify_paper(trend_summary_llm)
print(f"\n  ── 趋势摘要五行 ──")
print(f"  分类: {trend_wx}")
print(f"  摘要: {trend_summary_llm[:150]}...")

print(f"\n{'='*80}")
print(f"  全领域结构-活跃度框架")
print(f"{'='*80}")
print(f"\n  {'领域':<20s} {'节点':>5s} {'S_D':>8s} {'报告月':>6s} {'活跃度'}")
print(f"  {'-'*20} {'-'*5} {'-'*8} {'-'*6} {'-'*10}")

with open(PHASE2, "r", encoding="utf-8") as f:
    p2 = json.load(f)
domain_sd = {d: v["D"] for d, v in p2["domain_tracks"].items()}

reports_meta = [
    {"domain": "大语言模型", "date": "2026-07-02", "papers": 5900},
    {"domain": "自然语言处理", "date": "2026-07-02", "papers": None},
    {"domain": "具身智能与机器人", "date": "2026-07-02", "papers": None},
    {"domain": "多模态智能", "date": "2026-07-01", "papers": None},
    {"domain": "智能体", "date": "2026-07-01", "papers": None},
    {"domain": "生成式 AI", "date": "2026-07-01", "papers": None},
    {"domain": "机器学习基础", "date": "2026-07-01", "papers": None},
    {"domain": "安全、可信与伦理", "date": "2026-07-01", "papers": None},
    {"domain": "计算机视觉", "date": "2026-07-01", "papers": None},
    {"domain": "交叉领域智能应用", "date": "2026-07-01", "papers": None},
    {"domain": "知识表示与逻辑推理", "date": "2026-07-01", "papers": None},
    {"domain": "推荐系统与信息检索", "date": "2026-07-01", "papers": None},
    {"domain": "AI 系统与硬件", "date": "2026-07-01", "papers": None},
    {"domain": "软件工程与编程", "date": "2026-07-01", "papers": None},
    {"domain": "科学 AI", "date": "2026-07-01", "papers": None},
]

for r in reports_meta:
    domain = r["domain"]
    nc = domain_node_count.get(domain, 0)
    sd = domain_sd.get(domain, 0)
    p = r.get("papers")
    ps = f"{p/1000:.1f}k" if p else "N/A"
    if nc >= 20 and p and p > 5000: act = "🔥 高活跃"
    elif nc >= 10: act = "📊 中活跃"
    else: act = "📉 低密度"
    print(f"  {domain:<20s} {nc:>5d} {sd:>8.4f} {r['date'][5:]:>6s} {act}")

print(f"\n{'='*80}")
print(f"  θ_critical 校准")
print(f"{'='*80}")

llm_pm = 5900
llm_sd = domain_sd.get("大语言模型", 0.8315)
ab_ratio = llm_pm / 1000 * (1 - llm_sd)
print(f"\n  大语言模型活跃-失衡指标: {ab_ratio:.2f}")
print(f"  论文流量: {llm_pm/1000:.1f}k 篇/月, S_D: {llm_sd:.4f}, 失衡度: {1-llm_sd:.4f}")
print(f"  公式: 论文流量(千篇) × (1 - S_D)")
print(f"  阈值: > 1.0 → 失衡区")
print(f"  当前: {ab_ratio:.2f} → {'⚠️ 已进入失衡区' if ab_ratio > 1.0 else '未进入失衡区'}")

output = {
    "phase": 3,
    "data_sources": {"reports_graph_api": "15 domains, 2026-06", "paper_titles": f"{len(llm_papers_06)} papers from 大语言模型"},
    "paper_classification": {"total": len(llm_papers_06), "wuxing": dict(paper_wx), "details": paper_details},
    "structure_vs_activity": {"domain": "大语言模型", "node_wx": {wx: node_wx_llm.get(wx, 0) for wx in ["木","火","土","金","水"]}, "paper_wx": dict(paper_wx), "comparison": comparison, "centroid_drift": {"node": (round(node_cx,4), round(node_cy,4)), "paper": (round(paper_cx,4), round(paper_cy,4)), "drift": (round(drift_x,4), round(drift_y,4)), "magnitude": round(drift_magnitude,4), "reading": drift_reading}},
    "trend_summary": {"text": trend_summary_llm, "wuxing": trend_wx},
    "theta_critical": {"formula": "论文流量(千篇) × (1 - S_D)", "threshold": 1.0, "llm_value": round(ab_ratio, 2), "reading": "已进入失衡区" if ab_ratio > 1.0 else "未进入失衡区"},
    "domain_activity": [{"domain": r["domain"], "node_count": domain_node_count.get(r["domain"], 0), "sd": domain_sd.get(r["domain"], 0), "papers_6月": r.get("papers")} for r in reports_meta],
}

with open(os.path.join(OUTPUT, "phase3_diagnosis.json"), "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\nPhase 3 完成！结果保存到 phase3_diagnosis.json")