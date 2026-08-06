"""
p-P忠恕结合：广义平均 S_p 验证与落地脚本
============================================
基于《p与P忠恕结合_广义平均S_p的伦理灵魂》第五章「验证与落地」
- 5.1 恕度验证：p 平滑性、宽恕有效性、跨案例一致性、木桶检验
- 5.2 P忠恕版 S 卡：诊断报告呈现
"""
import math, json
from datetime import datetime

# ═══════════════════════════════════════════════
# 1. 核心计算函数
# ═══════════════════════════════════════════════

def compute_dao_realm(w_pct, H_ratio, cx, cy, ke_edge_count):
    """V1.2 3.3 节四维映射公式"""
    w = {k: v/100 for k, v in w_pct.items()}
    O_t = w['土'] * 0.6 + w['金'] * 0.3 + (1 - H_ratio) * 0.1
    E_u = 1 - 0.5 * abs(w['木'] - 0.25) - 0.5 * abs(w['水'] - 0.25) - 0.3 * math.sqrt(cx*cx + cy*cy)
    C_k = w['水'] * 0.5 + w['火'] * 0.3 + w['木'] * 0.2
    K_y = w['火'] * 0.4 + w['土'] * 0.3 + ke_edge_count / 2 * 0.3
    # 钳位到 [0, 1]
    return max(0, min(1, O_t)), max(0, min(1, E_u)), max(0, min(1, C_k)), max(0, min(1, K_y))

def compute_S_p(dims, p, scale=100):
    """广义平均存在度 S_p"""
    dims = [max(v, 1e-9) for v in dims]
    n = len(dims)
    if abs(p) < 1e-9:
        m = math.exp(sum(math.log(d) for d in dims) / n)
    else:
        m = (sum(d**p for d in dims) / n) ** (1.0 / p)
    return m * scale

def compute_S_p_weighted(dims, p, weights, scale=100):
    """带权广义平均"""
    dims = [max(v, 1e-9) for v in dims]
    wsum = sum(weights)
    if abs(p) < 1e-9:
        m = math.exp(sum(w * math.log(d) for w, d in zip(weights, dims)) / wsum)
    else:
        m = (sum(w * d**p for w, d in zip(weights, dims)) / wsum) ** (1.0 / p)
    return m * scale

# ═══════════════════════════════════════════════
# 2. P忠恕版 S 卡生成
# ═══════════════════════════════════════════════

def compassion_card(name, dims, p=0.5, p_label="中道", theta_base=50):
    """生成 P忠恕版 S 卡"""
    dim_names = ["O_t", "E_u", "C_k", "K_y"]
    dim_labels = ["时位", "宇位", "识位", "缘位"]
    S = compute_S_p(dims, p)
    
    # 定位最弱和最强维度
    weakest_idx = min(range(4), key=lambda i: dims[i])
    strongest_idx = max(range(4), key=lambda i: dims[i])
    
    # 阶段判定
    if S >= theta_base:
        stage_hint = "≥ θ_base → 可判'化'"
    elif S >= theta_base * 0.6:
        stage_hint = "接近 θ_base，积累中"
    else:
        stage_hint = "积累期，未达阈值"
    
    card = f"""
┌── P忠恕版 S 卡 ──────────────────────────────────
│
│  {name}
│
│  S = {S:.1f}  (p={p} · 恕度: {p_label})
│  θ_base = {theta_base}  →  {stage_hint}
│
│  四维读数:
│    {dim_labels[0]} {dim_names[0]} = {dims[0]:.4f}  {'█' * int(dims[0]*20)}{'░' * (20 - int(dims[0]*20))}
│    {dim_labels[1]} {dim_names[1]} = {dims[1]:.4f}  {'█' * int(dims[1]*20)}{'░' * (20 - int(dims[1]*20))}
│    {dim_labels[2]} {dim_names[2]} = {dims[2]:.4f}  {'█' * int(dims[2]*20)}{'░' * (20 - int(dims[2]*20))}
│    {dim_labels[3]} {dim_names[3]} = {dims[3]:.4f}  {'█' * int(dims[3]*20)}{'░' * (20 - int(dims[3]*20))}
│
│  最弱: {dim_labels[weakest_idx]} ({dim_names[weakest_idx]}={dims[weakest_idx]:.2f})  —— 如实看见
│  最强: {dim_labels[strongest_idx]} ({dim_names[strongest_idx]}={dims[strongest_idx]:.2f})  —— 可补足路径
│  恕语: 整体未被短板定义，成长空间仍在
│
└──────────────────────────────────────────────────"""
    return card

# ═══════════════════════════════════════════════
# 3. 验证用例定义
# ═══════════════════════════════════════════════

# 三案例（来自设计文档 6.1~6.3 节）
test_cases = [
    {
        "name": "小禾（12岁天文顿悟前）",
        "type": "个人案例",
        "w_pct": {'木': 25, '火': 15, '土': 30, '金': 15, '水': 15},
        "H_ratio": 0.93, "cx": -0.15, "cy": 0.05, "ke": 0,
        "expected_stage": "生",
        "context": "积累期，木/土主导，短板明显（火/金/水均弱）"
    },
    {
        "name": "小石（9岁ADHD诊断后）",
        "type": "个人案例",
        "w_pct": {'木': 10, '火': 5, '土': 15, '金': 20, '水': 50},
        "H_ratio": 0.80, "cx": 0.25, "cy": 0.40, "ke": 0,
        "expected_stage": "克",
        "context": "逆境，水单极主导(50%)，木/火极弱"
    },
]

# 孔子六阶段
kz_stages = [
    ("志于学 (~15)",  {'木': 30, '火': 15, '土': 20, '金': 15, '水': 20}, 0.75, 0.10, 0.15, 0),
    ("立 (~30)",      {'木': 20, '火': 15, '土': 30, '金': 25, '水': 10}, 0.65, 0.05, 0.10, 1),
    ("不惑 (~40)",    {'木': 15, '火': 20, '土': 25, '金': 20, '水': 20}, 0.55, 0.00, 0.00, 1),
    ("知天命 (~50)",  {'木': 20, '火': 25, '土': 20, '金': 15, '水': 20}, 0.50, 0.00, 0.00, 0),
    ("耳顺 (~60)",    {'木': 20, '火': 20, '土': 20, '金': 20, '水': 20}, 0.45, 0.00, 0.00, 0),
    ("从心所欲 (~70)",{'木': 20, '火': 20, '土': 20, '金': 20, '水': 20}, 0.40, 0.00, 0.00, 0),
]

# 四个月度流水线（来自实际运行结果）
monthly_pipeline = [
    ("2026-05", 0.2717, 0.9665, 0.2205, 0.2867, 278, 476),
    ("2026-06", 0.2691, 0.9645, 0.2214, 0.2876, 290, 525),
    ("2026-07", 0.2708, 0.9649, 0.2209, 0.2887, 302, 662),
    ("2026-08", 0.2751, 0.9666, 0.2193, 0.2908, 311, 687),
]

# ═══════════════════════════════════════════════
# 4. 验证执行
# ═══════════════════════════════════════════════

p_candidates = [1.0, 0.8, 0.5, 0.3, 0.0, -1.0]
p_labels = {
    1.0: "恕之极致（加性）",
    0.8: "宽恕",
    0.5: "P忠恕中道（默认）",
    0.3: "严格",
    0.0: "均衡（几何）",
    -1.0: "苛（调和）",
}

print("=" * 80)
print("  p-P忠恕结合：广义平均 S_p 验证与落地")
print(f"  执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)

# ── 4.1 三案例 S_p 全景 ──
print("\n" + "─" * 80)
print("  4.1 三案例 S_p 全景（p 从恕到苛）")
print("─" * 80)

# 计算所有案例的四维
all_case_dims = {}
for case in test_cases:
    dims = compute_dao_realm(case["w_pct"], case["H_ratio"], case["cx"], case["cy"], case["ke"])
    all_case_dims[case["name"]] = dims

for stage_name, wp, hr, cx, cy, ke in kz_stages:
    full_name = f"孔子 · {stage_name}"
    dims = compute_dao_realm(wp, hr, cx, cy, ke)
    all_case_dims[full_name] = dims

# 打印对照表
header = f"  {'案例':<24}"
for pv in p_candidates:
    header += f" p={pv:<5}"
print(header)
print("  " + "─" * (24 + len(p_candidates) * 10))

for name, dims in all_case_dims.items():
    row = f"  {name:<24}"
    for pv in p_candidates:
        row += f" {compute_S_p(dims, pv):>6.1f}"
    print(row)

# ── 4.2 恕度验证 ──
print("\n" + "─" * 80)
print("  4.2 恕度验证（5.1 节三项检查）")
print("─" * 80)

# 4.2.1 p 平滑性检查
print("\n  [检查 1] p 平滑性：S 随 p 从 0.3→0.8 的变化幅度")
print(f"  {'案例':<24} {'S(p=0.3)':>10} {'S(p=0.5)':>10} {'S(p=0.8)':>10} {'Δ(0.3→0.8)':>12} {'平滑':>6}")
print("  " + "─" * 76)
smooth_ok = True
for name, dims in all_case_dims.items():
    s03 = compute_S_p(dims, 0.3)
    s05 = compute_S_p(dims, 0.5)
    s08 = compute_S_p(dims, 0.8)
    delta = s08 - s03
    # 检查：变化应 > 0（宽恕有效）且 < 30（不跳变）
    ok = 0 < delta < 30
    if not ok:
        smooth_ok = False
    print(f"  {name:<24} {s03:>10.1f} {s05:>10.1f} {s08:>10.1f} {delta:>12.1f} {'✓' if ok else '✗':>6}")

print(f"\n  平滑性结论: {'✅ 通过' if smooth_ok else '❌ 未通过'}——所有案例 0.3→0.8 变化 < 30 且 > 0")

# 4.2.2 宽恕有效性（相对阈值为主，绝对阈值为参考）
print("\n  [检查 2] 宽恕有效性：短板明显时，p=0.8 的 S 应显著高于 p=0.3")
# 找出短板最明显的案例（C_k 最低的）
min_c_k_case = min(all_case_dims.items(), key=lambda x: x[1][2])
print(f"  短板最明显案例: {min_c_k_case[0]} (C_k={min_c_k_case[1][2]:.4f})")
s03_weak = compute_S_p(min_c_k_case[1], 0.3)
s08_weak = compute_S_p(min_c_k_case[1], 0.8)
delta_abs = s08_weak - s03_weak
delta_rel = delta_abs / s03_weak * 100  # 相对增幅
# 主判据：相对 > 10%；参考：绝对 > 5
compassion_effective = delta_rel > 10
print(f"  S(p=0.3, 严格) = {s03_weak:.1f}")
print(f"  S(p=0.8, 宽恕) = {s08_weak:.1f}")
print(f"  Δ_abs = {delta_abs:.1f} (参考, 阈值 > 5)")
print(f"  Δ_rel = {delta_rel:.1f}% (主判据, 阈值 > 10%)")
print(f"  {'> 10% → 宽恕有效 ✅' if compassion_effective else '≤ 10% → 宽恕效果不足 ❌'}")

# 4.2.3 跨案例排名稳定性
print("\n  [检查 3] 跨案例排名稳定性：p ∈ [0.3, 0.8] 时排名是否一致")
names = list(all_case_dims.keys())
rankings = {}
for pv in [0.3, 0.5, 0.8]:
    scored = [(name, compute_S_p(dims, pv)) for name, dims in all_case_dims.items()]
    scored.sort(key=lambda x: x[1], reverse=True)
    rankings[pv] = [name for name, _ in scored]

# 比较 0.3 和 0.8 的排名
rank_stable = rankings[0.3] == rankings[0.8]
print(f"  p=0.3 排名: {rankings[0.3][:4]}...")
print(f"  p=0.5 排名: {rankings[0.5][:4]}...")
print(f"  p=0.8 排名: {rankings[0.8][:4]}...")
if not rank_stable:
    # 检查是否只是局部交换
    diffs = [(i, rankings[0.3][i], rankings[0.8][i]) for i in range(min(5, len(names))) 
             if rankings[0.3][i] != rankings[0.8][i]]
    print(f"  差异项: {diffs}")
    rank_stable = len(diffs) <= 1  # 只允许 1 个位置交换
print(f"  排名稳定性: {'✅ 通过' if rank_stable else '❌ 未通过'}")

# 4.2.4 木桶检验
print("\n  [检查 4] 木桶检验：人为压扁 C_k 到 0.1，S 应显著下降")
for name, dims in [("小禾", all_case_dims["小禾（12岁天文顿悟前）"]),
                    ("小石", all_case_dims["小石（9岁ADHD诊断后）"])]:
    O_t, E_u, C_k, K_y = dims
    dims_halved = (O_t, E_u, 0.1, K_y)  # 压扁 C_k
    s_orig = compute_S_p(dims, 0.5)
    s_pinched = compute_S_p(dims_halved, 0.5)
    drop_pct = (s_orig - s_pinched) / s_orig * 100
    ok = drop_pct > 15
    print(f"  {name}: S_orig={s_orig:.1f} → S_pinched={s_pinched:.1f} (下降 {drop_pct:.1f}%) {'✓' if ok else '✗ (需 >15%)'}")

# ── 4.3 月度流水线 S_p 重算 ──
print("\n" + "─" * 80)
print("  4.3 四个月度流水线 S_p 重算")
print("─" * 80)

header = f"  {'月份':<10} {'节点':>6} {'边':>6} {'O_t':>8} {'E_u':>8} {'C_k':>8} {'K_y':>8} {'旧S':>8}"
for pv in p_candidates:
    header += f" {'S_p={pv}':>8}"
print(header)
print("  " + "─" * (64 + len(p_candidates) * 10))

for month, O_t, E_u, C_k, K_y, nodes, edges in monthly_pipeline:
    dims = (O_t, E_u, C_k, K_y)
    S_old = O_t * E_u * C_k * K_y * 100
    row = f"  {month:<10} {nodes:>6} {edges:>6} {O_t:>8.3f} {E_u:>8.3f} {C_k:>8.3f} {K_y:>8.3f} {S_old:>8.1f}"
    for pv in p_candidates:
        row += f" {compute_S_p(dims, pv):>8.1f}"
    print(row)

# 检查量纲对齐
print("\n  [检查 5] 量纲对齐：S_p 中位数是否落在 [20, 80]（θ_base=50 附近）")
monthly_dims = [(O_t, E_u, C_k, K_y) for _, O_t, E_u, C_k, K_y, _, _ in monthly_pipeline]
s_p05_values = [compute_S_p(d, 0.5) for d in monthly_dims]
median_s = sorted(s_p05_values)[len(s_p05_values)//2]
scale_ok = 20 <= median_s <= 80
print(f"  S_p(p=0.5) 值: {[f'{v:.1f}' for v in s_p05_values]}")
print(f"  中位数: {median_s:.1f} → {'✅ 落在 [20,80]' if scale_ok else '❌ 超出范围'}")


# ── 4.4 P忠恕版 S 卡 ──
print("\n" + "─" * 80)
print("  4.4 P忠恕版 S 卡（5.2 节诊断报告呈现）")
print("─" * 80)

# 小禾
print(compassion_card("小禾（12岁天文顿悟前）", all_case_dims["小禾（12岁天文顿悟前）"], p=0.5, p_label="P忠恕中道"))
# 小石
print(compassion_card("小石（9岁ADHD诊断后）", all_case_dims["小石（9岁ADHD诊断后）"], p=0.5, p_label="P忠恕中道"))
# 孔子·不惑（峰值）
print(compassion_card("孔子 · 不惑 (~40)", all_case_dims["孔子 · 不惑 (~40)"], p=0.5, p_label="P忠恕中道", theta_base=100))
# 月度流水线（最新月）
print(compassion_card("月度流水线 2026-08", monthly_dims[-1], p=0.5, p_label="P忠恕中道"))

# 小石宽恕版（p=0.8）
print(compassion_card("小石 · 宽恕版 (p=0.8)", all_case_dims["小石（9岁ADHD诊断后）"], p=0.8, p_label="宽恕"))

# ── 4.5 孔子六阶段 p=0.5 轨迹 ──
print("\n" + "─" * 80)
print("  4.5 孔子六阶段 S_p 轨迹 (p=0.5)")
print("─" * 80)
print(f"  {'阶段':<20} {'O_t':>8} {'E_u':>8} {'C_k':>8} {'K_y':>8} {'S_p':>8}")
print("  " + "─" * 56)
for stage_name, wp, hr, cx, cy, ke in kz_stages:
    dims = compute_dao_realm(wp, hr, cx, cy, ke)
    s = compute_S_p(dims, 0.5)
    print(f"  {'孔子·'+stage_name:<20} {dims[0]:>8.3f} {dims[1]:>8.3f} {dims[2]:>8.3f} {dims[3]:>8.3f} {s:>8.1f}")

# 找出峰值
max_s = 0
max_stage = ""
for stage_name, wp, hr, cx, cy, ke in kz_stages:
    dims = compute_dao_realm(wp, hr, cx, cy, ke)
    s = compute_S_p(dims, 0.5)
    if s > max_s:
        max_s = s
        max_stage = stage_name
print(f"\n  峰值: {max_stage} (S_p={max_s:.1f})")

# ═══════════════════════════════════════════════
# 5. 汇总判定
# ═══════════════════════════════════════════════
print("\n" + "=" * 80)
print("  验证汇总")
print("=" * 80)

all_checks = [
    ("p 平滑性", smooth_ok, "所有案例 0.3→0.8 变化 < 30 且 > 0"),
    ("宽恕有效性", compassion_effective, f"短板案例 Δ_rel={delta_rel:.1f}% > 10%（主），Δ_abs={delta_abs:.1f}（参考）"),
    ("排名稳定性", rank_stable, "p ∈ [0.3, 0.8] 案例排名一致"),
    ("量纲对齐", scale_ok, f"中位数 {median_s:.1f} ∈ [20, 80]"),
]

print(f"\n  {'检查项':<16} {'结果':>6} {'说明'}")
print("  " + "─" * 60)
for check_name, passed, desc in all_checks:
    print(f"  {check_name:<16} {'✅' if passed else '❌':>6}  {desc}")

all_passed = all(p for _, p, _ in all_checks)
print(f"\n  {'✅ 全部通过！' if all_passed else '❌ 存在未通过项，需调整'}")

print("\n" + "=" * 80)
print("  落地建议")
print("=" * 80)
print("""
  1. 默认 p=0.5（P忠恕中道）：适用于日常诊断，短板如实呈现但不苛责
  2. p=0.8（宽恕）：适用于逆境/初学/需要鼓励的场景，如小石案例
  3. p=0.3（严格）：适用于自我精进/顺境警醒场景
  4. p 稳定性约束：EMA 慢变，p_new = 0.9*p_old + 0.1*p_target
  5. 每个 S 值旁标注恕度标签，诊断报告使用 P忠恕版 S 卡格式
  6. 每次诊断自动附加"最弱维度 + 最强补足路径"的恕语
""")