#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_wuxing_graph.py —— D 道经五行图谱生成器
================================================================
输入：daojing_database_v2.json（81 章 dominant）
输出：
  output/wuxing_graph/daojing_wuxing_graph.json   图谱数据（节点/边/统计）
  output/wuxing_graph/daojing_wuxing_graph.html   可视化（零依赖 SVG，五行生态环 + 章节生克四邻）

模型：
  - 节点 = 五行（木火土金水）+ 每行章节列表（章号/标题/dominant）
  - 边   = 章间生克：两章 dominant 关系（生/克/同气/无关）
  - 布局 = 五行生态环（环形 + 中心玄鉴金？——五行环：木火土金水顺时针相生，隔位相克）

用法：
  python build_wuxing_graph.py --db verify/daojing_database_v2.json --out output/wuxing_graph
"""

import argparse
import json
import math
from pathlib import Path

# 五行相生环：木→火→土→金→水→木
SHENG_CYCLE = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
# 五行相克：木克土 土克水 水克火 火克金 金克木
KE_MAP = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
WUXING_ORDER = ["木", "火", "土", "金", "水"]
WUXING_COLORS = {"木": "#2ecc71", "火": "#e74c3c", "土": "#d4a44a", "金": "#f1c40f", "水": "#3498db"}
WUXING_CN = {"木": "木·仁(缘位)", "火": "火·礼(时位)", "土": "土·信(宇位)", "金": "金·义(玄鉴)", "水": "水·智(识位)"}


def relation(a: str, b: str) -> str:
    """两行关系：生/克/同气/无关"""
    if a == b:
        return "同气"
    if SHENG_CYCLE.get(a) == b:
        return "生"          # a 生 b
    if SHENG_CYCLE.get(b) == a:
        return "被生"        # b 生 a（a 被生）
    if KE_MAP.get(a) == b:
        return "克"          # a 克 b
    if KE_MAP.get(b) == a:
        return "被克"        # b 克 a（a 被克）
    return "无关"


def build_graph(db_path: Path) -> dict:
    db = json.loads(db_path.read_text(encoding="utf-8"))

    # 1. 收集 81 章 dominant
    chapters = []          # {num, title, dominant}
    by_wx = {w: [] for w in WUXING_ORDER}
    for num in range(1, 82):
        node = db.get(str(num), {})
        dom = (node.get("x_wuxing") or {}).get("dominant")
        if not dom:
            continue
        chapters.append({"num": num, "title": node.get("chapter_title", ""), "dominant": dom})
        by_wx[dom].append({"num": num, "title": node.get("chapter_title", "")})

    # 2. 五行节点（大小 = 章数）
    wx_nodes = []
    for w in WUXING_ORDER:
        wx_nodes.append({
            "wx": w,
            "label": WUXING_CN[w],
            "color": WUXING_COLORS[w],
            "count": len(by_wx[w]),
            "chapters": by_wx[w],
        })

    # 3. 五行级生克边
    wx_edges = []
    for a in WUXING_ORDER:
        b = SHENG_CYCLE[a]
        wx_edges.append({"from": a, "to": b, "type": "生", "color": "#2ecc71"})
        b2 = KE_MAP[a]
        wx_edges.append({"from": a, "to": b2, "type": "克", "color": "#e74c3c"})

    # 4. 章间生克网络（aggregated：每章 → 四邻）
    #    生我（母）/ 我生（子）/ 克我（所不胜）/ 我克（所胜）
    chapter_relations = {}
    for ch in chapters:
        w = ch["dominant"]
        sheng_me = [k for k, v in SHENG_CYCLE.items() if v == w]        # 生我者
        wo_sheng = SHENG_CYCLE[w]                                       # 我生
        ke_me = [k for k, v in KE_MAP.items() if v == w]                # 克我者
        wo_ke = KE_MAP[w]                                               # 我克
        chapter_relations[ch["num"]] = {
            "dominant": w,
            "title": ch["title"],
            "母(生我)": by_wx.get(sheng_me[0], []) if sheng_me else [],
            "子(我生)": by_wx.get(wo_sheng, []),
            "所不胜(克我)": by_wx.get(ke_me[0], []) if ke_me else [],
            "所胜(我克)": by_wx.get(wo_ke, []),
        }

    # 5. 统计
    from collections import Counter
    dist = Counter(ch["dominant"] for ch in chapters)
    stats = {
        "total_chapters": len(chapters),
        "wuxing_dist": dict(dist),
        "edge_types": {"生": sum(1 for e in wx_edges if e["type"] == "生"),
                       "克": sum(1 for e in wx_edges if e["type"] == "克")},
        "relation_counts": {"生": 0, "克": 0, "同气": 0, "无关": 0},
    }
    # 章间两两关系统计
    for i in range(len(chapters)):
        for j in range(i + 1, len(chapters)):
            r = relation(chapters[i]["dominant"], chapters[j]["dominant"])
            if r in ("生", "被生"):
                stats["relation_counts"]["生"] += 1
            elif r in ("克", "被克"):
                stats["relation_counts"]["克"] += 1
            elif r == "同气":
                stats["relation_counts"]["同气"] += 1
            else:
                stats["relation_counts"]["无关"] += 1

    return {
        "schema_version": "1.0",
        "generated": __import__("datetime").datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "daojing_database_v2.json#x_wuxing.dominant",
        "wuxing_nodes": wx_nodes,
        "wuxing_edges": wx_edges,
        "chapter_relations": chapter_relations,
        "stats": stats,
    }


def render_html(g: dict) -> str:
    """零依赖 SVG 可视化：五行生态环（环形布局 + 生克边）+ 章节选择面板"""
    W = 900
    H = 620
    cx, cy = 300, 310
    R = 170

    # 五行节点坐标（环形：木火土金水）
    pos = {}
    for i, w in enumerate(WUXING_ORDER):
        ang = -90 + i * 72
        pos[w] = (cx + R * math.cos(math.radians(ang)), cy + R * math.sin(math.radians(ang)))

    # SVG 元素
    svg_parts = []
    # 生克边（先画边后画节点）
    for e in g["wuxing_edges"]:
        x1, y1 = pos[e["from"]]
        x2, y2 = pos[e["to"]]
        # 曲线边（带弧度）
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        off = 30
        dx, dy = y2 - y1, -(x2 - x1)
        nl = math.hypot(dx, dy) or 1
        mx += dx / nl * off
        my += dy / nl * off
        dash = "4,4" if e["type"] == "克" else ""
        svg_parts.append(
            f'<path d="M{x1:.0f},{y1:.0f} Q{mx:.0f},{my:.0f} {x2:.0f},{y2:.0f}" '
            f'stroke="{e["color"]}" stroke-width="2.5" fill="none" stroke-dasharray="{dash}" opacity="0.75">'
            f'<title>{e["from"]} → {e["to"]}：{e["type"]}</title></path>'
        )

    # 五行节点
    for n in g["wuxing_nodes"]:
        x, y = pos[n["wx"]]
        r = 32 + n["count"] * 1.2  # 节点大小与章数正比
        svg_parts.append(
            f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.0f}" fill="{n["color"]}" fill-opacity="0.22" '
            f'stroke="{n["color"]}" stroke-width="3" class="wx-node" data-wx="{n["wx"]}" '
            f'style="cursor:pointer">'
            f'<title>{n["label"]}（{n["count"]} 章）</title></circle>'
        )
        svg_parts.append(
            f'<text x="{x:.0f}" y="{y - 4:.0f}" text-anchor="middle" font-size="17" font-weight="bold" '
            f'fill="#1A1715">{n["wx"]}</text>'
        )
        svg_parts.append(
            f'<text x="{x:.0f}" y="{y + 16:.0f}" text-anchor="middle" font-size="12" fill="#555">{n["count"]} 章</text>'
        )

    # 图例
    legend = """
    <div style="position:absolute;right:20px;top:20px;background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:12px;font-size:12px;line-height:1.8">
      <div><span style="color:#2ecc71;font-weight:bold">━━</span> 相生（木→火→土→金→水）</div>
      <div><span style="color:#e74c3c;font-weight:bold">┅┅</span> 相克（隔位）</div>
      <div style="margin-top:6px;color:#999">点击五行节点 → 查看章节</div>
    </div>
    """

    # 章节面板（右侧）
    panel = """
    <div id="panel" style="position:absolute;right:20px;top:110px;width:300px;background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:14px;max-height:420px;overflow:auto;display:none;box-shadow:0 4px 16px rgba(0,0,0,.08)">
      <div id="panelTitle" style="font-size:15px;font-weight:bold;margin-bottom:10px"></div>
      <div id="panelBody" style="font-size:13px;line-height:1.9"></div>
    </div>
    """

    # 章节详情（点击章号）
    relations_js = json.dumps(g["chapter_relations"], ensure_ascii=False)

    js = f"""
    <script>
    const REL = {relations_js};
    const TITLES = {{}};
    for (const [num, r] of Object.entries(REL)) {{ TITLES[num] = r.title; }}

    function showPanel(wx) {{
      const nodes = {json.dumps(g["wuxing_nodes"], ensure_ascii=False)};
      const n = nodes.find(x => x.wx === wx);
      if (!n) return;
      const p = document.getElementById('panel');
      const pt = document.getElementById('panelTitle');
      const pb = document.getElementById('panelBody');
      pt.textContent = n.label + '（' + n.count + ' 章）';
      pt.style.color = n.color;
      let html = '<div style="font-weight:bold;margin:6px 0 2px;color:#888">本章</div>';
      html += n.chapters.map(c => `<span class="chap" data-num="${{c.num}}" style="cursor:pointer;color:#C94B3A">${{c.num}}章·${{c.title.slice(0,10)}}</span>`).join(' · ') || '无';
      // 生克四邻
      const rel = REL[String(n.chapters[0]?.num || '')];
      if (rel) {{
        for (const key of ['母(生我)','子(我生)','所不胜(克我)','所胜(我克)']) {{
          const list = rel[key];
          html += `<div style="font-weight:bold;margin:8px 0 2px;color:#888">${{key}}（${{list.length}} 章）</div>`;
          html += list.map(c => `<span class="chap" data-num="${{c.num}}" style="cursor:pointer;color:#555">${{c.num}}章·${{c.title.slice(0,10)}}</span>`).join(' · ') || '无';
        }}
      }}
      pb.innerHTML = html;
      p.style.display = 'block';
      // 绑定章节点击
      document.querySelectorAll('.chap').forEach(el => {{
        el.onclick = () => showChapter(parseInt(el.dataset.num));
      }});
    }}

    function showChapter(num) {{
      const r = REL[String(num)];
      if (!r) return;
      const p = document.getElementById('panel');
      const pt = document.getElementById('panelTitle');
      const pb = document.getElementById('panelBody');
      pt.textContent = '第' + num + '章 · ' + r.title;
      pt.style.color = {json.dumps(WUXING_COLORS, ensure_ascii=False)}[r.dominant];
      let html = `<div style="color:#888;margin-bottom:6px">dominant：<b>${{r.dominant}}</b></div>`;
      for (const key of ['母(生我)','子(我生)','所不胜(克我)','所胜(我克)']) {{
        const list = r[key];
        html += `<div style="font-weight:bold;margin:6px 0 2px;color:#888">${{key}}（${{list.length}} 章）</div>`;
        html += list.map(c => `<span class="chap" data-num="${{c.num}}" style="cursor:pointer;color:#555">${{c.num}}章·${{c.title.slice(0,10)}}</span>`).join(' · ') || '无';
      }}
      pb.innerHTML = html;
      p.style.display = 'block';
      document.querySelectorAll('.chap').forEach(el => {{
        el.onclick = () => showChapter(parseInt(el.dataset.num));
      }});
    }}

    // 初始化：点击五行节点
    document.querySelectorAll('.wx-node').forEach(el => {{
      el.onclick = () => showPanel(el.dataset.wx);
    }});
    </script>
    """

    html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>道经五行图谱 · 章间生克网络</title>
<style>
  body {{ margin:0; font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif; background:#FAF8F5; color:#1A1715; }}
  header {{ padding:18px 24px; border-bottom:1px solid #e5e7eb; background:#fff; }}
  header h1 {{ margin:0; font-size:20px; color:#C94B3A; }}
  header p {{ margin:4px 0 0; font-size:12px; color:#888; }}
  .graph-wrap {{ position:relative; max-width:960px; margin:20px auto; padding:20px; background:#fff; border-radius:12px; border:1px solid #e5e7eb; }}
  .stat-row {{ display:flex; gap:16px; flex-wrap:wrap; margin:14px 24px; font-size:13px; color:#555; }}
  .stat-row b {{ color:#1A1715; }}
</style>
</head>
<body>
<header>
  <h1>道经五行图谱 · 章间生克网络</h1>
  <p>81 章 dominant → 五行生态环 + 生克四邻（点击五行节点或章号展开）· 生成 {g["generated"]}</p>
</header>
<div class="stat-row">
  <span>总章数 <b>{g["stats"]["total_chapters"]}</b></span>
  <span>分布 <b>{json.dumps(g["stats"]["wuxing_dist"], ensure_ascii=False)}</b></span>
  <span>章间关系 <b>{json.dumps(g["stats"]["relation_counts"], ensure_ascii=False)}</b></span>
</div>
<div class="graph-wrap">
  {legend}
  {panel}
  <svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" style="display:block;margin:0 auto">
    {''.join(svg_parts)}
  </svg>
</div>
{js}
</body>
</html>
"""
    return html


def main():
    parser = argparse.ArgumentParser(description="D 道经五行图谱生成器")
    parser.add_argument("--db", default="verify/daojing_database_v2.json", help="结构库")
    parser.add_argument("--out", default="output/wuxing_graph", help="输出目录")
    args = parser.parse_args()

    db_path = Path(args.db)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    graph = build_graph(db_path)
    (out_dir / "daojing_wuxing_graph.json").write_text(
        json.dumps(graph, ensure_ascii=False, indent=1), encoding="utf-8")
    (out_dir / "daojing_wuxing_graph.html").write_text(
        render_html(graph), encoding="utf-8")

    print("=" * 68)
    print("D 道经五行图谱 | build_wuxing_graph.py")
    print("=" * 68)
    s = graph["stats"]
    print(f"[章节] {s['total_chapters']}/81 章（有 dominant）")
    print(f"[分布] {s['wuxing_dist']}")
    print(f"[章间关系] 生={s['relation_counts']['生']} 克={s['relation_counts']['克']} "
          f"同气={s['relation_counts']['同气']} 无关={s['relation_counts']['无关']}")
    print(f"[输出] {out_dir / 'daojing_wuxing_graph.json'}")
    print(f"[输出] {out_dir / 'daojing_wuxing_graph.html'}")
    print("=" * 68)


if __name__ == "__main__":
    main()
