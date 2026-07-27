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
| `frontend/studio/template.html` | 生成的 HTML 模板（含 Canvas 渲染、UI 层、工具栏） |
| `frontend/studio/_worker.js` | **Cloudflare Pages Function — 路由总管**（API 代理 + 静态资源 + /studio/ 前缀处理） |
| `frontend/studio/preset-data/*.json` | 预设数据集（11 个） |
| `frontend/studio/_redirects` | Cloudflare Pages 路由规则 |
| `frontend/studio/functions/api/[[path]].js` | ⚠️ 已废弃 — 被 `_worker.js` 替代，API 代理逻辑已迁移 |
| `deploy/meta-skill/worker.js` | ⚠️ 已废弃 — 独立 Worker，无法连接自定义域名，已迁移到 `_worker.js` |
| `deploy/meta-skill/wrangler.toml` | Worker 部署配置（两个环境：default + production） |
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

`_worker.js` 作为 Pages Function 随 Pages 项目一起部署，无需单独部署 Worker：

```bash
cd frontend/studio
npx wrangler pages deploy . --project-name=meta-skill-studio --branch=main --commit-dirty=true
```

部署后注意 CDN 缓存，可能需要加版本参数或手动清除缓存才能看到新效果。

### meta-skill.org Worker（独立部署，当前已废弃）

> ⚠️ 独立 Worker 无法使用 `env.ASSETS` 绑定，不能正确服务静态文件。已迁移到 Pages Function（`_worker.js`）。以下命令仅供参考：
>
> ```bash
> cd deploy/meta-skill
> npx wrangler deploy --config wrangler.toml -e production   # 生产环境
> npx wrangler deploy --config wrangler.toml                  # 默认环境
> ```

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
┌───────────────────────────────────────────────────────────────────┐
│  frontend/studio/  (同一份代码)                                    │
│                                                                    │
│  meta-skill.org  ──wrangler pages──>  Cloudflare Pages            │
│  │   └── _worker.js 路由总管:                                      │
│  │       ├── /api/*  ──代理────>  hui-skill.cn:8000               │
│  │       ├── /       ──302─────>  /studio/                        │
│  │       └── 其他    ──env.ASSETS──>  静态文件（去掉 /studio 前缀）  │
│  │                                                                 │
│  hui-skill.cn    ──rsync────>  121.41.215.36 Nginx                │
│      └── /api/*  ──直连────>  127.0.0.1:8000                      │
└───────────────────────────────────────────────────────────────────┘
```

| 站点 | 部署 | 文本输入 | 预设数据集 | API 方式 | 路由方式 |
|------|------|:---:|:---:|------|------|
| meta-skill.org/studio/ | Cloudflare Pages | ✅ | ✅ | 代理转发 (X-Domain-Role: demo) | `_worker.js` (Pages Function) |
| hui-skill.cn/studio/ | 121.41.215.36 Nginx | ✅ | ✅ | 直连本机 FastAPI | Nginx 反向代理 |

## API 架构

- 文本提取: `POST /api/studio/extract`（body: `{ text: "..." }`）
- 微信公众号 URL 提取: `POST /api/studio/extract`（body: `{ url: "..." }`）— 仅后端 API，前端已移除
- 预设数据: 前端直接加载 `preset-data/*.json` 静态文件
- CORS 已配置为 `*`
- 后端运行在 Docker 容器 `ms-api`（`/opt/meta-skill/`，Docker Compose 管理）

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
- 前端统一为纯文本输入，提取按钮移至文本输入区域下方，界面更简洁
- 移除 HTML 中的 URL 输入区域、`or-divider` 分隔线、`freeUrlInput` DOM 引用、事件监听、互斥逻辑、URL 提取分支
- 清理 `.url-input-row` 和 `.url-input` CSS，替换为 `.extract-btn-row`（按钮右对齐）
- 进度提示文字从"正在获取文章内容..."改为"正在提取概念..."
- 微信公众号提取功能保留在后端 API，后续用于批量提取

### 4. 按钮样式统一 + 字数上限
- **提取概念按钮** 样式统一为与"生成 HTML"一致：`width: 100%`、`padding: 16px`、`font-size: 17px`、`border-radius: 10px`、置中显示
- 文本输入增加 `maxlength="5000"`，字数统计显示 `X / 5000 字` 格式
- **文件**: `index.html`、`styles.css`

### 5. PNG 导出标题缺失 + 重影
- **根因**: `outCtx.width` 引用了不再使用的临时 canvas，应使用 `outCanvas.width`；`strokeText` 描边在主文字之上产生重影
- **修复**: `outCtx.width` → `outCanvas.width`；去掉 `strokeText` 描边，标题使用白色填充、非加粗字体
- **文件**: `index.html`、`template.html`

### 6. PNG/视频导出文件名不含标题
- **修复**: 文件名统一为 `{标题}_莫比乌斯概念地图_{日期}.{扩展名}` 格式
- **文件**: `index.html`、`template.html`

### 7. Cloudflare Worker 无法连接自定义域名 — 静态资源返回 HTML
- **根因**: 独立 Worker（`deploy/meta-skill/worker.js`）部署后无法使用 `env.ASSETS` 绑定，`/studio/` 下所有静态文件（JSON、JS、CSS）被 Cloudflare Pages SPA fallback 返回 `index.html`，导致 `MIME type ('text/html') is not executable` 错误
- **表现**: `build_mobius.js` 加载失败 → `MobiusBuilder is not defined`；JSON 数据加载失败 → 模板回退到默认唯识论数据
- **修复**: 将 Worker 迁移为 Pages Function（`_worker.js`），使用 `env.ASSETS` 直接服务 Pages 静态资源，同时处理 API 代理、根路径重定向、`/studio/` 前缀路由
- **文件**: 新增 `frontend/studio/_worker.js`；废弃 `deploy/meta-skill/worker.js` 和 `functions/api/[[path]].js`

### 8. 四位菲尔兹奖得主数据一致性验证
- 逐一验证 王虹、邓煜、John Pardon、Jacob Tsimerman 四个模板的 JSON 数据与生成的 HTML 中 DEFAULT_RINGS 概念标签完全一致（0 错配）
- 验证节点数、层数、在线预览 Canvas 渲染均正确

### 9. 后端 AI 模型 max_tokens 不足导致 JSON 截断
- **根因**: Docker 容器 `ms-api` 中 `concept_extractor.py` 的 DeepSeek API 调用 `max_tokens=4096`，生成 15-25 个概念的完整 JSON 需要约 6000-8000 tokens，模型输出在 3200-3500 字符处被截断，导致 `JSONDecodeError: Unterminated string`
- **表现**: 微信公众号 URL 提取超长文章时 80% 失败，报错行号每次不同（char 2331 / 3204 等）
- **修复**: `max_tokens: 4096 → 16384`，输入文本截断 `text[:8000] → text[:5000]`（为输出留出更多空间）
- **部署**: 修改源码后 `docker compose build api && docker compose up -d api` 重建容器
- **文件**: `/opt/meta-skill/backend/services/concept_extractor.py`（服务器端，不在 Git 仓库中）

## 版本控制约定

每次提交代码前：
1. 读取 `PROJECT_CONTEXT.md`，与本地实际状态比较
2. 如有冲突（文件不存在、接口变更、架构调整等），提示用户处理
3. 无冲突则提交，并在提交后更新 `PROJECT_CONTEXT.md` 的相关条目

## 待办事项

- [ ] 微信公众号 URL 批量提取 API
- [ ] 后端代码纳入 Git 仓库管理（当前仅在服务器 `/opt/meta-skill/` 目录）

## 新对话快速启动

在新对话中引用此文件即可继续开发：
> "参考 PROJECT_CONTEXT.md 继续开发 SkillUp Studio"