"""Е12: сліпа вибірка. Друкує лише doc_id, статтю й фабулу; вихід екстрактора — в окремий файл (не читати до кінця розмітки)."""
import gzip, csv, glob, sqlite3, random, re, json, os, sys
sys.path.insert(0, 'D:/problem_orienting/karta-kyiv/src')
import labels
csv.field_size_limit(10**9)
R = 'D:/problem_orienting/karta-kyiv/'
S = os.path.dirname(os.path.abspath(__file__))
T = {}
for f in sorted(glob.glob(R + 'data/teksty/*.csv.gz')):
    for row in csv.DictReader(gzip.open(f, 'rt', encoding='utf-8'), delimiter='\t'):
        if row['fab'].strip():
            T[row['doc_id']] = row
c = sqlite3.connect(R + 'data/events.db')
cat = dict(c.execute('select doc_id, cat from events'))
def lab(code):
    v = labels.CODE.get(code)
    return v if isinstance(v, str) else (v[1] if isinstance(v, (list, tuple)) and len(v) > 1 else str(v))
STR = {'124': r'ст\.124 КУпАП', '130': r'ст\.130 КУпАП', '173': r'ст\.173(-\d)? КУпАП',
       '178': r'ст\.178 КУпАП', '185': r'ст\.185 (КУпАП|КК)', '309': r'ст\.309 КК'}
pools = {k: [] for k in STR}; pools['інші'] = []
for d, row in T.items():
    if d not in cat: continue
    l = lab(cat[d]) or ''
    for k, p in STR.items():
        if re.search(p, l): pools[k].append((d, l)); break
    else:
        pools['інші'].append((d, l))
rnd = random.Random(3412)
N = {'124': 50, '130': 50, '173': 50, '178': 45, '185': 50, '309': 50, 'інші': 30}
sample = []
for k, n in N.items():
    p = sorted(pools[k]); rnd.shuffle(p); sample += [(k, d, l) for d, l in p[:n]]
    print(k, 'у пулі', len(pools[k]), file=sys.stderr)
rnd.shuffle(sample)
# сліпа частина — лише текст
with open(os.path.join(S, 'e12_fabuly.txt'), 'w', encoding='utf-8') as f:
    for i, (k, d, l) in enumerate(sample, 1):
        fab = re.sub(r'\s+', ' ', T[d]['fab'])
        f.write(f'#{i} {d} | {l}\n{fab[:3000]}\n\n')
# прихована частина — вихід екстрактора
json.dump([{'n': i, 'doc_id': d, 'k': k, 'lab': l, **{x: T[d][x] for x in ('rule', 'klass', 'street', 'house', 'level', 'addr_sentence')}}
           for i, (k, d, l) in enumerate(sample, 1)], open(os.path.join(S, 'e12_vykhid_ekstraktora.json'), 'w', encoding='utf-8'), ensure_ascii=False)
print(len(sample), file=sys.stderr)
