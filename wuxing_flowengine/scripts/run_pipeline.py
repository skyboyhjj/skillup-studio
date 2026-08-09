"""
统一管线入口 —— 采集→质量门→诊断→打包→仪表盘

基于《统一数据运营与展示设计》Phase D 规格：
  一键触发全链路，阶段级容错，可审计运行日志

管线阶段:
  1. 采集 (pipeline_orchestrator.py)             —— 四源并行月度快照
  2. 标注版本统一 (unify_annotation_version.py)  —— 确保 meta.annotation_version = v2
  3. 质量门 (quality_gate.py)                     —— 七检查点质量报告
  4. 诊断 (engine_adapter_v2.py)                  —— 真实引擎四维诊断
  5. 壳核分析 (shell_nucleus_analysis_v2.py)      —— 壳核收敛 + 四层水梯度
  6. 仪表盘打包 (build_dashboard_data.py)          —— 统一 JSON 数据接口
  7. 前端部署                                   —— 复制到 hui-skill-product-matrix/data/

用法:
    python run_pipeline.py                          # 全链路，默认最近月
    python run_pipeline.py --month 2026-07          # 指定月份
    python run_pipeline.py --skip-collect           # 跳过采集（已有数据）
    python run_pipeline.py --from quality           # 从质量门开始
    python run_pipeline.py --dry-run                # 只输出计划不执行
"""

import argparse
import json
import os
import subprocess
import sys
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional


# ============================================================
# 路径配置
# ============================================================

SCRIPTS_DIR = Path(__file__).parent.resolve()
PROJECT_DIR = SCRIPTS_DIR.parent.resolve()
OUTPUT_DIR = PROJECT_DIR / "output"
DIAGNOSE_DIR = PROJECT_DIR / "diagnose"
FRONTEND_DATA_DIR = PROJECT_DIR.parent / "hui-skill-product-matrix" / "data"
FRONTEND_PAGES_DIR = PROJECT_DIR.parent / "hui-skill-product-matrix" / "pages"
RUNS_DIR = OUTPUT_DIR / "runs"

# 可执行脚本
PIPELINE_ORCH = SCRIPTS_DIR / "pipeline_orchestrator.py"
UNIFY_VERSION = SCRIPTS_DIR / "unify_annotation_version.py"
QUALITY_GATE = SCRIPTS_DIR / "quality_gate.py"
ENGINE_ADAPTER = DIAGNOSE_DIR / "engine_adapter_v2.py"
SHELL_NUCLEUS = SCRIPTS_DIR / "shell_nucleus_analysis_v2.py"
BUILD_DASHBOARD = SCRIPTS_DIR / "build_dashboard_data.py"

PYTHON = sys.executable


# ============================================================
# 阶段执行器
# ============================================================

class StageResult:
    """阶段执行结果"""
    def __init__(self, name: str, success: bool, output: str = "", error: str = "",
                 elapsed_s: float = 0, artifacts: list = None):
        self.name = name
        self.success = success
        self.output = output
        self.error = error
        self.elapsed_s = elapsed_s
        self.artifacts = artifacts or []


def run_stage(name: str, cmd: list, cwd: str = None, timeout: int = 900) -> StageResult:
    """执行一个管线阶段，捕获输出和错误"""
    import time
    t0 = time.time()
    cwd = cwd or str(SCRIPTS_DIR)

    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace"
        )
        elapsed = time.time() - t0
        if result.returncode == 0:
            return StageResult(name, True, output=result.stdout, elapsed_s=elapsed)
        else:
            err = result.stderr or result.stdout or f"exit code {result.returncode}"
            return StageResult(name, False, output=result.stdout, error=err, elapsed_s=elapsed)
    except subprocess.TimeoutExpired:
        elapsed = time.time() - t0
        return StageResult(name, False, error=f"超时（>{timeout}s）", elapsed_s=elapsed)
    except Exception as e:
        elapsed = time.time() - t0
        return StageResult(name, False, error=str(e), elapsed_s=elapsed)


def print_stage_header(name: str, num: int, total: int):
    """打印阶段标题"""
    print(f"\n{'─' * 60}")
    print(f"[{num}/{total}] {name}")
    print(f"{'─' * 60}")


def print_stage_result(result: StageResult):
    """打印阶段结果"""
    icon = "✓" if result.success else "❌"
    print(f"  {icon} 耗时 {result.elapsed_s:.1f}s")
    if result.output:
        # 只打印最后几行摘要
        lines = result.output.strip().split("\n")
        summary = lines[-5:] if len(lines) > 5 else lines
        for line in summary:
            if line.strip():
                print(f"    {line.strip()}")
    if result.error:
        print(f"  错误: {result.error[:200]}")


# ============================================================
# 管线编排
# ============================================================

def run_full_pipeline(month: str = None,
                      skip_collect: bool = False,
                      start_from: str = None,
                      dry_run: bool = False) -> dict:
    """
    执行完整管线。

    Args:
        month: 月份 YYYY-MM（默认最近完整月）
        skip_collect: 跳过采集阶段
        start_from: 从指定阶段开始（collect/quality/diagnose/shell/dashboard/deploy）
        dry_run: 只打印计划不执行

    Returns:
        {"run_id": str, "month": str, "stages": [StageResult], "verdict": str}
    """
    if month is None:
        now = datetime.now()
        month = f"{now.year}-{now.month - 1:02d}" if now.month > 1 else f"{now.year - 1}-12"

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    RUNS_DIR.mkdir(parents=True, exist_ok=True)

    # 阶段列表
    stages_def = [
        ("collect", "采集（四源并行）",
         [PYTHON, str(PIPELINE_ORCH), "--month", month]),
        ("unify", "标注版本统一",
         [PYTHON, str(UNIFY_VERSION)]),
        ("quality", "质量门（七检查点）",
         [PYTHON, str(QUALITY_GATE), "--month", month]),
        ("diagnose", "诊断（真实引擎）",
         [PYTHON, str(ENGINE_ADAPTER), "--dir", str(OUTPUT_DIR)]),
        ("shell", "壳核分析",
         [PYTHON, str(SHELL_NUCLEUS)]),
        ("dashboard", "仪表盘打包",
         [PYTHON, str(BUILD_DASHBOARD)]),
        ("deploy", "前端部署",
         None),  # 特殊处理：复制文件
    ]

    # 确定起始阶段
    start_idx = 0
    if start_from:
        for i, (key, _, _) in enumerate(stages_def):
            if key == start_from:
                start_idx = i
                break

    if skip_collect:
        start_idx = max(start_idx, 1)

    stages_to_run = stages_def[start_idx:]

    print(f"\n{'=' * 60}")
    print(f"  统一管线 — 知识树追踪引擎")
    print(f"  月份: {month}  |  运行 ID: {run_id}")
    print(f"  阶段: {' → '.join(k for k, _, _ in stages_to_run)}")
    if dry_run:
        print(f"  [DRY RUN — 仅预览，不执行]")
    print(f"{'=' * 60}")

    if dry_run:
        return {"run_id": run_id, "month": month, "stages": [], "verdict": "dry_run"}

    results = []
    total = len(stages_to_run)

    for i, (key, name, cmd) in enumerate(stages_to_run):
        print_stage_header(name, i + 1, total)

        if key == "deploy":
            # 特殊阶段：复制文件到前端
            result = deploy_to_frontend()
        else:
            result = run_stage(key, cmd)

        print_stage_result(result)
        results.append(result)

        # 关键阶段失败则终止
        if not result.success and key in ("collect", "quality", "diagnose"):
            print(f"\n  ⚠ 关键阶段 [{key}] 失败，管线终止")
            break

    # 生成运行日志
    all_success = all(r.success for r in results)
    verdict = "✓ 全链路通过" if all_success else "⚠ 部分阶段失败"

    run_log = {
        "run_id": run_id,
        "month": month,
        "trigger": "manual",
        "started_at": datetime.now().isoformat(),
        "verdict": verdict,
        "stages": [
            {
                "name": r.name,
                "success": r.success,
                "elapsed_s": round(r.elapsed_s, 1),
                "error": r.error[:200] if r.error else None,
                "artifacts": r.artifacts
            }
            for r in results
        ]
    }

    log_path = RUNS_DIR / f"pipeline_{run_id}.json"
    log_path.write_text(json.dumps(run_log, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{'=' * 60}")
    print(f"  管线完成: {verdict}")
    print(f"  运行日志: {log_path}")
    print(f"{'=' * 60}")

    return run_log


def deploy_to_frontend() -> StageResult:
    """部署：复制 dashboard_data.json 到前端数据目录"""
    import time
    t0 = time.time()

    src = OUTPUT_DIR / "dashboard_data.json"
    if not src.exists():
        return StageResult("deploy", False, error=f"源文件不存在: {src}")

    FRONTEND_DATA_DIR.mkdir(parents=True, exist_ok=True)
    dst = FRONTEND_DATA_DIR / "dashboard_data.json"

    try:
        shutil.copy2(src, dst)
        elapsed = time.time() - t0

        # 验证 tracker.html 存在
        tracker = FRONTEND_PAGES_DIR / "tracker.html"
        tracker_ok = tracker.exists()

        return StageResult(
            "deploy", True,
            output=f"dashboard_data.json → {dst}\n"
                   f"tracker.html: {'✓ 已就绪' if tracker_ok else '⚠ 未找到'}",
            elapsed_s=elapsed,
            artifacts=[str(dst)]
        )
    except Exception as e:
        elapsed = time.time() - t0
        return StageResult("deploy", False, error=str(e), elapsed_s=elapsed)


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="统一管线入口 — 采集→质量门→诊断→打包→仪表盘",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run_pipeline.py                          # 全链路，默认最近月
  python run_pipeline.py --month 2026-07          # 指定月份
  python run_pipeline.py --skip-collect           # 跳过采集（已有数据）
  python run_pipeline.py --from quality           # 从质量门开始
  python run_pipeline.py --dry-run                # 只输出计划
        """
    )
    parser.add_argument("--month", default=None,
                        help="月份 YYYY-MM（默认最近完整月）")
    parser.add_argument("--skip-collect", action="store_true",
                        help="跳过采集阶段（已有树文件）")
    parser.add_argument("--from", dest="start_from", default=None,
                        choices=["collect", "unify", "quality", "diagnose", "shell", "dashboard", "deploy"],
                        help="从指定阶段开始")
    parser.add_argument("--dry-run", action="store_true",
                        help="只输出计划不执行")
    parser.add_argument("--json", action="store_true",
                        help="JSON 格式输出运行日志")

    args = parser.parse_args()

    run_log = run_full_pipeline(
        month=args.month,
        skip_collect=args.skip_collect,
        start_from=args.start_from,
        dry_run=args.dry_run
    )

    if args.json:
        print(json.dumps(run_log, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()