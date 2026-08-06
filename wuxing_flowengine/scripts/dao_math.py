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