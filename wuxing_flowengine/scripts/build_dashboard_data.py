"""
展示数据打包 — 将诊断/质量/壳核数据合并为前端统一数据接口

基于《统一数据运营与展示设计》§3.4：
  输出: hui-skill-product-matrix/data/dashboard_data.json
  前端一次 fetch 驱动全页，论文列表按需懒加载

用法:
    python build_dashboard_data.py
    python build_dashboard_data.py --output ../output/dashboard_data.json
    python build_dashboard_data.py --engine ../output/engine_v2_series.json --shell ../output/shell_nucleus_analysis.json
"""

import json
import argparse
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional


# ============================================================
# 默认路径
# ============================================================

SCRIPTS_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPTS_DIR.parent / "output"
REPORT_DIR = OUTPUT_DIR / "reports"

DEFAULT_ENGINE = OUTPUT_DIR / "engine_v2_series.json"
DEFAULT_SHELL = OUTPUT_DIR / "shell_nucleus_analysis.json"
DEFAULT_QUALITY = REPORT_DIR / "quality_2026-07.json"
DEFAULT_OUTPUT = OUTPUT_DIR / "dashboard_data.json"


# ============================================================
# 数据加载
# ============================================================

def load_json(path: Path) -> Optional[dict]:
    """安全加载 JSON，不存在返回 None"""
    if not path.exists():
        print(f"⚠ 文件不存在: {path}")
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# 转换逻辑
# ============================================================

def build_monthly_records(engine_data: dict) -> list:
    """
    从 engine_v2_series.json 提取月度记录。

    Returns:
        [{
            "source": "arxiv",
            "month": "2026-08",
            "S_p": 8.45,
            "O_t": 0.2746,
            "E_u": 0.0335,
            "C_k": 0.0,
            "K_y": 0.2079,
            "dominant": "土",
            "wuxing": {"木": 23.9, "火": 23.9, "土": 27.5, "金": 11.8, "水": 12.9},
            "evolution": {"path": "土→土→火", "edges": [], "profile_match": false}
        }]
    """
    records = []
    for rec in engine_data.get("records", []):
        source = rec["source"]
        extra = rec.get("v2_extra", {})

        # 五行分布（百分比）
        wuxing_pct = {}
        for wx, info in extra.get("dim1_freq", {}).items():
            wuxing_pct[wx] = round(info["pct"] * 100, 1)

        # 演化路径
        profile = extra.get("dim3_profile", {})
        evolution = {
            "path": profile.get("path", ""),
            "edges": extra.get("dim3_edges", []),
            "profile_match": profile.get("matches_profile", False)
        }

        # 使用最后一个月
        months = rec.get("months", [])
        last_month = months[-1] if months else "unknown"

        records.append({
            "source": source,
            "month": last_month,
            "months": months,  # 所有可用月份
            "S_p": rec["S_p"],
            "O_t": rec["O_t"],
            "E_u": rec["E_u"],
            "C_k": rec["C_k"],
            "K_y": rec["K_y"],
            "dominant": rec["dominant"],
            "wuxing": wuxing_pct,
            "evolution": evolution,
            "n_nodes": rec.get("n_nodes", 0)
        })

    return records


def build_shell_nucleus(shell_data: dict, engine_data: dict) -> dict:
    """
    构建壳核对比数据。

    Returns:
        {"shell": "baai", "nucleus": "arxiv", "S_p_diff": 0.97,
         "water_gradient": [33.1, 12.7, 48.9, 43.3],
         "shell_wuxing": {...}, "nucleus_wuxing": {...}}
    """
    shell_avg = shell_data.get("shell_nucleus", {}).get("shell_avg", {})
    nucleus_avg = shell_data.get("shell_nucleus", {}).get("nucleus_avg", {})

    # 从 engine_data 获取 S_p
    shell_sp = None
    nucleus_sp = None
    for rec in engine_data.get("records", []):
        if rec["source"] == "baai":
            shell_sp = rec["S_p"]
        elif rec["source"] == "arxiv":
            nucleus_sp = rec["S_p"]

    sp_diff = round(abs((shell_sp or 0) - (nucleus_sp or 0)), 2) if shell_sp and nucleus_sp else None

    # 水梯度
    water_gradient = []
    for layer in shell_data.get("four_layer", []):
        water_gradient.append(layer.get("water", 0))

    return {
        "shell": "baai",
        "nucleus": "arxiv",
        "S_p_shell": shell_sp,
        "S_p_nucleus": nucleus_sp,
        "S_p_diff": sp_diff,
        "water_gradient": water_gradient,
        "shell_wuxing": {k: round(v * 100, 1) for k, v in shell_avg.items()},
        "nucleus_wuxing": {k: round(v * 100, 1) for k, v in nucleus_avg.items()},
        "cosine_similarity": shell_data.get("shell_nucleus", {}).get("cosine_similarity"),
        "l1_divergence": shell_data.get("shell_nucleus", {}).get("l1_divergence"),
        "four_layer": shell_data.get("four_layer", [])
    }


def build_quality(quality_data: dict) -> dict:
    """
    构建质量摘要。

    Returns:
        {"run_id": "quality_2026-07", "status": {...}, "warnings": [...], "verdict": "..."}
    """
    if not quality_data:
        return {"status": {}, "warnings": [], "verdict": "质量报告未生成"}

    status = {}
    for key, result in quality_data.get("checks", {}).items():
        # key 格式: "source_month" (用 _ 连接)
        source = key.rsplit("_", 1)[0] if "_" in key else key
        # 跳过 month 后缀，只取 source 部分
        # 处理多段 source 名（如 arxiv_ai）
        parts = key.split("_")
        # 找月份部分 YYYY-MM
        month_idx = None
        for i, p in enumerate(parts):
            if len(p) >= 4 and p[:4].isdigit() and "-" in p:
                month_idx = i
                break
        if month_idx is not None:
            source = "_".join(parts[:month_idx])
        else:
            source = key
        all_pass = all(
            v == "pass" for k, v in result.items()
            if k != "annotation"
        )
        if all_pass:
            status[source] = "success"
        elif any(v.startswith("FAIL") for v in result.values()):
            status[source] = "failed"
        else:
            status[source] = "warning"

    return {
        "run_id": quality_data.get("month", "unknown"),
        "generated": quality_data.get("generated", ""),
        "status": status,
        "warnings": quality_data.get("warnings", []),
        "failures": quality_data.get("failures", []),
        "verdict": quality_data.get("verdict", "")
    }


def build_time_series(shell_data: dict) -> list:
    """
    构建月度时间序列数据（供趋势图）。

    Returns:
        [{"source": "arxiv", "month": "2026-06", "O_t": 0.28, "dominant": "土", "total": 13364}, ...]
    """
    series = []
    monthly = shell_data.get("monthly_records", {})
    for source, months in monthly.items():
        for month, info in months.items():
            series.append({
                "source": source,
                "month": f"2026-{month}",
                "O_t": info.get("O_t", 0),
                "E_u": info.get("E_u", 0),
                "dominant": info.get("dominant", ""),
                "total": info.get("total", 0),
                "n_nodes": info.get("n_nodes", 0)
            })
    return sorted(series, key=lambda x: (x["source"], x["month"]))


# ============================================================
# 监控指标（设计文档 §2.4）
# ============================================================

def build_monitoring(quality_data: dict, time_series: list,
                     quality_raw: dict = None) -> dict:
    """
    构建运维监控面板数据。

    六项指标：
      1. 采集成功率（success 源数 / 总源数，< 75% 告警）
      2. 数据量级（n_nodes 与历史均值比，> 3x 或 < 0.3x）
      3. 截断率（触 MAX_PAGES 源数 / 总源数，> 0 告警）
      4. 空月数（n_nodes=0 源×月数，> 0 告警）
      5. 标注漂移（四同步 diff 数，> 0 告警）
      6. 管线耗时（采集→展示全链路，> 60 min 提示）

    Returns:
        {"metrics": {...}, "alerts": [...]}
    """
    # --- 指标 1: 采集成功率 ---
    status = quality_data.get("status", {})
    total_sources = len(status) if status else 0
    success_count = sum(1 for v in status.values() if v == "success")
    success_rate = round(success_count / total_sources * 100, 1) if total_sources > 0 else 0

    # --- 指标 2: 数据量级 ---
    volume_alerts = []
    for w in quality_data.get("warnings", []):
        if "volume" in w.lower() or "3x" in w or "0.3x" in w:
            volume_alerts.append(w)

    # --- 指标 3: 截断率 ---
    truncation_count = 0
    if quality_raw:
        for key, result in quality_raw.get("checks", {}).items():
            tr = result.get("truncation", "pass")
            if tr.startswith("warn") or tr.startswith("FAIL"):
                truncation_count += 1
    total_checks = len(quality_raw.get("checks", {})) if quality_raw else 0
    truncation_rate = round(truncation_count / total_checks * 100, 1) if total_checks > 0 else 0

    # --- 指标 4: 空月数 ---
    empty_months = 0
    for r in time_series:
        if r.get("total", 0) == 0 and r.get("n_nodes", 0) == 0:
            empty_months += 1

    # --- 指标 5: 标注漂移 ---
    annotation_summary = quality_data.get("annotation_summary", {})
    drift_count = annotation_summary.get("mismatch_count", 0) if isinstance(annotation_summary, dict) else 0

    # --- 指标 6: 管线耗时 ---
    pipeline_elapsed = 0
    runs_dir = OUTPUT_DIR / "runs"
    if runs_dir.exists():
        run_files = sorted(runs_dir.glob("pipeline_*.json"), reverse=True)
        if run_files:
            with open(run_files[0], "r", encoding="utf-8") as f:
                run_log = json.load(f)
            for stage in run_log.get("stages", []):
                pipeline_elapsed += stage.get("elapsed_s", 0)

    # --- 告警触发 ---
    alerts = []
    if success_rate < 75:
        alerts.append({
            "level": "error",
            "metric": "采集成功率",
            "value": f"{success_rate}%",
            "threshold": "< 75%",
            "message": f"采集成功率 {success_rate}% 低于 75% 阈值"
        })
    if truncation_rate > 0:
        alerts.append({
            "level": "warning",
            "metric": "截断率",
            "value": f"{truncation_rate}%",
            "threshold": "> 0",
            "message": f"{truncation_count}/{total_checks} 源存在截断（MAX_PAGES 触底）"
        })
    if empty_months > 0:
        alerts.append({
            "level": "warning",
            "metric": "空月数",
            "value": str(empty_months),
            "threshold": "> 0",
            "message": f"{empty_months} 个源×月数据为空"
        })
    if drift_count > 0:
        alerts.append({
            "level": "warning",
            "metric": "标注漂移",
            "value": str(drift_count),
            "threshold": "> 0",
            "message": f"标注一致性 {drift_count} 处不匹配"
        })
    if pipeline_elapsed > 3600:
        alerts.append({
            "level": "warning",
            "metric": "管线耗时",
            "value": f"{pipeline_elapsed:.0f}s",
            "threshold": "> 60 min",
            "message": f"全链路耗时 {pipeline_elapsed/60:.1f} min，超过 60 min 阈值"
        })
    if volume_alerts:
        alerts.append({
            "level": "warning",
            "metric": "数据量级",
            "value": f"{len(volume_alerts)} 处",
            "threshold": "> 3x 或 < 0.3x",
            "message": f"数据量级异常: {volume_alerts[0][:80]}..."
        })

    # 未触发告警的指标
    if not any(a["metric"] == "采集成功率" for a in alerts) and total_sources > 0:
        pass  # 正常，不告警
    if not any(a["metric"] == "管线耗时" for a in alerts) and pipeline_elapsed > 0:
        pass  # 正常，不告警

    return {
        "metrics": {
            "success_rate": {"value": success_rate, "unit": "%", "threshold": "75%", "status": "error" if success_rate < 75 else "ok"},
            "truncation_rate": {"value": truncation_rate, "unit": "%", "threshold": "0%", "status": "warning" if truncation_rate > 0 else "ok"},
            "empty_months": {"value": empty_months, "unit": "个", "threshold": "0", "status": "warning" if empty_months > 0 else "ok"},
            "annotation_drift": {"value": drift_count, "unit": "处", "threshold": "0", "status": "warning" if drift_count > 0 else "ok"},
            "pipeline_elapsed": {"value": round(pipeline_elapsed, 1), "unit": "s", "threshold": "3600s", "status": "warning" if pipeline_elapsed > 3600 else "ok"},
            "volume_alerts": {"value": len(volume_alerts), "unit": "处", "threshold": "0", "status": "warning" if volume_alerts else "ok"}
        },
        "alerts": alerts,
        "total_sources": total_sources,
        "success_count": success_count,
        "generated": datetime.now().isoformat()
    }


# ============================================================
# 每月任务概览
# ============================================================

def build_task_overview(time_series: list, quality_data: dict, quality_raw: dict = None,
                         output_dir: Path = None) -> dict:
    """
    构建每月任务概览（待执行 / 已执行 / 待确认 / 失败）。

    状态判定标准：
      - 已执行 (executed): 有数据（total > 0）且质量状态为 success
      - 待确认 (to_confirm): 有数据但质量状态为 warning（需人工审核 warning 内容后决定是否接受）
      - 待执行 (pending): 无数据或 total=0，且未标记为失败（可继续执行采集）
      - 失败 (failed): 无数据且存在空月/采集失败标记

    可继续性判定（can_proceed）：
      - BAAI：月度报告月末发布，仅当月结束后才可采集（如 8 月数据需 9 月初）
      - arXiv/GitHub/HuggingFace：实时 API，任意历史月份均可采集
      - 当前月（2026-08）：BAAI 不可执行，其余可执行（部分数据）

    行动指引：
      - pending + can_proceed=True → 执行采集
      - pending + can_proceed=False → 等待数据源就绪
      - to_confirm → 审核质量 warning，决定接受或重采
      - failed → 排查失败原因后重试

    Returns:
        {"tasks": {}, "summary": {}, "status_criteria": {}, "action_guidance": [...]}
    """
    # 收集所有源×月
    sources = set()
    months = set()
    source_month_data = {}  # {(source, month): data_point}

    for r in time_series:
        src = r.get("source", "")
        mon = r.get("month", "")
        sources.add(src)
        months.add(mon)
        source_month_data[(src, mon)] = r

    # 也从不含 monthly_records 的质量报告中提取源×月
    # quality_raw.checks 的 key 格式为 "source_YYYY-MM" 或 "source_ai_YYYY-MM"
    if quality_raw:
        for key, result in quality_raw.get("checks", {}).items():
            parts = key.split("_")
            month_idx = None
            for i, p in enumerate(parts):
                if len(p) >= 4 and p[:4].isdigit() and "-" in p:
                    month_idx = i
                    break
            if month_idx is not None:
                src = "_".join(parts[:month_idx])
                mon = parts[month_idx]
                # 标准化 source 名称（arxiv_ai → arxiv）
                if src == "arxiv_ai":
                    src = "arxiv"
                sources.add(src)
                months.add(mon)
                if (src, mon) not in source_month_data:
                    source_month_data[(src, mon)] = {"total": 1}  # 标记有数据

    # 质量状态
    quality_status = quality_data.get("status", {})
    quality_warnings = quality_data.get("warnings", [])

    # 构建 per-source×month 质量状态（从 quality_raw.checks）
    per_month_status = {}  # {(src, mon): "success"|"warning"|"failed"}
    if quality_raw:
        for key, result in quality_raw.get("checks", {}).items():
            parts = key.split("_")
            month_idx = None
            for i, p in enumerate(parts):
                if len(p) >= 4 and p[:4].isdigit() and "-" in p:
                    month_idx = i
                    break
            if month_idx is not None:
                src = "_".join(parts[:month_idx])
                mon = parts[month_idx]
                if src == "arxiv_ai":
                    src = "arxiv"
                all_pass = all(
                    v == "pass" for k, v in result.items()
                    if k != "annotation"
                )
                if all_pass:
                    per_month_status[(src, mon)] = "success"
                elif any(v.startswith("FAIL") for v in result.values()):
                    per_month_status[(src, mon)] = "failed"
                else:
                    per_month_status[(src, mon)] = "warning"

    # 当前日期
    now = datetime.now()
    current_month = now.strftime("%Y-%m")
    current_year = now.year
    current_mon = now.month

    # 树文件源→月份 glob 映射（用于读取 error 字段区分 total=0 vs 采集失败）
    TREE_GLOBS = {
        "baai": "baai_tree_*.json",
        "arxiv": "arxiv_ai_tree_*.json",
        "github": "github_tree_*.json",
        "huggingface": "hf_tree_*.json",
    }

    def _check_tree_errors(source: str, month_str: str) -> str:
        """读取树文件判断采集状态：'ok' | 'collection_failed' | 'no_file'"""
        if not output_dir or not output_dir.exists():
            return "no_file"
        glob_pat = TREE_GLOBS.get(source)
        if not glob_pat:
            return "no_file"
        # 匹配月份（兼容 2026-08 和 202608 两种格式）
        month_no_dash = month_str.replace("-", "")
        for f in sorted(output_dir.glob(glob_pat)):
            fname = f.name
            if month_str in fname or month_no_dash in fname:
                try:
                    tree = json.loads(f.read_text(encoding="utf-8"))
                except Exception:
                    return "no_file"
                nodes = tree.get("nodes", [])
                meta = tree.get("meta", {})
                # 检查 meta.source_type：空月标记
                src_type = meta.get("source_type", "")
                if src_type in ("empty", "failed"):
                    return "collection_failed"
                # 检查是否有节点携带 error 字段
                has_errors = any(n.get("error") for n in nodes)
                if has_errors:
                    return "collection_failed"
                # 检查 total_weight=0 且无 error → 真实空月
                total_w = meta.get("total_weight", 0)
                if total_w == 0 and not has_errors:
                    return "ok"  # 真实空月，不是采集失败
                return "ok"
        return "no_file"

    # BAAI 月末约束：BAAI 月度报告仅在次月发布
    def baai_available_for(month_str: str) -> bool:
        """BAAI 数据是否已可采集（月末发布，次月可用）"""
        y, m = int(month_str[:4]), int(month_str[5:7])
        # 如果当前月份 > 目标月份，说明已过月末
        if current_year > y:
            return True
        if current_year == y and current_mon > m:
            return True
        return False

    # 为每源×月判断状态
    tasks = {}
    for mon in sorted(months):
        tasks[mon] = {}
        for src in sorted(sources):
            key = (src, mon)
            data = source_month_data.get(key)
            status = None
            can_proceed = False
            action = ""

            if not data or data.get("total", 0) == 0:
                # 区分真实空月 vs 采集失败：读取树文件的 error 字段
                tree_status = _check_tree_errors(src, mon)
                if tree_status == "collection_failed":
                    status = "failed"
                elif tree_status == "no_file":
                    # 无文件 → 可能是未采集，判定为 pending（待执行）
                    status = "pending"
                else:
                    # tree_status == "ok"：真实空月（total=0 但采集成功）
                    status = "pending"

                # 可继续性判定
                if status == "pending":
                    if src == "baai":
                        can_proceed = baai_available_for(mon)
                        action = "BAAI 月末发布，可执行采集" if can_proceed else "等待 BAAI 月末报告发布（次月初可用）"
                    else:
                        can_proceed = True
                        action = "可执行采集（API 实时可用）" if tree_status == "no_file" else "上月为空月（total=0），可重采验证"
                else:
                    can_proceed = True  # failed 也可重试
                    action = "采集失败（节点含 error 字段），排查原因后重试"
            else:
                # 有数据，检查质量（优先 per-month 状态）
                qs = per_month_status.get((src, mon), quality_status.get(src, "unknown"))
                if qs == "success":
                    status = "executed"
                    can_proceed = False
                    action = "已完成，无需操作"
                elif qs == "warning":
                    status = "to_confirm"
                    can_proceed = True
                    # 提取具体 warning 内容
                    warn_detail = ""
                    for w in quality_warnings:
                        if src in w:
                            warn_detail = w.split(": ", 1)[-1] if ": " in w else w
                            break
                    action = f"审核质量警告后确认：{warn_detail}" if warn_detail else "审核质量警告后确认或重采"
                elif qs == "failed":
                    status = "failed"
                    can_proceed = True
                    action = "排查失败原因后重试采集"
                else:
                    status = "executed"
                    can_proceed = False
                    action = "已完成（默认通过）"

            tasks[mon][src] = {
                "status": status,
                "can_proceed": can_proceed,
                "action": action
            }

    # 汇总
    summary = {"executed": 0, "to_confirm": 0, "pending": 0, "failed": 0}
    pending_proceed = 0  # 待执行中可继续的
    pending_wait = 0     # 待执行中需等待的
    for mon_data in tasks.values():
        for info in mon_data.values():
            s = info["status"]
            summary[s] = summary.get(s, 0) + 1
            if s == "pending":
                if info["can_proceed"]:
                    pending_proceed += 1
                else:
                    pending_wait += 1

    # 最新月份
    sorted_months = sorted(months)
    latest_month = sorted_months[-1] if sorted_months else None

    # 状态判定标准文档
    status_criteria = {
        "executed": {
            "label": "已执行",
            "description": "有数据（total > 0）且质量门检查全部通过（status=success）",
            "next_action": "无需操作"
        },
        "to_confirm": {
            "label": "待确认",
            "description": "有数据但质量门检查存在 warning（如 weight=0、截断等），需人工审核 warning 内容后决定接受或重采",
            "next_action": "审核 warning → 接受则标记完成，否则重采"
        },
        "pending": {
            "label": "待执行",
            "description": "无数据或 total=0，且未被标记为失败。可继续执行采集（需注意数据源可用性约束，如 BAAI 月末发布）",
            "next_action": "can_proceed=True → 执行采集；can_proceed=False → 等待就绪"
        },
        "failed": {
            "label": "失败",
            "description": "无数据且存在空月/采集失败标记（如 API 限流、网络超时），需排查原因后重试",
            "next_action": "排查失败原因（日志: output/runs/）→ 重试采集"
        }
    }

    # 行动指引（按优先级排序，仅列出需行动的）
    action_guidance = []
    for mon in sorted_months:
        for src in sorted(sources):
            info = tasks.get(mon, {}).get(src, {})
            if info.get("status") in ("pending", "to_confirm", "failed"):
                action_guidance.append({
                    "month": mon,
                    "source": src,
                    "status": info["status"],
                    "can_proceed": info.get("can_proceed", False),
                    "action": info.get("action", ""),
                    "priority": "high" if info.get("can_proceed") else "normal"
                })

    # 按优先级排序：can_proceed=True 优先
    action_guidance.sort(key=lambda x: (0 if x["can_proceed"] else 1, x["month"], x["source"]))

    return {
        "tasks": tasks,
        "summary": summary,
        "pending_proceed": pending_proceed,
        "pending_wait": pending_wait,
        "status_criteria": status_criteria,
        "action_guidance": action_guidance,
        "sources": sorted(sources),
        "months": sorted_months,
        "latest_month": latest_month,
        "current_month": current_month,
        "generated": datetime.now().isoformat()
    }


# ============================================================
# 主函数
# ============================================================

def _merge_quality_reports(primary: dict, primary_path: str = None) -> dict:
    """
    合并所有可用的质量报告，避免单月数据覆盖仪表盘。

    扫描 reports/ 目录下所有 quality_*.json，合并 checks/warnings。
    """
    if not primary:
        primary = {}

    merged = {
        "checks": dict(primary.get("checks", {})),
        "warnings": list(primary.get("warnings", [])),
        "failures": list(primary.get("failures", [])),
        "verdict": primary.get("verdict", ""),
        "month": primary.get("month", "merged"),
        "generated": primary.get("generated", datetime.now().isoformat()),
    }

    # 扫描所有质量报告
    for qf in sorted(REPORT_DIR.glob("quality_*.json")):
        q_data = load_json(qf)
        if not q_data:
            continue
        for key, result in q_data.get("checks", {}).items():
            if key not in merged["checks"]:
                merged["checks"][key] = result
        for w in q_data.get("warnings", []):
            if w not in merged["warnings"]:
                merged["warnings"].append(w)
        for f in q_data.get("failures", []):
            if f not in merged["failures"]:
                merged["failures"].append(f)

    return merged


def build_dashboard(engine_path: str = None,
                    shell_path: str = None,
                    quality_path: str = None) -> dict:
    """
    构建统一的 dashboard 数据包。

    Returns:
        dashboard_data.json 格式
    """
    engine = load_json(Path(engine_path) if engine_path else DEFAULT_ENGINE)
    shell = load_json(Path(shell_path) if shell_path else DEFAULT_SHELL)
    quality = load_json(Path(quality_path) if quality_path else DEFAULT_QUALITY)

    # 合并所有可用的质量报告（避免单月覆盖）
    all_quality = _merge_quality_reports(quality, quality_path)

    if not engine:
        print("❌ engine_v2_series.json 不可用，无法构建 dashboard 数据")
        sys.exit(1)

    records = build_monthly_records(engine)
    sn = build_shell_nucleus(shell, engine) if shell else {}
    q = build_quality(all_quality)
    ts = build_time_series(shell) if shell else []

    # 运维监控指标
    monitoring = build_monitoring(q, ts, all_quality)

    # 每月任务概览
    task_overview = build_task_overview(ts, q, all_quality, OUTPUT_DIR)

    # 发现论文文件
    papers = []
    for f in OUTPUT_DIR.glob("papers_*.json"):
        papers.append(f.name)

    return {
        "schema_version": "1.1",
        "generated": datetime.now().isoformat(),
        "provenance": {
            "collector": "v1.2",
            "annotation": "v2",
            "coeff": "v1.1_calibrated",
            "engine": "wuxing_diagnose_v2 (via EngineAdapterV2)",
            "engine_output": str(engine_path or DEFAULT_ENGINE)
        },
        "monthly": records,
        "shell_nucleus": sn,
        "quality": q,
        "time_series": ts,
        "papers": papers,
        "monitoring": monitoring,
        "task_overview": task_overview
    }


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="展示数据打包 — 构建 dashboard_data.json")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT),
                        help=f"输出路径（默认 {DEFAULT_OUTPUT}）")
    parser.add_argument("--engine", default=str(DEFAULT_ENGINE),
                        help=f"engine_v2_series.json 路径")
    parser.add_argument("--shell", default=str(DEFAULT_SHELL),
                        help=f"shell_nucleus_analysis.json 路径")
    parser.add_argument("--quality", default=str(DEFAULT_QUALITY),
                        help=f"quality 报告路径")
    parser.add_argument("--json", action="store_true",
                        help="仅输出 JSON 到 stdout")

    args = parser.parse_args()

    dashboard = build_dashboard(args.engine, args.shell, args.quality)

    if args.json:
        print(json.dumps(dashboard, ensure_ascii=False, indent=2))
    else:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(dashboard, f, ensure_ascii=False, indent=2)

        print(f"✓ dashboard_data.json 已生成: {output_path}")
        print(f"  源×月: {len(dashboard['monthly'])} 条")
        print(f"  壳核: S_p_diff={dashboard['shell_nucleus'].get('S_p_diff')}")
        print(f"  时间序列: {len(dashboard['time_series'])} 个数据点")
        print(f"  论文文件: {len(dashboard['papers'])} 个")
        print(f"  质量状态: {dashboard['quality'].get('verdict', 'N/A')}")
        m = dashboard.get('monitoring', {})
        print(f"  监控: 成功率={m.get('metrics',{}).get('success_rate',{}).get('value','?')}% | "
              f"截断率={m.get('metrics',{}).get('truncation_rate',{}).get('value','?')}% | "
              f"告警={len(m.get('alerts',[]))} 条")
        to = dashboard.get('task_overview', {})
        print(f"  任务概览: {to.get('summary',{})}")


if __name__ == "__main__":
    main()