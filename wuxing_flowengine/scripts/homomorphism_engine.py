"""
同态映射引擎 — 土·通集成模块
===============================
将同态映射三步协议嵌入五行流转引擎的"土·通"阶段，
实现从"描述性标签"到"可执行协议"的升级。

五行流转生命周期：
  木·生（学习）→ 火·化（内化）→ 金·克（应用）
  → 水·变（创新）→ 土·通（迁移）← 同态映射引擎在此

土·通 · 同态映射三步协议：
  Step 1 - 结构提取：从 Base 层提取概念-关系图
  Step 2 - 同态匹配：LLM + 规则匹配，带信度出口
  Step 3 - 迁移验证：≥3 场景验证，通过固化/失败记录

Phase 5 集成（P忠恕伦理 + 旋量形式化）：
  - 忠恕伦理校验：每次 transfer 自动注入忠恕双向评估
  - 旋量形式化跟踪：每次 transfer 记录为"反者道之动"螺旋演化

用法:
    from homomorphism_engine import HomomorphismEngine
    engine = HomomorphismEngine(base_dir)
    result = engine.transfer(source_domain, target_domain)
    print(engine.format_report(result))
"""

import os
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any

from structure_extractor import StructureExtractor
from homomorphism_matcher import HomomorphismMatcher
from transfer_validator import TransferValidator
from homomorphism_types import (
    ConceptRelationGraph, HomomorphismCandidate,
    VerificationResult, DeviationRecord,
    ConfidenceLevel, classify_confidence, confidence_decision,
)
from zhongshu_ethics import ZhongshuEthics, ZhongshuResult
from spinor_formalism import SpinorHomomorphismBridge, DaoSpinorState


class HomomorphismEngine:
    """
    同态映射引擎 — 土·通 阶段的主控制器

    封装三步协议为统一入口，对接到五行流转生命周期。
    """

    def __init__(self, base_dir: str = None, llm_matcher=None, llm_verifier=None,
                 enable_zhongshu: bool = True, enable_spinor: bool = True):
        """
        Args:
            base_dir: wuxing_flowengine 根目录
            llm_matcher: LLM 语义匹配函数（可选）
            llm_verifier: LLM 验证函数（可选）
            enable_zhongshu: 是否启用 P忠恕伦理校验（默认 True）
            enable_spinor: 是否启用旋量形式化跟踪（默认 True）
        """
        if base_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.base_dir = base_dir

        self.extractor = StructureExtractor(base_dir)
        self.matcher = HomomorphismMatcher(llm_matcher=llm_matcher)
        self.validator = TransferValidator(
            output_dir=os.path.join(base_dir, 'output'),
            llm_verifier=llm_verifier,
        )

        # Phase 5 集成: P忠恕伦理
        self.enable_zhongshu = enable_zhongshu
        self.zhongshu_ethics = ZhongshuEthics() if enable_zhongshu else None

        # Phase 5 集成: 旋量形式化
        self.enable_spinor = enable_spinor
        self.spinor_bridge = SpinorHomomorphismBridge() if enable_spinor else None

        self.transfer_history: List[dict] = []

    # ── 三步协议主入口 ──

    def transfer(self, source_domain: str, target_domain: str,
                 snapshot_month: str = None,
                 strategies: List[str] = None) -> dict:
        """
        执行土·通 同态映射三步协议

        Args:
            source_domain: 源域名称（用户已掌握的知识领域）
            target_domain: 目标域名称（用户要迁移到的新领域）
            snapshot_month: 快照月份
            strategies: 匹配策略

        Returns:
            {
                "step1": 结构提取结果,
                "step2": 同态匹配结果,
                "step3": 验证结果,
                "decision": 信度出口决策,
                "transfer_id": 迁移ID,
                "solidified": 是否固化,
                "deviation": 偏差记录（如有）,
            }
        """
        transfer_id = f"transfer_{uuid.uuid4().hex[:8]}"
        result = {
            "transfer_id": transfer_id,
            "timestamp": datetime.now().isoformat(),
            "source_domain": source_domain,
            "target_domain": target_domain,
            "snapshot_month": snapshot_month,
        }

        # ── Step 1: 结构提取 ──
        try:
            source_graph = self.extractor.extract_from_snapshot(
                snapshot_month or "2026-08", domain=source_domain
            )
            target_graph = self.extractor.extract_from_snapshot(
                snapshot_month or "2026-08", domain=target_domain
            )
        except ValueError as e:
            result["step1"] = {"status": "failed", "error": str(e)}
            result["decision"] = {"action": "error", "message": f"结构提取失败: {e}"}
            return result

        result["step1"] = {
            "status": "ok",
            "source_graph": {
                "node_count": source_graph.node_count,
                "edge_count": source_graph.edge_count,
                "relation_types": source_graph.relation_types,
            },
            "target_graph": {
                "node_count": target_graph.node_count,
                "edge_count": target_graph.edge_count,
                "relation_types": target_graph.relation_types,
            },
        }

        # ── Step 2: 同态匹配 ──
        candidate = self.matcher.match(source_graph, target_graph, strategies)
        decision = self.matcher.confidence_decision(candidate)

        result["step2"] = {
            "status": "ok",
            "mapping_count": candidate.mapping_count,
            "coverage": candidate.coverage,
            "relation_preservation_score": candidate.relation_preservation_score,
            "confidence_level": candidate.confidence_level.value,
            "unmatched_source_count": len(candidate.unmatched_source_nodes),
            "unmatched_target_count": len(candidate.unmatched_target_nodes),
            "top_mappings": [
                {
                    "source": m.source_node_name,
                    "target": m.target_node_name,
                    "confidence": m.confidence,
                    "rationale": m.rationale,
                }
                for m in sorted(candidate.mappings, key=lambda x: x.confidence, reverse=True)[:5]
            ],
        }
        result["decision"] = decision

        # ── Phase 5: P忠恕伦理校验 ──
        if self.enable_zhongshu:
            zs_result = self.zhongshu_ethics.evaluate(candidate, target_graph)
            result["zhongshu_ethics"] = {
                "zhong_score": zs_result.zhong_score,
                "shu_score": zs_result.shu_score,
                "zhongshu_score": zs_result.zhongshu_score,
                "level": zs_result.level,
                "ethical_advice": zs_result.ethical_advice,
                "classical_ref": zs_result.classical_ref,
            }

        # ── Step 3: 迁移验证 ──
        if decision["action"] == "no_match":
            result["step3"] = {
                "status": "skipped",
                "reason": "信度不足，不强配（不假装精确）",
                "message": decision["message"],
            }
            result["solidified"] = False
        else:
            verification = self.validator.verify(candidate)
            result["step3"] = {
                "status": "ok",
                "scenarios_tested": verification.scenarios_tested,
                "overall_pass": verification.overall_pass,
                "pass_rate": verification.pass_rate,
                "relation_preservation_rate": verification.relation_preservation_rate,
                "verified_count": len(verification.verified_mappings),
                "failed_count": len(verification.failed_mappings),
            }

            if verification.overall_pass:
                self.validator.solidify(verification)
                result["solidified"] = True
                result["solidified_path"] = self.validator.output_dir
            else:
                deviation = self.validator.record_deviation(
                    verification,
                    root_cause=f"目标域 '{target_domain}' 与源域 '{source_domain}' 的映射未能通过 ≥2/3 场景验证",
                    lesson=f"迁移 '{source_domain} → {target_domain}' 需要重新审视：结构保持不是'看着像'，而是'关系运算可传递'"
                )
                result["solidified"] = False
                result["deviation"] = {
                    "record_id": deviation.record_id,
                    "root_cause": deviation.root_cause,
                    "lesson": deviation.lesson,
                    "wuxing_implication": deviation.wuxing_implication,
                }

        # 记录历史
        self.transfer_history.append(result)

        # ── Phase 5: 旋量形式化跟踪 ──
        if self.enable_spinor:
            self.spinor_bridge.track_transfer(source_domain, target_domain, result)

        return result

    # ── 批量迁移 ──

    def transfer_all(self, source_domain: str,
                     snapshot_month: str = None,
                     strategies: List[str] = None) -> List[dict]:
        """
        将源域迁移到所有可用领域

        Returns:
            按关系保持度降序的结果列表
        """
        all_graphs = self.extractor.extract_all_domains(snapshot_month)
        if source_domain in all_graphs:
            del all_graphs[source_domain]

        results = []
        for domain, graph in all_graphs.items():
            result = self.transfer(source_domain, domain, snapshot_month, strategies)
            results.append(result)

        # 按关系保持度排序
        results.sort(
            key=lambda r: r.get("step2", {}).get("relation_preservation_score", 0),
            reverse=True
        )
        return results

    # ── 五行流转集成 ──

    def earth_flow_transfer(self, source_domain: str, target_domain: str,
                            wuxing_context: dict = None) -> dict:
        """
        土·通 阶段的五行流转集成

        在五行流转的"土·通"阶段调用同态映射引擎，
        输出包含五行诊断信息的完整迁移报告。

        Args:
            source_domain: 源域
            target_domain: 目标域
            wuxing_context: 当前五行诊断上下文（可选）

        Returns:
            增强版迁移报告（含五行流转信息）
        """
        result = self.transfer(source_domain, target_domain)

        # 注入五行流转上下文
        if wuxing_context:
            result["wuxing_context"] = {
                "current_stage": wuxing_context.get("stage", "?"),
                "dominant_wx": wuxing_context.get("dominant_wx", "?"),
                "H_ratio": wuxing_context.get("H_ratio", 0),
                "S_p": wuxing_context.get("S_p", 0),
            }

        # 五行流转解读
        result["earth_flow_interpretation"] = self._interpret_earth_flow(result)

        # Phase 5: 忠恕伦理增强五行流转解读
        if self.enable_zhongshu:
            zs = result.get("zhongshu_ethics", {})
            if zs:
                result["earth_flow_interpretation"]["zhongshu_note"] = (
                    f"忠恕综合: {zs.get('zhongshu_score', 0):.2f} ({zs.get('level', '?')})"
                )

        return result

    def _interpret_earth_flow(self, result: dict) -> dict:
        """解读土·通流转结果"""
        score = result.get("step2", {}).get("relation_preservation_score", 0)
        decision = result.get("decision", {}).get("action", "unknown")

        if decision == "no_match":
            return {
                "phase": "土·通（未启动）",
                "interpretation": "五行流转中，土·通阶段暂未激活——两域结构差异过大，不宜强行迁移",
                "advice": "建议回归'木·生'阶段，在新领域重新积累认知，待结构自然形成后再尝试迁移",
                "classical_ref": "反者道之动，弱者道之用。——不强配，正是'弱'的智慧",
            }
        elif decision == "verify_extra":
            return {
                "phase": "土·通（低信度）",
                "interpretation": "土·通正在尝试建立两域间的同态映射，但信度偏低，需更多验证",
                "advice": "增加验证场景至 5 个，重点观察关键关系的保持情况",
                "classical_ref": "慎终如始，则无败事。——低信度时不急于固化，多加验证",
            }
        elif result.get("solidified", False):
            return {
                "phase": "土·通（已固化）",
                "interpretation": "土·通成功建立两域间的同态映射，迁移路径已固化",
                "advice": "可在新领域继续深化，进入'水·变'阶段，基于迁移结构进行创新",
                "classical_ref": "既知其子，复守其母。——迁移后不忘源域根基",
            }
        else:
            return {
                "phase": "土·通（验证失败）",
                "interpretation": "土·通尝试建立映射但验证未通过——自以为同态但实际不同态",
                "advice": "偏差已记录到 SAD 镜鉴，建议回到'金·克'阶段重新审视映射前提",
                "classical_ref": "知不知，尚矣；不知知，病也。——承认'不同态'是真正认知的开始",
            }

    # ── 报告生成 ──

    def format_report(self, result: dict) -> str:
        """生成可读的迁移报告"""
        lines = []
        lines.append("=" * 70)
        lines.append(f"  土·通 同态映射报告")
        lines.append(f"  迁移ID: {result.get('transfer_id', '?')}")
        lines.append(f"  时间: {result.get('timestamp', '?')}")
        lines.append("=" * 70)

        lines.append(f"\n  源域: {result.get('source_domain', '?')}")
        lines.append(f"  目标域: {result.get('target_domain', '?')}")

        # Step 1
        s1 = result.get("step1", {})
        lines.append(f"\n  ── Step 1: 结构提取 ──")
        if s1.get("status") == "failed":
            lines.append(f"    ❌ 失败: {s1.get('error')}")
        else:
            sg = s1.get("source_graph", {})
            tg = s1.get("target_graph", {})
            lines.append(f"    源域: {sg.get('node_count', 0)} 节点, {sg.get('edge_count', 0)} 边")
            lines.append(f"    目标域: {tg.get('node_count', 0)} 节点, {tg.get('edge_count', 0)} 边")

        # Step 2
        s2 = result.get("step2", {})
        lines.append(f"\n  ── Step 2: 同态匹配 ──")
        lines.append(f"    映射数: {s2.get('mapping_count', 0)}")
        lines.append(f"    覆盖率: {s2.get('coverage', 0):.1%}")
        lines.append(f"    关系保持度: {s2.get('relation_preservation_score', 0):.4f}")
        lines.append(f"    信度等级: {s2.get('confidence_level', '?')}")

        top = s2.get("top_mappings", [])
        if top:
            lines.append(f"    Top 映射:")
            for m in top[:3]:
                lines.append(f"      {m['source']} → {m['target']} (信度={m['confidence']:.2f})")

        # 信度出口
        decision = result.get("decision", {})
        lines.append(f"\n    信度出口: {decision.get('action', '?')}")
        lines.append(f"    {decision.get('message', '')}")

        # Step 3
        s3 = result.get("step3", {})
        lines.append(f"\n  ── Step 3: 迁移验证 ──")
        if s3.get("status") == "skipped":
            lines.append(f"    ⊘ 跳过: {s3.get('reason', '')}")
        else:
            lines.append(f"    测试场景: {s3.get('scenarios_tested', 0)}")
            lines.append(f"    通过率: {s3.get('pass_rate', 0):.0%}")
            lines.append(f"    关系保持率: {s3.get('relation_preservation_rate', 0):.4f}")
            if s3.get("overall_pass"):
                lines.append(f"    ✅ 验证通过 — 迁移路径已固化")
            else:
                lines.append(f"    ❌ 验证未通过 — 偏差已记录")

        # 偏差
        dev = result.get("deviation")
        if dev:
            lines.append(f"\n  ── SAD 镜鉴 ──")
            lines.append(f"    记录ID: {dev.get('record_id')}")
            lines.append(f"    根因: {dev.get('root_cause')}")
            lines.append(f"    教训: {dev.get('lesson')}")

        # 五行流转解读
        efi = result.get("earth_flow_interpretation")
        if efi:
            lines.append(f"\n  ── 五行流转解读 ──")
            lines.append(f"    {efi.get('phase')}")
            lines.append(f"    {efi.get('interpretation')}")
            lines.append(f"    建议: {efi.get('advice')}")
            lines.append(f"    经典: {efi.get('classical_ref')}")

        # Phase 5: P忠恕伦理
        zs = result.get("zhongshu_ethics")
        if zs:
            lines.append(f"\n  ── P忠恕伦理校验 ──")
            lines.append(f"    忠度 (源域结构保持): {zs.get('zhong_score', 0):.4f}")
            lines.append(f"    恕度 (目标域相容):   {zs.get('shu_score', 0):.4f}")
            lines.append(f"    忠恕综合:            {zs.get('zhongshu_score', 0):.4f}")
            lines.append(f"    等级: {zs.get('level', '?')}")
            lines.append(f"    {zs.get('ethical_advice', '')}")
            lines.append(f"    经典: {zs.get('classical_ref', '')}")

        # Phase 5: 旋量形式化
        spinor = result.get("spinor_formalism")
        if spinor:
            lines.append(f"\n  ── 旋量-太极形式化 ──")
            lines.append(f"    否定次数: {spinor.get('negation_count', 0)}")
            lines.append(f"    旋转角度: {spinor.get('theta', 0)}°")
            lines.append(f"    相位: {spinor.get('phase', '?')}")
            lines.append(f"    相位翻转: {'是' if spinor.get('is_flipped') else '否'}")
            lines.append(f"    升华层级: {spinor.get('elevation_level', 0)}")
            lines.append(f"    道解读: {spinor.get('interpretation', '')}")

        lines.append("\n" + "=" * 70)
        return "\n".join(lines)

    def save_report(self, result: dict, output_path: str = None) -> str:
        """保存迁移报告为 JSON"""
        if output_path is None:
            output_dir = os.path.join(self.base_dir, 'output')
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(
                output_dir,
                f"transfer_{result.get('transfer_id', 'unknown')}.json"
            )

        # 移除不可序列化的对象
        clean = {}
        for k, v in result.items():
            if k in ("step1", "step2", "step3", "decision", "transfer_id",
                     "timestamp", "source_domain", "target_domain",
                     "snapshot_month", "solidified", "deviation",
                     "earth_flow_interpretation", "wuxing_context", "solidified_path",
                     "zhongshu_ethics", "spinor_formalism"):
                clean[k] = v

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(clean, f, ensure_ascii=False, indent=2)

        return output_path

    # ── 统计 ──

    def get_stats(self) -> dict:
        """获取引擎统计信息"""
        validator_stats = self.validator.get_stats()
        stats = {
            "total_transfers": len(self.transfer_history),
            "solidified": sum(1 for r in self.transfer_history if r.get("solidified", False)),
            "deviations": sum(1 for r in self.transfer_history if r.get("deviation")),
            "skipped": sum(1 for r in self.transfer_history
                          if r.get("decision", {}).get("action") == "no_match"),
            "validator_stats": validator_stats,
            "recent_transfers": [
                {
                    "id": r.get("transfer_id"),
                    "source": r.get("source_domain"),
                    "target": r.get("target_domain"),
                    "score": r.get("step2", {}).get("relation_preservation_score", 0),
                    "solidified": r.get("solidified", False),
                }
                for r in self.transfer_history[-5:]
            ],
        }

        # Phase 5: 忠恕统计
        if self.enable_zhongshu:
            zs_scores = [r.get("zhongshu_ethics", {}).get("zhongshu_score", 0)
                        for r in self.transfer_history]
            stats["zhongshu_stats"] = {
                "avg_zhongshu_score": round(sum(zs_scores) / max(len(zs_scores), 1), 4),
                "zhongshu_high": sum(1 for s in zs_scores if s >= 0.7),
                "zhongshu_low": sum(1 for s in zs_scores if s < 0.4),
            }

        return stats

    # ── Phase 5: 旋量形式化查询 ──

    def get_dao_summary(self, source_domain: str, target_domain: str) -> dict:
        """
        获取指定映射的道的演化摘要

        Args:
            source_domain: 源域
            target_domain: 目标域

        Returns:
            旋量演化摘要
        """
        if not self.enable_spinor:
            return {"error": "旋量形式化未启用"}
        return self.spinor_bridge.get_dao_summary(source_domain, target_domain)

    def get_all_dao_states(self) -> List[dict]:
        """获取所有道的旋量状态"""
        if not self.enable_spinor:
            return []
        return self.spinor_bridge.get_all_states()


# ═══════════════════════════════════════════════
# 独立测试
# ═══════════════════════════════════════════════

if __name__ == '__main__':
    print("=" * 70)
    print("  同态映射引擎 — 土·通集成测试")
    print("=" * 70)

    engine = HomomorphismEngine()

    # 测试 1: 高信度迁移
    print("\n[测试 1] 大语言模型 → 自然语言处理 (高信度)")
    result = engine.transfer("大语言模型", "自然语言处理")
    print(engine.format_report(result))

    # 测试 2: 低信度迁移
    print("\n[测试 2] 大语言模型 → 生成式AI (低信度)")
    result2 = engine.transfer("大语言模型", "生成式AI")
    print(engine.format_report(result2))

    # 测试 3: 五行流转集成
    print("\n[测试 3] 土·通 五行流转集成")
    result3 = engine.earth_flow_transfer(
        "大语言模型", "自然语言处理",
        wuxing_context={
            "stage": "通",
            "dominant_wx": "水",
            "H_ratio": 0.65,
            "S_p": 39.5,
        }
    )
    efi = result3.get("earth_flow_interpretation", {})
    print(f"  阶段: {efi.get('phase')}")
    print(f"  解读: {efi.get('interpretation')}")
    print(f"  建议: {efi.get('advice')}")

    # 测试 4: 批量迁移
    print("\n[测试 4] 批量迁移（大语言模型 → 所有领域）")
    all_results = engine.transfer_all("大语言模型")
    print(f"  总领域数: {len(all_results)}")
    print(f"  {'目标域':<20} {'关系保持度':>10} {'信度':>6} {'结果':>10}")
    print("  " + "-" * 50)
    for r in all_results[:10]:
        score = r.get("step2", {}).get("relation_preservation_score", 0)
        level = r.get("step2", {}).get("confidence_level", "?")
        decision = r.get("decision", {}).get("action", "?")
        if r.get("solidified"):
            outcome = "✅ 固化"
        elif r.get("deviation"):
            outcome = "📝 偏差"
        else:
            outcome = "⊘ 跳过"
        print(f"  {r['target_domain']:<20} {score:>10.4f} {level:>6} {outcome:>10}")

    # 测试 5: 统计
    print("\n[测试 5] 引擎统计")
    stats = engine.get_stats()
    print(f"  总迁移数: {stats['total_transfers']}")
    print(f"  固化: {stats['solidified']}")
    print(f"  偏差: {stats['deviations']}")
    print(f"  跳过: {stats['skipped']}")

    # 保存报告
    path = engine.save_report(result)
    print(f"\n  报告已保存至: {path}")

    print("\n" + "=" * 70)
    print("  测试完成")
    print("=" * 70)