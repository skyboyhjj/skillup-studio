# hui-skill.cn — 道境空间 × AI 知识引擎

以道境空间为底色，以 AI 技术为引擎，面向知识工作者构建的新一代智能研究平台。

## 产品矩阵

| 产品 | 状态 | 描述 |
|------|------|------|
| 知识图谱标注平台 | 已上线 | 专为道境空间概念设计的智能标注工作台，支持多维标注、规则推理、数据交换 |
| 莫比乌斯概念地图 | 已上线 | 3D 交互式知识可视化，一键生成可交互的莫比乌斯环概念地图 |
| 知识树追踪引擎 | 即将上线 | 基于五行理论的 AI 知识领域动态追踪，月度论文采集、结构诊断与趋势分析 |
| 论文采集器 | 预览版 | arXiv 自动化月度采集，覆盖 11 个 AI 子领域；100 篇样本可筛选/搜索/导出 |

## 技术栈

- **前端框架**：纯静态 HTML + Tailwind CSS v4.3.1（CDN 运行时）
- **图标**：Lucide Icons v1.8.0（CDN）
- **设计系统**：基于 CSS 自定义属性的品牌 Design Token 体系
- **部署**：Nginx 静态托管，无需构建工具

## 项目结构

```
hui-skill-product-matrix/
├── pages/
│   ├── index.html          # 产品矩阵首页
│   ├── annotate.html       # 知识图谱标注平台
│   └── papers.html         # 论文采集器（预览版）
├── data/
│   └── papers-2026-06.json # 论文数据集（100 篇 arXiv）
├── colors_and_type.css      # 品牌 Design Token 定义
├── hui-skill-product-matrix.design  # 设计画布元数据
├── ARCHITECTURE.md          # 架构设计文档
└── README.md
```

## 快速开始

### 本地预览

```bash
cd hui-skill-product-matrix
python -m http.server 8080
```

访问 http://localhost:8080/pages/index.html 查看产品矩阵首页。

### Nginx 部署

```nginx
server {
    listen 80;
    server_name hui-skill.cn;

    root /var/www/hui-skill-product-matrix;
    index pages/index.html;

    location / {
        try_files $uri $uri/ =404;
    }
}
```

## 设计系统

品牌色系以墨色为底、朱砂红为辅，搭配宣纸白卡片，营造东方美学与现代科技交融的视觉基调。

| Token | 亮色 | 暗色 |
|-------|------|------|
| `--brand-primary` | `#C94B3A` | `#C94B3A` |
| `--brand-background` | `#FAF8F5` | `#141210` |
| `--brand-card` | `#FFFFFF` | `#1C1A17` |
| `--brand-foreground` | `#1A1715` | `#EDE8E3` |

完整 Token 定义见 `colors_and_type.css` 和 `ARCHITECTURE.md`。

## 权限模型

- **游客**：无需注册，可浏览公开数据集与预设功能
- **注册用户**：解锁完整标注、数据管理、规则库管理与 API 访问

## 许可

内部项目，暂未开源。