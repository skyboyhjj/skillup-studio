# WRL 规则加载报告
> 生成时间: 2026-08-07 18:40:56
> 规则目录: `E:\00-TRAEWK\6a59e217b55e181ea97f0df3\wuxing_flowengine\scripts\..\rules`

## classical_rules.wrl (4 条规则)

| 规则 ID | 分类 | 名称 | 可修改性 | 校准状态 | 依赖数 | 有校验 | 有变更日志 |
|---------|------|------|----------|----------|--------|--------|-----------|
| `C-SHENG` | C | 五行相生关系 | immutable | ? | 0 | ✅ | ✅ |
| `C-KE` | C | 五行相克关系 | immutable | ? | 0 | ✅ | ✅ |
| `C-WX-COORD` | C | 五行方位坐标映射 | immutable | ? | 0 | ✅ | ✅ |
| `C-WX-ROLES` | C | 五行角色定义 | immutable | ? | 0 | ✅ | ✅ |

## domain_rules.wrl (4 条规则)

| 规则 ID | 分类 | 名称 | 可修改性 | 校准状态 | 依赖数 | 有校验 | 有变更日志 |
|---------|------|------|----------|----------|--------|--------|-----------|
| `D-SCHOLARLY` | D | 学术考据视角 | configurable | ? | 5 | ✅ | ✅ |
| `D-PRACTICAL` | D | 实践视角预设 | configurable | ? | 5 | ✅ | ✅ |
| `D-EDUCATIONAL` | D | 教育视角预设 | configurable | ? | 5 | ✅ | ✅ |
| `D-DEFAULT` | D | 默认配置 | configurable | ? | 5 | ✅ | ✅ |

## formal_rules.wrl (8 条规则)

| 规则 ID | 分类 | 名称 | 可修改性 | 校准状态 | 依赖数 | 有校验 | 有变更日志 |
|---------|------|------|----------|----------|--------|--------|-----------|
| `F-ENTROPY` | F | Shannon 熵计算 | immutable | ? | 1 | ✅ | ✅ |
| `F-CENTROID` | F | 五行质心坐标计算 | immutable | ? | 1 | ✅ | ✅ |
| `F-O_T` | F | 时位 O_t 映射公式 | calibratable | v1.0_initial | 2 | ✅ | ✅ |
| `F-E_U` | F | 宇位 E_u 映射公式 | calibratable | v1.0_initial | 2 | ✅ | ✅ |
| `F-C_K` | F | 识位 C_k 映射公式 | calibratable | v1.0_initial | 1 | ✅ | ✅ |
| `F-K_Y` | F | 缘位 K_y 映射公式 | calibratable | v1.0_initial | 2 | ✅ | ✅ |
| `F-S_P` | F | 存在度 S_p 广义平均公式 | calibratable | v1.0_initial | 4 | ✅ | ✅ |
| `F-THETA` | F | 临界阈值 θ_critical 计算公式 | calibratable | v1.0_initial | 1 | ✅ | ✅ |

## heuristic_rules.wrl (19 条规则)

| 规则 ID | 分类 | 名称 | 可修改性 | 校准状态 | 依赖数 | 有校验 | 有变更日志 |
|---------|------|------|----------|----------|--------|--------|-----------|
| `H-DOMINANCE` | H | 主导判定阈值 | calibratable | v1.0_initial | 0 | ✅ | ✅ |
| `H-SCARCITY` | H | 稀缺判定阈值 | calibratable | v1.0_initial | 0 | ✅ | ✅ |
| `H-ENTROPY-CLASS` | H | 熵值分类阈值 | calibratable | v1.0_initial | 1 | ✅ | ✅ |
| `H-STAGE-SHENG` | H | 生阶段判定 | ? | ? | 2 | ✅ | ✅ |
| `H-STAGE-KE` | H | 克阶段判定 | ? | ? | 2 | ✅ | ✅ |
| `H-STAGE-HUA` | H | 化阶段判定 | ? | ? | 2 | ✅ | ✅ |
| `H-STAGE-TONG` | H | 通阶段判定 | ? | ? | 2 | ✅ | ✅ |
| `H-STAGE-BIAN` | H | 变阶段判定 | ? | ? | 1 | ✅ | ✅ |
| `H-STAGE-DEFAULT` | H | 默认回退阶段 | ? | ? | 0 | ✅ | ✅ |
| `H-PATH-PROFILES` | H | 路径画像库 | calibratable | v1.0_initial | 0 | ✅ | ✅ |
| `H-FREQ-INTERPRETATION` | H | 频次分布解读规则 | calibratable | v1.0_initial | 3 | ✅ | ✅ |
| `H-DEPTH-WEIGHTS` | H | 认知深度权重 | calibratable | v1.0_initial | 0 | ✅ | ✅ |
| `H-STAGE-GUIDANCE` | H | 阶段导航建议模板 | calibratable | v1.0_initial | 5 | ✅ | ✅ |
| `H-WUXING-ADJUSTMENT` | H | 五行偏态调节建议 | calibratable | v1.0_initial | 4 | ✅ | ✅ |
| `H-CLASSICAL-REFERENCES` | H | 经典文本引用库 | calibratable | v1.0_initial | 0 | ✅ | ✅ |
| `H-FOUR-DIMS-INTERPRETATION` | H | 四维读数解读模板 | calibratable | v1.0_initial | 4 | ✅ | ✅ |
| `H-MATRIX-INTERP` | H | 交叉矩阵解读规则 | calibratable | v1.0_initial | 4 | ✅ | ✅ |
| `H-SUMMARY-TEMPLATE` | H | 判语生成模板 | calibratable | v1.0_initial | 6 | ✅ | ✅ |
| `H-STAGE-THRESHOLDS` | H | 阶段判定阈值集 | calibratable | v1.0_initial | 5 | ✅ | ✅ |

## 汇总统计

| 指标 | 数值 |
|------|------|
| 规则文件数 | 4 |
| 规则总数 | 35 |
| 经典规则 (C) | 4 |
| 领域规则 (D) | 4 |
| 形式规则 (F) | 8 |
| 启发式规则 (H) | 19 |

## 依赖完整性检查

✅ 所有依赖完整，无缺失引用。

## 变更日志检查

✅ 所有规则均包含 `change_log` 字段。

## 校验规则检查

✅ 所有规则均包含 `validation` 校验。

## 覆盖度

| 指标 | 数值 |
|------|------|
| 启发式规则已覆盖 | 19/19 (100%) |

---
*报告由 `update_wrl_rules.py` 自动生成*