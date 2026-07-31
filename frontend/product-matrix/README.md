# hui-skill 产品矩阵前端

道境空间 × AI 知识引擎的产品矩阵页面与知识图谱标注平台。

## 页面

| 页面 | 文件 | 类型 | 说明 |
|------|------|------|------|
| 产品矩阵首页 | `pages/index.html` | 展示型 | 非对称布局展示四个产品，区分游客/注册用户权限 |
| 知识图谱标注平台 | `pages/annotate.html` | 任务驱动型 | 左侧层级树 + 右侧 6 维标注表单 + 规则库 |

## 品牌设计系统

品牌色系以墨色为底、朱砂红为辅，搭配宣纸白卡片。完整 Token 定义见 `colors_and_type.css`。

| Token | 亮色 | 暗色 | 用途 |
|-------|------|------|------|
| `--brand-primary` | `#C94B3A` | `#C94B3A` | 朱砂红 |
| `--brand-background` | `#FAF8F5` | `#141210` | 宣纸白 / 墨色 |
| `--brand-card` | `#FFFFFF` | `#1C1A17` | 卡片底色 |
| `--brand-foreground` | `#1A1715` | `#EDE8E3` | 文字主色 |

## 技术栈

- 纯静态 HTML + Tailwind CSS v4.3.1（CDN 运行时）
- Lucide Icons v1.8.0（CDN）
- 基于 CSS 自定义属性的 Design Token 体系
- 无需构建工具，直接部署至 Nginx

## 本地预览

```bash
cd frontend/product-matrix
python -m http.server 8080
```

- 产品矩阵首页：http://localhost:8080/pages/index.html
- 标注平台：http://localhost:8080/pages/annotate.html

## 权限模型

- **游客**：可浏览公开数据集，标注表单处于只读模式
- **注册用户**：完整编辑权限，数据管理，规则库管理

当前为前端演示模式，权限切换通过页面内按钮模拟。生产环境需对接后端认证服务。

## 设计工作流

本项目使用 Solo Design 工作流进行页面设计与迭代：

```
用户需求 → 车道匹配 → 预检 → 分发清单 → 子代理生成 → 验证 → 就绪
```

关键元数据文件：

| 文件 | 用途 |
|------|------|
| `hui-skill-product-matrix.design` | 设计画布注册表，记录所有页面节点 |
| `colors_and_type.css` | 品牌 Token 唯一权威来源 |

## 设计资产

- 图标：Lucide Icons（`unpkg.com/lucide@1.8.0`）
- 无图片/视频资源，当前项目不依赖 `assets/` 目录
- 计划将 Tailwind + Lucide 本地化至 `assets/` 消除外部 CDN 依赖