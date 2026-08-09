# 验证任务修订：CASE-LIU 增量审计断言修正（REV1.1）

> **任务ID**: TASK-HOMO-LIU-20260808-REV1
> **修订日期**: 2026-08-08
> **修订依据**: 确认结果——引擎输出与任务书 §二 预期一致，§四 断言过严（内部不一致）
> **REV1.1 修正**: `'破坏' not in j` 会误判"增量不破坏保持"（"不破坏"含"破坏"子串）——修正为先 `replace("不破坏","")` 排除合法子串再检查，语义等价，仅拦截"增量破坏保持"等真异常
> **修订范围**: `test_homo_liu.py` 断言 + 验收标准 + 新增一致性检查

---

## 一、修订背景（问题定性）

```
任务书 §二 输入预期（increment_audit_expected）：
  共情/倾听     → "增量不破坏保持"
  身体觉察/内观 → "增量，链式映射贡献"
  关系建立      → "增量，关系核体现"

任务书 §四 断言（test_increment_audit）：
  all(i['judgement'] == '增量不破坏保持')   ← 与 §二 自相矛盾

引擎实际输出：与 §二 完全一致（三种判定）
```

**定性：引擎无错，§四 断言写窄了——断言需与 §二 对齐，并增加一致性检查。**

---

## 二、修订项 1：断言修改（前缀 + 排除复合判定）

```python
def test_increment_audit(result):
    """增量审计：3 项，全部为'增量'且不破坏保持（REV1.1：先排除'不破坏'再检查'破坏'）"""
    inc = result['increment_audit']
    assert len(inc) == 3, f"增量项应为 3，实际 {len(inc)}"
    for i in inc:
        j = i['judgement']
        # ① 必须以"增量"开头（是增量，不是损耗/破坏）
        assert j.startswith('增量'), f"判定应以'增量'开头: {j}"
        # ② 先排除"不破坏"（合法子类，含'破坏'子串），再检查残留'破坏'
        #    仅拦截"增量破坏保持"等真异常——REV1.1 修正（原 '破坏' not in j 会误判"增量不破坏保持"）
        residual = j.replace('不破坏', '')
        assert '破坏' not in residual, f"增量不得破坏保持: {j}"
```

**判定规则**：

| 条件 | 说明 | 拦截 |
|------|------|------|
| `j.startswith('增量')` | 必须是增量（非损耗/非破坏） | 拦截"损耗""破坏"类误判 |
| `'破坏' not in j.replace('不破坏','')` | 排除合法"不破坏"子串后检查残留"破坏"（REV1.1） | 仅拦截"增量破坏保持"等真异常（不会误判"增量不破坏保持"） |

**允许通过**：`增量不破坏保持` / `增量，链式映射贡献` / `增量，关系核体现`——三种判定粒度全部保留。

---

## 三、修订项 2：新增一致性检查断言

```python
def test_increment_audit_matches_task_spec(result, task_spec):
    """引擎增量输出与任务书 §二 输入预期逐项一致"""
    engine_items = {i['item']: i['judgement'] for i in result['increment_audit']}
    spec_items = {i['item']: i['judgement'] for i in task_spec['increment_audit_expected']}
    assert set(engine_items.keys()) == set(spec_items.keys()), "增量项清单不一致"
    for item in spec_items:
        assert engine_items[item] == spec_items[item], \
            f"{item} 判定不一致: 引擎={engine_items[item]}, 预期={spec_items[item]}"
```

**意义**：锁定"引擎忠实执行任务书预期"——未来引擎判定若变化，要么任务书预期同步更新（改两处），要么引擎回归（测试拦截）。

---

## 四、修订项 3：验收标准微调

| # | 验收项 | 原标准 | 新标准 |
|---|--------|--------|--------|
| 1 | 映射保持度 | 平均 0.85（±0.05），单条 ≥0.7 | 不变 |
| 2 | 链式复合 | ≈0.73~0.90 | 不变 |
| 3 | 增量审计 | 3 项，全部"增量不破坏保持" | **3 项，全部以"增量"开头且不含"破坏"；且与任务书 §二 预期逐项一致** |
| 4 | 场景验证 | 4/4 PASS | 不变 |
| 5 | 壳核审计 | 三层判定正确 + H1 挂载 | 不变 |
| 6 | 自动化测试 | pytest 6/6 | **pytest 7/7（原 6 项 + 新增一致性检查）** |

---

## 五、修订后的完整测试文件（test_homo_liu_rev1.py——可直接运行）

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CASE-LIU 柳智宇同态映射验证 · 修订版测试（REV1.1）
运行: python -m pytest test_homo_liu_rev1.py -v
预期: 7/7 通过
"""
import json


def load_task(path='task_liu_input.json'):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def test_mapping_retention(result):
    """候选映射保持度在预期范围内（±0.08）"""
    for m in result['mappings']:
        exp = m['expected_retention']
        assert abs(m['retention'] - exp) <= 0.08, \
            f"{m['id']}: retention={m['retention']} vs expected={exp}"
        assert m['confidence'] == 'high', f"{m['id']} 信度应为 high"


def test_average_retention(result):
    """平均保持度 ≈0.85（±0.05）"""
    avg = result['average_retention']
    assert 0.80 <= avg <= 0.90, f"平均保持度 {avg} 不在 [0.80, 0.90]"


def test_chain_retention(result):
    """链式复合 ≈ 分段之积（±0.10，含桥梁增益）"""
    chain = result['chain_retention']
    product = 0.88 * 0.83  # ≈0.73
    assert product - 0.10 <= chain <= 0.90, \
        f"链式复合 {chain} 超出 [0.63, 0.90]"


def test_increment_audit(result):
    """增量审计：3 项，全部为'增量'且不破坏保持（REV1.1：先排除'不破坏'再检查'破坏'）"""
    inc = result['increment_audit']
    assert len(inc) == 3, f"增量项应为 3，实际 {len(inc)}"
    for i in inc:
        j = i['judgement']
        assert j.startswith('增量'), f"判定应以'增量'开头: {j}"
        residual = j.replace('不破坏', '')  # REV1.1：排除合法子串，避免误判"增量不破坏保持"
        assert '破坏' not in residual, f"增量不得破坏保持: {j}"


def test_increment_audit_matches_task_spec(result, task_spec):
    """REV1 新增：引擎增量输出与任务书 §二 输入预期逐项一致"""
    engine_items = {i['item']: i['judgement'] for i in result['increment_audit']}
    spec_items = {i['item']: i['judgement'] for i in task_spec['increment_audit_expected']}
    assert set(engine_items.keys()) == set(spec_items.keys()), "增量项清单不一致"
    for item in spec_items:
        assert engine_items[item] == spec_items[item], \
            f"{item} 判定不一致: 引擎={engine_items[item]}, 预期={spec_items[item]}"


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


# ===== 主入口（非 pytest 运行时直接执行） =====
if __name__ == '__main__':
    result = json.load(open('result_liu.json', encoding='utf-8'))
    spec = load_task()

    # 组装各模式结果（按实际引擎输出结构调整）
    r = {
        'mappings': result['modes']['homo_verify']['mappings'],
        'average_retention': result['modes']['homo_verify']['average_retention'],
        'increment_audit': result['modes']['homo_verify']['increment_audit'],
        'scenarios': result['modes']['homo_verify']['scenarios'],
        'chain_retention': result['modes']['chain_verify']['composite'],
        'shell_nucleus': {
            'topic_shell': result['modes']['shell_nucleus_audit']['three_layers']['topic_shell'],
            'method_nucleus': result['modes']['shell_nucleus_audit']['three_layers']['method_nucleus'],
            'direction_nucleus': result['modes']['shell_nucleus_audit']['three_layers']['direction_nucleus'],
        },
    }

    tests = [
        ('mapping_retention', lambda: test_mapping_retention(r)),
        ('average_retention', lambda: test_average_retention(r)),
        ('chain_retention', lambda: test_chain_retention(r)),
        ('increment_audit', lambda: test_increment_audit(r)),
        ('increment_audit_matches_task_spec', lambda: test_increment_audit_matches_task_spec(r, spec)),
        ('scenarios_all_pass', lambda: test_scenarios_all_pass(r)),
        ('shell_nucleus', lambda: test_shell_nucleus(r)),
    ]

    passed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"[PASS] {name}")
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {name}: {e}")
    print(f"\n结果: {passed}/{len(tests)} 通过")
    exit(0 if passed == len(tests) else 1)
```

---

## 六、执行命令（PowerShell）

```powershell
# 1. 确认输入数据与引擎结果就位
Test-Path task_liu_input.json
Test-Path result_liu.json

# 2. 运行修订版测试（pytest 模式）
python -m pytest test_homo_liu_rev1.py -v

# 3. 或直接运行（非 pytest 环境）
python test_homo_liu_rev1.py
```

**预期结果**: 7/7 通过（6 项原断言 + 1 项新增一致性检查）

---

## 七、验收确认

| # | 验收项 | 标准 | 预期 |
|---|--------|------|------|
| 1 | 映射保持度 | 平均 0.858（±0.05），单条 ±0.08 | PASS |
| 2 | 链式复合 | 0.8034（[0.63, 0.90]） | PASS |
| 3 | 增量审计（REV1） | 3 项"增量"开头 + 与 §二 逐项一致 | PASS |
| 4 | 场景验证 | 4/4 | PASS |
| 5 | 壳核审计 | 三层 + H1 | PASS |
| 6 | 自动化测试 | **7/7** | PASS |

**全部通过 → CASE-LIU 修订版验证完成，归档**（验证任务书 V1 + REV1 修订 + 引擎结果 result_liu.json + 本修订任务书）。

---

*CASE-LIU 验证任务修订书 REV1.1 · 2026-08-08*
