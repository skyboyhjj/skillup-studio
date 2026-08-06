"""
同态匹配器 — 同态映射引擎 Step 2
===================================
在旧域（源域）和新域（目标域）之间寻找同态映射候选，
输出关系保持度评分和信度出口决策。

核心机制：
  1. 结构匹配：基于图拓扑（节点度、关系类型）寻找候选映射
  2. 五行匹配：基于五行属性直接匹配（规则驱动，白盒）
  3. 语义匹配：LLM 辅助的概念语义相似度匹配
  4. 关系保持度计算：验证 f(A 生 B) == f(A) 生 f(B) 是否成立
  5. 信度出口：三档分类（≥0.7 / 0.4~0.7 / <0.4）

用法:
    from homomorphism_matcher import HomomorphismMatcher
    matcher = HomomorphismMatcher()
    candidate = matcher.match(source_graph, target_graph)
    decision = matcher.confidence_decision(candidate)
"""

import math
import json
from collections import defaultdict
from typing import List, Dict, Optional, Tuple, Callable

from homomorphism_types import (
    ConceptNode, RelationEdge, RelationType,
    ConceptRelationGraph, NodeMapping, HomomorphismCandidate,
    ConfidenceLevel, classify_confidence, confidence_decision,
    CONFIDENCE_THRESHOLD_HIGH, CONFIDENCE_THRESHOLD_MEDIUM,
)

# 五行相生相克规则
SHENG = {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'}
KE = {'木': '土', '土': '水', '水': '火', '火': '金', '金': '木'}


class HomomorphismMatcher:
    """
    同态匹配器

    在源域和目标域之间寻找同态映射候选。
    支持三种匹配策略（可组合使用）：
      - 结构匹配：基于图拓扑
      - 五行匹配：基于五行属性规则
      - 语义匹配：基于 LLM 概念相似度
    """

    def __init__(self, llm_matcher: Callable = None):
        """
        Args:
            llm_matcher: 可选的 LLM 语义匹配函数
                        签名: (source_graph, target_graph) -> List[NodeMapping]
        """
        self.llm_matcher = llm_matcher

    # ── 匹配策略 ──

    def match_by_wuxing(self, source: ConceptRelationGraph,
                        target: ConceptRelationGraph) -> List[NodeMapping]:
        """
        基于五行属性匹配（规则驱动，白盒）

        规则：若 source_node.wuxing == target_node.wuxing，则建立映射。
        信度 = 1.0（五行规则是公理，不需要统计推断）
        """
        mappings = []
        source_wx = {n.wuxing: n for n in source.nodes if n.wuxing}
        target_wx = {n.wuxing: n for n in target.nodes if n.wuxing}

        for wx, src_node in source_wx.items():
            if wx in target_wx:
                tgt_node = target_wx[wx]
                mappings.append(NodeMapping(
                    source_node_id=src_node.id,
                    source_node_name=src_node.name,
                    target_node_id=tgt_node.id,
                    target_node_name=tgt_node.name,
                    confidence=1.0,
                    rationale=f"五行属性匹配: 均为'{wx}'，经典规则约束",
                ))

        return mappings

    def match_by_structure(self, source: ConceptRelationGraph,
                           target: ConceptRelationGraph) -> List[NodeMapping]:
        """
        基于结构相似度匹配

        对每个源节点，在目标域中寻找结构最相似的节点。
        结构相似度 = 度相似度 + 关系类型分布相似度
        """
        # 计算源域和目标域每个节点的结构特征
        src_features = self._compute_node_features(source)
        tgt_features = self._compute_node_features(target)

        mappings = []
        for src_id, src_feat in src_features.items():
            src_node = source.get_node_by_id(src_id)
            best_match = None
            best_score = 0.0

            for tgt_id, tgt_feat in tgt_features.items():
                tgt_node = target.get_node_by_id(tgt_id)
                score = self._structural_similarity(src_feat, tgt_feat)

                if score > best_score:
                    best_score = score
                    best_match = (tgt_id, tgt_node, score)

            if best_match and best_score >= 0.3:  # 最低结构相似度阈值
                tgt_id, tgt_node, score = best_match
                mappings.append(NodeMapping(
                    source_node_id=src_id,
                    source_node_name=src_node.name if src_node else "?",
                    target_node_id=tgt_id,
                    target_node_name=tgt_node.name if tgt_node else "?",
                    confidence=round(score, 2),
                    rationale=f"结构相似度: {score:.2f} (度/入度/出度/关系类型分布)",
                ))

        return mappings

    def _compute_node_features(self, graph: ConceptRelationGraph) -> Dict[str, dict]:
        """计算每个节点的结构特征"""
        features = {}
        for node in graph.nodes:
            out_edges = graph.get_outgoing_edges(node.id)
            in_edges = graph.get_incoming_edges(node.id)

            # 关系类型分布
            out_types = defaultdict(int)
            in_types = defaultdict(int)
            for e in out_edges:
                out_types[e.relation_type.value] += 1
            for e in in_edges:
                in_types[e.relation_type.value] += 1

            features[node.id] = {
                'out_degree': len(out_edges),
                'in_degree': len(in_edges),
                'total_degree': len(out_edges) + len(in_edges),
                'out_type_dist': dict(out_types),
                'in_type_dist': dict(in_types),
                'wuxing': node.wuxing,
                'depth': node.cognitive_depth,
                'level': node.level,
            }
        return features

    def _structural_similarity(self, feat_a: dict, feat_b: dict) -> float:
        """计算两个节点结构特征的相似度"""
        if feat_a['total_degree'] == 0 and feat_b['total_degree'] == 0:
            return 0.5  # 两个孤立节点，中性相似度

        # 度相似度（使用相对差异）
        max_deg = max(feat_a['total_degree'], feat_b['total_degree'], 1)
        deg_sim = 1 - abs(feat_a['total_degree'] - feat_b['total_degree']) / max_deg

        # 关系类型分布相似度（Jaccard）
        all_types = set(feat_a['out_type_dist'].keys()) | set(feat_b['out_type_dist'].keys())
        if all_types:
            type_sim = len(set(feat_a['out_type_dist'].keys()) & set(feat_b['out_type_dist'].keys())) / len(all_types)
        else:
            type_sim = 0.5

        # 五行属性相似度（加分项）
        wx_sim = 0.0
        if feat_a.get('wuxing') and feat_b.get('wuxing'):
            if feat_a['wuxing'] == feat_b['wuxing']:
                wx_sim = 0.3  # 五行相同，显著加分
            elif SHENG.get(feat_a['wuxing']) == feat_b['wuxing']:
                wx_sim = 0.15  # 相生关系
            elif KE.get(feat_a['wuxing']) == feat_b['wuxing']:
                wx_sim = 0.1  # 相克关系

        # 加权综合
        return 0.4 * deg_sim + 0.3 * type_sim + 0.3 * wx_sim

    # ── 关系保持度计算 ──

    def compute_relation_preservation(self, source: ConceptRelationGraph,
                                      target: ConceptRelationGraph,
                                      mappings: List[NodeMapping]) -> float:
        """
        计算关系保持度评分

        核心逻辑（对应第三步"唯识纠正"）：
          验证标准回到源域公理——检查源域的关系在映射后是否在目标域中保持。
          不是"两域是否看着像"，而是"新域结构是否与源域公理相容"。

        算法：
          对源域的每条边 (A → B, type=T)：
            1. 找到 f(A) 和 f(B) 在目标域中的映射
            2. 检查目标域中 f(A) → f(B) 是否也存在类型 T 的关系
            3. 若存在，计为"保持"；若不存在，计为"未保持"
          关系保持度 = 保持的边数 / 总边数
        """
        if not source.edges:
            return 0.0

        # 建立映射查找表
        src_to_tgt = {m.source_node_id: m.target_node_id for m in mappings}

        preserved_count = 0
        total_count = len(source.edges)

        for edge in source.edges:
            src_id = edge.source_id
            tgt_id = edge.target_id

            mapped_src = src_to_tgt.get(src_id)
            mapped_tgt = src_to_tgt.get(tgt_id)

            if mapped_src is None or mapped_tgt is None:
                continue  # 无法映射，跳过（不计入保持）

            # 检查目标域中是否存在同类型的关系边
            if self._edge_exists(target, mapped_src, mapped_tgt, edge.relation_type):
                preserved_count += 1

        return round(preserved_count / total_count, 4) if total_count > 0 else 0.0

    def _edge_exists(self, graph: ConceptRelationGraph,
                     source_id: str, target_id: str,
                     relation_type: RelationType) -> bool:
        """检查图中是否存在指定类型的关系边"""
        for e in graph.edges:
            if (e.source_id == source_id
                    and e.target_id == target_id
                    and e.relation_type == relation_type):
                return True
        return False

    # ── 主匹配 ──

    def match(self, source: ConceptRelationGraph,
              target: ConceptRelationGraph,
              strategies: List[str] = None,
              use_llm: bool = False) -> HomomorphismCandidate:
        """
        执行同态匹配

        Args:
            source: 源域（旧域）概念-关系图
            target: 目标域（新域）概念-关系图
            strategies: 匹配策略列表 ["wuxing", "structure", "llm"]
            use_llm: 是否使用 LLM 语义匹配

        Returns:
            HomomorphismCandidate
        """
        if strategies is None:
            strategies = ["wuxing", "structure"]

        all_mappings: List[NodeMapping] = []
        mapped_source_ids = set()

        # 策略 1: 五行匹配（优先级最高，信度=1.0）
        if "wuxing" in strategies:
            wx_mappings = self.match_by_wuxing(source, target)
            for m in wx_mappings:
                if m.source_node_id not in mapped_source_ids:
                    all_mappings.append(m)
                    mapped_source_ids.add(m.source_node_id)

        # 策略 2: 结构匹配
        if "structure" in strategies:
            struct_mappings = self.match_by_structure(source, target)
            for m in struct_mappings:
                if m.source_node_id not in mapped_source_ids:
                    all_mappings.append(m)
                    mapped_source_ids.add(m.source_node_id)

        # 策略 3: LLM 语义匹配（可选）
        if "llm" in strategies and use_llm and self.llm_matcher:
            llm_mappings = self.llm_matcher(source, target)
            for m in llm_mappings:
                if m.source_node_id not in mapped_source_ids:
                    all_mappings.append(m)
                    mapped_source_ids.add(m.source_node_id)

        # 计算关系保持度
        relation_score = self.compute_relation_preservation(source, target, all_mappings)

        # 找出未匹配的节点
        all_source_ids = {n.id for n in source.nodes}
        all_target_ids = {n.id for n in target.nodes}
        unmatched_source = list(all_source_ids - mapped_source_ids)
        matched_target_ids = {m.target_node_id for m in all_mappings}
        unmatched_target = list(all_target_ids - matched_target_ids)

        candidate = HomomorphismCandidate(
            source_domain=source.domain,
            target_domain=target.domain,
            source_graph=source,
            mappings=all_mappings,
            relation_preservation_score=relation_score,
            confidence_level=classify_confidence(relation_score),
            unmatched_source_nodes=unmatched_source,
            unmatched_target_nodes=unmatched_target,
            suggested_verification_scenarios=self._get_verification_count(relation_score),
            metadata={
                'strategies_used': strategies,
                'use_llm': use_llm,
                'mapping_coverage': round(len(all_mappings) / max(source.node_count, 1), 2),
            }
        )

        return candidate

    def _get_verification_count(self, score: float) -> int:
        """根据信度确定验证场景数"""
        level = classify_confidence(score)
        if level == ConfidenceLevel.HIGH:
            return 3
        elif level == ConfidenceLevel.MEDIUM:
            return 5
        return 0

    # ── 信度出口 ──

    def confidence_decision(self, candidate: HomomorphismCandidate) -> dict:
        """信度出口决策（对齐三步协议 Step 2）"""
        return confidence_decision(candidate.relation_preservation_score)

    # ── 批量匹配 ──

    def match_all(self, source: ConceptRelationGraph,
                  target_graphs: Dict[str, ConceptRelationGraph],
                  strategies: List[str] = None) -> List[HomomorphismCandidate]:
        """
        将源域与多个目标域进行匹配

        Returns:
            按关系保持度降序排列的候选列表
        """
        candidates = []
        for domain, graph in target_graphs.items():
            candidate = self.match(source, graph, strategies)
            candidates.append(candidate)

        candidates.sort(key=lambda c: c.relation_preservation_score, reverse=True)
        return candidates


# ═══════════════════════════════════════════════
# 独立测试
# ═══════════════════════════════════════════════

if __name__ == '__main__':
    import os
    import sys

    print("=" * 70)
    print("  同态匹配器 — 独立测试")
    print("=" * 70)

    from structure_extractor import StructureExtractor

    extractor = StructureExtractor()

    # 加载两个领域
    try:
        print("\n[准备] 加载源域和目标域...")
        source_graph = extractor.extract_from_snapshot("2026-08", domain="大语言模型")
        target_graph = extractor.extract_from_snapshot("2026-08", domain="多模态智能")

        print(f"  源域 '{source_graph.domain}': {source_graph.node_count} 节点, {source_graph.edge_count} 边")
        print(f"  目标域 '{target_graph.domain}': {target_graph.node_count} 节点, {target_graph.edge_count} 边")

        # 创建匹配器
        matcher = HomomorphismMatcher()

        # 测试 1: 五行匹配
        print("\n[测试 1] 五行匹配策略")
        wx_mappings = matcher.match_by_wuxing(source_graph, target_graph)
        print(f"  匹配数: {len(wx_mappings)}")
        for m in wx_mappings[:5]:
            print(f"    {m.source_node_name} → {m.target_node_name} (信度={m.confidence}, {m.rationale})")

        # 测试 2: 结构匹配
        print("\n[测试 2] 结构匹配策略")
        struct_mappings = matcher.match_by_structure(source_graph, target_graph)
        print(f"  匹配数: {len(struct_mappings)}")
        for m in struct_mappings[:5]:
            print(f"    {m.source_node_name} → {m.target_node_name} (信度={m.confidence:.2f})")

        # 测试 3: 完整匹配 + 关系保持度
        print("\n[测试 3] 完整匹配（五行 + 结构）")
        candidate = matcher.match(source_graph, target_graph)
        print(f"  总映射数: {candidate.mapping_count}")
        print(f"  覆盖率: {candidate.coverage:.2%}")
        print(f"  关系保持度: {candidate.relation_preservation_score:.4f}")
        print(f"  信度等级: {candidate.confidence_level.value}")
        print(f"  建议验证场景: {candidate.suggested_verification_scenarios}")

        # 信度出口
        decision = matcher.confidence_decision(candidate)
        print(f"\n  信度出口: {decision['action']}")
        print(f"  消息: {decision['message']}")

        # 未匹配节点
        if candidate.unmatched_source_nodes:
            print(f"\n  未匹配源节点 ({len(candidate.unmatched_source_nodes)}):")
            for nid in candidate.unmatched_source_nodes[:5]:
                node = source_graph.get_node_by_id(nid)
                print(f"    {nid}: {node.name if node else '?'}")

        # 测试 4: 关系保持度详细计算
        print("\n[测试 4] 关系保持度详细分析")
        src_to_tgt = {m.source_node_id: m.target_node_id for m in candidate.mappings}
        preserved = 0
        total = len(source_graph.edges)
        for edge in source_graph.edges[:10]:  # 前 10 条边
            mapped_src = src_to_tgt.get(edge.source_id)
            mapped_tgt = src_to_tgt.get(edge.target_id)
            if mapped_src and mapped_tgt:
                exists = matcher._edge_exists(target_graph, mapped_src, mapped_tgt, edge.relation_type)
                if exists:
                    preserved += 1
                status = "✓ 保持" if exists else "✗ 未保持"
            else:
                status = "— 无法映射"
            src_name = source_graph.get_node_by_id(edge.source_id)
            tgt_name = source_graph.get_node_by_id(edge.target_id)
            print(f"    {src_name.name if src_name else '?'} → {tgt_name.name if tgt_name else '?'} [{edge.relation_type.value}] {status}")

        print(f"\n  关系保持: {preserved}/{total} = {preserved/total:.2%}")

        # 测试 5: 批量匹配
        print("\n[测试 5] 批量匹配（源域 vs 所有领域）")
        all_graphs = extractor.extract_all_domains("2026-08")
        # 移除源域自身
        if source_graph.domain in all_graphs:
            del all_graphs[source_graph.domain]

        candidates = matcher.match_all(source_graph, all_graphs)

        print(f"  候选领域数: {len(candidates)}")
        print(f"  {'目标域':<20} {'映射数':>6} {'关系保持度':>10} {'信度':>6} {'验证场景':>6}")
        print("  " + "-" * 52)
        for c in candidates[:10]:
            print(f"  {c.target_domain:<20} {c.mapping_count:>6} {c.relation_preservation_score:>10.4f} {c.confidence_level.value:>6} {c.suggested_verification_scenarios:>6}")

    except Exception as ex:
        import traceback
        traceback.print_exc()
        print(f"\n  ❌ 测试失败: {ex}")

    print("\n" + "=" * 70)
    print("  测试完成")
    print("=" * 70)