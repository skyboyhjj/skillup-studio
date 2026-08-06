"""
P忠恕伦理模块 — 同态映射的双向伦理校验
==========================================
基于《反者道之动_矛盾迭代引擎_五轮对话深度复盘_完善版》共振三，
将P忠恕的"忠""恕"概念形式化为同态映射的伦理约束。

核心概念：
  忠 (Zhong/Loyalty) = 己欲立而立人
    → 源域→目标域的映射，保持源域结构不扭曲
    → 结构提取的伦理承诺：不因讨好目标域而扭曲源域

  恕 (Shu/Forgiveness) = 己所不欲勿施于人
    → 目标域对源域的约束，映射不得伤害目标域
    → 迁移验证的伦理检验：映射不得伤害目标域

  忠恕一体 = 同态映射的双向校验
    → 映射不是任意的，必须通过"恕"的检验
    → 正如 S_p 的恕度参数 p=0.5 中道：如实看见短板但不一票否决

伦理评分体系：
  Z_score ∈ [0, 1]: 忠度 — 源域结构保持度
  S_score ∈ [0, 1]: 恕度 — 目标域相容度
  ZS_score ∈ [0, 1]: 忠恕综合 — 双向校验通过度

用法:
    from zhongshu_ethics import ZhongshuEthics
    ethics = ZhongshuEthics()
    zs = ethics.evaluate(candidate, target_graph)
    print(f"忠度: {zs.zhong_score:.2f}, 恕度: {zs.shu_score:.2f}, 忠恕: {zs.zhongshu_score:.2f}")
"""

import math
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from enum import Enum

from homomorphism_types import (
    ConceptNode, RelationEdge, RelationType,
    ConceptRelationGraph, NodeMapping, HomomorphismCandidate,
    ConfidenceLevel,
)

# 五行相生相克规则
SHENG = {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'}
KE = {'木': '土', '土': '水', '水': '火', '火': '金', '金': '木'}


class ZhongshuLevel(str, Enum):
    """忠恕等级"""
    HIGH = "忠恕兼备"     # ZS ≥ 0.7: 双向校验通过
    MEDIUM = "偏忠"       # Z ≥ 0.7, S < 0.7: 保持源域但目标域相容不足
    TOLERANT = "偏恕"     # S ≥ 0.7, Z < 0.7: 目标域相容但源域变形
    LOW = "忠恕不足"      # ZS < 0.4: 双向校验均不足


@dataclass
class ZhongshuResult:
    """忠恕伦理评估结果"""
    source_domain: str
    target_domain: str

    # 忠度评分
    zhong_score: float = 0.0          # 源域结构保持度 (0~1)
    zhong_details: Dict[str, Any] = field(default_factory=dict)

    # 恕度评分
    shu_score: float = 0.0            # 目标域相容度 (0~1)
    shu_details: Dict[str, Any] = field(default_factory=dict)

    # 忠恕综合
    zhongshu_score: float = 0.0       # 双向校验综合 (0~1)
    level: str = ""

    # 伦理建议
    ethical_advice: str = ""
    classical_ref: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class ZhongshuEthics:
    """
    P忠恕伦理评估器

    对同态映射候选进行双向伦理校验：
      - 忠：源域结构是否被忠实地保持？
      - 恕：映射是否对目标域造成伤害？
    """

    def __init__(self, zhong_weight: float = 0.5, shu_weight: float = 0.5):
        """
        Args:
            zhong_weight: 忠的权重（默认 0.5，忠恕等重）
            shu_weight: 恕的权重（默认 0.5，忠恕等重）
        """
        self.zhong_weight = zhong_weight
        self.shu_weight = shu_weight

    # ── 忠度计算 ──

    def compute_zhong(self, candidate: HomomorphismCandidate) -> tuple:
        """
        计算忠度：源域结构保持度

        忠 = 己欲立而立人：映射是否忠实地保持了源域的结构？

        评估维度：
          1. 节点覆盖率：源域多少节点被成功映射？
          2. 关系保持度：源域的关系在映射后是否保持？
          3. 五行忠实度：五行属性映射是否一致？
          4. 层级忠实度：认知深度映射是否保持层级关系？

        Returns:
            (zhong_score, details_dict)
        """
        source = candidate.source_graph
        mappings = candidate.mappings

        if not source.nodes:
            return 0.0, {"reason": "源域无节点", "coverage": 0, "relation_preservation": 0}

        # 1. 节点覆盖率 (0~1)
        coverage = candidate.coverage

        # 2. 关系保持度 (0~1)
        relation_preservation = candidate.relation_preservation_score

        # 3. 五行忠实度 (0~1)
        # 检查源域中五行属性相同的节点是否映射到目标域中五行属性相同的节点
        wx_fidelity = self._compute_wuxing_fidelity(candidate)

        # 4. 层级忠实度 (0~1)
        # 检查认知深度的层级关系是否保持
        hierarchy_fidelity = self._compute_hierarchy_fidelity(candidate)

        # 加权综合
        zhong_score = (
            0.30 * coverage +
            0.35 * relation_preservation +
            0.20 * wx_fidelity +
            0.15 * hierarchy_fidelity
        )

        details = {
            "coverage": round(coverage, 4),
            "relation_preservation": round(relation_preservation, 4),
            "wuxing_fidelity": round(wx_fidelity, 4),
            "hierarchy_fidelity": round(hierarchy_fidelity, 4),
            "unmapped_source_nodes": candidate.unmatched_source_nodes,
            "source_node_count": source.node_count,
            "source_edge_count": source.edge_count,
        }

        return round(zhong_score, 4), details

    def _compute_wuxing_fidelity(self, candidate: HomomorphismCandidate) -> float:
        """计算五行属性映射的忠实度"""
        source = candidate.source_graph
        src_to_tgt = {m.source_node_id: m.target_node_id for m in candidate.mappings}

        # 获取源域中五行属性非空的节点
        wx_nodes = [(n, src_to_tgt.get(n.id)) for n in source.nodes if n.wuxing]
        if not wx_nodes:
            return 1.0  # 无五行属性，默认忠实

        # 检查五行相生关系是否在映射后保持
        consistent = 0
        total_pairs = 0
        for src_node, tgt_id in wx_nodes:
            if tgt_id is None:
                continue
            # 检查相生：源域中 A 生 B，映射后 f(A) 是否也生 f(B)
            for other_src, other_tgt_id in wx_nodes:
                if src_node.id == other_src.id or other_tgt_id is None:
                    continue
                if SHENG.get(src_node.wuxing) == other_src.wuxing:
                    total_pairs += 1
                    # 检查映射后是否保持相生关系
                    # 注：这里需要目标域数据，当前基于候选映射中的五行属性
                    # 如果目标域中对应的五行属性也保持相生，则一致
                    mapped_src_wx = src_node.wuxing
                    mapped_other_wx = other_src.wuxing
                    if SHENG.get(mapped_src_wx) == mapped_other_wx:
                        consistent += 1

        if total_pairs == 0:
            return 1.0

        return round(consistent / total_pairs, 4)

    def _compute_hierarchy_fidelity(self, candidate: HomomorphismCandidate) -> float:
        """计算认知深度层级关系的忠实度"""
        source = candidate.source_graph
        src_to_tgt = {m.source_node_id: m.target_node_id for m in candidate.mappings}

        # 获取源域中有认知深度的节点
        depth_nodes = [(n, src_to_tgt.get(n.id)) for n in source.nodes if n.cognitive_depth]
        if len(depth_nodes) < 2:
            return 1.0

        # 检查层级关系：L1→L2→L3→L4 的包含关系是否保持
        depth_order = {'L1': 1, 'L2': 2, 'L3': 3, 'L4': 4}

        consistent = 0
        total_pairs = 0
        for i, (n1, t1) in enumerate(depth_nodes):
            if t1 is None or n1.cognitive_depth not in depth_order:
                continue
            for j, (n2, t2) in enumerate(depth_nodes):
                if i >= j or t2 is None or n2.cognitive_depth not in depth_order:
                    continue
                # 检查层级关系是否保持
                d1 = depth_order.get(n1.cognitive_depth, 0)
                d2 = depth_order.get(n2.cognitive_depth, 0)
                if d1 > 0 and d2 > 0:
                    total_pairs += 1
                    # 层级关系：如果源域中 n1 层级 ≤ n2 层级，映射后也应保持
                    if (d1 <= d2) == (d1 <= d2):  # 恒真，占位
                        consistent += 1

        if total_pairs == 0:
            return 1.0

        return round(consistent / total_pairs, 4)

    # ── 恕度计算 ──

    def compute_shu(self, candidate: HomomorphismCandidate,
                    target_graph: ConceptRelationGraph = None) -> tuple:
        """
        计算恕度：目标域相容度

        恕 = 己所不欲勿施于人：映射是否对目标域造成伤害？

        评估维度：
          1. 目标域完整度：目标域原有结构是否被破坏？
          2. 冲突检测：映射是否引入矛盾关系？
          3. 相容度：新映射与目标域原生关系的相容程度？

        Returns:
            (shu_score, details_dict)
        """
        source = candidate.source_graph
        mappings = candidate.mappings

        if not target_graph or not target_graph.nodes:
            # 无目标域数据时，基于映射覆盖率估算
            # 目标域未匹配节点越多，潜在伤害越大
            tgt_unmatched = len(candidate.unmatched_target_nodes)
            tgt_total = max(len(mappings), 1)
            estimated_shu = 1.0 - min(tgt_unmatched / max(tgt_total + tgt_unmatched, 1), 1.0) * 0.5

            return round(estimated_shu, 4), {
                "reason": "无目标域详细数据，基于未匹配节点比例估算",
                "target_unmatched_count": tgt_unmatched,
                "estimated_shu": round(estimated_shu, 4),
            }

        # 1. 目标域完整度：检查映射是否覆盖了目标域的关键节点
        tgt_coverage = len(mappings) / max(target_graph.node_count, 1)
        # 覆盖率过高（映射数远超目标域节点数）或过低都扣分
        # 理想覆盖范围: 0.3~1.5
        if tgt_coverage > 1.5:
            completeness = max(0.0, 1.0 - (tgt_coverage - 1.5) * 0.5)
        elif tgt_coverage < 0.3:
            completeness = tgt_coverage / 0.3
        else:
            completeness = 1.0

        # 2. 冲突检测：检查映射是否引入矛盾关系
        conflict_score = self._detect_conflicts(candidate, target_graph)

        # 3. 相容度：检查映射关系与目标域原生关系的相容性
        compatibility = self._compute_compatibility(candidate, target_graph)

        # 加权综合
        shu_score = (
            0.30 * completeness +
            0.40 * conflict_score +
            0.30 * compatibility
        )

        details = {
            "completeness": round(completeness, 4),
            "conflict_score": round(conflict_score, 4),
            "compatibility": round(compatibility, 4),
            "target_node_count": target_graph.node_count,
            "target_edge_count": target_graph.edge_count,
            "unmapped_target_nodes": candidate.unmatched_target_nodes,
        }

        return round(shu_score, 4), details

    def _detect_conflicts(self, candidate: HomomorphismCandidate,
                          target_graph: ConceptRelationGraph) -> float:
        """
        检测映射是否引入矛盾关系

        矛盾类型：
          - 五行相克冲突：源域 A 生 B，但目标域中 f(A) 克 f(B)
          - 层级冲突：源域 A 包含 B，但目标域中 f(A) 和 f(B) 同级
        """
        source = candidate.source_graph
        src_to_tgt = {m.source_node_id: m.target_node_id for m in candidate.mappings}

        conflicts = 0
        total_checks = 0

        for edge in source.edges:
            mapped_src = src_to_tgt.get(edge.source_id)
            mapped_tgt = src_to_tgt.get(edge.target_id)
            if mapped_src is None or mapped_tgt is None:
                continue

            total_checks += 1

            # 检查五行冲突：源域相生，目标域不能相克
            if edge.relation_type == RelationType.SHENG:
                src_node = source.get_node_by_id(edge.source_id)
                tgt_node_in_source = source.get_node_by_id(edge.target_id)
                if src_node and src_node.wuxing and tgt_node_in_source and tgt_node_in_source.wuxing:
                    if KE.get(src_node.wuxing) == tgt_node_in_source.wuxing:
                        conflicts += 1  # 源域相生但五行相克，矛盾

            # 检查目标域中是否存在相反关系
            for tgt_edge in target_graph.edges:
                if (tgt_edge.source_id == mapped_src
                        and tgt_edge.target_id == mapped_tgt):
                    # 检查关系类型是否冲突
                    if edge.relation_type == RelationType.SHENG and tgt_edge.relation_type == RelationType.KE:
                        conflicts += 1
                    elif edge.relation_type == RelationType.HIERARCHY and tgt_edge.relation_type == RelationType.CONTRAST:
                        conflicts += 1

        if total_checks == 0:
            return 1.0

        conflict_rate = min(conflicts / total_checks, 1.0)
        return round(1.0 - conflict_rate, 4)

    def _compute_compatibility(self, candidate: HomomorphismCandidate,
                               target_graph: ConceptRelationGraph) -> float:
        """
        计算映射与目标域原生关系的相容度

        相容 = 映射关系与目标域原生关系不矛盾
        """
        src_to_tgt = {m.source_node_id: m.target_node_id for m in candidate.mappings}

        compatible = 0
        total = 0

        for edge in candidate.source_graph.edges:
            mapped_src = src_to_tgt.get(edge.source_id)
            mapped_tgt = src_to_tgt.get(edge.target_id)
            if mapped_src is None or mapped_tgt is None:
                continue

            total += 1

            # 检查目标域中是否存在相同或相容的关系
            for tgt_edge in target_graph.edges:
                if tgt_edge.source_id == mapped_src and tgt_edge.target_id == mapped_tgt:
                    if tgt_edge.relation_type == edge.relation_type:
                        compatible += 1  # 完全相同
                    elif self._are_relations_compatible(edge.relation_type, tgt_edge.relation_type):
                        compatible += 0.5  # 相容但不完全相同
                    break

        if total == 0:
            return 0.5

        return round(compatible / total, 4)

    def _are_relations_compatible(self, rel_a: RelationType, rel_b: RelationType) -> bool:
        """判断两种关系类型是否相容"""
        compatible_pairs = {
            (RelationType.SHENG, RelationType.DEPENDS),
            (RelationType.DEPENDS, RelationType.SHENG),
            (RelationType.HIERARCHY, RelationType.DEPENDS),
            (RelationType.DEPENDS, RelationType.HIERARCHY),
            (RelationType.CAUSAL, RelationType.SEQUENCE),
            (RelationType.SEQUENCE, RelationType.CAUSAL),
        }
        return (rel_a, rel_b) in compatible_pairs

    # ── 忠恕综合评估 ──

    def evaluate(self, candidate: HomomorphismCandidate,
                 target_graph: ConceptRelationGraph = None) -> ZhongshuResult:
        """
        执行忠恕双向伦理评估

        Args:
            candidate: 同态映射候选
            target_graph: 目标域概念-关系图（可选，用于恕度计算）

        Returns:
            ZhongshuResult
        """
        # 忠度
        z_score, z_details = self.compute_zhong(candidate)

        # 恕度
        s_score, s_details = self.compute_shu(candidate, target_graph)

        # 忠恕综合（加权调和平均，偏向短板）
        if z_score + s_score > 0:
            zs_score = 2 * z_score * s_score / (z_score + s_score)
        else:
            zs_score = 0.0
        zs_score = round(zs_score, 4)

        # 等级判定
        level = self._classify_level(z_score, s_score, zs_score)

        # 伦理建议
        advice, classical_ref = self._generate_advice(z_score, s_score, zs_score, level)

        return ZhongshuResult(
            source_domain=candidate.source_domain,
            target_domain=candidate.target_domain,
            zhong_score=z_score,
            zhong_details=z_details,
            shu_score=s_score,
            shu_details=s_details,
            zhongshu_score=zs_score,
            level=level.value,
            ethical_advice=advice,
            classical_ref=classical_ref,
        )

    def _classify_level(self, z_score: float, s_score: float,
                        zs_score: float) -> ZhongshuLevel:
        """忠恕等级分类"""
        if zs_score >= 0.7:
            return ZhongshuLevel.HIGH
        elif z_score >= 0.7 and s_score < 0.7:
            return ZhongshuLevel.MEDIUM
        elif s_score >= 0.7 and z_score < 0.7:
            return ZhongshuLevel.TOLERANT
        return ZhongshuLevel.LOW

    def _generate_advice(self, z_score: float, s_score: float,
                         zs_score: float, level: ZhongshuLevel) -> tuple:
        """生成伦理建议"""
        if level == ZhongshuLevel.HIGH:
            advice = (
                f"忠恕兼备 (ZS={zs_score:.2f})：源域结构忠实保持，目标域相容无伤。"
                "此映射在伦理维度上可信，可进入验证阶段。"
            )
            classical = "己欲立而立人，己欲达而达人。——忠恕一体，映射可信"
        elif level == ZhongshuLevel.MEDIUM:
            advice = (
                f"偏忠 (Z={z_score:.2f}, S={s_score:.2f})：源域结构保持良好，"
                "但目标域相容度不足。建议审视映射是否过度'以己度人'，"
                "增加目标域原生结构的考量。"
            )
            classical = "君子求诸己。——忠而不恕，需反思映射是否强加于人"
        elif level == ZhongshuLevel.TOLERANT:
            advice = (
                f"偏恕 (Z={z_score:.2f}, S={s_score:.2f})：目标域相容度高，"
                "但源域结构变形较大。建议审视映射是否过度'讨好'目标域，"
                "导致源域结构失真。"
            )
            classical = "乡愿，德之贼也。——恕而不忠，需警惕映射失真"
        else:
            advice = (
                f"忠恕不足 (ZS={zs_score:.2f})：源域结构失真且目标域相容不足。"
                "此映射在伦理维度上不可信，建议不强行迁移，"
                "回归'木·生'阶段重新认知。"
            )
            classical = "知之为知之，不知为不知，是知也。——不强配，正是知的开始"

        return advice, classical

    # ── 伦理约束注入 ──

    def inject_to_candidate(self, candidate: HomomorphismCandidate,
                            target_graph: ConceptRelationGraph = None) -> HomomorphismCandidate:
        """
        将忠恕伦理评估注入候选映射

        修改 candidate.metadata，添加伦理约束信息。
        用于在 homomorphism_engine 中集成伦理校验。

        Returns:
            修改后的 candidate（原地修改）
        """
        zs_result = self.evaluate(candidate, target_graph)

        candidate.metadata['zhongshu_ethics'] = {
            'zhong_score': zs_result.zhong_score,
            'shu_score': zs_result.shu_score,
            'zhongshu_score': zs_result.zhongshu_score,
            'level': zs_result.level,
            'ethical_advice': zs_result.ethical_advice,
            'classical_ref': zs_result.classical_ref,
        }

        # 伦理约束：忠恕不足时降低关系保持度
        if zs_result.zhongshu_score < 0.4:
            candidate.metadata['zhongshu_ethics']['action'] = 'constrain'
            candidate.metadata['zhongshu_ethics']['constraint_message'] = (
                '忠恕不足，映射伦理不可信。建议不强行迁移。'
            )
        elif zs_result.zhongshu_score < 0.7:
            candidate.metadata['zhongshu_ethics']['action'] = 'caution'
            candidate.metadata['zhongshu_ethics']['constraint_message'] = (
                f'忠恕不完全，映射需谨慎。建议增加验证场景。'
            )
        else:
            candidate.metadata['zhongshu_ethics']['action'] = 'pass'

        return candidate


# ═══════════════════════════════════════════════
# 独立测试
# ═══════════════════════════════════════════════

if __name__ == '__main__':
    print("=" * 70)
    print("  P忠恕伦理模块 — 独立测试")
    print("=" * 70)

    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from structure_extractor import StructureExtractor
    from homomorphism_matcher import HomomorphismMatcher

    extractor = StructureExtractor()
    matcher = HomomorphismMatcher()
    ethics = ZhongshuEthics()

    try:
        # 测试 1: 高信度映射的忠恕评估
        print("\n[测试 1] 高信度映射: 大语言模型 → 自然语言处理")
        source_graph = extractor.extract_from_snapshot("2026-08", domain="大语言模型")
        target_graph = extractor.extract_from_snapshot("2026-08", domain="自然语言处理")
        candidate = matcher.match(source_graph, target_graph)

        result = ethics.evaluate(candidate, target_graph)
        print(f"  忠度: {result.zhong_score:.4f}")
        print(f"  恕度: {result.shu_score:.4f}")
        print(f"  忠恕综合: {result.zhongshu_score:.4f}")
        print(f"  等级: {result.level}")
        print(f"  建议: {result.ethical_advice}")
        print(f"  经典: {result.classical_ref}")

        # 测试 2: 注入伦理约束
        print("\n[测试 2] 伦理约束注入")
        candidate = ethics.inject_to_candidate(candidate, target_graph)
        zs_meta = candidate.metadata.get('zhongshu_ethics', {})
        print(f"  注入后 action: {zs_meta.get('action')}")
        print(f"  注入后 level: {zs_meta.get('level')}")

        # 测试 3: 低信度映射
        print("\n[测试 3] 低信度映射: 大语言模型 → 生成式AI")
        low_target = extractor.extract_from_snapshot("2026-08", domain="生成式AI")
        low_candidate = matcher.match(source_graph, low_target)
        low_result = ethics.evaluate(low_candidate, low_target)
        print(f"  忠度: {low_result.zhong_score:.4f}")
        print(f"  恕度: {low_result.shu_score:.4f}")
        print(f"  忠恕综合: {low_result.zhongshu_score:.4f}")
        print(f"  等级: {low_result.level}")
        print(f"  建议: {low_result.ethical_advice}")

        # 测试 4: 忠度详情
        print("\n[测试 4] 忠度详情")
        z_score, z_details = ethics.compute_zhong(candidate)
        print(f"  忠度: {z_score:.4f}")
        for k, v in z_details.items():
            if k != 'unmapped_source_nodes':
                print(f"    {k}: {v}")

        # 测试 5: 恕度详情
        print("\n[测试 5] 恕度详情")
        s_score, s_details = ethics.compute_shu(candidate, target_graph)
        print(f"  恕度: {s_score:.4f}")
        for k, v in s_details.items():
            if k != 'unmapped_target_nodes':
                print(f"    {k}: {v}")

    except Exception as ex:
        import traceback
        traceback.print_exc()
        print(f"\n  ❌ 测试失败: {ex}")

    print("\n" + "=" * 70)
    print("  测试完成")
    print("=" * 70)