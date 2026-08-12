#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S4 View 层检索：三类晶体统一检索 + 五行补益检索（retrieve_crystals.py）

输入：晶体库目录（classical_v02/ 81 章 + diagnostics/ + tizheng/）
检索：--wuxing 五行 / --kw 关键词 / --status 状态 / --type 类型 / --bu 五行补益
输出：Markdown（人读，默认）或 JSON（机器读，--json）
原则：引用不复制（扫描 frontmatter，不内嵌正文大数据）；无新增实体

用法示例：
  python retrieve_crystals.py --bu 水                # 五行补益：水弱 → 补水章 + 相关体证
  python retrieve_crystals.py --wuxing 水            # 水 dominant 经典章 + 相关
  python retrieve_crystals.py --kw 无为              # 关键词检索
  python retrieve_crystals.py --status draft         # 状态过滤
  python retrieve_crystals.py --type TizhengCard     # 类型过滤
  python retrieve_crystals.py --bu 水 --json         # JSON 输出（机器读）
"""

import argparse
import json
import re
import sys
from pathlib import Path

from contracts import WUXING_ORDER, VALID_TYPES, SHENG_CYCLE, KE_MAP

VALID_WUXING = WUXING_ORDER
CRYSTAL_DIRS = ["classical", "diagnosis", "tizheng", "wisdom"]


def parse_frontmatter(text: str) -> dict:
    """解析 OKF frontmatter（--- 包裹的 YAML 子集）"""
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return {}
    fields = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, val = line.partition(":")
        key, val = key.strip(), val.strip()
        # 内联对象 { by: ..., at: ... } 取 by
        if val.startswith("{") and val.endswith("}"):
            bm = re.search(r"by:\s*([^,}]+)", val)
            val = bm.group(1).strip() if bm else val
        # 数组 [a, b]
        if val.startswith("[") and val.endswith("]"):
            val = [v.strip().strip("\"'") for v in val[1:-1].split(",") if v.strip()]
        fields[key] = val
    return fields


def extract_text_scope(text: str) -> str:
    """正文关键词池：frontmatter 之后的前 600 字（标题/原文开头）"""
    m = re.match(r"^---\n.*?\n---\n(.*)", text, re.S)
    body = m.group(1) if m else text
    return body[:600]


def scan_crystals(root: Path) -> list:
    """扫描三类晶体目录，构建统一索引"""
    crystals = []
    for d in CRYSTAL_DIRS:
        dpath = root / d
        if not dpath.exists():
            continue
        for f in sorted(dpath.glob("*.md")):
            if f.name == "index.md":
                continue
            txt = f.read_text(encoding="utf-8")
            fm = parse_frontmatter(txt)
            if not fm.get("type"):
                continue
            crystals.append({
                "file": str(f.relative_to(root)),
                "type": fm.get("type"),
                "title": fm.get("title", f.stem),
                "status": fm.get("status", "unknown"),
                "generated_by": fm.get("generated", ""),
                "dominant": fm.get("dominant", ""),
                "weak": fm.get("weak", ""),
                "complement": fm.get("complement", ""),
                "dimension": fm.get("dimension", ""),
                "classic": fm.get("classic", ""),
                "recommend": fm.get("recommend", []),
                # WisdomInsight 信任标记（M2 入池写入，检索端展示）
                "sample_size": fm.get("sample_size", ""),
                "anonymization": fm.get("anonymization", ""),
                "depth_wc": (re.search(r"word_count:\s*(\d+)", fm.get("depth", "")) or [None, ""])[1]
                            if isinstance(fm.get("depth"), str) else "",
                "has_situation": (re.search(r"has_situation:\s*(true|false)", fm.get("depth", "")) or [None, ""])[1]
                                 if isinstance(fm.get("depth"), str) else "",
                "text": extract_text_scope(txt),
                "keywords": (fm.get("title", "") + " " + fm.get("description", "")),
            })
    return crystals


def wuxing_match(c: dict, wx: str) -> bool:
    """五行匹配：经典/诊断按 dominant；体证/智慧条目按 weak（缺失行）"""
    if c["type"] in ("TizhengCard", "WisdomInsight"):
        return c.get("weak") == wx or c.get("complement") == wx
    return c.get("dominant") == wx


def filter_crystals(crystals: list, wuxing=None, kw=None, status=None, ctype=None) -> list:
    """组合过滤（AND 语义）"""
    results = []
    for c in crystals:
        if wuxing and not wuxing_match(c, wuxing):
            continue
        if kw:
            kwl = kw.lower()
            hay = (c["title"] + " " + c["keywords"] + " " + c["text"]).lower()
            if kwl not in hay:
                continue
        if status and c["status"] != status:
            continue
        if ctype and c["type"] != ctype:
            continue
        results.append(c)
    return results


def bu_wuxing(crystals: list, wx: str) -> dict:
    """五行补益检索：缺 wx → 该行 dominant 经典章 + 相关体证 + 生克说明"""
    bu = {
        "weak": wx,
        "complement": wx,                      # 缺什么补什么（同气相求）
        "sheng_from": SHENG_CYCLE.get(wx, ""),  # 生 wx 的行（母）
        "sheng_to": [k for k, v in SHENG_CYCLE.items() if v == wx],  # wx 所生（子）
        "ke_by": KE_MAP.get(wx, ""),            # 克 wx 的行（所不胜）
        "ke_to": [k for k, v in KE_MAP.items() if v == wx],  # wx 所克（所胜）
        "classics": [],    # dominant=wx 的经典章
        "tizheng": [],     # weak=wx 的体证卡片
        "wisdom": [],      # weak=wx 的公共智慧条目（M2 入池，样本量透明）
        "diagnosis": [],   # dominant=wx 的诊断
    }
    for c in crystals:
        if c["type"] == "ClassicalInsight" and c.get("dominant") == wx:
            bu["classics"].append({"chapter": c["title"], "file": c["file"]})
        elif c["type"] == "TizhengCard" and (c.get("weak") == wx or c.get("complement") == wx):
            bu["tizheng"].append({"title": c["title"], "file": c["file"], "classic": c.get("classic")})
        elif c["type"] == "WisdomInsight" and (c.get("weak") == wx or c.get("complement") == wx):
            bu["wisdom"].append({"title": c["title"], "file": c["file"], "sample_size": c.get("sample_size")})
        elif c["type"] == "DiagnosisResult" and c.get("dominant") == wx:
            bu["diagnosis"].append({"title": c["title"], "file": c["file"]})
    return bu


def render_markdown(results: list, bu: dict = None) -> str:
    out = []
    if bu:
        out.append(f"# 五行补益检索 · {bu['weak']}弱")
        out.append("")
        sheng_to = "、".join(bu["sheng_to"]) or "无"
        ke_to = "、".join(bu["ke_to"]) or "无"
        out.append(f"- 缺: **{bu['weak']}** → 补: **{bu['complement']}**（同气相求）")
        out.append(f"- 生克: 生{bu['weak']}者={bu['sheng_from']}（母） | {bu['weak']}生者={sheng_to}（子）")
        out.append(f"- 所不胜(克{bu['weak']})={bu['ke_by']} | 所胜({bu['weak']}克)={ke_to}")
        out.append("")
        out.append(f"## 补益经典（{bu['weak']} dominant {len(bu['classics'])} 章）")
        out.append("")
        for c in bu["classics"]:
            out.append(f"- {c['chapter']}（{c['file']}）")
        if bu["tizheng"]:
            out.append("")
            out.append(f"## 相关体证（weak={bu['weak']}，{len(bu['tizheng'])} 张）")
            out.append("")
            for t in bu["tizheng"]:
                out.append(f"- {t['title']} → 关联经典 {t['classic']}（{t['file']}）")
        if bu["wisdom"]:
            out.append("")
            out.append(f"## 公共智慧（weak={bu['weak']}，{len(bu['wisdom'])} 条）")
            out.append("")
            for w in bu["wisdom"]:
                ss = f"（体证 {w['sample_size']} 人）" if w.get("sample_size") else ""
                out.append(f"- {w['title']}{ss}（{w['file']}）")
        if bu["diagnosis"]:
            out.append("")
            out.append("## 相关诊断")
            out.append("")
            for d in bu["diagnosis"]:
                out.append(f"- {d['title']}（{d['file']}）")
    else:
        out.append(f"# 晶体检索 · {len(results)} 条结果")
        out.append("")
        for c in results:
            tag = f"[{c['type']}]"
            wx = f" | 五行: {c['dominant'] or c['weak'] or '-'}"
            st = f" | status: {c['status']}"
            line = f"- {tag} **{c['title']}**{wx}{st}（{c['file']}）"
            if c["type"] == "WisdomInsight":
                trust = []
                if c.get("sample_size"):
                    depth_note = " · 深度体证" if c.get("has_situation") == "true" else ""
                    trust.append(f"体证 {c['sample_size']} 人{depth_note}")
                if c.get("anonymization"):
                    trust.append(f"匿名化：{c['anonymization']}（模式扫描）")
                if trust:
                    line += "  → " + " | ".join(trust)
            out.append(line)
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description="S4 View 层检索：三类晶体统一检索 + 五行补益")
    parser.add_argument("--root", default=str(Path(__file__).parent.parent / "output" / "crystals"),
                        help="晶体库根目录（默认 output/crystals）")
    parser.add_argument("--wuxing", choices=VALID_WUXING, help="按五行检索（经典/诊断 dominant；体证 weak）")
    parser.add_argument("--kw", help="关键词检索（标题/描述/正文前 600 字）")
    parser.add_argument("--status", help="按状态过滤（draft/current/deprecated/retired）")
    parser.add_argument("--type", dest="ctype", choices=VALID_TYPES[1:],  # 去掉 KnowledgeDomain（预留）
                        help="按类型过滤")
    parser.add_argument("--bu", choices=VALID_WUXING, help="五行补益检索（缺该行 → 推荐经典 + 相关体证）")
    parser.add_argument("--json", action="store_true", help="JSON 输出（机器读）")
    args = parser.parse_args()

    crystals = scan_crystals(Path(args.root))
    if not crystals:
        print(f"错误: {args.root} 下未找到晶体", file=sys.stderr)
        sys.exit(1)

    if args.bu:
        bu = bu_wuxing(crystals, args.bu)
        if args.json:
            print(json.dumps(bu, ensure_ascii=False, indent=1))
        else:
            print(render_markdown([], bu))
        return

    results = filter_crystals(crystals, wuxing=args.wuxing, kw=args.kw,
                              status=args.status, ctype=args.ctype)
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=1))
    else:
        print(render_markdown(results))


if __name__ == "__main__":
    main()
