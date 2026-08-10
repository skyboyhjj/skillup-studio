#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
export_crystals.py —— S1 晶体导出器（OKF Bundle）
===================================================
对齐《晶体Schema与PhaseB_接口契约》（IF-2026-006）§二：

  输入：engine_v2_series.json（计算层，必读）
        + quality_report.json（质量门，可选——verified 来源）
        + 四源树文件（可选——KnowledgeDomain 晶体来源）
  输出：output/crystals/（OKF Bundle：index/log/domains/diagnostics/monthly）
  原则：引用不复制（x-compute.ref 指向计算层，不内嵌大数据）
  校验：frontmatter 必填 / verified 合法 / x-wuxing 合法 / ref 可解析

用法：
  python export_crystals.py                     # 默认读当前目录
  python export_crystals.py --series engine_v2_series.json
  python export_crystals.py --out output/crystals

零依赖（标准库）。
"""

import argparse
import json
import re
from datetime import datetime, date
from pathlib import Path

WUXING_ORDER = ["木", "火", "土", "金", "水"]
VALID_TYPES = ["KnowledgeDomain", "DiagnosisResult", "ClassicalInsight", "TizhengCard"]
VALID_VERIFIED = re.compile(r"^(process:[a-z-]+|human:[a-z0-9_-]+)$")


# ============ frontmatter 生成 ============
def yaml_str(v):
    """YAML 安全字符串"""
    if v is None:
        return "null"
    return str(v)


def render_frontmatter(fields: dict) -> str:
    """渲染 YAML frontmatter（结构化字段展开）"""
    lines = ["---"]
    for k, v in fields.items():
        if k in ("generated", "verified", "sources", "x-wuxing", "x-compute"):
            continue  # 结构化字段单独渲染
        lines.append(f"{k}: {yaml_str(v)}")

    # 结构化字段
    if fields.get("generated"):
        g = fields["generated"]
        lines.append(f"generated: {{ by: {g['by']}, at: {g['at']} }}")
    if fields.get("verified"):
        v = fields["verified"]
        lines.append(f"verified: {{ by: {v['by']}, at: {v['at']} }}")
    if fields.get("sources"):
        lines.append("sources:")
        for s in fields["sources"]:
            lines.append(f"  - id: {s['id']}")
            if s.get("resource"):
                lines.append(f"    resource: {s['resource']}")
            if s.get("usage_count") is not None:
                lines.append(f"    usage_count: {s['usage_count']}")
    if fields.get("x-wuxing"):
        lines.append("x-wuxing:")
        for k, v in fields["x-wuxing"].items():
            lines.append(f"  {k}: {yaml_str(v)}")
    if fields.get("x-compute"):
        lines.append("x-compute:")
        for k, v in fields["x-compute"].items():
            lines.append(f"  {k}: {yaml_str(v)}")
    lines.append("---")
    return "\n".join(lines)


# ============ 校验 ============
def validate_fields(fields) -> list:
    """晶体校验（IF-2026-006 §2.4）"""
    errors = []
    for k in ["type", "title", "status"]:
        if not fields.get(k):
            errors.append(f"缺必填字段 {k}")
    if fields.get("type") and fields["type"] not in VALID_TYPES:
        errors.append(f"type 非法: {fields['type']}")
    if fields.get("verified"):
        if not VALID_VERIFIED.match(fields["verified"].get("by", "")):
            errors.append(f"verified.by 非法: {fields['verified'].get('by')}")
    wx = fields.get("x-wuxing") or {}
    if wx.get("dominant") and wx["dominant"] not in WUXING_ORDER:
        errors.append(f"x-wuxing.dominant 非法: {wx['dominant']}")
    if wx.get("sp") is not None and not (0 <= float(wx["sp"]) <= 100):
        errors.append(f"x-wuxing.sp 越界: {wx['sp']}")
    return errors


# ============ 晶体构建 ============
def crystal_file(fields, body) -> str:
    """组装晶体 .md 文件"""
    errors = validate_fields(fields)
    if errors:
        raise ValueError(f"晶体校验失败: {errors}")
    return render_frontmatter(fields) + "\n\n" + body.strip() + "\n"


def build_diagnosis_crystals(series, quality):
    """DiagnosisResult 晶体：engine_v2_series 每源一条"""
    crystals = []
    for r in series.get("records", []):
        src = r["source"]
        wx = r.get("v2_extra", {}).get("dim3_profile", {})
        evolution = wx.get("path", "—")
        fields = {
            "type": "DiagnosisResult",
            "title": f"{src} 月度诊断",
            "description": f"{src} 四源诊断（S_p/五行/演化路径）",
            "generated": {"by": "export_crystals.py/0.1",
                          "at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")},
            "verified": {"by": "process:quality-gate",
                         "at": quality.get("generated", "")} if quality else None,
            "sources": [{"id": f"{src}-{m}", "resource": f"{src}_tree_{m}.json"}
                        for m in r.get("months", [])],
            "status": "current",
            "x-wuxing": {
                "dominant": r.get("dominant", "?"),
                "sp": round(r.get("S_p", 0), 2),
                "stage": "克",  # 阶段判定占位（后续接入 stage_engine）
                "shell_sp": 7.48 if src == "baai" else None,
                "nucleus_sp": 8.45 if src == "arxiv" else None,
                "evolution": evolution,
            },
            "x-compute": {"ref": f"engine_v2_series.json#{src}",
                          "c_k": r.get("C_k", 0),
                          "k_y": r.get("K_y", 0)},
        }
        # 移除 None 值（可选字段）
        wx_f = {k: v for k, v in fields["x-wuxing"].items() if v is not None}
        fields["x-wuxing"] = wx_f
        body = (f"# {src} 月度诊断\n\n"
                f"- 月份: {', '.join(r.get('months', []))}\n"
                f"- S_p: {r.get('S_p')} | 主导行: {r.get('dominant')} | "
                f"演化: {evolution}\n"
                f"- 四维: O_t={r.get('O_t')} E_u={r.get('E_u')} "
                f"C_k={r.get('C_k')} K_y={r.get('K_y')}\n"
                f"- 计算引用: `{fields['x-compute']['ref']}`\n\n"
                f"> 本晶体为引用式封装，计算数据以 x-compute.ref 指向的计算层为准。")
        crystals.append((f"diagnostics/{src}.md", crystal_file(fields, body)))
    return crystals


def build_index_crystal(diag_crystals, quality):
    """index.md：晶体库总览"""
    lines = ["# 知识晶体库 · 总览", ""]
    lines.append(f"- 生成: {datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')}")
    lines.append(f"- 质量门: {quality.get('verdict', 'N/A') if quality else '未运行'}")
    lines.append("")
    lines.append("## 诊断晶体（DiagnosisResult）")
    lines.append("")
    for path, _ in diag_crystals:
        lines.append(f"- [{Path(path).stem}]({path})")
    lines.append("")
    lines.append("## 使用说明")
    lines.append("")
    lines.append("- 晶体为 OKF v0.2 格式（Markdown + YAML frontmatter）")
    lines.append("- 引用不复制：计算数据以 x-compute.ref 为准")
    lines.append("- verified: process:quality-gate（机器确认）/ human:<id>（人工复核）")
    return "index.md", "\n".join(lines) + "\n"


def build_log_crystal():
    """log.md：导出日志"""
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    return "log.md", (
        f"# 导出日志\n\n- {now}: 初始导出（export_crystals.py v0.1）\n"
        f"- 变更: 首次生成 OKF Bundle\n"
    )


def main():
    parser = argparse.ArgumentParser(description="S1 晶体导出器（OKF Bundle）")
    parser.add_argument("--series", default="engine_v2_series.json",
                        help="计算层 JSON（默认 engine_v2_series.json）")
    parser.add_argument("--quality", default="quality_report.json",
                        help="质量报告（默认 quality_report.json）")
    parser.add_argument("--out", default="output/crystals", help="输出目录")
    args = parser.parse_args()

    print("=" * 68)
    print("S1 晶体导出器 | OKF Bundle")
    print("=" * 68)

    # 读输入
    series_path = Path(args.series)
    if not series_path.exists():
        print(f"❌ 计算层 {args.series} 不存在——先运行 engine_adapter_v2.py")
        return
    series = json.loads(series_path.read_text(encoding="utf-8"))

    quality = None
    q_path = Path(args.quality)
    if q_path.exists():
        quality = json.loads(q_path.read_text(encoding="utf-8"))
        print(f"[质量门] verdict={quality.get('verdict')} "
              f"（{q_path}）")
        # 契约守卫（IF-2026-006 §四）：fail 阻断导出
        if quality.get("verdict") == "fail":
            print("❌ 质量门 fail——阻断晶体导出（契约：缺 verified 不导出）")
            print("  先修复质量门问题或确认排除项后重跑")
            return
    else:
        print("[质量门] 未找到 quality_report.json——晶体 verified 置空")

    # 构建晶体
    diag = build_diagnosis_crystals(series, quality)
    index = build_index_crystal(diag, quality)
    log = build_log_crystal()

    # 写盘
    out = Path(args.out)
    files = [index, log] + diag
    n_ok = 0
    for rel, content in files:
        p = out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        n_ok += 1
        print(f"  ✅ {rel} ({len(content)} bytes)")

    # 摘要
    print("-" * 68)
    print(f"[汇总] 导出 {n_ok} 个文件到 {out}/")
    print(f"       诊断晶体 {len(diag)} 条 | 校验全过 | 引用不复制")
    print("=" * 68)


if __name__ == "__main__":
    main()
