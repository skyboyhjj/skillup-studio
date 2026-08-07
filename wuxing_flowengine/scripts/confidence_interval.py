"""
信度区间计算模块 — 不确定微分几何的工程实现
=============================================
基于不确定理论的核心原则：数据不足时不"强做可知"，用信度区间替代点估计。

核心功能：
1. Wilson 二项比例区间 — 小样本下自动展宽、大样本下自动收窄
2. 五行诊断信度输出 — 每个五行的点估计 + 95% 信度区间
3. 漂移信度加权 — 小样本领域漂移标注低置信度
4. 样本量→置信度映射 — 统一的信度等级判定

理论依据：
- 不确定微分几何的"可信边界"概念：不计算概率分布，只计算可信区间
- 与五行诊断的"阈值/区间"哲学一致：阶段判定本身就是"边界思维"
- 直接解决 P1#4：小样本领域漂移不稳定 → 给这些领域打宽信度区间

用法:
    from confidence_interval import (
        wuxing_confidence_interval, drift_confidence,
        sample_confidence_level, wilson_interval
    )
    ci = wuxing_confidence_interval({"水": 0.261, "土": 0.254}, node_count=30)
"""

import math

# ============================================================
# 基础工具
# ============================================================

Z_95 = 1.96  # 95% 置信水平的 z 值


def wilson_interval(proportion, n, z=Z_95):
    """
    Wilson 二项比例置信区间。
    
    相比简单的 ±1/√n 近似，Wilson 区间在 p 接近 0 或 1 时表现更好，
    且在小样本下自动展宽、大样本下自动收窄。
    
    公式:
        p_hat = (x + z²/2) / (n + z²)
        margin = z * sqrt((p_hat*(1-p_hat) + z²/(4n)) / n) / (1 + z²/n)
        ci = [p_hat - margin, p_hat + margin]
    
    Args:
        proportion: 点估计比例，∈ [0, 1]
        n: 样本量
        z: z 值，默认 1.96（95% 置信水平）
    
    Returns:
        (ci_low, ci_high): 置信区间下界和上界，裁剪到 [0, 1]
    """
    if n <= 0:
        return (0.0, 1.0)  # 无样本时完全不确定
    
    proportion = max(0.0, min(1.0, proportion))  # 裁剪到 [0, 1]
    x = proportion * n
    p_hat = (x + z**2 / 2) / (n + z**2)
    # 防止浮点精度导致 sqrt 参数为负
    inner = (p_hat * (1 - p_hat) + z**2 / (4 * n)) / n
    inner = max(0.0, inner)
    margin = z * math.sqrt(inner)
    margin /= (1 + z**2 / n)
    
    ci_low = max(0.0, p_hat - margin)
    ci_high = min(1.0, p_hat + margin)
    return (round(ci_low, 4), round(ci_high, 4))


def sample_confidence_level(node_count):
    """
    样本量→置信度等级映射。
    
    | 样本量 | 等级 | 语义 |
    |--------|:---:|------|
    | < 10   | 低 | 数据不足，不假装精确 |
    | 10-50  | 中 | 有一定参考价值 |
    | > 50   | 高 | 相对确定 |
    | = 0    | 无 | 无数据 |
    
    Args:
        node_count: 节点/样本数量
    
    Returns:
        {"level": "低/中/高/无", "score": 0.0-1.0 置信度分数}
    """
    if node_count <= 0:
        return {"level": "无", "score": 0.0}
    elif node_count < 10:
        return {"level": "低", "score": 0.3}
    elif node_count <= 50:
        # 线性插值：10→0.3, 50→0.8
        score = 0.3 + (node_count - 10) / 40 * 0.5
        return {"level": "中", "score": round(score, 2)}
    else:
        # >50: 渐进接近 1.0
        score = min(1.0, 0.8 + (node_count - 50) / 200 * 0.2)
        return {"level": "高", "score": round(score, 2)}


# ============================================================
# 五行诊断信度输出
# ============================================================

def wuxing_confidence_interval(wuxing_dist, node_count, z=Z_95):
    """
    五行诊断的信度输出。
    
    不是"水占26.1%"的虚假精确，而是"水在[20%, 32%]范围内可信"。
    
    对应不确定理论：数据不足时不"强做可知"。
    
    Args:
        wuxing_dist: {五行: 比例} 如 {"水": 0.261, "土": 0.254, "金": 0.185, "木": 0.160, "火": 0.140}
        node_count: 总节点数
        z: 置信水平 z 值，默认 1.96
    
    Returns:
        {
            "水": {"point": 0.261, "ci_low": 0.20, "ci_high": 0.32, "ci_width": 0.12},
            ...
            "_meta": {"node_count": 30, "confidence_level": "中", "method": "wilson", "z": 1.96}
        }
    """
    conf = sample_confidence_level(node_count)
    
    result = {}
    for wx, proportion in sorted(wuxing_dist.items()):
        ci_low, ci_high = wilson_interval(proportion, node_count, z)
        result[wx] = {
            "point": round(proportion, 4),
            "ci_low": ci_low,
            "ci_high": ci_high,
            "ci_width": round(ci_high - ci_low, 4)
        }
    
    result["_meta"] = {
        "node_count": node_count,
        "confidence_level": conf["level"],
        "confidence_score": conf["score"],
        "method": "wilson",
        "z": z
    }
    
    return result


def wuxing_confidence_summary(wuxing_dist, node_count):
    """
    五行信度的一行摘要，用于报告文本。
    
    Args:
        wuxing_dist: 五行比例分布
        node_count: 节点数
    
    Returns:
        str: 如 "水 26.1%[20.0-32.3] 土 25.4%[19.3-31.6] ... (置信度:中)"
    """
    ci = wuxing_confidence_interval(wuxing_dist, node_count)
    parts = []
    for wx in ['木', '火', '土', '金', '水']:
        if wx in ci:
            d = ci[wx]
            parts.append(f"{wx} {d['point']*100:.1f}%[{d['ci_low']*100:.1f}-{d['ci_high']*100:.1f}]")
    level = ci["_meta"]["confidence_level"]
    return f"{' | '.join(parts)} (置信度:{level})"


# ============================================================
# 漂移信度加权
# ============================================================

def drift_confidence(drift_value, node_count, paper_count):
    """
    漂移值的信度加权。
    
    小样本领域的漂移值标注低置信度。
    当 node_count < 10 或 paper_count < 5 时，漂移值不可靠。
    
    Args:
        drift_value: 余弦距离漂移值，∈ [0, 1]
        node_count: 领域节点数
        paper_count: 领域论文数
    
    Returns:
        {
            "drift": 原始漂移值,
            "effective_sample": 有效样本量,
            "confidence": "高/中/低",
            "warning": 警告信息（如有）
        }
    """
    # 有效样本量 = min(node_count, paper_count)（两者都小则不可靠）
    effective = min(node_count, paper_count)
    node_conf = sample_confidence_level(node_count)
    paper_conf = sample_confidence_level(paper_count)
    
    # 综合置信度：取两者中较低者
    # 同时检查原始等级：任一方为"低"则综合为"低"
    if node_conf["level"] == "低" or paper_conf["level"] == "低":
        level = "低"
    elif node_conf["level"] == "无" or paper_conf["level"] == "无":
        level = "低"
    else:
        combined_score = min(node_conf["score"], paper_conf["score"])
        if combined_score >= 0.8:
            level = "高"
        else:
            level = "中"
    
    combined_score = min(node_conf["score"], paper_conf["score"])
    
    warning = None
    if level == "低":
        warning = (
            f"领域节点数({node_count})或论文数({paper_count})不足，"
            f"漂移值 {drift_value:.2f} 仅供参考，不应作为决策依据"
        )
    elif level == "中":
        warning = (
            f"领域样本量有限（节点{node_count}/论文{paper_count}），"
            f"漂移值 {drift_value:.2f} 有一定参考价值但需谨慎解读"
        )
    
    result = {
        "drift": round(drift_value, 4),
        "effective_sample": effective,
        "node_count": node_count,
        "paper_count": paper_count,
        "confidence": level,
        "confidence_score": round(combined_score, 2)
    }
    if warning:
        result["warning"] = warning
    
    return result


# ============================================================
# 漂移信度增强（P1#2：小样本领域漂移处理）
# ============================================================

def drift_confidence_interval(drift_value, node_count, paper_count, z=Z_95):
    """
    漂移值的信度区间估计。
    
    核心思路：漂移值本身也有不确定性，小样本下应该给出区间而非点估计。
    使用有效样本量 n_eff = min(node_count, paper_count) 来估计漂移的
    不确定性范围。
    
    公式（基于 Wilson 的启发式扩展）：
        margin = z * sqrt(drift * (1-drift) / n_eff)
        ci = [drift - margin, drift + margin]
    
    当 n_eff=0 时返回 [0, 1]（完全不确定）。
    
    Args:
        drift_value: 余弦距离漂移值，∈ [0, 1]
        node_count: 领域节点数
        paper_count: 领域论文数
        z: 置信水平 z 值，默认 1.96
    
    Returns:
        {
            "drift": 点估计,
            "ci_low": 下界,
            "ci_high": 上界,
            "ci_width": 区间宽度,
            "effective_sample": 有效样本量,
            "is_reliable": 是否可依赖
        }
    """
    n_eff = min(node_count, paper_count)
    
    if n_eff <= 0:
        return {
            "drift": round(drift_value, 4),
            "ci_low": 0.0,
            "ci_high": 1.0,
            "ci_width": 1.0,
            "effective_sample": 0,
            "is_reliable": False,
            "warning": "有效样本量为0，漂移值不可用"
        }
    
    # 漂移的标准误估计
    drift = max(0.0, min(1.0, drift_value))
    se = math.sqrt(drift * (1 - drift) / n_eff) if drift > 0 and drift < 1 else 0.0
    margin = z * se
    
    ci_low = max(0.0, drift - margin)
    ci_high = min(1.0, drift + margin)
    ci_width = ci_high - ci_low
    
    # 可靠性判定：区间宽度 < 0.5 且 有效样本 >= 10
    is_reliable = (ci_width < 0.5) and (n_eff >= 10)
    
    result = {
        "drift": round(drift, 4),
        "ci_low": round(ci_low, 4),
        "ci_high": round(ci_high, 4),
        "ci_width": round(ci_width, 4),
        "effective_sample": n_eff,
        "is_reliable": is_reliable
    }
    
    if not is_reliable:
        if n_eff < 10:
            result["warning"] = f"有效样本量仅{n_eff}，漂移区间宽度{ci_width:.2f}，数据不足以支撑可靠判定"
        else:
            result["warning"] = f"漂移区间宽度{ci_width:.2f}过大，建议补充数据后再判定"
    
    return result


def drift_direction_guarded(drift_value, node_count, paper_count):
    """
    带信度守卫的漂移方向判定。
    
    与简单阈值判定不同，此函数在置信度低时自动降低判定级别，
    避免小样本领域的"假阳性"漂移警报。
    
    规则：
    - 有效样本量为0 → "数据不足"
    - 置信度为"低" → "数据不足"（不强做判定）
    - 置信度为"中" + drift > 0.4 → "可能漂移（置信度中）"
    - 置信度为"中" + drift > 0.15 → "轻微漂移（置信度中）"
    - 置信度为"高" + drift > 0.4 → "显著漂移"
    - 置信度为"高" + drift > 0.15 → "轻度漂移"
    - 否则 → "基本一致"
    
    Args:
        drift_value: 漂移值
        node_count: 领域节点数
        paper_count: 领域论文数
    
    Returns:
        {
            "direction": 方向标签,
            "confidence_level": 判定置信度,
            "is_guarded": 是否被信度守卫降级
        }
    """
    n_eff = min(node_count, paper_count)
    
    # 无数据
    if n_eff <= 0:
        return {
            "direction": "数据不足",
            "confidence_level": "无",
            "is_guarded": True,
            "reason": "有效样本量为0，无法计算漂移"
        }
    
    conf = drift_confidence(drift_value, node_count, paper_count)
    level = conf["confidence"]
    
    # 低置信度 → 不强做判定
    if level == "低":
        return {
            "direction": "数据不足",
            "confidence_level": "低",
            "is_guarded": True,
            "reason": f"置信度不足（节点{node_count}/论文{paper_count}），不强做判定"
        }
    
    # 中置信度 → 降低判定级别
    if level == "中":
        if drift_value > 0.4:
            return {
                "direction": "可能漂移（置信度中）",
                "confidence_level": "中",
                "is_guarded": True,
                "reason": "置信度中等，漂移幅度较大但需谨慎解读"
            }
        elif drift_value > 0.15:
            return {
                "direction": "轻微漂移（置信度中）",
                "confidence_level": "中",
                "is_guarded": True,
                "reason": "置信度中等，漂移幅度较小"
            }
        else:
            return {
                "direction": "基本一致",
                "confidence_level": "中",
                "is_guarded": False
            }
    
    # 高置信度 → 正常判定
    if drift_value > 0.4:
        return {
            "direction": "显著漂移",
            "confidence_level": "高",
            "is_guarded": False
        }
    elif drift_value > 0.15:
        return {
            "direction": "轻度漂移",
            "confidence_level": "高",
            "is_guarded": False
        }
    else:
        return {
            "direction": "基本一致",
            "confidence_level": "高",
            "is_guarded": False
        }


def drift_reliability(node_count, paper_count):
    """
    领域漂移分析的可靠性综合评估。
    
    从三个维度评估：
    1. 节点覆盖度：领域节点数是否足够代表知识树结构
    2. 论文覆盖度：论文数是否足够反映研究热点
    3. 综合可靠性：两者结合的可信度
    
    Args:
        node_count: 领域节点数
        paper_count: 领域论文数
    
    Returns:
        {
            "level": "高/中/低/不可用",
            "score": 0.0-1.0,
            "node_coverage": 节点覆盖度评估,
            "paper_coverage": 论文覆盖度评估,
            "can_compare": 是否可以进行有意义的对比
        }
    """
    n_eff = min(node_count, paper_count)
    
    # 节点覆盖度
    node_conf = sample_confidence_level(node_count)
    # 论文覆盖度
    paper_conf = sample_confidence_level(paper_count)
    
    # 综合评分：取两者中较低者
    combined_score = min(node_conf["score"], paper_conf["score"])
    
    # 任一方为0 → 不可用
    if node_count <= 0 or paper_count <= 0:
        level = "不可用"
        can_compare = False
    elif combined_score < 0.3:
        level = "低"
        can_compare = False
    elif combined_score < 0.8:
        level = "中"
        can_compare = True
    else:
        level = "高"
        can_compare = True
    
    return {
        "level": level,
        "score": round(combined_score, 2),
        "effective_sample": n_eff,
        "node_count": node_count,
        "paper_count": paper_count,
        "node_coverage": node_conf,
        "paper_coverage": paper_conf,
        "can_compare": can_compare
    }


# ============================================================
# 四维信度加权
# ============================================================

def dimension_confidence(O_t, E_u, C_k, K_y,
                         node_count, edge_count, depth_count, domain_count):
    """
    计算四维各自的信度分数。
    
    每维度的信度由对应的数据充分性决定：
    - O_t: 由深度分布样本量决定（depth_count）
    - E_u: 由领域覆盖度决定（domain_count）
    - C_k: 由五行分布样本量决定（node_count）
    - K_y: 由边数量决定（edge_count）
    
    Args:
        O_t, E_u, C_k, K_y: 四维值
        node_count: 节点总数
        edge_count: 边总数
        depth_count: 有深度标注的节点数
        domain_count: 领域数
    
    Returns:
        [c_O, c_E, c_C, c_K]: 各维度置信度分数 ∈ [0, 1]
    """
    c_O = sample_confidence_level(depth_count)["score"]
    c_E = sample_confidence_level(domain_count)["score"]
    c_C = sample_confidence_level(node_count)["score"]
    # K_y 的置信度同时取决于节点数和边数
    c_K = min(
        sample_confidence_level(node_count)["score"],
        sample_confidence_level(edge_count)["score"]
    )
    return [c_O, c_E, c_C, c_K]


# ============================================================
# 自检
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("信度区间计算模块 — 自检")
    print("=" * 60)
    
    # 测试 1: Wilson 区间
    print("\n[测试 1] Wilson 区间")
    print(f"  p=0.5, n=10  → {wilson_interval(0.5, 10)}")
    print(f"  p=0.5, n=100 → {wilson_interval(0.5, 100)}")
    print(f"  p=0.1, n=10  → {wilson_interval(0.1, 10)}")
    print(f"  p=0.9, n=10  → {wilson_interval(0.9, 10)}")
    print(f"  p=0.5, n=0   → {wilson_interval(0.5, 0)}")
    
    # 测试 2: 样本量→置信度
    print("\n[测试 2] 样本量→置信度映射")
    for n in [0, 5, 10, 25, 50, 100, 200]:
        print(f"  n={n:>4} → {sample_confidence_level(n)}")
    
    # 测试 3: 五行信度区间
    print("\n[测试 3] 五行信度区间")
    wx_dist = {"水": 0.261, "土": 0.254, "金": 0.185, "木": 0.160, "火": 0.140}
    
    for n in [5, 30, 100]:
        ci = wuxing_confidence_interval(wx_dist, n)
        print(f"\n  n={n}:")
        for wx in ['木', '火', '土', '金', '水']:
            d = ci[wx]
            print(f"    {wx}: {d['point']*100:.1f}% [{d['ci_low']*100:.1f}-{d['ci_high']*100:.1f}]% "
                  f"(宽度={d['ci_width']*100:.1f}%)")
        print(f"    置信度: {ci['_meta']['confidence_level']} ({ci['_meta']['confidence_score']})")
    
    # 测试 4: 五行摘要
    print("\n[测试 4] 五行信度摘要")
    print(f"  n=30: {wuxing_confidence_summary(wx_dist, 30)}")
    print(f"  n=5:  {wuxing_confidence_summary(wx_dist, 5)}")
    
    # 测试 5: 漂移信度
    print("\n[测试 5] 漂移信度加权")
    test_cases = [
        (0.35, 100, 50),   # 大样本
        (0.35, 30, 20),    # 中样本
        (0.40, 4, 3),      # 小样本（如知识表示）
        (0.40, 9, 2),      # 极小样本
    ]
    for drift, nc, pc in test_cases:
        r = drift_confidence(drift, nc, pc)
        print(f"  drift={drift}, node={nc}, paper={pc}: "
              f"置信度={r['confidence']}, "
              f"{'⚠ ' + r['warning'] if r.get('warning') else '✓'}")
    
    # 测试 6: 四维信度
    print("\n[测试 6] 四维信度")
    confs = dimension_confidence(0.5, 0.6, 0.4, 0.3,
                                 node_count=30, edge_count=25,
                                 depth_count=30, domain_count=13)
    print(f"  [O_t, E_u, C_k, K_y] = {confs}")
    print(f"  有效维度数: {sum(confs):.2f}")
    
    print("\n" + "=" * 60)
    print("自检完成")