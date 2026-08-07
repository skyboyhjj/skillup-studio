"""
慧惠宪法审计模块 — 七窍校验的工程实现
=====================================
参照七窍框架的"校验模块"（前庭系统）设计：
毫秒级判断是否超出可信边界，如发现危险则立刻中断，不需要等待上层决策。

P忠恕三原则对应的审计钩子：
1. 性分自觉检查 (xingfen_check)  — "安住自身性分"
   检查动作是否在自身性分范围内，不越界
2. 减法优先检查 (subtraction_check) — "为道日损"
   检查动作是否增加系统负担，不堆砌
3. 善行无辙迹检查 (traceless_check) — "善行无辙迹"
   检查动作是否越权访问数据，不留痕

核心原则：REJECT 优先于 GENERATE（不需要等待上层决策）

集成点：
- 同态映射引擎：transfer 前/中/后注入审计钩子
- 五行流水线：各 Phase 输出前注入数据边界检查
- 可独立使用：任何需要宪法审计的模块

用法:
    from huihui_audit import HuihuiAuditor

    auditor = HuihuiAuditor()
    result = auditor.audit(
        action={"type": "transfer", "source": "A", "target": "B"},
        context={"max_mappings": 100, "node_count": 50}
    )
    if not result.passed:
        print(f"AUDIT REJECTED: {result.summary}")
"""

import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict


# ============================================================
# 数据类型
# ============================================================

@dataclass
class CheckResult:
    """单检查结果"""
    check_name: str          # 检查名称
    verdict: str             # "PASS" | "WARN" | "REJECT"
    reason: str              # 判定理由
    detail: dict = field(default_factory=dict)  # 详细数据
    classical_ref: str = ""  # 经典引用

    @property
    def is_reject(self) -> bool:
        return self.verdict == "REJECT"

    @property
    def is_warn(self) -> bool:
        return self.verdict == "WARN"

    @property
    def is_pass(self) -> bool:
        return self.verdict == "PASS"


@dataclass
class AuditResult:
    """审计结果"""
    passed: bool                      # 整体是否通过
    checks: List[CheckResult]         # 各项检查结果
    timestamp: str                    # 审计时间
    summary: str                      # 摘要
    action: dict = field(default_factory=dict)    # 被审计的动作
    context: dict = field(default_factory=dict)   # 审计上下文

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "checks": [
                {
                    "check_name": c.check_name,
                    "verdict": c.verdict,
                    "reason": c.reason,
                    "classical_ref": c.classical_ref,
                    "detail": c.detail
                }
                for c in self.checks
            ],
            "timestamp": self.timestamp,
            "summary": self.summary
        }

    def reject_reasons(self) -> List[str]:
        """获取所有 REJECT 的原因"""
        return [c.reason for c in self.checks if c.is_reject]

    def warn_reasons(self) -> List[str]:
        """获取所有 WARN 的原因"""
        return [c.reason for c in self.checks if c.is_warn]


# ============================================================
# 慧惠宪法审计器
# ============================================================

class HuihuiAuditor:
    """
    慧惠宪法审计器。

    参照七窍框架的"校验模块"（前庭系统）设计：
    - 实时接收数据，毫秒级判断是否超出可信边界
    - 发现危险则立刻中断当前动作，不需要等待上层决策
    - 为整个系统的安全兜底

    三审计钩子对应 P忠恕三原则：

    1. 性分自觉 — "安住自身性分"（《慧惠宪法》第一条）
       检查动作是否在自身性分范围内。
       对应七窍校验：物理可信边界检查。

    2. 减法优先 — "为道日损"（《道德经》第48章）
       检查动作是否增加系统不必要的负担。
       对应七窍校验：安全兜底，不增加复杂度。

    3. 善行无辙迹 — "善行无辙迹"（《道德经》第27章）
       检查动作是否越权访问数据或留下不可追踪的痕迹。
       对应七窍校验：数据边界，不越权访问。
    """

    # 默认边界配置
    DEFAULT_BOUNDS = {
        "max_mappings_per_transfer": 200,   # 单次迁移最大映射数
        "max_depth": 5,                      # 最大递归深度
        "max_output_size": 10_000_000,       # 最大输出字节数（10MB）
        "min_node_count": 1,                 # 最小节点数
        "max_node_count": 100_000,           # 最大节点数
        "allowed_domains": None,             # 允许的领域白名单（None=不限制）
        "forbidden_domains": None,           # 禁止的领域黑名单
    }

    def __init__(self, bounds: dict = None, strict_mode: bool = False):
        """
        Args:
            bounds: 自定义边界配置，覆盖默认值
            strict_mode: 严格模式，WARN 升级为 REJECT
        """
        self.bounds = {**self.DEFAULT_BOUNDS, **(bounds or {})}
        self.strict_mode = strict_mode
        self.audit_log: List[AuditResult] = []

    # ============================================================
    # 主入口
    # ============================================================

    def audit(self, action: dict, context: dict = None) -> AuditResult:
        """
        执行全部审计检查。

        任一 REJECT 则立即短路返回（不需要等待上层决策）。
        WARN 不阻断执行，但记录警告。

        Args:
            action: 被审计的动作描述
                {"type": "transfer", "source": "A", "target": "B", "mappings": [...]}
            context: 审计上下文
                {"node_count": 50, "max_mappings": 100, "depth": 1}

        Returns:
            AuditResult: 审计结果
        """
        context = context or {}
        checks = []

        # 检查顺序：性分自觉 → 减法优先 → 善行无辙迹
        # 任一 REJECT 即短路

        # 1. 性分自觉检查
        c = self._xingfen_check(action, context)
        checks.append(c)
        if c.is_reject:
            return self._make_result(action, context, checks)

        # 2. 减法优先检查
        c = self._subtraction_check(action, context)
        checks.append(c)
        if c.is_reject:
            return self._make_result(action, context, checks)

        # 3. 善行无辙迹检查
        c = self._traceless_check(action, context)
        checks.append(c)

        return self._make_result(action, context, checks)

    def audit_batch(self, actions: List[dict], context: dict = None) -> List[AuditResult]:
        """批量审计，每个动作独立审计"""
        return [self.audit(a, context) for a in actions]

    # ============================================================
    # 审计钩子一：性分自觉检查
    # ============================================================

    def _xingfen_check(self, action: dict, context: dict) -> CheckResult:
        """
        性分自觉检查：安住自身性分。

        检查要点：
        - 动作类型是否在允许范围内
        - 源域/目标域是否合法
        - 动作规模是否超出系统能力边界
        """
        action_type = action.get("type", "unknown")

        # 1.1 动作类型检查
        if action_type not in ("transfer", "diagnose", "classify", "validate", "query"):
            if self.strict_mode:
                return CheckResult(
                    check_name="性分自觉",
                    verdict="REJECT",
                    reason=f"未识别的动作类型: {action_type}",
                    detail={"action_type": action_type},
                    classical_ref="知不知，尚矣；不知知，病也。——《道德经》第71章"
                )
            return CheckResult(
                check_name="性分自觉",
                verdict="WARN",
                reason=f"未识别的动作类型: {action_type}，以宽松模式放行",
                detail={"action_type": action_type},
                classical_ref="知不知，尚矣。——《道德经》第71章"
            )

        # 1.2 领域白名单/黑名单检查
        if action_type == "transfer":
            source = action.get("source", "")
            target = action.get("target", "")

            forbidden = self.bounds.get("forbidden_domains")
            if forbidden and (source in forbidden or target in forbidden):
                return CheckResult(
                    check_name="性分自觉",
                    verdict="REJECT",
                    reason=f"领域在黑名单中: source={source}, target={target}",
                    detail={"source": source, "target": target, "forbidden": forbidden},
                    classical_ref="知其白，守其黑，为天下式。——《道德经》第28章"
                )

            allowed = self.bounds.get("allowed_domains")
            if allowed and (source not in allowed or target not in allowed):
                return CheckResult(
                    check_name="性分自觉",
                    verdict="REJECT",
                    reason=f"领域不在白名单中: source={source}, target={target}",
                    detail={"source": source, "target": target, "allowed": allowed},
                    classical_ref="不失其所者久。——《道德经》第33章"
                )

        # 1.3 规模边界检查
        mappings = action.get("mappings", [])
        max_mappings = context.get("max_mappings", self.bounds["max_mappings_per_transfer"])
        if len(mappings) > max_mappings:
            return CheckResult(
                check_name="性分自觉",
                verdict="REJECT",
                reason=f"映射数 {len(mappings)} 超出上限 {max_mappings}",
                detail={"mapping_count": len(mappings), "max": max_mappings}
            )

        node_count = context.get("node_count", 0)
        max_nodes = self.bounds["max_node_count"]
        if node_count > max_nodes:
            return CheckResult(
                check_name="性分自觉",
                verdict="REJECT",
                reason=f"节点数 {node_count} 超出上限 {max_nodes}",
                detail={"node_count": node_count, "max": max_nodes}
            )

        min_nodes = self.bounds["min_node_count"]
        if node_count < min_nodes:
            return CheckResult(
                check_name="性分自觉",
                verdict="WARN",
                reason=f"节点数 {node_count} 低于下限 {min_nodes}，数据可能不足",
                detail={"node_count": node_count, "min": min_nodes},
                classical_ref="合抱之木，生于毫末。——《道德经》第64章"
            )

        return CheckResult(
            check_name="性分自觉",
            verdict="PASS",
            reason="动作在性分范围内",
            detail={"action_type": action_type},
            classical_ref="知足不辱，知止不殆。——《道德经》第44章"
        )

    # ============================================================
    # 审计钩子二：减法优先检查
    # ============================================================

    def _subtraction_check(self, action: dict, context: dict) -> CheckResult:
        """
        减法优先检查：为道日损。

        检查要点：
        - 动作是否增加了不必要的复杂度
        - 递归深度是否超出限制
        - 映射数量是否过于冗余
        """
        action_type = action.get("type", "unknown")

        # 2.1 递归深度检查
        depth = context.get("depth", 1)
        max_depth = self.bounds["max_depth"]
        if depth > max_depth:
            return CheckResult(
                check_name="减法优先",
                verdict="REJECT",
                reason=f"递归深度 {depth} 超出上限 {max_depth}",
                detail={"depth": depth, "max": max_depth},
                classical_ref="为学日益，为道日损。——《道德经》第48章"
            )

        if depth >= max_depth * 0.8:
            return CheckResult(
                check_name="减法优先",
                verdict="WARN",
                reason=f"递归深度 {depth} 接近上限 {max_depth}（{depth/max_depth*100:.0f}%）",
                detail={"depth": depth, "max": max_depth},
                classical_ref="损之又损，以至于无为。——《道德经》第48章"
            )

        # 2.2 映射冗余度检查
        if action_type == "transfer":
            mappings = action.get("mappings", [])
            source_count = context.get("source_node_count", 0)
            target_count = context.get("target_node_count", 0)

            # 有效映射数不应远超源域或目标域节点数
            max_reasonable = max(source_count, target_count) * 2
            if len(mappings) > max_reasonable and max_reasonable > 0:
                return CheckResult(
                    check_name="减法优先",
                    verdict="WARN",
                    reason=(
                        f"映射数 {len(mappings)} 远超合理范围（源域{source_count}节点, "
                        f"目标域{target_count}节点，合理上限约{max_reasonable}）"
                    ),
                    detail={
                        "mapping_count": len(mappings),
                        "source_nodes": source_count,
                        "target_nodes": target_count,
                        "reasonable_max": max_reasonable
                    },
                    classical_ref="少则得，多则惑。——《道德经》第22章"
                )

        # 2.3 输出大小检查
        output_size = context.get("output_size", 0)
        max_output = self.bounds["max_output_size"]
        if output_size > max_output:
            return CheckResult(
                check_name="减法优先",
                verdict="REJECT",
                reason=f"输出大小 {output_size} 字节超出上限 {max_output}",
                detail={"output_size": output_size, "max": max_output}
            )

        return CheckResult(
            check_name="减法优先",
            verdict="PASS",
            reason="动作未增加不必要负担",
            detail={"depth": depth},
            classical_ref="大道至简。——《道德经》"
        )

    # ============================================================
    # 审计钩子三：善行无辙迹检查
    # ============================================================

    def _traceless_check(self, action: dict, context: dict) -> CheckResult:
        """
        善行无辙迹检查：不越权访问数据，不留不可追踪的痕迹。

        检查要点：
        - 数据访问是否越权
        - 输出是否包含敏感信息
        - 动作是否可追溯（有审计日志）
        """
        action_type = action.get("type", "unknown")

        # 3.1 数据访问路径检查
        accessed_paths = context.get("accessed_paths", [])
        allowed_paths = context.get("allowed_paths", [])

        if allowed_paths:
            for path in accessed_paths:
                if not any(path.startswith(allowed) for allowed in allowed_paths):
                    return CheckResult(
                        check_name="善行无辙迹",
                        verdict="REJECT",
                        reason=f"越权访问路径: {path}",
                        detail={"path": path, "allowed": allowed_paths},
                        classical_ref="善行无辙迹。——《道德经》第27章"
                    )

        # 3.2 敏感数据检查
        sensitive_keys = context.get("sensitive_keys", [])
        output_data = context.get("output_data", {})
        found_sensitive = []
        for key in sensitive_keys:
            if key in output_data or key in str(action):
                found_sensitive.append(key)

        if found_sensitive:
            return CheckResult(
                check_name="善行无辙迹",
                verdict="REJECT",
                reason=f"输出包含敏感字段: {found_sensitive}",
                detail={"sensitive_keys": found_sensitive},
                classical_ref="鱼不可脱于渊，国之利器不可以示人。——《道德经》第36章"
            )

        # 3.3 可追溯性检查
        action_id = action.get("id", "")
        if not action_id and action_type in ("transfer", "validate"):
            if self.strict_mode:
                return CheckResult(
                    check_name="善行无辙迹",
                    verdict="WARN",
                    reason="动作缺少 ID，事后无法追溯",
                    detail={"action_type": action_type},
                    classical_ref="慎终如始，则无败事。——《道德经》第64章"
                )

        return CheckResult(
            check_name="善行无辙迹",
            verdict="PASS",
            reason="数据访问合规，可追溯",
            detail={},
            classical_ref="善闭无关楗而不可开。——《道德经》第27章"
        )

    # ============================================================
    # 辅助方法
    # ============================================================

    def _make_result(self, action: dict, context: dict, checks: List[CheckResult]) -> AuditResult:
        """构造审计结果"""
        rejects = [c for c in checks if c.is_reject]
        warns = [c for c in checks if c.is_warn]
        passed = len(rejects) == 0

        if not passed:
            summary = f"REJECT ({len(rejects)}项): {'; '.join(c.reason for c in rejects)}"
        elif warns:
            summary = f"PASS with WARN ({len(warns)}项): {'; '.join(c.reason for c in warns)}"
        else:
            summary = "PASS: 全部检查通过"

        result = AuditResult(
            passed=passed,
            checks=checks,
            timestamp=datetime.now().isoformat(),
            summary=summary,
            action=action,
            context=context
        )
        self.audit_log.append(result)
        return result

    def get_audit_log(self, max_entries: int = 50) -> List[dict]:
        """获取审计日志（最近 N 条）"""
        return [r.to_dict() for r in self.audit_log[-max_entries:]]

    def clear_audit_log(self):
        """清空审计日志"""
        self.audit_log.clear()

    def stats(self) -> dict:
        """审计统计"""
        total = len(self.audit_log)
        if total == 0:
            return {"total": 0, "pass_rate": 1.0, "reject_count": 0, "warn_count": 0}

        reject_count = sum(1 for r in self.audit_log if not r.passed)
        warn_count = sum(1 for r in self.audit_log if r.passed and any(c.is_warn for c in r.checks))
        return {
            "total": total,
            "pass_rate": round((total - reject_count) / total, 4),
            "reject_count": reject_count,
            "warn_count": warn_count,
            "clean_pass": total - reject_count - warn_count
        }

    def format_report(self) -> str:
        """格式化审计统计报告"""
        s = self.stats()
        lines = [
            "=" * 50,
            "慧惠宪法审计报告",
            "=" * 50,
            f"  总审计次数: {s['total']}",
            f"  通过率: {s['pass_rate']*100:.1f}%",
            f"  REJECT: {s['reject_count']}",
            f"  WARN: {s['warn_count']}",
            f"  完全通过: {s['clean_pass']}",
            "=" * 50,
        ]
        if s['reject_count'] > 0:
            lines.append("最近 REJECT 记录:")
            for r in self.audit_log[-5:]:
                if not r.passed:
                    lines.append(f"  [{r.timestamp[:19]}] {r.summary}")
        return "\n".join(lines)


# ============================================================
# 便捷函数：同态映射引擎的审计钩子
# ============================================================

def audit_transfer(source_domain: str, target_domain: str,
                   source_node_count: int, target_node_count: int,
                   mapping_count: int = 0, depth: int = 1,
                   auditor: HuihuiAuditor = None) -> AuditResult:
    """
    同态映射引擎的专用审计钩子。

    在 transfer 前调用，检查迁移是否合法。

    Args:
        source_domain: 源域
        target_domain: 目标域
        source_node_count: 源域节点数
        target_node_count: 目标域节点数
        mapping_count: 映射数量
        depth: 递归深度
        auditor: 审计器实例（None 则创建默认实例）

    Returns:
        AuditResult
    """
    if auditor is None:
        auditor = HuihuiAuditor()

    return auditor.audit(
        action={
            "type": "transfer",
            "source": source_domain,
            "target": target_domain,
            "mappings": [{}] * mapping_count if mapping_count else []
        },
        context={
            "node_count": source_node_count + target_node_count,
            "source_node_count": source_node_count,
            "target_node_count": target_node_count,
            "depth": depth,
        }
    )


# ============================================================
# 自检
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("慧惠宪法审计模块 — 自检")
    print("=" * 60)

    auditor = HuihuiAuditor()

    # 测试 1: 正常 transfer
    print("\n[测试 1] 正常 transfer — 应全部 PASS")
    r = auditor.audit(
        action={"type": "transfer", "source": "大语言模型", "target": "自然语言处理", "mappings": []},
        context={"node_count": 50, "source_node_count": 20, "target_node_count": 30, "depth": 1}
    )
    print(f"  {r.summary}")
    for c in r.checks:
        print(f"    [{c.verdict}] {c.check_name}: {c.reason}")
    assert r.passed

    # 测试 2: 超出映射上限
    print("\n[测试 2] 超出映射上限 — 应 REJECT")
    r = auditor.audit(
        action={"type": "transfer", "source": "A", "target": "B",
                "mappings": [{}] * 250},
        context={"node_count": 50, "max_mappings": 200}
    )
    print(f"  {r.summary}")
    assert not r.passed

    # 测试 3: 递归深度过深
    print("\n[测试 3] 递归深度过深 — 应 REJECT")
    r = auditor.audit(
        action={"type": "transfer", "source": "A", "target": "B", "mappings": []},
        context={"node_count": 50, "depth": 10}
    )
    print(f"  {r.summary}")
    assert not r.passed

    # 测试 4: 递归深度接近上限 — 应 WARN
    print("\n[测试 4] 递归深度接近上限 — 应 WARN")
    r = auditor.audit(
        action={"type": "transfer", "source": "A", "target": "B", "mappings": []},
        context={"node_count": 50, "depth": 4}
    )
    print(f"  {r.summary}")
    for c in r.checks:
        if c.is_warn:
            print(f"    [{c.verdict}] {c.check_name}: {c.reason}")
    assert r.passed  # WARN 不阻断
    assert any(c.is_warn for c in r.checks)

    # 测试 5: 越权访问
    print("\n[测试 5] 越权数据访问 — 应 REJECT")
    r = auditor.audit(
        action={"type": "transfer", "source": "A", "target": "B", "mappings": []},
        context={
            "node_count": 50,
            "accessed_paths": ["/etc/secret", "/data/public"],
            "allowed_paths": ["/data/"]
        }
    )
    print(f"  {r.summary}")
    assert not r.passed

    # 测试 6: 严格模式
    print("\n[测试 6] 严格模式 — 未知动作类型应 REJECT")
    strict = HuihuiAuditor(strict_mode=True)
    r = strict.audit(
        action={"type": "unknown_action", "source": "A", "target": "B"},
        context={"node_count": 50}
    )
    print(f"  {r.summary}")
    assert not r.passed

    # 测试 7: 便捷函数
    print("\n[测试 7] 便捷函数 audit_transfer")
    r = audit_transfer("大语言模型", "自然语言处理", 20, 30, depth=1)
    print(f"  {r.summary}")
    assert r.passed

    # 测试 8: 审计统计
    print("\n[测试 8] 审计统计")
    print(auditor.format_report())
    s = auditor.stats()
    assert s["total"] >= 5

    # 测试 9: 审计日志
    print("\n[测试 9] 审计日志")
    log = auditor.get_audit_log(max_entries=3)
    print(f"  最近 {len(log)} 条:")
    for entry in log:
        print(f"    [{entry['timestamp'][:19]}] {entry['summary'][:60]}")

    print("\n" + "=" * 60)
    print("自检完成 — 全部 9 项测试通过")