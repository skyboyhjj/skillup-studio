# SkillUp Studio 项目上下文

## 项目概述

**道境空间** — AI 知识引擎产品矩阵，以中国传统哲学为内核的知识图谱工具集。

- [hui-skill.cn](https://hui-skill.cn/) — 产品矩阵统一入口
- [hui-skill.cn/studio/](https://hui-skill.cn/studio/) — 莫比乌斯环概念地图生成器

核心产品：

| 产品 | 状态 | 说明 |
|------|:---:|------|
| 知识图谱标注平台 | ✅ 已上线 | 6 维标注（五行、多层五行深度、认知深度、八卦等），规则库驱动 |
| 莫比乌斯环概念地图 | ✅ 已上线 | 选择数据集或输入文本，一键生成可交互的 3D 概念地图 HTML |
| 知识树追踪引擎 | 🔜 即将上线 | 概念演化路径追踪与可视化 |
| 论文采集器 | 🟡 预览版 | arXiv 月度采集（100 篇样本），分类筛选/搜索/导出 |
| 五行道境引擎 | 🟡 开发中 | 知识树五行诊断 + 道境四维映射 + 月度流水线 + 论文采集合成 |

## 关键文件

| 文件 | 用途 |
|------|------|
| `frontend/studio/index.html` | 主页面（包含 HTML/CSS/JS 全部逻辑） |
| `frontend/studio/styles.css` | 样式文件 |
| `frontend/studio/build_mobius.js` | 莫比乌斯环 3D 渲染引擎（Three.js） |
| `frontend/studio/template.html` | 生成的 HTML 模板（含 Canvas 渲染、UI 层、工具栏） |
| `frontend/studio/functions/api/[[path]].js` | Cloudflare Pages Function — meta-skill API 代理 |
| `frontend/studio/preset-data/*.json` | 预设数据集（11 个） |
| `frontend/studio/_redirects` | Cloudflare Pages 路由规则 |
| `deploy/hui-skill/nginx-hui-skill.conf` | hui-skill.cn Nginx 配置 |
| `deploy/hui-skill/deploy.ps1` | hui-skill.cn 部署脚本 |
| `frontend/product-matrix/pages/index.html` | 产品矩阵首页（非对称布局，4 产品卡片） |
| `frontend/product-matrix/pages/annotate.html` | 知识图谱标注平台（左侧层级树 + 右侧 6 维标注表单） |
| `frontend/product-matrix/pages/papers.html` | 论文采集器（统计概览 + 筛选侧栏 + 论文列表 + CSV/JSON 导出） |
| `frontend/product-matrix/data/papers-2026-06.json` | 论文采集器数据集（100 篇 arXiv 论文，2026-06-30 采集） |
| `frontend/product-matrix/colors_and_type.css` | 品牌 Design Token 定义（墨色+朱砂红+宣纸白） |
| `frontend/product-matrix/hui-skill-product-matrix.design` | 设计画布元数据 |
| `docs/network-monitoring.md` | 带宽监控方案 + 实际流量分析（2026-07-24 ~ 07-31） |
| `deploy/nginx/hui-skill.cn.conf` | Nginx 站点配置（含限流规则） |
| `wuxing_flowengine/diagnose/wuxing_diagnose_v2.py` | 五行诊断引擎（七维指标体系 + 层间路径分析） |
| `wuxing_flowengine/scripts/phase1_pipeline.py` | Phase 1 流水线（认知深度→五行映射→三层构建→四维计算） |
| `wuxing_flowengine/scripts/dao_realm_engine.py` | 道境融合诊断引擎（Ch5 五步算法） |
| `wuxing_flowengine/scripts/stage_engine.py` | 生克化通变五阶段判定引擎（Ch4） |
| `wuxing_flowengine/scripts/guidance.py` | 导航建议生成器 |
| `wuxing_flowengine/scripts/k_y_enhancer.py` | K_y 缘位增强器（Phase 4 自适应混合 E_relation） |
| `wuxing_flowengine/scripts/baai_scraper.py` | BAAI Hub 论文采集（reports_graph/reports_detail API + Tiptap JSON 解析） |
| `wuxing_flowengine/scripts/data_validator.py` | 数据验证模块（五检查点：语言/数量/覆盖/重复/一致性） |
| `wuxing_flowengine/scripts/monthly_pipeline.py` | 月度编排器（Phase 1→2→3+ + 时间序列 + 验证） |
| `wuxing_flowengine/scripts/phase3_plus_pipeline.py` | Phase 3+ 流水线（论文五行分类 + 领域漂移分析 + 领域名规范化） |
| `wuxing_flowengine/scripts/domain_calibration.py` | 领域基准校准 |
| `wuxing_flowengine/scripts/timeseries_analysis.py` | 时间序列分析（多月份 delta 链） |
| `wuxing_flowengine/scripts/wuxing_dsl.py` | 五行 DSL 引擎（WRL 规则语言 + 画像库） |
| `wuxing_flowengine/rules/` | WRL 规则文件（经典/形式/启发式/领域 四类 32 条规则） |
| `wuxing_flowengine/docs/` | 设计文档（融合设计方案 V1.2 + 数据采集经验总结） |
| `wuxing_flowengine/output/validation_report_2026-08.md` | 2026.08.05 验证批次报告（含 P0/P1/P2 修复 + 漂移分析） |
| `wuxing_flowengine/output/archive/` | 4 个月度归档（2026-05/06/07/08） |
| `wuxing_flowengine/scripts/homomorphism_types.py` | 同态映射引擎 — 核心数据类型（概念节点/关系边/候选映射/验证结果/偏差记录） |
| `wuxing_flowengine/scripts/structure_extractor.py` | 同态映射引擎 Step 1 — 结构提取器（从 Base 层提取概念-关系图） |
| `wuxing_flowengine/scripts/homomorphism_matcher.py` | 同态映射引擎 Step 2 — 同态匹配器（五行/结构/LLM 三策略 + 信度出口） |
| `wuxing_flowengine/scripts/transfer_validator.py` | 同态映射引擎 Step 3 — 迁移验证器（场景生成/验证/固化/SAD 镜鉴） |
| `wuxing_flowengine/scripts/homomorphism_engine.py` | 同态映射引擎 — 土·通集成（三步协议 + 五行流转 + P忠恕伦理 + 旋量形式化） |
| `wuxing_flowengine/scripts/zhongshu_ethics.py` | P忠恕伦理模块 — 忠恕双向校验（忠度/恕度/忠恕综合 + 伦理约束注入） |
| `wuxing_flowengine/scripts/spinor_formalism.py` | 旋量-太极形式化 — 反者道之动数学精确化（旋量相位/道旋量状态/桥接器） |

## 部署命令

### hui-skill.cn (服务器 Nginx)

```powershell
# 仅部署前端
.\deploy\hui-skill\deploy.ps1

# 完整部署（前端 + Nginx 配置）
.\deploy\hui-skill\deploy.ps1 -full
```

前置: 已配置 SSH 密钥到 `root@121.41.215.36`（见 `deploy.ps1` 顶部注释）。

## 站点架构

hui-skill.cn 前端通过 Nginx 反代服务，后端 API 直连本机 FastAPI：

```
frontend/studio/  ──rsync────>  Nginx (hui-skill.cn)
  └── /api/*  ──直连────>  FastAPI (127.0.0.1:8000)
```

| 站点 | 部署 | 文本输入 | 预设数据集 | API 方式 |
|------|------|:---:|:---:|------|
| hui-skill.cn/studio/ | Nginx + rsync | ✅ | ✅ | 直连本机 FastAPI |

## API 架构

- 文本提取: `POST /api/studio/extract`（body: `{ text: "..." }`）
- 微信公众号 URL 提取: `POST /api/studio/extract`（body: `{ url: "..." }`）— 仅后端 API，前端不暴露
- 后端运行在 Docker 容器 `ms-api`（`/opt/meta-skill/`，Docker Compose 管理）
- CORS 已配置为 `*`

## 分支管理 SOP

`PROJECT_CONTEXT.md` 按分支拆分管理，`hui-skill-cn` 分支记录后端/服务器相关任务：

| 分支 | 记录范围 | 同步方向 |
|------|----------|----------|
| `hui-skill-cn` | hui-skill.cn 网站相关任务（后端、服务器、Docker 等） | 修改后同步到 `master` |

**同步方式**: 在 `hui-skill-cn` 提交后，`git checkout master && git merge hui-skill-cn`，冲突时手动整合。

---

## 已完成 — 后端/服务器 (hui-skill-cn 分支)

### 1. 后端 AI 模型 max_tokens 不足导致 JSON 截断
- **根因**: Docker 容器 `ms-api` 中 `concept_extractor.py` 的 DeepSeek API 调用 `max_tokens=4096`，生成 15-25 个概念的完整 JSON 需要约 6000-8000 tokens，模型输出在 3200-3500 字符处被截断，导致 `JSONDecodeError: Unterminated string`
- **表现**: 微信公众号 URL 提取超长文章时 80% 失败，报错行号每次不同（char 2331 / 3204 等）
- **修复**: `max_tokens: 4096 → 16384`，输入文本截断 `text[:8000] → text[:5000]`（为输出留出更多空间）
- **部署**: 修改源码后 `docker compose build api && docker compose up -d api` 重建容器
- **文件**: `/opt/meta-skill/backend/services/concept_extractor.py`（服务器端，不在 Git 仓库中）

### 2. 产品矩阵首页设计与实现
- 创建产品矩阵首页 `frontend/product-matrix/pages/index.html`，非对称 7:5 / 5:7 交错卡片布局
- 展示四个产品：标注平台、莫比乌斯概念地图、知识树追踪引擎、论文采集器
- 区分游客/注册用户权限展示
- 品牌色系：墨色底（#141210）+ 朱砂红（#C94B3A）+ 宣纸白卡片（#F5F0E8）
- 技术栈：纯静态 HTML + Tailwind CSS v4.3.1 (CDN) + Lucide Icons v1.8.0 (CDN)

### 3. 知识图谱标注平台页面
- 创建 `frontend/product-matrix/pages/annotate.html`（1257 行）
- 左侧 320px 可拖拽概念层级树（搜索 + 展开/折叠 + 选中高亮 + 标注状态徽章）
- 右侧 6 维标注表单：五行、多层五行深度 L1-L4、认知深度、八卦、概念描述、来源出处
- 权限切换（游客只读 / 注册用户可编辑）+ 规则库（可展开卡片 + 自然语言修改）
- 内嵌 20 个概念树节点 + 16 条道德经标注数据

### 4. 品牌统一改名：中国哲学 → 道境空间
- 全局替换 6 个文件 12 处「中国哲学」→「道境空间」
- 涉及：`pages/index.html`、`pages/annotate.html`、`colors_and_type.css`、`.design`、编排文件

### 5. 服务器带宽监控方案 & 实际流量分析
- 服务器 21.41.215.36，按使用流量计费，50 Mbps 峰值带宽
- 分析 7/24-7/31 阿里云 OMS 流量数据（738 条小时级记录）
- 结果：7 天总流出 99.19 MB，峰值带宽 15.78 kbps（利用率 0.03%），带宽远未触及上限
- 文档：`docs/network-monitoring.md`（含 vnstat / Nginx 日志分析 / GoAccess / 限流四种方案）
- Nginx 配置：`deploy/nginx/hui-skill.cn.conf`（含限流规则 + API 反向代理 + 安全加固）

### 6. GitHub 仓库结构规划
- 规划 `frontend/` / `backend/` / `deploy/` 三层分离结构
- 创建根级 `README.md`、`.gitignore`
- 创建 `frontend/product-matrix/README.md`
- 排除运行时编排文件、预检模板、缓存、临时文件
- 保留 `PROJECT_CONTEXT.md` 作为跨分支共享任务参考文档

### 7. 论文采集器页面（预览版）
- 创建 `frontend/product-matrix/pages/papers.html`，亮色主题，复用品牌 Token 体系（墨色+朱砂红+宣纸白）
- 布局：顶部导航 + Hero 区 + 4 统计卡片（论文总数/主分类数/平均作者/采集日期）+ 左侧筛选栏（260px sticky）+ 右侧论文列表
- 数据：从 `wuxing_flowengine/output/papers_2026-06.json` 复制至 `frontend/product-matrix/data/papers-2026-06.json`（100 篇 arXiv 论文，2026-06-30 采集），页面通过 `fetch('../data/papers-2026-06.json')` 加载
- 交互：主分类多选筛选（20 个 arXiv 类别带计数）、关键词搜索（标题/作者/摘要/arXiv ID）、4 种排序、摘要展开收起、分页加载（20 篇/页）、权限切换（游客禁用导出）、CSV/JSON 导出（注册用户）、移动端筛选抽屉
- 数据画像：100 篇 / 20 主分类 / 平均 4.5 作者；主分类 Top5 为 cs.CV(25)、cs.LG(23)、cs.CL(14)、cs.RO(11)、cs.AI(7)
- 更新 `index.html` 论文采集器卡片：「敬请期待」→「预览版」徽章 + 「进入预览」按钮
- 本地预览：`cd frontend/product-matrix && python -m http.server 8088` → http://localhost:8088/pages/papers.html
- 浏览器自动化测试通过：初始加载、统计数值、摘要展开、权限切换、重置、加载更多、导航均正常，无 JS 报错

### 8. 五行道境引擎 V1.2 设计与实现
- 基于《五行诊断与道境坐标系：融合设计方案 V1.2》实现完整流水线
- **Phase 1**: 认知深度估算（L1-L4 关键词匹配）→ 五行映射（16 领域 + 关键词回退）→ 三层构建（种子/现行/超越）→ 四维计算（O_t/E_u/C_k/K_y）→ 存在度 S_p（广义平均，p=0.5 P忠恕中道，S_p ∈ [0,100]）
- **全局阶段判定**（`stage_engine.py`）：优先级链 `生 → 克（ke_edge_count ≥ 1）→ 化（S_p > θ_critical）→ 通 → 变`。S_p 仅作为"化"判定的单一输入条件，不替代全局阶段
- **Phase 2**: 双层标注（概念名 + 五行标签）+ Spinor 层构建 + 领域追踪
- **Phase 3+**: 论文五行分类 + 领域漂移分析（余弦距离）
- **Phase B** (`dao_realm_engine.py`): 道境诊断引擎 — 五步算法（诊断→四维映射→S 计算→阶段判定→导航建议）
- **Phase C2** (`k_y_enhancer.py`): K_y 缘位增强 — 自适应混合 E_relation（ke_density × β + graph_cohesion × (1-β)）
- **Phase C1** (`domain_calibration.py`): 领域基准校准
- 四个月度快照（2026-05/06/07/08）+ 时间序列 delta 链 + 验证报告（`output/validation_report_2026-08.md`）
- 文件：`wuxing_flowengine/diagnose/wuxing_diagnose_v2.py`、`scripts/phase1_pipeline.py`、`scripts/phase2_pipeline.py`、`scripts/phase3_plus_pipeline.py`、`scripts/dao_realm_engine.py`、`scripts/stage_engine.py`、`scripts/guidance.py`、`scripts/k_y_enhancer.py`、`scripts/domain_calibration.py`、`scripts/monthly_pipeline.py`、`scripts/timeseries_analysis.py`、`scripts/wuxing_dsl.py`、`docs/`

### 9. P0/P1/P2 修复：层间路径分析 + 通阶段画像匹配 + 领域名规范化
- **P0**: `_edge_paths()` 从全量桩代码（恒返回 10 条）重写为实际层间主导行分析
  - 逐对检查种子→现行、现行→超越的层间主导行是否构成相生/相克
  - `ke_edge_count` 从恒为 5 变为实际值 0-2，K_y 从 0.89→0.29，S 从 5.1→1.7
- **P1**: 通阶段补全"路径匹配画像"条件
  - 新增 `dim3_profile` 输出（层主导行/路径串/画像匹配）
  - `matches_profile = 至少一条相生边 + 无相克边`
  - `stage_engine.py` 通阶段判定改为 `matches_profile AND 0.50 < H_ratio < 0.85`
- **P2**: 领域名规范化 — 论文 domain（"生成式 AI"）与节点 domain（"生成式AI"）命名不一致 → 新增 `normalize_domain()` 统一去除空格和中文标点差异，消除 drift=1.0 伪影
- 文件：`wuxing_flowengine/diagnose/wuxing_diagnose_v2.py`、`scripts/stage_engine.py`、`scripts/phase3_plus_pipeline.py`

### 11. V1.2 设计文档验证批次更新 + P2 领域名规范化修复
- **V1.2 设计文档** (`五行诊断与道境坐标系：融合设计方案 V1.2.md`) 新增 2026.08.05 验证批次内容：
  - 9.2.1 Bug 修复记录：P0（`_edge_paths()` 恒返回 10 条边）、P1（通阶段画像匹配）、P2（领域名规范化）、P3（ke_edge_count 分母修正）
  - 9.3.1 Phase 3+ 流水线验证结果：四维指标跨月对比、阶段判定、论文-节点漂移分析、数据质量验证、对 9.3 遗留问题的逐条验证结论
  - 9.4 下一步行动：基于验证结果重新排序为 P0/P1/P2 三级
- **P2 Bug 修复**：论文 domain（"生成式 AI"）与节点 domain（"生成式AI"）命名不一致 → 新增 `normalize_domain()` 统一去除空格和中文标点差异，消除 drift=1.0 伪影
- 修复后 4 个月度流水线重跑，四维指标稳定（O_t: 0.27~0.28, E_u: 0.96, C_k: 0.22, K_y: 0.29），阶段一致判"克"（S≈1.7 << θ_critical=90）
- 实证确认 S 上限问题不可通过调参解决，需公式结构级变更（9.3 P0#1）
- 文件：`wuxing_flowengine/docs/五行诊断与道境坐标系：融合设计方案 V1.2.md`、`wuxing_flowengine/scripts/phase3_plus_pipeline.py`、`wuxing_flowengine/output/validation_report_2026-08.md`

### 12. 分支对比分析：master vs hui-skill-cn 的 wuxing_flowengine
- 对两个分支下 `wuxing_flowengine/` 做完整 diff 对比（116 文件，+63,086 / -21,497 行）
- **关键差异**：
  - `docs/`：master 含 10 份文档（含 ima/ 参考），hui-skill-cn 精简为 2 份核心文档
  - `scripts/`：删除 13 个临时/一次性脚本，新增 9 个核心模块（baai_scraper, wuxing_dsl, stage_engine, domain_calibration, data_validator, k_y_enhancer, guidance, dao_realm_engine, gen_monthly_snapshots）
  - `output/`：从扁平散落改为 `archive/{month}/` 结构化归档，覆盖 05/06/07/08 四个月
  - `config/`：从 4 个配置文件简化为 1 个（config_default.json）
  - `data/`：从 1 个真实快照扩展为 4 个月快照（1 真实 + 3 模拟）
  - 新增 `tests/` 目录（4 个测试文件）和 `README.md`
- **结论**：hui-skill-cn 是 master 的生产化演进版本，从"诊断工具"升级为"月度流水线平台"

### 13. p-P忠恕验证：S_p 广义平均公式的伦理落地
- 将 Power Mean 参数 p 与慧惠宪法 P忠恕原则结合，p 成为"恕度"参数
- **p 的伦理语义**：p=1.0（恕之极致/加性）、p=0.8（宽恕）、p=0.5（P忠恕中道/默认）、p=0.3（严格）、p=0.0（几何）、p=-1.0（苛/调和）
- **S_p 与全局阶段判定的关系**：S_p 仅作为"化"判定的单一输入条件（S_p > θ_critical 触发），不替代全局阶段判定。全局阶段优先级链：生 → 克（ke_edge_count ≥ 1）→ 化（S_p > θ_critical）→ 通 → 变
- 旧乘积 S 恒为 1.7（量纲不可达），S_p 重算后四个月度在 39.3~39.5（中位数 39.4，θ_base=50），量纲问题解决
- 三项验证通过：p 平滑性（Δ∈[3.9, 5.2]）、宽恕有效性（Δ_rel=12.0% > 10%）、排名稳定性（8 案例一致）、量纲对齐（中位数 ∈ [20,80]）
- 宽恕阈值采用相对为主（>10%）、绝对为辅（>5）的双判据，避免均衡数据时绝对差误报
- P忠恕版 S 卡格式：S 值旁标注恕度标签，自动附加"最弱维度 + 最强补足路径"的恕语
- 文件：`wuxing_flowengine/scripts/validate_p_zhongshu.py`、`docs/五行诊断与道境坐标系：融合设计方案 V1.2.md`（9.5 节）、`README.md`（诊断结果表同步更新 S_p 列）

### 10. 数据采集经验总结 + 验证模块
  - 总结智源社区（hub.baai.ac.cn）知识树 + 科研月报采集的七条核心教训
  - API 优先、格式不假设、逐领域验证、语言检测、弹窗处理、URL 编码、历史回溯
- 采集脚本增强：新增 `reports_graph` API 兜底 + 跨月格式一致性检查 + 逐领域验证
- 独立验证模块 `data_validator.py`：封装五个检查点（语言/数量/覆盖/重复/一致性）+ `ValidationReport` 类
- 现有 05/06/07 三个月数据（315+400+403 篇）全部通过验证
- 文件：`wuxing_flowengine/scripts/baai_scraper.py`、`scripts/data_validator.py`、`docs/网站数据采集经验总结.md`

### 14. P0#1 公式结构级变更：S_p 广义平均集成到生产引擎
- **背景**: 设计文档 9.4 P0#1 确认 S=1.7 << θ_critical=90，穷举 S 上限 1.47 与实测吻合，旧乘积公式量纲不可达
- **方案**: 采用已验证的 S_p（Power Mean/广义平均）替代旧乘积 S = O_t × E_u × C_k × K_y × 100
- **核心公式**: `S_p = M_p × 100`, `M_p = [ (O_t^p + E_u^p + C_k^p + K_y^p) / 4 ]^(1/p)`, p=0.5（P忠恕中道）
- **创建** `scripts/dao_math.py`：共享数学工具模块（compute_S_p, compute_S_p_weighted, compute_S_old, p_label）
- **更新 8 个文件**：
  - `dao_realm_engine.py`：S 计算改用 S_p，输出增加 S_formula/S_p/p/p_label/S_old 字段
  - `stage_engine.py`：θ_base 60→50（适配 S_p 量纲），S 参数文档更新
  - `config_default.json`：theta_critical.base 60→50
  - `phase1_pipeline.py`：tracks 增加 S_p/S_formula/p/p_label
  - `phase2_pipeline.py`：同上
  - `guidance.py`：四维解读 S 改用 S_p
  - `domain_calibration.py`：领域 S 改用 S_p
  - `k_y_enhancer.py`：原始/增强 S 改用 S_p
- **全局路径迁移**：所有脚本 DEFAULT_BASE 从 AppData 路径迁移到 E:\ 工作区路径（15 处）
- **验证结果**：
  - 月度流水线 8 阶段全部通过
  - S_p(2026-08)=39.5，旧 S=1.7，阶段判定"克"（S_p=39.5 < θ_critical=75）
  - Phase C2 K_y 增强 S 从 1.7→36.9（量纲正确）
  - Phase C1 领域校准 mean_S 在 16.9~57.6 范围（量纲合理）
  - p-P忠恕验证 5 项检查全部通过
- **文件**: `scripts/dao_math.py`（新增）, `scripts/dao_realm_engine.py`, `scripts/stage_engine.py`, `config/config_default.json`, `scripts/phase1_pipeline.py`, `scripts/phase2_pipeline.py`, `scripts/guidance.py`, `scripts/domain_calibration.py`, `scripts/k_y_enhancer.py`, `scripts/monthly_pipeline.py` 等 15 个文件

### 15. README.md S_p 公式文档完善
- **新增** `## 存在度 S_p 公式（V1.2 公式结构变更）` 章节，包含：
  - 为什么需要 S_p：旧乘积公式量纲不可达的根因说明
  - 核心公式：`S_p = M_p × 100`, `M_p = [ (O_t^p + E_u^p + C_k^p + K_y^p) / 4 ]^(1/p)`
  - p 的伦理语义表（1.0/0.8/0.5/0.3/0.0/-1.0 六档恕度标签 + 适用场景）
  - S_p 与全局阶段判定的关系：仅作为"化"判定输入，不替代全局阶段
  - P忠恕版 S 卡格式示例
  - 集成点表：8 个模块的 S_p 使用方式
- **文件**: `wuxing_flowengine/README.md`

### 16. WRL DSL Phase 1：规则清单 + 元数据标注
- 创建 `wuxing_flowengine/rules/` 目录，按设计文档 10.2 节四分类创建 `.wrl` 规则文件
- **32 条规则，4 个文件**：
  - `classical_rules.wrl`（4 条）：C-SHENG, C-KE, C-WX-COORD, C-WX-ROLES — 经典文献规则，不可修改
  - `formal_rules.wrl`（8 条）：F-ENTROPY, F-CENTROID, F-O_T, F-E_U, F-C_K, F-K_Y, F-S_P, F-THETA — 数学定义，可校准
  - `heuristic_rules.wrl`（16 条）：阶段判定链（6 子规则）+ H-DOMINANCE, H-SCARCITY, H-ENTROPY-CLASS, H-PATH-PROFILES, H-FREQ-INTERPRETATION, H-DEPTH-WEIGHTS, H-STAGE-GUIDANCE, H-WUXING-ADJUSTMENT, H-CLASSICAL-REFERENCES, H-FOUR-DIMS-INTERPRETATION — 经验判断，可校准
  - `domain_rules.wrl`（4 条）：D-SCHOLARLY, D-PRACTICAL, D-EDUCATIONAL, D-DEFAULT — 领域预设，可配置
- 每条规则携带完整元数据：rule_id, category, source（type/reference/quote）, mutability, calibration_status, affects, depends_on, validation, code_location
- 覆盖度：经典规则 4/4 (100%), 形式规则 8/8 (100%), 启发式规则 16/16 (100%), 领域规则 4/4 (100%)
- 此阶段为纯文档化（Phase 1），不影响现有代码运行。后续 Phase 2 将创建 WRL 解析器 + 规则注册表，Phase 3 逐步替换硬编码逻辑
- **文件**: `wuxing_flowengine/rules/classical_rules.wrl`, `formal_rules.wrl`, `heuristic_rules.wrl`, `domain_rules.wrl`

### 17. P0#2 案例数据真实化：设计文档第六章案例 S_p 重算
- 用 `validate_p_zhongshu.py` 的 S_p 公式（p=0.5）重算设计文档第六章全部案例数据
- **6.1 小禾案例**：S_p=31.1（旧 S=0.5），θ_critical=75，阶段判定逻辑完整追迹（ke=0 + H_ratio=0.93 > 0.85 → fallback "生"）
- **6.2 小石案例**：S_p=25.3（旧 S=0.2），θ_critical=30，增补宽恕版 S_p(p=0.8)=27.8
- **6.3 孔子案例**：六阶段 S_p 重算，S_p ∈ [29.7, 37.7]，呈"∧"形轨迹（峰值在"不惑"37.7，非"从心所欲"），旧 S 列（12/48/72/85/92/98）标注为叙事性占位
- **8.2 历史轨迹**：以孔子六阶段为原型重写，5 个时间点全部公式验证，S_p 不是单调递增
- 同步更新：3.4 节（S_p 公式）、4.5 节（θ_base 60→50）、7.1 节（theta_base 60→50）、8.1 节（示例数字）、9.3.1 节（S_p 列 + 判定说明）、9.3 验证结论（P0#1/P0#3/P1#5/P1#10 标记已解决）、9.4 下一步行动（P0 全部解决）
- **文件**: `wuxing_flowengine/docs/五行诊断与道境坐标系：融合设计方案 V1.2.md`

### 18. P1#6 系数校准：v1.0_initial 首次校准实验
- 创建 `scripts/calibrate_coefficients.py` 校准实验脚本，对 12 个映射系数完成四大实验
- **实验 1 — 灵敏度分析**：每系数 ±30% 扰动，测量 8 案例 S_p 平均变化。仅 O_t.土 为"中"灵敏度（ΔS_p≈1.2），其余 11 个为"低"灵敏度（<1.0）。E_u 三维系数灵敏度最低（<0.22），因 Power Mean 平滑效应
- **实验 2 — 可辨识性分类**：结构锁定 6 个（五行经典约束）、可辨识 3 个（K_y.土/火、C_k.火）、经验依赖 3 个（O_t.entropy、K_y.ke、E_u.centroid_modulus）
- **实验 3 — 约束边界探测**：所有系数安全区间充裕（79.5x~590.7x），无紧约束。C_k.水 安全倍数最小（79.5x），因在案例中接近上界
- **实验 4 — 优化建议**：P0 锁定 6 个结构系数，P1 建议 3 个可辨识系数用真实数据做网格搜索，P2 维持 3 个经验系数
- **结论**：v1.0_initial 系数整体稳定，当前无需调整任何系数。待真实时间序列接入后对 P1 系数做数据驱动校准，生成 v1.1_calibrated 版本
- 设计文档新增 9.6 节（系数校准实验），更新 9.3.1 遗留问题表（P1#6 标记已解决）、9.4 下一步行动（第 5 项标记已完成）
- **文件**: `wuxing_flowengine/scripts/calibrate_coefficients.py`（新增）, `wuxing_flowengine/docs/五行诊断与道境坐标系：融合设计方案 V1.2.md`, `PROJECT_CONTEXT.md`

### 19. Phase 5: P忠恕伦理 + 旋量形式化 + 同态映射引擎集成
- 基于《反者道之动_矛盾迭代引擎_五轮对话深度复盘_完善版》共振三和共振六，实现同态映射的伦理维度与数学形式化
- **P忠恕伦理模块** (`zhongshu_ethics.py`)：
  - 忠度 (Zhong): 源域结构保持度 — 四维评估（节点覆盖率 30% + 关系保持度 35% + 五行忠实度 20% + 层级忠实度 15%）
  - 恕度 (Shu): 目标域相容度 — 三维评估（完整度 30% + 冲突检测 40% + 相容度 30%）
  - 忠恕综合 (ZS): 调和平均（偏向短板），四等级分类（忠恕兼备/偏忠/偏恕/忠恕不足）
  - 伦理约束注入：`inject_to_candidate()` 将忠恕评估注入候选映射 metadata
  - 经典引用：每等级附带儒家经典原文
- **旋量形式化模块** (`spinor_formalism.py`)：
  - 旋量相位模型：θ=0°（正题）→ 180°（反）→ 360°（道之动，-1 相位翻转）→ 720°（完全回归，+1）
  - 关键洞见：360° 旋量语义下携带 -1 相位翻转（非 +1），"升华"是相位积累而非修辞
  - 道旋量状态 (`DaoSpinorState`): 跟踪同态映射的螺旋演化，每次迭代 = 一次否定之否定
  - 旋量-同态桥接 (`SpinorHomomorphismBridge`): 将旋量形式化注入同态映射引擎，自动跟踪每次 transfer
- **同态映射引擎集成** (`homomorphism_engine.py` 更新)：
  - `__init__` 新增 `enable_zhongshu` 和 `enable_spinor` 开关
  - `transfer()` 在 Step 2 后自动执行忠恕伦理校验，在 Step 3 后自动执行旋量形式化跟踪
  - `format_report()` 新增 P忠恕伦理和旋量-太极形式化两个展示段
  - `get_stats()` 新增 zhongshu_stats（平均忠恕综合分、高/低忠恕计数）
  - 新增 `get_dao_summary()` 和 `get_all_dao_states()` 查询旋量演化状态
  - `earth_flow_transfer()` 五行流转解读增强忠恕综合标注
- **验证结果**：大语言模型→自然语言处理 忠恕兼备 (ZS=0.78)，大语言模型→生成式AI 忠恕不足 (ZS=0.66)
- **文件**: `wuxing_flowengine/scripts/zhongshu_ethics.py`（新增）, `wuxing_flowengine/scripts/spinor_formalism.py`（新增）, `wuxing_flowengine/scripts/homomorphism_engine.py`（更新）

---

## 版本控制约定

每次提交代码前：
1. 读取 `PROJECT_CONTEXT.md`，与本地实际状态比较
2. 如有冲突（文件不存在、接口变更、架构调整等），提示用户处理
3. 无冲突则提交，并在提交后更新 `PROJECT_CONTEXT.md` 的相关条目

## 待办 / 已完成 工作流

- 新任务 → 先添加到 **待办事项** 列表
- 任务完成 → 从待办移至 **已完成** 列表，标注编号、根因、修复、文件
- 更新 `PROJECT_CONTEXT.md` 时，检查待办列表中是否有已完成的项，一并移动

## 待办

- [ ] 微信公众号 URL 批量提取 API
- [ ] 后端代码纳入 Git 仓库管理（当前仅在服务器 `/opt/meta-skill/` 目录）

## 新对话快速启动

在新对话中引用此文件即可继续开发：
> "参考 PROJECT_CONTEXT.md 继续开发道境空间"