"""Е18: чи збігається адреса в базі подій (events.db) з адресою останнього
проходу по текстах (data/teksty) — для 37 адрес установ і для всієї бази."""
import os, re, csv, gzip, glob, sqlite3, collections
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')
csv.field_size_limit(10**9)
def kl(street, house):
    w = re.findall(r"[А-ЯІЇЄҐа-яіїєґ'’`]{4,}", street or '')
    return ((w[-1].lower()[:6] if w else ''), re.sub(r'[\s\-–]', '', (house or '').lower()))
T = {}
for f in sorted(glob.glob(os.path.join(R, 'data', 'teksty', '*.csv.gz'))):
    for r in csv.DictReader(gzip.open(f, 'rt', encoding='utf-8'), delimiter='\t'):
        T[r['doc_id']] = r
db = sqlite3.connect(os.path.join(R, 'data', 'events.db'))
E = list(db.execute("select doc_id, street, house, level from events where level='house'"))
c = collections.Counter(); prykl = collections.defaultdict(list)
for d, st, hn, lv in E:
    t = T.get(d)
    if not t: c['немає в teksty'] += 1; continue
    same = kl(st, hn) == kl(t['street'], t['house'])
    key = ('збіг' if same else f"інша ({t['level'] or '—'})", t['rule'])
    c[key] += 1
    if not same and len(prykl[st + ', ' + hn]) < 3: prykl[st + ', ' + hn].append((d, t['street'], t['house'], t['level']))
print('events.db (house) проти teksty:', len(E))
for k, n in c.most_common(): print('  ', k, n)
top = collections.Counter(st + ', ' + hn for d, st, hn, lv in E
                          if T.get(d) and kl(st, hn) != kl(T[d]['street'], T[d]['house']))
print('\nадреси з найбільшою кількістю розбіжностей:')
for a, n in top.most_common(15): print(f'  {n:4}  {a}  → напр. {prykl[a][:2]}')
