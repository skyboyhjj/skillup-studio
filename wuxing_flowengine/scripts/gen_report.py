#!/usr/bin/env python3
"""
生成 Phase 1 Markdown 诊断报告
支持参数化调用，可被月度编排器导入。
"""
import json, os
from datetime import datetime


def run(base_dir, snapshot_path=None, class_path=None, diag_path=None, output_path=None, month_label=None):
    """
    生成 Phase 1 Markdown 诊断报告。

    参数:
        base_dir:     项目根目录
        snapshot_path:快照 JSON 路径
        class_path:   分类结果 JSON 路径
        diag_path:    诊断结果 JSON 路径
        output_path:  输出 Markdown 路径
        month_label:  月度标签

    返回:
        生成的 Markdown 文件路径
    """
    if snapshot_path is None:
        snap_dir = os.path.join(base_dir, "data", "snapshots")
        snap_files = sorted([f for f in os.listdir(snap_dir) if f.endswith("_snapshot.json")], reverse=True)
        snapshot_path = os.path.join(snap_dir, snap_files[0]) if snap_files else os.path.join(base_dir, "data", "snapshots", "2026-07-30_snapshot.json")

    suffix = f"_{month_label}" if month_label else ""
    if class_path is None:
        class_path = os.path.join(base_dir, "output", f"wuxing_classification{suffix}.json")
    if diag_path is None:
        diag_path = os.path.join(base_dir, "output", f"phase1_diagnosis{suffix}.json")
    if output_path is None:
        output_path = os.path.join(base_dir, "output", f"phase1_diagnosis_report{suffix}.md")

    output_dir = os.path.join(base_dir, "output")
    os.makedirs(output_dir, exist_ok=True)

    # 更新快照
    with open(snapshot_path, "r", encoding="utf-8") as f:
        snap = json.load(f)

    if os.path.exists(class_path):
        with open(class_path, "r", encoding="utf-8") as f:
            classified = json.load(f)
        class_map = {c["id"]: {"wuxing": c["wuxing"], "cognitive_depth": c["cognitive_depth"]} for c in classified}
        for n in snap.get("nodes", snap if isinstance(snap, list) else []):
            if n.get("id") in class_map:
                n["wuxing"] = class_map[n["id"]]["wuxing"]
                n["cognitive_depth"] = class_map[n["id"]]["cognitive_depth"]
        snap["classification_time"] = f"{month_label or '2026-07-30'}T14:00:00+08:00"
        with open(snapshot_path, "w", encoding="utf-8") as f:
            json.dump(snap, f, ensure_ascii=False, indent=2)
        print(f"  Updated snapshot")

    # 加载诊断
    with open(diag_path, "r", encoding="utf-8") as f:
        diag = json.load(f)

    s = diag["stats"]
    d = diag["depth_dist"]
    w = diag["wuxing_dist"]
    dims = diag["four_dims"]
    tracks = diag["tracks"]
    diag_r = diag["diagnosis"]
    total = s["total"]
    l3_count = total - 2 - 16

    lines = []
    lines.append("# 道境五行诊断报告 · AI 知识树")
    lines.append("")
    lines.append(f"**采集时间**: {month_label or '2026-07-30'}")
    lines.append("**数据来源**: BAAI 智源社区知识树 (hub.baai.ac.cn/knowledge-tree/graph)")
    lines.append("**诊断模式**: static（单次快照）")
    lines.append(f"**节点数**: {total}（Level 1: 2, Level 2: 16, Level 3: {l3_count}）")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 一、数据概况")
    lines.append("")
    lines.append("| 指标 | 数值 | 说明 |")
    lines.append("|------|------|------|")
    lines.append(f"| 总节点数 | {total} | Level 1: 2, Level 2: 16, Level 3: {l3_count} |")
    lines.append(f"| 种子层 (L1) | {s['seed']} | 基础知识、经典算法 |")
    lines.append(f"| 现行层 (L2) | {s['current']} | 具体技术方案、工程实践 |")
    lines.append(f"| 超越层 (L3/L4) | {s['transcend']} | 新架构、新范式 |")
    lines.append("")
    lines.append("## 二、认知深度分布")
    lines.append("")
    lines.append("| 深度 | 含义 | 节点数 | 占比 |")
    lines.append("|------|------|--------|------|")
    for lv in ["L1", "L2", "L3", "L4"]:
        cnt = d.get(lv, 0)
        desc = {"L1": "白话·基本义", "L2": "精读·哲学义", "L3": "应用·实践义", "L4": "学术·考据义"}[lv]
        lines.append(f"| {lv} | {desc} | {cnt} | {cnt/total*100:.1f}% |")
    lines.append("")
    lines.append("## 三、五行频次分布")
    lines.append("")
    lines.append("| 五行 | 角色 | 节点数 | 占比 | 主导领域 |")
    lines.append("|------|------|--------|------|----------|")
    wx_domains = {"木": "具身智能、多模态、生成式AI", "火": "智能体、推荐系统、交叉应用", "土": "ML基础、AI系统、软件工程", "金": "安全可信、知识表示、逻辑推理", "水": "LLM、NLP、CV、科学AI"}
    wx_roles = {"木": "开拓者", "火": "传播者", "土": "承载者", "金": "批判者", "水": "探索者"}
    for wx in ["木", "火", "土", "金", "水"]:
        cnt = w.get(wx, 0)
        lines.append(f"| {wx} | {wx_roles[wx]} | {cnt} | {cnt/total*100:.1f}% | {wx_domains[wx]} |")
    lines.append("")
    lines.append("## 四、三层×五行交叉矩阵")
    lines.append("")
    lines.append("| 层 | 木 | 火 | 土 | 金 | 水 |")
    lines.append("|----|----|----|----|----|----|")
    for row in diag_r["dim2_matrix"]:
        lines.append(f"| {row['layer']} | {row['wuxing']['木']['count']} | {row['wuxing']['火']['count']} | {row['wuxing']['土']['count']} | {row['wuxing']['金']['count']} | {row['wuxing']['水']['count']} |")
    lines.append("")
    lines.append("## 五、五行熵")
    lines.append("")
    lines.append(f"- **H** = {diag_r['dim4_entropy']['H']} / {diag_r['dim4_entropy']['H_max']}（{diag_r['dim4_entropy']['ratio']*100:.0f}%）")
    lines.append(f"- **判定**: {diag_r['dim4_entropy']['desc']}")
    lines.append("")
    lines.append("## 六、重心方位")
    lines.append("")
    lines.append(f"- **质心**: ({diag_r['dim5_compass']['cx']}, {diag_r['dim5_compass']['cy']})")
    lines.append(f"- **判定**: {diag_r['dim5_compass']['desc']}")
    lines.append("")
    lines.append("## 七、重心偏移路径")
    lines.append("")
    lines.append(f"- **路径**: {' → '.join(diag_r['dim3_path'])}")
    lines.append(f"- **节奏**: {diag_r['dim3_rhythm']}")
    lines.append("")
    lines.append("## 八、道境四维读数")
    lines.append("")
    lines.append("| 维度 | 值 | 解读 |")
    lines.append("|------|------|------|")
    lines.append(f"| O_t（时位） | {dims['O_t']:.4f} | {'沉淀定型' if dims['O_t'] > 0.5 else '仍在演化中'} |")
    lines.append(f"| E_u（宇位） | {dims['E_u']:.4f} | {'领域均衡' if dims['E_u'] > 0.5 else '分布不均'} |")
    lines.append(f"| C_k（识位） | {dims['C_k']:.4f} | {'深层理解充足' if dims['C_k'] > 0.5 else '仍在积累'} |")
    lines.append(f"| K_y（缘位） | {dims['K_y']:.4f} | {'因果链紧密' if dims['K_y'] > 0.5 else '领域间因果链松散'} |")
    lines.append("")
    lines.append("## 九、四轨 S 值对比")
    lines.append("")
    lines.append("| 轨道 | 数学定义 | S 值 |")
    lines.append("|------|----------|------|")
    lines.append(f"| A · 乘积 S | O_t×E_u×C_k×K_y×100 | {tracks['A']:.2f} |")
    lines.append(f"| B · S_spiral | Σ(各维度加权) | {tracks['B']:.2f} |")
    lines.append(f"| C · S_v2 | phase×gradient×accumulation | {tracks['C']:.2f} |")
    lines.append(f"| D · 模长 S | √(O_t²+E_u²+C_k²+K_y²) | {tracks['D']:.4f} |")
    lines.append("")
    lines.append("## 十、阶段判定")
    lines.append("")
    lines.append(f"**{diag['stage']}**")
    lines.append("")
    lines.append("## 十一、一句话风格判语")
    lines.append("")
    lines.append(f"> {diag_r['dim7_summary']}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 十二、关键发现")
    lines.append("")
    w_pct = {wx: w.get(wx, 0)/total*100 for wx in ["木","火","土","金","水"]}
    findings = [
        f"1. 水行主导：水行占比最高（{w_pct['水']:.1f}%），反映 AI 领域以深层探索和创新为核心驱动力。",
        f"2. 金行薄弱：金行仅占 {w_pct['金']:.1f}%，安全、可信、可解释性、因果推理等领域相对薄弱。",
        f"3. 种子层土行独大：种子层基础节点以土行为主，说明 AI 知识树的根基是扎实的基础设施和方法论。",
        f"4. 高度多元：熵值达 {diag_r['dim4_entropy']['ratio']*100:.0f}%，处于'化'阶段，AI 领域正经历范式转换。",
        f"5. 四轨验证：乘积 S（轨道 A）= {tracks['A']:.2f}，螺旋 S（轨道 B）= {tracks['B']:.2f}，模长 S（轨道 D）= {tracks['D']:.4f}。",
    ]
    for f_text in findings:
        lines.append(f_text)
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    lines.append("*Phase 1: 数据采集 & 静态诊断*")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"  Markdown report saved: {os.path.basename(output_path)}")
    return output_path


if __name__ == "__main__":
    DEFAULT_BASE = r"C:\Users\hejij\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a59e217b55e181ea97f0df3\wuxing_flowengine"
    run(DEFAULT_BASE)