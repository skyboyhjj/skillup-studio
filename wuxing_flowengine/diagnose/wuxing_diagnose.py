#!/usr/bin/env python3
"""
概念地图五行诊断器 · 通用版
对齐「五行诊断框架设计方案 v1.0」七维指标体系
用法: python wuxing_diagnose.py <json文件或目录> [--json] [--compare]
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


def extract_layer_name(ring_label):
    """从 ring label 提取短层名，如 '种子层 · 千年追问' → '种子层'"""
    for sep in ["·", "：", ":", " "]:
        if sep in ring_label:
            return ring_label.split(sep)[0].strip()
    return ring_label.strip()


def diagnose(data):
    """对单个概念地图执行七维诊断"""
    rings = data if isinstance(data, list) else data.get("rings", [])
    n_layers = len(rings)

    # 收集所有概念 + 层信息
    all_concepts = []
    layer_names = []
    layer_matrix = {}  # {layer_name: Counter(wuxing)}
    layer_concept_counts = []

    for ring in rings:
        ln = extract_layer_name(ring["label"])
        layer_names.append(ln)
        concepts = ring.get("concepts", [])
        layer_concept_counts.append(len(concepts))
        c = Counter()
        for con in concepts:
            wx = con.get("wuxing", "?")
            c[wx] += 1
            all_concepts.append(wx)
        layer_matrix[ln] = c

    total = Counter(all_concepts)
    N = sum(total.values())
    if N == 0:
        return {"error": "无概念节点"}

    # ================================================================
    # 维度一：五行总体频次分布
    # ================================================================
    freq = {wx: {"count": total.get(wx, 0), "pct": round(total.get(wx, 0) / N * 100, 1)}
            for wx in WX_ORDER}

    # 组合判读
    freq_interpretations = []
    for wx in WX_ORDER:
        pct = freq[wx]["pct"]
        if pct > 30:
            freq_interpretations.append(f"{wx}性主导（{pct}%），文章核心发力点")
        elif pct < 10:
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

    # 矩阵解读
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

    # 生克匹配
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

    # 路径画像匹配
    path_profile = None
    if len(path) >= 3:
        path_tuple = tuple(path[:3])
        path_profile = PATH_PROFILES.get(path_tuple)

    # 路径节奏
    if ke_count == 0 and sheng_count > 0:
        path_rhythm = "全程相生——顺滑推进"
    elif ke_count == 1:
        path_rhythm = "含一次相克——有转折感"
    elif ke_count >= 2:
        path_rhythm = "两次以上相克——跌宕起伏"
    else:
        path_rhythm = "全程中性——平稳"

    # ================================================================
    # 维度四：五行熵（Shannon 熵）
    # ================================================================
    H = -sum((total.get(wx, 0) / N) * math.log2(total.get(wx, 0) / N)
             for wx in WX_ORDER if total.get(wx, 0) > 0)
    H_max = math.log2(5)  # ≈ 2.322
    entropy_ratio = H / H_max

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
        profile_desc, profile_type = path_profile
        summary = f"「{path_profile[1]}」—— {profile_desc}"
    elif ke_count >= 1:
        # 有相克→范式翻转型
        summary = f"「{path[0]}藏{path[-1]}涌」—— 从{path[0]}性基础中翻转，最终以{path[-1]}性为归宿"
    else:
        summary = f"「{first}领{second}辅」—— {WX_ROLES[first][1]}为主，{WX_ROLES[second][1]}为辅"

    # 熵值修正
    if entropy_ratio < 0.5:
        summary += " · 单极聚焦"
    elif entropy_ratio > 0.85:
        summary += " · 高度多元"

    return {
        "file": None,  # 由调用者填充
        "N": N,
        "layer_names": layer_names,
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


def print_report(r):
    """打印完整诊断报告"""
    print("=" * 72)
    print(f"  🧬 {r['file']}")
    print(f"     概念总数: {r['N']}  |  层数: {len(r['layer_names'])}")
    print()

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
    print()


def print_compare_table(results):
    """打印对比表"""
    valid = [r for r in results if "error" not in r]
    if len(valid) < 2:
        return

    print("\n" + "=" * 72)
    print("  📊 多篇文章对比")
    print()
    header = f"  {'文件':<28s} {'N':>3s} {'路径':<12s} {'熵':>5s} {'重心':>13s} {'判语'}"
    print(header)
    print(f"  {'-'*28} {'-'*3} {'-'*12} {'-'*5} {'-'*13} {'-'*30}")
    for r in valid:
        name = r["file"][:26]
        path_str = "→".join(r["dim3_path"])
        ent = r["dim4_entropy"]["H"]
        c = r["dim5_compass"]
        comp = f"({c['cx']:.2f},{c['cy']:.2f})"
        summary = r["dim7_summary"][:30]
        print(f"  {name:<28s} {r['N']:>3d} {path_str:<12s} {ent:>5.2f} {comp:>13s} {summary}")
    print()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="概念地图五行诊断器")
    parser.add_argument("target", help="JSON 文件或目录路径")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式（供仪表盘消费）")
    parser.add_argument("--compare", action="store_true", help="多文件对比模式")
    args = parser.parse_args()

    target = args.target
    results = []

    if os.path.isfile(target):
        data = load_json(target)
        r = diagnose(data)
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
                r = diagnose(data)
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