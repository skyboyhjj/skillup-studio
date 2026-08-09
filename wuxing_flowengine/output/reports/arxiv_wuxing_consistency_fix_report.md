# arXiv 五行标注一致性修复报告

> **日期**：2026-08-09  
> **触发**：差异 #8 — 标注源分裂（55% 不一致）  
> **依据**：[docs/arXiv五行标注仲裁确认文档.md](../../docs/arXiv五行标注仲裁确认文档.md)

---

## 一、问题定性

`arxiv_ai_tree_*.json` 和 `arxiv_tree_*.json` 中 11 个分类的五行标注与 canonical `AI_CATEGORY_WUXING` 存在 **7 处（64%）不一致**。这是 BAAI 知识树"领域名规范化 bug → drift 伪影"教训的复演：标注源分裂会导致月度时间序列出现虚假漂移（O_t/E_u/C_k/K_y 全失真）。

| 分类 | 树文件（旧） | Canonical（新） | 依据 |
|------|-------------|----------------|------|
| cs.AI | 水 | 火 | AI 综合/扩散 > 语言流动 |
| cs.NE | 土 | 水 | 神经进化是流动/演化 |
| cs.MA | 火 | 木 | 多智能体协作是生发 |
| cs.RO | 木 | 金 | 机器人是执行/控制 |
| cs.IR | 火 | 金 | 信息检索是筛选精确 |
| cs.MM | 木 | 火 | 多媒体是多模态活跃 |
| stat.ML | 水 | 土 | 统计学习是基础承载 |

---

## 二、修复统计

### 2.1 代码变更

| 文件 | 变更 | 说明 |
|------|------|------|
| `docs/arxiv_diagnose.py` | V1.0 → V1.1 | 新增 `check_wuxing_consistency()`（P0）、`apply_wuxing_fixes()`、`--check`/`--fix` 模式、`wuxing_annotation_version` 输出（P1）、EngineAdapter 智能检测 |

### 2.2 树文件修复

| 文件 | 修复数 | 修复后状态 |
|------|--------|-----------|
| `arxiv_ai_tree_202606.json` | 7 | 一致 |
| `arxiv_ai_tree_202607.json` | 7 | 一致 |
| `arxiv_ai_tree_202608.json` | 7 | 一致 |
| `arxiv_tree_202606.json` | 7 | 一致 |
| `arxiv_tree_202607.json` | 7 | 一致 |
| `arxiv_tree_202608.json` | 7 | 一致 |
| **合计** | **42** | **6/6 通过** |

### 2.3 诊断输出更新

| 文件 | 状态 |
|------|------|
| `arxiv_diag_202606.json` | 已重生成（含 `wuxing_annotation_version: v1`） |
| `arxiv_diag_202607.json` | 已重生成 |
| `arxiv_diag_202608.json` | 已重生成 |
| `arxiv_series.json` | 已重生成（含 `annotation_versions` 逐月记录） |

---

## 三、回归验证结果

统一标注后 3 个月诊断对比：

| 月份 | 主导 | O_t | E_u | C_k | K_y | S_p | 阶段 |
|------|------|-----|-----|-----|-----|-----|------|
| 2026-06 | 土 | 0.2811 | 0.0293 | 0.2727 | 1.0 | 30.90 | 克·约束竞争 |
| 2026-07 | 土 | 0.2783 | 0.0402 | 0.2727 | 1.0 | 31.65 | 克·约束竞争 |
| 2026-08 | 火 | 0.2854 | 0.0395 | 0.2727 | 1.0 | 31.79 | 克·约束竞争 |

**主导路径**：土 → 土 → 火

**关键观察**：
- 6-7 月土主导（ML 基础承载权重最大），8 月火反超（AI 综合 + 多媒体 + 人机交互活跃度上升）
- S_p 稳定在 30-32 区间（克·约束竞争阶段），无虚假漂移
- C_k（0.2727）和 K_y（1.0）恒定——这是 fallback 引擎对平层 11 分类结构的固有特征，非数据问题

---

## 四、关键设计决策

### 4.1 仲裁确认：参考版为唯一标注源

参考版 `AI_CATEGORY_WUXING`（语义映射：土=承载/水=流动/木=生发/金=结构/火=活跃）在 NE/RO/MM 三条上依据比实际版充分，仲裁胜出。标注原则：**五行是视角，但诊断必须单一视角——统一之前，宁可不诊断，不产伪影**。

### 4.2 标注一致性校验（P0）：严格模式默认抛异常

`check_wuxing_consistency(nodes, canonical, strict=True)` 默认在任一分类不一致时抛 `ValueError`，阻断诊断流水线。`--fix` 模式下自动修复并回写树文件。`--check` 模式仅检查不修复，供 CI/定时任务使用。

### 4.3 标注版本化（P1）：变更显式记录

每次标注调整 → 版本 +1，在时间序列文件 `arxiv_series.json` 中逐月记录 `annotation_versions`。跨版本对比时标注"标注版本差异"，防止"标注变更"被误读为"领域漂移"。

### 4.4 EngineAdapter：平层数据用 fallback

arXiv 数据是 11 分类平层结构（无种子/现行/超越三层、无结构边），真实引擎 `wuxing_diagnose_v2` 设计用于层次化知识树。EngineAdapter 检测到节点无 `cognitive_depth` 分层时自动使用 fallback，避免格式不匹配。

### 4.5 双格式树文件同步修复

`arxiv_ai_tree_*.json`（ai_tree 兼容格式）和 `arxiv_tree_*.json`（四源统一 schema）均包含节点五行标注，需同步修复。`arxiv_diagnose.py --fix` 覆盖 `arxiv_ai_tree_*`，`arxiv_tree_*` 通过独立脚本修复。

---

## 五、验证命令

```powershell
# 一致性检查（CI 可用）
cd wuxing_flowengine/output
python ..\docs\arxiv_diagnose.py --check

# 单月诊断（含修复）
python ..\docs\arxiv_diagnose.py --month 2026-08 --fix

# 多月时间序列（含修复）
python ..\docs\arxiv_diagnose.py --glob "arxiv_ai_tree_*.json" --fix
```

---

## 六、教训

> 标注源分裂是 BAAI 知识树"领域名规范化 bug"的复演——同一分类在不同位置标注不同，导致时间序列伪影。预防措施：**所有标注变更必须同步更新 canonical 映射 + 树文件 + 诊断输出 + 版本号**，四者缺一不可。