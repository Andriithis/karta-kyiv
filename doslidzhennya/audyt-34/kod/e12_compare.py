"""Е12: розмітка проти виходу екстрактора (відкривається лише після розмітки)."""
import json, csv, re, os, collections
S = os.path.dirname(os.path.abspath(__file__))
H = {r['n']: r for r in json.load(open(os.path.join(S, 'e12_vykhid_ekstraktora.json'), encoding='utf-8'))}
R = [r for r in csv.DictReader(open(os.path.join(S, '..', 'E12-rozmitka.tsv'), encoding='utf-8'), delimiter='\t')]
assert len(R) == 325 and all(int(r['n']) in H for r in R)

def norm(s): return re.sub(r'[\s\-–]', '', (s or '').lower().replace('«', '').replace('»', ''))
def nums(q):
    # номери будинків у цитаті: «, 40», «буд. 3», «№ 10», «Бандери 8»
    # літера — частина номера, лише якщо за нею не йде ще літера («40 в м.» — це не «40в»)
    return {norm(x) for x in re.findall(r"(\d+(?:\s?-?\s?[а-яієїґa-z](?![а-яієїґa-z'’`]))?(?:/\d+[а-яієїґ]?)?)(?![\d.])", q.lower())}

M = collections.Counter(); rows = []
for r in R:
    h = H[int(r['n'])]; t = r['typ']; lv = h['level'] or '—'
    M[(t, lv)] += 1
    verdict = ''
    if t == 'H' and lv == 'house':
        hn = norm(h['house']); qn = nums(r['mistse_podii'])
        st_ok = any(w.lower()[:5] in r['mistse_podii'].lower() for w in re.findall(r"[А-ЯІЇЄҐа-яіїєґ'’`]{5,}", h['street'] or '') if w.lower() not in ('вулиця', 'проспект', 'бульвар', 'провулок'))
        verdict = 'збіг' if (hn in qn or any(hn == q.split('/')[0] for q in qn)) and st_ok else 'ІНША АДРЕСА'
    elif lv == 'house' and t != 'H':
        verdict = 'ЗАЙВА ТОЧКА'
    elif t == 'H' and lv != 'house':
        verdict = 'пропуск'
    rows.append((r['n'], h['k'], t, lv, verdict, h['street'], h['house'], (r['mistse_podii'] or '')[:90], (r['inshi_mistsia'] or '')[:80], (h['addr_sentence'] or '')[:160]))

print('== розмітка (рядки) × екстрактор (стовпці) ==')
lvs = ['house', 'cross', 'street', 'none', 'hidden', '—']
print('     ' + ''.join(f'{l:>8}' for l in lvs))
for t in 'HXSOAPNT':
    print(f'{t:5}' + ''.join(f'{M[(t, l)]:8}' for l in lvs))
v = collections.Counter(x[4] for x in rows)
print(dict(v))
print('\n== розбіжності ==')
for x in rows:
    if x[4] in ('ІНША АДРЕСА', 'ЗАЙВА ТОЧКА') or (x[4] == 'пропуск'):
        print(' | '.join(str(y) for y in x))
json.dump(rows, open(os.path.join(S, 'e12_rows.json'), 'w', encoding='utf-8'), ensure_ascii=False)

