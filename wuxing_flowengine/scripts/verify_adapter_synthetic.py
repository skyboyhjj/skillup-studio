# -*- coding: utf-8 -*-
"""EngineAdapterV2 机制验证：合成数据测生克演化（相生/相克/无演化三场景）"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'diagnose'))
from engine_adapter_v2 import EngineAdapterV2

adapter = EngineAdapterV2()

def make_month(weights):
    """weights: {id: (wuxing, weight)} → nodes"""
    return [{"id": k, "name": k, "parent": "r", "wuxing": w, "weight": v}
            for k, (w, v) in weights.items()]

# 场景 1：相生演化（木→火→土：木生火、火生土）
s1 = {
    "2026-06": make_month({"A": ("木", 100), "B": ("火", 20), "C": ("土", 10)}),
    "2026-07": make_month({"A": ("木", 30), "B": ("火", 100), "C": ("土", 20)}),
    "2026-08": make_month({"A": ("木", 20), "B": ("火", 30), "C": ("土", 100)}),
}
# 场景 2：相克演化（木→土→水：木克土、土克水）
s2 = {
    "2026-06": make_month({"A": ("木", 100), "B": ("土", 20), "C": ("水", 10)}),
    "2026-07": make_month({"A": ("木", 30), "B": ("土", 100), "C": ("水", 20)}),
    "2026-08": make_month({"A": ("木", 20), "B": ("土", 30), "C": ("水", 100)}),
}
# 场景 3：无演化（土→土→土）
s3 = {
    "2026-06": make_month({"A": ("土", 100), "B": ("木", 20)}),
    "2026-07": make_month({"A": ("土", 120), "B": ("木", 20)}),
    "2026-08": make_month({"A": ("土", 110), "B": ("木", 20)}),
}

print("=" * 72)
for name, series in [("场景1 相生演化(木→火→土)", s1),
                     ("场景2 相克演化(木→土→水)", s2),
                     ("场景3 无演化(土→土→土)", s3)]:
    diag = adapter.diagnose_source("test", series)
    fd = diag["four_dims"]
    ex = diag["v2_extra"]
    print(f"\n[{name}]")
    print(f"  四维: O_t={fd['O_t']} E_u={fd['E_u']} C_k={fd['C_k']} K_y={fd['K_y']} S_p={diag['S_p']} dom={diag['dominant']}")
    print(f"  演化边: {ex['dim3_edges']}")
    prof = ex["dim3_profile"]
    print(f"  路径: {prof['path']} 生={prof['sheng_count']} 克={prof['ke_count']} matches={prof['matches_profile']}")
    print(f"  dim4(层间重合度)={ex['dim4_entropy']['ratio']}  质心magnitude={ex['dim5_compass']['magnitude']}")
    print(f"  K_y增强: E_relation={ex['k_y_enhancer']['e_relation']}")

# 断言
print("\n" + "=" * 72)
print("[断言]")
d1 = adapter.diagnose_source("test", s1)
d2 = adapter.diagnose_source("test", s2)
d3 = adapter.diagnose_source("test", s3)

checks = [
    ("S1 相生演化 2 条边", len(d1["v2_extra"]["dim3_edges"]) == 2),
    ("S1 全相生 C_k=1.0", d1["four_dims"]["C_k"] == 1.0),
    ("S1 matches_profile=True", d1["v2_extra"]["dim3_profile"]["matches_profile"] is True),
    ("S2 相克演化 2 条边", len(d2["v2_extra"]["dim3_edges"]) == 2),
    ("S2 全相克 C_k=0.5", d2["four_dims"]["C_k"] == 0.5),
    ("S2 matches_profile=False", d2["v2_extra"]["dim3_profile"]["matches_profile"] is False),
    ("S3 无演化边", len(d3["v2_extra"]["dim3_edges"]) == 0),
    ("S3 C_k=0.0", d3["four_dims"]["C_k"] == 0.0),
    ("S1 C_k≠O_t 共线解除", d1["four_dims"]["C_k"] != d1["four_dims"]["O_t"]),
    ("S2 C_k≠O_t 共线解除", d2["four_dims"]["C_k"] != d2["four_dims"]["O_t"]),
    ("全部 K_y < 1.0 有区分度", all(d["four_dims"]["K_y"] < 1.0 for d in (d1, d2, d3))),
    ("S1 主导行=木或火（三层权重 150/150 并列，断言放宽）", d1["dominant"] in ("木", "火")),
]
passed = 0
for desc, ok in checks:
    print(f"  {'✅' if ok else '❌'} {desc}")
    passed += ok
print(f"\n通过 {passed}/{len(checks)}")
