# hui-skill.cn 带宽监控方案 & 实际流量分析

> 服务器: 21.41.215.36 | 计费模式: 按使用流量计费 | 峰值带宽: 50 Mbps

---

## 1. 页面体积估算

### 1.1 服务器侧资产

| 资源 | 大小 | 来源 |
|------|------|------|
| `index.html`（产品矩阵首页） | ~18 KB | 服务器 |
| `annotate.html`（标注平台） | ~48 KB | 服务器 |
| `colors_and_type.css` | ~1.5 KB | 服务器 |

### 1.2 CDN 资产（不消耗服务器带宽）

| 资源 | 大小 | 来源 |
|------|------|------|
| Tailwind CSS v4.3.1 | ~100 KB | jsdelivr CDN |
| Lucide Icons v1.8.0 | ~50 KB | unpkg CDN |

**结论**: 服务器实际承担的单次页面访问流量约 **15-50 KB**。

### 1.3 月度流量理论预估

| 日访问量 (PV) | 平均页大小 | 月流量 | 占峰值带宽 |
|--------------|-----------|--------|-----------|
| 500 | 40 KB | ~0.6 GB | < 0.1% |
| 5,000 | 40 KB | ~6 GB | < 0.5% |
| 50,000 | 40 KB | ~60 GB | ~3% |
| 500,000 | 40 KB | ~600 GB | ~30% |

---

## 2. 实际流量分析（2026-07-24 ~ 2026-07-31）

数据来源：阿里云 OMS 流量监控（小时级粒度，738 条记录）。

### 2.1 核心指标

| 指标 | 数值 |
|------|------|
| 有效流量天数 | 7 天（7/24 起） |
| 7 天总流出（网站服务） | **99.19 MB** |
| 7 天总流入 | **1,162.17 MB** |
| 日均流出 | **~14 MB/天** |
| 峰值小时流出 | 6.77 MB（7/24 23:00） |
| 峰值带宽 | **15.78 kbps** |
| 带宽利用率 | **0.03%**（vs 50 Mbps 上限） |

### 2.2 日趋势

| 日期 | 流出 (MB) | 流入 (MB) | 流入/流出比 | 备注 |
|------|----------|----------|-----------|------|
| 7/24 | 8.09 | 387.50 | 47.9x | 异常流入（初始部署/系统更新） |
| 7/25 | 13.34 | 628.70 | 47.1x | 异常流入（持续） |
| 7/26 | 11.07 | 44.94 | 4.1x | 流入回落 |
| 7/27 | 16.06 | 41.46 | 2.6x | 趋于正常 |
| 7/28 | 12.87 | 16.89 | 1.3x | 正常 |
| 7/29 | 14.78 | 17.32 | 1.2x | 正常 |
| 7/30 | 12.89 | 15.20 | 1.2x | 正常 |
| 7/31 | 10.08 | 10.16 | 1.0x | 正常（截至 20:00） |

### 2.3 24 小时分布

小时级流出流量全天均匀分布，无明显用户访问高峰：

| 时间段 | 小时均值 | 特征 |
|--------|---------|------|
| 00:00-06:00 | 80-175 KB/h | 夜间无明显下降 |
| 06:00-12:00 | 85-214 KB/h | 上午略高 |
| 12:00-18:00 | 122-214 KB/h | 下午持平 |
| 18:00-23:00 | 76-323 KB/h | 23:00 有峰值 |

### 2.4 流入峰值 Top 5

| 时间 | 流入 (MB) | 流出 (KB) |
|------|----------|----------|
| 7/25 18:00 | 397.37 | 2,964 |
| 7/24 23:00 | 332.79 | 6,933 |
| 7/25 17:00 | 209.63 | 1,898 |
| 7/24 21:00 | 33.17 | 401 |
| 7/24 22:00 | 21.41 | 955 |

### 2.5 关键发现

1. **带宽远未触及上限**：15.78 kbps 峰值 vs 50 Mbps 上限，利用率仅 0.03%
2. **流入异常已消退**：7/24-25 的异常流入（47:1 流入/流出比）是初始部署或系统更新流量，7/26 起恢复正常 1:1 比例
3. **流量全天均匀分布**：每小时 80-320 KB，更接近自动化流量（爬虫、监控探针、健康检查）而非大量真实用户访问
4. **日均 ~14 MB ≈ 350 次页面访问**（按 40 KB/页估算），站点处于早期阶段

### 2.6 结论

- 50 Mbps 按流量计费 **在当前阶段完全够用**
- 即使日访问量增长 100 倍（到 35,000 PV/天），月流量也仅约 42 GB，仍在安全范围
- 需关注 7/24-25 类型的异常流入——未来大规模部署或数据传输操作建议在低峰时段进行

---

## 3. 带宽监控方案

### 3.1 vnstat（轻量级，推荐）

```bash
# 安装
apt install vnstat -y

# 初始化监控网卡（替换 eth0 为实际网卡名）
vnstat -i eth0

# 启动服务
systemctl enable vnstat
systemctl start vnstat
```

常用命令：

```bash
vnstat -d    # 按天查看
vnstat -m    # 按月查看
vnstat -h    # 按小时查看
vnstat -l    # 实时流量
vnstat -t    # 显示 Top 10 流量天
```

### 3.2 Nginx 日志分析

在 `http` 块中开启流量日志：

```nginx
log_format traffic '$remote_addr - $request_time $body_bytes_sent $status';
access_log /var/log/nginx/traffic.log traffic;
```

每日流量统计：

```bash
awk '{sum+=$3} END {printf "%.2f MB\n", sum/1024/1024}' /var/log/nginx/traffic.log
```

### 3.3 GoAccess 实时可视化面板

```bash
apt install goaccess -y

# 实时监控
goaccess /var/log/nginx/access.log \
    --log-format=COMBINED \
    --real-time-html \
    -o /var/www/html/report.html
```

访问 `http://21.41.215.36/report.html` 查看实时流量仪表盘。

### 3.4 Nginx 限流保护（防爬虫/突发）

```nginx
# 在 http 块中定义限流区域
limit_req_zone $binary_remote_addr zone=perip:10m rate=10r/s;
limit_conn_zone $binary_remote_addr zone=perconn:10m;

server {
    listen 80;
    server_name hui-skill.cn;

    root /var/www/hui-skill-product-matrix;
    index pages/index.html;

    # 应用限流
    location / {
        limit_req zone=perip burst=20 nodelay;
        limit_conn perconn 10;
        try_files $uri $uri/ =404;
    }

    # 静态资源缓存
    location /colors_and_type.css {
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    # HTML 不缓存
    location ~ \.html$ {
        add_header Cache-Control "no-cache";
    }
}
```

### 3.5 阿里云 OMS 告警配置

在阿里云控制台为 ECS 实例 `i-bp1g4am8mtl1pjxa0rbk` 配置：

- **公网流出流量告警**：当每小时流出 > 500 MB 时发送通知
- **带宽使用率告警**：当峰值带宽利用率 > 80% 时发送通知

---

## 4. 实施优先级

| 优先级 | 任务 | 说明 |
|--------|------|------|
| P0 | 安装 vnstat | 零成本获得流量基线，5 分钟完成 |
| P1 | Nginx 限流规则上线 | 防止单 IP 突发消耗，已有完整配置 |
| P2 | Tailwind + Lucide 本地化 | 下载至本地 `assets/`，消除外部 CDN 依赖 |
| P3 | GoAccess 面板 | 日常巡检，可选 |
| P3 | 阿里云 OMS 告警 | 需要时再配置 |

---

## 5. 相关配置

- Nginx 完整配置：`deploy/nginx/hui-skill.cn.conf`
- 产品矩阵前端：`frontend/product-matrix/`
- 部署脚本：`deploy/hui-skill/deploy.ps1`