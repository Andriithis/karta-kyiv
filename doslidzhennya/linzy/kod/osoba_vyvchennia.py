# -*- coding: utf-8 -*-
"""Нові ознаки лінзи «Порушник» (Андрій 27.10): скільки подій карти дає кожна
ознака і вибірка з вікном навколо слова для перевірки очима — неповнолітній
правопорушник 50, решта по 20.

    py -3 doslidzhennya/linzy/kod/osoba_vyvchennia.py  -> doslidzhennya/linzy/osoba_vybirka.md
"""
import io, os, random, re, sqlite3, sys, contextlib

K = os.path.dirname(os.path.abspath(__file__))
R = os.path.abspath(os.path.join(K, '..', '..', '..'))
sys.path.insert(0, os.path.join(R, 'src'))
import step3_map as S3, linzy as LZ, step1c_teksty as TK, labels as L

with contextlib.redirect_stdout(io.StringIO()):
    V = S3.vybir(sqlite3.connect(S3.DB))
xs = {o[0]: [] for o in LZ.OZNAKY}
for r in V['rows']:
    f = (V['TKD'].get(r[0]) or {}).get('fab') or ''
    b = LZ.oznaky(f, TK.kodeks(r[2]), r[2])
    for bit in xs:
        if b & bit: xs[bit].append((r[0], L.CODE.get(r[2], ('', r[2]))[1], f))
o = ['# Нові ознаки порушника — вибірка для перевірки очима', '',
     f'Подій карти: {len(V["rows"]):,}. Вікно — 160 знаків до слова і 120 після.']
for bit, k, n, g in LZ.OZNAKY:
    vs = xs[bit]; nn = 50 if k == 'nepovnolitnii' else 20
    o += ['', f'## {g}: {n} ({k}) — {min(nn, len(vs))} випадкових з {len(vs):,}', '']
    for j, (d, cat, f) in enumerate(random.Random(41).sample(vs, min(nn, len(vs))), 1):
        m = LZ.nepovnolitnii(f) if k == 'nepovnolitnii' else LZ.ispytovyi(f) if k == 'ispytovyi' else (LZ.VYRAZ[k].search(f) if k in LZ.VYRAZ else None)
        v = f[max(0, m.start() - 160):m.end() + 120] if m else f[:240]
        o.append(f'**{j}.** {d} · {cat} · …{re.sub(r"\s+", " ", v)}…')
open(os.path.join(R, 'doslidzhennya', 'linzy', 'osoba_vybirka.md'), 'w', encoding='utf-8').write('\n'.join(o) + '\n')
for bit, k, n, g in LZ.OZNAKY: print(k, len(xs[bit]))
