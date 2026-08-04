# hui-skill.cn — 道境空间 × AI 知识引擎

以道境空间为底色，以 AI 技术为引擎，面向知识工作者构建的新一代智能研究平台。

- **公开 Demo**: [meta-skill.org/studio/](https://meta-skill.org/studio/)
- **自部署实例**: [hui-skill.cn](https://hui-skill.cn/)

## 产品矩阵

| 产品 | 状态 | 描述 |
|------|------|------|
| 知识图谱标注平台 | 已上线 | 专为道境空间概念设计的智能标注工作台，支持 6 维标注（五行、八卦、认知深度等）、规则推理、数据交换 |
| 莫比乌斯概念地图 | 已上线 | 3D 交互式知识可视化，一键生成可交互的莫比乌斯环概念地图，支持文本提取与 11 组预设数据集 |
| 知识树追踪引擎 | 即将上线 | 基于五行理论的 AI 知识领域动态追踪，月度论文采集、结构诊断与趋势分析 |
| 论文采集器 | 预览版 | arXiv 自动化月度采集，覆盖 11 个 AI 子领域；100 篇样本可筛选/搜索/导出 |

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端 | 纯静态 HTML + Tailwind CSS v4.3.1 (CDN) + Lucide Icons v1.8.0 (CDN) | 产品矩阵 |
| 前端 | Three.js + Canvas | 莫比乌斯 3D 渲染 |
| 后端 | Python FastAPI (Docker) | 文本提取 API |
| 后端 | Python 流水线脚本 | 五行知识图谱诊断引擎 |
| 部署 | Nginx + Cloudflare Pages | 双站点部署 |
| 设计 | CSS 自定义属性 Design Token 体系 | 品牌色系统 |

## 项目结构

```
hui-skill-cn/
├── README.md                          # 项目总览
├── ARCHITECTURE.md                    # 整体架构设计
├── PROJECT_CONTEXT.md                 # 共享任务参考文档（跨分支协作）
├── .gitignore
│
├── docs/                              # 文档
│   ├── network-monitoring.md          # 带宽监控方案 + 实际流量分析
│   └── design/                        # 设计系统文档
│
├── frontend/                          # 前端模块
│   ├── product-matrix/                # 产品矩阵（产品矩阵首页 + 标注平台）
│   │   ├── pages/
│   │   │   ├── index.html             # 产品矩阵首页
│   │   │   └── annotate.html          # 知识图谱标注平台
│   │   ├── colors_and_type.css        # 品牌 Design Token 定义
│   │   ├── hui-skill-product-matrix.design  # 设计画布元数据
│   │   └── README.md
│   │
│   └── studio/                        # 莫比乌斯概念地图
│       ├── index.html                 # 主页面
│       ├── styles.css                 # 样式
│       ├── build_mobius.js            # 3D 渲染引擎
│       ├── template.html              # 生成模板
│       ├── _worker.js                 # Cloudflare Pages Function
│       ├── _redirects
│       ├── preset-data/               # 11 个预设数据集
│       └── functions/api/             # API 路由
│
├── backend/                           # 后端模块
│   └── wuxing_flowengine/             # 五行知识图谱引擎
│       ├── config/                    # 流水线配置
│       ├── scripts/                   # Python 采集/诊断/报告脚本
│       ├── data/                      # 知识树数据 + 标注数据
│       ├── diagnose/                  # 五行诊断模块
│       ├── output/                    # 诊断输出报告
│       └── docs/                      # 道境坐标系设计文档
│
└── deploy/                            # 部署配置
    ├── nginx/
    │   └── hui-skill.cn.conf          # Nginx 站点配置（含限流规则）
    └── cloudflare/                    # Cloudflare 部署
        ├── worker.js                  # ⚠️ 已废弃
        └── wrangler.toml
```

## 快速开始

### 前端 — 产品矩阵（本地预览）

```bash
cd frontend/product-matrix
python -m http.server 8080
```

访问 http://localhost:8080/pages/index.html

### 前端 — 莫比乌斯概念地图（本地开发）

```bash
cd frontend/studio
npx wrangler pages dev . --port 10081
```

访问 http://127.0.0.1:10081/studio/

### 后端 — 五行知识图谱引擎

```bash
cd backend/wuxing_flowengine
python scripts/monthly_pipeline.py
```

## 设计系统

品牌色系以墨色为底、朱砂红为辅，搭配宣纸白卡片，营造东方美学与现代科技交融的视觉基调。

| Token | 亮色 | 暗色 | 用途 |
|-------|------|------|------|
| `--brand-primary` | `#C94B3A` | `#C94B3A` | 主按钮、链接、强调 |
| `--brand-background` | `#FAF8F5` | `#141210` | 页面底色 |
| `--brand-card` | `#FFFFFF` | `#1C1A17` | 卡片/面板 |
| `--brand-foreground` | `#1A1715` | `#EDE8E3` | 文字主色 |

完整 Token 定义见 `frontend/product-matrix/colors_and_type.css`。

## 权限模型

- **游客**：无需注册，可浏览公开数据集与预设功能
- **注册用户**：解锁完整标注、数据管理、规则库管理与 API 访问

## 部署

- **meta-skill.org**: Cloudflare Pages (`frontend/studio/`)
- **hui-skill.cn**: Nginx 自部署 (`21.41.215.36`)，按流量计费（50 Mbps 峰值）

详见 `docs/network-monitoring.md` 和 `deploy/nginx/hui-skill.cn.conf`。

## 分支管理

| 分支 | 范围 |
|------|------|
| `main` | 前端相关任务（页面、样式、部署、Cloudflare Pages） |
| `hui-skill-cn` | hui-skill.cn 网站相关任务（后端、服务器、Docker、Nginx） |
| `master` | 完整记录汇总 |

详见 `PROJECT_CONTEXT.md`。

## 许可

内部项目，暂未开源。