#!/usr/bin/env python3
"""
月度自动追踪流水线编排器
每月 3 日自动运行：数据验证 → Phase 1 → Phase 2 → Phase 3+ → 时间序列 → 报告

用法:
  python monthly_pipeline.py                        # 使用默认配置
  python monthly_pipeline.py --month 2026-08         # 指定月份
  python monthly_pipeline.py --base-dir /path/to/wuxing_flowengine
"""
import json, os, sys, argparse
from datetime import datetime, timedelta


def load_config(base_dir):
    """加载流水线配置"""
    config_path = os.path.join(base_dir, "config", "pipeline_config.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def get_latest_snapshot(base_dir):
    """获取最新的快照文件路径"""
    snap_dir = os.path.join(base_dir, "data", "snapshots")
    if not os.path.exists(snap_dir):
        return None
    snap_files = sorted([f for f in os.listdir(snap_dir) if f.endswith("_snapshot.json")], reverse=True)
    return os.path.join(snap_dir, snap_files[0]) if snap_files else None


def get_previous_month_label(month_label):
    """计算上个月标签，如 '2026-07' -> '2026-06'"""
    try:
        y, m = month_label.split("-")
        dt = datetime(int(y), int(m), 1) - timedelta(days=1)
        return dt.strftime("%Y-%m")
    except:
        return None


def find_previous_paper_titles(base_dir, prev_label):
    """查找上月论文标题文件"""
    candidates = [
        os.path.join(base_dir, "output", f"papers_{prev_label}.json"),
        os.path.join(base_dir, "output", f"phase3_paper_titles_{prev_label}.json"),
        os.path.join(base_dir, "output", "phase3_paper_titles.json"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def find_previous_diag(base_dir, prev_label):
    """查找上月诊断结果"""
    candidates = [
        os.path.join(base_dir, "output", f"phase3_plus_diagnosis_{prev_label}.json"),
        os.path.join(base_dir, "output", "phase3_plus_diagnosis.json"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def run_pipeline(base_dir, month_label=None, skip_collection=False, skip_validation=False):
    """
    运行完整的月度跟踪流水线。

    参数:
        base_dir:        项目根目录
        month_label:     目标月份标签（如 "2026-08"，默认当前月）
        skip_collection: 跳过数据采集（使用已有数据）
        skip_validation: 跳过数据验证

    返回:
        {"status": "ok", "phases": {...}, "summary": {...}}
    """
    if month_label is None:
        month_label = datetime.now().strftime("%Y-%m")

    config = load_config(base_dir)
    output_dir = os.path.join(base_dir, "output")
    archive_dir = os.path.join(output_dir, "archive", month_label)
    os.makedirs(archive_dir, exist_ok=True)

    # 将 scripts 目录加入 sys.path
    scripts_dir = os.path.join(base_dir, "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    print("=" * 80)
    print(f"  月度自动追踪流水线 — {month_label}")
    print(f"  项目: {base_dir}")
    print(f"  时间: {datetime.now().isoformat()}")
    print("=" * 80)

    snapshot_path = get_latest_snapshot(base_dir)
    paper_titles_path = os.path.join(output_dir, f"papers_{month_label}.json")
    # 如果不存在，回退到已有的 paper_titles 文件
    if not os.path.exists(paper_titles_path):
        for alt in [
            os.path.join(output_dir, "phase3_paper_titles.json"),
            os.path.join(output_dir, f"phase3_paper_titles_{month_label}.json"),
        ]:
            if os.path.exists(alt):
                paper_titles_path = alt
                break
    phases = {}

    # ── Step 0: 数据验证 ──
    if not skip_validation:
        print("\n" + "-" * 60)
        print("  [Step 0] 数据质量验证")
        print("-" * 60)

        from validator import validate_all as validate_all_func

        if snapshot_path and os.path.exists(snapshot_path):
            with open(snapshot_path, "r", encoding="utf-8") as f:
                snapshot = json.load(f)

            if os.path.exists(paper_titles_path):
                with open(paper_titles_path, "r", encoding="utf-8") as f:
                    paper_titles = json.load(f)
            else:
                # 尝试找最新的 paper_titles
                alt_paths = [
                    os.path.join(output_dir, "phase3_paper_titles.json"),
                    os.path.join(output_dir, f"phase3_paper_titles_{month_label}.json"),
                ]
                paper_titles = {}
                for p in alt_paths:
                    if os.path.exists(p):
                        with open(p, "r", encoding="utf-8") as f:
                            paper_titles = json.load(f)
                        break

            thresholds = config.get("thresholds", {})
            validation_result = validate_all_func(snapshot, paper_titles, output_dir, month_label, thresholds)
            phases["validation"] = {"passed": validation_result["passed"]}

            if not validation_result["passed"]:
                print("\n  ⚠ 数据验证未通过，但继续执行分析...")
        else:
            print(f"  ⚠ 快照文件不存在: {snapshot_path}")
            print("  跳过验证，继续执行分析...")
            phases["validation"] = {"passed": False, "warning": "快照缺失"}

    # ── Step 1: Phase 1 静态诊断 ──
    print("\n" + "-" * 60)
    print("  [Step 1] Phase 1: 静态诊断")
    print("-" * 60)

    from phase1_pipeline import run as run_phase1

    p1_config = config.get("phase1", {})
    p1_result = run_phase1(
        base_dir=base_dir,
        nodes_path=snapshot_path,
        output_dir=output_dir,
        month_label=month_label,
        config_path=p1_config.get("config_path") or None
    )
    phases["phase1"] = {"status": p1_result["status"], "outputs": p1_result["outputs"]}

    # ── Step 2: Phase 2 双层标注 + 三轨 ──
    print("\n" + "-" * 60)
    print("  [Step 2] Phase 2: 双层标注 + 三轨计算")
    print("-" * 60)

    from phase2_pipeline import run as run_phase2

    p2_result = run_phase2(
        base_dir=base_dir,
        nodes_path=snapshot_path,
        class_path=p1_result["outputs"]["classification"],
        output_dir=output_dir,
        month_label=month_label
    )
    phases["phase2"] = {"status": p2_result["status"], "outputs": p2_result["outputs"]}

    # ── Step 3: Phase 3+ 论文动态分析 ──
    print("\n" + "-" * 60)
    print("  [Step 3] Phase 3+: 论文五行分类 + 结构-活跃度对比")
    print("-" * 60)

    from phase3_plus_pipeline import run as run_phase3

    p3_result = run_phase3(
        base_dir=base_dir,
        snapshot_path=snapshot_path,
        phase2_path=p2_result["outputs"]["diagnosis"],
        paper_titles_path=paper_titles_path,
        output_dir=output_dir,
        month_label=month_label
    )
    phases["phase3_plus"] = {"status": p3_result["status"], "outputs": p3_result["outputs"]}

    # ── Step 4: 时间序列分析（如果有上月数据）──
    prev_label = get_previous_month_label(month_label)
    prev_papers = find_previous_paper_titles(base_dir, prev_label) if prev_label else None

    if prev_papers and p3_result["status"] == "ok":
        print("\n" + "-" * 60)
        print(f"  [Step 4] 时间序列分析: {prev_label} → {month_label}")
        print("-" * 60)

        from timeseries_analysis import run as run_timeseries

        ts_result = run_timeseries(
            base_dir=base_dir,
            current_diag_path=p3_result["outputs"]["diagnosis"],
            prev_paper_titles_path=prev_papers,
            output_dir=output_dir,
            current_label=month_label,
            prev_label=prev_label
        )
        phases["timeseries"] = {"status": ts_result["status"], "outputs": ts_result["outputs"]}
    else:
        print(f"\n  [Step 4] 时间序列分析: 跳过（无上月数据: {prev_label}）")
        phases["timeseries"] = {"status": "skipped", "reason": "no_previous_data"}

    # ── Step 5: 生成汇总报告 ──
    print("\n" + "-" * 60)
    print("  [Step 5] 生成月度汇总报告")
    print("-" * 60)

    summary = build_summary(phases, month_label, prev_label)
    summary_path = os.path.join(output_dir, f"summary_{month_label}.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # 归档
    archive_files(base_dir, month_label, phases, archive_dir)

    print("\n" + "=" * 80)
    print(f"  月度流水线完成 — {month_label}")
    print(f"  汇总报告: {summary_path}")
    print(f"  归档目录: {archive_dir}")
    print("=" * 80)

    return {"status": "ok", "phases": phases, "summary": summary, "archive_dir": archive_dir}


def build_summary(phases, month_label, prev_label):
    """构建月度汇总"""
    summary = {
        "month": month_label,
        "previous_month": prev_label,
        "generated_at": datetime.now().isoformat(),
        "phases": {},
    }

    for phase_name, phase_data in phases.items():
        summary["phases"][phase_name] = {
            "status": phase_data.get("status", "unknown"),
        }

    return summary


def archive_files(base_dir, month_label, phases, archive_dir):
    """将关键输出文件复制到归档目录"""
    import shutil

    files_to_archive = []

    for phase_name, phase_data in phases.items():
        outputs = phase_data.get("outputs", {})
        for key, path in outputs.items():
            if isinstance(path, str) and os.path.exists(path) and path.endswith(".json"):
                files_to_archive.append(path)

    for src in files_to_archive:
        dst = os.path.join(archive_dir, os.path.basename(src))
        try:
            shutil.copy2(src, dst)
        except Exception as e:
            print(f"  ⚠ 归档失败: {src} -> {dst}: {e}")

    print(f"  已归档 {len(files_to_archive)} 个文件到 {archive_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="月度自动追踪流水线")
    parser.add_argument("--month", "-m", type=str, default=None, help="月份标签，如 2026-08")
    parser.add_argument("--base-dir", "-b", type=str, default=None, help="项目根目录")
    parser.add_argument("--skip-collection", action="store_true", help="跳过数据采集")
    parser.add_argument("--skip-validation", action="store_true", help="跳过数据验证")
    args = parser.parse_args()

    DEFAULT_BASE = r"C:\Users\hejij\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a59e217b55e181ea97f0df3\wuxing_flowengine"
    base_dir = args.base_dir or DEFAULT_BASE

    if not os.path.exists(base_dir):
        print(f"错误: 项目目录不存在: {base_dir}")
        sys.exit(1)

    result = run_pipeline(
        base_dir=base_dir,
        month_label=args.month,
        skip_collection=args.skip_collection,
        skip_validation=args.skip_validation
    )

    if result["status"] != "ok":
        print(f"\n流水线执行异常: {result}")
        sys.exit(1)