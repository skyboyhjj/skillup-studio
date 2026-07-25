"""
五行八卦 DSL 解析器 — wuxing_dsl.py
版本：v1.0
功能：自然语言 → DSL 命令转换，MAP / LEARN / CORRECT / LAYER / FLOW 五指令解析与执行
架构：参考慧惠 huihui-chat.js 的意图检测模式（detectIntent → handleIntent）
"""

import json
import re
import copy
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any

# ===== 常量 =====
WUXING_ELEMENTS = ["木", "火", "土", "金", "水"]
BAGUA_SYMBOLS = ["☰乾", "☱兑", "☲离", "☳震", "☴巽", "☵坎", "☶艮", "☷坤"]
LAYER_KEYS = ["outer", "middle", "inner"]
COGNITIVE_LEVELS = ["L1", "L2", "L3", "L4"]
FLOW_STAGES = ["木·种子萌发", "火·繁茂整合", "金·修剪遗忘", "水·更新重组", "土·迁移沉淀"]

# 规则库路径
RULES_DIR = Path(__file__).parent / "rules" / "domains"

# ===== DSL 指令定义 =====
DSL_COMMANDS = {
    "MAP": {
        "desc": "映射概念到五行/八卦",
        "syntax": "MAP <concept> → <element>",
        "example": "MAP 关元 → 水",
        "nl_triggers": ["映射", "对应", "归属", "属于", "归为", "映射到", "放在", "加到"]
    },
    "LEARN": {
        "desc": "从规则库学习新概念关联",
        "syntax": "LEARN <concept> → <element> [weight=N]",
        "example": "LEARN 丹参 → 火 weight=0.9",
        "nl_triggers": ["学习", "新概念", "添加", "新增", "加入", "学会"]
    },
    "CORRECT": {
        "desc": "修正已有映射的权重或归属",
        "syntax": "CORRECT <concept> [weight=N] [→ <element>]",
        "example": "CORRECT 太渊 weight=1.5",
        "nl_triggers": ["修正", "修改", "调整", "改", "纠正", "变更"]
    },
    "LAYER": {
        "desc": "调整三层架构归属",
        "syntax": "LAYER <concept> → <outer|middle|inner>",
        "example": "LAYER 内视 → inner",
        "nl_triggers": ["层级", "架构", "归属层", "放在哪层", "移到", "分层"]
    },
    "FLOW": {
        "desc": "管理五行流转阶段",
        "syntax": "FLOW add|remove <stage> → <concept>",
        "example": "FLOW add 木·种子萌发 → 补法",
        "nl_triggers": ["流转", "阶段", "阶段添加", "阶段移除", "生命周期", "成长阶段"]
    }
}


class DSLParser:
    """DSL 解析器：NL → DSL 命令 → 规则更新"""

    def __init__(self, domain: str = "chinese_medicine"):
        self.domain = domain
        self.rules = self._load_rules()
        self.command_log: List[Dict] = []  # 操作日志，支持撤销

    # ===== 规则加载 =====
    def _load_rules(self) -> Dict:
        """加载域规则文件"""
        rules_path = RULES_DIR / f"{self.domain}.json"
        if not rules_path.exists():
            raise FileNotFoundError(f"规则文件不存在: {rules_path}")
        with open(rules_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_rules(self) -> None:
        """保存规则到文件"""
        rules_path = RULES_DIR / f"{self.domain}.json"
        with open(rules_path, "w", encoding="utf-8") as f:
            json.dump(self.rules, f, ensure_ascii=False, indent=2)

    def get_rules(self) -> Dict:
        """获取当前规则快照"""
        return copy.deepcopy(self.rules)

    # ===== 意图检测（参考 huihui-chat.js detectMirrorIntent 模式）=====
    def detect_intent(self, user_message: str) -> Optional[Dict]:
        """
        从自然语言中检测 DSL 意图
        返回: {"command": "MAP", "concept": "关元", "element": "水", "weight": None}
        """
        msg = user_message.strip()

        # 尝试匹配显式 DSL 语法
        dsl = self._parse_explicit_dsl(msg)
        if dsl:
            return dsl

        # 尝试自然语言 → DSL 映射
        return self._parse_natural_language(msg)

    def _parse_explicit_dsl(self, msg: str) -> Optional[Dict]:
        """解析显式 DSL 语法，如 'MAP 关元 → 水'"""
        for cmd in DSL_COMMANDS:
            if msg.upper().startswith(cmd):
                rest = msg[len(cmd):].strip()
                return self._parse_dsl_params(cmd, rest)
        return None

    def _parse_dsl_params(self, command: str, params: str) -> Optional[Dict]:
        """解析 DSL 参数部分"""
        result = {"command": command}

        # 解析概念、元素、权重
        # 支持: concept → element, concept weight=N, concept → element weight=N
        arrow_match = re.match(r'(.+?)\s*(?:→|->)\s*(.+)', params)
        if arrow_match:
            result["concept"] = arrow_match.group(1).strip()
            right_side = arrow_match.group(2).strip()
            # 检查右侧是否有 weight=
            weight_match = re.search(r'weight\s*=\s*([\d.]+)', right_side)
            if weight_match:
                result["weight"] = float(weight_match.group(1))
                result["element"] = right_side[:weight_match.start()].strip()
            else:
                result["element"] = right_side
        else:
            # 可能只有概念和权重
            parts = params.split()
            result["concept"] = parts[0] if parts else params
            weight_match = re.search(r'weight\s*=\s*([\d.]+)', params)
            if weight_match:
                result["weight"] = float(weight_match.group(1))

        return result if result.get("concept") else None

    def _parse_natural_language(self, msg: str) -> Optional[Dict]:
        """自然语言 → DSL 意图映射"""
        result = {}

        # 检测命令类型
        for cmd, info in DSL_COMMANDS.items():
            for trigger in info["nl_triggers"]:
                if trigger in msg:
                    result["command"] = cmd
                    break
            if result.get("command"):
                break

        if not result.get("command"):
            return None

        # === 提取概念（优先使用中文结构模式） ===

        # 书名号优先
        bookname_match = re.search(r'《(.+?)》', msg)
        if bookname_match:
            result["concept"] = bookname_match.group(1)
        else:
            result["concept"] = self._extract_concept_nl(msg, result["command"])

        # === 提取其他参数 ===

        # 目标元素（五行/八卦）
        for elem in WUXING_ELEMENTS + BAGUA_SYMBOLS:
            if elem in msg:
                # 确保元素不等于概念本身
                if elem != result.get("concept", ""):
                    result["element"] = elem
                    break

        # 权重
        weight_match = re.search(r'权重\s*[=为]?\s*([\d.]+)', msg)
        if weight_match:
            result["weight"] = float(weight_match.group(1))

        # 层级
        layer_map = {"外层": "outer", "中层": "middle", "内层": "inner",
                     "Base": "outer", "View": "middle", "SkillUP": "inner",
                     "体": "outer", "相": "middle", "用": "inner"}
        for nl_layer, key in layer_map.items():
            if nl_layer in msg:
                result["layer"] = key
                break

        # 流转阶段
        for stage in FLOW_STAGES:
            if stage in msg:
                result["stage"] = stage
                break

        # add/remove
        if "添加" in msg or "加入" in msg or "add" in msg.lower():
            result["action"] = "add"
        elif "移除" in msg or "删除" in msg or "remove" in msg.lower():
            result["action"] = "remove"

        return result if result.get("concept") else None

    def _extract_concept_nl(self, msg: str, command: str) -> Optional[str]:
        """
        从自然语言中提取操作目标概念。
        支持多种中文结构模式：
        - "把 X 映射到 Y" → X
        - "将 X 归为 Y" → X
        - "X 属于 Y" → X
        - "修正/调整 X 的权重" → X
        - "把 X 移到内层" → X
        """
        # 模式1: 把/将 X 动词 到/为 Y
        # 匹配 "把丹参映射到火"、"将内视移到内层" 等
        ba_jiang_pattern = re.compile(r'[把将](.+?)(?:映射|对应|归属|归为|属于|映射到|放在|加到|移到|移|添加|加入|新增|学习)')
        m = ba_jiang_pattern.search(msg)
        if m:
            concept = m.group(1).strip()
            # 清理：去除可能的尾随虚词和标点
            concept = re.sub(r'[的之，,。\s]+$', '', concept)
            if concept and len(concept) <= 10:
                return concept

        # 模式2: X 属于/对应 Y （前置概念）
        # 匹配 "丹参属于火"、"肝对应木"
        for trigger in ["属于", "对应", "归为", "归属"]:
            if trigger in msg:
                idx = msg.index(trigger)
                prefix = msg[:idx].strip()
                # 取最后一个连续的中文词作为概念
                concept_match = re.search(r'([\u4e00-\u9fff\w]{1,8})$', prefix)
                if concept_match:
                    concept = concept_match.group(1)
                    # 排除已知元素/层级
                    if concept not in WUXING_ELEMENTS and concept not in BAGUA_SYMBOLS:
                        return concept

        # 模式3: 修正/修改/调整 X 的权重
        for trigger in ["修正", "修改", "调整", "纠正", "变更"]:
            if trigger in msg:
                idx = msg.index(trigger) + len(trigger)
                remaining = msg[idx:].strip()
                # 去除"的"、"为"等虚词，但只取到"的"或"权重"之前的词
                remaining = re.sub(r'^(的|之|为|到|至)\s*', '', remaining)
                # 只取到"的"、"权重"、"weight"之前
                concept_end = re.search(r'[的权重weight]', remaining)
                if concept_end:
                    remaining = remaining[:concept_end.start()]
                concept_match = re.match(r'([\u4e00-\u9fff\w]{1,8})', remaining)
                if concept_match:
                    concept = concept_match.group(1)
                    if concept not in WUXING_ELEMENTS:
                        return concept

        # 模式4: 添加/学习/新增 X 到 Y（触发词前置）
        # 匹配 "添加补法到木·种子萌发阶段"、"学习合谷归为水"
        for trigger in ["添加", "学习", "新增", "加入"]:
            if msg.startswith(trigger) or trigger in msg:
                idx = msg.index(trigger) + len(trigger)
                remaining = msg[idx:].strip()
                # 去除"新概念"等修饰词
                remaining = re.sub(r'^(新概念|概念)\s*', '', remaining)
                # 取到"到"、"归为"、"→"、"->"之前
                concept_end = re.search(r'[到归为→\-]|阶段', remaining)
                if concept_end:
                    remaining = remaining[:concept_end.start()]
                remaining = remaining.strip().rstrip('，,')
                concept_match = re.match(r'([\u4e00-\u9fff\w]{1,8})', remaining)
                if concept_match:
                    concept = concept_match.group(1)
                    if concept not in WUXING_ELEMENTS + BAGUA_SYMBOLS:
                        return concept

        # 模式5: 在触发词后的概念（fallback）
        for trigger in DSL_COMMANDS[command]["nl_triggers"]:
            if trigger in msg:
                idx = msg.index(trigger) + len(trigger)
                remaining = msg[idx:].strip()
                remaining = re.sub(r'^(为|到|成|至|→|->|的)\s*', '', remaining)
                concept_match = re.match(r'([\u4e00-\u9fff\w]{1,8})', remaining)
                if concept_match:
                    concept = concept_match.group(1)
                    if concept not in WUXING_ELEMENTS + BAGUA_SYMBOLS:
                        return concept
                break

        return None

    # ===== DSL 命令执行 =====
    def execute(self, intent: Dict) -> Dict:
        """执行 DSL 命令并返回结果"""
        command = intent.get("command")
        if not command:
            return {"success": False, "error": "未识别到有效 DSL 命令"}

        # 保存快照用于撤销
        snapshot = copy.deepcopy(self.rules)

        try:
            if command == "MAP":
                result = self._cmd_map(intent)
            elif command == "LEARN":
                result = self._cmd_learn(intent)
            elif command == "CORRECT":
                result = self._cmd_correct(intent)
            elif command == "LAYER":
                result = self._cmd_layer(intent)
            elif command == "FLOW":
                result = self._cmd_flow(intent)
            else:
                result = {"success": False, "error": f"未知命令: {command}"}

            if result.get("success"):
                self._save_rules()
                self.command_log.append({
                    "command": command,
                    "intent": intent,
                    "snapshot": snapshot
                })

            return result
        except Exception as e:
            self.rules = snapshot  # 回滚
            return {"success": False, "error": str(e)}

    def _cmd_map(self, intent: Dict) -> Dict:
        """MAP: 映射概念到五行/八卦"""
        concept = intent.get("concept")
        element = intent.get("element")
        weight = intent.get("weight", 1.0)

        if not concept or not element:
            return {"success": False, "error": "MAP 需要概念和元素参数"}

        # 确定目标（五行 or 八卦）
        target = self._resolve_target(element)

        overrides = self.rules["overrides"]
        if target == "wuxing":
            section = overrides["wuxing"].get(element, {})
            if "keywords" not in section:
                section["keywords"] = []
            if concept not in section["keywords"]:
                section["keywords"].append(concept)
            if "fixed_mapping" not in section:
                section["fixed_mapping"] = {}
            section["fixed_mapping"][concept] = element
            section["weight"] = weight
            overrides["wuxing"][element] = section
        elif target == "bagua":
            section = overrides["bagua"].get(element, {})
            if "keywords" not in section:
                section["keywords"] = []
            if concept not in section["keywords"]:
                section["keywords"].append(concept)
            section["weight"] = weight
            overrides["bagua"][element] = section

        return {
            "success": True,
            "message": f"已将「{concept}」映射到 {element}（权重={weight}）",
            "command": "MAP",
            "concept": concept,
            "element": element
        }

    def _cmd_learn(self, intent: Dict) -> Dict:
        """LEARN: 学习新概念关联（同 MAP，但语义上表示"新增概念"）"""
        # LEARN 与 MAP 执行逻辑相同，但语义不同
        intent["command"] = "MAP"  # 复用 MAP 逻辑
        result = self._cmd_map(intent)
        if result.get("success"):
            result["command"] = "LEARN"
            result["message"] = result["message"].replace("映射", "学习")
        return result

    def _cmd_correct(self, intent: Dict) -> Dict:
        """CORRECT: 修正已有映射的权重或归属"""
        concept = intent.get("concept")
        element = intent.get("element")
        weight = intent.get("weight")

        if not concept:
            return {"success": False, "error": "CORRECT 需要概念参数"}

        overrides = self.rules["overrides"]
        modified = False
        messages = []

        # 在全文中搜索并修正
        if weight is not None:
            for elem in WUXING_ELEMENTS:
                section = overrides["wuxing"].get(elem, {})
                if concept in section.get("keywords", []):
                    section["weight"] = weight
                    overrides["wuxing"][elem] = section
                    modified = True
                    messages.append(f"权重已更新为 {weight}")
                    break

        if element:
            # 从旧位置移除，添加到新位置
            for elem_key in ["wuxing", "bagua"]:
                for elem, section in overrides.get(elem_key, {}).items():
                    if concept in section.get("keywords", []):
                        section["keywords"].remove(concept)
                        if concept in section.get("fixed_mapping", {}):
                            del section["fixed_mapping"][concept]
                        modified = True

            # 添加到新位置
            target = self._resolve_target(element)
            if target == "wuxing":
                section = overrides["wuxing"].get(element, {})
                if "keywords" not in section:
                    section["keywords"] = []
                section["keywords"].append(concept)
                if "fixed_mapping" not in section:
                    section["fixed_mapping"] = {}
                section["fixed_mapping"][concept] = element
                overrides["wuxing"][element] = section
            messages.append(f"归属已修正为 {element}")

        if not modified:
            return {"success": False, "error": f"未找到概念「{concept}」"}

        return {
            "success": True,
            "message": f"已修正「{concept}」：{'; '.join(messages)}",
            "command": "CORRECT",
            "concept": concept
        }

    def _cmd_layer(self, intent: Dict) -> Dict:
        """LAYER: 调整三层架构归属"""
        concept = intent.get("concept")
        layer = intent.get("layer")

        if not concept or not layer:
            return {"success": False, "error": "LAYER 需要概念和层级参数"}

        if layer not in LAYER_KEYS:
            return {"success": False, "error": f"无效层级: {layer}，可选: {LAYER_KEYS}"}

        layer_assignment = self.rules["overrides"].get("layer_assignment", {})
        modified = False

        # 从旧层级移除
        for key in LAYER_KEYS:
            indicators = layer_assignment.get(key, {}).get("indicators", [])
            if concept in indicators:
                indicators.remove(concept)
                modified = True

        # 添加到新层级
        if layer not in layer_assignment:
            layer_assignment[layer] = {"label": "", "indicators": [], "weight": 1.0}
        if "indicators" not in layer_assignment[layer]:
            layer_assignment[layer]["indicators"] = []
        layer_assignment[layer]["indicators"].append(concept)

        self.rules["overrides"]["layer_assignment"] = layer_assignment

        return {
            "success": True,
            "message": f"已将「{concept}」移至 {layer} 层",
            "command": "LAYER",
            "concept": concept,
            "layer": layer
        }

    def _cmd_flow(self, intent: Dict) -> Dict:
        """FLOW: 管理五行流转阶段"""
        concept = intent.get("concept")
        stage = intent.get("stage")
        action = intent.get("action", "add")

        if not concept or not stage:
            return {"success": False, "error": "FLOW 需要概念和阶段参数"}

        circulation = self.rules["overrides"].get("wuxing_circulation", {})
        stages = circulation.get("stages", {})

        if stage not in stages:
            return {"success": False, "error": f"无效阶段: {stage}，可选: {list(stages.keys())}"}

        concepts = stages[stage].get("concepts", [])

        if action == "add":
            if concept not in concepts:
                concepts.append(concept)
                msg = f"已将「{concept}」添加到 {stage} 阶段"
            else:
                msg = f"「{concept}」已在 {stage} 阶段中"
        elif action == "remove":
            if concept in concepts:
                concepts.remove(concept)
                msg = f"已将「{concept}」从 {stage} 阶段移除"
            else:
                msg = f"「{concept}」不在 {stage} 阶段中"
        else:
            return {"success": False, "error": f"无效操作: {action}，可选: add/remove"}

        stages[stage]["concepts"] = concepts
        circulation["stages"] = stages
        self.rules["overrides"]["wuxing_circulation"] = circulation

        return {
            "success": True,
            "message": msg,
            "command": "FLOW",
            "concept": concept,
            "stage": stage,
            "action": action
        }

    def _resolve_target(self, element: str) -> str:
        """判断元素属于五行还是八卦"""
        if element in WUXING_ELEMENTS:
            return "wuxing"
        if element in BAGUA_SYMBOLS:
            return "bagua"
        # 默认尝试五行
        return "wuxing"

    # ===== 撤销 =====
    def undo(self) -> Dict:
        """撤销最近一次操作"""
        if not self.command_log:
            return {"success": False, "error": "没有可撤销的操作"}

        last = self.command_log.pop()
        self.rules = last["snapshot"]
        self._save_rules()

        return {
            "success": True,
            "message": f"已撤销 {last['command']} 操作",
            "command": last["command"]
        }

    # ===== 查询 =====
    def query_concept(self, concept: str) -> Dict:
        """查询概念在规则库中的完整信息"""
        overrides = self.rules["overrides"]
        result = {"concept": concept, "found": False}

        # 五行查询
        for elem in WUXING_ELEMENTS:
            section = overrides["wuxing"].get(elem, {})
            if concept in section.get("keywords", []) or concept in section.get("fixed_mapping", {}):
                result["found"] = True
                result["wuxing"] = elem
                result["weight"] = section.get("weight", 1.0)
                result["section"] = "wuxing"
                break

        # 八卦查询
        for sym in BAGUA_SYMBOLS:
            section = overrides["bagua"].get(sym, {})
            if concept in section.get("keywords", []):
                result["found"] = True
                result["bagua"] = sym
                result["weight"] = section.get("weight", 1.0)
                result["section"] = "bagua"
                break

        # 层级查询
        layer_assignment = overrides.get("layer_assignment", {})
        for key in LAYER_KEYS:
            if concept in layer_assignment.get(key, {}).get("indicators", []):
                result["layer"] = key
                result["layer_label"] = layer_assignment[key].get("label", "")
                break

        # 认知深度查询
        cognitive_depth = overrides.get("cognitive_depth", {})
        concept_max_depth = cognitive_depth.get("concept_max_depth", {})
        if concept in concept_max_depth:
            result["max_depth"] = concept_max_depth[concept]

        # 流转阶段查询
        circulation = overrides.get("wuxing_circulation", {})
        for stage_name, stage_data in circulation.get("stages", {}).items():
            if concept in stage_data.get("concepts", []):
                result["flow_stage"] = stage_name
                break

        return result

    def get_concept_count(self) -> Dict:
        """统计概念数量（用于认知深度渐进判断）"""
        overrides = self.rules["overrides"]
        counts = {"wuxing": {}, "bagua": {}, "total": 0}

        for elem in WUXING_ELEMENTS:
            section = overrides["wuxing"].get(elem, {})
            cnt = len(section.get("keywords", []))
            counts["wuxing"][elem] = cnt
            counts["total"] += cnt

        for sym in BAGUA_SYMBOLS:
            section = overrides["bagua"].get(sym, {})
            cnt = len(section.get("keywords", []))
            counts["bagua"][sym] = cnt
            counts["total"] += cnt

        return counts

    def get_command_log(self) -> List[Dict]:
        """获取操作历史"""
        return [{"command": entry["command"], "concept": entry["intent"].get("concept")}
                for entry in self.command_log]


# ===== 认知深度渐进逻辑 =====
class CognitiveDepthManager:
    """
    认知深度管理器
    规则：用户操作 ≥ 3 个概念时，提示升级到 L3
    参考 huihui-chat.js 的 SkillUP 触发规则模式
    """

    def __init__(self, parser: DSLParser):
        self.parser = parser
        self.level = "L2"  # 默认 L2（Guest）
        self.modified_concepts: set = set()

    def record_interaction(self, concept: str) -> Optional[Dict]:
        """记录用户交互，返回触发提示（如有）"""
        self.modified_concepts.add(concept)
        count = len(self.modified_concepts)

        if count >= 3 and self.level == "L2":
            return {
                "trigger": "cognitive_depth_upgrade",
                "message": (
                    f"🌊 你已调整了 {count} 个概念，展现出对规则系统的深入理解。\n\n"
                    "是否切换到 **L3·应用** 层级？在 L3 下，你可以：\n"
                    "- 设置临床操作手法与穴位关联\n"
                    "- 定义补泻、迎随等实践型映射\n"
                    "- 管理五行流转引擎的阶段归属\n\n"
                    "点击上方 L3 按钮即可切换，或继续在 L2 精读。"
                ),
                "suggested_level": "L3"
            }

        return None

    def set_level(self, level: str) -> None:
        """手动设置认知深度"""
        if level in COGNITIVE_LEVELS:
            self.level = level

    def get_level(self) -> str:
        return self.level


# ===== CLI 入口（用于测试）=====
if __name__ == "__main__":
    import sys

    parser = DSLParser("chinese_medicine")
    depth_manager = CognitiveDepthManager(parser)

    print("=" * 60)
    print("  五行八卦 DSL 解析器 — 交互式测试")
    print("  支持命令: MAP / LEARN / CORRECT / LAYER / FLOW")
    print("  输入 'quit' 退出, 'undo' 撤销, 'query <概念>' 查询")
    print("=" * 60)

    while True:
        try:
            user_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue
        if user_input.lower() == "quit":
            break
        if user_input.lower() == "undo":
            result = parser.undo()
            print(f"  {'✓' if result['success'] else '✗'} {result.get('message', result.get('error'))}")
            continue
        if user_input.lower().startswith("query "):
            concept = user_input[6:].strip()
            result = parser.query_concept(concept)
            if result["found"]:
                print(f"  📍 {concept}")
                for k, v in result.items():
                    if k not in ("concept", "found"):
                        print(f"     {k}: {v}")
            else:
                print(f"  ✗ 未找到概念「{concept}」")
            continue

        # 检测意图
        intent = parser.detect_intent(user_input)
        if not intent:
            print(f"  ✗ 无法识别意图。请尝试：MAP <概念> → <元素>")
            continue

        print(f"  🔍 检测到: {intent.get('command')} {intent.get('concept')} → {intent.get('element', 'N/A')}")

        # 执行
        result = parser.execute(intent)
        if result["success"]:
            print(f"  ✓ {result['message']}")

            # 认知深度检查
            trigger = depth_manager.record_interaction(intent.get("concept", ""))
            if trigger:
                print(f"\n  {trigger['message']}")
        else:
            print(f"  ✗ {result.get('error', '未知错误')}")

    # 输出统计
    counts = parser.get_concept_count()
    print(f"\n  当前规则库概念总数: {counts['total']}")
    print(f"  操作历史: {len(parser.command_log)} 条")