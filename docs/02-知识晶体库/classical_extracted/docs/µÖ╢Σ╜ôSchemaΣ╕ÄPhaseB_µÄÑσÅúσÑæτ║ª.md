# 晶体 Schema 定稿 + Phase B 输出规格契约

**文档编号**: IF-2026-006（接口契约）
**日期**: 2026-08-10
**定位**: Phase B（质量门）与 S1（晶体导出）的接缝——双方都遵守此契约
**状态**: 定稿（可实施）

---

## 一、契约总览：数据流

```
四源树文件（schema v1.1 + metadata）
        │
        ▼
Phase B 质量门（data_validator.py）
  ├─ 七检查点 → pass/warn/fail（自愈三态）
  ├─ 排除清单（.collectignore）
  └─ 输出 quality_report.json + verified/provenance 注入树文件
        │
        ▼
EngineAdapterV2 诊断 → engine_v2_series.json（计算层，JSON 保留）
        │
        ▼
S1 晶体导出（export_crystals.py）
  ├─ 读：树文件（v1.1 metadata）+ engine_v2_series.json + quality_report.json
  ├─ 写：output/crystals/（OKF Bundle，引用不复制）
  └─ 输出：index.md / domains/ / diagnostics/ / monthly/ + .crystalignore
```

---

## 二、晶体 Schema（OKF v0.2 对齐）

### 2.1 晶体类型（type）

| type | 内容 | 来源 |
|------|------|------|
| `KnowledgeDomain` | 领域知识节点（如 CV/LLM） | 四源树节点 |
| `DiagnosisResult` | 诊断结果（S_p/五行/演化） | engine_v2_series.json |
| `ClassicalInsight` | 经典解读晶体（道德经等） | Base 层（S2） |
| `TizhengCard` | 体证卡片（用户践行） | 镜鉴入口（S3） |

### 2.2 晶体文件格式（每晶体一个 .md）

```yaml
---
type: KnowledgeDomain
title: 计算机视觉
description: CV 领域月度知识树节点画像
generated: { by: pipeline_orchestrator/0.2, at: 2026-08-10T21:00:00Z }
verified: { by: process:quality-gate, at: 2026-08-10T21:01:00Z }   # 或 human:<id>
sources:
  - id: arxiv-2026-08
    resource: arxiv_tree_2026-08.json
    usage_count: 2519
    last_modified: 2026-08-01
status: current                      # draft / current / deprecated / retired
x-wuxing:
  dominant: 水
  sp: 39.4
  stage: 克
  shell_sp: 7.48
  nucleus_sp: 8.45
  evolution: 木→水→水
x-compute:
  ref: engine_v2_series.json#arxiv   # 引用计算层，不复制数据
  c_k: 0.0
  k_y: 0.2079
---
正文（Markdown，人机共读）
```

### 2.3 Bundle 结构

```
output/crystals/
├── index.md                        # 晶体库总览（所有晶体索引）
├── log.md                          # 导出日志（版本/时间/变更）
├── domains/                        # KnowledgeDomain 晶体
│   ├── index.md
│   ├── computer-vision.md
│   └── ...
├── diagnostics/                    # DiagnosisResult 晶体
│   ├── index.md
│   ├── shell-nucleus.md
│   └── ...
└── monthly/                        # 月度快照晶体
    ├── index.md
    └── 2026-08.md
```

### 2.4 验证规则（导出器内置校验）

| 规则 | 说明 |
|------|------|
| frontmatter 必填 | type/title/status/generated 缺失 → 导出失败并报告 |
| verified 合法 | by ∈ {process:quality-gate, human:<id>} |
| x-wuxing 合法 | dominant ∈ 五元素；sp ∈ [0,100] |
| x-compute.ref 存在 | 引用的 JSON 路径可解析 |
| 引用不复制 | 正文不得内嵌计算层大数据（仅 ref） |

---

## 三、Phase B 输出规格（质量门契约）

### 3.1 质量报告 quality_report.json

```json
{
  "month": "2026-08",
  "generated": "2026-08-10T21:00:00Z",
  "checks": {
    "arxiv": {
      "schema": "pass", "wuxing": "pass", "weight": "pass",
      "volume": "warn", "empty": "pass", "truncation": "pass", "annotation": "pass"
    }
  },
  "warnings": ["arxiv 2026-08 为月中样本（2,519 vs 均值 12,000+）"],
  "collectignore": ["hf:text2text-generation"],
  "verdict": "pass_all" | "pass_with_warn" | "fail"
}
```

### 3.2 树文件 schema v1.1（metadata 注入）

```json
{
  "schema_version": "1.1",
  "source": "arxiv",
  "month": "2026-08",
  "metadata": {
    "collector": "arxiv_ai_collect.py v1.2",
    "collected_at": "2026-08-01T03:12:00Z",
    "annotation_version": "v2",
    "coeff_version": "v1.1_calibrated",
    "engine": "wuxing_diagnose_v2",
    "quality_gate": "pass_with_warn",
    "verified_at": "2026-08-10T21:01:00Z"
  },
  "nodes": [...]
}
```

### 3.3 自愈三态语义

| 状态 | 含义 | 下游行为 |
|------|------|----------|
| `pass` | 全部检查通过 | 正常进入诊断/导出 |
| `warn` | 有警告（降级继续） | 标记 warning，正常流转；下次运行自愈重试 |
| `fail` | 阻断（空月无回退/伪数据） | 不进诊断；调度器标记 failed 待重跑 |

### 3.4 排除清单 .collectignore

```
# 废弃标签（HF text2text-generation 全月 weight=0）
hf:text2text-generation
# 排除原始论文大文件
output/papers_*.json
# 临时运行日志
output/runs/*.json
```

---

## 四、接口契约（双方共同遵守）

| 契约项 | Phase B 承诺 | S1 承诺 |
|--------|--------------|---------|
| `verified` 字段 | 质量门通过后注入树文件 metadata | 晶体引用（verified: process:quality-gate） |
| `status` 语义 | warn → 晶体 status=warn（或 current+warning） | 按质量门结果映射 |
| provenance | metadata 完整（collector/annotation/coeff/engine） | 晶体 sources/generated 引用 |
| 引用不复制 | — | 晶体只 ref 计算层，不内嵌大数据 |
| 失败显式化 | fail 阻断 + 报告 | 无晶体导出（缺 verified 不导出） |

---

## 五、验收标准

- [ ] 晶体 Schema：4 种 type 均可导出，frontmatter 校验全过
- [ ] Phase B：七检查点输出 pass/warn/fail 三态 + quality_report.json
- [ ] 联调：质量门 warn 的月份 → 晶体 status 正确映射；fail 月份 → 无晶体
- [ ] 引用不复制：晶体文件大小 vs 计算层 JSON（晶体 << JSON）
- [ ] 可复跑：两次导出 diff 仅时间戳差异

*本契约是 Phase B 与 S1 并行开发的唯一接口——双方按此实现，联调时无歧义*
