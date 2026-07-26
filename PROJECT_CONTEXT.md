# SkillUp Studio 项目上下文

## 项目概述

**SkillUp Studio** — 莫比乌斯环概念地图生成器。

- [meta-skill.org/studio/](https://meta-skill.org/studio/) — 公开 demo
- [hui-skill.cn/studio/](https://hui-skill.cn/studio/) — 自部署实例

两个站点共享同一份代码，功能一致。用户选择数据集或输入文本，一键生成可交互的 3D 概念地图 HTML。

## 关键文件

| 文件 | 用途 |
|------|------|
| `frontend/studio/index.html` | 主页面（包含 HTML/CSS/JS 全部逻辑） |
| `frontend/studio/styles.css` | 样式文件 |
| `frontend/studio/build_mobius.js` | 莫比乌斯环 3D 渲染引擎（Three.js） |
| `frontend/studio/functions/api/[[path]].js` | Cloudflare Pages Function — meta-skill API 代理 |
| `frontend/studio/preset-data/*.json` | 预设数据集（11 个） |
| `frontend/studio/_redirects` | Cloudflare Pages 路由规则 |
| `deploy/hui-skill/nginx-hui-skill.conf` | hui-skill.cn Nginx 配置 |
| `deploy/hui-skill/deploy.ps1` | hui-skill.cn 部署脚本 |

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

### meta-skill.org (Cloudflare Pages)

```bash
cd frontend/studio
npx wrangler pages deploy . --project-name=meta-skill-studio --branch=main --commit-dirty=true
```

部署后注意 CDN 缓存，可能需要加版本参数或手动清除缓存才能看到新效果。

### hui-skill.cn (服务器 Nginx)

```powershell
# 仅部署前端
.\deploy\hui-skill\deploy.ps1

# 完整部署（前端 + Nginx 配置）
.\deploy\hui-skill\deploy.ps1 -full
```

前置: 已配置 SSH 密钥到 `root@121.41.215.36`（见 `deploy.ps1` 顶部注释）。

## 站点架构

两个站点共享同一份 `frontend/studio/` 代码和后端 API，前端各自独立部署：

```
┌─────────────────────────────────────────────────────────┐
│  frontend/studio/  (同一份代码)                          │
│  ├── meta-skill.org  ──wrangler──>  Cloudflare Pages    │
│  │   └── /api/*  ──CF Function──>  hui-skill.cn:8000   │
│  └── hui-skill.cn    ──rsync────>  121.41.215.36 Nginx │
│      └── /api/*  ──直连────────>  127.0.0.1:8000       │
└─────────────────────────────────────────────────────────┘
```

| 站点 | 部署 | 文本输入 | 预设数据集 | API 方式 |
|------|------|:---:|:---:|------|
| meta-skill.org/studio/ | Cloudflare Pages | ✅ | ✅ | 代理转发 (X-Domain-Role: demo) |
| hui-skill.cn/studio/ | 121.41.215.36 Nginx | ✅ | ✅ | 直连本机 FastAPI |

## API 架构

- 文本提取: `POST /api/studio/extract`（body: `{ text: "..." }`）
- 微信公众号 URL 提取: `POST /api/studio/extract`（body: `{ url: "..." }`）— 仅后端 API，前端暂不暴露
- 预设数据: 前端直接加载 `preset-data/*.json` 静态文件
- CORS 已配置为 `*`

## 已修复的问题

### 1. Cloudflare Pages Function 请求体转发
- **根因**: `Request.body` 是 ReadableStream，`await request.text()` 消费后 body 为空，导致后端 JSON 解析失败
- **修复**: 直接透传 `request.body`，不先读取再重构
- **文件**: `functions/api/[[path]].js`

### 2. 自由输入模式切换状态不一致
- **根因**: 切换文本/URL 输入模式时，之前的数据和生成按钮状态未复位
- **修复**: 为文本输入和 URL 输入添加互斥逻辑（输入时清空对方字段），并在模式切换时调用 `resetFreeInputInputState()` 复位标题、生成按钮和提取结果
- **文件**: `index.html`

### 3. 移除微信公众号 URL 前端输入
- 前端统一为纯文本输入，界面更简洁。微信公众号提取功能保留在后端 API，后续用于批量提取
- 移除 HTML 中的 URL 输入区域和相关 JS 逻辑（freeUrlInput DOM 引用、事件监听、互斥逻辑、URL 提取分支）
- 清理 `.url-input-row` 和 `.url-input` CSS 残留

### 4. 按钮样式统一 + 字数上限
- **提取概念按钮** 样式统一为与"生成 HTML"一致：`width: 100%`、`padding: 16px`、`font-size: 17px`、`border-radius: 10px`、置中显示
- 文本输入增加 `maxlength="5000"`，字数统计显示 `X / 5000 字` 格式
- **文件**: `index.html`、`styles.css`

## 版本控制约定

每次提交代码前：
1. 读取 `PROJECT_CONTEXT.md`，与本地实际状态比较
2. 如有冲突（文件不存在、接口变更、架构调整等），提示用户处理
3. 无冲突则提交，并在提交后更新 `PROJECT_CONTEXT.md` 的相关条目

## 待办事项

- [ ] hui-skill.cn 服务器 SSH 密钥配置
- [ ] hui-skill.cn 首次部署（Nginx + 前端）
- [ ] 微信公众号 URL 批量提取 API

## 新对话快速启动

在新对话中引用此文件即可继续开发：
> "参考 PROJECT_CONTEXT.md 继续开发 SkillUp Studio"