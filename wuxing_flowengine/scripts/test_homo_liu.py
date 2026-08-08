"""
CASE-LIU 柳智宇同态映射验证 — 自动化测试（7 项断言，REV1）
===========================================================
基于《验证任务_CASE-LIU柳智宇同态映射.md》§四 + REV1 修订。
REV1: 增量审计断言修正——允许子类标签（链式映射贡献/关系核体现），
      新增引擎输出与任务书 §二 逐项一致性检查。

运行:
    python -m pytest test_homo_liu.py -v
    # 或直接运行
    python test_homo_liu.py
"""

import json
import os
import sys

# 确保脚本目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from homomorphism_engine import HomomorphismEngine
from seed_cultivation import SeedCultivation


def load_task():
    """加载 task_liu_input.json"""
    task_path = os.path.join(os.path.dirname(__file__), "..", "data", "task_liu_input.json")
    with open(task_path, encoding="utf-8") as f:
        return json.load(f)


def load_result(mode: str) -> dict:
    """加载已生成的结果 JSON"""
    result_path = os.path.join(os.path.dirname(__file__), "..", "output", "reports",
                               f"result_liu_{mode}.json")
    with open(result_path, encoding="utf-8") as f:
        return json.load(f)


def run_and_get_result():
    """运行 homo_verify + chain_verify + shell_nucleus_audit，返回结果字典"""
    task_data = load_task()
    engine = HomomorphismEngine()

    homo_result = engine.transfer_from_graph(
        task_data["source_domain"],
        task_data["target_domain"],
        task_data["candidate_mappings"],
        task_data.get("verification_scenarios", []),
    )
    homo_result["shell_nucleus_input"] = task_data.get("shell_nucleus_input", {})

    chain = task_data["chain_mappings"][0]
    chain_result = engine.transfer_chain(chain["segments"])

    cultivator = SeedCultivation(time_scale="skill")
    sn_result = cultivator.shell_nucleus_audit(task_data.get("shell_nucleus_input", {}))

    return homo_result, chain_result, sn_result


# ── 测试 1: 候选映射保持度在预期范围内 ──

def test_mapping_retention():
    """每条映射保持度在 expected_retention ±0.08 内"""
    task_data = load_task()
    engine = HomomorphismEngine()
    result = engine.transfer_from_graph(
        task_data["source_domain"],
        task_data["target_domain"],
        task_data["candidate_mappings"],
    )

    for m in result["mappings"]:
        exp = m["expected_retention"]
        dev = abs(m["retention"] - exp)
        assert dev <= 0.08, f"{m['id']}: retention={m['retention']} vs expected={exp} (dev={dev:.4f})"
        assert m["confidence"] == "high", f"{m['id']} 信度应为 high，实际 {m['confidence']}"


# ── 测试 2: 平均保持度 ≈0.85（±0.05）──

def test_average_retention():
    """平均保持度在 [0.80, 0.90]"""
    task_data = load_task()
    engine = HomomorphismEngine()
    result = engine.transfer_from_graph(
        task_data["source_domain"],
        task_data["target_domain"],
        task_data["candidate_mappings"],
    )

    avg = result["average_retention"]
    assert 0.80 <= avg <= 0.90, f"平均保持度 {avg} 不在 [0.80, 0.90]"


# ── 测试 3: 链式复合 ≈ 分段之积（±0.10，含桥梁增益）──

def test_chain_retention():
    """链式复合在 [0.63, 0.90]"""
    task_data = load_task()
    chain = task_data["chain_mappings"][0]
    engine = HomomorphismEngine()
    result = engine.transfer_chain(chain["segments"])

    chain_ret = result["composite"]
    seg1, seg2 = 0.88, 0.83
    product = seg1 * seg2  # ≈0.73
    assert product - 0.10 <= chain_ret <= 0.90, \
        f"链式复合 {chain_ret} 超出 [0.63, 0.90]（分段积={product:.4f}）"


# ── 测试 4: 增量审计 3 项，全部为"增量"且不破坏保持（REV1：允许子类标签）──

def test_increment_audit():
    """增量审计：3 项，全部为'增量'且不破坏保持（允许子类标签：链式映射贡献/关系核体现）"""
    task_data = load_task()
    engine = HomomorphismEngine()
    result = engine.transfer_from_graph(
        task_data["source_domain"],
        task_data["target_domain"],
        task_data["candidate_mappings"],
    )

    inc = result["increment_audit"]
    assert len(inc) == 3, f"增量项应为 3，实际 {len(inc)}"
    for i in inc:
        j = i["judgement"]
        # ① 必须以"增量"开头（是增量，不是损耗/破坏）
        assert j.startswith("增量"), f"判定应以'增量'开头: {j}"
        # ② 不得含独立的"破坏"（排除"不破坏"中的"破坏"——"增量不破坏保持"允许）
        assert "破坏" not in j.replace("不破坏", ""), f"增量不得破坏保持: {j}"


# ── 测试 5: 增量审计与任务书 §二 逐项一致（REV1 新增）──

def test_increment_audit_matches_task_spec():
    """REV1 新增：引擎增量输出与任务书 §二 increment_audit_expected 逐项一致"""
    task_data = load_task()
    engine = HomomorphismEngine()
    result = engine.transfer_from_graph(
        task_data["source_domain"],
        task_data["target_domain"],
        task_data["candidate_mappings"],
    )

    engine_items = {i["item"]: i["judgement"] for i in result["increment_audit"]}
    spec_items = {i["item"]: i["judgement"] for i in task_data["increment_audit_expected"]}
    assert set(engine_items.keys()) == set(spec_items.keys()), "增量项清单不一致"
    for item in spec_items:
        assert engine_items[item] == spec_items[item], \
            f"{item} 判定不一致: 引擎={engine_items[item]}, 预期={spec_items[item]}"


# ── 测试 6: 迁移验证 4/4 PASS ──

def test_scenarios_all_pass():
    """迁移验证 4/4 PASS"""
    task_data = load_task()
    engine = HomomorphismEngine()
    result = engine.transfer_from_graph(
        task_data["source_domain"],
        task_data["target_domain"],
        task_data["candidate_mappings"],
        task_data.get("verification_scenarios", []),
    )

    scenarios = result["scenarios"]
    assert len(scenarios) == 4, f"场景应为 4，实际 {len(scenarios)}"
    for s in scenarios:
        assert s["result"] == "PASS", f"场景 {s['id']}({s['name']}) 应为 PASS，实际 {s['result']}"


# ── 测试 7: 壳核审计三层判定正确 + H1 挂载 ──

def test_shell_nucleus():
    """壳核审计：数学=壳（可换）、逻辑=核（可迁）、追问=方向核（保持，挂H1）"""
    task_data = load_task()
    cultivator = SeedCultivation(time_scale="skill")
    sn_input = task_data.get("shell_nucleus_input", {})
    result = cultivator.shell_nucleus_audit(sn_input)

    sn = result["shell_nucleus_audit"]
    tl = sn["three_layers"]

    assert tl["topic_shell"]["action"] == "可更换", \
        f"题目壳 action={tl['topic_shell']['action']}，期望=可更换"
    assert tl["method_nucleus"]["action"] == "可迁移", \
        f"方法核 action={tl['method_nucleus']['action']}，期望=可迁移"
    assert tl["direction_nucleus"]["action"] == "必须保持", \
        f"方向核 action={tl['direction_nucleus']['action']}，期望=必须保持"
    assert "H1" in tl["direction_nucleus"]["hypothesis"], \
        f"方向核应挂 H1 假设，实际={tl['direction_nucleus']['hypothesis']}"
    assert sn["passed"] is True, "壳核审计应全部通过"


# ── 直接运行入口 ──

if __name__ == "__main__":
    print("=" * 70)
    print("  CASE-LIU 柳智宇同态映射验证 — 自动化测试 (7 项，REV1)")
    print("=" * 70)

    test_funcs = [
        test_mapping_retention,
        test_average_retention,
        test_chain_retention,
        test_increment_audit,
        test_increment_audit_matches_task_spec,
        test_scenarios_all_pass,
        test_shell_nucleus,
    ]

    passed = 0
    failed = 0
    for i, fn in enumerate(test_funcs, 1):
        try:
            fn()
            print(f"\n  [测试 {i}] {fn.__name__}: ✅ PASS")
            passed += 1
        except AssertionError as e:
            print(f"\n  [测试 {i}] {fn.__name__}: ❌ FAIL")
            print(f"    {e}")
            failed += 1
        except Exception as e:
            print(f"\n  [测试 {i}] {fn.__name__}: ❌ ERROR")
            print(f"    {type(e).__name__}: {e}")
            failed += 1

    print(f"\n{'=' * 70}")
    print(f"  总计: {passed} 通过, {failed} 失败")
    print(f"{'=' * 70}")

    sys.exit(0 if failed == 0 else 1)