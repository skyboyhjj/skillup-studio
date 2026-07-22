---
name: mobius-concept-map
description: |
  基于3D莫比乌斯环引擎，将概念数据生成为可交互的动画概念地图（HTML单文件）。
  v2.0：五空动画系统（三轮体空·大圆镜智·觉知域·为道日损·色空不二）。
  支持三种布局模式：八卦方位布局、关联词条布局、同层展示。
  当用户说「用莫比乌斯环展示这些概念」「生成3D概念地图」「把这些概念做成旋转动画」
  「用八卦方位排列这些概念」「展示同一层的概念」时触发。
  不适用于：静态概念地图（用kb-concept-mapper）、仅文本输出不生成图谱。
---

# 莫比乌斯环概念地图生成器 v2.0

## 功能定位

将一组概念数据（支持三层结构 + 五行八卦属性）注入3D莫比乌斯环引擎，生成**可拖拽旋转、可点击查看、带五空动画**的交互式概念地图HTML。

### v2.0 新增：五空动画系统

| 空 | 名称 | 视觉通道 | 阶段 |
|:--:|:-----|:-------|:----:|
| 空一 | 三轮体空·粒子消散 | 粒子系统 | 三轮体空 |
| 空二 | 大圆镜智·背景镜面 | Canvas 背景层 | 全程 |
| 空三 | 觉知域·画布呼吸 | Canvas 明度 | 全程 |
| 空四 | 为道日损·节点渐隐 | 节点透明度 | 为道日损 |
| 空五 | 色空不二·粒子上旋 | 粒子方向 | 三轮体空 |

动画周期：50秒四阶段（建构0-8s → 流转8-20s → 三轮体空20-35s → 为道日损35-50s）。

### 三种布局模式

- **八卦方位布局**：节点按八卦方位分布在环上
- **关联词条布局**：根据概念间的关联关系就近排列
- **同层展示**：三层各自独立展示

---

## 触发条件

- "用莫比乌斯环展示这些概念"
- "把这些做成3D旋转的概念地图"
- "用八卦方位排列"
- "按关联关系重新布局"
- "只展示同一层的概念"
- "生成莫比乌斯环概念地图"

---

## 工作流

### Step 1：确认数据

1. **概念数据**——用户提供或AI从知识库提取。每一层包含：
   ```json
   {
     "label": "层名称", "R": 200, "w": 30, "yOffset": 120, "color": "#4ECDC4",
     "concepts": [
       { "label": "概念名", "desc": "描述", "docs": ["来源1"], "wuxing": "金", "bagua": "☰乾" }
     ]
   }
   ```
   `wuxing` 和 `bagua` 为可选字段。

2. **五空配置**（可选，默认全部开启）：
   ```json
   {
     "emptiness": {
       "sunyata": true, "mirror": true, "breath": true, "wane": true, "ascend": true,
       "mirrorRadius": 120, "breathPeriod": 10000, "fadeTarget": 0.15, "ascendRatio": 0.2
     }
   }
   ```

3. **布局模式**——`bagua` / `relation` / `layer`

4. **标题**

### Step 2：生成HTML

```bash
python3 scripts/build_mobius.py \
  --data concepts.json \
  --title "概念地图标题" \
  --output 概念地图_输出.html

# 关闭全部五空动画
python3 scripts/build_mobius.py --data concepts.json --no-emptiness --output output.html

# 自定义五空
python3 scripts/build_mobius.py --data concepts.json --emptiness '{"wane":false}' --output output.html
```

### Step 3：验证

```bash
# JS语法验证
node -e "const m=require('fs').readFileSync('输出.html','utf8').match(/<script>([\s\S]*?)<\/script>/);new Function(m[1]);console.log('✅')"
```

### Step 4：交付

提供HTML下载。告知用户交互方式：拖拽旋转、悬停查看、点击详情、管理面板CRUD。

---

## 数据配置格式

```json
{
  "rings": [
    {
      "label": "种子层", "R": 200, "w": 30, "yOffset": 120, "color": "#4ECDC4",
      "concepts": [
        { "label": "阿赖耶识", "desc": "第八识，含藏一切种子", "docs": ["唯识三十颂"], "wuxing": "土", "bagua": "☷坤" }
      ]
    }
  ],
  "emptiness": {
    "sunyata": true,
    "mirror": true,
    "breath": true,
    "wane": true,
    "ascend": true,
    "mirrorRadius": 120,
    "breathPeriod": 10000,
    "fadeTarget": 0.15,
    "ascendRatio": 0.2
  }
}
```

全部 `false` = v1.3 行为（仅原始三轮体空）。

---

## 五空动画详细规格

### 空一：三轮体空 · 粒子消散
- **阶段**：第三阶段（20-35秒）
- **效果**：粒子减速 → 汇聚为三金环 → 融合为一点 → 消散 → "空"字
- **参数**：`sunyata: true/false`

### 空二：大圆镜智 · 背景镜面
- **阶段**：全程
- **效果**：中心金色半透明圆盘 + 节点倒影（透明度8%）
- **参数**：`mirror: true/false`, `mirrorRadius: 120`

### 空三：觉知域 · 画布呼吸
- **阶段**：全程
- **效果**：背景色10秒周期±2 RGB微幅呼吸
- **参数**：`breath: true/false`, `breathPeriod: 10000`

### 空四：为道日损 · 节点渐隐
- **阶段**：第四阶段（35-50秒）
- **效果**：节点透明度线性降至15%，标语"损之又损以至于无为"。拖拽时恢复50%。
- **参数**：`wane: true/false`, `fadeTarget: 0.15`, `fadeRestore: 0.5`

### 空五：色空不二 · 粒子上旋穿透
- **阶段**：第三阶段（30-35秒）
- **效果**：20%粒子从种子层竖直穿透三层至消失，颜色渐变：青→红→金→白
- **参数**：`ascend: true/false`, `ascendRatio: 0.2`

---

## 向后兼容

| 场景 | 行为 |
|:-----|:-----|
| JSON 无 `emptiness` 字段 | 全部五个空默认**开启** |
| JSON 有 `emptiness: {}` | 按字段逐项覆盖 |
| JSON 有 `"emptiness": {"sunyata": false}` | 仅关闭三轮体空 |
| `--no-emptiness` 参数 | 全部关闭（纯骨架模式） |
| v1.3 生成的概念地图 | 不受影响 |

---

## 模板引擎特性

- **3D渲染**：莫比乌斯环数学建模 + 透视投影 + 画家算法
- **粒子系统**：种子层↔现行层双向流动 + 上旋穿透
- **五空动画**：50秒四阶段自动循环
- **交互**：鼠标/触摸拖拽旋转、悬停Tooltip、点击详情面板
- **管理面板**：CRUD操作（新增/编辑/删除/排序/导入/导出JSON）
- **localStorage**：自动持久化用户修改
- **五行八卦**：可选光晕 + Tooltip显示

---

## 注意事项

1. 概念数量建议5-30个节点
2. `wuxing` 取值：`木`/`火`/`土`/`金`/`水`
3. `bagua` 取值：`☰乾`/`☱兑`/`☲离`/`☳震`/`☴巽`/`☵坎`/`☶艮`/`☷坤`
4. 交付后提醒用户：拖拽旋转、悬停查看五行八卦、点击看详情、右上角管理概念、导出JSON备份
