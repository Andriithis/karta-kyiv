"""Е12, П1: вибірка за адресами — топ-100 точок живої карти, по 5 рішень.

Живу карту беремо з https://andriithis.github.io/karta-kyiv/ (index.html,
знято 07.10). Рішення до точки — за адресою з проходу по текстах (той самий
ключ «вулиця + номер», що й підпис точки). Для розмітки — лише речення
адреси й початок фабули, без підпису точки: розмічаємо наосліп.
"""
import os, re, csv, gzip, glob, json, random, collections, urllib.request
K = os.path.dirname(os.path.abspath(__file__))
R = os.path.abspath(os.path.join(K, '..', '..', '..'))
csv.field_size_limit(10**9)
LIVE = os.path.join(K, 'live_index.html')
if not os.path.exists(LIVE):
    with urllib.request.urlopen(urllib.request.Request('https://andriithis.github.io/karta-kyiv/index.html',
                                headers={'User-Agent': 'edrsr-academy/4.0'}), timeout=300) as r:
        open(LIVE, 'wb').write(r.read())

def kl(street, house):
    w = re.findall(r"[А-ЯІЇЄҐа-яіїєґ'’`]{4,}", street or '')
    w = [x for x in w if x.lower() not in ('вулиця', 'проспект', 'бульвар', 'провулок', 'площа', 'шосе', 'дорога')]
    return ((w[-1].lower()[:6] if w else ''), re.sub(r'[\s\-–]', '', (house or '').lower()).replace('a', 'а'))

h = open(LIVE, encoding='utf-8').read()
m = re.search(r'const M=(\{.*?\}), P=(\[.*?\]);\n', h, re.S)
P = json.loads(m.group(2))
top = sorted((p for p in P if p[3] == 1), key=lambda p: -len(p[4]))[:100]
T = {}
for f in sorted(glob.glob(os.path.join(R, 'data', 'teksty', '*.csv.gz'))):
    for r in csv.DictReader(gzip.open(f, 'rt', encoding='utf-8'), delimiter='\t'):
        T[r['doc_id']] = r
po = collections.defaultdict(list)
for d, r in T.items():
    if r['level'] == 'house': po[kl(r['street'], r['house'])].append(d)
rnd = random.Random(3514)
vyb, nema = [], []
for i, p in enumerate(top, 1):
    st, _, hn = p[2].rpartition(', ')
    ds = sorted(po.get(kl(st, hn), []))
    if not ds: nema.append(p[2]); continue
    rnd.shuffle(ds)
    for d in ds[:5]: vyb.append((i, p[2], len(p[4]), d))
json.dump([dict(n=j, top=i, tochka=a, podii=k, doc_id=d) for j, (i, a, k, d) in enumerate(vyb, 1)],
          open(os.path.join(K, 'e12_p1_TOCHKY.json'), 'w', encoding='utf-8'), ensure_ascii=False)
rnd.shuffle(vyb)   # перемішуємо, щоб сусідні рядки не підказували точку
with open(os.path.join(K, 'e12_p1_vybirka.txt'), 'w', encoding='utf-8') as f:
    for i, a, k, d in vyb:
        r = T[d]
        f.write(f"@{d}\n{re.sub(r'[ \t\r\n]+', ' ', r['addr_sentence'])[:420]}\n\n")
print('точок', len(top), '; без рішень у проході', len(nema), nema[:10], '; рішень у вибірці', len(vyb))
print('подій на топ-100:', sum(len(p[4]) for p in top), 'з', sum(len(p[4]) for p in P if p[3] in (1, 2)))
