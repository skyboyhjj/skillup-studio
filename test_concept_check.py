def concept_to_js_old(c):
    line = "{ label: 'x', desc: 'y', docs: [] }"
    if c.get('wuxing'):
        line = line[:-2] + ", wuxing:'" + c['wuxing'] + "' }"
    if c.get('bagua'):
        line = line[:-2] + ", bagua:'" + c['bagua'] + "' }"
    return line

c = {'wuxing': 'tu', 'bagua': 'kun'}
r = concept_to_js_old(c)
with open('c:/Users/hejij/.trae-cn/work/6a59e217b55e181ea97f0df6/test_out.txt', 'w') as f:
    f.write("BOTH: " + r + "\n")
    c2 = {'wuxing': 'tu'}
    r2 = concept_to_js_old(c2)
    f.write("WUXING_ONLY: " + r2 + "\n")
