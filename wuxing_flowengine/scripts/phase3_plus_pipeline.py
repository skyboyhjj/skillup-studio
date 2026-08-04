"""
Phase 3+ 完整流水线：论文五行分类 → 领域对比 → 时间序列追踪
"""

import json
import os
import math
from collections import Counter, defaultdict
from datetime import datetime

# 论文五行关键词
PAPER_WUXING_KEYWORDS = {
    '大语言模型': {'kw': ['语言模型', 'LLM', 'GPT', '大模型', '预训练', '微调', 'RLHF', 'DPO', '对齐', '幻觉', 'MoE', '长文本', '推理', '思维链', '检索增强', 'RAG', '知识编辑', '提示词', 'Transformer']},
    '自然语言处理': {'kw': ['语言', '文本', '翻译', '摘要', '命名实体', '语义', '句法', '词法', '语料', '多语言', '机器翻译', '情感', '对话', '问答', '阅读理解', '信息抽取', '关系抽取', '事件抽取', '指代消解', '文本分类', '文本聚类', '文本生成', '摘要生成', '复述', '文本蕴含', '共指消解']},
    '具身智能与机器人': {'kw': ['机器人', '具身', '机械臂', '自动驾驶', 'SLAM', '运动规划', '控制', 'Sim-to-Real', '抓取', '导航', '操作', '仿生', '外骨骼', '人形']},
    '多模态智能': {'kw': ['多模态', '视觉语言', '跨模态', '视频理解', '图像生成', '文本到图像', '视觉问答', 'VQA', '音视频', '融合', '对齐', '视觉']},
    '智能体': {'kw': ['智能体', 'Agent', '多智能体', '协作', '规划', '工具调用', '自主', '工作流', '自动化', 'ReAct', 'Tool Use']},
    '生成式 AI': {'kw': ['生成', '扩散模型', 'GAN', '变分自编码器', 'VAE', '生成式', '图像生成', '视频生成', '文本生成', '合成', '神经辐射场', 'NeRF', '3D生成']},
    '机器学习基础': {'kw': ['机器学习', '深度学习', '神经网络', '优化', '损失函数', '正则化', '梯度', '分类', '回归', '聚类', '降维', '特征工程', '集成学习', '元学习', '迁移学习', '自监督', '对比学习', '图神经网络', 'GNN']},
    '安全、可信与伦理': {'kw': ['安全', '隐私', '公平', '伦理', '可解释', '鲁棒', '对抗', '攻击', '后门', '水印', '审计', '透明', '偏见', '联邦学习', '差分隐私', '信任', '可靠性']},
    '计算机视觉': {'kw': ['视觉', '图像', '视频', '目标检测', '分割', '识别', '深度估计', 'OCR', '人脸', '姿态', '目标跟踪', '超分辨率', '去噪', '增强', '复原', '医学图像']},
    '交叉领域智能应用': {'kw': ['法律', '金融', '医疗', '教育', '交通', '农业', '制造', '能源', '数学', '物理', '化学', '生物', '药物', '基因', '蛋白质', '气象', '材料', '量子']},
    '推荐系统与信息检索': {'kw': ['推荐', '检索', '搜索', '排序', '点击率', '广告', '信息', '个性化', '协同过滤', '内容过滤', '语义搜索', '向量检索']},
    'AI 系统与硬件': {'kw': ['分布式', '训练', '推理', '加速', '编译器', 'GPU', 'TPU', 'NPU', '量化', '剪枝', '蒸馏', '部署', '边缘', '硬件', '芯片', '数据中心']},
    '软件工程与编程': {'kw': ['代码', '编程', '软件', '工程', '调试', '测试', '重构', '补全', '生成', '漏洞', '修复', '语义', '克隆', '文档', 'API']},
    '科学 AI': {'kw': ['科学', '物理', '化学', '生物', '医学', '药物', '蛋白质', '基因', '气象', '气候', '天文', '地理', '材料', '量子', '数学', '定理']},
    '知识表示与逻辑推理': {'kw': ['知识', '逻辑', '推理', '因果', '符号', '神经符号', '知识图谱', '本体', '语义网', '规则', '演绎', '归纳', '溯因', '常识', '定理证明', '形式化']},
    '其他AI领域': {'kw': []},
}

# 五元坐标
WX_COORDS = {
    '木': (1.0, 0.0),
    '火': (0.309, 0.951),
    '土': (-0.809, 0.588),
    '金': (-0.809, -0.588),
    '水': (0.309, -0.951),
}

# 论文关键词到领域快照的映射
PAPER_TO_SNAP = {
    '语言模型': '大语言模型', 'LLM': '大语言模型', '大模型': '大语言模型',
    '机器人': '具身智能与机器人', '具身': '具身智能与机器人',
    '多模态': '多模态智能', '视觉语言': '多模态智能',
    '智能体': '智能体', 'Agent': '智能体',
    '生成': '生成式AI', '扩散模型': '生成式AI',
    '安全': '安全可信与伦理', '隐私': '安全可信与伦理',
    '视觉': '计算机视觉', '图像': '计算机视觉',
    '推荐': '推荐系统与信息检索', '检索': '推荐系统与信息检索',
    '代码': '软件工程与编程', '编程': '软件工程与编程',
    '科学': '科学AI', '药物': '科学AI', '蛋白质': '科学AI',
}

DOMAIN_ORDER = [
    '大语言模型', '具身智能与机器人', '多模态智能', '智能体',
    '生成式AI', '机器学习基础', '安全可信与伦理', '计算机视觉',
    '交叉领域智能应用', '推荐系统与信息检索', 'AI系统与硬件',
    '软件工程与编程', '科学AI'
]


def classify_paper(paper):
    """
    论文领域分类
    优先使用 BAAI Hub 采集时分配的 domain 字段
    回退到关键词匹配
    """
    # 优先使用内置 domain 字段
    domain = paper.get('domain', '')
    if domain and domain in PAPER_WUXING_KEYWORDS:
        return domain

    # 回退：关键词匹配
    title = paper.get('title', '')
    summary = paper.get('summary', '')
    text = (title + ' ' + summary).lower()
    scores = Counter()
    for dom, cfg in PAPER_WUXING_KEYWORDS.items():
        for kw in cfg['kw']:
            if kw.lower() in text:
                scores[dom] += 1

    if not scores:
        return '其他AI领域'

    return scores.most_common(1)[0][0]


def run(base_dir, papers_path=None, phase2_path=None, output_dir=None,
        month_label=None):
    """
    Phase 3+ 主流程

    Args:
        base_dir: 项目根目录
        papers_path: 论文 JSON 路径
        phase2_path: Phase 2 输出路径
        output_dir: 输出目录
        month_label: 月份标签
    """
    if output_dir is None:
        output_dir = os.path.join(base_dir, 'output')

    if month_label:
        archive_dir = os.path.join(output_dir, 'archive', month_label)
    else:
        archive_dir = output_dir

    if papers_path is None:
        papers_path = os.path.join(output_dir, f'papers_{month_label}.json')

    if phase2_path is None:
        phase2_path = os.path.join(archive_dir, f'phase2_diagnosis_{month_label}.json')

    print('=' * 60)
    print(f'Phase 3+: 论文五行分类 & 领域对比'
          + (f' ({month_label})' if month_label else ''))
    print('=' * 60)

    # 加载论文
    papers = []
    if os.path.exists(papers_path):
        with open(papers_path, 'r', encoding='utf-8') as f:
            papers = json.load(f)
        print(f'\n[1] 加载 {len(papers)} 篇论文')
    else:
        print(f'\n[1] 论文文件不存在: {papers_path}')
        papers = []

    # 加载 Phase 2 输出
    node_data = {}
    if os.path.exists(phase2_path):
        with open(phase2_path, 'r', encoding='utf-8') as f:
            node_data = json.load(f)

    # 论文分类
    paper_domains = Counter()
    for p in papers:
        domain = classify_paper(p)
        paper_domains[domain] += 1

    print(f'[2] 论文领域分布:')
    for domain in sorted(paper_domains.keys()):
        print(f'  {domain}: {paper_domains[domain]} 篇')

    # 领域对比：使用 Phase 2 的 domain_tracks 节点数据
    domains = {}
    domain_tracks = node_data.get('domain_tracks', {})

    for domain in sorted(set(list(domain_tracks.keys()) + list(paper_domains.keys()))):
        domain_node = domain_tracks.get(domain, {})
        node_wx = domain_node.get('wuxing', {})
        node_count = domain_node.get('node_count', 0)
        paper_count = paper_domains.get(domain, 0)

        # 计算论文五行分布（基于论文标题关键词）
        domain_papers = [p for p in papers if classify_paper(p) == domain]
        paper_wx_dist = Counter()
        for p in domain_papers:
            title = p.get('title', '').lower()
            for wx, cfg in {'木': ['生成', '具身', '机器人', '多模态', '跨模态', '迁移', '扩散', 'GAN', 'NeRF', '3D'],
                            '火': ['推荐', '检索', '智能体', 'Agent', '协作', '交互', '对话', '搜索', '排序'],
                            '土': ['基础', '架构', '系统', '硬件', '工程', '编译器', '分布式', '训练', '优化'],
                            '金': ['安全', '可信', '伦理', '公平', '隐私', '对抗', '可解释', '鲁棒', '逻辑', '推理', '因果'],
                            '水': ['语言', '文本', '翻译', '视觉', '图像', '视频', '目标检测', '分割', '识别', '预训练', '微调', 'LLM']}.items():
                for kw in cfg:
                    if kw.lower() in title:
                        paper_wx_dist[wx] += 1

        # 归一化
        total_node = sum(node_wx.values()) or 1
        total_paper = sum(paper_wx_dist.values()) or 1
        node_wx_pct = {wx: round(node_wx.get(wx, 0) / total_node, 4) for wx in ['木', '火', '土', '金', '水']}
        paper_wx_pct = {wx: round(paper_wx_dist.get(wx, 0) / total_paper, 4) for wx in ['木', '火', '土', '金', '水']}

        # 漂移幅度：节点与论文五行分布的余弦距离
        dot = sum(node_wx_pct[wx] * paper_wx_pct[wx] for wx in ['木', '火', '土', '金', '水'])
        norm_n = math.sqrt(sum(v**2 for v in node_wx_pct.values()))
        norm_p = math.sqrt(sum(v**2 for v in paper_wx_pct.values()))
        drift = round(1 - dot / (norm_n * norm_p + 1e-10), 4)

        domains[domain] = {
            'node_count': node_count,
            'paper_count': paper_count,
            'node_wx': node_wx_pct,
            'paper_wx': paper_wx_pct,
            'comparison': {
                'drift': drift,
                'direction': '显著漂移' if drift > 0.4 else ('轻度漂移' if drift > 0.15 else '基本一致')
            }
        }

    # 构建输出
    output = {
        'report_type': 'phase3_plus_diagnosis',
        'version': 'V1.2',
        'generated_at': datetime.now().isoformat(),
        'phase': '3+',
        'month_label': month_label or '',
        'timestamp': month_label or '',
        'data_sources': {
            'snapshot': f'{month_label}_snapshot.json' if month_label else '',
            'paper_titles': f'papers_{month_label}.json' if month_label else '',
            'phase2': os.path.basename(phase2_path)
        },
        'domains': domains,
        'paper_domain_distribution': dict(paper_domains),
        'total_papers': len(papers)
    }

    # 保存
    diag_path = os.path.join(archive_dir, f'phase3_plus_diagnosis_{month_label}.json')
    with open(diag_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f'\n[3] 输出已保存: {diag_path}')
    print(f'  总论文: {len(papers)}')
    print(f'  涉及领域: {len(paper_domains)}')

    return output


if __name__ == '__main__':
    DEFAULT_BASE = r'C:\Users\hejij\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a59e217b55e181ea97f0df3\wuxing_flowengine'
    run(DEFAULT_BASE, month_label='2026-07')