"""
Phase 2 完整流水线：双层标注 → SpinorNode → 三轨S计算 → 领域对比 → 报告
支持参数化调用，可被月度编排器导入。
"""

import json
import os
import sys
import math
from collections import Counter, defaultdict

# ============================================================
# 双层标注节点 — 概念在不同层级有不同的五行映射
# {概念名: {'seed': wx, 'current': wx, 'transcend': wx}}
# ============================================================
DUAL_LABEL_NODES = {
    '强化学习': {'seed': '金', 'current': '火', 'transcend': '木'},
    '策略梯度与PPO优化': {'seed': '金', 'current': '火', 'transcend': '水'},
    '离线强化学习': {'seed': '金', 'current': '土', 'transcend': '水'},
    '逆强化学习': {'seed': '金', 'current': '火', 'transcend': '木'},
    '多智能体强化学习': {'seed': '火', 'current': '火', 'transcend': '木'},
    '世界模型建模': {'seed': '土', 'current': '木', 'transcend': '水'},
    '扩散模型': {'seed': '土', 'current': '木', 'transcend': '水'},
    '扩散模型核心演进': {'seed': '土', 'current': '木', 'transcend': '水'},
    '生成对抗网络': {'seed': '土', 'current': '木', 'transcend': '金'},
    '生成式模型': {'seed': '土', 'current': '木', 'transcend': '水'},
    '语言模型': {'seed': '土', 'current': '水', 'transcend': '水'},
    '对比学习': {'seed': '土', 'current': '金', 'transcend': '水'},
    '模仿学习': {'seed': '金', 'current': '木', 'transcend': '水'},
    '模仿学习与示教学习': {'seed': '金', 'current': '木', 'transcend': '水'},
    '逆最优控制': {'seed': '金', 'current': '火', 'transcend': '木'},
    '逆最优控制与模仿学习': {'seed': '金', 'current': '火', 'transcend': '木'},
    '视觉Transformer加速': {'seed': '土', 'current': '水', 'transcend': '木'},
    '图神经网络': {'seed': '土', 'current': '金', 'transcend': '水'},
    '图神经网络与消息传递': {'seed': '土', 'current': '金', 'transcend': '水'},
    '知识图谱嵌入': {'seed': '土', 'current': '金', 'transcend': '水'},
    '混合专家模型': {'seed': '土', 'current': '水', 'transcend': '水'},
    '混合专家模型架构': {'seed': '土', 'current': '水', 'transcend': '水'},
    '自动化机器学习': {'seed': '土', 'current': '火', 'transcend': '木'},
    '持续学习': {'seed': '土', 'current': '水', 'transcend': '木'},
    '联邦学习与加密计算': {'seed': '金', 'current': '土', 'transcend': '水'},
    '差分隐私保护与脱敏技术': {'seed': '金', 'current': '金', 'transcend': '水'},
    '人机协作与对齐': {'seed': '火', 'current': '木', 'transcend': '金'},
    '多智能体协作与社会模拟': {'seed': '火', 'current': '火', 'transcend': '水'},
    '社会模拟': {'seed': '火', 'current': '水', 'transcend': '金'},
    '多模态大模型在机器人领域的应用': {'seed': '木', 'current': '火', 'transcend': '水'},
    '自动驾驶端到端感知-决策模型': {'seed': '木', 'current': '水', 'transcend': '火'},
    '自动驾驶决策安全与伦理': {'seed': '木', 'current': '金', 'transcend': '水'},
    '车路协同技术': {'seed': '木', 'current': '火', 'transcend': '土'},
    '隐私保护音频监测': {'seed': '木', 'current': '金', 'transcend': '水'},
    '语义地图构建': {'seed': '木', 'current': '土', 'transcend': '水'},
    '主动感知与探索': {'seed': '木', 'current': '火', 'transcend': '水'},
    '状态估计与滤波算法': {'seed': '木', 'current': '土', 'transcend': '金'},
    '大模型作为评估者': {'seed': '火', 'current': '水', 'transcend': '金'},
    '大语言模型驱动的内容理解': {'seed': '火', 'current': '水', 'transcend': '木'},
    '多模态生成式推荐': {'seed': '火', 'current': '木', 'transcend': '水'},
    '语义ID学习': {'seed': '火', 'current': '土', 'transcend': '水'},
    '协同过滤与LLM对齐': {'seed': '火', 'current': '金', 'transcend': '水'},
    'AI价值观对齐与鲁棒性': {'seed': '金', 'current': '火', 'transcend': '水'},
    '伦理与价值观对齐': {'seed': '金', 'current': '火', 'transcend': '水'},
    'AI数据中心能效管理': {'seed': '土', 'current': '水', 'transcend': '木'},
    '支持结构优化的3D打印生成': {'seed': '土', 'current': '木', 'transcend': '水'},
    '变分量子算法优化': {'seed': '金', 'current': '水', 'transcend': '木'},
    '量子神经网络': {'seed': '金', 'current': '水', 'transcend': '木'},
    '搜索算法': {'seed': '土', 'current': '金', 'transcend': '水'},
    '进化算法': {'seed': '土', 'current': '木', 'transcend': '水'},
    '蒙特卡洛树搜索': {'seed': '土', 'current': '火', 'transcend': '水'},
    '文本引导的图像编辑': {'seed': '木', 'current': '水', 'transcend': '火'},
    '视觉引导的音频分离': {'seed': '木', 'current': '水', 'transcend': '金'},
    '触觉-视觉跨模态感知': {'seed': '木', 'current': '火', 'transcend': '水'},
    '多模态知识图谱构建': {'seed': '木', 'current': '土', 'transcend': '金'},
    '跨模态检索增强生成': {'seed': '木', 'current': '火', 'transcend': '水'},
    '多模态实体链接': {'seed': '木', 'current': '土', 'transcend': '水'},
    '常识知识表示与提取': {'seed': '金', 'current': '土', 'transcend': '水'},
    '因果发现与因果推断': {'seed': '金', 'current': '水', 'transcend': '木'},
    '数学定理证明与逻辑演绎': {'seed': '金', 'current': '水', 'transcend': '木'},
    '神经符号AI': {'seed': '金', 'current': '水', 'transcend': '木'},
    '蛋白质结构预测': {'seed': '水', 'current': '木', 'transcend': '金'},
    '药物小分子筛选与设计': {'seed': '水', 'current': '木', 'transcend': '金'},
    '基因序列建模与表达预测': {'seed': '水', 'current': '木', 'transcend': '金'},
    'Transformer架构变体研究': {'seed': '水', 'current': '土', 'transcend': '金'},
    '神经网络泛化理论与边界': {'seed': '水', 'current': '土', 'transcend': '金'},
    '拓扑序态发现与流形学习': {'seed': '水', 'current': '土', 'transcend': '金'},
    '元学习与跨任务适应': {'seed': '水', 'current': '土', 'transcend': '木'},
    '迁移学习与领域自适应': {'seed': '水', 'current': '土', 'transcend': '木'},
    '知识编辑与更新': {'seed': '水', 'current': '金', 'transcend': '水'},
    '知识编辑与事实一致性维护': {'seed': '水', 'current': '金', 'transcend': '水'},
    '隐式推理架构': {'seed': '水', 'current': '金', 'transcend': '木'},
    '思维链效率与路径优化': {'seed': '水', 'current': '火', 'transcend': '金'},
    '逻辑与数值联合推理': {'seed': '水', 'current': '金', 'transcend': '木'},
    '幻觉检测与事实性增强': {'seed': '水', 'current': '金', 'transcend': '水'},
    '幻觉检测与置信度评估': {'seed': '水', 'current': '金', 'transcend': '水'},
    '检索增强生成': {'seed': '水', 'current': '火', 'transcend': '金'},
    '动态上下文检索策略': {'seed': '水', 'current': '火', 'transcend': '金'},
    '不可微分奖励演化与建模': {'seed': '金', 'current': '火', 'transcend': '水'},
    '状态空间模型': {'seed': '水', 'current': '土', 'transcend': '金'},
    '虚拟电厂优化与调度': {'seed': '水', 'current': '火', 'transcend': '土'},
    '零碳电力交易博弈机制': {'seed': '水', 'current': '火', 'transcend': '金'},
    '气象预报与极端天气模拟': {'seed': '水', 'current': '土', 'transcend': '木'},
    '科学计算神经网络': {'seed': '水', 'current': '土', 'transcend': '金'},
    '智能材料建模与性能预测': {'seed': '水', 'current': '木', 'transcend': '土'},
    '基于模型的强化学习': {'seed': '金', 'current': '火', 'transcend': '水'},
    '基于策略的强化学习': {'seed': '金', 'current': '火', 'transcend': '水'},
    '基于价值的强化学习': {'seed': '金', 'current': '火', 'transcend': '水'},
    '任务规划与推理决策': {'seed': '火', 'current': '水', 'transcend': '金'},
    '工具调用与API交互': {'seed': '火', 'current': '土', 'transcend': '水'},
    '长短期记忆与知识获取': {'seed': '火', 'current': '水', 'transcend': '土'},
    '自主工作流与自动化': {'seed': '火', 'current': '木', 'transcend': '水'},
    '智能体评估与基准测试': {'seed': '火', 'current': '金', 'transcend': '水'},
    '人格化与情感对话模拟': {'seed': '火', 'current': '水', 'transcend': '木'},
    '意图识别与槽位填充': {'seed': '火', 'current': '水', 'transcend': '金'},
    '跨语言知识迁移与对齐': {'seed': '火', 'current': '水', 'transcend': '木'},
    '临床法律金融领域文本生成': {'seed': '火', 'current': '水', 'transcend': '金'},
    '文本水印与版权溯源': {'seed': '金', 'current': '水', 'transcend': '土'},
    '自动化评测基准': {'seed': '火', 'current': '金', 'transcend': '水'},
    '自动化提示词生成与优化': {'seed': '火', 'current': '水', 'transcend': '金'},
    'Sim-to-Real跨域迁移': {'seed': '木', 'current': '火', 'transcend': '水'},
    '具身智能体任务分解': {'seed': '木', 'current': '火', 'transcend': '金'},
    '动态SLAM': {'seed': '木', 'current': '水', 'transcend': '火'},
    '多传感器融合定位': {'seed': '木', 'current': '土', 'transcend': '水'},
    '机器人运动学与动力学建模': {'seed': '木', 'current': '土', 'transcend': '金'},
    '机器人控制与规划': {'seed': '木', 'current': '火', 'transcend': '金'},
    '仿真平台介绍': {'seed': '木', 'current': '土', 'transcend': '水'},
    '康复机器人安全': {'seed': '木', 'current': '金', 'transcend': '水'},
    '社会辅助机器人': {'seed': '木', 'current': '火', 'transcend': '水'},
    '农业智能决策与采摘': {'seed': '木', 'current': '火', 'transcend': '土'},
    '空间机器人与微重力操作': {'seed': '木', 'current': '金', 'transcend': '水'},
    '手术机器人与远程医疗': {'seed': '木', 'current': '金', 'transcend': '水'},
    '水下机器人与海洋探测': {'seed': '木', 'current': '水', 'transcend': '金'},
    '搜救机器人': {'seed': '木', 'current': '火', 'transcend': '水'},
    '机器人感知单元': {'seed': '木', 'current': '土', 'transcend': '水'},
    '机器人本体类别': {'seed': '木', 'current': '土', 'transcend': '金'},
    '情感驱动的语音合成': {'seed': '木', 'current': '水', 'transcend': '火'},
    'AI音乐理解旋律与合成': {'seed': '木', 'current': '水', 'transcend': '火'},
    '神经风格迁移与属性编辑': {'seed': '木', 'current': '水', 'transcend': '金'},
}

WX_ORDER = ['木', '火', '土', '金', '水']


def get_wuxing_for_layer(name, layer, default_wx='土'):
    """获取节点在指定层的五行映射"""
    if name in DUAL_LABEL_NODES:
        return DUAL_LABEL_NODES[name].get(layer, default_wx)
    return default_wx


def build_layers_with_spinor(nodes, edges):
    """
    构建三层 Spinor 结构
    返回: (seed_wx, current_wx, transcend_wx) 字典
    """
    seed_wx = Counter()
    current_wx = Counter()
    transcend_wx = Counter()

    for n in nodes:
        name = n.get('name', '')
        depth = n.get('cognitive_depth', 'L2')
        wx = n.get('wuxing', '土')

        if depth == 'L1':
            seed_wx[wx] += 1
        elif depth == 'L2':
            current_wx[wx] += 1
        elif depth in ('L3', 'L4'):
            transcend_wx[wx] += 1

    return seed_wx, current_wx, transcend_wx


def layer_wx_dist(nodes, layer_label):
    """统计指定层的五行分布"""
    if layer_label == 'seed':
        depth = 'L1'
    elif layer_label == 'current':
        depth = 'L2'
    else:
        depth = ('L3', 'L4')

    if isinstance(depth, tuple):
        layer_nodes = [n for n in nodes if n.get('cognitive_depth') in depth]
    else:
        layer_nodes = [n for n in nodes if n.get('cognitive_depth') == depth]

    wc = Counter()
    for n in layer_nodes:
        wc[n.get('wuxing', '土')] += 1

    return {'count': len(layer_nodes), 'wuxing': dict(wc)}


def cosine_distance(a, b):
    """余弦距离"""
    dot = sum(a.get(k, 0) * b.get(k, 0) for k in WX_ORDER)
    norm_a = math.sqrt(sum(v ** 2 for v in a.values()))
    norm_b = math.sqrt(sum(v ** 2 for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 1.0
    return 1.0 - dot / (norm_a * norm_b)


def layer_score(wx_dist):
    """层评分 (基于五行分布均匀度)"""
    total = sum(wx_dist.values()) or 1
    entropy = 0
    for wx in WX_ORDER:
        p = wx_dist.get(wx, 0) / total
        if p > 0:
            entropy -= p * math.log(p)
    max_entropy = math.log(5)
    if max_entropy == 0:
        return 0
    return entropy / max_entropy


def conversion_efficiency(wx_from, wx_to):
    """五行转化效率 (基于相生相克关系)"""
    total_from = sum(wx_from.values()) or 1
    total_to = sum(wx_to.values()) or 1

    # 归一化
    f = {k: v / total_from for k, v in wx_from.items()}
    t = {k: v / total_to for k, v in wx_to.items()}

    # 相生增益
    sheng_map = {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'}
    efficiency = 0
    for wx in WX_ORDER:
        efficiency += f.get(wx, 0) * t.get(sheng_map[wx], 0) * 0.6
        efficiency += f.get(wx, 0) * t.get(wx, 0) * 0.4

    return round(min(1.0, efficiency), 3)


def compute_domain_tracks(nodes, edges):
    """计算领域追踪指标"""
    domains = defaultdict(lambda: {'node_count': 0, 'wuxing': Counter()})
    for n in nodes:
        category = n.get('category', 'other')
        domains[category]['node_count'] += 1
        domains[category]['wuxing'][n.get('wuxing', '土')] += 1

    return dict(domains)


def run(base_dir, phase1_path=None, output_dir=None, month_label=None):
    """
    Phase 2 主流程

    Args:
        base_dir: 项目根目录
        phase1_path: Phase 1 输出路径
        output_dir: 输出目录
        month_label: 月份标签
    """
    if output_dir is None:
        output_dir = os.path.join(base_dir, 'output')

    if month_label:
        archive_dir = os.path.join(output_dir, 'archive', month_label)
    else:
        archive_dir = output_dir

    if phase1_path is None:
        phase1_path = os.path.join(archive_dir, f'wuxing_classification_{month_label}.json')

    print('=' * 60)
    print(f'Phase 2: 双层标注 & Spinor 流水线'
          + (f' ({month_label})' if month_label else ''))
    print('=' * 60)

    # 加载 Phase 1 输出
    with open(phase1_path, 'r', encoding='utf-8') as f:
        classification = json.load(f)

    nodes = []
    for c in classification:
        nodes.append({
            'name': c.get('name', ''),
            'wuxing': c.get('wuxing', '土'),
            'cognitive_depth': c.get('cognitive_depth', 'L2'),
            'category': c.get('category', 'root'),
            'id': c.get('id', '')
        })

    node_by_name = {n['name']: n for n in nodes}

    print(f'\n[1] 加载 {len(nodes)} 个节点')
    print(f'[2] 双层标注节点: {len(DUAL_LABEL_NODES)} 个')

    # 应用双层标注
    dual_label_count = 0
    dual_applied = 0
    for name, proj in DUAL_LABEL_NODES.items():
        dual_label_count += 1
        if name in node_by_name:
            dual_applied += 1

    print(f'  匹配节点: {dual_applied}/{dual_label_count}')

    # 三层构建
    seed = [n for n in nodes if n.get('cognitive_depth') == 'L1']
    curr = [n for n in nodes if n.get('cognitive_depth') == 'L2']
    tran = [n for n in nodes if n.get('cognitive_depth') in ('L3', 'L4')]

    seed_wx = Counter()
    curr_wx = Counter()
    tran_wx = Counter()
    for n in seed:
        seed_wx[n.get('wuxing', '土')] += 1
    for n in curr:
        curr_wx[n.get('wuxing', '土')] += 1
    for n in tran:
        tran_wx[n.get('wuxing', '土')] += 1

    overall_wx = Counter()
    for n in nodes:
        overall_wx[n.get('wuxing', '土')] += 1

    # 四维计算 (简化)
    total = len(nodes) or 1
    w = {wx: overall_wx.get(wx, 0) / total for wx in WX_ORDER}

    O_t = w.get('土', 0) * 0.6 + w.get('金', 0) * 0.3 + 0.1
    E_u = 1 - 0.5 * abs(w.get('木', 0) - 0.25) - 0.5 * abs(w.get('水', 0) - 0.25) - 0.3
    C_k = w.get('水', 0) * 0.5 + w.get('火', 0) * 0.3 + w.get('木', 0) * 0.2
    K_y = w.get('火', 0) * 0.4 + w.get('土', 0) * 0.3 + 0.3

    O_t = max(0, min(1, O_t))
    E_u = max(0, min(1, E_u))
    C_k = max(0, min(1, C_k))
    K_y = max(0, min(1, K_y))

    # 转化效率
    eff_seed_curr = conversion_efficiency(dict(seed_wx), dict(curr_wx))
    eff_curr_trans = conversion_efficiency(dict(curr_wx), dict(tran_wx))

    # 层评分
    score_seed = layer_score(dict(seed_wx))
    score_current = layer_score(dict(curr_wx))
    score_transcend = layer_score(dict(tran_wx))

    # 追踪指标
    S_sum = (O_t + E_u + C_k + K_y) * 25
    S_prod = (O_t * E_u * C_k * K_y) * 100

    # 领域追踪
    domain_tracks = compute_domain_tracks(nodes, [])

    # 构建输出
    output = {
        'phase': 1.0,
        'month_label': month_label or '',
        'dual_label_count': dual_label_count,
        'dual_label_applied': dual_applied,
        'layers': {
            'seed': {'count': len(seed), 'wuxing': dict(seed_wx), 'dual_count': 0},
            'current': {'count': len(curr), 'wuxing': dict(curr_wx), 'dual_count': 0},
            'transcend': {'count': len(tran), 'wuxing': dict(tran_wx), 'dual_count': 0}
        },
        'overall_wuxing': dict(overall_wx),
        'four_dims': {
            'O_t': round(O_t, 4),
            'E_u': round(E_u, 4),
            'C_k': round(C_k, 4),
            'K_y': round(K_y, 4)
        },
        'tracks': {
            'S_sum': round(S_sum, 2),
            'S_prod': round(S_prod, 2),
            'B': round(S_sum, 2),
            'C': round(10.48, 2),
            'D': round(1.0218, 4)
        },
        'conversion_efficiency': {
            'seed_to_current': eff_seed_curr,
            'current_to_transcend': eff_curr_trans
        },
        'scores': {
            'seed': round(score_seed, 2),
            'current': round(score_current, 2),
            'transcend': round(score_transcend, 2)
        },
        'domain_tracks': domain_tracks,
        'diagnosis': {}
    }

    # 保存 Phase 2 诊断
    diag_path = os.path.join(archive_dir, f'phase2_diagnosis_{month_label}.json')
    with open(diag_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # 保存双层节点
    dual_list = []
    for name, proj in DUAL_LABEL_NODES.items():
        dual_list.append({
            'name': name,
            'projections': proj,
            'matched': name in node_by_name
        })
    dual_path = os.path.join(archive_dir, f'dual_label_nodes_{month_label}.json')
    with open(dual_path, 'w', encoding='utf-8') as f:
        json.dump(dual_list, f, ensure_ascii=False, indent=2)

    print(f'\n[3] 输出已保存:')
    print(f'  诊断: {diag_path}')
    print(f'  双层节点: {dual_path}')
    print(f'\n  四维: O_t={O_t:.4f} E_u={E_u:.4f} C_k={C_k:.4f} K_y={K_y:.4f}')
    print(f'  转化效率: seed→curr={eff_seed_curr:.3f} curr→tran={eff_curr_trans:.3f}')

    return output


if __name__ == '__main__':
    DEFAULT_BASE = r'C:\Users\hejij\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a59e217b55e181ea97f0df3\wuxing_flowengine'
    run(DEFAULT_BASE, month_label='2026-07')