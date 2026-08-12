#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
complete_tizheng.py —— 体证卡片完成流程（B-1，DS-B-2026-001 v1.1 边界①）
================================================================
输入：TizhengCard 文件路径 + 体证三问（done/experience/cognition_shift）
流程：
  1. 读取卡片 frontmatter，校验 type=TizhengCard、status=draft
  2. 三问自检（机器校验，非审核）：
     - 三问均非空
     - 非占位（无模板残留）
     - 每问 ≥ 10 字（防敷衍）
  3. 通过 → status: draft → completed + x-evidence 写入
  4. 失败 → 明确提示（含建设性指引），不流转

设计要点（DS-B-2026-001 v1.1）：
  - 个人闭环不加外部审核：用户亲证即验证（verified: human:<id> 已是 human 层）
  - 自检失败给建设性指引（审核意见 A3）而非仅拒绝
  - x-evidence 含 word_count（供 M2 池条目 depth 复用，审核意见 A5）

用法：
  python complete_tizheng.py --card output/crystals/tizheng/tizheng_hjj_....md \
      --done "我做到了……" --experience "我的体验是……" --cognition "验证了……"
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

MIN_LEN = 10
TEMPLATE_MARKERS = ["（用户践行后填写", "待填写", "TODO", "placeholder"]

REQUIRED_KEYS = ["done", "experience", "cognition_shift"]
KEY_CN = {"done": "我做到了什么", "experience": "我的体验是什么", "cognition_shift": "验证/颠覆了哪个认知"}
KEY_LABEL = {"done": "done（做到了）", "experience": "experience（体验）", "cognition_shift": "cognition_shift（认知）"}


def parse_frontmatter(text: str) -> tuple:
    """解析 OKF frontmatter，返回 (fields, body, frontmatter_raw)"""
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


def self_check(done: str, experience: str, cognition: str) -> list:
    """三问自检（机器校验，非审核）。返回问题列表（空 = 通过）"""
    problems = []
    values = {"done": done, "experience": experience, "cognition_shift": cognition}

    for key in REQUIRED_KEYS:
        v = (values[key] or "").strip()
        if not v:
            problems.append(f"{KEY_CN[key]} 为空——请填写后再提交")
            continue
        if any(marker in v for marker in TEMPLATE_MARKERS):
            problems.append(f"{KEY_CN[key]} 含模板占位残留，请改写为真实体证")
        if len(v) < MIN_LEN:
            problems.append(f"{KEY_LABEL[key]} 仅 {len(v)} 字（需 ≥{MIN_LEN} 字）——请补充具体情境（时间/地点/人物/行为）")

    # experience 具体性启发式（审核意见 A3/A5）：含动词+情境词
    if (experience or "").strip():
        situation_words = ["会议", "今天", "昨天", "家里", "公司", "路上", "与人", "吃饭", "工作", "面对", "当时", "此刻"]
        verb_markers = ["了", "在", "感到", "发现", "尝试", "做到"]
        has_situation = any(w in experience for w in situation_words)
        has_verb = any(w in experience for w in verb_markers)
        if not has_situation and not has_verb:
            problems.append("experience 缺少具体情境（时间/地点/人物/行为）——请补充具体体验细节，而非仅感想")
    return problems


def update_card(path: Path, answers: dict) -> Path:
    """执行完成流转：draft → completed + x-evidence"""
    text = path.read_text(encoding="utf-8")
    fields, body, fm_raw = parse_frontmatter(text)

    if fields.get("type") != "TizhengCard":
        raise ValueError(f"非 TizhengCard（type={fields.get('type')}）")
    if fields.get("status") != "draft":
        raise ValueError(f"状态非 draft（status={fields.get('status')}）——仅 draft 可完成")

    problems = self_check(answers["done"], answers["experience"], answers["cognition_shift"])
    if problems:
        raise ValueError("自检未通过（不流转）:\n  - " + "\n  - ".join(problems))

    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

    # 构造 x-evidence 块（YAML 内联格式）
    evidence_lines = [
        "x-evidence:",
        f"  completed_at: {now}",
        f"  done: {answers['done']}",
        f"  experience: {answers['experience']}",
        f"  cognition_shift: {answers['cognition_shift']}",
        f"  word_count: {{ done: {len(answers['done'])}, experience: {len(answers['experience'])}, cognition_shift: {len(answers['cognition_shift'])} }}",
    ]

    # 替换 status 行 + 在 frontmatter 末尾追加 x-evidence
    lines = fm_raw.splitlines()
    new_lines = []
    inserted = False
    for line in lines:
        if line.strip().startswith("status:"):
            new_lines.append("status: completed")
        else:
            new_lines.append(line)
    new_fm = "\n".join(new_lines) + "\n" + "\n".join(evidence_lines)
    new_text = f"---\n{new_fm}\n---\n{body}"
    path.write_text(new_text, encoding="utf-8")
    return path


def main():
    parser = argparse.ArgumentParser(description="B-1 体证卡片完成流程（draft → completed）")
    parser.add_argument("--card", required=True, help="TizhengCard 文件路径")
    parser.add_argument("--done", required=True, help="我做到了什么")
    parser.add_argument("--experience", required=True, help="我的体验是什么")
    parser.add_argument("--cognition", required=True, help="验证/颠覆了哪个认知")
    args = parser.parse_args()

    answers = {
        "done": args.done,
        "experience": args.experience,
        "cognition_shift": args.cognition,
    }

    print("=" * 68)
    print("B-1 体证卡片完成流程 | complete_tizheng.py")
    print("=" * 68)
    try:
        out = update_card(Path(args.card), answers)
        print(f"[完成] {out} → status: completed")
        print("[x-evidence] 已写入（含 word_count，供池条目 depth 复用）")
    except ValueError as e:
        print(f"[未流转] {e}", file=sys.stderr)
        sys.exit(1)
    print("=" * 68)


if __name__ == "__main__":
    main()
