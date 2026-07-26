# SkillUp Studio — 莫比乌斯环概念地图生成器

基于三维莫比乌斯环的可交互概念地图生成工具。选择预设数据集或自由输入内容，一键生成带有五空动画效果的 3D 概念关系图。

## 在线体验

**[meta-skill.org/studio/](https://meta-skill.org/studio/)**

## 功能

- 预设数据集：儒学、道学、中医、科技、数学等多个领域的概念地图模板
- 自由输入：粘贴文本或微信公众号文章链接，AI 自动提取核心概念
- 五空动画：三轮体空、大圆镜智、觉知域、为道日损、色空不二
- 一键下载：生成独立 HTML 文件，可在本地浏览器打开

## 部署

本项目通过 Cloudflare Pages 部署，静态站点由 `main` 分支驱动。

```
frontend/studio/   → Cloudflare Pages 静态站点
deploy/meta-skill/ → Cloudflare Worker API 代理
```

## 许可证

MIT License