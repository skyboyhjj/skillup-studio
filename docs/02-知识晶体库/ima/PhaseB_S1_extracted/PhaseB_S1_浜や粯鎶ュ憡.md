# Phase B + S1 交付报告：质量门 × 晶体导出（并行设计）

**日期**: 2026-08-10
**依据**: 《晶体Schema与PhaseB_接口契约》（IF-2026-006）+ 知识晶体库提案 S1
**状态**: ✅ 并行设计完成，联调验证 7/7

---

## 1. 交付物清单

| 文件 | 说明 | 验证 |
|------|------|:----:|
| `晶体Schema与PhaseB_接口契约.md` | 接口契约（IF-2026-006）：晶体 Schema + 质量门输出规格 | ✅ |
| `data_validator.py` | Phase B 质量门（七检查点 × 三态 + 排除清单） | ✅ |
| `export_crystals.py` | S1 晶体导出器（OKF Bundle，引用不复制） | ✅ |
| `.collectignore` | 排除清单示例（静态图谱/大文件/日志） | ✅ |
| `verify/verify_crystal_link.py` | 联调验证（质量门三态 → 晶体导出） | ✅ 7/7 |

---

## 2. Phase B 质量门（data_validator.py）

### 2.1 七检查点 × 三态（本地实测）

```
✅ arxiv_ai 2026-06/07/08 → pass_with_warn
  [!] wuxing: 7/7 节点未标注（将按 canonical 映射）
  [·] schema/weight/volume/empty/annotation: pass
✅ huggingface 2026-08 → pass_with_warn
  [!] weight: weight=0 节点（废弃标签 hf:text-to-text）
  [!] truncation: 采集页数上限 2（可能截断）
⏭️ knowledge_tree_standardized.json → excluded（排除清单生效）
⚠️ knowledge_tree_raw.json → skip（非 dict 结构）
总判定: pass_with_warn + 6 条警告（自愈重试项）
```

### 2.2 三态语义（契约 §3.3）

| 状态 | 触发 | 下游行为 |
|------|------|----------|
| pass_all | 全检查过 | 正常流转 |
| pass_with_warn | 有警告（未标注/废弃标签/截断嫌疑/量级偏离） | 标记 + 自愈重试 |
| fail | 空月/全 0 伪数据/schema 残缺 | **阻断诊断与导出** |

### 2.3 输出 quality_report.json（verified 契约字段）

```json
{"month": "2026-08", "generated": "...", "checks": {...},
 "warnings": [...], "collectignore": [...], "verdict": "pass_with_warn"}
```

---

## 3. S1 晶体导出器（export_crystals.py）

### 3.1 OKF Bundle 产出（本地实测）

```
output/crystals/
├── index.md        # 总览（含质量门 verdict）
├── log.md          # 导出日志
└── diagnostics/
    └── arxiv.md    # DiagnosisResult 晶体
```

### 3.2 晶体样例（arxiv，实测输出）

```yaml
---
type: DiagnosisResult
title: arxiv 月度诊断
status: current
generated: { by: export_crystals.py/0.1, at: ... }
verified: { by: process:quality-gate, at: ... }   # ← 质量门写入
sources:
  - id: arxiv-2026-06 / resource: arxiv_tree_2026-06.json
x-wuxing: { dominant: 土, sp: 15.93, evolution: 土→土→土 }
x-compute: { ref: engine_v2_series.json#arxiv, c_k: 0.0, k_y: 0.2384 }
---
# arxiv 月度诊断
...（正文：人机共读 + 引用说明）
```

### 3.3 契约守卫（fail 阻断）

- quality_report.json verdict=fail → 导出器拒绝并提示"先修复质量门"
- verified 缺失（无质量报告）→ 晶体 verified 置空（不冒充已确认）

---

## 4. 联调验证（7/7）

| # | 场景 | 断言 |
|---|------|------|
| 1 | 质量门 pass → 晶体导出 | ✅ 导出成功 |
| 2 | verified 由质量门写入 | ✅ process:quality-gate |
| 3 | 引用不复制 | ✅ x-compute.ref |
| 4 | x-wuxing 完整 | ✅ dominant/sp |
| 5 | 空月识别 fail | ✅ verdict=fail |
| 6 | **fail 阻断导出** | ✅ 契约守卫生效 |
| 7 | 全链路无伪数据 | ✅ 无晶体时无输出 |

---

## 5. 与接口契约的符合性

| 契约项 | 实现 | 符合 |
|--------|------|:----:|
| verified 字段 | 质量门注入 → 晶体引用 | ✅ |
| status 语义 | warn→晶体 current+warning；fail→阻断 | ✅ |
| provenance | metadata 校验（schema 检查点） | ✅ |
| 引用不复制 | x-compute.ref 指向计算层 | ✅ |
| 失败显式化 | fail 阻断 + 报告 + 守卫 | ✅ |

---

## 6. 生产接入指引

```powershell
# 1. 质量门（树文件目录）
python data_validator.py --dir output --write

# 2. 诊断（EngineAdapterV2，计算层）
python engine_adapter_v2.py --dir output

# 3. 晶体导出（OKF Bundle）
python export_crystals.py --series output/engine_v2_series.json --quality output/quality_report.json

# 或全链路（调度器后置步骤注册）
python pipeline_orchestrator.py && python data_validator.py --dir output --write && python export_crystals.py
```

---

## 7. 已知限制与下一步

| 限制 | 说明 | 下一步 |
|------|------|--------|
| 晶体仅覆盖 DiagnosisResult | KnowledgeDomain（domains/）与 ClassicalInsight（Base）未导出 | S2：Base 经典晶体化 |
| x-wuxing.stage 为占位"克" | 阶段判定未接入 stage_engine | 后续接入 |
| 体证卡片未实现 | TizhengCard 类型已定义（schema 预留） | S3：镜鉴入口 |
| 质量门 warning 自愈 | 警告记录但未自动重试 | 与调度器 --resume 衔接 |

---

## 8. 一句话结论

> **Phase B 与 S1 按接口契约并行设计完成并联调通过：质量门七检查点 × 三态（pass/warn/fail）+ 排除清单 + verified 契约字段；晶体导出器产出 OKF Bundle（引用不复制、fail 阻断守卫）。全链路 7/7 验证——质量门把好"知识可信"的门，晶体库把好"知识可交换"的形。契约 IF-2026-006 是两者唯一的接缝，联调零歧义。**

*验证可复跑: python verify/verify_crystal_link.py*
