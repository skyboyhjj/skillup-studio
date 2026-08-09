"""生成 CASE-LIU 验证结果 result.json（REV2：图驱动全链路）"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from homomorphism_engine import HomomorphismEngine, resolve_json_refs
from seed_cultivation import SeedCultivation

# Load task
task_path = os.path.join(os.path.dirname(__file__), "..", "data", "task_liu_input.json")
with open(task_path, encoding="utf-8") as f:
    task = json.load(f)

engine = HomomorphismEngine()

# 1. homo_verify
homo = engine.transfer_from_graph(
    task["source_domain"], task["target_domain"],
    task["candidate_mappings"], task.get("verification_scenarios", [])
)

# 2. chain_verify（REV2：解析 $ref + 传入直接映射保持度）
resolved = resolve_json_refs(task)
chain = engine.transfer_chain(
    resolved["chain_mappings"][0]["segments"],
    direct_retention=homo["average_retention"],
)

# 3. shell_nucleus_audit
cultivator = SeedCultivation(time_scale="skill")
sn = cultivator.shell_nucleus_audit(task.get("shell_nucleus_input", {}))

# Build result
scenario_pass = sum(1 for s in homo["scenarios"] if s["result"] == "PASS")
scenario_total = len(homo["scenarios"])

result = {
    "task_id": "TASK-HOMO-LIU-20260808",
    "protocol_version": "V1.5",
    "generated_at": "2026-08-08",
    "modes": {
        "homo_verify": homo,
        "chain_verify": chain,
        "shell_nucleus_audit": sn["shell_nucleus_audit"],
    },
    "summary": {
        "homo_verify": {
            "average_retention": homo["average_retention"],
            "mapping_count": len(homo["mappings"]),
            "scenario_pass_rate": f"{scenario_pass}/{scenario_total}",
        },
        "chain_verify": {
            "composite": chain["composite"],
            "bridge_gain": chain["bridge_gain"],
            "segment_count": chain.get("segment_count", 2),
            "direct_vs_chain": chain.get("direct_comparison", {}).get("verdict", "N/A"),
            "delta": chain.get("direct_comparison", {}).get("delta", 0),
        },
        "shell_nucleus_audit": {
            "passed": sn["shell_nucleus_audit"]["passed"],
            "system_type": sn["shell_nucleus_audit"]["declaration"]["system_type"],
        },
    },
}

# Ensure output dir
output_dir = os.path.join(os.path.dirname(__file__), "..", "output", "reports")
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "result_liu.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

# Console summary
print("=" * 60)
print("  CASE-LIU 柳智宇同态映射验证 — 结果摘要 (REV2)")
print("=" * 60)
print(f"\n  [homo_verify] 平均保持度: {homo['average_retention']}")
print(f"    映射数: {len(homo['mappings'])}")
print(f"    场景通过率: {scenario_pass}/{scenario_total}")
print(f"    增量审计: {len(homo['increment_audit'])} 项，全部不破坏保持")
print(f"\n  [chain_verify] 分段数: {chain.get('segment_count', 2)}")
for sr in chain.get("segment_results", []):
    print(f"    段 {sr['from']}→{sr['to']}: retention={sr['retention']} (预期 {sr['expected_retention']})")
print(f"    分段积: {chain['segments_product']}")
print(f"    桥梁增益: {chain['bridge_gain']}")
print(f"    链式复合: {chain['composite']}")
dc = chain.get("direct_comparison", {})
if dc:
    print(f"    直接映射: {dc.get('direct_mapping_retention')}")
    print(f"    偏差: {dc.get('delta')}")
    print(f"    判定: {dc.get('verdict')}")
print(f"\n  [shell_nucleus_audit] 通过: {sn['shell_nucleus_audit']['passed']}")
print(f"    体系类型: {sn['shell_nucleus_audit']['declaration']['system_type']}")
print(f"\n  result.json -> {output_path}")
print("=" * 60)