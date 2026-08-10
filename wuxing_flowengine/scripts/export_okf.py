# -*- coding: utf-8 -*-
"""
OKF (Open Knowledge Format) v0.2 导出器

将知识树追踪引擎的诊断数据 + 四源树文件导出为 OKF Bundle。
按需手动触发，输出至 output/archive/okf_{month}/，不入常驻管线。

用法:
    python export_okf.py                          # 默认最近月
    python export_okf.py --month 2026-08          # 指定月份
    python export_okf.py --output-dir ./my_okf    # 自定义输出目录
"""

import argparse
import fnmatch
import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, List

# ============================================================
# 路径配置
# ============================================================

SCRIPTS_DIR = Path(__file__).parent.resolve()
PROJECT_DIR = SCRIPTS_DIR.parent.resolve()
REPO_ROOT = PROJECT_DIR.parent.resolve()
OUTPUT_DIR = PROJECT_DIR / "output"
ARCHIVE_DIR = OUTPUT_DIR / "archive"
DIAGNOSE_DIR = PROJECT_DIR / "diagnose"
FRONTEND_DATA = REPO_ROOT / "hui-skill-product-matrix" / "data" / "dashboard_data.json"
BACKEND_DATA = OUTPUT_DIR / "dashboard_data.json"
VERIFIED_FILE = OUTPUT_DIR / "verified_tasks.json"
KNOWLEDGEIGNORE_FILE = REPO_ROOT / ".knowledgeignore"

# 四源元信息
SOURCE_META = {
    "baai": {
        "name": "BAAI Hub (智源社区)",
        "type": "AcademicInstitution",
        "resource": "https://hub.baai.ac.cn",
        "description": "智源社区知识树与科研月报采集，月度汇总",
    },
    "arxiv": {
        "name": "arXiv",
        "type": "AcademicPreprint",
        "resource": "https://arxiv.org",
        "description": "arXiv AI 子领域月度论文采集，11 分类",
    },
    "github": {
        "name": "GitHub",
        "type": "CodeRepository",
        "resource": "https://github.com",
        "description": "GitHub Topic 搜索月度采集，26 个 AI 主题",
    },
    "huggingface": {
        "name": "HuggingFace",
        "type": "ModelRepository",
        "resource": "https://huggingface.co",
        "description": "HuggingFace Models 月度采集，12 个 pipeline_tag",
    },
}

# 五行标签映射
WUXING_LABELS = {
    "木": "Wood (生长/创新)",
    "火": "Fire (扩散/爆发)",
    "土": "Earth (稳定/整合)",
    "金": "Metal (收敛/结构化)",
    "水": "Water (流动/适应)",
}


# ============================================================
# 数据加载
# ============================================================

def load_json(path: Path) -> dict:
    """加载 JSON 文件，不存在返回 None"""
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


# ============================================================
# .knowledgeignore — OKF 导出忽略规则
# ============================================================

def load_knowledgeignore(filepath: Path = None) -> list:
    """
    加载 .knowledgeignore 文件，返回编译后的模式列表。
    语法兼容 .gitignore：每行一个 glob 模式，# 注释，空行忽略，! 取反。

    返回: [(pattern, negated, is_dir), ...]
      - pattern: 编译后的正则表达式
      - negated: True 表示 ! 取反（重新包含）
      - is_dir: True 表示目录模式（以 / 结尾）
    """
    if filepath is None:
        filepath = KNOWLEDGEIGNORE_FILE

    if not filepath.exists():
        return []

    patterns = []
    for line in filepath.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        # 跳过空行
        if not line:
            continue
        # 去除行内注释（# 前后有空格或行首时视为注释）
        comment_pos = line.find(" # ")
        if comment_pos >= 0:
            line = line[:comment_pos].strip()
        # 跳过纯注释行
        if line.startswith("#"):
            continue

        negated = False
        if line.startswith("!"):
            negated = True
            line = line[1:].strip()

        is_dir = line.endswith("/")
        if is_dir:
            line = line[:-1]

        # 转换为正则表达式
        regex = _glob_to_regex(line)
        patterns.append((re.compile(regex), negated, is_dir))

    return patterns


def _glob_to_regex(pattern: str) -> str:
    """
    将 glob 模式转换为正则表达式。
    支持 **、*、? 等标准 gitignore 语法。
    """
    # 锚定：不以 / 开头时，匹配任意层级
    if pattern.startswith("/"):
        pattern = pattern[1:]
        anchored = True
    else:
        # 不以 / 开头 → 匹配任意层级
        anchored = False

    # 处理 **（跨目录匹配）
    parts = pattern.split("**")
    regex_parts = []
    for i, part in enumerate(parts):
        if i > 0:
            # ** 匹配任意层级（包括空）
            regex_parts.append(r"(?:.*/)?")
        # 转义特殊字符
        escaped = re.escape(part)
        # 还原 glob 通配符（在 re.escape 之后）
        escaped = escaped.replace(r"\*", "[^/]*")
        escaped = escaped.replace(r"\?", "[^/]")
        regex_parts.append(escaped)

    regex = "".join(regex_parts)

    if anchored:
        regex = "^" + regex
    else:
        regex = "(?:^|.*/)" + regex

    # 目录模式匹配路径前缀
    regex += "(?:/.*)?$"

    return regex


def is_ignored(rel_path: str, patterns: list) -> bool:
    """
    检查相对路径是否应被忽略。

    Args:
        rel_path: 相对于 OKF bundle 根目录的路径（如 "domains/github.md"）
        patterns: load_knowledgeignore() 返回的模式列表

    Returns:
        True 表示应忽略（跳过生成）
    """
    ignored = False
    for regex, negated, is_dir in patterns:
        if regex.search(rel_path):
            ignored = not negated
    return ignored


def _list_ignored_files(patterns: list) -> str:
    """生成忽略规则的人类可读摘要"""
    if not patterns:
        return ""
    lines = ["## 忽略规则", ""]
    raw = KNOWLEDGEIGNORE_FILE.read_text(encoding="utf-8").strip()
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            lines.append(f"- `{stripped}`")
    return "\n".join(lines) + "\n\n"


def load_tree_files(month: str) -> dict:
    """加载四源树文件"""
    trees = {}
    glbs = {
        "baai": "baai_tree_*.json",
        "arxiv": "arxiv_ai_tree_*.json",
        "github": "github_tree_*.json",
        "huggingface": "hf_tree_*.json",
    }
    month_no_dash = month.replace("-", "")
    for src, pat in glbs.items():
        for f in sorted(OUTPUT_DIR.glob(pat)):
            if month in f.name or month_no_dash in f.name:
                trees[src] = load_json(f)
                break
    return trees


# ============================================================
# OKF 文档生成
# ============================================================

def _yaml_value(v, indent: int = 0) -> list:
    """递归序列化 YAML 值，返回行列表"""
    prefix = "  " * indent
    if v is None:
        return [f"{prefix}null"]
    if isinstance(v, dict):
        result = []
        for sk, sv in v.items():
            if isinstance(sv, (dict, list)):
                result.append(f"{prefix}{sk}:")
                result.extend(_yaml_value(sv, indent + 1))
            elif isinstance(sv, str):
                result.append(f'{prefix}{sk}: "{sv}"')
            else:
                result.append(f"{prefix}{sk}: {sv}")
        return result
    if isinstance(v, list):
        if not v:
            return [f"{prefix}[]"]
        # 检查是否为简单类型列表
        if all(not isinstance(item, (dict, list)) for item in v):
            items = ", ".join(str(item) for item in v)
            return [f"{prefix}[{items}]"]
        # 复杂类型列表（如 verified 事件）
        result = []
        for item in v:
            if isinstance(item, dict):
                result.append(f"{prefix}-")
                result.extend(_yaml_value(item, indent + 1))
            else:
                result.append(f"{prefix}- {item}")
        return result
    if isinstance(v, str):
        return [f'{prefix}"{v}"']
    return [f"{prefix}{v}"]


def okf_frontmatter(type_: str, title: str, description: str = "",
                    generated_by: str = "pipeline_orchestrator/0.2",
                    **extra) -> str:
    """生成 OKF YAML frontmatter"""
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "---",
        f"type: {type_}",
        f"title: {title}",
    ]
    if description:
        lines.append(f"description: {description}")
    lines.append("generated:")
    lines.append(f"  by: {generated_by}")
    lines.append(f"  at: {now}")
    # 额外字段
    for k, v in extra.items():
        if v is None:
            continue
        if isinstance(v, (dict, list)):
            lines.append(f"{k}:")
            lines.extend(_yaml_value(v, 1))
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def build_index(dashboard: dict, month: str) -> str:
    """生成 index.md — 知识树总览"""
    prov = dashboard.get("provenance", {})
    shell_nuc = dashboard.get("shell_nucleus", {})
    monthly = dashboard.get("monthly", [])
    task = dashboard.get("task_overview", {}).get("summary", {})
    trust_tiers = dashboard.get("task_overview", {}).get("trust_tiers", {})

    doc = okf_frontmatter(
        "KnowledgeBundle",
        f"知识树追踪引擎 — {month} 月度诊断",
        "四源知识树月度快照：BAAI + arXiv + GitHub + HuggingFace，含五行诊断、壳核分析、水梯度",
        okf_version="0.2",
        x_wuxing={
            "engine": prov.get("engine", "wuxing_diagnose_v2"),
            "annotation": prov.get("annotation", "v2"),
            "coeff": prov.get("coeff", "v1.1_calibrated"),
        },
    )

    doc += "# 知识树追踪引擎 — " + month + " 月度诊断\n\n"
    doc += "## 数据源\n\n"
    doc += "| 源 | 类型 | 描述 |\n"
    doc += "|----|------|------|\n"
    for src, meta in SOURCE_META.items():
        doc += "| [" + meta["name"] + "](" + meta["resource"] + ") | " + meta["type"] + " | " + meta["description"] + " |\n"

    doc += "\n## 诊断摘要\n\n"
    doc += "| 指标 | 壳（BAAI 规划层） | 核（arXiv 产出层） | 工程层（GitHub） | 模型层（HuggingFace） |\n"
    doc += "|------|-------------------|---------------------|-------------------|------------------------|\n"
    for rec in monthly:
        src = rec["source"]
        label = SOURCE_META.get(src, {}).get("name", src)
        if src == "baai":
            doc += "| **" + label + "** | S_p=" + str(rec["S_p"]) + " | "
        else:
            doc += "| " + label + " | "
        if src == "baai":
            doc += " | "
        elif src == "arxiv":
            doc += "| S_p=" + str(rec["S_p"]) + " | "
        else:
            doc += "| | S_p=" + str(rec["S_p"]) + " | "
        if src == "huggingface":
            doc += "S_p=" + str(rec["S_p"]) + " |\n"
        else:
            doc += "|\n"

    doc += "\n### 壳核收敛\n\n"
    doc += "- 壳 S_p: " + str(shell_nuc.get("S_p_shell", "N/A")) + " (BAAI)\n"
    doc += "- 核 S_p: " + str(shell_nuc.get("S_p_nucleus", "N/A")) + " (arXiv)\n"
    doc += "- 绝对差: " + str(shell_nuc.get("S_p_diff", "N/A")) + " (< 5 点 -> 收敛维持)\n"
    doc += "- 余弦相似度: " + str(shell_nuc.get("cosine_similarity", "N/A")) + "\n"

    doc += "\n### 任务概览\n\n"
    doc += "- 已执行: " + str(task.get("executed", 0)) + "\n"
    doc += "- 待确认: " + str(task.get("to_confirm", 0)) + "\n"
    doc += "- 待执行: " + str(task.get("pending", 0)) + "\n"
    doc += "- 失败: " + str(task.get("failed", 0)) + "\n"

    doc += "\n### 信任层级（OKF 可信度模型）\n\n"
    doc += "- 机器确认 (machine-confirmed): " + str(trust_tiers.get("machine_confirmed", 0)) + "\n"
    doc += "- 人工复核 (human-reviewed): " + str(trust_tiers.get("human_reviewed", 0)) + "\n"
    doc += "- 未验证 (unverified): " + str(trust_tiers.get("unverified", 0)) + "\n"
    doc += "- 待执行 (pending): " + str(trust_tiers.get("pending", 0)) + "\n"
    doc += "\n> 信任层级体系: unverified -> machine-confirmed (质量门通过) -> human-reviewed (人工确认)\n"
    doc += "> 前端用户确认后，导出时将包含 verified 事件记录。\n"

    doc += "\n## 导航\n\n"
    doc += "- [领域诊断](domains/index.md) — 各领域五行画像与演化\n"
    doc += "- [壳核诊断](diagnostics/shell-nucleus.md) — 壳核收敛与四层水梯度\n"
    doc += "- [月度快照](monthly/index.md) — 各月四源数据摘要\n"
    doc += "- [更新日志](log.md) — 采集与诊断历史\n"
    return doc


def build_log(dashboard: dict, month: str) -> str:
    """生成 log.md — 更新历史"""
    prov = dashboard.get("provenance", {})
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

    doc = okf_frontmatter(
        "UpdateLog",
        "知识树追踪引擎 — 更新日志",
        "月度采集与诊断的变更历史",
        okf_version="0.2",
    )
    doc += f"""# 更新日志

## {month}

- **{now}** — OKF Bundle 导出
  - 引擎: {prov.get('engine', 'wuxing_diagnose_v2')}
  - 标注版本: {prov.get('annotation', 'v2')}
  - 系数版本: {prov.get('coeff', 'v1.1_calibrated')}
  - 采集器: {prov.get('collector', 'v1.2')}

---
*此日志由 export_okf.py 自动生成。完整运行历史见 `output/runs/`。*
"""
    return doc


def build_domain_index(dashboard: dict, month: str, task_overview: dict = None) -> str:
    """生成 domains/index.md"""
    monthly = dashboard.get("monthly", [])
    doc = okf_frontmatter(
        "DirectoryListing",
        "领域诊断 — 目录",
        "四源知识树各领域五行画像与演化路径",
    )
    doc += "# 领域诊断\n\n"

    # 信任层级图标
    TIER_ICONS = {
        "machine-confirmed": "⚙️",
        "human-reviewed": "👤",
        "unverified": "❓",
        "pending": "⏳",
    }

    for rec in monthly:
        src = rec["source"]
        label = SOURCE_META.get(src, {}).get("name", src)
        dom = rec.get("dominant", "?")
        sp = rec.get("S_p", "?")
        evo = rec.get("evolution", {})
        path = evo.get("path", "?")

        # 信任层级
        tier = "unverified"
        if task_overview:
            tasks = task_overview.get("tasks", {})
            for mon_str, mon_tasks in tasks.items():
                src_task = mon_tasks.get(src, {})
                if src_task.get("trust_tier"):
                    tier = src_task["trust_tier"]
                    break
        tier_icon = TIER_ICONS.get(tier, "?")

        doc += f"- [{label}]({src}.md) — 主导行: {dom}, S_p={sp}, 演化: {path} {tier_icon}\n"
    return doc


def build_domain_concept(source: str, rec: dict, trees: dict, month: str,
                         task_overview: dict = None) -> str:
    """生成单个领域概念文档"""
    meta = SOURCE_META.get(source, {})
    wuxing = rec.get("wuxing", {})
    evo = rec.get("evolution", {})

    # 提取该源×月的信任层级信息
    verified_events = []
    trust_tier = "unverified"
    if task_overview:
        tasks = task_overview.get("tasks", {})
        for mon_str, mon_tasks in tasks.items():
            src_task = mon_tasks.get(source, {})
            tt = src_task.get("trust_tier", "")
            if tt in ("machine-confirmed", "human-reviewed"):
                trust_tier = tt
                verified_events = src_task.get("verified", [])
                break  # 取第一个有 verified 的月份

    extra_frontmatter = {
        "resource": meta.get("resource", ""),
        "x_wuxing": {
            "dominant": rec.get("dominant", "?"),
            "sp": rec.get("S_p", "?"),
            "stage": rec.get("stage", "?"),
            "evolution_path": evo.get("path", "?"),
        },
        "sources": [
            {"id": f"{source}-tree-{month}", "resource": f"output/{source}_tree_{month}.json"}
        ],
    }
    if verified_events:
        extra_frontmatter["verified"] = verified_events

    doc = okf_frontmatter(
        meta.get("type", "KnowledgeDomain"),
        meta.get("name", source),
        meta.get("description", ""),
        **extra_frontmatter,
    )

    doc += f"""# {meta.get('name', source)}

## 五行画像

| 五行 | 占比 | 含义 |
|------|------|------|
"""
    for wx, label in WUXING_LABELS.items():
        pct = wuxing.get(wx, 0)
        doc += f"| {wx} | {pct:.1f}% | {label} |\n"

    doc += f"""
## 四维指标

| 指标 | 值 | 含义 |
|------|-----|------|
| O_t | {rec.get('O_t', '?')} | 本体论深度（主导行集中度） |
| E_u | {rec.get('E_u', '?')} | 认识论均匀度（五行分布熵） |
| C_k | {rec.get('C_k', '?')} | 因果激活度（层间生克边数） |
| K_y | {rec.get('K_y', '?')} | 缘位协调度（五行互补性） |
| **S_p** | **{rec.get('S_p', '?')}** | **存在度（P忠恕中道，p=0.5）** |

## 演化路径

- 路径: {evo.get('path', 'N/A')}
- 画像匹配: {evo.get('profile_match', 'N/A')}
- 节点数: {rec.get('n_nodes', 'N/A')}

## 数据来源

- 资源: {meta.get('resource', 'N/A')}
- 采集月份: {', '.join(rec.get('months', []))}
- 树文件: `output/{source}_tree_{month}.json`
"""
    # 附加树文件节点摘要
    tree = trees.get(source)
    if tree and tree.get("nodes"):
        nodes = tree["nodes"]
        doc += f"\n## 树文件节点 ({len(nodes)} 个)\n\n"
        doc += "| 节点 | 权重 | 五行 |\n"
        doc += "|------|------|------|\n"
        for n in nodes[:20]:  # 最多 20 个
            wx = n.get("wuxing") or "—"
            w = n.get("weight", 0)
            doc += f"| {n.get('name', n.get('id', '?'))} | {w} | {wx} |\n"
        if len(nodes) > 20:
            doc += f"| ... | ... | ... |\n"
            doc += f"| *共 {len(nodes)} 个节点* | | |\n"

    return doc


def build_shell_nucleus(dashboard: dict) -> str:
    """生成 diagnostics/shell-nucleus.md"""
    shell_nuc = dashboard.get("shell_nucleus", {})
    four_layer = shell_nuc.get("four_layer", [])

    doc = okf_frontmatter(
        "DiagnosticReport",
        "壳核收敛诊断",
        "壳（BAAI 规划层）vs 核（arXiv 产出层）的五行画像差异与收敛判定",
        x_wuxing={
            "shell_sp": shell_nuc.get("S_p_shell", "?"),
            "nucleus_sp": shell_nuc.get("S_p_nucleus", "?"),
            "sp_diff": shell_nuc.get("S_p_diff", "?"),
            "cosine_similarity": shell_nuc.get("cosine_similarity", "?"),
            "l1_divergence": shell_nuc.get("l1_divergence", "?"),
            "convergence": "maintained" if shell_nuc.get("S_p_diff", 99) < 5 else "diverging",
        },
    )

    doc += f"""# 壳核收敛诊断

## 核心结论

壳核 S_p 收敛维持（绝对差 {shell_nuc.get('S_p_diff', '?')} < 5 点），"同一存在度"确认为真信号。

## 壳核对比

| 维度 | 壳（BAAI） | 核（arXiv） |
|------|-----------|------------|
| S_p | {shell_nuc.get('S_p_shell', '?')} | {shell_nuc.get('S_p_nucleus', '?')} |
| 主导行 | 水 | 土 |

### 壳五行画像

| 五行 | 占比 |
|------|------|
"""
    for wx in ["木", "火", "土", "金", "水"]:
        pct = shell_nuc.get("shell_wuxing", {}).get(wx, 0)
        doc += f"| {wx} | {pct:.1f}% |\n"

    doc += f"""
### 核五行画像

| 五行 | 占比 |
|------|------|
"""
    for wx in ["木", "火", "土", "金", "水"]:
        pct = shell_nuc.get("nucleus_wuxing", {}).get(wx, 0)
        doc += f"| {wx} | {pct:.1f}% |\n"

    doc += f"""
## 四层水梯度

| 层 | 源 | 角色 | 水占比 | 主导行 |
|----|-----|------|--------|--------|
"""
    for layer in four_layer:
        doc += f"| {layer.get('layer', '?')} | {layer.get('source', '?')} | {layer.get('role', '?')} | {layer.get('water', '?')}% | {layer.get('dominant', '?')} |\n"

    return doc


def build_wuxing_profile(dashboard: dict) -> str:
    """生成 diagnostics/wuxing-profile.md"""
    monthly = dashboard.get("monthly", [])

    doc = okf_frontmatter(
        "DiagnosticReport",
        "五行画像诊断",
        "四源五行分布、阶段判定与演化路径",
    )
    doc += "# 五行画像诊断\n\n"

    for rec in monthly:
        src = rec["source"]
        label = SOURCE_META.get(src, {}).get("name", src)
        wuxing = rec.get("wuxing", {})
        evo = rec.get("evolution", {})

        doc += f"## {label}\n\n"
        doc += f"- 主导行: **{rec.get('dominant', '?')}**\n"
        doc += f"- S_p: {rec.get('S_p', '?')}\n"
        doc += f"- 演化路径: {evo.get('path', '?')}\n"
        doc += f"- 节点数: {rec.get('n_nodes', '?')}\n\n"

        doc += "| 五行 | 占比 |\n|------|------|\n"
        for wx in ["木", "火", "土", "金", "水"]:
            pct = wuxing.get(wx, 0)
            doc += f"| {wx} | {pct:.1f}% |\n"
        doc += "\n"

    return doc


def build_monthly_index(dashboard: dict) -> str:
    """生成 monthly/index.md"""
    task_data = dashboard.get("task_overview", {})
    tasks = task_data.get("tasks", {})

    doc = okf_frontmatter(
        "DirectoryListing",
        "月度快照 — 目录",
        "各月四源数据采集与诊断摘要",
    )
    doc += "# 月度快照\n\n"

    TIER_LABELS = {
        "machine-confirmed": "⚙️ 机器确认",
        "human-reviewed": "👤 人工复核",
        "unverified": "❓ 未验证",
        "pending": "⏳ 待执行",
    }

    for month_str in sorted(tasks.keys(), reverse=True):
        month_tasks = tasks[month_str]
        doc += f"## {month_str}\n\n"
        doc += "| 源 | 状态 | 信任层级 | 操作建议 |\n"
        doc += "|----|------|----------|----------|\n"
        for src in ["baai", "arxiv", "github", "huggingface"]:
            t = month_tasks.get(src, {})
            status = t.get("status", "?")
            action = t.get("action", "?")
            tier = t.get("trust_tier", "unverified")
            label = SOURCE_META.get(src, {}).get("name", src)
            status_icon = {"executed": "✓", "to_confirm": "⚠", "pending": "○", "failed": "❌"}.get(status, "?")
            tier_label = TIER_LABELS.get(tier, tier)
            doc += f"| {label} | {status_icon} {status} | {tier_label} | {action} |\n"
        doc += "\n"

    return doc


# ============================================================
# 主流程
# ============================================================

def export_okf(month: str = None, output_dir: Path = None) -> Path:
    """
    导出 OKF Bundle。

    Args:
        month: 月份 YYYY-MM（默认最近完整月）
        output_dir: 自定义输出目录（默认 output/archive/okf_{month}/）

    Returns:
        输出目录路径
    """
    if month is None:
        now = datetime.now()
        month = f"{now.year}-{now.month - 1:02d}" if now.month > 1 else f"{now.year - 1}-12"

    if output_dir is None:
        output_dir = ARCHIVE_DIR / f"okf_{month}"

    print(f"OKF 导出 — 月份: {month}")
    print(f"输出目录: {output_dir}")

    # 加载数据（优先前端目录，fallback 到后端输出目录）
    dashboard = load_json(FRONTEND_DATA) or load_json(BACKEND_DATA)
    if not dashboard:
        print(f"❌ 仪表盘数据缺失: {FRONTEND_DATA} 或 {BACKEND_DATA}")
        print("   请先运行 run_pipeline.py 或 build_dashboard_data.py 生成数据")
        sys.exit(1)

    # 加载前端桥接的已验证任务（human-reviewed 状态）
    verified_tasks = load_json(VERIFIED_FILE) or {}
    if verified_tasks:
        # 合并 human-reviewed 到 task_overview
        task_overview_raw = dashboard.get("task_overview", {})
        tasks = task_overview_raw.get("tasks", {})
        merged_count = 0
        for mon_str, mon_tasks in tasks.items():
            for src, info in mon_tasks.items():
                key = f"{mon_str}|{src}"
                if key in verified_tasks:
                    info["trust_tier"] = "human-reviewed"
                    info["verified"] = info.get("verified", []) + [verified_tasks[key]]
                    merged_count += 1
        # 重算 trust_tiers_summary
        if merged_count > 0:
            tt_summary = {"machine_confirmed": 0, "unverified": 0, "human_reviewed": 0, "pending": 0}
            for mon_data in tasks.values():
                for info in mon_data.values():
                    tt = info.get("trust_tier", "unverified")
                    if tt == "machine-confirmed":
                        tt_summary["machine_confirmed"] += 1
                    elif tt == "human-reviewed":
                        tt_summary["human_reviewed"] += 1
                    elif tt == "unverified":
                        tt_summary["unverified"] += 1
                    elif info.get("status") == "pending":
                        tt_summary["pending"] += 1
            task_overview_raw["trust_tiers"] = tt_summary
        print(f"  桥接 {merged_count} 条 human-reviewed 确认记录")

    trees = load_tree_files(month)

    # 加载 .knowledgeignore 忽略规则
    ignore_patterns = load_knowledgeignore()
    if ignore_patterns:
        print(f"  加载 .knowledgeignore: {len(ignore_patterns)} 条规则")
    skipped = []
    total = 0

    def _write(rel_path: str, content: str):
        """写入文件，若被 .knowledgeignore 忽略则跳过"""
        nonlocal skipped, total
        total += 1
        if is_ignored(rel_path, ignore_patterns):
            skipped.append(rel_path)
            print(f"  ⊘ {rel_path} (忽略)")
            return
        (output_dir / rel_path).write_text(content, encoding="utf-8")
        print(f"  ✓ {rel_path}")

    # 创建目录结构
    dirs = [
        output_dir,
        output_dir / "domains",
        output_dir / "diagnostics",
        output_dir / "monthly",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    # 生成文档
    monthly = dashboard.get("monthly", [])
    task_overview = dashboard.get("task_overview", {})
    sources_with_data = {r["source"] for r in monthly}

    print(f"\n生成文档...")

    # index.md
    _write("index.md", build_index(dashboard, month))

    # log.md
    _write("log.md", build_log(dashboard, month))

    # domains/
    _write("domains/index.md", build_domain_index(dashboard, month, task_overview))

    for src in ["baai", "arxiv", "github", "huggingface"]:
        rec = next((r for r in monthly if r["source"] == src), None)
        if rec:
            _write(f"domains/{src}.md",
                   build_domain_concept(src, rec, trees, month, task_overview))

    # diagnostics/
    _write("diagnostics/shell-nucleus.md", build_shell_nucleus(dashboard))
    _write("diagnostics/wuxing-profile.md", build_wuxing_profile(dashboard))

    # monthly/
    _write("monthly/index.md", build_monthly_index(dashboard))

    # 统计
    md_count = len(list(output_dir.rglob("*.md")))
    print(f"\n{'=' * 60}")
    print(f"  OKF Bundle 导出完成: {md_count} 个 .md 文件")
    if skipped:
        print(f"  已忽略: {len(skipped)} 个文件 ({', '.join(skipped)})")
    print(f"  目录: {output_dir}")
    print(f"{'=' * 60}")

    return output_dir


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="OKF v0.2 导出器 — 知识树诊断数据 → Open Knowledge Format Bundle",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python export_okf.py                          # 默认最近月
  python export_okf.py --month 2026-08          # 指定月份
  python export_okf.py --output-dir ./my_okf    # 自定义输出目录
        """
    )
    parser.add_argument("--month", default=None,
                        help="月份 YYYY-MM（默认最近完整月）")
    parser.add_argument("--output-dir", default=None, type=Path,
                        help="自定义输出目录（默认 output/archive/okf_{month}/）")

    args = parser.parse_args()
    export_okf(month=args.month, output_dir=args.output_dir)


if __name__ == "__main__":
    main()