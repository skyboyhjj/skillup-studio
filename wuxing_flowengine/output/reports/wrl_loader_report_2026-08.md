# WRL 规则加载报告
> 加载时间: 2026-08-07T18:48:11.244841
> 规则总数: 35

## 验证状态: ✅ 全部通过

## 统计

| 指标 | 数值 |
|------|------|
| 规则总数 | 35 |
| 经典规则 (C) | 4 |
| 领域规则 (D) | 4 |
| 形式规则 (F) | 8 |
| 启发式规则 (H) | 19 |
| 含 validation | 35 |
| 含 change_log | 35 |
| 总依赖数 | 75 |
| 总 affects | 56 |

## 规则清单

### classical_rules.wrl (4 条)

| 规则 ID | 分类 | 名称 | 可修改性 | 依赖数 | 有校验 | 有变更日志 |
|---------|------|------|----------|--------|--------|-----------|
| `C-SHENG` | C | 五行相生关系 | immutable | 0 | ✅ | ✅ |
| `C-KE` | C | 五行相克关系 | immutable | 0 | ✅ | ✅ |
| `C-WX-COORD` | C | 五行方位坐标映射 | immutable | 0 | ✅ | ✅ |
| `C-WX-ROLES` | C | 五行角色定义 | immutable | 0 | ✅ | ✅ |

### domain_rules.wrl (4 条)

| 规则 ID | 分类 | 名称 | 可修改性 | 依赖数 | 有校验 | 有变更日志 |
|---------|------|------|----------|--------|--------|-----------|
| `D-SCHOLARLY` | D | 学术考据视角 | configurable | 5 | ✅ | ✅ |
| `D-PRACTICAL` | D | 实践视角预设 | configurable | 5 | ✅ | ✅ |
| `D-EDUCATIONAL` | D | 教育视角预设 | configurable | 5 | ✅ | ✅ |
| `D-DEFAULT` | D | 默认配置 | configurable | 5 | ✅ | ✅ |

### formal_rules.wrl (8 条)

| 规则 ID | 分类 | 名称 | 可修改性 | 依赖数 | 有校验 | 有变更日志 |
|---------|------|------|----------|--------|--------|-----------|
| `F-ENTROPY` | F | Shannon 熵计算 | immutable | 1 | ✅ | ✅ |
| `F-CENTROID` | F | 五行质心坐标计算 | immutable | 1 | ✅ | ✅ |
| `F-O_T` | F | 时位 O_t 映射公式 | calibratable | 2 | ✅ | ✅ |
| `F-E_U` | F | 宇位 E_u 映射公式 | calibratable | 2 | ✅ | ✅ |
| `F-C_K` | F | 识位 C_k 映射公式 | calibratable | 1 | ✅ | ✅ |
| `F-K_Y` | F | 缘位 K_y 映射公式 | calibratable | 2 | ✅ | ✅ |
| `F-S_P` | F | 存在度 S_p 广义平均公式 | calibratable | 4 | ✅ | ✅ |
| `F-THETA` | F | 临界阈值 θ_critical 计算公式 | calibratable | 1 | ✅ | ✅ |

### heuristic_rules.wrl (19 条)

| 规则 ID | 分类 | 名称 | 可修改性 | 依赖数 | 有校验 | 有变更日志 |
|---------|------|------|----------|--------|--------|-----------|
| `H-DOMINANCE` | H | 主导判定阈值 | calibratable | 0 | ✅ | ✅ |
| `H-SCARCITY` | H | 稀缺判定阈值 | calibratable | 0 | ✅ | ✅ |
| `H-ENTROPY-CLASS` | H | 熵值分类阈值 | calibratable | 1 | ✅ | ✅ |
| `H-STAGE-SHENG` | H | 生阶段判定 | calibratable | 2 | ✅ | ✅ |
| `H-STAGE-KE` | H | 克阶段判定 | calibratable | 2 | ✅ | ✅ |
| `H-STAGE-HUA` | H | 化阶段判定 | calibratable | 2 | ✅ | ✅ |
| `H-STAGE-TONG` | H | 通阶段判定 | calibratable | 2 | ✅ | ✅ |
| `H-STAGE-BIAN` | H | 变阶段判定 | calibratable | 1 | ✅ | ✅ |
| `H-STAGE-DEFAULT` | H | 默认回退阶段 | calibratable | 0 | ✅ | ✅ |
| `H-PATH-PROFILES` | H | 路径画像库 | calibratable | 0 | ✅ | ✅ |
| `H-FREQ-INTERPRETATION` | H | 频次分布解读规则 | calibratable | 3 | ✅ | ✅ |
| `H-DEPTH-WEIGHTS` | H | 认知深度权重 | calibratable | 0 | ✅ | ✅ |
| `H-STAGE-GUIDANCE` | H | 阶段导航建议模板 | calibratable | 5 | ✅ | ✅ |
| `H-WUXING-ADJUSTMENT` | H | 五行偏态调节建议 | calibratable | 4 | ✅ | ✅ |
| `H-CLASSICAL-REFERENCES` | H | 经典文本引用库 | calibratable | 0 | ✅ | ✅ |
| `H-FOUR-DIMS-INTERPRETATION` | H | 四维读数解读模板 | calibratable | 4 | ✅ | ✅ |
| `H-MATRIX-INTERP` | H | 交叉矩阵解读规则 | calibratable | 4 | ✅ | ✅ |
| `H-SUMMARY-TEMPLATE` | H | 判语生成模板 | calibratable | 6 | ✅ | ✅ |
| `H-STAGE-THRESHOLDS` | H | 阶段判定阈值集 | calibratable | 5 | ✅ | ✅ |

## 依赖关系

- `D-DEFAULT` → `H-DOMINANCE`, `H-SCARCITY`, `H-ENTROPY-CLASS`, `H-DEPTH-WEIGHTS`, `F-THETA`
- `D-EDUCATIONAL` → `H-DOMINANCE`, `H-SCARCITY`, `H-ENTROPY-CLASS`, `H-DEPTH-WEIGHTS`, `F-THETA`
- `D-PRACTICAL` → `H-DOMINANCE`, `H-SCARCITY`, `H-ENTROPY-CLASS`, `H-DEPTH-WEIGHTS`, `F-THETA`
- `D-SCHOLARLY` → `H-DOMINANCE`, `H-SCARCITY`, `H-ENTROPY-CLASS`, `H-DEPTH-WEIGHTS`, `F-THETA`
- `F-CENTROID` → `C-WX-COORD`
- `F-C_K` → `C-WX-ROLES`
- `F-ENTROPY` → `C-WX-ROLES`
- `F-E_U` → `C-WX-ROLES`, `F-CENTROID`
- `F-K_Y` → `C-KE`, `C-SHENG`
- `F-O_T` → `C-WX-ROLES`, `F-ENTROPY`
- `F-S_P` → `F-O_T`, `F-E_U`, `F-C_K`, `F-K_Y`
- `F-THETA` → `F-S_P`
- `H-ENTROPY-CLASS` → `F-ENTROPY`
- `H-FOUR-DIMS-INTERPRETATION` → `F-O_T`, `F-E_U`, `F-C_K`, `F-K_Y`
- `H-FREQ-INTERPRETATION` → `H-DOMINANCE`, `H-SCARCITY`, `C-WX-ROLES`
- `H-MATRIX-INTERP` → `F-O_T`, `F-E_U`, `F-C_K`, `F-K_Y`
- `H-STAGE-BIAN` → `H-DEPTH-WEIGHTS`
- `H-STAGE-GUIDANCE` → `H-STAGE-SHENG`, `H-STAGE-KE`, `H-STAGE-HUA`, `H-STAGE-TONG`, `H-STAGE-BIAN`
- `H-STAGE-HUA` → `F-S_P`, `F-THETA`
- `H-STAGE-KE` → `C-KE`, `C-SHENG`
- `H-STAGE-SHENG` → `H-DOMINANCE`, `H-ENTROPY-CLASS`
- `H-STAGE-THRESHOLDS` → `H-DOMINANCE`, `H-SCARCITY`, `H-ENTROPY-CLASS`, `F-THETA`, `H-DEPTH-WEIGHTS`
- `H-STAGE-TONG` → `H-PATH-PROFILES`, `H-ENTROPY-CLASS`
- `H-SUMMARY-TEMPLATE` → `F-S_P`, `F-O_T`, `F-E_U`, `F-C_K`, `F-K_Y`, `F-THETA`
- `H-WUXING-ADJUSTMENT` → `C-SHENG`, `C-KE`, `H-DOMINANCE`, `H-SCARCITY`

---
*报告由 `wrl_loader.py` 自动生成*