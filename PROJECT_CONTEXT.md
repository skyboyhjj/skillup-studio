# SkillUp Studio 项目上下文

## 项目概述

**SkillUp Studio** — 莫比乌斯环概念地图生成器。

- [meta-skill.org/studio/](https://meta-skill.org/studio/) — 公开 demo，仅支持文本输入提取概念
- [hui-skill.cn](https://hui-skill.cn) — 全功能平台，支持文本 + 微信公众号 URL 提取

用户选择数据集或输入文本，一键生成可交互的 3D 概念地图 HTML。

## 关键文件

| 文件 | 用途 |
|------|------|
| `index.html` | 主页面（包含 HTML/CSS/JS 全部逻辑） |
| `styles.css` | 样式文件 |
| `build_mobius.js` | 莫比乌斯环 3D 渲染引擎（Three.js） |
| `functions/api/[[path]].js` | Cloudflare Pages Function — API 代理转发到 hui-skill.cn |
| `preset-data/*.json` | 预设数据集（11 个） |
| `_redirects` | Cloudflare Pages 路由规则 |

## 预设数据集

| 文件名 | 领域 |
|--------|------|
| AI概念图_21nodes.json | 科技 |
| 2026菲尔兹奖_14nodes.json | 数学 |
| 黄帝内经_23nodes.json | 中医 |
| 儒家心学_21nodes.json | 儒学 |
| 道德经_20nodes.json | 道学 |
| 五行养生_15nodes.json | 中医 |
| 王虹_2026菲尔兹奖_11nodes.json | 数学 |
| 邓煜_2026菲尔兹奖_11nodes.json | 数学 |
| JohnPardon_2026菲尔兹奖_10nodes.json | 数学 |
| JacobTsimerman_2026菲尔兹奖_11nodes.json | 数学 |
| BaseViewSkillUP_19nodes.json | 通用 |

## 部署命令

```bash
cd frontend/studio
npx wrangler pages deploy . --project-name=meta-skill-studio --branch=main --commit-dirty=true
```

部署后注意 CDN 缓存，可能需要加版本参数或手动清除缓存才能看到新效果。

## 站点架构

两个站点共享同一个后端 API（121.41.215.36 / hui-skill.cn），前端各自独立部署：

| 站点 | 部署 | 文本输入 | 微信公众号 URL | 预设数据集 |
|------|------|----------|----------------|------------|
| meta-skill.org/studio/ | Cloudflare Pages | ✅ | ❌ | ✅ |
| hui-skill.cn/studio/ | 121.41.215.36 (Nginx) | ✅ | ✅ | ✅ |

## API 架构

meta-skill.org 前端 -> Cloudflare Pages Function (`functions/api/[[path]].js`) -> hui-skill.cn 后端
hui-skill.cn 前端 -> 直连本机后端 (FastAPI)

- meta-skill 代理层添加 `X-Domain-Role: demo` 头
- 文本提取接口: `POST /api/studio/extract`（body: `{ text: "..." }`）
- CORS 已配置为 `*`

## 已修复的问题

### 1. Cloudflare Pages Function 请求体转发
- **根因**: `Request.body` 是 ReadableStream，`await request.text()` 消费后 body 为空，导致后端 JSON 解析失败
- **修复**: 直接透传 `request.body`，不先读取再重构
- **文件**: `functions/api/[[path]].js`

### 2. 自由输入模式切换状态不一致
- **根因**: 切换文本/URL 输入模式时，之前的数据和生成按钮状态未复位
- **修复**: 为文本输入和 URL 输入添加互斥逻辑（输入时清空对方字段），并在模式切换时调用 `resetFreeInputState()` 复位标题、生成按钮和提取结果
- **文件**: `index.html`

### 3. meta-skill.org 移除微信公众号 URL 输入
- meta-skill.org 仅保留文本输入，微信公众号提取功能迁移到 hui-skill.cn
- 移除 HTML 中的 URL 输入区域和相关 JS 逻辑（freeUrlInput DOM 引用、事件监听、互斥逻辑、URL 提取分支）

## 待办事项

（在此记录后续开发计划）

## 新对话快速启动

在新对话中引用此文件即可继续开发：
> "参考 PROJECT_CONTEXT.md 继续开发 SkillUp Studio"