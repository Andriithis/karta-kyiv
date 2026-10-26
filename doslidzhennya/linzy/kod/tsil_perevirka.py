# -*- coding: utf-8 -*-
"""Перевірка витягу цілі (src/tsil.py, 36.41; README розділ 2): частки
заповнення за видом і по 50 випадкових рішень на вид для читання очима
(межа — хибних ≤ 2 на вид).

    py -3 doslidzhennya/linzy/kod/tsil_perevirka.py  -> doslidzhennya/linzy/tsil_perevirka.md
"""
import collections, io, os, random, re, sqlite3, sys, contextlib

K = os.path.dirname(os.path.abspath(__file__))
R = os.path.abspath(os.path.join(K, '..', '..', '..'))
sys.path.insert(0, os.path.join(R, 'src'))
import step3_map as S3, tsil as TS, podii as PD, mech as M

with contextlib.redirect_stdout(io.StringIO()):
    V = S3.vybir(sqlite3.connect(S3.DB))
TKD = V['TKD']
po_vydu = collections.defaultdict(list)
for r in V['rows']:
    th = PD.theme(r[2]); f = (TKD.get(r[0]) or {}).get('fab') or ''
    if th in ('МАЙ', 'ДТП', 'ГП', 'НАР', 'АЛК') and f:
        import labels as L
        sim = L.SIMGROUP.get(r[2], '')
        po_vydu[th].append((r[0], r[2], f, TS.tsil(th, sim, f)))
o = ['# Перевірка витягу цілі (36.41)', '']
for th, xs in po_vydu.items():
    pol = collections.Counter(k + '=' + v for _d, _c, _f, t in xs for k, v in t.items())
    z = sum(1 for x in xs if x[3])
    o += [f'## {th}: {len(xs):,} подій з фабулою, з ціллю {z:,} ({100 * z / len(xs):.0f}%)', '',
          'Значення: ' + ', '.join(f'{k} {v:,}' for k, v in pol.most_common(14)), '']
    for j, (d, c, f, t) in enumerate(random.Random(36).sample(xs, min(50, len(xs))), 1):
        o.append(f'{j}. {d} · {t or "—"} · {re.sub(r"\s+", " ", f)[:230]}')
    o.append('')
open(os.path.join(R, 'doslidzhennya', 'linzy', 'tsil_perevirka.md'), 'w', encoding='utf-8').write('\n'.join(o) + '\n')
print('\n'.join(l for l in o if l.startswith('## ') or l.startswith('Значення')))
