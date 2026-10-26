# -*- coding: utf-8 -*-
"""Е25, Н2 (36.40): події з інших міст на однойменних вулицях Києва — скільки
й 20 прикладів очима. Ознака — те саме правило, що в step3_map (inshe_misto):
у реченні з адресою (чи на початку фабули) назване інше місто чи село, а
«Київ» не назване.

    py -3 doslidzhennya/audyt-34/kod/e25_n2_mista.py  -> e25_vyhid/n2_mista.md
"""
import collections, io, os, random, re, sqlite3, sys, contextlib

K = os.path.dirname(os.path.abspath(__file__))
R = os.path.abspath(os.path.join(K, '..', '..', '..'))
sys.path.insert(0, os.path.join(R, 'src'))
import step3_map as S3

with contextlib.redirect_stdout(io.StringIO()) as buf:
    S3.vybir(sqlite3.connect(S3.DB))
print('\n'.join(l for l in buf.getvalue().splitlines() if 'інших міст' in l))
Z = S3.LAST_INSHE_MISTO
o = ['## Н2 — події з інших міст на однойменних вулицях Києва', '',
     f'Знято з карти: {len(Z):,}. За містом: ' +
     ', '.join(f'{k} {v}' for k, v in collections.Counter(m for _d, m, _a, _t in Z).most_common(15)), '',
     '### 20 випадкових (сід 41)', '']
for j, (d, m, a, t) in enumerate(random.Random(41).sample(Z, min(20, len(Z))), 1):
    o.append(f'{j}. {d} · «{m}» · адреса карти: {a} — {re.sub(r"\s+", " ", t)[:260]}')
open(os.path.join(K, 'e25_vyhid', 'n2_mista.md'), 'w', encoding='utf-8').write('\n'.join(o) + '\n')
print('\n'.join(o[:3]))
