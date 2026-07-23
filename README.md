# SkillUp Studio

从原始素材到可交付产出技能的完整工坊。

## 技能列表

### kb-concept-mapper — 知识库概念地图生成器

自动扫描知识库文档或单篇长文，提取核心概念并建立关联，生成可交互、可拖拽、可展开的概念地图。

- 单文件 HTML，纯 Canvas 引擎，零外部依赖
- 支持知识库模式（跨文档提取）和单文档模式
- 力导向布局 + 拖拽/缩放/hover/搜索/详情面板
- 概念分类、权重、关联关系可视化

### mobius-concept-map — 莫比乌斯环概念地图 v2.0

基于 3D 莫比乌斯环引擎，将概念数据生成为可交互的动画概念地图。

**五空动画系统（50秒四阶段循环）：**

| 空 | 名称 | 视觉效果 |
|:--:|:-----|:-------|
| 空一 | 三轮体空 | 粒子消散 → 三环融合 → "空"字 |
| 空二 | 大圆镜智 | 金色镜面光晕 + 节点倒影 |
| 空三 | 觉知域 | 画布明度呼吸 |
| 空四 | 为道日损 | 节点渐隐至透明 |
| 空五 | 色空不二 | 粒子上旋穿透三层 |

**五阶音景系统（Web Audio API 纯代码合成，432Hz 自然调谐）：**

| 音层 | 阶段 | 音效 |
|:----:|:----:|:-----|
| 呼吸层 | 全程 | 粉色噪声 4秒呼吸包络（觉知域的听觉镜像） |
| 建构层 | 0-8s | 432Hz + 864Hz 正弦波（种子破土） |
| 流转层 | 8-20s | 432/428Hz 差拍 + 白噪声溪流（水之流动） |
| 消散层 | 20-35s | 432→864Hz 滑音渐弱（粒子消散的听觉映射） |
| 渐隐层 | 35-50s | 216Hz 低频 + 偶发泛音（损之又损的最后一个念头） |

**核心特性：**

- 3D 莫比乌斯环数学建模 + 透视投影 + 画家算法
- CRUD 管理面板（新增/编辑/删除/排序/导入/导出 JSON）
- localStorage 自动持久化（按数据集隔离）
- 五行八卦属性标注（可选）
- 三种布局模式：八卦方位 / 关联词条 / 同层展示
- 移动端触屏支持
- 向后兼容：全部五空关闭 = v1.3 纯骨架模式

**动画录制：**

- 桌面端输出 MP4（H.264），移动端输出 WebM（VP9），自动降级
- 录制支持合并音频流（开启音景后录制即可获得带声音的视频）
- 自动缩放至 960×720 降低编码压力

**五阶音景交互：**

- 默认静音，遵守浏览器自动播放策略
- 三态切换：🔇静音 → 🔈呼吸+音景 → 🔊仅音景
- 音量滑块实时调节
- localStorage 记忆用户偏好

---

## 示例

`examples/` 目录包含多主题概念地图数据集和生成产物。

### 唯识论（初版）

| 文件 | 说明 |
|:-----|:-----|
| [weishi-23-nodes.json](examples/weishi-23-nodes.json) | 23 节点五行八卦概念数据（3 层 8/7/8 节点） |
| [weishi-mobius-v2.0.html](examples/weishi-mobius-v2.0.html) | v2.0 五空动画演示 |
| [weishi-mobius-v1.0.html](examples/weishi-mobius-v1.0.html) | v1.0 莫比乌斯初版（含 CRUD 管理面板） |
| [weishi-static-concept-map.html](examples/weishi-static-concept-map.html) | 静态概念地图（28 节点 6 分类） |

### 儒家心学（21节点）

| 文件 | 说明 |
|:-----|:-----|
| [儒家心学_21nodes.json](examples/儒家心学_21nodes.json) | 本原层(8) + 修证层(7) + 境界层(6) |
| [儒家心学_21v2.0.html](examples/儒家心学_21v2.0.html) | 儒红/橙/金配色五空动画演示 |

### 黄帝内经（23节点）

| 文件 | 说明 |
|:-----|:-----|
| [黄帝内经_23nodes.json](examples/黄帝内经_23nodes.json) | 阴阳层(8) + 诊治层(7) + 哲理层(8) |
| [黄帝内经_23v2.0.html](examples/黄帝内经_23v2.0.html) | 草木绿/蓝/紫配色五空动画演示 |

### 道德经（20节点）

| 文件 | 说明 |
|:-----|:-----|
| [道德经_20nodes.json](examples/道德经_20nodes.json) | 体·道(7) + 相·德(7) + 用·玄(6) |
| [道德经_20v2.0.html](examples/道德经_20v2.0.html) | 五空动画演示 |

### 五行养生（15节点）

| 文件 | 说明 |
|:-----|:-----|
| [五行养生_15nodes.json](examples/五行养生_15nodes.json) | 体·五行本质(5) + 相·五蕴对应(5) + 用·调养之道(5) |
| [五行养生_15v2.0.html](examples/五行养生_15v2.0.html) | 五空动画演示 |

### AI 概念图（21节点）

| 文件 | 说明 |
|:-----|:-----|
| [AI概念图_21nodes.json](examples/AI概念图_21nodes.json) | 基础层(7) + 架构层(7) + 前沿层(7) |
| [AI概念图_21v2.0.html](examples/AI概念图_21v2.0.html) | 科技蓝/创新绿/前沿紫配色五空动画演示 |

---

## 设计文档

`docs/` 目录包含完整的架构与设计文档。

| 文件 | 说明 |
|:-----|:-----|
| [莫比乌斯环_五空动画_设计文档_v2.0.md](docs/莫比乌斯环_五空动画_设计文档_v2.0.md) | 从创意到实现的完整设计书（14章），含五阶音景、动画录制系统 |
| [莫比乌斯环_五阶音景_独立提案_v1.0.md](docs/莫比乌斯环_五阶音景_独立提案_v1.0.md) | Web Audio API 五阶音景系统提案 |

---

## 快速开始

```bash
# 从数据集生成 HTML
python3 skills/mobius-concept-map/scripts/build_mobius.py \
  --data examples/儒家心学_21nodes.json \
  --title "我的概念地图" \
  --output output.html

# 关闭五空动画（纯骨架模式）
python3 skills/mobius-concept-map/scripts/build_mobius.py \
  --data examples/AI概念图_21nodes.json \
  --title "AI概念图" \
  --no-emptiness \
  --output output.html
```

### 数据格式

概念数据为 JSON 格式，包含三层结构，每个概念支持 `wuxing`（五行）和 `bagua`（八卦）可选属性。

详细格式参见 [examples/weishi-23-nodes.json](examples/weishi-23-nodes.json)。

## 依赖

- Python 3.x（仅生成脚本需要）
- 现代浏览器（HTML 产物零外部依赖）

## License

[MIT](LICENSE)
