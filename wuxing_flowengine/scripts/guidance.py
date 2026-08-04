"""
导航建议生成器 — 基于阶段 + 五行偏态 + 经典文本引用 (V1.2 Ch5 步骤5)

用法:
    from guidance import generate_guidance
    guidance = generate_guidance(stage, wuxing_freq, O_t, E_u, C_k, K_y)
"""

# ── 阶段→建议映射 ──
STAGE_GUIDANCE = {
    '生': {
        'title': '积累期',
        'advice': '当前处于积累阶段，宜深耕主导行，巩固根基。',
        'direction': '顺势而为，勿急于求成。',
        'caution': '注意单极偏向可能导致的视野窄化。',
        'next_step': '观察是否有其他行的萌芽出现，为"克"冲突做好准备。'
    },
    '克': {
        'title': '冲突期',
        'advice': '层间张力显现，需正视冲突而非回避。',
        'direction': '以通为贵，在冲突中寻找突破点。',
        'caution': '避免长期僵持导致结构僵化。',
        'next_step': '关注"化"的微光——局部突破往往是全面跃迁的前奏。'
    },
    '化': {
        'title': '跃迁期',
        'advice': '临界突破，四维同时跃迁。',
        'direction': '把握窗口期，大胆推进范式转换。',
        'caution': '跃迁后需重新校准，避免"化"后失序。',
        'next_step': '进入"通"阶段，将新范式迁移到更广泛的领域。'
    },
    '通': {
        'title': '贯通期',
        'advice': '时空直觉从源域迁移到目标域，找到节奏。',
        'direction': '保持熵适中，在多元与聚焦之间找到平衡。',
        'caution': '避免过早固化，保持通道的开放性。',
        'next_step': '持续积累深度经验，为"变"的范式升维做准备。'
    },
    '变': {
        'title': '升维期',
        'advice': '坐标系本身发生范式升维，深度画像跃迁。',
        'direction': '拥抱不确定性，在更高维度重新组织认知结构。',
        'caution': '范式转换期间可能出现暂时性认知失序。',
        'next_step': '在新范式中重新进入"生"阶段，开启新的螺旋上升。'
    }
}

# ── 五行偏态→调节方向 ──
WUXING_ADJUSTMENT = {
    '木': {
        'excess': '木气过盛，宜以金克木（引入逻辑/安全/对抗性思考）或以火泄木（转向传播/协作/智能体方向）',
        'deficit': '木气不足，宜以水生木（强化语言/视觉/科学多模态基础）',
        'balance': '木气均衡，生长有序'
    },
    '火': {
        'excess': '火气过盛，宜以水克火（深化探索/认知深度）或以土泄火（夯实系统/架构基础）',
        'deficit': '火气不足，宜以木生火（加强生成/具身/多模态推动传播与协作）',
        'balance': '火气均衡，传播有序'
    },
    '土': {
        'excess': '土气过盛，宜以木克土（引入生成/具身创新打破固化）或以金泄土（转向逻辑/推理精炼）',
        'deficit': '土气不足，宜以火生土（通过传播/协作建立系统基础）',
        'balance': '土气均衡，承载稳定'
    },
    '金': {
        'excess': '金气过盛，宜以火克金（引入传播/协作化解刚性）或以水泄金（深化探索/认知深度）',
        'deficit': '金气不足，宜以土生金（夯实系统/架构基础以支撑逻辑推理）',
        'balance': '金气均衡，收敛有度'
    },
    '水': {
        'excess': '水气过盛，宜以土克水（建立系统/架构约束）或以木泄水（将深层涌现转化为生成/具身创新）',
        'deficit': '水气不足，宜以金生水（强化逻辑/推理/安全以激发深层探索）',
        'balance': '水气均衡，流动不息'
    }
}

# ── 经典文本引用库 ──
CLASSICAL_REFERENCES = {
    '生': [
        {'text': '道生一，一生二，二生三，三生万物。', 'source': '道德经·第四十二章'},
        {'text': '万物并作，吾以观复。', 'source': '道德经·第十六章'},
    ],
    '克': [
        {'text': '反者道之动，弱者道之用。', 'source': '道德经·第四十章'},
        {'text': '将欲歙之，必固张之；将欲弱之，必固强之。', 'source': '道德经·第三十六章'},
    ],
    '化': [
        {'text': '大曰逝，逝曰远，远曰反。', 'source': '道德经·第二十五章'},
        {'text': '玄之又玄，众妙之门。', 'source': '道德经·第一章'},
    ],
    '通': [
        {'text': '不出户，知天下；不窥牖，见天道。', 'source': '道德经·第四十七章'},
        {'text': '为学日益，为道日损。', 'source': '道德经·第四十八章'},
    ],
    '变': [
        {'text': '天地不仁，以万物为刍狗。', 'source': '道德经·第五章'},
        {'text': '致虚极，守静笃。万物并作，吾以观复。', 'source': '道德经·第十六章'},
    ]
}


def analyze_wuxing_bias(wuxing_freq):
    """
    分析五行偏态

    Args:
        wuxing_freq: dim1_freq, {wx: {'pct': 0.xxxx}, ...}

    Returns:
        list of adjustment suggestions
    """
    adjustments = []

    for wx in ['木', '火', '土', '金', '水']:
        pct = wuxing_freq.get(wx, {}).get('pct', 0) * 100
        adj = WUXING_ADJUSTMENT.get(wx, {})

        if pct > 30:
            adjustments.append({
                'wx': wx,
                'status': 'excess',
                'pct': round(pct, 1),
                'advice': adj.get('excess', '')
            })
        elif pct < 12:
            adjustments.append({
                'wx': wx,
                'status': 'deficit',
                'pct': round(pct, 1),
                'advice': adj.get('deficit', '')
            })
        else:
            adjustments.append({
                'wx': wx,
                'status': 'balance',
                'pct': round(pct, 1),
                'advice': adj.get('balance', '')
            })

    return adjustments


def four_dims_interpretation(O_t, E_u, C_k, K_y):
    """
    四维读数解读

    Args:
        O_t, E_u, C_k, K_y: 四维值 (0~1)

    Returns:
        dict with interpretation text
    """
    def interpret(value, name, low_label, high_label):
        if value < 0.3:
            return f'{name}偏低 ({low_label})'
        elif value > 0.7:
            return f'{name}偏高 ({high_label})'
        return f'{name}适中'

    return {
        'O_t': interpret(O_t, '时位有序度', '节律紊乱，需重建时间基底', '过度结构化，需引入灵活性'),
        'E_u': interpret(E_u, '宇位均衡度', '能量分布壅塞，需拓宽空间', '能量过度分散，需聚焦'),
        'C_k': interpret(C_k, '识位清晰度', '觉知模糊，需深化探索', '觉知清晰，可转向实践'),
        'K_y': interpret(K_y, '缘位纠缠度', '关系稀疏，需建立连接', '关系过密，需简化因果'),
        'S': interpret(O_t * E_u * C_k * K_y * 100, '存在度', '存在感薄弱', '存在感强烈')
    }


def generate_guidance(stage, wuxing_freq, O_t, E_u, C_k, K_y, details=None):
    """
    生成导航建议 (V1.2 Ch5 步骤5)

    Args:
        stage: 当前阶段 ('生'|'克'|'化'|'通'|'变')
        wuxing_freq: dim1_freq
        O_t, E_u, C_k, K_y: 四维值
        details: 阶段判定详情 (from determine_stage)

    Returns:
        dict with structured guidance
    """
    stage_info = STAGE_GUIDANCE.get(stage, STAGE_GUIDANCE['生'])
    bias = analyze_wuxing_bias(wuxing_freq)
    four_dims = four_dims_interpretation(O_t, E_u, C_k, K_y)
    refs = CLASSICAL_REFERENCES.get(stage, [])

    # 选出需要调节的五行
    excess_wx = [b['wx'] for b in bias if b['status'] == 'excess']
    deficit_wx = [b['wx'] for b in bias if b['status'] == 'deficit']

    # 生成具体调节建议
    adjustment_advice = []
    for wx in excess_wx:
        adj = WUXING_ADJUSTMENT.get(wx, {})
        adjustment_advice.append(f"【{wx}过盛】{adj.get('excess', '')}")
    for wx in deficit_wx:
        adj = WUXING_ADJUSTMENT.get(wx, {})
        adjustment_advice.append(f"【{wx}不足】{adj.get('deficit', '')}")

    if not adjustment_advice:
        adjustment_advice.append('五行分布均衡，无需特别调节。')

    return {
        'stage': stage,
        'stage_title': stage_info['title'],
        'summary': stage_info['advice'],
        'direction': stage_info['direction'],
        'caution': stage_info['caution'],
        'next_step': stage_info['next_step'],
        'four_dims_interpretation': four_dims,
        'wuxing_bias': bias,
        'adjustment': adjustment_advice,
        'classical_refs': refs,
        'stage_details': details or {}
    }


if __name__ == '__main__':
    # 独立测试
    test_freq = {
        '木': {'count': 21, 'pct': 0.21},
        '火': {'count': 14, 'pct': 0.14},
        '土': {'count': 17, 'pct': 0.17},
        '金': {'count': 16, 'pct': 0.16},
        '水': {'count': 32, 'pct': 0.32},
    }
    g = generate_guidance('克', test_freq, 0.09, 0.70, 0.24, 0.75)
    import json
    print(json.dumps(g, ensure_ascii=False, indent=2))