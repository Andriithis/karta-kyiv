# -*- coding: utf-8 -*-
"""Е25, Н9 (36.40): та сама подія під різними номерами справ — скільки злито і
20 груп для читання очима (хибних злиттів має бути ≤ 1).

    py -3 doslidzhennya/audyt-34/kod/e25_n9_zlyttia.py  -> e25_vyhid/n9_zlyttia.md
"""
import collections, io, os, random, re, sqlite3, sys, contextlib

K = os.path.dirname(os.path.abspath(__file__))
R = os.path.abspath(os.path.join(K, '..', '..', '..'))
sys.path.insert(0, os.path.join(R, 'src'))
import step3_map as S3, labels as L

with contextlib.redirect_stdout(io.StringIO()) as buf:
    S3.vybir(sqlite3.connect(S3.DB))
print([l for l in buf.getvalue().splitlines() if 'різними справами' in l][0])
Z = S3.LAST_ZLYTO
import step1c_teksty as TK
TKD = TK.load_done()
vyd = collections.Counter(S3.PD.theme(z[2][0][2]) for z in Z)
rozm = collections.Counter(min(z[1], 10) for z in Z)
o = ['## Н9 — та сама подія під різними номерами справ', '',
     f'Груп {len(Z):,}, зайвих подій {sum(z[1] - 1 for z in Z):,}. За видами: ' +
     ', '.join(f'{L.THEMES.get(k, k)} {v}' for k, v in vyd.most_common()) +
     '. Розмір групи: ' + ', '.join(f'{k}{"+" if k == 10 else ""} — {v}' for k, v in sorted(rozm.items())), '',
     '### 20 випадкових груп (сід 40)', '']
for j, (k, n, reps) in enumerate(random.Random(40).sample(Z, min(20, len(Z))), 1):
    o.append(f'**{j}.** {k[1]} {k[2]} · {k[4]} · {reps[0][5]}, {reps[0][6]} · справ {n}')
    for r in reps[:4]:
        f = re.sub(r'\s+', ' ', (TKD.get(r[0]) or {}).get('fab') or '')[:230]
        o.append(f'- {r[0]}: {f}')
    o.append('')
open(os.path.join(K, 'e25_vyhid', 'n9_zlyttia.md'), 'w', encoding='utf-8').write('\n'.join(o) + '\n')
print('\n'.join(o[:3]))
