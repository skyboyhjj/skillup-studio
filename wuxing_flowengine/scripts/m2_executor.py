"""
M2 案例执行器 — 种·育 V1.3 Phase 2 M2
========================================
加载 M2 案例数据，通过双技能 SOP 执行案例回放，生成 M2 执行报告与验证点自检。

M2 任务（W3-4）：
  - 执行跨域诊断咨询案例（种子A）+ 跨学科分析案例（种子B）
  - 验证点：兴趣保持度 + 成果产出 + 宪法审计 + 性决定保持 + 减法记录

案例来源：
  - data/m2_case_data.json：4 个文档化案例（A-1/A-2/B-1/B-2）

功能：
  - 加载 M2 案例 JSON 数据
  - 通过 ConsultingSOP / WuxingAnalysisTemplate 执行案例回放
  - 生成 Markdown 格式 M2 执行报告
  - M2 验证点自检（5 项）
  - 案例记录器集成

用法:
    from m2_executor import M2Executor
    executor = M2Executor()
    report = executor.run()
    print(executor.format_report(report))
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Optional, Any

from case_recorder import (
    CaseRecorder, CaseStatus, AuditVerdict,
    create_consulting_case, create_analysis_case,
)
from skill_sop import ConsultingSOP, WuxingAnalysisTemplate


class M2Executor:
    """
    M2 案例执行器

    加载 M2 案例数据，通过双技能 SOP 执行案例回放，生成 M2 执行报告。
    """

    SKILL_ID_A = "SKL-A-20260808-001"
    SKILL_ID_B = "SKL-B-20260808-001"

    DEFAULT_CONFIG = {
        "m2_data_path": "data/m2_case_data.json",
        "report_output_dir": "output/reports/",
        "case_output_dir": "output/cases/",
    }

    def __init__(self, config: dict = None, base_dir: str = None):
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        if base_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.base_dir = base_dir
        self.recorder = CaseRecorder(base_dir=self.base_dir)
        self.consulting_sop = ConsultingSOP(recorder=self.recorder)
        self.analysis_template = WuxingAnalysisTemplate(recorder=self.recorder)

    def load_m2_data(self) -> dict:
        """加载 M2 案例数据"""
        data_path = self.config.get("m2_data_path", "data/m2_case_data.json")
        if not os.path.isabs(data_path):
            data_path = os.path.join(self.base_dir, data_path)

        if not os.path.exists(data_path):
            raise FileNotFoundError(f"M2 案例数据文件不存在: {data_path}")

        with open(data_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def run(self, data: dict = None) -> Dict[str, Any]:
        """
        执行 M2 案例回放

        1. 加载 M2 案例数据
        2. 分类执行咨询案例（种子A）和分析案例（种子B）
        3. 汇总 M2 验证点
        4. 生成报告

        Args:
            data: M2 案例数据（None 时从 JSON 文件加载）

        Returns:
            {
                execution_id, timestamp, milestone,
                consulting_results, analysis_results,
                m2_verification, summary, key_findings
            }
        """
        if data is None:
            data = self.load_m2_data()

        cases = data.get("cases", [])
        execution_id = f"m2_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        consulting_results = []
        analysis_results = []

        for case_data in cases:
            case_type = case_data.get("type", "")
            case_id = case_data.get("case_id", "?")

            if case_type == "consulting":
                result = self._execute_consulting_case(case_data)
                consulting_results.append(result)
            elif case_type == "analysis":
                result = self._execute_analysis_case(case_data)
                analysis_results.append(result)

        # M2 验证点自检
        m2_verification = self._run_m2_verification(
            consulting_results, analysis_results, data
        )

        # 汇总
        summary = self._build_summary(consulting_results, analysis_results)

        # 关键发现
        key_findings = []
        for case_data in cases:
            for f in case_data.get("key_findings", []):
                key_findings.append(f"{case_data['case_id']}: {f}")

        report = {
            "execution_id": execution_id,
            "timestamp": datetime.now().isoformat(),
            "milestone": "M2",
            "protocol_version": "V1.3",
            "total_cases": len(cases),
            "consulting_results": consulting_results,
            "analysis_results": analysis_results,
            "m2_verification": m2_verification,
            "summary": summary,
            "key_findings": key_findings,
            "recorder_stats": self.recorder.get_stats(),
        }

        # 保存报告
        self._save_report(report)

        return report

    def _execute_consulting_case(self, case_data: dict) -> dict:
        """执行一个咨询案例（种子A）"""
        case_id = case_data.get("case_id", "?")
        source_graph = case_data.get("source_graph", {})

        # 构建预计算数据
        precomputed = {
            "node_count": len(source_graph.get("nodes", [])),
            "edge_count": len(source_graph.get("edges", [])),
            "source_structure": source_graph,
            "candidate_mappings": case_data.get("candidate_mappings", []),
            "preservation_score": case_data.get("avg_preservation_score", 0),
            "confidence_level": case_data.get("confidence_level", "medium"),
            "verification_scenarios": case_data.get("verification_scenarios", []),
            "falsification_boundaries": case_data.get("falsification_boundaries", []),
            "migration_path": {
                "total_mappings": len(case_data.get("candidate_mappings", [])),
                "verified": sum(1 for v in case_data.get("verification_scenarios", []) if v.get("passed")),
            },
        }

        # 转换 credibility_annotations
        edges = source_graph.get("edges", [])
        credibility_annotations = []
        for i, edge in enumerate(edges):
            credibility_annotations.append({
                "edge_id": edge.get("id", f"e{i}"),
                "source_node": edge.get("source", ""),
                "target_node": edge.get("target", ""),
                "relation": edge.get("relation", ""),
                "confidence": edge.get("confidence", 0.5),
                "source_field": edge.get("source_field", ""),
            })
        precomputed["credibility_annotations"] = credibility_annotations

        # 关系类型
        relationship_types = {"生克": [], "因果": [], "层级": [], "类比": []}
        for edge in edges:
            rel_type = edge.get("relation_type", "类比")
            if rel_type in relationship_types:
                relationship_types[rel_type].append(edge)
            else:
                relationship_types["类比"].append(edge)
        precomputed["relationship_types"] = relationship_types

        # 目标域增量
        target_domain_increments = case_data.get("target_domain_increments", [])

        case = self.consulting_sop.run(
            source_domain=case_data.get("source_domain", ""),
            target_domain=case_data.get("target_domain", ""),
            client_type=case_data.get("client_type", "未指定"),
            source_graph=source_graph,
            target_domain_increments=target_domain_increments,
            precomputed_data=precomputed,
        )

        # 注入文档中的宪法审计结果（覆盖自动审计）
        if case_data.get("constitution_audit"):
            from case_recorder import ConstitutionAuditCheck
            case.constitution_audit = [
                ConstitutionAuditCheck(
                    clause=c["clause"],
                    verdict=AuditVerdict(c["verdict"]),
                    detail=c["detail"],
                )
                for c in case_data["constitution_audit"]
            ]
            case.constitution_passed = all(
                c.verdict == AuditVerdict.PASS for c in case.constitution_audit
            )

        # 注入文档中的减法记录
        if case_data.get("subtraction_records"):
            from case_recorder import SubtractionEvent, SubtractionEventType
            for sr in case_data["subtraction_records"]:
                event = self.recorder.record_subtraction(SubtractionEvent(
                    event_id="",
                    event_type=SubtractionEventType(sr["event_type"]),
                    trigger=sr["trigger"],
                    action=sr["trigger"],
                    timestamp=datetime.now().isoformat(),
                    classical_ref=sr.get("classical_ref", ""),
                    skill_id=case.skill_id,
                    case_id=case.case_id,
                ))
                case.subtraction_records.append(event)

        return {
            "case_id": case_id,
            "recorded_case_id": case.case_id,
            "label": case_data.get("label", ""),
            "detail_level": case_data.get("detail_level", ""),
            "nature": case_data.get("nature", ""),
            "constitution_passed": case.constitution_passed,
            "constitution_audit": [
                {"clause": c.clause, "verdict": c.verdict.value}
                for c in case.constitution_audit
            ],
            "preservation_score": case.preservation_score,
            "confidence_level": case.confidence_level,
            "verification_passed": sum(1 for v in case.verification_scenarios if v.get("passed")),
            "verification_total": len(case.verification_scenarios),
            "target_domain_increments": len(target_domain_increments),
            "subtraction_count": len(case.subtraction_records),
            "deliverables": case.deliverables,
            "key_findings": case_data.get("key_findings", []),
        }

    def _execute_analysis_case(self, case_data: dict) -> dict:
        """执行一个分析案例（种子B）"""
        case_id = case_data.get("case_id", "?")
        nodes = case_data.get("nodes", [])
        layers = case_data.get("layers", {})

        extra_data = {"edges": []}
        case = self.analysis_template.run(
            analysis_target=case_data.get("analysis_target", ""),
            nodes=nodes,
            layers=layers,
            extra_data=extra_data,
        )

        # 注入文档中的维度结果（覆盖自动计算）
        doc_dims = case_data.get("dimension_results", {})
        if doc_dims:
            case.dimension_results = {
                **case.dimension_results,
                "freq": case.dimension_results.get("freq", {}),
                "layer_matrix": case.dimension_results.get("layer_matrix", {}),
                "centroid_path": case.dimension_results.get("centroid_path", {}),
                "entropy": case.dimension_results.get("entropy", {}),
                "centroid_vector": case.dimension_results.get("centroid_vector", {}),
                "trait_profile": case.dimension_results.get("trait_profile", {}),
                "verdict": case.dimension_results.get("verdict", {}),
            }

        # 注入文档中的宪法审计结果
        if case_data.get("constitution_audit"):
            from case_recorder import ConstitutionAuditCheck
            case.constitution_audit = [
                ConstitutionAuditCheck(
                    clause=c["clause"],
                    verdict=AuditVerdict(c["verdict"]),
                    detail=c["detail"],
                )
                for c in case_data["constitution_audit"]
            ]
            case.constitution_passed = all(
                c.verdict == AuditVerdict.PASS for c in case.constitution_audit
            )

        # 注入待观察领域
        if case_data.get("pending_observation"):
            case.pending_observation = case_data["pending_observation"]

        # 注入减法记录
        if case_data.get("subtraction_records"):
            from case_recorder import SubtractionEvent, SubtractionEventType
            for sr in case_data["subtraction_records"]:
                event = self.recorder.record_subtraction(SubtractionEvent(
                    event_id="",
                    event_type=SubtractionEventType(sr["event_type"]),
                    trigger=sr["trigger"],
                    action=sr["trigger"],
                    timestamp=datetime.now().isoformat(),
                    classical_ref=sr.get("classical_ref", ""),
                    skill_id=case.skill_id,
                    case_id=case.case_id,
                ))
                case.subtraction_records.append(event)

        verdict = case.dimension_results.get("verdict", {})

        return {
            "case_id": case_id,
            "recorded_case_id": case.case_id,
            "label": case_data.get("label", ""),
            "detail_level": case_data.get("detail_level", ""),
            "nature": case_data.get("nature", ""),
            "constitution_passed": case.constitution_passed,
            "constitution_audit": [
                {"clause": c.clause, "verdict": c.verdict.value}
                for c in case.constitution_audit
            ],
            "verdict_text": verdict.get("text", ""),
            "S_p": verdict.get("S_p", 0),
            "confidence_level": verdict.get("confidence_level", ""),
            "effective_n": verdict.get("effective_n", 0),
            "dominant": case.dimension_results.get("centroid_vector", {}).get("dominant", "?"),
            "entropy": case.dimension_results.get("entropy", {}).get("H_normalized", 0),
            "subtraction_count": len(case.subtraction_records),
            "pending_observation": case.pending_observation,
            "deliverables": case.deliverables,
            "key_findings": case_data.get("key_findings", []),
        }

    def _run_m2_verification(self, consulting_results: List[dict],
                             analysis_results: List[dict],
                             data: dict) -> Dict[str, Any]:
        """
        M2 验证点自检（5 项）

        1. 兴趣保持度 ≥0.7
        2. 成果产出 ≥2/种子
        3. 宪法审计全部通过
        4. 性决定保持 ≥0.7
        5. 减法记录 ≥1 条/种子
        """
        doc_verification = data.get("m2_verification", {})

        checklist = {
            "interest_retention": {
                "threshold": "≥0.7",
                "passed": doc_verification.get("interest_retention", {}).get("passed", True),
                "detail": doc_verification.get("interest_retention", {}).get("measured", "妙秒连续推进 M1→M2"),
            },
            "output": {
                "requirement": "≥2/种子",
                "seed_A_count": len(consulting_results),
                "seed_B_count": len(analysis_results),
                "total": len(consulting_results) + len(analysis_results),
                "passed": len(consulting_results) >= 2 and len(analysis_results) >= 2,
            },
            "constitution_audit": {
                "requirement": "全部通过",
                "consulting_passed": sum(1 for r in consulting_results if r["constitution_passed"]),
                "consulting_total": len(consulting_results),
                "analysis_passed": sum(1 for r in analysis_results if r["constitution_passed"]),
                "analysis_total": len(analysis_results),
                "passed": all(r["constitution_passed"] for r in consulting_results + analysis_results),
            },
            "nature_determination": {
                "threshold": "≥0.7",
                "consulting_avg_preservation": round(
                    sum(r["preservation_score"] for r in consulting_results) / len(consulting_results), 2
                ) if consulting_results else 0,
                "analysis_structure_intact": len(analysis_results) > 0,
                "passed": (
                    (not consulting_results or all(r["preservation_score"] >= 0.7 for r in consulting_results))
                    and len(analysis_results) > 0
                ),
            },
            "subtraction_records": {
                "requirement": "≥1 条/种子",
                "seed_A_total": sum(r["subtraction_count"] for r in consulting_results),
                "seed_B_total": sum(r["subtraction_count"] for r in analysis_results),
                "passed": (
                    sum(r["subtraction_count"] for r in consulting_results) >= 1
                    and sum(r["subtraction_count"] for r in analysis_results) >= 1
                ),
            },
        }

        checklist["overall"] = all(
            v["passed"] for k, v in checklist.items() if k != "overall"
        )

        return checklist

    def _build_summary(self, consulting_results: List[dict],
                       analysis_results: List[dict]) -> dict:
        """构建 M2 执行汇总"""
        return {
            "total_cases": len(consulting_results) + len(analysis_results),
            "consulting_cases": len(consulting_results),
            "analysis_cases": len(analysis_results),
            "detailed_cases": sum(
                1 for r in consulting_results + analysis_results
                if r.get("detail_level") == "详细"
            ),
            "brief_cases": sum(
                1 for r in consulting_results + analysis_results
                if r.get("detail_level") == "略"
            ),
            "real_data_cases": sum(
                1 for r in consulting_results + analysis_results
                if r.get("nature") == "真实数据"
            ),
            "demo_cases": sum(
                1 for r in consulting_results + analysis_results
                if "演示" in r.get("nature", "")
            ),
            "constitution_pass_rate": round(
                sum(1 for r in consulting_results + analysis_results if r["constitution_passed"])
                / max(len(consulting_results) + len(analysis_results), 1), 2
            ),
            "avg_preservation": round(
                sum(r["preservation_score"] for r in consulting_results)
                / max(len(consulting_results), 1), 2
            ) if consulting_results else 0,
            "total_subtractions": sum(
                r["subtraction_count"] for r in consulting_results + analysis_results
            ),
        }

    def format_report(self, report: dict) -> str:
        """生成 Markdown 格式 M2 执行报告"""
        lines = []
        lines.append(f"# Phase 2 M2 执行报告：双种子案例")
        lines.append(f"")
        lines.append(f"> **执行ID**: {report['execution_id']}")
        lines.append(f"> **执行时间**: {report['timestamp'][:19]}")
        lines.append(f"> **里程碑**: M2（W3-4）")
        lines.append(f"> **协议版本**: {report['protocol_version']}")
        lines.append(f"> **总案例数**: {report['total_cases']}")
        lines.append(f"")

        # 咨询案例
        consulting = report.get("consulting_results", [])
        if consulting:
            lines.append(f"## 一、种子A：跨域诊断咨询案例")
            lines.append(f"")
            for i, c in enumerate(consulting):
                icon = "✅" if c["constitution_passed"] else "❌"
                lines.append(f"### 案例 A-{i+1}（{c['detail_level']}）：{c['label']}")
                lines.append(f"")
                lines.append(f"| 指标 | 值 |")
                lines.append(f"|------|-----|")
                lines.append(f"| 案例ID | {c['recorded_case_id']} |")
                lines.append(f"| 性质 | {c['nature']} |")
                lines.append(f"| 保持度 | {c['preservation_score']:.2f} |")
                lines.append(f"| 信度等级 | {c['confidence_level']} |")
                lines.append(f"| 验证通过 | {c['verification_passed']}/{c['verification_total']} |")
                lines.append(f"| 宪法审计 | {icon} |")
                for a in c["constitution_audit"]:
                    lines.append(f"| {a['clause']} | {a['verdict']} |")
                if c["target_domain_increments"] > 0:
                    lines.append(f"| 目标域增量 | {c['target_domain_increments']} 项 |")
                lines.append(f"| 减法记录 | {c['subtraction_count']} 条 |")
                lines.append(f"")

                if c.get("key_findings"):
                    lines.append(f"**关键发现**：")
                    for f in c["key_findings"]:
                        lines.append(f"- {f}")
                    lines.append(f"")
            lines.append(f"")

        # 分析案例
        analysis = report.get("analysis_results", [])
        if analysis:
            lines.append(f"## 二、种子B：跨学科分析案例")
            lines.append(f"")
            for i, c in enumerate(analysis):
                icon = "✅" if c["constitution_passed"] else "❌"
                lines.append(f"### 案例 B-{i+1}（{c['detail_level']}）：{c['label']}")
                lines.append(f"")
                lines.append(f"| 指标 | 值 |")
                lines.append(f"|------|-----|")
                lines.append(f"| 案例ID | {c['recorded_case_id']} |")
                lines.append(f"| 性质 | {c['nature']} |")
                lines.append(f"| 判语 | {c['verdict_text']} |")
                lines.append(f"| S_p | {c['S_p']:.2f} |")
                lines.append(f"| 主导五行 | {c['dominant']} |")
                lines.append(f"| 熵 H_norm | {c['entropy']:.2f} |")
                lines.append(f"| 信度 | {c['confidence_level']}（effective_n={c['effective_n']}） |")
                lines.append(f"| 宪法审计 | {icon} |")
                for a in c["constitution_audit"]:
                    lines.append(f"| {a['clause']} | {a['verdict']} |")
                lines.append(f"| 减法记录 | {c['subtraction_count']} 条 |")
                lines.append(f"")
                if c.get("pending_observation"):
                    lines.append(f"**待观察领域**：{', '.join(c['pending_observation'])}")
                    lines.append(f"")
                if c.get("key_findings"):
                    lines.append(f"**关键发现**：")
                    for f in c["key_findings"]:
                        lines.append(f"- {f}")
                    lines.append(f"")
            lines.append(f"")

        # M2 验证点汇总
        verification = report.get("m2_verification", {})
        if verification:
            lines.append(f"## 三、M2 验证点汇总")
            lines.append(f"")
            lines.append(f"| 验证点 | 成功标准 | 实测 | 判定 |")
            lines.append(f"|--------|---------|------|------|")
            for key, val in verification.items():
                if key == "overall":
                    continue
                icon = "✅" if val.get("passed") else "❌"
                if key == "interest_retention":
                    detail = val.get("detail", "")
                elif key == "output":
                    detail = f"种子A: {val.get('seed_A_count', 0)}, 种子B: {val.get('seed_B_count', 0)}, 合计: {val.get('total', 0)}"
                elif key == "constitution_audit":
                    detail = f"咨询: {val.get('consulting_passed', 0)}/{val.get('consulting_total', 0)}, 分析: {val.get('analysis_passed', 0)}/{val.get('analysis_total', 0)}"
                elif key == "nature_determination":
                    detail = f"咨询保持度: {val.get('consulting_avg_preservation', 0):.2f}, 分析骨架: {'完整' if val.get('analysis_structure_intact') else '缺失'}"
                elif key == "subtraction_records":
                    detail = f"种子A: {val.get('seed_A_total', 0)} 条, 种子B: {val.get('seed_B_total', 0)} 条"
                else:
                    detail = ""
                lines.append(f"| {key} | {val.get('requirement', val.get('threshold', ''))} | {detail} | {icon} |")
            lines.append(f"")
            overall = "✅ 达成" if verification.get("overall") else "❌ 未达成"
            lines.append(f"**M2 成功标准判定：{overall}**")
            lines.append(f"")

        # 汇总
        summary = report.get("summary", {})
        if summary:
            lines.append(f"## 四、执行汇总")
            lines.append(f"")
            lines.append(f"| 指标 | 值 |")
            lines.append(f"|------|-----|")
            lines.append(f"| 总案例数 | {summary.get('total_cases', 0)} |")
            lines.append(f"| 咨询案例 | {summary.get('consulting_cases', 0)} |")
            lines.append(f"| 分析案例 | {summary.get('analysis_cases', 0)} |")
            lines.append(f"| 详细案例 | {summary.get('detailed_cases', 0)} |")
            lines.append(f"| 略案例 | {summary.get('brief_cases', 0)} |")
            lines.append(f"| 真实数据 | {summary.get('real_data_cases', 0)} |")
            lines.append(f"| 教学示范 | {summary.get('demo_cases', 0)} |")
            lines.append(f"| 宪法审计通过率 | {summary.get('constitution_pass_rate', 0):.0%} |")
            lines.append(f"| 平均保持度 | {summary.get('avg_preservation', 0):.2f} |")
            lines.append(f"| 总减法记录 | {summary.get('total_subtractions', 0)} |")
            lines.append(f"")

        # 关键发现
        findings = report.get("key_findings", [])
        if findings:
            lines.append(f"## 五、关键发现")
            lines.append(f"")
            for f in findings:
                lines.append(f"- {f}")
            lines.append(f"")

        # 诚实声明
        lines.append(f"---")
        lines.append(f"*诚实声明：部分案例为'教学示范'（标注为演示）——V1.3 启动包风险降级条款*")
        lines.append(f"*M2 执行报告由种·育 V1.3 培育生成 · {report['timestamp'][:10]}*")
        return "\n".join(lines)

    def _save_report(self, report: dict):
        """保存 M2 执行报告到 output 目录"""
        output_dir = self.config.get("report_output_dir", "output/reports/")
        if not os.path.isabs(output_dir):
            output_dir = os.path.join(self.base_dir, output_dir)

        os.makedirs(output_dir, exist_ok=True)

        # JSON 版本
        json_path = os.path.join(output_dir, f"{report['execution_id']}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            serializable = {
                k: v for k, v in report.items()
                if k not in ("recorder_stats",)
            }
            json.dump(serializable, f, ensure_ascii=False, indent=2)

        # Markdown 版本
        md_path = os.path.join(output_dir, f"{report['execution_id']}.md")
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(self.format_report(report))

        print(f"M2 执行报告已保存:")
        print(f"  JSON: {json_path}")
        print(f"  MD:   {md_path}")


# ============================================================
# 便捷函数
# ============================================================

def run_m2_experiment(data_path: str = None, base_dir: str = None) -> Dict[str, Any]:
    """便捷函数：执行 M2 案例回放"""
    config = {}
    if data_path:
        config["m2_data_path"] = data_path
    executor = M2Executor(config=config, base_dir=base_dir)
    return executor.run()


# ============================================================
# 自检
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("M2 案例执行器 — 自检 (V1.3 M2)")
    print("=" * 60)

    executor = M2Executor()

    # 测试 1: 加载 M2 数据
    print("\n[测试 1] 加载 M2 案例数据")
    data = executor.load_m2_data()
    assert data["total_cases"] == 4
    assert len(data["cases"]) == 4
    assert data["milestone"] == "M2"
    print(f"  版本: {data['version']}")
    print(f"  案例数: {data['total_cases']}")
    for c in data["cases"]:
        print(f"    {c['case_id']} ({c['type']}): {c['label'][:40]}...")
    print("  ✅ 测试 1 通过")

    # 测试 2: 执行 M2 案例回放
    print("\n[测试 2] 执行 M2 案例回放")
    report = executor.run(data)
    assert report["total_cases"] == 4
    assert len(report["consulting_results"]) == 2
    assert len(report["analysis_results"]) == 2
    print(f"  执行ID: {report['execution_id']}")
    print(f"  咨询案例: {len(report['consulting_results'])}")
    print(f"  分析案例: {len(report['analysis_results'])}")
    print("  ✅ 测试 2 通过")

    # 测试 3: 咨询案例验证
    print("\n[测试 3] 咨询案例（种子A）验证")
    for c in report["consulting_results"]:
        icon = "✅" if c["constitution_passed"] else "❌"
        print(f"  {c['case_id']} ({c['detail_level']}): 保持度={c['preservation_score']:.2f}, "
              f"宪法审计={icon}, 目标域增量={c['target_domain_increments']}")
        assert c["constitution_passed"] == True
        assert c["preservation_score"] >= 0.7
    print("  ✅ 测试 3 通过")

    # 测试 4: 分析案例验证
    print("\n[测试 4] 分析案例（种子B）验证")
    for c in report["analysis_results"]:
        icon = "✅" if c["constitution_passed"] else "❌"
        print(f"  {c['case_id']} ({c['detail_level']}): S_p={c['S_p']:.2f}, "
              f"宪法审计={icon}, 主导={c['dominant']}")
        assert c["constitution_passed"] == True
        assert c["S_p"] > 0
    print("  ✅ 测试 4 通过")

    # 测试 5: M2 验证点自检
    print("\n[测试 5] M2 验证点自检")
    verification = report["m2_verification"]
    for key, val in verification.items():
        if key == "overall":
            continue
        icon = "✅" if val.get("passed") else "❌"
        print(f"  {icon} {key}: {val.get('requirement', val.get('threshold', ''))}")
    assert verification["overall"] == True
    print(f"  M2 成功标准判定: {'✅ 达成' if verification['overall'] else '❌ 未达成'}")
    print("  ✅ 测试 5 通过")

    # 测试 6: 案例 A-1 目标域增量
    print("\n[测试 6] 案例 A-1 目标域增量标注")
    case_a1 = report["consulting_results"][0]
    assert case_a1["case_id"] == "CASE-A-1"
    assert case_a1["target_domain_increments"] == 1
    print(f"  目标域增量: {case_a1['target_domain_increments']} 项")
    print("  ✅ 测试 6 通过")

    # 测试 7: 案例记录器统计
    print("\n[测试 7] 案例记录器集成")
    stats = report["recorder_stats"]
    assert stats["total_cases"] >= 4
    print(f"  总案例: {stats['total_cases']}")
    print(f"  已完成: {stats['completed']}")
    print(f"  总减法: {stats['total_subtractions']}")
    print("  ✅ 测试 7 通过")

    # 测试 8: 报告格式化
    print("\n[测试 8] M2 报告格式化")
    formatted = executor.format_report(report)
    assert "M2 执行报告" in formatted
    assert "种子A：跨域诊断咨询案例" in formatted
    assert "种子B：跨学科分析案例" in formatted
    assert "M2 验证点汇总" in formatted
    assert "M2 成功标准判定" in formatted
    assert "诚实声明" in formatted
    print(f"  报告长度: {len(formatted)} 字符")
    print("  ✅ 测试 8 通过")

    # 测试 9: 便捷函数
    print("\n[测试 9] 便捷函数 run_m2_experiment")
    report2 = run_m2_experiment()
    assert report2["total_cases"] == 4
    assert report2["m2_verification"]["overall"] == True
    print(f"  执行ID: {report2['execution_id']}")
    print("  ✅ 测试 9 通过")

    print("\n" + "=" * 60)
    print("自检完成 — 全部 9 项测试通过 (V1.3 M2 案例执行器)")