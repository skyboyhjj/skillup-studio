#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_classical_crystals.py v0.2 —— S2 经典晶体化（三源归一）
=============================================================
将五步读解 81 章 + daojingDatabaseV2 结构 + 镜鉴矩阵 合成为 ClassicalInsight 晶体
（对齐契约 IF-2026-006 §二）。

数据源：
  ① 五步读解.md（81 章，25 文件）→ 正文（五步读解文本 + 原文 + SPO）
  ② daojingDatabaseV2.json（结构源）→ original_text/core_concepts/spo_triples/dimensions/daily_mirror
  ③ chapters/*.html（可选）→ 概念标签交叉验证

设计要点：
  - 标题兼容：阿拉伯（第10章）与中文数字（第十六章）
  - 正文优先五步读解，缺失时用 daojingDatabaseV2 兜底（原文+概念占位）
  - SPO 优先 daojingDatabaseV2（572 条），缺失时用读解内嵌
  - x-wuxing 保留结构，dominant 待五行映射（不假装精确——留空标注）
  - status: draft（AI 初审）——导师确认后 --verified-by

用法：
  python build_classical_crystals.py --md-dir uploads --db verify/daojing_database_v2.json
  python build_classical_crystals.py --md-dir uploads --db verify/daojing_database_v2.json --verified-by master
"""

import argparse
import glob
import json
import re
from datetime import datetime
from pathlib import Path

WUXING_ORDER = ["木", "火", "土", "金", "水"]
VALID_TYPES = ["KnowledgeDomain", "DiagnosisResult", "ClassicalInsight", "TizhengCard"]
VALID_VERIFIED = re.compile(r"^(process:[a-z-]+|human:[a-z0-9_-]+)$")

# 四维→五行映射定案（DEC-2026-009 V1.1）：识水/缘木/宇土/时火；玄鉴决策中心=金（义·统摄决断）
DIMENSION_WUXING = {"时位轴": "火", "宇位轴": "土", "识位轴": "水", "缘位轴": "木"}
XUANJIAN_WUXING = "金"  # 玄鉴决策中心 = 金（四维之上的统摄决策层）

# 中文数字映射（章节标题）
CN_NUM = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}


def cn2num(s: str) -> int:
    s = s.strip()
    if '十' not in s:
        return CN_NUM.get(s, 0)
    parts = s.split('十')
    if parts[0] == '' and parts[1] == '':
        return 10
    if parts[0] == '':
        return 10 + CN_NUM.get(parts[1], 0)
    if parts[1] == '':
        return CN_NUM.get(parts[0], 0) * 10
    return CN_NUM.get(parts[0], 0) * 10 + CN_NUM.get(parts[1], 0)


def extract_chapter_num(title: str):
    """从标题提取章号（阿拉伯/中文数字兼容）"""
    m = re.match(r'^第(.+?)章', title)
    if not m:
        return None
    num = m.group(1)
    if num.isdigit():
        return int(num)
    return cn2num(num)


# ============ 工具（与契约一致） ============
def render_frontmatter(fields: dict) -> str:
    lines = ["---"]
    for k, v in fields.items():
        if k in ("generated", "verified", "sources", "x-wuxing", "x-mirror", "x-compute"):
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
    for section in ("x-wuxing", "x-mirror", "x-compute"):
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
    return errors


def crystal_file(fields, body) -> str:
    errors = validate_fields(fields)
    if errors:
        raise ValueError(f"晶体校验失败: {errors}")
    return render_frontmatter(fields) + "\n\n" + body.strip() + "\n"


# ============ 解析五步读解 ============
def parse_wubu_dir(md_dir: Path):
    """解析五步读解目录 → {章号: {title, original, steps, spo}}"""
    chapters = {}
    for f in sorted(md_dir.glob("**/第*章_五步读解.md")):
        text = f.read_text(encoding="utf-8", errors="replace")
        # 按章节标题切分（兼容 # 和 ##、阿拉伯/中文数字）
        blocks = []
        cur = None
        for line in text.splitlines():
            m = re.match(r'^#{1,2}\s*(第.+?章)[^\n]*', line)
            if m:
                n = extract_chapter_num(m.group(1))
                if n and 1 <= n <= 81:
                    if cur and cur["num"] not in chapters:
                        chapters[cur["num"]] = cur
                    cur = {"num": n, "title": line.strip().lstrip("#").strip(),
                           "lines": [], "original": "", "spo": []}
                    continue
            if cur is not None:
                cur["lines"].append(line)
        if cur and cur["num"] not in chapters:
            chapters[cur["num"]] = cur

        # 提取原文（### 原文 或 **原文** 段）+ 内嵌 SPO
        for ch in [chapters.get(k) for k in list(chapters) if k in chapters]:
            if not ch:
                continue
            lines = ch["lines"]
            ch["original"] = ""
            # 格式 A：### 原文 标题段
            for m in re.finditer(r'^#{1,3}\s*原文[^\n]*\n(.*?)(?=^#{1,3}|\Z)', "\n".join(lines), re.M | re.S):
                ch["original"] = m.group(1).strip()
                break
            # 格式 B：**原文**（王弼本）：加粗段
            if not ch["original"]:
                for i, line in enumerate(lines):
                    if re.match(r'^\*\*原文', line):
                        j = i + 1
                        orig = []
                        while j < len(lines) and not re.match(r'^#{1,3}', lines[j]) \
                                and not re.match(r'^\*\*', lines[j]):
                            orig.append(lines[j])
                            j += 1
                        ch["original"] = "\n".join(orig).strip()
                        break
            # 内嵌 SPO JSON（```json 代码块）
            ch["spo"] = extract_spo_json("\n".join(lines))
    return chapters


def extract_spo_json(text: str) -> list:
    """提取 ```json 代码块中的 SPO 三元组"""
    spo = []
    for m in re.finditer(r'```json\s*(\{.*?\})\s*```', text, re.S):
        try:
            obj = json.loads(m.group(1))
            if isinstance(obj, list):
                spo.extend(obj)
            elif isinstance(obj, dict) and "spo_triples" in obj:
                spo.extend(obj["spo_triples"])
        except Exception:
            pass
    return spo


# ============ 解析 daojingDatabaseV2 ============
def load_daojing_db(db_path: Path):
    """加载 daojingDatabaseV2.json → {章号: {...}}"""
    return json.loads(db_path.read_text(encoding="utf-8"))


# ============ 晶体构建 ============
def build_crystal(num: int, wubu, db_entry, verified_by: str = None):
    """单章三源合成 → ClassicalInsight 晶体"""
    is_confirmed = verified_by is not None
    db = db_entry or {}

    # 标题优先读解，其次数据库
    w_title = wubu["title"] if wubu else ""
    db_title = f"{num}章 {db.get('chapter_title', '')}" if db else ""
    title = w_title or db_title or f"第{num}章"

    # 原文优先读解，其次数据库
    original = wubu["original"] if wubu and wubu["original"] else db.get("original_text", "")

    # SPO 优先数据库（572 条权威），其次读解内嵌
    spo = db.get("spo_triples") or (wubu["spo"] if wubu else [])

    # 概念
    concepts = db.get("core_concepts", [])

    # 镜鉴（dimensions 主源 + daily_mirror 精选）
    dims = db.get("dimensions", {})
    dim_summary = {}
    for dim_name, levels in dims.items():
        dim_summary[dim_name] = {lv: list(lv_data.get("triggers", []))[:3]
                                 for lv, lv_data in levels.items()}
    dm = (db.get("empowerment") or {}).get("daily_mirror") or {}

    fields = {
        "type": "ClassicalInsight",
        "title": title,
        "description": f"道德经第{num}章五步读解与结构化知识（SPO {len(spo)} 条）",
        "generated": {"by": "build_classical_crystals/0.2",
                      "at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")},
        "verified": {"by": f"human:{verified_by}",
                     "at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")} if is_confirmed else None,
        "sources": [
            {"id": f"wubu-{num:02d}", "resource": f"第{num:02d}章_五步读解"},
            {"id": f"daojing-v2-{num}", "resource": "daojing_database_v2.json"},
        ],
        "status": "current" if is_confirmed else "draft",
        "x-wuxing": {
            "dimension_map": DIMENSION_WUXING,
            "xuanjian": XUANJIAN_WUXING,
            "dominant": (db.get("x_wuxing") or {}).get("dominant"),
            "dist": (db.get("x_wuxing") or {}).get("dist"),
            "note": "四维映射定案（DEC-2026-009 V1.1）：识水/缘木/宇土/时火；玄鉴决策中心=金；dominant=概念级标注（S2/S3）或待SPO补充",
        },
        "x-mirror": {
            "dimensions": dim_summary or None,
            "daily_mirror": {k: v for k, v in dm.items() if v} or None,
        },
        "x-compute": {"spo_count": len(spo), "spo_ref": f"daojing_database_v2.json#{num}"},
    }
    # 去空
    fields["x-mirror"] = {k: v for k, v in fields["x-mirror"].items() if v}

    # 正文
    body = [f"# 第{num}章", ""]
    body.append(f"**标题**: {db.get('chapter_title', '')}")
    if concepts:
        body.append(f"**核心概念**: {'、'.join(concepts)}")
    body.append("")
    body.append("## 原文")
    body.append("")
    body.append(original or "（原文待补——daojingDatabaseV2 无此章原文）")
    body.append("")
    if wubu and wubu["lines"]:
        body.append("## 五步读解")
        body.append("")
        body.extend(wubu["lines"])
    else:
        body.append("## 五步读解")
        body.append("")
        body.append("（五步读解正文待补——当前为结构骨架）")
    body.append("")
    body.append(f"## 结构化知识（{len(spo)} 条 SPO）")
    body.append("")
    body.append(f"SPO 三元组见 daojingDatabaseV2（`x-compute.spo_ref`），共 {len(spo)} 条。")
    body.append("")
    if not is_confirmed:
        body.append("> Base 铁律：只组织，不生产。本晶体为 AI 初审（draft，未验证），")
        body.append("> 待人类导师确认后 status 改 current 并 verified: human:<id>。")
    return crystal_file(fields, "\n".join(body))


def main():
    parser = argparse.ArgumentParser(description="S2 经典晶体化 v0.2（三源归一）")
    parser.add_argument("--md-dir", default="uploads", help="五步读解.md 目录")
    parser.add_argument("--db", default="verify/daojing_database_v2.json", help="daojingDatabaseV2.json")
    parser.add_argument("--out", default="output/crystals/classical", help="晶体输出目录")
    parser.add_argument("--verified-by", default=None, help="导师确认者 id")
    args = parser.parse_args()

    print("=" * 68)
    print("S2 经典晶体化 v0.2 | 三源归一（五步读解 + daojingDatabaseV2 + 镜鉴）")
    print("=" * 68)

    md_dir = Path(args.md_dir)
    wubu = parse_wubu_dir(md_dir) if md_dir.exists() else {}
    print(f"[五步读解] {len(wubu)} 章")

    db_path = Path(args.db)
    db = load_daojing_db(db_path) if db_path.exists() else {}
    print(f"[结构库] {len(db)} 章（SPO {sum(len(v.get('spo_triples', [])) for v in db.values())} 条）")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    n_ok, n_warn = 0, 0
    for num in range(1, 82):
        try:
            body = build_crystal(num, wubu.get(num), db.get(str(num)), args.verified_by)
            (out / f"{num}.md").write_text(body, encoding="utf-8")
            n_ok += 1
            has_wubu = num in wubu
            has_spo = len((db.get(str(num)) or {}).get("spo_triples", [])) > 0
            if not has_wubu or not has_spo:
                n_warn += 1
                print(f"  ⚠️ {num:02d}.md 读解={'✅' if has_wubu else '❌'} SPO={'✅' if has_spo else '❌'}")
        except Exception as e:
            print(f"  ❌ 第{num}章: {e}")

    # index
    idx_lines = ["# 经典晶体库 · 目录（81 章）", "",
                 f"- 生成: {datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')}",
                 f"- 晶体数: {n_ok}/81", "", "## 章节索引", ""]
    for num in range(1, 82):
        db_entry = db.get(str(num), {})
        idx_lines.append(f"- [第{num}章 · {db_entry.get('chapter_title', '')}]({num}.md)")
    (out / "index.md").write_text("\n".join(idx_lines) + "\n", encoding="utf-8")

    print("-" * 68)
    print(f"[汇总] {n_ok}/81 章晶体化 → {out}/（警告 {n_warn} 章：缺读解或 SPO）")
    print("=" * 68)


if __name__ == "__main__":
    main()
