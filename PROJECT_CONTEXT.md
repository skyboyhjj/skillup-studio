# SkillUp Studio 项目上下文

## 项目概述

**SkillUp Studio** — 莫比乌斯环概念地图生成器。

- [hui-skill.cn/studio/](https://hui-skill.cn/studio/) — 自部署实例

用户选择数据集或输入文本，一键生成可交互的 3D 概念地图 HTML。

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
> "参考 PROJECT_CONTEXT.md 继续开发 SkillUp Studio"