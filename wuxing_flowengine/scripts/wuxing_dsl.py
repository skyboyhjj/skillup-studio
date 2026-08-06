"""
五行生克 DSL 引擎 — 从 spec 第十章伪代码 + 五阶段规则重建 (V1.2)

功能:
  1. 五行生克规则解析器 (生/克/化/通/变)
  2. 画像库加载与匹配 (附录 A)
  3. 规则优先级与冲突解决

DSL 语法:
  RULE <name>:
    WHEN <condition1> AND <condition2> ...
    THEN <stage> WITH <confidence>

用法:
    from wuxing_dsl import WuxingDSL
    dsl = WuxingDSL()
    dsl.load_profiles()
    stage, confidence = dsl.evaluate(freq, entropy, depth, edges)
"""

import json
import math
from collections import Counter

WX_ORDER = ['木', '火', '土', '金', '水']
SHENG = {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'}
KE = {'木': '土', '土': '水', '水': '火', '火': '金', '金': '木'}
SHENG_REVERSE = {v: k for k, v in SHENG.items()}  # 谁生我
KE_REVERSE = {v: k for k, v in KE.items()}        # 谁克我


# ── 附录 A: 画像库 ──
DEFAULT_PROFILES = {
    '生_初学者': {
        'stage': '生',
        'description': '初学者积累阶段，单一领域深入',
        'conditions': {
            'dominant_pct_min': 30,    # 主导行 > 30%
            'H_ratio_max': 0.50,       # 低熵聚焦
            'depth_L1_min': 1,         # 至少有一个 L1
            'depth_L4_max': 0,         # 无 L4
            'domain_count_max': 3      # 不超过 3 个领域
        },
        'priority': 1
    },
    '生_领域深耕': {
        'stage': '生',
        'description': '在特定领域内深耕，五行以主导行+相生行为主',
        'conditions': {
            'dominant_pct_min': 25,
            'H_ratio_max': 0.55,
            'sheng_chain_min': 2,      # 至少 2 个相生链
            'depth_L2_min': 3,
            'domain_count_max': 4
        },
        'priority': 2
    },
    '克_层间冲突': {
        'stage': '克',
        'description': '层间五行冲突，相克路径活跃',
        'conditions': {
            'ke_count_min': 1,         # 存在相克边
            'seed_dominant': 'any',    # 种子层主导行
            'current_dominant': 'any', # 现行层主导行
            'transcend_dominant': 'any' # 超越层主导行
        },
        'priority': 10
    },
    '克_领域张力': {
        'stage': '克',
        'description': '不同领域间的五行张力，主导行间存在相克关系',
        'conditions': {
            'ke_count_min': 2,
            'H_ratio_min': 0.40,
            'H_ratio_max': 0.70,
            'domain_count_min': 3
        },
        'priority': 11
    },
    '化_存在度跃迁': {
        'stage': '化',
        'description': '存在度 S 跨越临界阈值，四维同时跃迁',
        'conditions': {
            'S_min': 60,               # S > θ_critical
            'H_ratio_min': 0.30,
            'H_ratio_max': 0.60,
            'ke_count_min': 1,         # 经历过冲突
            'depth_L3_min': 2          # 有一定深度
        },
        'priority': 5
    },
    '化_动态突变': {
        'stage': '化',
        'description': '动态模式: ΔH 陡降 + 重心位移 > 阈值',
        'conditions': {
            'delta_H_min': 0.3,        # 熵下降
            'centroid_disp_min': 0.3,  # 重心位移
            'mode': 'dynamic'
        },
        'priority': 4
    },
    '通_均衡贯通': {
        'stage': '通',
        'description': '五行分布均衡，熵适中，路径匹配画像',
        'conditions': {
            'H_ratio_min': 0.50,
            'H_ratio_max': 0.85,
            'ke_count_max': 2,         # 冲突较少
            'depth_L3_min': 3,
            'domain_count_min': 3
        },
        'priority': 8
    },
    '通_时空直觉': {
        'stage': '通',
        'description': '经过克化后进入贯通，领域间知识迁移顺畅',
        'conditions': {
            'H_ratio_min': 0.55,
            'H_ratio_max': 0.80,
            'sheng_chain_min': 3,      # 相生链完整
            'depth_L4_min': 1,         # 有 L4 超越层
            'domain_count_min': 4
        },
        'priority': 9
    },
    '变_深度范式转换': {
        'stage': '变',
        'description': '动态模式: 认知深度跨越 1 级以上',
        'conditions': {
            'depth_shift_min': 1,      # 深度跃迁 ≥ 1 级
            'mode': 'dynamic'
        },
        'priority': 3
    },
    '变_范式升维': {
        'stage': '变',
        'description': '坐标系本身发生范式升维，L4 概念涌现',
        'conditions': {
            'depth_L4_min': 2,
            'H_ratio_min': 0.60,
            'H_ratio_max': 0.90,
            'ke_count_min': 1          # 经过了冲突
        },
        'priority': 6
    }
}


class WuxingDSL:
    """五行生克规则 DSL 引擎"""

    def __init__(self):
        self.profiles = {}
        self.rules = []
        self._load_builtin_rules()

    def _load_builtin_rules(self):
        """加载内置生克规则"""
        self.builtin_rules = {
            'sheng': {wx: SHENG[wx] for wx in WX_ORDER},
            'ke': {wx: KE[wx] for wx in WX_ORDER},
            'sheng_reverse': SHENG_REVERSE,
            'ke_reverse': KE_REVERSE,
            'sheng_chain': self._build_sheng_chain(),
            'ke_chain': self._build_ke_chain()
        }

    def _build_sheng_chain(self):
        """构建相生链: 木→火→土→金→水→木"""
        return [(wx, SHENG[wx]) for wx in WX_ORDER]

    def _build_ke_chain(self):
        """构建相克链: 木→土→水→火→金→木"""
        return [(wx, KE[wx]) for wx in WX_ORDER]

    def load_profiles(self, profiles=None):
        """加载画像库"""
        self.profiles = profiles or DEFAULT_PROFILES

    def load_profiles_from_file(self, path):
        """从 JSON 文件加载画像库"""
        with open(path, 'r', encoding='utf-8') as f:
            self.profiles = json.load(f)

    def sheng(self, wx):
        """相生: 谁生我"""
        return SHENG_REVERSE.get(wx)

    def ke(self, wx):
        """相克: 谁克我"""
        return KE_REVERSE.get(wx)

    def sheng_cycle(self, wx):
        """我生谁"""
        return SHENG.get(wx)

    def ke_cycle(self, wx):
        """我克谁"""
        return KE.get(wx)

    def find_sheng_chain(self, freq, min_len=2):
        """
        寻找相生链

        在五行频率分布中，检查是否存在连续相生的高频行。
        例如: 木→火→土 如果木/火/土 pct 都 > 15%
        """
        chains = []
        visited = set()

        for start_wx in WX_ORDER:
            if start_wx in visited:
                continue
            chain = [start_wx]
            current = start_wx
            while True:
                next_wx = SHENG.get(current)
                if next_wx is None or next_wx == start_wx:
                    break
                if freq.get(next_wx, {}).get('pct', 0) > 0.15:
                    chain.append(next_wx)
                    visited.add(next_wx)
                    current = next_wx
                else:
                    break
                if len(chain) > 5:
                    break
            if len(chain) >= min_len:
                chains.append(chain)

        return chains

    def find_ke_chain(self, freq, min_len=2):
        """
        寻找相克链
        """
        chains = []
        visited = set()

        for start_wx in WX_ORDER:
            if start_wx in visited:
                continue
            chain = [start_wx]
            current = start_wx
            while True:
                next_wx = KE.get(current)
                if next_wx is None or next_wx == start_wx:
                    break
                if freq.get(next_wx, {}).get('pct', 0) > 0.10:
                    chain.append(next_wx)
                    visited.add(next_wx)
                    current = next_wx
                else:
                    break
                if len(chain) > 5:
                    break
            if len(chain) >= min_len:
                chains.append(chain)

        return chains

    def _check_condition(self, condition, value, context):
        """检查单个条件"""
        if condition.endswith('_min'):
            key = condition[:-4]
            return context.get(key, 0) >= value
        elif condition.endswith('_max'):
            key = condition[:-4]
            return context.get(key, float('inf')) <= value
        return True

    def _match_profile(self, profile, context):
        """检查上下文是否匹配画像"""
        conditions = profile.get('conditions', {})
        for key, value in conditions.items():
            if key == 'mode':
                if context.get('mode') != value:
                    return False
            elif key == 'seed_dominant':
                if value != 'any' and context.get('seed_dominant') != value:
                    return False
            elif key == 'current_dominant':
                if value != 'any' and context.get('current_dominant') != value:
                    return False
            elif key == 'transcend_dominant':
                if value != 'any' and context.get('transcend_dominant') != value:
                    return False
            elif key.endswith('_min'):
                ctx_key = key[:-4]
                if context.get(ctx_key, 0) < value:
                    return False
            elif key.endswith('_max'):
                ctx_key = key[:-4]
                if context.get(ctx_key, float('inf')) > value:
                    return False
        return True

    def evaluate(self, freq, entropy_info, depth_info, edge_info, S=0,
                 mode='static', previous=None):
        """
        评估当前状态，返回最匹配的阶段

        Args:
            freq: dim1_freq, {wx: {pct: ..., count: ...}}
            entropy_info: {H: float, H_ratio: float}
            depth_info: {L1: int, L2: int, L3: int, L4: int}
            edge_info: {ke_count: int, sheng_count: int, ...}
            S: 存在度
            mode: 'static' | 'dynamic'
            previous: 上一快照数据 (动态模式)

        Returns:
            (stage: str, confidence: float, matched_profile: str, details: dict)
        """
        # 构建上下文
        dominant = max(freq, key=lambda k: freq[k]['pct'])
        dominant_pct = freq[dominant]['pct'] * 100

        context = {
            'dominant_pct': dominant_pct,
            'H_ratio': entropy_info.get('H_ratio', 0),
            'H': entropy_info.get('H', 0),
            'ke_count': edge_info.get('ke_count', 0),
            'sheng_count': edge_info.get('sheng_count', 0),
            'sheng_chain': edge_info.get('sheng_chain', 0),
            'depth_L1': depth_info.get('L1', 0),
            'depth_L2': depth_info.get('L2', 0),
            'depth_L3': depth_info.get('L3', 0),
            'depth_L4': depth_info.get('L4', 0),
            'domain_count': edge_info.get('domain_count', 1),
            'S': S,
            'mode': mode,
            'dominant': dominant,
            'seed_dominant': depth_info.get('seed_dominant', ''),
            'current_dominant': depth_info.get('current_dominant', ''),
            'transcend_dominant': depth_info.get('transcend_dominant', '')
        }

        # 动态模式: 添加 delta 信息
        if mode == 'dynamic' and previous:
            context['delta_H'] = previous.get('H', 0) - context['H']
            context['centroid_disp'] = previous.get('centroid_disp', 0)
            context['depth_shift'] = previous.get('depth_shift', 0)

        # 匹配画像库
        matches = []
        for name, profile in self.profiles.items():
            if self._match_profile(profile, context):
                matches.append((name, profile))

        if not matches:
            # 默认回退: 生
            return '生', 0.5, 'default_fallback', {
                'reason': '未匹配任何画像，默认回归积累',
                'context': context
            }

        # 按优先级排序 (数字越小优先级越高)
        matches.sort(key=lambda x: x[1].get('priority', 99))

        # 计算置信度: 基于匹配的画像数量
        best_name, best_profile = matches[0]
        confidence = min(1.0, 0.5 + 0.5 / len(matches))

        # 冲突检测: 如果多个不同阶段匹配，报告冲突
        stages = set(m[1]['stage'] for m in matches)
        conflict = len(stages) > 1

        details = {
            'reason': best_profile['description'],
            'matched_profiles': [m[0] for m in matches[:3]],
            'conflict': conflict,
            'conflicting_stages': list(stages) if conflict else [],
            'context': context
        }

        return best_profile['stage'], round(confidence, 4), best_name, details

    def evaluate_from_diagnosis(self, wuxing_result, S=0, mode='static',
                                  previous=None):
        """从完整诊断结果评估"""
        freq = wuxing_result['dim1_freq']
        layers = wuxing_result['dim2_layers']
        path_edges = wuxing_result['dim3_edges']

        # 熵
        H = 0.0
        for wx in WX_ORDER:
            p = freq.get(wx, {}).get('pct', 0)
            if p > 0:
                H -= p * math.log2(p)
        H_max = math.log2(5)
        H_ratio = H / H_max if H_max > 0 else 0

        # 深度分布
        depth_info = {
            'L1': layers.get('种子层', {}).get('count', 0),
            'L2': layers.get('现行层', {}).get('count', 0),
            'L3': layers.get('超越层', {}).get('count', 0),
            'L4': 0
        }

        # 主导行
        for layer_name in ['种子层', '现行层', '超越层']:
            layer_wx = layers.get(layer_name, {}).get('wuxing', {})
            if layer_wx:
                dominant = max(layer_wx, key=layer_wx.get)
                if layer_name == '种子层':
                    depth_info['seed_dominant'] = dominant
                elif layer_name == '现行层':
                    depth_info['current_dominant'] = dominant
                else:
                    depth_info['transcend_dominant'] = dominant

        # 边信息
        ke_count = sum(1 for p in path_edges if p.get('type') == '相克')
        sheng_count = sum(1 for p in path_edges if p.get('type') == '相生')
        sheng_chain = len(self.find_sheng_chain(freq))

        edge_info = {
            'ke_count': ke_count,
            'sheng_count': sheng_count,
            'sheng_chain': sheng_chain,
            'domain_count': 5  # 默认
        }

        return self.evaluate(
            freq, {'H': H, 'H_ratio': H_ratio},
            depth_info, edge_info, S, mode, previous
        )

    def explain(self, stage):
        """解释阶段含义"""
        explanations = {
            '生': {
                'title': '积累期',
                'meaning': '知识体系在单一领域扎根，五行由主导行牵引，熵低聚焦',
                'risk': '视野窄化，单极偏向',
                'path': '关注其他行的萌芽，为"克"冲突做好准备'
            },
            '克': {
                'title': '冲突期',
                'meaning': '不同领域/层级的五行张力显现，相克路径活跃',
                'risk': '长期僵持导致结构僵化',
                'path': '以通为贵，在冲突中寻找突破点'
            },
            '化': {
                'title': '跃迁期',
                'meaning': '临界突破，四维同时跃迁，存在度跨越阈值',
                'risk': '跃迁后失序，新范式不稳定',
                'path': '把握窗口期，大胆推进范式转换'
            },
            '通': {
                'title': '贯通期',
                'meaning': '时空直觉从源域迁移到目标域，五行分布均衡',
                'risk': '过早固化，通道关闭',
                'path': '保持熵适中，在多元与聚焦间平衡'
            },
            '变': {
                'title': '升维期',
                'meaning': '坐标系本身发生范式升维，认知深度跃迁',
                'risk': '暂时性认知失序，旧框架瓦解',
                'path': '拥抱不确定性，在新范式下重新进入"生"'
            }
        }
        return explanations.get(stage, {
            'title': '未知阶段',
            'meaning': '未定义',
            'risk': '未知',
            'path': '建议重新诊断'
        })

    def list_rules(self):
        """列出所有已加载的规则"""
        return [
            {
                'name': name,
                'stage': profile['stage'],
                'description': profile['description'],
                'priority': profile['priority']
            }
            for name, profile in self.profiles.items()
        ]


if __name__ == '__main__':
    import sys
    import os

    BASE = r'E:\00-TRAEWK\6a59e217b55e181ea97f0df3\wuxing_flowengine'
    sys.path.insert(0, BASE)
    sys.path.insert(0, os.path.join(BASE, 'diagnose'))

    from diagnose.wuxing_diagnose_v2 import diagnose

    # 测试 DSL
    dsl = WuxingDSL()
    dsl.load_profiles()

    print('=' * 60)
    print('  DSL 引擎测试')
    print('=' * 60)

    # 测试内置规则
    print(f'\n  内置生克规则:')
    print(f'  相生: {dsl.builtin_rules["sheng"]}')
    print(f'  相克: {dsl.builtin_rules["ke"]}')

    # 测试画像库
    print(f'\n  画像库: {len(dsl.profiles)} 个画像')
    rules = dsl.list_rules()
    for r in rules:
        print(f'    [{r["priority"]}] {r["name"]}: {r["stage"]} — {r["description"]}')

    # 测试评估
    rings = [
        {'label': '种子层', 'concepts': [
            {'name': 'n1', 'wuxing': '土'}, {'name': 'n2', 'wuxing': '金'},
            {'name': 'n3', 'wuxing': '土'}
        ]},
        {'label': '现行层', 'concepts': [
            {'name': 'n4', 'wuxing': '水'}, {'name': 'n5', 'wuxing': '水'},
            {'name': 'n6', 'wuxing': '木'}
        ]},
        {'label': '超越层', 'concepts': [
            {'name': 'n7', 'wuxing': '水'}, {'name': 'n8', 'wuxing': '木'}
        ]}
    ]
    result = diagnose(rings)
    stage, confidence, profile_name, details = dsl.evaluate_from_diagnosis(result, S=25)
    print(f'\n  评估结果:')
    print(f'    阶段: {stage} (置信度: {confidence})')
    print(f'    匹配画像: {profile_name}')
    print(f'    冲突: {details["conflict"]}')
    explanation = dsl.explain(stage)
    print(f'    解释: {explanation["title"]} — {explanation["meaning"]}')