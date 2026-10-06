# -*- coding: utf-8 -*-
"""Крок 2c. Прохідність — модельований потік людей (RISHENNYA 34.1, 35.2).

Один потік замість трьох (до шкіл, до транспорту, до магазинів). Від кожного
житлового будинку люди йдуть до цілей шести мет — робота, торгівля, школи й
садки, здоров'я, парки, інше (кафе, послуги) — з частками поїздок METY.
Мешканці будинку — населення шестикутника Kontur, поділене пропорційно
площі поверхів. Ціль обирається за відстанню мережею й вагою (розмір):
до 3 цілей мети в межах ходьби, імовірність ∝ вага × exp(−d / 400 м).
Роботи чи школи в межах ходьби немає — людина йде до зупинки чи метро.
Зворотний потік — ті, хто приїхав: від зупинок і метро до роботи, стільки
ж людей, скільки поїхало транспортом на роботу по місту.

Вихід — data/network.json: [геометрія, назва, potik, id відрізка] для КОЖНОГО
відрізка між перехрестями (vidrizky); відрізок без маршрутів — 0, а не
відсутній. potik — «≈ осіб на добу» в моделі: туди й назад.

Основа: Davies & Bishop (2014), betweenness як потік; Andresen (2006, 2011)
— ризик ділиться на людей, що там є, а не лише на мешканців.
"""
import os, sys, json, math, time, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
RAW = os.path.join(DATA, 'osm_risks_raw.json')
OUT = os.path.join(DATA, 'network.json')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vidrizky as VR

MAX_M = int(os.environ.get('MAXWALK', '1200'))   # межа пішої ходьби
TAU = 400.0            # м: як швидко падає охота йти далі
K_CIL = 3              # до скількох цілей мети розходяться люди одного будинку
TUDY_NAZAD = 2         # маршрут туди й назад — дві проходки відрізком

# ---- МЕТИ Й ЧАСТКИ ПОЇЗДОК (одне місце в коді; джерела — METODYKA, «Прохідність») ----
# Частки — початкові (Андрій 06.10): відкритого обстеження мобільності Києва
# з розбивкою за метою не знайдено; порядок величин — з європейських
# обстежень (робота й навчання ≈ 40%, покупки ≈ 20%, дозвілля й послуги ≈ 30%).
# (ключі цілей, частка поїздок, як важить ціль)
METY = {
    'робота':   (('robota',), .30, 'площа'),
    'торгівля': (('market', 'b1_super', 'b1_mall', 'shop24'), .20, 'тип'),
    'школи':    (('school', 'kindergarten'), .12, 'тип'),
    'здоров’я': (('b1_pharmacy', 'b1_hospital', 'clinic'), .08, 'тип'),
    'парки':    (('park_vkhid',), .10, 'тип'),
    'інше':     (('b1_cafe', 'b1_fastfood', 'posluhy'), .20, 'тип'),
}
VAGA_TYPU = {'b1_mall': 8, 'market': 6, 'b1_super': 4, 'shop24': 1, 'b1_hospital': 5, 'clinic': 3,
             'b1_pharmacy': 1, 'school': 4, 'kindergarten': 2, 'b1_cafe': 1, 'b1_fastfood': 1,
             'posluhy': 1, 'park_vkhid': 1}
# мети, для яких людина без цілі в межах ходьби їде транспортом
TRANSPORTOM = ('робота', 'школи')

# ---- БУДИНКИ ----
ZHYTLO = ('apartments', 'residential', 'house', 'dormitory', 'detached', 'semidetached_house', 'terrace')
POVERHY_TYPU = {'house': 1.5, 'detached': 1.5, 'semidetached_house': 1.5, 'terrace': 2,
                'apartments': 5, 'residential': 5, 'dormitory': 5, 'yes': 3}
CHASTKA_PLOSHCHI = 0.7     # під житло — 70% рамки будинку


def mdeg(lat): return 111320.0, 111320.0 * math.cos(math.radians(lat))


def dist_m(a, b):
    my, mx = mdeg((a[0] + b[0]) / 2)
    return math.hypot((a[0] - b[0]) * my, (a[1] - b[1]) * mx)


def key(lat, lon): return VR.key(lat, lon)


def centr(el):
    la = el.get('lat') or (el.get('center') or {}).get('lat')
    lo = el.get('lon') or (el.get('center') or {}).get('lon')
    if la and lo: return (la, lo)
    g = el.get('geometry')
    if g: return (sum(p['lat'] for p in g) / len(g), sum(p['lon'] for p in g) / len(g))
    return None


def ploshcha(el):
    """м² рамки елемента (out bb); немає рамки — 0"""
    b = el.get('bounds')
    if not b: return 0.0
    my, mx = mdeg((b['minlat'] + b['maxlat']) / 2)
    return abs(b['maxlat'] - b['minlat']) * my * abs(b['maxlon'] - b['minlon']) * mx


def poverhy(t):
    for k in ('building:levels',):
        try:
            v = float(str(t.get(k, '')).replace(',', '.').split(';')[0])
            if v > 0: return v
        except ValueError:
            pass
    try:
        h = float(str(t.get('height', '')).replace(',', '.').replace('m', '').strip())
        if h > 0: return max(1.0, h / 3)
    except ValueError:
        pass
    return POVERHY_TYPU.get(t.get('building'), 3)


class Grid:
    def __init__(s, pts, cell=0.0015):
        s.c = cell; s.g = collections.defaultdict(list)
        for i, p in enumerate(pts): s.g[(int(p[0] / cell), int(p[1] / cell))].append((p, i))

    def nearest(s, la, lo, rad):
        my, mx = mdeg(la)
        n = int(max(rad / my, rad / mx) / s.c) + 1
        ci, cj = int(la / s.c), int(lo / s.c)
        best, bd = None, 1e18
        for i in range(ci - n, ci + n + 1):
            for j in range(cj - n, cj + n + 1):
                for p, k in s.g.get((i, j), ()):
                    d = math.hypot((p[0] - la) * my, (p[1] - lo) * mx)
                    if d < bd: bd, best = d, k
        return best if bd <= rad else None


def v_poligoni(la, lo, ring):
    c = False
    for (a1, o1), (a2, o2) in zip(ring, ring[1:] + ring[:1]):
        if (o1 > lo) != (o2 > lo) and la < (a2 - a1) * (lo - o1) / (o2 - o1) + a1: c = not c
    return c


def zhytlova_zona(raw):
    """функція (lat, lon) -> чи в landuse=residential"""
    polys = []
    for el in raw.get('zhytlo_zona') or []:
        g = el.get('geometry') or []
        if len(g) >= 4:
            ring = [(p['lat'], p['lon']) for p in g]
            polys.append((min(p[0] for p in ring), max(p[0] for p in ring),
                          min(p[1] for p in ring), max(p[1] for p in ring), ring))
    C = 0.01
    idx = collections.defaultdict(list)
    for k, (a, b, c, d, _r) in enumerate(polys):
        for i in range(int(a / C), int(b / C) + 1):
            for j in range(int(c / C), int(d / C) + 1):
                idx[(i, j)].append(k)

    def f(la, lo):
        for k in idx.get((int(la / C), int(lo / C)), ()):
            a, b, c, d, r = polys[k]
            if a <= la <= b and c <= lo <= d and v_poligoni(la, lo, r): return True
        return False
    return f, len(polys)


def budynky(raw, log=print):
    """[(lat, lon, площа поверхів)] житлових будинків; building=yes — лише в
    житловій забудові або від 3 поверхів, інакше це сараї й гаражі."""
    zona, n_z = zhytlova_zona(raw)
    out, st = [], collections.Counter()
    for el in raw.get('houses') or []:
        t = el.get('tags') or {}
        c = centr(el)
        if not c: continue
        b = t.get('building')
        pv = poverhy(t)
        if b == 'yes':
            yavni = 'building:levels' in t and pv >= 3
            if not (yavni or (n_z and zona(*c))):
                st['yes — не житло'] += 1; continue
            st['yes — житло'] += 1
        elif b in ZHYTLO:
            st[b] += 1
        else:
            continue
        S = max(ploshcha(el), 40.0) * CHASTKA_PLOSHCHI * pv
        out.append((c[0], c[1], S))
    log('   будинки: ' + ', '.join(f'{k} {v:,}' for k, v in st.most_common()))
    return out


def tsili(raw):
    """мета -> [(lat, lon, вага)]; плюс транспорт [(lat, lon)]"""
    def els(k):
        if k in ('school', 'kindergarten'):
            return [e for e in raw.get('b1_school') or [] if (e.get('tags') or {}).get('amenity') == k]
        if k == 'clinic':
            return [e for e in raw.get('b1_hospital') or [] if (e.get('tags') or {}).get('amenity') == 'clinic']
        if k == 'b1_hospital':
            return [e for e in raw.get('b1_hospital') or [] if (e.get('tags') or {}).get('amenity') == 'hospital']
        if k == 'market':
            return raw.get('b1_market') or []
        if k == 'shop24':
            return [e for e in raw.get('shop24') or [] if (e.get('tags') or {}).get('shop') == 'convenience']
        if k == 'park_vkhid':
            return raw.get('park') or []
        return raw.get(k) or []
    out = {}
    for m, (keys, _sh, vaga) in METY.items():
        acc = []
        for k in keys:
            for e in els(k):
                c = centr(e)
                if not c: continue
                w = max(ploshcha(e), 200.0) if vaga == 'площа' else VAGA_TYPU.get(k, 1)
                acc.append((c[0], c[1], w))
        out[m] = acc
    trans = [c for k in ('b1_metro', 'b1_stops') for e in raw.get(k) or [] if (c := centr(e))]
    return out, trans


def naselennia(houses, log=print):
    """мешканці кожного будинку: населення шестикутника ∝ площа поверхів"""
    pp = os.path.join(DATA, 'population.json')
    if not os.path.exists(pp):
        log('   population.json немає — кожен будинок важить свою площу поверхів / 25 м²')
        return [S / 25.0 for _la, _lo, S in houses]
    P = json.load(open(pp, encoding='utf-8'))['items']
    C = 0.0045
    pg = collections.defaultdict(list)
    for k, (la, lo, n) in enumerate(P): pg[(int(la / C), int(lo / C))].append((la, lo, k))
    hex_of, suma = [], collections.Counter()
    for la, lo, S in houses:
        best, bd = None, 1e18
        ci, cj = int(la / C), int(lo / C)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for a, b, k in pg.get((ci + di, cj + dj), ()):
                    d = dist_m((la, lo), (a, b))
                    if d < bd: bd, best = d, k
        best = best if bd <= 600 else None
        hex_of.append(best)
        if best is not None: suma[best] += S
    out = [(P[k][2] * S / suma[k]) if k is not None and suma[k] else 0.0
           for (la, lo, S), k in zip(houses, hex_of)]
    log(f'   мешканців розподілено: {sum(out):,.0f} (у шестикутниках Kontur {sum(p[2] for p in P):,.0f})')
    return out


def main():
    import numpy as np
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import dijkstra, connected_components
    if not os.path.exists(RAW):
        print('немає data/osm_risks_raw.json — спершу крок 2b'); sys.exit(1)
    t0 = time.time()
    raw = json.load(open(RAW, encoding='utf-8'))
    roads, foot = VR.vulytsi(raw), raw.get('foot') or []
    houses = budynky(raw)
    print(f'дороги {len(roads):,}   пішохідні {len(foot):,}   житлові будинки {len(houses):,}')
    if not houses or not foot:
        # Без будинків маршрутів немає; без доріжок потоки йшли б лише
        # проїжджою частиною. network.json лишається з минулого запуску.
        print('УВАГА: у знімку OSM немає ' + ' і '.join(n for n, v in (('будинків (houses)', houses),
                                                                     ('пішохідних доріжок (foot)', foot)) if not v)
              + ' — прохідність не перераховується')
        sys.exit(1)

    # ---- граф ----
    nid, coord = {}, []
    def node(k):
        if k not in nid: nid[k] = len(coord); coord.append(k)
        return nid[k]
    A, B, W = [], [], []
    for w in roads + foot:
        g = w.get('geometry') or []
        ks = [key(p['lat'], p['lon']) for p in g]
        for u, v in zip(ks, ks[1:]):
            if u == v: continue
            d = dist_m(u, v)
            if d <= 0: continue
            a, b = node(u), node(v)
            A += [a, b]; B += [b, a]; W += [d, d]
    N = len(coord)
    G = csr_matrix((W, (A, B)), shape=(N, N))
    nc, lab = connected_components(G, directed=False)
    big = np.bincount(lab).argmax()
    main_n = np.where(lab == big)[0]
    print(f'1) граф: вузлів {N:,}, ребер {len(W) // 2:,}; найбільша компонента {len(main_n):,} '
          f'({100 * len(main_n) / N:.0f}%)')
    ngrid = Grid([coord[i] for i in main_n])
    snap = lambda la, lo, r: (lambda k: None if k is None else int(main_n[k]))(ngrid.nearest(la, lo, r))

    # ---- джерела: мешканці на вузлах ----
    people = naselennia(houses)
    src = collections.Counter()
    for (la, lo, _S), n in zip(houses, people):
        if n <= 0: continue
        k = snap(la, lo, 300)
        if k is not None: src[k] += n
    print(f'2) джерел (вузлів з мешканцями): {len(src):,}; мешканців на мережі {sum(src.values()):,.0f}')

    # ---- цілі ----
    T, trans = tsili(raw)
    tn = {}
    for m, lst in T.items():
        nodes, ws = [], []
        for la, lo, w in lst:
            k = snap(la, lo, 400)
            if k is not None: nodes.append(k); ws.append(w)
        tn[m] = (np.array(nodes, dtype=np.int64), np.array(ws, dtype=float))
        print(f'   мета «{m}»: цілей {len(lst):,}, у мережі {len(nodes):,}')
    trn = np.array(sorted({k for la, lo in trans if (k := snap(la, lo, 300)) is not None}), dtype=np.int64)
    print(f'   зупинок і входів метро в мережі: {len(trn):,}')

    load = collections.defaultdict(float)     # (u, v), u < v -> людей

    def walk(pred_row, s, t, L):
        v = t
        while v != s and v >= 0:
            u = pred_row[v]
            if u < 0: break
            load[(u, v) if u < v else (v, u)] += L
            v = u

    def rozpodil(d, w):
        """до K_CIL найближчих цілей у межах ходьби -> (індекси, частки)"""
        ok = np.where(np.isfinite(d) & (d <= MAX_M))[0]
        if not len(ok): return ok, None
        if len(ok) > K_CIL:
            ok = ok[np.argpartition(d[ok], K_CIL)[:K_CIL]]
        p = w[ok] * np.exp(-d[ok] / TAU)
        return ok, p / p.sum()

    # ---- маршрути з дому ----
    S_ = np.array(list(src.keys()), dtype=np.int64)
    R_ = np.array([src[k] for k in S_], dtype=float)
    BATCH = 64
    transportom = 0.0
    st = collections.Counter()
    print('3) маршрути з дому…', flush=True)
    for b0 in range(0, len(S_), BATCH):
        idx = S_[b0:b0 + BATCH]
        D, Pr = dijkstra(G, directed=False, indices=idx, limit=MAX_M * 1.25, return_predecessors=True)
        for r, s in enumerate(idx):
            R = R_[b0 + r]
            for m, (keys, share, _v) in METY.items():
                nodes, ws = tn[m]
                if not len(nodes): continue
                ok, p = rozpodil(D[r, nodes], ws)
                if p is not None:
                    st[m + ': пішки'] += 1
                    for j, pj in zip(ok, p): walk(Pr[r], s, nodes[j], R * share * pj)
                elif m in TRANSPORTOM and len(trn):
                    dt = D[r, trn]
                    j = int(np.argmin(dt))
                    if np.isfinite(dt[j]) and dt[j] <= MAX_M:
                        walk(Pr[r], s, trn[j], R * share)
                        if m == 'робота': transportom += R * share
                        st[m + ': до зупинки'] += 1
                    else:
                        st[m + ': недосяжно'] += 1
                else:
                    st[m + ': недосяжно'] += 1
        if (b0 // BATCH) % 50 == 0:
            print(f'   {b0 + len(idx):,} / {len(S_):,} · {time.time() - t0:.0f} c', flush=True)
    print('   ' + ', '.join(f'{k} {v:,}' for k, v in sorted(st.items())))

    # ---- зворотний потік: ті, хто приїхав на роботу ----
    nodes, ws = tn['робота']
    if transportom > 0 and len(nodes) and len(trn):
        best = np.full((len(nodes), K_CIL), np.inf); bs = np.full((len(nodes), K_CIL), -1, dtype=np.int64)
        for b0 in range(0, len(trn), BATCH):
            idx = trn[b0:b0 + BATCH]
            D = dijkstra(G, directed=False, indices=idx, limit=MAX_M * 1.25)[:, nodes]   # зупинки × цілі
            for r in range(len(idx)):
                row = np.concatenate([best, D[r][:, None]], axis=1)
                srow = np.concatenate([bs, np.full((len(nodes), 1), b0 + r)], axis=1)
                o = np.argsort(row, axis=1)[:, :K_CIL]
                best = np.take_along_axis(row, o, 1); bs = np.take_along_axis(srow, o, 1)
        dosyazh = np.isfinite(best[:, 0]) & (best[:, 0] <= MAX_M)
        A_ = np.where(dosyazh, ws, 0.0)
        pryizd = transportom * A_ / A_.sum() if A_.sum() else A_
        # маршрути від зупинок, згруповані за зупинкою
        po_zup = collections.defaultdict(list)
        for j in np.where(dosyazh)[0]:
            d = best[j]; ok = np.isfinite(d) & (d <= MAX_M)
            p = np.exp(-d[ok] / TAU); p /= p.sum()
            for k, pk in zip(bs[j][ok], p): po_zup[int(k)].append((int(nodes[j]), pryizd[j] * pk))
        zk = sorted(po_zup)
        for b0 in range(0, len(zk), BATCH):
            idx = trn[zk[b0:b0 + BATCH]]
            _D, Pr = dijkstra(G, directed=False, indices=idx, limit=MAX_M * 1.25, return_predecessors=True)
            for r, k in enumerate(zk[b0:b0 + BATCH]):
                for t, L in po_zup[k]: walk(Pr[r], int(trn[k]), t, L)
        print(f'4) зворотний потік: {transportom:,.0f} осіб приїхали на роботу до {int(dosyazh.sum()):,} цілей '
              f'від {len(zk):,} зупинок')

    # ---- зведення по відрізках між перехрестями ----
    # Навантаження відрізка = середнє по його ребрах, зважене на довжину;
    # доріжка впритул уздовж дороги (≤ 35 м) — частина коридору вулиці.
    SEG = VR.build(roads)
    seg_of = VR.rebra(SEG)
    CELL = 0.0006
    rgrid = collections.defaultdict(list)
    for sid, s in SEG.items():
        for a, b in zip(s['pts'], s['pts'][1:]):
            mla, mlo = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            rgrid[(int(mla / CELL), int(mlo / CELL))].append((mla, mlo, sid))

    def owner(la, lo, rad=35.0):
        my, mx = mdeg(la)
        ci, cj = int(la / CELL), int(lo / CELL)
        best_, bd = None, 1e18
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for pa, po, s_ in rgrid.get((ci + di, cj + dj), ()):
                    d = math.hypot((pa - la) * my, (po - lo) * mx)
                    if d < bd: bd, best_ = d, s_
        return best_ if bd <= rad else None
    acc = collections.defaultdict(float); ln = collections.defaultdict(float)
    for (u, v), c in load.items():
        a, b = coord[u], coord[v]
        sid = seg_of.get((a, b))
        if sid is None:
            sid = owner((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            if sid is None: continue
        d = dist_m(a, b) or 1.0
        acc[sid] += c * d; ln[sid] += d
    items = []
    for sid, s in SEG.items():
        g = s['pts']; stp = max(1, len(g) // 10)
        geo = [[round(p[0], 5), round(p[1], 5)] for p in g[::stp]]
        if geo[-1] != [round(g[-1][0], 5), round(g[-1][1], 5)]:
            geo.append([round(g[-1][0], 5), round(g[-1][1], 5)])
        potik = int(round(TUDY_NAZAD * acc[sid] / ln[sid])) if ln.get(sid) else 0
        items.append([geo, s['name'], potik, sid])
    items.sort(key=lambda x: -x[2])
    json.dump({'title': 'Прохідність (модельований потік людей, осіб на добу)', 'versiia': 2, 'items': items},
              open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    nz = sum(1 for it in items if it[2] > 0)
    print(f'5) відрізків {len(items):,} (з потоком {nz:,}) -> data/network.json')

    # ---- будова мережі (Johnson & Bowers 2014) — та сама, що в кроці 4 ----
    netgeo = VR.budova(SEG, VR.stupeni(roads))
    json.dump(netgeo, open(os.path.join(DATA, 'netgeo.json'), 'w', encoding='utf-8'), separators=(',', ':'))
    print(f'   -> data/netgeo.json ({len(netgeo):,} відрізків) · {time.time() - t0:.0f} c')

    # ---- перевірка очима (ZAVDANNYA-32, 4.4): потік і процентиль ----
    vals = sorted(it[2] for it in items)
    def pct(v):
        import bisect
        return 100 * bisect.bisect_left(vals, v) / len(vals)
    PEREVIRKA = os.environ.get('PEREVIRKA', 'Хрещатик;Велика Васильківська;Лісовий;Кадетський Гай;Героїв Дніпра;'
                               'Дорогожицька;Андріївський узвіз;Набережне шосе;Подільський міст').split(';')
    print('\n=== ПЕРЕВІРКА (найвищий відрізок вулиці) ===')
    for q in PEREVIRKA:
        hit = [it for it in items if q.lower() in (it[1] or '').lower()]
        if not hit: print(f'   {q}: немає в мережі'); continue
        top = max(hit, key=lambda x: x[2]); med = sorted(h[2] for h in hit)[len(hit) // 2]
        print(f'   {q}: макс {top[2]:,} (вище за {pct(top[2]):.0f}% відрізків), медіана {med:,} '
              f'({pct(med):.0f}%), відрізків {len(hit)}')


if __name__ == '__main__':
    main()
