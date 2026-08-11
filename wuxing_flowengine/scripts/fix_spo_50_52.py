#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""50-52 章 SPO 补全：按 SPO 提示词规范提取（原子化/谓词规范/context 必填）"""
import json
from pathlib import Path

# 第50章 出生入死
SPO_50 = [
    {"subject": "出生入死", "subject_type": "状态", "predicate": "是",
     "relation_type": "判断", "object": "生命的基本现象", "object_type": "概念",
     "context": "出生入死。"},
    {"subject": "人", "subject_type": "人", "predicate": "分属",
     "relation_type": "判断", "object": "生之徒、死之徒、动之于死地三类",
     "object_type": "概念", "context": "生之徒十有三，死之徒十有三，人之生动之于死地亦十有三。"},
    {"subject": "生生之厚", "subject_type": "概念", "predicate": "导致",
     "relation_type": "因果", "object": "动之于死地", "object_type": "状态",
     "context": "夫何故？以其生生之厚。"},
    {"subject": "善摄生者", "subject_type": "人", "predicate": "无",
     "relation_type": "否定", "object": "死地", "object_type": "概念",
     "context": "夫何故？以其无死地。"},
    {"subject": "无死地", "subject_type": "概念", "predicate": "使",
     "relation_type": "因果", "object": "兕虎甲兵无所伤", "object_type": "状态",
     "context": "兕无所投其角，虎无所措其爪，兵无所容其刃。"},
    {"subject": "无死地", "subject_type": "概念", "predicate": "源于",
     "relation_type": "因果", "object": "不执著于形躯自我", "object_type": "行为",
     "context": "盖闻善摄生者，陆行不遇兕虎，入军不被甲兵。"},
    {"subject": "过度养生", "subject_type": "行为", "predicate": "违反",
     "relation_type": "否定", "object": "道法自然", "object_type": "概念",
     "context": "以其生生之厚。"},
]

# 第51章 道生之德畜之
SPO_51 = [
    {"subject": "道", "subject_type": "概念", "predicate": "生",
     "relation_type": "因果", "object": "万物", "object_type": "自然物",
     "context": "道生之。"},
    {"subject": "德", "subject_type": "概念", "predicate": "畜",
     "relation_type": "因果", "object": "万物", "object_type": "自然物",
     "context": "德畜之。"},
    {"subject": "物", "subject_type": "概念", "predicate": "形",
     "relation_type": "因果", "object": "万物", "object_type": "自然物",
     "context": "物形之。"},
    {"subject": "势", "subject_type": "概念", "predicate": "成",
     "relation_type": "因果", "object": "万物", "object_type": "自然物",
     "context": "势成之。"},
    {"subject": "万物", "subject_type": "自然物", "predicate": "尊",
     "relation_type": "判断", "object": "道", "object_type": "概念",
     "context": "是以万物莫不尊道而贵德。"},
    {"subject": "道之尊德之贵", "subject_type": "概念", "predicate": "是谓",
     "relation_type": "判断", "object": "常自然", "object_type": "状态",
     "context": "道之尊，德之贵，夫莫之命而常自然。"},
    {"subject": "玄德", "subject_type": "概念", "predicate": "是谓",
     "relation_type": "判断", "object": "生而不有，为而不恃，长而不宰",
     "object_type": "行为", "context": "生而不有，为而不恃，长而不宰，是谓玄德。"},
    {"subject": "道", "subject_type": "概念", "predicate": "不有",
     "relation_type": "否定", "object": "生之成果", "object_type": "概念",
     "context": "生而不有。"},
]

# 第52章 天下有始
SPO_52 = [
    {"subject": "天下", "subject_type": "概念", "predicate": "有",
     "relation_type": "判断", "object": "始", "object_type": "概念",
     "context": "天下有始。"},
    {"subject": "始", "subject_type": "概念", "predicate": "是谓",
     "relation_type": "判断", "object": "天下母", "object_type": "概念",
     "context": "以为天下母。"},
    {"subject": "得母者", "subject_type": "人", "predicate": "知",
     "relation_type": "因果", "object": "子", "object_type": "概念",
     "context": "既得其母，以知其子。"},
    {"subject": "知子者", "subject_type": "人", "predicate": "守",
     "relation_type": "因果", "object": "母", "object_type": "概念",
     "context": "既知其子，复守其母。"},
    {"subject": "守母者", "subject_type": "人", "predicate": "无",
     "relation_type": "否定", "object": "身殆", "object_type": "状态",
     "context": "没身不殆。"},
    {"subject": "塞兑闭门", "subject_type": "行为", "predicate": "则",
     "relation_type": "因果", "object": "终身不勤", "object_type": "状态",
     "context": "塞其兑，闭其门，终身不勤。"},
    {"subject": "开兑济事", "subject_type": "行为", "predicate": "则",
     "relation_type": "因果", "object": "终身不救", "object_type": "状态",
     "context": "开其兑，济其事，终身不救。"},
    {"subject": "见小", "subject_type": "行为", "predicate": "曰",
     "relation_type": "判断", "object": "明", "object_type": "概念",
     "context": "见小曰明。"},
    {"subject": "守柔", "subject_type": "行为", "predicate": "曰",
     "relation_type": "判断", "object": "强", "object_type": "概念",
     "context": "守柔曰强。"},
    {"subject": "用光归明", "subject_type": "行为", "predicate": "是谓",
     "relation_type": "判断", "object": "袭常", "object_type": "概念",
     "context": "用其光，复归其明，无遗身殃，是为袭常。"},
]

SPO_MAP = {"50": SPO_50, "51": SPO_51, "52": SPO_52}

# 校验（SPO 提示词契约）
def validate(spo_list):
    errors = []
    for i, s in enumerate(spo_list):
        for k in ["subject", "predicate", "object", "context"]:
            if not s.get(k):
                errors.append(f"[{i}] 缺 {k}")
        if not s.get("relation_type"):
            errors.append(f"[{i}] 缺 relation_type")
        if len(s.get("predicate", "")) > 3:
            errors.append(f"[{i}] 谓词超过 3 字: {s['predicate']}")
    return errors

ok = True
for ch, spo in SPO_MAP.items():
    errs = validate(spo)
    if errs:
        ok = False
        print(f"第{ch}章 校验失败: {errs}")
    else:
        print(f"第{ch}章: {len(spo)} 条 SPO ✅")

if ok:
    # 注入 daojingDatabaseV2
    db_path = Path("verify/daojing_database_v2.json")
    db = json.loads(db_path.read_text(encoding="utf-8"))
    for ch, spo in SPO_MAP.items():
        db[ch]["spo_triples"] = spo
        db[ch]["core_concepts"] = db[ch].get("core_concepts") or []
    db_path.write_text(json.dumps(db, ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(len(v.get("spo_triples", [])) for v in db.values())
    print(f"\n已注入 daojing_database_v2.json | SPO 总数: {total}")
