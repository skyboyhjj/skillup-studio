#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pipeline_orchestrator 单元验证：并行/重试/失败隔离/幂等/断点续跑/超时/dry-run"""
import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline_orchestrator import PipelineOrchestrator, SourceSpec, RUNS_DIR

WORK = Path("/sandbox/workspace/verify/workspace")
MOCK = Path("/sandbox/workspace/verify/mock_collector.py")
RESULTS = []


def check(desc, ok, detail=""):
    RESULTS.append((desc, ok))
    print(f"  {'✅' if ok else '❌'} {desc}" + (f"  [{detail}]" if detail else ""))


def fresh_workspace():
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)
    (WORK / "output/runs").mkdir(parents=True)
    # 清理 mock 标记
    for f in Path("/sandbox/workspace/verify").glob(".mock_attempt_*"):
        f.unlink()


def mk(orch, workdir):
    return orch


print("=" * 72)
print("Phase A 调度器单元验证")
print("=" * 72)

# ---------- 用例 1：并行 + 失败隔离 ----------
print("\n[用例 1] 四源并行 + 源级容错（baai 失败不阻断其他源）")
fresh_workspace()
sources = {
    "arxiv": SourceSpec("arxiv", [sys.executable, str(MOCK), "--source", "arxiv"], "arxiv_tree_*.json", timeout=60),
    "baai": SourceSpec("baai", [sys.executable, str(MOCK), "--source", "baai", "--fail"], "baai_tree_*.json", timeout=60),
    "github": SourceSpec("github", [sys.executable, str(MOCK), "--source", "github", "--delay", "2"], "github_tree_*.json", timeout=60),
    "huggingface": SourceSpec("huggingface", [sys.executable, str(MOCK), "--source", "huggingface"], "hf_tree_*.json", timeout=60),
}
orch = PipelineOrchestrator(sources, workdir=WORK, runs_dir=WORK / "output/runs")
t0 = time.time()
run1 = orch.run("2026-08")
elapsed = time.time() - t0

check("四源并行总耗时 < 串行和（github delay 2s，总耗时应 < 8s）",
      elapsed < 8, f"elapsed={elapsed:.1f}s")
check("arxiv success", run1["sources"]["arxiv"]["status"] == "success")
check("baai failed（源级容错）", run1["sources"]["baai"]["status"] == "failed")
check("github success（不受 baai 失败影响）", run1["sources"]["github"]["status"] == "success")
check("huggingface success", run1["sources"]["huggingface"]["status"] == "success")
check("汇总 success=3 failed=1", run1["summary"]["success"] == 3 and run1["summary"]["failed"] == 1)
check("运行日志已落盘", (WORK / f"output/runs/{run1['run_id']}.json").exists())
# 验证运行日志内容
log = json.loads((WORK / f"output/runs/{run1['run_id']}.json").read_text(encoding="utf-8"))
check("日志含 run_id/month/trigger/sources", all(k in log for k in ["run_id", "month", "trigger", "sources", "summary"]))

# ---------- 用例 2：幂等跳过 ----------
print("\n[用例 2] 幂等：同月输出已存在 → skip（失败源无输出则重试）")
run2 = orch.run("2026-08")
check("arxiv/github/hf skipped（有输出）",
      run2["sources"]["arxiv"]["status"] == "skipped" and
      run2["sources"]["github"]["status"] == "skipped" and
      run2["sources"]["huggingface"]["status"] == "skipped")
check("baai 无输出→重试仍 failed", run2["sources"]["baai"]["status"] == "failed")
check("汇总 skipped=3 failed=1", run2["summary"]["skipped"] == 3 and run2["summary"]["failed"] == 1)

# ---------- 用例 3：--force 覆盖 ----------
print("\n[用例 3] --force 强制重跑")
run3 = orch.run("2026-08", force=True)
check("force 后 baai 仍 failed、其余 success", 
      run3["sources"]["baai"]["status"] == "failed" and
      run3["sources"]["arxiv"]["status"] == "success")

# ---------- 用例 4：重试（前 2 次失败第 3 次成功） ----------
print("\n[用例 4] 指数退避重试（fail-first=2 → attempts=3 成功）")
fresh_workspace()
sources_retry = {
    "arxiv": SourceSpec("arxiv", [sys.executable, str(MOCK), "--source", "arxiv", "--fail-first", "2"], "arxiv_tree_*.json", timeout=60),
    "github": SourceSpec("github", [sys.executable, str(MOCK), "--source", "github"], "github_tree_*.json", timeout=60),
}
orch2 = PipelineOrchestrator(sources_retry, workdir=WORK, runs_dir=WORK / "output/runs")
t0 = time.time()
run4 = orch2.run("2026-07")
elapsed4 = time.time() - t0
check("arxiv 重试 3 次后 success", run4["sources"]["arxiv"]["status"] == "success")
check("arxiv attempts=3", run4["sources"]["arxiv"]["attempts"] == 3)
check("退避耗时 ≥ 1+2=3s", elapsed4 >= 3, f"elapsed={elapsed4:.1f}s")
check("github 不受影响 success", run4["sources"]["github"]["status"] == "success")

# ---------- 用例 5：超时 ----------
print("\n[用例 5] 硬超时（timeout=2s，mock delay=10s）")
fresh_workspace()
sources_to = {
    "arxiv": SourceSpec("arxiv", [sys.executable, str(MOCK), "--source", "arxiv", "--delay", "10"], "arxiv_tree_*.json", timeout=2),
}
orch3 = PipelineOrchestrator(sources_to, workdir=WORK, runs_dir=WORK / "output/runs")
run5 = orch3.run("2026-07")
check("timeout 状态", run5["sources"]["arxiv"]["status"] == "timeout")
check("timeout 错误信息", "timeout" in (run5["sources"]["arxiv"]["error"] or ""))

# ---------- 用例 6：断点续跑 ----------
print("\n[用例 6] --resume 只重跑 failed 源")
fresh_workspace()
sources_resume = {
    "arxiv": SourceSpec("arxiv", [sys.executable, str(MOCK), "--source", "arxiv"], "arxiv_tree_*.json", timeout=60),
    "baai": SourceSpec("baai", [sys.executable, str(MOCK), "--source", "baai", "--fail"], "baai_tree_*.json", timeout=60),
    "github": SourceSpec("github", [sys.executable, str(MOCK), "--source", "github"], "github_tree_*.json", timeout=60),
}
orch4 = PipelineOrchestrator(sources_resume, workdir=WORK, runs_dir=WORK / "output/runs")
run6a = orch4.run("2026-06")
check("首次运行 baai failed", run6a["sources"]["baai"]["status"] == "failed")

# 修复 baai（去掉 --fail）后 resume
sources_resume["baai"] = SourceSpec("baai", [sys.executable, str(MOCK), "--source", "baai"], "baai_tree_*.json", timeout=60)
orch5 = PipelineOrchestrator(sources_resume, workdir=WORK, runs_dir=WORK / "output/runs")
run6b = orch5.run("2026-06", resume=True)
check("resume 只跑 baai（sources 仅含 baai）",
      list(run6b["sources"].keys()) == ["baai"] and
      run6b["sources"]["baai"]["status"] == "success")

# ---------- 用例 7：dry-run ----------
print("\n[用例 7] dry-run 只输出计划")
fresh_workspace()
run7 = orch4.run("2026-08", dry_run=True)
check("dry-run 全部 planned", all(s["status"] == "planned" for s in run7["sources"].values()))
check("dry-run 不产生输出文件", not list(WORK.glob("*_tree_*.json")))

# ---------- 用例 8：空跑检测 ----------
print("\n[用例 8] exit=0 但输出缺失 → failed")
fresh_workspace()
sources_empty = {
    "arxiv": SourceSpec("arxiv", [sys.executable, str(MOCK), "--source", "arxiv", "--empty"], "arxiv_tree_*.json", timeout=60),
}
orch6 = PipelineOrchestrator(sources_empty, workdir=WORK, runs_dir=WORK / "output/runs")
run8 = orch6.run("2026-07")
check("空跑识别为 failed", run8["sources"]["arxiv"]["status"] == "failed")
check("空跑错误信息含'输出文件缺失'", "输出文件缺失" in (run8["sources"]["arxiv"]["error"] or ""))

# ---------- 汇总 ----------
print("\n" + "=" * 72)
passed = sum(1 for _, ok in RESULTS if ok)
print(f"[汇总] {passed}/{len(RESULTS)} 通过")
for desc, ok in RESULTS:
    if not ok:
        print(f"  ❌ FAILED: {desc}")
print("=" * 72)
sys.exit(0 if passed == len(RESULTS) else 1)
