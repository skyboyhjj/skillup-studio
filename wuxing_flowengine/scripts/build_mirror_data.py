#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_mirror_data.py —— 从 daojing_database_v2.json 提取镜鉴前端数据

输入：wuxing_flowengine/data/daojing_database_v2.json（单一可信源）
输出：hui-skill-product-matrix/data/mirror_data.json（离线模式数据源）

逻辑：
  1. 遍历 81 章，提取 chapter_title、dominant、dist、dimensions（4维×2级）
  2. 按 dominant 分组生成 wuxing_chapters 索引
  3. 注入 dimension_wuxing/dimension_keys/dimension_cn 常量

用法：
  python build_mirror_data.py
  python build_mirror_data.py --db path/to/daojing_database_v2.json
  python build_mirror_data.py --out path/to/mirror_data.json
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from contracts import DIMENSION_WUXING, DIMENSION_KEYS, DIMENSION_CN


def build_mirror_data(db_path: Path, out_path: Path):
    db = json.loads(db_path.read_text(encoding="utf-8"))

    chapters = {}
    wuxing_chapters = {wx: [] for wx in ["水", "木", "火", "土", "金"]}

    for num_str in sorted(db.keys(), key=lambda k: int(k)):
        ch = db[num_str]
        dominant = ch.get("x_wuxing", {}).get("dominant")
        dist = ch.get("x_wuxing", {}).get("dist", {})

        # 提取 dimensions（4维 × 2级）
        dims = {}
        for dim_name in ["时位轴", "宇位轴", "识位轴", "缘位轴"]:
            dim_data = ch.get("dimensions", {}).get(dim_name, {})
            if not dim_data:
                continue
            dims[dim_name] = {}
            for level in ["低", "高"]:
                entry = dim_data.get(level, {})
                if not entry:
                    continue
                dims[dim_name][level] = {
                    "triggers": entry.get("triggers", []),
                    "insight_desc": entry.get("insight_desc", ""),
                    "action_desc": entry.get("action_desc", ""),
                    "reflection": entry.get("reflection", ""),
                }

        chapters[num_str] = {
            "title": ch.get("chapter_title", ""),
            "dominant": dominant,
            "dist": dist,
            "dimensions": dims,
        }

        if dominant in wuxing_chapters:
            wuxing_chapters[dominant].append(num_str)

    mirror_data = {
        "generated": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "schema": "mirror_data_v1",
        "source": str(db_path.name),
        "dimension_wuxing": DIMENSION_WUXING,
        "dimension_keys": DIMENSION_KEYS,
        "dimension_cn": DIMENSION_CN,
        "chapters": chapters,
        "wuxing_chapters": wuxing_chapters,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(mirror_data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    # 写入后校验：JSON 可解析 + 数据完整性
    written = json.loads(out_path.read_text(encoding="utf-8"))
    n_chapters = len(written.get("chapters", {}))
    n_entries = sum(
        sum(len(level) for level in (ch.get("dimensions", {}).values()))
        for ch in written["chapters"].values()
    )
    if n_chapters != 81:
        raise RuntimeError(f"章节数异常: {n_chapters}/81")
    if n_entries != 648:
        raise RuntimeError(f"维度条目异常: {n_entries}/648")

    size_kb = out_path.stat().st_size / 1024
    print(f"[mirror_data] {n_chapters} 章 · {n_entries} 维度条目 · {size_kb:.0f} KB")
    print(f"[输出] {out_path}")

    # 五行分布
    wx_counts = {wx: len(chs) for wx, chs in wuxing_chapters.items()}
    print(f"[五行分布] {wx_counts}")


def main():
    parser = argparse.ArgumentParser(description="从数据库提取镜鉴前端数据")
    parser.add_argument(
        "--db",
        default=None,
        help="daojing_database_v2.json 路径（默认自动查找）",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="输出路径（默认 hui-skill-product-matrix/data/mirror_data.json）",
    )
    args = parser.parse_args()

    # 路径解析
    script_dir = Path(__file__).parent.resolve()
    repo_root = script_dir.parent.parent  # scripts → wuxing_flowengine → repo root

    db_path = Path(args.db) if args.db else (
        script_dir.parent / "data" / "daojing_database_v2.json"
    )
    out_path = Path(args.out) if args.out else (
        repo_root / "hui-skill-product-matrix" / "data" / "mirror_data.json"
    )

    if not db_path.exists():
        print(f"[错误] 数据库文件不存在: {db_path}")
        return 1

    print(f"[输入] {db_path}")
    build_mirror_data(db_path, out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())