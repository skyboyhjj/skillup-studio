# HuggingFace API 不可达 · 根因分析与修复报告

**日期**: 2026-08-10
**现象**: HuggingFace API 连接超时，两个月份均未采集成功（hf_collect.py 直连 huggingface.co）
**状态**: ✅ 根因定位 + 补丁验证通过

---

## 一、根因分析（实测证据）

### 1.1 症状特征

| 检测项 | 结果 |
|--------|------|
| DNS 解析 huggingface.co | ✅ 正常（0.01s → 199.59.148.15，Fastly CDN） |
| HTTPS 连接 huggingface.co/api/models | ❌ `URLError: [Errno 101] Network is unreachable`（10s 超时） |
| HTTPS 连接 huggingface.com（备选域名） | ❌ 同样不可达 |
| HTTPS 连接 **hf-mirror.com/api/models** | ✅ HTTP 200（0.38s，返回模型 JSON，API 完全兼容） |

### 1.2 根因结论

**DNS 解析正常，但 huggingface.co 解析出的 CDN IP（199.59.148.15）在当前网络环境下无法路由**——这是国内/受限网络直连 HuggingFace 的典型症状（官方域名被墙/路由黑洞）。**不是 HF 服务故障，是网络可达性问题**。

**证据链**：同一网络环境下 hf-mirror.com（国内镜像）0.38s 可达且 API 格式兼容——证明问题在"到 huggingface.co 的路由"，不在"HF API 本身"。

### 1.3 为什么"两个月份均失败"

hf_collect.py 原版**无重试、无端点切换**：`urllib.request.urlopen(timeout=30)` 连接超时抛异常 → 每个 tag 记 `weight=0, error=...` → 整月输出全零树文件。**失败是静默的**（有 error 字段但主流程继续），两个月的树文件都是"全 0 伪数据"——比失败更危险的是"假装成功"。

---

## 二、修复方案（hf_collect.py v0.2 补丁）

### 2.1 改动点（最小侵入）

| # | 改动 | 说明 |
|---|------|------|
| 1 | **端点 failover**：`HF_API_ENDPOINTS = [huggingface.co, hf-mirror.com]`，按序尝试，首个成功即用 | 官方优先，镜像兜底 |
| 2 | **环境变量覆盖**：`HF_API_BASE` 可指定自定义端点（代理网关/自建镜像） | 灵活适配部署环境 |
| 3 | **连接/读取超时拆分**：connect 10s（连接不可达快速切换）+ read 30s | 原 30s 单一超时让连接黑洞拖满 30s |
| 4 | **每端点重试**：3 次指数退避（1s/2s/4s），全部失败才切端点 | 抗网络抖动 |
| 5 | **可操作错误提示**：全部端点失败时提示 ① 检查网络 ② 设 HF_API_BASE ③ 检查 DNS | 不再静默失败 |
| 6 | **端点审计**：meta.api 记录实际成功端点 + compliance_report 带 endpoint | 数据可追溯（哪个端点采的） |

### 2.2 验证结果（本地实测）

```
端点列表: ['https://huggingface.co', 'https://hf-mirror.com']
✅ 采集成功: active_endpoint = https://hf-mirror.com（自动 failover）
   返回条数: 1000（text-generation 单页）
完整月度采集（12 tags, --max-pages 2）:
  ✅ 12/12 tags 跑通，输出 hf_tree_2026-08.json（总权重 6826）
  ✅ 14 次请求，间隔合规=True
  ✅ meta.api 记录实际端点（可审计）
```

---

## 三、生产接入指引

### 3.1 直接使用（推荐）

将更新后的 `hf_collect.py` 同步到生产（wuxing_flowengine/docs/），直接运行即可：

```powershell
python hf_collect.py --month 2026-08     # 自动 failover 到 hf-mirror.com
python hf_collect.py --month 2026-07     # 补采 7 月（之前失败的月份）
```

### 3.2 自定义端点（如有代理/网关）

```powershell
$env:HF_API_BASE="https://your-proxy.example.com"; python hf_collect.py --month 2026-08
```

### 3.3 补采策略（两个失败月份）

```
1. 先跑 --month 2026-07 → 验证树文件非全零（total_weight > 0）
2. 再跑 --month 2026-08 → 补全
3. 重新合并: merge_and_calibrate.py（或 EngineAdapterV2 管线）
4. 注意：补采后需重跑诊断——之前的"全 0 伪数据"树文件应作废/归档标记
```

### 3.4 调度器集成（Phase A 已支持）

```powershell
python pipeline_orchestrator.py --source huggingface --month 2026-07 --force
python pipeline_orchestrator.py --source huggingface --month 2026-08 --force
```

---

## 四、教训沉淀

1. **采集器必须"失败显式化"**：原版失败记 `weight=0` 继续跑——产出的"全 0 树"是伪数据。补丁后：全部端点失败 → 抛 ConnectionError + 可操作提示；单 tag 失败 → error 字段 + 计数可区分
2. **外部 API 需端点 failover**：HF 直连不可达是网络常态（国内环境），镜像/备用端点应是标配（OpenAlex/S2 同理可加）
3. **"连接超时"≠"服务故障"**：先查网络可达性（DNS → 连接 → 镜像），再怀疑 API 本身——本次 10 分钟定位

---

## 五、结论

> **根因：huggingface.co 官方域名在当前网络不可路由（DNS 正常、连接 Network is unreachable），非 HF 服务故障；hf-mirror.com 镜像 API 实测完全兼容（0.38s）。修复：hf_collect.py v0.2 增加端点 failover（官方→镜像）+ 环境变量覆盖 + 超时拆分 + 重试 + 可操作错误提示 + 端点审计，本地验证 12/12 tags 跑通。两个失败月份按指引补采即可——补采后重跑诊断，作废旧的全 0 树文件。**

*修改文件: hf_collect.py（v0.1 → v0.2）*
*验证: python hf_collect.py --month 2026-08 --max-pages 2（12 tags 全通）*
