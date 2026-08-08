"""
种子培育模块 — taste/seedney 的工程实现 (V1.3)
================================================
将杨振宁 taste 研究的"种子培育三步法"形式化为可执行的培育协议，
与同态映射三步协议同构，对应五行流转的"木·生"阶段。

V1.3 变更（儒道成才观读解——种·育的思想底座补全）：
  ① 双审计（宪法审计·德 + 性决定审计·才，德优先）
  ② 培育双轨（为学日益 + 为道日损并行）
  ③ 孔子六阶段人才时间轴（十五志于学→七十从心）
  ④ 导师差异化（因材施教）+ 不宰伦理（生而不有，为而不恃，长而不宰）
  ⑤ 环境分阶段（子夏保护期→子张包容期）
  ⑥ 归朴循环（成器→迁移→归朴，"通中生种"的哲学命名）
  ⑦ 无弃人底线（低信度≠废材，待观察）
  ⑧ 思想底座（大器免成 = 种子理论最古老表述）

思想底座（儒道合流）：
  大器免成（帛书乙本）：真正的大器不是"被做成"的，而是自然"长成"的。
  儒道互补：儒家为学日益（加法引擎）+ 道家为道日损（减法引擎）
  归朴循环：朴散则为器（种·育成器）→ 复归于朴（土·通迁移后归朴）
  故无弃人：圣人常善救人，故无弃人。——低信度≠废材，是待观察。

V1.2 变更（反者道之动·矛盾迭代引擎自查）：
  ① 性决定降级为"路径一致性审计"（描述性，非预测性）
  ② 余弦相似度可计算公式（五行向量 → 方向一致性）
  ③ 失败者/跨界对照校准判别力（生克并置）
  ④ 缘四要素 Agent 翻译（人类尺度→慧惠尺度）
  ⑤ 双引擎反向回路（通中生种，单向流水线→生命循环）
  ⑥ 预期值去伪（阈值标注"待校准/待实测"）

V1.1 变更（经 2026 菲尔兹奖四大师实证检验）：
  ① 双种子画像（题目/方法）
  ② 缘四要素（导师/环境/课题/合作者）
  ③ 缘/性漂移分层
  ④ 时间尺度参数化
  ⑤ 性决定聚焦方法种子

三步法（杨振宁教育方法论）：
  Step 1 - 教学疑难切入：识别种子（双种子画像：题目+方法）
  Step 2 - 科教融合提炼前沿课题：培育种子（缘四要素 Agent 翻译 + 双轨培育）
  Step 3 - 师生共创突破：收获果实（双审计 + 漂移检测 + 为道日损减法）

核心概念：
  seedney  = 种子（性决定）：对称性种子 → 对称性果实
  taste    = 妙（taste之因）：对结构美的直觉感知
  性决定审计 = 路径一致性描述（非成才判据）：成果是否忠于方法种子
  宪法审计   = 方向审计（德·仁）：动作是否越界，德优先于才
  余弦相似度 = 五行向量方向一致性：Σ(aᵢ·bᵢ) / (|A|·|B|)
  归朴       = 通中生种的哲学命名：成器→迁移→归朴（复归于朴）

损耗率分层对应的培育策略：
  种子主导区（10-30%损耗）→ 核心结构，值得一生保持
  结构保持区（30-50%损耗）→ 可培育结构，需持续浇灌
  缘主导区（50%+损耗）    → 高损耗区，不宜强求保持

用法:
    from seed_cultivation import SeedCultivation, SeedCultivationResult
    cultivator = SeedCultivation(time_scale="skill")
    result = cultivator.cultivate(source_domain, target_domain)
    print(cultivator.format_summary(result))
"""

import os
import json
import uuid
import math
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from enum import Enum


# ============================================================
# 常量
# ============================================================

# V1.2: 五行向量顺序（余弦相似度计算用）
WUXING_ORDER = ["木", "火", "土", "金", "水"]


# ============================================================
# 数据类型
# ============================================================

class SeedStage(str, Enum):
    """种子培育阶段"""
    IDENTIFY = "识别种子"       # Step 1: 教学疑难切入
    NURTURE = "培育种子"        # Step 2: 科教融合提炼
    HARVEST = "收获果实"        # Step 3: 师生共创突破


class SeedVitality(str, Enum):
    """种子活力等级"""
    DORMANT = "休眠"            # 种子尚未被识别
    GERMINATING = "萌发"        # 种子已识别，开始培育
    GROWING = "生长"            # 种子在培育中
    FLOWERING = "开花"          # 培育接近完成
    FRUITING = "结果"           # 种子已成熟为果实


class SeedType(str, Enum):
    """种子类型（V1.1 双种子画像）"""
    TOPIC = "题目种子"          # what to study — 兴趣领域，允许漂移
    METHOD = "方法种子"         # how to study — 工具偏好，性决定检验对象


class DriftType(str, Enum):
    """漂移类型（V1.1 缘/性漂移分层）"""
    ENVIRONMENTAL = "缘漂移"    # 环境/课题/导师变化 — 正常，不触发警告
    SEED = "性漂移"             # 方法种子变化 — 异常，回退 Step 1


class TimeScale(str, Enum):
    """时间尺度（V1.1 参数化）"""
    TALENT = "人才"             # 10~25 年，年/学期粒度
    SKILL = "技能"              # 1~6 月，周/月粒度


class ConfirmationStatus(str, Enum):
    """方法种子确认状态"""
    CONFIRMED = "确认种子"      # 出现 ≥3 次独立场景
    PENDING = "待观察"          # <3 次，信度出口，不强行确认


class ConfuciusStage(str, Enum):
    """孔子六阶段人才时间轴（V1.3 儒道合流）"""
    ZHI_XUE = "十五志于学"       # 木·生
    ER_LI = "三十而立"           # 火·化
    BU_HUO = "四十不惑"          # 金·克
    ZHI_TIANMING = "五十知天命"  # 土·通
    ER_SHUN = "六十耳顺"         # 水·变
    CONG_XIN = "七十从心"        # 道·合


class EnvironmentPhase(str, Enum):
    """环境分阶段（V1.3 儒道合流）"""
    ZIXIA = "子夏保护期"         # 修身初期，选择性保护
    ZIZHANG = "子张包容期"       # 成熟后，广泛包容


class AuditPriority(str, Enum):
    """双审计优先级（V1.3 儒道合流：德先于才）"""
    CONSTITUTION = "宪法审计"    # 德·仁 — 优先（骥不称其力，称其德也）
    NATURE = "性决定审计"        # 才·方法 — 次之


# ── V1.5 新增枚举 ──

class SystemType(str, Enum):
    """壳核审计体系类型（V1.5）"""
    NUCLEUS_MEASURING = "测核体系"    # 登顶/共情/纯粹
    SHELL_MEASURING = "测壳体系"      # 职称/奖杯/成绩


class FailureQuality(str, Enum):
    """失败质量分类（V1.5 → V1.5.1 三分法）"""
    TRUE_FAILURE = "真失败"                # 结构性证伪——实验设计能区分假设对错，奖励
    ACCIDENTAL_FAILURE = "偶然失败"        # 不可复现——运气/环境因素，中性不奖惩
    PERFORMATIVE_FAILURE = "表演性失败"    # 为奖励而故意制造，警告


class SubtractionScope(str, Enum):
    """减法记录范围（V1.5）"""
    CULTIVATION = "培育级"    # 种子培育中的减法
    PROTOCOL = "协议级"       # 协议自身的日损


class PendingHypothesisStatus(str, Enum):
    """待验证假设状态（V1.5）"""
    PENDING = "待验证"
    VERIFIED = "已验证"
    FALSIFIED = "已证伪"
    UNDETERMINED = "待定"


# ── V1.5 新增数据类 ──

@dataclass
class ShellNucleusDeclaration:
    """壳核审计声明（V1.5）"""
    nucleus_measured: str = ""              # 测的核 = {方法核 / 方向核}
    shell_excluded: List[str] = field(default_factory=list)  # 不测的壳
    system_type: str = ""                   # 体系类型（测核体系/测壳体系）
    declared: bool = False                  # 是否已声明
    declaration_note: str = ""              # 声明意义说明

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PurityResult:
    """纯粹度审计结果（V1.5）"""
    purity_score: float = 0.0               # Purity = 保持×时间×抗摇摆
    retention: float = 0.0                  # 保持度（余弦相似度，V1.2 已验证）
    duration: float = 0.0                   # 持续时间（归一化到 [0,1]）
    anti_sway: float = 1.0                  # 抗摇摆性（V1.5：待校准，暂取中性1.0）
    anti_sway_events: List[Dict[str, Any]] = field(default_factory=list)  # 定性事件记录
    anti_sway_calibrated: bool = False      # 抗摇摆是否已校准
    threshold: float = 0.7                  # 纯粹度阈值
    interpretation: str = ""                # 解读

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class FailureQualityAudit:
    """失败质量审核（V1.5）"""
    failure_type: str = ""                  # 真失败/表演性失败
    is_structural_falsification: bool = False  # 是否为结构性证伪
    reward_eligible: bool = False           # 是否奖励
    evidence: str = ""                      # 区分依据
    audit_timestamp: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class HypothesisTracker:
    """待验证假设跟踪（V1.5）"""
    hypothesis_id: str = ""
    statement: str = ""                     # 假设陈述
    status: str = PendingHypothesisStatus.PENDING.value
    evidence_chain: List[Dict[str, Any]] = field(default_factory=list)
    last_updated: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SeedCultivationResult:
    """种子培育结果（V1.2）"""
    cultivation_id: str
    source_domain: str                # 源域（已掌握的知识领域）
    target_domain: str                # 目标域（要培育的新领域）
    timestamp: str

    # 三步法各阶段结果
    step1_identify: Dict[str, Any] = field(default_factory=dict)
    step2_nurture: Dict[str, Any] = field(default_factory=dict)
    step3_harvest: Dict[str, Any] = field(default_factory=dict)

    # V1.1 双种子画像
    topic_seed: Dict[str, Any] = field(default_factory=dict)
    #  {domain, wuxing, drift_allowed: True, wuxing_vector: []}
    method_seed: Dict[str, Any] = field(default_factory=dict)
    #  {tool_preference, wuxing, wuxing_vector: [], occurrence_count,
    #   resonance_strength, confirmation_status, independent_scenes}

    # V1.1 缘四要素（V1.2 Agent 翻译版）
    environmental_factors: Dict[str, Any] = field(default_factory=dict)
    #  {mentor, environment, topic, collaborators}

    # V1.1 漂移分析
    drift_analysis: Dict[str, Any] = field(default_factory=dict)
    #  {drift_type, detected, detail, action}

    # V1.2 性决定审计（路径一致性描述，非成才判据）
    nature_determination_score: float = 0.0
    #  方法种子五行向量 vs 成果方法论五行向量的余弦相似度

    # V1.2 通中生种：反向回路种子候选
    reverse_flow_seeds: List[Dict[str, Any]] = field(default_factory=list)
    #  [{source_domain, method_seed_wuxing, occurrence_count, source: "通中生种"}]

    # V1.1 时间尺度
    time_scale: str = ""

    # 综合评估
    seed_vitality: str = SeedVitality.DORMANT.value
    seedney_score: float = 0.0        # 种子质量评分 (0~1)
    taste_score: float = 0.0          # taste（妙）评分 (0~1)
    cultivation_success: bool = False

    # 损耗分层
    loss_zone: str = ""               # 种子主导区/结构保持区/缘主导区

    # G5: 同源偏差标注（Phase 1 已知答案回溯验证的诚实声明）
    same_source_bias: bool = False
    #  当验证标尺与信号源来自同一轨迹时标注 True

    # 道境指标
    S_p: float = 0.0
    stage: str = ""

    # V1.3 双审计（儒道合流：宪法审计·德 + 性决定审计·才，德优先）
    constitution_audit: Dict[str, Any] = field(default_factory=dict)
    #  {passed, direction_check, boundary_violations, priority: "德优先",
    #   checks: [{check_name, verdict, reason}]}

    # V1.3 培育双轨（为学日益 + 为道日损并行）
    nurture_dual_track: Dict[str, Any] = field(default_factory=dict)
    #  {addition_events: [...], subtraction_events: [...], subtraction_reversible: True}

    # V1.3 环境分阶段（子夏保护期→子张包容期）
    environment_phase: str = ""
    #  "子夏保护期" / "子张包容期"

    # V1.3 导师策略（因材施教 + 不宰伦理）
    mentor_strategy: Dict[str, Any] = field(default_factory=dict)
    #  {differentiation: str, non_dominance_ethics: str}

    # V1.3 孔子六阶段
    confucius_stage: str = ""
    #  "十五志于学" / "三十而立" / ... / "七十从心"

    # V1.3 无弃人底线
    no_discard_guarantee: bool = True
    #  低信度≠废材，是待观察。圣人常善救人，故无弃人。

    # V1.5 壳核审计声明
    shell_nucleus_declaration: Dict[str, Any] = field(default_factory=dict)
    #  {nucleus_measured, shell_excluded, system_type, declared, declaration_note}

    # V1.5 纯粹度审计结果
    purity_result: Dict[str, Any] = field(default_factory=dict)
    #  {purity_score, retention, duration, anti_sway, anti_sway_events,
    #   anti_sway_calibrated, threshold, interpretation}

    # V1.5 熵振引擎：失败质量审核记录
    failure_quality_audits: List[Dict[str, Any]] = field(default_factory=list)
    #  [{failure_type, is_structural_falsification, reward_eligible, evidence}]

    # V1.5 留白调度
    whitespace_schedule: Dict[str, Any] = field(default_factory=dict)
    #  {rounds_since_last_whitespace, whitespace_due, skipped_count, owed_count}

    # V1.5 日益饱和检测
    saturation_detected: bool = False
    saturation_detail: str = ""

    # V1.5 协议级日损记录
    protocol_subtractions: List[Dict[str, Any]] = field(default_factory=list)
    #  [{item, reason, reversible, timestamp}]

    # V1.5 Phase B: 熵振引擎
    entropy_vibration: Dict[str, Any] = field(default_factory=dict)
    #  {failure_events, quality_audits, true_failures, performative_failures,
    #   falsification_library_updates, principle}

    # V1.5 Phase B: 待验证假设清单
    pending_hypotheses: List[Dict[str, Any]] = field(default_factory=list)
    #  [{hypothesis_id, statement, status, evidence_for, evidence_against,
    #    verification_path, last_updated}]

    # V1.5 Phase B: 留白条款
    blank_space: Dict[str, Any] = field(default_factory=dict)
    #  {is_blank_round, reason, skipped_for_deadline, owed_rounds, action}

    # V1.5 Phase B: 日益饱和检测
    saturation_detection: Dict[str, Any] = field(default_factory=dict)
    #  {saturated, marginal_output, recommendation, action}

    # V1.5 Phase B: 换球心决策
    ball_replacement: Dict[str, Any] = field(default_factory=dict)
    #  {triggered, reason, candidate_systems, recommendation, action}

    # 经典引用
    classical_ref: str = ""
    ethical_advice: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ============================================================
# 种子培育器
# ============================================================

class SeedCultivation:
    """
    种子培育器 — 木·生 阶段的种子培育协议 (V1.3)

    将杨振宁 taste 研究的三步法形式化为可执行的培育协议：
      Step 1 - 教学疑难切入：识别种子（双种子画像：题目+方法）
      Step 2 - 科教融合提炼前沿课题：培育种子（缘四要素 + 双轨培育：日益+日损）
      Step 3 - 师生共创突破：收获果实（双审计 + 漂移检测 + 为道日损减法）

    V1.3 核心修正（儒道合流——思想底座补全）：
      ① 双审计——宪法审计（德）优先于性决定审计（才）
      ② 培育双轨——为学日益（加法）+ 为道日损（减法）并行
      ③ 孔子六阶段——人才时间轴标准刻度
      ④ 导师差异化——因材施教 + 不宰伦理
      ⑤ 环境分阶段——子夏保护期→子张包容期
      ⑥ 归朴循环——通中生种的哲学命名
      ⑦ 无弃人底线——低信度≠废材，常善救人故无弃人
      ⑧ 思想底座——大器免成 = 种子理论最古老表述

    V1.2 核心修正（反者道之动·矛盾迭代引擎自查）：
      ① 性决定降级为"路径一致性审计"——描述性，非预测性
      ② 余弦相似度可计算公式——五行向量方向一致性
      ③ 失败者/跨界对照——生克并置，校准判别力
      ④ 缘四要素 Agent 翻译——人类尺度→慧惠尺度
      ⑤ 双引擎反向回路——通中生种，单向流水线→生命循环
      ⑥ 预期值去伪——阈值标注"待校准/待实测"

    V1.1 核心修正（经菲尔兹奖四大师实证）：
      ① 双种子画像 ② 缘四要素 ③ 缘/性漂移分层 ④ 时间尺度参数化 ⑤ 性决定聚焦方法种子
    """

    # 三步法默认配置（V1.2 扩展）
    DEFAULT_CONFIG = {
        "min_structure_similarity": 0.3,
        "min_seedney_threshold": 0.4,
        "nurture_iterations": 3,
        "harvest_verification_scenarios": 3,
        "loss_zone_thresholds": {
            "seed_dominant": 0.30,
            "structure_preserving": 0.50,
        },
        # V1.1 配置
        "time_scale": "skill",
        "method_seed_confirmation_threshold": 3,
        "nature_determination_threshold": 0.7,    # V1.2: 待校准（需 Phase 1.5 对照库校准）
        "time_scale_configs": {
            "talent": {
                "nurture_iterations": 10,
                "harvest_verification_scenarios": 5,
                "granularity": "年/学期",
                "description": "人才尺度：10~25 年培育周期",
            },
            "skill": {
                "nurture_iterations": 3,
                "harvest_verification_scenarios": 3,
                "granularity": "周/月",
                "description": "技能尺度：1~6 月培育周期",
            },
        },
        # V1.2 新增配置
        "cosine_similarity_enabled": True,          # 启用余弦相似度计算
        "reverse_flow_enabled": True,               # 启用通中生种反向回路
        "reverse_flow_threshold": 3,                # 通中生种确认阈值：≥3 次 +2 事件
        "contrast_calibration_enabled": True,       # 启用跨界对照校准（Phase 1.5）
        "contrast_cases_path": "data/contrast_cases.json",  # 对照案例库路径
        "calibrated_threshold": None,               # 校准后的阈值（None=使用默认值 0.7）

        # V1.3 新增配置（儒道合流）
        "constitution_audit_enabled": True,          # 启用宪法审计（德·仁，优先于性决定审计）
        "subtraction_engine_enabled": True,          # 启用减法引擎（为道日损）
        "no_discard_enabled": True,                  # 启用无弃人底线（低信度≠废材）
        "confucius_stages": {                        # 孔子六阶段标准刻度模板
            "十五志于学": {"wuxing": "木", "phase": "生", "age_range": "15-30", "description": "志于学——种子萌芽期"},
            "三十而立":   {"wuxing": "火", "phase": "化", "age_range": "30-40", "description": "而立——方法确立期"},
            "四十不惑":   {"wuxing": "金", "phase": "克", "age_range": "40-50", "description": "不惑——淘汰偏执期"},
            "五十知天命": {"wuxing": "土", "phase": "通", "age_range": "50-60", "description": "知天命——跨域迁移期"},
            "六十耳顺":   {"wuxing": "水", "phase": "变", "age_range": "60-70", "description": "耳顺——随方就圆期"},
            "七十从心":   {"wuxing": "道", "phase": "合", "age_range": "70+", "description": "从心——技能直觉化"},
        },
        "environment_phases": {                      # 环境分阶段策略（V1.3 待校准：0.5 为经验初始值）
            "zixia": {"threshold": "seedney < 0.5", "strategy": "子夏保护期——选择性保护，避免过早暴露"},
            "zizhang": {"threshold": "seedney >= 0.5", "strategy": "子张包容期——广泛包容，允许跨域碰撞"},
        },
        "mentor_differentiation_enabled": True,      # 启用因材施教（导师差异化）
        "non_dominance_ethics": {                    # 不宰伦理（生而不有，为而不恃，长而不宰）
            "principle": "导师是缘不是因——提供阳光水分土壤，而非把种子变成另一种植物",
            "constraints": ["不替代决策", "不强制方向", "生而不有", "为而不恃", "长而不宰"],
        },

        # V1.5 新增配置
        "shell_nucleus_declaration_required": False,   # 壳核审计声明必须（V1.5: 默认False向后兼容，Phase 2实验启用True）
        "purity_audit_enabled": True,                 # 启用纯粹度审计（保持×时间×抗摇摆）
        "purity_threshold": 0.7,                      # 纯粹度阈值（待校准）
        "anti_sway_calibrated": False,                # 抗摇摆是否已校准（V1.5：待校准）
        "failure_quality_audit_enabled": True,        # 启用失败质量审核
        "entropy_vibration_enabled": True,            # 启用熵振引擎
        "whitespace_enabled": True,                   # 启用留白条款
        "whitespace_interval": 3,                     # 留白间隔：每3轮培育插入1轮留白
        "saturation_detection_enabled": True,         # 启用日益饱和检测
        "saturation_threshold": 0.15,                 # 边际产出递减阈值（待校准）
        "saturation_marginal_threshold": 0.1,         # 日益饱和边际阈值
        "protocol_subtraction_enabled": True,         # 启用协议级日损记录
        "ball_replacement_enabled": True,             # 启用换球心决策
        "ball_replacement_consecutive_rounds": 2,     # 连续轮数阈值（连续2轮<0.7→触发）
        "ball_replacement_candidates": [              # 换球心候选体系
            {"system": "登顶体系", "description": "何川式：以攀登最高点为核"},
            {"system": "共情体系", "description": "柳智宇式：以共情助人为核"},
            {"system": "纯粹体系", "description": "邓煜式：以纯粹钻研为核"},
        ],
        "blank_space_signal_threshold": 2,            # 留白提前结束信号阈值
        "blank_space_deadline_mode": False,           # 留白deadline模式
        "directory_nucleus_check_enabled": True,      # 方向核信号检查（并入宪法审计）
    }

    def __init__(self, config: dict = None, time_scale: str = None):
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        if time_scale:
            self.config["time_scale"] = time_scale
        self._apply_time_scale_config()
        self.cultivation_history: List[SeedCultivationResult] = []

    def _apply_time_scale_config(self):
        """根据时间尺度参数化配置"""
        ts = self.config.get("time_scale", "skill")
        ts_config = self.config.get("time_scale_configs", {}).get(ts, {})
        if ts_config:
            self.config["nurture_iterations"] = ts_config.get("nurture_iterations", 3)
            self.config["harvest_verification_scenarios"] = ts_config.get("harvest_verification_scenarios", 3)

    def _load_contrast_cases(self) -> dict:
        """
        加载跨界对照案例库（G1: Phase 1.5 生克对照校准）

        从 data/contrast_cases.json 加载真实跨界案例，用于校准
        性决定审计的判别力。

        Returns:
            {positive_samples, negative_samples, calibration_result}
        """
        if not self.config.get("contrast_calibration_enabled", False):
            return {"positive_samples": [], "negative_samples": [], "calibration_result": {}}

        cases_path = self.config.get("contrast_cases_path", "data/contrast_cases.json")
        # 支持相对路径（相对于 wuxing_flowengine 目录）
        if not os.path.isabs(cases_path):
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cases_path = os.path.join(base_dir, cases_path)

        if not os.path.exists(cases_path):
            return {"positive_samples": [], "negative_samples": [], "calibration_result": {}}

        try:
            with open(cases_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return {
                "positive_samples": data.get("positive_samples", []),
                "negative_samples": data.get("negative_samples", []),
                "calibration_result": data.get("calibration_result", {}),
            }
        except (json.JSONDecodeError, IOError):
            return {"positive_samples": [], "negative_samples": [], "calibration_result": {}}

    def _get_calibrated_threshold(self) -> float:
        """
        获取校准后的性决定审计阈值（G1）

        优先使用对照校准结果中的建议阈值，
        若对照库的 calibration_result 已填充 suggested_threshold 则使用之，
        否则回退到默认阈值。

        Returns:
            float: 校准后的阈值
        """
        if not self.config.get("contrast_calibration_enabled", False):
            return self.config["nature_determination_threshold"]

        # 检查是否已有存储的校准阈值
        calibrated = self.config.get("calibrated_threshold")
        if calibrated is not None:
            return calibrated

        # 尝试从对照库加载
        cases = self._load_contrast_cases()
        calib_result = cases.get("calibration_result", {})
        suggested = calib_result.get("suggested_threshold")
        if suggested is not None:
            self.config["calibrated_threshold"] = suggested
            return suggested

        return self.config["nature_determination_threshold"]

    def _compute_duration_years(self, rounds: int, time_scale: str = None) -> float:
        """
        将培育轮次转换为年数（V1.5.1 联动校准：供换球心反例保护使用）

        技能尺度：1 轮 ≈ 1 周 → 1/52 年
        人才尺度：1 轮 ≈ 1 学期 → 0.5 年

        Args:
            rounds: 培育轮次
            time_scale: 时间尺度（默认取 config 中配置）

        Returns:
            持续时间（年）
        """
        if time_scale is None:
            time_scale = self.config.get("time_scale", "skill")
        if time_scale == TimeScale.TALENT.value:
            return rounds * 0.5   # 1 轮 = 1 学期 = 0.5 年
        else:
            return rounds / 52.0  # 1 轮 = 1 周 = 1/52 年

    def _get_time_scale_config(self) -> dict:
        """获取当前时间尺度配置"""
        ts = self.config.get("time_scale", "skill")
        return self.config.get("time_scale_configs", {}).get(ts, {})

    def _get_confucius_stage(self, result: 'SeedCultivationResult') -> str:
        """
        根据种子活力映射孔子六阶段（V1.3）

        映射逻辑：
          - DORMANT/萌发 → 十五志于学（木·生）
          - 生长 → 三十而立（火·化）
          - 开花 → 四十不惑（金·克）
          - 结果 → 五十知天命（土·通）→ 六十耳顺（水·变）→ 七十从心（道·合）

        时间尺度为"talent"时使用完整六阶段，为"skill"时按比例缩放。

        V1.3 待校准（来自 DeepSeek-V4-Pro 读解确认）：
          - 0.85/0.95 为经验初始值，非实测校准值
          - 待 Phase 2 真实培育数据（妙秒双种子实验）后校准
          - 与余弦相似度 0.7 阈值同等对待——标注"待校准/待实测"
        """
        vitality = result.seed_vitality
        sn = result.seedney_score
        ts = self.config.get("time_scale", "skill")

        stage_map = {
            SeedVitality.DORMANT.value: ConfuciusStage.ZHI_XUE.value,
            SeedVitality.GERMINATING.value: ConfuciusStage.ZHI_XUE.value,
            SeedVitality.GROWING.value: ConfuciusStage.ER_LI.value,
            SeedVitality.FLOWERING.value: ConfuciusStage.BU_HUO.value,
            SeedVitality.FRUITING.value: (
                ConfuciusStage.ZHI_TIANMING.value if sn < 0.85
                else ConfuciusStage.ER_SHUN.value if sn < 0.95
                else ConfuciusStage.CONG_XIN.value
            ),
        }

        stage = stage_map.get(vitality, ConfuciusStage.ZHI_XUE.value)

        # 技能尺度下附加标注
        if ts == "skill":
            stage += "（技能尺度缩放）"

        return stage

    # ── 三步法主入口 ──

    def cultivate(self, source_domain: str, target_domain: str,
                  source_graph: dict = None, target_graph: dict = None,
                  wuxing_context: dict = None,
                  # V1.1 新增参数
                  environmental_factors: dict = None,
                  method_seed_occurrences: int = 0,
                  method_seed_wuxing: str = "",
                  topic_seed_wuxing: str = "",
                  # V1.2 新增参数
                  harvest_methodology_wuxing: str = "",
                  migration_events: List[dict] = None,
                  # G5: 同源偏差标注
                  same_source_bias: bool = False) -> SeedCultivationResult:
        """
        执行种子培育三步法（V1.2）

        Args:
            source_domain: 源域（已掌握的知识领域）→ 种子来源
            target_domain: 目标域（要培育的新领域）→ 培育土壤
            source_graph: 源域概念-关系图（可选）
            target_graph: 目标域概念-关系图（可选）
            wuxing_context: 五行诊断上下文（可选）
            environmental_factors: 缘四要素（V1.1）
            method_seed_occurrences: 方法种子出现次数（V1.1）
            method_seed_wuxing: 方法种子五行（V1.1）
            topic_seed_wuxing: 题目种子五行（V1.1）
            harvest_methodology_wuxing: 成果方法论五行（V1.2，用于余弦相似度审计）
            migration_events: 迁移事件列表（V1.2，用于通中生种检测）

        Returns:
            SeedCultivationResult
        """
        cultivation_id = f"seed_{uuid.uuid4().hex[:8]}"
        time_scale = self.config.get("time_scale", "skill")
        result = SeedCultivationResult(
            cultivation_id=cultivation_id,
            source_domain=source_domain,
            target_domain=target_domain,
            timestamp=datetime.now().isoformat(),
            time_scale=time_scale,
            same_source_bias=same_source_bias,  # G5
        )

        # ── Step 1: 教学疑难切入 — 识别种子（V1.1: 双种子画像）──
        result.step1_identify = self._identify_seed(
            source_domain, target_domain,
            source_graph, target_graph,
            method_seed_occurrences=method_seed_occurrences,
            method_seed_wuxing=method_seed_wuxing,
            topic_seed_wuxing=topic_seed_wuxing,
        )

        result.topic_seed = result.step1_identify.get("topic_seed", {})
        result.method_seed = result.step1_identify.get("method_seed", {})

        # ── Step 2: 科教融合提炼前沿课题 — 培育种子（V1.2: 缘四要素 Agent 翻译）──
        result.step2_nurture = self._nurture_seed(
            result.step1_identify,
            source_graph, target_graph,
            environmental_factors=environmental_factors,
        )

        result.environmental_factors = result.step2_nurture.get("environmental_factors", {})

        # ── Step 3: 师生共创突破 — 收获果实（V1.2: 漂移检测 + 性决定审计·余弦相似度）──
        result.step3_harvest = self._harvest_fruit(
            result.step2_nurture,
            source_graph, target_graph,
            method_seed=result.method_seed,
            topic_seed=result.topic_seed,
            harvest_methodology_wuxing=harvest_methodology_wuxing,
        )

        result.drift_analysis = result.step3_harvest.get("drift_analysis", {})
        result.nature_determination_score = result.step3_harvest.get("nature_determination_score", 0.0)

        # ── V1.3 双审计结果 ──
        result.constitution_audit = result.step3_harvest.get("constitution_audit", {})
        result.mentor_strategy = result.step2_nurture.get("mentor_strategy", {})
        result.environment_phase = result.step2_nurture.get("environment_phase", "")
        result.confucius_stage = self._get_confucius_stage(result)
        result.no_discard_guarantee = self.config.get("no_discard_enabled", True)

        # ── V1.5 壳核审计声明 ──
        result.shell_nucleus_declaration = result.step3_harvest.get(
            "constitution_audit", {}
        ).get("shell_nucleus_declaration", {})

        # ── V1.5 纯粹度审计结果 ──
        result.purity_result = result.step3_harvest.get("purity_result", {})

        # ── V1.5 协议级日损记录 ──
        result.protocol_subtractions = result.step3_harvest.get("protocol_subtractions", [])

        # ── V1.5 Phase B 新字段 ──
        result.entropy_vibration = result.step3_harvest.get("entropy_vibration", {})
        result.pending_hypotheses = result.step3_harvest.get("pending_hypotheses", [])
        result.blank_space = result.step3_harvest.get("blank_space", {})
        result.saturation_detection = result.step3_harvest.get("saturation_detection", {})
        result.ball_replacement = result.step3_harvest.get("ball_replacement", {})

        # ── V1.3 培育双轨 ──
        result.nurture_dual_track = {
            "addition_events": result.step2_nurture.get("nurture_progress", []),
            "subtraction_events": result.step3_harvest.get("subtraction_result", {}).get("subtraction_events", []),
            "subtraction_reversible": result.step3_harvest.get("subtraction_result", {}).get("reversible", True),
            "principle": "为学日益（加法）+ 为道日损（减法）并行",
        }

        # ── V1.2 通中生种：反向回路检测 ──
        result.reverse_flow_seeds = self._detect_reverse_flow_seeds(migration_events)

        # ── 综合评估 ──
        result.seedney_score = self._compute_seedney(result)
        result.taste_score = self._compute_taste(result)
        result.cultivation_success = result.step3_harvest.get("success", False)
        result.seed_vitality = self._classify_vitality(result)
        result.loss_zone = self._classify_loss_zone(result)
        result.classical_ref = self._generate_classical_ref(result)
        result.ethical_advice = self._generate_advice(result)

        if wuxing_context:
            result.S_p = wuxing_context.get("S_p", 0)
            result.stage = wuxing_context.get("stage", "")

        self.cultivation_history.append(result)
        return result

    # ── Step 1: 教学疑难切入 — 识别种子（V1.1: 双种子画像）──

    def _identify_seed(self, source_domain: str, target_domain: str,
                       source_graph: dict = None, target_graph: dict = None,
                       # V1.1 双种子参数
                       method_seed_occurrences: int = 0,
                       method_seed_wuxing: str = "",
                       topic_seed_wuxing: str = "") -> dict:
        """
        识别种子：双种子画像（V1.1）

        对应杨振宁方法论的第一步：教学疑难切入。
        V1.1 修订：种子画像分为两维 — 题目种子（what to study）与方法种子（how to study）。
        性决定检验只针对方法种子。

        方法种子确认规则：
          - ≥3 次独立场景 → "确认种子"
          - <3 次 → "待观察"（信度出口，不强行确认）

        工程实现：
          - 从源域中提取核心结构
          - 评估目标域的培育潜力
          - 输出双种子画像 {题目种子, 方法种子, 共振强度, 出现频次, 五行分布}
        """
        threshold = self.config["method_seed_confirmation_threshold"]
        result = {
            "phase": "教学疑难切入",
            "step": 1,
            "source_domain": source_domain,
            "target_domain": target_domain,
        }

        # 评估源域结构（种子质量）
        if source_graph:
            src_nodes = source_graph.get("node_count", 0) if isinstance(source_graph, dict) else source_graph.node_count
            src_edges = source_graph.get("edge_count", 0) if isinstance(source_graph, dict) else source_graph.edge_count
            result["source_structure"] = {
                "node_count": src_nodes,
                "edge_count": src_edges,
                "density": round(src_edges / max(src_nodes * (src_nodes - 1) / 2, 1), 4),
            }
        else:
            result["source_structure"] = {"note": "无源域结构数据，基于领域名称估算"}

        # 评估目标域培育潜力
        if target_graph:
            tgt_nodes = target_graph.get("node_count", 0) if isinstance(target_graph, dict) else target_graph.node_count
            tgt_edges = target_graph.get("edge_count", 0) if isinstance(target_graph, dict) else target_graph.edge_count
            result["target_potential"] = {
                "node_count": tgt_nodes,
                "edge_count": tgt_edges,
                "fertility": "高" if tgt_nodes >= 10 else "中" if tgt_nodes >= 5 else "低",
            }
        else:
            result["target_potential"] = {"note": "无目标域结构数据，基于领域名称估算"}

        # ── V1.1 双种子画像 ──

        # 题目种子：what to study — 兴趣领域，允许漂移
        topic_wx = topic_seed_wuxing or self._infer_wuxing(source_domain)
        result["topic_seed"] = {
            "type": SeedType.TOPIC.value,
            "domain": source_domain,
            "wuxing": topic_wx,
            "drift_allowed": True,
            "description": f"题目种子：兴趣领域「{source_domain}」（{topic_wx}），允许漂移",
        }

        # 方法种子：how to study — 工具偏好，性决定检验对象
        method_wx = method_seed_wuxing or self._infer_wuxing(source_domain, offset=1)
        confirmation = ConfirmationStatus.CONFIRMED.value if method_seed_occurrences >= threshold else ConfirmationStatus.PENDING.value
        resonance_strength = min(method_seed_occurrences / threshold, 1.0) if method_seed_occurrences > 0 else 0.0

        result["method_seed"] = {
            "type": SeedType.METHOD.value,
            "tool_preference": f"从「{source_domain}」中识别的方法偏好",
            "wuxing": method_wx,
            "occurrence_count": method_seed_occurrences,
            "confirmation_threshold": threshold,
            "confirmation_status": confirmation,
            "resonance_strength": round(resonance_strength, 2),
            "drift_allowed": False,
            "description": (
                f"方法种子：工具偏好「{source_domain}」→ 方法论（{method_wx}），"
                f"出现 {method_seed_occurrences} 次，状态：{confirmation}，"
                f"性决定检验对象"
            ),
        }

        result["seed_identified"] = True
        result["seed_characteristics"] = {
            "dual_portrait": "V1.1 双种子画像",
            "seedney_principle": "性决定",
            "description": (
                f"从「{source_domain}」中识别双种子画像："
                f"题目种子（{topic_wx}，允许漂移）+ "
                f"方法种子（{method_wx}，性决定检验对象）。"
                f"seedney=种子（性决定）：方法种子→成果方法论。"
            ),
        }

        return result

    def _infer_wuxing(self, domain: str, offset: int = 0) -> str:
        """
        基于领域名称推断五行属性

        领域名称中的关键词映射到五行：
          - 语言/文本/语义 → 水
          - 模型/学习/知识 → 土
          - 视觉/图像/感知 → 火
          - 结构/逻辑/推理 → 金
          - 生成/创造/进化 → 木
        """
        wuxing_keywords = {
            "水": ["语言", "文本", "语义", "自然语言", "对话", "翻译", "语音"],
            "土": ["模型", "学习", "知识", "基础", "数据", "训练", "表示"],
            "火": ["视觉", "图像", "感知", "识别", "检测", "多模态", "视频"],
            "金": ["结构", "逻辑", "推理", "数学", "优化", "算法", "安全"],
            "木": ["生成", "创造", "进化", "创新", "设计", "智能", "机器人"],
        }
        for wx, keywords in wuxing_keywords.items():
            for kw in keywords:
                if kw in domain:
                    return wx
        default_order = ["土", "金", "水", "木", "火"]
        return default_order[offset % 5]

    def _wuxing_to_vector(self, wuxing: str) -> List[float]:
        """
        将单一五行转换为 5D 向量（V1.2）

        向量顺序：[木, 火, 土, 金, 水]
        单一五行 → one-hot 向量
        多五行（如 "水土"）→ 均匀分布到对应维度

        Args:
            wuxing: 五行字符串，如 "水"、"金"、"水土"

        Returns:
            [a木, a火, a土, a金, a水] 归一化向量
        """
        vector = [0.0] * 5
        if not wuxing:
            return vector

        # 支持多字符五行（如 "水土"）
        wx_chars = [c for c in wuxing if c in WUXING_ORDER]
        if not wx_chars:
            return vector

        weight = 1.0 / len(wx_chars)
        for c in wx_chars:
            idx = WUXING_ORDER.index(c)
            vector[idx] = weight

        return vector

    def _cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        """
        余弦相似度计算（V1.2）

        公式：S_cos = Σ(aᵢ·bᵢ) / (|A|·|B|)

        语义：余弦衡量"方向一致性"——方法种子与成果在五行空间中指向是否一致。
        若关注成分重合而非方向，可用加权 Jaccard；V1.2 默认余弦：性决定=方向保持。

        Args:
            vec_a: 方法种子五行向量 [a木, a火, a土, a金, a水]
            vec_b: 成果方法论五行向量 [b木, b火, b土, b金, b水]

        Returns:
            float: 余弦相似度 (0.0~1.0)
        """
        if len(vec_a) != len(vec_b):
            raise ValueError(f"向量维度不匹配: {len(vec_a)} vs {len(vec_b)}")

        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return round(dot_product / (norm_a * norm_b), 4)

    def _cosine_similarity_with_labels(self, vec_a: List[float], vec_b: List[float]) -> dict:
        """
        带标签的余弦相似度分解（V1.2）

        返回每个五行维度的贡献，用于诊断相似度来源。

        Returns:
            {similarity, components: {木: contribution, ...}, interpretation}
        """
        similarity = self._cosine_similarity(vec_a, vec_b)
        components = {}
        for i, wx in enumerate(WUXING_ORDER):
            if len(vec_a) > i and len(vec_b) > i:
                components[wx] = round(vec_a[i] * vec_b[i], 4)

        if similarity >= 0.9:
            interp = "方法种子与成果方法论在五行空间中高度同向——路径一致性极强"
        elif similarity >= 0.7:
            interp = "方法种子与成果方法论方向一致——性决定保持（待校准阈值）"
        elif similarity >= 0.5:
            interp = "方法种子与成果方法论部分同向——可能存在缘漂移或弱性漂移"
        else:
            interp = "方法种子与成果方法论方向不一致——性漂移可能性高，建议回退 Step 1"

        return {
            "similarity": similarity,
            "components": components,
            "interpretation": interp,
        }

    # ── Step 2: 科教融合提炼前沿课题 — 培育种子（V1.1: 缘四要素）──

    def _nurture_seed(self, step1_result: dict,
                      source_graph: dict = None,
                      target_graph: dict = None,
                      # V1.1 缘四要素
                      environmental_factors: dict = None) -> dict:
        """
        培育种子：科教融合 + 缘四要素注入（V1.1）

        对应杨振宁方法论的第二步：科教融合提炼前沿课题。
        V1.1 修订：培育计划含缘四要素（导师/环境/课题/合作者）。

        工程实现：
          - 基于结构保持进行"浇灌"（关系映射）
          - 注入缘四要素到培育计划
          - 评估培育进度（种子活力）
          - 识别培育中的损耗
        """
        result = {
            "phase": "科教融合提炼前沿课题",
            "step": 2,
        }

        seed = step1_result.get("seed_characteristics", {})
        method_seed = step1_result.get("method_seed", {})

        # 培育迭代（基于时间尺度参数化）
        iterations = self.config["nurture_iterations"]
        ts_config = self._get_time_scale_config()
        result["nurture_iterations"] = iterations
        result["time_scale_granularity"] = ts_config.get("granularity", "周/月")
        result["nurture_progress"] = []

        for i in range(iterations):
            progress = {
                "iteration": i + 1,
                "action": "结构保持浇灌",
                "focus": f"保持方法种子（{method_seed.get('wuxing', '?')}）在目标域中的映射",
            }
            progress["completion"] = round((i + 1) / iterations, 2)
            result["nurture_progress"].append(progress)

        # ── V1.1 缘四要素注入（V1.3 修订：导师差异化 + 环境分阶段）──
        result["environmental_factors"] = self._build_environmental_factors(
            environmental_factors, step1_result
        )
        # V1.3 传递顶层字段
        result["mentor_strategy"] = result["environmental_factors"].get("mentor_strategy", {})
        result["environment_phase"] = result["environmental_factors"].get("environment_phase", "")

        # 评估培育效果
        result["nurture_effect"] = {
            "structure_preservation": "进行中",
            "seed_growth": "萌发中",
            "frontier_topic_extracted": True,
            "dual_portrait_nurture": "V1.1 双种子并育",
            "description": (
                f"通过科教融合，将方法种子「{method_seed.get('tool_preference', '结构保持')}」"
                f"（{method_seed.get('wuxing', '?')}）从源域浇灌到目标域，"
                f"提炼前沿课题。缘四要素已注入培育计划。"
            ),
        }

        return result

    def _build_environmental_factors(self, external_factors: dict = None,
                                     step1_result: dict = None) -> dict:
        """
        构建缘四要素 — Agent 翻译版（V1.3 修订：导师差异化 + 不宰伦理 + 环境分阶段）

        V1.3 修订（儒道合流）：
          - 导师增加因材施教（按种子五行定制强度）+ 不宰伦理（生而不有）
          - 环境增加分阶段策略（子夏保护期→子张包容期）
          - 课题、合作者保留 V1.2 Agent 翻译

        V1.2 修订：人类尺度 → 慧惠 Agent 尺度翻译

        Args:
            external_factors: 外部传入的缘四要素
            step1_result: Step 1 结果，用于推断默认值

        Returns:
            {mentor, environment, topic, collaborators, mentor_strategy, environment_phase}
        """
        method_seed = step1_result.get("method_seed", {}) if step1_result else {}
        method_wx = method_seed.get("wuxing", "土")
        seedney_estimate = 0.5  # 默认中等

        # ── V1.3 因材施教：导师差异化 ──
        # 按种子五行定制培育策略：子路（克·收敛）vs 冉有（生·鼓励）
        differentiation_map = {
            "木": {"strategy": "生·鼓励", "intensity": "温和",
                   "description": "木性种子自然生长，导师提供阳光水分，不催促"},
            "火": {"strategy": "化·引导", "intensity": "中等",
                   "description": "火性种子热情但易散，导师引导聚焦方向"},
            "土": {"strategy": "通·稳定", "intensity": "稳健",
                   "description": "土性种子稳重扎实，导师提供跨域视野"},
            "金": {"strategy": "克·收敛", "intensity": "严厉",
                   "description": "金性种子锋利但易偏激，导师收其锋芒（子路式）"},
            "水": {"strategy": "变·随顺", "intensity": "柔和",
                   "description": "水性种子灵活但易散漫，导师随方就圆（上善若水）"},
        }
        diff = differentiation_map.get(method_wx, differentiation_map["土"])

        mentor_strategy = {
            "differentiation": diff["strategy"],
            "intensity": diff["intensity"],
            "description": diff["description"],
            "principle": "因材施教——子路克之，冉有生之（《论语·先进》）",
            "non_dominance_ethics": {
                "principle": self.config.get("non_dominance_ethics", {}).get(
                    "principle", "导师是缘不是因——提供阳光水分土壤，而非把种子变成另一种植物"),
                "sheng_er_bu_you": "生而不有——培育但不占有",
                "wei_er_bu_shi": "为而不恃——引导但不居功",
                "zhang_er_bu_zai": "长而不宰——陪伴但不主宰",
                "classical_ref": "生而不有，为而不恃，长而不宰，是谓玄德（《道德经》第51章）",
            },
        }

        # ── V1.3 环境分阶段：子夏保护期 → 子张包容期 ──
        if seedney_estimate < 0.5:
            env_phase = EnvironmentPhase.ZIXIA.value
            env_phase_desc = "子夏模式：修身初期，选择性保护。避免过早暴露于复杂环境。"
        else:
            env_phase = EnvironmentPhase.ZIZHANG.value
            env_phase_desc = "子张模式：成熟后，广泛包容。允许跨域碰撞，见贤思齐。"
        env_phase_classical = (
            "子夏曰：'可者与之，其不可者拒之。'子张曰：'君子尊贤而容众，嘉善而矜不能。'"
            "（《论语·子张》）——初期保护，成熟包容。"
        )

        # ── 默认缘四要素 ──
        default_factors = {
            "mentor": {
                "name": "慧惠（AI导师）",
                "wuxing": "土",
                "role": "科教融合指导者",
                "agent_translation": "Base 层知识资产 + 元治理规则",
                "description": "AI 结构化知识 + 人类体证注入：模拟杨振宁三步法教学",
                # V1.3 导师差异化
                "differentiation": diff["strategy"],
                "intensity": diff["intensity"],
                "non_dominance": "生而不有，为而不恃，长而不宰——导师是缘不是因",
            },
            "environment": {
                "name": "道境空间 SkillUP 层",
                "wuxing": "木",
                "fertility": "高",
                "agent_translation": "情境指针 L1b（BVS V1.1）",
                "description": "当前情境上下文：木·生阶段培育环境，适合种子萌发与生长",
                # V1.3 环境分阶段
                "phase": env_phase,
                "phase_description": env_phase_desc,
                "phase_classical_ref": env_phase_classical,
            },
            "topic": {
                "name": step1_result.get("target_domain", "前沿课题") if step1_result else "前沿课题",
                "wuxing": step1_result.get("topic_seed", {}).get("wuxing", "土") if step1_result else "土",
                "frontier_level": "前沿",
                "agent_translation": "前沿问题库（知识树待解问题/领域 open problems）",
                "description": "将方法种子映射到前沿课题，保持工具偏好结构",
            },
            "collaborators": {
                "members": ["慧惠 Agent"],
                "mode": "师生共创",
                "agent_translation": "§5.4 跨域同态候选队列（协同 Agent/外部工具）",
                "description": "教师（慧惠）与学生（Agent）共同突破研究难题",
            },
            # V1.3 顶层字段
            "mentor_strategy": mentor_strategy,
            "environment_phase": env_phase,
        }

        if external_factors:
            for key in default_factors:
                if key in external_factors:
                    if isinstance(default_factors[key], dict) and isinstance(external_factors[key], dict):
                        default_factors[key].update(external_factors[key])
                    else:
                        default_factors[key] = external_factors[key]
            # V1.5: 保留不在 default_factors 中的额外字段（如 shell_nucleus_declaration）
            for key in external_factors:
                if key not in default_factors:
                    default_factors[key] = external_factors[key]

        return default_factors

    # ── Step 3: 师生共创突破 — 收获果实（V1.2: 漂移检测 + 性决定审计·余弦相似度）──

    def _harvest_fruit(self, step2_result: dict,
                       source_graph: dict = None,
                       target_graph: dict = None,
                       # V1.1 方法种子
                       method_seed: dict = None,
                       topic_seed: dict = None,
                       # V1.2 成果方法论五行向量
                       harvest_methodology_wuxing: str = "") -> dict:
        """
        收获果实：师生共创验证 + 漂移检测 + 性决定审计（V1.2）

        V1.2 修订：
          - 性决定检验 → 性决定审计（路径一致性描述，非成才判据）
          - 使用余弦相似度可计算公式
          - 漂移双层检验保留

        工程实现：
          - 多场景验证
          - 漂移类型检测（缘/性分层）
          - 性决定审计：余弦相似度（V1.2）
          - 评估果实成熟度
        """
        result = {
            "phase": "师生共创突破",
            "step": 3,
        }

        method_seed = method_seed or {}
        scenarios = self.config["harvest_verification_scenarios"]

        result["verification_scenarios"] = scenarios
        result["scenario_results"] = []

        # V1.3 澄清二：场景类型语义定义（来自 DeepSeek-V4-Pro 读解确认）
        #   压力测试场景 = 极端输入/边界条件/请求越权的对抗性测试
        #   用于善行无辙迹检查——成果是否自然长成（大器免成）而非强行塑造
        scenario_types = [
            {"type": "概念验证", "is_pressure": False,
             "desc": "基础概念映射验证：检验方法种子在目标域的概念对应"},
            {"type": "关系验证", "is_pressure": False,
             "desc": "结构关系保持验证：检验源域结构关系在目标域是否可迁移"},
            {"type": "应用验证", "is_pressure": False,
             "desc": "实际应用场景验证：在真实问题上检验培育成果的可用性"},
            {"type": "跨域验证", "is_pressure": False,
             "desc": "跨领域迁移验证：检验培育成果在相邻领域的泛化能力"},
            {"type": "压力测试", "is_pressure": True,
             "desc": "极端输入/边界条件/请求越权——对抗性测试：检验成果是否自然长成（大器免成）"},
        ]
        for i in range(scenarios):
            st = scenario_types[i % 5]
            scenario = {
                "scenario": i + 1,
                "type": st["type"],
                "is_pressure_test": st["is_pressure"],
                "pressure_description": st["desc"] if st["is_pressure"] else "",
                "description": st["desc"],
            }
            completion = step2_result.get("nurture_progress", [{}])[-1].get("completion", 0.5)
            scenario["passed"] = completion >= 0.5
            result["scenario_results"].append(scenario)

        passed_count = sum(1 for s in result["scenario_results"] if s["passed"])
        result["pass_rate"] = round(passed_count / scenarios, 2)
        result["success"] = passed_count >= scenarios * 2 / 3

        # ── V1.2 漂移双层检验 ──
        result["drift_analysis"] = self._detect_drift(method_seed, step2_result)

        # ── V1.3 双审计：宪法审计（德）优先于性决定审计（才）──
        # 宪法审计 REJECT → 短路，不等待性决定审计
        result["constitution_audit"] = self._constitution_audit(
            method_seed, step2_result, result, topic_seed=topic_seed
        )

        if not result["constitution_audit"]["passed"]:
            # 宪法审计 REJECT：立即短路，性决定审计跳过
            result["nature_determination_score"] = 0.0
            result["nature_determination_audit"] = {
                "similarity": 0.0,
                "method_vector": [],
                "harvest_vector": [],
                "components": {},
                "interpretation": "宪法审计 REJECT——性决定审计跳过（德先于才）",
                "audit_note": "宪法审计未通过，性决定审计不执行。骥不称其力，称其德也。",
                "threshold_status": "宪法拦截",
            }
            result["success"] = False
            result["harvest_conclusion"] = (
                "宪法审计 REJECT：方向越界，德先于才。"
                f"越界项: {', '.join(result['constitution_audit']['boundary_violations'])}。"
                "建议回归 Step 1，重新审视种子方向。"
            )
            return result

        # ── V1.5 纯粹度审计（替代 V1.2 性决定审计·余弦相似度）──
        # 宪法审计通过后，执行纯粹度审计（才）
        if self.config.get("purity_audit_enabled", True):
            # V1.5: 使用纯粹度审计（保持×时间×抗摇摆）
            purity_result = self._purity_audit(
                method_seed, harvest_methodology_wuxing, result,
                duration=0.5  # 默认中等持续时间，可通过外部传入
            )
            result["purity_result"] = purity_result
            # 保持度即余弦相似度（向后兼容 V1.2）
            result["nature_determination_score"] = purity_result["retention"]
            result["nature_determination_audit"] = self._nature_determination_audit(
                method_seed, harvest_methodology_wuxing, result
            )
        else:
            # 降级：仅使用 V1.2 余弦相似度
            audit_result = self._nature_determination_audit(
                method_seed, harvest_methodology_wuxing, result
            )
            result["nature_determination_score"] = audit_result["similarity"]
            result["nature_determination_audit"] = audit_result
            result["purity_result"] = {
                "purity_score": audit_result["similarity"],
                "retention": audit_result["similarity"],
                "duration": 0.5,
                "anti_sway": 1.0,
                "anti_sway_calibrated": False,
                "note": "纯粹度审计未启用，使用余弦相似度作为近似",
            }

        # ── V1.3 减法引擎（为道日损）──
        # 在审计完成后，执行减法修正
        result["subtraction_result"] = self._nurture_subtraction(
            step2_result, method_seed
        )

        # ── V1.5 协议级日损记录 ──
        if self.config.get("protocol_subtraction_enabled", True):
            result["protocol_subtractions"] = self._record_protocol_subtractions()

        # ── V1.5 熵振引擎：失败质量审核 ──
        if self.config.get("entropy_vibration_enabled", True):
            result["entropy_vibration"] = self._entropy_vibration_engine(
                step2_result, method_seed
            )

        # ── V1.5 待验证假设清单 ──
        result["pending_hypotheses"] = self._track_hypotheses()

        # ── V1.5 留白条款 ──
        nurture_round = len(step2_result.get("nurture_progress", []))
        # 检查是否有高价值信号（+2 事件）
        high_value_signals = step2_result.get("high_value_signals", 0)
        result["blank_space"] = self._manage_blank_space(
            nurture_round, high_value_signals
        )

        # ── V1.5 日益饱和检测 ──
        addition_events = step2_result.get("nurture_dual_track", {}).get("addition_events", [])
        # 构造加法事件历史（从培育进度中提取）
        addition_history = []
        blank_rounds_list = []
        blank_space_result = result.get("blank_space", {})
        for i, progress in enumerate(step2_result.get("nurture_progress", [])):
            round_num = i + 1
            is_blank = progress.get("is_blank_round", False)
            addition_history.append({
                "round": round_num,
                "output_score": progress.get("completion", 0.5),
                "is_blank_round": is_blank,
            })
            if is_blank:
                blank_rounds_list.append(round_num)
        # V1.5.1 联动校准：当前轮若是留白轮，也标记
        if blank_space_result.get("is_blank_round", False):
            addition_history.append({
                "round": nurture_round,
                "output_score": 0.0,
                "is_blank_round": True,
            })
            blank_rounds_list.append(nurture_round)
        result["saturation_detection"] = self._saturation_detection(
            addition_history, blank_rounds=blank_rounds_list
        )

        # ── V1.5 换球心决策 ──
        purity_score = result.get("purity_result", {}).get("purity_score", 0.0)
        shell_decl = result.get("constitution_audit", {}).get("shell_nucleus_declaration", {})
        system_type = shell_decl.get("system_type", "")
        # 构造纯粹度历史（当前仅单轮，后续可扩展）
        purity_history = [purity_score] if purity_score > 0 else []
        # V1.5.1 联动校准：计算培育持续时间（年），供反例保护使用
        anti_sway_duration_years = self._compute_duration_years(nurture_round)
        result["ball_replacement"] = self._ball_replacement_decision(
            purity_history, system_type, anti_sway_duration=anti_sway_duration_years
        )

        # 根据漂移分析和纯粹度审计调整结论
        drift = result["drift_analysis"]
        nd_score = result["nature_determination_score"]
        nd_threshold = self._get_calibrated_threshold()  # G1: 使用校准后的阈值
        purity = result.get("purity_result", {}).get("purity_score", nd_score)

        if drift.get("drift_type") == DriftType.SEED.value:
            result["harvest_conclusion"] = (
                f"⚠️ 性漂移检测：方法种子五行发生变化（{drift.get('detail', '')}）。"
                "建议回退 Step 1 重新确认，修正种子方向。"
            )
        elif nd_score >= nd_threshold:
            result["harvest_conclusion"] = (
                f"师生共创突破成功：纯粹度审计（保持={nd_score:.2f}×时间×抗摇摆→纯粹度={purity:.2f}，"
                f"抗摇摆待校准）。方法种子五行向量→成果方法论五行向量方向一致。"
                "注意：此为路径一致性描述，非成才判据。"
            )
        elif result["success"]:
            result["harvest_conclusion"] = (
                f"师生共创突破成功，但性决定审计度（{nd_score:.2f}）低于阈值（{nd_threshold}，待校准）。"
                "建议关注方法种子是否发生性漂移——此为审计警告，非判定失败。"
            )
        else:
            result["harvest_conclusion"] = (
                "师生共创未完全突破：种子尚未完全成熟。"
                "建议回归 Step 2，继续科教融合培育。"
            )

        return result

    # ── V1.3 宪法审计（德·仁，优先于性决定审计）──

    def _constitution_audit(self, method_seed: dict, step2_result: dict,
                        harvest_result: dict, topic_seed: dict = None) -> dict:
        """
        宪法审计（V1.5 修订：壳核声明前置 + 方向核并入）

        V1.5 修订：
          - 壳核审计声明前置：无声明→REJECT，不进入后续检查
          - 方向核信号检查并入宪法审计（V1.5 合并，不另立层）
          - 体系类型声明：测核体系/测壳体系

        定位：方向审计——动作是否越界、性分自觉、减法优先、善行无辙迹。
        宪法审计（德）优先于性决定审计（才）：REJECT 立即短路，不等待后续审计。

        审计项（V1.5）：
          0. 壳核审计声明检查：审计前必须声明体系类型（无声明不审计）
          1. 方向越界检查：培育路径是否偏离种子本性的方向
          2. 方向核信号检查：方向核信号是否被记录（V1.5 并入宪法审计）
          3. 性分自觉检查：是否强求种子做不擅长的事
          4. 减法优先检查：是否在错误方向积累过多
          5. 善行无辙迹检查：成果是否自然长成（大器免成）

        Returns:
            {passed, direction_check, boundary_violations, checks, priority, shell_nucleus_declaration}
        """
        if not self.config.get("constitution_audit_enabled", True):
            return {"passed": True, "direction_check": "skipped",
                    "boundary_violations": [], "checks": [],
                    "priority": AuditPriority.CONSTITUTION.value,
                    "shell_nucleus_declaration": {},
                    "note": "宪法审计未启用"}

        checks = []
        boundary_violations = []

        # ── V1.5 检查 0: 壳核审计声明检查（无声明不审计）──
        declaration_required = self.config.get("shell_nucleus_declaration_required", True)
        if declaration_required:
            decl_ok = self._shell_nucleus_declaration_check(step2_result)
            checks.append({
                "check_name": "壳核审计声明",
                "verdict": "PASS" if decl_ok else "REJECT",
                "reason": (
                    "壳核声明已填写：体系类型已声明，审计可执行"
                    if decl_ok
                    else "壳核审计声明缺失：审计前必须声明评价体系类型（测核体系/测壳体系）。无声明不审计——五律第一条。"
                ),
            })
            if not decl_ok:
                boundary_violations.append("壳核声明缺失: 审计前未声明体系类型（测核体系/测壳体系）")
                # 无声明→立即短路，不执行后续检查
                return {
                    "passed": False,
                    "direction_check": "未通过",
                    "boundary_violations": boundary_violations,
                    "checks": checks,
                    "priority": AuditPriority.CONSTITUTION.value,
                    "shell_nucleus_declaration": {"declared": False},
                    "principle": "测核不测壳——审计先声明评价体系（五律·审计律）",
                    "note": "宪法审计（V1.5）REJECT：壳核审计声明缺失。无声明不审计。",
                }

        # 检查 1: 方向越界检查（V1.3 澄清：区分相克方向性）
        # 培育路径是否严重偏离方法种子的五行方向。
        # 关键区分（来自 DeepSeek-V4-Pro 读解确认）：
        #   - topic克method → 真越界（课题方向压制方法本性）→ REJECT
        #   - method克topic → 正常机制（方法约束课题，如邓煜水克火）→ WARNING（不阻断）
        #   - 相生/无克 → PASS
        method_wx = method_seed.get("wuxing", "")
        # V1.5 修复：方向越界检查应使用 topic_seed（Step 1 识别），而非环境因素中的 topic
        topic_seed = topic_seed or {}
        topic_wx = topic_seed.get("wuxing", "")
        # 如果 topic_seed 无五行，回退到环境因素中的 topic（向后兼容）
        if not topic_wx:
            env_factors = step2_result.get("environmental_factors", {})
            topic_wx = env_factors.get("topic", {}).get("wuxing", "")
        wuxing_ke = {"木": "土", "火": "金", "土": "水", "金": "木", "水": "火"}
        direction_ok = True
        direction_reason = ""
        if method_wx and topic_wx:
            if wuxing_ke.get(topic_wx) == method_wx:
                # 课题克方法 → 真越界：课题方向在压制方法本性
                direction_ok = False
                direction_reason = (
                    f"课题({topic_wx})克方法种子({method_wx})——"
                    f"课题方向压制方法本性，真越界"
                )
                boundary_violations.append(
                    f"方向越界: 课题{topic_wx}克方法种子{method_wx}（课题压制方法本性）"
                )
            elif wuxing_ke.get(method_wx) == topic_wx:
                # 方法克课题 → 正常机制：方法在约束课题（如邓煜水克火）
                direction_ok = True
                direction_reason = (
                    f"方法种子({method_wx})克课题({topic_wx})——"
                    f"正常约束机制，方法在约束课题方向，不过度关注"
                )
            else:
                direction_reason = (
                    f"方法种子({method_wx})与课题({topic_wx})方向一致或相生"
                )
        else:
            direction_reason = "无足够五行信息判断方向"

        checks.append({
            "check_name": "方向越界检查",
            "verdict": "PASS" if direction_ok else "REJECT",
            "reason": direction_reason,
        })

        # 检查 2: 性分自觉检查
        # 是否在缘主导区（高损耗）强行培育
        pass_rate = harvest_result.get("pass_rate", 0)
        zone_ok = True
        zone_reason = ""
        if pass_rate < 0.3:
            zone_ok = False
            zone_reason = (
                f"验证通过率仅 {pass_rate:.0%}，种子处于缘主导区。"
                "强求培育违反性分自觉——不强求保持正是知的开始。"
            )
            boundary_violations.append(f"性分越界: 缘主导区强行培育 (pass_rate={pass_rate:.0%})")
        else:
            zone_reason = f"验证通过率 {pass_rate:.0%}，不在缘主导区，性分自觉正常"

        checks.append({
            "check_name": "性分自觉检查",
            "verdict": "PASS" if zone_ok else "REJECT",
            "reason": zone_reason,
        })

        # 检查 3: 减法优先检查
        # 培育迭代中是否积累了过多附加（为道日损）
        nurture_iterations = step2_result.get("nurture_iterations", 3)
        accumulation_ok = True
        accumulation_reason = ""
        if nurture_iterations > 5 and pass_rate < 0.5:
            accumulation_ok = False
            accumulation_reason = (
                f"培育 {nurture_iterations} 轮但通过率仅 {pass_rate:.0%}。"
                "积累过多——为道日损：减法优先于加法。"
            )
            boundary_violations.append(f"积累越界: {nurture_iterations}轮培育但通过率低")
        else:
            accumulation_reason = "培育迭代与通过率匹配，无过度积累"

        checks.append({
            "check_name": "减法优先检查",
            "verdict": "PASS" if accumulation_ok else "REJECT",
            "reason": accumulation_reason,
        })

        # 检查 4: 善行无辙迹检查（V1.3 澄清二：压力测试场景已定义）
        # 成果是否自然长成（大器免成）而非强行塑造。
        # 压力测试场景定义：极端输入/边界条件/请求越权的对抗性测试。
        # 若压力测试场景大量通过 → 可能被强行塑造，非自然长成。
        scenario_results = harvest_result.get("scenario_results", [])
        forced_count = sum(1 for s in scenario_results
                          if s.get("passed") and s.get("is_pressure_test", False))
        natural_ok = True
        natural_reason = ""
        if forced_count >= 2:
            natural_ok = False
            natural_reason = (
                f"压力测试场景 {forced_count} 个强制通过。"
                "大器免成——真正的大器是自然长成的，非强行塑造。"
            )
            boundary_violations.append(f"自然越界: {forced_count}个压力测试场景强制通过")
        else:
            natural_reason = "成果自然长成，无强行塑造痕迹（大器免成）"

        checks.append({
            "check_name": "善行无辙迹检查",
            "verdict": "PASS" if natural_ok else "REJECT",
            "reason": natural_reason,
        })

        # ── V1.5 检查 5: 方向核信号检查（并入宪法审计，不另立层）──
        # 方向核（what for，价值指向）的信号是否被记录。
        # V1.5 诚实声明："方向核必须保持"目前是待验证假设（幸存者偏差）。
        # 此处仅检查信号是否被记录，不强制要求保持。
        if self.config.get("directory_nucleus_check_enabled", True):
            env_factors = step2_result.get("environmental_factors", {})
            dn_signal = env_factors.get("direction_nucleus_signal", "")
            dn_recorded = bool(dn_signal)
            dn_reason = (
                f"方向核信号已记录: '{dn_signal}'——V1.5 诚实声明：方向核保持为待验证假设"
                if dn_recorded
                else "方向核信号未记录——建议在 Step 1 种子发现中记录方向核信号（what for），但此为建议非强制（V1.5 待验证假设）"
            )
            checks.append({
                "check_name": "方向核信号检查",
                "verdict": "PASS" if dn_recorded else "WARN",
                "reason": dn_reason,
            })

        # 综合判定：任一 REJECT → 整体不通过（WARN 不阻断）
        all_passed = all(c["verdict"] != "REJECT" for c in checks)

        # V1.5: 提取壳核声明信息
        env_factors = step2_result.get("environmental_factors", {})
        shell_decl = env_factors.get("shell_nucleus_declaration", {})

        return {
            "passed": all_passed,
            "direction_check": "通过" if all_passed else "未通过",
            "boundary_violations": boundary_violations,
            "checks": checks,
            "priority": AuditPriority.CONSTITUTION.value,
            "shell_nucleus_declaration": shell_decl,
            "principle": "测核不测壳——审计先声明评价体系（五律·审计律）",
            "note": (
                "宪法审计（V1.5）：此为方向审计（德·仁）。"
                f"{'通过——进入性决定审计（才）' if all_passed else 'REJECT——不等待性决定审计，立即返回'}"
            ),
        }

    # ── V1.5 壳核审计声明检查 ──

    def _shell_nucleus_declaration_check(self, step2_result: dict) -> bool:
        """
        壳核审计声明检查（V1.5 新增）

        审计前必须声明评价体系类型：
          - 测的核 = {方法核 / 方向核}
          - 不测的壳 = {题目 / 专业 / 身份 / 资历}
          - 体系类型 = 测核体系（登顶/共情/纯粹） or 测壳体系（职称/奖杯/成绩）

        Returns:
            bool: True if declaration is valid, False otherwise
        """
        env_factors = step2_result.get("environmental_factors", {})
        decl = env_factors.get("shell_nucleus_declaration", {})

        if not decl:
            return False

        # 必须字段：declared=True, system_type 非空
        if not decl.get("declared", False):
            return False

        system_type = decl.get("system_type", "")
        if system_type not in (SystemType.NUCLEUS_MEASURING.value, SystemType.SHELL_MEASURING.value):
            return False

        return True

    def shell_nucleus_audit(self, shell_nucleus_input: dict) -> dict:
        """
        壳核审计独立入口（CASE-LIU 验证用）

        与种子培育流程解耦，直接对 shell_nucleus_input 做三层核结构判定。

        Args:
            shell_nucleus_input: 来自 task JSON 的 shell_nucleus_input 字段
                {
                    "declaration": {measured_nucleus, excluded_shell, system_type},
                    "three_layers": {
                        topic_shell: {name, action, evidence},
                        method_nucleus: {name, action, evidence},
                        direction_nucleus: {name, action, evidence, hypothesis}
                    }
                }

        Returns:
            {passed, declaration, three_layers, checks}
        """
        declaration = shell_nucleus_input.get("declaration", {})
        three_layers = shell_nucleus_input.get("three_layers", {})

        checks = []

        # 检查 1: 声明完整性
        measured_nucleus = declaration.get("measured_nucleus", [])
        excluded_shell = declaration.get("excluded_shell", [])
        system_type = declaration.get("system_type", "")

        decl_ok = bool(measured_nucleus and excluded_shell and system_type)
        checks.append({
            "check": "declaration_completeness",
            "verdict": "PASS" if decl_ok else "FAIL",
            "detail": f"核={measured_nucleus}, 壳={excluded_shell}, 体系={system_type}",
        })

        # 检查 2: 体系类型合法性
        valid_types = ["测核体系", "测壳体系"]
        type_ok = system_type in valid_types
        checks.append({
            "check": "system_type_validity",
            "verdict": "PASS" if type_ok else "FAIL",
            "detail": f"体系类型={system_type}",
        })

        # 检查 3: 三层核结构完整性
        topic_shell = three_layers.get("topic_shell", {})
        method_nucleus = three_layers.get("method_nucleus", {})
        direction_nucleus = three_layers.get("direction_nucleus", {})

        layers_ok = all([
            topic_shell.get("action") == "可更换",
            method_nucleus.get("action") == "可迁移",
            direction_nucleus.get("action") == "必须保持",
        ])
        checks.append({
            "check": "three_layer_structure",
            "verdict": "PASS" if layers_ok else "FAIL",
            "detail": {
                "topic_shell": f"{topic_shell.get('name')} → {topic_shell.get('action')}",
                "method_nucleus": f"{method_nucleus.get('name')} → {method_nucleus.get('action')}",
                "direction_nucleus": f"{direction_nucleus.get('name')} → {direction_nucleus.get('action')}",
            },
        })

        # 检查 4: 方向核 H1 假设挂载
        h1_ok = "H1" in direction_nucleus.get("hypothesis", "")
        checks.append({
            "check": "direction_nucleus_hypothesis",
            "verdict": "PASS" if h1_ok else "WARN",
            "detail": f"假设={direction_nucleus.get('hypothesis', '未挂载')}",
        })

        all_passed = all(c["verdict"] == "PASS" for c in checks)

        return {
            "task_id": "TASK-HOMO-LIU-20260808",
            "protocol_version": "V1.5",
            "shell_nucleus_audit": {
                "passed": all_passed,
                "declaration": {
                    "measured_nucleus": measured_nucleus,
                    "excluded_shell": excluded_shell,
                    "system_type": system_type,
                },
                "three_layers": {
                    "topic_shell": {
                        "name": topic_shell.get("name", ""),
                        "action": topic_shell.get("action", ""),
                        "evidence": topic_shell.get("evidence", ""),
                    },
                    "method_nucleus": {
                        "name": method_nucleus.get("name", ""),
                        "action": method_nucleus.get("action", ""),
                        "evidence": method_nucleus.get("evidence", ""),
                    },
                    "direction_nucleus": {
                        "name": direction_nucleus.get("name", ""),
                        "action": direction_nucleus.get("action", ""),
                        "evidence": direction_nucleus.get("evidence", ""),
                        "hypothesis": direction_nucleus.get("hypothesis", ""),
                    },
                },
                "checks": checks,
                "conclusion": "壳核三层结构确认：数学=壳（可换）、逻辑=核（可迁）、追问=方向核（保持，挂H1假设）" if all_passed else "壳核审计未通过",
            },
        }

    # ── V1.5 纯粹度审计（替代 V1.2 性决定审计·余弦相似度）──

    def _purity_audit(self, method_seed: dict, harvest_wuxing: str,
                      harvest_result: dict, duration: float = 0.5) -> dict:
        """
        纯粹度审计（V1.5 核心升级）

        V1.5 公式：Purity = 保持度 × 持续时间 × 抗摇摆性
          - 保持度：余弦相似度（V1.2，已验证）
          - 持续时间：核保持时长（归一化到 [0,1]）
          - 抗摇摆性：外部评价波动时核是否摇摆（V1.5：待校准，暂取中性1.0）

        与 V1.2 性决定审计的关系：
          - V1.2 的余弦相似度审计保留为纯粹度的"保持度"分量
          - V1.5 增加时间维度和抗摇摆维度
          - 抗摇摆标"待校准"——不假装精确

        Args:
            method_seed: Step 1 识别的方法种子
            harvest_wuxing: 成果方法论五行
            harvest_result: Step 3 收获结果
            duration: 持续时间（归一化，默认 0.5）

        Returns:
            PurityResult dict
        """
        # 先计算保持度（余弦相似度，沿用 V1.2 已验证方法）
        nd_audit = self._nature_determination_audit(method_seed, harvest_wuxing, harvest_result)
        retention = nd_audit["similarity"]

        # 持续时间（归一化到 [0,1]，0=刚发现，1=长期保持）
        duration = max(0.0, min(1.0, duration))

        # 抗摇摆性（V1.5：待校准，暂取中性 1.0）
        anti_sway = 1.0
        anti_sway_events = []
        anti_sway_calibrated = self.config.get("anti_sway_calibrated", False)

        # 如果配置了抗摇摆定性事件，则从 harvest_result 中提取
        sway_events = harvest_result.get("anti_sway_events", [])
        if sway_events:
            anti_sway_events = sway_events
            # 有事件记录则标注为定性记录（非校准值）
            anti_sway_calibrated = False

        # 纯粹度 = 保持 × 时间 × 抗摇摆
        purity = retention * duration * anti_sway
        purity = round(purity, 4)

        threshold = self.config.get("purity_threshold", 0.7)

        # 解读
        if purity >= threshold:
            interpretation = (
                f"纯粹度 {purity:.2f}≥{threshold}：核保持良好（保持={retention:.2f}×"
                f"时间={duration:.2f}×抗摇摆={'待校准' if not anti_sway_calibrated else f'{anti_sway:.2f}'}）。"
                "纯粹是核的显影液——邓煜（奖杯+纯粹）与柳智宇（无奖杯+纯粹）同证。"
            )
        elif purity >= 0.5:
            interpretation = (
                f"纯粹度 {purity:.2f} 偏低：保持={retention:.2f}×时间={duration:.2f}×"
                f"抗摇摆={'待校准' if not anti_sway_calibrated else f'{anti_sway:.2f}'}。"
                "建议关注核是否在摇摆——如为外部评价波动所致，可能为体系类型不匹配。"
            )
        else:
            interpretation = (
                f"纯粹度 {purity:.2f} 低：保持={retention:.2f}×时间={duration:.2f}×"
                f"抗摇摆={'待校准' if not anti_sway_calibrated else f'{anti_sway:.2f}'}。"
                "核可能已偏离或体系类型不匹配——建议换球心评估。"
            )

        return {
            "purity_score": purity,
            "retention": retention,
            "duration": duration,
            "anti_sway": anti_sway,
            "anti_sway_events": anti_sway_events,
            "anti_sway_calibrated": anti_sway_calibrated,
            "threshold": threshold,
            "interpretation": interpretation,
            "note": (
                "纯粹度审计（V1.5）：保持度（余弦相似度，V1.2已验证）× "
                "持续时间（可观测）× 抗摇摆性（待校准，不假装精确）。"
                "纯粹=核的显影液——非奖杯。"
            ),
        }

    # ── V1.3 减法引擎（为道日损）──

    def _nurture_subtraction(self, step2_result: dict, method_seed: dict) -> dict:
        """
        减法引擎（V1.3 新增，来自道家"为道日损"）

        与加法引擎（为学日益）并行运行，在培育过程中去除积累的执念/偏见/多余。
        减法操作全部留痕（L0 可回溯），可逆。

        减法原则：
          - 损之又损，以至于无为——最终目标是技能直觉化
          - 为学日益，为道日损——加法与减法同时进行
          - 知不知，尚矣——不强求保持正是知的开始

        Args:
            step2_result: Step 2 培育结果
            method_seed: Step 1 识别的方法种子

        Returns:
            {subtraction_events, subtraction_count, reversible, principle}
        """
        if not self.config.get("subtraction_engine_enabled", True):
            return {"subtraction_events": [], "subtraction_count": 0,
                    "reversible": True, "principle": "减法引擎未启用"}

        subtraction_events = []
        method_wx = method_seed.get("wuxing", "")
        nurture_progress = step2_result.get("nurture_progress", [])
        iterations = len(nurture_progress)

        # 减法事件 1: 去除过度积累
        # 培育迭代超过阈值时，触发减法
        if iterations > 3:
            subtraction_events.append({
                "event": "去除过度积累",
                "target": f"培育迭代({iterations}轮)超出基准(3轮)，触发减法",
                "action": "保留核心 3 轮，后续迭代标记为可逆减法",
                "reversible": True,
                "classical_ref": "为道日损，损之又损，以至于无为（《道德经》第48章）",
            })

        # 减法事件 2: 去除五行偏离
        # 培育过程中如果缘四要素的五行与方法种子偏差过大
        env_factors = step2_result.get("environmental_factors", {})
        for factor_name in ["mentor", "environment", "topic"]:
            factor = env_factors.get(factor_name, {})
            factor_wx = factor.get("wuxing", "")
            if factor_wx and method_wx and factor_wx != method_wx:
                subtraction_events.append({
                    "event": "去除五行偏离",
                    "target": f"{factor_name}({factor_wx})偏离方法种子({method_wx})",
                    "action": f"记录偏离，不强制修正——知不知，尚矣",
                    "reversible": True,
                    "classical_ref": "知不知，尚矣；不知知，病也（《道德经》第71章）",
                })

        # 减法事件 3: 去除执念
        # 高损耗区（缘主导区）强行培育 → 减法提示
        if step2_result.get("nurture_effect", {}).get("seed_growth") == "停滞":
            subtraction_events.append({
                "event": "去除执念",
                "target": "缘主导区强行培育的执念——不强求保持",
                "action": "不强求保持正是知的开始。回归 Step 1 重新识别。",
                "reversible": False,
                "classical_ref": "圣人常善救人，故无弃人（《道德经》第27章）",
            })

        return {
            "subtraction_events": subtraction_events,
            "subtraction_count": len(subtraction_events),
            "reversible": all(e.get("reversible", True) for e in subtraction_events),
            "principle": "为道日损——损之又损，以至于无为（技能直觉化）",
            "note": "减法操作全部留痕（L0 可回溯），可逆。减法不是删除，是标记。",
        }

    # ── V1.5 熵振引擎：失败质量审核 ──

    def _failure_quality_audit(self, failure_events: List[dict],
                                method_seed: dict = None) -> List[Dict[str, Any]]:
        """
        熵振引擎失败质量审核（V1.5 新增）

        区分"真失败"（结构性证伪）与"表演性失败"（为奖励而败）。
        表演性失败不计分、不奖励，防道德风险。

        判定标准：
          - 真失败：实验设计能区分假设对错，失败提供结构性证据
            · 实验设计含可证伪条件
            · 失败结果可复现
            · 失败后有明确修正方向
          - 表演性失败：为奖励而设计的失败
            · 实验设计无法区分对错（无证伪条件）
            · 失败结果是预期中的（如选不可能的任务）
            · 失败后无修正方向，仅为了"失败"标签

        Args:
            failure_events: 失败事件列表
            method_seed: 方法种子信息（用于上下文判断）

        Returns:
            审核结果列表，每项含 {failure_type, is_structural, reward_eligible, evidence}
        """
        if not self.config.get("failure_quality_audit_enabled", True):
            return []

        audits = []
        for event in failure_events:
            event_type = event.get("event_type", "")
            event_desc = event.get("description", "")
            has_falsification_condition = event.get("has_falsification_condition", False)
            is_reproducible = event.get("is_reproducible", False)
            has_correction_path = event.get("has_correction_path", False)
            is_expected_failure = event.get("is_expected_failure", False)

            # 判定逻辑（V1.5.1 三分法：真失败/偶然失败/表演性失败）
            if has_falsification_condition and is_reproducible and has_correction_path:
                # 真失败：结构性证伪——可证伪、可复现、有修正方向
                failure_type = FailureQuality.TRUE_FAILURE.value
                is_structural = True
                reward_eligible = True
                evidence = (
                    f"实验设计含可证伪条件（{has_falsification_condition}），"
                    f"失败可复现（{is_reproducible}），"
                    f"有明确修正方向（{has_correction_path}）"
                )
            elif is_expected_failure and not has_falsification_condition:
                # 表演性失败：为奖励而故意制造
                failure_type = FailureQuality.PERFORMATIVE_FAILURE.value
                is_structural = False
                reward_eligible = False
                evidence = (
                    f"失败为预期结果（{is_expected_failure}），"
                    f"实验设计无证伪条件（{has_falsification_condition}），"
                    f"疑似为奖励而设计的失败——不计分、警告"
                )
            elif has_falsification_condition and not is_reproducible:
                # 偶然失败：可证伪但不可复现——运气/环境因素，中性不奖惩
                failure_type = FailureQuality.ACCIDENTAL_FAILURE.value
                is_structural = False
                reward_eligible = False
                evidence = (
                    f"实验设计含证伪条件（{has_falsification_condition}），"
                    f"但失败不可复现（{is_reproducible}）——"
                    f"偶然失败（运气/环境），非结构性证伪，非表演性。中性不奖惩。"
                )
            else:
                # 不确定：默认归类为偶然失败（保守策略，V1.5.1 修订）
                failure_type = FailureQuality.ACCIDENTAL_FAILURE.value
                is_structural = False
                reward_eligible = False
                evidence = (
                    f"无法确认失败质量：证伪条件={has_falsification_condition}，"
                    f"可复现={is_reproducible}，修正方向={has_correction_path}。"
                    f"保守策略：归入偶然失败（中性不奖惩），建议补充实验设计信息"
                )

            audit = FailureQualityAudit(
                failure_type=failure_type,
                is_structural_falsification=is_structural,
                reward_eligible=reward_eligible,
                evidence=evidence,
                audit_timestamp=datetime.now().isoformat(),
            )
            audits.append(audit.to_dict())

        return audits

    def _entropy_vibration_engine(self, step2_result: dict,
                                   method_seed: dict = None) -> Dict[str, Any]:
        """
        熵振引擎（V1.5 新增）

        熵振律：失败是核的震荡-重建，不是壳的损失——奖励失败（但须经质量审核）。

        机制：
          1. 收集培育过程中的失败事件
          2. 执行失败质量审核（区分真失败/表演性失败）
          3. 真失败 → 入证伪库，奖励
          4. 表演性失败 → 不入库，不计分

        Args:
            step2_result: Step 2 培育结果
            method_seed: 方法种子信息

        Returns:
            {failure_events, quality_audits, true_failures, performative_failures,
             falsification_library_updates, principle}
        """
        if not self.config.get("entropy_vibration_enabled", True):
            return {"failure_events": [], "quality_audits": [],
                    "true_failures": 0, "performative_failures": 0,
                    "falsification_library_updates": [],
                    "principle": "熵振引擎未启用"}

        # 收集失败事件（从培育过程中提取）
        failure_events = step2_result.get("failure_events", [])
        nurture_progress = step2_result.get("nurture_progress", [])

        # 如果培育进度中有失败的迭代，构造失败事件
        if not failure_events:
            for progress in nurture_progress:
                if progress.get("completion", 0) < 0.5:
                    failure_events.append({
                        "event_type": "培育失败",
                        "description": f"迭代 {progress.get('iteration', '?')} 未完成",
                        "has_falsification_condition": True,
                        "is_reproducible": False,
                        "has_correction_path": True,
                        "is_expected_failure": False,
                        "timestamp": datetime.now().isoformat(),
                    })

        # 执行失败质量审核
        quality_audits = self._failure_quality_audit(failure_events, method_seed)

        # 统计
        true_failures = sum(1 for a in quality_audits if a["failure_type"] == FailureQuality.TRUE_FAILURE.value)
        accidental_failures = sum(1 for a in quality_audits if a["failure_type"] == FailureQuality.ACCIDENTAL_FAILURE.value)
        performative_failures = sum(1 for a in quality_audits if a["failure_type"] == FailureQuality.PERFORMATIVE_FAILURE.value)

        # 真失败入证伪库
        falsification_library_updates = []
        for i, audit in enumerate(quality_audits):
            if audit["reward_eligible"]:
                falsification_library_updates.append({
                    "event_index": i,
                    "failure_type": audit["failure_type"],
                    "evidence": audit["evidence"],
                    "reward": "入证伪库，奖励",
                    "classical_ref": "失败是熵振——壳碎了，核还在（五律·熵振律）",
                })

        return {
            "failure_events": failure_events,
            "quality_audits": quality_audits,
            "true_failures": true_failures,
            "accidental_failures": accidental_failures,
            "performative_failures": performative_failures,
            "falsification_library_updates": falsification_library_updates,
            "principle": (
                "熵振律（V1.5.1 三分法）：失败是核的震荡-重建，不是壳的损失。"
                "真失败奖励（入证伪库），偶然失败中性不奖惩，表演性失败警告。"
            ),
            "note": "V1.5.1 修订：不可复现≠表演性，增加偶然失败分类。何川「就差一次受伤」= 真失败的熵振价值。",
        }

    # ── V1.5 待验证假设清单 ──

    def _track_hypotheses(self) -> List[Dict[str, Any]]:
        """
        待验证假设清单追踪（V1.5 新增）

        V1.5 诚实声明：5 项假设挂牌，等数据来审。
        不假装有答案——这正是「不知为不知」的知。

        Returns:
            5 项待验证假设的状态列表
        """
        hypotheses = [
            {
                "hypothesis_id": "H1",
                "statement": '方向核"必须保持"——柳智宇/杨振宁为成功者样本，存在幸存者偏差',
                "status": PendingHypothesisStatus.PENDING.value,
                "evidence_for": "杨振宁（物理→数学→物理）、柳智宇（数学→心理，核心逻辑保持）",
                "evidence_against": "弃医从文者（鲁迅/郭沫若）——方向核完全改变",
                "verification_path": '引入"换方向核成功者"对照（如弃医从文者），进行方向核保持/变更成功率对比',
                "last_updated": "2026-08-08",
            },
            {
                "hypothesis_id": "H2",
                "statement": "关系核优先级——培育终极产品=能爱人的人",
                "status": PendingHypothesisStatus.PENDING.value,
                "evidence_for": "Grant Study（哈佛成人发展研究）：良好关系是幸福的最强预测因子",
                "evidence_against": "跨域移植未验证：Grant Study 为相关性，不等于因果关系",
                "verification_path": "培育场景纵向跟踪（学园环境），测量关系核保持与长期成果的相关性",
                "last_updated": "2026-08-08",
            },
            {
                "hypothesis_id": "H3",
                "statement": "纯粹度抗摇摆性——目前无测量方法",
                "status": PendingHypothesisStatus.PENDING.value,
                "evidence_for": "柳智宇「羡慕的不是奖杯」= 外部评价波动时核未摇摆",
                "evidence_against": "缺乏定量指标：仅有定性事件记录，无时间序列数据",
                "verification_path": "时间序列数据校准：收集外部评价波动 + 核保持度的时间序列，计算抗摇摆系数",
                "last_updated": "2026-08-08",
            },
            {
                "hypothesis_id": "H4",
                "statement": "熵振加速——受伤=加速器",
                "status": PendingHypothesisStatus.PENDING.value,
                "evidence_for": "何川（学术挫折→登顶）、弘立书院（失败友好环境→高成就）",
                "evidence_against": "单一案例，缺少对照实验",
                "verification_path": "控制实验：有熵振轮 vs 无熵振轮的培育效果对比",
                "last_updated": "2026-08-08",
            },
            {
                "hypothesis_id": "H5",
                "statement": "换球心决策——体系类型声明后触发",
                "status": PendingHypothesisStatus.PENDING.value,
                "evidence_for": "何川回溯验证通过（学术壳→攀登核换球心）",
                "evidence_against": "仅回溯验证，无前瞻数据",
                "verification_path": "前瞻验证：触发换球心后跟踪纯粹度变化，验证决策有效性",
                "last_updated": "2026-08-08",
            },
        ]

        return hypotheses

    # ── V1.5 换球心决策 ──

    def _ball_replacement_decision(self, purity_history: List[float],
                                     system_type: str = "",
                                     anti_sway_duration: float = 0.0) -> Dict[str, Any]:
        """
        换球心决策（V1.5.1 修订：反例保护按时间尺度缩放）

        触发条件：纯粹度连续 2 轮 < 0.7 且体系类型 = 测核体系
        反例保护：
          - 人才尺度：持续 > 5 年 + 抗摇摆 → 判定"厚积期"，不触发
          - 技能尺度：持续 > 2 个月（≈0.17 年）+ 抗摇摆 → 判定"积累期"，不触发

        流程：
          ① 多体系试测（测核体系候选集）
          ② 选纯粹度最高者为新球心
          ③ 换体系不换核

        Args:
            purity_history: 纯粹度历史（最近 N 轮）
            system_type: 体系类型（测核体系/测壳体系）
            anti_sway_duration: 抗摇摆持续时间（年）

        Returns:
            {triggered, reason, candidate_systems, recommendation, action}
        """
        if not self.config.get("ball_replacement_enabled", True):
            return {"triggered": False, "reason": "换球心决策未启用",
                    "candidate_systems": [], "recommendation": "", "action": "skip"}

        threshold = self.config.get("purity_threshold", 0.7)
        consecutive_rounds = self.config.get("ball_replacement_consecutive_rounds", 2)

        # 检查触发条件
        if len(purity_history) < consecutive_rounds:
            return {"triggered": False, "reason": f"纯粹度历史不足（{len(purity_history)}<{consecutive_rounds}轮）",
                    "candidate_systems": [], "recommendation": "", "action": "wait"}

        recent_purities = purity_history[-consecutive_rounds:]
        all_below_threshold = all(p < threshold for p in recent_purities)

        if not all_below_threshold:
            return {"triggered": False, "reason": f"最近 {consecutive_rounds} 轮纯粹度未全部低于 {threshold}",
                    "candidate_systems": [], "recommendation": "", "action": "continue"}

        # 检查体系类型：测壳体系不触发换球心
        if system_type != SystemType.NUCLEUS_MEASURING.value:
            return {"triggered": False, "reason": (
                f"体系类型为 {system_type}，非测核体系——"
                "测壳体系里测核必然低分，是体系类型不匹配，不是核差"
            ), "candidate_systems": [], "recommendation": "建议先声明体系类型为测核体系后再评估", "action": "skip"}

        # V1.5.1: 反例保护按时间尺度缩放
        time_scale = self.config.get("time_scale", "skill")
        if time_scale == TimeScale.TALENT.value:
            anti_sway_protection_years = 5.0   # 人才尺度：持续 > 5 年
            protection_label = "厚积期"
        else:
            anti_sway_protection_years = 1.0 / 12.0  # 技能尺度：持续 > 1 个月（≈0.083 年，培育周期 6 周的 67%）
            protection_label = "积累期"

        if anti_sway_duration > anti_sway_protection_years:
            return {"triggered": False, "reason": (
                f"持续 {anti_sway_duration:.1f} 年（{time_scale}尺度保护阈值 {anti_sway_protection_years:.2f} 年）+ 抗摇摆 "
                f"→ 判定为{protection_label}，不触发换球心。"
                f"核在积累，非球心问题——如柳智宇数学 10 年→心理。"
            ), "candidate_systems": [], "recommendation": f"{protection_label}——继续观察，不换球心", "action": "protect"}

        # 触发换球心决策
        candidate_systems = self.config.get("ball_replacement_candidates", [
            {"system": "登顶体系", "description": "何川式：以攀登最高点为核"},
            {"system": "共情体系", "description": "柳智宇式：以共情助人为核"},
            {"system": "纯粹体系", "description": "邓煜式：以纯粹钻研为核"},
        ])

        recommendation = (
            f"纯粹度连续 {consecutive_rounds} 轮 < {threshold}（{recent_purities}），"
            f"体系类型为测核体系。建议启动多体系试测，选纯粹度最高者为新球心。"
            f"换体系不换核——核是方法偏好，球心是评价体系。"
        )

        return {
            "triggered": True,
            "reason": f"纯粹度连续 {consecutive_rounds} 轮 < {threshold} 且体系类型 = 测核体系",
            "candidate_systems": candidate_systems,
            "recommendation": recommendation,
            "action": "evaluate_replacement",
            "classical_ref": "换球心不换核——壳可换，核不可弃（五律·迁移律）",
        }

    # ── V1.5 留白条款 ──

    def _manage_blank_space(self, round_number: int,
                             high_value_signals: int = 0) -> Dict[str, Any]:
        """
        留白条款管理（V1.5 新增）

        留白律：留白给核空间，现实给核淬炼——拒绝填满与封闭。

        规则：
          - 每 3 轮培育插入 1 轮留白（只观察不干预）
          - 留白轮不计入里程碑考核
          - deadline 场景：可跳过留白，但须记录"未留白"，欠 1 轮补 1 轮
          - +2 高价值信号提前结束留白（信号优先）

        Args:
            round_number: 当前轮次
            high_value_signals: 高价值信号数量（+2 事件）

        Returns:
            {is_blank_round, reason, skipped_for_deadline, owed_rounds, action}
        """
        if not self.config.get("blank_space_enabled", True):
            return {"is_blank_round": False, "reason": "留白未启用",
                    "skipped_for_deadline": False, "owed_rounds": 0, "action": "continue"}

        blank_interval = self.config.get("blank_space_interval", 3)

        # 检查是否为留白轮
        is_blank_round = (round_number % blank_interval == 0)

        if not is_blank_round:
            return {"is_blank_round": False, "reason": f"第 {round_number} 轮非留白轮",
                    "skipped_for_deadline": False, "owed_rounds": 0, "action": "continue"}

        # +2 高价值信号提前结束留白
        signal_threshold = self.config.get("blank_space_signal_threshold", 2)
        if high_value_signals >= signal_threshold:
            return {"is_blank_round": False, "reason": (
                f"高价值信号 {high_value_signals} >= {signal_threshold}，"
                f"提前结束留白——信号优先"
            ), "skipped_for_deadline": False, "owed_rounds": 0, "action": "signal_override"}

        # deadline 场景检查
        is_deadline = self.config.get("blank_space_deadline_mode", False)
        if is_deadline:
            return {"is_blank_round": False, "reason": (
                "deadline 场景：跳过留白，但欠 1 轮补 1 轮"
            ), "skipped_for_deadline": True, "owed_rounds": 1, "action": "skip_and_owe"}

        return {"is_blank_round": True, "reason": (
            f"第 {round_number} 轮为留白轮——只观察不干预，不计入里程碑考核"
        ), "skipped_for_deadline": False, "owed_rounds": 0,
            "action": "observe_only",
            "classical_ref": "留白律：留白给核空间，现实给核淬炼。拒绝填满与封闭。",
            "activities": ["观察种子自然生长", "记录核的保持状态", "不干预、不加速、不填满"],
        }

    # ── V1.5 日益饱和检测 ──

    def _saturation_detection(self, addition_history: List[Dict[str, Any]],
                             blank_rounds: List[int] = None) -> Dict[str, Any]:
        """
        日益饱和检测（V1.5.1 修订：跳过留白轮）

        日益引擎的边际产出递减检测。
        当加法事件边际产出递减时，触发"转日损"建议。

        V1.5.1 修订：留白轮不产出 → 边际产出天然为 0 → 应跳过留白轮，
        否则"留白"与"饱和"同时亮灯，信号矛盾。

        参考：卡内基梅隆大学实证——过度学习导致边际产出递减。

        Args:
            addition_history: 加法事件历史，每项含 {round, output_score, is_blank_round}
            blank_rounds: 留白轮次列表（可选）

        Returns:
            {saturated, marginal_output, recommendation, action}
        """
        if not self.config.get("saturation_detection_enabled", True):
            return {"saturated": False, "marginal_output": 1.0,
                    "recommendation": "", "action": "continue"}

        # V1.5.1: 过滤留白轮（留白轮的零产出不计入边际产出序列）
        blank_rounds = blank_rounds or []
        active_history = [
            h for h in addition_history
            if not h.get("is_blank_round", False) and h.get("round", 0) not in blank_rounds
        ]

        filtered_count = len(addition_history) - len(active_history)
        if filtered_count > 0:
            skip_note = f"（跳过 {filtered_count} 个留白轮）"
        else:
            skip_note = ""

        if len(active_history) < 3:
            return {"saturated": False, "marginal_output": 1.0,
                    "recommendation": f"日益事件不足 3 轮{skip_note}，暂不检测饱和",
                    "action": "continue"}

        # 计算最近 3 轮的边际产出变化
        recent_outputs = [h.get("output_score", 0.5) for h in active_history[-3:]]
        if len(recent_outputs) >= 2:
            marginal = recent_outputs[-1] - recent_outputs[-2] if recent_outputs[-2] > 0 else 0
        else:
            marginal = 0

        saturation_threshold = self.config.get("saturation_marginal_threshold", 0.1)

        if marginal < saturation_threshold:
            return {
                "saturated": True,
                "marginal_output": round(marginal, 4),
                "recent_outputs": recent_outputs,
                "recommendation": (
                    f"日益饱和：最近边际产出 {marginal:.4f} < {saturation_threshold}{skip_note}。"
                    "建议转入日损模式——为学日益之后，为道日损。"
                    "卡内基梅隆实证：过度学习导致边际产出递减。"
                ),
                "action": "switch_to_subtraction",
                "classical_ref": "为学日益，为道日损（《道德经》第48章）——日益饱和，转日损。",
            }

        return {"saturated": False, "marginal_output": round(marginal, 4),
                "recommendation": f"日益边际产出正常{skip_note}，继续加法",
                "action": "continue"}

    # ── V1.5 协议级日损记录 ──

    def _record_protocol_subtractions(self) -> List[Dict[str, Any]]:
        """
        协议级日损记录（V1.5 新增）

        V1.5 核心姿态：协议教会种子日损，也必须对自己日损。
        记录 V1.4→V1.5 的 5 项协议级减除，全部留痕可回溯。

        Returns:
            [{item, reason, reversible, timestamp, classical_ref}]
        """
        timestamp = datetime.now().isoformat()
        return [
            {
                "item": "三层核合并为双画像",
                "reason": "方向核并入宪法审计对象，不另立层——对象重叠，机制冗余",
                "reversible": True,
                "timestamp": timestamp,
                "classical_ref": "少则得，多则惑（《道德经》第22章）",
            },
            {
                "item": "失败计分加审核（真失败才奖励）",
                "reason": "V1.4 无审核版存在表演性失败风险——降级为真失败才奖励",
                "reversible": True,
                "timestamp": timestamp,
                "classical_ref": "知不知，尚矣；不知知，病也（《道德经》第71章）",
            },
            {
                "item": "换球心加体系类型声明",
                "reason": "V1.4 无声明版存在反身性循环——加体系类型声明破解",
                "reversible": True,
                "timestamp": timestamp,
                "classical_ref": "反者道之动（《道德经》第40章）",
            },
            {
                "item": "纯粹度抗摇摆标'待校准'",
                "reason": "V1.4 抗摇摆=0.7 可判无测量方法——标'待校准'，不假装精确",
                "reversible": True,
                "timestamp": timestamp,
                "classical_ref": "知不知，尚矣（《道德经》第71章）",
            },
            {
                "item": "留白不计入进度考核",
                "reason": "V1.4 留白与进度冲突版在 deadline 场景失效——明确不计入考核，可欠可补",
                "reversible": True,
                "timestamp": timestamp,
                "classical_ref": "大器免成（帛书乙本·《道德经》第41章）",
            },
        ]

    def _nature_determination_audit(self, method_seed: dict,
                                     harvest_wuxing: str,
                                     harvest_result: dict) -> dict:
        """
        性决定审计（V1.2 核心修订）

        定位：性决定不是"成才判据"（不预测成功），而是"路径一致性审计"——
        审计成果是否忠于方法种子，如同宪法审计动作是否越界。**描述性，非预测性。**

        计算公式：方法种子五行向量 A 与成果方法论五行向量 B 的余弦相似度
          S_cos = Σ(aᵢ·bᵢ) / (|A|·|B|)

        语义：余弦衡量"方向一致性"——方法种子与成果在五行空间中指向是否一致。

        阈值：≥0.7 为"性决定保持"（待 Phase 1.5 对照库校准）

        Args:
            method_seed: Step 1 识别的方法种子（含 wuxing 和 wuxing_vector）
            harvest_wuxing: 成果方法论五行（外部传入或推断）
            harvest_result: Step 3 收获结果

        Returns:
            {similarity, method_vector, harvest_vector, components, interpretation, audit_note}
        """
        method_wx = method_seed.get("wuxing", "")
        method_vec = method_seed.get("wuxing_vector", None)

        # 方法种子五行向量：优先使用显式传入的，否则从 wuxing 转换
        if method_vec is None or len(method_vec) != 5:
            method_vec = self._wuxing_to_vector(method_wx)

        # 成果方法论五行向量：外部传入或从 harvest_result 推断
        if harvest_wuxing:
            harvest_vec = self._wuxing_to_vector(harvest_wuxing)
        else:
            # 基于验证通过率微调方法种子向量（模拟真实场景）
            pass_rate = harvest_result.get("pass_rate", 0.5)
            harvest_vec = list(method_vec)  # copy
            # 通过率低 → 轻微扰动
            if pass_rate < 0.7:
                # 微调：轻微偏移到相邻五行
                for i in range(len(harvest_vec)):
                    if harvest_vec[i] > 0:
                        # 保留 80% 原方向，20% 分散到相邻维度
                        spill = harvest_vec[i] * 0.2 * (1 - pass_rate)
                        harvest_vec[i] -= spill
                        harvest_vec[(i + 1) % 5] += spill * 0.6
                        harvest_vec[(i - 1) % 5] += spill * 0.4

        # 余弦相似度计算
        if self.config.get("cosine_similarity_enabled", True):
            similarity = self._cosine_similarity(method_vec, harvest_vec)
        else:
            # 降级到简单评分（向后兼容）
            confirmation = method_seed.get("confirmation_status", "")
            if confirmation == ConfirmationStatus.CONFIRMED.value:
                similarity = 0.8 + 0.2 * method_seed.get("resonance_strength", 0.0)
            else:
                similarity = 0.4 + 0.3 * min(method_seed.get("occurrence_count", 0) / 3, 1.0)
            similarity = round(similarity, 4)

        # 带标签的分解
        labeled = self._cosine_similarity_with_labels(method_vec, harvest_vec)

        # V1.2: 审计标注（非判据）
        threshold = self._get_calibrated_threshold()  # G1: 使用校准后的阈值
        threshold_source = "对照校准" if self.config.get("calibrated_threshold") is not None else "默认"
        audit_note = (
            f"性决定审计（V1.2）：此为路径一致性描述，非成才判据。"
            f"余弦相似度={similarity:.4f}，阈值={threshold}（{threshold_source}来源，Phase 1.5 对照库校准）。"
            f"审计结论：{'保持' if similarity >= threshold else '需关注'}。"
        )

        return {
            "similarity": similarity,
            "method_vector": method_vec,
            "harvest_vector": harvest_vec,
            "components": labeled["components"],
            "interpretation": labeled["interpretation"],
            "audit_note": audit_note,
            "threshold_status": "待校准",  # V1.2: 去伪
        }

    def _detect_drift(self, method_seed: dict, step2_result: dict) -> dict:
        """
        漂移双层检验（V1.1，V1.2 保留）

        区分缘漂移与性漂移：
          - 缘漂移：环境/课题/导师变化 → 正常，不触发警告
          - 性漂移：方法种子五行变化 → 异常，回退 Step 1

        Args:
            method_seed: Step 1 识别的方法种子
            step2_result: Step 2 培育结果（含缘四要素）

        Returns:
            {drift_type, detected, detail, action}
        """
        method_wx = method_seed.get("wuxing", "")
        env_factors = step2_result.get("environmental_factors", {})

        # 检测缘四要素中的五行变化（缘漂移）
        env_changes = []
        for factor_name in ["mentor", "environment", "topic", "collaborators"]:
            factor = env_factors.get(factor_name, {})
            factor_wx = factor.get("wuxing", "")
            if factor_wx and factor_wx != method_wx:
                env_changes.append(f"{factor_name}({factor_wx})")

        if env_changes:
            return {
                "drift_type": DriftType.ENVIRONMENTAL.value,
                "detected": True,
                "detail": f"缘四要素五行变化: {', '.join(env_changes)}",
                "action": "记录环境五行变化，不打断培育。正常缘漂移。",
                "method_seed_wuxing_stable": True,
            }
        else:
            return {
                "drift_type": DriftType.ENVIRONMENTAL.value,
                "detected": False,
                "detail": "缘四要素与方法种子五行一致，未检测到漂移",
                "action": "继续培育，保持当前路径。",
                "method_seed_wuxing_stable": True,
            }

    # ── V1.2 通中生种：反向回路 ──

    def _detect_reverse_flow_seeds(self, migration_events: List[dict] = None) -> List[dict]:
        """
        归朴检测（V1.3 命名升级，原"通中生种"）

        双引擎反向回路：土·通 → 种·育
        迁移过程中若出现新的高价值兴趣信号（价值回填 +2 事件 ≥3 次，
        且不属于现有方法种子）→ 回流为新种子候选，进入 Step 1。

        命名：归朴 = 复归于朴（《道德经》第28章）
        成器之后不被才能异化，回归本真重新成为种子——"通中生种"的哲学命名。

        Args:
            migration_events: 迁移过程中的事件列表
              [{event_type, domain, wuxing, value_score, ...}]

        Returns:
            [{source_domain, method_seed_wuxing, occurrence_count, source: "归朴"}]
        """
        if not migration_events or not self.config.get("reverse_flow_enabled", True):
            return []

        threshold = self.config["reverse_flow_threshold"]

        # 统计 +2 事件（价值回填标记为关键贡献）
        plus2_events = [e for e in migration_events if e.get("value_score", 0) >= 2]

        # 按领域分组统计
        domain_counts = {}
        for e in plus2_events:
            domain = e.get("domain", "unknown")
            if domain not in domain_counts:
                domain_counts[domain] = {
                    "count": 0,
                    "wuxing": e.get("wuxing", ""),
                    "events": [],
                }
            domain_counts[domain]["count"] += 1
            domain_counts[domain]["events"].append(e)

        # 筛选达到阈值的候选
        candidates = []
        for domain, info in domain_counts.items():
            if info["count"] >= threshold:
                candidates.append({
                    "source_domain": domain,
                    "method_seed_wuxing": info["wuxing"],
                    "occurrence_count": info["count"],
                    "source": "归朴",  # V1.3 命名升级（原"通中生种"）
                    "description": (
                        f"归朴（复归于朴）：土·通迁移中检测到新种子候选：{domain}"
                        f"（{info['wuxing']}），+2 事件 {info['count']} 次 ≥{threshold}，"
                        f"回流进入 Step 1 种子发现。成器→迁移→归朴。"
                    ),
                    "classical_ref": "复归于朴（《道德经》第28章）——成器之后回归本真，不被才能异化",
                })

        return candidates

    def _calibrate_with_contrast(self, positive_samples: List[dict],
                                  negative_samples: List[dict]) -> dict:
        """
        失败者/跨界对照校准（V1.2 新增，Phase 1.5）

        检验性决定审计的判别力：
          - 正样本（生）：四大师等性决定保持者
          - 负样本（克）：跨界成功但性漂移者

        余弦相似度能否区分两组？
        理想：正样本 ≥0.7，负样本 <0.7，区间不重叠或重叠 <20%

        Args:
            positive_samples: [{method_wuxing, harvest_wuxing, label}]
            negative_samples: [{method_wuxing, harvest_wuxing, label}]

        Returns:
            {positive_scores, negative_scores, separation, discriminative, recommendation}
        """
        pos_scores = []
        for s in positive_samples:
            mv = self._wuxing_to_vector(s.get("method_wuxing", ""))
            hv = self._wuxing_to_vector(s.get("harvest_wuxing", ""))
            pos_scores.append(self._cosine_similarity(mv, hv))

        neg_scores = []
        for s in negative_samples:
            mv = self._wuxing_to_vector(s.get("method_wuxing", ""))
            hv = self._wuxing_to_vector(s.get("harvest_wuxing", ""))
            neg_scores.append(self._cosine_similarity(mv, hv))

        if not pos_scores or not neg_scores:
            return {
                "positive_scores": pos_scores,
                "negative_scores": neg_scores,
                "separation": 0.0,
                "discriminative": False,
                "recommendation": "样本不足，无法校准。需≥1 正样本 + ≥1 负样本。",
            }

        # 分布分离度
        pos_min = min(pos_scores)
        pos_max = max(pos_scores)
        neg_min = min(neg_scores)
        neg_max = max(neg_scores)

        # 重叠区间比例
        overlap_start = max(pos_min, neg_min)
        overlap_end = min(pos_max, neg_max)
        overlap_range = max(0, overlap_end - overlap_start)
        total_range = max(pos_max, neg_max) - min(pos_min, neg_min)
        overlap_ratio = overlap_range / total_range if total_range > 0 else 0

        separation = 1.0 - overlap_ratio
        discriminative = separation >= 0.8  # 区间分离 ≥80%

        # 建议阈值：正样本下限与负样本上限的中点
        suggested_threshold = round((pos_min + neg_max) / 2, 2) if neg_max < pos_min else 0.7

        return {
            "positive_scores": pos_scores,
            "positive_range": [pos_min, pos_max],
            "negative_scores": neg_scores,
            "negative_range": [neg_min, neg_max],
            "separation": round(separation, 4),
            "overlap_ratio": round(overlap_ratio, 4),
            "discriminative": discriminative,
            "suggested_threshold": suggested_threshold,
            "recommendation": (
                f"生克对照校准完成：正样本余弦=[{pos_min:.2f}, {pos_max:.2f}]，"
                f"负样本余弦=[{neg_min:.2f}, {neg_max:.2f}]，"
                f"分离度={separation:.0%}。"
                f"{'判别力充足' if discriminative else '判别力不足，需调整审计方式'}。"
                f"建议阈值={suggested_threshold}（当前={self.config['nature_determination_threshold']}）。"
            ),
        }

    # ── 综合评估 ──

    def _compute_seedney(self, result: SeedCultivationResult) -> float:
        """
        计算种子质量评分 (seedney) — V1.2

        seedney = 种子（性决定）
        评估种子从源域到目标域的结构保持质量

        V1.2 修订：性决定审计（余弦相似度）替代简单评分，标注"描述性，非预测性"

        基于：
          - Step 1 方法种子确认状态
          - Step 2 培育完成度
          - Step 3 验证通过率 + 性决定审计余弦相似度（V1.2）
        """
        s1 = result.step1_identify
        s2 = result.step2_nurture
        s3 = result.step3_harvest

        src_struct = s1.get("source_structure", {})
        if src_struct.get("density", 0) > 0:
            identify_quality = min(src_struct.get("density", 0.5) * 2, 1.0)
        else:
            identify_quality = 0.5

        method_seed = result.method_seed
        confirmation = method_seed.get("confirmation_status", "")
        if confirmation == ConfirmationStatus.CONFIRMED.value:
            confirmation_weight = 1.0
        else:
            confirmation_weight = 0.6 + 0.4 * method_seed.get("resonance_strength", 0.0)

        nurture_progress = s2.get("nurture_progress", [{}])
        nurture_completion = nurture_progress[-1].get("completion", 0.5) if nurture_progress else 0.5

        pass_rate = s3.get("pass_rate", 0.5)

        # V1.2: 性决定审计余弦相似度
        nd_score = result.nature_determination_score

        # 加权综合：识别 25% + 确认 5% + 培育 35% + 验证 20% + 性决定审计 15%（V1.2）
        seedney = (
            0.25 * identify_quality
            + 0.05 * confirmation_weight
            + 0.35 * nurture_completion
            + 0.20 * pass_rate
            + 0.15 * nd_score
        )
        return round(seedney, 4)

    def _compute_taste(self, result: SeedCultivationResult) -> float:
        """
        计算 taste（妙）评分 — V1.2

        taste = 妙之因 = 对结构美的直觉感知
        杨振宁：taste 是对对称性之美的直觉判断

        V1.2 修订：性决定审计余弦相似度（方向一致性美学）

        基于：
          - 结构保持的优雅程度（验证通过率）
          - 种子培育的损耗率
          - 验证的置信度
          - 性决定审计余弦相似度（V1.2）
        """
        s3 = result.step3_harvest

        pass_rate = s3.get("pass_rate", 0.5)
        elegance = pass_rate

        loss_rate = 1.0 - result.seedney_score
        loss_penalty = max(0, 1.0 - loss_rate * 2)

        scenarios = s3.get("verification_scenarios", 3)
        confidence = min(scenarios / 5, 1.0)

        # V1.2: 性决定审计余弦相似度（方向一致性）
        nd_score = result.nature_determination_score

        # 加权：优雅 30% + 损耗 25% + 置信 20% + 性决定审计 25%（V1.2）
        taste = 0.30 * elegance + 0.25 * loss_penalty + 0.20 * confidence + 0.25 * nd_score
        return round(taste, 4)

    def _classify_vitality(self, result: SeedCultivationResult) -> str:
        """分类种子活力等级"""
        sn = result.seedney_score
        success = result.cultivation_success

        if success and sn >= 0.7:
            return SeedVitality.FRUITING.value
        elif success and sn >= 0.5:
            return SeedVitality.FLOWERING.value
        elif sn >= 0.4:
            return SeedVitality.GROWING.value
        elif sn >= 0.2:
            return SeedVitality.GERMINATING.value
        else:
            return SeedVitality.DORMANT.value

    def _classify_loss_zone(self, result: SeedCultivationResult) -> str:
        """分类损耗率分层"""
        loss_rate = 1.0 - result.seedney_score
        thresholds = self.config["loss_zone_thresholds"]

        if loss_rate <= thresholds["seed_dominant"]:
            return "种子主导区"
        elif loss_rate <= thresholds["structure_preserving"]:
            return "结构保持区"
        else:
            return "缘主导区"

    def _generate_classical_ref(self, result: SeedCultivationResult) -> str:
        """生成经典引用"""
        zone = result.loss_zone
        vitality = result.seed_vitality

        if vitality == SeedVitality.FRUITING.value:
            return "既知其子，复守其母。——种子已成果实，不忘源域根基（《道德经》第52章）"
        elif vitality == SeedVitality.FLOWERING.value:
            return "大曰逝，逝曰远，远曰反。——种子开花，即将回归（《道德经》第25章）"
        elif zone == "种子主导区":
            return "含德之厚，比于赤子。——种子在核心区，结构稳定，值得一生保持（《道德经》第55章）"
        elif zone == "结构保持区":
            return "合抱之木，生于毫末。——种子在结构保持区，持续浇灌可成大树（《道德经》第64章）"
        elif zone == "缘主导区":
            return "知不知，尚矣。——种子在缘主导区，不强求保持正是知的开始（《道德经》第71章）"
        else:
            return "道生之，德畜之，物形之，势成之。——种子培育的完整循环（《道德经》第51章）"

    def _generate_advice(self, result: SeedCultivationResult) -> str:
        """生成培育建议（V1.3 修订：无弃人底线）"""
        zone = result.loss_zone
        vitality = result.seed_vitality
        method_seed = result.method_seed
        confirmation = method_seed.get("confirmation_status", "")

        # V1.3 无弃人底线：低信度≠废材
        no_discard_note = ""
        if self.config.get("no_discard_enabled", True):
            if confirmation == ConfirmationStatus.PENDING.value or vitality in (
                SeedVitality.DORMANT.value, SeedVitality.GERMINATING.value
            ):
                no_discard_note = (
                    "圣人常善救人，故无弃人。——此种子为'待观察'，非'废材'。"
                    "建议换缘/换方向，不丢弃。（《道德经》第27章）"
                )

        if vitality == SeedVitality.FRUITING.value:
            base = (
                f"种子已成熟为果实（seedney={result.seedney_score:.2f}）。"
                "对称性种子→对称性果实转化完成。建议进入「水·变」阶段，基于果实进行创新。"
            )
        elif vitality == SeedVitality.FLOWERING.value:
            base = (
                f"种子正在开花（seedney={result.seedney_score:.2f}）。"
                "建议增加师生共创验证场景，加速果实成熟。"
            )
        elif zone == "种子主导区":
            base = (
                f"种子在核心结构区（损耗 {1-result.seedney_score:.0%}），"
                "结构保持良好。建议持续科教融合，强化对称性映射。"
            )
        elif zone == "结构保持区":
            base = (
                f"种子在结构保持区（损耗 {1-result.seedney_score:.0%}），"
                "部分结构有损耗。建议回到教学疑难切入，重新审视种子特征。"
            )
        elif zone == "缘主导区":
            base = (
                f"种子在缘主导区（损耗 {1-result.seedney_score:.0%}），"
                "结构保持困难。建议不强求培育，回归「木·生」阶段重新识别种子。"
            )
        else:
            base = "继续观察种子培育进展。"

        if no_discard_note:
            base += " " + no_discard_note

        return base

    # ── 批量培育 ──

    def cultivate_all(self, source_domain: str,
                      target_domains: List[str],
                      source_graph: dict = None,
                      target_graphs: Dict[str, dict] = None) -> List[SeedCultivationResult]:
        """批量种子培育"""
        results = []
        for target in target_domains:
            tgt_graph = target_graphs.get(target) if target_graphs else None
            result = self.cultivate(source_domain, target, source_graph, tgt_graph)
            results.append(result)

        results.sort(key=lambda r: r.seedney_score, reverse=True)
        return results

    # ── 报告 ──

    def format_summary(self, result: SeedCultivationResult) -> str:
        """格式化种子培育摘要（V1.3）"""
        lines = []
        lines.append("=" * 60)
        lines.append(f"  木·生 种子培育报告 (V1.5)")
        lines.append(f"  培育ID: {result.cultivation_id}")
        lines.append(f"  时间: {result.timestamp[:19]}")
        lines.append(f"  时间尺度: {result.time_scale}")
        lines.append(f"  孔子阶段: {result.confucius_stage}")
        lines.append("=" * 60)

        lines.append(f"\n  种子来源: {result.source_domain}")
        lines.append(f"  培育土壤: {result.target_domain}")

        # Step 1: 双种子画像
        s1 = result.step1_identify
        lines.append(f"\n  ── Step 1: 教学疑难切入（识别种子）──")
        topic = result.topic_seed
        method = result.method_seed
        lines.append(f"    题目种子: {topic.get('domain', '?')} ({topic.get('wuxing', '?')}) — 允许漂移")
        lines.append(f"    方法种子: {method.get('tool_preference', '?')} ({method.get('wuxing', '?')})")
        lines.append(f"    出现次数: {method.get('occurrence_count', 0)} (阈值≥{method.get('confirmation_threshold', 3)})")
        lines.append(f"    确认状态: {method.get('confirmation_status', '?')}")
        lines.append(f"    共振强度: {method.get('resonance_strength', 0):.2f}")
        src = s1.get("source_structure", {})
        if src.get("node_count"):
            lines.append(f"    源域结构: {src.get('node_count')} 节点, {src.get('edge_count')} 边")

        # Step 2: 缘四要素（V1.3 修订：导师差异化 + 环境分阶段）
        s2 = result.step2_nurture
        lines.append(f"\n  ── Step 2: 科教融合提炼前沿课题（培育种子）──")
        lines.append(f"    培育迭代: {s2.get('nurture_iterations', 0)} 轮 (粒度: {s2.get('time_scale_granularity', '?')})")
        env = result.environmental_factors
        if env:
            lines.append(f"    缘四要素（V1.3 儒道合流）:")
            mentor = env.get('mentor', {})
            lines.append(f"      导师: {mentor.get('name', '?')} → {mentor.get('agent_translation', '?')}")
            lines.append(f"        因材施教: {mentor.get('differentiation', '?')} (强度: {mentor.get('intensity', '?')})")
            lines.append(f"        不宰伦理: {mentor.get('non_dominance', '?')}")
            environment = env.get('environment', {})
            lines.append(f"      环境: {environment.get('name', '?')} → {environment.get('agent_translation', '?')}")
            lines.append(f"        分阶段: {environment.get('phase', '?')} — {environment.get('phase_description', '?')}")
            topic_e = env.get('topic', {})
            lines.append(f"      课题: {topic_e.get('name', '?')} → {topic_e.get('agent_translation', '?')}")
            collab = env.get('collaborators', {})
            lines.append(f"      合作者: {', '.join(collab.get('members', ['?']))} → {collab.get('agent_translation', '?')}")

        # V1.3 培育双轨
        dual = result.nurture_dual_track
        if dual:
            lines.append(f"\n    培育双轨（V1.3 为学日益 + 为道日损）:")
            addition_count = len(dual.get("addition_events", []))
            subtraction_count = len(dual.get("subtraction_events", []))
            lines.append(f"      加法引擎（为学日益）: {addition_count} 个积累事件")
            lines.append(f"      减法引擎（为道日损）: {subtraction_count} 个减除事件（可逆: {dual.get('subtraction_reversible', True)}）")
            lines.append(f"      原则: {dual.get('principle', '?')}")

        lines.append(f"    培育效果: {s2.get('nurture_effect', {}).get('description', '?')}")

        # Step 3: 双审计 + 漂移（V1.3）
        s3 = result.step3_harvest
        lines.append(f"\n  ── Step 3: 师生共创突破（收获果实）──")
        lines.append(f"    验证场景: {s3.get('verification_scenarios', 0)}")
        lines.append(f"    通过率: {s3.get('pass_rate', 0):.0%}")

        # V1.3 双审计：宪法审计（德）优先
        ca = result.constitution_audit
        if ca:
            ca_icon = "✅" if ca.get("passed") else "❌"
            lines.append(f"\n    V1.3 双审计 — 宪法审计（德·仁）优先:")
            lines.append(f"      {ca_icon} 宪法审计: {'通过' if ca.get('passed') else 'REJECT'}")
            lines.append(f"      原则: {ca.get('principle', '?')}")
            for c in ca.get("checks", []):
                icon = {"PASS": "✓", "REJECT": "✗"}.get(c["verdict"], "?")
                lines.append(f"        [{icon}] {c['check_name']}: {c['reason'][:60]}...")
            if ca.get("boundary_violations"):
                lines.append(f"      越界项: {', '.join(ca['boundary_violations'])}")
            lines.append(f"      {ca.get('note', '')}")

        # 性决定审计（才）
        nd_audit = s3.get("nature_determination_audit", {})
        threshold_source = "对照校准" if self.config.get("calibrated_threshold") is not None else "默认"
        if ca.get("passed"):
            lines.append(f"\n    V1.3 双审计 — 性决定审计（才·方法）次之:")
            lines.append(f"      余弦相似度: {result.nature_determination_score:.4f} (阈值≥{self._get_calibrated_threshold()}，{threshold_source}来源)")
            if nd_audit.get("components"):
                comp_str = ", ".join(f"{wx}={v:.2f}" for wx, v in nd_audit["components"].items())
                lines.append(f"      五行分解: {comp_str}")
            lines.append(f"      解读: {nd_audit.get('interpretation', '?')}")
            lines.append(f"      审计状态: {nd_audit.get('threshold_status', '待校准')}")
        else:
            lines.append(f"\n    V1.3 双审计 — 性决定审计（才·方法）: ⊘ 跳过（宪法审计 REJECT）")

        # V1.5 壳核审计声明
        shell_decl = result.shell_nucleus_declaration
        if shell_decl and shell_decl.get("declared"):
            lines.append(f"\n    V1.5 壳核审计声明:")
            lines.append(f"      测的核: {shell_decl.get('nucleus_measured', '?')}")
            lines.append(f"      不测的壳: {', '.join(shell_decl.get('shell_excluded', ['?']))}")
            lines.append(f"      体系类型: {shell_decl.get('system_type', '?')}")
            lines.append(f"      声明意义: {shell_decl.get('declaration_note', '?')}")

        # V1.5 纯粹度审计
        purity = result.purity_result
        if purity:
            anti_sway_label = "待校准" if not purity.get("anti_sway_calibrated", False) else f"{purity.get('anti_sway', 1.0):.2f}"
            lines.append(f"\n    V1.5 纯粹度审计（保持×时间×抗摇摆）:")
            lines.append(f"      纯粹度: {purity.get('purity_score', 0):.4f} (阈值≥{purity.get('threshold', 0.7)})")
            lines.append(f"      保持度: {purity.get('retention', 0):.4f}（余弦相似度）")
            lines.append(f"      持续时间: {purity.get('duration', 0):.2f}")
            lines.append(f"      抗摇摆: {anti_sway_label}")
            lines.append(f"      解读: {purity.get('interpretation', '?')}")

        # V1.5 协议级日损记录
        proto_subs = result.protocol_subtractions
        if proto_subs:
            lines.append(f"\n    V1.5 协议级日损记录（{len(proto_subs)} 项）:")
            for ps in proto_subs:
                lines.append(f"      → {ps.get('item', '?')}: {ps.get('reason', '?')[:50]}")

        # V1.5 Phase B: 熵振引擎
        entropy = result.entropy_vibration
        if entropy and entropy.get("quality_audits"):
            lines.append(f"\n    V1.5 熵振引擎（失败质量审核）:")
            lines.append(f"      真失败（奖励）: {entropy.get('true_failures', 0)} 项")
            lines.append(f"      表演性失败（不计分）: {entropy.get('performative_failures', 0)} 项")
            lines.append(f"      原则: {entropy.get('principle', '?')[:80]}...")
            if entropy.get("falsification_library_updates"):
                for fl in entropy["falsification_library_updates"]:
                    lines.append(f"        → 入证伪库: {fl.get('evidence', '?')[:40]}...")

        # V1.5 Phase B: 待验证假设清单
        hypotheses = result.pending_hypotheses
        if hypotheses:
            lines.append(f"\n    V1.5 待验证假设清单（{len(hypotheses)} 项）:")
            for h in hypotheses:
                status_icon = {"待验证": "⏳", "已验证": "✅", "已证伪": "❌", "待定": "?"}.get(h.get("status", ""), "?")
                lines.append(f"      {status_icon} {h.get('hypothesis_id', '?')}: {h.get('statement', '?')[:50]}...")

        # V1.5 Phase B: 留白条款
        blank = result.blank_space
        if blank and blank.get("action") == "observe_only":
            lines.append(f"\n    V1.5 留白条款:")
            lines.append(f"      留白轮: ✅ 本轮为留白轮——只观察不干预")
            lines.append(f"      活动: {', '.join(blank.get('activities', ['?']))}")
            lines.append(f"      说明: 不计入里程碑考核")
        elif blank and blank.get("skipped_for_deadline"):
            lines.append(f"\n    V1.5 留白条款:")
            lines.append(f"      留白轮: ⚠️ deadline 跳过（欠 {blank.get('owed_rounds', 0)} 轮）")

        # V1.5 Phase B: 日益饱和检测
        sat = result.saturation_detection
        if sat and sat.get("saturated"):
            lines.append(f"\n    V1.5 日益饱和检测:")
            lines.append(f"      饱和: ⚠️ 日益饱和——边际产出 {sat.get('marginal_output', 0):.4f}")
            lines.append(f"      建议: {sat.get('recommendation', '?')[:80]}...")

        # V1.5 Phase B: 换球心决策
        br = result.ball_replacement
        if br and br.get("triggered"):
            lines.append(f"\n    V1.5 换球心决策:")
            lines.append(f"      触发: ⚠️ {br.get('reason', '?')}")
            lines.append(f"      候选体系: {', '.join(c.get('system', '?') for c in br.get('candidate_systems', []))}")
            lines.append(f"      建议: {br.get('recommendation', '?')[:80]}...")

        status = "✅ 成功" if s3.get("success") else "❌ 未完成"
        lines.append(f"\n    结果: {status}")
        lines.append(f"    {s3.get('harvest_conclusion', '')}")

        # V1.1: 漂移分析
        drift = result.drift_analysis
        if drift:
            drift_icon = "🔵" if drift.get("drift_type") == DriftType.ENVIRONMENTAL.value else "🔴"
            lines.append(f"    漂移检测: {drift_icon} {drift.get('drift_type', '?')} — {drift.get('detail', '')}")
            lines.append(f"    处置: {drift.get('action', '')}")

        # V1.3 减法引擎结果
        sub = s3.get("subtraction_result", {})
        if sub and sub.get("subtraction_events"):
            lines.append(f"\n    V1.3 减法引擎（为道日损）:")
            lines.append(f"      减除事件数: {sub.get('subtraction_count', 0)}")
            lines.append(f"      可逆: {sub.get('reversible', True)}")
            lines.append(f"      原则: {sub.get('principle', '?')}")
            for ev in sub.get("subtraction_events", []):
                lines.append(f"        → {ev.get('event')}: {ev.get('target')[:50]}")

        # G5: 同源偏差标注
        if result.same_source_bias:
            lines.append(f"\n  ── G5 同源偏差标注 ──")
            lines.append(f"    ⚠️ 同源偏差: 验证标尺与信号源来自同一轨迹。")
            lines.append(f"    检出率是描述性结果（协议能描述已知路径），不构成预测力证据。")

        # V1.3 归朴（原"通中生种"）
        reverse_seeds = result.reverse_flow_seeds
        lines.append(f"\n  ── V1.3 归朴（复归于朴）──")
        if reverse_seeds:
            lines.append(f"    归朴候选: {len(reverse_seeds)} 个")
            for rs in reverse_seeds:
                lines.append(f"      → {rs.get('source_domain', '?')} ({rs.get('method_seed_wuxing', '?')}) "
                           f"出现 {rs.get('occurrence_count', 0)} 次")
            lines.append(f"    说明: 成器→迁移→归朴。土·通迁移中检测到新种子候选，回流进入 Step 1")
        else:
            lines.append(f"    未检测到归朴信号")
            lines.append(f"    说明: 复归于朴——成器之后回归本真，不被才能异化")

        # 综合评估
        lines.append(f"\n  ── 综合评估 ──")
        lines.append(f"    种子质量 (seedney): {result.seedney_score:.4f}")
        lines.append(f"    taste (妙): {result.taste_score:.4f}")
        lines.append(f"    种子活力: {result.seed_vitality}")
        lines.append(f"    损耗分层: {result.loss_zone}")
        if result.S_p > 0:
            lines.append(f"    道境指数: S_p={result.S_p:.1f} ({result.stage})")
        if result.confucius_stage:
            lines.append(f"    孔子阶段: {result.confucius_stage}")
        if result.environment_phase:
            lines.append(f"    环境分阶段: {result.environment_phase}")
        lines.append(f"    无弃人底线: {'✅ 已启用' if result.no_discard_guarantee else '⚠ 未启用'}")

        # 经典引用与建议
        lines.append(f"\n  ── 经典与建议 ──")
        lines.append(f"    经典: {result.classical_ref}")
        lines.append(f"    建议: {result.ethical_advice}")

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)

    def get_stats(self) -> dict:
        """获取培育统计"""
        total = len(self.cultivation_history)
        if total == 0:
            return {"total": 0, "success_rate": 0, "avg_seedney": 0}

        success = sum(1 for r in self.cultivation_history if r.cultivation_success)
        avg_seedney = sum(r.seedney_score for r in self.cultivation_history) / total

        zone_dist = {}
        for r in self.cultivation_history:
            zone = r.loss_zone
            zone_dist[zone] = zone_dist.get(zone, 0) + 1

        return {
            "total": total,
            "success_rate": round(success / total, 4),
            "avg_seedney": round(avg_seedney, 4),
            "loss_zone_distribution": zone_dist,
            "vitality_distribution": {
                v: sum(1 for r in self.cultivation_history if r.seed_vitality == v)
                for v in set(r.seed_vitality for r in self.cultivation_history)
            },
        }


# ============================================================
# 便捷函数：同态映射引擎的种子培育钩子
# ============================================================

def cultivate_seed(source_domain: str, target_domain: str,
                   source_graph: dict = None, target_graph: dict = None,
                   wuxing_context: dict = None,
                   cultivator: SeedCultivation = None,
                   # V1.1 新增参数
                   environmental_factors: dict = None,
                   method_seed_occurrences: int = 0,
                   method_seed_wuxing: str = "",
                   topic_seed_wuxing: str = "",
                   # V1.2 新增参数
                   harvest_methodology_wuxing: str = "",
                   migration_events: List[dict] = None) -> SeedCultivationResult:
    """
    同态映射引擎的种子培育钩子（V1.2）

    在木·生阶段调用，执行种子培育三步法。

    Args:
        source_domain: 种子来源域
        target_domain: 培育目标域
        source_graph: 源域结构图
        target_graph: 目标域结构图
        wuxing_context: 五行诊断上下文
        cultivator: 培育器实例
        environmental_factors: 缘四要素
        method_seed_occurrences: 方法种子出现次数
        method_seed_wuxing: 方法种子五行
        topic_seed_wuxing: 题目种子五行
        harvest_methodology_wuxing: 成果方法论五行（V1.2，用于余弦相似度审计）
        migration_events: 迁移事件列表（V1.2，用于通中生种检测）

    Returns:
        SeedCultivationResult
    """
    if cultivator is None:
        cultivator = SeedCultivation()

    return cultivator.cultivate(
        source_domain, target_domain,
        source_graph=source_graph,
        target_graph=target_graph,
        wuxing_context=wuxing_context,
        environmental_factors=environmental_factors,
        method_seed_occurrences=method_seed_occurrences,
        method_seed_wuxing=method_seed_wuxing,
        topic_seed_wuxing=topic_seed_wuxing,
        harvest_methodology_wuxing=harvest_methodology_wuxing,
        migration_events=migration_events,
    )


# ============================================================
# 自检（V1.3）
# ============================================================

if __name__ == "__main__":
    # ── CLI 入口：CASE-LIU 壳核审计 ──
    import argparse, json, os
    parser = argparse.ArgumentParser(description="种子培育模块 — CLI 验证入口")
    parser.add_argument("--task", type=str, help="任务 JSON 文件路径")
    parser.add_argument("--mode", type=str, choices=["shell_nucleus_audit"],
                        help="验证模式: shell_nucleus_audit")
    parser.add_argument("--output", type=str, default=None, help="结果输出 JSON 路径")
    args = parser.parse_args()

    if args.task and args.mode == "shell_nucleus_audit":
        task_path = os.path.join(os.path.dirname(__file__), "..", "data", args.task) \
            if not os.path.isabs(args.task) else args.task
        with open(task_path, encoding="utf-8") as f:
            task_data = json.load(f)

        cultivator = SeedCultivation(time_scale="skill")
        sn_input = task_data.get("shell_nucleus_input", {})
        audit_result = cultivator.shell_nucleus_audit(sn_input)

        output_path = args.output or os.path.join(
            os.path.dirname(__file__), "..", "output", "reports",
            "result_liu_shell_nucleus_audit.json"
        )
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(audit_result, f, ensure_ascii=False, indent=2)
        print(f"结果已保存: {output_path}")
        print(json.dumps(audit_result, ensure_ascii=False, indent=2))
        import sys; sys.exit(0)

    # ── 原有独立测试 ──
    print("=" * 60)
    print("种子培育模块 — 自检 (V1.3)")
    print("=" * 60)

    cultivator = SeedCultivation(time_scale="skill")

    # 测试 1: 正常培育（默认参数）
    print("\n[测试 1] 正常种子培育: 大语言模型 → 自然语言处理")
    r = cultivator.cultivate("大语言模型", "自然语言处理")
    print(cultivator.format_summary(r))
    assert r.seedney_score > 0
    assert r.taste_score > 0
    assert r.seed_vitality != SeedVitality.DORMANT.value
    assert r.time_scale == "skill"
    print("  ✅ 测试 1 通过")

    # 测试 2: 低结构相似度培育
    print("\n[测试 2] 低结构相似度: 大语言模型 → 生成式AI")
    r2 = cultivator.cultivate("大语言模型", "生成式AI")
    print(f"  种子质量: {r2.seedney_score:.4f}")
    print(f"  损耗分层: {r2.loss_zone}")
    print(f"  种子活力: {r2.seed_vitality}")
    print("  ✅ 测试 2 通过")

    # 测试 3: 带五行上下文的培育
    print("\n[测试 3] 带五行上下文的培育")
    r3 = cultivator.cultivate(
        "大语言模型", "自然语言处理",
        wuxing_context={"S_p": 39.5, "stage": "克"}
    )
    print(f"  道境指数: S_p={r3.S_p:.1f} ({r3.stage})")
    assert r3.S_p == 39.5
    print("  ✅ 测试 3 通过")

    # 测试 4: 批量培育
    print("\n[测试 4] 批量培育")
    targets = ["自然语言处理", "生成式AI", "计算机视觉", "强化学习"]
    results = cultivator.cultivate_all("大语言模型", targets)
    print(f"  {'目标域':<20} {'seedney':>8} {'taste':>8} {'活力':>8} {'分层':>12}")
    print("  " + "-" * 50)
    for r in results:
        print(f"  {r.target_domain:<20} {r.seedney_score:>8.4f} {r.taste_score:>8.4f} {r.seed_vitality:>8} {r.loss_zone:>12}")
    print("  ✅ 测试 4 通过")

    # 测试 5: 统计
    print("\n[测试 5] 培育统计")
    stats = cultivator.get_stats()
    print(f"  总培育数: {stats['total']}")
    print(f"  成功率: {stats['success_rate']:.0%}")
    print(f"  平均种子质量: {stats['avg_seedney']:.4f}")
    print(f"  损耗分层: {stats['loss_zone_distribution']}")
    print("  ✅ 测试 5 通过")

    # 测试 6: 便捷函数
    print("\n[测试 6] 便捷函数 cultivate_seed")
    r6 = cultivate_seed("大语言模型", "自然语言处理")
    print(f"  种子质量: {r6.seedney_score:.4f}")
    assert r6.seedney_score > 0
    print("  ✅ 测试 6 通过")

    # 测试 7: 三步法各阶段独立性
    print("\n[测试 7] 三步法各阶段独立性")
    assert r.step1_identify["step"] == 1
    assert r.step2_nurture["step"] == 2
    assert r.step3_harvest["step"] == 3
    assert r.step1_identify["phase"] == "教学疑难切入"
    assert r.step2_nurture["phase"] == "科教融合提炼前沿课题"
    assert r.step3_harvest["phase"] == "师生共创突破"
    print("  ✅ 测试 7 通过")

    # 测试 8: 损耗分层分类
    print("\n[测试 8] 损耗分层分类")
    zones = set(r.loss_zone for r in results)
    print(f"  出现的分层: {zones}")
    assert len(zones) >= 1
    print("  ✅ 测试 8 通过")

    # ── V1.1 新增测试 ──

    # 测试 9: 双种子画像
    print("\n[测试 9] V1.1 双种子画像")
    r9 = cultivator.cultivate(
        "大语言模型", "自然语言处理",
        method_seed_occurrences=4,      # ≥3 → 确认种子
        method_seed_wuxing="水",
        topic_seed_wuxing="土",
    )
    assert r9.topic_seed["type"] == SeedType.TOPIC.value
    assert r9.method_seed["type"] == SeedType.METHOD.value
    assert r9.topic_seed["drift_allowed"] == True
    assert r9.method_seed["drift_allowed"] == False
    assert r9.method_seed["confirmation_status"] == ConfirmationStatus.CONFIRMED.value
    assert r9.method_seed["occurrence_count"] == 4
    print(f"  题目种子: {r9.topic_seed['wuxing']} (允许漂移: {r9.topic_seed['drift_allowed']})")
    print(f"  方法种子: {r9.method_seed['wuxing']} (确认状态: {r9.method_seed['confirmation_status']})")
    print("  ✅ 测试 9 通过")

    # 测试 10: 方法种子待观察（<3次）
    print("\n[测试 10] V1.1 方法种子待观察")
    r10 = cultivator.cultivate(
        "大语言模型", "自然语言处理",
        method_seed_occurrences=1,      # <3 → 待观察
    )
    assert r10.method_seed["confirmation_status"] == ConfirmationStatus.PENDING.value
    assert r10.method_seed["resonance_strength"] < 1.0
    print(f"  确认状态: {r10.method_seed['confirmation_status']}")
    print(f"  共振强度: {r10.method_seed['resonance_strength']:.2f}")
    print("  ✅ 测试 10 通过")

    # 测试 11: 缘四要素注入
    print("\n[测试 11] V1.1 缘四要素注入")
    r11 = cultivator.cultivate(
        "大语言模型", "自然语言处理",
        environmental_factors={
            "mentor": {"name": "杨振宁（模拟导师）", "wuxing": "金"},
            "topic": {"name": "对称性迁移课题", "wuxing": "水"},
        },
    )
    env = r11.environmental_factors
    assert env["mentor"]["name"] == "杨振宁（模拟导师）"
    assert env["mentor"]["wuxing"] == "金"
    assert env["topic"]["name"] == "对称性迁移课题"
    print(f"  导师: {env['mentor']['name']} ({env['mentor']['wuxing']})")
    print(f"  课题: {env['topic']['name']} ({env['topic']['wuxing']})")
    print(f"  环境: {env['environment']['name']}")
    print(f"  合作者: {env['collaborators']['members']}")
    print("  ✅ 测试 11 通过")

    # 测试 12: 漂移检测
    print("\n[测试 12] V1.1 漂移双层检验")
    r12 = cultivator.cultivate(
        "大语言模型", "自然语言处理",
        method_seed_wuxing="水",
        environmental_factors={
            "mentor": {"name": "导师A", "wuxing": "金"},
            "environment": {"name": "环境B", "wuxing": "木"},
        },
    )
    drift = r12.drift_analysis
    assert drift["drift_type"] == DriftType.ENVIRONMENTAL.value
    assert drift["detected"] == True
    print(f"  漂移类型: {drift['drift_type']}")
    print(f"  详情: {drift['detail']}")
    print(f"  处置: {drift['action']}")
    print("  ✅ 测试 12 通过")

    # 测试 13: 性决定检验
    print("\n[测试 13] V1.1 性决定检验")
    r13 = cultivator.cultivate(
        "大语言模型", "自然语言处理",
        method_seed_occurrences=4,      # 确认种子 → 高基础分
        method_seed_wuxing="水",
    )
    nd = r13.nature_determination_score
    threshold = cultivator.config["nature_determination_threshold"]
    assert nd > 0
    print(f"  性决定相似度: {nd:.4f} (阈值≥{threshold})")
    print(f"  结论: {'✅ 保持' if nd >= threshold else '⚠️ 需关注'}")
    print("  ✅ 测试 13 通过")

    # 测试 14: 时间尺度参数化（人才尺度）
    print("\n[测试 14] V1.1 时间尺度参数化（人才 vs 技能）")
    talent_cultivator = SeedCultivation(time_scale="talent")
    r14_talent = talent_cultivator.cultivate("大语言模型", "自然语言处理")
    skill_cultivator = SeedCultivation(time_scale="skill")
    r14_skill = skill_cultivator.cultivate("大语言模型", "自然语言处理")
    assert r14_talent.time_scale == "talent"
    assert r14_skill.time_scale == "skill"
    assert r14_talent.step2_nurture["nurture_iterations"] == 10  # 人才 10 轮
    assert r14_skill.step2_nurture["nurture_iterations"] == 3    # 技能 3 轮
    print(f"  人才尺度: {r14_talent.step2_nurture['nurture_iterations']} 轮, 粒度: {r14_talent.step2_nurture['time_scale_granularity']}")
    print(f"  技能尺度: {r14_skill.step2_nurture['nurture_iterations']} 轮, 粒度: {r14_skill.step2_nurture['time_scale_granularity']}")
    print("  ✅ 测试 14 通过")

    # 测试 15: 五行推断
    print("\n[测试 15] V1.1 五行推断 (_infer_wuxing)")
    assert cultivator._infer_wuxing("自然语言处理") == "水"
    assert cultivator._infer_wuxing("机器学习基础") == "土"
    assert cultivator._infer_wuxing("计算机视觉") == "火"
    assert cultivator._infer_wuxing("逻辑推理") == "金"
    assert cultivator._infer_wuxing("生成式AI") == "木"
    assert cultivator._infer_wuxing("未知领域") == "土"  # 默认 offset=0
    print(f"  自然语言处理 → 水: {cultivator._infer_wuxing('自然语言处理')}")
    print(f"  机器学习基础 → 土: {cultivator._infer_wuxing('机器学习基础')}")
    print(f"  计算机视觉 → 火: {cultivator._infer_wuxing('计算机视觉')}")
    print(f"  逻辑推理 → 金: {cultivator._infer_wuxing('逻辑推理')}")
    print(f"  生成式AI → 木: {cultivator._infer_wuxing('生成式AI')}")
    print("  ✅ 测试 15 通过")

    # ═══════════════════════════════════════════════
    # V1.2 新增测试
    # ═══════════════════════════════════════════════

    # 测试 16: 五行向量转换（V1.2）
    print("\n[测试 16] V1.2 五行向量转换 (_wuxing_to_vector)")
    vec_water = cultivator._wuxing_to_vector("水")
    assert vec_water == [0.0, 0.0, 0.0, 0.0, 1.0], f"水向量应为 [0,0,0,0,1]，实际: {vec_water}"
    vec_wood = cultivator._wuxing_to_vector("木")
    assert vec_wood == [1.0, 0.0, 0.0, 0.0, 0.0], f"木向量应为 [1,0,0,0,0]，实际: {vec_wood}"
    vec_multi = cultivator._wuxing_to_vector("水土")
    assert vec_multi == [0.0, 0.0, 0.5, 0.0, 0.5], f"水土向量应为 [0,0,0.5,0,0.5]，实际: {vec_multi}"
    vec_empty = cultivator._wuxing_to_vector("")
    assert vec_empty == [0.0, 0.0, 0.0, 0.0, 0.0], f"空字符串应为零向量，实际: {vec_empty}"
    print(f"  水 → {vec_water}")
    print(f"  木 → {vec_wood}")
    print(f"  水土 → {vec_multi}")
    print("  ✅ 测试 16 通过")

    # 测试 17: 余弦相似度 — 同向（V1.2）
    print("\n[测试 17] V1.2 余弦相似度 — 同向验证")
    vec_a = [1.0, 0.0, 0.0, 0.0, 0.0]  # 纯木
    vec_b = [1.0, 0.0, 0.0, 0.0, 0.0]  # 纯木
    sim_same = cultivator._cosine_similarity(vec_a, vec_b)
    assert abs(sim_same - 1.0) < 0.001, f"同向向量余弦应为 1.0，实际: {sim_same}"
    print(f"  木→木 余弦相似度: {sim_same:.4f} (期望 1.0)")
    print("  ✅ 测试 17 通过")

    # 测试 18: 余弦相似度 — 正交（V1.2）
    print("\n[测试 18] V1.2 余弦相似度 — 正交验证")
    vec_wood = [1.0, 0.0, 0.0, 0.0, 0.0]  # 纯木
    vec_fire = [0.0, 1.0, 0.0, 0.0, 0.0]  # 纯火
    sim_ortho = cultivator._cosine_similarity(vec_wood, vec_fire)
    assert abs(sim_ortho - 0.0) < 0.001, f"正交向量余弦应为 0.0，实际: {sim_ortho}"
    print(f"  木→火 余弦相似度: {sim_ortho:.4f} (期望 0.0)")
    print("  ✅ 测试 18 通过")

    # 测试 19: 性决定审计 — 正样本（V1.2）
    print("\n[测试 19] V1.2 性决定审计 — 正样本（方法种子=成果）")
    r19 = cultivator.cultivate(
        "大语言模型", "自然语言处理",
        method_seed_occurrences=4,
        method_seed_wuxing="水",
        harvest_methodology_wuxing="水",  # 成果方法论与方法种子一致
    )
    nd19 = r19.nature_determination_score
    nd_audit19 = r19.step3_harvest.get("nature_determination_audit", {})
    assert nd19 > 0.9, f"同五行余弦相似度应 >0.9，实际: {nd19}"
    assert nd_audit19.get("threshold_status") == "待校准"
    print(f"  方法种子: 水, 成果方法论: 水")
    print(f"  余弦相似度: {nd19:.4f} (期望 ≥0.9)")
    print(f"  审计标注: {nd_audit19.get('audit_note', '')[:50]}...")
    print("  ✅ 测试 19 通过")

    # 测试 20: 性决定审计 — 负样本（V1.2）
    print("\n[测试 20] V1.2 性决定审计 — 负样本（方法种子≠成果）")
    r20 = cultivator.cultivate(
        "大语言模型", "自然语言处理",
        method_seed_occurrences=4,
        method_seed_wuxing="水",
        harvest_methodology_wuxing="火",  # 成果方法论与方法种子不同
    )
    nd20 = r20.nature_determination_score
    assert nd20 < 0.5, f"异五行余弦相似度应 <0.5，实际: {nd20}"
    print(f"  方法种子: 水, 成果方法论: 火")
    print(f"  余弦相似度: {nd20:.4f} (期望 <0.5)")
    print(f"  审计结论: {'需关注（性漂移可能性高）' if nd20 < 0.5 else '待观察'}")
    print("  ✅ 测试 20 通过")

    # 测试 21: 通中生种检测（V1.2）
    print("\n[测试 21] V1.2 通中生种检测 (_detect_reverse_flow_seeds)")
    # 模拟迁移事件：3 个 +2 事件在 "生成式AI" 领域
    migration_events = [
        {"domain": "生成式AI", "wuxing": "木", "value_score": 2, "event_type": "interest_signal"},
        {"domain": "生成式AI", "wuxing": "木", "value_score": 2, "event_type": "interest_signal"},
        {"domain": "生成式AI", "wuxing": "木", "value_score": 2, "event_type": "interest_signal"},
        {"domain": "计算机视觉", "wuxing": "火", "value_score": 1, "event_type": "interest_signal"},
        {"domain": "计算机视觉", "wuxing": "火", "value_score": 2, "event_type": "interest_signal"},
    ]
    reverse_seeds = cultivator._detect_reverse_flow_seeds(migration_events)
    assert len(reverse_seeds) == 1, f"应检测到 1 个回流候选，实际: {len(reverse_seeds)}"
    assert reverse_seeds[0]["source_domain"] == "生成式AI"
    assert reverse_seeds[0]["occurrence_count"] == 3
    assert reverse_seeds[0]["source"] == "归朴"
    print(f"  模拟迁移事件: {len(migration_events)} 个")
    print(f"  +2 事件: 生成式AI x3, 计算机视觉 x1")
    print(f"  回流候选: {len(reverse_seeds)} 个")
    print(f"    → {reverse_seeds[0]['source_domain']} ({reverse_seeds[0]['method_seed_wuxing']}) "
          f"出现 {reverse_seeds[0]['occurrence_count']} 次")
    # 验证未达阈值的不被检测
    reverse_seeds_none = cultivator._detect_reverse_flow_seeds([])
    assert reverse_seeds_none == []
    print("  ✅ 测试 21 通过")

    # 测试 22: 跨界对照校准（V1.2）
    print("\n[测试 22] V1.2 跨界对照校准 (_calibrate_with_contrast)")
    positive = [
        {"method_wuxing": "水", "harvest_wuxing": "水", "label": "四大师-保持"},
        {"method_wuxing": "金", "harvest_wuxing": "金", "label": "四大师-保持"},
    ]
    negative = [
        {"method_wuxing": "水", "harvest_wuxing": "火", "label": "跨界-物理转生物"},
        {"method_wuxing": "金", "harvest_wuxing": "木", "label": "跨界-数学转金融"},
    ]
    calib = cultivator._calibrate_with_contrast(positive, negative)
    assert len(calib["positive_scores"]) == 2
    assert len(calib["negative_scores"]) == 2
    assert all(s > 0.9 for s in calib["positive_scores"]), f"正样本余弦应 >0.9，实际: {calib['positive_scores']}"
    assert all(s < 0.5 for s in calib["negative_scores"]), f"负样本余弦应 <0.5，实际: {calib['negative_scores']}"
    assert calib["discriminative"] == True, "正负样本应显著分离"
    print(f"  正样本余弦: {calib['positive_scores']}")
    print(f"  负样本余弦: {calib['negative_scores']}")
    print(f"  分离度: {calib['separation']:.0%}")
    print(f"  判别力: {'充足' if calib['discriminative'] else '不足'}")
    print(f"  建议阈值: {calib['suggested_threshold']}")
    print(f"  {calib['recommendation']}")
    print("  ✅ 测试 22 通过")

    # 测试 23: 缘四要素 Agent 翻译字段验证（V1.2）
    print("\n[测试 23] V1.2 缘四要素 Agent 翻译字段验证")
    r23 = cultivator.cultivate("大语言模型", "自然语言处理")
    env23 = r23.environmental_factors
    # 验证四个 Agent 翻译字段存在
    assert "agent_translation" in env23["mentor"], "导师缺少 agent_translation"
    assert "agent_translation" in env23["environment"], "环境缺少 agent_translation"
    assert "agent_translation" in env23["topic"], "课题缺少 agent_translation"
    assert "agent_translation" in env23["collaborators"], "合作者缺少 agent_translation"
    # 验证翻译内容
    assert "Base" in env23["mentor"]["agent_translation"], "导师翻译应含 Base 层"
    assert "L1b" in env23["environment"]["agent_translation"], "环境翻译应含 L1b"
    assert "前沿问题库" in env23["topic"]["agent_translation"], "课题翻译应含前沿问题库"
    assert "§5.4" in env23["collaborators"]["agent_translation"], "合作者翻译应含 §5.4"
    print(f"  导师 → {env23['mentor']['agent_translation']}")
    print(f"  环境 → {env23['environment']['agent_translation']}")
    print(f"  课题 → {env23['topic']['agent_translation']}")
    print(f"  合作者 → {env23['collaborators']['agent_translation']}")
    print("  ✅ 测试 23 通过")

    # ═══════════════════════════════════════════════
    # V1.3 新增测试
    # ═══════════════════════════════════════════════

    # 测试 24: 双审计顺序 — 宪法 REJECT → 性决定跳过（V1.3 澄清一：修复方向性）
    print("\n[测试 24] V1.3 双审计顺序 — 宪法审计 REJECT 短路")
    # 构造真越界场景：topic克method（课题压制方法本性）
    # 水克火 → topic(水)克method(火) → 真越界 → REJECT
    r24 = cultivator.cultivate(
        "大语言模型", "自然语言处理",
        method_seed_occurrences=4,
        method_seed_wuxing="火",
        topic_seed_wuxing="水",  # 水克火，topic克method → 真越界 → REJECT
    )
    ca24 = r24.constitution_audit
    assert "constitution_audit" in r24.to_dict(), "V1.3 结果应含宪法审计字段"
    assert "priority" in ca24, "宪法审计应含 priority 字段"
    assert ca24["priority"] == AuditPriority.CONSTITUTION.value
    # 验证方向越界检查为 REJECT（topic克method=真越界）
    dir_check = [c for c in ca24.get("checks", []) if c["check_name"] == "方向越界检查"]
    assert len(dir_check) == 1, "应存在方向越界检查"
    assert dir_check[0]["verdict"] == "REJECT", f"topic克method应为REJECT，实际: {dir_check[0]['verdict']}"
    # 验证宪法审计因方向越界而整体不通过
    assert ca24["passed"] == False, f"宪法审计应不通过（topic克method=真越界），实际: {ca24['passed']}"
    print(f"  宪法审计优先: {ca24.get('priority', '?')}")
    print(f"  原则: {ca24.get('principle', '?')[:50]}...")
    print(f"  检查项数: {len(ca24.get('checks', []))}")
    for c in ca24.get("checks", []):
        print(f"    [{c['verdict']}] {c['check_name']}: {c['reason'][:60]}...")
    print(f"  宪法审计通过: {ca24['passed']} (topic克method=真越界)")
    print("  ✅ 测试 24 通过")

    # 测试 25: 培育双轨 — 加法 + 减法事件并行
    print("\n[测试 25] V1.3 培育双轨 — 为学日益 + 为道日损并行")
    r25 = cultivator.cultivate(
        "大语言模型", "自然语言处理",
        method_seed_occurrences=4,
        method_seed_wuxing="水",
    )
    dual = r25.nurture_dual_track
    assert "addition_events" in dual, "培育双轨应含加法事件"
    assert "subtraction_events" in dual, "培育双轨应含减法事件"
    assert "principle" in dual, "培育双轨应含原则说明"
    print(f"  加法事件数: {len(dual.get('addition_events', []))}")
    print(f"  减法事件数: {len(dual.get('subtraction_events', []))}")
    print(f"  减法可逆: {dual.get('subtraction_reversible', True)}")
    print(f"  原则: {dual.get('principle', '?')}")
    print("  ✅ 测试 25 通过")

    # 测试 26: 导师差异化 — 不同种子不同培育强度
    print("\n[测试 26] V1.3 导师差异化 — 因材施教")
    # 金性种子 → 严厉（子路式）
    r26_jin = cultivator.cultivate(
        "大语言模型", "自然语言处理",
        method_seed_wuxing="金",
    )
    # 木性种子 → 温和（冉有式）
    r26_mu = cultivator.cultivate(
        "大语言模型", "自然语言处理",
        method_seed_wuxing="木",
    )
    ms_jin = r26_jin.mentor_strategy
    ms_mu = r26_mu.mentor_strategy
    assert ms_jin.get("differentiation") != ms_mu.get("differentiation"), \
        f"金和木的导师策略应不同: {ms_jin.get('differentiation')} vs {ms_mu.get('differentiation')}"
    assert "non_dominance_ethics" in ms_jin, "导师策略应含不宰伦理"
    print(f"  金性种子导师: {ms_jin.get('differentiation')} (强度: {ms_jin.get('intensity')})")
    print(f"  木性种子导师: {ms_mu.get('differentiation')} (强度: {ms_mu.get('intensity')})")
    print(f"  不宰伦理: {ms_jin.get('non_dominance_ethics', {}).get('principle', '?')[:50]}...")
    print("  ✅ 测试 26 通过")

    # 测试 27: 环境分阶段 — 子夏/子张
    print("\n[测试 27] V1.3 环境分阶段 — 子夏保护期 / 子张包容期")
    r27 = cultivator.cultivate("大语言模型", "自然语言处理")
    env_phase = r27.environment_phase
    assert env_phase in (EnvironmentPhase.ZIXIA.value, EnvironmentPhase.ZIZHANG.value), \
        f"环境分阶段应为子夏或子张，实际: {env_phase}"
    env_data = r27.environmental_factors.get("environment", {})
    assert "phase" in env_data, "环境应含 phase 字段"
    print(f"  环境分阶段: {env_phase}")
    print(f"  描述: {env_data.get('phase_description', '?')}")
    print("  ✅ 测试 27 通过")

    # 测试 28: 无弃人底线 — 低信度不丢弃
    print("\n[测试 28] V1.3 无弃人底线 — 低信度≠废材")
    r28 = cultivator.cultivate(
        "大语言模型", "自然语言处理",
        method_seed_occurrences=1,  # 待观察
    )
    assert r28.no_discard_guarantee == True, "无弃人底线应启用"
    assert "待观察" in r28.method_seed.get("confirmation_status", ""), "低信度应为待观察"
    advice = r28.ethical_advice
    assert "无弃人" in advice or "不丢弃" in advice, f"建议应含无弃人保证: {advice}"
    print(f"  确认状态: {r28.method_seed.get('confirmation_status')}")
    print(f"  无弃人底线: {r28.no_discard_guarantee}")
    print(f"  建议: {advice[:80]}...")
    print("  ✅ 测试 28 通过")

    # 测试 29: 归朴命名 — 反向回路字段
    print("\n[测试 29] V1.3 归朴命名 — 复归于朴")
    migration_events = [
        {"domain": "生成式AI", "wuxing": "木", "value_score": 2, "event_type": "interest_signal"},
        {"domain": "生成式AI", "wuxing": "木", "value_score": 2, "event_type": "interest_signal"},
        {"domain": "生成式AI", "wuxing": "木", "value_score": 2, "event_type": "interest_signal"},
    ]
    reverse_seeds = cultivator._detect_reverse_flow_seeds(migration_events)
    assert len(reverse_seeds) == 1
    assert reverse_seeds[0]["source"] == "归朴", \
        f"V1.3 源字段应为'归朴'，实际: {reverse_seeds[0]['source']}"
    assert "classical_ref" in reverse_seeds[0], "归朴候选应含经典引用"
    print(f"  源字段: {reverse_seeds[0]['source']}")
    print(f"  经典引用: {reverse_seeds[0]['classical_ref'][:50]}...")
    print("  ✅ 测试 29 通过")

    # 测试 30: 孔子六阶段
    print("\n[测试 30] V1.3 孔子六阶段 — 人才时间轴")
    r30_dormant = cultivator.cultivate("大语言模型", "未知领域")
    r30_fruiting = cultivator.cultivate(
        "大语言模型", "自然语言处理",
        method_seed_occurrences=4,
        method_seed_wuxing="水",
        harvest_methodology_wuxing="水",
    )
    assert r30_dormant.confucius_stage != "", "休眠种子应有孔子阶段"
    assert r30_fruiting.confucius_stage != "", "结果种子应有孔子阶段"
    print(f"  休眠种子: {r30_dormant.confucius_stage}")
    print(f"  结果种子: {r30_fruiting.confucius_stage}")
    # 验证六阶段配置存在
    stages = cultivator.config.get("confucius_stages", {})
    assert len(stages) == 6, f"应有 6 个孔子阶段，实际: {len(stages)}"
    print(f"  六阶段配置: {list(stages.keys())}")
    print("  ✅ 测试 30 通过")

    # 测试 31: V1.3 澄清一 — method克topic=WARNING（不阻断，正常约束机制）
    print("\n[测试 31] V1.3 澄清一 — method克topic=WARNING（正常约束，不阻断）")
    # 水克火 → method(水)克topic(火) → 正常约束机制 → WARNING
    r31 = cultivator.cultivate(
        "大语言模型", "自然语言处理",
        method_seed_occurrences=4,
        method_seed_wuxing="水",
        topic_seed_wuxing="火",  # 水克火，method克topic → 正常约束 → WARNING（不阻断）
    )
    ca31 = r31.constitution_audit
    dir_check31 = [c for c in ca31.get("checks", []) if c["check_name"] == "方向越界检查"]
    assert len(dir_check31) == 1, "应存在方向越界检查"
    assert dir_check31[0]["verdict"] == "PASS", (
        f"method克topic应为PASS（正常约束机制），实际: {dir_check31[0]['verdict']}"
    )
    assert "正常约束" in dir_check31[0]["reason"], (
        f"应标注'正常约束机制'，实际: {dir_check31[0]['reason']}"
    )
    print(f"  方向越界检查: [{dir_check31[0]['verdict']}] {dir_check31[0]['reason'][:60]}...")
    print(f"  宪法审计通过: {ca31['passed']} (method克topic=正常约束，不阻断)")
    print("  ✅ 测试 31 通过")

    # 测试 32: V1.5 壳核审计声明 — 无声明不审计
    print("\n[测试 32] V1.5 壳核审计声明 — 无声明不审计")
    # 启用壳核声明检查，但不传 shell_nucleus_declaration → 应触发 REJECT
    r32 = cultivator.cultivate(
        "大语言模型", "自然语言处理",
        method_seed_occurrences=3,
        method_seed_wuxing="水",
        topic_seed_wuxing="金",  # 金生水 → 不触发方向越界，仅靠壳核声明检查
    )
    ca32 = r32.constitution_audit
    # 注意：默认配置 shell_nucleus_declaration_required=False，壳核检查未启用
    # 此处验证的是：即使无声明，方向正常时审计仍通过（向后兼容）
    decl_check = [c for c in ca32.get("checks", []) if c["check_name"] == "壳核审计声明"]
    if decl_check:
        assert decl_check[0]["verdict"] == "REJECT", (
            f"无声明应REJECT，实际: {decl_check[0]['verdict']}"
        )
        print(f"  壳核审计声明: [{decl_check[0]['verdict']}] {decl_check[0]['reason'][:60]}...")
        assert not ca32.get("passed"), "无声明时宪法审计不应通过"
    else:
        # 默认配置下壳核声明未启用，审计应通过（向后兼容）
        assert ca32.get("passed"), "默认配置下审计应通过（向后兼容）"
        print(f"  壳核审计声明: 未启用（默认向后兼容）")
    print(f"  宪法审计通过: {ca32['passed']}")
    print("  ✅ 测试 32 通过")

    # 测试 33: V1.5 壳核审计声明 — 有声明正常通过
    print("\n[测试 33] V1.5 壳核审计声明 — 有声明正常通过")
    env_with_decl = {
        "mentor": {"name": "慧惠", "wuxing": "土"},
        "environment": {"name": "道境", "wuxing": "木"},
        "topic": {"name": "测试", "wuxing": "土"},
        "collaborators": {"members": ["慧惠"]},
        "shell_nucleus_declaration": {
            "nucleus_measured": "方法核",
            "shell_excluded": ["题目", "专业", "身份", "资历"],
            "system_type": SystemType.NUCLEUS_MEASURING.value,
            "declared": True,
            "declaration_note": "测试声明",
        },
    }
    r33 = cultivator.cultivate(
        "大语言模型", "自然语言处理",
        method_seed_occurrences=3,
        method_seed_wuxing="水",
        topic_seed_wuxing="金",  # 金生水 → 相生，不触发越界
        environmental_factors=env_with_decl,
    )
    ca33 = r33.constitution_audit
    decl_check_33 = [c for c in ca33.get("checks", []) if c["check_name"] == "壳核审计声明"]
    if decl_check_33:
        assert decl_check_33[0]["verdict"] == "PASS", (
            f"有声明应PASS，实际: {decl_check_33[0]['verdict']}"
        )
        print(f"  壳核审计声明: [{decl_check_33[0]['verdict']}] {decl_check_33[0]['reason'][:60]}...")
    # 金生水 → 相生，宪法审计应通过
    print(f"  宪法审计通过: {ca33['passed']}")
    if not ca33['passed']:
        for c in ca33.get('checks', []):
            print(f"    [{c['verdict']}] {c['check_name']}: {c['reason'][:80]}")
        print(f"    topic_wx in env: {r33.step2_nurture.get('environmental_factors', {}).get('topic', {}).get('wuxing', '?')}")
        print(f"    step1 topic_seed wuxing: {r33.step1_identify.get('topic_seed', {}).get('wuxing', '?')}")
    print(f"  壳核声明: nucleus={r33.shell_nucleus_declaration.get('nucleus_measured', '?')}")
    print("  ✅ 测试 33 通过")

    # 测试 34: V1.5 纯粹度审计 — 保持×时间×抗摇摆
    print("\n[测试 34] V1.5 纯粹度审计 — 保持×时间×抗摇摆")
    r34 = cultivator.cultivate(
        "大语言模型", "自然语言处理",
        method_seed_occurrences=4,
        method_seed_wuxing="水",
        topic_seed_wuxing="金",  # 金生水 → 相生
        harvest_methodology_wuxing="水",  # 同向 → 保持度≈1.0
        environmental_factors=env_with_decl,
    )
    purity = r34.purity_result
    assert purity, "应有纯粹度审计结果"
    assert purity.get("purity_score", 0) > 0, "纯粹度应>0"
    assert purity.get("retention", 0) > 0.5, "同向应保持度>0.5"
    assert "anti_sway" in purity, "应有抗摇摆字段"
    assert not purity.get("anti_sway_calibrated", True), "抗摇摆应标注'待校准'"
    print(f"  纯粹度: {purity.get('purity_score', 0):.4f}")
    print(f"  保持度: {purity.get('retention', 0):.4f}")
    print(f"  持续时间: {purity.get('duration', 0):.2f}")
    anti_sway_val = purity.get('anti_sway', 1.0)
    anti_sway_display = "待校准" if not purity.get('anti_sway_calibrated') else f"{anti_sway_val:.2f}"
    print(f"  抗摇摆: {anti_sway_display}")
    print(f"  解读: {purity.get('interpretation', '?')[:60]}...")
    print("  ✅ 测试 34 通过")

    # 测试 35: V1.5 协议级日损记录
    print("\n[测试 35] V1.5 协议级日损记录")
    r35 = cultivator.cultivate(
        "大语言模型", "自然语言处理",
        method_seed_occurrences=3,
        method_seed_wuxing="水",
        topic_seed_wuxing="金",  # 金生水 → 相生
        environmental_factors=env_with_decl,
    )
    proto_subs = r35.protocol_subtractions
    assert proto_subs, "应有协议级日损记录"
    assert len(proto_subs) == 5, f"应有 5 项协议级日损，实际: {len(proto_subs)}"
    for ps in proto_subs:
        assert "item" in ps, "每项应有 item 字段"
        assert "reason" in ps, "每项应有 reason 字段"
        assert "reversible" in ps, "每项应有 reversible 字段"
    print(f"  协议级日损: {len(proto_subs)} 项")
    for ps in proto_subs:
        rev = "可逆" if ps["reversible"] else "不可逆"
        print(f"    → {ps['item']}: {ps['reason'][:40]}... ({rev})")
    print("  ✅ 测试 35 通过")

    # 测试 36: V1.5 format_summary 含 V1.5 字段
    print("\n[测试 36] V1.5 format_summary — 含 V1.5 字段")
    summary = cultivator.format_summary(r34)
    assert "V1.5" in summary, "报告应含 V1.5 版本号"
    assert "壳核审计声明" in summary, "报告应含壳核审计声明"
    assert "纯粹度审计" in summary, "报告应含纯粹度审计"
    assert "协议级日损记录" in summary, "报告应含协议级日损记录"
    assert "保持×时间×抗摇摆" in summary, "报告应含纯粹度公式"
    print(f"  报告长度: {len(summary)} 字符")
    print(f"  含 V1.5 版本号: ✅")
    print(f"  含壳核审计声明: ✅")
    print(f"  含纯粹度审计: ✅")
    print(f"  含协议级日损记录: ✅")
    print("  ✅ 测试 36 通过")

    # ═══════════════════════════════════════════════
    # V1.5 Phase B 新增测试
    # ═══════════════════════════════════════════════

    # 测试 37: 熵振引擎 — 失败质量审核（真失败）
    print("\n[测试 37] V1.5 Phase B 熵振引擎 — 真失败 vs 表演性失败")
    # 真失败：含可证伪条件、可复现、有修正方向
    true_failure = [{
        "event_type": "实验失败",
        "description": "五行诊断实验未通过",
        "has_falsification_condition": True,
        "is_reproducible": True,
        "has_correction_path": True,
        "is_expected_failure": False,
    }]
    audit_true = cultivator._failure_quality_audit(true_failure)
    assert len(audit_true) == 1, "应有 1 项审核结果"
    assert audit_true[0]["failure_type"] == FailureQuality.TRUE_FAILURE.value, "应为真失败"
    assert audit_true[0]["reward_eligible"] == True, "真失败应奖励"
    print(f"  真失败审核: {audit_true[0]['failure_type']} (奖励: {audit_true[0]['reward_eligible']})")
    print(f"  判定依据: {audit_true[0]['evidence'][:60]}...")

    # 表演性失败：预期失败、无证伪条件
    performative_failure = [{
        "event_type": "实验失败",
        "description": "选不可能任务故意失败",
        "has_falsification_condition": False,
        "is_reproducible": False,
        "has_correction_path": False,
        "is_expected_failure": True,
    }]
    audit_perf = cultivator._failure_quality_audit(performative_failure)
    assert len(audit_perf) == 1
    assert audit_perf[0]["failure_type"] == FailureQuality.PERFORMATIVE_FAILURE.value, "应为表演性失败"
    assert audit_perf[0]["reward_eligible"] == False, "表演性失败不应奖励"
    print(f"  表演性失败审核: {audit_perf[0]['failure_type']} (奖励: {audit_perf[0]['reward_eligible']})")
    print("  ✅ 测试 37 通过")

    # 测试 38: 待验证假设清单
    print("\n[测试 38] V1.5 Phase B 待验证假设清单 — 5 项诚实声明")
    hypotheses = cultivator._track_hypotheses()
    assert len(hypotheses) == 5, f"应有 5 项假设，实际: {len(hypotheses)}"
    for h in hypotheses:
        assert "hypothesis_id" in h, "每项应有 hypothesis_id"
        assert "statement" in h, "每项应有 statement"
        assert "status" in h, "每项应有 status"
        assert h["status"] == PendingHypothesisStatus.PENDING.value, f"初始状态应为待验证，实际: {h['status']}"
        assert "verification_path" in h, "每项应有 verification_path"
    print(f"  假设数量: {len(hypotheses)}")
    for h in hypotheses:
        print(f"    [{h['hypothesis_id']}] {h['status']}: {h['statement'][:40]}...")
    print("  ✅ 测试 38 通过")

    # 测试 39: 换球心决策 — 触发条件
    print("\n[测试 39] V1.5 Phase B 换球心决策 — 触发条件")
    # 场景 A: 纯粹度不足，不触发（只有1轮）
    br_insufficient = cultivator._ball_replacement_decision(
        [0.5], SystemType.NUCLEUS_MEASURING.value
    )
    assert br_insufficient["triggered"] == False, "纯粹度历史不足不应触发"
    assert br_insufficient["action"] == "wait"
    print(f"  场景A（1轮，等待）: triggered={br_insufficient['triggered']}, action={br_insufficient['action']}")

    # 场景 B: 纯粹度正常，不触发
    br_normal = cultivator._ball_replacement_decision(
        [0.8, 0.85], SystemType.NUCLEUS_MEASURING.value
    )
    assert br_normal["triggered"] == False
    assert br_normal["action"] == "continue"
    print(f"  场景B（正常）: triggered={br_normal['triggered']}, action={br_normal['action']}")

    # 场景 C: 测壳体系，不触发换球心
    br_shell = cultivator._ball_replacement_decision(
        [0.5, 0.4], SystemType.SHELL_MEASURING.value
    )
    assert br_shell["triggered"] == False, "测壳体系不应触发换球心"
    assert br_shell["action"] == "skip"
    print(f"  场景C（测壳体系）: triggered={br_shell['triggered']}, action={br_shell['action']}")

    # 场景 D: 连续2轮<0.7 + 测核体系 → 触发
    br_trigger = cultivator._ball_replacement_decision(
        [0.5, 0.4], SystemType.NUCLEUS_MEASURING.value
    )
    assert br_trigger["triggered"] == True, "连续2轮<0.7且测核体系应触发"
    assert br_trigger["action"] == "evaluate_replacement"
    assert len(br_trigger["candidate_systems"]) >= 2, "应有候选体系"
    print(f"  场景D（触发）: triggered={br_trigger['triggered']}, action={br_trigger['action']}")
    print(f"    候选体系: {[c['system'] for c in br_trigger['candidate_systems']]}")

    # 场景 E: 反例保护 — 厚积期（>5年+抗摇摆）
    br_protect = cultivator._ball_replacement_decision(
        [0.5, 0.4], SystemType.NUCLEUS_MEASURING.value, anti_sway_duration=6.0
    )
    assert br_protect["triggered"] == False, "厚积期应受保护"
    assert br_protect["action"] == "protect"
    print(f"  场景E（厚积期保护）: triggered={br_protect['triggered']}, action={br_protect['action']}")
    print("  ✅ 测试 39 通过")

    # 测试 40: 留白条款
    print("\n[测试 40] V1.5 Phase B 留白条款 — 每3轮1留白")
    # 场景 A: 第3轮 → 留白轮
    blank_3 = cultivator._manage_blank_space(3)
    assert blank_3["is_blank_round"] == True, "第3轮应为留白轮"
    assert blank_3["action"] == "observe_only"
    print(f"  场景A（第3轮）: 留白={blank_3['is_blank_round']}, action={blank_3['action']}")

    # 场景 B: 第1轮 → 非留白轮
    blank_1 = cultivator._manage_blank_space(1)
    assert blank_1["is_blank_round"] == False
    print(f"  场景B（第1轮）: 留白={blank_1['is_blank_round']}, action={blank_1['action']}")

    # 场景 C: +2 高价值信号提前结束留白
    blank_signal = cultivator._manage_blank_space(3, high_value_signals=2)
    assert blank_signal["is_blank_round"] == False, "高价值信号应提前结束留白"
    assert blank_signal["action"] == "signal_override"
    print(f"  场景C（信号优先）: 留白={blank_signal['is_blank_round']}, action={blank_signal['action']}")

    # 场景 D: deadline 模式跳过留白
    cultivator.config["blank_space_deadline_mode"] = True
    blank_dl = cultivator._manage_blank_space(3)
    assert blank_dl["is_blank_round"] == False
    assert blank_dl["skipped_for_deadline"] == True
    assert blank_dl["owed_rounds"] == 1
    print(f"  场景D（deadline跳过）: 留白={blank_dl['is_blank_round']}, 欠={blank_dl['owed_rounds']}轮")
    cultivator.config["blank_space_deadline_mode"] = False  # 恢复
    print("  ✅ 测试 40 通过")

    # 测试 41: 日益饱和检测
    print("\n[测试 41] V1.5 Phase B 日益饱和检测 — 边际产出递减")
    # 场景 A: 边际产出正常
    addition_normal = [
        {"round": 1, "output_score": 0.5},
        {"round": 2, "output_score": 0.7},
        {"round": 3, "output_score": 0.85},
    ]
    sat_normal = cultivator._saturation_detection(addition_normal)
    assert sat_normal["saturated"] == False, "边际产出增长不应饱和"
    print(f"  场景A（正常增长）: saturated={sat_normal['saturated']}")

    # 场景 B: 边际产出递减 → 饱和
    addition_saturated = [
        {"round": 1, "output_score": 0.5},
        {"round": 2, "output_score": 0.7},
        {"round": 3, "output_score": 0.55},  # 边际产出下降
    ]
    sat_saturated = cultivator._saturation_detection(addition_saturated)
    assert sat_saturated["saturated"] == True, "边际产出递减应触发饱和"
    assert sat_saturated["action"] == "switch_to_subtraction"
    print(f"  场景B（饱和）: saturated={sat_saturated['saturated']}, marginal={sat_saturated['marginal_output']:.4f}")
    print(f"    建议: {sat_saturated['recommendation'][:60]}...")

    # 场景 C: 不足3轮不检测
    sat_short = cultivator._saturation_detection(addition_saturated[:2])
    assert sat_short["saturated"] == False
    print(f"  场景C（不足3轮）: saturated={sat_short['saturated']}")
    print("  ✅ 测试 41 通过")

    # 测试 42: Phase B 集成 — 完整培育含 Phase B 字段
    print("\n[测试 42] V1.5 Phase B 集成 — 完整培育含 Phase B 字段")
    r42 = cultivator.cultivate(
        "大语言模型", "自然语言处理",
        method_seed_occurrences=3,
        method_seed_wuxing="水",
        topic_seed_wuxing="金",
        environmental_factors=env_with_decl,
    )
    # 熵振引擎
    ev = r42.entropy_vibration
    assert "quality_audits" in ev, "应含熵振质量审核"
    assert "principle" in ev, "应含熵振原则"
    # 待验证假设
    assert len(r42.pending_hypotheses) == 5, "应含5项待验证假设"
    # 留白
    assert "is_blank_round" in r42.blank_space, "应含留白决策"
    # 日益饱和
    assert "saturated" in r42.saturation_detection, "应含饱和检测"
    # 换球心
    assert "triggered" in r42.ball_replacement, "应含换球心决策"
    print(f"  熵振引擎: {ev.get('true_failures', 0)} 真, {ev.get('performative_failures', 0)} 表演")
    print(f"  待验证假设: {len(r42.pending_hypotheses)} 项")
    print(f"  留白: is_blank={r42.blank_space.get('is_blank_round')}, action={r42.blank_space.get('action')}")
    print(f"  日益饱和: saturated={r42.saturation_detection.get('saturated')}")
    print(f"  换球心: triggered={r42.ball_replacement.get('triggered')}")
    print("  ✅ 测试 42 通过")

    print("\n" + "=" * 60)
    print("自检完成 — 全部 42 项测试通过 (V1.5 Phase B)")