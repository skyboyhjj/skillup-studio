#!/usr/bin/env python3
"""
莫比乌斯环概念地图生成脚本 v2.1
新增：五行八卦规则引擎集成 + 自动推断
用法:
  python3 build_mobius.py --data data.json --title "标题" --output 输出.html
  python3 build_mobius.py --data data.json --auto-wuxing daojism --output 输出.html
  python3 build_mobius.py --data data.json --auto-wuxing default --rules-output rules_export.json --output 输出.html

注：生成的 HTML 内置五阶音景（Web Audio API）和动画录制功能（桌面端MP4/移动端WebM），需通过 HTTP 服务器访问。
"""
import json, argparse, subprocess, re, sys, os, hashlib
from pathlib import Path

# 模板路径
TEMPLATE = Path(__file__).parent / 'template_v2.1.html'
RULES_DIR = Path(__file__).parent / 'rules'

# 默认五空配置
DEFAULT_EMPTINESS = {
    'sunyata': True, 'mirror': True, 'breath': True, 'wane': True, 'ascend': True,
    'mirrorRatio': 0.42, 'breathPeriod': 10000, 'breathAmplitude': 15,
    'fadeStart': 35000, 'fadeEnd': 50000, 'fadeTarget': 0.15, 'fadeRestore': 0.5,
    'ascendRatio': 0.2
}

# ─── 规则引擎路径 ───
ENGINE_PATH = Path(__file__).parent / 'wuxing_engine.py'


def esc_js(s):
    """转义字符串用于 JS 单引号"""
    return s.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n')


def concept_to_js(c):
    """单个概念 → JS对象字符串"""
    docs_str = json.dumps(c.get('docs', []), ensure_ascii=False)
    line = "{{ label: '{l}', desc: '{d}', docs: {docs} }}".format(
        l=esc_js(c['label']), d=esc_js(c.get('desc', '')), docs=docs_str)
    if c.get('wuxing'):
        line = line[:-2] + ", wuxing:'" + c['wuxing'] + "' }"
    if c.get('bagua'):
        line = line[:-2] + ", bagua:'" + c['bagua'] + "' }"
    return line


def build_rings_js(rings):
    """整个rings数据 → JS字符串"""
    lines = ['var DEFAULT_RINGS = [']
    for ri, r in enumerate(rings):
        lines.append('    {')
        lines.append("      label: '{l}', R: {R}, w: {w}, yOffset: {yO}, color: '{c}',".format(
            l=esc_js(r['label']),
            R=r.get('R', 150), w=r.get('w', 25), yO=r.get('yOffset', 0),
            c=r.get('color', '#4ECDC4')))
        lines.append('      concepts: [')
        for c in r.get('concepts', []):
            lines.append('        ' + concept_to_js(c) + ',')
        lines.append('      ]')
        lines.append('    }' + (',' if ri < len(rings) - 1 else ''))
    lines.append('  ];')
    return '\n'.join(lines)


def build_emptiness_js(emp):
    """EMPTINESS 配置 → JS字符串"""
    lines = ['  var EMPTINESS = {']
    items = list(emp.items())
    for i, (k, v) in enumerate(items):
        if isinstance(v, bool):
            lines.append('    {}: {}'.format(k, 'true' if v else 'false'))
        elif isinstance(v, (int, float)):
            lines.append('    {}: {}'.format(k, v))
        else:
            lines.append("    {}: '{}'".format(k, v))
        if i < len(items) - 1:
            lines[-1] += ','
    lines.append('  };')
    return '\n'.join(lines)


def auto_infer_wuxing(rings, rules_path, domain):
    """
    使用规则引擎自动推断五行+八卦
    如果概念已有 wuxing/bagua，则跳过
    """
    # 将引擎目录加入 sys.path
    engine_dir = str(Path(__file__).parent)
    if engine_dir not in sys.path:
        sys.path.insert(0, engine_dir)

    try:
        from wuxing_engine import WuxingEngine
        engine = WuxingEngine(rules_path=rules_path, domain=domain)
    except ImportError:
        print("⚠ 无法导入 wuxing_engine.py，请确保引擎文件在同一目录")
        return rings, {'wuxing_map': {}, 'bagua_map': {}, 'layer_map': {}, 'validation': {'passed': False, 'issues': ['引擎未加载']}}

    all_concepts = []
    for ring in rings:
        for c in ring.get('concepts', []):
            all_concepts.append(c)

    result = engine.infer_all(all_concepts, auto_validate=True)
    wuxing_map = result['wuxing_map']
    bagua_map = result['bagua_map']

    stats = {'inferred': 0, 'skipped': 0}
    for ring in rings:
        for c in ring.get('concepts', []):
            label = c.get('label', '')
            if not c.get('wuxing'):
                c['wuxing'] = wuxing_map.get(label, '土')
                stats['inferred'] += 1
            else:
                stats['skipped'] += 1

            if not c.get('bagua'):
                c['bagua'] = bagua_map.get(label, '☷坤')
            else:
                if not c.get('wuxing'):
                    stats['skipped'] += 1

    print(f"🎯 自动推断: {stats['inferred']} 个概念, 跳过 {stats['skipped']} 个（已有标注）")
    if result.get('validation') and not result['validation']['passed']:
        print(f"⚠ 质量校验未通过: {', '.join(result['validation']['issues'])}")

    return rings, result


def main():
    parser = argparse.ArgumentParser(description='莫比乌斯环概念地图生成器 v2.1')
    parser.add_argument('--data', required=True, help='概念数据 JSON 文件')
    parser.add_argument('--title', default='概念地图', help='页面标题')
    parser.add_argument('--output', default='output.html', help='输出 HTML 文件')
    parser.add_argument('--no-emptiness', action='store_true', help='关闭全部五空动画')
    parser.add_argument('--emptiness', default=None, help='自定义 emptiness JSON 字符串')
    parser.add_argument('--auto-wuxing', default=None, help='启用自动五行八卦推断（指定领域: default/daojism/buddhism/...）')
    parser.add_argument('--rules', default=None, help='指定规则库路径（默认 rules/wuxing_bagua_rules.json）')
    parser.add_argument('--rules-output', default=None, help='导出推断结果 JSON 供审查')
    args = parser.parse_args()

    with open(args.data, encoding='utf-8') as f:
        data = json.load(f)
    rings = data.get('rings', data if isinstance(data, list) else [])

    # ─── 自动五行八卦推断 ───
    if args.auto_wuxing:
        rules_path = args.rules or str(RULES_DIR / 'wuxing_bagua_rules.json')
        rings, infer_result = auto_infer_wuxing(rings, rules_path, args.auto_wuxing)

        # 导出推断结果
        if args.rules_output:
            export_data = {
                'domain': args.auto_wuxing,
                'rings': [
                    {
                        'label': r['label'],
                        'concepts': [
                            {'label': c['label'], 'wuxing': c.get('wuxing', ''), 'bagua': c.get('bagua', '')}
                            for c in r.get('concepts', [])
                        ]
                    }
                    for r in rings
                ],
                'validation': infer_result.get('validation', {})
            }
            with open(args.rules_output, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            print(f"📄 推断结果已导出: {args.rules_output}")

    # ─── 读取模板 ───
    with open(TEMPLATE, encoding='utf-8') as f:
        html = f.read()

    # 替换 DEFAULT_RINGS
    old = 'var DEFAULT_RINGS = ['
    old_end = '  ];'
    si = html.index(old)
    ei = html.index(old_end, si) + len(old_end)
    html = html.replace(html[si:ei], build_rings_js(rings))

    # 构建 emptiness 配置
    if args.no_emptiness:
        emp = {k: False for k, v in DEFAULT_EMPTINESS.items() if isinstance(v, bool)}
    elif args.emptiness:
        emp = {**DEFAULT_EMPTINESS, **json.loads(args.emptiness)}
    elif isinstance(data, dict) and 'emptiness' in data:
        emp = {**DEFAULT_EMPTINESS, **data['emptiness']}
    else:
        emp = DEFAULT_EMPTINESS

    # 替换 EMPTINESS 配置
    emp_old = '  var EMPTINESS = {'
    emp_si = html.index(emp_old)
    brace_count = 0
    emp_ei = emp_si
    for i in range(emp_si, len(html)):
        if html[i] == '{':
            brace_count += 1
        elif html[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                emp_ei = i + 2
                break
    html = html.replace(html[emp_si:emp_ei], build_emptiness_js(emp))

    # 替换标题
    html = html.replace('唯识论 · 种子现行 · v1.2 修正版', args.title)
    html = html.replace('唯识论 · 种子现行 · 概念地图', args.title)
    html = html.replace('莫比乌斯环概念地图 · v2.0', args.title)

    # 替换 Legend 三层标注
    legend_lines = []
    for r in rings:
        label = r.get('label', '未命名')
        color = r.get('color', '#4ECDC4')
        first_concept = r.get('concepts', [{}])[0].get('label', '')
        desc = ' · ' + first_concept if first_concept else ''
        legend_lines.append(
            '<div><span class="dot" style="background:{}"></span>{}{}</div>'.format(color, label, desc))
    html = html.replace('<!--LEGEND_RINGS-->', '\n'.join(legend_lines))

    # 替换 STORAGE_KEY
    storage_key = 'mobius_' + hashlib.md5(args.title.encode('utf-8')).hexdigest()[:8]
    html = html.replace("var STORAGE_KEY = 'weishi_mobius_data'", "var STORAGE_KEY = '" + storage_key + "'")

    # ─── 嵌入规则库（如果使用了自动推断且规则库存在） ───
    if args.auto_wuxing:
        try:
            engine_dir = str(Path(__file__).parent)
            if engine_dir not in sys.path:
                sys.path.insert(0, engine_dir)
            from wuxing_engine import WuxingEngine
            rules_path = args.rules or str(RULES_DIR / 'wuxing_bagua_rules.json')
            engine = WuxingEngine(rules_path=rules_path, domain=args.auto_wuxing)
            rules_json = engine.export_rules_json(minified=True)
            # 替换 WUXING_RULES 占位符
            inject = "var WUXING_RULES = " + rules_json + ";"
            html = html.replace("var WUXING_RULES = null;", inject)
        except Exception as e:
            print(f"⚠ 规则嵌入失败: {e}")

    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(html)

    # 验证 JS 语法
    abs_output = str(Path(args.output).resolve())
    r = subprocess.run(['node', '-e',
        "const m=require('fs').readFileSync(process.argv[1],'utf8').match(/<script>([\\s\\S]*?)<\\/script>/);new Function(m[1]);console.log('OK')",
        abs_output],
        capture_output=True, text=True)
    ok = 'OK' in r.stdout
    total_nodes = sum(len(rn.get('concepts', [])) for rn in rings)
    emp_status = '五空全开' if all(v for k, v in emp.items() if isinstance(v, bool)) else '部分关闭'
    wuxing_status = f' + 规则推断({args.auto_wuxing})' if args.auto_wuxing else ''
    print("JS: {} | 节点: {} | 层: {} | {}{} | {}".format(
        '✅' if ok else '❌', total_nodes, len(rings), emp_status, wuxing_status, args.output))
    if not ok:
        print(r.stderr[:500])


if __name__ == '__main__':
    main()