"""临时验证脚本：Q6 (HF 06) + Q7 (arXiv 05)"""
import json
from pathlib import Path

OUT = Path(r"e:\00-TRAEWK\6a59e217b55e181ea97f0df3\wuxing_flowengine\output")

# === Q6: HF 2026-06 ===
print("=" * 60)
print("Q6: HF 2026-06 量级核验")
print("=" * 60)
hf06 = OUT / "hf_tree_2026-06.json"
if hf06.exists():
    d = json.loads(hf06.read_text(encoding="utf-8"))
    print(f"meta: {json.dumps(d['meta'], indent=2, ensure_ascii=False)}")
    print()
    for n in d["nodes"]:
        flag = " <-- weight=0!" if n["weight"] == 0 else ""
        print(f"  {n['id']:40s} weight={n['weight']:>6d}{flag}")
    total = sum(n["weight"] for n in d["nodes"])
    zero_count = sum(1 for n in d["nodes"] if n["weight"] == 0)
    print(f"\n  total_weight={total}, zero_nodes={zero_count}/{len(d['nodes'])}")
else:
    print("  FILE NOT FOUND")

# === Q7: arXiv 2026-05 ===
print()
print("=" * 60)
print("Q7: arXiv 2026-05 量级核验")
print("=" * 60)
ax05 = OUT / "arxiv_ai_tree_2026-05.json"
if ax05.exists():
    d = json.loads(ax05.read_text(encoding="utf-8"))
    print(f"meta: {json.dumps(d.get('meta', {}), indent=2, ensure_ascii=False)}")
    print()
    for n in d["nodes"]:
        print(f"  {n['id']:40s} weight={n.get('weight',0):>6d}")
    total = sum(n.get("weight", 0) for n in d["nodes"])
    print(f"\n  total_weight={total}, nodes={len(d['nodes'])}")
else:
    print("  FILE NOT FOUND")

# Compare with other arXiv months
print()
print("=" * 60)
print("arXiv 逐月对比")
print("=" * 60)
for m in ["2026-05", "202606", "202607", "202608"]:
    f = OUT / f"arxiv_ai_tree_{m}.json"
    if f.exists():
        d = json.loads(f.read_text(encoding="utf-8"))
        total = sum(n.get("weight", 0) for n in d["nodes"])
        print(f"  {m}: total_weight={total}, nodes={len(d['nodes'])}")