# -*- coding: utf-8 -*-
"""Крок 2c. Прохідність — модельований потік людей (RISHENNYA 34.1, 35.2).

Один потік замість трьох (до шкіл, до транспорту, до магазинів). Від кожного
житлового будинку люди йдуть до цілей шести мет — робота, торгівля, школи й
садки, здоров'я, парки, інше (кафе, послуги) — з частками поїздок METY.
Мешканці будинку — населення шестикутника Kontur, поділене пропорційно
площі поверхів. Ціль обирається за відстанню мережею й вагою (розмір):
до 3 цілей мети в межах ходьби, імовірність ∝ вага × exp(−d / 400 м).
60% поїздок на роботу й до вишів — завжди пішки до зупинки чи метро; школи
чи роботи в межах ходьби немає — теж (рішення Андрія 07.10). Зворотний
потік — ті, хто приїхав: від зупинок і метро до роботи, стільки ж людей,
скільки поїхало транспортом на роботу, і приїжджі — до ТЦ, ринків, парків,
вокзалів і місць з магазинами й кафе.

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
# вага цілі «робота» — площа рамки, але не більше 0,5 км²; відношення з
# рамкою понад 2 км² — розкидані корпуси, не місце
MAKS_PLOSHCHA_M2 = 500_000.0
ROZKYD_M2 = 2_000_000.0
# мети, для яких людина без цілі в межах ходьби їде транспортом
TRANSPORTOM = ('робота', 'школи')

# ---- ТРАНСПОРТ І ПРИЇЖДЖІ (рішення Андрія 07.10; ZVIT-32, 4.4) ----
# Попередня модель вела до зупинки лише тих, кому роботи поруч немає, а
# робота є майже всюди — метро й центр лишалися без потоку. Тепер частка
# поїздок на роботу й до вишів іде пішки до зупинки чи метро завжди.
# Орієнтир Андрія ~60% (План сталої міської мобільності); відкритий розподіл
# Києва 2015 р. для всіх поїздок: 37% громадським транспортом, 35% пішки,
# 28% авто (texty.org.ua, 2020) — без авто 51%, а поїздки на роботу довші.
TRANSPORT_ROBOTA = 0.60
GT_USIKH = 37 / (37 + 35)      # частка громадського транспорту серед поїздок без авто
# Приїжджі — решта поїздок громадським транспортом понад роботу: від зупинок
# і метро до ТЦ, ринків, парків, вокзалів і місць з магазинами й кафе.
# Школи, магазини поруч, аптеки — без змін (пішки), тож приїжджі — окремі
# поїздки понад шість мет: (0,51 − 0,30 × 0,60) ≈ 0,33 на мешканця.
PRYIZHDZHI = GT_USIKH - METY['робота'][1] * TRANSPORT_ROBOTA
R_METRO, R_ZUPYNKA = 1500.0, 500.0   # м: до метро йдуть далі, ніж до зупинки
# Метро — кілька ліній і поїзд щокілька хвилин: між входом за 800 м і
# зупинкою за 200 м люди частіше обирають метро. Вага взята до перевірки й
# не підганялася; частка метро серед поїздок транспортом — у журналі, для
# звірки з річними даними (метро ≈ 45% поїздок громадським транспортом).
VAGA_METRO = 5.0
R_MAGAZYNY = 150.0             # вага місця приїжджих — магазини й кафе в 150 м
MAGAZYNY_KAFE = ('shop24', 'b1_super', 'b1_alk', 'b1_mall', 'b1_cafe', 'b1_fastfood', 'b1_bars')

# ---- ПІША МЕРЕЖА (рішення Андрія 07.10, п. 4) ----
# Магістралі (motorway, trunk) — пішки лише з позначеним тротуаром; решта
# доріг, проїзди й сходи — пішки. Тротуар, що не сходиться з мережею
# (кінець лінії, не прив'язаний до переходу), з'єднується з найближчою
# іншою лінією в 25 м; шматок мережі, що лишився окремо, — з головною
# мережею в 50 м. Без цього 25% мешканців стояли на окремих шматках, і
# масив зводився в одну точку (провулок Матущака — 8 893 осіб).
MAGISTRALI = ('motorway', 'motorway_link', 'trunk', 'trunk_link')
PRYVIAZKA_M, SHMATOK_M = 25.0, 50.0

# ---- ЧИЯ ЛІНІЯ (рішення Андрія 07.10, друге) ----
# Тротуар уздовж широкої магістралі буває за 40–60 м від осі; паралельність
# відрізняє його від доріжки двору поруч.
PARALEL_M, PARALEL_KUT, BLYZKO_M = 60.0, 20.0, 35.0
KROK_OSI_M = 20.0

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
    # «out center bb» віддає лише рамку — центр з неї
    b = el.get('bounds')
    if b: return ((b['minlat'] + b['maxlat']) / 2, (b['minlon'] + b['maxlon']) / 2)
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

    def within(s, la, lo, rad):
        """[(відстань, індекс)] усіх точок у rad м"""
        my, mx = mdeg(la)
        n = int(max(rad / my, rad / mx) / s.c) + 1
        ci, cj = int(la / s.c), int(lo / s.c)
        out = []
        for i in range(ci - n, ci + n + 1):
            for j in range(cj - n, cj + n + 1):
                for p, k in s.g.get((i, j), ()):
                    d = math.hypot((p[0] - la) * my, (p[1] - lo) * mx)
                    if d <= rad: out.append((d, k))
        return out


def pishi_liniyi(raw):
    """лінії, якими ходять пішки: вулиці (магістралі — лише з тротуаром),
    доріжки, проїзди, сходи"""
    out = []
    for w in VR.vulytsi(raw):
        t = w.get('tags') or {}
        if t.get('highway') in MAGISTRALI and t.get('sidewalk') not in ('both', 'left', 'right', 'yes'):
            continue
        out.append(w)
    return out + list(raw.get('foot') or []) + list(raw.get('pishky_dod') or [])


def transport(raw):
    """[(lat, lon, метро?)]: входи метро (станція без входів — сама станція)
    і наземні зупинки, разом із залізничними станціями"""
    out, z_vkhodamy = [], set()
    st = [e for e in raw.get('b1_metro') or [] if (e.get('tags') or {}).get('railway') == 'station']
    vkh = [e for e in raw.get('b1_metro') or [] if (e.get('tags') or {}).get('railway') == 'subway_entrance']
    metro_st = [e for e in st if (e.get('tags') or {}).get('station') == 'subway']
    for e in vkh:
        c = centr(e)
        if not c: continue
        out.append((c[0], c[1], True))
        near = min(metro_st, key=lambda s_: dist_m(c, centr(s_)), default=None)
        if near is not None and dist_m(c, centr(near)) <= 500: z_vkhodamy.add(near['id'])
    for e in metro_st:
        if e['id'] not in z_vkhodamy and (c := centr(e)): out.append((c[0], c[1], True))
    for e in st:
        if (e.get('tags') or {}).get('station') != 'subway' and (c := centr(e)): out.append((c[0], c[1], False))
    for e in raw.get('b1_stops') or []:
        if (c := centr(e)): out.append((c[0], c[1], False))
    return out


def mistsia_pryizhdzhykh(raw):
    """[(lat, lon, вага)]: ТЦ, ринки, парки, вокзали і місця з магазинами та
    кафе (клітинки 150 м); вага — магазини й кафе в 150 м, не менше 1.
    Окремого ручного «центру» немає: центр виходить сам — там їх більше."""
    seen, pts = set(), []
    for k in MAGAZYNY_KAFE:
        for e in raw.get(k) or []:
            if (e.get('type'), e.get('id')) in seen: continue
            seen.add((e.get('type'), e.get('id')))
            if (c := centr(e)): pts.append(c)
    g = Grid(pts, cell=0.002)
    vaga = lambda la, lo: max(1, len(g.within(la, lo, R_MAGAZYNY)))
    out = []
    obj = (list(raw.get('b1_mall') or []) + list(raw.get('b1_market') or []) + list(raw.get('park') or [])
           + [e for e in raw.get('b1_metro') or [] if (e.get('tags') or {}).get('railway') == 'station'
              and (e.get('tags') or {}).get('station') not in ('subway',)])
    for e in obj:
        if (c := centr(e)): out.append((c[0], c[1], vaga(*c)))
    kl = collections.defaultdict(list)
    C = 150.0 / 111320
    for la, lo in pts: kl[(int(la / C), int(lo / C))].append((la, lo))
    for v in kl.values():
        la, lo = sum(p[0] for p in v) / len(v), sum(p[1] for p in v) / len(v)
        out.append((la, lo, vaga(la, lo)))
    return out


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
                if vaga == 'площа':
                    s = ploshcha(e)
                    # Університет у OSM — відношення з корпусів по всьому місту:
                    # рамка КНУ 29 км², Драгоманова 36 км², а центр рамки — ніде.
                    # Такі цілі пропускаємо, решту обмежуємо: одна промзона
                    # не має важити як район (знімок 07.10, ZVIT-32).
                    if e.get('type') == 'relation' and s > ROZKYD_M2: continue
                    w = min(max(s, 200.0), MAKS_PLOSHCHA_M2)
                else:
                    w = VAGA_TYPU.get(k, 1)
                acc.append((c[0], c[1], w))
        out[m] = acc
    return out


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
    if not raw.get('pishky_dod'):
        print('УВАГА: у знімку немає pishky_dod (проїзди, сходи) — двори мікрорайонів будуть окремими шматками')
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
    liniyi = pishi_liniyi(raw)
    lin_of = collections.defaultdict(set)      # вузол -> лінії, щоб не з'єднувати лінію саму з собою
    for li, w in enumerate(liniyi):
        g = w.get('geometry') or []
        ks = [key(p['lat'], p['lon']) for p in g]
        for k in ks: lin_of[node(k)].add(li)
        for u, v in zip(ks, ks[1:]):
            if u == v: continue
            d = dist_m(u, v)
            if d <= 0: continue
            a, b = node(u), node(v)
            A += [a, b]; B += [b, a]; W += [d, d]
    N = len(coord)
    stup = np.bincount(np.array(A, dtype=np.int64), minlength=N)
    vsi = Grid(coord, cell=0.0004)
    # кінець лінії, що ні з чим не сходиться, — до найближчої іншої лінії
    n_kin = 0
    for a in np.where(stup == 1)[0]:
        la, lo = coord[a]
        cand = [(d, k) for d, k in vsi.within(la, lo, PRYVIAZKA_M) if k != a and not (lin_of[k] & lin_of[a])]
        if cand:
            d, k = min(cand)
            A += [a, k]; B += [k, a]; W += [max(d, 1.0)] * 2; n_kin += 1
    G = csr_matrix((W, (A, B)), shape=(N, N))
    nc, lab = connected_components(G, directed=False)
    big = np.bincount(lab).argmax()
    # шматки, що лишились окремо, — з головною мережею в 50 м
    n_sh = 0
    gol = Grid([coord[i] for i in np.where(lab == big)[0]], cell=0.0006)
    gol_ids = np.where(lab == big)[0]
    krashche = {}
    for i in np.where(lab != big)[0]:
        k = gol.nearest(coord[i][0], coord[i][1], SHMATOK_M)
        if k is None: continue
        d = dist_m(coord[i], coord[gol_ids[k]])
        if lab[i] not in krashche or d < krashche[lab[i]][0]: krashche[lab[i]] = (d, i, int(gol_ids[k]))
    for d, i, k in krashche.values():
        A += [i, k]; B += [k, i]; W += [max(d, 1.0)] * 2; n_sh += 1
    G = csr_matrix((W, (A, B)), shape=(N, N))
    nc, lab = connected_components(G, directed=False)
    big = np.bincount(lab).argmax()
    main_n = np.where(lab == big)[0]
    print(f'1) граф: ліній {len(liniyi):,}, вузлів {N:,}, ребер {len(W) // 2:,}; з\'єднано кінців {n_kin:,}, '
          f'шматків {n_sh:,}; найбільша компонента {len(main_n):,} ({100 * len(main_n) / N:.0f}%)')
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
    T = tsili(raw)
    tn = {}
    for m, lst in T.items():
        nodes, ws = [], []
        for la, lo, w in lst:
            k = snap(la, lo, 400)
            if k is not None: nodes.append(k); ws.append(w)
        tn[m] = (np.array(nodes, dtype=np.int64), np.array(ws, dtype=float))
        print(f'   мета «{m}»: цілей {len(lst):,}, у мережі {len(nodes):,}')
    # транспорт: вузол -> (метро?); метро переважає зупинку на тому самому вузлі
    tr = {}
    for la, lo, metro in transport(raw):
        k = snap(la, lo, 300)
        if k is not None: tr[k] = tr.get(k, False) or metro
    trn = np.array(sorted(tr), dtype=np.int64)
    TRN_M = np.array([tr[k] for k in trn])
    TRN_R = np.where(TRN_M, R_METRO, R_ZUPYNKA)
    TRN_W = np.where(TRN_M, VAGA_METRO, 1.0)
    print(f'   транспорт у мережі: входів метро {int(TRN_M.sum()):,}, зупинок {int((~TRN_M).sum()):,}')
    MP = mistsia_pryizhdzhykh(raw)
    mp_n, mp_w = [], []
    for la, lo, w in MP:
        k = snap(la, lo, 400)
        if k is not None: mp_n.append(k); mp_w.append(w)
    mp_n, mp_w = np.array(mp_n, dtype=np.int64), np.array(mp_w, dtype=float)
    print(f'   місць для приїжджих: {len(MP):,}, у мережі {len(mp_n):,}')
    LIMIT = max(MAX_M * 1.25, R_METRO)

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

    def bali_transportu(d):
        """вага × exp(−d/τ) для зупинок і метро в їхньому радіусі, інакше 0"""
        return np.where(np.isfinite(d) & (d <= TRN_R), TRN_W * np.exp(-np.minimum(d, 1e6) / TAU), 0.0)

    def do_transportu(d):
        b = bali_transportu(d)
        ok = np.where(b > 0)[0]
        if not len(ok): return ok, None
        if len(ok) > K_CIL: ok = ok[np.argpartition(-b[ok], K_CIL)[:K_CIL]]
        return ok, b[ok] / b[ok].sum()

    # ---- маршрути з дому ----
    S_ = np.array(list(src.keys()), dtype=np.int64)
    R_ = np.array([src[k] for k in S_], dtype=float)
    BATCH = 64
    obsiah = collections.Counter()            # поїздки транспортом: робота, приїжджі
    do_metro = 0.0
    st = collections.Counter()
    print('3) маршрути з дому…', flush=True)
    for b0 in range(0, len(S_), BATCH):
        idx = S_[b0:b0 + BATCH]
        D, Pr = dijkstra(G, directed=False, indices=idx, limit=LIMIT, return_predecessors=True)
        for r, s in enumerate(idx):
            R = R_[b0 + r]
            dt = D[r, trn] if len(trn) else np.zeros(0)
            def transportom(L, m):
                nonlocal do_metro
                ok, p = do_transportu(dt) if len(trn) else ((), None)
                if p is None:
                    st[m + ': недосяжно'] += 1; return False
                for j, pj in zip(ok, p):
                    walk(Pr[r], s, trn[j], L * pj)
                    if TRN_M[j]: do_metro += L * pj
                st[m + ': транспортом'] += 1
                return True
            for m, (keys, share, _v) in METY.items():
                nodes, ws = tn[m]
                if not len(nodes) and m not in TRANSPORTOM: continue
                ok, p = rozpodil(D[r, nodes], ws) if len(nodes) else (nodes, None)
                if m == 'робота':
                    # частка — транспортом завжди; решта — до роботи поруч, а
                    # немає її в межах ходьби — теж транспортом
                    t_ = R * share * TRANSPORT_ROBOTA
                    w_ = R * share - t_
                    if p is None: t_, w_ = t_ + w_, 0.0
                    if w_:
                        for j, pj in zip(ok, p): walk(Pr[r], s, nodes[j], w_ * pj)
                        st[m + ': пішки'] += 1
                    if transportom(t_, m): obsiah['робота'] += t_
                elif p is not None:
                    st[m + ': пішки'] += 1
                    for j, pj in zip(ok, p): walk(Pr[r], s, nodes[j], R * share * pj)
                elif m in TRANSPORTOM:
                    transportom(R * share, m)
                else:
                    st[m + ': недосяжно'] += 1
            # приїжджі — поїздки транспортом понад шість мет: з дому до зупинки
            if PRYIZHDZHI > 0 and transportom(R * PRYIZHDZHI, 'приїжджі'):
                obsiah['приїжджі'] += R * PRYIZHDZHI
        if (b0 // BATCH) % 50 == 0:
            print(f'   {b0 + len(idx):,} / {len(S_):,} · {time.time() - t0:.0f} c', flush=True)
    print('   ' + ', '.join(f'{k} {v:,}' for k, v in sorted(st.items())))
    vsogo_tr = sum(obsiah.values())
    print(f'   поїздок транспортом: робота {obsiah["робота"]:,.0f}, приїжджі {obsiah["приїжджі"]:,.0f}; '
          f'з них до метро {100 * do_metro / max(vsogo_tr, 1):.0f}% (звірка: метро ≈ 45% поїздок громадським транспортом)')

    # ---- приїзд: від зупинок і метро до роботи й до місць приїжджих ----
    def pryizd(obs, nodes, ws, nazva):
        """obs осіб приїжджають до цілей ∝ вага; кожна ціль — з K_CIL зупинок
        чи входів метро з найбільшими балами (як і з дому)"""
        if obs <= 0 or not len(nodes) or not len(trn): return
        nb = len(nodes)
        best = np.zeros((nb, K_CIL)); bs = np.full((nb, K_CIL), -1, dtype=np.int64)
        for b0 in range(0, len(trn), BATCH):
            idx = trn[b0:b0 + BATCH]
            D = dijkstra(G, directed=False, indices=idx, limit=LIMIT)[:, nodes]     # зупинки × цілі
            Sb = np.where(np.isfinite(D) & (D <= TRN_R[b0:b0 + BATCH, None]),
                          TRN_W[b0:b0 + BATCH, None] * np.exp(-np.minimum(D, 1e6) / TAU), 0.0).T
            cat = np.concatenate([best, Sb], axis=1)
            ci = np.concatenate([bs, np.broadcast_to(np.arange(b0, b0 + len(idx)), (nb, len(idx)))], axis=1)
            o = np.argsort(-cat, axis=1)[:, :K_CIL]
            best = np.take_along_axis(cat, o, 1); bs = np.take_along_axis(ci, o, 1)
        dosyazh = best[:, 0] > 0
        A_ = np.where(dosyazh, ws, 0.0)
        if not A_.sum(): return
        prybulo = obs * A_ / A_.sum()
        po_zup = collections.defaultdict(list)
        for j in np.where(dosyazh)[0]:
            ok = best[j] > 0
            p = best[j][ok] / best[j][ok].sum()
            for k, pk in zip(bs[j][ok], p): po_zup[int(k)].append((int(nodes[j]), prybulo[j] * pk))
        zk = sorted(po_zup)
        for b0 in range(0, len(zk), BATCH):
            idx = trn[zk[b0:b0 + BATCH]]
            _D, Pr = dijkstra(G, directed=False, indices=idx, limit=LIMIT, return_predecessors=True)
            for r, k in enumerate(zk[b0:b0 + BATCH]):
                for t, L in po_zup[k]: walk(Pr[r], int(trn[k]), t, L)
        print(f'4) приїзд «{nazva}»: {obs:,.0f} осіб до {int(dosyazh.sum()):,} цілей від {len(zk):,} зупинок і входів')
    pryizd(obsiah['робота'], *tn['робота'], 'робота')
    pryizd(obsiah['приїжджі'], mp_n, mp_w, 'приїжджі')

    # ---- зведення по відрізках між перехрестями ----
    # Тротуари й доріжки вздовж вулиці — частина її коридору, і їхні потоки
    # СКЛАДАЮТЬСЯ (рішення Андрія 07.10, п. 3): навантаження × довжина всіх
    # ребер коридору ділиться на довжину осі — сума поперек, середнє вздовж.
    # Чия лінія (рішення Андрія 07.10, друге): паралельна осі (кут ≤ 20°) у
    # 60 м — тротуар цієї вулиці; решта — найближча вісь у 35 м. Вісь узята
    # точками кожні 20 м: раніше бралася середина шматка осі, і тротуар біля
    # кінця довгого прямого шматка магістралі не належав нікому.
    from scipy.spatial import cKDTree
    SEG = VR.build(VR.vulytsi(raw))
    seg_of = VR.rebra(SEG)
    KX = 111320.0 * math.cos(math.radians(50.45))
    xy = lambda la, lo: (lo * KX, la * 111320.0)
    SX, SY, SA, SS = [], [], [], []
    sids = list(SEG)
    for si, sid in enumerate(sids):
        for a, b in zip(SEG[sid]['pts'], SEG[sid]['pts'][1:]):
            (x1, y1), (x2, y2) = xy(*a), xy(*b)
            L = math.hypot(x2 - x1, y2 - y1)
            if L <= 0: continue
            kut = math.degrees(math.atan2(y2 - y1, x2 - x1)) % 180
            for t in range(int(L // KROK_OSI_M) + 1):
                f = min(1.0, (t * KROK_OSI_M + KROK_OSI_M / 2) / L)
                SX.append(x1 + (x2 - x1) * f); SY.append(y1 + (y2 - y1) * f); SA.append(kut); SS.append(si)
    SA, SS = np.array(SA), np.array(SS)
    tree = cKDTree(np.column_stack([SX, SY]))
    acc = collections.defaultdict(float)
    reshta = []                               # ребра не з осі: (середина, кут, навантаження × довжина)
    for (u, v), c in load.items():
        a, b = coord[u], coord[v]
        d = dist_m(a, b) or 1.0
        sid = seg_of.get((a, b))
        if sid is not None:
            acc[sid] += c * d; continue
        (x1, y1), (x2, y2) = xy(*a), xy(*b)
        reshta.append(((x1 + x2) / 2, (y1 + y2) / 2, math.degrees(math.atan2(y2 - y1, x2 - x1)) % 180, c * d))
    if reshta:
        R = np.array(reshta)
        dd, ix = tree.query(R[:, :2], k=12, distance_upper_bound=PARALEL_M)
        ok = np.isfinite(dd)
        ixc = np.where(ok, ix, 0)
        dk = np.abs(R[:, 2:3] - SA[ixc]); dk = np.minimum(dk, 180 - dk)
        par = ok & (dk <= PARALEL_KUT)
        perp = ok & (dd <= BLYZKO_M)
        # найближча паралельна точка осі; немає — найближча будь-яка в 35 м
        j_par = np.where(par.any(1), par.argmax(1), -1)
        j_blyz = np.where(perp.any(1), perp.argmax(1), -1)
        j = np.where(j_par >= 0, j_par, j_blyz)
        rows = np.where(j >= 0)[0]
        for r_, s_ in zip(rows, SS[ixc[rows, j[rows]]]):
            acc[sids[s_]] += R[r_, 3]
        print(f'   ребер поза осями {len(R):,}: паралельних у {PARALEL_M:.0f} м {int((j_par >= 0).sum()):,}, '
              f'інших у {BLYZKO_M:.0f} м {int(((j_par < 0) & (j_blyz >= 0)).sum()):,}, нічиїх {int((j < 0).sum()):,}')
    items = []
    for sid, s in SEG.items():
        g = s['pts']; stp = max(1, len(g) // 10)
        geo = [[round(p[0], 5), round(p[1], 5)] for p in g[::stp]]
        if geo[-1] != [round(g[-1][0], 5), round(g[-1][1], 5)]:
            geo.append([round(g[-1][0], 5), round(g[-1][1], 5)])
        L_os = sum(dist_m(p, q) for p, q in zip(g, g[1:])) or 1.0
        potik = int(round(TUDY_NAZAD * acc[sid] / L_os)) if acc.get(sid) else 0
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
    perevirka_metro(raw, items)


def perevirka_metro(raw, items, log=print):
    """Зовнішня перевірка (рішення Андрія 07.10, п. 5): пасажиропотік станцій
    метро (2017) проти модельованого потоку в 300 м від входів — кореляція
    рангів Спірмена. Міра станції — Σ потік × довжина відрізків, що мають
    точку в 300 м від входу (люди, що підходять до станції, проходять тут).
    Параметри під цю перевірку не підганяються."""
    pp = os.path.join(DATA, 'metro_pasazhyropotik_2017.json')
    if not os.path.exists(pp): log('   немає data/metro_pasazhyropotik_2017.json — перевірку пропущено'); return None
    from scipy.stats import spearmanr
    norm = lambda s: (s or '').replace('ʼ', "'").replace('’', "'").replace('«', '').replace('»', '').strip().lower()
    PS = {norm(k): v for k, v in json.load(open(pp, encoding='utf-8'))['stantsii'].items()}
    st = [e for e in raw.get('b1_metro') or [] if (e.get('tags') or {}).get('station') == 'subway'
          and (e.get('tags') or {}).get('railway') == 'station']
    vkh = [centr(e) for e in raw.get('b1_metro') or [] if (e.get('tags') or {}).get('railway') == 'subway_entrance']
    tochky = collections.defaultdict(list)
    for c in vkh:
        if not c: continue
        s_ = min(st, key=lambda e: dist_m(c, centr(e)), default=None)
        if s_ is not None and dist_m(c, centr(s_)) <= 500: tochky[s_['id']].append(c)
    g = Grid([tuple(p) for it in items for p in it[0]], cell=0.003)
    vlas = [k for k, it in enumerate(items) for _p in it[0]]
    dov = [sum(dist_m(p, q) for p, q in zip(it[0], it[0][1:])) for it in items]
    rows = []
    for e in st:
        nm = norm((e.get('tags') or {}).get('name'))
        if nm not in PS: continue
        pts = tochky.get(e['id']) or [centr(e)]
        vids = {vlas[k] for c in pts for _d, k in g.within(c[0], c[1], 300)}
        rows.append((nm, PS[nm], sum(items[k][2] * dov[k] for k in vids) / 1000))
    if len(rows) < 10: log(f'   метро: зіставлено лише {len(rows)} станцій — перевірку пропущено'); return None
    rho, pv = spearmanr([r[1] for r in rows], [r[2] for r in rows])
    log(f'   метро: {len(rows)} станцій, кореляція рангів Спірмена ρ = {rho:.2f} (p = {pv:.3g})')
    return rho, rows


if __name__ == '__main__':
    main()
