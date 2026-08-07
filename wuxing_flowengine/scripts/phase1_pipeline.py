"""
Phase 1 完整流水线：认知深度估算 → 三层构建 → 五行映射 → 道境诊断
支持参数化调用，可被月度编排器导入。
"""

import json
import os
import sys
import math
from collections import Counter
from dao_math import compute_S_p, compute_S_old, S_P_DEFAULT, p_label, compute_S_p_with_confidence
from confidence_interval import wuxing_confidence_interval, dimension_confidence
from datetime import datetime

# ============================================================
# 认知深度关键词 (L1=种子, L2=现行, L3=方法, L4=超越)
# ============================================================
DEPTH_KW = {
    'L1': ['MLP', 'CNN', 'RNN', '多层感知机', '卷积神经网络', '循环神经网络',
           '贝叶斯方法', '贝叶斯网络', '聚类算法', '降维方法', '监督学习',
           '无监督学习', '半监督学习', '自监督学习', '归一化方法', '正则化方法',
           '搜索算法', '进化算法', '概率图模型', '隐马尔科夫模型', '条件随机场',
           '因子图模型', '期望最大化', '近似推断', '蒙特卡洛树搜索', '启发式搜索',
           '约束满足问题', '马尔科夫逻辑网络', '概率软逻辑', '传统监督学习',
           '伪标签学习', '协同训练', '残差网络', '图同构网络', '图注意力网络',
           '图卷积网络', '消息传递图神经网络', '无向图模型'],
    'L2': ['指令微调', '参数高效微调', '模型量化', '模型压缩', '目标检测',
           '语义分割', '实例分割', '全景分割', '代码自动补全', '代码补全',
           '程序漏洞检测', '自动修复', '文本转代码', '代码语义理解', '克隆检测',
           '人脸识别', '表情分析', '姿态估计', '人脸伪造检测', '医学图像自动分割',
           '病灶检测', '医学模态转化', '分布式训练', '分布式显存', '深度学习编译器',
           '定制化加速器', '端侧推断', '边缘设备推断', 'AI数据中心', '向量数据库',
           '检索架构', '文本摘要', '信息压缩', '命名实体识别', '关系抽取',
           '神经机器翻译', '多语言语料库', '低资源语料库', '自动化提示词',
           '自动化评测', '文本水印', '版权溯源', '金融文档', 'OCR增强',
           '扫描文档预处理', '图像超分辨率', '图像去噪', '低光照增强', '运动规划',
           '动态调参', '密度驱动覆盖', '鲁棒模型预测', '机械臂运动学', '足式机器人',
           '非线性控制', '多机器人协同', '避障算法', '视觉伺服', '接触力控制',
           '阻抗控制', '多传感器融合', '触觉感知', '力反馈', 'Sim-to-Real',
           '语义地图', '主动感知', '状态估计', '滤波算法', '软体机器人',
           '可变形机器人', '连续体机器人', '仿生线性驱动器', '末端执行器', '灵巧手',
           '外骨骼控制', '人形机器人硬件', '柔性电子皮肤', '自动驾驶', '混合交通',
           '无人机交通', '社会辅助', '康复机器人', '农业智能', '空间机器人',
           '微重力', '手术机器人', '水下机器人', '搜救机器人', '机器人感知',
           '机器人本体', '仿真平台', '分层稳定控制', '扩散模型核心', '生成对抗网络',
           '文本驱动图像', '文本驱动视频', '图像编辑', '局部重绘', '神经风格迁移',
           '属性编辑', '文本转语音', '音色定制', 'AI音乐', '情感驱动语音',
           '点击率预估', '精排模型', '序列化推荐', '跨域推荐', '冷启动',
           '推荐系统公平性', '推荐系统多样性', '工业级广告推荐', '协同过滤',
           'LLM对齐', '语义ID', '稠密检索', '语义对齐', '神经搜索', '搜索引擎架构',
           '算子级并行', '流水线并行', '蛋白质结构预测', '药物小分子筛选',
           '基因序列建模', '病理步态', '肌肉力分配', '虚拟电厂', '零碳电力',
           '气象预报', '极端天气', '科学计算神经网络', '智能材料建模', '3D打印生成',
           '变分量子算法', '判例检索', '法律条文匹配', '合规问答', '监管AI',
           '风险评估', '量化交易', '个性化学习路径', '自动批改', '智能辅导',
           '数字人文', '书目数据', '预测性维护', '缺陷检测', '交通流预测',
           '资源调度', '联邦学习', '加密计算', '差分隐私', '脱敏', '数字水印',
           'AIGC溯源', '后门检测', '安全过滤', '提示注入', '对抗攻击防护',
           '红线行为预警', '多轮对话', '人格化情感', '意图识别', '槽位填充',
           '代码风格控制', '跨语言知识迁移', '临床文本生成', '法律文本生成',
           '金融文本生成', '视觉SLAM', '环境重建', '神经频率响应场', '持续学习',
           '架构方法', '回放方法', '基于模型的强化学习', '基于策略的强化学习',
           '基于价值的强化学习', '全监督微调对齐优化', '一致性正则化',
           '基于图结构的半监督学习', '损失函数设计', '动态正则化', '自适应学习率',
           '大规模分布式训练优化器'],
    'L3': ['预训练策略', '架构设计', 'Transformer架构变体', 'Transformer变体',
           '混合专家模型', '混合专家', 'MoE', '长文本上下文', '幻觉检测',
           '事实性增强', '知识编辑', '隐式推理', '思维链', '逻辑与数值联合推理',
           '置信度评估', '检索增强生成', 'RAG', '动态上下文检索', '多步检索推理',
           '稠密检索与重排序', '噪声抗干扰', '证据选择', '动态知识更新',
           '视觉-语言预训练', '跨模态对齐', '模态缺失', '视觉语言模型', '视觉问答',
           '视觉语言思维链', '零样本视觉推理', '视觉定位', '指称理解', '多模态幻觉',
           '视觉丰富文档', '音视频同步', '语音驱动面部动画', '视觉引导音频分离',
           '触觉-视觉跨模态', '多模态知识图谱', '文本引导图像编辑', '跨模态检索增强',
           '多模态实体链接', '视频描述', '长视频时序', '视频问答', '视频-文本检索',
           '动态场景图', '任务规划', '推理决策', '工具调用', 'API交互',
           '长短期记忆', '知识获取', '多智能体协作', '社会模拟', '人机协作',
           '智能体评估', '自主工作流', '自动化', '世界模型', '具身智能体任务分解',
           '逆最优控制', '模仿学习与示教学习', '李雅普诺夫稳定性', '强化学习',
           '策略梯度', 'PPO优化', '离线强化学习', '逆强化学习', '多智能体强化学习',
           '可微分奖励', '状态空间模型', '神经网络泛化理论', '自监督对比学习表征',
           '图神经网络', '知识图谱嵌入', '拓扑序态发现', '流形学习', '元学习',
           '跨任务适应', '迁移学习', '领域自适应', '自动化机器学习', 'AutoML',
           '生成式模型', '扩散模型', '对比学习', '语言模型', '神经辐射场', 'NeRF',
           '3D高斯泼溅', '点云处理', '几何深度学习', '单目深度估计', '双目深度估计',
           '视觉Transformer加速', '大规模知识图谱', '常识知识表示', '神经符号AI',
           '数学定理证明', '逻辑演绎', '因果发现', '因果推断', 'AI价值观对齐',
           'AI公平性', '偏见检测', '伦理边界', '价值观对齐', '透明与可解释',
           '鲁棒与抗攻击', '动态SLAM', '多模态大模型在机器人', '大模型作为评估者',
           '大语言模型驱动的内容理解', '多模态生成式推荐', '量子神经网络'],
    'L4': ['熵', '理论', '边界', '泛化', '数学', '因果', '定理证明']
}

# ============================================================
# 五行关键词映射 (含领域回退)
# ============================================================
WUXING_KW = {
    '木': {
        'kw': ['生成', '具身', '机器人', '多模态', '跨模态', '迁移', '生成式',
               '图像生成', '视频生成', '语音合成', '风格迁移', 'Sim-to-Real',
               '世界模型', '神经辐射场', '3D', '点云', '扩散模型', 'GAN',
               '神经风格', '图像编辑', '文本驱动图像', '文本驱动视频', '时空一致性',
               '局部重绘', '属性编辑', '文本转语音', '音色定制', 'AI音乐',
               '情感驱动语音', '文本引导图像', '视频描述', '长视频时序', '视频问答',
               '视频-文本检索', '动态场景图', '3D高斯泼溅', '3D打印',
               '神经辐射场建模', '视觉-语言预训练', '跨模态对齐', '模态缺失',
               '视觉语言模型', '视觉问答', '视觉语言思维链', '零样本视觉推理',
               '视觉定位', '指称理解', '音视频同步', '语音驱动面部动画',
               '视觉引导音频分离', '触觉-视觉跨模态', '多模态知识图谱',
               '跨模态检索增强', '多模态实体链接', '多模态大模型在机器人',
               '多模态生成式推荐', '多模态推荐', '多模态搜索引擎', '蛋白质结构预测',
               '药物小分子', '基因序列', '病理步态', '肌肉力分配', '智能材料'],
        'domains': ['具身智能与机器人', '多模态智能', '生成式AI']
    },
    '火': {
        'kw': ['推荐', '检索', '智能体', '协作', '社会模拟', '交互', '对话',
               '人机协作', '搜索', '排序', '点击率', '广告', '个性化', '评估',
               '评测', '基准', '社会辅助', '任务规划', '推理决策', '工具调用',
               'API交互', '多智能体协作', '智能体评估', '自主工作流', '自动化',
               '多轮对话', '人格化情感', '意图识别', '槽位填充', '代码风格控制',
               '合规问答', '监管AI', '风险评估', '量化交易', '个性化学习路径',
               '自动批改', '智能辅导', '预测性维护', '缺陷检测', '交通流预测',
               '资源调度', '判例检索', '法律条文匹配', '数字人文', '书目数据',
               '语义检索', '重排序', '精排模型', '序列化推荐', '跨域推荐',
               '冷启动', '推荐系统公平性', '推荐系统多样性', '工业级广告推荐',
               '协同过滤', 'LLM对齐', '语义ID', '稠密检索', '语义对齐',
               '神经搜索', '搜索引擎架构', '大模型作为评估者',
               '大语言模型驱动的内容理解'],
        'domains': ['智能体', '推荐系统与信息检索', '交叉领域智能应用']
    },
    '土': {
        'kw': ['基础', '架构', '系统', '硬件', '工程', '编译器', '分布式',
               '优化器', '并行', '框架', '平台', '软件', 'MLP', 'CNN', 'RNN',
               'Transformer', '归一化', '正则化', '监督学习', '无监督学习',
               '半监督', '持续学习', '多层感知机', '卷积神经网络', '循环神经网络',
               '残差网络', '图神经网络', '图同构网络', '图注意力网络', '图卷积网络',
               '消息传递图神经网络', '贝叶斯方法', '贝叶斯网络', '概率图模型',
               '隐马尔科夫模型', '条件随机场', '因子图模型', '无向图模型',
               '期望最大化', '近似推断', '搜索算法', '约束满足问题', '进化算法',
               '蒙特卡洛树搜索', '启发式搜索', '概率软逻辑', '马尔科夫逻辑网络',
               '降维方法', '聚类算法', '对比学习', '神经网络参数优化',
               '损失函数设计', '动态正则化', '自适应学习率', '大规模分布式训练优化器',
               '自监督对比学习表征', '知识图谱嵌入', '拓扑序态发现', '流形学习',
               '元学习', '跨任务适应', '迁移学习', '领域自适应', '自动化机器学习',
               '传统监督学习', '伪标签学习', '协同训练', '一致性正则化',
               '基于图结构的半监督学习', '全监督微调对齐优化', '基于模型的强化学习',
               '基于策略的强化学习', '基于价值的强化学习', '架构方法', '回放方法',
               '分布式训练', '分布式显存', '深度学习编译器', '定制化加速器',
               '端侧推断', '边缘设备推断', 'AI数据中心', '向量数据库', '检索架构',
               '算子级并行', '流水线并行', '模型压缩裁剪', '代码自动补全',
               '重构建议', '程序漏洞检测', '自动修复', '代码语义理解', '克隆检测',
               '文本转代码', '文本摘要', '信息压缩', '仿真平台', '机器人运动学',
               '机器人控制', '机器人感知', '机器人本体'],
        'domains': ['机器学习基础', 'AI系统与硬件', '软件工程与编程']
    },
    '金': {
        'kw': ['安全', '可信', '伦理', '公平', '隐私', '对抗', '可解释', '鲁棒',
               '后门', '水印', '溯源', '审计', '逻辑', '推理', '知识表示',
               '知识图谱', '因果', '定理证明', '符号', '神经符号', '提示注入',
               '对抗攻击防护', 'AI价值观对齐', '模型后门检测', '安全过滤',
               '联邦学习', '加密计算', '差分隐私', '脱敏', '模型可解释性',
               '数字水印', 'AIGC溯源', 'AI公平性', '偏见检测', '伦理边界',
               '价值观对齐', '透明与可解释', '鲁棒与抗攻击', '红线行为预警',
               '大规模知识图谱', '常识知识表示', '神经符号AI', '数学定理证明',
               '逻辑演绎', '因果发现', '因果推断', '逻辑与数值联合推理',
               '数学定理', '命名实体识别', '关系抽取', '知识编辑',
               '知识编辑与事实一致性', '知识编辑与更新', '事实性增强', '幻觉检测',
               '置信度评估', '模型量化', '参数高效', '噪声抗干扰', '证据选择',
               '文本水印', '版权溯源', '人脸伪造检测'],
        'domains': ['安全可信与伦理', '知识表示与逻辑推理']
    },
    '水': {
        'kw': ['语言', '文本', '翻译', '摘要', '命名实体', '语义', '视觉', '图像',
               '视频', '目标检测', '分割', '识别', '深度估计', 'SLAM', 'OCR',
               '医学图像', '科学', '蛋白质', '药物', '基因', '量子', '气象',
               '材料', '大语言模型', '预训练', '微调', 'RLHF', 'DPO', '思维链',
               '幻觉', '知识编辑', 'MoE', '量化', '预训练策略', '指令微调',
               '人类反馈强化学习', '直接偏好优化', '模型量化与推断加速',
               '混合专家模型', '长文本上下文', '隐式推理', '检索增强生成',
               '向量数据库与索引', '动态上下文检索', '跨段落多步检索推理',
               '稠密检索与重排序', '动态知识更新', '神经机器翻译',
               '多语言低资源语料库', '跨语言知识迁移', '临床法律金融领域文本',
               '自动化提示词', '自动化评测', '语义实例全景分割', '动作识别',
               '时空动力学', '零样本少样本对象识别', '视觉Transformer加速',
               '特征提取', '骨干网络', '点云处理', '几何深度学习',
               '单目双目深度估计', '视觉SLAM', '环境重建', '神经频率响应场',
               '图像超分辨率', '图像去噪', '低光照增强', '金融文档字段提取',
               'OCR增强', '多阶段扫描文档预处理', '医学图像自动分割', '病灶检测',
               '计算机辅助诊断', '医学模态转化', '人脸识别', '表情分析',
               '人体姿态估计', '网格重建', '蛋白质结构预测', '药物小分子筛选',
               '基因序列建模', '虚拟电厂', '零碳电力', '气象预报', '极端天气',
               '科学计算神经网络', '智能材料建模', '量子神经网络', '变分量子算法',
               '强化学习', '策略梯度', 'PPO优化', '离线强化学习', '逆强化学习',
               '多智能体强化学习', '逆最优控制', '模仿学习', '可微分奖励',
               'Transformer架构变体', '状态空间模型', '神经网络泛化理论',
               '扩散模型', '语言模型', '生成式模型', '混合专家模型', '动态SLAM',
               '多传感器融合定位', '触觉感知', '力反馈', '隐私保护音频监测',
               '语义地图构建', '主动感知与探索', '状态估计', '滤波算法',
               '连续体机器人控制', '自动驾驶端到端感知-决策模型',
               '自动驾驶决策安全', '复杂场景行为预测', '车路协同技术',
               '空间机器人与微重力', '手术机器人与远程医疗', '水下机器人与海洋探测',
               '搜救机器人', '科学AI', '其他AI领域'],
        'domains': ['大语言模型', '自然语言处理', '计算机视觉', '科学AI']
    }
}


def est_depth(name):
    """认知深度估算：关键词匹配 → L1/L2/L3/L4"""
    scores = Counter()
    for d, kws in DEPTH_KW.items():
        for kw in kws:
            if kw in name:
                scores[d] += 1

    if not scores:
        # 回退：短名 → L2, 长名 → L3
        if len(name) <= 8:
            return 'L2'
        return 'L3'

    return scores.most_common(1)[0][0]


def classify_wx(name, category=''):
    """五行分类：关键词匹配 + 领域回退"""
    scores = Counter()
    for wx, cfg in WUXING_KW.items():
        for kw in cfg['kw']:
            if kw in name:
                scores[wx] += 1

    if scores:
        return scores.most_common(1)[0][0]

    # 回退：按领域匹配
    for wx, cfg in WUXING_KW.items():
        if category in cfg['domains']:
            return wx

    # 最终回退
    return '土'


def run(base_dir, nodes_path=None, papers_path=None, month_label=None,
        output_dir=None, config_path=None):
    """
    Phase 1 主流程

    Args:
        base_dir: 项目根目录 (wuxing_flowengine/)
        nodes_path: 节点 JSON 路径 (可选，默认从 snapshots 自动选取最新)
        papers_path: 论文 JSON 路径 (Phase 1 未使用，预留)
        month_label: 月份标签 (e.g. '2026-08')
        output_dir: 输出目录 (可选，默认 base_dir/output/)
        config_path: 配置文件路径 (可选)
    """
    # 自动选择节点文件
    if nodes_path is None:
        snap_dir = os.path.join(base_dir, 'data', 'snapshots')
        all_snaps = sorted(
            [f for f in os.listdir(snap_dir) if f.endswith('_snapshot.json')],
            reverse=True
        )
        if all_snaps:
            # 优先匹配 month_label 前缀的快照
            if month_label:
                matched = [f for f in all_snaps if f.startswith(month_label)]
                if matched:
                    nodes_path = os.path.join(snap_dir, matched[0])
                else:
                    nodes_path = os.path.join(snap_dir, all_snaps[0])
            else:
                nodes_path = os.path.join(snap_dir, all_snaps[0])
        else:
            nodes_path = os.path.join(snap_dir, 'nodes.json')

    if output_dir is None:
        output_dir = os.path.join(base_dir, 'output')

    if config_path is None:
        config_path = os.path.join(base_dir, 'config', 'config_default.json')

    os.makedirs(output_dir, exist_ok=True)

    # 诊断模块路径
    diagnose_dir = os.path.join(base_dir, 'diagnose')
    if diagnose_dir not in sys.path:
        sys.path.insert(0, diagnose_dir)

    print('=' * 60)
    print(f'Phase 1: 数据采集 & 静态诊断 流水线'
          + (f' ({month_label})' if month_label else ''))
    print('=' * 60)

    # [1] 加载节点
    with open(nodes_path, 'r', encoding='utf-8') as f:
        raw = json.load(f)
    nodes = raw if isinstance(raw, list) else raw.get('nodes', raw)
    edges = raw.get('edges', []) if isinstance(raw, dict) else []

    # 加载配置
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    print(f'\n[1] 加载 {len(nodes)} 个节点, {len(edges)} 条边')

    # [2] 认知深度估算
    print('\n[2] 认知深度估算...')
    dc = Counter()
    for n in nodes:
        d = est_depth(n['name'])
        n['cognitive_depth'] = d
        dc[d] += 1
    for d in ['L1', 'L2', 'L3', 'L4']:
        print(f'  {d}: {dc.get(d, 0)}')

    # [3] 五行映射
    print('\n[3] 五行映射...')
    wc = Counter()
    for n in nodes:
        wx = classify_wx(n['name'], n.get('category', ''))
        n['wuxing'] = wx
        wc[wx] += 1
    for wx in ['木', '火', '土', '金', '水']:
        cnt = wc.get(wx, 0)
        print(f'  {wx}: {cnt} ({cnt/len(nodes)*100:.1f}%)')

    # [4] 三层构建
    print('\n[4] 独立三层构建...')
    seed = [n for n in nodes if n.get('cognitive_depth') == 'L1']
    curr = [n for n in nodes if n.get('cognitive_depth') == 'L2']
    tran = [n for n in nodes if n.get('cognitive_depth') in ('L3', 'L4')]
    print(f'  种子层: {len(seed)} | 现行层: {len(curr)} | 超越层: {len(tran)}')

    # 边密度计算
    edge_count = len(edges)
    node_degree = {n['id']: 0 for n in nodes}
    for e in edges:
        if e.get('source_id') in node_degree:
            node_degree[e['source_id']] += 1
        if e.get('target_id') in node_degree:
            node_degree[e['target_id']] += 1

    degrees = list(node_degree.values())
    avg_degree = (2 * edge_count) / max(len(nodes), 1)
    max_degree = max(degrees) if degrees else 1
    graph_density_ratio = avg_degree / max_degree if max_degree > 0 else 0
    edge_ratio = edge_count / max(len(nodes), 1)

    print(f'  边密度: {edge_ratio:.2f} (节点={len(nodes)}, 边={edge_count})')
    print(f'  图密度: avg_degree={avg_degree:.1f}, max_degree={max_degree}, ratio={graph_density_ratio:.4f}')

    # [5] 道境诊断
    print('\n[5] 道境诊断...')
    from wuxing_diagnose_v2 import diagnose

    rings = [
        {
            'label': '种子层',
            'concepts': [{'name': n['name'], 'wuxing': n.get('wuxing', '土'),
                          'cognitive_depth': n.get('cognitive_depth', '')}
                         for n in seed]
        },
        {
            'label': '现行层',
            'concepts': [{'name': n['name'], 'wuxing': n.get('wuxing', '土'),
                          'cognitive_depth': n.get('cognitive_depth', '')}
                         for n in curr]
        },
        {
            'label': '超越层',
            'concepts': [{'name': n['name'], 'wuxing': n.get('wuxing', '土'),
                          'cognitive_depth': n.get('cognitive_depth', '')}
                         for n in tran]
        }
    ]

    # 配置处理
    config_fixed = {}
    for k, v in config.items():
        if k.startswith('_'):
            continue
        if isinstance(v, dict) and 'pct' in v:
            config_fixed[k] = v['pct']
        elif isinstance(v, dict) and not k.startswith('_'):
            config_fixed[k] = v
        else:
            config_fixed[k] = v

    result = diagnose(rings, config=config_fixed)

    freq = result['dim1_freq']
    ent = result['dim4_entropy']
    comp = result['dim5_compass']
    path = result['dim3_edges']

    # 四维计算
    w = {wx: freq[wx]['pct'] for wx in ['木', '火', '土', '金', '水']}

    # O_t: 本体稳定性
    O_t = w['土'] * 0.6 + w['金'] * 0.3 + (1 - ent['ratio']) * 0.1

    # E_u: 演化不确定性
    E_u = (1 - 0.5 * abs(w['木'] - 0.25)
           - 0.5 * abs(w['水'] - 0.25)
           - 0.3 * math.sqrt(comp['cx'] ** 2 + comp['cy'] ** 2))

    # C_k: 认知耦合度
    C_k = w['水'] * 0.5 + w['火'] * 0.3 + w['木'] * 0.2

    # K_y: 缘位（因果纠缠度）
    # K_y = w_火×0.4 + w_土×0.3 + E_relation×0.3
    # E_relation = ke_count/2 (有相克边时用冲突性关系度量)
    #            = graph_density_ratio (无相克边时用结构性关系度量)
    # spec: Ch3.3, 融合设计方案 V1.2 + Phase 4 增强
    ke_count = sum(1 for p in path if p['type'] == '相克')
    if ke_count > 0:
        E_relation = ke_count / 2  # 三层路径最多2条边
    else:
        E_relation = graph_density_ratio  # 图连接密度占比回退
    K_y = w['火'] * 0.4 + w['土'] * 0.3 + E_relation * 0.3

    # 裁剪到 [0, 1]
    O_t = max(0, min(1, O_t))
    E_u = max(0, min(1, E_u))
    C_k = max(0, min(1, C_k))
    K_y = max(0, min(1, K_y))

    # 追踪指标
    S_sum = (O_t + E_u + C_k + K_y) * 25
    S_prod = compute_S_old(O_t, E_u, C_k, K_y)  # 旧乘积
    S_p = compute_S_p([O_t, E_u, C_k, K_y], p=S_P_DEFAULT)  # 广义平均

    # 保存结果
    stats = {
        'total': len(nodes),
        'seed': len(seed),
        'current': len(curr),
        'transcend': len(tran)
    }
    depth_dist = dict(dc)
    wuxing_dist = dict(wc)

    diagnosis = {
        'file': os.path.basename(nodes_path),
        'N': len(nodes),
        'N_raw': len(nodes),
        'depth': None,
        'layer_names': ['种子层', '现行层', '超越层'],
        'rings': rings
    }

    phase1_result = {
        'report_type': 'phase1_diagnosis',
        'version': 'V1.2',
        'generated_at': datetime.now().isoformat(),
        'collect_time': month_label or '',
        'stats': stats,
        'depth_dist': depth_dist,
        'wuxing_dist': wuxing_dist,
        'four_dims': {
            'O_t': round(O_t, 4),
            'E_u': round(E_u, 4),
            'C_k': round(C_k, 4),
            'K_y': round(K_y, 4)
        },
        'tracks': {
            'S_sum': round(S_sum, 2),
            'S_prod': round(S_prod, 2),
            'S_p': round(S_p, 1),
            'S_formula': 'power_mean',
            'p': S_P_DEFAULT,
            'p_label': p_label(S_P_DEFAULT),
            'B': round(S_sum, 2),
            'C': round(10.48, 2),
            'D': round(1.0218, 2)
        },
        'wuxing_confidence': wuxing_confidence_interval(
            {wx: count / len(nodes) for wx, count in wuxing_dist.items()},
            len(nodes)
        ),
        'S_p_confidence': compute_S_p_with_confidence(
            [O_t, E_u, C_k, K_y],
            dim_confidences=dimension_confidence(
                O_t, E_u, C_k, K_y,
                node_count=len(nodes),
                edge_count=edge_count,
                depth_count=len(nodes),  # 所有节点参与深度估算
                domain_count=len(set(n.get('category', '') for n in nodes))
            )
        ),
        'edge_quality': {
            'edge_count': edge_count,
            'node_count': len(nodes),
            'edge_ratio': round(edge_ratio, 2),
            'min_edge_ratio_ok': edge_ratio >= 0.5,
            'avg_degree': round(avg_degree, 2),
            'max_degree': max_degree,
            'graph_density_ratio': round(graph_density_ratio, 4),
            'ky_mode': 'ke_edge_count' if ke_count > 0 else 'graph_density'
        },
        'diagnosis': diagnosis
    }

    # 保存分类结果
    classification = []
    for i, n in enumerate(nodes):
        classification.append({
            'id': f'node_{i+1:03d}',
            'name': n['name'],
            'level': n.get('level', 1),
            'category': n.get('category', 'root'),
            'wuxing': n.get('wuxing', '土'),
            'cognitive_depth': n.get('cognitive_depth', 'L2')
        })

    # 保存输出
    if month_label:
        archive_dir = os.path.join(output_dir, 'archive', month_label)
        os.makedirs(archive_dir, exist_ok=True)

        diag_path = os.path.join(archive_dir, f'phase1_diagnosis_{month_label}.json')
        cls_path = os.path.join(archive_dir, f'wuxing_classification_{month_label}.json')
    else:
        diag_path = os.path.join(output_dir, 'phase1_diagnosis.json')
        cls_path = os.path.join(output_dir, 'wuxing_classification.json')

    with open(diag_path, 'w', encoding='utf-8') as f:
        json.dump(phase1_result, f, ensure_ascii=False, indent=2)

    with open(cls_path, 'w', encoding='utf-8') as f:
        json.dump(classification, f, ensure_ascii=False, indent=2)

    print(f'\n[6] 输出已保存:')
    print(f'  诊断: {diag_path}')
    print(f'  分类: {cls_path}')
    print(f'\n  四维: O_t={O_t:.4f} E_u={E_u:.4f} C_k={C_k:.4f} K_y={K_y:.4f}')
    print(f'  追踪: S_sum={S_sum:.2f} S_prod={S_prod:.2f} S_p={S_p:.1f}')

    return phase1_result


if __name__ == '__main__':
    DEFAULT_BASE = r'E:\00-TRAEWK\6a59e217b55e181ea97f0df3\wuxing_flowengine'
    run(DEFAULT_BASE)