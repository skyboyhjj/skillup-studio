# -*- coding: utf-8 -*-
"""
知识晶体导出器 v1.0

将知识树追踪引擎的诊断数据封装为独立的知识晶体文件（Markdown + YAML frontmatter）。
晶体 = OKF 结构层（可验证）× 五行语义层（可诊断）× 引用计算层（可计算）。

设计原则:
  - 引用不复制：x-compute.ref 指向 engine_v2_series.json，不复制数据
  - 两级验证：verified 分 process:quality-gate（机器）和 human:<id>（人工）
  - 生命周期：status 从 draft → current → deprecated → retired
  - Base 铁律：只组织，不生产——封装已有知识，不创造新知识

用法:
    python export_crystals.py                          # 全量导出
    python export_crystals.py --source arxiv           # 单源导出
    python export_crystals.py --output-dir ./my_crystals  # 自定义输出目录
"""

import argparse
import json
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# ============================================================
# 路径配置
# ============================================================

SCRIPTS_DIR = Path(__file__).parent.resolve()
PROJECT_DIR = SCRIPTS_DIR.parent.resolve()
REPO_ROOT = PROJECT_DIR.parent.resolve()
OUTPUT_DIR = PROJECT_DIR / "output"
CRYSTALS_DIR = OUTPUT_DIR / "crystals"
DIAGNOSE_DIR = PROJECT_DIR / "diagnose"
CONFIG_DIR = PROJECT_DIR / "config"
FRONTEND_DATA = REPO_ROOT / "hui-skill-product-matrix" / "data" / "dashboard_data.json"
BACKEND_DATA = OUTPUT_DIR / "dashboard_data.json"
VERIFIED_FILE = OUTPUT_DIR / "verified_tasks.json"
ENGINE_SERIES = DIAGNOSE_DIR / "engine_v2_series.json"
CANONICAL_MAPPING = CONFIG_DIR / "canonical_wuxing_mapping.json"
CRYSTALIGNORE_FILE = REPO_ROOT / ".crystalignore"
QUALITY_REPORT = OUTPUT_DIR / "quality_report.json"

# 校验常量（对齐 IF-2026-006 §2.4）
WUXING_ORDER = ["木", "火", "土", "金", "水"]
VALID_TYPES = ["KnowledgeDomain", "DiagnosisResult", "ClassicalInsight", "TizhengCard"]
VALID_VERIFIED = re.compile(r"^(process:[a-z-]+|human:[a-z0-9_-]+)$")

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

# 五行标签
WUXING_LABELS = {
    "木": "Wood (生长/创新)",
    "火": "Fire (扩散/爆发)",
    "土": "Earth (稳定/整合)",
    "金": "Metal (收敛/结构化)",
    "水": "Water (流动/适应)",
}

# 四维指标含义
DIM4_LABELS = {
    "O_t": "本体论深度（主导行集中度）",
    "E_u": "认识论均匀度（五行分布熵）",
    "C_k": "因果激活度（层间生克边数）",
    "K_y": "缘位协调度（五行互补性）",
    "S_p": "存在度（P忠恕中道，p=0.5）",
}


# ============================================================
# 数据加载
# ============================================================

def load_json(path: Path) -> Optional[dict]:
    """加载 JSON 文件，不存在返回 None"""
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


# ============================================================
# .crystalignore — 晶体导出忽略规则
# ============================================================

def load_crystalignore(filepath: Path = None) -> list:
    """
    加载 .crystalignore 文件，返回编译后的模式列表。
    语法兼容 .gitignore：每行一个 glob 模式，# 注释，空行忽略，! 取反。
    """
    if filepath is None:
        filepath = CRYSTALIGNORE_FILE

    if not filepath.exists():
        return []

    patterns = []
    for line in filepath.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        comment_pos = line.find(" # ")
        if comment_pos >= 0:
            line = line[:comment_pos].strip()
        if line.startswith("#"):
            continue

        negated = False
        if line.startswith("!"):
            negated = True
            line = line[1:].strip()

        is_dir = line.endswith("/")
        if is_dir:
            line = line[:-1]

        regex = _glob_to_regex(line)
        patterns.append((re.compile(regex), negated, is_dir))

    return patterns


def _glob_to_regex(pattern: str) -> str:
    """将 glob 模式转换为正则表达式"""
    if pattern.startswith("/"):
        pattern = pattern[1:]
        anchored = True
    else:
        anchored = False

    parts = pattern.split("**")
    regex_parts = []
    for i, part in enumerate(parts):
        if i > 0:
            regex_parts.append(r"(?:.*/)?")
        escaped = re.escape(part)
        escaped = escaped.replace(r"\*", "[^/]*")
        escaped = escaped.replace(r"\?", "[^/]")
        regex_parts.append(escaped)

    regex = "".join(regex_parts)
    if anchored:
        regex = "^" + regex
    else:
        regex = "(?:^|.*/)" + regex
    regex += "(?:/.*)?$"
    return regex


def is_ignored(rel_path: str, patterns: list) -> bool:
    """检查相对路径是否应被忽略"""
    ignored = False
    for regex, negated, is_dir in patterns:
        if regex.search(rel_path):
            ignored = not negated
    return ignored


# ============================================================
# YAML frontmatter 生成
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
                if any(c in sv for c in ['"', '\\', '\n', ':']):
                    result.append(f'{prefix}{sk}: "{sv}"')
                else:
                    result.append(f"{prefix}{sk}: {sv}")
            elif isinstance(sv, bool):
                result.append(f"{prefix}{sk}: {'true' if sv else 'false'}")
            else:
                result.append(f"{prefix}{sk}: {sv}")
        return result
    if isinstance(v, list):
        if not v:
            return [f"{prefix}[]"]
        if all(not isinstance(item, (dict, list)) for item in v):
            items = ", ".join(str(item) for item in v)
            return [f"{prefix}[{items}]"]
        result = []
        for item in v:
            if isinstance(item, dict):
                result.append(f"{prefix}-")
                result.extend(_yaml_value(item, indent + 1))
            else:
                result.append(f"{prefix}- {item}")
        return result
    if isinstance(v, str):
        if any(c in v for c in ['"', '\\', '\n']):
            return [f'{prefix}"{v}"']
        return [f"{prefix}{v}"]
    if isinstance(v, bool):
        return [f"{prefix}{'true' if v else 'false'}"]
    return [f"{prefix}{v}"]


def crystal_frontmatter(type_: str, title: str, description: str = "",
                        generated_by: str = "export_crystals.py/1.0",
                        **extra) -> str:
    """生成晶体 YAML frontmatter"""
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
    for k, v in extra.items():
        if v is None:
            continue
        if isinstance(v, (dict, list)):
            lines.append(f"{k}:")
            lines.extend(_yaml_value(v, 1))
        elif isinstance(v, bool):
            lines.append(f"{k}: {'true' if v else 'false'}")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines) + "\n"


# ============================================================
# frontmatter 校验（对齐 IF-2026-006 §2.4）
# ============================================================

def validate_fields(fields: dict) -> list:
    """
    晶体 frontmatter 校验。

    检查项：
      1. 必填字段：type / title / status
      2. type 合法性：∈ VALID_TYPES
      3. verified.by 格式：process:xxx 或 human:xxx
      4. x-wuxing.dominant 合法性：∈ 五行
      5. x-wuxing.sp 范围：[0, 100]

    Returns:
        错误消息列表，空列表表示通过
    """
    errors = []
    for k in ["type", "title", "status"]:
        if not fields.get(k):
            errors.append(f"缺必填字段 {k}")
    if fields.get("type") and fields["type"] not in VALID_TYPES:
        errors.append(f"type 非法: {fields['type']}（合法值: {VALID_TYPES}）")
    if fields.get("verified"):
        verified_list = fields["verified"]
        if isinstance(verified_list, dict):
            verified_list = [verified_list]
        for v in verified_list:
            if isinstance(v, dict) and not VALID_VERIFIED.match(v.get("by", "")):
                errors.append(f"verified.by 非法: {v.get('by')}")
    wx = fields.get("x_wuxing") or {}
    if wx.get("dominant") and wx["dominant"] not in WUXING_ORDER:
        errors.append(f"x-wuxing.dominant 非法: {wx['dominant']}（合法值: {WUXING_ORDER}）")
    if wx.get("sp") is not None:
        try:
            sp_val = float(wx["sp"])
            if not (0 <= sp_val <= 100):
                errors.append(f"x-wuxing.sp 越界: {sp_val}（合法范围 [0, 100]）")
        except (ValueError, TypeError):
            errors.append(f"x-wuxing.sp 非数值: {wx['sp']}")
    return errors


# ============================================================
# 晶体生成
# ============================================================

def _extract_wuxing_from_record(record: dict) -> dict:
    """
    从 engine_v2_series.json 记录中提取五行占比。
    数据在 v2_extra.dim1_freq 中，格式为 {木: {count, pct}, ...}。
    返回 {木: pct, 火: pct, ...}，pct 为百分比数值（0-100）。
    """
    v2_extra = record.get("v2_extra", {})
    dim1 = v2_extra.get("dim1_freq", {})
    if dim1:
        return {
            wx: round(info.get("pct", 0) * 100, 1)
            for wx, info in dim1.items()
        }
    # fallback: 顶层 wuxing 字段（dashboard_data.json 格式）
    return record.get("wuxing", {})


def _extract_evolution_from_record(record: dict) -> dict:
    """
    从 engine_v2_series.json 记录中提取演化路径。
    数据在 v2_extra.dim3_profile 中。
    """
    v2_extra = record.get("v2_extra", {})
    dim3 = v2_extra.get("dim3_profile", {})
    if dim3:
        return {
            "path": dim3.get("path", "?"),
            "profile_match": dim3.get("matches_profile", False),
        }
    # fallback: 顶层 evolution 字段（dashboard_data.json 格式）
    return record.get("evolution", {})


def build_diagnosis_crystal(record: dict, source: str, months: list,
                            trust_tier: str = "unverified",
                            verified_events: list = None,
                            shell_nuc: dict = None) -> str:
    """
    生成 DiagnosisResult 晶体。

    Args:
        record: engine_v2_series.json 中的单条记录
        source: 数据源标识 (baai/arxiv/github/huggingface)
        months: 采集月份列表
        trust_tier: 信任层级 (unverified/machine-confirmed/human-reviewed)
        verified_events: 验证事件列表
        shell_nuc: 壳核收敛数据（用于壳/核源标注 shell_sp/nucleus_sp）
    """
    meta = SOURCE_META.get(source, {})
    wuxing = _extract_wuxing_from_record(record)
    evo = _extract_evolution_from_record(record)

    # 状态映射：信任层级 → 晶体 status
    tier_to_status = {
        "human-reviewed": "current",
        "machine-confirmed": "current",
        "unverified": "draft",
        "pending": "draft",
    }
    status = tier_to_status.get(trust_tier, "draft")

    # 标题
    title = f"{meta.get('name', source)} 领域月度画像"
    description = f"{meta.get('name', source)} 知识树节点诊断（{', '.join(months)}）"

    # x-wuxing
    x_wuxing = {
        "dominant": record.get("dominant", "?"),
        "sp": record.get("S_p", "?"),
        "stage": record.get("stage", "?"),
        "evolution": evo.get("path", "?"),
    }
    # 壳核标注：baai=壳, arxiv=核
    if shell_nuc:
        if source == "baai":
            x_wuxing["shell_sp"] = shell_nuc.get("S_p_shell", "?")
        elif source == "arxiv":
            x_wuxing["nucleus_sp"] = shell_nuc.get("S_p_nucleus", "?")

    # x-compute：引用不复制
    x_compute = {
        "ref": f"engine_v2_series.json#{source}",
        "c_k": record.get("C_k", 0),
        "k_y": record.get("K_y", 0),
    }

    # sources
    sources = [{
        "id": f"{source}-diagnosis-{months[-1]}",
        "resource": f"engine_v2_series.json",
        "usage_count": record.get("n_nodes", 0),
    }]

    # 构建 frontmatter
    extra = {
        "status": status,
        "sources": sources,
        "x_wuxing": x_wuxing,
        "x_compute": x_compute,
    }
    if verified_events:
        extra["verified"] = verified_events

    # frontmatter 校验（IF-2026-006 §2.4）
    validation_fields = {
        "type": "DiagnosisResult",
        "title": title,
        "status": status,
        "verified": verified_events,
        "x_wuxing": x_wuxing,
    }
    errors = validate_fields(validation_fields)
    if errors:
        print(f"  ⚠️ 晶体校验警告 [{source}]: {'; '.join(errors)}")

    doc = crystal_frontmatter(
        "DiagnosisResult",
        title,
        description,
        **extra,
    )

    # 正文
    doc += f"# {title}\n\n"
    doc += f"## 五行画像\n\n"
    doc += "| 五行 | 占比 | 含义 |\n"
    doc += "|------|------|------|\n"
    for wx, label in WUXING_LABELS.items():
        pct = wuxing.get(wx, 0)
        doc += f"| {wx} | {pct:.1f}% | {label} |\n"

    doc += f"\n## 四维指标\n\n"
    doc += "| 指标 | 值 | 含义 |\n"
    doc += "|------|-----|------|\n"
    for dim, label in DIM4_LABELS.items():
        val = record.get(dim, "?")
        doc += f"| {dim} | {val} | {label} |\n"

    doc += f"\n## 演化路径\n\n"
    doc += f"- 路径: {evo.get('path', 'N/A')}\n"
    doc += f"- 画像匹配: {evo.get('profile_match', 'N/A')}\n"
    doc += f"- 节点数: {record.get('n_nodes', 'N/A')}\n"
    doc += f"- 采集月份: {', '.join(months)}\n"

    # 信任层级
    tier_labels = {
        "human-reviewed": "👤 人工复核",
        "machine-confirmed": "⚙️ 机器确认（质量门通过）",
        "unverified": "❓ 未验证",
        "pending": "⏳ 待执行",
    }
    doc += f"\n## 信任层级\n\n"
    doc += f"- 当前状态: {tier_labels.get(trust_tier, trust_tier)}\n"
    if verified_events:
        doc += f"- 验证记录:\n"
        for ev in verified_events:
            doc += f"  - {ev.get('by', '?')} @ {ev.get('at', '?')}\n"

    # 数据来源
    doc += f"\n## 数据来源\n\n"
    doc += f"- 资源: {meta.get('resource', 'N/A')}\n"
    doc += f"- 类型: {meta.get('type', 'N/A')}\n"
    doc += f"- 计算层引用: `{x_compute['ref']}`\n"
    doc += f"\n> *晶体由 export_crystals.py 自动生成。Base 铁律：只组织，不生产。*\n"

    return doc


def build_crystal_index(crystals: list, shell_nuc: dict = None) -> str:
    """生成晶体索引 index.md"""
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

    doc = crystal_frontmatter(
        "KnowledgeDomain",
        "知识晶体库 — 索引",
        "可计算-可验证的知识晶体目录：DiagnosisResult / KnowledgeDomain / ClassicalInsight / TizhengCard",
        generated_by="export_crystals.py/1.0",
        status="current",
        sources=[{
            "id": "engine_v2_series",
            "resource": "engine_v2_series.json",
        }],
    )

    doc += "# 知识晶体库\n\n"
    doc += "> 知识晶体 = OKF 结构层（可验证）× 五行语义层（可诊断）× 引用计算层（可计算）\n\n"
    doc += f"> 生成时间: {now}\n\n"

    # 分类列出晶体
    by_type = {}
    for c in crystals:
        t = c.get("type", "other")
        by_type.setdefault(t, []).append(c)

    for type_name, type_label in [
        ("DiagnosisResult", "诊断结果"),
        ("KnowledgeDomain", "领域知识"),
        ("ClassicalInsight", "经典解读"),
        ("TizhengCard", "体证卡片"),
    ]:
        items = by_type.get(type_name, [])
        if not items:
            continue
        doc += f"## {type_label} ({len(items)})\n\n"
        for c in items:
            tier = c.get("trust_tier", "unverified")
            tier_icon = {"human-reviewed": "👤", "machine-confirmed": "⚙️", "unverified": "❓", "pending": "⏳"}.get(tier, "?")
            doc += f"- [{c['title']}]({c['path']}) — S_p={c.get('sp', '?')}, 主导行: {c.get('dominant', '?')} {tier_icon}\n"
        doc += "\n"

    if shell_nuc:
        doc += "## 壳核收敛\n\n"
        doc += f"- 壳 S_p: {shell_nuc.get('S_p_shell', 'N/A')} (BAAI)\n"
        doc += f"- 核 S_p: {shell_nuc.get('S_p_nucleus', 'N/A')} (arXiv)\n"
        doc += f"- 绝对差: {shell_nuc.get('S_p_diff', 'N/A')}\n"

    doc += "\n---\n"
    doc += "*晶体库由 export_crystals.py 自动生成。Base 铁律：只组织，不生产。*\n"
    return doc


def build_log_crystal(quality_verdict: str = None, crystal_count: int = 0) -> str:
    """生成 log.md — 导出日志"""
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    doc = crystal_frontmatter(
        "DiagnosisResult",
        "知识晶体库 — 导出日志",
        "晶体导出历史记录",
        generated_by="export_crystals.py/1.0",
        status="current",
    )
    doc += "# 导出日志\n\n"
    doc += f"- **{now}** — 晶体导出 v1.0\n"
    doc += f"  - 晶体数量: {crystal_count}\n"
    if quality_verdict:
        doc += f"  - 质量门判定: {quality_verdict}\n"
    doc += f"  - 格式: OKF v0.2（Markdown + YAML frontmatter）\n"
    doc += f"  - 原则: 引用不复制（x-compute.ref 指向计算层）\n"
    doc += "\n---\n"
    doc += "*此日志由 export_crystals.py 自动生成。*\n"
    return doc


# ============================================================
# 主流程
# ============================================================

def export_crystals(source_filter: str = None, output_dir: Path = None,
                    quality_path: Path = None) -> Optional[Path]:
    """
    导出知识晶体。

    Args:
        source_filter: 限定数据源（baai/arxiv/github/huggingface），None=全量
        output_dir: 自定义输出目录（默认 output/crystals/）
        quality_path: 质量报告路径（默认 output/quality_report.json）

    Returns:
        输出目录路径，质量门 fail 时返回 None
    """
    if output_dir is None:
        output_dir = CRYSTALS_DIR

    print(f"知识晶体导出器 v1.0")
    print(f"输出目录: {output_dir}")

    # 加载质量门报告（IF-2026-006 §四：fail 阻断）
    q_path = quality_path or QUALITY_REPORT
    quality = load_json(q_path)
    if quality:
        verdict = quality.get("verdict", "?")
        print(f"[质量门] verdict={verdict}（{q_path}）")
        if verdict == "fail":
            print("❌ 质量门 fail——阻断晶体导出（契约：缺 verified 不导出）")
            print("   先修复质量门问题或确认排除项后重跑")
            return None
    else:
        print("[质量门] 未找到 quality_report.json——晶体 verified 仅来自 dashboard/verified_tasks")
        verdict = None

    # 加载数据
    engine_data = load_json(ENGINE_SERIES)
    if not engine_data:
        print(f"❌ 诊断数据缺失: {ENGINE_SERIES}")
        print("   请先运行诊断管线生成 engine_v2_series.json")
        sys.exit(1)

    dashboard = load_json(FRONTEND_DATA) or load_json(BACKEND_DATA)
    verified_tasks = load_json(VERIFIED_FILE) or {}

    records = engine_data.get("records", [])
    if not records:
        print("❌ engine_v2_series.json 中无诊断记录")
        sys.exit(1)

    # 壳核数据
    shell_nuc = dashboard.get("shell_nucleus", {}) if dashboard else {}

    # 构建任务信任层级映射
    task_trust = {}
    if dashboard:
        task_overview = dashboard.get("task_overview", {})
        tasks = task_overview.get("tasks", {})
        for mon_str, mon_tasks in tasks.items():
            for src, info in mon_tasks.items():
                key = f"{mon_str}|{src}"
                tt = info.get("trust_tier", "unverified")
                # 合并 verified_tasks.json 中的 human-reviewed
                if key in verified_tasks:
                    tt = "human-reviewed"
                # 取最高信任层级
                existing = task_trust.get(src, ("unverified", []))
                tier_order = {"human-reviewed": 3, "machine-confirmed": 2, "unverified": 1, "pending": 0}
                if tier_order.get(tt, 0) > tier_order.get(existing[0], 0):
                    verified_events = info.get("verified", [])
                    if key in verified_tasks:
                        verified_events = verified_events + [verified_tasks[key]]
                    task_trust[src] = (tt, verified_events)

    # 加载 .crystalignore
    ignore_patterns = load_crystalignore()
    if ignore_patterns:
        print(f"  加载 .crystalignore: {len(ignore_patterns)} 条规则")

    # 创建目录
    dirs = [
        output_dir,
        output_dir / "diagnosis",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    # 生成晶体
    skipped = []
    total = 0
    crystals_meta = []

    def _write(rel_path: str, content: str):
        nonlocal skipped, total
        total += 1
        if is_ignored(rel_path, ignore_patterns):
            skipped.append(rel_path)
            print(f"  ⊘ {rel_path} (忽略)")
            return
        (output_dir / rel_path).write_text(content, encoding="utf-8")
        print(f"  ✓ {rel_path}")

    print(f"\n生成 DiagnosisResult 晶体...")

    for record in records:
        source = record.get("source", "")
        if source_filter and source != source_filter:
            continue

        months = record.get("months", [])
        trust_tier, verified_events = task_trust.get(source, ("unverified", []))

        content = build_diagnosis_crystal(
            record, source, months,
            trust_tier=trust_tier,
            verified_events=verified_events,
            shell_nuc=shell_nuc,
        )

        rel_path = f"diagnosis/{source}.md"
        _write(rel_path, content)

        crystals_meta.append({
            "type": "DiagnosisResult",
            "title": f"{SOURCE_META.get(source, {}).get('name', source)} 领域月度画像",
            "path": rel_path,
            "trust_tier": trust_tier,
            "sp": record.get("S_p", "?"),
            "dominant": record.get("dominant", "?"),
        })

    # 生成索引
    _write("index.md", build_crystal_index(crystals_meta, shell_nuc))

    # 生成日志
    _write("log.md", build_log_crystal(verdict, len(crystals_meta)))

    # 统计
    md_count = len(list(output_dir.rglob("*.md")))
    print(f"\n{'=' * 60}")
    print(f"  知识晶体导出完成: {md_count} 个 .md 文件")
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
        description="知识晶体导出器 v1.0 — 诊断数据 → 知识晶体（Markdown + YAML frontmatter）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python export_crystals.py                        # 全量导出
  python export_crystals.py --source arxiv         # 单源导出
  python export_crystals.py --output-dir ./my_crystals  # 自定义输出目录
        """
    )
    parser.add_argument("--source", default=None,
                    choices=["baai", "arxiv", "github", "huggingface"],
                    help="限定数据源（默认全量）")
    parser.add_argument("--quality", default=None, type=Path,
                        help="质量报告路径（默认 output/quality_report.json）")
    parser.add_argument("--output-dir", default=None, type=Path,
                        help="自定义输出目录（默认 output/crystals/）")

    args = parser.parse_args()
    export_crystals(source_filter=args.source, output_dir=args.output_dir,
                    quality_path=args.quality)


if __name__ == "__main__":
    main()