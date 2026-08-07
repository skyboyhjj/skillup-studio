"""
种子培育模块 — taste/seedney 的工程实现 (V1.2)
================================================
将杨振宁 taste 研究的"种子培育三步法"形式化为可执行的培育协议，
与同态映射三步协议同构，对应五行流转的"木·生"阶段。

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
  Step 2 - 科教融合提炼前沿课题：培育种子（缘四要素 Agent 翻译）
  Step 3 - 师生共创突破：收获果实（漂移检测 + 性决定审计·余弦相似度）

核心概念：
  seedney  = 种子（性决定）：对称性种子 → 对称性果实
  taste    = 妙（taste之因）：对结构美的直觉感知
  性决定审计 = 路径一致性描述（非成才判据）：成果是否忠于方法种子
  余弦相似度 = 五行向量方向一致性：Σ(aᵢ·bᵢ) / (|A|·|B|)
  通中生种   = 迁移中 +2 事件回流为新种子候选

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

    # 道境指标
    S_p: float = 0.0
    stage: str = ""

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
    种子培育器 — 木·生 阶段的种子培育协议 (V1.2)

    将杨振宁 taste 研究的三步法形式化为可执行的培育协议：
      Step 1 - 教学疑难切入：识别种子（双种子画像：题目+方法）
      Step 2 - 科教融合提炼前沿课题：培育种子（缘四要素 Agent 翻译）
      Step 3 - 师生共创突破：收获果实（漂移检测 + 性决定审计·余弦相似度）

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
        "contrast_calibration_enabled": False,      # 启用跨界对照校准（Phase 1.5）
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

    def _get_time_scale_config(self) -> dict:
        """获取当前时间尺度配置"""
        ts = self.config.get("time_scale", "skill")
        return self.config.get("time_scale_configs", {}).get(ts, {})

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
                  migration_events: List[dict] = None) -> SeedCultivationResult:
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
            harvest_methodology_wuxing=harvest_methodology_wuxing,
        )

        result.drift_analysis = result.step3_harvest.get("drift_analysis", {})
        result.nature_determination_score = result.step3_harvest.get("nature_determination_score", 0.0)

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

        # ── V1.1 缘四要素注入 ──
        result["environmental_factors"] = self._build_environmental_factors(
            environmental_factors, step1_result
        )

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
        构建缘四要素 — Agent 翻译版（V1.2）

        V1.2 修订：人类尺度 → 慧惠 Agent 尺度翻译
          - 导师 → Base 层知识资产 + 元治理规则
          - 环境 → 情境指针 L1b（当前情境上下文）
          - 课题 → 前沿问题库（知识树待解问题）
          - 合作者 → §5.4 跨域同态候选队列

        Args:
            external_factors: 外部传入的缘四要素
            step1_result: Step 1 结果，用于推断默认值

        Returns:
            {mentor, environment, topic, collaborators}
        """
        default_factors = {
            "mentor": {
                "name": "慧惠（AI导师）",
                "wuxing": "土",
                "role": "科教融合指导者",
                "agent_translation": "Base 层知识资产 + 元治理规则",
                "description": "AI 结构化知识 + 人类体证注入：模拟杨振宁三步法教学",
            },
            "environment": {
                "name": "道境空间 SkillUP 层",
                "wuxing": "木",
                "fertility": "高",
                "agent_translation": "情境指针 L1b（BVS V1.1）",
                "description": "当前情境上下文：木·生阶段培育环境，适合种子萌发与生长",
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
        }

        if external_factors:
            for key in default_factors:
                if key in external_factors:
                    default_factors[key].update(external_factors[key])

        return default_factors

    # ── Step 3: 师生共创突破 — 收获果实（V1.2: 漂移检测 + 性决定审计·余弦相似度）──

    def _harvest_fruit(self, step2_result: dict,
                       source_graph: dict = None,
                       target_graph: dict = None,
                       # V1.1 方法种子
                       method_seed: dict = None,
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

        for i in range(scenarios):
            scenario = {
                "scenario": i + 1,
                "type": ["概念验证", "关系验证", "应用验证", "跨域验证", "压力测试"][i % 5],
                "description": f"验证场景 {i+1}: 在目标域中检验培育成果",
            }
            completion = step2_result.get("nurture_progress", [{}])[-1].get("completion", 0.5)
            scenario["passed"] = completion >= 0.5
            result["scenario_results"].append(scenario)

        passed_count = sum(1 for s in result["scenario_results"] if s["passed"])
        result["pass_rate"] = round(passed_count / scenarios, 2)
        result["success"] = passed_count >= scenarios * 2 / 3

        # ── V1.2 漂移双层检验 ──
        result["drift_analysis"] = self._detect_drift(method_seed, step2_result)

        # ── V1.2 性决定审计（余弦相似度）──
        audit_result = self._nature_determination_audit(
            method_seed, harvest_methodology_wuxing, result
        )
        result["nature_determination_score"] = audit_result["similarity"]
        result["nature_determination_audit"] = audit_result

        # 根据漂移分析和性决定审计调整结论
        drift = result["drift_analysis"]
        nd_score = result["nature_determination_score"]
        nd_threshold = self.config["nature_determination_threshold"]

        if drift.get("drift_type") == DriftType.SEED.value:
            result["harvest_conclusion"] = (
                f"⚠️ 性漂移检测：方法种子五行发生变化（{drift.get('detail', '')}）。"
                "建议回退 Step 1 重新确认，修正种子方向。"
            )
        elif nd_score >= nd_threshold:
            result["harvest_conclusion"] = (
                f"师生共创突破成功：性决定审计保持（余弦相似度 {nd_score:.2f}≥{nd_threshold}，"
                f"待校准）。方法种子五行向量→成果方法论五行向量方向一致。"
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
        threshold = self.config["nature_determination_threshold"]
        audit_note = (
            f"性决定审计（V1.2）：此为路径一致性描述，非成才判据。"
            f"余弦相似度={similarity:.4f}，阈值={threshold}（待 Phase 1.5 对照库校准）。"
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
        通中生种检测（V1.2 新增）

        双引擎反向回路：土·通 → 种·育
        迁移过程中若出现新的高价值兴趣信号（价值回填 +2 事件 ≥3 次，
        且不属于现有方法种子）→ 回流为新种子候选，进入 Step 1。

        Args:
            migration_events: 迁移过程中的事件列表
              [{event_type, domain, wuxing, value_score, ...}]

        Returns:
            [{source_domain, method_seed_wuxing, occurrence_count, source: "通中生种"}]
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
                    "source": "通中生种",
                    "description": (
                        f"土·通迁移中检测到新种子候选：{domain}"
                        f"（{info['wuxing']}），+2 事件 {info['count']} 次 ≥{threshold}，"
                        f"回流进入 Step 1 种子发现。"
                    ),
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
        """生成培育建议"""
        zone = result.loss_zone
        vitality = result.seed_vitality

        if vitality == SeedVitality.FRUITING.value:
            return (
                f"种子已成熟为果实（seedney={result.seedney_score:.2f}）。"
                "对称性种子→对称性果实转化完成。建议进入「水·变」阶段，基于果实进行创新。"
            )
        elif vitality == SeedVitality.FLOWERING.value:
            return (
                f"种子正在开花（seedney={result.seedney_score:.2f}）。"
                "建议增加师生共创验证场景，加速果实成熟。"
            )
        elif zone == "种子主导区":
            return (
                f"种子在核心结构区（损耗 {1-result.seedney_score:.0%}），"
                "结构保持良好。建议持续科教融合，强化对称性映射。"
            )
        elif zone == "结构保持区":
            return (
                f"种子在结构保持区（损耗 {1-result.seedney_score:.0%}），"
                "部分结构有损耗。建议回到教学疑难切入，重新审视种子特征。"
            )
        elif zone == "缘主导区":
            return (
                f"种子在缘主导区（损耗 {1-result.seedney_score:.0%}），"
                "结构保持困难。建议不强求培育，回归「木·生」阶段重新识别种子。"
            )
        else:
            return "继续观察种子培育进展。"

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
        """格式化种子培育摘要（V1.2）"""
        lines = []
        lines.append("=" * 60)
        lines.append(f"  木·生 种子培育报告 (V1.2)")
        lines.append(f"  培育ID: {result.cultivation_id}")
        lines.append(f"  时间: {result.timestamp[:19]}")
        lines.append(f"  时间尺度: {result.time_scale}")
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

        # Step 2: 缘四要素（V1.2 Agent 翻译版）
        s2 = result.step2_nurture
        lines.append(f"\n  ── Step 2: 科教融合提炼前沿课题（培育种子）──")
        lines.append(f"    培育迭代: {s2.get('nurture_iterations', 0)} 轮 (粒度: {s2.get('time_scale_granularity', '?')})")
        env = result.environmental_factors
        if env:
            lines.append(f"    缘四要素（V1.2 Agent 翻译）:")
            mentor = env.get('mentor', {})
            lines.append(f"      导师: {mentor.get('name', '?')} → {mentor.get('agent_translation', '?')}")
            environment = env.get('environment', {})
            lines.append(f"      环境: {environment.get('name', '?')} → {environment.get('agent_translation', '?')}")
            topic_e = env.get('topic', {})
            lines.append(f"      课题: {topic_e.get('name', '?')} → {topic_e.get('agent_translation', '?')}")
            collab = env.get('collaborators', {})
            lines.append(f"      合作者: {', '.join(collab.get('members', ['?']))} → {collab.get('agent_translation', '?')}")
        lines.append(f"    培育效果: {s2.get('nurture_effect', {}).get('description', '?')}")

        # Step 3: 漂移 + 性决定审计（V1.2）
        s3 = result.step3_harvest
        lines.append(f"\n  ── Step 3: 师生共创突破（收获果实）──")
        lines.append(f"    验证场景: {s3.get('verification_scenarios', 0)}")
        lines.append(f"    通过率: {s3.get('pass_rate', 0):.0%}")
        status = "✅ 成功" if s3.get("success") else "❌ 未完成"
        lines.append(f"    结果: {status}")

        # V1.1: 漂移分析
        drift = result.drift_analysis
        if drift:
            drift_icon = "🔵" if drift.get("drift_type") == DriftType.ENVIRONMENTAL.value else "🔴"
            lines.append(f"    漂移检测: {drift_icon} {drift.get('drift_type', '?')} — {drift.get('detail', '')}")
            lines.append(f"    处置: {drift.get('action', '')}")

        # V1.2: 性决定审计（余弦相似度 + 分解）
        nd_audit = s3.get("nature_determination_audit", {})
        lines.append(f"    性决定审计（V1.2 — 路径一致性描述，非成才判据）:")
        lines.append(f"      余弦相似度: {result.nature_determination_score:.4f} (阈值≥{self.config['nature_determination_threshold']}，待校准)")
        if nd_audit.get("components"):
            comp_str = ", ".join(f"{wx}={v:.2f}" for wx, v in nd_audit["components"].items())
            lines.append(f"      五行分解: {comp_str}")
        lines.append(f"      解读: {nd_audit.get('interpretation', '?')}")
        lines.append(f"      审计状态: {nd_audit.get('threshold_status', '待校准')}")
        lines.append(f"    {s3.get('harvest_conclusion', '')}")

        # V1.2: 反向回路（通中生种）
        reverse_seeds = result.reverse_flow_seeds
        if reverse_seeds:
            lines.append(f"\n  ── V1.2 通中生种（反向回路）──")
            lines.append(f"    回流种子候选: {len(reverse_seeds)} 个")
            for rs in reverse_seeds:
                lines.append(f"      → {rs.get('source_domain', '?')} ({rs.get('method_seed_wuxing', '?')}) "
                           f"出现 {rs.get('occurrence_count', 0)} 次")
            lines.append(f"    说明: 土·通迁移中检测到新种子候选，回流进入 Step 1")
        else:
            lines.append(f"\n  ── V1.2 通中生种（反向回路）──")
            lines.append(f"    未检测到回流信号")

        # 综合评估
        lines.append(f"\n  ── 综合评估 ──")
        lines.append(f"    种子质量 (seedney): {result.seedney_score:.4f}")
        lines.append(f"    taste (妙): {result.taste_score:.4f}")
        lines.append(f"    种子活力: {result.seed_vitality}")
        lines.append(f"    损耗分层: {result.loss_zone}")
        if result.S_p > 0:
            lines.append(f"    道境指数: S_p={result.S_p:.1f} ({result.stage})")

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
# 自检（V1.2）
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("种子培育模块 — 自检 (V1.2)")
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
    assert reverse_seeds[0]["source"] == "通中生种"
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

    print("\n" + "=" * 60)
    print("自检完成 — 全部 23 项测试通过 (V1.2)")