"""DSL 执行器 — 封装 wuxing_dsl.py"""
import sys
import json
from pathlib import Path
from typing import Any

# 将 wuxing_rules 加入 sys.path
_WUXING_DIR = Path(__file__).resolve().parent.parent / "wuxing_rules"
if str(_WUXING_DIR) not in sys.path:
    sys.path.insert(0, str(_WUXING_DIR))

from wuxing_dsl import DSLParser


class DSLExecutor:
    """无状态 DSL 执行器，每次调用加载规则库并执行命令"""

    def __init__(self):
        self.parser = DSLParser()

    def execute(self, command: dict, rules_data: dict) -> dict:
        """
        执行 DSL 命令

        Args:
            command:  {"command": "MAP", "concept": "丹参", "element": "火", "weight": 0.9}
            rules_data: 当前规则库 JSON

        Returns:
            {"success": True, "message": "...", "rules": <更新后的规则库>,
             "changes": {"added": [...], "modified": [...], "removed": [...]}}
        """
        cmd = command.get("command", "").upper()
        concept = command.get("concept", "")
        element = command.get("element", "")
        weight = command.get("weight", 0.7)
        layer = command.get("layer", "")
        stage = command.get("stage", "")
        action = command.get("action", "add")  # FLOW: add/remove

        try:
            if cmd == "MAP":
                return self._handle_map(rules_data, concept, element, weight)
            elif cmd == "LEARN":
                return self._handle_learn(rules_data, concept, element, weight)
            elif cmd == "CORRECT":
                return self._handle_correct(rules_data, concept, element, weight, layer)
            elif cmd == "LAYER":
                return self._handle_layer(rules_data, concept, layer)
            elif cmd == "FLOW":
                return self._handle_flow(rules_data, concept, stage, action)
            else:
                return {"success": False, "message": f"未知命令: {cmd}", "rules": rules_data}
        except Exception as e:
            return {"success": False, "message": f"DSL 执行错误: {str(e)}", "rules": rules_data}

    def _handle_map(self, rules: dict, concept: str, element: str, weight: float) -> dict:
        """映射概念到五行/八卦"""
        concepts = rules.get("concepts", [])
        # 去重：从其他元素移除
        for c in concepts:
            if c.get("name") == concept and c.get("element") != element:
                c["element"] = element
                c["weight"] = weight
                return {
                    "success": True,
                    "message": f"已将「{concept}」从 {c.get('element', '?')} 移动到 {element}（权重={weight}）",
                    "rules": rules,
                    "changes": {"modified": [concept]}
                }
            elif c.get("name") == concept:
                c["weight"] = weight
                return {
                    "success": True,
                    "message": f"已更新「{concept}」在 {element} 的权重为 {weight}",
                    "rules": rules,
                    "changes": {"modified": [concept]}
                }
        # 新概念
        concepts.append({"name": concept, "element": element, "weight": weight})
        return {
            "success": True,
            "message": f"已将「{concept}」映射到 {element}（权重={weight}）",
            "rules": rules,
            "changes": {"added": [concept]}
        }

    def _handle_learn(self, rules: dict, concept: str, element: str, weight: float) -> dict:
        """学习新概念关联（同 MAP，但生成更详细的解释）"""
        return self._handle_map(rules, concept, element, weight)

    def _handle_correct(self, rules: dict, concept: str, element: str,
                        weight: float, layer: str) -> dict:
        """修正权重或归属"""
        concepts = rules.get("concepts", [])
        for c in concepts:
            if c.get("name") == concept:
                changes = {"modified": [concept]}
                msgs = []
                if element:
                    c["element"] = element
                    msgs.append(f"归属改为 {element}")
                if weight is not None:
                    c["weight"] = weight
                    msgs.append(f"权重改为 {weight}")
                if layer:
                    c["layer"] = layer
                    msgs.append(f"层级改为 {layer}")
                return {
                    "success": True,
                    "message": f"已修正「{concept}」：{', '.join(msgs)}",
                    "rules": rules,
                    "changes": changes
                }
        return {"success": False, "message": f"概念「{concept}」不存在", "rules": rules}

    def _handle_layer(self, rules: dict, concept: str, layer: str) -> dict:
        """调整三层架构"""
        valid_layers = ["outer", "middle", "inner"]
        if layer not in valid_layers:
            return {"success": False, "message": f"无效层级: {layer}，可选: {valid_layers}", "rules": rules}

        concepts = rules.get("concepts", [])
        for c in concepts:
            if c.get("name") == concept:
                c["layer"] = layer
                return {
                    "success": True,
                    "message": f"已将「{concept}」调整为 {layer} 层",
                    "rules": rules,
                    "changes": {"modified": [concept]}
                }
        return {"success": False, "message": f"概念「{concept}」不存在", "rules": rules}

    def _handle_flow(self, rules: dict, concept: str, stage: str, action: str) -> dict:
        """管理流转阶段"""
        concepts = rules.get("concepts", [])
        for c in concepts:
            if c.get("name") == concept:
                stages = c.get("stages", [])
                if action == "add":
                    if stage not in stages:
                        stages.append(stage)
                        c["stages"] = stages
                        return {
                            "success": True,
                            "message": f"已将「{concept}」添加到流转阶段 {stage}",
                            "rules": rules,
                            "changes": {"modified": [concept]}
                        }
                    return {"success": True, "message": f"「{concept}」已在阶段 {stage}", "rules": rules}
                elif action == "remove":
                    if stage in stages:
                        stages.remove(stage)
                        c["stages"] = stages
                        return {
                            "success": True,
                            "message": f"已将「{concept}」从流转阶段 {stage} 移除",
                            "rules": rules,
                            "changes": {"modified": [concept]}
                        }
                    return {"success": True, "message": f"「{concept}」不在阶段 {stage}", "rules": rules}
        return {"success": False, "message": f"概念「{concept}」不存在", "rules": rules}


# 单例
dsl_executor = DSLExecutor()