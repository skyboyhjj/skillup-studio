#!/usr/bin/env python3
"""
五行八卦推理规则引擎 v1.0
- 基于加权关键词匹配推断五行属性
- 基于五行+卦德匹配推断八卦属性
- 支持领域覆盖（中医/佛学/儒学/道学/西方哲学/科技）
- 自我演化：记录用户修正，频率学习，定期生成 diff 报告
- 质量校验：五行分布均衡、八卦覆盖度、相生链连续

用法:
  from wuxing_engine import WuxingEngine
  engine = WuxingEngine(rules_path='rules/wuxing_bagua_rules.json', domain='default')
  wuxing = engine.infer_wuxing("概念名", "概念描述")
  bagua = engine.infer_bagua("概念名", "概念描述", wuxing)
  layer = engine.infer_layer("概念名", "概念描述")
  engine.record_correction("概念名", "火", "木", "修正原因")
  engine.export_rules_json()  # 导出嵌入 template.html 的规则
"""
import json
import os
import re
from pathlib import Path
from datetime import datetime
from collections import Counter

# ─── 五行相生顺序 ───
WUXING_ORDER = ['木', '火', '土', '金', '水']
WUXING_GENERATION = {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'}

# ─── 八卦与五行对应 ───
BAGUA_WUXING_MAP = {
    '☰乾': '金', '☱兑': '金',
    '☲离': '火',
    '☳震': '木', '☴巽': '木',
    '☵坎': '水',
    '☶艮': '土', '☷坤': '土'
}

ALL_BAGUA = ['☰乾', '☱兑', '☲离', '☳震', '☴巽', '☵坎', '☶艮', '☷坤']

# ─── 学习阈值 ───
FREQUENCY_THRESHOLD = 3  # 同一关键词被修正 ≥3 次指向同一五行时提升权重
DOMAIN_MIGRATION_THRESHOLD = 10  # 新领域出现 ≥10 条修正记录时生成草稿


class WuxingEngine:
    def __init__(self, rules_path=None, domain='default', corrections_path=None):
        """
        Args:
            rules_path: 规则库 JSON 路径
            domain: 知识领域 (default / chinese_medicine / buddhism / ...)
            corrections_path: 修正记录文件路径 (默认与 rules 同目录)
        """
        if rules_path is None:
            rules_path = Path(__file__).parent / 'rules' / 'wuxing_bagua_rules.json'
        self.rules_path = Path(rules_path)
        self.rules_dir = self.rules_path.parent
        self.domain = domain

        # 加载核心规则
        with open(self.rules_path, encoding='utf-8') as f:
            self.rules = json.load(f)

        # 加载领域覆盖
        if domain != 'default':
            self._load_domain_override(domain)

        # 加载修正记录
        if corrections_path is None:
            corrections_path = self.rules_dir / 'local_corrections.json'
        self.corrections_path = Path(corrections_path)
        self.corrections = self._load_corrections()

    # ─── 领域覆盖 ───

    def _load_domain_override(self, domain):
        domain_file = self.rules_dir / 'domains' / f'{domain}.json'
        if not domain_file.exists():
            print(f"⚠ 领域文件不存在: {domain_file}，使用默认规则")
            return

        with open(domain_file, encoding='utf-8') as f:
            override = json.load(f)

        ov = override.get('overrides', {})

        if 'wuxing' in ov:
            for wx in WUXING_ORDER:
                if wx in ov['wuxing']:
                    wx_ov = ov['wuxing'][wx]
                    base = self.rules['wuxing'][wx]
                    if 'keywords' in wx_ov:
                        base['keywords'] = list(set(base['keywords'] + wx_ov['keywords']))
                    if 'weight' in wx_ov:
                        base['weight'] = wx_ov['weight']
                    if 'fixed_mapping' in wx_ov:
                        if not hasattr(self, '_fixed_mapping'):
                            self._fixed_mapping = {}
                        for concept, mapped_wx in wx_ov['fixed_mapping'].items():
                            self._fixed_mapping[concept] = mapped_wx

        if 'bagua' in ov:
            for bg in ALL_BAGUA:
                if bg in ov['bagua']:
                    bg_ov = ov['bagua'][bg]
                    if 'keywords' in bg_ov:
                        base = self.rules['bagua'][bg]
                        if 'concept_types' in base:
                            base['concept_types'] = list(set(base['concept_types'] + bg_ov['keywords']))
                    if 'weight' in bg_ov:
                        base['weight'] = bg_ov['weight']

    def _load_corrections(self):
        if self.corrections_path.exists():
            with open(self.corrections_path, encoding='utf-8') as f:
                return json.load(f)
        return {
            'domain': self.domain,
            'history': [],
            'keyword_stats': {}
        }

    def _save_corrections(self):
        self.corrections_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.corrections_path, 'w', encoding='utf-8') as f:
            json.dump(self.corrections, f, ensure_ascii=False, indent=2)

    # ─── 核心推断：五行 ───

    def infer_wuxing(self, label, desc=''):
        text = (label + ' ' + desc).lower()
        scores = {wx: 0.0 for wx in WUXING_ORDER}

        if hasattr(self, '_fixed_mapping'):
            for concept, wx in self._fixed_mapping.items():
                if concept in label or concept in desc:
                    scores[wx] += 10.0

        for wx in WUXING_ORDER:
            wx_data = self.rules['wuxing'][wx]
            weight = wx_data.get('weight', 1.0)

            for kw in wx_data.get('keywords', []):
                if kw in label:
                    scores[wx] += 3.0 * weight
                if kw in desc:
                    scores[wx] += 1.0 * weight

            for kw in wx_data.get('en_keywords', []):
                kw_lower = kw.lower()
                if kw_lower in label.lower():
                    scores[wx] += 3.0 * weight
                if kw_lower in desc.lower():
                    scores[wx] += 1.0 * weight

            for ct in wx_data.get('concept_types', []):
                if ct in label:
                    scores[wx] += 2.0 * weight
                if ct in desc:
                    scores[wx] += 1.0 * weight

        for kw, stats in self.corrections.get('keyword_stats', {}).items():
            if kw.lower() in text:
                for wx, count in stats.items():
                    if count >= FREQUENCY_THRESHOLD and wx in scores:
                        scores[wx] += count * 0.5

        if all(v == 0 for v in scores.values()):
            return '土'

        return max(scores, key=scores.get)

    def infer_wuxing_with_scores(self, label, desc=''):
        text = (label + ' ' + desc).lower()
        scores = {wx: 0.0 for wx in WUXING_ORDER}

        if hasattr(self, '_fixed_mapping'):
            for concept, wx in self._fixed_mapping.items():
                if concept in label or concept in desc:
                    scores[wx] += 10.0

        for wx in WUXING_ORDER:
            wx_data = self.rules['wuxing'][wx]
            weight = wx_data.get('weight', 1.0)

            for kw in wx_data.get('keywords', []):
                if kw in label:
                    scores[wx] += 3.0 * weight
                if kw in desc:
                    scores[wx] += 1.0 * weight

            for kw in wx_data.get('en_keywords', []):
                if kw.lower() in label.lower():
                    scores[wx] += 3.0 * weight
                if kw.lower() in desc.lower():
                    scores[wx] += 1.0 * weight

            for ct in wx_data.get('concept_types', []):
                if ct in label:
                    scores[wx] += 2.0 * weight
                if ct in desc:
                    scores[wx] += 1.0 * weight

        for kw, stats in self.corrections.get('keyword_stats', {}).items():
            if kw.lower() in text:
                for wx, count in stats.items():
                    if count >= FREQUENCY_THRESHOLD and wx in scores:
                        scores[wx] += count * 0.5

        if all(v == 0 for v in scores.values()):
            scores['土'] = 0.1

        return max(scores, key=scores.get), scores

    # ─── 核心推断：八卦 ───

    def infer_bagua(self, label, desc='', wuxing=None):
        if wuxing is None:
            wuxing = self.infer_wuxing(label, desc)

        candidates = {bg: bg_data for bg, bg_data in self.rules['bagua'].items()
                      if bg_data.get('wuxing') == wuxing}

        if not candidates:
            return ALL_BAGUA[0]

        if len(candidates) == 1:
            return list(candidates.keys())[0]

        text = (label + ' ' + desc).lower()
        scores = {}
        for bg, bg_data in candidates.items():
            score = bg_data.get('weight', 1.0)
            for ct in bg_data.get('concept_types', []):
                if ct in label:
                    score += 3.0
                if ct in desc:
                    score += 1.0
            scores[bg] = score

        return max(scores, key=scores.get)

    # ─── 核心推断：层位 ───

    def infer_layer(self, label, desc=''):
        text = (label + ' ' + desc).lower()
        scores = {}

        for layer_key, layer_data in self.rules.get('layer_assignment', {}).items():
            score = layer_data.get('weight', 1.0)
            for indicator in layer_data.get('indicators', []):
                if indicator in label:
                    score += 3.0
                if indicator in desc:
                    score += 1.0
            scores[layer_key] = score

        if all(v == 0 for v in scores.values()):
            return 'middle'

        return max(scores, key=scores.get)

    # ─── 自我演化 ───

    def record_correction(self, concept, old_wuxing, new_wuxing, reason='', auto_learned=False):
        entry = {
            'concept': concept,
            'old_wuxing': old_wuxing,
            'new_wuxing': new_wuxing,
            'reason': reason,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'auto_learned': auto_learned
        }
        self.corrections.setdefault('history', []).append(entry)

        stats = self.corrections.setdefault('keyword_stats', {})
        for kw in self._tokenize(concept):
            kw_stats = stats.setdefault(kw, {})
            kw_stats[new_wuxing] = kw_stats.get(new_wuxing, 0) + 1

        self._save_corrections()

        if len(self.corrections['history']) >= DOMAIN_MIGRATION_THRESHOLD:
            self._generate_domain_draft()

        return entry

    def _tokenize(self, text):
        tokens = set()
        for n in [2, 3, 4]:
            for i in range(len(text) - n + 1):
                tokens.add(text[i:i+n])
        return tokens

    def _generate_domain_draft(self):
        draft = {
            'domain': self.domain,
            'description': f'自动生成领域覆盖（{len(self.corrections["history"])} 条修正记录）',
            'generated_at': datetime.utcnow().isoformat() + 'Z',
            'overrides': {'wuxing': {}}
        }

        for wx in WUXING_ORDER:
            keywords = []
            for kw, stats in self.corrections.get('keyword_stats', {}).items():
                if stats.get(wx, 0) >= FREQUENCY_THRESHOLD:
                    keywords.append(kw)
            if keywords:
                draft['overrides']['wuxing'][wx] = {
                    'keywords': keywords,
                    'weight': 1.1
                }

        draft_path = self.rules_dir / 'domains' / f'{self.domain}_draft.json'
        with open(draft_path, 'w', encoding='utf-8') as f:
            json.dump(draft, f, ensure_ascii=False, indent=2)
        print(f"📝 领域覆盖草稿已生成: {draft_path}")

    # ─── 质量校验 ───

    def validate_concepts(self, concepts, wuxing_map, bagua_map):
        issues = []
        adjustments = []

        wuxing_counts = Counter(wuxing_map.values())
        if len(wuxing_counts) < 3:
            issues.append(f"五行分布不均衡：仅覆盖 {len(wuxing_counts)}/5 种")

        bagua_counts = Counter(bagua_map.values())
        if len(bagua_counts) < 6:
            issues.append(f"八卦覆盖不足：仅覆盖 {len(bagua_counts)}/8 卦")

        gen_chain = 0
        wx_set = set(wuxing_map.values())
        for wx in wx_set:
            if wx in WUXING_GENERATION and WUXING_GENERATION[wx] in wx_set:
                gen_chain += 1
        if gen_chain < 2:
            issues.append(f"相生链不连续：仅 {gen_chain} 对相生关系")

        return {
            'passed': len(issues) == 0,
            'issues': issues,
            'adjustments': adjustments
        }

    # ─── 批量推断 ───

    def infer_all(self, concepts, auto_validate=True):
        wuxing_map = {}
        bagua_map = {}
        layer_map = {}

        for c in concepts:
            label = c.get('label', '')
            desc = c.get('desc', '')
            wx = self.infer_wuxing(label, desc)
            bg = self.infer_bagua(label, desc, wx)
            layer = self.infer_layer(label, desc)

            wuxing_map[label] = wx
            bagua_map[label] = bg
            layer_map[label] = layer

        result = {
            'wuxing_map': wuxing_map,
            'bagua_map': bagua_map,
            'layer_map': layer_map
        }

        if auto_validate:
            result['validation'] = self.validate_concepts(concepts, wuxing_map, bagua_map)

        return result

    # ─── 导出规则（供 template.html 嵌入） ───

    def export_rules_json(self, minified=True):
        export = {
            'wuxing': {},
            'bagua': self.rules.get('bagua', {}),
            'layer_assignment': self.rules.get('layer_assignment', {})
        }
        for wx in WUXING_ORDER:
            wx_data = self.rules['wuxing'][wx]
            export['wuxing'][wx] = {
                'keywords': wx_data.get('keywords', []),
                'en_keywords': wx_data.get('en_keywords', []),
                'concept_types': wx_data.get('concept_types', []),
                'weight': wx_data.get('weight', 1.0)
            }

        if self.corrections.get('keyword_stats'):
            export['learned_keywords'] = self.corrections['keyword_stats']

        if minified:
            return json.dumps(export, ensure_ascii=False, separators=(',', ':'))
        return json.dumps(export, ensure_ascii=False, indent=2)

    # ─── CLI ───

    @staticmethod
    def cli_infer(args):
        engine = WuxingEngine(rules_path=args.rules, domain=args.domain)
        wx = engine.infer_wuxing(args.label, args.desc or '')
        bg = engine.infer_bagua(args.label, args.desc or '', wx)
        layer = engine.infer_layer(args.label, args.desc or '')
        print(f"概念: {args.label}")
        print(f"  五行: {wx}  八卦: {bg}  层位: {layer}")

    @staticmethod
    def cli_export(args):
        engine = WuxingEngine(rules_path=args.rules, domain=args.domain)
        rules_json = engine.export_rules_json(minified=not args.pretty)
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(rules_json)
            print(f"✅ 规则已导出: {args.output}")
        else:
            print(rules_json)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='五行八卦推理规则引擎')
    sub = parser.add_subparsers(dest='command')

    p_infer = sub.add_parser('infer', help='推断单个概念')
    p_infer.add_argument('label', help='概念名称')
    p_infer.add_argument('--desc', default='', help='概念描述')
    p_infer.add_argument('--rules', default=None, help='规则库路径')
    p_infer.add_argument('--domain', default='default', help='知识领域')

    p_export = sub.add_parser('export', help='导出规则 JSON')
    p_export.add_argument('--output', '-o', default=None, help='输出文件')
    p_export.add_argument('--rules', default=None, help='规则库路径')
    p_export.add_argument('--domain', default='default', help='知识领域')
    p_export.add_argument('--pretty', action='store_true', help='格式化输出')

    args = parser.parse_args()

    if args.command == 'infer':
        WuxingEngine.cli_infer(args)
    elif args.command == 'export':
        WuxingEngine.cli_export(args)
    else:
        parser.print_help()