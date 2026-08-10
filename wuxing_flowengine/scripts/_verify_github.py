"""临时验证脚本：GitHub rate limit 确认"""
import json
from pathlib import Path

OUT = Path(r"e:\00-TRAEWK\6a59e217b55e181ea97f0df3\wuxing_flowengine\output")

print("=" * 60)
print("GitHub 逐月节点权重对比")
print("=" * 60)
for m in ["2026-05", "202606", "202607", "2026-08"]:
    f = OUT / f"github_tree_{m}.json"
    if f.exists():
        d = json.loads(f.read_text(encoding="utf-8"))
        total = sum(n.get("weight", 0) for n in d["nodes"])
        zero_nodes = [n["id"] for n in d["nodes"] if n.get("weight", 0) == 0]
        print(f"\n{m}: total_weight={total}, nodes={len(d['nodes'])}, zero_nodes={len(zero_nodes)}")
        if zero_nodes:
            print(f"  weight=0: {zero_nodes}")
        for n in d["nodes"]:
            err = n.get("error", "")
            flag = " <-- ERROR" if err else (" <-- weight=0" if n.get("weight",0)==0 else "")
            print(f"  {n['id']:35s} weight={n.get('weight',0):>8d}{flag}")
            if err:
                print(f"    error: {err[:100]}")
    else:
        print(f"\n{m}: FILE NOT FOUND")