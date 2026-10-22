# -*- coding: utf-8 -*-
"""ZAVDANNYA-38, крок 4 (ZAVDANNYA-39, Д.1): слід 50 + 50.

Вперед — 50 випадкових рішень (усі види, що пройшли «форму»: вирок чи
постанова) від тексту до карти: де відпало (e25_vyhid/prychyny.tsv.gz), яку
адресу взяв прохід, чи на карті, у проблемі, у ризику (e25_vyhid/mapa.tsv.gz).
Назад — 30 випадкових адрес карти й 20 проблем: що каже текст рішення
(site/spravy) — чи названо в ньому саме цю адресу, і чи про те саме подія,
що в назві проблеми.

Скрипт лише готує таблиці; «правильне місце» й «той самий сценарій» —
читанням очима (стовпець «очима» у e25_vyhid/slid.md заповнюється вручну).

    py -3 doslidzhennya/audyt-34/kod/e25_slid.py   -> e25_vyhid/slid_*.md
"""
import collections, csv, glob, gzip, json, os, random, re, sys

K = os.path.dirname(os.path.abspath(__file__))
R = os.path.abspath(os.path.join(K, '..', '..', '..'))
sys.path.insert(0, os.path.join(R, 'src'))
OUT = os.path.join(K, 'e25_vyhid')
SEED = 38


def korotko(s, n=420):
    s = re.sub(r'\s+', ' ', s or '').strip()
    return s if len(s) <= n else s[:n] + '…'


def vpered(rng):
    import labels as L, step1c_teksty as TK
    pr = [r for r in csv.DictReader(gzip.open(os.path.join(OUT, 'prychyny.tsv.gz'), 'rt', encoding='utf-8'), delimiter='\t')
          if r['vidpalo_na'] != 'форма']
    mapa = {r['doc_id']: r for r in csv.DictReader(gzip.open(os.path.join(OUT, 'mapa.tsv.gz'), 'rt', encoding='utf-8'), delimiter='\t')}
    TKD = TK.load_done()
    out = ['| # | doc_id | вид · стаття | відпало | адреса проходу | карта · проблема · ризик | фабула |', '|---|---|---|---|---|---|---|']
    for j, r in enumerate(rng.sample(pr, 50), 1):
        t = TKD.get(r['doc_id']) or {}
        m = mapa.get(r['doc_id']) or {}
        adr = ', '.join(x for x in (t.get('street'), t.get('house')) if x) or '—'
        kpr = '·'.join('так' if m.get(k) == '1' else '—' for k in ('karta', 'problema', 'ryzyk')) if m else '—'
        vid = (r['vidpalo_na'] + (': ' + r['prychyna'] if r['prychyna'] else '')) or 'дійшло'
        lab = (L.CODE.get(r['cat']) or ('', r['cat']))[1].split(' · ')[0]
        out.append(f"| {j} | {r['doc_id']} | {r['vyd']} · {lab} | {vid} | {adr} ({t.get('level', '')}) | {kpr} | "
                   f"{korotko(t.get('fab') or t.get('addr_sentence')).replace('|', '/')} |")
    return out


def nazad(rng):
    import map_dani
    d = map_dani.chytaty(os.path.join(R, 'site', 'index.html'), 'meta', 'pts')
    M, P = d['meta'], d['pts']
    slug = M.get('dslug', [])
    sp = {}
    for f in glob.glob(os.path.join(R, 'site', 'spravy', '*.json')):
        sp.update({int(k): v for k, v in json.load(open(f, encoding='utf-8')).items()})
    adresy = [i for i, p in enumerate(P) if p[3] in (1, 2) and i in sp]
    out = ['### Назад: 30 адрес карти', '',
           '| # | адреса на карті | подій | стаття | фабула випадкової події | номер і вулиця в тексті |', '|---|---|---|---|---|---|']
    for j, i in enumerate(rng.sample(adresy, 30), 1):
        p = P[i]; e = rng.choice(sp[i])
        st, _, h = p[2].rpartition(', ')
        slova = [w for w in re.findall(r"[А-ЯІЇЄҐ][а-яіїєґ'’]{3,}", st)]
        f_ = e[5] or ''
        ozn = ('вулиця ' + ('так' if any(w[:-2].lower() in f_.lower() for w in slova) else 'НІ') +
               ', номер ' + ('так' if h and re.search(r'(?<!\d)' + re.escape(re.sub(r'[^0-9]', '', h)) + r'(?!\d)', f_) else 'НІ'))
        out.append(f"| {j} | {p[2]} | {len(p[4])} | {M['cats'][e[0]].split(' · ')[0]} | {korotko(f_, 300).replace('|', '/')} | {ozn} |")
    # p[7] — проблеми точки (map_problems: ... категорія, проблеми, район)
    probs = [(i, q) for i, p in enumerate(P) for q in (p[7] if len(p) > 7 and isinstance(p[7], list) else []) if isinstance(q, dict)]
    out += ['', '### Назад: 20 проблем', '', '| # | проблема | адреса | 3 випадкові фабули її подій |', '|---|---|---|---|']
    for j, (i, q) in enumerate(rng.sample(probs, min(20, len(probs))), 1):
        ev = q.get('ev') or [[i, k] for k in range(len(P[i][4]))]
        fab = []
        for pi, k in rng.sample(ev, min(3, len(ev))):
            s = sp.get(pi) or []
            if k < len(s): fab.append(korotko(s[k][5], 220).replace('|', '/'))
        out.append(f"| {j} | {q.get('theme', '')} · {q.get('mech', '')} ({q.get('n', '')}) | {P[i][2]} | " + ' ◦ '.join(fab) + ' |')
    return out


def main():
    rng = random.Random(SEED)
    v = vpered(rng); n = nazad(rng)
    open(os.path.join(OUT, 'slid_vpered.md'), 'w', encoding='utf-8').write('\n'.join(['### Вперед: 50 рішень', ''] + v) + '\n')
    open(os.path.join(OUT, 'slid_nazad.md'), 'w', encoding='utf-8').write('\n'.join(n) + '\n')
    print('готово: e25_vyhid/slid_vpered.md, slid_nazad.md')


if __name__ == '__main__':
    main()
