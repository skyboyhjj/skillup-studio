#!/usr/bin/env python3
"""
边生成器：为知识树快照自动生成跨领域关系边。

三层策略:
  第一层 — 关键词重叠：计算任意两个领域间 L3 节点名的关键词重叠率
  第二层 — 共享节点名：检测跨领域同名/近名节点，建立共享关系
  第三层 — LLM 推理：调用 LLM 判断领域间是否存在方法依赖/应用关系（可选）

目标: 将边密度从 0.99 提升至 ≥ 1.5。

用法:
  python edge_generator.py
  python edge_generator.py --snapshot data/snapshots/2026-07-30_snapshot.json
  python edge_generator.py --dry-run  # 仅预览，不写入文件
"""
import json, os, sys, re, math
from collections import Counter, defaultdict
from difflib import SequenceMatcher

# ── 从 phase1_pipeline 复用关键词库 ──
WUXING_KW = {
    "木": {"kw": ["生成", "具身", "机器人", "多模态", "跨模态", "迁移", "生成式", "图像生成", "视频生成",
                  "语音合成", "风格迁移", "Sim-to-Real", "世界模型", "神经辐射场", "3D", "点云", "扩散模型",
                  "GAN", "神经风格", "图像编辑", "文本驱动图像", "文本驱动视频", "文本转语音", "AI音乐",
                  "视频描述", "视觉-语言预训练", "跨模态对齐", "视觉语言模型", "视觉问答", "蛋白质结构预测",
                  "药物小分子", "基因序列", "智能材料", "3D高斯泼溅"],
           "domains": ["具身智能与机器人", "多模态智能", "生成式AI"]},
    "火": {"kw": ["推荐", "检索", "智能体", "协作", "社会模拟", "交互", "对话", "人机协作", "搜索", "排序",
                  "点击率", "广告", "个性化", "评估", "评测", "基准", "任务规划", "推理决策", "工具调用",
                  "API交互", "多智能体协作", "智能体评估", "自主工作流", "自动化", "多轮对话", "意图识别",
                  "合规问答", "监管AI", "个性化学习", "预测性维护", "缺陷检测", "交通流预测", "协同过滤",
                  "LLM对齐", "语义ID", "稠密检索", "语义对齐"],
           "domains": ["智能体", "推荐系统与信息检索", "交叉领域智能应用"]},
    "土": {"kw": ["基础", "架构", "系统", "硬件", "工程", "编译器", "分布式", "优化器", "并行", "框架",
                  "平台", "软件", "MLP", "CNN", "RNN", "Transformer", "归一化", "正则化", "监督学习",
                  "无监督学习", "半监督", "持续学习", "图神经网络", "贝叶斯", "搜索算法", "进化算法",
                  "蒙特卡洛树搜索", "降维方法", "聚类算法", "对比学习", "损失函数", "自适应学习率",
                  "分布式训练", "深度学习编译器", "端侧推断", "模型压缩", "代码自动补全", "重构建议",
                  "程序漏洞检测", "自动修复", "文本转代码", "机器人运动学", "机器人控制"],
           "domains": ["机器学习基础", "AI系统与硬件", "软件工程与编程"]},
    "金": {"kw": ["安全", "可信", "伦理", "公平", "隐私", "对抗", "可解释", "鲁棒", "后门", "水印", "溯源",
                  "审计", "逻辑", "推理", "知识表示", "知识图谱", "因果", "定理证明", "符号", "神经符号",
                  "提示注入", "对抗攻击防护", "AI价值观对齐", "模型后门检测", "安全过滤", "联邦学习",
                  "加密计算", "差分隐私", "脱敏", "可解释性", "偏见检测", "伦理边界", "价值观对齐",
                  "数学定理证明", "逻辑演绎", "因果发现", "因果推断", "知识编辑", "幻觉检测", "置信度评估",
                  "模型量化", "文本水印", "版权溯源"],
           "domains": ["安全可信与伦理", "知识表示与逻辑推理"]},
    "水": {"kw": ["语言", "文本", "翻译", "摘要", "命名实体", "语义", "视觉", "图像", "视频", "目标检测",
                  "分割", "识别", "深度估计", "SLAM", "OCR", "医学图像", "科学", "蛋白质", "药物", "基因",
                  "量子", "气象", "材料", "大语言模型", "预训练", "微调", "RLHF", "DPO", "思维链", "幻觉",
                  "知识编辑", "MoE", "量化", "指令微调", "检索增强生成", "混合专家模型", "长文本上下文",
                  "隐式推理", "神经机器翻译", "跨语言知识迁移", "自动化提示词", "自动化评测", "图像超分辨率",
                  "图像去噪", "低光照增强", "医学图像自动分割", "病灶检测", "人脸识别", "表情分析",
                  "强化学习", "策略梯度", "PPO优化", "离线强化学习", "逆强化学习", "多智能体强化学习",
                  "模仿学习", "状态空间模型", "Transformer变体", "科学AI", "其他AI领域"],
           "domains": ["大语言模型", "自然语言处理", "计算机视觉", "科学AI"]},
}

# 领域名标准化映射（处理 Phase 3+ 中带空格的变体）
DOMAIN_NORMALIZE = {
    "生成式 AI": "生成式AI",
    "AI 系统与硬件": "AI系统与硬件",
    "安全、可信与伦理": "安全可信与伦理",
    "科学 AI": "科学AI",
}


def load_snapshot(snapshot_path):
    """加载快照，返回节点列表和边列表"""
    with open(snapshot_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    nodes = data if isinstance(data, list) else data.get("nodes", data)
    edges = data.get("edges", []) if isinstance(data, dict) else []
    return nodes, edges


def get_domain_nodes(nodes):
    """按领域分组 L3 节点，返回 {domain_name: [node, ...]}"""
    domain_nodes = defaultdict(list)
    domain_level2 = {}  # domain_name -> level 2 node (按 name 匹配)

    for n in nodes:
        if n["level"] == 2:
            # level 2 节点的 name 是实际域名（如"生成式AI"），category 是父级分类
            domain_level2[n["name"]] = n
        if n["level"] == 3:
            cat = n.get("category", "")
            # 标准化 L3 的 category 以匹配 L2 的 name
            cat = DOMAIN_NORMALIZE.get(cat, cat)
            domain_nodes[cat].append(n)

    return domain_nodes, domain_level2


def extract_keywords_from_node(node):
    """从节点名中提取关键词（基于 WUXING_KW 词库匹配）"""
    name = node["name"]
    keywords = set()
    for wx, cfg in WUXING_KW.items():
        for kw in cfg["kw"]:
            if kw in name:
                keywords.add(kw)
    return keywords


def extract_domain_keywords(domain_nodes_list):
    """提取一个领域所有节点的关键词集合"""
    all_kw = set()
    for n in domain_nodes_list:
        all_kw |= extract_keywords_from_node(n)
    return all_kw


def jaccard_similarity(set_a, set_b):
    """计算两个集合的 Jaccard 相似度"""
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def name_similarity(name_a, name_b):
    """计算两个节点名的相似度"""
    return SequenceMatcher(None, name_a, name_b).ratio()


def generate_keyword_overlap_edges(domain_nodes, domain_level2, threshold=0.08):
    """
    第一层：关键词重叠边。
    计算任意两个领域间的关键词 Jaccard 相似度，超过阈值则建立 RELATES_TO 边。
    """
    domain_names = sorted(domain_nodes.keys())
    domain_keywords = {d: extract_domain_keywords(domain_nodes[d]) for d in domain_names}

    edges = []
    stats = []

    for i, da in enumerate(domain_names):
        for db in domain_names[i + 1:]:
            sim = jaccard_similarity(domain_keywords[da], domain_keywords[db])
            if sim >= threshold:
                # 获取 level 2 节点 ID
                src_id = domain_level2.get(da, {}).get("id", "")
                tgt_id = domain_level2.get(db, {}).get("id", "")

                if src_id and tgt_id:
                    shared = domain_keywords[da] & domain_keywords[db]
                    edges.append({
                        "source_id": src_id,
                        "target_id": tgt_id,
                        "relation": "RELATES_TO",
                        "source": "keyword_overlap",
                        "weight": round(sim, 4),
                        "shared_keywords": sorted(shared),
                        "shared_count": len(shared)
                    })
                    stats.append({
                        "domains": f"{da} ↔ {db}",
                        "similarity": round(sim, 4),
                        "shared_kw": len(shared),
                        "top_shared": sorted(shared, key=lambda x: -len(x))[:5]
                    })

    return edges, sorted(stats, key=lambda x: -x["similarity"])


def generate_shared_concept_edges(domain_nodes, domain_level2, name_threshold=0.85):
    """
    第二层：共享节点名边。
    检测跨领域同名或近名节点，建立 SHARES_CONCEPT 边。
    """
    domain_names = sorted(domain_nodes.keys())
    edges = []
    stats = []

    for i, da in enumerate(domain_names):
        for db in domain_names[i + 1:]:
            nodes_a = domain_nodes[da]
            nodes_b = domain_nodes[db]

            for na in nodes_a:
                for nb in nodes_b:
                    sim = name_similarity(na["name"], nb["name"])
                    if sim >= name_threshold:
                        src_id = domain_level2.get(da, {}).get("id", "")
                        tgt_id = domain_level2.get(db, {}).get("id", "")

                        if src_id and tgt_id:
                            edges.append({
                                "source_id": src_id,
                                "target_id": tgt_id,
                                "relation": "SHARES_CONCEPT",
                                "source": "shared_concept",
                                "concept_name": na["name"] if sim >= 0.95 else f"{na['name']} ~ {nb['name']}",
                                "similarity": round(sim, 4),
                                "node_a": na["name"],
                                "node_b": nb["name"]
                            })
                            stats.append({
                                "domains": f"{da} ↔ {db}",
                                "concept": na["name"] if sim >= 0.95 else f"{na['name']} ≈ {nb['name']}",
                                "similarity": round(sim, 4)
                            })

    return edges, stats


def run(base_dir, snapshot_path=None, dry_run=False, output_path=None):
    """
    运行边生成器。

    参数:
        base_dir:      项目根目录
        snapshot_path: 快照 JSON 路径
        dry_run:       仅预览，不写入文件
        output_path:   输出路径（默认覆盖原快照文件）

    返回:
        {"status": "ok", "stats": {...}, "new_edges": [...]}
    """
    if snapshot_path is None:
        snap_dir = os.path.join(base_dir, "data", "snapshots")
        snap_files = sorted([f for f in os.listdir(snap_dir) if f.endswith("_snapshot.json")], reverse=True)
        snapshot_path = os.path.join(snap_dir, snap_files[0]) if snap_files else os.path.join(base_dir, "data", "snapshots", "2026-07-30_snapshot.json")

    if output_path is None:
        output_path = snapshot_path

    nodes, existing_edges = load_snapshot(snapshot_path)
    domain_nodes, domain_level2 = get_domain_nodes(nodes)

    print("=" * 70)
    print("  边生成器 — 跨领域关系边自动生成")
    print("=" * 70)
    print(f"\n  快照: {os.path.basename(snapshot_path)}")
    print(f"  节点: {len(nodes)} (领域: {len(domain_nodes)})")
    print(f"  现有边: {len(existing_edges)} (含 contains 层级边)")

    # ── 第一层：关键词重叠 ──
    print(f"\n{'─' * 50}")
    print(f"  第一层：关键词重叠（Jaccard 相似度 ≥ 0.08）")
    print(f"{'─' * 50}")

    kw_edges, kw_stats = generate_keyword_overlap_edges(domain_nodes, domain_level2)
    print(f"  生成 {len(kw_edges)} 条 RELATES_TO 边")
    for s in kw_stats[:10]:
        print(f"    {s['domains']:<30s} sim={s['similarity']:.4f}  shared={s['shared_kw']}  top={s['top_shared']}")

    if len(kw_stats) > 10:
        print(f"    ... 还有 {len(kw_stats) - 10} 对")

    # ── 第二层：共享节点名 ──
    print(f"\n{'─' * 50}")
    print(f"  第二层：共享节点名（名称相似度 ≥ 0.85）")
    print(f"{'─' * 50}")

    sc_edges, sc_stats = generate_shared_concept_edges(domain_nodes, domain_level2)
    print(f"  生成 {len(sc_edges)} 条 SHARES_CONCEPT 边")
    for s in sc_stats[:15]:
        print(f"    {s['domains']:<30s} {s['concept']} (sim={s['similarity']:.4f})")

    if len(sc_stats) > 15:
        print(f"    ... 还有 {len(sc_stats) - 15} 条")

    # ── 合并 & 去重 ──
    all_new_edges = kw_edges + sc_edges

    # 去重：同一对 domain 只保留一条最高权重的边
    seen_pairs = set()
    deduped = []
    for e in sorted(all_new_edges, key=lambda x: -x.get("weight", 1.0)):
        pair = tuple(sorted([e["source_id"], e["target_id"]]))
        if pair not in seen_pairs:
            seen_pairs.add(pair)
            deduped.append(e)

    # ── 汇总 ──
    total_before = len(existing_edges)
    total_after = total_before + len(deduped)
    edge_ratio_before = total_before / max(len(nodes), 1)
    edge_ratio_after = total_after / max(len(nodes), 1)

    print(f"\n{'─' * 50}")
    print(f"  汇总")
    print(f"{'─' * 50}")
    print(f"  关键词重叠边: {len(kw_edges)}")
    print(f"  共享节点边:   {len(sc_edges)}")
    print(f"  去重后新增:   {len(deduped)}")
    print(f"  原有边:       {total_before}")
    print(f"  合并后总边:   {total_after}")
    print(f"  边密度:       {edge_ratio_before:.2f} → {edge_ratio_after:.2f}")
    print(f"  min=1.5:      {'✅ 达标' if edge_ratio_after >= 1.5 else '⚠️ 未达标 (' + str(round(1.5 - edge_ratio_after, 2)) + ' 差距)'}")

    if dry_run:
        print(f"\n  [DRY RUN] 未写入文件")
        return {
            "status": "ok",
            "dry_run": True,
            "stats": {
                "kw_edges": len(kw_edges),
                "sc_edges": len(sc_edges),
                "total_new": len(deduped),
                "total_before": total_before,
                "total_after": total_after,
                "edge_ratio_before": round(edge_ratio_before, 2),
                "edge_ratio_after": round(edge_ratio_after, 2),
                "meets_target": edge_ratio_after >= 1.5,
            },
            "new_edges": deduped,
            "kw_stats": kw_stats,
            "sc_stats": sc_stats,
        }

    # ── 写入快照 ──
    # 加载原始数据保留完整结构
    with open(snapshot_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    if isinstance(raw, dict):
        raw["edges"] = existing_edges + deduped
        raw["edge_generation"] = {
            "method": "keyword_overlap + shared_concept",
            "generated_at": __import__("datetime").datetime.now().isoformat(),
            "kw_edges": len(kw_edges),
            "sc_edges": len(sc_edges),
            "total_new": len(deduped),
            "total_edges": total_after,
            "edge_ratio": round(edge_ratio_after, 2),
        }
    else:
        # list 格式：创建完整结构
        raw = {
            "nodes": raw,
            "edges": existing_edges + deduped,
            "edge_generation": {
                "method": "keyword_overlap + shared_concept",
                "generated_at": __import__("datetime").datetime.now().isoformat(),
                "kw_edges": len(kw_edges),
                "sc_edges": len(sc_edges),
                "total_new": len(deduped),
                "total_edges": total_after,
                "edge_ratio": round(edge_ratio_after, 2),
            }
        }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=2)

    print(f"\n  已写入: {os.path.basename(output_path)}")
    print("=" * 70)

    return {
        "status": "ok",
        "stats": {
            "kw_edges": len(kw_edges),
            "sc_edges": len(sc_edges),
            "total_new": len(deduped),
            "total_before": total_before,
            "total_after": total_after,
            "edge_ratio_before": round(edge_ratio_before, 2),
            "edge_ratio_after": round(edge_ratio_after, 2),
            "meets_target": edge_ratio_after >= 1.5,
        },
        "new_edges": deduped,
        "kw_stats": kw_stats,
        "sc_stats": sc_stats,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="边生成器 — 自动生成跨领域关系边")
    parser.add_argument("--snapshot", "-s", type=str, default=None, help="快照文件路径")
    parser.add_argument("--dry-run", "-n", action="store_true", help="仅预览，不写入")
    parser.add_argument("--output", "-o", type=str, default=None, help="输出路径")
    parser.add_argument("--base-dir", "-b", type=str, default=None, help="项目根目录")
    args = parser.parse_args()

    DEFAULT_BASE = r"C:\Users\hejij\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a59e217b55e181ea97f0df3\wuxing_flowengine"
    base_dir = args.base_dir or DEFAULT_BASE

    result = run(
        base_dir=base_dir,
        snapshot_path=args.snapshot,
        dry_run=args.dry_run,
        output_path=args.output
    )