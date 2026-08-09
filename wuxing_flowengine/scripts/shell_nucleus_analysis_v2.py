#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
shell_nucleus_analysis_v2.py —— C1 回归对比（P0-2）
=====================================================
读 engine_adapter_v2.py 输出的 engine_v2_series.json，
重跑壳核对比分析，回答核心问题：

  E_u 伪影消失后（真实引擎），壳核 S_p 收敛（32.5 vs 31.7）结论是否成立？

输出：
  1. 壳核 S_p 对照（v2 引擎 vs fallback 历史）
  2. 五行画像差异（v2 引擎下）
  3. 画像相似度（余弦/L1）
  4. 收敛结论判定

用法（置于 engine_v2_series.json 同目录）：
  python shell_nucleus_analysis_v2.py
"""

import json
import math
import sys
from pathlib import Path

WX_ORDER = ["木", "火", "土", "金", "水"]
# fallback 历史口径（来自壳核报告 V2 §4.1）
FALLBACK_HISTORY = {
    "baai": {"months": ["2026-05", "2026-06", "2026-07"], "S_p_mean": 32.50},
    "arxiv": {"months": ["2026-06", "2026-07", "2026-08"], "S_p_mean": 31.68},
}

def entropy(p_list):
    H = 0.0
    for p in p_list:
        if p > 0:
            H -= p * math.log2(p)
    return H

def main():
    path = Path("engine_v2_series.json")
    if not path.exists():
        print("❌ 未找到 engine_v2_series.json——先运行 engine_adapter_v2.py")
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    records = {r["source"]: r for r in data.get("records", [])}

    print("=" * 68)
    print("C1 回归对比：v2 真实引擎 vs fallback（壳核收敛结论验证）")
    print("=" * 68)

    # 1. S_p 对照
    print("\n[1] S_p 对照")
    print(f"{'源':<10}{'fallback均值':<14}{'v2(演化三层)':<16}{'Δ':<10}")
    for src in ["baai", "arxiv", "github", "huggingface"]:
        fb = FALLBACK_HISTORY.get(src, {}).get("S_p_mean")
        r = records.get(src)
        v2_sp = r["S_p"] if r else None
        fb_s = f"{fb}" if fb else "—"
        v2_s = f"{v2_sp}" if v2_sp is not None else "—"
        delta = f"{round(v2_sp - fb, 2)}" if (v2_sp is not None and fb) else "—"
        print(f"{src:<10}{fb_s:<14}{v2_s:<16}{delta:<10}")

    # 2. 壳核 S_p 差异判定
    print("\n[2] 壳核收敛结论判定")
    baai = records.get("baai")
    arxiv = records.get("arxiv")
    if baai and arxiv:
        diff = abs(baai["S_p"] - arxiv["S_p"])
        fb_diff = abs(FALLBACK_HISTORY["baai"]["S_p_mean"] - FALLBACK_HISTORY["arxiv"]["S_p_mean"])
        # 双口径：绝对差 + 相对差（以两者均值作分母）
        fb_mean = (FALLBACK_HISTORY["baai"]["S_p_mean"] + FALLBACK_HISTORY["arxiv"]["S_p_mean"]) / 2
        v2_mean = (baai["S_p"] + arxiv["S_p"]) / 2
        fb_rel = fb_diff / fb_mean * 100 if fb_mean > 0 else 0
        v2_rel = diff / v2_mean * 100 if v2_mean > 0 else 0
        print(f"  fallback 壳核差: 绝对 {fb_diff:.2f}（相对 {fb_rel:.1f}%，均值 {fb_mean:.2f}）")
        print(f"  v2 壳核差:       绝对 {diff:.2f}（相对 {v2_rel:.1f}%，均值 {v2_mean:.2f}）")
        print(f"  壳 S_p={baai['S_p']}  核 S_p={arxiv['S_p']}")
        if diff <= 5:
            verdict = "✅ 收敛结论仍成立（绝对差 < 5 点）——'同一存在度'升级为真信号"
        elif diff <= 10:
            verdict = "⚠️ 收敛减弱（绝对差 5-10 点）——'同一存在度'存疑，需更多月份"
        else:
            verdict = "❌ 收敛结论被推翻（绝对差 > 10 点）——'同一存在度'是 fallback 伪影"
        print(f"  判定: {verdict}")
        if v2_rel > fb_rel:
            print(f"  注意: v2 相对差 {v2_rel:.1f}% > fallback {fb_rel:.1f}%，因 v2 S_p 绝对值下移 ~4 倍，"
                  f"收敛以绝对差为准，相对差供参考")
    else:
        missing = [s for s in ["baai", "arxiv"] if s not in records]
        print(f"  ⚠️ 缺少源数据: {missing}——完整壳核对比需 BAAI + arXiv 生产数据")

    # 3. 五行画像差异（v2 引擎）
    print("\n[3] 五行画像差异（v2 引擎 dim1_freq, weight 加权）")
    for src in ["baai", "arxiv", "github", "huggingface"]:
        r = records.get(src)
        if not r:
            continue
        freq = r["v2_extra"]["dim1_freq"]
        dist = {w: freq[w]["pct"] * 100 for w in WX_ORDER}
        line = "  ".join(f"{w}:{dist[w]:.1f}%" for w in WX_ORDER)
        print(f"  {src:<12} dominant={r['dominant']:<3} {line}")

    # 4. 画像相似度（壳核）
    print("\n[4] 画像相似度（壳 vs 核）")
    if baai and arxiv:
        f1 = {w: baai["v2_extra"]["dim1_freq"][w]["pct"] for w in WX_ORDER}
        f2 = {w: arxiv["v2_extra"]["dim1_freq"][w]["pct"] for w in WX_ORDER}
        dot = sum(f1[w] * f2[w] for w in WX_ORDER)
        n1 = math.sqrt(sum(f1[w] ** 2 for w in WX_ORDER))
        n2 = math.sqrt(sum(f2[w] ** 2 for w in WX_ORDER))
        cos = dot / (n1 * n2) if n1 * n2 > 0 else 0
        l1 = sum(abs(f1[w] - f2[w]) for w in WX_ORDER)
        print(f"  余弦相似度: {cos:.4f}（V2 报告 fallback 口径 0.8910）")
        print(f"  L1 散度:    {l1:.4f}（V2 报告 fallback 口径 0.2000）")
        # 最大差异元素
        diffs = {w: (f1[w] - f2[w]) * 100 for w in WX_ORDER}
        top = sorted(diffs.items(), key=lambda kv: abs(kv[1]), reverse=True)[:3]
        print(f"  最大差异: " + ", ".join(f"{w} {d:+.1f}pp" for w, d in top))

    # 5. 演化边（时间演化模式的新信息）
    print("\n[5] 演化生克边（时间演化模式新增维度）")
    for src in ["baai", "arxiv", "github", "huggingface"]:
        r = records.get(src)
        if not r:
            continue
        edges = r["v2_extra"]["dim3_edges"]
        prof = r["v2_extra"]["dim3_profile"]
        if edges:
            es = "; ".join(f"{e['source']}─{e['type']}→{e['target']}" for e in edges)
            print(f"  {src:<12} path={prof['path']}  边: {es}")
        else:
            print(f"  {src:<12} path={prof['path']}  无演化边（月数不足或主导行无生克转换）")

    # 6. 汇总结论
    print("\n" + "=" * 68)
    print("[汇总]")
    if baai and arxiv:
        print("  - 完整壳核回归已执行（见 [2] 判定）")
    else:
        print("  - 本地缺少 BAAI/GitHub/HF 月度树——当前为 arXiv 单源演示")
        print("  - 生产侧完整回归: python engine_adapter_v2.py --dir <四源树目录> && python shell_nucleus_analysis_v2.py")
    print("=" * 68)


if __name__ == "__main__":
    main()
