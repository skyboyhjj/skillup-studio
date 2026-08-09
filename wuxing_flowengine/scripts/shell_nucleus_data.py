"""提取壳核五行分布逐月详细数据"""
import json
from collections import Counter

WX_ORDER = ["木", "火", "土", "金", "水"]

# BAAI shell
for m in ["202605", "202606", "202607"]:
    path = f"../output/baai_tree_{m}.json"
    d = json.load(open(path, "r", encoding="utf-8"))
    nodes = d["nodes"]
    total = sum(n.get("weight", 0) for n in nodes)
    wx = Counter()
    for n in nodes:
        wx[n.get("wuxing", "?")] += n.get("weight", 0)
    parts = "  ".join(f"{w}:{wx.get(w,0)/total*100:.1f}%" for w in WX_ORDER)
    details = []
    for n in sorted(nodes, key=lambda x: -x.get("weight", 0)):
        w = n.get("wuxing", "?")
        wt = n.get("weight", 0)
        details.append(f"{n['name']}({w}={wt})")
    print(f"BAAI {m[4:]}  total={total:>4d}")
    print(f"  分布: {parts}")
    print(f"  节点: {'  '.join(details)}")
    print()

# arXiv nucleus
for m in ["202606", "202607", "202608"]:
    path = f"../output/arxiv_ai_tree_{m}.json"
    d = json.load(open(path, "r", encoding="utf-8"))
    nodes = d["nodes"]
    total = sum(n.get("weight", 0) for n in nodes)
    wx = Counter()
    for n in nodes:
        wx[n.get("wuxing", "?")] += n.get("weight", 0)
    parts = "  ".join(f"{w}:{wx.get(w,0)/total*100:.1f}%" for w in WX_ORDER)
    details = []
    for n in sorted(nodes, key=lambda x: -x.get("weight", 0)):
        w = n.get("wuxing", "?")
        wt = n.get("weight", 0)
        details.append(f"{n['name']}({w}={wt})")
    print(f"arXiv {m[4:]} total={total:>5d}")
    print(f"  分布: {parts}")
    print(f"  节点: {'  '.join(details)}")
    print()