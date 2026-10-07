# -*- coding: utf-8 -*-
"""Скарги 1551 для вкладки «Скарги N» у картках (RISHENNYA 35.10;
ZAVDANNYA-32, ч. 9).

Окремий файл site/skargy.json поруч зі сторінкою, як site/spravy: карта
тягне його, коли вперше відкривають картку, — index.html не важчає.
Скарга лягає на карту лише з точкою (адреса є в реєстрі КМДА, тим самим, що
геокодує голос мешканців). Карта сама добирає скарги для соти, проблеми й
ризику за відстанню; для адреси — той самий будинок за ключем «вулиця +
будинок», тож і скарги на «просп. Берестейський (Перемоги), 117» знаходять
свою адресу.

Формат: {"d0": перший день, "c": [зміст], "r": [результат],
"s": [[шир×1e5, довг×1e5, днів від d0, зміст, результат], …] новіші вгорі,
"a": {індекс точки карти: [номери скарг]}}.
"""
import os, re, csv, gzip, glob, json, datetime as dt, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D1551 = os.path.join(ROOT, 'data', '1551')
POCHATOK = '2025-08'      # з цього місяця збираються скарги (вікно 1551)

# Набір відкритий і знеособлений; якщо в тексті все ж трапиться телефон,
# пошта чи «Прізвище Ім'я По-батькові» — рядок не показуємо
TELEFON = re.compile(r'(\+?38)?[\s(]*0\d{2}[\s)-]*\d{3}[\s-]*\d{2}[\s-]*\d{2}')
POSHTA = re.compile(r'\S+@\S+\.\S+')
PIB = re.compile(r"[А-ЯІЇЄҐ][а-яіїєґ'’]+\s+[А-ЯІЇЄҐ][а-яіїєґ'’]+\s+[А-ЯІЇЄҐ][а-яіїєґ'’]+(?:вич|івна|ївна|овна)\b")


def osobysti(*t):
    s = ' '.join(x or '' for x in t)
    return bool(TELEFON.search(s) or POSHTA.search(s) or PIB.search(s))


def zibraty(P, dst_dir, log=print):
    """site/skargy.json; повертає (скарг, з них на адресах карти) або None"""
    import problems as PR
    from step2_geocode import skey, nh
    fv = sorted(f for f in glob.glob(os.path.join(D1551, 'vidbir-*.tsv.gz'))
                if os.path.basename(f)[7:14] >= POCHATOK)
    if not fv:
        log('   скарги 1551: даних немає (data/1551) — вкладки «Скарги» не буде')
        return None
    idx, _sk, _nh = PR.geokoder()
    if not idx:
        log('   скарги 1551: немає реєстру КМДА — точок немає, вкладки не буде')
        return None

    def kliuch(vul, bud):
        if not vul or not bud: return None
        return skey(str(vul).split('(')[0]), nh(str(bud))

    rows, st = [], collections.Counter()
    for f in fv:
        with gzip.open(f, 'rt', encoding='utf-8', newline='') as fh:
            for r in csv.DictReader(fh, delimiter='\t'):
                k = kliuch(r.get('vulytsya'), r.get('budynok'))
                p = idx.get(k) if k else None
                if p is None and k and '(' in str(r.get('vulytsya')):
                    # давня назва в дужках — запасний варіант, як у голосі мешканців
                    st_ = str(r['vulytsya']); typ = st_.split()[0]
                    k2 = kliuch(f"{typ} {st_.split('(', 1)[1].rstrip(') ')}", r.get('budynok'))
                    p = idx.get(k2); k = k2 if p else k
                if p is None: st['без точки'] += 1; continue
                if osobysti(r.get('content'), r.get('rezultat')): st['особисті дані — не показано'] += 1; continue
                # «Роз`яснено» — у наборі гравіс замість апострофа
                rows.append((r['data'][:10], p, (r.get('content') or '').strip().replace('`', '’'),
                             (r.get('rezultat') or '').strip().replace('`', '’'), k))
                st['з точкою'] += 1
    rows.sort(key=lambda x: x[0], reverse=True)
    d0 = dt.date.fromisoformat(POCHATOK + '-01')
    C, R = {}, {}
    ci = lambda s: C.setdefault(s, len(C))
    ri = lambda s: R.setdefault(s, len(R))
    s_out = [[round(p[0] * 1e5), round(p[1] * 1e5), (dt.date.fromisoformat(d) - d0).days, ci(c), ri(r)]
             for d, p, c, r, _k in rows]
    # адреса карти — той самий будинок
    po_kl = collections.defaultdict(list)
    for j, x in enumerate(rows): po_kl[x[4]].append(j)
    a, na = {}, 0
    for i, p in enumerate(P):
        if not p or not p[3] or not p[2] or ', ' not in p[2]: continue
        vul, bud = p[2].rsplit(', ', 1)
        js = po_kl.get(kliuch(vul, bud))
        if js: a[i] = js; na += len(js)
    out = dict(d0=d0.isoformat(), c=list(C), r=list(R), s=s_out, a=a)
    fp = os.path.join(dst_dir, 'skargy.json')
    json.dump(out, open(fp, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    log(f'   скарги 1551 для карток: ' + ', '.join(f'{k} {v:,}' for k, v in st.items())
        + f'; на адресах карти (той самий будинок) {na:,} на {len(a):,} адресах -> skargy.json '
        f'({os.path.getsize(fp) / 1048576:.1f} МБ)')
    return len(rows), na
