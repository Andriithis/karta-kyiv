# -*- coding: utf-8 -*-
"""Крок 3. Карта з агрегацією по адресах + рейтинг адрес.

Класифікація спрощена до інцидент/проблема (передача, п.7.1): «проблема» —
це членство в кураторському списку ~50 адрес-напрямків (п.7.3), відібраних за
однорідністю СТАТТІ, а не теми (п.7.2). Аномалія як окрема категорія прибрана:
якщо відібраний напрямок не пояснюється моделлю ризику, картка просто каже
«причина встановлюється на місці» (п.7.1, 7.4).
"""
import os, sys, csv, json, glob, math, sqlite3, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import labels as L
import mech as M
import pravo as PR          # офіційні назви статей для картки і листа
# HTML-шаблон винесено в окремий файл: разом із ним модуль важив 67 КБ,
# а це один файл на дві дуже різні речі — логіку відбору й розмітку.
from step3_tpl import TPL
from map_excl import load_excl, detect_institutional
import map_layers
import map_problems
from map_problems import COURTS, SLUG

LAST_META = {}          # meta останньої збірки — читає крок 5

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data'); DB = os.path.join(DATA, 'events.db')
OUT  = os.path.join(ROOT, 'karta.html')
RISKS = os.path.join(DATA, 'risks.json')
NETW  = os.path.join(DATA, 'network.json')
RISKF = os.path.join(DATA, 'risk.json')
BORD  = os.path.join(DATA, 'borders.json')
FACTF = os.path.join(DATA, 'factors.json')             # шар чинників середовища (крок 2e)
EXCL = os.path.join(DATA, 'vykluchennya.txt')          # формується автоматично
MANUAL = os.path.join(DATA, 'vykluchennya_moyi.txt')    # ваш список, ніколи не перезаписується
REVIEW = os.path.join(DATA, 'top100_dlya_pereviryky.txt')

def main(district=None, mode='full', out=None):
    if not os.path.exists(DB): print('спочатку кроки 1 і 2'); sys.exit(1)
    c = sqlite3.connect(DB)
    if not c.execute("SELECT name FROM sqlite_master WHERE name='geo'").fetchone():
        print('немає таблиці geo — крок 2 не відпрацював'); sys.exit(1)

    extra = {}
    for fp in glob.glob(os.path.join(DATA, 'kyiv_*.csv')):
        with open(fp, encoding='utf-8-sig') as fh:
            for r in csv.DictReader(fh, delimiter='\t'):
                extra[r['doc_id']] = (r['cause_num'], r['doc_url'])

    rows = list(c.execute("""SELECT e.doc_id,e.court,e.cat,e.date,e.tm,e.street,e.house,
        g.lat,g.lon,g.precision FROM events e JOIN geo g ON g.doc_id=e.doc_id"""))
    print(f'подій з координатами: {len(rows):,}')
    if not rows: return

    print('перевірка на адреси установ:')
    excl = detect_institutional(rows, load_excl())
    before = len(rows)
    rows = [r for r in rows
            if ((r[5] + ', ' + r[6]) if (r[5] and r[6]) else (r[5] or '')).lower() not in excl]
    print(f'   вилучено подій: {before - len(rows):,}  ->  залишилось {len(rows):,}')

    # ---- злиття кодів у назви ----
    cnt = collections.Counter()
    for r in rows:
        lb = L.CODE.get(r[2])
        if lb: cnt[lb] += 1
        else: cnt[('СЕР', 'інші (код ' + r[2] + ')')] += 1

    labels = sorted(cnt, key=lambda k: (L.ORDER.index(k[0]) if k[0] in L.ORDER else 9, -cnt[k]))
    li = {k: i for i, k in enumerate(labels)}
    ck = sorted({r[1] for r in rows}); ci = {v: i for i, v in enumerate(ck)}

    yc = collections.Counter(r[3][:4] for r in rows)
    yrs = sorted(y for y, n in yc.items() if n >= 200 and y.isdigit())
    ykeys = yrs + (['раніше'] if sum(n for y, n in yc.items() if y not in yrs) else [])
    yi = {y: i for i, y in enumerate(ykeys)}
    print('роки:', ', '.join(ykeys))
    print(f'статей після злиття: {len(labels)} (було би {len({r[2] for r in rows})} за кодами)')

    # група подібності (п.7.2) для кожного індексу в `labels`
    LBL2SIM = {}
    for _code, (_th, _lbl) in L.CODE.items():
        LBL2SIM[(_th, _lbl)] = M.simgroup(_code) or f'{_th}_{_code}'
    sim_of = [LBL2SIM.get(k, f'{k[0]}_i{i}') for i, k in enumerate(labels)]

    agg = collections.defaultdict(list)
    for doc, court, cat, date, tm, street, house, la, lo, prec in rows:
        lb = L.CODE.get(cat) or ('СЕР', 'інші (код ' + cat + ')')
        agg[(round(la, 5), round(lo, 5))].append(
            (ci[court], li[lb], yi.get(date[:4], yi.get('раніше', 0)),
             int(tm[:2]) if tm and tm[:2].isdigit() else -1,
             1 if prec == 'house' else 0, date, street or '', house or '',
             *extra.get(doc, ('', ''))))

    # ---- ЧЕСНА НАЗВА ТОЧКИ (виправлено 01.09.2026) ----
    # Крок 2 має два режими прив'язки. Коли будинок є в OpenStreetMap, подія
    # стає на свою адресу. Коли будинку немає — подія стає в ЦЕНТР ВУЛИЦІ,
    # і туди ж стають усі інші події цієї вулиці без знайденого будинку.
    # Раніше така купа підписувалася номером першої-ліпшої події: «вул.
    # Міхновського, 42 — 96 подій», хоча на самому будинку 42 сталася одна.
    # Це не установа й не помилка адреси — це загальний осередок вулиці,
    # і називати його треба саме так.
    P = []
    n_street = 0
    for (la, lo), evs in agg.items():
        hs = [e for e in evs if e[4] and e[6]]
        if hs:
            e = hs[0]
            a = f"{e[6]}, {e[7]}" if e[7] else e[6]
            prec = 1
        else:
            e = next((e for e in evs if e[6]), None)
            a = (e[6] + ' · вся вулиця') if e else ''
            prec = 0
            n_street += 1
        P.append([la, lo, a, prec,
                  [[e_[0], e_[1], e_[2], e_[3]] for e_ in evs],
                  [[e_[1], e_[5], e_[3], e_[8], e_[9]] for e_ in sorted(evs, key=lambda x: x[5], reverse=True)[:6]]])
    print(f'унікальних адрес: {len(P):,} '
          f'(з них {n_street:,} — центри вулиць, точного будинку немає)')

    groups_idx = {}
    for ti, t in enumerate(L.ORDER):
        for i, k in enumerate(labels):
            if k[0] == t: groups_idx[i] = ti
    groups = []
    gi_of_theme = {}       # код теми -> її індекс у meta['groups'] (для фільтрації карток)
    for t in L.ORDER:
        ids = [li[k] for k in labels if k[0] == t]
        if ids:
            gi_of_theme[t] = len(groups)
            groups.append([L.THEMES[t], ids, sum(cnt[labels[i]] for i in ids)])
    # law: короткий підпис -> повна назва статті з кодексу. Коротким підписом
    # карта користується в списках, повним — картка проблеми й паспорт SARA,
    # бо лист балансоутримувачу має називати статтю так, як її названо в законі.
    law = {k[1]: PR.nazva(k[1]) for k in labels if PR.nazva(k[1])}
    _no = [k[1] for k in labels if not PR.nazva(k[1])]
    if _no: print(f'   без офіційної назви статті: {len(_no)} — {"; ".join(_no[:3])}')
    meta = dict(courts=[COURTS.get(x, x) for x in ck], cats=[k[1] for k in labels],
                counts=[cnt[k] for k in labels], groups=groups, years=ykeys, law=law)


    # ---- шари контексту: потоки, ризик, чинники (map_layers) ----
    risks, ER, theme_rgrid, pred_theme, FACT = map_layers.build(district, labels)

    # ---- відбір проблем і обрізання до району (map_problems) ----
    P, POP, meta, theme_cnt = map_problems.select(
        P, meta, labels, ck, ykeys, sim_of, gi_of_theme,
        district, mode, risks, ER, FACT, theme_rgrid, pred_theme)

    html = TPL.replace('__POP__', json.dumps(POP, separators=(',', ':'))) \
              .replace('__FACTS__', json.dumps(FACT, ensure_ascii=False, separators=(',', ':'))) \
              .replace('__RISKS__', json.dumps(risks, ensure_ascii=False, separators=(',', ':'))) \
              .replace('__META__', json.dumps(meta, ensure_ascii=False)) \
              .replace('__PTS__', json.dumps(P, ensure_ascii=False, separators=(',', ':')))
    # Крок 5 бере звідси числа районів для плиток — щоб не збирати десять карт
    # заради десяти чисел.
    global LAST_META
    LAST_META = meta

    dst = out or OUT
    os.makedirs(os.path.dirname(dst) or '.', exist_ok=True)
    open(dst, 'w', encoding='utf-8').write(html)
    print(f'готово: {os.path.basename(dst)} ({os.path.getsize(dst)/1048576:.1f} МБ)')
    return theme_cnt

if __name__ == '__main__':
    main()
