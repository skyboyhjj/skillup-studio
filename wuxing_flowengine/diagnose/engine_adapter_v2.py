#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EngineAdapterV2 —— 真实引擎接入适配层（P0-1）
===============================================
将四源单层树文件适配为 wuxing_diagnose_v2 的三层 rings 结构（时间演化模式），
并解决 fallback 三大问题：
  1. C_k ≡ O_t 共线  →  C_k 改为"演化耦合度"（基于 v2 dim3 生克边）
  2. K_y = 1.0 零区分 →  k_y_enhancer（火/土权重 + E_relation）
  3. E_u 低值        →  E_u 自算（1-H_norm, weight 加权）+ v2_extra 补充维度

时间演化模式（方案 A）：
  最早月 → 种子层（规划之始）
  中间月 → 现行层（当前状态）
  最近月 → 超越层（最新演化）
  dim3 生克边 = "主导行如何演化"：相生边=顺畅演进（种子生现行），相克边=张力转折

引擎纯净原则：不改 wuxing_diagnose_v2 源码（config 为死参数，系数在适配层实现）。

用法（置于树文件目录）：
  python engine_adapter_v2.py                    # 全源诊断（arXiv 默认 + 所有可用源）
  python engine_adapter_v2.py --source arxiv     # 指定源
  python engine_adapter_v2.py --dir ./output     # 指定树文件目录
"""

import argparse
import glob
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from wuxing_diagnose_v2 import diagnose as v2_diagnose

# 五行标注（与 merge_and_calibrate.py 同源 canonical）
CANONICAL_WUXING = {
    "cs.AI": "火", "cs.LG": "土", "cs.CL": "水", "cs.CV": "木",
    "cs.NE": "水", "cs.MA": "木", "cs.RO": "金", "cs.HC": "火",
    "cs.IR": "金", "cs.MM": "火", "stat.ML": "土",
    "LLM": "水", "NLP": "水", "计算机视觉": "木", "CV": "木",
}
TOPIC_WUXING = {
    "llm": "水", "large-language-models": "水",
    "machine-learning": "土", "deep-learning": "土",
    "natural-language-processing": "水", "computer-vision": "木",
    "reinforcement-learning": "火", "multimodal": "火",
    "agents": "木", "autonomous-agents": "木",
    "retrieval-augmented-generation": "金",
    "graph-neural-network": "金", "federated-learning": "金",
    "robotics": "金",
    "text-generation": "水", "text-classification": "水",
    "token-classification": "水", "question-answering": "水",
    "summarization": "水", "translation": "水",
    "image-classification": "木", "image-text-to-text": "火",
    "text-to-image": "木", "automatic-speech-recognition": "水",
    "text-to-text": "水",
}
WUXING_ORDER = ["木", "火", "土", "金", "水"]
SOURCE_GLOBS = {
    "baai": "knowledge_tree_*.json",
    "arxiv": "ai_tree_*.json",
    "github": "github_tree_*.json",
    "huggingface": "hf_tree_*.json",
}
LAYER_LABELS = ["种子层", "现行层", "超越层"]
DEFAULT_BETA = 0.5  # E_relation 中 ke_density 的权重


def extract_month(filename: str) -> str:
    """从文件名提取 YYYY-MM"""
    m = re.search(r"(\d{4})-(\d{2})", filename)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    m2 = re.search(r"(\d{6})", filename)
    if m2:
        s = m2.group(1)
        return f"{s[:4]}-{s[4:]}"
    return "unknown"


def entropy(p_list):
    H = 0.0
    for p in p_list:
        if p > 0:
            H -= p * math.log2(p)
    return H


def k_y_enhancer(wuxing_dist, edges, dim4_ratio, beta=DEFAULT_BETA):
    """K_y 增强：K_y = w_火×0.4 + w_土×0.3 + E_relation×0.3

    E_relation = β×ke_density + (1-β)×graph_cohesion
      - ke_density  = 生克边密度（dim3_edges 数 / 最大边数 2）
      - graph_cohesion = 层间重合度（v2 dim4.ratio）
    """
    w_huo = wuxing_dist.get("火", 0.0)
    w_tu = wuxing_dist.get("土", 0.0)
    max_edges = 2  # 三层最多 2 条边
    ke_density = min(1.0, len(edges) / max_edges)
    graph_cohesion = dim4_ratio if dim4_ratio is not None else 0.0
    e_relation = beta * ke_density + (1 - beta) * graph_cohesion
    k_y = w_huo * 0.4 + w_tu * 0.3 + e_relation * 0.3
    return round(k_y, 4), round(e_relation, 4)


def fallback_diagnose(nodes, canonical, topic):
    """fallback 诊断（对照基准——与原 merge_and_calibrate 完全一致）"""
    for n in nodes:
        w = n.get("wuxing")
        if not w:
            cid = str(n.get("id", ""))
            name = str(n.get("name", ""))
            w = canonical.get(cid)
            if not w:
                key = name if name else cid.split(":", 1)[-1]
                w = topic.get(key, "土")
            n["wuxing"] = w
    total = sum(n.get("weight", 1) for n in nodes) or 1
    wuxing_weight = defaultdict(int)
    for n in nodes:
        wuxing_weight[n.get("wuxing", "土")] += n.get("weight", 1)
    dist = {w: wuxing_weight.get(w, 0) / total for w in WUXING_ORDER}
    probs = [dist[w] for w in WUXING_ORDER]
    H = entropy(probs)
    H_max = entropy([0.2] * 5)
    H_norm = H / H_max if H_max > 0 else 0
    dominant = max(WUXING_ORDER, key=lambda w: dist[w])
    n_cat = len(nodes)
    O_t = round(dist[dominant], 4)
    E_u = round(1 - H_norm, 4)
    C_k = round(dist[dominant], 4)  # fallback：= O_t（共线缺陷）
    K_y = round(min(1.0, n_cat / 11.0), 4)
    dims = [O_t, E_u, C_k, K_y]
    p = 0.5
    s_sum = sum(d ** p for d in dims) / len(dims)
    S_p = round((s_sum ** (1 / p)) * 100, 2)
    return {"four_dims": {"O_t": O_t, "E_u": E_u, "C_k": C_k, "K_y": K_y},
            "S_p": S_p, "dominant": dominant, "n_nodes": n_cat}


class EngineAdapterV2:
    """真实引擎适配层：单源多月 → 时间演化三层 → v2 诊断 → 四维指标"""

    def __init__(self, canonical=None, topic=None, beta=DEFAULT_BETA):
        self.canonical = canonical or CANONICAL_WUXING
        self.topic = topic or TOPIC_WUXING
        self.beta = beta

    # ---------- 采集 ----------
    def load_series(self, directory, source):
        """读单源树文件 → {month: nodes}（按月份升序）"""
        pattern = SOURCE_GLOBS[source]
        series = {}
        for f in sorted(glob.glob(str(Path(directory) / pattern))):
            month = extract_month(f)
            try:
                tree = json.loads(Path(f).read_text(encoding="utf-8"))
                series[month] = tree.get("nodes", [])
            except Exception as e:
                print(f"  ⚠️ 读取失败 {f}: {e}")
        return series

    # ---------- 标注与展开 ----------
    def annotate(self, nodes):
        """节点五行标注（节点自带 → canonical → topic → 土默认）"""
        for n in nodes:
            w = n.get("wuxing")
            if not w:
                cid = str(n.get("id", ""))
                name = str(n.get("name", ""))
                w = self.canonical.get(cid)
                if not w:
                    key = name if name else cid.split(":", 1)[-1]
                    w = self.topic.get(key, "土")
                n["wuxing"] = w
        return nodes

    @staticmethod
    def expand_nodes(nodes):
        """weight 归一化展开 → 轻量概念列表（解决 v2 等权计数缺陷）

        v2 引擎 _count_layer_wx 是等权计数（+1），不感知 weight。
        将每个节点按 weight 展开为 {'wuxing': X} 轻量概念，
        使引擎统计等价于 weight 加权。arXiv 月 ~1.3 万 / HF ~2.5 万，
        纯 Counter 操作，毫秒级。
        """
        concepts = []
        for n in nodes:
            w = n.get("wuxing", "土")
            weight = int(n.get("weight", 1) or 1)
            # weight 可能带小数（归一化后），最小 1
            weight = max(1, weight)
            concepts.extend([{"wuxing": w}] * weight)
        return concepts

    # ---------- 时间演化三层 ----------
    def build_rings(self, series):
        """时间演化模式：最早月→种子层，中间月→现行层，最近月→超越层

        返回 (rings, months)。不足 3 个月时：
          - 2 个月 → 种子层=最早月，现行层=次月，超越层=现行层镜像（无演化边）
          - 1 个月 → 单层镜像填充（种子=现行=超越=同月，无演化边）
        """
        months = sorted(series.keys())
        nodes_by_month = {m: self.annotate(list(series[m])) for m in months}

        if len(months) >= 3:
            triple = [months[-3], months[-2], months[-1]]
            mapping = {m: l for m, l in zip(triple, LAYER_LABELS)}
            rings = [{"label": mapping[m], "month": m,
                      "concepts": self.expand_nodes(nodes_by_month[m])}
                     for m in triple]
        elif len(months) == 2:
            rings = [
                {"label": "种子层", "month": months[0],
                 "concepts": self.expand_nodes(nodes_by_month[months[0]])},
                {"label": "现行层", "month": months[1],
                 "concepts": self.expand_nodes(nodes_by_month[months[1]])},
                {"label": "超越层", "month": months[1],
                 "concepts": self.expand_nodes(nodes_by_month[months[1]])},
            ]
        elif len(months) == 1:
            m = months[0]
            concepts = self.expand_nodes(nodes_by_month[m])
            rings = [{"label": l, "month": m, "concepts": list(concepts)}
                     for l in LAYER_LABELS]
        else:
            rings = []
        return rings, months

    # ---------- 诊断 ----------
    def diagnose_source(self, source, months_nodes):
        """单源完整诊断 → 记录 dict"""
        rings, months = self.build_rings(months_nodes)
        if not rings:
            return None

        # v2 引擎诊断
        v2 = v2_diagnose(rings, config={})

        # weight 加权五行分布（适配层自算——展开后的 concepts 与 dim1 一致）
        wuxing_dist = {w: v2["dim1_freq"][w]["pct"] for w in WUXING_ORDER}
        dominant = max(WUXING_ORDER, key=lambda w: wuxing_dist[w])

        # O_t：主导行占比（weight 加权，v2 dim1 展开后即加权口径）
        O_t = round(wuxing_dist[dominant], 4)

        # E_u：适配层自算（1 - H_norm，weight 加权口径）——语义 ≠ v2 dim4
        probs = [wuxing_dist[w] for w in WUXING_ORDER]
        H = entropy(probs)
        H_max = entropy([0.2] * 5)
        E_u = round(1 - H / H_max, 4) if H_max > 0 else 0.0

        # C_k：演化耦合度（基于 v2 dim3 生克边）——解除 C_k≡O_t 共线
        edges = v2["dim3_edges"]
        sheng = sum(1 for e in edges if e["type"] == "相生")
        ke = sum(1 for e in edges if e["type"] == "相克")
        C_k = round((sheng * 1.0 + ke * 0.5) / 2.0, 4)  # 全相生=1.0，有相克=0.75，无边=0

        # K_y：k_y_enhancer
        dim4_ratio = v2["dim4_entropy"]["ratio"]
        K_y, e_relation = k_y_enhancer(wuxing_dist, edges, dim4_ratio, self.beta)

        # S_p：power_mean(p=0.5, scale=100)，等权（v0.1 口径）
        dims = [O_t, E_u, C_k, K_y]
        p = 0.5
        s_sum = sum(d ** p for d in dims) / len(dims)
        S_p = round((s_sum ** (1 / p)) * 100, 2)

        # 节点数（未展开的分类数）
        n_nodes = sum(len(v) for v in months_nodes.values())

        return {
            "four_dims": {"O_t": O_t, "E_u": E_u, "C_k": C_k, "K_y": K_y},
            "S_p": S_p, "dominant": dominant, "n_nodes": n_nodes,
            "months": months,
            "v2_extra": {
                "dim1_freq": v2["dim1_freq"],
                "dim2_layers": v2["dim2_layers"],
                "dim3_edges": edges,
                "dim3_profile": v2["dim3_profile"],
                "dim4_entropy": v2["dim4_entropy"],
                "dim5_compass": v2["dim5_compass"],
                "k_y_enhancer": {"e_relation": e_relation},
            },
        }

    # ---------- 记录与对照 ----------
    def to_record(self, source, diag):
        """输出 merged_series 兼容记录"""
        return {
            "source": source,
            "months": diag["months"],
            "O_t": diag["four_dims"]["O_t"],
            "E_u": diag["four_dims"]["E_u"],
            "C_k": diag["four_dims"]["C_k"],
            "K_y": diag["four_dims"]["K_y"],
            "S_p": diag["S_p"],
            "dominant": diag["dominant"],
            "n_nodes": diag["n_nodes"],
            "engine": "wuxing_diagnose_v2",
            "v2_extra": diag["v2_extra"],
        }

    def compare_fallback(self, source, months_nodes, diag_v2):
        """fallback vs v2 对照（同数据、双引擎）"""
        # fallback 用最近月（保持与壳核报告逐月口径可比）
        last_month = sorted(months_nodes.keys())[-1]
        fb = fallback_diagnose([dict(n) for n in months_nodes[last_month]],
                               self.canonical, self.topic)
        d2 = diag_v2["four_dims"]
        return {
            "source": source, "months": sorted(months_nodes.keys()),
            "last_month": last_month,
            "fallback": fb["four_dims"], "fallback_S_p": fb["S_p"],
            "fallback_dominant": fb["dominant"],
            "v2": d2, "v2_S_p": diag_v2["S_p"], "v2_dominant": diag_v2["dominant"],
            "deltas": {
                "O_t": round(d2["O_t"] - fb["four_dims"]["O_t"], 4),
                "E_u": round(d2["E_u"] - fb["four_dims"]["E_u"], 4),
                "C_k": round(d2["C_k"] - fb["four_dims"]["C_k"], 4),
                "K_y": round(d2["K_y"] - fb["four_dims"]["K_y"], 4),
                "S_p": round(diag_v2["S_p"] - fb["S_p"], 2),
            },
            "issues_resolved": {
                "C_k_neq_O_t": d2["C_k"] != d2["O_t"],
                "K_y_discrimination": d2["K_y"] < 1.0,
            },
        }


# ============ 主流程 ============
def main():
    parser = argparse.ArgumentParser(description="EngineAdapterV2 —— 真实引擎接入适配层")
    parser.add_argument("--dir", default=".", help="树文件目录（默认当前目录）")
    parser.add_argument("--source", default=None,
                        help="指定源（baai/arxiv/github/huggingface，默认全部可用源）")
    parser.add_argument("--min-months", type=int, default=1,
                        help="最少月数（不足则跳过，默认 1）")
    args = parser.parse_args()

    print("=" * 68)
    print("EngineAdapterV2 —— 真实引擎接入（时间演化模式）")
    print("=" * 68)

    adapter = EngineAdapterV2()
    sources = [args.source] if args.source else list(SOURCE_GLOBS.keys())

    records = []
    comparisons = []
    for source in sources:
        series = adapter.load_series(args.dir, source)
        if not series:
            print(f"\n[跳过] {source}: 无树文件")
            continue
        if len(series) < args.min_months:
            print(f"\n[跳过] {source}: 仅 {len(series)} 月（< {args.min_months}）")
            continue

        diag = adapter.diagnose_source(source, series)
        if diag is None:
            print(f"\n[跳过] {source}: 诊断失败")
            continue

        rec = adapter.to_record(source, diag)
        records.append(rec)

        cmp = adapter.compare_fallback(source, series, diag)
        comparisons.append(cmp)

        print(f"\n[诊断] {source}  months={diag['months']}")
        fd = diag["four_dims"]
        print(f"  四维: O_t={fd['O_t']} E_u={fd['E_u']} C_k={fd['C_k']} K_y={fd['K_y']}  "
              f"S_p={diag['S_p']}  dominant={diag['dominant']}")
        edges = diag["v2_extra"]["dim3_edges"]
        if edges:
            for e in edges:
                print(f"  演化边: {e['source']}─{e['type']}→{e['target']} ({e['layer_transition']})")
        else:
            print("  演化边: 无（月数不足或主导行无生克关系）")
        prof = diag["v2_extra"]["dim3_profile"]
        print(f"  路径画像: {prof['path']}  生={prof['sheng_count']} 克={prof['ke_count']}  "
              f"匹配画像={prof['matches_profile']}")
        compass = diag["v2_extra"]["dim5_compass"]
        print(f"  质心: cx={compass['cx']} cy={compass['cy']} magnitude={compass['magnitude']}")

    # 输出
    out = {
        "generated": date.today().strftime("%Y-%m-%d"),
        "engine": "wuxing_diagnose_v2 (via EngineAdapterV2, 时间演化模式)",
        "records": records,
        "fallback_comparison": comparisons,
    }
    Path("engine_v2_series.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 68)
    print("[fallback vs v2 对照]")
    for c in comparisons:
        fb = c["fallback"]
        d2 = c["v2"]
        print(f"\n  {c['source']}（{c['last_month']}，fallback 逐月 vs v2 演化三层）")
        print(f"    fallback: O_t={fb['O_t']} E_u={fb['E_u']} C_k={fb['C_k']} K_y={fb['K_y']} "
              f"S_p={c['fallback_S_p']} dom={c['fallback_dominant']}")
        print(f"    v2      : O_t={d2['O_t']} E_u={d2['E_u']} C_k={d2['C_k']} K_y={d2['K_y']} "
              f"S_p={c['v2_S_p']} dom={c['v2_dominant']}")
        print(f"    Δ       : {c['deltas']}")
        print(f"    问题修复: C_k≠O_t={c['issues_resolved']['C_k_neq_O_t']}  "
              f"K_y<1.0={c['issues_resolved']['K_y_discrimination']}")

    print(f"\n[输出] engine_v2_series.json（{len(records)} 条）")
    print("=" * 68)


if __name__ == "__main__":
    main()
