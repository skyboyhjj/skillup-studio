#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""联调验证：质量门三态 → 晶体导出（契约 IF-2026-006 全链路）"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import data_validator
import export_crystals

WORK = Path(tempfile.mkdtemp(prefix="crystal_verify_"))
RESULTS = []


def check(desc, ok, detail=""):
    RESULTS.append((desc, ok))
    print(f"  {'✅' if ok else '❌'} {desc}" + (f"  [{detail}]" if detail else ""))


def make_tree(source, month, nodes):
    return {"schema_version": "1.0", "source": source, "month": month,
            "nodes": [{"id": n[0], "name": n[0], "parent": "r",
                       "wuxing": n[1], "weight": n[2]} for n in nodes]}


def write_tree(path, tree):
    Path(path).write_text(json.dumps(tree, ensure_ascii=False), encoding="utf-8")


print("=" * 72)
print("联调验证：质量门三态 → 晶体导出")
print("=" * 72)

# ---------- 场景 1：pass_with_warn → 晶体正常导出 + verified 写入 ----------
print("\n[场景 1] pass_with_warn → 导出 + verified")
d = WORK / "s1"
d.mkdir()
write_tree(d / "ai_tree_2026-07.json", make_tree("arxiv", "2026-07", [
    ("cs.LG", "土", 100), ("cs.CL", "水", 80), ("cs.AI", "火", 60)]))

# 模拟诊断 series
series = {"records": [{
    "source": "arxiv", "months": ["2026-07"], "S_p": 8.45,
    "dominant": "土", "O_t": 0.33, "E_u": 0.03, "C_k": 0.0, "K_y": 0.2,
    "v2_extra": {"dim3_profile": {"path": "土→土→土"}}}]}

# 跑质量门（单文件，volume 检查无历史 → pass；wuxing 已标注 → pass）
import subprocess, os
cwd = str(Path(__file__).resolve().parent.parent)  # 工作区根（脚本所在）
os.chdir(d)
r1 = subprocess.run([sys.executable, os.path.join(cwd, "data_validator.py"), "--dir", ".", "--write"],
                    capture_output=True, text=True)
if not Path("quality_report.json").exists():
    print("  [调试] stderr:", r1.stderr[-500:])
    print("  [调试] stdout:", r1.stdout[-300:])
    print("  [调试] 文件:", sorted(p.name for p in Path(".").iterdir()))
    raise SystemExit(1)
quality = json.loads(Path("quality_report.json").read_text(encoding="utf-8"))
check("质量门 verdict=pass_all", quality["verdict"] == "pass_all", quality["verdict"])

Path("engine_v2_series.json").write_text(json.dumps(series, ensure_ascii=False), encoding="utf-8")
r2 = subprocess.run([sys.executable, os.path.join(cwd, "export_crystals.py")], capture_output=True, text=True)
if not Path("output/crystals").exists():
    print("  [调试] export stderr:", r2.stderr[-500:])
    print("  [调试] export stdout:", r2.stdout[-300:])
    raise SystemExit(1)

crystals = Path("output/crystals")
check("晶体导出成功", crystals.exists() and (crystals / "diagnostics/arxiv.md").exists())
crystal = (crystals / "diagnostics/arxiv.md").read_text(encoding="utf-8")
check("verified 由质量门写入", "verified: { by: process:quality-gate" in crystal)
check("引用不复制", "engine_v2_series.json#arxiv" in crystal)
check("x-wuxing 完整", "dominant: 土" in crystal and "sp: 8.45" in crystal)

os.chdir(cwd)

# ---------- 场景 2：fail → 阻断导出 ----------
print("\n[场景 2] fail → 阻断导出（契约守卫）")
d2 = WORK / "s2"
d2.mkdir()
write_tree(d2 / "ai_tree_2026-07.json", make_tree("arxiv", "2026-07", []))  # 空月 → fail
os.chdir(d2)
subprocess.run([sys.executable, os.path.join(cwd, "data_validator.py"), "--dir", ".", "--write"],
               capture_output=True)
quality2 = json.loads(Path("quality_report.json").read_text(encoding="utf-8"))
check("空月被识别 fail", quality2["verdict"] == "fail", quality2["verdict"])

Path("engine_v2_series.json").write_text(json.dumps(series, ensure_ascii=False), encoding="utf-8")
r = subprocess.run([sys.executable, os.path.join(cwd, "export_crystals.py")],
                   capture_output=True, text=True)
check("fail 阻断导出（exit 无晶体）",
      "阻断晶体导出" in r.stdout and not Path("output/crystals").exists(),
      r.stdout.strip().splitlines()[-2] if r.stdout.strip() else "")
os.chdir(cwd)

# ---------- 汇总 ----------
print("\n" + "=" * 72)
passed = sum(1 for _, ok in RESULTS if ok)
print(f"[汇总] {passed}/{len(RESULTS)} 通过")
for desc, ok in RESULTS:
    if not ok:
        print(f"  ❌ FAILED: {desc}")
print("=" * 72)
shutil.rmtree(WORK, ignore_errors=True)
sys.exit(0 if passed == len(RESULTS) else 1)
