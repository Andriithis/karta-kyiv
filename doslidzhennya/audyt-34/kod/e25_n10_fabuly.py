# -*- coding: utf-8 -*-
"""Е25, Н10 (36.40): фабули в показі — порожні, шапка RTF, «До суду надійшов…»
(S-П.7), повні ПІБ поліцейських. Міряє зібраний сайт (site/spravy), частки й
по 5 прикладів кожної вади.

    py -3 doslidzhennya/audyt-34/kod/e25_n10_fabuly.py [мітка]  -> e25_vyhid/n10_<мітка>.md
"""
import glob, json, os, re, sys

K = os.path.dirname(os.path.abspath(__file__))
R = os.path.abspath(os.path.join(K, '..', '..', '..'))
VADY = {
    'порожня': lambda f: not f.strip(),
    'шапка RTF': lambda f: bool(re.search(r'Times New Roman|Tahoma;|\\rtf|;;;', f)),
    '«До суду надійшов…»': lambda f: bool(re.match(r'\s*(До\s+[^.]{0,160}?суд\w*[^.]{0,120}?надійш|На\s+розгляд\s+[^.]{0,80}?надійш)', f, re.I)),
    'ПІБ поліцейського': lambda f: bool(re.search(
        r"(?:сержант|лейтенант|капітан|майор|підполковник|інспектор|поліцейськ)\w*[^.;]{0,60}?\s"
        r"[А-ЯІЇЄҐ][а-яіїєґ'’]+\s+[А-ЯІЇЄҐ][а-яіїєґ'’]+\s+[А-ЯІЇЄҐ][а-яіїєґ'’]+(?:вич|івн|ївн)\w*", f)),
}


def main(mitka='do'):
    fab = [e[5] or '' for f in glob.glob(os.path.join(R, 'site', 'spravy', '*.json'))
           for v in json.load(open(f, encoding='utf-8')).values() for e in v]
    n = len(fab)
    o = [f'## Н10 — фабули в показі ({mitka}), {n:,} рішень', '', '| Вада | рішень | частка |', '|---|---|---|']
    pr = {}
    for k, f_ in VADY.items():
        x = [f for f in fab if f_(f)]
        pr[k] = x[:5]
        o.append(f'| {k} | {len(x):,} | {100 * len(x) / n:.2f}% |')
    for k, x in pr.items():
        o += ['', f'### {k}', ''] + [f'- {re.sub(chr(10), " ", f)[:220]}' for f in x if f.strip()]
    open(os.path.join(K, 'e25_vyhid', f'n10_{mitka}.md'), 'w', encoding='utf-8').write('\n'.join(o) + '\n')
    print('\n'.join(o[:8]))


if __name__ == '__main__':
    main(*(sys.argv[1:] or ['do']))
