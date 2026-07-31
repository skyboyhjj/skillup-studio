#!/usr/bin/env python3
"""
归档模块：管理历史诊断结果的归档、索引和查询。
"""
import json, os, shutil
from datetime import datetime


def archive_run(base_dir, month_label, file_paths, archive_dir=None):
    """
    将指定文件归档到 output/archive/YYYY-MM/ 目录。

    参数:
        base_dir:    项目根目录
        month_label: 月份标签
        file_paths:  要归档的文件路径列表
        archive_dir: 归档目标目录（默认 output/archive/YYYY-MM/）

    返回:
        归档文件列表
    """
    if archive_dir is None:
        archive_dir = os.path.join(base_dir, "output", "archive", month_label)

    os.makedirs(archive_dir, exist_ok=True)
    archived = []

    for src in file_paths:
        if not os.path.exists(src):
            continue
        dst = os.path.join(archive_dir, os.path.basename(src))
        shutil.copy2(src, dst)
        archived.append(dst)

    return archived


def list_archives(base_dir):
    """
    列出所有归档月份。

    返回:
        [{"month": "2026-07", "files": [...], "size": bytes}, ...]
    """
    archive_root = os.path.join(base_dir, "output", "archive")
    if not os.path.exists(archive_root):
        return []

    archives = []
    for month_dir in sorted(os.listdir(archive_root), reverse=True):
        full_path = os.path.join(archive_root, month_dir)
        if not os.path.isdir(full_path):
            continue
        files = os.listdir(full_path)
        total_size = sum(os.path.getsize(os.path.join(full_path, f)) for f in files)
        archives.append({
            "month": month_dir,
            "file_count": len(files),
            "files": sorted(files),
            "total_size": total_size
        })

    return archives


def get_archive_summary(base_dir, month_label):
    """
    获取指定月份的归档摘要。

    返回:
        {"month": "2026-07", "files": {...}, "summary": {...}}
    """
    archive_dir = os.path.join(base_dir, "output", "archive", month_label)
    if not os.path.exists(archive_dir):
        return None

    files = {}
    for fname in os.listdir(archive_dir):
        fpath = os.path.join(archive_dir, fname)
        if fname.endswith(".json"):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # 提取关键摘要
                summary = {}
                if "phase" in data:
                    summary["phase"] = data["phase"]
                if "summary" in data:
                    summary["summary"] = data["summary"]
                if "four_dims" in data:
                    summary["four_dims"] = data["four_dims"]
                if "tracks" in data:
                    summary["tracks"] = data["tracks"]
                files[fname] = {
                    "size": os.path.getsize(fpath),
                    "summary": summary
                }
            except:
                files[fname] = {"size": os.path.getsize(fpath), "summary": {}}

    return {
        "month": month_label,
        "file_count": len(files),
        "files": files,
        "total_size": sum(f["size"] for f in files.values())
    }


def build_timeseries_index(base_dir):
    """
    构建时间序列索引：扫描所有归档，提取关键指标的时间序列。

    返回:
        [{month: "2026-07", "S_A": ..., "S_D": ..., "O_t": ..., ...}, ...]
    """
    archive_root = os.path.join(base_dir, "output", "archive")
    if not os.path.exists(archive_root):
        return []

    index = []
    for month_dir in sorted(os.listdir(archive_root)):
        full_path = os.path.join(archive_root, month_dir)
        if not os.path.isdir(full_path):
            continue

        entry = {"month": month_dir}

        # 从 phase1 诊断提取指标
        p1_path = os.path.join(full_path, f"phase1_diagnosis_{month_dir}.json")
        if not os.path.exists(p1_path):
            p1_path = os.path.join(full_path, "phase1_diagnosis.json")

        if os.path.exists(p1_path):
            try:
                with open(p1_path, "r", encoding="utf-8") as f:
                    p1 = json.load(f)
                entry["four_dims"] = p1.get("four_dims", {})
                entry["tracks"] = p1.get("tracks", {})
                entry["stage"] = p1.get("stage", "")
                entry["node_count"] = p1.get("stats", {}).get("total", 0)
            except:
                pass

        # 从 phase3+ 提取
        p3_path = os.path.join(full_path, f"phase3_plus_diagnosis_{month_dir}.json")
        if not os.path.exists(p3_path):
            p3_path = os.path.join(full_path, "phase3_plus_diagnosis.json")

        if os.path.exists(p3_path):
            try:
                with open(p3_path, "r", encoding="utf-8") as f:
                    p3 = json.load(f)
                entry["paper_count"] = p3.get("summary", {}).get("total_papers", 0)
                entry["mean_drift"] = p3.get("summary", {}).get("mean_drift_magnitude", 0)
            except:
                pass

        index.append(entry)

    return index


if __name__ == "__main__":
    DEFAULT_BASE = r"C:\Users\hejij\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a59e217b55e181ea97f0df3\wuxing_flowengine"

    print("=== 归档列表 ===")
    archives = list_archives(DEFAULT_BASE)
    for a in archives:
        print(f"  {a['month']}: {a['file_count']} files, {a['total_size']} bytes")

    print("\n=== 时间序列索引 ===")
    index = build_timeseries_index(DEFAULT_BASE)
    for entry in index:
        dims = entry.get("four_dims", {})
        tracks = entry.get("tracks", {})
        print(f"  {entry['month']}: nodes={entry.get('node_count', 0)}, S_D={tracks.get('D', 'N/A')}, O_t={dims.get('O_t', 'N/A')}")