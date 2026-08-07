"""
从浏览器日志构建 2026-08-07 知识树快照
输入: 浏览器 evaluate 日志 (节点坐标 + 边坐标)
输出: 标准快照 JSON (nodes with id/level/parent_id/category + edges with source_id/target_id)

层级检测策略:
- 使用已知的 16 个分类名进行匹配（来自 2026-07-30 快照）
- 同时结合子节点数阈值 >= 8 作为辅助判断
"""

import json
import os
from datetime import datetime, timezone, timedelta

# 路径
LOG_FILE = r"C:\Users\hejij\AppData\Local\Temp\trae\browser-logs\evaluate-2026-08-07T09-16-55-594Z.log"
OUTPUT_DIR = r"e:\00-TRAEWK\6a59e217b55e181ea97f0df3\wuxing_flowengine\data\snapshots"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "2026-08-07_snapshot.json")

# 已知的 Level 2 分类名（来自 2026-07-30 快照）
KNOWN_CATEGORIES = [
    "大语言模型",
    "自然语言处理",
    "具身智能与机器人",
    "多模态智能",
    "智能体",
    "生成式AI",
    "生成式 AI",  # 浏览器数据中的变体
    "机器学习基础",
    "安全可信与伦理",
    "安全、可信与伦理",  # 浏览器数据中的变体
    "计算机视觉",
    "交叉领域智能应用",
    "知识表示与逻辑推理",
    "推荐系统与信息检索",
    "AI系统与硬件",
    "AI 系统与硬件",  # 浏览器数据中的变体
    "软件工程与编程",
    "科学AI",
    "科学 AI",  # 浏览器数据中的变体
    "其他AI领域",
]

# 名称归一化映射（浏览器数据名 → 标准名）
NAME_ALIASES = {
    "生成式 AI": "生成式AI",
    "安全、可信与伦理": "安全可信与伦理",
    "AI 系统与硬件": "AI系统与硬件",
    "科学 AI": "科学AI",
}

def load_log_data():
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        raw = f.read().strip()
    if raw.startswith('"'):
        raw = json.loads(raw)
    return json.loads(raw)

def build_coord_to_name(nodes):
    mapping = {}
    for n in nodes:
        key = (round(n['x'], 2), round(n['y'], 2))
        mapping[key] = n['name']
    return mapping

def find_node_by_coord(coord_map, x, y):
    key = (round(x, 2), round(y, 2))
    return coord_map.get(key)

def normalize_name(name):
    """将浏览器数据中的名称归一化到标准名"""
    return NAME_ALIASES.get(name, name)

def build_hierarchy(nodes, edges):
    coord_map = build_coord_to_name(nodes)
    
    parent_children = {}
    child_parents = {}
    
    for e in edges:
        src_name = find_node_by_coord(coord_map, e['x1'], e['y1'])
        tgt_name = find_node_by_coord(coord_map, e['x2'], e['y2'])
        
        if src_name and tgt_name:
            if src_name not in parent_children:
                parent_children[src_name] = set()
            parent_children[src_name].add(tgt_name)
            
            if tgt_name not in child_parents:
                child_parents[tgt_name] = set()
            child_parents[tgt_name].add(src_name)
    
    root_name = "大语言模型"
    child_counts = {name: len(children) for name, children in parent_children.items()}
    
    # 识别 Level 2 节点: 匹配已知分类名
    level2_names = set()
    for name in [n['name'] for n in nodes]:
        if name == root_name:
            continue
        norm = normalize_name(name)
        if norm in KNOWN_CATEGORIES:
            level2_names.add(name)
    
    # 补充: 子节点数 >= 8 但未被已知分类覆盖的节点
    for name in [n['name'] for n in nodes]:
        if name != root_name and name not in level2_names:
            if child_counts.get(name, 0) >= 8:
                print(f"  [警告] 未匹配已知分类但子节点数 >= 8: {name} ({child_counts[name]})")
    
    # 预分配 ID
    name_to_id = {}
    for i, n in enumerate(nodes):
        node_id = f"node_{i+1:04d}"
        name_to_id[n['name']] = node_id
    
    root_id = name_to_id[root_name]
    
    # 构建结果节点
    result_nodes = []
    for n in nodes:
        name = n['name']
        node_id = name_to_id[name]
        
        if name == root_name:
            level = 1
            parent_id = None
            category = "root"
        elif name in level2_names:
            level = 2
            parent_id = root_id
            category = normalize_name(name)
        else:
            level = 3
            if name in child_parents:
                parents = child_parents[name]
                # 优先选择 Level 2 parent
                l2_candidates = [(p, child_counts.get(p, 0)) for p in parents if p in level2_names]
                if l2_candidates:
                    l2_candidates.sort(key=lambda x: x[1], reverse=True)
                    l2_parent = l2_candidates[0][0]
                    parent_id = name_to_id[l2_parent]
                    category = normalize_name(l2_parent)
                elif root_name in parents:
                    parent_id = root_id
                    category = "大语言模型"
                else:
                    found = False
                    for p in parents:
                        if p != root_name:
                            parent_id = name_to_id[p]
                            category = normalize_name(p)
                            found = True
                            break
                    if not found:
                        parent_id = root_id
                        category = "其他"
            else:
                parent_id = root_id
                category = "其他"
        
        result_nodes.append({
            "id": node_id,
            "name": name,
            "level": level,
            "parent_id": parent_id,
            "category": normalize_name(category) if category != "root" else "root",
            "wuxing": "水",
            "cognitive_depth": "L3",
            "position": {"x": n['x'], "y": n['y']}
        })
    
    return result_nodes, name_to_id, level2_names, child_counts

def build_edges(edges_raw, name_to_id, coord_map):
    result_edges = []
    seen = set()
    
    for e in edges_raw:
        src_name = find_node_by_coord(coord_map, e['x1'], e['y1'])
        tgt_name = find_node_by_coord(coord_map, e['x2'], e['y2'])
        
        if src_name and tgt_name and src_name in name_to_id and tgt_name in name_to_id:
            src_id = name_to_id[src_name]
            tgt_id = name_to_id[tgt_name]
            key = (src_id, tgt_id)
            if key not in seen:
                seen.add(key)
                result_edges.append({
                    "source_id": src_id,
                    "target_id": tgt_id,
                    "relation": "contains"
                })
    
    return result_edges

def main():
    print("=" * 60)
    print("构建 2026-08-07 知识树快照")
    print("=" * 60)
    
    print("\n[1/4] 加载浏览器日志数据...")
    data = load_log_data()
    raw_nodes = data['nodes']
    raw_edges = data['edges']
    print(f"  - 原始节点: {len(raw_nodes)}")
    print(f"  - 原始边: {len(raw_edges)}")
    
    print("\n[2/4] 构建节点层级 (已知分类名匹配)...")
    coord_map = build_coord_to_name(raw_nodes)
    nodes, name_to_id, level2_names, child_counts = build_hierarchy(raw_nodes, raw_edges)
    
    level_counts = {}
    for n in nodes:
        l = n['level']
        level_counts[l] = level_counts.get(l, 0) + 1
    print(f"  - Level 分布: {level_counts}")
    
    print(f"\n  Level 2 分类节点 ({len(level2_names)} 个):")
    for name in sorted(level2_names, key=lambda n: child_counts.get(n, 0), reverse=True):
        norm = normalize_name(name)
        print(f"    [{child_counts.get(name, 0):3d} children] {name} -> {norm}")
    
    print("\n[3/4] 转换边格式...")
    edges = build_edges(raw_edges, name_to_id, coord_map)
    print(f"  - 有效边: {len(edges)}")
    
    print("\n[4/4] 组装快照...")
    tz = timezone(timedelta(hours=8))
    snapshot = {
        "collect_time": datetime.now(tz).isoformat(),
        "source": "https://hub.baai.ac.cn/knowledge-tree/graph",
        "method": "Browser automation (SVG extraction)",
        "nodes": nodes,
        "edges": edges
    }
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)
    
    print(f"\n快照已保存: {OUTPUT_FILE}")
    print(f"  - 节点: {len(nodes)}")
    print(f"  - 边: {len(edges)}")
    
    print("\n验证:")
    print(f"  - 根节点: {nodes[0]['name']} (id={nodes[0]['id']})")
    l2_nodes = [n for n in nodes if n['level'] == 2]
    print(f"  - Level 2 节点: {len(l2_nodes)}")
    l3_nodes = [n for n in nodes if n['level'] == 3]
    print(f"  - Level 3 节点: {len(l3_nodes)}")
    
    cat_counts = {}
    for n in l3_nodes:
        cat = n['category']
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    print(f"\n  各分类下 Level 3 节点数:")
    for cat, count in sorted(cat_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"    {cat}: {count}")
    
    print("\n完成!")

if __name__ == '__main__':
    main()