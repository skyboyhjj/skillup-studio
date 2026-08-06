"""
同态映射引擎 — 数据类型定义
=============================
基于《反者道之动_矛盾迭代引擎_五轮对话深度复盘_完善版》第五步三步协议，
定义同态映射引擎的核心数据结构。

关系类型：
  - 生克: 五行相生相克关系
  - 因果: 逻辑因果关系
  - 层级: 概念层级关系（上下位/包含）
  - 类比: 相似性关系

信度出口三档：
  ≥ 0.7 → 高信度，直接进入验证
  0.4 ~ 0.7 → 低信度，增加验证场景
  < 0.4 → 不强配
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Literal
from enum import Enum


# ═══════════════════════════════════════════════
# 枚举类型
# ═══════════════════════════════════════════════

class RelationType(str, Enum):
    """关系类型"""
    SHENG = "相生"       # 五行相生
    KE = "相克"          # 五行相克
    CAUSAL = "因果"      # 逻辑因果
    HIERARCHY = "层级"   # 上下位/包含
    ANALOGY = "类比"     # 相似性
    DEPENDS = "依赖"     # 功能依赖
    CONTRAST = "对立"    # 对比/对立
    SEQUENCE = "时序"    # 时间先后


class ConfidenceLevel(str, Enum):
    """信度等级"""
    HIGH = "high"        # ≥ 0.7
    MEDIUM = "medium"    # 0.4 ~ 0.7
    LOW = "low"          # < 0.4


class VerificationStatus(str, Enum):
    """验证状态"""
    PASSED = "passed"
    FAILED = "failed"
    PARTIAL = "partial"  # 部分通过


# ═══════════════════════════════════════════════
# 核心数据结构
# ═══════════════════════════════════════════════

@dataclass
class ConceptNode:
    """概念节点"""
    id: str                                    # 节点唯一标识
    name: str                                  # 概念名称
    wuxing: Optional[str] = None               # 五行属性（木/火/土/金/水）
    cognitive_depth: Optional[str] = None      # 认知深度（L1/L2/L3/L4）
    category: Optional[str] = None             # 所属领域/分类
    description: Optional[str] = None          # 概念描述
    level: int = 1                             # 层级深度
    attributes: Dict[str, Any] = field(default_factory=dict)  # 扩展属性


@dataclass
class RelationEdge:
    """关系边"""
    source_id: str                             # 源节点 ID
    target_id: str                             # 目标节点 ID
    relation_type: RelationType                # 关系类型
    weight: float = 1.0                        # 关系权重 (0~1)
    description: Optional[str] = None          # 关系描述
    is_directed: bool = True                   # 是否单向
    attributes: Dict[str, Any] = field(default_factory=dict)  # 扩展属性


@dataclass
class ConceptRelationGraph:
    """
    概念-关系图（结构提取器的输出）

    这是同态映射的"源域结构"——一个领域内概念之间的运算关系图。
    """
    domain: str                                # 领域名称
    nodes: List[ConceptNode] = field(default_factory=list)
    edges: List[RelationEdge] = field(default_factory=list)
    relation_types: List[str] = field(default_factory=list)  # 该域中存在的关系类型
    metadata: Dict[str, Any] = field(default_factory=dict)   # 领域元数据

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)

    def get_node_by_id(self, node_id: str) -> Optional[ConceptNode]:
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None

    def get_node_by_name(self, name: str) -> Optional[ConceptNode]:
        for n in self.nodes:
            if n.name == name:
                return n
        return None

    def get_edges_by_type(self, relation_type: RelationType) -> List[RelationEdge]:
        return [e for e in self.edges if e.relation_type == relation_type]

    def get_outgoing_edges(self, node_id: str) -> List[RelationEdge]:
        return [e for e in self.edges if e.source_id == node_id]

    def get_incoming_edges(self, node_id: str) -> List[RelationEdge]:
        return [e for e in self.edges if e.target_id == node_id]

    def get_sheng_edges(self) -> List[RelationEdge]:
        return self.get_edges_by_type(RelationType.SHENG)

    def get_ke_edges(self) -> List[RelationEdge]:
        return self.get_edges_by_type(RelationType.KE)

    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "nodes": [asdict(n) for n in self.nodes],
            "edges": [asdict(e) for e in self.edges],
            "relation_types": self.relation_types,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "metadata": self.metadata,
        }


@dataclass
class NodeMapping:
    """节点映射对"""
    source_node_id: str                        # 旧域节点 ID
    source_node_name: str                      # 旧域节点名
    target_node_id: str                        # 新域节点 ID
    target_node_name: str                      # 新域节点名
    confidence: float = 0.0                    # 映射信度 (0~1)
    rationale: Optional[str] = None            # 映射理由


@dataclass
class HomomorphismCandidate:
    """
    同态候选映射（同态匹配器的输出）

    包含旧域→新域的节点映射和关系保持度评分。
    """
    source_domain: str                         # 源域名称
    target_domain: str                         # 目标域名称
    source_graph: ConceptRelationGraph         # 源域结构图
    mappings: List[NodeMapping] = field(default_factory=list)
    relation_preservation_score: float = 0.0   # 整体关系保持度 (0~1)
    confidence_level: ConfidenceLevel = ConfidenceLevel.LOW
    unmatched_source_nodes: List[str] = field(default_factory=list)  # 找不到映射的源节点
    unmatched_target_nodes: List[str] = field(default_factory=list)  # 未匹配的新域节点
    suggested_verification_scenarios: int = 3  # 建议验证场景数
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def mapping_count(self) -> int:
        return len(self.mappings)

    @property
    def coverage(self) -> float:
        """源域节点覆盖率"""
        total = self.source_graph.node_count
        if total == 0:
            return 0.0
        return len(self.mappings) / total

    def classify_confidence(self) -> ConfidenceLevel:
        """根据评分确定信度等级"""
        if self.relation_preservation_score >= 0.7:
            return ConfidenceLevel.HIGH
        elif self.relation_preservation_score >= 0.4:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.LOW

    def get_verification_scenario_count(self) -> int:
        """根据信度确定验证场景数"""
        level = self.classify_confidence()
        if level == ConfidenceLevel.HIGH:
            return 3
        elif level == ConfidenceLevel.MEDIUM:
            return 5
        return 0  # 不强配

    def to_dict(self) -> dict:
        return {
            "source_domain": self.source_domain,
            "target_domain": self.target_domain,
            "mappings": [asdict(m) for m in self.mappings],
            "relation_preservation_score": self.relation_preservation_score,
            "confidence_level": self.classify_confidence().value,
            "unmatched_source_nodes": self.unmatched_source_nodes,
            "unmatched_target_nodes": self.unmatched_target_nodes,
            "suggested_verification_scenarios": self.get_verification_scenario_count(),
            "coverage": self.coverage,
            "mapping_count": self.mapping_count,
            "metadata": self.metadata,
        }


@dataclass
class ScenarioResult:
    """单个场景的验证结果"""
    scenario_description: str                  # 场景描述
    relations_held: int                        # 保持的关系数
    total_relations: int                       # 总关系数
    passed: bool                               # 是否通过
    failed_relations: List[Dict[str, str]] = field(default_factory=list)  # 失败的关系详情
    notes: Optional[str] = None


@dataclass
class VerificationResult:
    """
    迁移验证结果（迁移验证器的输出）
    """
    mapping_id: str                            # 候选映射 ID
    source_domain: str
    target_domain: str
    scenarios_tested: int                      # 测试场景数
    scenario_results: List[ScenarioResult] = field(default_factory=list)
    overall_pass: bool = False
    verified_mappings: List[NodeMapping] = field(default_factory=list)
    failed_mappings: List[NodeMapping] = field(default_factory=list)
    relation_preservation_rate: float = 0.0    # 关系保持率
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def pass_rate(self) -> float:
        if self.scenarios_tested == 0:
            return 0.0
        return sum(1 for s in self.scenario_results if s.passed) / self.scenarios_tested

    def to_dict(self) -> dict:
        return {
            "mapping_id": self.mapping_id,
            "source_domain": self.source_domain,
            "target_domain": self.target_domain,
            "scenarios_tested": self.scenarios_tested,
            "scenario_results": [asdict(s) for s in self.scenario_results],
            "overall_pass": self.overall_pass,
            "verified_mappings": [asdict(m) for m in self.verified_mappings],
            "failed_mappings": [asdict(m) for m in self.failed_mappings],
            "relation_preservation_rate": self.relation_preservation_rate,
            "pass_rate": self.pass_rate,
            "metadata": self.metadata,
        }


@dataclass
class DeviationRecord:
    """
    SAD 镜鉴偏差记录

    当验证失败时，记录"自以为同态但实际不同态"的偏差。
    对应第四步唯识纠正：标准在结构本身，不在识别者。
    """
    record_id: str
    timestamp: str
    source_domain: str
    target_domain: str
    attempted_mapping: str                    # 尝试的映射描述
    expected_relation: str                    # 期望保持的关系
    actual_result: str                        # 实际结果
    root_cause: str                           # 根因分析
    lesson: str                               # 教训
    wuxing_implication: Optional[str] = None  # 五行启示
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


# ═══════════════════════════════════════════════
# 信度出口辅助函数
# ═══════════════════════════════════════════════

CONFIDENCE_THRESHOLD_HIGH = 0.7
CONFIDENCE_THRESHOLD_MEDIUM = 0.4


def classify_confidence(score: float) -> ConfidenceLevel:
    """信度出口三档分类"""
    if score >= CONFIDENCE_THRESHOLD_HIGH:
        return ConfidenceLevel.HIGH
    elif score >= CONFIDENCE_THRESHOLD_MEDIUM:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.LOW


def get_verification_count(score: float) -> int:
    """根据信度返回验证场景数"""
    level = classify_confidence(score)
    if level == ConfidenceLevel.HIGH:
        return 3
    elif level == ConfidenceLevel.MEDIUM:
        return 5
    return 0


def confidence_decision(score: float) -> dict:
    """
    信度出口决策

    Returns:
        {"action": "verify"|"verify_extra"|"no_match", "scenarios": int, "message": str}
    """
    level = classify_confidence(score)
    if level == ConfidenceLevel.HIGH:
        return {
            "action": "verify",
            "scenarios": 3,
            "message": f"高信度 (score={score:.2f} ≥ 0.7)，进入 Step 3 验证"
        }
    elif level == ConfidenceLevel.MEDIUM:
        return {
            "action": "verify_extra",
            "scenarios": 5,
            "message": f"低信度 (0.4 ≤ {score:.2f} < 0.7)，标注'低信度候选'，验证场景增至 5 个"
        }
    else:
        return {
            "action": "no_match",
            "scenarios": 0,
            "message": f"极低信度 ({score:.2f} < 0.4)，输出'暂未发现同态'，不强配（不假装精确）"
        }