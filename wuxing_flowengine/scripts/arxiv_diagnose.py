#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
arxiv_ai_tree_*.json → 五行诊断引擎接入脚本
=============================================
基于 docs/arxiv_diagnose.py 参考实现，适配实际项目格式。
修正了五行标注冲突（以参考版 AI_CATEGORY_WUXING 为 canonical）。

输入：arxiv_ai_tree_YYYYMM.json（四源 schema 节点树：11 分类 + weight）
输出：
  1. arxiv_diag_YYYYMM.json   单月诊断（七维指标 + four_dims + S_p + 信度）
  2. arxiv_series.json        多月时间序列（O_t/E_u/C_k/K_y 演化 + 重心路径）

引擎接入方式：
  - 优先复用项目现有诊断引擎（dao_math.compute_S_p + confidence_interval）
  - 四维计算使用 fallback 简化（v0.1_initial，标注待校准）
  - 真实引擎通过 EngineAdapter 对接，接口契约见 ENGINE_CONTRACT

用法（PowerShell）：
  cd wuxing_flowengine/scripts
  python arxiv_diagnose.py --month 2026-08
  python arxiv_diagnose.py --tree ../output/arxiv_ai_tree_202607.json
  python arxiv_diagnose.py --glob "../output/arxiv_ai_tree_*.json"
"""

import argparse
import glob as glob_mod
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

# 项目路径
SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPTS_DIR.parent
OUTPUT_DIR = PROJECT_DIR / "output"
sys.path.insert(0, str(SCRIPTS_DIR))

# ============ 五行标注表（canonical：参考 docs/arxiv_diagnose.py） ============
# 修正了与 scripts/arxiv_collect.py 中 classify_wuxing() 的 6 处冲突
# 标注原则：语义映射（参考语言树标注经验）
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

# 修正说明：与 arxiv_collect.py 中 classify_wuxing() 的差异
# 详见 docs/arxiv_diagnose.py 的 AI_CATEGORY_WUXING 注释
WUXING_FIX_LOG = {
    "cs.AI":   "水→火（AI 综合/扩散 > 语言流动，火更准确）",
    "cs.NE":   "土→水（神经进化是流动/演化，非基础承载）",
    "cs.MA":   "火→木（多智能体协作是生发，非交互活跃）",
    "cs.RO":   "木→金（机器人是执行控制，非感知生发）",
    "cs.IR":   "火→金（信息检索是筛选精确，非交互活跃）",
    "cs.MM":   "木→火（多媒体是多模态活跃，非感知生发）",
}

# 标注版本化（仲裁文档决议 3）
ANNOTATION_VERSION = "v1"
ANNOTATION_SOURCE = "AI_CATEGORY_WUXING"
ANNOTATION_RATIONALE = "语义映射：土=承载/水=流动/木=生发/金=结构/火=活跃"


# ============ 标注一致性校验（仲裁文档决议 2） ============
def check_wuxing_consistency(nodes, label="unknown"):
    """
    标注源一致性检查：防止标注分裂导致时间序列伪影。
    原则：宁可停，不产伪影。

    Args:
        nodes: 节点列表，每个节点需含 id 和 wuxing
        label: 上下文标签（月份或文件名），用于错误信息

    Raises:
        ValueError: 任一节点 wuxing 与 canonical 不一致
    """
    diff = {}
    for n in nodes:
        nid = n.get("id", "")
        if nid in AI_CATEGORY_WUXING:
            expected = AI_CATEGORY_WUXING[nid]
            actual = n.get("wuxing", "")
            if actual and actual != expected:
                diff[nid] = (expected, actual)
    if diff:
        details = ", ".join(f"{k}: expected={v[0]}, got={v[1]}" for k, v in diff.items())
        raise ValueError(
            f"[{label}] 标注源分裂 {len(diff)} 处: {details} —— "
            f"必须先统一标注源，禁止混用。"
        )
    return True


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
    "note": "真实引擎（wuxing_flowengine 的 diagnose）按此契约对接；EngineAdapter 自动适配",
}


# ============ 引擎适配层 ============
class EngineAdapter:
    """适配真实引擎；不可用时用 fallback（v0.1_initial 待校准）"""

    def __init__(self):
        self.engine_type = "fallback_v0.1_initial"
        self._try_real_engine()

    def _try_real_engine(self):
        """尝试导入项目现有诊断模块"""
        try:
            from dao_math import compute_S_p, S_P_DEFAULT, p_label
            from confidence_interval import wilson_interval
            self._compute_S_p = compute_S_p
            self._S_P_DEFAULT = S_P_DEFAULT
            self._p_label = p_label
            self._wilson_interval = wilson_interval
            self._has_real = True
        except ImportError:
            self._has_real = False

    def diagnose(self, nodes):
        """诊断入口：优先真实引擎，回退 fallback"""
        if self._has_real:
            return self._diagnose_with_real(nodes)
        return fallback_diagnose(nodes)

    def _diagnose_with_real(self, nodes):
        """使用项目现有模块计算（四维用 fallback 简化，S_p 用 dao_math）"""
        diag = fallback_diagnose(nodes)
        # 用 dao_math.compute_S_p 替换自实现的 S_p
        try:
            dims = [diag["four_dims"][k] for k in ["O_t", "E_u", "C_k", "K_y"]]
            S_p = round(self._compute_S_p(dims, p=self._S_P_DEFAULT), 2)
            diag["tracks"]["S_p"] = S_p
            diag["tracks"]["p_label"] = self._p_label(self._S_P_DEFAULT)
            diag["engine"] = "fallback_v0.1_initial+dao_math"
        except Exception:
            diag["engine"] = "fallback_v0.1_initial（dao_math 调用失败）"
        return diag


# ============ 统计工具 ============
def wilson_ci(k, n, z=1.96):
    """Wilson 置信区间（内置 fallback，不依赖 confidence_interval 模块）"""
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
    """Shannon 熵（log2）"""
    H = 0.0
    for p in p_list:
        if p > 0:
            H -= p * math.log2(p)
    return H


# ============ Fallback 诊断（v0.1_initial，待真实引擎校准） ============
def fallback_diagnose(nodes):
    """
    简化七维诊断——标注 v0.1_initial。
    真实引擎接入后替换此函数。
    """
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
    # E_u：1 - 熵归一化（熵越低越确定）
    E_u = round(1 - H_norm, 4)
    # C_k：分类耦合（同五行分类数 / 总分类数）
    wx_counts = Counter(n.get("wuxing", "土") for n in nodes)
    same_wuxing = max(wx_counts.values()) if wx_counts else 0
    C_k = round(same_wuxing / n_cat, 4) if n_cat > 0 else 0.0
    # K_y：因果纠缠（fallback：分类数密度，arXiv 树无结构边）
    K_y = round(min(1.0, n_cat / 11.0), 4)

    # --- D7 S_p（广义平均 p=0.5，scale=100）---
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
def build_series(tree_files):
    """多月时间序列：逐月诊断 → O_t/E_u/C_k/K_y 演化 + 重心路径"""
    adapter = EngineAdapter()
    series = []
    for f in sorted(tree_files):
        tree = json.loads(Path(f).read_text(encoding="utf-8"))
        nodes = tree.get("nodes", [])
        # 确保五行标注（树里 wuxing 可能为空或与 canonical 不一致，以 canonical 为准）
        for n in nodes:
            n["wuxing"] = AI_CATEGORY_WUXING.get(n["id"], n.get("wuxing", "土"))
        diag = adapter.diagnose(nodes)
        series.append({
            "month": tree.get("month", str(f)),
            "file": str(f),
            "four_dims": diag["four_dims"],
            "S_p": diag["tracks"]["S_p"],
            "dominant": diag["dominant"],
            "wuxing_dist": diag["wuxing_dist"],
        })
    path = [s["dominant"] for s in series]
    return {"series": series, "dominant_path": path}


# ============ 主流程 ============
def main():
    parser = argparse.ArgumentParser(description="arxiv_ai_tree → 五行诊断接入")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--tree", help="单个 arxiv_ai_tree 文件路径")
    group.add_argument("--month", help="月份 YYYY-MM，自动找 arxiv_ai_tree_YYYYMM.json")
    group.add_argument("--glob", default=None, help="多月 glob 模式")
    args = parser.parse_args()

    adapter = EngineAdapter()

    # ── 多月时间序列 ──
    if args.glob:
        files = sorted(glob_mod.glob(args.glob))
        if not files:
            print(f"ERROR: 无匹配文件: {args.glob}")
            return 1
        result = build_series(files)
        out = OUTPUT_DIR / "arxiv_series.json"
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"时间序列 {len(files)} 个月 → {out}")
        print("主导五行路径:", " → ".join(result["dominant_path"]))
        print("\n逐月 O_t/E_u/C_k/K_y:")
        for s in result["series"]:
            d = s["four_dims"]
            print(f"  {s['month']}: O_t={d['O_t']:.4f} E_u={d['E_u']:.4f} "
                  f"C_k={d['C_k']:.4f} K_y={d['K_y']:.4f} "
                  f"S_p={s['S_p']} 主导={s['dominant']}")
        return 0

    # ── 单月 ──
    tree_path = args.tree
    if args.month:
        ym = args.month.replace("-", "")
        tree_path = str(OUTPUT_DIR / f"arxiv_ai_tree_{ym}.json")

    if not Path(tree_path).exists():
        print(f"ERROR: 文件不存在: {tree_path}")
        print("请先运行 arxiv_collect.py --month YYYY-MM 采集数据")
        return 1

    tree = json.loads(Path(tree_path).read_text(encoding="utf-8"))
    nodes = tree.get("nodes", [])
    month = tree.get("month", args.month or "unknown")

    # 以 canonical 五行标注覆盖（修正 arxiv_collect.py 的标注）
    fix_count = 0
    for n in nodes:
        old_wx = n.get("wuxing", "")
        new_wx = AI_CATEGORY_WUXING.get(n["id"], old_wx)
        if old_wx and old_wx != new_wx:
            fix_count += 1
        n["wuxing"] = new_wx

    diag = adapter.diagnose(nodes)

    # 输出
    result = {
        "month": month,
        "source": tree.get("source", "arxiv_ai"),
        "diagnosis": diag,
        "meta": {
            "node_count": len(nodes),
            "total_weight": tree.get("meta", {}).get("total_weight", 0),
            "wuxing_mapping": "AI_CATEGORY_WUXING (canonical)",
            "wuxing_fixes_applied": fix_count,
            "wuxing_fix_details": WUXING_FIX_LOG if fix_count > 0 else {},
            "engine": diag["engine"],
            "generated_at": datetime.now().isoformat(),
        },
    }

    ym = month.replace("-", "")
    out = OUTPUT_DIR / f"arxiv_diag_{ym}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    # 控制台摘要
    print(f"{'='*64}")
    print(f"arXiv AI 五行诊断 | {month} | 引擎: {diag['engine']}")
    if fix_count > 0:
        print(f"五行标注修正: {fix_count}/11 分类（详见 meta.wuxing_fix_details）")
    print(f"{'='*64}")
    print(f"五行分布:")
    for wx in WUXING_ORDER:
        pct = diag["wuxing_dist"][wx] * 100
        bar = "█" * int(pct / 2)
        print(f"  {wx}: {pct:5.1f}% {bar}")
    print(f"\n四维指标:")
    print(f"  O_t={diag['four_dims']['O_t']:.4f}  E_u={diag['four_dims']['E_u']:.4f}  "
          f"C_k={diag['four_dims']['C_k']:.4f}  K_y={diag['four_dims']['K_y']:.4f}")
    print(f"  S_p={diag['tracks']['S_p']}  "
          f"(effective_n={diag['S_p_confidence']['effective_n']}, "
          f"信度={diag['S_p_confidence']['confidence_level']})")
    print(f"  判语: {diag['verdict']}")
    print(f"\n输出: {out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())