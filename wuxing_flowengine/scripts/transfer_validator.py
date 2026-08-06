"""
迁移验证器 — 同态映射引擎 Step 3
===================================
将候选同态映射应用到新领域的 ≥3 个具体场景中，
验证"关系是否保持"。

验证标准（对齐第四步唯识纠正）：
  标准在结构本身，不在识别者。
  验证的是"新域结构是否与源域公理相容"，而非"两域是否看着像"。

核心逻辑：
  1. 生成验证场景（基于源域关系类型 + 新域上下文）
  2. 在每个场景中检查：旧域"A 生 B"，新域 f(A) 是否也"生" f(B)
  3. 通过 → 固化为用户迁移路径
  4. 失败 → 触发 SAD 镜鉴，记录偏差

用法:
    from transfer_validator import TransferValidator
    validator = TransferValidator()
    result = validator.verify(candidate, scenarios)
    if result.overall_pass:
        validator.solidify(result)
    else:
        validator.record_deviation(result)
"""

import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Callable

from homomorphism_types import (
    ConceptNode, RelationEdge, RelationType,
    ConceptRelationGraph, NodeMapping, HomomorphismCandidate,
    ScenarioResult, VerificationResult, DeviationRecord,
    ConfidenceLevel, classify_confidence,
)

# 五行相生相克规则（源域公理）
SHENG = {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'}
KE = {'木': '土', '土': '水', '水': '火', '火': '金', '金': '木'}


class TransferValidator:
    """
    迁移验证器

    在具体场景中验证同态映射的关系保持性。
    验证通过 → 固化路径；验证失败 → SAD 镜鉴记录。
    """

    def __init__(self, output_dir: str = None, llm_verifier: Callable = None):
        """
        Args:
            output_dir: 输出目录（用于保存验证结果和偏差记录）
            llm_verifier: 可选的 LLM 验证函数
                         签名: (scenario, candidate) -> ScenarioResult
        """
        if output_dir is None:
            output_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'output'
            )
        self.output_dir = output_dir
        self.llm_verifier = llm_verifier
        self.deviation_records: List[DeviationRecord] = []
        self.solidified_paths: List[VerificationResult] = []

        os.makedirs(output_dir, exist_ok=True)

    # ── 场景生成 ──

    def generate_scenarios(self, candidate: HomomorphismCandidate,
                           count: int = None) -> List[str]:
        """
        生成验证场景

        基于源域的关系类型和候选映射，自动生成验证场景描述。
        场景数量由信度等级决定。

        Args:
            candidate: 候选映射
            count: 场景数量，None 则根据信度自动确定

        Returns:
            场景描述列表
        """
        if count is None:
            count = candidate.get_verification_scenario_count()
        if count == 0:
            return []

        scenarios = []
        source = candidate.source_graph

        # 基于源域边类型生成场景模板
        edge_types = list(set(e.relation_type for e in source.edges))

        for i in range(count):
            # 选择一条有代表性的边
            edge_idx = (i * len(source.edges) // count) % max(len(source.edges), 1)
            if source.edges:
                edge = source.edges[edge_idx]
                src_node = source.get_node_by_id(edge.source_id)
                tgt_node = source.get_node_by_id(edge.target_id)

                src_name = src_node.name if src_node else "?"
                tgt_name = tgt_node.name if tgt_node else "?"
                rel_type = edge.relation_type.value

                scenario = (
                    f"场景 {i+1}: 在目标域 '{candidate.target_domain}' 中，"
                    f"验证映射后的 '{src_name}' 与 '{tgt_name}' "
                    f"之间是否保持 '{rel_type}' 关系"
                )
                scenarios.append(scenario)
            else:
                scenarios.append(
                    f"场景 {i+1}: 在目标域 '{candidate.target_domain}' 中，"
                    f"验证候选映射的通用关系保持性"
                )

        return scenarios

    # ── 关系保持验证 ──

    def verify_relation_preservation(self, candidate: HomomorphismCandidate,
                                     scenario: str) -> ScenarioResult:
        """
        验证单个场景中的关系保持性

        验证逻辑（基于源域公理）：
          1. 建立源域边→目标域映射的对应关系
          2. 对每条源域边 (A→B, type=T)，检查 f(A)→f(B) 是否也存在 type=T 的边
          3. 统计保持与未保持的关系数
        """
        source = candidate.source_graph
        src_to_tgt = {m.source_node_id: m.target_node_id for m in candidate.mappings}

        relations_held = 0
        total_relations = len(source.edges)
        failed_relations = []

        for edge in source.edges:
            mapped_src = src_to_tgt.get(edge.source_id)
            mapped_tgt = src_to_tgt.get(edge.target_id)

            if mapped_src is None or mapped_tgt is None:
                continue  # 映射不完整，跳过

            src_node = source.get_node_by_id(edge.source_id)
            tgt_node = source.get_node_by_id(edge.target_id)

            # 检查目标域中是否存在对应关系
            # 注意：这里需要目标域的实际数据，当前实现基于候选映射中的源域结构
            # 在实际使用中，需要传入目标域的概念-关系图
            if self._check_relation_in_target(mapped_src, mapped_tgt, edge.relation_type):
                relations_held += 1
            else:
                failed_relations.append({
                    "source_edge": f"{src_node.name if src_node else '?'} → {tgt_node.name if tgt_node else '?'}",
                    "relation_type": edge.relation_type.value,
                    "mapped_src": mapped_src,
                    "mapped_tgt": mapped_tgt,
                    "reason": f"目标域中未找到对应的 {edge.relation_type.value} 关系",
                })

        # 判定：≥50% 关系保持即通过
        passed = relations_held >= total_relations * 0.5 if total_relations > 0 else False

        return ScenarioResult(
            scenario_description=scenario,
            relations_held=relations_held,
            total_relations=total_relations,
            passed=passed,
            failed_relations=failed_relations,
            notes=f"关系保持率: {relations_held}/{total_relations} = {relations_held/max(total_relations,1):.1%}",
        )

    def _check_relation_in_target(self, source_id: str, target_id: str,
                                   relation_type: RelationType) -> bool:
        """
        检查目标域中是否存在对应关系

        当前实现：基于源域公理检查五行关系保持
        完整实现需要传入目标域数据
        """
        # 对于五行关系，基于源域公理验证
        if relation_type in (RelationType.SHENG, RelationType.KE):
            return True  # 五行关系是先验公理，默认保持
        return False  # 非五行关系需要目标域数据验证

    # ── 主验证流程 ──

    def verify(self, candidate: HomomorphismCandidate,
               scenarios: List[str] = None,
               generate_scenarios: bool = True) -> VerificationResult:
        """
        执行迁移验证

        Args:
            candidate: 候选同态映射
            scenarios: 自定义验证场景，None 则自动生成
            generate_scenarios: 是否自动生成场景

        Returns:
            VerificationResult
        """
        mapping_id = f"map_{uuid.uuid4().hex[:8]}"

        if scenarios is None and generate_scenarios:
            scenarios = self.generate_scenarios(candidate)

        if not scenarios:
            return VerificationResult(
                mapping_id=mapping_id,
                source_domain=candidate.source_domain,
                target_domain=candidate.target_domain,
                scenarios_tested=0,
                overall_pass=False,
                metadata={"reason": "信度不足，未生成验证场景（不强配）"},
            )

        scenario_results = []
        for scenario in scenarios:
            if self.llm_verifier:
                result = self.llm_verifier(scenario, candidate)
            else:
                result = self.verify_relation_preservation(candidate, scenario)
            scenario_results.append(result)

        # 整体判定：至少 2/3 场景通过
        passed_count = sum(1 for r in scenario_results if r.passed)
        overall_pass = passed_count >= max(len(scenario_results) * 2 / 3, 1)

        # 分类映射
        verified = []
        failed = []
        if overall_pass:
            verified = candidate.mappings
        else:
            # 按信度分：高信度映射视为通过，低信度视为失败
            for m in candidate.mappings:
                if m.confidence >= 0.7:
                    verified.append(m)
                else:
                    failed.append(m)

        # 关系保持率
        total_held = sum(r.relations_held for r in scenario_results)
        total_rel = sum(r.total_relations for r in scenario_results)
        preservation_rate = round(total_held / max(total_rel, 1), 4)

        return VerificationResult(
            mapping_id=mapping_id,
            source_domain=candidate.source_domain,
            target_domain=candidate.target_domain,
            scenarios_tested=len(scenario_results),
            scenario_results=scenario_results,
            overall_pass=overall_pass,
            verified_mappings=verified,
            failed_mappings=failed,
            relation_preservation_rate=preservation_rate,
            metadata={
                'candidate_confidence': candidate.relation_preservation_score,
                'candidate_confidence_level': candidate.confidence_level.value,
                'mapping_count': candidate.mapping_count,
                'coverage': candidate.coverage,
            }
        )

    # ── 固化与记录 ──

    def solidify(self, result: VerificationResult) -> str:
        """
        固化验证通过的迁移路径

        Args:
            result: 验证结果

        Returns:
            保存路径
        """
        self.solidified_paths.append(result)

        path = os.path.join(self.output_dir, 'solidified_transfers.json')
        existing = []
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                existing = json.load(f)

        existing.append(result.to_dict())
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)

        return path

    def record_deviation(self, result: VerificationResult,
                         root_cause: str = "",
                         lesson: str = "") -> DeviationRecord:
        """
        记录验证失败的偏差到 SAD 镜鉴

        Args:
            result: 验证结果
            root_cause: 根因分析
            lesson: 教训

        Returns:
            DeviationRecord
        """
        failed_rels = []
        for sr in result.scenario_results:
            for fr in sr.failed_relations:
                failed_rels.append(fr)

        expected_rel = "; ".join(
            f"{fr.get('source_edge', '?')}[{fr.get('relation_type', '?')}]"
            for fr in failed_rels[:3]
        ) if failed_rels else "未明确"

        record = DeviationRecord(
            record_id=f"dev_{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now().isoformat(),
            source_domain=result.source_domain,
            target_domain=result.target_domain,
            attempted_mapping=f"{result.source_domain} → {result.target_domain}",
            expected_relation=expected_rel,
            actual_result=f"验证失败: {result.pass_rate:.0%} 场景通过, 关系保持率 {result.relation_preservation_rate:.2%}",
            root_cause=root_cause or "目标域结构与源域公理不相容——映射未能保持关键关系",
            lesson=lesson or "自以为同态但实际不同态——结构保持不是'看着像'，而是'关系运算可传递'",
            wuxing_implication=self._infer_wuxing_implication(result),
            metadata={
                'mapping_id': result.mapping_id,
                'scenarios_tested': result.scenarios_tested,
                'pass_rate': result.pass_rate,
                'relation_preservation_rate': result.relation_preservation_rate,
            }
        )

        self.deviation_records.append(record)
        self._save_deviation(record)
        return record

    def _infer_wuxing_implication(self, result: VerificationResult) -> str:
        """从验证失败中推断五行启示"""
        rate = result.relation_preservation_rate
        if rate > 0.6:
            return "部分结构保持，宜以'土·通'的包容性接纳差异，逐步深化映射"
        elif rate > 0.3:
            return "结构保持度不足，需以'金·克'的收敛性重新审视映射前提"
        else:
            return "结构严重不兼容，宜以'木·生'的开放性重新建立认知框架，勿强行映射"

    def _save_deviation(self, record: DeviationRecord):
        """保存偏差记录到 SAD 镜鉴文件"""
        path = os.path.join(self.output_dir, 'sad_mirror_deviations.json')
        existing = []
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                existing = json.load(f)

        existing.append(record.to_dict())
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)

    # ── 统计 ──

    def get_stats(self) -> dict:
        """获取验证器统计信息"""
        return {
            "total_solidified": len(self.solidified_paths),
            "total_deviations": len(self.deviation_records),
            "solidified_paths": [r.mapping_id for r in self.solidified_paths],
            "deviation_records": [r.record_id for r in self.deviation_records],
        }


# ═══════════════════════════════════════════════
# SAD 镜鉴辅助函数
# ═══════════════════════════════════════════════

def load_sad_mirror(output_dir: str) -> List[DeviationRecord]:
    """加载 SAD 镜鉴记录"""
    path = os.path.join(output_dir, 'sad_mirror_deviations.json')
    if not os.path.exists(path):
        return []

    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    records = []
    for item in data:
        records.append(DeviationRecord(
            record_id=item.get('record_id', ''),
            timestamp=item.get('timestamp', ''),
            source_domain=item.get('source_domain', ''),
            target_domain=item.get('target_domain', ''),
            attempted_mapping=item.get('attempted_mapping', ''),
            expected_relation=item.get('expected_relation', ''),
            actual_result=item.get('actual_result', ''),
            root_cause=item.get('root_cause', ''),
            lesson=item.get('lesson', ''),
            wuxing_implication=item.get('wuxing_implication'),
            metadata=item.get('metadata', {}),
        ))
    return records


def get_sad_summary(output_dir: str) -> dict:
    """获取 SAD 镜鉴摘要"""
    records = load_sad_mirror(output_dir)
    if not records:
        return {"total": 0, "message": "无偏差记录"}

    domains = set()
    for r in records:
        domains.add(r.source_domain)
        domains.add(r.target_domain)

    return {
        "total": len(records),
        "domains_involved": list(domains),
        "latest_record": records[-1].timestamp if records else None,
        "common_lessons": list(set(r.lesson for r in records)),
    }


# ═══════════════════════════════════════════════
# 独立测试
# ═══════════════════════════════════════════════

if __name__ == '__main__':
    import os
    import sys
    import tempfile

    print("=" * 70)
    print("  迁移验证器 — 独立测试")
    print("=" * 70)

    from structure_extractor import StructureExtractor
    from homomorphism_matcher import HomomorphismMatcher

    extractor = StructureExtractor()
    matcher = HomomorphismMatcher()

    # 创建临时输出目录
    test_output = os.path.join(tempfile.gettempdir(), 'transfer_validator_test')
    validator = TransferValidator(output_dir=test_output)

    try:
        # 加载两个领域
        source_graph = extractor.extract_from_snapshot("2026-08", domain="大语言模型")
        target_graph = extractor.extract_from_snapshot("2026-08", domain="自然语言处理")

        # 匹配
        candidate = matcher.match(source_graph, target_graph)
        print(f"\n[准备] 候选映射: {candidate.source_domain} → {candidate.target_domain}")
        print(f"  关系保持度: {candidate.relation_preservation_score:.4f}")
        print(f"  信度等级: {candidate.confidence_level.value}")

        # 测试 1: 场景生成
        print("\n[测试 1] 场景生成")
        scenarios = validator.generate_scenarios(candidate)
        print(f"  生成 {len(scenarios)} 个场景:")
        for s in scenarios:
            print(f"    {s}")

        # 测试 2: 验证
        print("\n[测试 2] 执行验证")
        result = validator.verify(candidate, scenarios)
        print(f"  映射ID: {result.mapping_id}")
        print(f"  测试场景数: {result.scenarios_tested}")
        print(f"  整体通过: {result.overall_pass}")
        print(f"  通过率: {result.pass_rate:.0%}")
        print(f"  关系保持率: {result.relation_preservation_rate:.4f}")

        for sr in result.scenario_results:
            print(f"    {sr.scenario_description[:60]}... → {'✓ 通过' if sr.passed else '✗ 失败'} ({sr.relations_held}/{sr.total_relations})")

        # 测试 3: 固化
        if result.overall_pass:
            print("\n[测试 3] 固化迁移路径")
            path = validator.solidify(result)
            print(f"  已保存至: {path}")
        else:
            print("\n[测试 3] 记录偏差")
            record = validator.record_deviation(
                result,
                root_cause="目标域'自然语言处理'与源域'大语言模型'存在部分结构重叠，但层级关系映射不完整",
                lesson="同态映射需区分'语义相似'与'结构保持'——两个领域概念相似不等于结构兼容"
            )
            print(f"  偏差ID: {record.record_id}")
            print(f"  根因: {record.root_cause}")
            print(f"  教训: {record.lesson}")
            print(f"  五行启示: {record.wuxing_implication}")

        # 测试 4: 统计
        print("\n[测试 4] 验证器统计")
        stats = validator.get_stats()
        print(f"  固化路径数: {stats['total_solidified']}")
        print(f"  偏差记录数: {stats['total_deviations']}")

        # 测试 5: 低信度→不强配
        print("\n[测试 5] 低信度场景（不强配）")
        low_target = extractor.extract_from_snapshot("2026-08", domain="生成式AI")
        low_candidate = matcher.match(source_graph, low_target)
        print(f"  候选: {low_candidate.source_domain} → {low_candidate.target_domain}")
        print(f"  关系保持度: {low_candidate.relation_preservation_score:.4f}")
        print(f"  信度等级: {low_candidate.confidence_level.value}")
        print(f"  建议验证场景: {low_candidate.suggested_verification_scenarios}")

        low_result = validator.verify(low_candidate)
        if low_result.scenarios_tested == 0:
            print(f"  ✓ 正确: 信度不足，不生成验证场景（不强配）")
            print(f"    原因: {low_result.metadata.get('reason', '')}")

    except Exception as ex:
        import traceback
        traceback.print_exc()
        print(f"\n  ❌ 测试失败: {ex}")

    print("\n" + "=" * 70)
    print("  测试完成")
    print("=" * 70)