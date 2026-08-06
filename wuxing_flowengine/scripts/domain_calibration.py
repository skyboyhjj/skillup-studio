"""
领域基准校准器 — 跨领域 S 值归一化 (V1.2 Ch6)

Ch6 核心论点: 不同领域的 S 值不可直接比较，需建立领域基准。
校准流程:
  1. 收集多月份各领域的基础统计 (mean_S, std_S, wuxing 分布)
  2. 计算校准因子: baseline_S = mean(领域 S 值)
  3. 归一化: S_calibrated = S_raw / baseline_S
  4. 输出领域校准表，供跨领域诊断使用

用法:
    from domain_calibration import DomainCalibrator
    cal = DomainCalibrator(base_dir)
    cal.build_baseline()
    S_cal = cal.calibrate('大语言模型', S_raw=0.12)
"""

import json
import os
import math
from collections import defaultdict, Counter
from dao_math import compute_S_p, S_P_DEFAULT

WX_ORDER = ['木', '火', '土', '金', '水']
DOMAIN_ORDER = [
    '大语言模型', '具身智能与机器人', '多模态智能', '智能体',
    '生成式AI', '机器学习基础', '安全可信与伦理', '计算机视觉',
    '交叉领域智能应用', '推荐系统与信息检索', 'AI系统与硬件',
    '软件工程与编程', '科学AI', '知识表示与逻辑推理'
]


class DomainCalibrator:
    """领域基准校准器"""

    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.archive_base = os.path.join(base_dir, 'output', 'archive')
        self.baseline = {}        # {domain: {mean_S, std_S, ...}}
        self.wuxing_baseline = {} # {domain: {wx: mean_pct, ...}}
        self.calibration_cache = {}

    def _load_month_data(self, month_label):
        """加载单月诊断数据"""
        diag_path = os.path.join(
            self.archive_base, month_label,
            f'phase1_diagnosis_{month_label}.json'
        )
        cls_path = os.path.join(
            self.archive_base, month_label,
            f'wuxing_classification_{month_label}.json'
        )

        if not os.path.exists(diag_path) or not os.path.exists(cls_path):
            return None

        with open(diag_path, 'r', encoding='utf-8') as f:
            diag = json.load(f)
        with open(cls_path, 'r', encoding='utf-8') as f:
            classification = json.load(f)

        return {'diag': diag, 'classification': classification}

    def _compute_domain_S(self, classification, four_dims):
        """
        为每个领域计算独立的 S 值

        S_domain = compute_S_p([O_t_domain, E_u_domain, C_k_domain, K_y_domain], p=S_P_DEFAULT)
        其中各维度基于该领域内的节点计算
        """
        # 按领域分组节点
        domain_nodes = defaultdict(list)
        for c in classification:
            cat = c.get('category', 'root')
            if cat == 'root':
                continue
            domain_nodes[cat].append(c)

        domain_S = {}
        for domain, nodes in domain_nodes.items():
            wc = Counter()
            for n in nodes:
                wc[n.get('wuxing', '土')] += 1
            total = len(nodes)

            w = {}
            for wx in WX_ORDER:
                w[wx] = wc.get(wx, 0) / total if total > 0 else 0

            # 领域 O_t: 基于五行分布均匀度
            entropy = 0
            for wx in WX_ORDER:
                p = w[wx]
                if p > 0:
                    entropy -= p * math.log(p)
            max_entropy = math.log(5)
            O_t_d = entropy / max_entropy if max_entropy > 0 else 0

            # 领域 E_u: 基于节点数量归一化
            E_u_d = min(1.0, total / 30)

            # 领域 C_k: 基于主导行集中度
            dominant_pct = max(w.values()) if w else 0
            C_k_d = 1 - dominant_pct  # 越集中越不清晰

            # 领域 K_y: 简化版，基于五行交互
            K_y_d = w.get('火', 0) * 0.4 + w.get('土', 0) * 0.3 + 0.3 * 0.3

            S_d = compute_S_p([O_t_d, E_u_d, C_k_d, K_y_d], p=S_P_DEFAULT)
            domain_S[domain] = {
                'S': round(S_d, 4),
                'node_count': total,
                'wuxing': dict(wc),
                'O_t': round(O_t_d, 4),
                'E_u': round(E_u_d, 4),
                'C_k': round(C_k_d, 4),
                'K_y': round(K_y_d, 4),
                'dominant_wx': max(wc, key=wc.get) if wc else '土'
            }

        return domain_S

    def build_baseline(self):
        """
        构建领域基准

        遍历所有归档月份，计算每个领域的:
        - mean_S: 平均 S 值
        - std_S: S 值标准差
        - node_count_avg: 平均节点数
        - wuxing_profile: 平均五行分布
        - sample_count: 样本月份数
        """
        # 收集各月数据
        monthly_domain_S = defaultdict(list)
        monthly_domain_wx = defaultdict(list)
        monthly_domain_count = defaultdict(list)

        if not os.path.exists(self.archive_base):
            print(f'  归档目录不存在: {self.archive_base}')
            return False

        months = sorted(os.listdir(self.archive_base))
        print(f'  发现 {len(months)} 个归档月份: {months}')

        for month in months:
            month_path = os.path.join(self.archive_base, month)
            if not os.path.isdir(month_path):
                continue

            data = self._load_month_data(month)
            if data is None:
                print(f'  跳过 {month}: 数据不完整')
                continue

            domain_S = self._compute_domain_S(
                data['classification'],
                data['diag'].get('four_dims', {})
            )

            for domain, info in domain_S.items():
                monthly_domain_S[domain].append(info['S'])
                monthly_domain_wx[domain].append(info['wuxing'])
                monthly_domain_count[domain].append(info['node_count'])

            print(f'  {month}: {len(domain_S)} 个领域')

        # 计算基准
        for domain in sorted(monthly_domain_S.keys()):
            S_values = monthly_domain_S[domain]
            if not S_values:
                continue

            mean_S = sum(S_values) / len(S_values)
            std_S = math.sqrt(
                sum((s - mean_S) ** 2 for s in S_values) / len(S_values)
            ) if len(S_values) > 1 else 0.0

            # 聚合五行分布
            wx_agg = defaultdict(list)
            for wx_dist in monthly_domain_wx[domain]:
                for wx, count in wx_dist.items():
                    wx_agg[wx].append(count)
            wx_profile = {}
            for wx, counts in wx_agg.items():
                wx_profile[wx] = round(sum(counts) / len(counts), 1) if counts else 0

            self.baseline[domain] = {
                'mean_S': round(mean_S, 4),
                'std_S': round(std_S, 4),
                'node_count_avg': round(
                    sum(monthly_domain_count[domain]) / len(monthly_domain_count[domain]), 1
                ),
                'wuxing_profile': wx_profile,
                'sample_count': len(S_values),
                'S_range': [round(min(S_values), 4), round(max(S_values), 4)]
            }

        print(f'\n  基准构建完成: {len(self.baseline)} 个领域')
        return True

    def calibrate(self, domain, S_raw):
        """
        校准 S 值

        S_calibrated = S_raw / baseline_mean_S

        Args:
            domain: 领域名
            S_raw: 原始 S 值

        Returns:
            dict: {S_raw, S_calibrated, baseline_mean_S, calibration_factor, domain}
        """
        bl = self.baseline.get(domain)
        if bl is None or bl['mean_S'] == 0:
            return {
                'domain': domain,
                'S_raw': round(S_raw, 4),
                'S_calibrated': round(S_raw, 4),
                'baseline_mean_S': None,
                'calibration_factor': 1.0,
                'status': 'no_baseline'
            }

        baseline_mean = bl['mean_S']
        factor = 1.0 / baseline_mean
        S_cal = S_raw * factor

        return {
            'domain': domain,
            'S_raw': round(S_raw, 4),
            'S_calibrated': round(S_cal, 4),
            'baseline_mean_S': baseline_mean,
            'calibration_factor': round(factor, 4),
            'status': 'calibrated'
        }

    def calibrate_all_domains(self, domain_S_dict):
        """
        批量校准所有领域

        Args:
            domain_S_dict: {domain: S_raw, ...}

        Returns:
            dict: {domain: calibration_result, ...}
        """
        results = {}
        for domain, S_raw in domain_S_dict.items():
            results[domain] = self.calibrate(domain, S_raw)
        return results

    def get_calibration_table(self):
        """获取完整的校准表"""
        table = []
        for domain in DOMAIN_ORDER:
            bl = self.baseline.get(domain)
            if bl:
                table.append({
                    'domain': domain,
                    'mean_S': bl['mean_S'],
                    'std_S': bl['std_S'],
                    'sample_count': bl['sample_count'],
                    'node_count_avg': bl['node_count_avg'],
                    'dominant_wx': max(bl['wuxing_profile'], key=bl['wuxing_profile'].get)
                        if bl['wuxing_profile'] else '?'
                })
        return table

    def save_baseline(self, output_dir=None):
        """保存基准到文件"""
        if output_dir is None:
            output_dir = os.path.join(self.base_dir, 'output')

        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, 'domain_calibration_baseline.json')

        output = {
            'version': 'V1.2',
            'description': '领域基准校准表 (Ch6)',
            'baseline': self.baseline,
            'calibration_table': self.get_calibration_table()
        }

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f'  基准已保存: {path}')
        return path


def run(base_dir, output_dir=None):
    """领域基准校准主流程"""
    print('=' * 60)
    print('Phase C1: 领域基准校准 (Ch6)')
    print('=' * 60)

    cal = DomainCalibrator(base_dir)
    cal.build_baseline()

    # 输出校准表
    table = cal.get_calibration_table()
    print(f'\n  校准表 ({len(table)} 个领域):')
    print(f'  {"领域":<16} {"mean_S":>8} {"std_S":>8} {"样本":>5} {"节点均":>7} {"主导行":>5}')
    print(f'  {"-"*50}')
    for row in table:
        print(f'  {row["domain"]:<16} {row["mean_S"]:>8.4f} {row["std_S"]:>8.4f} '
              f'{row["sample_count"]:>5} {row["node_count_avg"]:>7.1f} {row["dominant_wx"]:>5}')

    # 保存
    cal.save_baseline(output_dir)
    return cal


if __name__ == '__main__':
    DEFAULT_BASE = r'E:\00-TRAEWK\6a59e217b55e181ea97f0df3\wuxing_flowengine'
    cal = run(DEFAULT_BASE)