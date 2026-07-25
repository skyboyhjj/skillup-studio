# Meta-Skill.org 技术架构与 AI 助手实现方案

> 版本：v1.0 | 日期：2026-07-24

---

## 一、总览

```
┌──────────────────────────────────────────────────────────────────┐
│                        meta-skill.org                             │
├──────────────┬──────────────────────┬─────────────────────────────┤
│  /studio/    │  /studio/rules/      │  /studio/community/         │
│  概念地图生成器 │  规则引擎工作室        │  规则库社区                  │
│  (现有 SPA)   │  (meta-skill-studio) │  (新建)                     │
│  无需登录     │  需登录 + 角色鉴权     │  浏览无需登录，发布需登录       │
├──────────────┴──────────────────────┴─────────────────────────────┤
│                        API Gateway (/api/)                        │
├──────────────────────────────────────────────────────────────────┤
│   Auth Service  │  Rule Service  │  AI Service  │  Community Svc  │
├──────────────────────────────────────────────────────────────────┤
│                    PostgreSQL + Redis                             │
│              (规则库 JSON 存储 + 用户/会话/缓存)                     │
└──────────────────────────────────────────────────────────────────┘
```

---

## 二、技术栈选型

### 前端

| 层 | 技术 | 理由 |
|----|------|------|
| `/studio/` | 现有实现（原生 JS） | 保持稳定，后续渐进增强 |
| `/studio/rules/` | 原生 JS + CSS（当前 meta-skill-studio.html） | 已完成 DSL 解析、预览生成、AI 聊天面板，无需框架迁移 |
| `/studio/community/` | 原生 JS + CSS | 与 rules 共享 UI 设计语言，降低依赖 |
| 认证页面 | 原生 JS + CSS | 登录/注册/个人中心，轻量即可 |
| UI 设计系统 | CSS 变量统一（`--bg-primary`, `--accent` 等） | 三页面共享同一套设计 token |

### 后端

| 组件 | 技术 | 理由 |
|------|------|------|
| API 框架 | **Python FastAPI** | 与现有 `wuxing_dsl.py` 同语言，DSL 解析器可直接复用；异步高性能 |
| 数据库 | **PostgreSQL** + JSONB | 用户/工作室/权限用关系型；规则库 JSON 用 JSONB 列存储，支持索引查询 |
| 缓存 / 会话 | **Redis** | 用户会话、DSL 操作限流、AI 对话缓存 |
| 任务队列 | Redis + RQ / Celery | 社区审核异步处理、HTML 批量生成 |
| 文件存储 | 本地文件系统 → 后续迁移 OSS | 规则库导出文件、社区分享快照 |

### AI 服务

| 组件 | 技术 | 理由 |
|------|------|------|
| LLM 后端 | **DeepSeek API**（或兼容 OpenAI 接口的模型） | 中文能力强，成本可控 |
| 嵌入模型 | 可选，用于社区规则库相似度搜索 | 未来功能 |
| 请求代理 | 后端 FastAPI 代理，不暴露 API Key | 安全 + 权限控制 + 用量统计 |

---

## 三、数据模型

### 核心表结构

```
users
├── id (UUID, PK)
├── username (UNIQUE)
├── email (UNIQUE)
├── password_hash
├── avatar_url
├── contribution_level (0-4)         # 贡献者等级
├── created_at
└── updated_at

studios
├── id (UUID, PK)
├── name
├── owner_id (FK → users)
├── visibility (private/public)
├── description
├── created_at
└── updated_at

studio_members
├── studio_id (FK → studios)
├── user_id (FK → users)
├── role (owner/admin/member/viewer)
├── ai_depth_limit (L1/L2/L3/L4)     # AI 助手认知深度上限
├── ai_can_edit (boolean)            # 是否允许通过 AI 编辑规则
├── ai_require_approval (boolean)    # 是否需要审批
├── ai_domain_scope (JSON)           # 可操作的领域范围
├── ai_daily_limit (int)             # 每日操作限额
└── joined_at

rule_libraries
├── id (UUID, PK)
├── owner_type (admin/studio/user)   # 归属层级
├── owner_id (UUID)                  # 对应 admin/studio/user 的 id
├── domain (chinese_medicine/daojism/…)
├── rules_json (JSONB)               # 完整的规则 JSON
├── version (int)
├── parent_library_id (FK → self)    # 继承来源
├── created_at
└── updated_at

community_shares
├── id (UUID, PK)
├── author_id (FK → users)
├── library_id (FK → rule_libraries)
├── title
├── description
├── tags (JSONB)
├── license (CC BY 4.0 / CC BY-SA 4.0 / CC0)
├── forked_from (FK → community_shares)  # Fork 来源
├── status (pending/approved/rejected)
├── is_curated (boolean)                 # 是否精选
├── download_count (int)
├── fork_count (int)
├── reviewed_by (FK → users)
├── review_comment
├── created_at
└── updated_at

dsl_audit_logs
├── id (UUID, PK)
├── user_id (FK → users)
├── library_id (FK → rule_libraries)
├── command (MAP/LEARN/CORRECT/LAYER/FLOW)
├── intent (JSONB)                   # 原始 DSL 意图
├── result (JSONB)                   # 执行结果
├── snapshot (JSONB)                 # 撤销快照
└── created_at
```

---

## 四、API 设计

### 认证 API (`/api/auth/`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 注册 |
| POST | `/api/auth/login` | 登录，返回 JWT |
| POST | `/api/auth/logout` | 登出 |
| GET | `/api/auth/me` | 获取当前用户信息 |
| PUT | `/api/auth/profile` | 更新个人资料 |

### 规则 API (`/api/rules/`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/rules/library` | 获取当前用户的合并规则库 |
| GET | `/api/rules/library/:id` | 获取指定规则库 |
| GET | `/api/rules/layers` | 列出所有可用层级（个人/工作室/全局） |
| PUT | `/api/rules/library/:id` | 更新规则库（JSON 编辑器批量保存） |
| POST | `/api/rules/dsl` | 执行 DSL 命令（单条操作） |
| POST | `/api/rules/dsl/batch` | 批量执行 DSL 命令 |
| GET | `/api/rules/audit` | 查询操作日志 |
| POST | `/api/rules/undo` | 撤销最近操作 |
| GET | `/api/rules/preview` | 生成 HTML 预览（服务端渲染） |

### AI 助手 API (`/api/ai/`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/ai/chat` | NL → DSL 转换 + 执行（核心接口） |
| GET | `/api/ai/suggestions` | 获取当前上下文建议 |
| GET | `/api/ai/limits` | 查询当前用户 AI 配额 |

### 社区 API (`/api/community/`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/community/shares` | 浏览社区规则库列表（分页/搜索/标签） |
| GET | `/api/community/shares/:id` | 查看分享详情 |
| POST | `/api/community/shares` | 发布规则库到社区 |
| POST | `/api/community/shares/:id/fork` | Fork 到个人规则库 |
| GET | `/api/community/curated` | 精选集列表 |
| POST | `/api/community/shares/:id/review` | 审核（管理员/维护者） |

### 工作室 API (`/api/studio/`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/studio/create` | 创建工作室 |
| GET | `/api/studio/:id` | 工作室信息 |
| PUT | `/api/studio/:id` | 更新工作室信息 |
| POST | `/api/studio/:id/members` | 邀请成员 |
| PUT | `/api/studio/:id/members/:uid` | 更新成员 AI 权限 |
| DELETE | `/api/studio/:id/members/:uid` | 移除成员 |

---

## 五、AI 助手实现方案

### 5.1 架构

```
┌──────────────────────────────────────────────────────────────┐
│                    前端 (meta-skill-studio.html)               │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │            AI 聊天面板 (已有)                               │ │
│  │  - 用户输入 NL → detectIntent() → executeDSL()              │ │
│  │  - 本地 DSL 解析 + 执行 (离线可用)                          │ │
│  └──────────────────────────────────────────────────────────┘ │
│                            │ HTTP POST /api/ai/chat           │
└────────────────────────────┼──────────────────────────────────┘
                             │
┌────────────────────────────┼──────────────────────────────────┐
│                    后端 FastAPI                                │
│  ┌─────────────────────────▼────────────────────────────────┐ │
│  │              AI Service (/api/ai/)                        │ │
│  │                                                           │ │
│  │  1. 鉴权 → 提取 user_id, role, studio_id                  │ │
│  │  2. 权限检查 → 读取 studio_members.ai_* 字段              │ │
│  │  3. 规则加载 → 合并当前用户可见的全部规则层级               │ │
│  │  4. LLM 调用 → DeepSeek API (NL → DSL 增强)               │ │
│  │  5. DSL 执行 → 复用 wuxing_dsl.py DSLParser               │ │
│  │  6. 审计记录 → 写入 dsl_audit_logs                        │ │
│  │  7. 返回结果 → { success, message, dsl, preview? }        │ │
│  └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

### 5.2 双模式运行

AI 助手支持两种模式，根据网络状况自动切换：

| 模式 | 条件 | 行为 |
|------|------|------|
| **本地模式** | 未登录 或 网络不可用 | 前端 `detectIntent()` + `executeDSL()` 纯本地执行；AI 回应为模板化文本 |
| **云端模式** | 已登录 + 网络可用 | 后端代理 LLM 调用，NL 理解更准确，支持复杂多轮对话，记录审计日志 |

### 5.3 LLM 调用流程

```
用户输入: "把丹参映射到火，权重0.9"
    │
    ▼
┌─────────────────────────────────────────────┐
│  Step 1: 构建 System Prompt                  │
│  - 当前规则库摘要（五行元素 + 已有概念列表）    │
│  - 当前领域（中医/道学）                       │
│  - 用户认知深度（L1-L4）                      │
│  - 用户权限限制（可编辑/只读/需审批）          │
│  - DSL 指令参考（MAP/LEARN/CORRECT/LAYER/FLOW）│
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│  Step 2: NL → DSL 转换（LLM）                 │
│  Input:  "把丹参映射到火，权重0.9"            │
│  Output: {"command":"MAP","concept":"丹参",   │
│            "element":"火","weight":0.9}       │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│  Step 3: 权限检查                             │
│  - 用户是否有编辑权限？→ 是                   │
│  - 操作是否在领域范围内？→ 中医领域，是        │
│  - 是否需要审批？→ 否                          │
│  - 是否超过每日限额？→ 否                      │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│  Step 4: DSL 执行 (wuxing_dsl.py)             │
│  - 执行 MAP 命令                              │
│  - 去重：从其他元素移除丹参                    │
│  - 写入 rules_json                            │
│  - 记录审计日志                                │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│  Step 5: 构建 AI 回应                         │
│  - 成功: "✓ 已将「丹参」映射到 火（权重=0.9）" │
│  - 附带更新后的预览 HTML (可选)               │
│  - 认知深度触发提示（如需升级）                │
└─────────────────────────────────────────────┘
```

### 5.4 System Prompt 模板

```
你是一个五行八卦规则引擎的 AI 助手，名为 Meta-Skill 助手。

## 当前上下文
- 领域：{domain}
- 用户认知深度：{cognitive_depth}
- 用户角色：{role}（{permission_summary}）
- 当前规则库包含 {concept_count} 个概念，分布在 5 个五行元素和 8 个八卦符号中

## DSL 指令参考
- MAP: 映射概念到五行/八卦 → "MAP 概念 → 元素"
- LEARN: 学习新概念关联 → "LEARN 概念 → 元素 weight=N"
- CORRECT: 修正权重或归属 → "CORRECT 概念 weight=N 或 → 元素"
- LAYER: 调整三层架构 → "LAYER 概念 → outer|middle|inner"
- FLOW: 管理流转阶段 → "FLOW add|remove 阶段 → 概念"

## 规则
1. 将用户自然语言转换为上述 DSL 指令
2. 如果用户输入不明确，请求澄清
3. 如果操作可能产生冲突，告知用户
4. 使用 {cognitive_depth} 对应的解释深度
5. 不要执行超出用户权限的操作
```

### 5.5 前端 fallback 策略

当后端不可用时，前端已有完整的本地 DSL 解析能力（`detectIntent()` + `executeDSL()`），可独立运行。区分点：

| 能力 | 本地模式 | 云端模式 |
|------|:--:|:--:|
| NL → DSL 解析 | 正则匹配（已有） | LLM 理解（更准确） |
| 多轮对话 | 不支持 | 支持（上下文记忆） |
| 模糊意图澄清 | 不支持 | 支持 |
| 规则库操作 | 本地 JS 执行 | 服务端执行 + 持久化 |
| 审计日志 | 仅前端内存 | 数据库持久化 |
| 权限检查 | 无 | 完整权限链 |
| 撤销 | 重置为原始数据 | 精确回滚到操作前 |

---

## 六、规则合并引擎

### 合并逻辑

```
function mergeRules(userId):
    adminRules = loadRules(owner_type="admin")         # 管理员全局规则
    studioRules = loadRules(owner_type="studio", owner_id=userStudioId)  # 工作室规则
    personalRules = loadRules(owner_type="user", owner_id=userId)  # 个人规则

    merged = deepMerge(adminRules, studioRules, personalRules)
    # 合并策略：后层覆盖前层同字段
    # 概念去重：同概念在多个层级出现时，保留最高优先级的映射
    return merged
```

### 规则库版本管理

- 每次 DSL 操作生成版本快照
- 支持版本回滚
- 社区分享时锁定特定版本

---

## 七、服务器配置

### 7.1 现有服务器规格

| 配置项 | 实际配置 | 备注 |
|--------|---------|------|
| 实例规格 | 8 vCPU / 16GB DDR4 | ecs.e 系列 V，Intel Xeon |
| 系统盘 | 40 GB ESSD Entry | /dev/xvda |
| 带宽 | 3 Mbps 固定带宽 | 出网带宽上限 ~375 KB/s |
| 操作系统 | Linux 64位（容器版） | 云·原生建站-容器版，预装 Docker |
| 地域/可用区 | 华东1（杭州）可用区K | VPC 专有网络 |
| I/O 优化 | 已启用 | — |

### 7.2 资源评估与建议

| 资源 | 当前规格 | 评估 | 建议 |
|------|---------|------|------|
| CPU | 8 vCPU | 充裕，Phase 1-4 全程够用 | 无需升级 |
| 内存 | 16 GB | 充裕，四服务 + OS 缓存约 8-10GB | 无需升级 |
| 系统盘 | 40 GB | ⚠️ 偏紧：OS ~8GB + Docker 镜像 ~5GB + PostgreSQL 数据 + 日志 | **建议挂载 100GB 数据盘**，将 PostgreSQL、Redis 数据、日志写入数据盘 |
| 带宽 | 3 Mbps | ⚠️ 静态资源并发瓶颈：3 个并发用户即占满 | **静态资源接入 CDN（阿里云 CDN / Cloudflare）**；AI API 调用走服务端，不占用出网带宽 |
| 磁盘类型 | ESSD Entry | 低 IOPS，适合轻量场景 | 数据库建议使用 ESSD PL1 数据盘 |

### 7.3 服务资源分配

```
┌─────────────────────────────────────────────────────────┐
│             阿里云 ECS 8vCPU / 16GB / 40GB               │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Nginx (1 vCPU, 256MB)                            │  │
│  │  - 静态文件服务 (前端 HTML/CSS/JS)                  │  │
│  │  - 反向代理 → FastAPI                             │  │
│  │  - SSL 终端 (Let's Encrypt)                       │  │
│  │  - gzip 压缩 (缓解 3Mbps 带宽压力)                  │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  FastAPI × 2 (Gunicorn + Uvicorn, 2 workers)      │  │
│  │  - 每 worker: 1 vCPU, 512MB                       │  │
│  │  - 处理 /api/* 请求                                │  │
│  │  - 异步 I/O 处理 LLM API 代理（不阻塞）             │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  ┌──────────────┐  ┌──────────────────────────────┐   │
│  │  PostgreSQL  │  │  Redis (1 vCPU, 256MB)        │   │
│  │  (2 vCPU,    │  │  - 会话缓存 (JWT token)       │   │
│  │   2GB)       │  │  - DSL 操作限流计数器          │   │
│  │              │  │  - AI 对话临时缓存             │   │
│  └──────────────┘  └──────────────────────────────┘   │
│                                                         │
│  剩余 ~2 vCPU / ~10GB → OS 缓存 + 峰值余量               │
└─────────────────────────────────────────────────────────┘
```

### 7.4 磁盘空间规划

| 挂载点 | 容量 | 用途 |
|--------|------|------|
| `/` (系统盘) | 40 GB | OS (~8GB) + Docker 镜像 (~5GB) + 应用代码 (~500MB) + Nginx 日志 (~2GB, 7天轮转) |
| `/data` (数据盘) | **100 GB (建议新增)** | PostgreSQL 数据 (~20GB 预留) + Redis 持久化 (~2GB) + 规则库备份 (~10GB) + 应用日志 (~5GB) + 社区分享快照 (~10GB) |

**磁盘不足时的应急方案**（在数据盘挂载前）：
- PostgreSQL 数据目录限制在 10GB 以内
- 日志保留天数从 30 天压缩到 7 天
- 社区分享快照使用按需生成，不预存
- Docker 镜像定期清理 `docker system prune -f`

### 7.5 带宽优化策略

3 Mbps 是主要瓶颈，需从多个层面缓解：

| 策略 | 实现方式 | 预期效果 |
|------|---------|---------|
| **CDN 加速静态资源** | 阿里云 CDN / Cloudflare 缓存前端 HTML/CSS/JS/字体 | 静态资源出网流量降低 90%+ |
| **gzip / brotli 压缩** | Nginx 开启 `gzip on` + `gzip_static on` | HTML/JSON 响应体积缩小 60-80% |
| **API 响应精简** | 分页默认 20 条，支持 `?fields=` 字段过滤 | 减少不必要的数据传输 |
| **AI 代理走服务端** | 用户 → FastAPI → DeepSeek API，不走用户出网 | AI 调用 0 出网带宽消耗 |
| **图片懒加载 + WebP** | 社区页面缩略图使用 WebP，滚动加载 | 减少首屏带宽 |
| **缓存头策略** | `Cache-Control: public, max-age=86400` 对静态资源 | 减少重复请求 |

### 7.6 Docker Compose 部署配置

服务器为容器版，建议使用 Docker Compose 编排全部服务：

```yaml
# docker-compose.yml
version: '3.8'

services:
  nginx:
    image: nginx:1.25-alpine
    container_name: ms-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./frontend:/usr/share/nginx/html:ro
      - ./deploy/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./deploy/nginx/conf.d:/etc/nginx/conf.d:ro
      - ./deploy/certbot/www:/var/www/certbot:ro
      - ./deploy/certbot/conf:/etc/letsencrypt:ro
      - nginx_logs:/var/log/nginx
    depends_on:
      - api
    restart: unless-stopped
    networks:
      - ms-net
    mem_limit: 256m
    cpus: '1.0'

  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: ms-api
    expose:
      - "8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://ms_user:${DB_PASSWORD}@db:5432/meta_skill
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
      - DEEPSEEK_BASE_URL=${DEEPSEEK_BASE_URL:-https://api.deepseek.com/v1}
      - CORS_ORIGINS=https://meta-skill.org
      - LOG_LEVEL=INFO
    volumes:
      - ./data/rule_libraries:/app/data/rule_libraries
      - app_logs:/app/logs
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - ms-net
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 1g
    command: >
      gunicorn main:app
      --worker-class uvicorn.workers.UvicornWorker
      --workers 2
      --bind 0.0.0.0:8000
      --max-requests 1000
      --max-requests-jitter 100
      --timeout 60
      --keep-alive 5

  db:
    image: postgres:16-alpine
    container_name: ms-db
    environment:
      - POSTGRES_USER=ms_user
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_DB=meta_skill
    volumes:
      - pg_data:/var/lib/postgresql/data
      - ./deploy/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    expose:
      - "5432"
    restart: unless-stopped
    networks:
      - ms-net
    mem_limit: 2g
    cpus: '2.0'
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ms_user -d meta_skill"]
      interval: 10s
      timeout: 5s
      retries: 5
    command: >
      postgres
      -c shared_buffers=512MB
      -c effective_cache_size=1GB
      -c max_connections=100
      -c log_rotation_age=1d
      -c log_rotation_size=100MB

  redis:
    image: redis:7-alpine
    container_name: ms-redis
    command: >
      redis-server
      --maxmemory 256mb
      --maxmemory-policy allkeys-lru
      --save 900 1
      --save 300 10
      --appendonly yes
    volumes:
      - redis_data:/data
    expose:
      - "6379"
    restart: unless-stopped
    networks:
      - ms-net
    mem_limit: 256m
    cpus: '1.0'
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

networks:
  ms-net:
    driver: bridge

volumes:
  pg_data:
    driver: local
    driver_opts:
      device: /data/postgres
      o: bind
  redis_data:
    driver: local
    driver_opts:
      device: /data/redis
      o: bind
  nginx_logs:
  app_logs:
```

### 7.7 Dockerfile (FastAPI)

```dockerfile
# backend/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 应用代码
COPY . .

# 非 root 运行
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
```

### 7.8 Nginx 核心配置

```nginx
# deploy/nginx/conf.d/meta-skill.conf
upstream api_backend {
    server api:8000;
}

server {
    listen 80;
    server_name meta-skill.org www.meta-skill.org;

    # 静态资源：强缓存 + gzip
    location /studio/ {
        alias /usr/share/nginx/html/studio/;
        try_files $uri $uri/ /studio/index.html;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    location /studio/rules/ {
        alias /usr/share/nginx/html/rules/;
        try_files $uri $uri/ /studio/rules/index.html;
        expires 1d;
    }

    location /studio/community/ {
        alias /usr/share/nginx/html/community/;
        try_files $uri $uri/ /studio/community/index.html;
        expires 1d;
    }

    # API 反向代理
    location /api/ {
        proxy_pass http://api_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;  # AI 调用可能较慢
        proxy_buffering off;      # SSE 支持（未来）
    }

    # gzip 压缩
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml+rss;
    gzip_min_length 256;
    gzip_comp_level 5;
    gzip_vary on;

    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
}
```

### 7.9 域名与 SSL 配置

| 域名 | 指向 | 说明 |
|------|------|------|
| `meta-skill.org` | ECS 公网 IP | 主站 |
| `www.meta-skill.org` | CNAME → `meta-skill.org` | www 重定向 |
| `api.meta-skill.org` | 同 ECS（或未来独立部署） | API 子域名（可选，初期复用主域名 `/api/`） |
| `cdn.meta-skill.org` | 阿里云 CDN 回源 | 静态资源 CDN（带宽缓解后启用） |

SSL 证书使用 **Let's Encrypt + Certbot**，通过 Nginx 插件自动续期：

```bash
# 首次申请
docker compose run --rm certbot certonly --webroot \
  --webroot-path=/var/www/certbot \
  -d meta-skill.org -d www.meta-skill.org

# 自动续期（crontab 每月执行）
0 3 1 * * docker compose run --rm certbot renew --quiet && docker compose exec nginx nginx -s reload
```

### 7.10 监控与运维

| 维度 | 工具 | 说明 |
|------|------|------|
| 容器监控 | `docker stats` + cAdvisor (可选) | CPU/内存/网络实时监控 |
| 日志聚合 | Docker `json-file` driver + `docker logs` | 初期够用，后续可切 Loki |
| 应用健康检查 | `/api/health` 端点 | 返回 `{"status":"ok","db":"connected","redis":"connected"}` |
| 数据库备份 | `pg_dump` + cron 每日备份 | 备份到 `/data/backups/pg/`，保留 30 天 |
| 报警 | 阿里云云监控 (免费) | CPU > 80% / 磁盘 > 85% / 带宽满负荷 |
| 证书到期 | Certbot 自动续期 + 邮件通知 | 到期前 30 天提醒 |

**备份脚本**（crontab 每日 3:00 执行）：

```bash
#!/bin/bash
# /opt/scripts/backup.sh
BACKUP_DIR=/data/backups/pg
RETENTION_DAYS=30
mkdir -p $BACKUP_DIR
docker compose exec -T db pg_dump -U ms_user meta_skill | gzip > $BACKUP_DIR/meta_skill_$(date +%Y%m%d).sql.gz
find $BACKUP_DIR -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete
```

### 7.11 成本估算（月）

| 项目 | 月费用 | 说明 |
|------|--------|------|
| ECS 8vCPU 16GB | ~¥400-600 | 现有实例（按量/包年） |
| 100GB ESSD 数据盘 | ~¥70 | 建议新增 |
| 3 Mbps 固定带宽 | ~¥70 | 现有 |
| 阿里云 CDN (可选) | ~¥30-100 | 按流量，初期可省 |
| DeepSeek API | ~¥50-200 | 按调用量，初期量小 |
| SSL 证书 | ¥0 | Let's Encrypt 免费 |
| **合计** | **~¥620-1040/月** | — |

---

## 八、目录结构

```
/opt/meta-skill/                        # 部署根目录
├── docker-compose.yml
├── .env                                # 环境变量（SECRET_KEY, DB_PASSWORD 等）
├── frontend/
│   ├── studio/                         # /studio/ 概念地图生成器 (现有)
│   ├── rules/                          # /studio/rules/ 规则引擎 (meta-skill-studio.html)
│   └── community/                      # /studio/community/ 社区
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                         # FastAPI 入口
│   ├── config.py                       # 配置（从环境变量读取）
│   ├── models/                         # SQLAlchemy 模型
│   ├── routers/                        # API 路由
│   │   ├── auth.py
│   │   ├── rules.py
│   │   ├── ai.py
│   │   ├── community.py
│   │   └── studio.py
│   ├── services/                       # 业务逻辑
│   │   ├── rule_engine.py              # 规则合并引擎
│   │   ├── dsl_executor.py             # DSL 执行器 (复用 wuxing_dsl.py)
│   │   ├── ai_service.py               # AI 助手服务
│   │   ├── auth_service.py             # 认证服务
│   │   └── community_service.py        # 社区服务
│   ├── middleware/                     # 中间件
│   │   ├── auth.py                     # JWT 鉴权
│   │   └── rate_limit.py               # 限流
│   └── migrations/                     # 数据库迁移 (Alembic)
├── deploy/
│   ├── nginx/
│   │   ├── nginx.conf
│   │   └── conf.d/
│   │       └── meta-skill.conf
│   ├── postgres/
│   │   └── init.sql
│   └── certbot/
│       ├── www/
│       └── conf/
└── data/ (→ 数据盘 /data)
    ├── postgres/                       # PostgreSQL 数据卷
    ├── redis/                          # Redis 持久化
    ├── backups/                        # 数据库备份
    └── rule_libraries/                 # 规则库 JSON 文件备份
```

---

## 九、分阶段实施路线

### Phase 1：基础后端 + 认证（2-3 周）
- FastAPI 项目搭建
- 用户注册/登录/角色管理
- 规则库 CRUD API
- 前端 `/studio/rules/` 接入后端 API（替换内嵌数据）

### Phase 2：AI 助手云端化（2 周）
- AI Service 实现（LLM 代理 + 权限检查）
- 前端 NL → DSL 改为优先调用后端 API
- 审计日志

### Phase 3：工作室 + 多层规则（2-3 周）
- 工作室创建/成员管理
- AI 权限配置界面
- 规则合并引擎
- 规则库层级切换器

### Phase 4：社区 + 部署（3-4 周）
- 社区浏览/分享/Fork 页面
- 审核工作流
- 贡献者升级体系
- Nginx 反向代理 + 生产部署

---

## 十、关键技术决策总结

| 决策 | 选择 | 理由 |
|------|------|------|
| 前端框架 | 原生 JS（无框架） | 现有代码已成熟，不需要 SPA 框架的额外复杂度 |
| 后端语言 | Python | 复用 `wuxing_dsl.py`，降低维护成本 |
| NL → DSL | 本地正则 + 云端 LLM 双模式 | 离线可用 + 在线增强 |
| 规则存储 | PostgreSQL JSONB | 结构化查询 + 灵活 JSON + 版本管理 |
| 认证 | JWT | 无状态，适合前后端分离 |
| AI 模型 | DeepSeek | 中文能力强，成本可控 |
| 部署 | Nginx + FastAPI + PostgreSQL + Redis | 经典稳健架构 |