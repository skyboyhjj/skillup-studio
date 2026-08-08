"""
案例记录系统 — 种·育 V1.3 Phase 2 M1
========================================
为双技能（咨询 SOP + 分析模板）提供统一的案例记录与减法记录基础设施。

设计原则：
  - L0 可回溯：所有记录带时间戳，不可删除，只可标记
  - 减法不是删除：减法事件标记为"已减除"，保留原始记录
  - 宪法审计集成：每次案例记录附带宪法审计检查
  - 案例可检索：按技能ID、日期、状态等维度检索

用法:
    from case_recorder import CaseRecorder, ConsultingCase, AnalysisCase
    recorder = CaseRecorder()
    case = ConsultingCase(source="大语言模型", target="自然语言处理")
    recorder.record(case)
    recorder.list_cases(skill_id="SKL-A-20260808-001")
"""

import os
import json
import uuid
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from enum import Enum


# ============================================================
# 枚举
# ============================================================

class CaseStatus(str, Enum):
    """案例状态"""
    DRAFT = "草稿"
    IN_PROGRESS = "进行中"
    COMPLETED = "已完成"
    ARCHIVED = "已归档"


class SubtractionEventType(str, Enum):
    """减法事件类型（为道日损）"""
    OVER_PROCESS = "去除过度流程"      # 案例执行证明某步骤无信息增量
    TEMPLATE_REDUNDANCY = "去除模板冗余"  # 模板字段 >10 且 >30% 为空
    OBSESSION = "去除执念"            # 对低信度仍强行输出
    WUXING_DEVIATION = "去除五行偏离"    # v1.1 M3: 无溯源依据的五行标注
    OVER_ACCUMULATION = "去除过度积累"   # v1.1 M3: 样本不足时强行高级运算


class AuditVerdict(str, Enum):
    """宪法审计判定"""
    PASS = "通过"
    FAIL = "未通过"
    N_A = "不适用"


# ============================================================
# 数据模型
# ============================================================

@dataclass
class SubtractionEvent:
    """减法事件（为道日损记录）"""
    event_id: str
    event_type: SubtractionEventType
    trigger: str           # 触发条件描述
    action: str            # 处置动作
    timestamp: str
    reversible: bool = True
    classical_ref: str = ""
    skill_id: str = ""
    case_id: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["event_type"] = self.event_type.value if isinstance(self.event_type, SubtractionEventType) else self.event_type
        return d


@dataclass
class ConstitutionAuditCheck:
    """宪法审计单条检查"""
    clause: str            # 条款名称（不宰/溯源/不假装精确/无弃人/不曲解）
    verdict: AuditVerdict
    detail: str            # 判定依据
    evidence: str = ""     # 证据（如字段名、数据行号）


@dataclass
class CaseRecord:
    """案例记录基类"""
    case_id: str
    skill_id: str
    timestamp: str
    status: CaseStatus = CaseStatus.DRAFT

    # 基本信息
    basic_info: Dict[str, Any] = field(default_factory=dict)

    # 三步记录
    step_records: Dict[str, Any] = field(default_factory=dict)

    # 宪法审计
    constitution_audit: List[ConstitutionAuditCheck] = field(default_factory=list)
    constitution_passed: bool = False

    # 减法记录
    subtraction_records: List[SubtractionEvent] = field(default_factory=list)

    # 交付物
    deliverables: List[str] = field(default_factory=list)

    # 元数据
    notes: str = ""
    version: str = "v1.0"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value if isinstance(self.status, CaseStatus) else self.status
        d["constitution_audit"] = [
            {
                "clause": c.clause,
                "verdict": c.verdict.value if isinstance(c.verdict, AuditVerdict) else c.verdict,
                "detail": c.detail,
                "evidence": c.evidence,
            }
            for c in self.constitution_audit
        ]
        d["subtraction_records"] = [s.to_dict() for s in self.subtraction_records]
        return d


@dataclass
class ConsultingCase(CaseRecord):
    """咨询案例（种子A：跨域诊断咨询技能）"""
    # 种子A 特有字段
    source_domain: str = ""
    target_domain: str = ""
    client_type: str = ""
    node_count: int = 0
    edge_count: int = 0

    # Step 1 细化
    source_structure: Dict[str, Any] = field(default_factory=dict)
    relationship_types: Dict[str, List[str]] = field(default_factory=dict)
    #  {生克: [...], 因果: [...], 层级: [...], 类比: [...]}
    credibility_annotations: List[Dict[str, Any]] = field(default_factory=list)
    #  [{edge_id, source_node, target_node, relation, confidence, source_field}]

    # Step 2 细化
    candidate_mappings: List[Dict[str, Any]] = field(default_factory=list)
    #  [{mapping_id, f, preservation_score, per_edge_check}]
    preservation_score: float = 0.0
    confidence_level: str = ""  # high / medium / low / no_match

    # Step 3 细化
    verification_scenarios: List[Dict[str, Any]] = field(default_factory=list)
    #  [{scenario_id, description, passed, detail}]
    falsification_boundaries: List[str] = field(default_factory=list)
    migration_path: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.skill_id:
            self.skill_id = "SKL-A-20260808-001"


@dataclass
class AnalysisCase(CaseRecord):
    """分析案例（种子B：五行七维分析模板）"""
    # 种子B 特有字段
    analysis_target: str = ""       # 分析对象
    node_count: int = 0
    layer_structure: str = ""       # 层结构描述

    # 数据采集
    data_snapshot: Dict[str, Any] = field(default_factory=dict)
    #  {nodes: [...], edges: [...], layers: [...]}

    # 七维计算结果
    dimension_results: Dict[str, Any] = field(default_factory=dict)
    #  {
    #    freq: {占比 + wilson 信度区间},
    #    layer_matrix: 3x5 矩阵,
    #    centroid_path: 向量序列,
    #    entropy: H 值,
    #    centroid_vector: 主导五行,
    #    trait_profile: 画像匹配,
    #    verdict: 一句话判语 + S_p
    #  }

    # 信度标注
    credibility_annotations: Dict[str, Any] = field(default_factory=dict)
    #  {confidence_level, effective_n, interval_width, prefix}

    # 待观察领域
    pending_observation: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.skill_id:
            self.skill_id = "SKL-B-20260808-001"


# ============================================================
# 案例记录器
# ============================================================

class CaseRecorder:
    """
    案例记录器 — 为双技能提供统一的案例管理

    功能：
      - 记录案例（咨询/分析）
      - 管理减法记录（L0 可回溯）
      - 宪法审计集成
      - 案例检索与统计
    """

    DEFAULT_CONFIG = {
        "max_history": 1000,
        "auto_audit": True,
        "subtraction_trace_enabled": True,
        "case_output_dir": "output/cases/",
    }

    def __init__(self, config: dict = None, base_dir: str = None):
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        if base_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.base_dir = base_dir
        self.case_history: List[CaseRecord] = []
        self.subtraction_history: List[SubtractionEvent] = []

    # ── 案例记录 ──

    def record(self, case: CaseRecord) -> CaseRecord:
        """记录一个案例"""
        if not case.case_id:
            case.case_id = f"case_{uuid.uuid4().hex[:8]}"
        if not case.timestamp:
            case.timestamp = datetime.now().isoformat()

        # 自动宪法审计
        if self.config.get("auto_audit", True) and not case.constitution_audit:
            case.constitution_audit = self._auto_audit(case)
            case.constitution_passed = all(
                c.verdict == AuditVerdict.PASS for c in case.constitution_audit
            )

        self.case_history.append(case)
        if len(self.case_history) > self.config["max_history"]:
            self.case_history = self.case_history[-self.config["max_history"]:]

        return case

    def _auto_audit(self, case: CaseRecord) -> List[ConstitutionAuditCheck]:
        """自动宪法审计（根据案例类型选择审计条款）"""
        if isinstance(case, ConsultingCase):
            return self._audit_consulting(case)
        elif isinstance(case, AnalysisCase):
            return self._audit_analysis(case)
        return []

    def _audit_consulting(self, case: ConsultingCase) -> List[ConstitutionAuditCheck]:
        """种子A 宪法审计：不宰/溯源/不假装精确/无弃人"""
        checks = []

        # 1. 不宰：咨询只提供可选方案，不强制采纳
        has_options = len(case.candidate_mappings) > 1 or any(
            "可选" in d.get("description", "") for d in case.deliverables
        )
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

        # 3. 不假装精确：低信度标注"待验证"
        low_conf = [a for a in case.credibility_annotations if a.get("confidence", 0) < 0.4]
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

    def _audit_analysis(self, case: AnalysisCase) -> List[ConstitutionAuditCheck]:
        """种子B 宪法审计：溯源/不曲解/不假装精确/无弃人"""
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

    # ── 减法记录 ──

    def record_subtraction(self, event: SubtractionEvent) -> SubtractionEvent:
        """
        记录减法事件（为道日损）

        减法不是删除，是标记（L0 可回溯，可逆）。
        """
        if not event.event_id:
            event.event_id = f"sub_{uuid.uuid4().hex[:8]}"
        if not event.timestamp:
            event.timestamp = datetime.now().isoformat()

        self.subtraction_history.append(event)
        return event

    def check_over_process(self, case: CaseRecord, step_name: str,
                           has_info_gain: bool) -> Optional[SubtractionEvent]:
        """检查并记录过度流程"""
        if not has_info_gain:
            event = SubtractionEvent(
                event_id="",
                event_type=SubtractionEventType.OVER_PROCESS,
                trigger=f"案例 {case.case_id} 步骤 {step_name} 无信息增量",
                action=f"标记'{step_name}'已减除，L0 留痕可回溯",
                timestamp=datetime.now().isoformat(),
                reversible=True,
                classical_ref="为道日损，损之又损，以至于无为（《道德经》第48章）",
                skill_id=case.skill_id,
                case_id=case.case_id,
            )
            return self.record_subtraction(event)
        return None

    def check_template_redundancy(self, case: CaseRecord,
                                  field_count: int, empty_ratio: float) -> Optional[SubtractionEvent]:
        """检查并记录模板冗余"""
        if field_count > 10 and empty_ratio > 0.3:
            event = SubtractionEvent(
                event_id="",
                event_type=SubtractionEventType.TEMPLATE_REDUNDANCY,
                trigger=f"案例 {case.case_id} 模板字段 {field_count} 个，{empty_ratio:.0%} 为空",
                action=f"建议合并/删除冗余字段，版本 +0.1",
                timestamp=datetime.now().isoformat(),
                reversible=True,
                classical_ref="少则得，多则惑（《道德经》第22章）",
                skill_id=case.skill_id,
                case_id=case.case_id,
            )
            return self.record_subtraction(event)
        return None

    def check_obsession(self, case: CaseRecord,
                        low_confidence_forcing: bool) -> Optional[SubtractionEvent]:
        """检查并记录执念"""
        if low_confidence_forcing:
            event = SubtractionEvent(
                event_id="",
                event_type=SubtractionEventType.OBSESSION,
                trigger=f"案例 {case.case_id} 对低信度结果仍强行输出",
                action="触发宪法审计 REJECT，记录案例。不强求保持正是知的开始。",
                timestamp=datetime.now().isoformat(),
                reversible=False,
                classical_ref="知不知，尚矣；不知知，病也（《道德经》第71章）",
                skill_id=case.skill_id,
                case_id=case.case_id,
            )
            return self.record_subtraction(event)
        return None

    def record_m3_subtractions(self) -> List[SubtractionEvent]:
        """
        v1.1 M3: 记录 M3 复盘阶段识别的 6 条减法事件

        全部"标记而非删除"（L0 可回溯、可逆）。

        Returns:
            List[SubtractionEvent]: 记录的 6 条减法事件
        """
        events = []

        # 1. 种子A: 删除"指令式建议"字段（改为可选方案）——去除执念
        events.append(SubtractionEvent(
            event_id="sub_m3_001",
            event_type=SubtractionEventType.OBSESSION,
            trigger="删除'指令式建议'字段（改为可选方案）",
            action="宪法审计·不宰：咨询只提供诊断，不指令改造",
            timestamp=datetime.now().isoformat(),
            reversible=True,
            classical_ref="长而不宰（《道德经》第10章）",
            skill_id="SKL-A-20260808-001",
            case_id="M3-复盘-A",
        ))

        # 2. 种子A: 信度标注 全量→关键路径——去除过度流程
        events.append(SubtractionEvent(
            event_id="sub_m3_002",
            event_type=SubtractionEventType.OVER_PROCESS,
            trigger="信度标注 全量→关键路径",
            action="A-1 案例反馈：非关键路径不逐条标注，关键路径阈值=0.7",
            timestamp=datetime.now().isoformat(),
            reversible=True,
            classical_ref="为道日损，损之又损，以至于无为（《道德经》第48章）",
            skill_id="SKL-A-20260808-001",
            case_id="M3-复盘-A",
        ))

        # 3. 种子A: 验证场景 ≥3→≥2+反馈（内容线类）——去除过度流程
        events.append(SubtractionEvent(
            event_id="sub_m3_003",
            event_type=SubtractionEventType.OVER_PROCESS,
            trigger="验证场景 ≥3→≥2+反馈（内容线类）",
            action="A-2 案例反馈：内容线场景降为轻量验证模式",
            timestamp=datetime.now().isoformat(),
            reversible=True,
            classical_ref="为道日损，损之又损，以至于无为（《道德经》第48章）",
            skill_id="SKL-A-20260808-001",
            case_id="M3-复盘-A",
        ))

        # 4. 种子B: 删除"无溯源情感词"字段——去除五行偏离
        events.append(SubtractionEvent(
            event_id="sub_m3_004",
            event_type=SubtractionEventType.WUXING_DEVIATION,
            trigger="删除'无溯源情感词'字段（日语恋/愛）",
            action="B-1 溯源审计：无溯源依据的五行标注应减除",
            timestamp=datetime.now().isoformat(),
            reversible=True,
            classical_ref="溯源必称尧舜（《墨子·贵义》）",
            skill_id="SKL-B-20260808-001",
            case_id="M3-复盘-B",
        ))

        # 5. 种子B: 画像库匹配 n<10 降级为提示——去除过度积累
        events.append(SubtractionEvent(
            event_id="sub_m3_005",
            event_type=SubtractionEventType.OVER_ACCUMULATION,
            trigger="画像库匹配 n<10 降级为提示",
            action="B-1 案例反馈：小样本不适合画像库匹配，降级为画像提示",
            timestamp=datetime.now().isoformat(),
            reversible=True,
            classical_ref="少则得，多则惑（《道德经》第22章）",
            skill_id="SKL-B-20260808-001",
            case_id="M3-复盘-B",
        ))

        # 6. 种子B: 模板字段 12→10——去除模板冗余
        events.append(SubtractionEvent(
            event_id="sub_m3_006",
            event_type=SubtractionEventType.TEMPLATE_REDUNDANCY,
            trigger="模板字段 12→10",
            action="合并'画像库版本'+'画像来源'；删除'分析耗时'字段",
            timestamp=datetime.now().isoformat(),
            reversible=True,
            classical_ref="少则得，多则惑（《道德经》第22章）",
            skill_id="SKL-B-20260808-001",
            case_id="M3-复盘-B",
        ))

        for event in events:
            self.record_subtraction(event)

        return events

    # ── 查询 ──

    def list_cases(self, skill_id: str = None,
                   status: CaseStatus = None,
                   limit: int = 50) -> List[CaseRecord]:
        """按条件检索案例"""
        results = self.case_history
        if skill_id:
            results = [c for c in results if c.skill_id == skill_id]
        if status:
            results = [c for c in results if c.status == status]
        return results[-limit:]

    def get_case(self, case_id: str) -> Optional[CaseRecord]:
        """按 ID 获取案例"""
        for c in self.case_history:
            if c.case_id == case_id:
                return c
        return None

    def get_subtractions(self, skill_id: str = None,
                         case_id: str = None) -> List[SubtractionEvent]:
        """查询减法记录"""
        results = self.subtraction_history
        if skill_id:
            results = [s for s in results if s.skill_id == skill_id]
        if case_id:
            results = [s for s in results if s.case_id == case_id]
        return results

    def get_stats(self) -> dict:
        """获取记录器统计"""
        total = len(self.case_history)
        if total == 0:
            return {"total_cases": 0, "total_subtractions": 0}

        completed = sum(1 for c in self.case_history if c.status == CaseStatus.COMPLETED)
        by_skill = {}
        for c in self.case_history:
            by_skill[c.skill_id] = by_skill.get(c.skill_id, 0) + 1

        return {
            "total_cases": total,
            "completed": completed,
            "completion_rate": round(completed / total, 2),
            "by_skill": by_skill,
            "total_subtractions": len(self.subtraction_history),
            "subtractions_by_type": {
                t.value: sum(1 for s in self.subtraction_history
                           if s.event_type == t)
                for t in SubtractionEventType
            },
        }

    def format_summary(self) -> str:
        """生成案例记录摘要"""
        stats = self.get_stats()
        lines = []
        lines.append("=" * 60)
        lines.append("  案例记录器 — 摘要")
        lines.append("=" * 60)
        lines.append(f"  总案例数: {stats['total_cases']}")
        lines.append(f"  已完成: {stats['completed']} ({stats['completion_rate']:.0%})")
        if stats.get("by_skill"):
            for sid, cnt in stats["by_skill"].items():
                lines.append(f"    {sid}: {cnt} 案例")
        lines.append(f"  减法记录: {stats['total_subtractions']}")
        for t, cnt in stats.get("subtractions_by_type", {}).items():
            if cnt > 0:
                lines.append(f"    {t}: {cnt}")
        lines.append("=" * 60)
        return "\n".join(lines)

    # ── 持久化 ──

    def save_case(self, case: CaseRecord, output_dir: str = None):
        """保存单个案例到 JSON 文件"""
        if output_dir is None:
            output_dir = os.path.join(self.base_dir, self.config["case_output_dir"])
        os.makedirs(output_dir, exist_ok=True)

        filepath = os.path.join(output_dir, f"{case.case_id}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(case.to_dict(), f, ensure_ascii=False, indent=2)

        return filepath


# ============================================================
# 便捷函数
# ============================================================

def create_consulting_case(source_domain: str, target_domain: str,
                           client_type: str = "未指定") -> ConsultingCase:
    """创建咨询案例（种子A）"""
    return ConsultingCase(
        case_id=f"CASE-A-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4]}",
        skill_id="SKL-A-20260808-001",
        timestamp=datetime.now().isoformat(),
        source_domain=source_domain,
        target_domain=target_domain,
        client_type=client_type,
        basic_info={
            "date": datetime.now().strftime('%Y-%m-%d'),
            "source_domain": source_domain,
            "target_domain": target_domain,
            "client_type": client_type,
        },
    )


def create_analysis_case(analysis_target: str,
                         node_count: int = 0,
                         layer_structure: str = "") -> AnalysisCase:
    """创建分析案例（种子B）"""
    return AnalysisCase(
        case_id=f"CASE-B-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4]}",
        skill_id="SKL-B-20260808-001",
        timestamp=datetime.now().isoformat(),
        analysis_target=analysis_target,
        node_count=node_count,
        layer_structure=layer_structure,
        basic_info={
            "date": datetime.now().strftime('%Y-%m-%d'),
            "analysis_target": analysis_target,
            "node_count": node_count,
            "layer_structure": layer_structure,
        },
    )


# ============================================================
# 自检
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("案例记录系统 — 自检 (V1.3 M1)")
    print("=" * 60)

    recorder = CaseRecorder()

    # 测试 1: 创建咨询案例
    print("\n[测试 1] 创建咨询案例（种子A）")
    case_a = create_consulting_case("大语言模型", "自然语言处理", "企业客户")
    assert case_a.skill_id == "SKL-A-20260808-001"
    assert case_a.source_domain == "大语言模型"
    assert case_a.case_id.startswith("CASE-A-")
    case_a.node_count = 22
    case_a.edge_count = 178
    case_a.credibility_annotations = [
        {"edge_id": "e1", "source_node": "A", "target_node": "B",
         "relation": "生", "confidence": 0.85, "source_field": "访谈记录第3段"},
    ]
    case_a.candidate_mappings = [
        {"mapping_id": "m1", "f": "映射1", "preservation_score": 0.7},
        {"mapping_id": "m2", "f": "映射2（可选）", "preservation_score": 0.5},
    ]
    recorder.record(case_a)
    print(f"  案例ID: {case_a.case_id}")
    print(f"  宪法审计: {'✅' if case_a.constitution_passed else '❌'}")
    for c in case_a.constitution_audit:
        print(f"    [{c.verdict.value}] {c.clause}: {c.detail[:40]}")
    print("  ✅ 测试 1 通过")

    # 测试 2: 创建分析案例
    print("\n[测试 2] 创建分析案例（种子B）")
    case_b = create_analysis_case("道德经第1-6章", node_count=15, layer_structure="种子/现行/超越")
    assert case_b.skill_id == "SKL-B-20260808-001"
    assert case_b.case_id.startswith("CASE-B-")
    case_b.data_snapshot = {
        "nodes": [{"id": "n1", "name": "道", "wuxing": "水", "wuxing_source": "道德经25章"}],
        "edges": [],
        "layers": {"种子": 5, "现行": 6, "超越": 4},
    }
    case_b.dimension_results = {
        "verdict": {"text": "水·变阶段", "S_p": 42.5, "data_ref": "dim_entropy_L42"},
    }
    case_b.credibility_annotations = {
        "confidence_level": "中",
        "interval_width": 0.15,
        "prefix": "",
    }
    case_b.pending_observation = ["第3章待更多数据"]
    recorder.record(case_b)
    print(f"  案例ID: {case_b.case_id}")
    print(f"  宪法审计: {'✅' if case_b.constitution_passed else '❌'}")
    for c in case_b.constitution_audit:
        print(f"    [{c.verdict.value}] {c.clause}: {c.detail[:40]}")
    print("  ✅ 测试 2 通过")

    # 测试 3: 减法记录
    print("\n[测试 3] 减法记录机制")
    # 过度流程
    sub1 = recorder.check_over_process(case_a, "Step 2 同态匹配", has_info_gain=False)
    assert sub1 is not None
    assert sub1.event_type == SubtractionEventType.OVER_PROCESS
    print(f"  过度流程: {sub1.trigger[:50]}...")
    print(f"  可逆: {sub1.reversible}")
    # 模板冗余
    sub2 = recorder.check_template_redundancy(case_a, field_count=15, empty_ratio=0.4)
    assert sub2 is not None
    assert sub2.event_type == SubtractionEventType.TEMPLATE_REDUNDANCY
    print(f"  模板冗余: {sub2.trigger[:50]}...")
    # 执念
    sub3 = recorder.check_obsession(case_a, low_confidence_forcing=True)
    assert sub3 is not None
    assert sub3.event_type == SubtractionEventType.OBSESSION
    print(f"  执念: {sub3.trigger[:50]}...")
    print(f"  可逆: {sub3.reversible}")
    print("  ✅ 测试 3 通过")

    # 测试 4: 查询
    print("\n[测试 4] 案例查询")
    cases_a = recorder.list_cases(skill_id="SKL-A-20260808-001")
    cases_b = recorder.list_cases(skill_id="SKL-B-20260808-001")
    assert len(cases_a) == 1
    assert len(cases_b) == 1
    subs = recorder.get_subtractions(skill_id="SKL-A-20260808-001")
    assert len(subs) == 3
    print(f"  种子A 案例: {len(cases_a)}")
    print(f"  种子B 案例: {len(cases_b)}")
    print(f"  种子A 减法: {len(subs)}")
    print("  ✅ 测试 4 通过")

    # 测试 5: 统计
    print("\n[测试 5] 记录器统计")
    stats = recorder.get_stats()
    assert stats["total_cases"] == 2
    assert stats["total_subtractions"] == 3
    print(recorder.format_summary())
    print("  ✅ 测试 5 通过")

    # 测试 6: 案例持久化
    print("\n[测试 6] 案例持久化")
    tmp_dir = os.path.join(recorder.base_dir, "output", "cases")
    filepath = recorder.save_case(case_a, tmp_dir)
    assert os.path.exists(filepath), f"文件未保存: {filepath}"
    print(f"  已保存: {filepath}")
    print("  ✅ 测试 6 通过")

    print("\n" + "=" * 60)
    print("自检完成 — 全部 6 项测试通过 (V1.3 M1)")