"""测试语言树数据在 phase1 流水线中的运行"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from phase1_pipeline import run

base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
nodes_path = os.path.join(base, 'data', 'language_tree', 'language_tree_snapshot.json')

result = run(base, nodes_path=nodes_path, month_label='language_tree')

print('\n=== 语言树诊断结果 ===')
dims = result['four_dims']
print(f'  O_t (本体稳定性): {dims["O_t"]}')
print(f'  E_u (演化不确定性): {dims["E_u"]}')
print(f'  C_k (认知耦合度): {dims["C_k"]}')
print(f'  K_y (缘位/因果纠缠度): {dims["K_y"]}')
print(f'  S_p (道境指数): {result["tracks"]["S_p"]}')
print(f'  S_p 信度: {result["S_p_confidence"]}')
print(f'  五行信度: {result["wuxing_confidence"]}')

# 与知识树对比
import json
with open(os.path.join(base, 'output', 'archive', '2026-07', 'phase1_diagnosis_2026-07.json'), 'r', encoding='utf-8') as f:
    kt = json.load(f)
kt_dims = kt['four_dims']
# 旧版诊断文件可能没有 S_p，从四维计算
kt_sp = kt['tracks'].get('S_p')
if kt_sp is None and 'S_prod' in kt['tracks']:
    from dao_math import compute_S_p, S_P_DEFAULT
    kt_sp = compute_S_p([kt_dims['O_t'], kt_dims['E_u'], kt_dims['C_k'], kt_dims['K_y']], p=S_P_DEFAULT)

print(f'\n=== 知识树 (2026-07) 对比 ===')
print(f'  O_t: {kt_dims["O_t"]}')
print(f'  E_u: {kt_dims["E_u"]}')
print(f'  C_k: {kt_dims["C_k"]}')
print(f'  K_y: {kt_dims["K_y"]}')
print(f'  S_p: {kt_sp:.1f}' if kt_sp else '  S_p: (旧版文件无此字段)')

print(f'\n=== 跨域差异 ===')
for d in ['O_t', 'E_u', 'C_k', 'K_y']:
    diff = dims[d] - kt_dims[d]
    print(f'  {d}: Δ={diff:+.4f}')
if kt_sp:
    print(f'  S_p: Δ={result["tracks"]["S_p"] - kt_sp:+.1f}')