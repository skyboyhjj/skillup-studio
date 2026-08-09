# CASE-LIU 链式映射 REV2 最终交付清单

> **任务ID**: TASK-HOMO-LIU-20260808
> **协议版本**: V1.5
> **修订**: REV1 → REV2（图驱动全链路升级）
> **交付日期**: 2026-08-09
> **状态**: ✅ 全部交付完成，10/10 测试通过，4 处修复已归档

---

## 一、交付物清单

### 1.1 核心代码（3 文件）

| 文件 | 行数 | 变更 | 说明 |
|------|------|------|------|
| `wuxing_flowengine/scripts/homomorphism_engine.py` | ~1240 | `transfer_chain` 升级为图驱动；新增 `resolve_json_refs()`；CLI 入口适配 | REV2 核心升级 |
| `wuxing_flowengine/scripts/test_homo_liu.py` | ~295 | 新增 3 项 REV2 测试（8/9/10），总计 7→10 项；断言粒度标注 | 回归安全网 |
| `wuxing_flowengine/scripts/gen_result_liu.py` | ~97 | 解析 $ref + 传入直接映射保持度；控制台摘要增强分段详情 | 结果生成器 |

### 1.2 数据文件（1 文件）

| 文件 | 变更 | 说明 |
|------|------|------|
| `wuxing_flowengine/data/task_liu_input.json` | 新增佛学中间域图（5 节点 4 边）+ 2 段候选映射（6 条），使用 `$ref` 引用复用域定义 | 输入数据扩展 |

### 1.3 报告文档（3 文件）

| 文件 | 行数 | 说明 |
|------|------|------|
| `wuxing_flowengine/output/reports/result_liu.json` | 416 | 结构化验证结果（homo_verify + chain_verify + shell_nucleus_audit） |
| `wuxing_flowengine/output/reports/case_liu_chain_buddhism_report.md` | 197 | 佛学中间域图与映射结果专项报告（8 章） |
| `wuxing_flowengine/output/reports/m3_deliverables_report.md` | ~540 | Phase 2 验证报告整合版（新增 §十二 链式映射全链路验证） |

### 1.4 项目记忆（1 文件）

| 文件 | 变更 | 说明 |
|------|------|------|
| `project_memory.md` | 新增 6 条经验 + 4 处修复记录 + 4 条工程约定 | 可复用知识归档 |

---

## 二、验证结果

### 2.1 测试（10/10 PASS）

| # | 测试 | 断言 | 结果 |
|---|------|------|------|
| 1 | test_mapping_retention | 每条映射保持度在 expected ±0.08 内 | ✅ |
| 2 | test_average_retention | 平均保持度在 [0.80, 0.90] | ✅ |
| 3 | test_chain_retention | 链式复合在 [0.63, 0.90] | ✅ |
| 4 | test_increment_audit | 增量审计 3 项，全部不破坏保持 | ✅ |
| 5 | test_increment_audit_matches_task_spec | 增量输出与任务书 §二 逐项一致 | ✅ |
| 6 | test_scenarios_all_pass | 迁移验证 4/4 PASS | ✅ |
| 7 | test_shell_nucleus | 壳核审计三层判定正确 + H1 挂载 | ✅ |
| 8 | test_chain_segment_retention | 每段段平均保持度在预期 ±0.08 内 | ✅ |
| 9 | test_chain_bridge_gain_positive | 桥梁增益 ≥ 0 | ✅ |
| 10 | test_chain_vs_direct_delta | 链式 vs 直接偏差 ≤ 0.16 | ✅ |

### 2.2 核心指标

| 指标 | 值 |
|------|-----|
| 直接映射保持度 | 0.858 |
| 段1 保持度（数学→佛学） | 0.8667 |
| 段2 保持度（佛学→心理） | 0.7767 |
| 分段积 | 0.6732 |
| 桥梁增益 | 0.05 |
| 链式复合 | 0.7068 |
| 偏差（链式 vs 直接） | −0.1512 |
| 壳核审计 | 4/4 PASS |

---

## 三、REV2 vs REV1 对比

| 维度 | REV1（专家估值） | REV2（图驱动） |
|------|-----------------|---------------|
| 分段计算 | 取 expected 硬编码值 | 每段独立 `transfer_from_graph` 实跑 |
| 中间域 | 无图 | 佛学 5 节点 4 边完整图 |
| 损耗归因 | 无 | 逐映射五行关系归因（土克水 -0.27、土生金之逆 -0.13） |
| 桥梁角色 | 单一"桥梁" | "桥梁+转换层"双重角色 |
| 输入数据 | 仅含 expected_retention | 含完整中间域图及分段候选映射 |
| 直接对比 | 硬编码 direct=0.85 | 从 homo_verify 实跑获取 |

---

## 四、修复记录（4 处）

| # | 问题 | 修复 |
|---|------|------|
| 1 | 两份报告单条映射值不一致 | m3 §12.3 数值同步为 result_liu.json 实跑值 |
| 2 | 保持度分布表内部矛盾 | 修正为极高 4(66.7%)、中等 1(16.7%)、低 1(16.7%) |
| 3 | 五行术语"金生土（反生）"不准确 | 统一为"土生金之逆（非相生方向）" |
| 4 | 测试断言粒度模糊 + 阈值紧贴 | 明确标注"段平均"、标注阈值 v1.0_initial 待校准 |

---

## 五、关键结论

1. **同五行映射保持度极高**：金→金（0.94）和水→水（0.90），数学逻辑与佛学因明/中观存在二阶同构
2. **土克水是核心瓶颈**：缘起性空（土）→ 模式识别（水）保持度仅 0.53，唯一的 `medium` 信度映射
3. **佛学双重角色**：既是桥梁（金金同构加速 +0.05），也是转换层（土水相克减速 -0.1512）
4. **链式 < 直接**：佛学中间域有独立认知代价，不是纯桥梁

---

*交付清单由 CASE-LIU REV2 实施生成 · 2026-08-09*