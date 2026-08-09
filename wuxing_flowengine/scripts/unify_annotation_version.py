"""
标注版本号统一脚本 — 将所有树文件统一至 canonical v2

合并策略:
  - arXiv (6 文件): meta.wuxing_annotation_version v1→v2, 字段名统一为 annotation_version
  - BAAI (4 文件): 新增 meta.annotation_version: "v2"
  - GitHub (2 文件): 新增 meta.annotation_version: "v2"
  - HF (2 文件): 顶层 wuxing_annotation_version 移至 meta.annotation_version: "v2"

用法:
    python unify_annotation_version.py          # 执行更新
    python unify_annotation_version.py --dry-run  # 预览不写入
    python unify_annotation_version.py --check    # 仅检查当前状态
"""

import json
import os
import sys
from pathlib import Path
from glob import glob
import argparse


OUTPUT_DIR = Path(__file__).parent.parent / "output"
TARGET = "v2"


def update_tree_file(path: str, dry_run: bool = False) -> dict:
    """更新单个树文件的标注版本号"""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    source = data.get("source", "unknown")
    fname = os.path.basename(path)
    changes = []

    if "meta" not in data:
        data["meta"] = {}

    meta = data["meta"]

    # 检查当前版本
    current_ver = meta.get("annotation_version") or meta.get("wuxing_annotation_version") or data.get("wuxing_annotation_version") or data.get("annotation_version")

    if current_ver == TARGET and "annotation_version" in meta:
        return {"file": fname, "source": source, "action": "skip", "reason": f"已是 {TARGET}（meta.annotation_version）"}

    # 策略：统一使用 meta.annotation_version
    if "wuxing_annotation_version" in meta:
        # arXiv: meta 内有 wuxing_annotation_version
        old = meta.pop("wuxing_annotation_version")
        meta["annotation_version"] = TARGET
        changes.append(f"meta.wuxing_annotation_version: {old} → meta.annotation_version: {TARGET}")

    elif "wuxing_annotation_version" in data:
        # HF: 顶层有 wuxing_annotation_version
        old = data.pop("wuxing_annotation_version")
        meta["annotation_version"] = TARGET
        changes.append(f"顶层 wuxing_annotation_version: {old} → meta.annotation_version: {TARGET}")

    else:
        # BAAI/GitHub: 无版本号
        meta["annotation_version"] = TARGET
        changes.append(f"新增 meta.annotation_version: {TARGET}")

    if not dry_run:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        # 确保末尾换行
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n")

    return {
        "file": fname,
        "source": source,
        "action": "update",
        "changes": changes
    }


def main():
    parser = argparse.ArgumentParser(description="标注版本号统一至 canonical v2")
    parser.add_argument("--dry-run", action="store_true", help="预览变更，不写入文件")
    parser.add_argument("--check", action="store_true", help="仅检查当前状态")
    args = parser.parse_args()

    tree_files = sorted(glob(str(OUTPUT_DIR / "*_tree_*.json")))

    if args.check:
        print(f"检查 {len(tree_files)} 个树文件:\n")
        for f in tree_files:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            meta = data.get("meta", {})
            ver = meta.get("annotation_version") or meta.get("wuxing_annotation_version") or data.get("wuxing_annotation_version") or "NONE"
            status = "✓" if ver == TARGET and "annotation_version" in meta else "⚠"
            print(f"  {status} {os.path.basename(f):40s} version={ver}")
        return

    results = []
    for f in tree_files:
        result = update_tree_file(f, dry_run=args.dry_run)
        results.append(result)

    updated = [r for r in results if r["action"] == "update"]
    skipped = [r for r in results if r["action"] == "skip"]

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}标注版本统一: {len(updated)} 更新, {len(skipped)} 跳过\n")

    for r in updated:
        print(f"  ✓ {r['file']}")
        for c in r["changes"]:
            print(f"    {c}")

    for r in skipped:
        print(f"  - {r['file']}: {r['reason']}")

    if not args.dry_run:
        print(f"\n完成。标注版本已统一至 {TARGET}。")
        print("建议运行 annotation_check.py --check-all 验证一致性。")


if __name__ == "__main__":
    main()