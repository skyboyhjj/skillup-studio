"""
结构提取器 — 同态映射引擎 Step 1
===================================
从 Base 层的概念网络中提取"概念-关系图"（ConceptRelationGraph），
作为同态映射的源域结构。

功能：
  1. 从 JSON 快照（nodes.json + edges.json）加载概念网络
  2. 基于五行属性推断生克关系
  3. 基于层级关系推断层级边
  4. 基于 LLM 辅助推断因果/类比关系（可选）
  5. 输出标准化的 ConceptRelationGraph

用法:
    from structure_extractor import StructureExtractor
    extractor = StructureExtractor(base_dir)
    graph = extractor.extract("道德经")
    graph = extractor.extract_from_snapshot("2026-08")
"""

import json
import os
import math
from collections import defaultdict
from typing import List, Dict, Optional, Tuple

from homomorphism_types import (
    ConceptNode, RelationEdge, RelationType,
    ConceptRelationGraph,
)

# 五行相生相克（来自经典规则 C-SHENG / C-KE）
SHENG = {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'}
KE = {'木': '土', '土': '水', '水': '火', '火': '金', '金': '木'}

# 五行→认知深度映射（用于推断关系强度）
WX_DEPTH_WEIGHT = {
    'L1': 0.3,  # 种子层：基础认知
    'L2': 0.5,  # 现行层：操作认知
    'L3': 0.7,  # 超越层：深度认知
    'L4': 0.9,  # 智慧层：元认知
}


class StructureExtractor:
    """从概念网络中提取结构化的概念-关系图"""

    def __init__(self, base_dir: str = None):
        """
        Args:
            base_dir: wuxing_flowengine 根目录
        """
        if base_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.base_dir = base_dir
        self.data_dir = os.path.join(base_dir, 'data', 'snapshots')

    # ── 加载 ──

    def load_nodes(self, snapshot_month: str = None) -> List[dict]:
        """加载节点数据"""
        path = os.path.join(self.data_dir, 'nodes.json')
        if snapshot_month:
            alt_path = os.path.join(self.data_dir, f'{snapshot_month}-30_snapshot.json')
            if os.path.exists(alt_path):
                path = alt_path

        if not os.path.exists(path):
            raise FileNotFoundError(f"节点文件不存在: {path}")

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 兼容快照格式（snapshot JSON 包含 nodes/edges/collect_time 等字段）
        if isinstance(data, dict) and 'nodes' in data:
            return data['nodes']
        return data

    def load_edges(self, snapshot_month: str = None) -> List[dict]:
        """加载边数据"""
        path = os.path.join(self.data_dir, 'edges.json')
        if snapshot_month:
            alt_path = os.path.join(self.data_dir, f'{snapshot_month}-30_snapshot.json')
            if os.path.exists(alt_path):
                with open(alt_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, dict) and 'edges' in data:
                    return data['edges']

        if not os.path.exists(path):
            raise FileNotFoundError(f"边文件不存在: {path}")

        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    # ── 转换 ──

    def _node_to_concept(self, raw: dict) -> ConceptNode:
        """将原始节点转为 ConceptNode"""
        return ConceptNode(
            id=raw.get('id', ''),
            name=raw.get('name', ''),
            wuxing=raw.get('wuxing'),
            cognitive_depth=raw.get('cognitive_depth'),
            category=raw.get('category'),
            level=raw.get('level', 1),
            attributes={
                'parent_id': raw.get('parent_id'),
                'position': raw.get('position'),
            }
        )

    def _edge_to_relation(self, raw: dict, nodes_by_id: dict) -> Optional[RelationEdge]:
        """将原始边转为 RelationEdge"""
        source_id = raw.get('source_id', '')
        target_id = raw.get('target_id', '')
        relation_str = raw.get('relation', 'contains')

        # 映射关系类型
        type_map = {
            'contains': RelationType.HIERARCHY,
            'hierarchy': RelationType.HIERARCHY,
            'causal': RelationType.CAUSAL,
            'causes': RelationType.CAUSAL,
            'analogy': RelationType.ANALOGY,
            'similar': RelationType.ANALOGY,
            'depends': RelationType.DEPENDS,
            'contrast': RelationType.CONTRAST,
            'sequence': RelationType.SEQUENCE,
        }
        rel_type = type_map.get(relation_str, RelationType.HIERARCHY)

        # 计算权重：基于两节点的认知深度
        weight = 1.0
        source_node = nodes_by_id.get(source_id)
        target_node = nodes_by_id.get(target_id)
        if source_node and target_node:
            src_depth = source_node.cognitive_depth
            tgt_depth = target_node.cognitive_depth
            if src_depth and tgt_depth:
                weight = (WX_DEPTH_WEIGHT.get(src_depth, 0.5) +
                          WX_DEPTH_WEIGHT.get(tgt_depth, 0.5)) / 2

        return RelationEdge(
            source_id=source_id,
            target_id=target_id,
            relation_type=rel_type,
            weight=round(weight, 2),
            description=f"{source_id} → {target_id} ({relation_str})",
            is_directed=True,
        )

    # ── 五行关系推断 ──

    def _infer_wuxing_relations(self, nodes: List[ConceptNode]) -> List[RelationEdge]:
        """
        基于节点的五行属性，推断相生/相克关系

        规则：
          - 若 node_A.wuxing 生 node_B.wuxing → 添加相生边
          - 若 node_A.wuxing 克 node_B.wuxing → 添加相克边
          - 关系权重 = 两节点深度的平均权重
        """
        edges = []
        wx_nodes = [n for n in nodes if n.wuxing in SHENG]

        for i, node_a in enumerate(wx_nodes):
            for j, node_b in enumerate(wx_nodes):
                if i == j:
                    continue
                wx_a = node_a.wuxing
                wx_b = node_b.wuxing

                if SHENG.get(wx_a) == wx_b:
                    weight = self._compute_wx_edge_weight(node_a, node_b)
                    edges.append(RelationEdge(
                        source_id=node_a.id,
                        target_id=node_b.id,
                        relation_type=RelationType.SHENG,
                        weight=weight,
                        description=f"{node_a.name}({wx_a}) 生 {node_b.name}({wx_b})",
                        is_directed=True,
                    ))

                if KE.get(wx_a) == wx_b:
                    weight = self._compute_wx_edge_weight(node_a, node_b)
                    edges.append(RelationEdge(
                        source_id=node_a.id,
                        target_id=node_b.id,
                        relation_type=RelationType.KE,
                        weight=weight,
                        description=f"{node_a.name}({wx_a}) 克 {node_b.name}({wx_b})",
                        is_directed=True,
                    ))

        return edges

    def _compute_wx_edge_weight(self, node_a: ConceptNode, node_b: ConceptNode) -> float:
        """计算五行边权重"""
        depth_a = WX_DEPTH_WEIGHT.get(node_a.cognitive_depth, 0.5)
        depth_b = WX_DEPTH_WEIGHT.get(node_b.cognitive_depth, 0.5)
        return round((depth_a + depth_b) / 2, 2)

    # ── 主提取 ──

    def extract(self, domain: str, snapshot_month: str = None,
                infer_wuxing: bool = True) -> ConceptRelationGraph:
        """
        从 Base 层提取指定领域的概念-关系图

        Args:
            domain: 领域名称（如 "大语言模型"、"道德经"）
            snapshot_month: 快照月份（如 "2026-08"），None 使用默认
            infer_wuxing: 是否基于五行属性推断生克关系

        Returns:
            ConceptRelationGraph
        """
        raw_nodes = self.load_nodes(snapshot_month)
        raw_edges = self.load_edges(snapshot_month)

        # 过滤指定领域的节点
        domain_nodes = [n for n in raw_nodes
                        if n.get('category') == domain or n.get('name') == domain]

        # 如果没有 category 匹配，尝试按名称匹配
        if not domain_nodes:
            domain_nodes = [n for n in raw_nodes
                            if domain.lower() in n.get('name', '').lower()
                            or domain.lower() in n.get('category', '').lower()]

        if not domain_nodes:
            raise ValueError(f"未找到领域 '{domain}' 的节点数据")

        # 收集所有相关节点 ID
        domain_node_ids = {n['id'] for n in domain_nodes}

        # 转换节点
        concept_nodes = [self._node_to_concept(n) for n in domain_nodes]
        nodes_by_id = {n.id: n for n in concept_nodes}

        # 转换边（仅保留两端都在领域内的边）
        concept_edges = []
        for e in raw_edges:
            if e['source_id'] in domain_node_ids and e['target_id'] in domain_node_ids:
                rel = self._edge_to_relation(e, nodes_by_id)
                if rel:
                    concept_edges.append(rel)

        # 推断五行关系
        if infer_wuxing:
            wx_edges = self._infer_wuxing_relations(concept_nodes)
            concept_edges.extend(wx_edges)

        # 收集关系类型
        relation_types = list(set(e.relation_type.value for e in concept_edges))

        return ConceptRelationGraph(
            domain=domain,
            nodes=concept_nodes,
            edges=concept_edges,
            relation_types=relation_types,
            metadata={
                'snapshot_month': snapshot_month,
                'infer_wuxing': infer_wuxing,
                'total_nodes_loaded': len(raw_nodes),
                'total_edges_loaded': len(raw_edges),
            }
        )

    def extract_from_snapshot(self, snapshot_month: str,
                              domain: str = None,
                              infer_wuxing: bool = True) -> ConceptRelationGraph:
        """
        从指定月份的快照中提取概念-关系图

        Args:
            snapshot_month: 快照月份（如 "2026-08"）
            domain: 领域名称，None 则提取全部领域
            infer_wuxing: 是否推断五行关系

        Returns:
            ConceptRelationGraph
        """
        raw_nodes = self.load_nodes(snapshot_month)
        raw_edges = self.load_edges(snapshot_month)

        # 过滤领域
        if domain:
            raw_nodes = [n for n in raw_nodes
                         if n.get('category') == domain
                         or domain.lower() in n.get('name', '').lower()
                         or domain.lower() in n.get('category', '').lower()]

        if not raw_nodes:
            raise ValueError(f"快照 {snapshot_month} 中未找到领域 '{domain}' 的节点数据")

        node_ids = {n['id'] for n in raw_nodes}

        concept_nodes = [self._node_to_concept(n) for n in raw_nodes]
        nodes_by_id = {n.id: n for n in concept_nodes}

        concept_edges = []
        for e in raw_edges:
            if e['source_id'] in node_ids and e['target_id'] in node_ids:
                rel = self._edge_to_relation(e, nodes_by_id)
                if rel:
                    concept_edges.append(rel)

        if infer_wuxing:
            wx_edges = self._infer_wuxing_relations(concept_nodes)
            concept_edges.extend(wx_edges)

        relation_types = list(set(e.relation_type.value for e in concept_edges))

        return ConceptRelationGraph(
            domain=domain or snapshot_month,
            nodes=concept_nodes,
            edges=concept_edges,
            relation_types=relation_types,
            metadata={
                'snapshot_month': snapshot_month,
                'infer_wuxing': infer_wuxing,
                'total_nodes': len(raw_nodes),
                'total_edges': len(concept_edges),
            }
        )

    def extract_all_domains(self, snapshot_month: str = None,
                            infer_wuxing: bool = True) -> Dict[str, ConceptRelationGraph]:
        """
        提取所有领域的概念-关系图

        Returns:
            {domain_name: ConceptRelationGraph}
        """
        raw_nodes = self.load_nodes(snapshot_month)

        # 按 category 分组
        nodes_by_category = defaultdict(list)
        for n in raw_nodes:
            cat = n.get('category', 'unknown')
            nodes_by_category[cat].append(n)

        graphs = {}
        for domain, domain_nodes in nodes_by_category.items():
            if domain == 'root':
                continue
            if len(domain_nodes) < 3:  # 跳过太小的领域
                continue

            node_ids = {n['id'] for n in domain_nodes}
            concept_nodes = [self._node_to_concept(n) for n in domain_nodes]
            nodes_by_id = {n.id: n for n in concept_nodes}

            raw_edges = self.load_edges(snapshot_month)
            concept_edges = []
            for e in raw_edges:
                if e['source_id'] in node_ids and e['target_id'] in node_ids:
                    rel = self._edge_to_relation(e, nodes_by_id)
                    if rel:
                        concept_edges.append(rel)

            if infer_wuxing:
                wx_edges = self._infer_wuxing_relations(concept_nodes)
                concept_edges.extend(wx_edges)

            relation_types = list(set(e.relation_type.value for e in concept_edges))

            graphs[domain] = ConceptRelationGraph(
                domain=domain,
                nodes=concept_nodes,
                edges=concept_edges,
                relation_types=relation_types,
                metadata={
                    'snapshot_month': snapshot_month,
                    'infer_wuxing': infer_wuxing,
                }
            )

        return graphs

    # ── 图统计 ──

    def get_graph_stats(self, graph: ConceptRelationGraph) -> dict:
        """获取图的统计信息"""
        edge_type_counts = defaultdict(int)
        for e in graph.edges:
            edge_type_counts[e.relation_type.value] += 1

        wx_dist = defaultdict(int)
        depth_dist = defaultdict(int)
        for n in graph.nodes:
            if n.wuxing:
                wx_dist[n.wuxing] += 1
            if n.cognitive_depth:
                depth_dist[n.cognitive_depth] += 1

        return {
            "domain": graph.domain,
            "node_count": graph.node_count,
            "edge_count": graph.edge_count,
            "edge_type_distribution": dict(edge_type_counts),
            "wuxing_distribution": dict(wx_dist),
            "depth_distribution": dict(depth_dist),
            "relation_types": graph.relation_types,
            "avg_degree": round(graph.edge_count * 2 / max(graph.node_count, 1), 2),
        }


# ═══════════════════════════════════════════════
# 独立测试
# ═══════════════════════════════════════════════

if __name__ == '__main__':
    print("=" * 70)
    print("  结构提取器 — 独立测试")
    print("=" * 70)

    extractor = StructureExtractor()

    # 测试 1: 提取单个领域
    print("\n[测试 1] 提取 '大语言模型' 领域")
    try:
        graph = extractor.extract("大语言模型")
        print(f"  节点数: {graph.node_count}")
        print(f"  边数: {graph.edge_count}")
        print(f"  关系类型: {graph.relation_types}")

        stats = extractor.get_graph_stats(graph)
        print(f"  边类型分布: {stats['edge_type_distribution']}")
        print(f"  五行分布: {stats['wuxing_distribution']}")
        print(f"  平均度: {stats['avg_degree']}")

        # 打印前 5 个节点
        print("\n  前 5 个节点:")
        for n in graph.nodes[:5]:
            print(f"    [{n.id}] {n.name} (五行={n.wuxing}, 深度={n.cognitive_depth})")

        # 打印关系边样例
        sheng_edges = graph.get_sheng_edges()
        ke_edges = graph.get_ke_edges()
        print(f"\n  相生边: {len(sheng_edges)} 条")
        for e in sheng_edges[:3]:
            print(f"    {e.description} (权重={e.weight})")
        print(f"  相克边: {len(ke_edges)} 条")
        for e in ke_edges[:3]:
            print(f"    {e.description} (权重={e.weight})")

    except Exception as ex:
        print(f"  ❌ 失败: {ex}")

    # 测试 2: 提取所有领域
    print("\n[测试 2] 提取所有领域")
    try:
        all_graphs = extractor.extract_all_domains()
        print(f"  领域数: {len(all_graphs)}")
        for domain, g in sorted(all_graphs.items()):
            print(f"    {domain}: {g.node_count} 节点, {g.edge_count} 边")
    except Exception as ex:
        print(f"  ❌ 失败: {ex}")

    # 测试 3: 从快照提取
    print("\n[测试 3] 从快照 '2026-08' 提取")
    try:
        graph = extractor.extract_from_snapshot("2026-08", domain="大语言模型")
        print(f"  节点数: {graph.node_count}")
        print(f"  边数: {graph.edge_count}")

        # 导出 dict
        d = graph.to_dict()
        print(f"  to_dict 字段: {list(d.keys())}")
    except Exception as ex:
        print(f"  ❌ 失败: {ex}")

    print("\n" + "=" * 70)
    print("  测试完成")
    print("=" * 70)