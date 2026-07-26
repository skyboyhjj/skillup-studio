# SkillUp Studio 项目上下文

## 项目概述

**SkillUp Studio** — 莫比乌斯环概念地图生成器，部署于 [meta-skill.org](https://meta-skill.org)。

用户选择数据集或输入文本/微信公众号 URL，一键生成可交互的 3D 概念地图 HTML。

## 项目路径

```
C:\Users\hejij\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a59e217b55e181ea97f0df3\frontend\studio\
```

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

## 已修复的问题

### 1. Cloudflare Pages Function 请求体转发
- **根因**: `Request.body` 是 ReadableStream，`await request.text()` 消费后 body 为空，导致后端 JSON 解析失败
- **修复**: 直接透传 `request.body`，不先读取再重构
- **文件**: `functions/api/[[path]].js`

### 2. 自由输入模式切换状态不一致
- **根因**: 切换文本/URL 输入模式时，之前的数据和生成按钮状态未复位
- **修复**: 为文本输入和 URL 输入添加互斥逻辑（输入时清空对方字段），并在模式切换时调用 `resetFreeInputState()` 复位标题、生成按钮和提取结果
- **文件**: `index.html`

## API 架构

前端 -> Cloudflare Pages Function (`functions/api/[[path]].js`) -> hui-skill.cn 后端

- 代理层添加 `X-Domain-Role: demo` 头
- 微信公众号提取接口: `POST /api/studio/extract`（body: `{ url: "..." }`）
- CORS 已配置为 `*`

## 待办事项

（在此记录后续开发计划）

## 新对话快速启动

在新对话中引用此文件即可继续开发：
> "参考 PROJECT_CONTEXT.md 继续开发 SkillUp Studio"