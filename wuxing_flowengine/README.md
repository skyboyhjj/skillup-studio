# 五行道境流引擎 (Wuxing Dao-Realm Flow Engine)

基于五行（金木水火土）哲学框架的 AI 研究领域趋势诊断与追踪系统。将 AI 前沿概念映射到五行体系，通过多阶段管道分析认知深度、领域分布和道境演化阶段。

## 核心概念

- **五行映射**：将 AI 概念（如"强化学习""扩散模型""多模态大模型"）映射到木/火/土/金/水五行
- **三层 Spinor 结构**：种子层 (L1) → 现行层 (L2) → 超越层 (L3/L4)，模拟认知深度演化
- **四维道境读数**：O_t（本体稳定性）、E_u（演化不确定性）、C_k（认知耦合度）、K_y（缘位/因果纠缠度）
- **五阶段判定**：生 → 克 → 化 → 通 → 变，诊断领域所处道境阶段
- **双层标注**：同一概念在不同认知层级可具有不同的五行投影

## 项目结构

```
wuxing_flowengine/
├── config/                          # 配置文件
│   └── config_default.json          # 默认配置（阈值、诊断模式等）
├── data/                            # 数据
│   └── snapshots/                   # 快照数据（按月独立）
│       ├── 2026-05-30_snapshot.json # 5月 (278 节点, 476 边)
│       ├── 2026-06-30_snapshot.json # 6月 (290 节点, 525 边)
│       ├── 2026-07-30_snapshot.json # 7月 (302 节点, 662 边) [基准]
│       └── 2026-08-30_snapshot.json # 8月 (311 节点, 687 边)
├── diagnose/                        # 诊断模块
│   └── wuxing_diagnose_v2.py        # 五行诊断引擎（环分析、熵、罗盘）
├── scripts/                         # 核心脚本
│   ├── monthly_pipeline.py          # 月度编排器入口（主入口）
│   ├── phase1_pipeline.py           # Phase 1: 认知深度估算 + 五行映射 + 道境诊断
│   ├── phase2_pipeline.py           # Phase 2: 双层标注 + Spinor 层构建 + 领域追踪
│   ├── phase3_plus_pipeline.py      # Phase 3+: 论文五行分类 + 领域漂移分析
│   ├── dao_realm_engine.py          # 道境融合诊断引擎（统一入口）
│   ├── stage_engine.py              # 阶段判定引擎（生/克/化/通/变）
│   ├── timeseries_analysis.py       # 时间序列分析（多月份趋势对比）
│   ├── domain_calibration.py        # 领域基准校准（跨领域 S 值归一化）
│   ├── k_y_enhancer.py              # K_y 缘位增强（图密度混合 E_relation）
│   ├── edge_generator.py            # 边生成器（概念间关系构建）
│   ├── wuxing_dsl.py                # 五行 DSL 引擎（生克规则 + 画像库）
│   ├── guidance.py                  # 导航建议生成
│   ├── data_validator.py            # 数据质量验证（五检查点）
│   ├── baai_scraper.py              # BAAI Hub 论文采集
│   ├── build_snapshot.py            # 快照构建器
│   ├── gen_monthly_snapshots.py     # 月度快照模拟生成
│   └── validator.py                 # 输出合法性验证
├── tests/                           # 测试
│   ├── test_cases.py                # 自动化验证脚本
│   ├── xiaohe_case.json             # 小禾案例测试数据
│   ├── kongzi_case.json             # 孔子案例测试数据
│   └── daodejing_concepts.json      # 道德经概念测试数据
└── output/                          # 输出（按月份归档）
    ├── papers_2026-05.json          # 2026-05 论文数据
    ├── papers_2026-06.json          # 2026-06 论文数据
    ├── papers_2026-07.json          # 2026-07 论文数据
    ├── domain_calibration_baseline.json  # 领域校准基线
    ├── validation_report_2026-08.md      # 验证报告
    ├── pipeline_comparison_report.md     # 流水线对比报告
    └── archive/
        ├── 2026-05/                 # 2026-05 月度归档
        ├── 2026-06/                 # 2026-06 月度归档
        ├── 2026-07/                 # 2026-07 月度归档
        └── 2026-08/                 # 2026-08 月度归档
```

## 快速开始

### 环境要求

- Python 3.10+
- 仅使用标准库（无外部依赖）

### 运行完整月度管道

```bash
cd wuxing_flowengine
python scripts/monthly_pipeline.py --month 2026-08
```

### 管道阶段

| 阶段 | 说明 | 输出 |
|------|------|------|
| Phase 1 | 认知深度估算 + 五行映射 + 三层构建 + 道境四维诊断 | `phase1_diagnosis_{month}.json` |
| Phase 2 | 双层标注 + Spinor 层构建 + 领域追踪 | `phase2_diagnosis_{month}.json` |
| Phase 3+ | 论文五行分类 + 领域漂移分析（余弦距离） | `phase3_plus_diagnosis_{month}.json` |
| 时间序列 | 多月份趋势对比分析 | `phase3_timeseries_diagnosis_{month}.json` |
| 验证 | 数据质量五检查点（语言/数量/覆盖/重复/一致性） | 控制台输出 + `validation_report_*.md` |

### 跳过特定阶段

```bash
python scripts/monthly_pipeline.py --month 2026-08 --skip phase3,phaseC1
```

### 运行测试

```bash
cd wuxing_flowengine
python tests/test_cases.py
```

## 输出格式 (V1.2)

所有报告统一包含以下字段：

```json
{
  "report_type": "phase1_diagnosis",
  "version": "V1.2",
  "generated_at": "2026-08-04T16:54:26.623727",
  ...
}
```

## 五行分类规则

| 五行 | 象征 | 覆盖领域 |
|------|------|----------|
| 木 | 生成、生长 | 具身智能与机器人、多模态智能、生成式 AI |
| 火 | 交互、协作 | 智能体、推荐系统与信息检索、交叉领域智能应用 |
| 土 | 基础、承载 | 机器学习基础、AI 系统与硬件、软件工程与编程 |
| 金 | 安全、逻辑 | 安全可信与伦理、知识表示与逻辑推理 |
| 水 | 流动、知识 | 大语言模型、自然语言处理、计算机视觉、科学 AI |

## 道境五阶段

| 阶段 | 特征 | 导航建议 |
|------|------|----------|
| 生 | 新生萌芽，五行初生 | 蓄势待发，温和培育 |
| 克 | 层间张力，冲突显现 | 正视冲突，不可回避 |
| 化 | 冲突化解，体系融合 | 顺势而为，保持平衡 |
| 通 | 体系贯通，流转自如 | 巩固成果，防止回退 |
| 变 | 根本性转变，范式跃迁 | 拥抱变化，重构框架 |

## 当前诊断结果

| 月份 | 道境阶段 | O_t | E_u | C_k | K_y | 存在度 S | 节点 | 边 |
|------|----------|-----|-----|-----|-----|----------|------|-----|
| 2026-05 | 克 | 0.2717 | 0.9665 | 0.2205 | 0.2867 | 1.7 | 278 | 476 |
| 2026-06 | 克 | 0.2691 | 0.9645 | 0.2214 | 0.2876 | 1.7 | 290 | 525 |
| 2026-07 | 克 | 0.2708 | 0.9649 | 0.2209 | 0.2887 | 1.7 | 302 | 662 |
| 2026-08 | 克 | 0.2751 | 0.9666 | 0.2193 | 0.2908 | 1.7 | 311 | 687 |

> 验证日期：2026-08-05 · V1.2 流水线 · 四个月度独立快照 · 全线通过（含 P0/P1/P2 修复）

### 时间序列趋势 (2026-05 → 2026-08)

| 维度 | 趋势 | 说明 |
|------|------|------|
| O_t | +0.0034 ↑ | 时位有序度稳步上升 |
| E_u | +0.0001 → | 宇位均衡度基本稳定 |
| C_k | -0.0012 ↓ | 识位耦合度轻度松弛 |
| K_y | +0.0041 ↑ | 缘位关系密度持续增长 |

> ⚠️ **数据边界**：仅 2026-07 为真实 API 快照（hub.baai.ac.cn），其余 3 个月为模拟演化数据。四维指标的"趋势"（如 K_y +0.0041 上升）反映模拟参数的一致性，真实月度变化幅度待接入真实 API 后验证。完整验证结果见 `output/validation_report_2026-08.md`。

## License

MIT