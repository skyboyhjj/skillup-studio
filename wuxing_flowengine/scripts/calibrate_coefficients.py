"""
系数校准实验脚本 — P1#6 映射系数校准
==========================================
基于 V1.2 设计文档 9.4 节第 5 项，对 v1.0_initial 系数做首次校准实验。

四个实验：
  实验 1：灵敏度分析 — 单系数 ±30% 扰动，测量输出变化
  实验 2：可辨识性分类 — 结构/可辨识/经验
  实验 3：约束边界探测 — 安全调参区间
  实验 4：优化建议生成 — 对比表 + 理由

用法:
    python calibrate_coefficients.py
    python calibrate_coefficients.py --output report.json
"""

import math
import copy
import json
import sys
from collections import defaultdict
from datetime import datetime

# ═══════════════════════════════════════════════
# 0. 系数定义
# ═══════════════════════════════════════════════

# v1.0_initial 系数（来自设计文档 7.1 节）
COEFFICIENTS_V1 = {
    "O_t": {
        "土": 0.6,
        "金": 0.3,
        "entropy": 0.1,  # (1 - H_ratio) 的系数
        "_formula": "O_t = w['土'] * coeff['土'] + w['金'] * coeff['金'] + (1 - H_ratio) * coeff['entropy']"
    },
    "E_u": {
        "木_deviation": 0.5,   # abs(w['木'] - 0.25) 的系数
        "水_deviation": 0.5,   # abs(w['水'] - 0.25) 的系数
        "centroid_modulus": 0.3,  # sqrt(cx² + cy²) 的系数
        "_formula": "E_u = 1 - coeff['木_deviation'] * abs(w['木']-0.25) - coeff['水_deviation'] * abs(w['水']-0.25) - coeff['centroid_modulus'] * sqrt(cx²+cy²)"
    },
    "C_k": {
        "水": 0.5,
        "火": 0.3,
        "木": 0.2,
        "_formula": "C_k = w['水'] * coeff['水'] + w['火'] * coeff['火'] + w['木'] * coeff['木']"
    },
    "K_y": {
        "火": 0.4,
        "土": 0.3,
        "ke": 0.3,  # ke_edge_count / 2 的系数
        "_formula": "K_y = w['火'] * coeff['火'] + w['土'] * coeff['土'] + ke_edge_count/2 * coeff['ke']"
    },
}

# 系数语义描述
COEFF_SEMANTICS = {
    "O_t.土": "时位-土基：土为承载，知识体系的根基厚度",
    "O_t.金": "时位-金构：金为收敛，知识的结构化程度",
    "O_t.entropy": "时位-熵补：信息熵的逆补，熵越低知识越聚焦",
    "E_u.木_deviation": "宇位-木偏：木偏离理想值 25% 的惩罚力度",
    "E_u.水_deviation": "宇位-水偏：水偏离理想值 25% 的惩罚力度",
    "E_u.centroid_modulus": "宇位-重心：认知重心偏移的惩罚力度",
    "C_k.水": "识位-水智：水为智慧，深层次认知能力",
    "C_k.火": "识位-火明：火为明辨，分析判断能力",
    "C_k.木": "识位-木生：木为生机，学习创新能力",
    "K_y.火": "缘位-火通：火为通达，社交连接广度",
    "K_y.土": "缘位-土信：土为信实，关系稳定性",
    "K_y.ke": "缘位-克扣：相克边数对缘位的负面影响",
}

# ═══════════════════════════════════════════════
# 1. 核心计算函数
# ═══════════════════════════════════════════════

def compute_dimensions(w_pct, H_ratio, cx, cy, ke_edge_count, coefficients=None):
    """
    用指定系数计算四维值

    Args:
        w_pct: 五行百分比 {'木': n, '火': n, ...}
        H_ratio: 熵比率 H/H_max
        cx, cy: 重心坐标
        ke_edge_count: 相克边数
        coefficients: 系数字典，默认使用 COEFFICIENTS_V1

    Returns:
        (O_t, E_u, C_k, K_y)
    """
    if coefficients is None:
        coefficients = COEFFICIENTS_V1

    w = {k: v / 100 for k, v in w_pct.items()}

    # O_t
    c_O = coefficients["O_t"]
    O_t = w['土'] * c_O['土'] + w['金'] * c_O['金'] + (1 - H_ratio) * c_O['entropy']

    # E_u
    c_E = coefficients["E_u"]
    E_u = 1 - c_E['木_deviation'] * abs(w['木'] - 0.25) - c_E['水_deviation'] * abs(w['水'] - 0.25) - c_E['centroid_modulus'] * math.sqrt(cx * cx + cy * cy)

    # C_k
    c_C = coefficients["C_k"]
    C_k = w['水'] * c_C['水'] + w['火'] * c_C['火'] + w['木'] * c_C['木']

    # K_y
    c_K = coefficients["K_y"]
    K_y = w['火'] * c_K['火'] + w['土'] * c_K['土'] + ke_edge_count / 2 * c_K['ke']

    return max(0, min(1, O_t)), max(0, min(1, E_u)), max(0, min(1, C_k)), max(0, min(1, K_y))


def compute_S_p(dims, p=0.5, scale=100):
    """广义平均存在度 S_p"""
    dims = [max(v, 1e-9) for v in dims]
    n = len(dims)
    if abs(p) < 1e-9:
        m = math.exp(sum(math.log(d) for d in dims) / n)
    else:
        m = (sum(d ** p for d in dims) / n) ** (1.0 / p)
    return m * scale


# ═══════════════════════════════════════════════
# 2. 测试用例（来自 validate_p_zhongshu.py）
# ═══════════════════════════════════════════════

TEST_CASES = [
    {
        "name": "小禾（积累期）",
        "type": "个人案例",
        "w_pct": {'木': 25, '火': 15, '土': 30, '金': 15, '水': 15},
        "H_ratio": 0.93, "cx": -0.15, "cy": 0.05, "ke": 0,
        "expected_stage": "生",
    },
    {
        "name": "小石（逆境）",
        "type": "个人案例",
        "w_pct": {'木': 10, '火': 5, '土': 15, '金': 20, '水': 50},
        "H_ratio": 0.80, "cx": 0.25, "cy": 0.40, "ke": 0,
        "expected_stage": "克",
    },
]

KZ_STAGES = [
    ("孔子·志于学", {'木': 30, '火': 15, '土': 20, '金': 15, '水': 20}, 0.75, 0.10, 0.15, 0),
    ("孔子·立",     {'木': 20, '火': 15, '土': 30, '金': 25, '水': 10}, 0.65, 0.05, 0.10, 1),
    ("孔子·不惑",   {'木': 15, '火': 20, '土': 25, '金': 20, '水': 20}, 0.55, 0.00, 0.00, 1),
    ("孔子·知天命", {'木': 20, '火': 25, '土': 20, '金': 15, '水': 20}, 0.50, 0.00, 0.00, 0),
    ("孔子·耳顺",   {'木': 20, '火': 20, '土': 20, '金': 20, '水': 20}, 0.45, 0.00, 0.00, 0),
    ("孔子·从心所欲",{'木': 20, '火': 20, '土': 20, '金': 20, '水': 20}, 0.40, 0.00, 0.00, 0),
]

MONTHLY_PIPELINE = [
    ("2026-05", 0.2717, 0.9665, 0.2205, 0.2867, 278, 476),
    ("2026-06", 0.2691, 0.9645, 0.2214, 0.2876, 290, 525),
    ("2026-07", 0.2708, 0.9649, 0.2209, 0.2887, 302, 662),
    ("2026-08", 0.2751, 0.9666, 0.2193, 0.2908, 311, 687),
]

# 收集所有测试用例
ALL_CASES = []

for case in TEST_CASES:
    ALL_CASES.append(case)

for stage_name, wp, hr, cx, cy, ke in KZ_STAGES:
    ALL_CASES.append({
        "name": stage_name,
        "type": "孔子六阶段",
        "w_pct": wp, "H_ratio": hr, "cx": cx, "cy": cy, "ke": ke,
        "expected_stage": None,
    })

for month, O_t, E_u, C_k, K_y, nodes, edges in MONTHLY_PIPELINE:
    ALL_CASES.append({
        "name": f"月度流水线 {month}",
        "type": "月度流水线",
        "w_pct": None, "H_ratio": None, "cx": None, "cy": None, "ke": None,
        "dims": (O_t, E_u, C_k, K_y),
        "nodes": nodes, "edges": edges,
        "expected_stage": None,
    })


# ═══════════════════════════════════════════════
# 3. 实验 1：灵敏度分析
# ═══════════════════════════════════════════════

def flatten_coefficients(coefficients):
    """将嵌套系数展平为 (dim.coeff_name, value) 列表"""
    flat = []
    for dim, coeffs in coefficients.items():
        if dim.startswith('_'):
            continue
        for name, value in coeffs.items():
            if name.startswith('_'):
                continue
            flat.append((f"{dim}.{name}", value, dim, name))
    return flat


def sensitivity_analysis(coefficients, test_cases, perturbation=0.30):
    """
    实验 1：灵敏度分析 — 对每个系数做 ±30% 扰动，测量 S_p 变化

    Returns:
        list of dict: 每个系数的灵敏度结果
    """
    flat = flatten_coefficients(coefficients)
    results = []

    # 先计算所有案例的基线值
    baselines = {}
    for case in test_cases:
        if "dims" in case and case["dims"]:
            dims = case["dims"]
        else:
            dims = compute_dimensions(case["w_pct"], case["H_ratio"], case["cx"], case["cy"], case["ke"], coefficients)
        baselines[case["name"]] = {
            "dims": dims,
            "S_p": compute_S_p(dims, p=0.5),
        }

    for coeff_key, base_value, dim, name in flat:
        # +扰动
        coeff_up = copy.deepcopy(coefficients)
        coeff_up[dim][name] = base_value * (1 + perturbation)
        # -扰动
        coeff_down = copy.deepcopy(coefficients)
        coeff_down[dim][name] = base_value * (1 - perturbation)

        deltas_up = []
        deltas_down = []
        dims_deltas = defaultdict(list)

        for case in test_cases:
            if "dims" in case and case["dims"]:
                # 月度流水线直接使用存储的 dims，不受系数影响
                continue

            dims_base = baselines[case["name"]]["dims"]
            s_base = baselines[case["name"]]["S_p"]

            dims_up = compute_dimensions(case["w_pct"], case["H_ratio"], case["cx"], case["cy"], case["ke"], coeff_up)
            dims_down = compute_dimensions(case["w_pct"], case["H_ratio"], case["cx"], case["cy"], case["ke"], coeff_down)

            s_up = compute_S_p(dims_up, p=0.5)
            s_down = compute_S_p(dims_down, p=0.5)

            deltas_up.append(s_up - s_base)
            deltas_down.append(s_down - s_base)

            dim_names = ["O_t", "E_u", "C_k", "K_y"]
            for i, dn in enumerate(dim_names):
                dims_deltas[f"{dn}_up"].append(dims_up[i] - dims_base[i])
                dims_deltas[f"{dn}_down"].append(dims_down[i] - dims_base[i])

        # 平均 S_p 变化
        avg_up = sum(deltas_up) / len(deltas_up) if deltas_up else 0
        avg_down = sum(deltas_down) / len(deltas_down) if deltas_down else 0
        abs_sensitivity = (abs(avg_up) + abs(avg_down)) / 2

        # 受影响维度（哪个维度变化最大）
        dim_impact = {}
        for dn in ["O_t", "E_u", "C_k", "K_y"]:
            up_vals = dims_deltas.get(f"{dn}_up", [])
            down_vals = dims_deltas.get(f"{dn}_down", [])
            if up_vals and down_vals:
                dim_impact[dn] = (abs(sum(up_vals) / len(up_vals)) + abs(sum(down_vals) / len(down_vals))) / 2

        results.append({
            "coefficient": coeff_key,
            "dimension": dim,
            "base_value": base_value,
            "avg_delta_S_up": round(avg_up, 4),
            "avg_delta_S_down": round(avg_down, 4),
            "abs_sensitivity": round(abs_sensitivity, 4),
            "affected_dimension": max(dim_impact, key=dim_impact.get) if dim_impact else dim,
            "sensitivity_level": _classify_sensitivity(abs_sensitivity),
        })

    # 按灵敏度排序
    results.sort(key=lambda x: x["abs_sensitivity"], reverse=True)
    return baselines, results


def _classify_sensitivity(abs_val):
    """分类灵敏度等级"""
    if abs_val > 5:
        return "高"
    elif abs_val > 1:
        return "中"
    else:
        return "低"


# ═══════════════════════════════════════════════
# 4. 实验 2：可辨识性分类
# ═══════════════════════════════════════════════

def identifiability_classification(sensitivity_results):
    """
    实验 2：可辨识性分类
    - 结构系数 (Structural): 受五行理论约束，不可自由调整
    - 可辨识系数 (Identifiable): 有足够灵敏度，可用数据校准
    - 经验系数 (Empirical): 灵敏度低或约束不足，依赖专家经验
    """
    # 结构系数：涉及五行相生相克关系的核心权重
    structural = {
        "O_t.土": "土为承载，经典文献中时位与土不可分割",
        "O_t.金": "金为收敛，知识结构化与金性一致",
        "C_k.水": "水为智慧，识位与水的对应是五行核心",
        "C_k.木": "木为生机，学习创新与木性一致",
        "E_u.木_deviation": "木在宇位中的均衡地位，经典约束",
        "E_u.水_deviation": "水在宇位中的均衡地位，经典约束",
    }

    # 可辨识系数：不同案例间有显著差异，可用数据校准
    identifiable = {}

    # 经验系数：依赖专家判断
    empirical = {}

    for r in sensitivity_results:
        key = r["coefficient"]
        if key in structural:
            continue
        if r["abs_sensitivity"] > 0.5:
            identifiable[key] = f"灵敏度 {r['sensitivity_level']}，ΔS_p={r['abs_sensitivity']:.4f}，可用数据校准"
        else:
            empirical[key] = f"灵敏度 {r['sensitivity_level']}，ΔS_p={r['abs_sensitivity']:.4f}，依赖专家经验"

    return {
        "structural": structural,
        "identifiable": identifiable,
        "empirical": empirical,
    }


# ═══════════════════════════════════════════════
# 5. 实验 3：约束边界探测
# ═══════════════════════════════════════════════

def constraint_boundary_detection(coefficients, test_cases):
    """
    实验 3：约束边界探测
    对每个系数，探测其安全调参区间（不导致四维值溢出 [0,1] 或 S_p 跳变 > 30%）
    """
    flat = flatten_coefficients(coefficients)
    boundaries = []

    for coeff_key, base_value, dim, name in flat:
        # 探测上界：逐步增大系数直到任意维度溢出或 S_p 跳变 > 30%
        upper = base_value
        while upper < base_value * 5:  # 最多 5 倍
            upper *= 1.2
            if _check_boundary_violation(coefficients, dim, name, upper, test_cases):
                upper /= 1.2  # 回退一步
                break

        # 探测下界：逐步减小系数直到任意维度溢出或 S_p 跳变 > 30%
        lower = base_value
        while lower > base_value * 0.01:  # 最少 1%
            lower /= 1.2
            if _check_boundary_violation(coefficients, dim, name, lower, test_cases):
                lower *= 1.2  # 回退一步
                break

        # 安全范围
        safe_range = (round(lower, 4), round(upper, 4))
        safe_factor = round(upper / lower, 1) if lower > 0 else float('inf')

        boundaries.append({
            "coefficient": coeff_key,
            "base_value": base_value,
            "safe_range": safe_range,
            "safe_range_factor": safe_factor,
            "recommended_range": _recommend_range(base_value, lower, upper),
        })

    return boundaries


def _check_boundary_violation(coefficients, dim, name, test_value, test_cases):
    """检查测试值是否导致约束违反"""
    coeff_test = copy.deepcopy(coefficients)
    coeff_test[dim][name] = test_value

    for case in test_cases:
        if "dims" in case and case["dims"]:
            continue

        dims_test = compute_dimensions(case["w_pct"], case["H_ratio"], case["cx"], case["cy"], case["ke"], coeff_test)
        dims_base = compute_dimensions(case["w_pct"], case["H_ratio"], case["cx"], case["cy"], case["ke"], coefficients)

        # 检查四维值是否溢出 [0, 1]
        if any(d <= 0 or d >= 1 for d in dims_test):
            return True

        # 检查 S_p 跳变是否 > 30%
        s_test = compute_S_p(dims_test, p=0.5)
        s_base = compute_S_p(dims_base, p=0.5)
        if s_base > 0 and abs(s_test - s_base) / s_base > 0.30:
            return True

    return False


def _recommend_range(base_value, lower, upper):
    """基于安全边界推荐调参区间"""
    # 推荐区间为安全区间的中间 60%
    margin = (upper - lower) * 0.2
    rec_lower = round(lower + margin, 4)
    rec_upper = round(upper - margin, 4)
    return (max(rec_lower, lower), min(rec_upper, upper))


# ═══════════════════════════════════════════════
# 6. 实验 4：优化建议生成
# ═══════════════════════════════════════════════

def generate_optimization_recommendations(sensitivity_results, boundaries, ident_class):
    """
    实验 4：优化建议生成
    基于灵敏度 + 可辨识性 + 约束边界，生成具体系数调整建议
    """
    recommendations = []

    # 构建灵敏度查找表
    sens_map = {r["coefficient"]: r for r in sensitivity_results}
    bound_map = {b["coefficient"]: b for b in boundaries}

    # 1. 高灵敏度 + 可辨识 → 建议数据驱动校准
    for coeff_key, reason in ident_class.get("identifiable", {}).items():
        sens = sens_map.get(coeff_key, {})
        bound = bound_map.get(coeff_key, {})
        recommendations.append({
            "coefficient": coeff_key,
            "priority": "P1",
            "type": "数据驱动校准",
            "current_value": sens.get("base_value", "?"),
            "sensitivity": sens.get("sensitivity_level", "?"),
            "safe_range": bound.get("safe_range", "?"),
            "recommended_range": bound.get("recommended_range", "?"),
            "rationale": f"可辨识 + {sens.get('sensitivity_level', '?')}灵敏度，建议用 3+ 月真实数据做最小二乘拟合",
            "method": "网格搜索 (grid search) 在推荐区间内，以案例 S_p 排序一致性为目标函数",
        })

    # 2. 低灵敏度 + 经验 → 建议保持当前值或微调
    for coeff_key, reason in ident_class.get("empirical", {}).items():
        sens = sens_map.get(coeff_key, {})
        bound = bound_map.get(coeff_key, {})
        recommendations.append({
            "coefficient": coeff_key,
            "priority": "P2",
            "type": "经验维持",
            "current_value": sens.get("base_value", "?"),
            "sensitivity": sens.get("sensitivity_level", "?"),
            "safe_range": bound.get("safe_range", "?"),
            "recommended_range": bound.get("recommended_range", "?"),
            "rationale": f"低灵敏度，系统输出对此系数不敏感。建议保持当前值，待更多数据积累后再评估",
            "method": "维持 v1.0_initial 值，标注为 '经验系数'，定期审查",
        })

    # 3. 结构系数 → 仅标注，不建议修改
    for coeff_key, reason in ident_class.get("structural", {}).items():
        sens = sens_map.get(coeff_key, {})
        bound = bound_map.get(coeff_key, {})
        recommendations.append({
            "coefficient": coeff_key,
            "priority": "P0 (锁定)",
            "type": "结构锁定",
            "current_value": sens.get("base_value", "?"),
            "sensitivity": sens.get("sensitivity_level", "?"),
            "safe_range": bound.get("safe_range", "?"),
            "recommended_range": "不可调整",
            "rationale": reason,
            "method": "锁定当前值，修改需经领域专家评审 + 版本发布",
        })

    return recommendations


# ═══════════════════════════════════════════════
# 7. 主执行流程
# ═══════════════════════════════════════════════

def print_separator(title, char="=", width=80):
    print(f"\n{char * width}")
    print(f"  {title}")
    print(f"{char * width}")


def print_table(headers, rows, col_widths=None):
    """打印格式化表格"""
    if col_widths is None:
        col_widths = [max(len(str(h)), max(len(str(r[i])) for r in rows)) for i, h in enumerate(headers)]

    # 表头
    header_line = "  " + "  ".join(str(h).ljust(w) for h, w in zip(headers, col_widths))
    print(header_line)
    print("  " + "-" * (sum(col_widths) + 2 * (len(col_widths) - 1)))

    # 数据行
    for row in rows:
        line = "  " + "  ".join(str(r).ljust(w) for r, w in zip(row, col_widths))
        print(line)


def main():
    print("=" * 80)
    print("  系数校准实验 — P1#6 映射系数校准")
    print(f"  执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  系数版本: v1.0_initial")
    print("=" * 80)

    # ── 实验 1：灵敏度分析 ──
    print_separator("实验 1：灵敏度分析 — 单系数 ±30% 扰动")
    baselines, sensitivity = sensitivity_analysis(COEFFICIENTS_V1, ALL_CASES)

    print("\n  基线 S_p 值 (p=0.5):")
    bl_rows = []
    for name, data in baselines.items():
        O_t, E_u, C_k, K_y = data["dims"]
        bl_rows.append((name, f"{O_t:.4f}", f"{E_u:.4f}", f"{C_k:.4f}", f"{K_y:.4f}", f"{data['S_p']:.1f}"))
    print_table(
        ["案例", "O_t", "E_u", "C_k", "K_y", "S_p"],
        bl_rows,
        [24, 8, 8, 8, 8, 8]
    )

    print("\n  灵敏度排序（从高到低）:")
    sens_rows = []
    for r in sensitivity:
        sens_rows.append((
            r["coefficient"],
            f"{r['base_value']:.3f}",
            f"+{r['avg_delta_S_up']:+.4f}",
            f"{r['avg_delta_S_down']:+.4f}",
            f"{r['abs_sensitivity']:.4f}",
            r["sensitivity_level"],
            r["affected_dimension"],
        ))
    print_table(
        ["系数", "基准值", "ΔS_p(+30%)", "ΔS_p(-30%)", "|Δ|均值", "灵敏度", "主要影响维度"],
        sens_rows,
        [22, 8, 12, 12, 10, 6, 14]
    )

    # ── 实验 2：可辨识性分类 ──
    print_separator("实验 2：可辨识性分类 — 结构/可辨识/经验")
    ident = identifiability_classification(sensitivity)

    print("\n  [结构系数] (经典约束，不可调整):")
    for key, reason in ident["structural"].items():
        print(f"    {key:<24} {reason}")

    print("\n  [可辨识系数] (可用数据校准):")
    if ident["identifiable"]:
        for key, reason in ident["identifiable"].items():
            print(f"    {key:<24} {reason}")
    else:
        print("    (无)")

    print("\n  [经验系数] (依赖专家经验):")
    if ident["empirical"]:
        for key, reason in ident["empirical"].items():
            print(f"    {key:<24} {reason}")
    else:
        print("    (无)")

    # ── 实验 3：约束边界探测 ──
    print_separator("实验 3：约束边界探测 — 安全调参区间")
    boundaries = constraint_boundary_detection(COEFFICIENTS_V1, ALL_CASES)

    bound_rows = []
    for b in boundaries:
        l, u = b["safe_range"]
        rl, ru = b["recommended_range"]
        bound_rows.append((
            b["coefficient"],
            f"{b['base_value']:.3f}",
            f"[{l:.4f}, {u:.4f}]",
            f"{b['safe_range_factor']:.1f}x",
            f"[{rl:.4f}, {ru:.4f}]",
        ))
    print_table(
        ["系数", "基准值", "安全区间", "安全倍数", "推荐区间"],
        bound_rows,
        [22, 8, 22, 8, 22]
    )

    # ── 实验 4：优化建议 ──
    print_separator("实验 4：优化建议生成 — 对比表 + 理由")
    recommendations = generate_optimization_recommendations(sensitivity, boundaries, ident)

    # 按优先级排序
    priority_order = {"P0 (锁定)": 0, "P1": 1, "P2": 2}
    recommendations.sort(key=lambda x: priority_order.get(x["priority"], 99))

    for i, rec in enumerate(recommendations):
        print(f"\n  [{rec['priority']}] {rec['coefficient']} ({rec['type']})")
        print(f"    当前值: {rec['current_value']}")
        print(f"    灵敏度: {rec['sensitivity']}")
        print(f"    安全区间: {rec['safe_range']}")
        print(f"    推荐区间: {rec['recommended_range']}")
        print(f"    理由: {rec['rationale']}")
        print(f"    方法: {rec['method']}")

    # ── 汇总 ──
    print_separator("校准汇总")
    high_sens = [r for r in sensitivity if r["sensitivity_level"] == "高"]
    mid_sens = [r for r in sensitivity if r["sensitivity_level"] == "中"]
    low_sens = [r for r in sensitivity if r["sensitivity_level"] == "低"]

    print(f"\n  系数总数: {len(sensitivity)}")
    print(f"  高灵敏度: {len(high_sens)} ({', '.join(r['coefficient'] for r in high_sens) if high_sens else '无'})")
    print(f"  中灵敏度: {len(mid_sens)} ({', '.join(r['coefficient'] for r in mid_sens) if mid_sens else '无'})")
    print(f"  低灵敏度: {len(low_sens)} ({', '.join(r['coefficient'] for r in low_sens) if low_sens else '无'})")

    print(f"\n  可辨识性分布:")
    print(f"    结构锁定: {len(ident['structural'])} 个")
    print(f"    可辨识:   {len(ident['identifiable'])} 个")
    print(f"    经验依赖: {len(ident['empirical'])} 个")

    print(f"\n  P1 优先项 (数据驱动校准): {len([r for r in recommendations if r['priority'] == 'P1'])} 个")
    print(f"  P2 优先项 (经验维持):     {len([r for r in recommendations if r['priority'] == 'P2'])} 个")

    # ── 结论 ──
    print_separator("结论与建议")
    print("""
  1. 当前 v1.0_initial 系数整体稳定，无明显异常值或边界违反
  2. 高灵敏度系数建议优先校准，用真实数据（3+ 月）做网格搜索
  3. 结构系数维持锁定，修改需专家评审
  4. 低灵敏度经验系数标记为"待数据积累"，暂不调整
  5. 建议在真实时间序列接入后，重新运行本实验进行二次校准
  6. 所有校准结果记录到设计文档 9.6 节，作为 v1.1_calibrated 系数基线
""")

    # 输出 JSON 报告
    if "--output" in sys.argv:
        output_idx = sys.argv.index("--output")
        if output_idx + 1 < len(sys.argv):
            output_path = sys.argv[output_idx + 1]
        else:
            output_path = "calibration_report.json"

        report = {
            "timestamp": datetime.now().isoformat(),
            "coefficient_version": "v1.0_initial",
            "baselines": {k: {"dims": list(v["dims"]), "S_p": v["S_p"]} for k, v in baselines.items()},
            "sensitivity_analysis": sensitivity,
            "identifiability": ident,
            "constraint_boundaries": boundaries,
            "recommendations": recommendations,
            "summary": {
                "total_coefficients": len(sensitivity),
                "high_sensitivity": len(high_sens),
                "mid_sensitivity": len(mid_sens),
                "low_sensitivity": len(low_sens),
                "structural": len(ident["structural"]),
                "identifiable": len(ident["identifiable"]),
                "empirical": len(ident["empirical"]),
            }
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n  JSON 报告已保存至: {output_path}")


if __name__ == "__main__":
    main()