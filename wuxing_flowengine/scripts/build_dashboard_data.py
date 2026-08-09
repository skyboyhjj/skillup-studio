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
        # key 格式: "source/month" (点号被替换为 _)
        # 还原为原始格式
        source = key.split(".")[0] if "." in key else key
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
# 主函数
# ============================================================

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

    if not engine:
        print("❌ engine_v2_series.json 不可用，无法构建 dashboard 数据")
        sys.exit(1)

    records = build_monthly_records(engine)
    sn = build_shell_nucleus(shell, engine) if shell else {}
    q = build_quality(quality)
    ts = build_time_series(shell) if shell else []

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
        "papers": papers
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


if __name__ == "__main__":
    main()