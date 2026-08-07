"""
道境数学工具模块 — 共享的 S_p 计算与四维工具函数
==================================================
V1.2 公式结构变更：从旧乘积 S = O_t × E_u × C_k × K_y × 100
迁移到广义平均 S_p = M_p × 100，解决量纲不可达问题。

M_p = [ (O_t^p + E_u^p + C_k^p + K_y^p) / 4 ]^(1/p)

p 的伦理语义（P忠恕结合）：
  p=1.0 → 恕之极致（加性平均）
  p=0.8 → 宽恕
  p=0.5 → P忠恕中道（默认）
  p=0.3 → 严格
  p=0.0 → 均衡（几何平均）
  p=-1.0 → 苛（调和平均）

用法:
    from dao_math import compute_S_p, compute_S_p_weighted, S_P_DEFAULT
    s = compute_S_p([O_t, E_u, C_k, K_y])  # 默认 p=0.5
"""

import math

# 默认恕度参数
S_P_DEFAULT = 0.5  # P忠恕中道
S_P_SCALE = 100     # 输出缩放因子


def compute_S_p(dims, p=S_P_DEFAULT, scale=S_P_SCALE):
    """
    广义平均存在度 S_p (Power Mean)

    Args:
        dims: 四维值 [O_t, E_u, C_k, K_y]，每个 ∈ [0, 1]
        p: 恕度参数，默认 0.5（P忠恕中道）
        scale: 输出缩放因子，默认 100

    Returns:
        float: S_p 值
    """
    dims = [max(v, 1e-9) for v in dims]  # 防止 log(0) 或 0^p
    n = len(dims)
    if abs(p) < 1e-9:
        # p=0: 几何平均
        m = math.exp(sum(math.log(d) for d in dims) / n)
    else:
        m = (sum(d ** p for d in dims) / n) ** (1.0 / p)
    return m * scale


def compute_S_p_weighted(dims, p, weights, scale=S_P_SCALE):
    """
    带权广义平均

    Args:
        dims: 四维值 [O_t, E_u, C_k, K_y]
        p: 恕度参数
        weights: 权重 [w_O, w_E, w_C, w_K]
        scale: 输出缩放因子

    Returns:
        float: 加权 S_p 值
    """
    dims = [max(v, 1e-9) for v in dims]
    wsum = sum(weights)
    if abs(p) < 1e-9:
        m = math.exp(sum(w * math.log(d) for w, d in zip(weights, dims)) / wsum)
    else:
        m = (sum(w * d ** p for w, d in zip(weights, dims)) / wsum) ** (1.0 / p)
    return m * scale


def compute_S_old(O_t, E_u, C_k, K_y):
    """
    旧乘积公式（保留用于对比输出）

    Args:
        O_t, E_u, C_k, K_y: 四维值

    Returns:
        float: 旧乘积 S
    """
    return O_t * E_u * C_k * K_y * 100


def compute_S_p_with_confidence(dims, dim_confidences=None, p=S_P_DEFAULT, scale=S_P_SCALE):
    """
    带信度边界的 S_p 计算。
    
    当某维度置信度低时，其权重降低——不对不确定的维度"强做可知"。
    对应不确定理论：数据不足时不假装精确。
    
    Args:
        dims: 四维值 [O_t, E_u, C_k, K_y]
        dim_confidences: 各维度置信度 [c_O, c_E, c_C, c_K]，每个 ∈ [0, 1]
                         如果为 None，则视为各维度置信度相同（退化为标准 S_p）
        p: 恕度参数
        scale: 输出缩放因子
    
    Returns:
        {
            "S": S_p 值,
            "effective_n": 有效维度数,
            "confidence_level": "高/中/低",
            "p": 恕度参数,
            "p_label": 恕度标签
        }
    """
    if dim_confidences is None:
        # 退化为标准 S_p
        dim_confidences = [1.0] * len(dims)
    
    n = len(dims)
    effective_n = sum(dim_confidences)
    
    # 置信度等级
    if effective_n >= 3.5:
        conf_level = "高"
    elif effective_n >= 2.0:
        conf_level = "中"
    else:
        conf_level = "低"
    
    # 使用置信度作为权重计算加权 S_p
    # 归一化权重
    wsum = sum(dim_confidences)
    if wsum < 1e-9:
        # 全部无置信度，退化为等权
        S = compute_S_p(dims, p, scale)
    else:
        S = compute_S_p_weighted(dims, p, dim_confidences, scale)
    
    return {
        "S": round(S, 1),
        "effective_n": round(effective_n, 2),
        "confidence_level": conf_level,
        "p": p,
        "p_label": p_label(p)
    }


def p_label(p):
    """返回 p 值的恕度标签"""
    labels = {
        1.0: "恕之极致",
        0.8: "宽恕",
        0.5: "P忠恕中道",
        0.3: "严格",
        0.0: "均衡",
        -1.0: "苛",
    }
    if p in labels:
        return labels[p]
    return f"p={p:.1f}"