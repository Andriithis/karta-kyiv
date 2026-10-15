# -*- coding: utf-8 -*-
"""Е12б, А2 (ZAVDANNYA-36 з поправками 15.10): точність точок карти.

Еталон — полігон будівлі OSM з тією самою адресою (e12b_budivli.py, файл
Geofabrik). Мірило (центральний чат 15.10) — «точка в межах своєї будівлі» і
відстань до КОНТУРУ (0 — усередині), а не до центроїда; тому підхід «центр
полігона» цим еталоном не судиться. Для інтерполяції й «бази» без полігона —
відстань до точки КМДА тієї самої адреси; немає й її — «не перевірено».

Спосіб кожної точки — з geo кроку 2: house+osm — точно OSM, house+kmda —
точно КМДА, interp — інтерполяція між сусідами, base — біля будинку без
літери («20Б» біля 20), cross — перехрестя (поза А2), об'єкт — точкою
названого місця (36.12; у даних ще немає).

Окремо по всій базі — відстань OSM ↔ КМДА для адрес, що є в обох.
Запуск: python e12b_a2_tochky.py <events.db> <e12b_budivli.json.gz>
"""
import os, sys, json, gzip, csv, math, sqlite3, collections
K = os.path.dirname(os.path.abspath(__file__))
R = os.path.abspath(os.path.join(K, '..', '..', '..'))
sys.path.insert(0, K); sys.path.insert(0, os.path.join(R, 'src'))
from e12b_adresy import skey, nh
from shapely.geometry import Polygon, Point

MX, MY = 111320 * math.cos(math.radians(50.45)), 111320.0
def dist(a, b): return math.hypot((a[0] - b[0]) * MY, (a[1] - b[1]) * MX)


def main(db, bud):
    B = json.load(gzip.open(bud, 'rt', encoding='utf-8'))
    # (ключ, номер) -> [(Polygon, площа)]: однойменні вулиці в різних районах
    # дають кілька будівель з тією самою адресою — «своя» = найближча до точки
    polys = collections.defaultdict(list)
    for st, h, typ, pt, cen, area, pg in B['adr']:
        if not pg or len(pg) < 4: continue
        polys[(skey(st), nh(h).upper())].append((Polygon([(x[1], x[0]) for x in pg]), area or 0))
    poly = polys
    ob = [(Polygon([(x[1], x[0]) for x in o[4]]), o[0], o[1], o[3]) for o in B['ob'] if o[4] and len(o[4]) >= 4]
    kmda = {}
    for r in csv.DictReader(gzip.open(os.path.join(R, 'data', 'geokoder_kmda.csv.gz'), 'rt', encoding='utf-8'), delimiter='\t'):
        kmda.setdefault((skey(r['street']), nh(r['house']).upper()), []).append((float(r['lat']), float(r['lon'])))
    osm = {}
    for st, h, la, lo in json.load(open(os.path.join(R, 'data', 'osm_kyiv_city.json'), encoding='utf-8')):
        osm.setdefault((skey(st), nh(h).upper()), []).append((la, lo))

    def do_konturu(p, k):
        best = 1e18
        P_ = Point(p[1], p[0])
        for pg, _a in poly[k]:
            if pg.contains(P_): return 0.0
            q = pg.exterior.interpolate(pg.exterior.project(P_))
            best = min(best, dist(p, (q.y, q.x)))
        return best
    def blyzh(ps, p): return min(ps, key=lambda x: dist(x, p)) if ps else None
    def plosha(k, p):
        P_ = Point(p[1], p[0])
        return min(poly[k], key=lambda x: x[0].distance(P_))[1]

    c = sqlite3.connect(db)
    # номер — з проходу по текстах, як у геокодера (крок 2), а не зі старого витягу
    import step1c_teksty as TK
    TKD = TK.load_done()
    rows = list(c.execute("select g.adresa, e.street, e.house, g.lat, g.lon, g.precision, g.source, e.doc_id "
                          "from geo g join events e on e.doc_id = g.doc_id where g.precision in ('house','base','interp')"))
    SP = {('house', 'osm'): 'точно OSM', ('house', 'kmda'): 'точно КМДА', ('interp', 'osm'): 'інтерполяція',
          ('base', 'osm'): 'база вулиці («20Б» біля 20)'}
    # одна точка карти = одна адреса (подій на ній — вага для другого рядка)
    tochky = {}
    for adresa, st, h, la, lo, pr, src, doc in rows:
        tk = TKD.get(doc)
        if tk and tk.get('house'): h = tk['house']
        k = (skey(adresa or st or ''), nh(h or '').upper())
        sp = SP.get((pr, src), f'{pr}/{src}')
        t = tochky.setdefault((k, round(la, 5), round(lo, 5)), dict(k=k, p=(la, lo), sp=sp, n=0))
        t['n'] += 1
    st = collections.defaultdict(lambda: dict(точок=0, подій=0, з_еталоном=0, всередині=0, d=[], kmda_d=[], не_перевірено=0))
    for t in tochky.values():
        s = st[t['sp']]; s['точок'] += 1; s['подій'] += t['n']
        d = do_konturu(t['p'], t['k']) if t['k'] in poly else None
        # будівля з тією самою адресою далі 1 км — однойменна вулиця в іншому районі
        # (геокодер обирав район судом) або ключ не збігся: еталоном не вважаємо
        if d is not None and d > 1000: s['далі_1км'] = s.get('далі_1км', 0) + 1; d = None
        if d is not None:
            s['з_еталоном'] += 1; s['d'].append(d); s['всередині'] += d == 0
        elif t['k'] in kmda and t['sp'] != 'точно КМДА':
            s['kmda_d'].append(dist(t['p'], blyzh(kmda[t['k']], t['p'])))
        else:
            s['не_перевірено'] += 1
    def q(v, p):
        v = sorted(v); return round(v[min(len(v) - 1, int(p * len(v)))], 1) if v else None
    out = {}
    print('Спосіб точки | точок | подій | з еталоном | у межах будівлі | медіана до контуру, м | >50 | >100 | >200 | без полігона: до КМДА медіана / >100 м | не перевірено')
    for sp, s in sorted(st.items(), key=lambda x: -x[1]['точок']):
        d = s['d']; kd = s['kmda_d']
        o = dict(точок=s['точок'], подій=s['подій'], з_еталоном=s['з_еталоном'],
                 у_межах=round(s['всередині'] / max(len(d), 1), 3), медіана=q(d, .5),
                 більше_50=round(sum(x > 50 for x in d) / max(len(d), 1), 3),
                 більше_100=round(sum(x > 100 for x in d) / max(len(d), 1), 3),
                 більше_200=round(sum(x > 200 for x in d) / max(len(d), 1), 3),
                 до_КМДА=len(kd), до_КМДА_медіана=q(kd, .5),
                 до_КМДА_більше_100=round(sum(x > 100 for x in kd) / max(len(kd), 1), 3) if kd else None,
                 не_перевірено=s['не_перевірено'], однойменна_далі_1км=s.get('далі_1км', 0))
        out[sp] = o
        print(f"{sp} | {o['точок']:,} | {o['подій']:,} | {o['з_еталоном']:,} | {o['у_межах']:.0%} | {o['медіана']} | "
              f"{o['більше_50']:.1%} | {o['більше_100']:.1%} | {o['більше_200']:.1%} | {o['до_КМДА_медіана']} / {o['до_КМДА_більше_100']} ({o['до_КМДА']}) | {o['не_перевірено']} (+{o['однойменна_далі_1км']} однойменних далі 1 км)")

    # ---- підходи на тому самому еталоні: адреси карти з полігоном ----
    pidkh = collections.defaultdict(list)
    kat = collections.defaultdict(lambda: collections.defaultdict(list))
    def kategoriia(k, t):
        h = k[1]
        a = plosha(k, t['p'])
        if a >= 3000: return 'великі об\'єкти (≥3000 м²)'
        if '/' in h or 'К' in h[1:]: return 'дріб і корпус'
        if h and h[-1].isalpha(): return 'з літерою («20Б»)'
        if a < 250: return 'приватний сектор (<250 м²)'
        return 'решта'
    for t in tochky.values():
        k = t['k']
        if k not in poly: continue
        cur = do_konturu(t['p'], k)
        if cur > 1000: continue
        pidkh['як зараз'].append(cur)
        o_, km_ = blyzh(osm.get(k), t['p']), blyzh(kmda.get(k), t['p'])
        if o_: pidkh['точка OSM-адреси'].append(do_konturu(o_, k))
        if km_: pidkh['точка КМДА'].append(do_konturu(km_, k))
        pidkh['КМДА першим, OSM запасним'].append(do_konturu(km_ or o_ or t['p'], k))
        kt = kategoriia(k, t)
        kat[kt]['як зараз'].append(cur)
        if km_: kat[kt]['КМДА'].append(do_konturu(km_, k))
        if o_: kat[kt]['OSM'].append(do_konturu(o_, k))
    # «сам об'єкт»: адреси, чия будівля — названий великий об'єкт (ТЦ, ринок,
    # вокзал), — чи стоїть точка в межах самого об'єкта
    from shapely import STRtree
    tr = STRtree([o[0] for o in ob])
    obj = []
    for t in tochky.values():
        ix = tr.query(Point(t['p'][1], t['p'][0]).buffer(0.003), predicate='intersects')
        for i in ix:
            o = ob[int(i)]
            if t['k'] in poly and any(pg.intersects(o[0]) for pg, _a in poly[t['k']]):
                P_ = Point(t['p'][1], t['p'][0])
                obj.append((o[1], 0.0 if o[0].contains(P_) else dist(t['p'], (o[0].exterior.interpolate(o[0].exterior.project(P_)).y, o[0].exterior.interpolate(o[0].exterior.project(P_)).x)), t['n']))
                break
    def pidsum(v):
        return dict(n=len(v), у_межах=round(sum(x == 0 for x in v) / max(len(v), 1), 3), медіана=q(v, .5),
                    більше_50=round(sum(x > 50 for x in v) / max(len(v), 1), 3),
                    більше_100=round(sum(x > 100 for x in v) / max(len(v), 1), 3),
                    більше_200=round(sum(x > 200 for x in v) / max(len(v), 1), 3))
    out['_підходи'] = {a: pidsum(v) for a, v in pidkh.items()}
    out['_категорії'] = {kt: {a: pidsum(v) for a, v in d.items()} for kt, d in kat.items()}
    out['_обʼєкти'] = dict(точок=len(obj), у_межах_обʼєкта=round(sum(x[1] == 0 for x in obj) / max(len(obj), 1), 3),
                           поза=sorted([[x[0], round(x[1]), x[2]] for x in obj if x[1] > 0], key=lambda x: -x[2])[:20])
    print('\nПідходи (адреси карти з полігоном OSM):')
    for a, v in out['_підходи'].items(): print(f'  {a}: {v}')
    print('\nЗа категоріями:')
    for kt, d in out['_категорії'].items(): print(f'  {kt}: ' + '; '.join(f"{a} n={v['n']} у межах {v['у_межах']:.0%}, >100 {v['більше_100']:.1%}" for a, v in d.items()))
    print('\nНазвані об\'єкти:', {k: v for k, v in out['_обʼєкти'].items() if k != 'поза'})

    # ---- OSM ↔ КМДА по всій базі ----
    # однойменні — пара найближчих точок; далі 1 км — різні вулиці, не розбіжність
    sp_ = [(k, d) for k in osm.keys() & kmda.keys()
           for d in [min(dist(a, b) for a in osm[k] for b in kmda[k])] if d < 1000]
    dd = [x[1] for x in sp_]
    out['_OSM_КМДА'] = dict(адрес_в_обох=len(dd), медіана=q(dd, .5), більше_50=sum(x > 50 for x in dd),
                            більше_100=sum(x > 100 for x in dd), більше_200=sum(x > 200 for x in dd),
                            перелік_більше_100=[[k[0], k[1], round(d)] for k, d in sorted(sp_, key=lambda x: -x[1]) if d > 100][:300])
    print(f"\nOSM ↔ КМДА: адрес в обох {len(dd):,}; медіана {q(dd, .5)} м; >50 м {out['_OSM_КМДА']['більше_50']:,}, "
          f">100 м {out['_OSM_КМДА']['більше_100']:,}, >200 м {out['_OSM_КМДА']['більше_200']:,}")
    json.dump(out, open(os.path.join(K, 'e12b_a2.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
