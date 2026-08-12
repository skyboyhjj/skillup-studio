#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S2.6 补充 6 章核心概念标注 → 81 章 dominant 全覆盖"""
import json
from collections import Counter
from pathlib import Path

WUXING_ORDER = ["木", "火", "土", "金", "水"]

# 6 章核心概念补充（长 SPO 词 → 短概念）
EXTRA = {
    20: {"绝学": "水", "众人": "土", "体道者": "水", "食母": "水"},
    54: {"善建者": "土", "修德于身": "土", "德乃真": "土", "德乃普": "土"},
    58: {"其政闷闷": "土", "其民淳淳": "土", "福": "火", "祸": "火", "圣人直": "土"},
    61: {"下流": "水", "以静为下": "水", "牝": "水", "各得所欲": "土"},
    68: {"不争之德": "水", "用人之力": "金", "善为士者": "土", "天古之极": "水"},
    80: {"小国寡民": "土", "甘食美服安居乐俗": "土", "结绳而用": "木", "什伯之器": "金"},
}

# 词典 v1.2 合并
dict_path = Path("verify/concept_wuxing_dict_v1_2.json")
dict_v12 = json.loads(dict_path.read_text(encoding="utf-8"))
d = dict_v12["dict"]
for ch, items in EXTRA.items():
    d.update(items)

# 章节概念归属：EXTRA 直接给
print("=" * 68)
print("S2.6 补充标注 → 81 章 dominant 全覆盖")
print("=" * 68)

db = json.loads(Path("verify/daojing_database_v2.json").read_text(encoding="utf-8"))

# 重新计算 81 章 dominant（core_concepts + SPO ≤6字 + EXTRA）
from collections import defaultdict
chapter_concepts = defaultdict(set)
for num in range(1, 82):
    ch = db.get(str(num), {})
    for c in ch.get("core_concepts", []):
        chapter_concepts[num].add(c)
    for spo in ch.get("spo_triples", []):
        for key in ["subject", "object"]:
            v = spo.get(key, "")
            if v and len(v) <= 6 and v in d:
                chapter_concepts[num].add(v)
    # EXTRA 补充
    chapter_concepts[num].update(EXTRA.get(num, {}).keys())

for num in range(1, 82):
    cs = [c for c in chapter_concepts.get(num, set()) if c in d]
    if not cs:
        print(f"  第{num:02d}章: 无概念（异常）")
        continue
    dist = Counter(d[c] for c in cs)
    top = sorted(dist.items(), key=lambda kv: (-kv[1], WUXING_ORDER.index(kv[0])))
    info = {"dominant": top[0][0], "dist": dict(dist), "concepts": len(cs)}
    db[str(num)].setdefault("x_wuxing", {}).update(info)

n_dom = sum(1 for n in db if db[n].get("x_wuxing", {}).get("dominant"))
print(f"[dominant] {n_dom}/81 章")

# 保存
Path("verify/daojing_database_v2.json").write_text(
    json.dumps(db, ensure_ascii=False, indent=1), encoding="utf-8")
dict_v12["dict"] = d
dict_v12["schema_version"] = "1.3"
dict_v12["note"] = "全量词典 v1.3（81 章 dominant 全覆盖）"
dict_path.write_text(json.dumps(dict_v12, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"[输出] 词典 v1.3（{len(d)} 概念）+ daojingDatabaseV2 回注")
print("=" * 68)
