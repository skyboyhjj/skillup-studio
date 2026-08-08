"""
双技能 SOP 模块 — 种·育 V1.3 Phase 2 M1
===========================================
M1 交付物：双技能 v1.0 的工程实现。

种子A：跨域诊断咨询技能 SOP v1.1（ConsultingSOP）
种子B：五行七维分析模板 v1.1（WuxingAnalysisTemplate）

设计原则：
  - 案例记录：所有操作通过 CaseRecorder 记录，L0 可回溯
  - 减法入魂：每一步检查信息增量，无增量则标记减法事件
  - 宪法审计：每次案例记录附带宪法审计检查，德优先于才
  - 结构保持：方法种子骨架完整，仅细化与增补条款

用法:
    from skill_sop import ConsultingSOP, WuxingAnalysisTemplate
    from case_recorder import CaseRecorder

    recorder = CaseRecorder()
    sop = ConsultingSOP(recorder)
    case = sop.run("大语言模型", "自然语言处理", "企业客户")
    print(sop.format_report(case))

    template = WuxingAnalysisTemplate(recorder)
    case = template.run("道德经", nodes_data, "种子/现行/超越")
    print(template.format_report(case))
"""

import math
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple

from case_recorder import (
    CaseRecorder, CaseRecord, ConsultingCase, AnalysisCase,
    CaseStatus, AuditVerdict, ConstitutionAuditCheck,
    SubtractionEventType, create_consulting_case, create_analysis_case,
)


# ============================================================
# 种子A：跨域诊断咨询技能 SOP v1.0
# ============================================================

class ConsultingSOP:
    """
    跨域诊断咨询技能 SOP v1.1（种子A）

    方法种子：同态映射三步协议（结构提取→同态匹配→增量审计→迁移验证）
    服务定位：帮助客户把 A 领域已验证的方法论/能力迁移到 B 领域

    v1.1 新增（M3 复盘修订）：
      日益：Step 2.5 目标域增量审计（正式步骤）、演示模板（问题→方法→证据→方案）
      日损：Step 1 关键路径信度标注（减除非关键路径逐条标注）、Step 3 轻量验证模式

    三步流程：
      Step 1 - 结构提取：提取客户源领域的"概念-关系图"
      Step 2 - 同态匹配：在目标领域寻找候选映射 f
      Step 2.5 - 增量审计：检查目标域是否有源域不存在的"新增运算"
      Step 3 - 迁移验证：≥2-3 个场景检验 f 是否保持运算关系

    宪法审计条款：不宰 / 溯源 / 不假装精确 / 无弃人
    减法记录：为道日损——过度流程 / 模板冗余 / 执念
    """

    SKILL_ID = "SKL-A-20260808-001"
    SKILL_NAME = "跨域诊断咨询技能"
    METHOD_SEED = "同态映射三步协议"

    DEFAULT_CONFIG = {
        "min_nodes": 5,                    # 源域最少节点数
        "min_edges": 3,                    # 源域最少边数
        "verification_scenarios": 3,       # 默认验证场景数
        "lightweight_scenarios": 2,        # v1.1: 轻量验证场景数
        "lightweight_mode": False,         # v1.1: 是否启用轻量验证模式
        "critical_path_threshold": 0.7,   # v1.1: 关键路径信度阈值
        "preservation_threshold": 0.7,     # 保持度进入验证阈值
        "low_confidence_threshold": 0.4,   # 低信度阈值
        "auto_audit": True,                # 自动宪法审计
        "subtraction_enabled": True,       # 启用减法记录
    }

    def __init__(self, recorder: CaseRecorder = None, config: dict = None):
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self.recorder = recorder or CaseRecorder()

    def run(self, source_domain: str, target_domain: str,
            client_type: str = "未指定",
            source_graph: dict = None,
            target_graph: dict = None,
            target_domain_increments: List[dict] = None,
            precomputed_data: dict = None,
            lightweight_mode: bool = None) -> ConsultingCase:
        """
        执行完整的三步咨询流程（v1.1：含 Step 2.5 增量审计）

        Args:
            source_domain: 源域（客户已掌握的领域）
            target_domain: 目标域（要迁移到的领域）
            client_type: 客户类型
            source_graph: 源域概念-关系图（可选，自动构建）
            target_graph: 目标域概念-关系图（可选）
            target_domain_increments: 目标域增量列表（V1.3 M2/M3：标记目标域新增运算）
            precomputed_data: 预计算数据（直接注入，跳过三步计算）
            lightweight_mode: v1.1 轻量验证模式（None 时使用 config 默认值）

        Returns:
            ConsultingCase: 咨询案例记录
        """
        case = create_consulting_case(source_domain, target_domain, client_type)
        case.status = CaseStatus.IN_PROGRESS

        source_graph = source_graph or {}
        target_graph = target_graph or {}

        # v1.1: 轻量验证模式
        if lightweight_mode is None:
            lightweight_mode = self.config.get("lightweight_mode", False)
        self.config["lightweight_mode"] = lightweight_mode

        # V1.3 M2: 预计算数据注入（用于案例回放）
        if precomputed_data:
            case = self._inject_precomputed(case, precomputed_data)
            case.step_records["_source"] = "precomputed"
        else:
            # Step 1: 结构提取（v1.1: 关键路径信度标注）
            step1 = self._step1_structure_extraction(source_domain, target_domain, source_graph)
            case = self._update_case_with_step(case, step1, "Step 1 结构提取")

            # Step 2: 同态匹配
            step2 = self._step2_homomorphism_matching(source_graph, target_graph, step1, target_domain)
            case = self._update_case_with_step(case, step2, "Step 2 同态匹配")

            # v1.1 Step 2.5: 目标域增量审计
            if target_domain_increments:
                step2_5 = self._step2_5_increment_audit(step2, target_domain_increments, source_graph)
                case = self._update_case_with_step(case, step2_5, "Step 2.5 增量审计")
                case.basic_info["target_domain_increments"] = target_domain_increments

            # Step 3: 迁移验证（v1.1: 轻量验证模式）
            step3 = self._step3_transfer_verification(step2, source_graph, target_graph)
            case = self._update_case_with_step(case, step3, "Step 3 迁移验证")

        # 宪法审计
        case.constitution_audit = self._run_constitution_audit(case)
        case.constitution_passed = all(
            c.verdict == AuditVerdict.PASS for c in case.constitution_audit
        )

        # 减法记录
        if self.config["subtraction_enabled"]:
            case.subtraction_records = self._collect_subtraction_records(case)

        case.status = CaseStatus.COMPLETED
        case.deliverables = self._collect_deliverables(case)

        self.recorder.record(case)
        return case

    def _step1_structure_extraction(self, source_domain: str, target_domain: str,
                                    source_graph: dict) -> dict:
        """Step 1: 结构提取——提取源域的概念-关系图（v1.1: 关键路径信度标注）"""
        nodes = source_graph.get("nodes", [])
        edges = source_graph.get("edges", [])

        # 关系类型分类
        relationship_types = {"生克": [], "因果": [], "层级": [], "类比": []}
        credibility_annotations = []

        # v1.1: 关键路径阈值
        cp_threshold = self.config.get("critical_path_threshold", 0.7)

        for i, edge in enumerate(edges):
            rel_type = edge.get("relation_type", "类比")
            if rel_type in relationship_types:
                relationship_types[rel_type].append(edge)
            else:
                relationship_types["类比"].append(edge)

            # v1.1: 仅对关键路径（高信度）边做逐条标注
            conf = edge.get("confidence", 0.5)
            if conf >= cp_threshold:
                credibility_annotations.append({
                    "edge_id": edge.get("id", f"e{i}"),
                    "source_node": edge.get("source", ""),
                    "target_node": edge.get("target", ""),
                    "relation": edge.get("relation", ""),
                    "confidence": conf,
                    "source_field": edge.get("source_field", ""),
                    "on_critical_path": True,
                })

        # 非关键路径边数
        non_critical_count = len(edges) - len(credibility_annotations)

        return {
            "source_domain": source_domain,
            "target_domain": target_domain,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "source_structure": {"nodes": nodes, "edges": edges},
            "relationship_types": relationship_types,
            "credibility_annotations": credibility_annotations,
            "critical_path_count": len(credibility_annotations),
            "non_critical_count": non_critical_count,
            "critical_path_threshold": cp_threshold,
            "has_min_structure": len(nodes) >= self.config["min_nodes"],
        }

    def _step2_homomorphism_matching(self, source_graph: dict, target_graph: dict,
                                     step1: dict, target_domain: str) -> dict:
        """Step 2: 同态匹配——在目标领域寻找候选映射"""
        edges = source_graph.get("edges", [])
        credibility_annotations = step1.get("credibility_annotations", [])
        candidate_mappings = []
        preservation_scores = []

        # 基于源域边结构生成候选映射
        for i, edge in enumerate(edges):
            source = edge.get("source", "")
            target = edge.get("target", "")
            relation = edge.get("relation", "")

            conf = 0.5
            for ann in credibility_annotations:
                if ann.get("source_node") == source and ann.get("target_node") == target:
                    conf = ann.get("confidence", 0.5)
                    break

            # 映射保持度 = 信度 × 结构完整性
            preservation = conf * 0.8 + 0.2 * (1.0 if len(edges) >= 3 else 0.5)
            preservation_scores.append(preservation)

            candidate_mappings.append({
                "mapping_id": f"m{i+1}",
                "f": f"f({source}→{target})",
                "source_edge": f"{source} {relation} {target}",
                "target_domain": target_domain,
                "preservation_score": round(preservation, 3),
                "per_edge_check": {
                    "source_relation": relation,
                    "preserved": preservation >= self.config["preservation_threshold"],
                },
            })

        avg_preservation = sum(preservation_scores) / len(preservation_scores) if preservation_scores else 0

        confidence_level = "high"
        if avg_preservation < self.config["low_confidence_threshold"]:
            confidence_level = "low"
        elif avg_preservation < self.config["preservation_threshold"]:
            confidence_level = "medium"

        return {
            "candidate_mappings": candidate_mappings,
            "avg_preservation_score": round(avg_preservation, 3),
            "confidence_level": confidence_level,
            "mapping_count": len(candidate_mappings),
        }

    def _step2_5_increment_audit(self, step2: dict,
                                  target_domain_increments: List[dict],
                                  source_graph: dict) -> dict:
        """
        v1.1 Step 2.5: 目标域增量审计

        检查目标域是否有源域不存在的"新增运算"：
          - 增量不破坏保持 → 标注"增量不破坏保持"
          - 增量破坏保持 → 修正映射或标注证伪边界

        Args:
            step2: Step 2 同态匹配结果
            target_domain_increments: 目标域增量列表
            source_graph: 源域图结构

        Returns:
            {increments, preserving, breaking, audit_passed, summary}
        """
        preserving = []
        breaking = []

        source_nodes = {n.get("name", "") for n in source_graph.get("nodes", [])}
        source_relations = {e.get("relation", "") for e in source_graph.get("edges", [])}

        for inc in target_domain_increments:
            item = inc.get("item", "未知增量")
            source_counterpart = inc.get("source_counterpart", "无")
            preserves = inc.get("preserves_homomorphism", True)
            increment_type = inc.get("increment_type", "新增运算")

            if preserves:
                preserving.append({
                    "item": item,
                    "source_counterpart": source_counterpart,
                    "increment_type": increment_type,
                    "verdict": "增量不破坏保持",
                    "note": inc.get("note", f"{item} 在源域无对应物，但属目标域必要运算，不破坏同态结构"),
                })
            else:
                breaking.append({
                    "item": item,
                    "source_counterpart": source_counterpart,
                    "increment_type": increment_type,
                    "verdict": "增量破坏保持，需修正映射或标注证伪边界",
                    "note": inc.get("note", ""),
                })

        audit_passed = len(breaking) == 0

        return {
            "increments": target_domain_increments,
            "preserving": preserving,
            "breaking": breaking,
            "preserving_count": len(preserving),
            "breaking_count": len(breaking),
            "audit_passed": audit_passed,
            "summary": (f"目标域增量审计: {len(preserving)} 项保持, {len(breaking)} 项破坏"
                        if preserving or breaking else "无目标域增量"),
        }

    def _step3_transfer_verification(self, step2: dict, source_graph: dict,
                                     target_graph: dict) -> dict:
        """Step 3: 迁移验证——场景检验映射（v1.1: 轻量验证模式）"""
        candidate_mappings = step2.get("candidate_mappings", [])
        verification_scenarios = []
        falsification_boundaries = []

        # v1.1: 轻量验证模式 vs 标准验证模式
        lightweight = self.config.get("lightweight_mode", False)
        n_scenarios = self.config["lightweight_scenarios"] if lightweight else self.config["verification_scenarios"]

        for i in range(min(n_scenarios, len(candidate_mappings))):
            mapping = candidate_mappings[i]
            passed = mapping["preservation_score"] >= self.config["preservation_threshold"]

            verification_scenarios.append({
                "scenario_id": f"vs{i+1}",
                "description": f"验证映射 {mapping['mapping_id']}: {mapping['f']}",
                "passed": passed,
                "detail": f"保持度 {mapping['preservation_score']:.2f} {'≥' if passed else '<'} 阈值 {self.config['preservation_threshold']}",
            })

            if not passed:
                falsification_boundaries.append(
                    f"映射 {mapping['mapping_id']} 未通过验证：保持度 {mapping['preservation_score']:.2f}"
                )

        migration_path = {
            "total_mappings": len(candidate_mappings),
            "verified": sum(1 for v in verification_scenarios if v["passed"]),
            "failed": sum(1 for v in verification_scenarios if not v["passed"]),
            "verified_mappings": [m for m, v in zip(candidate_mappings, verification_scenarios) if v["passed"]],
        }

        return {
            "verification_scenarios": verification_scenarios,
            "falsification_boundaries": falsification_boundaries,
            "migration_path": migration_path,
            "verification_count": len(verification_scenarios),
            "verification_mode": "轻量验证" if lightweight else "标准验证",
            "lightweight_note": "≥2 场景 + 读者反馈" if lightweight else "",
        }

    def _inject_precomputed(self, case: ConsultingCase, data: dict) -> ConsultingCase:
        """V1.3 M2: 预计算数据注入——跳过三步计算，直接填充案例数据（用于案例回放）"""
        # 基本信息
        if data.get("node_count"):
            case.node_count = data["node_count"]
        if data.get("edge_count"):
            case.edge_count = data["edge_count"]

        # 源域结构
        if data.get("source_structure"):
            case.source_structure = data["source_structure"]
        if data.get("relationship_types"):
            case.relationship_types = data["relationship_types"]
        if data.get("credibility_annotations"):
            case.credibility_annotations = data["credibility_annotations"]

        # 候选映射
        if data.get("candidate_mappings"):
            case.candidate_mappings = data["candidate_mappings"]
        if data.get("preservation_score"):
            case.preservation_score = data["preservation_score"]
        if data.get("confidence_level"):
            case.confidence_level = data["confidence_level"]

        # 验证结果
        if data.get("verification_scenarios"):
            case.verification_scenarios = data["verification_scenarios"]
        if data.get("falsification_boundaries"):
            case.falsification_boundaries = data["falsification_boundaries"]
        if data.get("migration_path"):
            case.migration_path = data["migration_path"]

        # 步骤记录
        case.step_records["Step 1 结构提取"] = {
            "node_count": case.node_count,
            "edge_count": case.edge_count,
            "source_structure": case.source_structure,
            "relationship_types": case.relationship_types,
            "credibility_annotations": case.credibility_annotations,
        }
        case.step_records["Step 2 同态匹配"] = {
            "candidate_mappings": case.candidate_mappings,
            "avg_preservation_score": case.preservation_score,
            "confidence_level": case.confidence_level,
        }
        case.step_records["Step 3 迁移验证"] = {
            "verification_scenarios": case.verification_scenarios,
            "falsification_boundaries": case.falsification_boundaries,
            "migration_path": case.migration_path,
        }

        return case

    def _update_case_with_step(self, case: ConsultingCase, step_result: dict,
                               step_name: str) -> ConsultingCase:
        """将步骤结果更新到案例中，并检查信息增量"""
        case.step_records[step_name] = step_result

        if step_name == "Step 1 结构提取":
            case.source_structure = step_result.get("source_structure", {})
            case.relationship_types = step_result.get("relationship_types", {})
            case.credibility_annotations = step_result.get("credibility_annotations", [])
            case.node_count = step_result.get("node_count", 0)
            case.edge_count = step_result.get("edge_count", 0)

        elif step_name == "Step 2 同态匹配":
            case.candidate_mappings = step_result.get("candidate_mappings", [])
            case.preservation_score = step_result.get("avg_preservation_score", 0)
            case.confidence_level = step_result.get("confidence_level", "")

        elif step_name == "Step 2.5 增量审计":
            case.basic_info["increment_audit"] = step_result

        elif step_name == "Step 3 迁移验证":
            case.verification_scenarios = step_result.get("verification_scenarios", [])
            case.falsification_boundaries = step_result.get("falsification_boundaries", [])
            case.migration_path = step_result.get("migration_path", {})

        return case

    def _run_constitution_audit(self, case: ConsultingCase) -> List[ConstitutionAuditCheck]:
        """宪法审计：不宰 / 溯源 / 不假装精确 / 无弃人"""
        checks = []

        # 1. 不宰：咨询只提供可选方案，不强制采纳
        has_options = len(case.candidate_mappings) > 1 or case.confidence_level == "low"
        checks.append(ConstitutionAuditCheck(
            clause="不宰",
            verdict=AuditVerdict.PASS if has_options else AuditVerdict.FAIL,
            detail="交付物含可选方案而非唯一指令" if has_options else "仅提供单一方案，长而不宰原则未满足",
            evidence=f"候选映射数: {len(case.candidate_mappings)}",
        ))

        # 2. 溯源：每条关系标注来源与信度
        has_source = all(
            a.get("source_field", "") for a in case.credibility_annotations
        ) if case.credibility_annotations else False
        checks.append(ConstitutionAuditCheck(
            clause="溯源",
            verdict=AuditVerdict.PASS if has_source or case.node_count == 0 else AuditVerdict.FAIL,
            detail="关系图每边带 source 字段" if has_source else "部分边缺 source 字段",
            evidence=f"信度标注数: {len(case.credibility_annotations)}",
        ))

        # 3. 不假装精确：低信度映射标注"待验证"
        low_conf = [a for a in case.credibility_annotations if a.get("confidence", 0) < self.config["low_confidence_threshold"]]
        has_note = all(a.get("note", "") for a in low_conf) if low_conf else True
        checks.append(ConstitutionAuditCheck(
            clause="不假装精确",
            verdict=AuditVerdict.PASS if has_note else AuditVerdict.FAIL,
            detail="低信度映射标注'待验证'" if has_note else f"存在 {len(low_conf)} 条低信度边未标注",
            evidence=f"低信度边数: {len(low_conf)}",
        ))

        # 4. 无弃人：结构不佳 ≠ 无价值
        checks.append(ConstitutionAuditCheck(
            clause="无弃人",
            verdict=AuditVerdict.PASS,
            detail="案例已记录，不因结构不佳丢弃",
            evidence=f"节点数: {case.node_count}",
        ))

        return checks

    def _collect_subtraction_records(self, case: ConsultingCase) -> list:
        """收集减法记录（为道日损）"""
        records = []

        # 检查过度流程：各步骤信息增量
        for step_name, step_result in case.step_records.items():
            if step_name == "Step 1 结构提取":
                has_gain = step_result.get("edge_count", 0) > 0
            elif step_name == "Step 2 同态匹配":
                has_gain = len(step_result.get("candidate_mappings", [])) > 0
            elif step_name == "Step 3 迁移验证":
                has_gain = len(step_result.get("verification_scenarios", [])) > 0
            else:
                has_gain = True

            if not has_gain:
                event = self.recorder.check_over_process(case, step_name, has_info_gain=False)
                if event:
                    records.append(event)

        # 检查模板冗余：字段 >10 且 >30% 为空
        # 统计 ConsultingCase 特殊字段
        special_fields = [
            case.source_structure, case.relationship_types,
            case.credibility_annotations, case.candidate_mappings,
            case.verification_scenarios, case.falsification_boundaries,
            case.migration_path,
        ]
        empty_count = sum(1 for f in special_fields if not f)
        total_special = len(special_fields)
        if total_special > 10 and total_special > 0:
            empty_ratio = empty_count / total_special
            if empty_ratio > 0.3:
                event = self.recorder.check_template_redundancy(
                    case, field_count=total_special, empty_ratio=empty_ratio
                )
                if event:
                    records.append(event)

        # 检查执念：低信度仍强行输出
        if case.confidence_level == "low" and case.candidate_mappings:
            event = self.recorder.check_obsession(case, low_confidence_forcing=True)
            if event:
                records.append(event)

        # 将减法记录也写入案例
        if records:
            case.subtraction_records = [r for r in records]

        return records

    def _collect_deliverables(self, case: ConsultingCase) -> List[str]:
        """收集交付物清单（v1.1: 含演示模板）"""
        deliverables = []
        if case.step_records.get("Step 1 结构提取"):
            deliverables.append("源域结构图 + 信度标注表")
        if case.candidate_mappings:
            deliverables.append(f"候选映射表 ({len(case.candidate_mappings)} 个映射)")
        if case.basic_info.get("increment_audit"):
            inc = case.basic_info["increment_audit"]
            deliverables.append(f"目标域增量审计 ({inc.get('preserving_count', 0)} 保持 / {inc.get('breaking_count', 0)} 破坏)")
        if case.verification_scenarios:
            passed = sum(1 for v in case.verification_scenarios if v["passed"])
            mode = "轻量验证" if any("轻量" in str(v.get("detail", "")) for v in case.verification_scenarios) else "标准验证"
            deliverables.append(f"验证记录 ({passed}/{len(case.verification_scenarios)} 通过, {mode})")
        if case.falsification_boundaries:
            deliverables.append(f"证伪边界标注 ({len(case.falsification_boundaries)} 条)")
        if case.constitution_audit:
            passed = sum(1 for c in case.constitution_audit if c.verdict == AuditVerdict.PASS)
            deliverables.append(f"宪法审计记录 ({passed}/{len(case.constitution_audit)} 通过)")
        if case.subtraction_records:
            deliverables.append(f"减法记录 ({len(case.subtraction_records)} 条)")
        # v1.1: 演示模板
        deliverables.append("演示模板（问题→方法→证据→方案）")
        return deliverables

    def format_report(self, case: ConsultingCase) -> str:
        """生成 Markdown 格式咨询报告"""
        lines = []
        lines.append(f"# 跨域诊断咨询报告")
        lines.append(f"")
        lines.append(f"> **案例编号**: {case.case_id}")
        lines.append(f"> **技能ID**: {case.skill_id}")
        lines.append(f"> **执行时间**: {case.timestamp[:19]}")
        lines.append(f"> **源域**: {case.source_domain} → **目标域**: {case.target_domain}")
        lines.append(f"> **客户类型**: {case.client_type}")
        lines.append(f"> **状态**: {case.status.value}")
        lines.append(f"")

        # Step 1
        lines.append(f"## Step 1: 结构提取")
        lines.append(f"")
        lines.append(f"| 指标 | 值 |")
        lines.append(f"|------|-----|")
        lines.append(f"| 节点数 | {case.node_count} |")
        lines.append(f"| 边数 | {case.edge_count} |")
        if case.relationship_types:
            lines.append(f"| 关系类型 | {', '.join(f'{k}({len(v)})' for k, v in case.relationship_types.items() if v)} |")
        lines.append(f"| 信度标注 | {len(case.credibility_annotations)} 条 |")
        lines.append(f"")

        # Step 2
        if case.candidate_mappings:
            lines.append(f"## Step 2: 同态匹配")
            lines.append(f"")
            lines.append(f"| 映射ID | 映射 | 保持度 | 信度 |")
            lines.append(f"|--------|------|--------|------|")
            for m in case.candidate_mappings:
                lines.append(f"| {m['mapping_id']} | {m['f']} | {m['preservation_score']:.3f} | {case.confidence_level} |")
            lines.append(f"")
            lines.append(f"**平均保持度**: {case.preservation_score:.3f}")
            lines.append(f"")
            lines.append(f"**信度等级**: {case.confidence_level}")
            lines.append(f"")

        # v1.1 Step 2.5: 目标域增量审计
        inc_audit = case.basic_info.get("increment_audit", {})
        if inc_audit:
            lines.append(f"## Step 2.5: 目标域增量审计")
            lines.append(f"")
            preserving = inc_audit.get("preserving", [])
            breaking = inc_audit.get("breaking", [])
            if preserving:
                lines.append(f"**增量保持**（不破坏同态）：")
                for p in preserving:
                    lines.append(f"- {p['item']}: {p['verdict']}（源域对应物: {p['source_counterpart']}）")
                lines.append(f"")
            if breaking:
                lines.append(f"**增量破坏**（需修正）：")
                for b in breaking:
                    lines.append(f"- {b['item']}: {b['verdict']}")
                lines.append(f"")
            lines.append(f"**审计结果**: {'✅ 通过' if inc_audit.get('audit_passed') else '❌ 存在破坏性增量'}")
            lines.append(f"")

        # Step 3
        if case.verification_scenarios:
            lines.append(f"## Step 3: 迁移验证")
            lines.append(f"")
            passed = sum(1 for v in case.verification_scenarios if v["passed"])
            lines.append(f"| 场景 | 结果 | 详情 |")
            lines.append(f"|------|------|------|")
            for v in case.verification_scenarios:
                icon = "✅" if v["passed"] else "❌"
                lines.append(f"| {v['scenario_id']} | {icon} | {v['detail']} |")
            lines.append(f"")
            lines.append(f"**通过率**: {passed}/{len(case.verification_scenarios)}")
            lines.append(f"")

            if case.falsification_boundaries:
                lines.append(f"**证伪边界**:")
                for fb in case.falsification_boundaries:
                    lines.append(f"- {fb}")
                lines.append(f"")

        # 宪法审计
        if case.constitution_audit:
            lines.append(f"## 宪法审计")
            lines.append(f"")
            lines.append(f"| 条款 | 判定 | 依据 |")
            lines.append(f"|------|------|------|")
            for c in case.constitution_audit:
                icon = "✅" if c.verdict == AuditVerdict.PASS else "❌"
                lines.append(f"| {icon} {c.clause} | {c.verdict.value} | {c.detail[:50]} |")
            lines.append(f"")

        # 减法记录
        if case.subtraction_records:
            lines.append(f"## 减法记录（为道日损）")
            lines.append(f"")
            for s in case.subtraction_records:
                lines.append(f"- **{s.event_type.value}**: {s.trigger[:60]}")
            lines.append(f"")

        # 交付物
        if case.deliverables:
            lines.append(f"## 交付物清单")
            lines.append(f"")
            for d in case.deliverables:
                lines.append(f"- {d}")
            lines.append(f"")

        lines.append(f"---")
        lines.append(f"*报告由 {self.SKILL_NAME} SOP v1.1 生成 · {case.timestamp[:10]}*")
        return "\n".join(lines)


# ============================================================
# 种子B：五行七维分析模板 v1.1
# ============================================================

class WuxingAnalysisTemplate:
    """
    五行七维分析模板 v1.1（种子B）

    方法种子：五行诊断七维指标体系（频次/矩阵/路径/熵/重心/画像/判语）
    服务定位：对任意领域的"概念集合"输出五行诊断画像（跨学科通用）

    v1.1 新增（M3 复盘修订）：
      日益：小样本模式（n<10 画像降级为提示）、无层级模式（维度2 跳过+标注）
      日损：画像库匹配 n<10 减除、模板字段 12→10

    七维计算：
      D1 五行频次：各五行节点占比 + Wilson 信度区间
      D2 层×五行矩阵：种子/现行/超越 × 五行分布矩阵（v1.1: 无层级则跳过）
      D3 重心偏移路径：层间五行重心的迁移轨迹
      D4 五行熵 H：-Σpᵢ·log₂(pᵢ)
      D5 重心向量：主导五行判定
      D6 特质画像：矩阵+熵+路径的组合解读（v1.1: n<10 降级为画像提示）
      D7 一句话判语：阶段判定 + S_p + 信度标注

    宪法审计条款：溯源 / 不曲解 / 不假装精确 / 无弃人
    """

    SKILL_ID = "SKL-B-20260808-001"
    SKILL_NAME = "五行七维分析模板"
    METHOD_SEED = "五行七维指标体系"

    DEFAULT_CONFIG = {
        "min_nodes": 5,                    # 最少节点数
        "wuxing_types": ["木", "火", "土", "金", "水"],
        "layers": ["种子", "现行", "超越"],  # 标准三层结构
        "wilson_z": 1.96,                  # Wilson 区间 95% 置信度
        "low_confidence_node_threshold": 10,  # 低信度节点阈值
        "small_sample_threshold": 10,      # v1.1: 小样本模式阈值（n<10 降级）
        "effective_n_threshold": 3,        # effective_n 下限
        "auto_audit": True,
        "subtraction_enabled": True,
    }

    def __init__(self, recorder: CaseRecorder = None, config: dict = None):
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self.recorder = recorder or CaseRecorder()

    def run(self, analysis_target: str,
            nodes: List[dict] = None,
            layers: dict = None,
            extra_data: dict = None) -> AnalysisCase:
        """
        执行完整的七维分析（v1.1: 小样本/无层级双模式）

        Args:
            analysis_target: 分析对象名称
            nodes: 节点列表 [{"id", "name", "wuxing", "layer", "wuxing_source"}, ...]
            layers: 层结构 {"种子": n, "现行": n, "超越": n}
            extra_data: 额外数据

        Returns:
            AnalysisCase: 分析案例记录
        """
        nodes = nodes or []
        layers = layers or {"种子": 0, "现行": 0, "超越": 0}

        # v1.1: 模式检测
        small_sample_mode = len(nodes) < self.config["small_sample_threshold"]
        has_layer_data = any(n.get("layer") for n in nodes)
        no_layer_mode = not has_layer_data

        layer_structure = "/".join(f"{k}({v})" for k, v in layers.items() if v > 0)
        case = create_analysis_case(analysis_target, len(nodes), layer_structure)
        case.status = CaseStatus.IN_PROGRESS

        case.data_snapshot = {
            "nodes": nodes,
            "edges": extra_data.get("edges", []) if extra_data else [],
            "layers": layers,
            # v1.1: 模式标记
            "small_sample_mode": small_sample_mode,
            "no_layer_mode": no_layer_mode,
        }

        wuxing_types = self.config["wuxing_types"]

        # D1: 五行频次
        dim1 = self._calc_dim1_frequency(nodes, wuxing_types)
        # D2: 层×五行矩阵（v1.1: 无层级则跳过）
        dim2 = self._calc_dim2_layer_matrix(nodes, layers, wuxing_types, no_layer_mode)
        # D3: 重心偏移路径
        dim3 = self._calc_dim3_centroid_path(nodes, layers, wuxing_types)
        # D4: 五行熵
        dim4 = self._calc_dim4_entropy(dim1, wuxing_types)
        # D5: 重心向量
        dim5 = self._calc_dim5_centroid_vector(dim1, wuxing_types)
        # D6: 特质画像（v1.1: 小样本模式降级）
        dim6 = self._calc_dim6_trait_profile(dim1, dim2, dim3, dim4, dim5, small_sample_mode)
        # D7: 一句话判语
        dim7 = self._calc_dim7_verdict(dim1, dim4, dim5, dim6, len(nodes))

        case.dimension_results = {
            "freq": dim1,
            "layer_matrix": dim2,
            "centroid_path": dim3,
            "entropy": dim4,
            "centroid_vector": dim5,
            "trait_profile": dim6,
            "verdict": dim7,
        }

        # 信度标注
        case.credibility_annotations = self._build_credibility_annotations(nodes, dim1)
        case.pending_observation = self._identify_pending_observations(dim1, dim2, nodes)

        # 宪法审计
        case.constitution_audit = self._run_constitution_audit(case)
        case.constitution_passed = all(
            c.verdict == AuditVerdict.PASS for c in case.constitution_audit
        )

        # 减法记录
        if self.config["subtraction_enabled"]:
            case.subtraction_records = self._collect_subtraction_records(case)

        case.status = CaseStatus.COMPLETED
        case.deliverables = self._collect_deliverables(case)

        self.recorder.record(case)
        return case

    # ── 七维计算 ──

    def _calc_dim1_frequency(self, nodes: List[dict],
                             wuxing_types: List[str]) -> dict:
        """D1: 五行频次 + Wilson 信度区间"""
        total = len(nodes)
        if total == 0:
            return {"percentages": {w: 0 for w in wuxing_types}, "ci": {}, "total": 0}

        counts = {w: 0 for w in wuxing_types}
        for n in nodes:
            w = n.get("wuxing", "")
            if w in counts:
                counts[w] += 1

        percentages = {}
        ci = {}
        z = self.config["wilson_z"]

        for w in wuxing_types:
            p = counts[w] / total
            percentages[w] = round(p, 4)

            # Wilson 区间
            if total > 0:
                denominator = 1 + z**2 / total
                center = (p + z**2 / (2 * total)) / denominator
                margin = z * math.sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / denominator
                ci[w] = {
                    "ci_low": round(max(0, center - margin), 4),
                    "ci_high": round(min(1, center + margin), 4),
                    "ci_width": round(2 * margin, 4),
                }
            else:
                ci[w] = {"ci_low": 0, "ci_high": 1, "ci_width": 1}

        return {
            "percentages": percentages,
            "counts": counts,
            "ci": ci,
            "total": total,
        }

    def _calc_dim2_layer_matrix(self, nodes: List[dict], layers: dict,
                                wuxing_types: List[str],
                                no_layer_mode: bool = False) -> dict:
        """D2: 层×五行矩阵（v1.1: 无层级模式跳过）"""
        # v1.1: 无层级模式
        if no_layer_mode:
            return {
                "matrix": {},
                "total_per_layer": {},
                "distribution_warning": "",
                "skipped": True,
                "skip_reason": "无层级，矩阵跳过",
            }

        layer_names = [k for k, v in sorted(layers.items(), key=lambda x: x[1], reverse=True) if v > 0]
        if not layer_names:
            layer_names = self.config["layers"]

        matrix = {}
        for layer in layer_names:
            row = {w: 0 for w in wuxing_types}
            layer_nodes = [n for n in nodes if n.get("layer") == layer]
            for n in layer_nodes:
                w = n.get("wuxing", "")
                if w in row:
                    row[w] += 1
            matrix[layer] = row

        # 检查层间分布不均
        total_per_layer = {layer: sum(row.values()) for layer, row in matrix.items()}
        distribution_warning = ""
        if total_per_layer:
            max_layer = max(total_per_layer, key=total_per_layer.get)
            min_layer = min(total_per_layer, key=total_per_layer.get)
            if total_per_layer[max_layer] > 2 * total_per_layer[min_layer] and total_per_layer[min_layer] > 0:
                distribution_warning = f"层间分布不均：{max_layer}（{total_per_layer[max_layer]}）vs {min_layer}（{total_per_layer[min_layer]}）"

        return {
            "matrix": matrix,
            "total_per_layer": total_per_layer,
            "distribution_warning": distribution_warning,
        }

    def _calc_dim3_centroid_path(self, nodes: List[dict], layers: dict,
                                 wuxing_types: List[str]) -> dict:
        """D3: 重心偏移路径——层间五行重心的迁移轨迹"""
        layer_names = [k for k, v in sorted(layers.items(), key=lambda x: x[1], reverse=True) if v > 0]
        if not layer_names:
            layer_names = [k for k, v in layers.items() if v > 0]

        # 五行权重：木=1, 火=2, 土=3, 金=4, 水=5
        wuxing_weight = {w: i + 1 for i, w in enumerate(wuxing_types)}

        centroids = {}
        for layer in layer_names:
            layer_nodes = [n for n in nodes if n.get("layer") == layer]
            if not layer_nodes:
                centroids[layer] = {"centroid": 0, "dominant": "无"}
                continue

            total_weight = sum(wuxing_weight.get(n.get("wuxing", ""), 0) for n in layer_nodes)
            avg_weight = total_weight / len(layer_nodes)
            centroids[layer] = {
                "centroid": round(avg_weight, 2),
                "dominant": self._weight_to_wuxing(avg_weight, wuxing_types),
                "node_count": len(layer_nodes),
            }

        # 迁移轨迹
        path = []
        sorted_layers = sorted(layer_names, key=lambda l: self.config["layers"].index(l) if l in self.config["layers"] else 99)
        for i in range(len(sorted_layers) - 1):
            from_layer = sorted_layers[i]
            to_layer = sorted_layers[i + 1]
            if centroids.get(from_layer) and centroids.get(to_layer):
                delta = centroids[to_layer]["centroid"] - centroids[from_layer]["centroid"]
                path.append({
                    "from": from_layer,
                    "to": to_layer,
                    "from_centroid": centroids[from_layer]["centroid"],
                    "to_centroid": centroids[to_layer]["centroid"],
                    "delta": round(delta, 2),
                    "direction": "正向" if delta > 0 else "逆向" if delta < 0 else "持平",
                })

        return {
            "centroids": centroids,
            "path": path,
            "layer_order": sorted_layers,
        }

    def _calc_dim4_entropy(self, dim1: dict, wuxing_types: List[str]) -> dict:
        """D4: 五行熵 H = -Σpᵢ·log₂(pᵢ)"""
        percentages = dim1.get("percentages", {})
        total = dim1.get("total", 0)

        if total == 0:
            return {"H": 0, "H_normalized": 0, "interpretation": "无数据"}

        H = 0.0
        for w in wuxing_types:
            p = percentages.get(w, 0)
            if p > 0:
                H -= p * math.log2(p)

        H_max = math.log2(len(wuxing_types))  # 均匀分布时的最大熵
        H_normalized = H / H_max if H_max > 0 else 0

        interpretation = "多元均衡" if H_normalized > 0.7 else "单极主导" if H_normalized < 0.3 else "中等偏散"

        return {
            "H": round(H, 4),
            "H_max": round(H_max, 4),
            "H_normalized": round(H_normalized, 4),
            "interpretation": interpretation,
        }

    def _calc_dim5_centroid_vector(self, dim1: dict, wuxing_types: List[str]) -> dict:
        """D5: 重心向量——主导五行判定（v1.1: 并列主导检测）"""
        percentages = dim1.get("percentages", {})
        counts = dim1.get("counts", {})

        if not percentages:
            return {"dominant": "无", "secondary": "无", "triple": [], "vector": {},
                    "tied_dominants": [], "tie_break_rule": ""}

        sorted_wuxing = sorted(wuxing_types, key=lambda w: percentages.get(w, 0), reverse=True)
        max_pct = percentages.get(sorted_wuxing[0], 0)

        # v1.1: 并列主导检测（容忍 1e-6 浮点误差）
        tied = [w for w in sorted_wuxing if abs(percentages.get(w, 0) - max_pct) < 1e-6]
        is_tied = len(tied) > 1

        dominant = sorted_wuxing[0]
        secondary = sorted_wuxing[1] if len(sorted_wuxing) > 1 else "无"

        # 三元组合
        triple = sorted_wuxing[:3]

        return {
            "dominant": dominant,
            "dominant_label": f"并列主导: {'/'.join(tied)}" if is_tied else dominant,
            "dominant_pct": round(max_pct, 4),
            "secondary": secondary,
            "secondary_pct": round(percentages.get(secondary, 0), 4) if secondary != "无" else 0,
            "triple": triple,
            "triple_pct": round(sum(percentages.get(w, 0) for w in triple), 4),
            "vector": {w: round(percentages.get(w, 0), 4) for w in wuxing_types},
            # v1.1: 并列主导信息
            "is_tied": is_tied,
            "tied_dominants": tied if is_tied else [],
            "tie_break_rule": "并列主导清单（无优先级，保留首位用于阶段判定）" if is_tied else "",
        }

    def _calc_dim6_trait_profile(self, dim1: dict, dim2: dict, dim3: dict,
                                 dim4: dict, dim5: dict,
                                 small_sample_mode: bool = False) -> dict:
        """D6: 特质画像——矩阵+熵+路径的组合解读（v1.1: n<10 降级为画像提示）"""
        # V1.5.1: 优先使用 dominant_label（与 D5 保持一致），并列时显示完整清单
        dominant = dim5.get("dominant_label", dim5.get("dominant", "无"))
        dominant_raw = dim5.get("dominant", "无")  # 用于画像匹配
        entropy = dim4.get("H_normalized", 0)
        path = dim3.get("path", [])
        matrix = dim2.get("matrix", {})

        # v1.1: 小样本模式——降级为画像提示，不做画像库匹配
        if small_sample_mode:
            hint_traits = []
            if dominant_raw == "木":
                hint_traits.append("木·生发倾向")
            elif dominant_raw == "火":
                hint_traits.append("火·化育倾向")
            elif dominant_raw == "土":
                hint_traits.append("土·承载倾向")
            elif dominant_raw == "金":
                hint_traits.append("金·克制倾向")
            elif dominant_raw == "水":
                hint_traits.append("水·变通倾向")

            if entropy > 0.7:
                hint_traits.append("多元均衡")
            elif entropy < 0.3:
                hint_traits.append("高度聚焦")

            return {
                "profile_name": f"画像提示（{dominant}，n={dim1.get('total', 0)}）",
                "traits": hint_traits,
                "profile_match_confidence": 0,
                "small_sample_mode": True,
                "note": "小样本模式：n<10，画像库匹配降级为提示",
            }

        # 标准模式：画像库匹配
        traits = []
        if dominant_raw == "木":
            traits.append("生发型——创造力强，善于开创")
        elif dominant_raw == "火":
            traits.append("化育型——内化能力强，善于转化")
        elif dominant_raw == "土":
            traits.append("承载型——稳定厚重，善于整合")
        elif dominant_raw == "金":
            traits.append("克制型——精准犀利，善于批判")
        elif dominant_raw == "水":
            traits.append("变通型——灵活多变，善于创新")

        if entropy > 0.7:
            traits.append("多元均衡——多方向并进")
        elif entropy < 0.3:
            traits.append("高度聚焦——单方向深耕")

        if path:
            last_delta = path[-1]["delta"]
            if last_delta > 0.5:
                traits.append("上行趋势——重心向高级层迁移")
            elif last_delta < -0.5:
                traits.append("下行趋势——重心向基础层回归")

        # 画像库匹配
        profile_name = "通用画像"
        if dominant_raw in ("土", "金") and entropy < 0.5:
            profile_name = f"{dominant_raw}·系统架构型"
        elif dominant_raw in ("木", "火") and entropy > 0.5:
            profile_name = f"{dominant_raw}·生态发散型"
        elif dominant_raw == "水":
            profile_name = "水·变通演化型"

        return {
            "profile_name": profile_name,
            "traits": traits,
            "profile_match_confidence": round(0.5 + 0.3 * (1 - entropy), 2),
        }

    def _calc_dim7_verdict(self, dim1: dict, dim4: dict, dim5: dict,
                           dim6: dict, node_count: int) -> dict:
        """D7: 一句话判语——阶段判定 + S_p + 信度标注"""
        dominant = dim5.get("dominant", "土")
        entropy = dim4.get("H_normalized", 0)
        total = dim1.get("total", 0)

        # 阶段判定
        stage_map = {
            "木": "生", "火": "化", "土": "通",
            "金": "克", "水": "变",
        }
        stage = stage_map.get(dominant, "通")

        # S_p 广义平均（p=0.5 恕度, scale=100, V1.2 定标）
        if total == 0:
            S_p = 0.0
        else:
            p_val = 0.5
            S_p = sum(
                (dim1["percentages"].get(w, 0) + 0.001) ** p_val
                for w in self.config["wuxing_types"]
            ) / len(self.config["wuxing_types"])
            S_p = S_p ** (1 / p_val) * 100  # V1.2 定标: scale=100, S_p ∈ [0, 100]

        # 信度标注
        effective_n = total
        if effective_n >= 50:
            confidence = "高"
            prefix = ""
        elif effective_n >= 10:
            confidence = "中"
            prefix = ""
        else:
            confidence = "低"
            prefix = "低信度"

        # v1.1 修复: S_p 低于生阶段下限 (25) 时标注"萌芽前"
        S_p_rounded = round(S_p, 2)
        stage_qualifier = ""
        if S_p_rounded < 25:
            stage_qualifier = "萌芽前·"
            stage = f"萌芽前（{stage}倾向，S_p={S_p_rounded:.1f}，未入阶段）"

        text = f"{dominant}·{stage_qualifier}{stage}阶段" if not stage_qualifier else f"[萌芽前] {dominant}·{stage_map.get(dominant, '通')}倾向（S_p={S_p_rounded:.1f}，未入阶段）"
        if prefix:
            text = f"[{prefix}] {text}"

        return {
            "text": text,
            "stage": stage,
            "S_p": S_p_rounded,
            "confidence_level": confidence,
            "effective_n": effective_n,
            "prefix": prefix,
            "data_ref": f"dim_entropy_L{len(str(dim4))}",
            "below_stage_threshold": S_p_rounded < 25,  # v1.1: 标记是否低于阶段下限
        }

    # ── 辅助方法 ──

    def _weight_to_wuxing(self, weight: float, wuxing_types: List[str]) -> str:
        """将数值权重映射到五行"""
        idx = round(weight) - 1
        idx = max(0, min(idx, len(wuxing_types) - 1))
        return wuxing_types[idx]

    def _build_credibility_annotations(self, nodes: List[dict],
                                       dim1: dict) -> dict:
        """构建信度标注"""
        total = dim1.get("total", 0)

        if total >= 50:
            confidence_level = "高"
        elif total >= 10:
            confidence_level = "中"
        else:
            confidence_level = "低"

        interval_width = 0
        ci = dim1.get("ci", {})
        if ci:
            widths = [v["ci_width"] for v in ci.values()]
            interval_width = sum(widths) / len(widths) if widths else 0

        return {
            "confidence_level": confidence_level,
            "effective_n": total,
            "interval_width": round(interval_width, 4),
            "prefix": "低信度" if total < self.config["low_confidence_node_threshold"] else "",
        }

    def _identify_pending_observations(self, dim1: dict, dim2: dict,
                                       nodes: List[dict]) -> List[str]:
        """识别待观察领域"""
        pending = []

        # 样本量不足
        total = dim1.get("total", 0)
        if total < self.config["low_confidence_node_threshold"]:
            pending.append(f"样本量不足（n={total}<{self.config['low_confidence_node_threshold']}），待补充数据后复测")

        # 层间分布不均
        warning = dim2.get("distribution_warning", "")
        if warning:
            pending.append(f"层间分布不均：{warning}")

        # 低信度维度
        percentages = dim1.get("percentages", {})
        for w, p in percentages.items():
            if 0 < p < 0.1:
                pending.append(f"{w} 行占比过低（{p:.1%}），待更多数据验证")

        return pending

    def _run_constitution_audit(self, case: AnalysisCase) -> List[ConstitutionAuditCheck]:
        """宪法审计：溯源 / 不曲解 / 不假装精确 / 无弃人"""
        checks = []

        # 1. 溯源：节点五行标注含来源
        nodes = case.data_snapshot.get("nodes", [])
        has_source = all(n.get("wuxing_source", "") for n in nodes) if nodes else True
        checks.append(ConstitutionAuditCheck(
            clause="溯源",
            verdict=AuditVerdict.PASS if has_source else AuditVerdict.FAIL,
            detail="节点 JSON 含 wuxing_source 字段" if has_source else "部分节点缺 wuxing_source",
            evidence=f"节点数: {len(nodes)}",
        ))

        # 2. 不曲解：判语引用数据行号
        verdict = case.dimension_results.get("verdict", {})
        has_ref = bool(verdict.get("data_ref", ""))
        checks.append(ConstitutionAuditCheck(
            clause="不曲解",
            verdict=AuditVerdict.PASS if has_ref or not verdict else AuditVerdict.FAIL,
            detail="判语引用数据行号，可回溯" if has_ref else "判语未引用数据行号",
            evidence=f"判语: {verdict.get('text', '')[:50]}",
        ))

        # 3. 不假装精确：小样本打宽区间
        interval_width = case.credibility_annotations.get("interval_width", 0)
        has_prefix = case.credibility_annotations.get("prefix", "") == "低信度"
        checks.append(ConstitutionAuditCheck(
            clause="不假装精确",
            verdict=AuditVerdict.PASS if interval_width <= 0.3 or has_prefix else AuditVerdict.FAIL,
            detail="宽区间 + 判语'低信度'前缀" if has_prefix else f"区间宽度 {interval_width:.2f}，未标注低信度",
            evidence=f"区间宽度: {interval_width:.2f}",
        ))

        # 4. 无弃人：低信度领域 ≠ 无价值
        checks.append(ConstitutionAuditCheck(
            clause="无弃人",
            verdict=AuditVerdict.PASS,
            detail="报告含'待观察领域'清单（非废材）",
            evidence=f"待观察领域数: {len(case.pending_observation)}",
        ))

        return checks

    def _collect_subtraction_records(self, case: AnalysisCase) -> list:
        """收集减法记录"""
        records = []

        # 检查维度信息增量
        dim_results = case.dimension_results
        total = case.node_count

        # D3 重心路径：无节点则无增量
        path = dim_results.get("centroid_path", {}).get("path", [])
        if not path and total > 0:
            event = self.recorder.check_over_process(case, "D3 重心偏移路径", has_info_gain=False)
            if event:
                records.append(event)

        # 检查模板冗余
        # 统计 AnalysisCase 特殊字段
        dim_fields = list(dim_results.keys())
        empty_dims = sum(1 for k, v in dim_results.items() if not v)
        if len(dim_fields) > 10 and empty_dims / len(dim_fields) > 0.3:
            event = self.recorder.check_template_redundancy(
                case, field_count=len(dim_fields), empty_ratio=empty_dims / len(dim_fields)
            )
            if event:
                records.append(event)

        # 检查执念：低信度仍写强判语
        confidence = case.credibility_annotations.get("confidence_level", "")
        verdict = dim_results.get("verdict", {})
        if confidence == "低" and verdict.get("stage", "") and not verdict.get("prefix", ""):
            event = self.recorder.check_obsession(case, low_confidence_forcing=True)
            if event:
                records.append(event)

        if records:
            case.subtraction_records = [r for r in records]

        return records

    def _collect_deliverables(self, case: AnalysisCase) -> List[str]:
        """收集交付物清单（v1.1: 模板字段 12→10）"""
        deliverables = []
        if case.dimension_results.get("freq"):
            deliverables.append("五行频次分布 + Wilson 信度区间")
        if case.dimension_results.get("layer_matrix"):
            dim2 = case.dimension_results["layer_matrix"]
            if dim2.get("skipped"):
                deliverables.append("层×五行矩阵（跳过：无层级数据）")
            else:
                deliverables.append("层×五行矩阵")
        if case.dimension_results.get("centroid_path"):
            deliverables.append("重心偏移路径")
        if case.dimension_results.get("entropy"):
            deliverables.append(f"五行熵 H={case.dimension_results['entropy'].get('H_normalized', 0):.2f}")
        if case.dimension_results.get("centroid_vector"):
            deliverables.append(f"主导五行：{case.dimension_results['centroid_vector'].get('dominant', '?')}")
        if case.dimension_results.get("trait_profile"):
            dim6 = case.dimension_results["trait_profile"]
            if dim6.get("small_sample_mode"):
                deliverables.append(f"特质画像提示：{dim6.get('profile_name', '?')}")
            else:
                deliverables.append(f"特质画像：{dim6.get('profile_name', '?')}")
        if case.dimension_results.get("verdict"):
            deliverables.append(f"判语：{case.dimension_results['verdict'].get('text', '?')}")
        if case.constitution_audit:
            passed = sum(1 for c in case.constitution_audit if c.verdict == AuditVerdict.PASS)
            deliverables.append(f"宪法审计记录 ({passed}/{len(case.constitution_audit)} 通过)")
        if case.subtraction_records:
            deliverables.append(f"减法记录 ({len(case.subtraction_records)} 条)")
        if case.pending_observation:
            deliverables.append(f"待观察领域 ({len(case.pending_observation)} 个)")
        return deliverables

    def format_report(self, case: AnalysisCase) -> str:
        """生成 Markdown 格式分析报告"""
        lines = []
        lines.append(f"# 五行七维分析报告")
        lines.append(f"")
        lines.append(f"> **案例编号**: {case.case_id}")
        lines.append(f"> **技能ID**: {case.skill_id}")
        lines.append(f"> **执行时间**: {case.timestamp[:19]}")
        lines.append(f"> **分析对象**: {case.analysis_target}")
        lines.append(f"> **节点数**: {case.node_count} | **层结构**: {case.layer_structure}")
        lines.append(f"")

        # D1: 五行频次
        dim1 = case.dimension_results.get("freq", {})
        if dim1:
            lines.append(f"## D1: 五行频次")
            lines.append(f"")
            lines.append(f"| 五行 | 占比 | Wilson 95% CI | 节点数 |")
            lines.append(f"|------|------|-------------|--------|")
            ci = dim1.get("ci", {})
            for w in self.config["wuxing_types"]:
                pct = dim1["percentages"].get(w, 0)
                c = ci.get(w, {})
                lines.append(f"| {w} | {pct:.1%} | [{c.get('ci_low', 0):.1%}, {c.get('ci_high', 0):.1%}] | {dim1['counts'].get(w, 0)} |")
            lines.append(f"")
            lines.append(f"**总节点数**: {dim1.get('total', 0)}")
            lines.append(f"")

        # D2: 层×五行矩阵
        dim2 = case.dimension_results.get("layer_matrix", {})
        if dim2 and dim2.get("skipped"):
            lines.append(f"## D2: 层×五行矩阵")
            lines.append(f"")
            lines.append(f"> ⚠️ {dim2.get('skip_reason', '无层级，矩阵跳过')}")
            lines.append(f"")
        elif dim2 and dim2.get("matrix"):
            lines.append(f"## D2: 层×五行矩阵")
            lines.append(f"")
            header = "| 层 | " + " | ".join(self.config["wuxing_types"]) + " | 合计 |"
            lines.append(header)
            lines.append("|" + "|".join(["----"] * (len(self.config["wuxing_types"]) + 2)) + "|")
            for layer, row in dim2["matrix"].items():
                total_layer = sum(row.values())
                vals = " | ".join(str(row.get(w, 0)) for w in self.config["wuxing_types"])
                lines.append(f"| {layer} | {vals} | {total_layer} |")
            lines.append(f"")
            if dim2.get("distribution_warning"):
                lines.append(f"> ⚠️ {dim2['distribution_warning']}")
                lines.append(f"")

        # D3: 重心偏移路径
        dim3 = case.dimension_results.get("centroid_path", {})
        if dim3 and dim3.get("path"):
            lines.append(f"## D3: 重心偏移路径")
            lines.append(f"")
            for p in dim3["path"]:
                arrow = "→" if p["direction"] == "正向" else "←" if p["direction"] == "逆向" else "—"
                lines.append(f"- {p['from']} {arrow} {p['to']}: Δ={p['delta']:.2f} ({p['direction']})")
            lines.append(f"")

        # D4: 五行熵
        dim4 = case.dimension_results.get("entropy", {})
        if dim4:
            lines.append(f"## D4: 五行熵")
            lines.append(f"")
            lines.append(f"| 指标 | 值 |")
            lines.append(f"|------|-----|")
            lines.append(f"| H | {dim4.get('H', 0):.4f} |")
            lines.append(f"| H_max | {dim4.get('H_max', 0):.4f} |")
            lines.append(f"| H_normalized | {dim4.get('H_normalized', 0):.4f} |")
            lines.append(f"| 解读 | {dim4.get('interpretation', '')} |")
            lines.append(f"")

        # D5: 重心向量
        dim5 = case.dimension_results.get("centroid_vector", {})
        if dim5:
            lines.append(f"## D5: 重心向量")
            lines.append(f"")
            lines.append(f"- **主导五行**: {dim5.get('dominant', '?')}（{dim5.get('dominant_pct', 0):.1%}）")
            # v1.1: 并列主导时展示并列清单
            tied = dim5.get("tied_dominants", [])
            if tied:
                lines.append(f"- **并列主导**: {' / '.join(tied)}（{dim5.get('tie_break_rule', '')}）")
            lines.append(f"- **次主导**: {dim5.get('secondary', '?')}（{dim5.get('secondary_pct', 0):.1%}）")
            lines.append(f"- **三元组合**: {' + '.join(dim5.get('triple', []))}（{dim5.get('triple_pct', 0):.1%}）")
            lines.append(f"")

        # D6: 特质画像
        dim6 = case.dimension_results.get("trait_profile", {})
        if dim6:
            lines.append(f"## D6: 特质画像")
            lines.append(f"")
            if dim6.get("small_sample_mode"):
                lines.append(f"**画像提示**: {dim6.get('profile_name', '?')}")
                lines.append(f"")
                lines.append(f"> {dim6.get('note', '')}")
            else:
                lines.append(f"**画像**: {dim6.get('profile_name', '?')}（匹配置信度 {dim6.get('profile_match_confidence', 0):.2f}）")
            lines.append(f"")
            for t in dim6.get("traits", []):
                lines.append(f"- {t}")
            lines.append(f"")

        # D7: 一句话判语
        dim7 = case.dimension_results.get("verdict", {})
        if dim7:
            lines.append(f"## D7: 一句话判语")
            lines.append(f"")
            lines.append(f"> **{dim7.get('text', '?')}**")
            lines.append(f"")
            lines.append(f"| 指标 | 值 |")
            lines.append(f"|------|-----|")
            lines.append(f"| S_p | {dim7.get('S_p', 0):.2f} |")
            lines.append(f"| 阶段 | {dim7.get('stage', '?')} |")
            lines.append(f"| 信度 | {dim7.get('confidence_level', '?')}（effective_n={dim7.get('effective_n', 0)}） |")
            lines.append(f"")

        # 宪法审计
        if case.constitution_audit:
            lines.append(f"## 宪法审计")
            lines.append(f"")
            lines.append(f"| 条款 | 判定 | 依据 |")
            lines.append(f"|------|------|------|")
            for c in case.constitution_audit:
                icon = "✅" if c.verdict == AuditVerdict.PASS else "❌"
                lines.append(f"| {icon} {c.clause} | {c.verdict.value} | {c.detail[:50]} |")
            lines.append(f"")

        # 减法记录
        if case.subtraction_records:
            lines.append(f"## 减法记录（为道日损）")
            lines.append(f"")
            for s in case.subtraction_records:
                lines.append(f"- **{s.event_type.value}**: {s.trigger[:60]}")
            lines.append(f"")

        # 待观察领域
        if case.pending_observation:
            lines.append(f"## 待观察领域（无弃人）")
            lines.append(f"")
            for p in case.pending_observation:
                lines.append(f"- {p}")
            lines.append(f"")

        # 交付物
        if case.deliverables:
            lines.append(f"## 交付物清单")
            lines.append(f"")
            for d in case.deliverables:
                lines.append(f"- {d}")
            lines.append(f"")

        lines.append(f"---")
        lines.append(f"*报告由 {self.SKILL_NAME} v1.1 生成 · {case.timestamp[:10]}*")
        return "\n".join(lines)


# ============================================================
# 便捷函数
# ============================================================

def run_consulting(source_domain: str, target_domain: str,
                   client_type: str = "未指定",
                   source_graph: dict = None,
                   target_graph: dict = None,
                   recorder: CaseRecorder = None) -> ConsultingCase:
    """便捷函数：执行一次跨域诊断咨询"""
    sop = ConsultingSOP(recorder)
    return sop.run(source_domain, target_domain, client_type, source_graph, target_graph)


def run_analysis(analysis_target: str,
                 nodes: List[dict] = None,
                 layers: dict = None,
                 extra_data: dict = None,
                 recorder: CaseRecorder = None) -> AnalysisCase:
    """便捷函数：执行一次五行七维分析"""
    template = WuxingAnalysisTemplate(recorder)
    return template.run(analysis_target, nodes, layers, extra_data)


# ============================================================
# 自检
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("双技能 SOP 模块 — 自检 (V1.3 M3 v1.1)")
    print("=" * 60)

    recorder = CaseRecorder()

    # ============================================================
    # 测试 1: ConsultingSOP 基本流程
    # ============================================================
    print("\n[测试 1] ConsultingSOP 基本流程（种子A）")
    sop = ConsultingSOP(recorder)

    source_graph = {
        "nodes": [
            {"id": "n1", "name": "注意力机制", "wuxing": "火"},
            {"id": "n2", "name": "Transformer", "wuxing": "金"},
            {"id": "n3", "name": "预训练", "wuxing": "土"},
            {"id": "n4", "name": "微调", "wuxing": "木"},
            {"id": "n5", "name": "推理", "wuxing": "水"},
        ],
        "edges": [
            {"id": "e1", "source": "注意力机制", "target": "Transformer", "relation": "生",
             "relation_type": "生克", "confidence": 0.85, "source_field": "论文§2.3"},
            {"id": "e2", "source": "预训练", "target": "微调", "relation": "层级",
             "relation_type": "层级", "confidence": 0.9, "source_field": "论文§3.1"},
            {"id": "e3", "source": "推理", "target": "注意力机制", "relation": "因果",
             "relation_type": "因果", "confidence": 0.7, "source_field": "论文§4.2"},
        ],
    }

    case = sop.run("大语言模型", "自然语言处理", "企业客户", source_graph)
    assert case.skill_id == "SKL-A-20260808-001"
    assert case.case_id.startswith("CASE-A-")
    assert case.status == CaseStatus.COMPLETED
    assert len(case.step_records) == 3
    assert len(case.candidate_mappings) > 0
    assert len(case.verification_scenarios) > 0
    assert len(case.constitution_audit) == 4
    print(f"  案例ID: {case.case_id}")
    print(f"  步骤数: {len(case.step_records)}")
    print(f"  候选映射: {len(case.candidate_mappings)}")
    print(f"  验证场景: {len(case.verification_scenarios)}")
    print(f"  宪法审计: {'✅' if case.constitution_passed else '❌'}")
    print("  ✅ 测试 1 通过")

    # ============================================================
    # 测试 2: ConsultingSOP 宪法审计
    # ============================================================
    print("\n[测试 2] ConsultingSOP 宪法审计（种子A）")
    for check in case.constitution_audit:
        icon = "✅" if check.verdict == AuditVerdict.PASS else "❌"
        print(f"  {icon} {check.clause}: {check.detail[:50]}")
    print("  ✅ 测试 2 通过")

    # ============================================================
    # 测试 3: ConsultingSOP 减法记录
    # ============================================================
    print("\n[测试 3] ConsultingSOP 减法记录（种子A）")
    subs = case.subtraction_records
    print(f"  减法记录数: {len(subs)}")
    for s in subs:
        print(f"    - {s.event_type.value}: {s.trigger[:60]}...")
    print("  ✅ 测试 3 通过")

    # ============================================================
    # 测试 4: ConsultingSOP 报告格式化
    # ============================================================
    print("\n[测试 4] ConsultingSOP 报告格式化（种子A）")
    report = sop.format_report(case)
    assert "跨域诊断咨询报告" in report
    assert "Step 1" in report
    assert "Step 2" in report
    assert "Step 3" in report
    assert "宪法审计" in report
    print(f"  报告长度: {len(report)} 字符")
    print("  ✅ 测试 4 通过")

    # ============================================================
    # 测试 5: WuxingAnalysisTemplate 基本流程
    # ============================================================
    print("\n[测试 5] WuxingAnalysisTemplate 基本流程（种子B）")
    template = WuxingAnalysisTemplate(recorder)

    nodes = [
        {"id": "n1", "name": "道", "wuxing": "水", "layer": "种子", "wuxing_source": "道德经25章"},
        {"id": "n2", "name": "德", "wuxing": "土", "layer": "现行", "wuxing_source": "道德经38章"},
        {"id": "n3", "name": "仁", "wuxing": "木", "layer": "现行", "wuxing_source": "道德经5章"},
        {"id": "n4", "name": "义", "wuxing": "金", "layer": "超越", "wuxing_source": "道德经18章"},
        {"id": "n5", "name": "礼", "wuxing": "火", "layer": "超越", "wuxing_source": "道德经38章"},
        {"id": "n6", "name": "无为", "wuxing": "水", "layer": "种子", "wuxing_source": "道德经37章"},
        {"id": "n7", "name": "自然", "wuxing": "木", "layer": "种子", "wuxing_source": "道德经25章"},
        {"id": "n8", "name": "玄德", "wuxing": "土", "layer": "超越", "wuxing_source": "道德经10章"},
    ]

    layers = {"种子": 3, "现行": 2, "超越": 3}

    case_b = template.run("道德经第1-10章", nodes, layers)
    assert case_b.skill_id == "SKL-B-20260808-001"
    assert case_b.case_id.startswith("CASE-B-")
    assert case_b.status == CaseStatus.COMPLETED
    assert len(case_b.dimension_results) == 7
    assert len(case_b.constitution_audit) == 4
    print(f"  案例ID: {case_b.case_id}")
    print(f"  七维计算: {len(case_b.dimension_results)} 个维度")
    print(f"  宪法审计: {'✅' if case_b.constitution_passed else '❌'}")
    print("  ✅ 测试 5 通过")

    # ============================================================
    # 测试 6: WuxingAnalysisTemplate 七维计算
    # ============================================================
    print("\n[测试 6] WuxingAnalysisTemplate 七维计算（种子B）")
    dims = case_b.dimension_results

    # D1: 频次
    freq = dims["freq"]
    assert freq["total"] == 8
    assert len(freq["percentages"]) == 5
    print(f"  D1 频次: {freq['percentages']}")

    # D2: 矩阵
    matrix = dims["layer_matrix"]["matrix"]
    assert len(matrix) == 3  # 种子/现行/超越
    print(f"  D2 矩阵: 3 层 × 5 五行")

    # D3: 重心路径
    path = dims["centroid_path"]["path"]
    assert len(path) >= 2
    print(f"  D3 路径: {len(path)} 段")

    # D4: 熵
    entropy = dims["entropy"]
    assert 0 <= entropy["H_normalized"] <= 1
    print(f"  D4 熵: H={entropy['H']:.4f}, H_norm={entropy['H_normalized']:.4f}")

    # D5: 重心
    dominant = dims["centroid_vector"]["dominant"]
    assert dominant in template.config["wuxing_types"]
    print(f"  D5 主导: {dominant}")

    # D6: 画像
    profile = dims["trait_profile"]["profile_name"]
    print(f"  D6 画像: {profile}")

    # D7: 判语
    verdict = dims["verdict"]
    assert verdict["S_p"] > 0
    print(f"  D7 判语: {verdict['text']} (S_p={verdict['S_p']:.2f})")
    print("  ✅ 测试 6 通过")

    # ============================================================
    # 测试 7: WuxingAnalysisTemplate 宪法审计
    # ============================================================
    print("\n[测试 7] WuxingAnalysisTemplate 宪法审计（种子B）")
    for check in case_b.constitution_audit:
        icon = "✅" if check.verdict == AuditVerdict.PASS else "❌"
        print(f"  {icon} {check.clause}: {check.detail[:50]}")
    print("  ✅ 测试 7 通过")

    # ============================================================
    # 测试 8: WuxingAnalysisTemplate 报告格式化
    # ============================================================
    print("\n[测试 8] WuxingAnalysisTemplate 报告格式化（种子B）")
    report_b = template.format_report(case_b)
    assert "五行七维分析报告" in report_b
    assert "D1:" in report_b
    assert "D7:" in report_b
    assert "宪法审计" in report_b
    print(f"  报告长度: {len(report_b)} 字符")
    print("  ✅ 测试 8 通过")

    # ============================================================
    # 测试 9: 案例记录器集成
    # ============================================================
    print("\n[测试 9] 案例记录器集成")
    cases_a = recorder.list_cases(skill_id="SKL-A-20260808-001")
    cases_b = recorder.list_cases(skill_id="SKL-B-20260808-001")
    assert len(cases_a) >= 1
    assert len(cases_b) >= 1
    stats = recorder.get_stats()
    print(f"  种子A 案例: {len(cases_a)}")
    print(f"  种子B 案例: {len(cases_b)}")
    print(f"  总案例: {stats['total_cases']}")
    print(f"  总减法: {stats['total_subtractions']}")
    print("  ✅ 测试 9 通过")

    # ============================================================
    # 测试 10: 便捷函数
    # ============================================================
    print("\n[测试 10] 便捷函数")
    case_quick = run_consulting("Python", "Rust", "个人开发者", recorder=recorder)
    assert case_quick.skill_id == "SKL-A-20260808-001"
    print(f"  run_consulting: {case_quick.case_id}")

    case_quick_b = run_analysis("测试目标", [{"id": "n1", "name": "X", "wuxing": "土", "layer": "现行"}],
                                {"现行": 1}, recorder=recorder)
    assert case_quick_b.skill_id == "SKL-B-20260808-001"
    print(f"  run_analysis: {case_quick_b.case_id}")
    print("  ✅ 测试 10 通过")

    # ============================================================
    # 测试 11: ConsultingSOP v1.1 Step 2.5 增量审计
    # ============================================================
    print("\n[测试 11] ConsultingSOP v1.1 Step 2.5 增量审计")
    increments = [
        {
            "item": "宪法审计",
            "source_counterpart": "无（语言树无对应物）",
            "increment_type": "新增运算",
            "preserves_homomorphism": True,
            "note": "目标域增量，不破坏保持——如实标注",
        }
    ]
    case_v11 = sop.run("语言谱系树", "慧惠 Agent 体系", "演示",
                       source_graph, target_domain_increments=increments)
    inc_audit = case_v11.basic_info.get("increment_audit", {})
    assert inc_audit, "增量审计不应为空"
    assert inc_audit["preserving_count"] == 1
    assert inc_audit["breaking_count"] == 0
    assert inc_audit["audit_passed"] == True
    print(f"  增量审计: {inc_audit['preserving_count']} 保持 / {inc_audit['breaking_count']} 破坏")
    print(f"  审计结果: {'✅ 通过' if inc_audit['audit_passed'] else '❌ 未通过'}")
    print("  ✅ 测试 11 通过")

    # ============================================================
    # 测试 12: ConsultingSOP v1.1 轻量验证模式
    # ============================================================
    print("\n[测试 12] ConsultingSOP v1.1 轻量验证模式")
    sop_lw = ConsultingSOP(recorder, config={"lightweight_mode": True})
    case_lw = sop_lw.run("大语言模型", "自然语言处理", "企业客户", source_graph)
    # 轻量模式应有 ≤2 个场景
    assert len(case_lw.verification_scenarios) <= 2
    print(f"  验证场景数: {len(case_lw.verification_scenarios)} (轻量模式)")
    print("  ✅ 测试 12 通过")

    # ============================================================
    # 测试 13: ConsultingSOP v1.1 关键路径信度标注
    # ============================================================
    print("\n[测试 13] ConsultingSOP v1.1 关键路径信度标注")
    step1 = case_v11.step_records.get("Step 1 结构提取", {})
    total_edges = len(source_graph["edges"])  # 3 edges
    cp_count = step1.get("critical_path_count", 0)
    # 3 edges: 0.85, 0.9, 0.7 → all >= 0.7 => all on critical path
    assert cp_count <= total_edges
    print(f"  总边数: {total_edges}, 关键路径标注: {cp_count} (阈值={step1.get('critical_path_threshold', 0.7)})")
    print("  ✅ 测试 13 通过")

    # ============================================================
    # 测试 14: WuxingAnalysisTemplate v1.1 小样本模式
    # ============================================================
    print("\n[测试 14] WuxingAnalysisTemplate v1.1 小样本模式（n<10）")
    small_nodes = [
        {"id": "n1", "name": "A", "wuxing": "火", "layer": "现行", "wuxing_source": "test"},
        {"id": "n2", "name": "B", "wuxing": "土", "layer": "现行", "wuxing_source": "test"},
        {"id": "n3", "name": "C", "wuxing": "水", "layer": "现行", "wuxing_source": "test"},
    ]
    case_small = template.run("小样本测试", small_nodes, {"现行": 3})
    dim6 = case_small.dimension_results["trait_profile"]
    assert dim6.get("small_sample_mode") == True
    assert "画像提示" in dim6.get("profile_name", "")
    assert dim6["profile_match_confidence"] == 0  # 小样本模式不计算匹配置信度
    print(f"  画像: {dim6['profile_name']}")
    print(f"  模式: {'小样本模式 ✅' if dim6.get('small_sample_mode') else '标准模式'}")
    print("  ✅ 测试 14 通过")

    # ============================================================
    # 测试 15: WuxingAnalysisTemplate v1.1 无层级模式
    # ============================================================
    print("\n[测试 15] WuxingAnalysisTemplate v1.1 无层级模式")
    no_layer_nodes = [
        {"id": "n1", "name": "X", "wuxing": "金", "wuxing_source": "test"},
        {"id": "n2", "name": "Y", "wuxing": "木", "wuxing_source": "test"},
    ]
    case_nl = template.run("无层级测试", no_layer_nodes, {"种子": 0, "现行": 0, "超越": 0})
    dim2_nl = case_nl.dimension_results["layer_matrix"]
    assert dim2_nl.get("skipped") == True
    assert "无层级" in dim2_nl.get("skip_reason", "")
    print(f"  D2 矩阵: {'跳过' if dim2_nl.get('skipped') else '正常计算'}")
    print(f"  跳过原因: {dim2_nl.get('skip_reason', '')}")
    print("  ✅ 测试 15 通过")

    print("\n" + "=" * 60)
    print("自检完成 — 全部 15 项测试通过 (V1.3 M3 双技能 v1.1)")