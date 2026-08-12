#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_tizheng_card.py —— S3 体证卡片生成器（TizhengCard v0.3）
================================================================
输入：事件描述 + 四维自评（时/宇/识/缘 1-10）
流程：
  1. 四维评分 → 最低维度（核心关注维度）
  2. 最低维度 → 五行映射（dimension_map：时火/宇土/识水/缘木）
  3. 镜鉴匹配：从 daojingDatabaseV2.dimensions 取对应维度条目
     （评分 <5 → 低，≥5 → 高；triggers 含事件关键词优先）
  4. 相关经典推荐：weak 五行 dominant 的章（ClassicalInsight）
  5. 生成 TizhengCard（OKF frontmatter + 知-行-证正文）

用法：
  python build_tizheng_card.py --event "会议上对下属提案不耐烦" \
      --scores shi=7 yu=6 shi_identify=3 yuan=5 --user hjj
  python build_tizheng_card.py --event "..." --scores 7,6,3,5  # 顺序: 时,宇,识,缘
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

WUXING_ORDER = ["木", "火", "土", "金", "水"]
DIMENSION_WUXING = {"时位轴": "火", "宇位轴": "土", "识位轴": "水", "缘位轴": "木"}
DIMENSION_KEYS = {"时位轴": "shi", "宇位轴": "yu", "识位轴": "identify", "缘位轴": "yuan"}
DIMENSION_CN = {"时位轴": "时", "宇位轴": "宇", "识位轴": "识", "缘位轴": "缘"}
VALID_VERIFIED = re.compile(r"^(process:[a-z-]+|human:[a-z0-9_-]+)$")
VALID_TYPES = ["KnowledgeDomain", "DiagnosisResult", "ClassicalInsight", "TizhengCard"]


def render_frontmatter(fields: dict) -> str:
    lines = ["---"]
    for k, v in fields.items():
        if k in ("generated", "verified", "sources", "x-mirror", "x-scores", "x-wuxing", "x-relation"):
            continue
        lines.append(f"{k}: {v if v is not None else 'null'}")
    if fields.get("generated"):
        g = fields["generated"]
        lines.append(f"generated: {{ by: {g['by']}, at: {g['at']} }}")
    if fields.get("verified"):
        v = fields["verified"]
        lines.append(f"verified: {{ by: {v['by']}, at: {v['at']} }}")
    if fields.get("sources"):
        lines.append("sources:")
        for s in fields["sources"]:
            lines.append(f"  - id: {s['id']}")
            if s.get("resource"):
                lines.append(f"    resource: {s['resource']}")
    for section in ("x-mirror", "x-scores", "x-wuxing", "x-relation"):
        if fields.get(section):
            lines.append(f"{section}:")
            for k, v in fields[section].items():
                if isinstance(v, (dict, list)):
                    lines.append(f"  {k}: {json.dumps(v, ensure_ascii=False)}")
                else:
                    lines.append(f"  {k}: {v}")
    lines.append("---")
    return "\n".join(lines)


def validate_fields(fields) -> list:
    errors = []
    for k in ["type", "title", "status"]:
        if not fields.get(k):
            errors.append(f"缺必填字段 {k}")
    if fields.get("type") and fields["type"] not in VALID_TYPES:
        errors.append(f"type 非法: {fields['type']}")
    if fields.get("verified"):
        if not VALID_VERIFIED.match(fields["verified"].get("by", "")):
            errors.append(f"verified.by 非法: {fields['verified'].get('by')}")
    wx = fields.get("x-wuxing") or {}
    if wx.get("weak") and wx["weak"] not in WUXING_ORDER:
        errors.append(f"x-wuxing.weak 非法: {wx['weak']}")
    return errors


def crystal_file(fields, body) -> str:
    errors = validate_fields(fields)
    if errors:
        raise ValueError(f"晶体校验失败: {errors}")
    return render_frontmatter(fields) + "\n\n" + body.strip() + "\n"


def load_db(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def find_mirror_entry(db, chapter: int, dimension: str, p_level: str, event: str):
    """从 daojingDatabaseV2.dimensions 匹配镜鉴条目

    优先：triggers 含事件关键词的条目；否则取该维度该级别条目
    """
    dims = db.get(str(chapter), {}).get("dimensions", {})
    level = dims.get(dimension, {}).get(p_level, {})
    if not level:
        return None
    # triggers 匹配优先
    triggers = level.get("triggers", [])
    hit = [t for t in triggers if t and t in event]
    return {
        "chapter": chapter,
        "dimension": dimension,
        "p_level": p_level,
        "trigger_hit": hit[:3] if hit else (triggers[:3] if triggers else []),
        "insight_desc": level.get("insight_desc", ""),
        "action_desc": level.get("action_desc", ""),
        "reflection": level.get("reflection", ""),
    }


def find_weak_wuxing_chapters(db, weak_wx: str, limit: int = 5):
    """weak 五行 dominant 的章（相关经典推荐）"""
    hits = []
    for num in range(1, 82):
        dom = db.get(str(num), {}).get("x_wuxing", {}).get("dominant")
        if dom == weak_wx:
            title = db.get(str(num), {}).get("chapter_title", "")
            hits.append(f"第{num}章 · {title}")
    return hits[:limit], len(hits)


def build_card(args) -> str:
    db = load_db(Path(args.db))

    # 1. 四维评分
    scores = {}
    keys = ["时位轴", "宇位轴", "识位轴", "缘位轴"]
    for dim in keys:
        scores[dim] = args.scores[DIMENSION_KEYS[dim]]

    # 2. 最低维度 + 五行
    lowest_dim = min(keys, key=lambda d: scores[d])
    weak_wx = DIMENSION_WUXING[lowest_dim]
    p_level = "低" if scores[lowest_dim] < 5 else "高"

    # 3. 镜鉴匹配（用最低维度所在章？——需要定章节：默认从镜鉴数据库找 triggers 命中的章，
    #    若无命中用"该维度低分推荐章"——简版：先全局搜 triggers 命中章）
    matched = None
    for num in range(1, 82):
        dims = db.get(str(num), {}).get("dimensions", {}).get(lowest_dim, {}).get(p_level, {})
        if any(t and t in args.event for t in dims.get("triggers", [])):
            matched = find_mirror_entry(db, num, lowest_dim, p_level, args.event)
            break
    if not matched:
        matched = find_mirror_entry(db, args.fallback_chapter, lowest_dim, p_level, args.event)
        if not matched:
            matched = {"chapter": args.fallback_chapter, "dimension": lowest_dim,
                       "p_level": p_level, "trigger_hit": [],
                       "insight_desc": f"（第{args.fallback_chapter}章 {lowest_dim}·{p_level} 镜鉴条目缺失）",
                       "action_desc": "", "reflection": ""}

    # 4. 相关经典推荐（weak 五行 dominant 章）
    rec_chapters, n_wx = find_weak_wuxing_chapters(db, weak_wx)

    # 5. 字段
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    fields = {
        "type": "TizhengCard",
        "title": f"体证：{args.event[:20]}（{DIMENSION_CN[lowest_dim]}位·{p_level}）",
        "status": "draft",
        "generated": {"by": f"human:{args.user}@镜鉴", "at": now},
        "verified": {"by": f"human:{args.user}", "at": now},
        "sources": [{"id": f"mirror-{matched['chapter']}-{lowest_dim}-{p_level}",
                     "resource": "daojing_database_v2.json#dimensions"}],
        "x-mirror": {
            "chapter": matched["chapter"],
            "dimension": lowest_dim,
            "p_level": p_level,
            "trigger": matched["trigger_hit"],
            "classic": db.get(str(matched["chapter"]), {}).get("chapter_title", ""),
        },
        "x-scores": {DIMENSION_KEYS[d]: scores[d] for d in keys},
        "x-wuxing": {
            "weak": weak_wx,
            "lowest_dimension": lowest_dim,
            "complement": weak_wx,
            "recommend": rec_chapters,
            "weak_chapter_count": n_wx,
        },
    }

    # 正文（知-行-证）
    body = [f"# 体证卡片 · {DIMENSION_CN[lowest_dim]}位·{p_level}", ""]
    body.append(f"**用户**: {args.user}  **时间**: {args.generated_at or now[:10]}")
    body.append("")
    body.append("## 事件（知）")
    body.append("")
    body.append(args.event)
    body.append("")
    body.append("## 四维评分")
    body.append("")
    for d in keys:
        mark = " ← 核心关注" if d == lowest_dim else ""
        body.append(f"- {d}: {scores[d]} 分{mark}")
    body.append("")
    body.append("## 镜鉴反馈（行）")
    body.append("")
    body.append(f"📖 第{matched['chapter']}章 · {db.get(str(matched['chapter']), {}).get('chapter_title', '')}")
    body.append("")
    if matched["insight_desc"]:
        body.append(f"**洞察**: {matched['insight_desc']}")
    if matched["action_desc"]:
        body.append(f"**今日功课**: {matched['action_desc']}")
    if matched["reflection"]:
        body.append(f"🤔 **反思**: {matched['reflection']}")
    body.append("")
    body.append("## 五行补益")
    body.append("")
    body.append(f"- 最低维度: {lowest_dim} → **{weak_wx}弱**（补{weak_wx}）")
    body.append(f"- 推荐经典（{weak_wx} dominant 章 {n_wx} 章）: {', '.join(rec_chapters) if rec_chapters else '待补充'}")
    body.append("")
    body.append("## 体证记录（证）")
    body.append("")
    body.append("（用户践行后填写：我做到了什么 + 我的体验是什么 + 验证/颠覆了哪个认知）")
    return crystal_file(fields, "\n".join(body))


def main():
    parser = argparse.ArgumentParser(description="S3 体证卡片生成器")
    parser.add_argument("--event", required=True, help="事件描述")
    parser.add_argument("--scores", required=True, help="四维评分: shi,yu,identify,yuan 或 7,6,3,5（时,宇,识,缘）")
    parser.add_argument("--user", default="hjj", help="用户 id")
    parser.add_argument("--db", default="verify/daojing_database_v2.json", help="结构库")
    parser.add_argument("--fallback-chapter", type=int, default=10, help="无触发命中时的默认章")
    parser.add_argument("--generated-at", default=None, help="事件日期 YYYY-MM-DD")
    parser.add_argument("--out", default="output/crystals/tizheng", help="输出目录")
    args = parser.parse_args()

    # 解析评分
    parts = [p.strip() for p in args.scores.split(",")]
    if len(parts) == 4 and all(p.isdigit() for p in parts):
        args.scores = {"shi": int(parts[0]), "yu": int(parts[1]),
                       "identify": int(parts[2]), "yuan": int(parts[3])}
    else:
        args.scores = {}
        for p in parts:
            k, v = p.split("=")
            args.scores[k.strip()] = int(v.strip())
        assert all(k in args.scores for k in ["shi", "yu", "identify", "yuan"]), "评分键需含 shi/yu/identify/yuan"

    print("=" * 68)
    print("S3 体证卡片生成器 | TizhengCard v0.3")
    print("=" * 68)
    print(f"[事件] {args.event}")
    print(f"[评分] {args.scores}")

    card = build_card(args)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    fname = f"tizheng_{args.user}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    (out / fname).write_text(card, encoding="utf-8")
    print(f"[输出] {out / fname}")
    print("=" * 68)


if __name__ == "__main__":
    main()
