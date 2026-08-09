"""壳核画像分化综合分析脚本

输入：四源树文件（baai/arxiv/github/hf）
输出：壳核画像分化分析数据（JSON），供报告撰写使用
"""

import json
import math
import statistics
from collections import defaultdict, Counter
from pathlib import Path

WX_ORDER = ["木", "火", "土", "金", "水"]
SOURCES = ["baai", "arxiv", "github", "huggingface"]

# v1.1_calibrated 权重（草案，待真实引擎复核）
V1_1_WEIGHTS = {"O_t": 0.1939, "E_u": 0.6123, "C_k": 0.1939, "K_y": 0.0}

# 四源生态层定义
LAYER_DEF = {
    "baai": {"layer": "规划层（壳）", "role": "机构'应该做什么'"},
    "arxiv": {"layer": "产出层（核）", "role": "研究者'实际在做什么'"},
    "github": {"layer": "工程层", "role": "开发者'在构建什么'"},
    "huggingface": {"layer": "模型层", "role": "模型'被部署什么'"},
}


def load_tree(source, month_short):
    """加载树文件"""
    month_map = {
        "05": "202605", "06": "202606", "07": "202607", "08": "202608"
    }
    prefix = {
        "baai": "baai_tree", "arxiv": "arxiv_ai_tree",
        "github": "github_tree", "huggingface": "hf_tree",
    }
    fname = month_map.get(month_short, f"2026{month_short}")
    path = Path(f"../output/{prefix[source]}_{fname}.json")
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def compute_wuxing_dist(nodes):
    """计算五行分布"""
    total = sum(n.get("weight", 0) for n in nodes)
    if total == 0:
        return {w: 0.0 for w in WX_ORDER}, 0
    wx = Counter()
    for n in nodes:
        wx[n.get("wuxing", "?")] += n.get("weight", 0)
    dist = {w: wx.get(w, 0) / total for w in WX_ORDER}
    return dist, total


def compute_entropy(dist):
    """计算归一化熵"""
    probs = [dist[w] for w in WX_ORDER]
    H = sum(-p * math.log2(p) for p in probs if p > 0)
    H_max = math.log2(5)
    return H / H_max if H_max > 0 else 0


def compute_S_p_v1_1(O_t, E_u, C_k, K_y):
    """v1.1_calibrated 加权 S_p"""
    dims = {"O_t": O_t, "E_u": E_u, "C_k": C_k, "K_y": K_y}
    p = 0.5
    w_sum = sum(V1_1_WEIGHTS.values())
    s_sum = sum(V1_1_WEIGHTS[d] * (dim ** p) for d, dim in dims.items()) / w_sum
    return round((s_sum ** (1 / p)) * 100, 2)


def compute_cosine_sim(d1, d2):
    """五行分布余弦相似度"""
    v1 = [d1[w] for w in WX_ORDER]
    v2 = [d2[w] for w in WX_ORDER]
    dot = sum(a * b for a, b in zip(v1, v2))
    n1 = math.sqrt(sum(a * a for a in v1))
    n2 = math.sqrt(sum(b * b for b in v2))
    if n1 == 0 or n2 == 0:
        return 0.0
    return dot / (n1 * n2)


def compute_l1_divergence(d1, d2):
    """L1 散度（总变异距离）"""
    return sum(abs(d1[w] - d2[w]) for w in WX_ORDER) / 2


def main():
    print("=" * 72)
    print("壳核画像分化综合分析")
    print("=" * 72)

    # ========== 1. 逐源逐月五行分布 ==========
    print("\n## 1. 逐源逐月五行分布")
    records = {}
    for source in SOURCES:
        records[source] = {}
        for month_short in ["05", "06", "07", "08"]:
            tree = load_tree(source, month_short)
            if tree is None:
                continue
            dist, total = compute_wuxing_dist(tree["nodes"])
            dominant = max(WX_ORDER, key=lambda w: dist[w])
            H_norm = compute_entropy(dist)
            E_u = round(1 - H_norm, 4)
            O_t = round(dist[dominant], 4)

            # 打印
            parts = "  ".join(f"{w}:{dist[w]*100:.1f}%" for w in WX_ORDER)
            print(f"  {source} {month_short}月  total={total:>6d}  dominant={dominant}  "
                  f"O_t={O_t}  E_u={E_u}")
            print(f"    分布: {parts}")

            records[source][month_short] = {
                "dist": {w: round(dist[w], 4) for w in WX_ORDER},
                "total": total, "dominant": dominant,
                "O_t": O_t, "E_u": E_u, "n_nodes": len(tree["nodes"]),
            }

    # ========== 2. 壳核画像分化核心指标 ==========
    print("\n## 2. 壳核画像分化核心指标")

    shell_months = [m for m in ["05", "06", "07"] if m in records["baai"]]
    nucleus_months = [m for m in ["06", "07", "08"] if m in records["arxiv"]]

    # 壳核均值分布
    shell_avg = {w: statistics.mean(records["baai"][m]["dist"][w] for m in shell_months)
                 for w in WX_ORDER}
    nucleus_avg = {w: statistics.mean(records["arxiv"][m]["dist"][w] for m in nucleus_months)
                   for w in WX_ORDER}

    print("\n  壳核均值五行分布:")
    print(f"  壳（BAAI）: {'  '.join(f'{w}:{shell_avg[w]*100:.1f}%' for w in WX_ORDER)}")
    print(f"  核（arXiv）: {'  '.join(f'{w}:{nucleus_avg[w]*100:.1f}%' for w in WX_ORDER)}")

    # 差异量化
    diffs = {w: nucleus_avg[w] - shell_avg[w] for w in WX_ORDER}
    print("\n  五行差异（核-壳，pp）:")
    for w in WX_ORDER:
        direction = "核高" if diffs[w] > 0 else "壳高"
        sig = "***" if abs(diffs[w]) > 0.1 else ("**" if abs(diffs[w]) > 0.05 else "*")
        print(f"    {w}: {diffs[w]*100:+.1f}pp ({direction}) {sig}")

    # 余弦相似度
    cos_sim = compute_cosine_sim(shell_avg, nucleus_avg)
    l1_div = compute_l1_divergence(shell_avg, nucleus_avg)
    print(f"\n  壳核肖像相似度: 余弦={cos_sim:.4f}  L1={l1_div:.4f}")

    # ========== 3. 四层生态水梯度 ==========
    print("\n## 3. 四层生态水梯度")

    # 取各源可用月份
    source_months = {
        "baai": ["06", "07"],
        "arxiv": ["06", "07", "08"],
        "github": ["06", "07"],
        "huggingface": ["06", "07"],
    }

    layers = []
    for source in SOURCES:
        months = [m for m in source_months[source] if m in records[source]]
        if not months:
            continue
        water_vals = [records[source][m]["dist"]["水"] for m in months]
        water_avg = statistics.mean(water_vals)
        S_p_vals = []
        for m in months:
            r = records[source][m]
            sp = compute_S_p_v1_1(r["O_t"], r["E_u"], r["O_t"], 1.0)
            S_p_vals.append(sp)
        S_p_avg = statistics.mean(S_p_vals)

        dist_avg = {w: statistics.mean(records[source][m]["dist"][w] for m in months)
                    for w in WX_ORDER}
        layers.append({
            "source": source, "layer": LAYER_DEF[source]["layer"],
            "role": LAYER_DEF[source]["role"],
            "water": round(water_avg * 100, 1),
            "S_p_v1_1": round(S_p_avg, 1),
            "dist": {w: round(dist_avg[w] * 100, 1) for w in WX_ORDER},
            "dominant": max(WX_ORDER, key=lambda w: dist_avg[w]),
        })

    print(f"  {'层':<10} {'水%':<8} {'S_p(v1.1)':<10} {'主导':<6} {'画像'}")
    for l in layers:
        dist_str = "  ".join(f"{w}:{l['dist'][w]}%" for w in WX_ORDER)
        print(f"  {l['layer']:<10} {l['water']:<8} {l['S_p_v1_1']:<10} {l['dominant']:<6} {dist_str}")

    # 水梯度
    water_gradient = [l["water"] for l in layers]
    grad_str = " → ".join(l["layer"] + "(" + str(l["water"]) + "%)" for l in layers)
    print(f"\n  水梯度: {grad_str}")
    print(f"  壳→核跃变: {water_gradient[0] - water_gradient[1]:.1f}pp")
    print(f"  核→工程跃变: {water_gradient[2] - water_gradient[1]:.1f}pp")
    print(f"  工程→模型跃变: {water_gradient[3] - water_gradient[2]:.1f}pp")

    # ========== 4. 壳核节点级归因 ==========
    print("\n## 4. 壳核节点级归因")

    for source, label in [("baai", "壳（BAAI）"), ("arxiv", "核（arXiv）")]:
        print(f"\n  {label} 水元素节点明细:")
        months = shell_months if source == "baai" else nucleus_months
        for m in months:
            tree = load_tree(source, m)
            if tree is None:
                continue
            water_nodes = [(n["name"], n.get("weight", 0))
                          for n in tree["nodes"] if n.get("wuxing") == "水"]
            water_total = sum(w for _, w in water_nodes)
            total = sum(n.get("weight", 0) for n in tree["nodes"])
            print(f"    {m}月: 水节点={len(water_nodes)} 水总量={water_total} "
                  f"占比={water_total/total*100:.1f}%")
            for name, w in sorted(water_nodes, key=lambda x: -x[1]):
                print(f"      {name}: {w}")

    # ========== 5. 壳核相位差分析 ==========
    print("\n## 5. 壳核相位差分析")

    # 逐月壳核差异
    common_months = [m for m in ["06", "07"] if m in records["baai"] and m in records["arxiv"]]
    print(f"\n  共有时段: {common_months}")
    for m in common_months:
        shell_dist = records["baai"][m]["dist"]
        nucleus_dist = records["arxiv"][m]["dist"]
        l1 = compute_l1_divergence(shell_dist, nucleus_dist)
        cos = compute_cosine_sim(shell_dist, nucleus_dist)
        print(f"  {m}月: L1={l1:.4f}  cos={cos:.4f}  "
              f"水差={shell_dist['水']-nucleus_dist['水']:.1%}  "
              f"火差={nucleus_dist['火']-shell_dist['火']:.1%}")

    # ========== 6. 输出 JSON ==========
    output = {
        "generated": "2026-08-09",
        "shell_nucleus": {
            "shell_avg": {w: round(shell_avg[w], 4) for w in WX_ORDER},
            "nucleus_avg": {w: round(nucleus_avg[w], 4) for w in WX_ORDER},
            "diffs": {w: round(diffs[w], 4) for w in WX_ORDER},
            "cosine_similarity": round(cos_sim, 4),
            "l1_divergence": round(l1_div, 4),
        },
        "four_layer": layers,
        "monthly_records": {
            source: {m: {k: v for k, v in rec.items() if k != "dist"}
                    for m, rec in source_recs.items()}
            for source, source_recs in records.items()
        },
    }

    out_path = Path("../output/shell_nucleus_analysis.json")
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[输出] {out_path}")

    print("\n" + "=" * 72)
    print("分析完成")
    print("=" * 72)


if __name__ == "__main__":
    main()