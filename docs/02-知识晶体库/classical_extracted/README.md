# 经典晶体库 · 数据与文档包（README）

**版本**: V1.0
**日期**: 2026-08-11
**用途**: 供生产侧参考——S2 经典晶体化 + S3 体证卡片的数据地基与设计依据

---

## 一、包内结构

```
经典晶体库_数据与文档包/
├── data/                              # 数据资产
│   ├── daojing_database_v2.json        # ★ 81章结构化（SPO 572条 + 镜鉴648条目 + 原文/概念）
│   ├── daily_mirror_metadata_v2.0.txt  #   原始 js（含 keywordIndexV2 触发词索引）
│   ├── 《道德经》镜鉴反馈库20251224.xlsx #   10章富化反馈库（80条 × 13字段）
│   └── 第01-09章_五步读解.md            #   五步读解示例（生产侧需补全 81 章）
├── prompts/                           # 提示词（已按确认微调固化）
│   ├── 五步协同读解_提示词.md            # 炼章：矛盾迭代 × 五步读解 × 晶体铸造
│   └── SPO三元组提取_提示词.md          # 铸晶：原子化 + 谓词规范 + SPO V3.0 契约
└── docs/                              # 设计文档
    ├── daojingDatabaseV2_完整数据评估.md  # ★ 数据画像与 S2/S3 主源定案
    ├── 道德经数据源_三源评估与归一提案.md   # PRP-2026-007
    ├── 镜鉴反馈库_评估与S3设计升级.md      # PRP-2026-008
    ├── 知识晶体库_三方融合提案.md         # PRP-2026-005（母提案）
    ├── 晶体Schema与PhaseB_接口契约.md    # IF-2026-006（晶体格式契约）
    └── S2_交付报告.md                   # S2 交付记录
```

---

## 二、数据资产速览

| 数据 | 规模 | 用途 | 备注 |
|------|:----:|------|------|
| daojing_database_v2.json | 81 章 | S2 结构源 + S3 镜鉴主源 | **解析后的 JSON**（原始 js 的 raw_decode 产物） |
| daily_mirror_metadata_v2.0.txt | 81 章 js | 原始数据 | 含 keywordIndexV2（文件尾 767 字符） |
| 镜鉴反馈库 xlsx | 10 章 × 8 条 = 80 条 | S3 富化增强 | 13 字段（含 Action Category/Status） |
| 五步读解 md | 01-09 章 | S2 正文源 | **生产侧需补全 81 章** |

**daojingDatabaseV2 关键画像**（详见评估文档）：
- 章节：81 章（chapter_title/original_text/core_concepts/relation_network/dimensions/empowerment/spo_triples）
- **SPO：572 条**（格式符合 SPO V3.0 契约——可直接作 x-compute 资产）
- **镜鉴矩阵：648/648 条目**（81章×4维×2级×4字段：triggers/insight_desc/action_desc/reflection）——S3 主源全量
- daily_mirror：15 章有值（1-9、13-15、25-27）
- concept_cards/dq_dimensions：位于 empowerment 下（81 章）

---

## 三、生产侧接入步骤（建议）

```
S2 经典晶体化（build_classical_crystals.py v0.2）：
  1. 输入：五步读解.md（81章）+ daojing_database_v2.json + chapters/*.html（可选）
  2. 解析：五步读解（正文） + daojingDatabaseV2（raw_decode 取结构字段）
  3. 输出：ClassicalInsight 晶体（正文五步 + x-compute.spo + x-mirror 钩子）

S3 体证卡片（TizhengCard v0.2）：
  1. 镜鉴源：daojingDatabaseV2.dimensions（主源）+ xlsx（富化）+ daily_mirror（精选）
  2. 数据流：事件 → 四维自评 → 最低维度 → 关联镜鉴条目 → 反馈 → 践行 → 体证 → 回流
```

---

## 四、待办清单（生产侧）

| # | 项 | 优先级 |
|---|-----|:------:|
| 1 | 补全 81 章五步读解.md（当前仅 01-09 示例） | P0（S2 正文源） |
| 2 | build_classical_crystals.py v0.2 实施（三源解析归一） | P0 |
| 3 | 维度→五行映射定案（时/宇/识/缘 → 木火土金水） | P1（S3 前置） |
| 4 | xlsx 富化字段（Action Category）回注 ClassicalInsight（x-application） | P1 |
| 5 | 反馈库扩展：xlsx 10章 → 81章（复用提示词流水线生成富化条目） | P2 |

---

## 五、关键设计纪律（勿违背）

1. **Base 铁律**：只组织，不生产——晶体封装已有知识，不创造新知识
2. **引用不复制**：晶体 x-compute.ref 指向计算层，不内嵌大数据
3. **draft 无 verified**：AI 初审（status=draft）不冒充已验证；导师确认后 current + verified: human:<id>
4. **契约先行**：晶体格式遵循 IF-2026-006；SPO 遵循提示词输出契约（context 必填）
5. **KSMG G6**：模块间接口契约 + import 冒烟——quality_gate 教训
