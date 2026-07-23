#!/usr/bin/env python3
"""
莫比乌斯环概念地图生成脚本 v2.0
用法:
  python3 build_mobius.py --data data.json --title "标题" --output 输出.html
  python3 build_mobius.py --data data.json --no-emptiness --output 输出.html
  python3 build_mobius.py --data data.json --emptiness '{"wane":false}' --output 输出.html

注：生成的 HTML 内置五阶音景（Web Audio API）和动画录制功能（桌面端MP4/移动端WebM），需通过 HTTP 服务器访问。
"""
import json, argparse, subprocess, re
from pathlib import Path

TEMPLATE = Path(__file__).parent.parent / 'assets' / 'template.html'

# 默认五空配置
DEFAULT_EMPTINESS = {
    'sunyata': True, 'mirror': True, 'breath': True, 'wane': True, 'ascend': True,
    'mirrorRatio': 0.42, 'breathPeriod': 10000, 'breathAmplitude': 15,
    'fadeStart': 35000, 'fadeEnd': 50000, 'fadeTarget': 0.15, 'fadeRestore': 0.5,
    'ascendRatio': 0.2
}

def esc_js(s):
    """转义字符串用于 JS 单引号"""
    return s.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n')

def concept_to_js(c):
    """单个概念 → JS对象字符串"""
    docs_str = json.dumps(c.get('docs', []), ensure_ascii=False)
    line = "{{ label: '{l}', desc: '{d}', docs: {docs} }}".format(
        l=esc_js(c['label']), d=esc_js(c.get('desc', '')), docs=docs_str)
    # 注入可选字段
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

def main():
    parser = argparse.ArgumentParser(description='莫比乌斯环概念地图生成器 v2.0')
    parser.add_argument('--data', required=True, help='概念数据 JSON 文件')
    parser.add_argument('--title', default='概念地图', help='页面标题')
    parser.add_argument('--output', default='output.html', help='输出 HTML 文件')
    parser.add_argument('--no-emptiness', action='store_true', help='关闭全部五空动画')
    parser.add_argument('--emptiness', default=None, help='自定义 emptiness JSON 字符串')
    args = parser.parse_args()

    with open(args.data, encoding='utf-8') as f:
        data = json.load(f)
    rings = data.get('rings', data if isinstance(data, list) else [])

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
    # 找到 EMPTINESS 对象的开始和结束
    emp_si = html.index(emp_old)
    # 找到匹配的 }; 结束
    brace_count = 0
    emp_ei = emp_si
    for i in range(emp_si, len(html)):
        if html[i] == '{':
            brace_count += 1
        elif html[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                emp_ei = i + 2  # 包含 };\n
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

    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(html)

    # 验证 JS 语法
    import shlex
    abs_output = str(Path(args.output).resolve())
    r = subprocess.run(['node', '-e',
        "const m=require('fs').readFileSync(process.argv[1],'utf8').match(/<script>([\\s\\S]*?)<\\/script>/);new Function(m[1]);console.log('OK')",
        abs_output],
        capture_output=True, text=True)
    ok = 'OK' in r.stdout
    total_nodes = sum(len(rn.get('concepts', [])) for rn in rings)
    emp_status = '五空全开' if all(v for k, v in emp.items() if isinstance(v, bool)) else '部分关闭'
    print("JS: {} | 节点: {} | 层: {} | {} | {}".format(
        '✅' if ok else '❌', total_nodes, len(rings), emp_status, args.output))
    if not ok:
        print(r.stderr[:500])

if __name__ == '__main__':
    main()
