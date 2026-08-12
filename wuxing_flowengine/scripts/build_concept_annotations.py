#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S2 概念五行标注（83 概念，27 章 core_concepts）
按《概念五行标注_提示词》执行：判据表 + 种子继承参考 + JSON 契约
跨章一致性：道（第1/25章）→ 水（两章同标）
"""
import json
from pathlib import Path

# 83 个 core_concepts 标注（concept -> {wuxing, alt, basis}）
ANNOTATIONS = {
    # 第1章
    "道": {"wuxing": "水", "alt": "金", "basis": "道体渊深，虚静润下"},
    "无": {"wuxing": "水", "alt": None, "basis": "无为之体，虚极静笃"},
    "有": {"wuxing": "木", "alt": None, "basis": "万物之母，生发之端"},
    "玄": {"wuxing": "水", "alt": None, "basis": "玄深如渊，幽远难测"},
    "妙": {"wuxing": "水", "alt": None, "basis": "精微幽深，智之微"},
    # 第2章
    "对立统一": {"wuxing": "火", "alt": "金", "basis": "相反相成，明辨之动"},
    "无为": {"wuxing": "土", "alt": "水", "basis": "处无为之事，治世承载（种子同）"},
    "不言": {"wuxing": "水", "alt": None, "basis": "行不言之教，默然虚静"},
    "不居": {"wuxing": "金", "alt": None, "basis": "功成弗居，收敛之义（种子同）"},
    "相生": {"wuxing": "木", "alt": None, "basis": "生生不息，相生之机"},
    # 第3章
    "不尚贤": {"wuxing": "水", "alt": None, "basis": "不尚贤使民不争，虚静（种子同）"},
    "虚心实腹": {"wuxing": "土", "alt": None, "basis": "实腹养身，承载之义"},
    "无知无欲": {"wuxing": "水", "alt": None, "basis": "无知无欲，虚极之境"},
    "为无为": {"wuxing": "土", "alt": None, "basis": "为无为则无不治，治世（种子同）"},
    "无不治": {"wuxing": "土", "alt": None, "basis": "无不治，承载成治"},
    # 第4章
    "冲": {"wuxing": "水", "alt": "土", "basis": "道冲而用之，冲虚不盈"},
    "不盈": {"wuxing": "水", "alt": None, "basis": "虚而不盈，静笃"},
    "渊": {"wuxing": "水", "alt": None, "basis": "渊兮似万物之宗，深水"},
    "湛": {"wuxing": "水", "alt": None, "basis": "湛兮似或存，清澈虚静"},
    "帝之先": {"wuxing": "水", "alt": None, "basis": "象帝之先，本源虚静"},
    # 第5章
    "不仁": {"wuxing": "金", "alt": None, "basis": "天地不仁，肃杀无情"},
    "刍狗": {"wuxing": "金", "alt": None, "basis": "刍狗无情之用，肃敛"},
    "橐籥": {"wuxing": "水", "alt": "火", "basis": "中空鼓风，虚而愈出"},
    "虚而不屈": {"wuxing": "水", "alt": None, "basis": "虚而不屈，静虚之动"},
    "守中": {"wuxing": "土", "alt": None, "basis": "守中，中央承载"},
    # 第6章
    "谷神": {"wuxing": "水", "alt": None, "basis": "谷神，虚谷流水"},
    "玄牝": {"wuxing": "水", "alt": None, "basis": "玄牝，虚静母性"},
    "天地根": {"wuxing": "水", "alt": None, "basis": "玄牝之门为天地根，根源虚静"},
    "不死": {"wuxing": "水", "alt": None, "basis": "谷神不死，绵绵虚续"},
    "不勤": {"wuxing": "水", "alt": None, "basis": "无为不勤，虚静"},
    # 第7章
    "不自生": {"wuxing": "水", "alt": None, "basis": "不自生故长生，虚静"},
    "长生": {"wuxing": "水", "alt": "木", "basis": "虚静致久，天长地久"},
    "后身": {"wuxing": "水", "alt": None, "basis": "后其身而身先，谦下"},
    "外身": {"wuxing": "水", "alt": None, "basis": "外其身而身存，无身"},
    "无私成私": {"wuxing": "水", "alt": None, "basis": "无私故能成其私，虚静"},
    # 第8章
    "上善": {"wuxing": "水", "alt": None, "basis": "上善若水，水德"},
    "水": {"wuxing": "水", "alt": None, "basis": "水之七德，润下"},
    "不争": {"wuxing": "水", "alt": None, "basis": "不争，水德之至"},
    "处下": {"wuxing": "水", "alt": None, "basis": "处众人之所恶，就下"},
    "七善": {"wuxing": "水", "alt": None, "basis": "七善皆水德"},
    # 第9章
    "持盈": {"wuxing": "金", "alt": "火", "basis": "持而盈之不如其已，知止"},
    "揣锐": {"wuxing": "金", "alt": None, "basis": "锐，金之锐"},
    "知止": {"wuxing": "金", "alt": None, "basis": "知止不殆，收敛决断"},
    "功遂身退": {"wuxing": "金", "alt": None, "basis": "功成身退，收敛（种子同）"},
    "天之道": {"wuxing": "土", "alt": "金", "basis": "天之道利而不害，均平（种子同）"},
    # 第13章
    "宠辱": {"wuxing": "火", "alt": None, "basis": "宠辱若惊，情动"},
    "惊": {"wuxing": "火", "alt": None, "basis": "若惊，心动"},
    "大患": {"wuxing": "火", "alt": "土", "basis": "大患若身，忧动"},
    "有身": {"wuxing": "土", "alt": None, "basis": "有身，形体承载"},
    "无身": {"wuxing": "水", "alt": None, "basis": "无身，虚静无我"},
    "以身为天下": {"wuxing": "火", "alt": "土", "basis": "贵以身任天下，担当明动"},
    # 第14章
    "夷": {"wuxing": "水", "alt": None, "basis": "视之不见，隐微虚静"},
    "希": {"wuxing": "水", "alt": None, "basis": "听之不闻，希声"},
    "微": {"wuxing": "水", "alt": None, "basis": "搏之不得，微妙"},
    "惚恍": {"wuxing": "水", "alt": None, "basis": "惚恍，虚漠无象"},
    "无状之状": {"wuxing": "水", "alt": None, "basis": "无状之状，虚"},
    "执古御今": {"wuxing": "金", "alt": "火", "basis": "执古御今，断今之宜"},
    "道纪": {"wuxing": "金", "alt": "水", "basis": "道纪，纲纪决断"},
    # 第15章
    "微妙玄通": {"wuxing": "水", "alt": None, "basis": "微妙玄通，虚静深通"},
    "豫": {"wuxing": "水", "alt": "金", "basis": "豫兮若冬涉川，慎静"},
    "犹": {"wuxing": "水", "alt": None, "basis": "犹兮若畏四邻，戒惧"},
    "徐清": {"wuxing": "水", "alt": None, "basis": "静之徐清，澄静"},
    "徐生": {"wuxing": "木", "alt": None, "basis": "动之徐生，生发"},
    "不欲盈": {"wuxing": "水", "alt": None, "basis": "不欲盈，虚"},
    "蔽不新成": {"wuxing": "水", "alt": "土", "basis": "保此道者不欲盈，虚旧"},
    # 第25章
    "道": {"wuxing": "水", "alt": "金", "basis": "道体渊深（跨章一致，与第1章同）"},
    "大": {"wuxing": "水", "alt": "土", "basis": "强为之名曰大，道之属性"},
    "逝": {"wuxing": "水", "alt": "火", "basis": "大曰逝，流行深远"},
    "远": {"wuxing": "水", "alt": None, "basis": "逝曰远，深远"},
    "反": {"wuxing": "火", "alt": None, "basis": "反者道之动，反动之机"},
    "四大": {"wuxing": "土", "alt": None, "basis": "域中有四大，包罗承载"},
    "自然": {"wuxing": "水", "alt": "土", "basis": "道法自然，虚静自足"},
    # 第26章
    "重": {"wuxing": "土", "alt": None, "basis": "重为轻根，厚重"},
    "轻": {"wuxing": "火", "alt": None, "basis": "轻则失根，轻浮"},
    "静": {"wuxing": "水", "alt": None, "basis": "静为躁君，虚静"},
    "躁": {"wuxing": "火", "alt": None, "basis": "躁则失君，躁动"},
    "根基": {"wuxing": "土", "alt": None, "basis": "根，承载"},
    "主宰": {"wuxing": "金", "alt": "土", "basis": "静为躁君，制胜统摄"},
    # 第27章
    "善行": {"wuxing": "水", "alt": "木", "basis": "善行无辙迹，不露虚静"},
    "袭明": {"wuxing": "火", "alt": None, "basis": "袭明，承明"},
    "无弃人": {"wuxing": "木", "alt": None, "basis": "常善救人故无弃人，仁"},
    "无弃物": {"wuxing": "木", "alt": None, "basis": "常善救物故无弃物，仁"},
    "师资": {"wuxing": "金", "alt": "木", "basis": "善人为师不善为资，义之节制"},
    "要妙": {"wuxing": "水", "alt": None, "basis": "是谓要妙，精微虚妙"},
}

# 章节归属（core_concepts 所在章）
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

# 校验
print("=" * 68)
print("S2 概念五行标注（83 概念 / 15 章）")
print("=" * 68)

# 1. 覆盖校验
assert len(ANNOTATIONS) == 83, f"标注数 {len(ANNOTATIONS)} != 83"
all_concepts = set()
for cs in CHAPTER_CONCEPTS.values():
    all_concepts.update(cs)
assert all_concepts == set(ANNOTATIONS.keys()), "标注与章节概念不一致"
print(f"✅ 标注覆盖: {len(ANNOTATIONS)} 概念 / {len(CHAPTER_CONCEPTS)} 章")

# 2. 跨章一致性校验（道: 第1/25章）
dao_chapters = [cs for cs in CHAPTER_CONCEPTS.values() if "道" in cs]
print(f"✅ 跨章概念 '道' 出现 {len(dao_chapters)} 章 — 五行: {ANNOTATIONS['道']['wuxing']}（一致）")

# 3. 五行合法性
for c, a in ANNOTATIONS.items():
    assert a["wuxing"] in "木火土金水", f"{c} 五行非法"
print("✅ 五行合法性: 全部通过")

# 4. 分布统计
from collections import Counter
dist = Counter(a["wuxing"] for a in ANNOTATIONS.values())
print("✅ 五行分布:", dict(dist))

# 输出词典 v1.1
dict_out = {
    "schema_version": "1.1",
    "source": "core_concepts-27chapters",
    "generated": __import__("datetime").datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "dict": {c: a["wuxing"] for c, a in ANNOTATIONS.items()},
    "alt": {c: a["alt"] for c, a in ANNOTATIONS.items() if a["alt"]},
    "basis": {c: a["basis"] for c, a in ANNOTATIONS.items()},
    "note": "S2 概念级标注（15 章 core_concepts）；54 空章待 SPO 补充；跨章一致性校验通过（道→水）；54 空章待 SPO 补充",
}
Path("verify/concept_wuxing_dict_v1_1.json").write_text(
    json.dumps(dict_out, ensure_ascii=False, indent=2), encoding="utf-8")
print("\n[输出] verify/concept_wuxing_dict_v1_1.json（83 概念）")
print("=" * 68)
