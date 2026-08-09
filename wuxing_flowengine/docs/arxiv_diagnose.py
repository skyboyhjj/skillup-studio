#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ai_tree_*.json → 五行诊断引擎接入脚本（W2.5）
==============================================
输入：arxiv_ai_tree_YYYYMM.json（四源 schema 节点树：11 分类 + weight）
输出：
  1. arxiv_diag_YYYYMM.json   单月诊断（七维指标 + four_dims + S_p + 信度）
  2. arxiv_series.json        多月时间序列（O_t/E_u/C_k/K_y 演化 + 重心路径）

V1.1 新增（2026-08-09）：
  - check_wuxing_consistency() 标注一致性校验（P0）
  - --fix 自动修复标注不一致
  - wuxing_annotation_version 标注版本化（P1）
  - 引擎优先尝试真实引擎（wuxing_diagnose_v2），不可用时 fallback

引擎接入方式：
  - 优先调用真实五行诊断引擎（wuxing_flowengine 的 diagnose 接口）
  - 引擎不可用时用内置 fallback（简化计算，明确标注 v0.1_initial 待校准）
  - 接口契约见 ENGINE_CONTRACT——真实引擎按此对接即可无缝替换

用法（PowerShell，置于 wuxing_flowengine 目录下运行）：
  python arxiv_diagnose.py --month 2026-08                 # 自动找 arxiv_ai_tree_202608.json
  python arxiv_diagnose.py --tree arxiv_ai_tree_202608.json
  python arxiv_diagnose.py --month 2026-08 --fix           # 修复标注不一致
  python arxiv_diagnose.py --glob "arxiv_ai_tree_*.json"   # 多月时间序列
  python arxiv_diagnose.py --check                         # 仅检查所有树文件标注一致性

零依赖：urllib 不需要；json + math + glob（标准库）
"""

import argparse
import glob
import json
import math
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

# ============ 五行标注表（11 分类 → 五行，仲裁确认唯一源） ============
# 标注原则：语义映射（土=承载/水=流动/木=生发/金=结构/火=活跃）
# 标注版本：v1（2026-08-09），仲裁确认文档：docs/arXiv五行标注仲裁确认文档.md
WUXING_ANNOTATION_VERSION = "v1"
WUXING_ANNOTATION_SOURCE = "AI_CATEGORY_WUXING (canonical, arbitration-confirmed)"
WUXING_ANNOTATION_RATIONALE = "语义映射：土=承载/水=流动/木=生发/金=结构/火=活跃"

AI_CATEGORY_WUXING = {
    "cs.AI":   "火",   # 人工智能：综合、扩散、显性
    "cs.LG":   "土",   # 机器学习：基础承载（方法底座）
    "cs.CL":   "水",   # 计算语言：语言流动、理解
    "cs.CV":   "木",   # 计算机视觉：感知生发
    "cs.NE":   "水",   # 神经进化：神经流动、演化
    "cs.MA":   "木",   # 多智能体：多体协作、生发
    "cs.RO":   "金",   # 机器人：执行、结构、控制
    "cs.HC":   "火",   # 人机交互：交互活跃
    "cs.IR":   "金",   # 信息检索：筛选精确
    "cs.MM":   "火",   # 多媒体：多模态活跃
    "stat.ML": "土",   # 统计学习：统计基础
}
WUXING_ORDER = ["木", "火", "土", "金", "水"]


# ============ P0: 标注一致性校验 ============
def check_wuxing_consistency(nodes, canonical=None, strict=True):
    """标注源一致性检查：防止标注分裂导致时间序列伪影。

    参考：docs/arXiv五行标注仲裁确认文档.md 决议 2

    Args:
        nodes: 节点列表（含 id/wuxing 字段）
        canonical: 规范标注映射（默认 AI_CATEGORY_WUXING）
        strict: True=不一致时抛异常，False=返回差异列表

    Returns:
        dict: {
            "consistent": bool,
            "mismatches": {cat_id: (actual, canonical)} 仅不一致项,
            "fix_count": int,
            "fix_details": {cat_id: "actual→canonical (reason)"}
        }

    Raises:
        ValueError: strict=True 且有标注不一致时
    """
    if canonical is None:
        canonical = AI_CATEGORY_WUXING

    mismatches = {}
    fix_details = {}
    for n in nodes:
        cat_id = n.get("id", "")
        if cat_id not in canonical:
            continue
        actual = n.get("wuxing", "")
        expected = canonical[cat_id]
        if actual != expected:
            mismatches[cat_id] = (actual, expected)
            fix_details[cat_id] = f"{actual}→{expected}"

    result = {
        "consistent": len(mismatches) == 0,
        "mismatches": mismatches,
        "fix_count": len(mismatches),
        "fix_details": fix_details,
        "annotation_version": WUXING_ANNOTATION_VERSION,
        "annotation_source": WUXING_ANNOTATION_SOURCE,
    }

    if not result["consistent"] and strict:
        raise ValueError(
            f"标注源分裂 {len(mismatches)} 处: {mismatches}——"
            f"必须先统一，禁止混用（参考：docs/arXiv五行标注仲裁确认文档.md 决议 2）"
        )

    return result


def apply_wuxing_fixes(nodes, canonical=None):
    """原地修复标注不一致（用 canonical 覆盖）。

    Args:
        nodes: 节点列表（会被原地修改）
        canonical: 规范标注映射

    Returns:
        dict: 同 check_wuxing_consistency 的返回值
    """
    if canonical is None:
        canonical = AI_CATEGORY_WUXING

    consistency = check_wuxing_consistency(nodes, canonical, strict=False)
    if consistency["fix_count"] > 0:
        for n in nodes:
            cat_id = n.get("id", "")
            if cat_id in consistency["mismatches"]:
                old = n["wuxing"]
                n["wuxing"] = canonical[cat_id]
    return consistency


# ============ 引擎接口契约 ============
ENGINE_CONTRACT = {
    "input": {
        "nodes": [
            {"id": "cs.AI", "name": "人工智能", "wuxing": "火", "weight": 1284,
             "parent": "cs", "layer": "L1"}
        ]
    },
    "output": {
        "wuxing_dist": {"木": 0.2, "火": 0.3, "土": 0.2, "金": 0.1, "水": 0.2},
        "four_dims": {"O_t": 0.277, "E_u": 0.8593, "C_k": 0.1761, "K_y": 0.2639},
        "tracks": {"S_p": 35.6, "p": 0.5, "p_label": "P忠恕中道"},
        "wuxing_confidence": {"木": {"point": 0.2, "ci_low": 0.1, "ci_high": 0.3}},
        "S_p_confidence": {"S": 30.9, "effective_n": 2.99, "confidence_level": "中"},
        "verdict": "化·吸收融合阶段",
    },
    "note": "真实引擎（wuxing_flowengine 的 diagnose）按此契约对接；本脚本 EngineAdapter 自动适配",
}


# ============ 引擎适配层 ============
class EngineAdapter:
    """适配真实引擎；不可用时用 fallback（v0.1_initial 待校准）"""

    def __init__(self):
        self.real_engine = None
        self.engine_name = "fallback_v0.1_initial"
        try:
            # 尝试导入真实诊断引擎
            diagnose_dir = Path(__file__).resolve().parent.parent / "diagnose"
            if str(diagnose_dir) not in sys.path:
                sys.path.insert(0, str(diagnose_dir))
            from wuxing_diagnose_v2 import diagnose
            self.real_engine = diagnose
            self.engine_name = "wuxing_diagnose_v2"
        except ImportError:
            # 尝试备用路径
            try:
                scripts_dir = Path(__file__).resolve().parent.parent / "scripts"
                if str(scripts_dir) not in sys.path:
                    sys.path.insert(0, str(scripts_dir))
                from phase1_pipeline import run as phase1_run
                self.real_engine = phase1_run
                self.engine_name = "phase1_pipeline"
            except ImportError:
                self.real_engine = None

    def diagnose(self, nodes):
        """诊断入口：真实引擎优先 → fallback

        arXiv 数据是平层结构（无种子/现行/超越三层），
        真实引擎设计用于层次化知识树，对平层数据使用 fallback 更准确。
        """
        # 检测是否适合用真实引擎：节点有 cognitive_depth 分层
        has_layers = any(n.get("cognitive_depth") in ("L1", "L2", "L3", "L4") for n in nodes)
        has_edges = any(n.get("edges") for n in nodes)

        if self.real_engine is not None and (has_layers or has_edges):
            try:
                return self._real_diagnose(nodes)
            except Exception as e:
                print(f"  [警告] 真实引擎调用失败: {e}，回退到 fallback")
        return fallback_diagnose(nodes)

    def _real_diagnose(self, nodes):
        """调用真实诊断引擎"""
        if self.engine_name == "wuxing_diagnose_v2":
            # 构建 rings 格式
            rings = [{
                "label": "arXiv AI 子领域",
                "concepts": [
                    {"name": n.get("name", n["id"]),
                     "wuxing": n.get("wuxing", "土"),
                     "cognitive_depth": n.get("cognitive_depth", "L2")}
                    for n in nodes
                ]
            }]
            result = self.real_engine(rings)
            return self._adapt_real_result(result, nodes)
        elif self.engine_name == "phase1_pipeline":
            # phase1_pipeline 需要文件路径，不适合直接调用
            # 回退到 fallback
            raise NotImplementedError("phase1_pipeline 需要文件路径，使用 fallback")
        return fallback_diagnose(nodes)

    def _adapt_real_result(self, result, nodes):
        """将真实引擎输出适配为统一格式。

        wuxing_diagnose_v2 输出: dim1_freq, dim4_entropy, dim5_compass, dim3_edges
        phase1_pipeline 输出: four_dims, tracks, S_p_confidence
        均需适配为统一格式。
        """
        # 尝试从 dim1_freq 提取五行分布（wuxing_diagnose_v2 格式）
        freq = result.get("dim1_freq", {})
        wuxing_dist = {}
        if freq:
            for w in WUXING_ORDER:
                wuxing_dist[w] = round(freq.get(w, {}).get("pct", 0), 4)

        # 尝试从 phase1_pipeline 格式提取
        four_dims = result.get("four_dims", {})
        tracks = result.get("tracks", {})
        S_p = tracks.get("S_p", None)

        # 如果 four_dims 缺失，从原始指标计算
        if not four_dims:
            # 从 wuxing_diagnose_v2 原始指标计算 four_dims（简化版）
            ent = result.get("dim4_entropy", {})
            compass = result.get("dim5_compass", {})
            edges = result.get("dim3_edges", {})

            # 使用 wuxing_dist 或 freq 计算
            if not wuxing_dist and freq:
                # freq 是计数，转为比例
                total = sum(freq.values()) or 1
                wuxing_dist = {w: freq.get(w, 0) / total for w in WUXING_ORDER}

            if wuxing_dist:
                w = wuxing_dist
                dominant = max(WUXING_ORDER, key=lambda x: w.get(x, 0))
                H_norm = ent.get("ratio", 0.5)
                n_cat = len(nodes)

                O_t = round(w.get(dominant, 0), 4)
                E_u = round(1 - H_norm, 4)
                C_k = round(max(Counter(n.get("wuxing", "土") for n in nodes).values()) / n_cat, 4)
                K_y = round(min(1.0, n_cat / 11.0), 4)
                four_dims = {"O_t": O_t, "E_u": E_u, "C_k": C_k, "K_y": K_y}

        # 如果 S_p 缺失，计算
        if S_p is None:
            dims = [four_dims.get("O_t", 0), four_dims.get("E_u", 0),
                    four_dims.get("C_k", 0), four_dims.get("K_y", 0)]
            p = 0.5
            s_sum = sum(d ** p for d in dims) / len(dims)
            S_p = round((s_sum ** (1 / p)) * 100, 2)
            tracks = {"S_p": S_p, "p": p, "p_label": "P忠恕中道"}

        # 确定主导/次主导
        if not wuxing_dist:
            wuxing_count = Counter(n.get("wuxing", "土") for n in nodes)
            total = sum(wuxing_count.values()) or 1
            wuxing_dist = {w: wuxing_count.get(w, 0) / total for w in WUXING_ORDER}
        dominant = max(WUXING_ORDER, key=lambda x: wuxing_dist.get(x, 0))
        second = sorted(WUXING_ORDER, key=lambda x: wuxing_dist.get(x, 0), reverse=True)[1]

        # 阶段判定
        if S_p >= 50:
            stage = "通·结构成熟"
        elif S_p >= 40:
            stage = "变·结构演变"
        elif S_p >= 35:
            stage = "化·吸收融合"
        elif S_p >= 30:
            stage = "克·约束竞争"
        elif S_p >= 25:
            stage = "生·新生萌芽"
        else:
            stage = "未入阶段（萌芽前）"

        return {
            "engine": self.engine_name,
            "wuxing_dist": {k: round(v, 4) for k, v in wuxing_dist.items()},
            "wuxing_confidence": result.get("wuxing_confidence", {}),
            "four_dims": four_dims,
            "tracks": tracks,
            "S_p_confidence": result.get("S_p_confidence", {
                "S": round(S_p * 0.87, 2),
                "effective_n": round(sum(1 for d in four_dims.values() if d > 0.05), 2),
                "confidence_level": "中（引擎适配）",
            }),
            "entropy": result.get("dim4_entropy", result.get("entropy", {})),
            "dominant": dominant,
            "second": second,
            "stage": stage,
            "verdict": f"{stage}（{dominant}主导，次{second}）",
        }


# ============ 统计工具 ============
def wilson_ci(k, n, z=1.96):
    """Wilson 置信区间（占比）"""
    if n == 0:
        return 0.0, 0.0, 0.0
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    lo = max(0.0, center - margin)
    hi = min(1.0, center + margin)
    return p, lo, hi


def entropy(p_list):
    """Shannon 熵（以 2 为底）"""
    H = 0.0
    for p in p_list:
        if p > 0:
            H -= p * math.log2(p)
    return H


# ============ Fallback 诊断（v0.1_initial，待真实引擎校准） ============
def fallback_diagnose(nodes):
    """简化七维诊断——标注 v0.1_initial，真实引擎接入后替换"""
    # --- D1 五行频次（weight 加权）---
    total = sum(n.get("weight", 1) for n in nodes) or 1
    wuxing_weight = defaultdict(int)
    for n in nodes:
        wuxing_weight[n.get("wuxing", "土")] += n.get("weight", 1)

    wuxing_dist = {w: wuxing_weight.get(w, 0) / total for w in WUXING_ORDER}
    wuxing_confidence = {}
    for w in WUXING_ORDER:
        p, lo, hi = wilson_ci(wuxing_weight.get(w, 0), total)
        wuxing_confidence[w] = {
            "point": round(p, 4),
            "ci_low": round(lo, 4),
            "ci_high": round(hi, 4),
            "ci_width": round(hi - lo, 4),
        }

    # --- D4 五行熵 ---
    probs = [wuxing_dist[w] for w in WUXING_ORDER]
    H = entropy(probs)
    H_max = entropy([0.2] * 5)
    H_norm = H / H_max if H_max > 0 else 0

    # --- D5 重心向量（主导五行）---
    dominant = max(WUXING_ORDER, key=lambda w: wuxing_dist[w])
    second = sorted(WUXING_ORDER, key=lambda w: wuxing_dist[w], reverse=True)[1]

    # --- four_dims（fallback 简化，v0.1_initial）---
    n_cat = len(nodes)
    # O_t：主导五行占比（越高越"稳定"）
    O_t = round(wuxing_dist[dominant], 4)
    # E_u：1 - 熵归一化（熵越低越确定；fallback 简化）
    E_u = round(1 - H_norm, 4)
    # C_k：分类耦合（fallback：同五行分类数 / 总分类数——近似）
    same_wuxing = max(Counter(n.get("wuxing", "土") for n in nodes).values())
    C_k = round(same_wuxing / n_cat, 4)
    # K_y：因果纠缠（fallback：分类数密度，arXiv 树无结构边）
    K_y = round(min(1.0, n_cat / 11.0), 4)

    # --- S_p（广义平均 p=0.5，scale=100——V1.2 定标）---
    dims = [O_t, E_u, C_k, K_y]
    p = 0.5
    s_sum = sum(d ** p for d in dims) / len(dims)
    S_p = round((s_sum ** (1 / p)) * 100, 2)
    effective_n = round(sum(1 for d in dims if d > 0.05), 2)

    # --- 阶段判定（V1.2 区间表）---
    if S_p >= 50:
        stage = "通·结构成熟"
    elif S_p >= 40:
        stage = "变·结构演变"
    elif S_p >= 35:
        stage = "化·吸收融合"
    elif S_p >= 30:
        stage = "克·约束竞争"
    elif S_p >= 25:
        stage = "生·新生萌芽"
    else:
        stage = "未入阶段（萌芽前）"

    return {
        "engine": "fallback_v0.1_initial",
        "wuxing_dist": {k: round(v, 4) for k, v in wuxing_dist.items()},
        "wuxing_confidence": wuxing_confidence,
        "four_dims": {"O_t": O_t, "E_u": E_u, "C_k": C_k, "K_y": K_y},
        "tracks": {"S_p": S_p, "p": p, "p_label": "P忠恕中道"},
        "S_p_confidence": {
            "S": round(S_p * 0.87, 2),
            "effective_n": effective_n,
            "confidence_level": "低（fallback）",
        },
        "entropy": {"H": round(H, 4), "H_norm": round(H_norm, 4)},
        "dominant": dominant,
        "second": second,
        "stage": stage,
        "verdict": f"{stage}（{dominant}主导，次{second}）",
    }


# ============ 时间序列 ============
def build_series(tree_files, canonical=None, fix=False):
    """多月时间序列：逐月诊断 → O_t/E_u/C_k/K_y 演化 + 重心路径

    Args:
        tree_files: ai_tree JSON 文件路径列表
        canonical: 规范标注映射
        fix: 是否自动修复标注不一致

    Returns:
        dict: {"series": [...], "dominant_path": [...], "annotation_versions": {...}}
    """
    if canonical is None:
        canonical = AI_CATEGORY_WUXING

    adapter = EngineAdapter()
    series = []
    annotation_versions = {}
    total_fixes = 0

    for f in sorted(tree_files):
        tree = json.loads(Path(f).read_text(encoding="utf-8"))
        nodes = tree.get("nodes", [])
        month = tree.get("month", Path(f).stem)

        # P0: 标注一致性校验
        consistency = check_wuxing_consistency(nodes, canonical, strict=not fix)
        if not consistency["consistent"]:
            if fix:
                apply_wuxing_fixes(nodes, canonical)
                total_fixes += consistency["fix_count"]
                print(f"  [修复] {month}: {consistency['fix_count']} 处标注不一致已修复 -> {consistency['fix_details']}")

                # 回写修复后的树文件
                tree["nodes"] = nodes
                tree["meta"] = tree.get("meta", {})
                tree["meta"]["wuxing_fixes_applied"] = consistency["fix_count"]
                tree["meta"]["wuxing_fix_details"] = consistency["fix_details"]
                tree["meta"]["wuxing_annotation_version"] = WUXING_ANNOTATION_VERSION
                tree["meta"]["wuxing_fixed_at"] = datetime.now().isoformat()
                Path(f).write_text(json.dumps(tree, ensure_ascii=False, indent=2), encoding="utf-8")
            else:
                print(f"  [警告] {month}: {consistency['fix_count']} 处标注不一致（用 --fix 自动修复）")

        # 确保所有节点有标注（缺失的回退到 canonical）
        for n in nodes:
            if not n.get("wuxing") or n["wuxing"] not in WUXING_ORDER:
                n["wuxing"] = canonical.get(n["id"], "土")

        diag = adapter.diagnose(nodes)
        series.append({
            "month": month,
            "file": str(f),
            "four_dims": diag["four_dims"],
            "S_p": diag["tracks"]["S_p"],
            "dominant": diag["dominant"],
            "wuxing_dist": diag["wuxing_dist"],
            "wuxing_annotation_version": WUXING_ANNOTATION_VERSION,
        })
        annotation_versions[month] = WUXING_ANNOTATION_VERSION

    path = [s["dominant"] for s in series]
    return {
        "series": series,
        "dominant_path": path,
        "annotation_versions": annotation_versions,
        "annotation_source": WUXING_ANNOTATION_SOURCE,
        "annotation_rationale": WUXING_ANNOTATION_RATIONALE,
        "fixes_applied_total": total_fixes,
    }


def find_tree_file(month_str):
    """根据月份查找树文件（优先 arxiv_ai_tree_*，回退 arxiv_tree_*，再回退 ai_tree_*）"""
    # 解析 YYYY-MM
    parts = month_str.replace("-", "").replace("_", "")
    if len(parts) == 6:
        yyyymm = parts
    else:
        yyyymm = month_str

    candidates = [
        f"arxiv_ai_tree_{yyyymm}.json",
        f"arxiv_tree_{yyyymm}.json",
        f"ai_tree_{month_str}.json",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    return candidates[0]  # 返回首选（供报错用）


# ============ 主流程 ============
def main():
    parser = argparse.ArgumentParser(description="ai_tree → 五行诊断接入（V1.1）")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--tree", help="单个 ai_tree 文件路径")
    group.add_argument("--month", help="月份 YYYY-MM，自动找 arxiv_ai_tree_YYYYMM.json")
    group.add_argument("--glob", default=None, help="多月 glob 模式，如 arxiv_ai_tree_*.json")
    group.add_argument("--check", action="store_true", help="仅检查所有树文件标注一致性（不诊断）")
    parser.add_argument("--fix", action="store_true", help="自动修复标注不一致")
    parser.add_argument("--canonical", default=None, help="规范标注 JSON 文件路径（覆盖内置）")
    parser.add_argument("--output-dir", default=None, help="输出目录（默认 ../output/）")
    args = parser.parse_args()

    # 确定输出目录
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = Path(__file__).resolve().parent.parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 加载规范标注
    canonical = AI_CATEGORY_WUXING
    if args.canonical:
        with open(args.canonical, "r", encoding="utf-8") as f:
            canonical = json.load(f)

    adapter = EngineAdapter()

    # --check 模式：仅检查一致性
    if args.check:
        tree_files = sorted(output_dir.glob("arxiv_ai_tree_*.json"))
        if not tree_files:
            tree_files = sorted(output_dir.glob("arxiv_tree_*.json"))
        if not tree_files:
            tree_files = sorted(Path(".").glob("ai_tree_*.json"))

        print(f"=== 标注一致性检查（{len(tree_files)} 个文件）===")
        all_ok = True
        for f in tree_files:
            tree = json.loads(Path(f).read_text(encoding="utf-8"))
            nodes = tree.get("nodes", [])
            month = tree.get("month", f.stem)
            try:
                consistency = check_wuxing_consistency(nodes, canonical, strict=True)
                print(f"  ✓ {month}: 一致")
            except ValueError as e:
                all_ok = False
                consistency = check_wuxing_consistency(nodes, canonical, strict=False)
                print(f"  ✗ {month}: {consistency['fix_count']} 处不一致")
                for cat_id, (old, new) in consistency["mismatches"].items():
                    print(f"      {cat_id}: {old}→{new}")
        if all_ok:
            print("\n全部一致 ✓")
        else:
            print(f"\n存在不一致，用 --fix 自动修复")
        return

    # --glob 模式：多月时间序列
    if args.glob:
        files = sorted(glob.glob(args.glob))
        if not files:
            # 尝试从 output 目录找
            files = sorted(output_dir.glob(args.glob))
        if not files:
            print(f"错误: 无匹配文件: {args.glob}")
            return

        result = build_series(files, canonical, fix=args.fix)
        out = output_dir / "arxiv_series.json"
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"时间序列 {len(files)} 个月 → {out}")
        if result["fixes_applied_total"] > 0:
            print(f"标注修复: {result['fixes_applied_total']} 处")
        print(f"标注版本: {result['annotation_versions']}")
        print("主导五行路径:", " → ".join(result["dominant_path"]))
        print("\n逐月 O_t/E_u/C_k/K_y:")
        for s in result["series"]:
            d = s["four_dims"]
            print(f"  {s['month']}: O_t={d['O_t']} E_u={d['E_u']} C_k={d['C_k']} "
                  f"K_y={d['K_y']} S_p={s['S_p']} 主导={s['dominant']}")
        return

    # 单月模式
    tree_path = args.tree
    if args.month:
        tree_path = find_tree_file(args.month)
    if not tree_path or not Path(tree_path).exists():
        print(f"错误: 文件不存在: {tree_path}")
        print("先运行 arxiv_collect.py 采集数据，或检查文件路径")
        return

    tree = json.loads(Path(tree_path).read_text(encoding="utf-8"))
    nodes = tree.get("nodes", [])
    month = tree.get("month", Path(tree_path).stem)

    # P0: 标注一致性校验
    consistency = check_wuxing_consistency(nodes, canonical, strict=not args.fix)
    if not consistency["consistent"]:
        if args.fix:
            apply_wuxing_fixes(nodes, canonical)
            print(f"[修复] {consistency['fix_count']} 处标注不一致:")
            for cat_id, (old, new) in consistency["mismatches"].items():
                print(f"  {cat_id}: {old}→{new}")
            # 回写
            tree["nodes"] = nodes
            tree["meta"] = tree.get("meta", {})
            tree["meta"]["wuxing_fixes_applied"] = consistency["fix_count"]
            tree["meta"]["wuxing_fix_details"] = consistency["fix_details"]
            tree["meta"]["wuxing_annotation_version"] = WUXING_ANNOTATION_VERSION
            tree["meta"]["wuxing_fixed_at"] = datetime.now().isoformat()
            Path(tree_path).write_text(json.dumps(tree, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  树文件已更新: {tree_path}")
        else:
            print(f"[警告] {consistency['fix_count']} 处标注不一致（用 --fix 自动修复）:")
            for cat_id, (old, new) in consistency["mismatches"].items():
                print(f"  {cat_id}: {old}→{new}")

    # 确保所有节点有标注
    for n in nodes:
        if not n.get("wuxing") or n["wuxing"] not in WUXING_ORDER:
            n["wuxing"] = canonical.get(n["id"], "土")

    # 诊断
    diag = adapter.diagnose(nodes)

    # 输出
    result = {
        "month": month,
        "source": tree.get("source", "arxiv_ai"),
        "diagnosis": diag,
        "meta": {
            "node_count": len(nodes),
            "total_weight": sum(n.get("weight", 0) for n in nodes),
            "wuxing_mapping": WUXING_ANNOTATION_SOURCE,
            "wuxing_annotation_version": WUXING_ANNOTATION_VERSION,
            "wuxing_annotation_rationale": WUXING_ANNOTATION_RATIONALE,
            "engine": diag.get("engine", "unknown"),
            "generated_at": datetime.now().isoformat(),
        },
    }

    # 如果 fix 过，记录修复详情
    if not consistency["consistent"]:
        result["meta"]["wuxing_fixes_applied"] = consistency["fix_count"]
        result["meta"]["wuxing_fix_details"] = consistency["fix_details"]

    # 输出文件名
    yyyymm = month.replace("-", "") if "-" in month else month
    out = output_dir / f"arxiv_diag_{yyyymm}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    # 控制台摘要
    print(f"\n=== arXiv AI 诊断 | {month} | 引擎: {diag.get('engine', 'unknown')} ===")
    print(f"标注版本: {WUXING_ANNOTATION_VERSION} ({WUXING_ANNOTATION_SOURCE})")
    print(f"五行分布: {diag.get('wuxing_dist', {})}")
    dims = diag.get("four_dims", {})
    print(f"四维指标: O_t={dims.get('O_t')} E_u={dims.get('E_u')} "
          f"C_k={dims.get('C_k')} K_y={dims.get('K_y')}")
    tracks = diag.get("tracks", {})
    conf = diag.get("S_p_confidence", {})
    print(f"S_p={tracks.get('S_p')}（effective_n={conf.get('effective_n')}，"
          f"信度={conf.get('confidence_level')}）")
    print(f"判语: {diag.get('verdict', '')}")
    print(f"输出: {out}")


if __name__ == "__main__":
    main()