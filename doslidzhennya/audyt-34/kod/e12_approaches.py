"""Е12: прості підходи на тих самих фабулах, порівняння з ручною розміткою."""
import json, csv, re, os, collections
S = os.path.dirname(os.path.abspath(__file__))
R = {int(r['n']): r for r in csv.DictReader(open(os.path.join(S, '..', 'E12-rozmitka.tsv'), encoding='utf-8'), delimiter='\t')}
H = {r['n']: r for r in json.load(open(os.path.join(S, 'e12_vykhid_ekstraktora.json'), encoding='utf-8'))}
FAB = {}
cur = None
for line in open(os.path.join(S, 'e12_fabuly.txt'), encoding='utf-8'):
    m = re.match(r'#(\d+) ', line)
    if m: cur = int(m.group(1)); continue
    if cur and line.strip(): FAB[cur] = line.strip()

TYP = r"(?:вул(?:иц[яіею])?\.?|просп(?:ект[уі]?)?\.?|пр-т(?:у)?\.?|пр-кт[уі]?|пр\.|бул(?:ьв)?(?:ар[іу]?)?\.?|б-р[уі]?|пл(?:оща|ощі)?\.?|пров(?:ул(?:ок|ку)?)?\.?|шосе|узвіз|набережн[аій])"
NUM = r"(\d+(?:\s?-?\s?[а-яієїґА-ЯІЄЇҐ](?![а-яієїґА-ЯІЄЇҐ]))?(?:/\d+[а-яієїґ]?)?)"
ADR = re.compile(TYP + r"\s*([А-ЯІЇЄҐ][^,;()]{2,40}?)\s*,?\s*(?:буд(?:инок|\.)?\s*№?\s*)?" + NUM + r"(?![\d])")
ADR2 = re.compile(r"(?:буд(?:инку|\.)|будинку)\s*№?\s*" + NUM + r"\s*(?:корп\.?\s*\d+\s*)?(?:по|на)\s+" + TYP + r"\s*([А-ЯІЇЄҐ][а-яієїґ'’`\-]+)")
ROLE = re.compile(r"(доставлен|госпіталізов|нарколог|соціотерап|огляд\w* на стан|місц\w* проживан|проживає|протокол\w*\s+\S*\s*склад|складен\w* протокол|обшук|кімнат\w* поліції|відеозапис|камер\w* спостереження)", re.I)

def found(fab):
    out = []
    for m in ADR.finditer(fab): out.append((m.start(), m.group(1), m.group(2)))
    for m in ADR2.finditer(fab): out.append((m.start(), m.group(2), m.group(1)))
    return sorted(out)
def norm(s): return re.sub(r'[\s\-–]', '', s.lower())
def a2_first(fab):
    f = found(fab); return f[0] if f else None
def a3_role(fab):
    for p, st, hn in found(fab):
        if not ROLE.search(fab[max(0, p - 80):p + 10]): return (p, st, hn)
    return None
def a4_last(fab):
    # для 309: місце затримання зазвичай назване останнім
    f = [x for x in found(fab) if not ROLE.search(fab[max(0, x[0] - 80):x[0] + 10])]
    return f[-1] if f else None
def ok(pred, gold_q):
    if not pred: return None
    _, st, hn = pred; g = gold_q.lower()
    w = [x for x in re.findall(r"[а-яієїґ'’`]{5,}", st.lower())][:1]
    return bool(w) and w[0][:5] in g and norm(hn) in {norm(x) for x in re.findall(NUM, gold_q)}

res = collections.defaultdict(collections.Counter)
for n, r in R.items():
    t = r['typ']
    if t == 'T': continue
    fab = FAB[n]
    for name, fn in (('A2 перша адреса', a2_first), ('A3 перша без ролі', a3_role), ('A4 остання без ролі', a4_last)):
        p = fn(fab); c = res[name]
        if t == 'H':
            v = ok(p, r['mistse_podii'])
            c['H: правильна' if v else ('H: інша адреса' if p else 'H: пропуск')] += 1
        elif p:
            c[f'зайва точка ({t})'] += 1
        if t == 'H' and H[n]['k'] == '309':
            c['309 H правильна' if ok(p, r['mistse_podii']) else '309 H ні'] += 1
for k, c in res.items(): print(k, dict(sorted(c.items())))
