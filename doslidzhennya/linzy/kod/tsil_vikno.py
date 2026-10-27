# -*- coding: utf-8 -*-
"""Перевірка цілі з вікном навколо слова, за яким обрано значення (src/tsil.py):
по 50 випадкових подій виду з ціллю. Для ДТП і майна перший прохід
(tsil_perevirka.py) обрізав фабулу раніше, ніж текст доходив до цілі.

    py -3 doslidzhennya/linzy/kod/tsil_vikno.py ДТП|МАЙ  -> doslidzhennya/linzy/tsil_vikno_<вид>.md
"""
import io, os, random, re, sqlite3, sys, contextlib

K = os.path.dirname(os.path.abspath(__file__))
R = os.path.abspath(os.path.join(K, '..', '..', '..'))
sys.path.insert(0, os.path.join(R, 'src'))
import step3_map as S3, tsil as TS, podii as PD, labels as L

VYD = sys.argv[1]
POLE = {'ДТП': [('zitknennia', 'ZITKN')], 'МАЙ': [('berut', 'BERUT'), ('u_koho', None)]}[VYD]
with contextlib.redirect_stdout(io.StringIO()):
    V = S3.vybir(sqlite3.connect(S3.DB))
xs = []
for r in V['rows']:
    if PD.theme(r[2]) != VYD: continue
    f = (V['TKD'].get(r[0]) or {}).get('fab') or ''
    t = TS.tsil(VYD, L.SIMGROUP.get(r[2], ''), f)
    if t: xs.append((r[0], f, t))
o = [f'# Ціль: {VYD}, вікно навколо слова (50 випадкових з {len(xs):,})', '']
for j, (d, f, t) in enumerate(random.Random(37).sample(xs, 50), 1):
    o.append(f'**{j}.** {d} · {t}')
    for pole, sl in POLE:
        if pole in t:
            v = TS.dokaz(sl, t[pole], f) if sl else ''
            if pole == 'u_koho':
                m = (TS.MEREZHA.search(f) or TS.MAGAZYN_SYLNO.search(f) or TS.LIUDYNA.search(f) or TS.MAGAZYN.search(f))
                v = f[max(0, m.start() - 90):m.end() + 90] if m else ''
            o.append(f'- {pole}: …{re.sub(chr(10), " ", v)}…')
    o.append('')
open(os.path.join(R, 'doslidzhennya', 'linzy', f'tsil_vikno_{VYD}.md'), 'w', encoding='utf-8').write('\n'.join(o) + '\n')
print(o[0])
