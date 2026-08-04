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
| `wuxing_flowengine/scripts/monthly_pipeline.py` | 月度编排器（Phase 1→2→3+→B→C + 时间序列 + 验证） |
| `wuxing_flowengine/docs/` | 设计文档（融合设计方案 V1.2 + 数据采集经验总结） |

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
- **Phase 1**: 认知深度估算（L1-L4 关键词匹配）→ 五行映射（16 领域 + 关键词回退）→ 三层构建（种子/现行/超越）→ 四维计算（O_t/E_u/C_k/K_y）→ 存在度 S
- **Phase 2**: 双层标注（概念名 + 五行标签）+ Spinor 层构建 + 领域追踪
- **Phase 3+**: 论文五行分类 + 领域漂移分析（余弦距离）
- **Phase B** (`dao_realm_engine.py`): 道境诊断引擎 — 五步算法（诊断→四维映射→S 计算→阶段判定→导航建议）
- **Phase C2** (`k_y_enhancer.py`): K_y 缘位增强 — 自适应混合 E_relation（ke_density × β + graph_cohesion × (1-β)）
- **Phase C1** (`domain_calibration.py`): 领域基准校准
- 四个月度快照（2026-05/06/07/08）+ 时间序列 delta 链
- 文件：`wuxing_flowengine/diagnose/wuxing_diagnose_v2.py`、`scripts/phase1_pipeline.py`、`scripts/phase2_pipeline.py`、`scripts/phase3_plus_pipeline.py`、`scripts/dao_realm_engine.py`、`scripts/stage_engine.py`、`scripts/guidance.py`、`scripts/k_y_enhancer.py`、`scripts/domain_calibration.py`、`scripts/monthly_pipeline.py`、`scripts/timeseries_analysis.py`、`scripts/wuxing_dsl.py`、`docs/`

### 9. P0/P1 修复：层间路径分析 + 通阶段画像匹配
- **P0**: `_edge_paths()` 从全量桩代码（恒返回 10 条）重写为实际层间主导行分析
  - 逐对检查种子→现行、现行→超越的层间主导行是否构成相生/相克
  - `ke_edge_count` 从恒为 5 变为实际值 0-2，K_y 不再饱和，S 值恢复合理区间
- **P1-1**: 通阶段补全"路径匹配画像"条件
  - 新增 `dim3_profile` 输出（层主导行/路径串/画像匹配）
  - `matches_profile = 至少一条相生边 + 无相克边`
  - `stage_engine.py` 通阶段判定改为 `matches_profile AND 0.50 < H_ratio < 0.85`
- 文件：`wuxing_flowengine/diagnose/wuxing_diagnose_v2.py`、`scripts/stage_engine.py`

### 10. 数据采集经验总结 + 验证模块
- 总结智源社区（hub.baai.ac.cn）知识树 + 科研月报采集的七条核心教训
  - API 优先、格式不假设、逐领域验证、语言检测、弹窗处理、URL 编码、历史回溯
- 采集脚本增强：新增 `reports_graph` API 兜底 + 跨月格式一致性检查 + 逐领域验证
- 独立验证模块 `data_validator.py`：封装五个检查点（语言/数量/覆盖/重复/一致性）+ `ValidationReport` 类
- 现有 05/06/07 三个月数据（315+400+403 篇）全部通过验证
- 文件：`wuxing_flowengine/scripts/baai_scraper.py`、`scripts/data_validator.py`、`docs/网站数据采集经验总结.md`

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