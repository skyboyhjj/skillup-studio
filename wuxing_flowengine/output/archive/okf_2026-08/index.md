---
type: KnowledgeBundle
title: 知识树追踪引擎 — 2026-08 月度诊断
description: 四源知识树月度快照：BAAI + arXiv + GitHub + HuggingFace，含五行诊断、壳核分析、水梯度
generated:
  by: pipeline_orchestrator/0.2
  at: 2026-08-10T21:20:23Z
okf_version: 0.2
x_wuxing:
  engine: "wuxing_diagnose_v2 (via EngineAdapterV2)"
  annotation: "v2"
  coeff: "v1.1_calibrated"
---
# 知识树追踪引擎 — 2026-08 月度诊断

## 数据源

| 源 | 类型 | 描述 |
|----|------|------|
| [BAAI Hub (智源社区)](https://hub.baai.ac.cn) | AcademicInstitution | 智源社区知识树与科研月报采集，月度汇总 |
| [arXiv](https://arxiv.org) | AcademicPreprint | arXiv AI 子领域月度论文采集，11 分类 |
| [GitHub](https://github.com) | CodeRepository | GitHub Topic 搜索月度采集，26 个 AI 主题 |
| [HuggingFace](https://huggingface.co) | ModelRepository | HuggingFace Models 月度采集，12 个 pipeline_tag |

## 诊断摘要

| 指标 | 壳（BAAI 规划层） | 核（arXiv 产出层） | 工程层（GitHub） | 模型层（HuggingFace） |
|------|-------------------|---------------------|-------------------|------------------------|
| **BAAI Hub (智源社区)** | S_p=7.48 |  | |
| arXiv | | S_p=8.45 | |
| GitHub | | | S_p=14.02 | |
| HuggingFace | | | S_p=13.72 | S_p=13.72 |

### 壳核收敛

- 壳 S_p: 7.48 (BAAI)
- 核 S_p: 8.45 (arXiv)
- 绝对差: 0.97 (< 5 点 -> 收敛维持)
- 余弦相似度: 0.891

### 任务概览

- 已执行: 11
- 待确认: 4
- 待执行: 1
- 失败: 0

### 信任层级（OKF 可信度模型）

- 机器确认 (machine-confirmed): 8
- 人工复核 (human-reviewed): 2
- 未验证 (unverified): 6
- 待执行 (pending): 0

> 信任层级体系: unverified -> machine-confirmed (质量门通过) -> human-reviewed (人工确认)
> 前端用户确认后，导出时将包含 verified 事件记录。

## 导航

- [领域诊断](domains/index.md) — 各领域五行画像与演化
- [壳核诊断](diagnostics/shell-nucleus.md) — 壳核收敛与四层水梯度
- [月度快照](monthly/index.md) — 各月四源数据摘要
- [更新日志](log.md) — 采集与诊断历史
