import json, urllib.request, urllib.parse

# Check a domain with 0 papers
url = 'https://hub-notion.baai.ac.cn/api_v2/api/reports_detail?title=%s&id=%s' % (
    urllib.parse.quote('具身智能与机器人'), '36ea1a9e-cf9f-42b1-b6b7-e744a6b3a9d7')
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=30) as resp:
    data = json.loads(resp.read().decode())
content = data['info']['documentInfo']['data']['content']

# Find ordered_lists
def find_ordered(blocks, depth=0):
    for b in blocks:
        t = b.get('type','')
        if t == 'ordered_list':
            items = b.get('content', [])
            print(f'ordered_list depth={depth}, items={len(items)}')
            for i, item in enumerate(items[:3]):
                for p in item.get('content', []):
                    text = ''.join(ct.get('text','') for ct in p.get('content', []))
                    if text.strip():
                        print(f'  [{i}] {text[:120]}')
        if 'content' in b and isinstance(b['content'], list):
            find_ordered(b['content'], depth+1)

find_ordered(content)

# Headings
headings = [b for b in content if b.get('type') == 'heading']
print(f'\nHeadings:')
for h in headings:
    hc = h.get('content', [])
    if hc:
        print(f'  L{h.get("attrs",{}).get("level","?")}: {hc[0].get("text","")[:80]}')