# 验证任务：CASE-LIU 柳智宇同态映射验证

> **任务ID**: TASK-HOMO-LIU-20260808
> **提交日期**: 2026-08-08
> **执行引擎**: `homomorphism_engine.py`（同态映射）+ `seed_cultivation.py`（壳核审计/纯粹度）
> **协议版本**: V1.5（同态映射三步协议 + Step 2.5 增量审计 + 壳核审计）
> **验证对象**: 柳智宇跨界轨迹（数学→佛学→心理学）——链式同态映射

---

## 一、任务概述

### 1.1 验证目标

用同态映射三步协议验证柳智宇"数学→佛学→心理"跨界轨迹：
1. 数学方法种子（逻辑思辨）在心理咨询中的映射保持度
2. 链式映射（数学→佛学→心理）的复合保持度
3. 增量审计（心理域新增运算）
4. 壳核审计（题目壳/方法核/方向核三层）

### 1.2 前置条件

- `homomorphism_engine.py` 支持：结构提取、同态匹配、迁移验证、增量审计
- `seed_cultivation.py` 支持：壳核审计声明、纯粹度计算
- 数据文件：`task_liu_input.json`（本任务 §二 输入数据）

### 1.3 预期结论（对照基准）

| 验证项 | 预期值 | 依据 |
|--------|--------|------|
| 映射平均保持度 | 0.85 | 柳智宇自述"数学逻辑→剖析情绪底层结构" |
| 映射1 保持度（数学→佛学） | 0.88 | 因明学/唯识学与数学逻辑结构同构 |
| 映射2 保持度（佛学→心理） | 0.83 | 唯识底座→心理学 |
| 链式复合 | ≈0.73~0.85 | 复合=分段之积（含桥梁增益） |
| 增量审计 | 3 项不破坏保持 | 共情/内观/关系 |
| 场景验证 | 4/4 通过 | 焦虑剖析/模式识别/干预验证/概念澄清 |
| 壳核审计 | 数学=壳可换 / 逻辑=核可迁 / 追问=方向核保持 | 三层核结构 |

---

## 二、输入数据（task_liu_input.json）

```json
{
  "task_id": "TASK-HOMO-LIU-20260808",
  "protocol_version": "V1.5",
  "source_domain": {
    "name": "数学训练（方法种子=逻辑思辨）",
    "nodes": [
      {"id": "s1", "name": "公理化", "wuxing": "金"},
      {"id": "s2", "name": "逻辑推演", "wuxing": "金"},
      {"id": "s3", "name": "抽象化", "wuxing": "金"},
      {"id": "s4", "name": "精确性", "wuxing": "金"},
      {"id": "s5", "name": "证明", "wuxing": "金"}
    ],
    "edges": [
      {"from": "s1", "to": "s2", "relation": "推演", "confidence": 0.9},
      {"from": "s1", "to": "s3", "relation": "派生", "confidence": 0.85},
      {"from": "s2", "to": "s5", "relation": "前提_结论", "confidence": 0.9},
      {"from": "s3", "to": "s4", "relation": "提炼", "confidence": 0.85},
      {"from": "s5", "to": "s4", "relation": "检验", "confidence": 0.8}
    ]
  },
  "target_domain": {
    "name": "心理咨询",
    "nodes": [
      {"id": "t1", "name": "认知模型框架", "wuxing": "水"},
      {"id": "t2", "name": "情绪因果链", "wuxing": "水"},
      {"id": "t3", "name": "情绪模式识别", "wuxing": "水"},
      {"id": "t4", "name": "干预效果评估", "wuxing": "水"}
    ]
  },
  "candidate_mappings": [
    {"id": "m1", "source": "s1", "target": "t1", "relation_kept": "公理化→框架", "expected_retention": 0.85},
    {"id": "m2", "source": "s2", "target": "t2", "relation_kept": "推演→因果链", "expected_retention": 0.90},
    {"id": "m3", "source": "s3", "target": "t3", "relation_kept": "抽象→模式识别", "expected_retention": 0.82},
    {"id": "m4", "source": "s4", "target": "t2", "relation_kept": "精确→概念澄清", "expected_retention": 0.88},
    {"id": "m5", "source": "s5", "target": "t4", "relation_kept": "证明→干预评估", "expected_retention": 0.80}
  ],
  "chain_mappings": [
    {
      "id": "chain1",
      "from": "数学",
      "via": "佛学（因明/唯识）",
      "to": "心理学",
      "segments": [
        {"from": "数学", "to": "佛学", "expected_retention": 0.88, "bridge": "因明学/唯识学（与数学逻辑结构同构）"},
        {"from": "佛学", "to": "心理", "expected_retention": 0.83, "bridge": "唯识底座（八识/种子现行）"}
      ]
    }
  ],
  "verification_scenarios": [
    {"id": "vs1", "name": "焦虑剖析", "mapping_id": "m2", "check": "用逻辑拆解焦虑认知链条（前提→结论保持）", "expected": "PASS"},
    {"id": "vs2", "name": "模式识别", "mapping_id": "m3", "check": "剥离具体找情绪模式（抽象保持）", "expected": "PASS"},
    {"id": "vs3", "name": "干预验证", "mapping_id": "m5", "check": "方案效果假设检验（证明保持）", "expected": "PASS"},
    {"id": "vs4", "name": "概念澄清", "mapping_id": "m4", "check": "模糊情绪精确化（定义保持）", "expected": "PASS"}
  ],
  "increment_audit_expected": [
    {"item": "共情/倾听", "source_counterpart": "无", "judgement": "增量不破坏保持"},
    {"item": "身体觉察/内观", "source_counterpart": "无（来自佛学中间域）", "judgement": "增量，链式映射贡献"},
    {"item": "关系建立", "source_counterpart": "无", "judgement": "增量，关系核体现"}
  ],
  "shell_nucleus_input": {
    "declaration": {
      "measured_nucleus": ["方法核（逻辑思辨）", "方向核（向内追问）"],
      "excluded_shell": ["数学专业", "IMO 满分", "MIT offer", "出家身份"],
      "system_type": "测核体系"
    },
    "three_layers": {
      "topic_shell": {"name": "数学研究", "action": "可更换", "evidence": "2010 放弃 MIT offer"},
      "method_nucleus": {"name": "逻辑思辨", "action": "可迁移", "evidence": "数学→佛学→心理全程保持"},
      "direction_nucleus": {"name": "向内追问", "action": "必须保持", "evidence": "耕读社→出家→心理 20 年", "hypothesis": "H1（待验证）"}
    }
  },
  "wuxing_annotation": {
    "source": "金（逻辑思辨）",
    "target": "水（共情/心理）",
    "relation": "金生水——理性的极致是通往共情的路"
  }
}
```

---

## 三、执行步骤（引擎调用）

### 3.1 同态映射验证

```powershell
# PowerShell（Windows 环境）
python homomorphism_engine.py --task task_liu_input.json --mode homo_verify
```

**引擎应执行**：
1. Step 1 结构提取：读取 source_domain 节点/边 → 运算关系图
2. Step 2 同态匹配：对 candidate_mappings 逐条计算保持度 → 输出映射表 + 平均保持度
3. Step 2.5 增量审计：比对 target 域与 source 域 → 输出增量项
4. Step 3 迁移验证：对 verification_scenarios 逐场景检验 → 输出 PASS/FAIL

### 3.2 链式映射验证

```powershell
python homomorphism_engine.py --task task_liu_input.json --mode chain_verify
```

**引擎应执行**：
1. 对 chain_mappings.segments 逐段计算保持度
2. 复合保持度 = 分段之积（含桥梁增益判定）
3. 输出：链式复合值 + 与直接映射对比

### 3.3 壳核审计验证

```powershell
python seed_cultivation.py --task task_liu_input.json --mode shell_nucleus_audit
```

**引擎应执行**：
1. 壳核声明（measured_nucleus / excluded_shell / system_type）
2. 三层核结构判定（topic_shell 可换 / method_nucleus 可迁 / direction_nucleus 保持）
3. 方向核挂 H1 假设（幸存者偏差标注）

---

## 四、预期输出与断言（自动化测试用例）

### 4.1 同态映射断言（test_homo_liu.py）

```python
import json, sys

def load_task():
    with open('task_liu_input.json', encoding='utf-8') as f:
        return json.load(f)

def test_mapping_retention(result):
    """候选映射保持度在预期范围内"""
    for m in result['mappings']:
        exp = m['expected_retention']
        assert abs(m['retention'] - exp) <= 0.08, f"{m['id']}: {m['retention']} vs {exp}"
        assert m['confidence'] == 'high', f"{m['id']} 信度应为 high"

def test_average_retention(result):
    """平均保持度 ≈0.85（±0.05）"""
    avg = result['average_retention']
    assert 0.80 <= avg <= 0.90, f"平均保持度 {avg} 不在 [0.80, 0.90]"

def test_chain_retention(result):
    """链式复合 ≈ 分段之积（±0.10，含桥梁增益）"""
    chain = result['chain_retention']
    seg1, seg2 = 0.88, 0.83
    product = seg1 * seg2  # ≈0.73
    assert product - 0.10 <= chain <= 0.90, f"链式复合 {chain} 超出 [0.63, 0.90]"

def test_increment_audit(result):
    """增量审计：3 项，全部'不破坏保持'"""
    inc = result['increment_audit']
    assert len(inc) == 3, f"增量项应为 3，实际 {len(inc)}"
    assert all(i['judgement'] == '增量不破坏保持' for i in inc), "增量不得破坏保持"

def test_scenarios_all_pass(result):
    """迁移验证：4/4 PASS"""
    scenarios = result['scenarios']
    assert len(scenarios) == 4, f"场景应为 4，实际 {len(scenarios)}"
    assert all(s['result'] == 'PASS' for s in scenarios), "应全部 PASS"

def test_shell_nucleus(result):
    """壳核审计：数学=壳（可换）、逻辑=核（可迁）、追问=方向核（保持）"""
    sn = result['shell_nucleus']
    assert sn['topic_shell']['action'] == '可更换'
    assert sn['method_nucleus']['action'] == '可迁移'
    assert sn['direction_nucleus']['action'] == '必须保持'
    assert sn['direction_nucleus']['hypothesis'] == 'H1', "方向核应挂 H1 假设"
```

### 4.2 全部测试执行

```powershell
python -m pytest test_homo_liu.py -v
```

**预期结果**: 6 项测试全部通过（mapping_retention / average_retention / chain_retention / increment_audit / scenarios_all_pass / shell_nucleus）

---

## 五、验收标准

| # | 验收项 | 标准 | 判定 |
|---|--------|------|------|
| 1 | 映射保持度 | 平均 0.85（±0.05），单条 ≥0.7 | 通过/未通过 |
| 2 | 链式复合 | ≈0.73~0.90（分段之积±桥梁增益） | 通过/未通过 |
| 3 | 增量审计 | 3 项，全部"不破坏保持" | 通过/未通过 |
| 4 | 场景验证 | 4/4 PASS | 通过/未通过 |
| 5 | 壳核审计 | 三层判定正确 + H1 挂载 | 通过/未通过 |
| 6 | 自动化测试 | pytest 6/6 通过 | 通过/未通过 |

**全部通过 → CASE-LIU 验证完成**：柳智宇跨界轨迹 = 链式同态映射成立（平均保持度 0.85），壳核三层结构确认（数学=壳可换/逻辑=核可迁/追问=方向核保持），可作为 Phase 3 第一个正式跨域映射案例归档。

---

## 六、注意事项（诚实声明）

1. **保持度预期值为专家评估**（基于柳智宇自述与因明/唯识结构同构判断）——引擎计算值在 ±0.08 容差内即通过
2. **链式复合含桥梁增益假设**——唯识中间域可能贡献增量（非纯损耗），复合值允许高于分段之积
3. **方向核 H1 为待验证假设**（幸存者偏差）——本任务仅挂载，不判定
4. 运行环境为 Windows PowerShell（用户环境）——命令已按 PowerShell 语法书写

---

*验证任务书由种·育 V1.5 生成 · 2026-08-08*
