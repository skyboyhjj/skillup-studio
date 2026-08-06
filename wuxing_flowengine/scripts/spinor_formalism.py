"""
旋量-太极形式化 — "反者道之动"的数学精确化
=============================================
基于《反者道之动_矛盾迭代引擎_五轮对话深度复盘_完善版》共振六，
将"反者道之动"的直觉形式化为旋量-太极数学模型。

核心概念：
  旋量 (Spinor)：旋转 360° 后不是回到原点，而是携带 -1 相位翻转；
  旋转 720° 后才完全回归。这精确对应了"反者道之动"的否定之否定逻辑。

太极旋量模型：
  θ = 0°    → 正题（源域结构）         → 旋量态 |ψ⟩
  θ = 180°  → 第一次否定（反）         → 映射到否定域
  θ = 360°  → 第二次否定（道之动）     → 旋量语义下携带 -1 相位翻转！
             经典（向量）语义下"看似回归"
             旋量语义下"结构保持但位置已升"
  θ = 720°  → 完全回归                → 需要两轮"反者道之动"

关键洞见：
  "升华"不是修辞，是相位积累。
  每一次否定之否定都留下一圈旋转的相位，
  让结果"结构保持但位置已升"——
  这解释了为什么否定之否定不是原地打转。
  多出来的 360° 就是"道"在每次循环中留下的成长。

对应 S_spiral 语言：
  反者道之动 = 结构保持的螺旋上升，而非封闭循环。

用法:
    from spinor_formalism import SpinorPhase, DaoSpinor
    sp = SpinorPhase(theta=0)
    sp.negate()  # 第一次否定 → 180°
    sp.negate()  # 第二次否定 → 360° (相位翻转!)
    sp.negate()  # 第三次否定 → 540°
    sp.negate()  # 第四次否定 → 720° (完全回归)
"""

import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum


# ═══════════════════════════════════════════════
# 基础旋量模型
# ═══════════════════════════════════════════════

class NegationPhase(str, Enum):
    """否定阶段"""
    THESIS = "正题"          # θ = 0° mod 360°
    ANTITHESIS = "反"        # θ = 180° mod 360°
    SUBLATION = "道之动"     # θ = 360° mod 360° (旋量: -1 相位)
    RETURN = "完全回归"       # θ = 720° mod 360° (旋量: +1 回归)


class SpinorPhase:
    """
    旋量相位模型

    经典向量：旋转 360° 回到原点
    旋量：旋转 360° 携带 -1 相位翻转，旋转 720° 才完全回归

    这精确对应了"反者道之动"的否定之否定逻辑：
    - 第一次否定 (反)：180° 旋转
    - 第二次否定 (道之动)：360° 旋转 → 旋量语义下携带 -1 相位
    - 第三次否定 (再反)：540° 旋转
    - 第四次否定 (再道之动)：720° 旋转 → 完全回归
    """

    def __init__(self, theta: float = 0.0):
        """
        Args:
            theta: 初始角度（度），默认 0°（正题）
        """
        self.theta = theta  # 累积角度
        self.negation_count = 0  # 否定次数
        self.history: List[Dict] = []  # 否定历史

    @property
    def theta_rad(self) -> float:
        """弧度制"""
        return math.radians(self.theta)

    @property
    def phase_factor(self) -> complex:
        """
        旋量相位因子 e^{iθ/2}

        关键性质：
          - θ=360° → e^{iπ} = -1 (相位翻转!)
          - θ=720° → e^{i2π} = +1 (完全回归)
        """
        return cmath.exp(1j * self.theta_rad / 2.0)

    @property
    def vector_equivalent(self) -> complex:
        """
        经典向量等价 e^{iθ}

        向量语义下 360° 即回归，无相位翻转
        """
        return cmath.exp(1j * self.theta_rad)

    @property
    def phase(self) -> NegationPhase:
        """当前否定阶段"""
        mod_360 = self.theta % 360.0
        if mod_360 < 1e-6:
            return NegationPhase.THESIS
        elif abs(mod_360 - 180.0) < 1e-6:
            return NegationPhase.ANTITHESIS
        elif abs(mod_360 - 360.0) < 1e-6 or mod_360 < 1e-6:
            # 360° 在旋量语义下 ≠ 0°，但模 360° 角度相同
            # 使用 negation_count 区分
            full_cycles = self.negation_count // 2
            if full_cycles >= 2 and self.negation_count % 2 == 0:
                return NegationPhase.RETURN
            return NegationPhase.SUBLATION
        return NegationPhase.THESIS  # 默认

    @property
    def is_spinor_flipped(self) -> bool:
        """
        是否处于旋量翻转状态

        旋量在 360° 时携带 -1 相位翻转
        """
        cycles = self.negation_count // 2  # 完整否定之否定轮数
        return cycles > 0 and cycles % 2 == 1  # 奇数轮 → 翻转

    @property
    def elevation_level(self) -> int:
        """
        升华层级

        每两轮否定之否定（720°）完成一次完整的螺旋上升。
        升华层级 = 完整循环数。
        """
        return self.negation_count // 4

    def negate(self, description: str = "") -> Dict:
        """
        执行一次否定操作

        否定 = 旋转 180°，即"反"。

        Args:
            description: 否定操作的描述

        Returns:
            否定操作记录
        """
        self.negation_count += 1
        self.theta += 180.0

        record = {
            "negation_index": self.negation_count,
            "theta": self.theta,
            "phase": self.phase.value,
            "phase_factor": f"{self.phase_factor.real:.4f}{self.phase_factor.imag:+.4f}j",
            "is_flipped": self.is_spinor_flipped,
            "elevation_level": self.elevation_level,
            "description": description,
            "interpretation": self._interpret_current(),
        }
        self.history.append(record)
        return record

    def negate_negate(self, description: str = "") -> Dict:
        """
        执行一次完整的否定之否定（反者道之动）

        连续两次否定，旋转 360°。
        在旋量语义下携带 -1 相位翻转。

        Returns:
            否定之否定操作记录
        """
        self.negate(description or "反（第一次否定）")
        return self.negate(description or "道之动（第二次否定）")

    def _interpret_current(self) -> str:
        """解读当前状态"""
        n = self.negation_count
        if n == 0:
            return "正题：源域结构建立，初始认知框架"
        elif n == 1:
            return "反：第一次否定，映射到否定域——结构被质疑、被反转"
        elif n == 2:
            return "道之动：第二次否定，否定之否定完成——旋量语义下携带 -1 相位翻转！结构保持但位置已升"
        elif n == 3:
            return "再反：第三次否定，在升华后的新位置再次质疑——新一轮螺旋的开始"
        elif n == 4:
            return "完全回归：第四次否定，两轮反者道之动完成——旋量回归 +1，结构在更高层次上完全保持"
        else:
            cycles = n // 4
            remainder = n % 4
            base = f"第{cycles}轮螺旋完成"
            if remainder == 1:
                return f"{base}，新一轮反开始"
            elif remainder == 2:
                return f"{base}，新一轮道之动"
            elif remainder == 3:
                return f"{base}，再反"
            return base

    def to_dict(self) -> dict:
        return {
            "theta": self.theta,
            "theta_rad": self.theta_rad,
            "negation_count": self.negation_count,
            "phase": self.phase.value,
            "phase_factor": complex(round(self.phase_factor.real, 4),
                                    round(self.phase_factor.imag, 4)),
            "is_spinor_flipped": self.is_spinor_flipped,
            "elevation_level": self.elevation_level,
            "history": self.history,
            "current_interpretation": self._interpret_current(),
        }


# 导入 cmath 用于复指数
import cmath


# ═══════════════════════════════════════════════
# 太极旋量 — 同态映射集成
# ═══════════════════════════════════════════════

@dataclass
class DaoSpinorState:
    """
    道旋量状态 — 同态映射的螺旋演化跟踪

    记录一个同态映射在"反者道之动"循环中的旋量演化。
    """
    source_domain: str
    target_domain: str
    spinor: SpinorPhase = field(default_factory=SpinorPhase)

    # 演化记录
    iterations: List[Dict] = field(default_factory=list)

    def iterate(self, mapping_result: dict, description: str = "") -> Dict:
        """
        一次迭代 = 一次否定之否定

        在旋量模型中，一次完整的同态映射迭代（结构提取→匹配→验证）
        对应一次否定之否定（360° 旋转）。

        Args:
            mapping_result: 同态映射结果
            description: 迭代描述

        Returns:
            迭代记录
        """
        self.spinor.negate_negate(description)

        record = {
            "iteration": self.spinor.negation_count // 2,
            "theta": self.spinor.theta,
            "phase": self.spinor.phase.value,
            "is_flipped": self.spinor.is_spinor_flipped,
            "elevation": self.spinor.elevation_level,
            "mapping_result": {
                "relation_preservation_score": mapping_result.get("step2", {}).get("relation_preservation_score", 0),
                "confidence_level": mapping_result.get("step2", {}).get("confidence_level", "?"),
                "solidified": mapping_result.get("solidified", False),
            },
            "interpretation": self._interpret_iteration(mapping_result),
        }
        self.iterations.append(record)
        return record

    def _interpret_iteration(self, mapping_result: dict) -> str:
        """解读当前迭代"""
        n = self.spinor.negation_count // 2
        if n == 0:
            return "初始映射：正题建立"
        elif n == 1:
            if self.spinor.is_spinor_flipped:
                return ("第一轮反者道之动完成：映射经过否定之否定，"
                       "结构保持但携带 -1 相位翻转——这是'升华'的数学表达")
            return "第一次否定之否定"
        else:
            if self.spinor.elevation_level > 0:
                return (f"第{self.spinor.elevation_level}层螺旋上升完成："
                       f"映射在更高层次上完全回归，结构保持且深化")
            return f"第{n}轮迭代"

    def to_dict(self) -> dict:
        return {
            "source_domain": self.source_domain,
            "target_domain": self.target_domain,
            "spinor": self.spinor.to_dict(),
            "iterations": self.iterations,
            "total_iterations": len(self.iterations),
            "current_elevation": self.spinor.elevation_level,
        }


# ═══════════════════════════════════════════════
# 反者道之动 — 形式化操作
# ═══════════════════════════════════════════════

def reversal_is_dao_motion(iterations: int = 1) -> Dict:
    """
    演示"反者道之动"的旋量形式化

    执行指定轮数的否定之否定循环，展示旋量相位翻转。

    Args:
        iterations: 否定之否定轮数（默认 1 轮 = 2 次否定 = 360°）

    Returns:
        演示结果
    """
    spinor = SpinorPhase()

    for i in range(iterations):
        spinor.negate_negate(f"第{i+1}轮反者道之动")

    return {
        "total_negations": spinor.negation_count,
        "total_rotation": spinor.theta,
        "phase_factor": f"{spinor.phase_factor.real:.4f}{spinor.phase_factor.imag:+.4f}j",
        "is_flipped": spinor.is_spinor_flipped,
        "elevation_level": spinor.elevation_level,
        "vector_illusion": (
            f"经典向量语义下，{spinor.theta}° 看似回归原点"
            if spinor.theta % 360 == 0 else
            f"经典向量语义下，{spinor.theta}° 未回归"
        ),
        "spinor_truth": (
            "旋量语义下，360° 携带 -1 相位翻转——'看似回归实则升华'"
            if spinor.is_spinor_flipped else
            "旋量语义下，720° 完全回归——'否定之否定后的真正回归'"
            if spinor.theta >= 720 and spinor.theta % 720 == 0 else
            "旋量语义下，仍在旋转中"
        ),
        "interpretation": _interpret_dao_motion(spinor),
    }


def _interpret_dao_motion(spinor: SpinorPhase) -> str:
    """解读反者道之动的旋量状态"""
    if spinor.negation_count == 0:
        return "正题：道生一"
    elif spinor.negation_count == 1:
        return "反：一生二——第一次否定，走向反面"
    elif spinor.negation_count == 2:
        return ("道之动：二生三——第二次否定，否定之否定。"
               "旋量语义下携带 -1 相位翻转：结构保持但位置已升。"
               "多出来的 360° 就是'道'留下的成长。")
    elif spinor.negation_count == 3:
        return "三生万物：在升华后的新位置，重新开始新一轮螺旋"
    elif spinor.negation_count == 4:
        return ("万物归一：两轮反者道之动完成，720° 完全回归。"
               "结构在更高层次上完全保持——这是'道'的完整循环。")
    else:
        return f"第{spinor.negation_count // 4}层螺旋，第{spinor.negation_count % 4}次否定"


# ═══════════════════════════════════════════════
# 旋量-同态映射桥接
# ═══════════════════════════════════════════════

class SpinorHomomorphismBridge:
    """
    旋量-同态映射桥接器

    将旋量形式化注入同态映射引擎，使得每次同态映射迭代
    都被记录为"反者道之动"螺旋中的一步。
    """

    def __init__(self):
        self.dao_states: Dict[str, DaoSpinorState] = {}

    def get_or_create_state(self, source_domain: str,
                            target_domain: str) -> DaoSpinorState:
        """获取或创建道旋量状态"""
        key = f"{source_domain}→{target_domain}"
        if key not in self.dao_states:
            self.dao_states[key] = DaoSpinorState(
                source_domain=source_domain,
                target_domain=target_domain,
            )
        return self.dao_states[key]

    def track_transfer(self, source_domain: str, target_domain: str,
                       mapping_result: dict) -> Dict:
        """
        跟踪一次同态迁移，记录为旋量演化的迭代

        Args:
            source_domain: 源域
            target_domain: 目标域
            mapping_result: 同态映射引擎的结果

        Returns:
            旋量演化记录
        """
        state = self.get_or_create_state(source_domain, target_domain)
        iteration = state.iterate(mapping_result,
                                  description=f"{source_domain}→{target_domain} 同态迁移")

        # 注入旋量信息到 mapping_result
        mapping_result["spinor_formalism"] = {
            "theta": state.spinor.theta,
            "negation_count": state.spinor.negation_count,
            "phase": state.spinor.phase.value,
            "phase_factor": f"{state.spinor.phase_factor.real:.4f}{state.spinor.phase_factor.imag:+.4f}j",
            "is_flipped": state.spinor.is_spinor_flipped,
            "elevation_level": state.spinor.elevation_level,
            "interpretation": state.spinor._interpret_current(),
        }

        return iteration

    def get_dao_summary(self, source_domain: str,
                        target_domain: str) -> Dict:
        """获取指定映射的道的演化摘要"""
        state = self.get_or_create_state(source_domain, target_domain)
        return {
            "mapping": f"{source_domain}→{target_domain}",
            "total_iterations": len(state.iterations),
            "current_theta": state.spinor.theta,
            "phase": state.spinor.phase.value,
            "is_flipped": state.spinor.is_spinor_flipped,
            "elevation_level": state.spinor.elevation_level,
            "dao_interpretation": _interpret_dao_motion(state.spinor),
            "iterations": state.iterations,
        }

    def get_all_states(self) -> List[Dict]:
        """获取所有道旋量状态摘要"""
        return [
            {
                "mapping": state.spinor.to_dict(),
                "iterations": len(state.iterations),
                "elevation": state.spinor.elevation_level,
            }
            for state in self.dao_states.values()
        ]


# ═══════════════════════════════════════════════
# 独立测试
# ═══════════════════════════════════════════════

if __name__ == '__main__':
    print("=" * 70)
    print("  旋量-太极形式化 — 独立测试")
    print("=" * 70)

    # 测试 1: 基础旋量 — 单轮反者道之动
    print("\n[测试 1] 基础旋量：单轮反者道之动（360°）")
    spinor = SpinorPhase()
    print(f"  初始: θ={spinor.theta}°, phase={spinor.phase.value}, "
          f"phase_factor={spinor.phase_factor.real:.2f}{spinor.phase_factor.imag:+.2f}j")

    # 第一次否定
    r1 = spinor.negate("反：质疑源域结构")
    print(f"  否定1: θ={r1['theta']}°, phase={r1['phase']}, "
          f"phase_factor={r1['phase_factor']}, flipped={r1['is_flipped']}")
    print(f"    解读: {r1['interpretation']}")

    # 第二次否定
    r2 = spinor.negate("道之动：否定之否定")
    print(f"  否定2: θ={r2['theta']}°, phase={r2['phase']}, "
          f"phase_factor={r2['phase_factor']}, flipped={r2['is_flipped']}")
    print(f"    解读: {r2['interpretation']}")

    # 测试 2: 旋量相位翻转验证
    print("\n[测试 2] 旋量相位翻转验证")
    print(f"  360° 旋量相位因子: {spinor.phase_factor.real:.2f}{spinor.phase_factor.imag:+.2f}j")
    print(f"  关键: 360° 下 phase_factor = -1 (不是 +1)！")
    print(f"  向量等价 (360°): {spinor.vector_equivalent.real:.2f}{spinor.vector_equivalent.imag:+.2f}j")
    print(f"  向量语义下 360°='回归原点'，旋量语义下 360°='相位翻转'")

    # 测试 3: 两轮反者道之动（720°）
    print("\n[测试 3] 两轮反者道之动（720° 完全回归）")
    spinor.negate("再反：第三轮开始")
    spinor.negate("再道之动：第四轮完成")
    print(f"  720° 旋量相位因子: {spinor.phase_factor.real:.2f}{spinor.phase_factor.imag:+.2f}j")
    print(f"  720° 下 phase_factor = +1 (完全回归)")
    print(f"  升华层级: {spinor.elevation_level}")

    # 测试 4: 反者道之动形式化函数
    print("\n[测试 4] 反者道之动形式化 (2 轮)")
    result = reversal_is_dao_motion(iterations=2)
    print(f"  总否定次数: {result['total_negations']}")
    print(f"  总旋转角度: {result['total_rotation']}°")
    print(f"  相位因子: {result['phase_factor']}")
    print(f"  翻转状态: {result['is_flipped']}")
    print(f"  升华层级: {result['elevation_level']}")
    print(f"  向量幻觉: {result['vector_illusion']}")
    print(f"  旋量真相: {result['spinor_truth']}")
    print(f"  道解读: {result['interpretation']}")

    # 测试 5: 旋量-同态映射桥接
    print("\n[测试 5] 旋量-同态映射桥接")
    bridge = SpinorHomomorphismBridge()

    # 模拟三次同态迁移迭代
    for i in range(3):
        mock_result = {
            "step2": {"relation_preservation_score": 0.6 + i * 0.1,
                      "confidence_level": "high"},
            "solidified": i >= 1,
        }
        iteration = bridge.track_transfer(
            "大语言模型", "自然语言处理", mock_result
        )
        print(f"  迭代 {i+1}: θ={iteration['theta']}°, "
              f"phase={iteration['phase']}, "
              f"flipped={iteration['is_flipped']}, "
              f"elevation={iteration['elevation']}")

    # 获取道的演化摘要
    summary = bridge.get_dao_summary("大语言模型", "自然语言处理")
    print(f"\n  道演化摘要:")
    print(f"    总迭代: {summary['total_iterations']}")
    print(f"    当前角度: {summary['current_theta']}°")
    print(f"    相位: {summary['phase']}")
    print(f"    翻转: {summary['is_flipped']}")
    print(f"    升华层级: {summary['elevation_level']}")
    print(f"    道解读: {summary['dao_interpretation']}")

    # 测试 6: 旋量形式化注入到 mapping_result
    print("\n[测试 6] 旋量形式化注入验证")
    mock_result = {
        "step2": {"relation_preservation_score": 0.8,
                  "confidence_level": "high"},
        "solidified": True,
    }
    bridge.track_transfer("大语言模型", "生成式AI", mock_result)
    spinor_info = mock_result.get("spinor_formalism", {})
    print(f"  注入的旋量信息:")
    print(f"    theta: {spinor_info.get('theta')}°")
    print(f"    phase: {spinor_info.get('phase')}")
    print(f"    is_flipped: {spinor_info.get('is_flipped')}")
    print(f"    elevation: {spinor_info.get('elevation_level')}")

    print("\n" + "=" * 70)
    print("  测试完成")
    print("=" * 70)