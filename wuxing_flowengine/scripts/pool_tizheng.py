#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pool_tizheng.py —— 体证入池流程（B-2，DS-B-2026-001 v1.1 边界②）
================================================================
输入：completed 的 TizhengCard 文件路径 + 用户确认（--confirm）
流程（三道护栏，无人工审核员）：
  护栏1 · 匿名化核验：PII 模式扫描（姓名/手机/邮箱/公司名/地点）
         → 命中拦截 + 提示脱敏；通过 → 输出扫描边界说明（审核 A2）
  护栏2 · 完整度校验：三问非空 + ≥10 字 + experience 具体性
         → 失败给建设性指引（审核 A3）；通过 → 输出 depth 数据（审核 A5）
  护栏3 · 用户确认（唯一人类环节）：展示匿名化预览 + 扫描边界说明
         → 用户 --confirm yes 才入池
入池：生成 wisdom/w-{ts}-{hash6}.md（published 副本，信任标记）+ 回注数据库（方案 A，M3 衔接）

设计要点（DS-B-2026-001 v1.1）：
  - verified: human:anonymous（匿名亲证，非 process）
  - x-evidence: sample_size + depth + anonymization: best-effort（信任标记）
  - 摘要 ≤200 字（引用性精炼，非原文复制——契约例外条款，审核 A9）
  - 原卡片保持 completed，回注 x-ref.pooled

用法：
  python pool_tizheng.py --card output/crystals/tizheng/tizheng_hjj_....md --confirm yes
"""

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

MIN_LEN = 10
SUMMARY_MAX = 200
TEMPLATE_MARKERS = ["（用户践行后填写", "待填写", "TODO", "placeholder"]

# PII 模式（护栏1）：姓名/手机/邮箱/公司名/地点——显式标注扫描边界（审核 A2）
PII_PATTERNS = {
    "手机号": re.compile(r"1[3-9]\d{9}"),
    "邮箱": re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),
    "身份证": re.compile(r"\d{17}[\dXx]"),
    "姓名(中文2-4字全名模式)": re.compile(r"(?:我叫|我是|我的名字|姓名)[:：]?[\u4e00-\u9fa5]{2,4}"),
    "公司名(XX公司/集团)": re.compile(r"[\u4e00-\u9fa5]{2,12}(?:公司|集团|科技|有限)"),
    "地点(市/区/县)": re.compile(r"[\u4e00-\u9fa5]{2,8}(?:市|区|县|镇)"),
}
SCAN_BOUNDARY_NOTE = "匿名化：尽力而为（模式扫描）。已扫描：姓名/手机/邮箱/身份证/公司名/地点；未扫描：上下文推断性识别（如'今天在XX部门'的部门名）"

SITUATION_WORDS = ["会议", "今天", "昨天", "家里", "公司", "路上", "与人", "吃饭", "工作", "面对", "当时", "此刻", "下午", "早上"]
VERB_MARKERS = ["了", "在", "感到", "发现", "尝试", "做到"]


def parse_frontmatter(text: str) -> tuple:
    m = re.match(r"^---\n(.*?)\n---\n?(.*)", text, re.S)
    if not m:
        raise ValueError("文件缺少 OKF frontmatter")
    fm_raw, body = m.group(1), m.group(2)
    fields = {}
    for line in fm_raw.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, val = line.partition(":")
        key, val = key.strip(), val.strip()
        if val.startswith("{") and val.endswith("}"):
            bm = re.search(r"by:\s*([^,}]+)", val)
            val = bm.group(1).strip() if bm else val
        if val.startswith("[") and val.endswith("]"):
            val = [v.strip().strip("\"'") for v in val[1:-1].split(",") if v.strip()]
        fields[key] = val
    return fields, body, fm_raw


def guard1_anonymize(texts: list) -> list:
    """护栏1：PII 模式扫描。返回命中列表（空 = 通过）"""
    hits = []
    for t in texts:
        for label, pat in PII_PATTERNS.items():
            for m in pat.finditer(t):
                hits.append(f"[{label}] 命中: {m.group(0)}")
    return hits


def guard2_completeness(done: str, experience: str, cognition: str) -> tuple:
    """护栏2：完整度校验。返回 (通过?, 问题列表, depth 数据)"""
    problems = []
    values = {"done": done, "experience": experience, "cognition_shift": cognition}
    labels = {"done": "done（做到了）", "experience": "experience（体验）", "cognition_shift": "cognition_shift（认知）"}
    for k, v in values.items():
        v = (v or "").strip()
        if not v:
            problems.append(f"{labels[k]} 为空")
        elif len(v) < MIN_LEN:
            problems.append(f"{labels[k]} 仅 {len(v)} 字（需 ≥{MIN_LEN} 字）——请补充具体情境（时间/地点/人物/行为）")
        elif any(marker in v for marker in TEMPLATE_MARKERS):
            problems.append(f"{labels[k]} 含模板占位残留")
    has_situation = any(w in (experience or "") for w in SITUATION_WORDS)
    has_verb = any(w in (experience or "") for w in VERB_MARKERS)
    if (experience or "").strip() and not has_situation and not has_verb:
        problems.append("experience 缺少具体情境——请补充具体体验细节，而非仅感想")
    depth = {
        "word_count": sum(len((v or "").strip()) for v in values.values()),
        "has_situation": bool(has_situation and has_verb),
    }
    return (len(problems) == 0), problems, depth


def summarize(answers: dict) -> str:
    """引用性精炼摘要（≤200 字，非原文复制——契约例外条款，审核 A9）"""
    parts = []
    if answers["done"]:
        parts.append(f"做到了：{answers['done'][:60]}")
    if answers["experience"]:
        parts.append(f"体验：{answers['experience'][:60]}")
    if answers["cognition_shift"]:
        parts.append(f"认知：{answers['cognition_shift'][:50]}")
    summary = "；".join(parts)
    return summary[:SUMMARY_MAX]


def extract_answers(fields: dict, text: str) -> dict:
    """从 x-evidence 提取三问（个人文件内）"""
    m = re.search(r"x-evidence:.*?done: (.*?)\nexperience: (.*?)\ncognition_shift: (.*?)\n", text, re.S)
    if m:
        return {"done": m.group(1), "experience": m.group(2), "cognition_shift": m.group(3)}
    return {"done": fields.get("done", ""), "experience": fields.get("experience", ""),
            "cognition_shift": fields.get("cognition_shift", "")}


def write_db_backref(db_path: Path, chapter: str, wid: str):
    """M3 回注（方案 A）：写 daojing_database_v2.json → 章节点 x_application
    x_application: { tizheng_count, wisdom_refs }——晶体生成时自动读取（数据源是可信源）
    """
    if not chapter or not db_path.exists():
        return False
    db = json.loads(db_path.read_text(encoding="utf-8"))
    node = db.get(str(chapter))
    if node is None:
        return False
    xa = node.get("x_application") or {"tizheng_count": 0, "wisdom_refs": []}
    if wid not in xa["wisdom_refs"]:
        xa["wisdom_refs"].append(wid)
    xa["tizheng_count"] = len(xa["wisdom_refs"])
    node["x_application"] = xa
    db_path.write_text(json.dumps(db, ensure_ascii=False, indent=1), encoding="utf-8")
    return True


def pool_card(path: Path, confirm: bool, db_path: Path) -> dict:
    """执行入池（三道护栏）。返回池条目信息"""
    text = path.read_text(encoding="utf-8")
    fields, body, _ = parse_frontmatter(text)

    if fields.get("type") != "TizhengCard":
        raise ValueError(f"非 TizhengCard（type={fields.get('type')}）")
    if fields.get("status") != "completed":
        raise ValueError(f"状态非 completed（status={fields.get('status')}）——仅 completed 可入池（先跑 complete_tizheng.py）")

    answers = extract_answers(fields, text)

    # 护栏1：PII 扫描
    scan_texts = [answers.get("done", ""), answers.get("experience", ""), answers.get("cognition_shift", ""),
                  fields.get("title", ""), fields.get("x-mirror", "") if isinstance(fields.get("x-mirror"), str) else ""]
    pii_hits = guard1_anonymize([t for t in scan_texts if t])
    if pii_hits:
        raise ValueError("护栏1 · 匿名化核验未通过（请脱敏后重提）:\n  - " + "\n  - ".join(pii_hits))

    # 护栏2：完整度
    ok, problems, depth = guard2_completeness(answers.get("done", ""), answers.get("experience", ""),
                                              answers.get("cognition_shift", ""))
    if not ok:
        raise ValueError("护栏2 · 完整度校验未通过（不入池）:\n  - " + "\n  - ".join(problems))

    # 匿名化预览 + 扫描边界说明（护栏3）
    summary = summarize(answers)
    preview = f"--- 匿名化预览 ---\n标题: {fields.get('title')}\n摘要: {summary}\n---\n{SCAN_BOUNDARY_NOTE}"
    if not confirm:
        raise ValueError(f"护栏3 · 需用户确认（--confirm yes）:\n{preview}")

    # 入池：生成 wisdom 条目
    now = datetime.now()
    ts = now.strftime("%Y%m%d-%H%M%S")
    hash6 = hashlib.md5((path.name + ts).encode()).hexdigest()[:6]
    wid = f"w-{ts}-{hash6}"

    # x-mirror/x-wuxing 字段：解析器将嵌套键提到顶层（chapter/dimension/p_level/classic/weak/complement）
    chapter = fields.get("chapter", "")
    weak = fields.get("weak", "")
    complement = fields.get("complement", "") or weak

    entry = f"""---
type: WisdomInsight
title: 体证洞察：{fields.get('title', '').replace('体证：', '')[:30]}
status: published
generated: {{ by: pool_tizheng.py/0.1, at: {now.strftime('%Y-%m-%dT%H:%M:%SZ')} }}
verified: {{ by: human:anonymous, at: {now.strftime('%Y-%m-%dT%H:%M:%SZ')} }}
sources:
  - id: mirror-{chapter}-{fields.get('dimension', '')}-{fields.get('p_level', '')}
    resource: daojing_database_v2.json#dimensions
x-mirror:
  chapter: {chapter}
  dimension: {fields.get('dimension', '')}
  p_level: {fields.get('p_level', '')}
  classic: {fields.get('classic', '')}
x-wuxing:
  weak: {weak}
  complement: {complement}
x-evidence:
  sample_size: 1
  depth: {{ word_count: {depth['word_count']}, has_situation: {str(depth['has_situation']).lower()} }}
  anonymization: best-effort
  pooled: true
  source_ref: {path.name}
---
{summary}
※ 摘要为引用性精炼（≤200 字），非原文复制——契约"引用不复制"例外条款
"""

    # wisdom 目录：固定在晶体库 output/crystals/wisdom（与卡片所在 tizheng/ 同级）
    wisdom_dir = Path(__file__).parent.parent / "output" / "crystals" / "wisdom"
    wisdom_dir.mkdir(parents=True, exist_ok=True)
    entry_path = wisdom_dir / f"{wid}.md"
    entry_path.write_text(entry, encoding="utf-8")

    # 原卡片回注 x-ref.pooled（保持 completed）
    if "x-ref:" not in text:
        new_text = text.replace("---\n", f"x-ref:\n  pooled: {wid}\n---\n", 1) if text.count("---") >= 2 else text
        # 更稳妥：在最后一个 frontmatter 行后插入——用 frontmatter 末尾的 status 行替换
        fm_end = text.find("\n---", text.find("\n---") + 4)
        new_text = text[:fm_end] + f"\nx-ref:\n  pooled: {wid}" + text[fm_end:]
        path.write_text(new_text, encoding="utf-8")

    # M3 回注（方案 A）：写数据库 x_application
    ref_ok = write_db_backref(db_path, chapter, wid)
    if not ref_ok:
        print(f"[警告] 数据库回注未执行（chapter={chapter!r} 或 db 不存在）——不影响入池，但经典章 x-application 将缺失")

    return {"id": wid, "path": str(entry_path), "chapter": chapter, "weak": weak}


def main():
    parser = argparse.ArgumentParser(description="B-2 体证入池流程（completed → published，三道护栏）")
    parser.add_argument("--card", required=True, help="completed 的 TizhengCard 文件路径")
    parser.add_argument("--confirm", default="no", help="用户确认（yes=确认匿名化预览后入池；唯一人类环节）")
    parser.add_argument("--db", default="verify/daojing_database_v2.json", help="结构库（M3 回注用）")
    args = parser.parse_args()

    print("=" * 68)
    print("B-2 体证入池流程 | pool_tizheng.py")
    print("=" * 68)
    try:
        info = pool_card(Path(args.card), args.confirm.lower() == "yes", Path(args.db))
        print(f"[入池] {info['id']} → {info['path']}")
        print(f"[信任标记] verified: human:anonymous | sample_size: 1 | anonymization: best-effort")
        print(f"[关联] chapter={info['chapter']} weak={info['weak']}")
        print("[原卡片] status 保持 completed + x-ref.pooled 回注")
    except ValueError as e:
        print(f"[未入池] {e}", file=sys.stderr)
        sys.exit(1)
    print("=" * 68)


if __name__ == "__main__":
    main()
