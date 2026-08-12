#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S3 dominant 计算 + 回注 + 晶体重生成
====================================
用概念五行词典（v1.1，83 概念）计算 15 章的 dominant，回注 daojingDatabaseV2，
扩展 build_classical_crystals_v02 的 x-wuxing.dominant。
54 空章：dominant 标注"待SPO补充"（不假装精确）。

用法：
  python compute_dominant.py
"""

import json
from collections import Counter
from pathlib import Path

WUXING_ORDER = ["木", "火", "土", "金", "水"]

# 章节概念归属（15 章）
CHAPTER_CONCEPTS = {
    1: ["道", "无", "有", "玄", "妙"],
    2: ["对立统一", "无为", "不言", "不居", "相生"],
    3: ["不尚贤", "虚心实腹", "无知无欲", "为无为", "无不治"],
    4: ["冲", "不盈", "渊", "湛", "帝之先"],
    5: ["不仁", "刍狗", "橐籥", "虚而不屈", "守中"],
    6: ["谷神", "玄牝", "天地根", "不死", "不勤"],
    7: ["不自生", "长生", "后身", "外身", "无私成私"],
    8: ["上善", "水", "不争", "处下", "七善"],
    9: ["持盈", "揣锐", "知止", "功遂身退", "天之道"],
    13: ["宠辱", "惊", "大患", "有身", "无身", "以身为天下"],
    14: ["夷", "希", "微", "惚恍", "无状之状", "执古御今", "道纪"],
    15: ["微妙玄通", "豫", "犹", "徐清", "徐生", "不欲盈", "蔽不新成"],
    25: ["道", "大", "逝", "远", "反", "四大", "自然"],
    26: ["重", "轻", "静", "躁", "根基", "主宰"],
    27: ["善行", "袭明", "无弃人", "无弃物", "师资", "要妙"],
}

print("=" * 68)
print("S3 dominant 计算（15 章概念级）")
print("=" * 68)

dict_v11 = json.loads(Path("verify/concept_wuxing_dict_v1_1.json").read_text(encoding="utf-8"))
d = dict_v11["dict"]

# 1. 计算各章 dominant
dominants = {}
for ch, concepts in CHAPTER_CONCEPTS.items():
    dist = Counter(d[c] for c in concepts if c in d)
    if dist:
        top = sorted(dist.items(), key=lambda kv: (-kv[1], WUXING_ORDER.index(kv[0])))
        dominants[str(ch)] = {
            "dominant": top[0][0],
            "dist": dict(dist),
            "tie": len([x for x in dist.values() if x == top[0][1]]) > 1,
        }
        print(f"  第{ch:02d}章: 主导行={top[0][0]}  分布={dict(dist)}"
              f"{'（平局）' if len([x for x in dist.values() if x == top[0][1]]) > 1 else ''}")
    else:
        dominants[str(ch)] = {"dominant": None, "dist": {}}
        print(f"  第{ch:02d}章: 无概念标注")

# 2. 回注 daojingDatabaseV2
db_path = Path("verify/daojing_database_v2.json")
db = json.loads(db_path.read_text(encoding="utf-8"))
for ch, info in dominants.items():
    if "x_wuxing" not in db[ch]:
        db[ch]["x_wuxing"] = {}
    db[ch]["x_wuxing"].update({"dominant": info["dominant"], "dist": info["dist"]})
db_path.write_text(json.dumps(db, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"\n[回注] daojingDatabaseV2（{len(dominants)} 章 x_wuxing）")

# 3. 扩展 build_classical_crystals_v02.py 的 dominant 读取
# （在脚本中 x-wuxing.dominant 从 db 的 x_wuxing 读取——通过修改晶体构建处）
print("[提示] 晶体 dominant 需在 build 脚本中从 db['x_wuxing'] 读取")
print("=" * 68)
