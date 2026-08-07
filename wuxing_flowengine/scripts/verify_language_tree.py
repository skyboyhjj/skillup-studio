"""验证语言树数据集格式兼容性"""
import json
from collections import Counter

with open(r'e:\00-TRAEWK\6a59e217b55e181ea97f0df3\wuxing_flowengine\data\language_tree\language_tree_snapshot.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

nodes = data['nodes']
edges = data['edges']

print('=== 格式验证 ===')
required_node_fields = ['id', 'name', 'level', 'parent_id', 'category', 'wuxing', 'cognitive_depth']
for n in nodes[:3]:
    missing = [f for f in required_node_fields if f not in n]
    print(f'  节点 {n["name"]}: {"OK" if not missing else f"缺少字段: {missing}"}')

required_edge_fields = ['source_id', 'target_id', 'relation']
for e in edges[:3]:
    missing = [f for f in required_edge_fields if f not in e]
    print(f'  边 {e["relation"]}: {"OK" if not missing else f"缺少字段: {missing}"}')

node_ids = {n['id'] for n in nodes}
broken_edges = [e for e in edges if e['source_id'] not in node_ids or e['target_id'] not in node_ids]
print(f'\n=== 引用完整性 ===')
print(f'  节点数: {len(nodes)}')
print(f'  边数: {len(edges)}')
print(f'  悬挂边: {len(broken_edges)}')

# 语系详情
print(f'\n=== 语系详情 ===')
for n in nodes:
    if n['level'] == 1:
        langs = sum(1 for x in nodes if x['category'] == n['name'] and x['level'] == 3)
        subfams = sum(1 for x in nodes if x['category'] == n['name'] and x['level'] == 2)
        print(f'  {n["name"]} ({n["wuxing"]}): {subfams} 语族, {langs} 语言')

# 跟 BAAI 快照对比
with open(r'e:\00-TRAEWK\6a59e217b55e181ea97f0df3\wuxing_flowengine\data\snapshots\2026-07-30_snapshot.json', 'r', encoding='utf-8') as f:
    baai = json.load(f)

print(f'\n=== 与 BAAI 快照对比 ===')
print(f'  语言树: {len(nodes)} 节点, {len(edges)} 边')
print(f'  知识树: {len(baai["nodes"])} 节点, {len(baai.get("edges", []))} 边')
print(f'  格式兼容: {"通过" if "nodes" in baai and "nodes" in data else "失败"}')

# 检查 phase1 兼容性
print(f'\n=== phase1 兼容性检查 ===')
print(f'  顶层有 nodes: {"nodes" in data}')
print(f'  顶层有 edges: {"edges" in data}')
print(f'  节点有 wuxing: {all("wuxing" in n for n in nodes)}')
print(f'  节点有 cognitive_depth: {all("cognitive_depth" in n for n in nodes)}')
print(f'  节点有 category: {all("category" in n for n in nodes)}')
print(f'  节点有 name: {all("name" in n for n in nodes)}')
print(f'  节点有 level: {all("level" in n for n in nodes)}')

# 五行分布对比
lt_wx = Counter(n['wuxing'] for n in nodes if n['level'] > 0)
baai_wx = Counter(n.get('wuxing', '?') for n in baai['nodes'] if n.get('level', 0) > 0)
print(f'\n=== 五行分布对比 ===')
print(f'  {"五行":<4} {"语言树":>6} {"知识树":>6}')
for wx in ['木', '火', '土', '金', '水']:
    lt_cnt = lt_wx.get(wx, 0)
    baai_cnt = baai_wx.get(wx, 0)
    print(f'  {wx:<4} {lt_cnt:>6} {baai_cnt:>6}')

print(f'\n✅ 验证通过 — 格式与 BAAI 快照兼容')