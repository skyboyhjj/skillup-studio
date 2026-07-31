import json, urllib.request, urllib.parse

url = 'https://hub-notion.baai.ac.cn/api_v2/api/reports_detail?title=%s&id=%s' % (
    urllib.parse.quote('软件工程与编程'), '866c61cc-6b89-4e5d-81cf-0e9de13865a3')
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=30) as resp:
    data = json.loads(resp.read().decode())
content = data['info']['documentInfo']['data']['content']

def find_ordered(blocks, depth=0):
    for b in blocks:
        t = b.get('type','')
        if t == 'ordered_list':
            items = b.get('content', [])
            print(f'ordered_list depth={depth}, items={len(items)}')
            for i, item in enumerate(items[:5]):
                for p in item.get('content', []):
                    text = ''.join(ct.get('text','') for ct in p.get('content', []))
                    if text.strip():
                        print(f'  [{i}] {text[:150]}')
        if 'content' in b and isinstance(b['content'], list):
            find_ordered(b['content'], depth+1)

find_ordered(content)

# Headings
headings = [b for b in content if b.get('type') == 'heading']
print(f'\nHeadings ({len(headings)}):')
for h in headings:
    hc = h.get('content', [])
    if hc:
        print(f'  L{h.get("attrs",{}).get("level","?")}: {hc[0].get("text","")[:80]}')