#!/usr/bin/env python3
"""
概念地图五行诊断器 v2.0 · 认知深度感知版
对齐「五行诊断框架设计方案 v2.0」七维指标体系 + 认知深度维度
新增: --depth L1|L2|L3|L4|all 深度筛选
      --depth-compare 两文件深度差异对比
      --depth-profile 展示各深度的五行分布
用法: python wuxing_diagnose_v2.py <json文件或目录> [--depth L2] [--depth-compare] [--depth-profile]
"""

import json
import os
import sys
import math
from collections import Counter
from pathlib import Path

# ============================================================
# 常量
# ============================================================
WX_ORDER = ["木", "火", "土", "金", "水"]
WX_COLORS = {
    "木": "#2ecc71", "火": "#e74c3c", "土": "#d4a44a",
    "金": "#f1c40f", "水": "#3498db"
}
WX_ROLES = {
    "木": ("开拓者", "开拓新方向、催生新框架"),
    "火": ("传播者", "传播观点、引发讨论、行动号召"),
    "土": ("承载者", "综合前人成果、承载历史厚度"),
    "金": ("批判者", "精准实验、锐利批判、定论收敛"),
    "水": ("探索者", "探索开放、深层涌现、跨域连接"),
}

# 认知深度元数据
DEPTH_LEVELS = ["L1", "L2", "L3", "L4"]
DEPTH_LABELS = {
    "L1": "白话 · 基本义",
    "L2": "精读 · 哲学义",
    "L3": "应用 · 实践义",
    "L4": "学术 · 考据义",
}
DEPTH_WEIGHTS = {"L1": 1.0, "L2": 2.0, "L3": 3.0, "L4": 4.0}
DEPTH_EMOJI = {"L1": "👶", "L2": "📚", "L3": "💼", "L4": "🔬"}

# 相生: 木→火→土→金→水→木
SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
# 相克: 木→土→水→火→金→木
KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

# 五行方位坐标
WX_COORD = {"木": (-1, 0), "火": (0, -1), "土": (0, 0), "金": (1, 0), "水": (0, 1)}

# 路径画像库
PATH_PROFILES = {
    ("木", "火", "土"): ("趋势→热议→沉淀", "新技术报道"),
    ("火", "水", "金"): ("热点→深挖→定论", "深度调查"),
    ("土", "金", "水"): ("综述→批判→开放", "学术评论"),
    ("水", "木", "火"): ("迷茫→破局→号召", "思想启蒙"),
    ("土", "水", "金"): ("传统→颠覆→精炼", "范式翻转型"),
    ("木", "火", "金"): ("创新→传播→定论", "科普型"),
    ("金", "水", "木"): ("证据→探索→新方向", "实证探索型"),
}


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_config(path):
    """加载权重配置文件，合并默认值"""
    defaults = {
        "depth_weights": {"L1": 1.0, "L2": 2.0, "L3": 3.0, "L4": 4.0},
        "layer_weights": {},
        "wuxing_bias": {"木": 1.0, "火": 1.0, "土": 1.0, "金": 1.0, "水": 1.0},
        "entropy_thresholds": {"high": 0.85, "low": 0.50},
        "path_sensitivity": {"sheng_multiplier": 1.0, "ke_multiplier": 1.0},
        "dominance_threshold": 30.0,
        "scarcity_threshold": 10.0,
    }
    if not path:
        return defaults
    with open(path, "r", encoding="utf-8") as f:
        user_config = json.load(f)
    # 合并：用户配置覆盖默认值
    for key in defaults:
        if key in user_config:
            if isinstance(defaults[key], dict):
                defaults[key].update(user_config[key])
            else:
                defaults[key] = user_config[key]
    return defaults


def extract_layer_name(ring_label):
    for sep in ["·", "：", ":", " "]:
        if sep in ring_label:
            return ring_label.split(sep)[0].strip()
    return ring_label.strip()


def get_wuxing(concept, depth=None):
    """
    从概念中提取五行属性，支持认知深度。
    - 如果 depth=None，返回默认 wuxing（向后兼容）
    - 如果 depth 指定，优先从 wuxing_depth 中取该深度的值
    - 如果 wuxing_depth 不存在，回退到默认 wuxing
    """
    if depth and "wuxing_depth" in concept:
        return concept["wuxing_depth"].get(depth, concept.get("wuxing", "?"))
    return concept.get("wuxing", "?")


def get_cognitive_depth(concept):
    """获取概念的主导认知深度（如果标注了）"""
    return concept.get("cognitive_depth", None)


def collect_concepts_weighted(rings, depth=None, config=None):
    """
    收集所有概念，支持深度加权和层加权。
    返回: (all_wuxing_list, weighted_counter, depth_distribution)
    """
    if config is None:
        config = {"depth_weights": DEPTH_WEIGHTS, "layer_weights": {}, "wuxing_bias": {}}

    depth_weights = config.get("depth_weights", DEPTH_WEIGHTS)
    layer_weights = config.get("layer_weights", {})
    wuxing_bias = config.get("wuxing_bias", {})

    all_concepts = []
    weighted = Counter()
    depth_dist = Counter()
    layer_names = []
    layer_matrix = {}
    layer_concept_counts = []
    depth_layer_matrices = {d: {} for d in DEPTH_LEVELS}

    for ring in rings:
        ln = extract_layer_name(ring["label"])
        layer_names.append(ln)
        concepts = ring.get("concepts", [])
        layer_concept_counts.append(len(concepts))
        c = Counter()

        # 层权重: 匹配层名（支持部分匹配，如 "种子层 · 道体玄理" 匹配 "种子层"）
        lw = 1.0
        for lk, lv in layer_weights.items():
            if lk in ring.get("label", ""):
                lw = lv
                break

        for con in concepts:
            wx = get_wuxing(con, depth)
            cd = get_cognitive_depth(con)
            c[wx] += 1
            all_concepts.append(wx)

            # 深度加权
            dw = depth_weights.get(cd, 1.0) if cd else 1.0
            # 层加权
            # 五行偏置
            bw = wuxing_bias.get(wx, 1.0)
            total_w = dw * lw * bw
            weighted[wx] += total_w

            if cd:
                depth_dist[cd] += 1

            if cd:
                for d in DEPTH_LEVELS:
                    if d not in depth_layer_matrices[d]:
                        depth_layer_matrices[d][ln] = Counter()
                    wx_d = get_wuxing(con, d)
                    depth_layer_matrices[d][ln][wx_d] += 1

        layer_matrix[ln] = c

    return all_concepts, weighted, depth_dist, layer_names, layer_matrix, layer_concept_counts, depth_layer_matrices


def diagnose(data, depth=None, config=None):
    """对单个概念地图执行七维诊断（支持深度筛选 + 权重配置）"""
    if config is None:
        config = {}
    rings = data if isinstance(data, list) else data.get("rings", [])

    all_concepts, weighted, depth_dist, layer_names, layer_matrix, layer_concept_counts, depth_layer_matrices = \
        collect_concepts_weighted(rings, depth, config)

    # 使用加权或原始计数
    if depth:
        total = Counter({wx: round(weighted[wx]) for wx in WX_ORDER})
        total = Counter({wx: max(total[wx], 0) for wx in WX_ORDER})
    else:
        total = Counter(all_concepts)

    N_raw = len(all_concepts)
    N = sum(total.values())
    if N == 0:
        return {"error": "无概念节点"}

    # ================================================================
    # 维度一：五行总体频次分布
    # ================================================================
    freq = {wx: {"count": total.get(wx, 0), "pct": round(total.get(wx, 0) / N * 100, 1)}
            for wx in WX_ORDER}

    freq_interpretations = []
    dom_threshold = config.get("dominance_threshold", 30.0)
    scar_threshold = config.get("scarcity_threshold", 10.0)
    for wx in WX_ORDER:
        pct = freq[wx]["pct"]
        if pct > dom_threshold:
            freq_interpretations.append(f"{wx}性主导（{pct}%），文章核心发力点")
        elif pct < scar_threshold:
            freq_interpretations.append(f"{wx}性显著缺失（{pct}%），文章避开该思维方式")
    if not freq_interpretations:
        freq_interpretations.append("五行接近均衡，综合性文章")

    pct_metal = freq["金"]["pct"]
    pct_water = freq["水"]["pct"]
    pct_fire = freq["火"]["pct"]
    pct_wood = freq["木"]["pct"]
    pct_earth = freq["土"]["pct"]

    if pct_metal + pct_water > 50:
        freq_interpretations.append("金+水 > 50%：实证+探索型，理性驱动")
    if pct_fire + pct_wood > 50:
        freq_interpretations.append("火+木 > 50%：创新+号召型，开拓驱动")
    if pct_earth > 30:
        freq_interpretations.append("土 > 30%：厚重综述型，文献驱动")

    # ================================================================
    # 维度二：三层×五行交叉矩阵
    # ================================================================
    matrix = []
    matrix_interpretations = []
    for i, ln in enumerate(layer_names):
        c = layer_matrix[ln]
        row = {"layer": ln, "total": layer_concept_counts[i],
               "wuxing": {wx: {"count": c.get(wx, 0),
                               "pct": round(c.get(wx, 0) / layer_concept_counts[i] * 100, 1)
                               if layer_concept_counts[i] > 0 else 0}
                          for wx in WX_ORDER}}
        row["dominant"] = max(c, key=c.get) if c else None
        matrix.append(row)

    for i, row in enumerate(matrix):
        for wx in WX_ORDER:
            cnt = row["wuxing"][wx]["count"]
            if cnt == 0:
                if i == 0 and wx == "木":
                    matrix_interpretations.append(f"{row['layer']}无木：不追新，从成熟问题出发")
                elif i == 1 and wx == "火":
                    matrix_interpretations.append(f"{row['layer']}无火：不煽情，靠证据不靠情绪")
                elif i == 2 and wx == "水":
                    matrix_interpretations.append(f"{row['layer']}无水：结论封闭，不留开放尾巴")
            if cnt >= max(row["wuxing"][w]["count"] for w in WX_ORDER) and cnt > 0:
                if i == 0 and wx == "金":
                    matrix_interpretations.append(f"{row['layer']}金密：问题的锐利界定")
                elif i == 1 and wx == "水":
                    matrix_interpretations.append(f"{row['layer']}水密：从流动中寻找答案")
                elif i == 2 and wx == "火":
                    matrix_interpretations.append(f"{row['layer']}火密：结论的传播号召")

    # ================================================================
    # 维度三：五行重心偏移路径
    # ================================================================
    path = []
    for i, row in enumerate(matrix):
        dom = row["dominant"]
        path.append(dom)

    path_edges = []
    sheng_count = 0
    ke_count = 0
    for i in range(len(path) - 1):
        a, b = path[i], path[i + 1]
        if SHENG.get(a) == b:
            path_edges.append({"from": a, "to": b, "relation": "相生", "desc": "逻辑自然推进"})
            sheng_count += 1
        elif KE.get(a) == b:
            path_edges.append({"from": a, "to": b, "relation": "相克", "desc": "范式翻转"})
            ke_count += 1
        else:
            path_edges.append({"from": a, "to": b, "relation": "中性", "desc": "平稳过渡"})

    path_profile = None
    if len(path) >= 3:
        path_tuple = tuple(path[:3])
        path_profile = PATH_PROFILES.get(path_tuple)

    if ke_count == 0 and sheng_count > 0:
        path_rhythm = "全程相生——顺滑推进"
    elif ke_count == 1:
        path_rhythm = "含一次相克——有转折感"
    elif ke_count >= 2:
        path_rhythm = "两次以上相克——跌宕起伏"
    else:
        path_rhythm = "全程中性——平稳"

    # ================================================================
    # 维度四：五行熵
    # ================================================================
    H = -sum((total.get(wx, 0) / N) * math.log2(total.get(wx, 0) / N)
             for wx in WX_ORDER if total.get(wx, 0) > 0)
    H_max = math.log2(5)
    entropy_ratio = H / H_max

    ent_thresholds = config.get("entropy_thresholds", {"high": 0.85, "low": 0.50})
    if H > 2.0:
        entropy_desc = "高度多元 · 跨学科综述风"
    elif H > 1.5:
        entropy_desc = "中等多元 · 深度分析风"
    else:
        entropy_desc = "单极聚焦 · 单一论点风"

    # ================================================================
    # 维度五：重心向量
    # ================================================================
    cx = sum(WX_COORD[wx][0] * total.get(wx, 0) for wx in WX_ORDER) / N
    cy = sum(WX_COORD[wx][1] * total.get(wx, 0) for wx in WX_ORDER) / N

    if abs(cx) < 0.2 and abs(cy) < 0.2:
        compass_desc = "重心居中 · 土德厚重 · 综合均衡"
    else:
        dirs = []
        if cx < -0.2: dirs.append("偏东(木)·生长开拓")
        if cx > 0.2: dirs.append("偏西(金)·精炼收敛")
        if cy < -0.2: dirs.append("偏南(火)·发散号召")
        if cy > 0.2: dirs.append("偏北(水)·流动探索")
        compass_desc = "重心 " + " · ".join(dirs)

    # ================================================================
    # 维度六：五行特质画像
    # ================================================================
    profile = []
    for wx in WX_ORDER:
        role, role_desc = WX_ROLES[wx]
        profile.append({
            "wuxing": wx,
            "role": role,
            "role_desc": role_desc,
            "count": total.get(wx, 0),
            "pct": round(total.get(wx, 0) / N * 100, 1),
        })

    # ================================================================
    # 维度七：一句话风格判语
    # ================================================================
    top2 = sorted(total.items(), key=lambda x: -x[1])[:2]
    first, second = top2[0][0], top2[1][0] if len(top2) > 1 else first

    if path_profile:
        summary = f"「{path_profile[1]}」—— {path_profile[0]}"
    elif ke_count >= 1:
        summary = f"「{path[0]}藏{path[-1]}涌」—— 从{path[0]}性基础中翻转，最终以{path[-1]}性为归宿"
    else:
        summary = f"「{first}领{second}辅」—— {WX_ROLES[first][1]}为主，{WX_ROLES[second][1]}为辅"

    if entropy_ratio < ent_thresholds["low"]:
        summary += " · 单极聚焦"
    elif entropy_ratio > ent_thresholds["high"]:
        summary += " · 高度多元"

    # ================================================================
    # 维度八（新增）：认知深度画像
    # ================================================================
    depth_profile = {}
    if depth_dist:
        total_depth_concepts = sum(depth_dist.values())
        for d in DEPTH_LEVELS:
            cnt = depth_dist.get(d, 0)
            depth_profile[d] = {
                "label": DEPTH_LABELS[d],
                "emoji": DEPTH_EMOJI[d],
                "count": cnt,
                "pct": round(cnt / total_depth_concepts * 100, 1) if total_depth_concepts > 0 else 0,
                "weight": DEPTH_WEIGHTS[d],
            }

    # 深度×五行交叉矩阵
    depth_wx_matrix = {}
    for d in DEPTH_LEVELS:
        if d in depth_layer_matrices and depth_layer_matrices[d]:
            depth_wx_matrix[d] = {}
            for ln, c in depth_layer_matrices[d].items():
                depth_wx_matrix[d][ln] = {wx: c.get(wx, 0) for wx in WX_ORDER}

    return {
        "file": None,
        "N": N,
        "N_raw": N_raw,
        "depth": depth,
        "layer_names": layer_names,
        "depth_profile": depth_profile,
        "depth_wx_matrix": depth_wx_matrix,
        "dim1_freq": freq,
        "dim1_interpretations": freq_interpretations,
        "dim2_matrix": matrix,
        "dim2_interpretations": matrix_interpretations,
        "dim3_path": path,
        "dim3_edges": path_edges,
        "dim3_rhythm": path_rhythm,
        "dim3_profile": path_profile,
        "dim4_entropy": {"H": round(H, 3), "H_max": round(H_max, 3),
                         "ratio": round(entropy_ratio, 3), "desc": entropy_desc},
        "dim5_compass": {"cx": round(cx, 3), "cy": round(cy, 3), "desc": compass_desc},
        "dim6_profile": profile,
        "dim7_summary": summary,
    }


def print_depth_profile(r):
    """打印认知深度画像"""
    if not r.get("depth_profile"):
        return
    print()
    print("  ── 认知深度画像（新增维度）──")
    print(f"    深度分布:")
    for d in DEPTH_LEVELS:
        dp = r["depth_profile"].get(d)
        if dp and dp["count"] > 0:
            bar = "█" * dp["count"] + "░" * (max(1, r["N_raw"] // 2 - dp["count"]))
            print(f"    {dp['emoji']} {d} {dp['label']:<12s}  {bar}  {dp['pct']:5.1f}%  ({dp['count']}/{r['N_raw']})  权重: {dp['weight']:.0f}x")
    print(f"    深度加权后概念数: {r['N']}（原始: {r['N_raw']}）")


def print_depth_wx_matrix(r):
    """打印深度×五行交叉矩阵"""
    dwm = r.get("depth_wx_matrix", {})
    if not dwm:
        return
    has_any = False
    for d in DEPTH_LEVELS:
        if d in dwm and dwm[d]:
            has_any = True
            break
    if not has_any:
        return

    print()
    print("  ── 深度×五行交叉矩阵 ──")
    for d in DEPTH_LEVELS:
        if d not in dwm or not dwm[d]:
            continue
        print(f"    {DEPTH_EMOJI[d]} {d} {DEPTH_LABELS[d]}:")
        for ln, wx_counts in dwm[d].items():
            line = f"      {ln:12s}"
            for wx in WX_ORDER:
                line += f" {wx}={wx_counts.get(wx, 0):>2d}"
            print(line)


def print_report(r):
    """打印完整诊断报告"""
    depth_tag = f" [深度: {r['depth']}]" if r.get("depth") else ""
    print("=" * 72)
    print(f"  🧬 {r['file']}{depth_tag}")
    print(f"     概念总数: {r['N']}  |  层数: {len(r['layer_names'])}")
    if r.get("N_raw") and r["N_raw"] != r["N"]:
        print(f"     （原始概念: {r['N_raw']}，深度加权: {r['N']}）")
    print()

    # 维度八（新增）：认知深度画像
    print_depth_profile(r)

    # 维度一
    print("  ── 一、五行总体频次分布 ──")
    bar_width = 30
    for wx in WX_ORDER:
        f = r["dim1_freq"][wx]
        bar = "█" * int(f["pct"] / 100 * bar_width) + "░" * (bar_width - int(f["pct"] / 100 * bar_width))
        print(f"    {wx}  {bar}  {f['pct']:5.1f}%  ({f['count']}个)")
    for interp in r["dim1_interpretations"]:
        print(f"    → {interp}")

    # 维度二
    print()
    print("  ── 二、三层×五行交叉矩阵 ──")
    header = f"    {'':12s}"
    for wx in WX_ORDER:
        header += f" {wx:>5s}"
    print(header)
    for row in r["dim2_matrix"]:
        line = f"    {row['layer']:12s}"
        for wx in WX_ORDER:
            line += f" {row['wuxing'][wx]['count']:>5d}"
        print(line)
    if r["dim2_interpretations"]:
        for interp in r["dim2_interpretations"]:
            print(f"    → {interp}")

    # 维度三
    print()
    print("  ── 三、五行重心偏移路径 ──")
    print(f"    路径: {' → '.join(r['dim3_path'])}")
    for edge in r["dim3_edges"]:
        tag = {"相生": "✅", "相克": "⚡", "中性": "➖"}[edge["relation"]]
        print(f"      {edge['from']} → {edge['to']}  {tag} {edge['relation']}（{edge['desc']}）")
    print(f"    节奏: {r['dim3_rhythm']}")
    if r["dim3_profile"]:
        desc, ptype = r["dim3_profile"]
        print(f"    画像: {ptype} —— {desc}")

    # 维度四
    print()
    print("  ── 四、五行熵 · 思维多样性 ──")
    e = r["dim4_entropy"]
    print(f"    H = {e['H']} / {e['H_max']}  ({e['ratio']*100:.0f}%)  |  {e['desc']}")

    # 维度五
    print()
    print("  ── 五、重心方位 · 思想坐标 ──")
    c = r["dim5_compass"]
    print(f"    质心: ({c['cx']}, {c['cy']})  |  {c['desc']}")

    # 维度六
    print()
    print("  ── 六、五行特质画像 ──")
    for p in r["dim6_profile"]:
        bar = "█" * p["count"] + "░" * (r["N"] - p["count"]) if r["N"] <= 30 else "█" * int(p["pct"] / 100 * 20)
        print(f"    {p['wuxing']} {p['role']:4s}  {bar}  {p['pct']:5.1f}%  ({p['count']}/{r['N']})  {p['role_desc']}")

    # 维度七
    print()
    print("  ── 七、一句话风格判语 ──")
    print(f"    {r['dim7_summary']}")

    # 深度×五行矩阵
    print_depth_wx_matrix(r)

    print()


def print_depth_compare(results_a, results_b, label_a, label_b):
    """打印两个深度/文件之间的差异对比"""
    valid_a = [r for r in results_a if "error" not in r]
    valid_b = [r for r in results_b if "error" not in r]
    if not valid_a or not valid_b:
        return

    ra, rb = valid_a[0], valid_b[0]

    print("\n" + "=" * 72)
    print(f"  🔬 深度差异对比: {label_a} vs {label_b}")
    print()

    # 五行频次对比
    print(f"  {'五行':<4s} {'':>6s}{label_a:<15s} {'':>6s}{label_b:<15s} {'差异':>8s}")
    print(f"  {'-'*4} {'-'*6} {'-'*15} {'-'*6} {'-'*15} {'-'*8}")
    for wx in WX_ORDER:
        fa = ra["dim1_freq"][wx]
        fb = rb["dim1_freq"][wx]
        diff = fa["pct"] - fb["pct"]
        sign = "+" if diff > 0 else ""
        bar_a = "█" * int(fa["pct"] / 100 * 15)
        bar_b = "█" * int(fb["pct"] / 100 * 15)
        print(f"  {wx:<4s} {bar_a:<15s} {fa['pct']:5.1f}%  {bar_b:<15s} {fb['pct']:5.1f}%  {sign}{diff:+.1f}%")

    # 路径对比
    print()
    print(f"  路径:  {label_a}: {'→'.join(ra['dim3_path']):<12s}  {label_b}: {'→'.join(rb['dim3_path']):<12s}")

    # 熵值对比
    ea, eb = ra["dim4_entropy"], rb["dim4_entropy"]
    print(f"  熵值:  {label_a}: {ea['H']:.3f} ({ea['ratio']*100:.0f}%)  {label_b}: {eb['H']:.3f} ({eb['ratio']*100:.0f}%)")

    # 重心对比
    ca, cb = ra["dim5_compass"], rb["dim5_compass"]
    print(f"  重心:  {label_a}: ({ca['cx']:.2f},{ca['cy']:.2f})  {label_b}: ({cb['cx']:.2f},{cb['cy']:.2f})")

    # 判语对比
    print(f"  判语:  {label_a}: {ra['dim7_summary']}")
    print(f"         {label_b}: {rb['dim7_summary']}")

    # 解释差异来源
    print()
    print("  ── 差异解读 ──")
    if ra.get("depth") and rb.get("depth"):
        print(f"    认知深度不同: {label_a} 以 {DEPTH_LABELS[ra['depth']]} 解读，{label_b} 以 {DEPTH_LABELS[rb['depth']]} 解读")
        print(f"    深层解读倾向于揭示更多元的思维维度，浅层解读更贴近原文字面义")
    print()


def print_compare_table(results):
    """打印对比表"""
    valid = [r for r in results if "error" not in r]
    if len(valid) < 2:
        return

    print("\n" + "=" * 72)
    print("  📊 多篇文章对比")
    print()
    header = f"  {'文件':<28s} {'N':>3s} {'深度':>4s} {'路径':<12s} {'熵':>5s} {'重心':>13s} {'判语'}"
    print(header)
    print(f"  {'-'*28} {'-'*3} {'-'*4} {'-'*12} {'-'*5} {'-'*13} {'-'*30}")
    for r in valid:
        name = r["file"][:26]
        path_str = "→".join(r["dim3_path"])
        ent = r["dim4_entropy"]["H"]
        c = r["dim5_compass"]
        comp = f"({c['cx']:.2f},{c['cy']:.2f})"
        summary = r["dim7_summary"][:30]
        d_tag = r.get("depth", "all") if r.get("depth") else "all"
        print(f"  {name:<28s} {r['N']:>3d} {d_tag:>4s} {path_str:<12s} {ent:>5.2f} {comp:>13s} {summary}")
    print()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="概念地图五行诊断器 v2.0 · 认知深度感知版")
    parser.add_argument("target", help="JSON 文件或目录路径")
    parser.add_argument("--target2", help="第二个 JSON 文件（用于深度对比）")
    parser.add_argument("--depth", choices=["L1", "L2", "L3", "L4", "all"], default=None,
                        help="按认知深度筛选（L1=白话, L2=精读, L3=应用, L4=学术）")
    parser.add_argument("--config", default=None, help="权重配置文件路径（JSON 格式）")
    parser.add_argument("--depth-profile", action="store_true", help="展示各深度的五行分布")
    parser.add_argument("--depth-compare", action="store_true", help="两文件/两深度差异对比")
    parser.add_argument("--compare", action="store_true", help="多文件对比模式")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    args = parser.parse_args()

    # 加载配置
    config = load_config(args.config)

    # 深度对比模式：两个文件
    if args.target2 and args.depth_compare:
        data_a = load_json(args.target)
        data_b = load_json(args.target2)
        r_a = diagnose(data_a, args.depth, config)
        r_a["file"] = os.path.basename(args.target)
        r_b = diagnose(data_b, args.depth, config)
        r_b["file"] = os.path.basename(args.target2)
        print_report(r_a)
        print_report(r_b)
        print_depth_compare([r_a], [r_b],
                            os.path.basename(args.target),
                            os.path.basename(args.target2))
        return

    # 深度对比模式：同一文件不同深度
    if args.depth_compare and args.depth:
        data = load_json(args.target)
        results = []
        for d in DEPTH_LEVELS:
            r = diagnose(data, d)
            r["file"] = os.path.basename(args.target)
            results.append(r)
        for r in results:
            print_report(r)
        # 对比 L1 vs L4
        print_depth_compare(results[:1], results[3:],
                            f"{DEPTH_EMOJI['L1']} L1 {DEPTH_LABELS['L1']}",
                            f"{DEPTH_EMOJI['L4']} L4 {DEPTH_LABELS['L4']}")
        return

    # 常规模式
    target = args.target
    results = []

    if os.path.isfile(target):
        data = load_json(target)
        r = diagnose(data, args.depth)
        r["file"] = os.path.basename(target)
        results.append(r)
    elif os.path.isdir(target):
        json_files = sorted(Path(target).glob("*.json"))
        if not json_files:
            print(f"目录 {target} 中没有找到 JSON 文件")
            sys.exit(1)
        for f in json_files:
            try:
                data = load_json(str(f))
                r = diagnose(data, args.depth)
                r["file"] = f.name
                results.append(r)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                results.append({"file": f.name, "error": str(e), "N": 0})
    else:
        print(f"路径不存在: {target}")
        sys.exit(1)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    for r in results:
        if "error" in r:
            print(f"  ⚠ {r['file']}: 解析失败 ({r['error']})")
            print()
        else:
            print_report(r)

    if args.compare or len(results) > 1:
        print_compare_table(results)


if __name__ == "__main__":
    main()