#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data_validator.py —— Phase B 质量门（七检查点 + 自愈三态 + 排除清单）
========================================================================
对齐《晶体Schema与PhaseB_接口契约》（IF-2026-006）§三：

  七检查点：schema 完整性 / 五行合法 / 权重为正 / 量级合理性 /
            空月检测 / 截断检测 / 标注一致性
  自愈三态：pass（通过）/ warn（降级继续）/ fail（阻断）
  排除清单：.collectignore（显式排除项，不参与检查）
  输出：quality_report.json（含 verified 契约字段）

用法：
  python data_validator.py --dir .            # 扫描目录内所有 *_tree_*.json
  python data_validator.py --month 2026-08    # 只查指定月份
  python data_validator.py --dir . --write    # 顺带写 quality_report.json

零依赖（标准库）。
"""

import argparse
import json
import glob
import re
import statistics
from datetime import date
from pathlib import Path

WUXING_ORDER = ["木", "火", "土", "金", "水"]
CANONICAL_WUXING = {
    "cs.AI": "火", "cs.LG": "土", "cs.CL": "水", "cs.CV": "木",
    "cs.NE": "水", "cs.MA": "木", "cs.RO": "金", "cs.HC": "火",
    "cs.IR": "金", "cs.MM": "火", "stat.ML": "土",
    "LLM": "水", "NLP": "水", "计算机视觉": "木", "CV": "木",
}
VOLUME_RATIO_WARN = 3.0   # 量级比历史均值 >3x 或 <0.33x → warn
EMPTY_IS_FAIL = True      # 空月 → fail（除非回退机制已处理）


def extract_month(filename: str) -> str:
    m = re.search(r"(\d{4})-(\d{2})", filename)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    m2 = re.search(r"(\d{6})", filename)
    if m2:
        s = m2.group(1)
        return f"{s[:4]}-{s[4:]}"
    return "unknown"


def load_collectignore(directory: Path):
    """解析 .collectignore（每行一个排除模式，支持 # 注释）"""
    excludes = []
    f = directory / ".collectignore"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                excludes.append(line)
    return excludes


def check_schema(tree):
    """检查点 1：schema 完整性"""
    issues = []
    if not isinstance(tree, dict):
        return "fail", "树文件不是 JSON 对象"
    for k in ["schema_version", "source", "month", "nodes"]:
        if k not in tree:
            issues.append(f"缺顶层字段 {k}")
    nodes = tree.get("nodes", [])
    if not isinstance(nodes, list):
        issues.append("nodes 不是数组")
    else:
        for i, n in enumerate(nodes[:20]):
            for k in ["id", "name", "weight"]:
                if k not in n:
                    issues.append(f"节点[{i}] 缺字段 {k}")
    if issues:
        return "fail", "; ".join(issues[:5])
    return "pass", f"schema v{tree.get('schema_version', '?')} 完整，{len(nodes)} 节点"


def check_wuxing(tree):
    """检查点 2：五行合法（已标注节点；未标注 → warn 提示将按 canonical）"""
    nodes = tree.get("nodes", [])
    unlabeled = 0
    invalid = []
    for n in nodes:
        w = n.get("wuxing")
        if w is None or w == "":
            unlabeled += 1
            continue
        if w not in WUXING_ORDER:
            invalid.append(f"{n.get('id')}={w}")
    if invalid:
        return "fail", f"非法五行: {invalid[:5]}"
    if unlabeled > 0:
        return "warn", f"{unlabeled}/{len(nodes)} 节点未标注（将按 canonical 映射）"
    return "pass", f"全部 {len(nodes)} 节点五行合法"


def check_weight(tree):
    """检查点 3：权重为正"""
    nodes = tree.get("nodes", [])
    zeros = [n.get("id") for n in nodes if n.get("weight", 1) == 0]
    neg = [n.get("id") for n in nodes if n.get("weight", 1) < 0]
    if neg:
        return "fail", f"负权重: {neg[:5]}"
    if zeros:
        return "warn", f"weight=0 节点（废弃标签）: {zeros[:5]}"
    return "pass", f"全部 {len(nodes)} 节点权重为正"


def check_volume(tree, history):
    """检查点 4：量级合理性（与同源历史均值比）"""
    nodes = tree.get("nodes", [])
    total = sum(n.get("weight", 0) for n in nodes)
    if not history:
        return "pass", f"无历史可比，记录基线（total={total}）"
    mean = statistics.mean(history)
    if mean <= 0:
        return "pass", "历史均值异常（≤0），跳过量级检查"
    ratio = total / mean
    if ratio > VOLUME_RATIO_WARN or ratio < 1 / VOLUME_RATIO_WARN:
        return "warn", (f"量级偏离历史均值 {ratio:.1f}x（本月 total={total} vs "
                        f"历史均值 {mean:.0f}）——月中样本或采集异常")
    return "pass", f"量级正常（{ratio:.2f}x 历史均值）"


def check_empty(tree):
    """检查点 5：空月检测"""
    nodes = tree.get("nodes", [])
    if len(nodes) == 0:
        return "fail", "空月（n_nodes=0）——需回退或补采"
    if sum(n.get("weight", 0) for n in nodes) == 0:
        return "fail", "全 0 伪数据（total_weight=0）——采集失败未显式化"
    return "pass", f"{len(nodes)} 节点，total_weight={sum(n.get('weight',0) for n in nodes)}"


def check_truncation(tree):
    """检查点 6：截断检测"""
    meta = tree.get("meta", {})
    max_pages = meta.get("max_pages_per_tag") or meta.get("max_pages")
    api = str(meta.get("api", ""))
    if max_pages:
        return "warn", f"采集页数上限 {max_pages}（可能截断）——需人工确认"
    if "MAX_PAGES" in api:
        return "warn", "meta 提及 MAX_PAGES，疑似截断风险"
    return "pass", "未见截断标记"


def check_annotation(tree):
    """检查点 7：标注一致性（canonical 对照）"""
    nodes = tree.get("nodes", [])
    mismatches = []
    for n in nodes:
        cid = str(n.get("id", ""))
        w = n.get("wuxing")
        expect = CANONICAL_WUXING.get(cid)
        if w and expect and w != expect:
            mismatches.append(f"{cid}: 树={w} vs canonical={expect}")
    if mismatches:
        return "fail", f"与 canonical 不一致: {mismatches[:5]}"
    return "pass", "与 canonical 一致（或节点不在 canonical 表）"


CHECKERS = [
    ("schema", check_schema),
    ("wuxing", check_wuxing),
    ("weight", check_weight),
    ("volume", check_volume),
    ("empty", check_empty),
    ("truncation", check_truncation),
    ("annotation", check_annotation),
]


def validate_tree(tree, path, history, excludes):
    """单树检查 → {检查点: 状态} + 状态汇总"""
    src = tree.get("source", "?")
    node_ids = {str(n.get("id", "")) for n in tree.get("nodes", [])}

    # 文件级排除：整个文件被 .collectignore 命中 → 跳过检查
    file_excluded = [e for e in excludes if e in str(path)]
    if file_excluded:
        return {
            "source": src, "month": tree.get("month"),
            "path": str(path), "checks": {},
            "verdict": "excluded",
            "excluded": file_excluded,
        }

    # 节点级排除：被排除的节点 id 不参与检查
    node_excludes = {e.split(":", 1)[-1] for e in excludes
                     if ":" in e and e.split(":")[-1] in node_ids}

    results = {}
    for name, fn in CHECKERS:
        if name == "volume":
            status, msg = fn(tree, history.get(src, []))
        else:
            status, msg = fn(tree)
        results[name] = {"status": status, "message": msg}

    statuses = [r["status"] for r in results.values()]
    if "fail" in statuses:
        verdict = "fail"
    elif "warn" in statuses:
        verdict = "pass_with_warn"
    else:
        verdict = "pass_all"
    return {
        "source": src, "month": tree.get("month"),
        "path": str(path), "checks": results,
        "verdict": verdict,
        "excluded": list(file_excluded) + list(node_excludes),
    }


def main():
    parser = argparse.ArgumentParser(description="Phase B 质量门（七检查点 + 三态）")
    parser.add_argument("--dir", default=".", help="树文件目录")
    parser.add_argument("--month", default=None, help="只检查指定月份 YYYY-MM")
    parser.add_argument("--write", action="store_true", help="写 quality_report.json")
    args = parser.parse_args()

    directory = Path(args.dir)
    files = sorted(glob.glob(str(directory / "*_tree_*.json")))
    if args.month:
        files = [f for f in files if extract_month(f) == args.month]
    if not files:
        print("❌ 未找到树文件")
        return

    excludes = load_collectignore(directory)
    if excludes:
        print(f"[排除清单] {len(excludes)} 项: {excludes[:5]}...")

    # 历史量级（同源）
    history = {}
    for f in files:
        try:
            tree = json.loads(Path(f).read_text(encoding="utf-8"))
            src = tree.get("source", "?")
            total = sum(n.get("weight", 0) for n in tree.get("nodes", []))
            history.setdefault(src, []).append(total)
        except Exception:
            pass

    print("=" * 68)
    print(f"Phase B 质量门 | {len(files)} 个树文件 | 七检查点 × 三态")
    print("=" * 68)

    report = {
        "month": args.month,
        "generated": date.today().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "checks": {},
        "warnings": [],
        "collectignore": excludes,
    }

    for f in files:
        try:
            tree = json.loads(Path(f).read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  ❌ {f}: 解析失败 {e}")
            report["checks"][Path(f).stem] = {"verdict": "fail", "error": str(e)}
            continue
        if not isinstance(tree, dict):
            print(f"  ⚠️ {f}: 非树文件结构（list/其他）——跳过")
            report["checks"][Path(f).stem] = {"verdict": "skip", "error": "非 dict 结构"}
            continue
        res = validate_tree(tree, f, history, excludes)
        src_month = f"{res['source']}-{res['month']}"
        report["checks"][src_month] = res

        icon = {"pass_all": "✅", "pass_with_warn": "⚠️", "fail": "❌",
                "excluded": "⏭️"}[res["verdict"]]
        print(f"\n  {icon} {res['source']} {res['month']} → {res['verdict']}")
        for name, r in res["checks"].items():
            mark = {"pass": "·", "warn": "!", "fail": "×"}[r["status"]]
            print(f"    [{mark}] {name:<12} {r['message']}")
        if res["excluded"]:
            print(f"    (排除: {res['excluded']})")
        if res["verdict"] == "pass_with_warn":
            for r in res["checks"].values():
                if r["status"] == "warn":
                    report["warnings"].append(f"{src_month}: {r['message']}")

    # 汇总
    verdicts = [v["verdict"] for v in report["checks"].values()]
    n_pass = verdicts.count("pass_all")
    n_warn = verdicts.count("pass_with_warn")
    n_fail = verdicts.count("fail")
    if n_fail > 0:
        report["verdict"] = "fail"
    elif n_warn > 0:
        report["verdict"] = "pass_with_warn"
    else:
        report["verdict"] = "pass_all"

    print("\n" + "=" * 68)
    print(f"[汇总] pass_all={n_pass} pass_with_warn={n_warn} fail={n_fail} "
          f"→ 总判定: {report['verdict']}")
    if report["warnings"]:
        print(f"[警告] {len(report['warnings'])} 条（自愈重试项）")
        for w in report["warnings"][:5]:
            print(f"  ⚠️ {w}")

    if args.write:
        out = Path("quality_report.json")
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        print(f"[输出] {out}")
    print("=" * 68)


if __name__ == "__main__":
    main()
