"""Е18 / 36.12: 37 адрес «поліція чи суд у 60 м» — чи це місце події.

Для кожної будівлі — статті подій і речення з адресою з тексту рішення,
щоб людина прочитала й вирішила, а не правило.
"""
import os, re, csv, gzip, glob, sqlite3, collections, sys, random
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')
sys.path.insert(0, os.path.join(R, 'src'))
import labels
csv.field_size_limit(10**9)

def kl(street, house):
    # одна будівля пишеться по-різному: «Я. Коласа, 27» і «Якуба Коласа, 27»
    w = re.findall(r"[А-ЯІЇЄҐа-яіїєґ'’`]{4,}", street or '')
    return ((w[-1].lower()[:6] if w else ''), re.sub(r'[\s\-–]', '', (house or '').lower()).replace('a', 'а'))

rows = [l.rstrip() for l in open(os.path.join(R, 'data', 'vykluchennya.txt'), encoding='utf-8')
        if l.strip() and not l.startswith('#')]
budivli = {}
for l in rows:
    if 'будівля установи' not in l: continue
    a = l.split('#')[0].strip(); st, _, hn = a.rpartition(',')
    budivli.setdefault(kl(st, hn), []).append(a)

T = {}
for f in sorted(glob.glob(os.path.join(R, 'data', 'teksty', '*.csv.gz'))):
    for r in csv.DictReader(gzip.open(f, 'rt', encoding='utf-8'), delimiter='\t'):
        T[r['doc_id']] = r['addr_sentence']
db = sqlite3.connect(os.path.join(R, 'data', 'events.db'))
ev = collections.defaultdict(list)
for d, st, hn, cat in db.execute("select doc_id, street, house, cat from events where level='house'"):
    k = kl(st, hn)
    if k in budivli: ev[k].append((d, cat))

def lab(c):
    v = labels.CODE.get(c); return v[1] if isinstance(v, tuple) else '?'
rnd = random.Random(3612)
for k, nazvy in sorted(budivli.items(), key=lambda x: -len(ev[x[0]])):
    e = ev[k]
    print(f'\n### {nazvy[0]} — {len(e)} подій; написання: {"; ".join(nazvy)}')
    print('   статті: ' + '; '.join(f'{a} {n}' for a, n in collections.Counter(lab(c).split(' · ')[0] for _, c in e).most_common(6)))
    s = [x for x in e if T.get(x[0])]; rnd.shuffle(s)
    for d, c in s[:4]:
        print(f'   - {d} {lab(c)[:28]}: {re.sub(chr(10), " ", T[d])[:260]}')
