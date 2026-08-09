#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pipeline_orchestrator.py —— 四源并行采集调度器（Phase A）
===========================================================
对齐《统一数据运营与展示设计》Phase A 规格：

  - 四源并行：ThreadPoolExecutor(max_workers=4)（网络 IO 密集）
  - 重试：网络错误指数退避 3 次（1s/2s/4s），退出码非零或输出缺失即重试
  - 超时：每源硬超时 15 分钟（900s），超时标记 failed(timeout)
  - 幂等：同月输出文件已存在且非空 → skip（--force 覆盖）
  - 状态机：pending → running → success / failed(原因) / skipped
  - 源级容错：单源失败不阻断其他源
  - 运行日志：output/runs/run_YYYYMMDD_HHMMSS.json（可审计）
  - 断点续跑：--resume 只重跑最近一次运行的 failed 源
  - 触发：手动 / --month 补采 / --source 单源 / 定时（cron 调本脚本）

用法：
  python pipeline_orchestrator.py                       # 全源，默认最近月
  python pipeline_orchestrator.py --month 2026-08       # 指定月份
  python pipeline_orchestrator.py --source arxiv        # 单源
  python pipeline_orchestrator.py --resume              # 断点续跑（failed 源）
  python pipeline_orchestrator.py --force               # 强制覆盖已存在输出
  python pipeline_orchestrator.py --dry-run             # 只输出计划不执行

零依赖：标准库（subprocess/threading/concurrent.futures）
"""

import argparse
import concurrent.futures
import json
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# ============ 配置 ============
DEFAULT_TIMEOUT_S = 900          # 每源硬超时 15 分钟
RETRY_ATTEMPTS = 3               # 重试次数（含首次）
RETRY_BACKOFF = [1, 2, 4]        # 指数退避（秒）
RUNS_DIR = Path("../output/runs")   # 运行日志目录（相对 scripts/）

# ============ 源注册表 ============
@dataclass
class SourceSpec:
    """采集源规格：命令模板 + 输出模式"""
    name: str
    cmd: list                    # 命令模板，[0] 为解释器/脚本
    output_glob: str             # 输出文件 glob（用于幂等检查）
    timeout: int = DEFAULT_TIMEOUT_S
    enabled: bool = True


# 生产侧四源注册表（命令路径可经 --dir 覆盖）
def build_sources(script_dir: str = ".") -> dict:
    """构建源注册表——对齐生产管线 docs/ + scripts/ 布局

    脚本缺失的源自动 enabled=False（如本地无 baai_scraper.py 时 baai 禁用），
    避免 run 时 FileNotFoundError 噪声。
    """
    d = Path(script_dir)
    specs = {
        "arxiv": SourceSpec("arxiv", [sys.executable, str(d / "arxiv_ai_collect.py")],
                            "arxiv_ai_tree_*.json"),
        "baai": SourceSpec("baai", [sys.executable, str(d / "baai_scraper.py")],
                           "baai_tree_*.json"),
        "github": SourceSpec("github", [sys.executable, str(d / "github_collect.py")],
                             "github_tree_*.json"),
        "huggingface": SourceSpec("huggingface", [sys.executable, str(d / "hf_collect.py")],
                                  "hf_tree_*.json"),
    }
    for name, spec in specs.items():
        script = spec.cmd[-1]
        if not Path(script).exists():
            spec.enabled = False
            print(f"  ⚠️ [{name}] 脚本缺失，已禁用: {script}")
    return specs


# ============ 状态机 ============
PENDING, RUNNING, SUCCESS, FAILED, SKIPPED, TIMEOUT = (
    "pending", "running", "success", "failed", "skipped", "timeout"
)


# ============ 调度器 ============
class PipelineOrchestrator:
    def __init__(self, sources: dict, workdir: Path = None,
                 runs_dir: Path = RUNS_DIR):
        self.sources = sources
        self.workdir = Path(workdir) if workdir else Path.cwd()
        self.runs_dir = Path(runs_dir)

    # ---------- 运行日志 ----------
    def _new_run_id(self) -> str:
        return datetime.now().strftime("run_%Y%m%d_%H%M%S")

    def _save_run(self, run: dict):
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        path = self.runs_dir / f"{run['run_id']}.json"
        path.write_text(json.dumps(run, ensure_ascii=False, indent=2),
                        encoding="utf-8")
        return path

    def _latest_run(self) -> dict:
        """读取最近一次运行（断点续跑用）"""
        if not self.runs_dir.exists():
            return None
        runs = sorted(self.runs_dir.glob("run_*.json"))
        if not runs:
            return None
        return json.loads(runs[-1].read_text(encoding="utf-8"))

    # ---------- 幂等检查 ----------
    def _output_exists(self, spec: SourceSpec, month: str) -> bool:
        """同月输出文件已存在且非空 → 幂等跳过"""
        pattern = spec.output_glob.replace("*", f"*{month.replace('-', '')}*")
        # 也兼容带 '-' 的月份（如 2026-08 → ai_tree_2026-08.json）
        hits = list(self.workdir.glob(pattern))
        hits += list(self.workdir.glob(
            spec.output_glob.replace("*", f"*{month.replace('-', '-')}*")))
        for h in hits:
            if h.stat().st_size > 0:
                return True
        return False

    # ---------- 单源执行（含重试） ----------
    def _run_source(self, spec: SourceSpec, month: str, force: bool) -> dict:
        """执行单源采集：pending → running → success/failed，带重试"""
        status = {"status": PENDING, "attempts": 0, "elapsed_s": 0.0,
                  "error": None, "output": None}

        # 幂等
        if not force and self._output_exists(spec, month):
            status["status"] = SKIPPED
            status["note"] = f"输出已存在（{spec.output_glob}）——幂等跳过，--force 覆盖"
            return status

        cmd = spec.cmd + ["--month", month]
        for attempt in range(RETRY_ATTEMPTS):
            status["attempts"] = attempt + 1
            status["status"] = RUNNING
            t0 = time.time()
            try:
                proc = subprocess.run(
                    cmd, cwd=str(self.workdir), capture_output=True, text=True,
                    timeout=spec.timeout,
                )
                elapsed = time.time() - t0
                status["elapsed_s"] = round(elapsed, 1)

                if proc.returncode != 0:
                    err = f"exit={proc.returncode}: {proc.stderr.strip()[-300:]}"
                    status["error"] = err
                    status["status"] = FAILED
                elif not self._output_exists(spec, month):
                    # 退出码 0 但输出缺失——同样视为失败（采集器空跑）
                    err = "exit=0 但输出文件缺失（可能空月或脚本 bug）"
                    status["error"] = err
                    status["status"] = FAILED
                else:
                    status["status"] = SUCCESS
                    status["output"] = self._find_output(spec, month)
                    status.pop("error", None)
                    return status
            except subprocess.TimeoutExpired:
                status["elapsed_s"] = round(time.time() - t0, 1)
                status["error"] = f"timeout>{spec.timeout}s"
                status["status"] = TIMEOUT
                break  # 超时不重试（大概率持续超时）
            except Exception as e:
                status["error"] = f"{type(e).__name__}: {e}"
                status["status"] = FAILED

            # 退避后重试（最后一次不等待）
            if attempt < RETRY_ATTEMPTS - 1:
                time.sleep(RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)])

        return status

    def _find_output(self, spec: SourceSpec, month: str) -> str:
        pattern = spec.output_glob.replace("*", f"*{month}*")
        hits = list(self.workdir.glob(pattern))
        return str(hits[0]) if hits else None

    # ---------- 主流程 ----------
    def run(self, month: str, sources: list = None, force: bool = False,
            resume: bool = False, dry_run: bool = False) -> dict:
        """调度主入口"""
        targets = {k: v for k, v in self.sources.items()
                   if v.enabled and (sources is None or k in sources)}
        if not targets:
            print("❌ 无可用源（检查注册表）")
            return {}

        run = {
            "run_id": self._new_run_id(),
            "trigger": "resume" if resume else "manual",
            "month": month,
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "dry_run": dry_run,
            "sources": {},
            "summary": {"success": 0, "failed": 0, "skipped": 0, "timeout": 0},
        }

        # 断点续跑：只取上次 failed/timeout 源
        if resume:
            prev = self._latest_run()
            if prev and prev.get("month") == month:
                failed = [k for k, s in prev["sources"].items()
                          if s["status"] in (FAILED, TIMEOUT)]
                if failed:
                    targets = {k: v for k, v in targets.items() if k in failed}
                    print(f"  [resume] 重跑失败源: {failed}")
                else:
                    print("  [resume] 上次运行无失败源——无需续跑")
                    run["summary"]["skipped"] = len(targets)
                    for k in targets:
                        run["sources"][k] = {"status": SKIPPED, "note": "resume: 无失败"}
                    return self._finish(run)
            else:
                print("  ⚠️ 无匹配月份的上次运行——按全量执行")

        print(f"\n[调度] {month} 月 · {'dry-run' if dry_run else '并行'} · "
              f"源={list(targets.keys())}")

        # dry-run：只输出计划
        if dry_run:
            for name, spec in targets.items():
                exists = self._output_exists(spec, month)
                print(f"  - {name:<12} 输出{'已存在(skip)' if exists else '将采集'} "
                      f"cmd={' '.join(spec.cmd)} --month {month}")
            run["sources"] = {k: {"status": "planned"} for k in targets}
            return self._finish(run)

        # 四源并行（线程池）
        t0 = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            futures = {pool.submit(self._run_source, spec, month, force): name
                       for name, spec in targets.items()}
            for fut in concurrent.futures.as_completed(futures):
                name = futures[fut]
                try:
                    st = fut.result()
                except Exception as e:
                    st = {"status": FAILED, "error": f"{type(e).__name__}: {e}"}
                run["sources"][name] = st
                self._print_status(name, st)

        run["elapsed_total_s"] = round(time.time() - t0, 1)
        return self._finish(run)

    def _print_status(self, name: str, st: dict):
        icon = {"success": "✅", "failed": "❌", "skipped": "⏭️", "timeout": "⏱️",
                "pending": "⏳", "running": "▶️"}.get(st["status"], "?")
        line = f"  {icon} {name:<12} {st['status']}"
        if st.get("elapsed_s"):
            line += f"  {st['elapsed_s']}s"
        if st.get("error"):
            line += f"  {st['error'][:120]}"
        if st.get("note"):
            line += f"  {st['note'][:120]}"
        print(line)

    def _finish(self, run: dict) -> dict:
        """汇总 + 落盘运行日志"""
        for st in run["sources"].values():
            s = st["status"]
            if s in run["summary"]:
                run["summary"][s] += 1
        run["finished_at"] = datetime.now().isoformat(timespec="seconds")
        path = self._save_run(run)
        print(f"\n[汇总] success={run['summary']['success']} "
              f"failed={run['summary']['failed']} "
              f"skipped={run['summary']['skipped']} "
              f"timeout={run['summary']['timeout']}")
        print(f"[日志] {path}")
        return run


# ============ 主流程 ============
def main():
    parser = argparse.ArgumentParser(description="四源并行采集调度器（Phase A）")
    parser.add_argument("--month", default=None, help="采集月份 YYYY-MM（默认最近完整月）")
    parser.add_argument("--source", action="append", help="指定源（可多次，如 --source arxiv）")
    parser.add_argument("--dir", default=".", help="采集脚本目录（默认当前 scripts/）")
    parser.add_argument("--out", default="../output", help="输出目录（树文件位置，默认 ../output/）")
    parser.add_argument("--force", action="store_true", help="覆盖已存在输出")
    parser.add_argument("--resume", action="store_true", help="断点续跑（重跑上次 failed 源）")
    parser.add_argument("--dry-run", action="store_true", help="只输出计划不执行")
    args = parser.parse_args()

    print("=" * 68)
    print("pipeline_orchestrator —— 四源并行采集调度器（Phase A）")
    print("=" * 68)

    # 默认月份：最近完整月（上个月）
    if not args.month:
        now = datetime.now()
        if now.month == 1:
            args.month = f"{now.year - 1}-12"
        else:
            args.month = f"{now.year}-{now.month - 1:02d}"
        print(f"[默认月份] 最近完整月: {args.month}")

    sources = build_sources(args.dir)
    orch = PipelineOrchestrator(sources, workdir=Path(args.out))
    orch.run(args.month, sources=args.source, force=args.force,
             resume=args.resume, dry_run=args.dry_run)
    print("=" * 68)


if __name__ == "__main__":
    main()
