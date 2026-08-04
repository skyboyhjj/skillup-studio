import json, os

base = r'C:\Users\hejij\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a59e217b55e181ea97f0df3\wuxing_flowengine\data\snapshots'

# Load nodes.json
nodes_data = json.load(open(os.path.join(base, 'nodes.json'), 'r', encoding='utf-8'))
nodes = nodes_data['nodes']
edges = json.load(open(os.path.join(base, 'edges.json'), 'r', encoding='utf-8'))

# Count unique node IDs
edge_ids = set()
for e in edges:
    edge_ids.add(e['source_id'])
    edge_ids.add(e['target_id'])
node_ids = set(n['id'] for n in nodes)

print(f'nodes.json: {len(nodes)} nodes, {len(node_ids)} unique IDs')
print(f'edges.json: {len(edges)} edges, {len(edge_ids)} unique node IDs')
print(f'Node IDs in edges but NOT in nodes.json: {len(edge_ids - node_ids)}')
print(f'Node IDs in nodes.json but NOT in edges: {len(node_ids - edge_ids)}')

# Build combined snapshot
combined = {
    '_snapshot': '2026-08-04_combined',
    '_description': 'Combined from nodes.json (100 nodes) + edges.json (301 edges)',
    '_collect_time': '2026-08-04',
    'nodes': nodes,
    'edges': edges
}

output_path = os.path.join(base, '2026-08-04_combined_snapshot.json')
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(combined, f, ensure_ascii=False, indent=2)

print(f'\nCombined snapshot saved: {output_path}')
print(f'Total nodes: {len(nodes)}, Total edges: {len(edges)}')