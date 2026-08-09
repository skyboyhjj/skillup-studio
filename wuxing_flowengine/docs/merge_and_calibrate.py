#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
四源时间序列合并与系数校准（W4）
================================
输入：BAAI（knowledge_tree_*.json）+ arXiv（ai_tree_*.json）
      + GitHub（github_tree_*.json）+ HF（hf_tree_*.json）
处理：按 source×month 合并 → 逐源逐月诊断 → 数据驱动系数校准
输出：
  1. merged_series.json      四源时间序列（四维指标 + S_p 逐月）
  2. calibration_report.json 校准报告（v0.1_initial 观测分布 → v1.1_calibrated 建议）

校准原则（不假装精确）：
  - 观测各维度跨源跨月分布：均值/极差/变异系数 CV
  - CV > 0.1 → 有区分度（系数可保留）；CV ≤ 0.1 → 恒定（标注待真实引擎）
  - S_p 权重按"区分度"（逆方差）加权——让 S_p 主要由有区分度的维度驱动
  - 校准建议均为"草案"，真实引擎接入后复核

用法（PowerShell，置于树文件目录）：
  python merge_and_calibrate.py
  python merge_and_calibrate.py --dir ./output
"""

import argparse
import glob
import json
import math
import statistics
from collections import defaultdict
from datetime import date
from pathlib import Path

# 五行标注（统一 canonical——四源共用）
CANONICAL_WUXING = {
    # arXiv AI 分类
    "cs.AI": "火", "cs.LG": "土", "cs.CL": "水", "cs.CV": "木",
    "cs.NE": "水", "cs.MA": "木", "cs.RO": "金", "cs.HC": "火",
    "cs.IR": "金", "cs.MM": "火", "stat.ML": "土",
    # BAAI 领域（简化映射，待校准）
    "LLM": "水", "NLP": "水", "计算机视觉": "木", "CV": "木",
}
# GitHub/HF 主题 → 五行（v2: 2026-08-09 对齐生产版 TAG_WUXING 5 处修正 + 对齐 github_collect 4 处）
# 原则：水=语言/流动/模型、火=交互/活跃/智能体、木=感知/生发/视觉、
#       土=基础/承载/工程、金=结构/精确/分类
TOPIC_WUXING = {
    "llm": "水", "large-language-models": "水",
    "machine-learning": "土", "deep-learning": "水",
    "natural-language-processing": "水", "computer-vision": "木",
    "reinforcement-learning": "金", "multimodal": "木",
    "agents": "火", "autonomous-agents": "火",
    "retrieval-augmented-generation": "金",
    "graph-neural-network": "土", "federated-learning": "金",
    "robotics": "金",
    "text-generation": "水", "text-classification": "金",
    "token-classification": "金", "question-answering": "火",
    "summarization": "水", "translation": "水",
    "image-classification": "木", "image-text-to-text": "木",
    "text-to-image": "木", "automatic-speech-recognition": "水",
    "text-to-text": "水",
    # v2 变更记录：
    #   HF 5 处（对齐 hf_collect.py TAG_WUXING）：
    #     text-classification:     水→金（分类=结构/精确）
    #     token-classification:    水→金（分类=结构/精确）
    #     question-answering:      水→火（问答=交互活跃）
    #     image-text-to-text:      火→木（视觉-语言=感知生发）
    #     reinforcement-learning:  火→金（RL=策略结构）
    #   GitHub 4 处（对齐 github_collect.py TOPIC_WUXING）：
    #     deep-learning:           土→水（水=模型）
    #     multimodal:              火→木（木=感知/视觉）
    #     agents:                  木→火（火=智能体）
    #     graph-neural-network:    金→土（土=基础/工程）
}
WUXING_ORDER = ["木", "火", "土", "金", "水"]
SOURCES = ["baai", "arxiv", "github", "huggingface"]

# HF pipeline_tag 12 个 → 生产版 canonical 五行（v2: 2026-08-09）
# 来源：scripts/hf_collect.py TAG_WUXING——逐条语义标注，已升级为 canonical
HF_CANONICAL_WUXING = {
    "text-generation": "水", "text-classification": "金",
    "token-classification": "金", "question-answering": "火",
    "summarization": "水", "translation": "水",
    "image-classification": "木", "image-text-to-text": "木",
    "text-to-image": "木", "automatic-speech-recognition": "水",
    "reinforcement-learning": "金", "text-to-text": "水",
}


def check_hf_cross_source_consistency(strict=True):
    """跨源标注一致性校验：TOPIC_WUXING(HF tags) vs HF_CANONICAL_WUXING。

    防止参考版（merge_and_calibrate）与生产版（hf_collect）标注分裂。
    参考：docs/arXiv五行标注仲裁确认文档.md 决议 2（扩展至 HF 源）

    Args:
        strict: True=不一致时抛 ValueError，False=返回差异列表

    Returns:
        dict: {consistent, mismatches, fix_count, annotation_version}
    """
    mismatches = {}
    for tag in HF_CANONICAL_WUXING:
        if tag not in TOPIC_WUXING:
            mismatches[tag] = ("缺失", HF_CANONICAL_WUXING[tag])
            continue
        actual = TOPIC_WUXING[tag]
        expected = HF_CANONICAL_WUXING[tag]
        if actual != expected:
            mismatches[tag] = (actual, expected)

    result = {
        "consistent": len(mismatches) == 0,
        "mismatches": mismatches,
        "fix_count": len(mismatches),
        "annotation_version": "v2",
    }

    if not result["consistent"] and strict:
        raise ValueError(
            f"HF 跨源标注分裂 {len(mismatches)} 处: {mismatches}——"
            f"merge_and_calibrate.py TOPIC_WUXING 与 hf_collect.py TAG_WUXING 不一致，"
            f"请对齐后重试"
        )

    return result
SOURCE_GLOBS = {
    "baai": "baai_tree_*.json",
    "arxiv": "arxiv_ai_tree_*.json",
    "github": "github_tree_*.json",
    "huggingface": "hf_tree_*.json",
}

# v0.1_initial 系数（标注：待校准）
COEFF_V0 = {
    "O_t": {"formula": "dominant_share", "note": "主导五行占比", "status": "v0.1_initial"},
    "E_u": {"formula": "1 - H_norm", "note": "熵确定度", "status": "v0.1_initial"},
    "C_k": {"formula": "same_wuxing_ratio", "note": "同五行分类占比", "status": "v0.1_initial"},
    "K_y": {"formula": "category_density", "note": "分类数密度（无结构边）", "status": "v0.1_initial"},
    "S_p": {"formula": "power_mean(p=0.5, scale=100)", "note": "四维等权", "status": "v0.1_initial"},
}


# ============ 工具 ============
def wilson_ci(k, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, center - margin), min(1.0, center + margin)


def entropy(p_list):
    H = 0.0
    for p in p_list:
        if p > 0:
            H -= p * math.log2(p)
    return H


def extract_month(filename: str) -> str:
    """从文件名提取 YYYY-MM"""
    import re
    m = re.search(r"(\d{4})-(\d{2})", filename)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    m2 = re.search(r"(\d{6})", filename)
    if m2:
        s = m2.group(1)
        return f"{s[:4]}-{s[4:]}"
    return "unknown"


# ============ 采集与诊断 ============
def collect_series(directory: str):
    """读四源树文件 → {source: {month: nodes}}"""
    series = defaultdict(dict)
    for source, pattern in SOURCE_GLOBS.items():
        files = sorted(glob.glob(str(Path(directory) / pattern)))
        for f in files:
            month = extract_month(f)
            try:
                tree = json.loads(Path(f).read_text(encoding="utf-8"))
                nodes = tree.get("nodes", [])
                series[source][month] = nodes
            except Exception as e:
                print(f"  ⚠️ 读取失败 {f}: {e}")
    return series


def diagnose_nodes(nodes):
    """简化七维诊断（fallback——复用 arxiv_diagnose 逻辑）"""
    # 五行标注（节点自带或 canonical/topic 映射）
    for n in nodes:
        w = n.get("wuxing")
        if not w:
            cid = str(n.get("id", ""))
            name = str(n.get("name", ""))
            # ① canonical 分类（arXiv/BAAI）
            w = CANONICAL_WUXING.get(cid)
            if not w:
                # ② GitHub/HF topic 映射（按 name，或 id 冒号后部分）
                key = name if name else cid.split(":", 1)[-1]
                w = TOPIC_WUXING.get(key, "土")
            n["wuxing"] = w

    total = sum(n.get("weight", 1) for n in nodes) or 1
    wuxing_weight = defaultdict(int)
    for n in nodes:
        wuxing_weight[n.get("wuxing", "土")] += n.get("weight", 1)

    wuxing_dist = {w: wuxing_weight.get(w, 0) / total for w in WUXING_ORDER}
    probs = [wuxing_dist[w] for w in WUXING_ORDER]
    H = entropy(probs)
    H_max = entropy([0.2] * 5)
    H_norm = H / H_max if H_max > 0 else 0
    dominant = max(WUXING_ORDER, key=lambda w: wuxing_dist[w])

    n_cat = len(nodes)
    O_t = round(wuxing_dist[dominant], 4)
    E_u = round(1 - H_norm, 4)
    # C_k：主导五行权重占比（认知耦合近似——fallback，待真实引擎）
    C_k = round(wuxing_dist[dominant], 4)
    K_y = round(min(1.0, n_cat / 11.0), 4)

    dims = [O_t, E_u, C_k, K_y]
    p = 0.5
    s_sum = sum(d ** p for d in dims) / len(dims)
    S_p = round((s_sum ** (1 / p)) * 100, 2)

    return {"four_dims": {"O_t": O_t, "E_u": E_u, "C_k": C_k, "K_y": K_y},
            "S_p": S_p, "dominant": dominant, "n_nodes": n_cat}


def build_series_records(series):
    """逐源逐月诊断 → 记录列表"""
    records = []
    for source, months in series.items():
        for month, nodes in months.items():
            diag = diagnose_nodes(nodes)
            records.append({
                "source": source, "month": month,
                **diag["four_dims"], "S_p": diag["S_p"],
                "dominant": diag["dominant"], "n_nodes": diag["n_nodes"],
            })
    return records


# ============ 系数校准 ============
def calibrate(records):
    """数据驱动校准：观测分布 → v1.1_calibrated 建议（排除空月后）"""
    dims = ["O_t", "E_u", "C_k", "K_y"]
    calib = {"v0_1_initial": COEFF_V0, "observed": {}, "v1_1_calibrated": {},
             "calibration_filter": "excluded n_nodes=0 empty months"}

    for d in dims:
        values = [r[d] for r in records if d in r]
        if len(values) < 3:
            calib["observed"][d] = {"n": len(values), "note": "数据不足，维持 v0.1_initial"}
            continue
        mean = statistics.mean(values)
        stdev = statistics.stdev(values) if len(values) > 1 else 0.0
        cv = stdev / mean if mean > 0 else 0.0
        lo, hi = min(values), max(values)

        # 判别区分度：CV=0 表示所有值相同（如 K_y 全 1.0），无区分度
        if cv == 0.0:
            discrimination = "无区分度（恒定，权重归零）"
        elif cv > 0.1:
            discrimination = "有区分度"
        else:
            discrimination = "低区分度（恒定，待真实引擎）"

        calib["observed"][d] = {
            "n": len(values), "mean": round(mean, 4), "stdev": round(stdev, 4),
            "cv": round(cv, 4), "range": [round(lo, 4), round(hi, 4)],
            "discrimination": discrimination,
        }

    # S_p 权重 ∝ 区分度（CV）——CV=0 的维度权重归零
    cvs = {d: calib["observed"].get(d, {}).get("cv", 0.0) for d in dims}
    total_cv = sum(cvs.values()) or 1e-9
    weights = {d: round(cv / total_cv, 4) for d, cv in cvs.items()}

    # 校准建议
    calib["v1_1_calibrated"] = {
        "coefficients": {d: {"weight": weights[d], "status": "v1.1_calibrated(草案)",
                              "basis": f"观测 CV={cvs[d]}，区分度加权"}
                         for d in dims},
        "S_p": {"formula": "power_mean(p=0.5, scale=100)", "weights": weights,
                "note": "权重 ∝ 区分度（CV）——区分度高的维度主导 S_p，CV=0 维度权重归零"},
        "warning": "v1.1_calibrated 为数据驱动草案，真实引擎接入后复核",
    }
    return calib


# ============ 主流程 ============
def main():
    parser = argparse.ArgumentParser(description="四源时间序列合并与系数校准")
    parser.add_argument("--dir", default=".", help="树文件目录（默认当前目录）")
    args = parser.parse_args()

    print("=" * 64)
    print("四源时间序列合并与系数校准（W4）")
    print("=" * 64)

    # 0. 跨源标注一致性校验（HF: TOPIC_WUXING vs canonical）
    hf_consistency = check_hf_cross_source_consistency(strict=True)
    print(f"[一致性] HF 跨源标注校验: {'通过' if hf_consistency['consistent'] else '不一致'}")

    # 1. 采集
    series = collect_series(args.dir)
    total_records = sum(len(v) for v in series.values())
    print(f"\n[采集] 源数={sum(1 for s in series.values() if s)} "
          f"(BAAI={len(series.get('baai', {}))}月, arXiv={len(series.get('arxiv', {}))}月, "
          f"GitHub={len(series.get('github', {}))}月, HF={len(series.get('huggingface', {}))}月)")

    if total_records == 0:
        print("❌ 未找到任何树文件——先运行四源采集脚本")
        return

    # 2. 诊断
    records = build_series_records(series)
    print(f"\n[诊断] {total_records} 条（源×月）记录")

    # 2.5 校准前过滤：排除空月（n_nodes=0），避免伪区分度
    calib_records = [r for r in records if r.get("n_nodes", 0) > 0]
    excluded_empty = total_records - len(calib_records)
    if excluded_empty > 0:
        print(f"[过滤] 排除 {excluded_empty} 条空月记录（n_nodes=0），校准使用 {len(calib_records)} 条")

    # 3. 校准
    calib = calibrate(calib_records)
    print("\n[观测分布]")
    for d, obs in calib["observed"].items():
        if "n" in obs and obs["n"] >= 3:
            print(f"  {d}: mean={obs['mean']} cv={obs['cv']} range={obs['range']} "
                  f"→ {obs['discrimination']}")

    print("\n[v1.1_calibrated 草案] S_p 权重（∝ 区分度）:")
    for d, w in calib["v1_1_calibrated"]["S_p"]["weights"].items():
        cv_val = calib["observed"].get(d, {}).get("cv", "?")
        print(f"  {d}: {w}（CV={cv_val}）")

    # 4. 输出
    output_dir = Path(args.dir)
    merged = {"generated": date.today().strftime("%Y-%m-%d"), "records": records}
    calib["records_count"] = total_records
    (output_dir / "merged_series.json").write_text(
        json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "calibration_report.json").write_text(
        json.dumps(calib, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n[输出] {output_dir}/merged_series.json（{total_records} 条）+ calibration_report.json")
    print("=" * 64)


if __name__ == "__main__":
    main()
