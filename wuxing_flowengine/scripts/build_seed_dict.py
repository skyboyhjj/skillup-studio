#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S1 种子词典提取 + 词典级校验
============================
从莫比乌斯 6 章（道德经_第01/02/03/79/80/81章.json）提取 concepts 的 wuxing 标注，
构建"概念→五行"初始词典，并执行词典级校验：
  - 同名概念跨章五行必须一致（冲突时仲裁）
  - 输出种子词典（可版本化、可迁移到其余 75 章）

用法：
  python build_seed_dict.py [--dir .] [--out verify/concept_wuxing_dict.json]
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

WUXING_ORDER = ["木", "火", "土", "金", "水"]
SEED_CHAPTERS = ["第01章", "第02章", "第03章", "第79章", "第80章", "第81章"]


def load_seed_concepts(dir_path: Path):
    """提取 6 章莫比乌斯 JSON 的概念→五行"""
    records = []  # {concept, wuxing, chapter, desc}
    for ch in SEED_CHAPTERS:
        f = dir_path / f"道德经_{ch}.json"
        if not f.exists():
            print(f"  ⚠️ 缺 {f.name}（跳过）")
            continue
        data = json.loads(f.read_text(encoding="utf-8"))
        for ring in data.get("rings", []):
            for c in ring.get("concepts", []):
                wx = c.get("wuxing")
                if not wx:
                    continue
                records.append({
                    "concept": c.get("label", "").strip(),
                    "wuxing": wx,
                    "chapter": data.get("chapter", ch),
                    "desc": c.get("desc", "")[:60],
                })
    return records


def build_dict(records):
    """概念聚合 → {concept: {wuxing: 频次, chapters: [...], descs: [...]}}"""
    agg = defaultdict(lambda: {"wuxing": defaultdict(int), "chapters": [], "descs": []})
    for r in records:
        agg[r["concept"]]["wuxing"][r["wuxing"]] += 1
        if r["chapter"] not in agg[r["concept"]]["chapters"]:
            agg[r["concept"]]["chapters"].append(r["chapter"])
        agg[r["concept"]]["descs"].append(r["desc"])
    return agg


def resolve_conflicts(agg):
    """词典级校验：同名概念多五行 → 仲裁

    仲裁规则：
      1. 频次最高的五行胜出（多数原则）
      2. 平局时按 WUXING_ORDER 序（文档顺序）
      3. 冲突记录保留（供人工复核）
    """
    resolved = {}
    conflicts = []
    for concept, info in sorted(agg.items()):
        wuxing_counts = info["wuxing"]
        if len(wuxing_counts) == 1:
            resolved[concept] = {"wuxing": next(iter(wuxing_counts)), "conflict": False}
        else:
            # 多数原则
            top = sorted(wuxing_counts.items(), key=lambda kv: (-kv[1], WUXING_ORDER.index(kv[0])))
            resolved[concept] = {"wuxing": top[0][0], "conflict": True}
            conflicts.append({
                "concept": concept,
                "counts": dict(wuxing_counts),
                "chosen": top[0][0],
                "chapters": info["chapters"],
            })
    return resolved, conflicts


def main():
    parser = argparse.ArgumentParser(description="S1 种子词典提取 + 词典级校验")
    parser.add_argument("--dir", default=".", help="莫比乌斯 JSON 目录")
    parser.add_argument("--out", default="verify/concept_wuxing_dict.json", help="词典输出")
    args = parser.parse_args()

    print("=" * 68)
    print("S1 种子词典提取（莫比乌斯 6 章 → 概念五行词典）")
    print("=" * 68)

    records = load_seed_concepts(Path(args.dir))
    print(f"[提取] {len(records)} 条概念标注（6 章）")

    agg = build_dict(records)
    print(f"[聚合] {len(agg)} 个独立概念")

    # 词典级校验：同名概念跨章一致性
    print("\n[词典级校验] 同名概念跨章五行一致性")
    multi_chapter = {c: i for c, i in agg.items() if len(i["chapters"]) > 1}
    print(f"  跨章概念: {len(multi_chapter)} 个")
    inconsistent = 0
    for concept, info in sorted(multi_chapter.items()):
        wxs = list(info["wuxing"].keys())
        mark = "❌ 冲突" if len(wxs) > 1 else "✅ 一致"
        if len(wxs) > 1:
            inconsistent += 1
        print(f"    {mark} {concept}: {dict(info['wuxing'])}（{info['chapters']}）")

    # 冲突仲裁
    resolved, conflicts = resolve_conflicts(agg)
    print(f"\n[仲裁] 冲突概念 {len(conflicts)} 个（多数原则）")
    for c in conflicts:
        print(f"  ⚖️ {c['concept']}: {c['counts']} → 选定 {c['chosen']}")

    # 输出词典
    dict_out = {
        "schema_version": "1.0",
        "source": "mobius-6-chapters",
        "generated": __import__("datetime").datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dict": {c: v["wuxing"] for c, v in resolved.items()},
        "conflicts_resolved": conflicts,
        "inconsistent_cross_chapter": inconsistent,
        "note": "种子词典——迁移到 75 章时同名概念必须同五行（词典级校验规则）",
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(dict_out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[输出] {out_path}（{len(resolved)} 概念）")
    print("=" * 68)


if __name__ == "__main__":
    main()
