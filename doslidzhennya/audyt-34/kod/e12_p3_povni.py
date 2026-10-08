"""Е12, П3: повний текст проти фабули — 60 рішень із 325 (по 10 на статтю).

Качає сторінку рішення з reyestr.court.gov.ua (публічна, без ключів), бере
текст і дивиться, чи є в повному тексті місце події з будинком там, де за
фабулою розмітка дала «немає» (T, N, P, S, O). Кеш — kod/p3/<doc_id>.txt.
"""
import os, re, csv, json, random, time, html, urllib.request, sys
K = os.path.dirname(os.path.abspath(__file__))
R = os.path.abspath(os.path.join(K, '..', '..', '..'))
sys.path.insert(0, os.path.join(R, 'src'))
import addr as A
D = os.path.join(K, 'p3'); os.makedirs(D, exist_ok=True)
H = {x['doc_id']: x for x in json.load(open(os.path.join(K, 'e12_vykhid_ekstraktora.json'), encoding='utf-8'))}
L = {r['doc_id']: r for r in csv.DictReader(open(os.path.join(K, '..', 'E12-rozmitka.tsv'), encoding='utf-8'), delimiter='\t')}
rnd = random.Random(353)
vyb = []
for k in ('124', '130', '173', '178', '185', '309'):
    ds = sorted(d for d, h in H.items() if h['k'] == k); rnd.shuffle(ds); vyb += ds[:10]

def tekst(d):
    f = os.path.join(D, d + '.txt')
    if os.path.exists(f): return open(f, encoding='utf-8').read()
    req = urllib.request.Request(f'https://reyestr.court.gov.ua/Review/{d}', headers={'User-Agent': 'edrsr-academy/4.0'})
    h = urllib.request.urlopen(req, timeout=60).read().decode('utf-8', 'replace')
    m = re.search(r'<textarea[^>]*id="txtdepository"[^>]*>(.*?)</textarea>', h, re.S)
    body = html.unescape(m.group(1)) if m else h
    t = re.sub(r'<[^>]+>', ' ', html.unescape(body)); t = re.sub(r'\s+', ' ', t).strip()
    open(f, 'w', encoding='utf-8').write(t); time.sleep(1.5)
    return t

out = []
for d in vyb:
    t = tekst(d); lab = L[d]['typ']
    r = A.extract(t)
    out.append((d, H[d]['k'], lab, r['level'], r['street'] or '', r['house'] or '', len(t)))
nove = [o for o in out if o[2] not in ('H', 'X') and o[3] in ('house', 'cross')]
print('рішень', len(out), '; порожніх сторінок', sum(1 for o in out if o[6] < 500))
print('за фабулою немає будинку, а в повному тексті розбір знаходить:', len(nove))
for o in nove: print('  ', o)
json.dump(out, open(os.path.join(K, 'e12_p3.json'), 'w', encoding='utf-8'), ensure_ascii=False)
