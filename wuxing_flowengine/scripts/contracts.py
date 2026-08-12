#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
contracts.py —— 晶体库共享契约常量（DS-B-2026-001 v1.1 · 审核意见 A1）
================================================================
消除 VALID_TYPES 等常量在多个脚本中的硬编码重复（G6：契约与代码同步）。
所有晶体脚本统一从此模块引用，禁止内联重复定义。

常量清单：
  WUXING_ORDER     五行顺序
  VALID_TYPES      合法晶体类型
  VALID_VERIFIED   verified.by 合法正则（process:/human: 双层）
  DIMENSION_WUXING 四维→五行映射（DEC-2026-009 V1.1）
  DIMENSION_KEYS   四维中文→英文键
  DIMENSION_CN     四维中文→单字
  STATUS_LIFECYCLE 晶体生命周期状态
"""

import re

# 五行（生克环：木→火→土→金→水→木）
WUXING_ORDER = ["木", "火", "土", "金", "水"]

# 晶体类型（DS-B-2026-001 v1.1：新增 WisdomInsight）
VALID_TYPES = [
    "KnowledgeDomain",
    "DiagnosisResult",
    "ClassicalInsight",
    "TizhengCard",
    "WisdomInsight",
]

# verified.by 合法前缀：process:（机器确认）/ human:（人工亲证，含匿名）
VALID_VERIFIED = re.compile(r"^(process:[a-z-]+|human:[a-z0-9_-]+)$")

# 四维→五行映射（DEC-2026-009 V1.1：识水/缘木/宇土/时火；玄鉴决策中心=金）
DIMENSION_WUXING = {"时位轴": "火", "宇位轴": "土", "识位轴": "水", "缘位轴": "木"}
DIMENSION_KEYS = {"时位轴": "shi", "宇位轴": "yu", "识位轴": "identify", "缘位轴": "yuan"}
DIMENSION_CN = {"时位轴": "时", "宇位轴": "宇", "识位轴": "识", "缘位轴": "缘"}

# 晶体生命周期（IF-2026-006 扩展：published 为池副本状态）
STATUS_LIFECYCLE = ["draft", "completed", "published", "current", "deprecated", "retired"]

# 五行相生（补益环）：木→火→土→金→水→木
SHENG_CYCLE = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
# 五行相克：木克土 土克水 水克火 火克金 金克木
KE_MAP = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
