# -*- coding: utf-8 -*-
"""ZAVDANNYA-37, крок 3: дві перевірки адрес перед планом правок (36.18).

1. Адреси будівель Geofabrik (e12b_budivli.json.gz) у межах Києва проти
   знімка osm_kyiv_city.json: скільки адрес є лише в будівлях; скільки подій
   «вулиця є, будинку з таким номером немає» (розклад Е12б, 6 370) та
   інтерполяцій і «баз» (2 082 + 1 680) знаходять там свій будинок. Знімок
   бере з будівлі одну точку й губить частину адрес — якщо їх багато, перша
   хвиля бере адреси будівель у довідник геокодера.
2. Точки на однойменних вулицях, чия будівля з тією самою адресою далі 1 км
   (А2: 659): скільки виправляє район суду так, як це робить геокодер
   (step2_geocode.pick: кандидати в районі суду в межах R_ODNA одне від
   одного — точка; кілька далеких — точки немає).

Правила — копії e12b_adresy і e12b_a2_tochky, ті самі ключі (skey, nh).
Запуск: python e37_adresy.py <тека даних (events.db, nabir_36_14.csv.gz,
1551/)> <e12b_budivli.json.gz>
"""
import os, sys, json, gzip, csv, math, sqlite3, collections
K = os.path.dirname(os.path.abspath(__file__))
R = os.path.abspath(os.path.join(K, '..', '..', '..'))
sys.path.insert(0, K); sys.path.insert(0, os.path.join(R, 'src'))
from e12b_adresy import Dovidnyk, skey, nh
import step2_geocode as G

MX, MY = 111320 * math.cos(math.radians(50.45)), 111320.0
def dist(a, b): return math.hypot((a[0] - b[0]) * MY, (a[1] - b[1]) * MX)


def main(DD, bud):
    import step3_map as S3, labels as L, podii as PD
    import step1c_teksty as TK
    from map_problems import COURTS
    from shapely.geometry import Polygon, Point
    Dv = Dovidnyk(os.path.join(DD, '1551'))
    borders = json.load(open(os.path.join(R, 'data', 'borders.json'), encoding='utf-8'))
    _dc = {}
    def raion(p):
        k = (round(p[0], 5), round(p[1], 5))
        if k not in _dc: _dc[k] = G.district_of(k, borders)
        return _dc[k]
    B = json.load(gzip.open(bud, 'rt', encoding='utf-8'))
    out = {}

    # ---------------------------------------------------------------- 1
    # адреса будівлі -> точки (центроїд полігона, інакше вузол); лише в межах Києва
    BUD = collections.defaultdict(list)
    for st, h, typ, pt, cen, area, pg in B['adr']:
        p = cen or pt
        if not raion(p): continue
        BUD[(Dv.vulytsia(st), nh(h))].append(p)
    znimok = {(Dv.vulytsia(st), nh(h)) for st, h, _a, _b in Dv.osm}
    kmda = {(Dv.vulytsia(r['street']), nh(r['house'])) for r in Dv.kmda}
    lyshe = set(BUD) - znimok
    out['1_адреси'] = dict(будівель_з_адресою_в_Києві=len(BUD), у_знімку=len(znimok),
                           лише_в_будівлях=len(lyshe), лише_в_будівлях_і_не_в_КМДА=len(lyshe - kmda))
    print('1. адреси:', out['1_адреси'])

    NB = {r['doc_id']: r for r in csv.DictReader(gzip.open(os.path.join(DD, 'nabir_36_14.csv.gz'), 'rt', encoding='utf-8'))}
    c = sqlite3.connect(os.path.join(DD, 'events.db'))
    cat = dict(c.execute('select doc_id, cat from events'))
    court = dict(c.execute('select doc_id, court from events'))
    geo = {r[0]: r[1:] for r in c.execute('select doc_id, lat, lon, precision, source from geo')}
    st = collections.Counter(); pryk = collections.defaultdict(list)
    for d, r in NB.items():
        if r['v_rozrakhunkakh'] != '1' or PD.theme(cat.get(d, '')) not in L.ORDER: continue
        g = geo.get(d); pr = g[2] if g else None
        if pr in ('house', 'cross'): continue
        k = Dv.vulytsia(r['street']) if r['street'] else ''
        key = (k, nh(r['house']))
        # ті самі категорії, що в розкладі Е12б (e12b_adresy.rozklad)
        if pr in ('base', 'interp'): kat = 'інтерполяція' if pr == 'interp' else 'база'
        elif not k or not r['house'] or k not in Dv.full: continue
        elif key not in Dv.bud: kat = 'будинку немає'
        else: continue
        st[f'{kat}: подій'] += 1
        if key in BUD:
            # будівля може стояти на однойменній вулиці в іншому районі —
            # рахуємо окремо ті, що в районі суду
            rd = COURTS.get(court.get(d))
            v_rs = rd and any(raion(p) == rd for p in BUD[key])
            st[f'{kat}: будинок є в будівлях'] += 1
            st[f'{kat}: будинок є в будівлях, у районі суду'] += bool(v_rs)
            a = f"{r['street']}, {r['house']}"
            if len(pryk[kat]) < 15 and a not in pryk[kat]: pryk[kat].append(a)
    out['1_події'] = dict(st); out['1_приклади'] = pryk
    for k_, v in sorted(st.items()): print(f'   {k_}: {v:,}')

    # ---------------------------------------------------------------- 2
    polys = collections.defaultdict(list)
    for s_, h, typ, pt, cen, area, pg in B['adr']:
        if pg and len(pg) >= 4: polys[(skey(s_), nh(h).upper())].append(Polygon([(x[1], x[0]) for x in pg]))
    def do_konturu(p, k):
        P_ = Point(p[1], p[0]); best = 1e18
        for pg in polys[k]:
            if pg.contains(P_): return 0.0
            q = pg.exterior.interpolate(pg.exterior.project(P_)); best = min(best, dist(p, (q.y, q.x)))
        return best
    TKD = TK.load_done()
    # кандидати адреси, як у геокодері: усі точки OSM і КМДА з тим самим ключем
    kand = collections.defaultdict(list)
    for s_, h, la, lo in Dv.osm: kand[(skey(s_), nh(h).upper())].append((la, lo))
    for r in Dv.kmda: kand[(skey(r['street']), nh(r['house']).upper())].append((float(r['lat']), float(r['lon'])))
    tochky = {}
    for adresa, s_, h, la, lo, pr, src, doc in c.execute(
            "select g.adresa, e.street, e.house, g.lat, g.lon, g.precision, g.source, e.doc_id "
            "from geo g join events e on e.doc_id = g.doc_id where g.precision in ('house','base','interp')"):
        tk = TKD.get(doc)
        if tk and tk.get('house'): h = tk['house']
        k = (skey(adresa or s_ or ''), nh(h or '').upper())
        t = tochky.setdefault((k, round(la, 5), round(lo, 5)), dict(k=k, p=(la, lo), n=0, sudy=collections.Counter(), a=adresa or s_ or (tk or {}).get('street') or k[0]))
        t['n'] += 1; t['sudy'][COURTS.get(court.get(doc))] += 1
    s2 = collections.Counter(); pr2 = collections.defaultdict(list)
    for t in tochky.values():
        if t['k'] not in polys or do_konturu(t['p'], t['k']) <= 1000: continue
        s2['точок'] += 1; s2['подій'] += t['n']
        rd = t['sudy'].most_common(1)[0][0]
        rp = raion(t['p'])
        if not rd:
            v = 'суд не районний — район суду не допоможе'
        elif rp == rd:
            # точка вже в районі суду: далека будівля — однойменна вулиця деінде
            v = 'точка вже в районі суду — лишається'
        else:
            vr = [p for p in kand.get(t['k'], []) + [pg.centroid.coords[0][::-1] for pg in polys[t['k']]] if raion(p) == rd]
            if vr and G.spread_km(vr) <= G.R_ODNA: v = 'район суду дає іншу точку — виправляє'
            elif vr: v = 'у районі суду кілька далеких кандидатів — точки немає'
            else: v = 'у районі суду такої адреси немає — точки немає'
        s2[v] += 1; s2[v + ' (подій)'] += t['n']
        if len(pr2[v]) < 12: pr2[v].append(f"{t['a']}, {t['k'][1]} — точка: {rp or '?'}, суд: {rd or '—'} ({t['n']})")
    out['2_однойменні'] = dict(s2); out['2_приклади'] = pr2
    print('2. однойменні:')
    for k_, v in sorted(s2.items()): print(f'   {k_}: {v:,}')
    for k_, v in pr2.items(): print(f'   {k_}: ' + '; '.join(v[:6]))
    json.dump(out, open(os.path.join(K, 'e37_adresy.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
