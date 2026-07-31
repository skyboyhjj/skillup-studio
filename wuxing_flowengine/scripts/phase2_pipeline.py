#!/usr/bin/env python3
"""
Phase 2 完整流水线：双层标注 → SpinorNode → 三轨S计算 → 领域对比 → 报告
支持参数化调用，可被月度编排器导入。
"""
import json, os, sys, math
from collections import Counter, defaultdict

# ============================================================
# 第 1 步：关键节点双层标注 (SpinorNode)
# ============================================================
# 旋量节点：同一节点在不同层级上可以有不同五行标签
# 基于设计文档 §4.2.1 的旋量-太极修正方案

DUAL_LABEL_NODES = {
    # 跨领域节点 (~20%)
    "强化学习":         {"seed": "金", "current": "火", "transcend": "木"},
    "策略梯度与PPO优化": {"seed": "金", "current": "火", "transcend": "水"},
    "离线强化学习":     {"seed": "金", "current": "土", "transcend": "水"},
    "逆强化学习":       {"seed": "金", "current": "火", "transcend": "木"},
    "多智能体强化学习": {"seed": "火", "current": "火", "transcend": "木"},
    "世界模型建模":     {"seed": "土", "current": "木", "transcend": "水"},
    "扩散模型":         {"seed": "土", "current": "木", "transcend": "水"},
    "扩散模型核心演进": {"seed": "土", "current": "木", "transcend": "水"},
    "生成对抗网络":     {"seed": "土", "current": "木", "transcend": "金"},
    "生成式模型":       {"seed": "土", "current": "木", "transcend": "水"},
    "语言模型":         {"seed": "土", "current": "水", "transcend": "水"},
    "对比学习":         {"seed": "土", "current": "金", "transcend": "水"},
    "模仿学习":         {"seed": "金", "current": "木", "transcend": "水"},
    "模仿学习与示教学习": {"seed": "金", "current": "木", "transcend": "水"},
    "逆最优控制":       {"seed": "金", "current": "火", "transcend": "木"},
    "逆最优控制与模仿学习": {"seed": "金", "current": "火", "transcend": "木"},
    "视觉Transformer加速": {"seed": "土", "current": "水", "transcend": "木"},
    "图神经网络":       {"seed": "土", "current": "金", "transcend": "水"},
    "图神经网络与消息传递": {"seed": "土", "current": "金", "transcend": "水"},
    "知识图谱嵌入":     {"seed": "土", "current": "金", "transcend": "水"},
    "混合专家模型":     {"seed": "土", "current": "水", "transcend": "水"},
    "混合专家模型架构": {"seed": "土", "current": "水", "transcend": "水"},
    "自动化机器学习":   {"seed": "土", "current": "火", "transcend": "木"},
    "持续学习":         {"seed": "土", "current": "水", "transcend": "木"},
    "联邦学习与加密计算": {"seed": "金", "current": "土", "transcend": "水"},
    "差分隐私保护与脱敏技术": {"seed": "金", "current": "金", "transcend": "水"},

    # 混合型节点 (~30%)
    "人机协作与对齐":   {"seed": "火", "current": "木", "transcend": "金"},
    "多智能体协作与社会模拟": {"seed": "火", "current": "火", "transcend": "水"},
    "社会模拟":         {"seed": "火", "current": "水", "transcend": "金"},
    "多模态大模型在机器人领域的应用": {"seed": "木", "current": "水", "transcend": "火"},
    "自动驾驶端到端感知-决策模型": {"seed": "木", "current": "水", "transcend": "金"},
    "自动驾驶决策安全与伦理": {"seed": "金", "current": "水", "transcend": "金"},
    "车路协同技术":     {"seed": "土", "current": "火", "transcend": "木"},
    "隐私保护音频监测": {"seed": "金", "current": "水", "transcend": "金"},
    "语义地图构建":     {"seed": "土", "current": "水", "transcend": "木"},
    "主动感知与探索":   {"seed": "木", "current": "水", "transcend": "水"},
    "状态估计与滤波算法": {"seed": "土", "current": "金", "transcend": "水"},
    "大模型作为评估者": {"seed": "金", "current": "火", "transcend": "水"},
    "大语言模型驱动的内容理解": {"seed": "水", "current": "火", "transcend": "水"},
    "多模态生成式推荐": {"seed": "木", "current": "火", "transcend": "水"},
    "语义ID学习":       {"seed": "土", "current": "火", "transcend": "水"},
    "协同过滤与LLM对齐": {"seed": "土", "current": "火", "transcend": "金"},
    "AI价值观对齐与鲁棒性": {"seed": "金", "current": "火", "transcend": "金"},
    "伦理与价值观对齐": {"seed": "金", "current": "火", "transcend": "金"},
    "AI数据中心能效管理": {"seed": "土", "current": "金", "transcend": "水"},
    "支持结构优化的3D打印生成": {"seed": "木", "current": "土", "transcend": "水"},
    "变分量子算法优化": {"seed": "金", "current": "水", "transcend": "水"},
    "量子神经网络":     {"seed": "金", "current": "水", "transcend": "水"},
    "搜索算法":         {"seed": "土", "current": "金", "transcend": "水"},
    "进化算法":         {"seed": "土", "current": "木", "transcend": "水"},
    "蒙特卡洛树搜索":   {"seed": "土", "current": "金", "transcend": "水"},
    "文本引导的图像编辑": {"seed": "木", "current": "火", "transcend": "水"},
    "视觉引导的音频分离": {"seed": "木", "current": "水", "transcend": "金"},
    "触觉-视觉跨模态感知": {"seed": "木", "current": "水", "transcend": "金"},
    "多模态知识图谱构建": {"seed": "金", "current": "木", "transcend": "水"},
    "跨模态检索增强生成": {"seed": "木", "current": "火", "transcend": "水"},
    "多模态实体链接":   {"seed": "金", "current": "木", "transcend": "水"},
    "常识知识表示与提取": {"seed": "金", "current": "土", "transcend": "水"},
    "因果发现与因果推断": {"seed": "金", "current": "水", "transcend": "水"},
    "数学定理证明与逻辑演绎": {"seed": "金", "current": "金", "transcend": "水"},
    "神经符号AI":       {"seed": "金", "current": "水", "transcend": "水"},
    "蛋白质结构预测":   {"seed": "水", "current": "木", "transcend": "金"},
    "药物小分子筛选与设计": {"seed": "水", "current": "木", "transcend": "金"},
    "基因序列建模与表达预测": {"seed": "水", "current": "木", "transcend": "金"},
    "Transformer架构变体研究": {"seed": "土", "current": "水", "transcend": "木"},
    "神经网络泛化理论与边界": {"seed": "土", "current": "金", "transcend": "水"},
    "拓扑序态发现与流形学习": {"seed": "土", "current": "水", "transcend": "水"},
    "元学习与跨任务适应": {"seed": "土", "current": "木", "transcend": "水"},
    "迁移学习与领域自适应": {"seed": "土", "current": "木", "transcend": "水"},
    "知识编辑与更新":   {"seed": "金", "current": "水", "transcend": "水"},
    "知识编辑与事实一致性维护": {"seed": "金", "current": "水", "transcend": "水"},
    "隐式推理架构":     {"seed": "金", "current": "水", "transcend": "水"},
    "思维链效率与路径优化": {"seed": "金", "current": "水", "transcend": "火"},
    "逻辑与数值联合推理": {"seed": "金", "current": "金", "transcend": "水"},
    "幻觉检测与事实性增强": {"seed": "金", "current": "水", "transcend": "金"},
    "幻觉检测与置信度评估": {"seed": "金", "current": "水", "transcend": "金"},
    "检索增强生成":     {"seed": "水", "current": "火", "transcend": "水"},
    "动态上下文检索策略": {"seed": "水", "current": "火", "transcend": "水"},
    "不可微分奖励演化与建模": {"seed": "金", "current": "火", "transcend": "水"},
    "状态空间模型":     {"seed": "土", "current": "水", "transcend": "木"},
    "虚拟电厂优化与调度": {"seed": "水", "current": "火", "transcend": "金"},
    "零碳电力交易博弈机制": {"seed": "水", "current": "火", "transcend": "金"},
    "气象预报与极端天气模拟": {"seed": "水", "current": "土", "transcend": "金"},
    "科学计算神经网络": {"seed": "水", "current": "土", "transcend": "水"},
    "智能材料建模与性能预测": {"seed": "水", "current": "木", "transcend": "金"},
    "基于模型的强化学习": {"seed": "金", "current": "火", "transcend": "木"},
    "基于策略的强化学习": {"seed": "金", "current": "火", "transcend": "木"},
    "基于价值的强化学习": {"seed": "金", "current": "火", "transcend": "木"},
    "任务规划与推理决策": {"seed": "金", "current": "火", "transcend": "水"},
    "工具调用与API交互": {"seed": "土", "current": "火", "transcend": "水"},
    "长短期记忆与知识获取": {"seed": "土", "current": "水", "transcend": "火"},
    "自主工作流与自动化": {"seed": "土", "current": "火", "transcend": "木"},
    "智能体评估与基准测试": {"seed": "金", "current": "火", "transcend": "金"},
    "人格化与情感对话模拟": {"seed": "水", "current": "火", "transcend": "木"},
    "意图识别与槽位填充": {"seed": "水", "current": "火", "transcend": "金"},
    "跨语言知识迁移与对齐": {"seed": "水", "current": "木", "transcend": "金"},
    "临床法律金融领域文本生成": {"seed": "水", "current": "火", "transcend": "金"},
    "文本水印与版权溯源": {"seed": "金", "current": "水", "transcend": "金"},
    "自动化评测基准":   {"seed": "金", "current": "火", "transcend": "金"},
    "自动化提示词生成与优化": {"seed": "水", "current": "火", "transcend": "木"},
    "Sim-to-Real跨域迁移": {"seed": "木", "current": "金", "transcend": "水"},
    "具身智能体任务分解": {"seed": "木", "current": "火", "transcend": "金"},
    "动态SLAM":         {"seed": "土", "current": "水", "transcend": "木"},
    "多传感器融合定位": {"seed": "土", "current": "水", "transcend": "金"},
    "机器人运动学与动力学建模": {"seed": "土", "current": "金", "transcend": "木"},
    "机器人控制与规划": {"seed": "土", "current": "木", "transcend": "金"},
    "仿真平台介绍":     {"seed": "土", "current": "火", "transcend": "水"},
    "康复机器人安全":   {"seed": "木", "current": "金", "transcend": "火"},
    "社会辅助机器人":   {"seed": "木", "current": "火", "transcend": "金"},
    "农业智能决策与采摘": {"seed": "木", "current": "火", "transcend": "金"},
    "空间机器人与微重力操作": {"seed": "木", "current": "金", "transcend": "水"},
    "手术机器人与远程医疗": {"seed": "木", "current": "金", "transcend": "火"},
    "水下机器人与海洋探测": {"seed": "木", "current": "水", "transcend": "金"},
    "搜救机器人":       {"seed": "木", "current": "火", "transcend": "金"},
    "机器人感知单元":   {"seed": "木", "current": "土", "transcend": "水"},
    "机器人本体类别":   {"seed": "木", "current": "土", "transcend": "金"},
    "情感驱动的语音合成": {"seed": "水", "current": "火", "transcend": "木"},
    "AI音乐理解旋律与合成": {"seed": "水", "current": "火", "transcend": "木"},
    "神经风格迁移与属性编辑": {"seed": "木", "current": "水", "transcend": "金"},
    "空间机器人与微重力": {"seed": "木", "current": "金", "transcend": "水"},
    "水下机器人与海洋探测": {"seed": "木", "current": "水", "transcend": "金"},
}


def get_wuxing_for_layer(node_name, default_wx, layer):
    """获取节点在指定层的五行标签"""
    if node_name in DUAL_LABEL_NODES:
        return DUAL_LABEL_NODES[node_name].get(layer, default_wx)
    return default_wx


def build_layers_with_spinor(nodes):
    """按认知深度构建三层，应用双层标注"""
    seed_layer = []
    current_layer = []
    transcend_layer = []

    for n in nodes:
        cd = n.get("cognitive_depth", "L2")
        default_wx = n.get("wuxing", "土")

        if cd == "L1":
            wx = get_wuxing_for_layer(n["name"], default_wx, "seed")
            seed_layer.append({"name": n["name"], "wuxing": wx, "cognitive_depth": cd, "category": n.get("category", ""), "default_wx": default_wx, "is_dual": n["name"] in DUAL_LABEL_NODES})
        elif cd == "L2":
            wx = get_wuxing_for_layer(n["name"], default_wx, "current")
            current_layer.append({"name": n["name"], "wuxing": wx, "cognitive_depth": cd, "category": n.get("category", ""), "default_wx": default_wx, "is_dual": n["name"] in DUAL_LABEL_NODES})
        else:  # L3, L4
            wx = get_wuxing_for_layer(n["name"], default_wx, "transcend")
            transcend_layer.append({"name": n["name"], "wuxing": wx, "cognitive_depth": cd, "category": n.get("category", ""), "default_wx": default_wx, "is_dual": n["name"] in DUAL_LABEL_NODES})

    return seed_layer, current_layer, transcend_layer


def layer_wx_dist(layer_data):
    c = Counter(n["wuxing"] for n in layer_data)
    total = max(len(layer_data), 1)
    return [c.get(wx, 0) / total for wx in ["木", "火", "土", "金", "水"]]


def cosine_distance(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x**2 for x in a))
    norm_b = math.sqrt(sum(y**2 for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0
    return 1 - dot / (norm_a * norm_b)


def layer_score(layer_data, layer_type):
    """计算单层得分：基于五行分布的均衡性和深度"""
    wx_counts = Counter(n["wuxing"] for n in layer_data)
    total = len(layer_data)
    if total == 0:
        return 0

    H_layer = -sum((wx_counts.get(wx, 0) / total) * math.log2(max(wx_counts.get(wx, 0), 1) / total)
                    for wx in ["木", "火", "土", "金", "水"] if wx_counts.get(wx, 0) > 0)
    H_max = math.log2(5)
    balance = H_layer / H_max if H_max > 0 else 0

    depth_weights = {"L1": 1.0, "L2": 2.0, "L3": 3.0, "L4": 4.0}
    avg_depth = sum(depth_weights.get(n.get("cognitive_depth", "L2"), 2.0) for n in layer_data) / total

    categories = set(n.get("category", "") for n in layer_data)
    coverage = len(categories) / 16

    return balance * 20 + avg_depth * 5 + coverage * 10


def conversion_efficiency(layer_a, layer_b):
    """计算层间转换效率"""
    wx_a = Counter(n["wuxing"] for n in layer_a)
    wx_b = Counter(n["wuxing"] for n in layer_b)

    SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
    KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

    sheng_score = 0
    ke_score = 0
    total_pairs = 0

    for wx1, cnt1 in wx_a.items():
        for wx2, cnt2 in wx_b.items():
            if SHENG.get(wx1) == wx2:
                sheng_score += cnt1 * cnt2
            elif KE.get(wx1) == wx2:
                ke_score += cnt1 * cnt2
            total_pairs += cnt1 * cnt2

    if total_pairs == 0:
        return 0.5

    sheng_ratio = sheng_score / total_pairs
    ke_ratio = ke_score / total_pairs

    return 0.5 + sheng_ratio * 0.4 - ke_ratio * 0.2


def compute_domain_tracks(domain_nodes_all):
    """对单个领域的所有节点计算三轨 S 值"""
    if not domain_nodes_all:
        return {"A": 0, "B": 0, "C": 0, "D": 0, "total": 0}

    d_seed = [n for n in domain_nodes_all if n.get("cognitive_depth") == "L1"]
    d_curr = [n for n in domain_nodes_all if n.get("cognitive_depth") == "L2"]
    d_tran = [n for n in domain_nodes_all if n.get("cognitive_depth") in ("L3", "L4")]

    d_seed_wx = [get_wuxing_for_layer(n["name"], n.get("wuxing", "土"), "seed") for n in d_seed]
    d_curr_wx = [get_wuxing_for_layer(n["name"], n.get("wuxing", "土"), "current") for n in d_curr]
    d_tran_wx = [get_wuxing_for_layer(n["name"], n.get("wuxing", "土"), "transcend") for n in d_tran]

    all_wx = d_seed_wx + d_curr_wx + d_tran_wx
    total = len(all_wx)
    if total == 0:
        return {"A": 0, "B": 0, "C": 0, "D": 0, "total": 0}

    wc = Counter(all_wx)
    w_d = {wx: wc.get(wx, 0) / total for wx in ["木", "火", "土", "金", "水"]}

    O_t_d = w_d["土"] * 0.6 + w_d["金"] * 0.3 + 0.1
    E_u_d = 1 - 0.5 * abs(w_d["木"] - 0.25) - 0.5 * abs(w_d["水"] - 0.25)
    C_k_d = w_d["水"] * 0.5 + w_d["火"] * 0.3 + w_d["木"] * 0.2
    K_y_d = w_d["火"] * 0.4 + w_d["土"] * 0.3 + 0.1

    O_t_d = max(0, min(1, O_t_d)); E_u_d = max(0, min(1, E_u_d))
    C_k_d = max(0, min(1, C_k_d)); K_y_d = max(0, min(1, K_y_d))

    S_A_d = O_t_d * E_u_d * C_k_d * K_y_d * 100
    S_B_d = (len(d_seed) * 0.3 + len(d_curr) * 0.4 + len(d_tran) * 0.3) * 5
    S_C_d = (1 + len(d_seed) * 0.1) * (len(d_tran) / max(len(d_curr), 1)) * total * 0.5
    S_D_d = math.sqrt(O_t_d**2 + E_u_d**2 + C_k_d**2 + K_y_d**2)

    return {"A": round(S_A_d, 2), "B": round(S_B_d, 2), "C": round(S_C_d, 2), "D": round(S_D_d, 4), "total": total}


def run(base_dir, nodes_path=None, class_path=None, output_dir=None, month_label=None):
    """
    运行 Phase 2 流水线。

    参数:
        base_dir:    项目根目录（wuxing_flowengine/）
        nodes_path:  快照节点 JSON 路径（默认自动找最新）
        class_path:  Phase 1 分类结果路径（默认 output/wuxing_classification.json）
        output_dir:  输出目录
        month_label: 月度标签

    返回:
        {"status": "ok", "outputs": {"diagnosis": path, "dual_labels": path}, "tracks": {...}, "domain_tracks": {...}}
    """
    if nodes_path is None:
        snap_dir = os.path.join(base_dir, "data", "snapshots")
        snap_files = sorted([f for f in os.listdir(snap_dir) if f.endswith("_snapshot.json")], reverse=True)
        if snap_files:
            nodes_path = os.path.join(snap_dir, snap_files[0])
        else:
            nodes_path = os.path.join(base_dir, "data", "snapshots", "2026-07-30_snapshot.json")

    if class_path is None:
        class_path = os.path.join(base_dir, "output", "wuxing_classification.json")

    if output_dir is None:
        output_dir = os.path.join(base_dir, "output")

    os.makedirs(output_dir, exist_ok=True)

    diagnose_dir = os.path.join(base_dir, "diagnose")
    if diagnose_dir not in sys.path:
        sys.path.insert(0, diagnose_dir)

    print(f"[Phase 2] 已定义 {len(DUAL_LABEL_NODES)} 个双层标注节点")

    # 加载数据
    with open(nodes_path, "r", encoding="utf-8") as f:
        snapshot = json.load(f)
        nodes = snapshot.get("nodes", [])
        edges = snapshot.get("edges", [])
    with open(class_path, "r", encoding="utf-8") as f:
        classified = json.load(f)

    class_by_id = {c["id"]: c for c in classified}
    node_by_name = {}
    for n in nodes:
        if n["level"] == 3:
            node_by_name[n["name"]] = n

    # 统计双层标注覆盖
    dual_matched = sum(1 for name in DUAL_LABEL_NODES if name in node_by_name)
    dual_mismatched = len(DUAL_LABEL_NODES) - dual_matched
    print(f"[Phase 2] 双层标注: 精确匹配 {dual_matched}, 未匹配 {dual_mismatched}")

    # 构建三层
    seed_layer, current_layer, transcend_layer = build_layers_with_spinor(nodes)

    # 图密度计算（用于 K_y 替代方案）
    edge_count = len(edges)
    node_degree = {}
    for n in nodes:
        node_degree[n["id"]] = 0
    for e in edges:
        if e.get("source_id") in node_degree:
            node_degree[e["source_id"]] += 1
        if e.get("target_id") in node_degree:
            node_degree[e["target_id"]] += 1
    degrees = list(node_degree.values())
    avg_degree = 2 * edge_count / max(len(nodes), 1)
    max_degree = max(degrees) if degrees else 1
    graph_density_ratio = avg_degree / max_degree if max_degree > 0 else 0
    edge_ratio = edge_count / max(len(nodes), 1)

    # 层级完整性检查（按领域）
    def layer_completeness(nodes_list):
        """领域层级完整性检查。种子层缺失 ≠ 缺陷，而是共享全局种子层的信号。"""
        domain_groups = defaultdict(list)
        for n in nodes_list:
            if n["level"] == 3:
                domain_groups[n.get("category", "")].append(n)
        result = {}
        for domain, dn in domain_groups.items():
            l1 = sum(1 for n in dn if n.get("cognitive_depth") == "L1")
            l2 = sum(1 for n in dn if n.get("cognitive_depth") == "L2")
            l3 = sum(1 for n in dn if n.get("cognitive_depth") in ("L3", "L4"))
            result[domain] = {
                "node_count": len(dn),
                "L1_count": l1, "L2_count": l2, "L3_count": l3,
                "has_seed": l1 > 0,
                "seed_share": "own" if l1 > 0 else "shared_global",
                "report_note": "该领域无独立种子层，共享全局基础层（机器学习基础），按子旋量处理" if l1 == 0 else "该领域有独立种子层"
            }
        return result

    layer_completeness_result = layer_completeness(nodes)

    print("\n[Phase 2] 三层五行分布（含双层标注）:")
    for layer_name, layer_data in [("种子层", seed_layer), ("现行层", current_layer), ("超越层", transcend_layer)]:
        wx_counts = Counter(n["wuxing"] for n in layer_data)
        dual_count = sum(1 for n in layer_data if n["is_dual"])
        print(f"  {layer_name}: {len(layer_data)}节点 (双层标注: {dual_count})")
        for wx in ["木", "火", "土", "金", "水"]:
            print(f"    {wx}: {wx_counts.get(wx, 0)}")

    # 道境诊断
    from wuxing_diagnose_v2 import diagnose

    rings = [
        {"label": "种子层", "concepts": [{"name": n["name"], "wuxing": n["wuxing"], "cognitive_depth": n.get("cognitive_depth")} for n in seed_layer]},
        {"label": "现行层", "concepts": [{"name": n["name"], "wuxing": n["wuxing"], "cognitive_depth": n.get("cognitive_depth")} for n in current_layer]},
        {"label": "超越层", "concepts": [{"name": n["name"], "wuxing": n["wuxing"], "cognitive_depth": n.get("cognitive_depth")} for n in transcend_layer]},
    ]

    result = diagnose(rings)

    # 四维读数
    freq = result["dim1_freq"]
    ent = result["dim4_entropy"]
    comp = result["dim5_compass"]
    path = result["dim3_edges"]

    w = {wx: freq[wx]["pct"] / 100.0 for wx in ["木", "火", "土", "金", "水"]}

    O_t = w["土"] * 0.6 + w["金"] * 0.3 + (1 - ent["ratio"]) * 0.1
    E_u = 1 - 0.5 * abs(w["木"] - 0.25) - 0.5 * abs(w["水"] - 0.25) - 0.3 * math.sqrt(comp["cx"]**2 + comp["cy"]**2)
    C_k = w["水"] * 0.5 + w["火"] * 0.3 + w["木"] * 0.2
    ke_count = sum(1 for e in path if e["relation"] == "相克")
    # K_y: 图密度替代方案
    if ke_count > 0:
        K_y = w["火"] * 0.4 + w["土"] * 0.3 + (ke_count / max(1, len(path))) * 0.3
    else:
        K_y = w["火"] * 0.4 + w["土"] * 0.3 + graph_density_ratio * 0.3

    O_t = max(0, min(1, O_t)); E_u = max(0, min(1, E_u)); C_k = max(0, min(1, C_k)); K_y = max(0, min(1, K_y))

    # S_sum: 加权和（主指标，与 θ 同量纲 0~100）
    S_sum = (O_t + E_u + C_k + K_y) * 25
    # S_prod: 乘积（辅助指标，木桶效应检测）
    S_prod = O_t * E_u * C_k * K_y * 100

    # 轨道 A: 乘积 S（保留为辅助）
    S_A = S_prod

    # 轨道 B: S_spiral
    score_seed = layer_score(seed_layer, "seed")
    score_current = layer_score(current_layer, "current")
    score_transcend = layer_score(transcend_layer, "transcend")
    eff_seed_curr = conversion_efficiency(seed_layer, current_layer)
    eff_curr_trans = conversion_efficiency(current_layer, transcend_layer)
    S_B = (score_seed * 0.3 + score_current * 0.4 + score_transcend * 0.3) * eff_seed_curr * eff_curr_trans

    # 轨道 C: S_v2
    sheng_count = sum(1 for e in path if e["relation"] == "相生")
    phase = 1.0 + sheng_count * 0.3 + ke_count * 0.5
    dist_seed = layer_wx_dist(seed_layer)
    dist_curr = layer_wx_dist(current_layer)
    dist_trans = layer_wx_dist(transcend_layer)
    gradient = (cosine_distance(dist_seed, dist_curr) + cosine_distance(dist_curr, dist_trans)) * 50
    avg_depth = sum({"L1": 1, "L2": 2, "L3": 3, "L4": 4}.get(n.get("cognitive_depth", "L2"), 2) for n in nodes) / len(nodes)
    accumulation = len(nodes) * avg_depth / 100
    S_C = phase * gradient * accumulation

    # 轨道 D: 模长 S
    S_D = math.sqrt(O_t**2 + E_u**2 + C_k**2 + K_y**2)

    # 领域计算
    print("\n[Phase 2] 按领域计算三轨 S 值...")
    domains = set(n.get("category", "") for n in nodes if n["level"] == 3)
    domain_results = {}
    for domain in sorted(domains):
        domain_nodes = [n for n in nodes if n.get("category") == domain]
        domain_results[domain] = compute_domain_tracks(domain_nodes)

    print(f"  {'领域':<20s} {'节点':>4s} {'A(乘积)':>8s} {'B(螺旋)':>8s} {'C(v2)':>8s} {'D(模长)':>8s}")
    print(f"  {'-'*20} {'-'*4} {'-'*8} {'-'*8} {'-'*8} {'-'*8}")
    for domain, tr in sorted(domain_results.items(), key=lambda x: -x[1]["total"]):
        print(f"  {domain:<20s} {tr['total']:>4d} {tr['A']:>8.2f} {tr['B']:>8.2f} {tr['C']:>8.2f} {tr['D']:>8.4f}")

    # 输出
    print("\n" + "=" * 70)
    print(f"  Phase 2 诊断结果：双层标注 + 三轨对比{f' ({month_label})' if month_label else ''}")
    print("=" * 70)

    print(f"\n  ── 四维读数 ──")
    print(f"    O_t={O_t:.4f} E_u={E_u:.4f} C_k={C_k:.4f} K_y={K_y:.4f}")
    print(f"    K_y: ke_count={ke_count}, graph_density_ratio={graph_density_ratio:.4f}")

    print(f"\n  ── 三轨 S 值对比 ──")
    print(f"    S_sum (加权和·主):  {S_sum:.2f}")
    print(f"    S_prod (乘积·辅助): {S_prod:.2f}")
    print(f"    轨道 B (S_spiral):   {S_B:.2f}")
    print(f"    轨道 C (S_v2):       {S_C:.2f}")
    print(f"    轨道 D (模长):       {S_D:.4f}")

    print(f"\n  ── 层间转换效率 ──")
    print(f"    种子→现行: {eff_seed_curr:.3f} | 现行→超越: {eff_curr_trans:.3f}")

    # 阶段判定
    all_wx = [n["wuxing"] for n in seed_layer] + [n["wuxing"] for n in current_layer] + [n["wuxing"] for n in transcend_layer]
    wc_all = Counter(all_wx)
    max_pct = max(wc_all.values()) / len(all_wx) * 100
    if S_sum >= 90:
        stage = "化（转折期）—— S_sum 极高，系统进入范式转换"
    elif S_sum >= 60:
        stage = "通（成熟期）—— S_sum 健康，四维运转良好"
    elif max_pct > 30:
        stage = "生（积累期）"
    else:
        stage = "生（积累期）"
    print(f"\n  ── 阶段判定 ──")
    print(f"    {stage}")

    # 层级完整性报告
    print(f"\n  ── 层级完整性（shared_global 语义）──")
    shared_count = sum(1 for v in layer_completeness_result.values() if v["seed_share"] == "shared_global")
    own_count = sum(1 for v in layer_completeness_result.values() if v["seed_share"] == "own")
    print(f"    独立种子层: {own_count} 领域 | 共享全局种子层: {shared_count} 领域")
    for domain, lc in sorted(layer_completeness_result.items()):
        if lc["seed_share"] == "shared_global":
            print(f"    {domain:<20s}: {lc['report_note']}")

    # 保存
    suffix = f"_{month_label}" if month_label else ""
    diag_path = os.path.join(output_dir, f"phase2_diagnosis{suffix}.json")
    dual_path = os.path.join(output_dir, f"dual_label_nodes{suffix}.json")

    output = {
        "phase": 2,
        "month_label": month_label,
        "dual_label_count": len(DUAL_LABEL_NODES),
        "dual_label_applied": dual_matched,
        "layers": {
            "seed": {"count": len(seed_layer), "wuxing": dict(Counter(n["wuxing"] for n in seed_layer)), "dual_count": sum(1 for n in seed_layer if n["is_dual"])},
            "current": {"count": len(current_layer), "wuxing": dict(Counter(n["wuxing"] for n in current_layer)), "dual_count": sum(1 for n in current_layer if n["is_dual"])},
            "transcend": {"count": len(transcend_layer), "wuxing": dict(Counter(n["wuxing"] for n in transcend_layer)), "dual_count": sum(1 for n in transcend_layer if n["is_dual"])},
        },
        "overall_wuxing": dict(wc_all),
        "four_dims": {"O_t": round(O_t, 4), "E_u": round(E_u, 4), "C_k": round(C_k, 4), "K_y": round(K_y, 4)},
        "tracks": {
            "S_sum": round(S_sum, 2),       # 加权和（主指标）
            "S_prod": round(S_prod, 2),      # 乘积（辅助指标）
            "B": round(S_B, 2), "C": round(S_C, 2), "D": round(S_D, 4)
        },
        "edge_quality": {
            "edge_count": edge_count, "node_count": len(nodes),
            "edge_ratio": round(edge_ratio, 2),
            "min_edge_ratio_ok": edge_ratio >= 1.5,
            "avg_degree": round(avg_degree, 2), "max_degree": max_degree,
            "graph_density_ratio": round(graph_density_ratio, 4),
            "ky_mode": "graph_density" if ke_count == 0 else "ke_edge_count"
        },
        "layer_completeness": layer_completeness_result,
        "conversion_efficiency": {"seed_to_current": round(eff_seed_curr, 3), "current_to_transcend": round(eff_curr_trans, 3)},
        "scores": {"seed": round(score_seed, 2), "current": round(score_current, 2), "transcend": round(score_transcend, 2)},
        "phase": phase, "gradient": round(gradient, 2), "accumulation": round(accumulation, 2),
        "domain_tracks": domain_results,
        "stage": stage,
        "diagnosis": result,
    }

    with open(diag_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    dual_list = [{"name": name, "projections": proj, "matched": name in node_by_name}
                 for name, proj in DUAL_LABEL_NODES.items()]
    with open(dual_path, "w", encoding="utf-8") as f:
        json.dump(dual_list, f, ensure_ascii=False, indent=2)

    print(f"\n  结果已保存到: {output_dir}")
    print("=" * 70)
    print("Phase 2 完成!")
    print("=" * 70)

    return {
        "status": "ok",
        "outputs": {"diagnosis": diag_path, "dual_labels": dual_path},
        "tracks": {"S_sum": round(S_sum, 2), "S_prod": round(S_prod, 2), "B": round(S_B, 2), "C": round(S_C, 2), "D": round(S_D, 4)},
        "four_dims": {"O_t": round(O_t, 4), "E_u": round(E_u, 4), "C_k": round(C_k, 4), "K_y": round(K_y, 4)},
        "domain_tracks": domain_results,
        "layer_completeness": layer_completeness_result,
        "edge_quality": {"edge_ratio": round(edge_ratio, 2), "min_edge_ratio_ok": edge_ratio >= 1.5},
        "stage": stage
    }


if __name__ == "__main__":
    DEFAULT_BASE = r"C:\Users\hejij\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a59e217b55e181ea97f0df3\wuxing_flowengine"
    run(DEFAULT_BASE)