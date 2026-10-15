# -*- coding: utf-8 -*-
"""Е8, перевірка (ZAVDANNYA-35, крок 2): R0–R12 × E1–E7 на наборі 36.14.

Код карти не чіпаємо: відрізки, ознаки, прив'язка подій і модель R3 — ті
самі, що в src/step4_engine.py (функції беремо звідти, цикл прив'язки
повторено тут), міняється лише відбір подій і те, що рахується далі.

Змінні середовища:
  NABIR  36_14 (за замовчуванням) — набір kod/nabir_36_14.csv.gz:
         подія в розрахунках, якщо v_rozrakhunkakh = 1; B — чинний клас B
  VYD    ключ виду чи механізму (ГП, ДТП, ГП_хуліг, …); кома — кілька
  LITE   1 — лише R0, R1, R2, R3, R9 (порівняння наборів)
  N_STAB прогонів відбору стійкості (20 — не 100: підходів і зрізів тут
         у ~10 разів більше, ніж у перенавчанні; поріг 70% той самий)
  OUT    тека для e8_<вид>_<набір>.json

Зрізи. Повних років два (2024, 2025), 2023 — 2,1 тис. подій, тож історія
12 міс. до кінця 2023 майже порожня. Тому ознаки рахуються «до дати T», а
перевірка — на наступних 6 і 12 місяцях (2026 — лише відомі місяці, без
двох останніх: затримка судів). Навчання моделей — на парі «ознаки до
T−h → події (T−h, T]», тобто без підглядання в ціль. Головний зріз —
T = 12.2025, навчання «2024 → 2025», як у перенавчанні.
"""
import os, sys, re, csv, gzip, json, math, time, heapq, collections
import numpy as np
K = os.path.dirname(os.path.abspath(__file__))
R = os.path.abspath(os.path.join(K, '..', '..', '..'))
sys.path.insert(0, os.path.join(R, 'src'))
import step4_engine as E
import rtm, rtm_tochky as RT, labels as L, mech as M

NABIR = os.environ.get('NABIR', '36_14')
# Набір перезбирається в workflow на свіжій базі подій і лягає в data/ (поправка 15.10)
NABIR_F = next((p for p in (os.path.join(R, 'data', 'nabir_36_14.csv.gz'), os.path.join(K, 'nabir_36_14.csv.gz')) if os.path.exists(p)), None)
# Види, яких у 2024 зібрано неповно (поправка центрального чату 15.10)
NEPOVNI = {'МАЙ', 'НАС', 'НАР'}
LITE = os.environ.get('LITE', '0') == '1'
N_RUNS = int(os.environ.get('N_STAB', '20'))
OUT = os.environ.get('OUT', os.path.join(K, 'e8_vyhid'))
PCTS = (0.01, 0.05, 0.10, 0.20)
TOCHKA_M = 50.0          # точка = 50 м довжини (протокол, E1)
N_BOOT = 500
log = lambda *a: print(*a, flush=True)


def mshift(m, k):
    y, mm = int(m[:4]), int(m[5:7])
    t = y * 12 + mm - 1 + k
    return f'{t // 12:04d}-{t % 12 + 1:02d}'


def misiatsi(a, b):
    """місяці (a, b] — a виключно"""
    out, m = [], mshift(a, 1)
    while m <= b: out.append(m); m = mshift(m, 1)
    return out


# ---------------------------------------------------------------- події
def nabir_36_14():
    p = NABIR_F
    log(f'   набір 36.14 — {p}')
    out = {}
    for r in csv.DictReader(gzip.open(p, 'rt', encoding='utf-8')):
        out[r['doc_id']] = r['v_rozrakhunkakh'] == '1'
    return out


def podii():
    """E.podii, але клас B замінено набором 36.14: подія в розрахунках, якщо
    речення адреси описує саму подію. Документи, новіші за набір (після
    08.10), лишаються за чинним класом — їх небагато, а перепрохід не наш."""
    import step3_map as S3
    if NABIR == 'B':
        return E.podii(log)
    NB = nabir_36_14()
    orig = S3.vybir
    st = collections.Counter()
    def vybir(c, **kw):
        V = orig(c, **kw)
        for d, tk in V['TKD'].items():
            if d in NB:
                st['у наборі'] += 1
                if NB[d] != (tk.get('klass') == 'B'): st['змінився'] += 1
                V['TKD'][d] = dict(tk, klass='B' if NB[d] else 'X')
        return V
    S3.vybir = vybir
    try:
        ev, drop = E.podii(log)
    finally:
        S3.vybir = orig
    log(f'   набір 36.14: документів у наборі {st["у наборі"]:,}, клас змінився в {st["змінився"]:,}')
    return ev, drop


# ---------------------------------------------------------------- мережа
def sosidy(SEG, sids, hmax):
    """Сусідство відрізків по мережі для NTKDE (R2): (i, j, відстань між
    серединами по мережі, множник рівного поділу). Рівний поділ на
    перехресті (Okabe та ін. 2009): маса ділиться на (ступінь − 1) гілок,
    тож згладжування не «множить» події на густих перехрестях. Множник
    береться вздовж найкоротшого шляху — наближення, точний ESK для
    кількох шляхів тут не потрібен (ширини 200–800 м — 1–6 кварталів)."""
    import vidrizky as VR
    idx = {s: i for i, s in enumerate(sids)}
    ends = []
    inc = collections.defaultdict(list)
    for i, s in enumerate(sids):
        a, b = VR.key(*SEG[s]['pts'][0]), VR.key(*SEG[s]['pts'][-1])
        ends.append((a, b)); inc[a].append(i); inc[b].append(i)
    ln = np.array([SEG[s]['len'] for s in sids])
    I, J, D, W = [], [], [], []
    for i in range(len(sids)):
        best = {i: 0.0}
        fac = {i: 1.0}
        # стан — (відстань до вузла, вузол, множник)
        hq = [(ln[i] / 2, ends[i][0], 1.0), (ln[i] / 2, ends[i][1], 1.0)]
        seen = {}
        while hq:
            d, v, f = heapq.heappop(hq)
            if d > hmax or seen.get(v, 1e18) <= d: continue
            seen[v] = d
            k = max(len(inc[v]) - 1, 1)
            for j in inc[v]:
                if j == i: continue
                dj = d + ln[j] / 2
                fj = f / k
                if dj <= hmax and dj < best.get(j, 1e18):
                    best[j] = dj; fac[j] = fj
                a, b = ends[j]
                w = b if a == v else a
                if d + ln[j] <= hmax: heapq.heappush(hq, (d + ln[j], w, fj))
        for j, d in best.items():
            I.append(i); J.append(j); D.append(d); W.append(fac[j])
    return np.array(I), np.array(J), np.array(D), np.array(W)


def ntkde(NB_, n, h, cnt, length):
    """Щільність подій на метр у мережевому околі ширини h: Σ k·події ÷ Σ k·довжина.
    Ділимо на зважену довжину, а не беремо суму подій: інакше довгий
    відрізок вигравав би просто довжиною (та сама вада, що в hit_rate)."""
    import scipy.sparse as sp
    I, J, D, W = NB_
    m = D <= h
    k = (1 - (D[m] / h) ** 2) * W[m]
    Km = sp.csr_matrix((k, (I[m], J[m])), shape=(n, n))
    return (Km @ cnt) / np.maximum(Km @ length, 1e-9)


def kde_sitka(ev_xy, w, Q, h):
    """R9: KDE на сітці 150 м (Гаусове ядро ширини h), значення — у клітинці
    точки Q (середини відрізка чи точки)."""
    if len(ev_xy) == 0: return np.zeros(len(Q))
    lat0 = 50.45
    my, mx = 111320.0, 111320.0 * math.cos(math.radians(lat0))
    C = 150.0
    gx = lambda la, lo: (np.floor(la * my / C).astype(int), np.floor(lo * mx / C).astype(int))
    ei, ej = gx(ev_xy[:, 0], ev_xy[:, 1])
    qi, qj = gx(Q[:, 0], Q[:, 1])
    i0, j0 = min(ei.min(), qi.min()) - 10, min(ej.min(), qj.min()) - 10
    ni, nj = max(ei.max(), qi.max()) - i0 + 11, max(ej.max(), qj.max()) - j0 + 11
    G = np.zeros((ni, nj))
    np.add.at(G, (ei - i0, ej - j0), w)
    from scipy.ndimage import gaussian_filter
    S = gaussian_filter(G, sigma=h / C, mode='constant', truncate=3.0)
    return S[qi - i0, qj - j0]


# ---------------------------------------------------------------- мірила
def ranh_dovzhyna(dens, length, pct):
    o = np.argsort(-dens, kind='stable')
    c = np.cumsum(length[o])
    k = int(np.searchsorted(c, pct * length.sum())) + 1
    return o[:k]


def e1e2(dens, y, length):
    """E1 — влучність і PAI на 1/5/10/20% довжини; E2 — PEI: влучність ÷
    найкраща можлива на тому самому покритті (верхні за справжньою
    щільністю цілі)."""
    out = {}
    tot = max(y.sum(), 1e-9)
    for p in PCTS:
        top = ranh_dovzhyna(dens, length, p)
        hit = float(y[top].sum() / tot)
        share = float(length[top].sum() / length.sum())
        best = ranh_dovzhyna(y / length, length, share)
        hb = float(y[best].sum() / tot)
        out[f'{int(p * 100)}'] = dict(hit=round(hit, 4), PAI=round(hit / share, 3),
                                      PEI=round(hit / hb, 3) if hb else None)
    return out


def butstrep(dens_by, y, length, blok, pct=0.10, ref=('R0', 'R2', 'R3')):
    """E3 — бутстреп блоками 1 км, 500 повторів: межі PAI і парна різниця з
    R0, R2 і R3 (ті самі блоки в кожному повторі; R3 — щоб R10–R11 мали
    «приріст понад R3» з похибкою)."""
    ub, inv = np.unique(blok, return_inverse=True)
    nb = len(ub)
    tot_e = np.bincount(inv, weights=y, minlength=nb)
    tot_l = np.bincount(inv, weights=length, minlength=nb)
    cov = {}
    for a, d in dens_by.items():
        top = np.zeros(len(y), bool); top[ranh_dovzhyna(d, length, pct)] = True
        cov[a] = (np.bincount(inv, weights=y * top, minlength=nb),
                  np.bincount(inv, weights=length * top, minlength=nb))
    rng = np.random.default_rng(35)
    S = {a: np.zeros(N_BOOT) for a in dens_by}
    for b in range(N_BOOT):
        c = np.bincount(rng.integers(0, nb, nb), minlength=nb).astype(float)
        E_, L_ = (c * tot_e).sum(), (c * tot_l).sum()
        for a, (ce, cl) in cov.items():
            S[a][b] = ((c * ce).sum() / max(E_, 1e-9)) / max((c * cl).sum() / L_, 1e-9)
    out = {}
    for a in dens_by:
        o = dict(lo=round(float(np.percentile(S[a], 2.5)), 3), hi=round(float(np.percentile(S[a], 97.5)), 3))
        for r in ref:
            if r in S and r != a:
                d = S[a] - S[r]
                o[f'різниця_з_{r}'] = [round(float(np.percentile(d, 2.5)), 3), round(float(np.mean(d)), 3),
                                       round(float(np.percentile(d, 97.5)), 3)]
        out[a] = o
    return out


def spirmen(a, b):
    ra = np.argsort(np.argsort(a)); rb = np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1])


def zhakkar(a, b, length, pct=0.05):
    A = set(ranh_dovzhyna(a, length, pct).tolist()); B = set(ranh_dovzhyna(b, length, pct).tolist())
    return len(A & B) / max(len(A | B), 1)


def spravdzh(mu, y, length, pct=0.05):
    """E5 — частка показаних (верхні 5% довжини), де подій у межах M/2…2M, і
    спостережене ÷ прогноз за децилями прогнозу"""
    top = ranh_dovzhyna(mu / length, length, pct)
    m = mu[top]; o = y[top]
    ok = float(((o >= m / 2) & (o <= 2 * m)).mean())
    q = np.argsort(mu)
    dec = [round(float(y[c].sum() / max(mu[c].sum(), 1e-9)), 2) for c in np.array_split(q, 10)]
    return dict(частка_M=round(ok, 3), спост_прогноз_децилі=dec)


def perekis(dens, y, length, rai, pct=0.05):
    """E7 — частка верхніх 5% довжини в районі ÷ частка подій району"""
    top = np.zeros(len(y), bool); top[ranh_dovzhyna(dens, length, pct)] = True
    out = {}
    for r in sorted(set(rai.tolist())):
        if not r: continue
        m = rai == r
        sl = length[m & top].sum() / max(length[top].sum(), 1e-9)
        se = y[m].sum() / max(y.sum(), 1e-9)
        out[r] = round(float(sl / se), 2) if se > 0 else None
    v = [x for x in out.values() if x]
    return dict(райони=out, макс=max(v) if v else None, мін=min(v) if v else None,
                сер_лог=round(float(np.mean(np.abs(np.log(v)))), 3) if v else None)


# ---------------------------------------------------------------- головне
def main():
    t0 = time.time()
    raw = json.load(open(E.RAW, encoding='utf-8'))
    F = E.oznaky(raw, log)
    SEG, sids, mid, slen, X = F['SEG'], F['sids'], F['mid'], F['slen'], F['X']
    cname, ctyp, expo, VR = F['cname'], F['ctyp'], F['expo'], F['VR']
    n = len(sids)
    idx = {s: i for i, s in enumerate(sids)}
    ev, drop = podii()
    last = max(e['d'] for e in ev)
    # відомі місяці — без двох останніх (затримка судів), як вікно карти
    KNOWN = mshift(last[:7], -2)
    log(f'подій у розрахунках: {len(ev):,}; остання дата {last}; відомі місяці — до {KNOWN}')

    # ---- точки, як у step4_engine ----
    _r2 = set(misiatsi(mshift(last[:7], -24), last[:7]))
    TP = RT.kandydaty(raw, VR.vulytsi(raw), [], VR)
    S_ = RT.Sitka([(t['la'], t['lo']) for t in TP])
    ist = [0] * len(TP)
    for e in ev:
        if e.get('vul') or e['m'] not in _r2: continue
        for d, k in S_.blyzki(e['la'], e['lo'], RT.R_TOCHKA):
            if d <= (RT.R_PEREKH if TP[k]['typ'] == 'перехрестя' else RT.R_TOCHKA): ist[k] += 1
    nal = RT.nalezhnist(ev, TP, ist)
    NP_ = len(TP)
    log(f'точок-кандидатів {NP_:,}; подій точок {sum(1 for x in nal if x is not None):,}')

    # ---- прив'язка: цикл step4_engine.main (лінії — події не точок) ----
    six = list(L.ORDER)
    PV = VR.Pryviazka(SEG)
    Y = collections.defaultdict(lambda: np.zeros(n))
    YP = collections.defaultdict(lambda: np.zeros(NP_))
    XYL = collections.defaultdict(list)       # (ключ) -> [(la, lo, місяць)] подій ліній, для R9
    XYP = collections.defaultdict(list)
    sl_all = {sid: VR.slova(SEG[sid]['name']) for sid in sids}
    po_slovu = collections.defaultdict(list)
    for sid, w_ in sl_all.items():
        for x in w_: po_slovu[x].append(sid)
    def korotka(e):
        ws = VR.slova(e['street'])
        if not ws: return None
        c_ = set.intersection(*[set(po_slovu.get(x, ())) for x in ws])
        c_ = [sid for sid in c_ if VR.ta_sama(ws, sl_all[sid])
              and VR.dovzhyna([(e['la'], e['lo']), SEG[sid]['pts'][len(SEG[sid]['pts']) // 2]]) <= 3000]
        if not c_ or len(c_) > E.KOROTKA[0] or sum(SEG[x]['len'] for x in c_) > E.KOROTKA[1]: return None
        return c_
    cache = {}
    for ie, e in enumerate(ev):
        ks = [e['th']] + ([e['mekh']] if e['mekh'] else [])
        if nal[ie] is not None:
            for k in ks:
                YP[(k, e['m'])][nal[ie]] += 1; XYP[k].append((TP[nal[ie]]['la'], TP[nal[ie]]['lo'], e['m']))
            continue
        if e.get('vul'):
            ck = ('vul', e['street'], round(e['la'], 3), round(e['lo'], 3))
            if ck not in cache: cache[ck] = korotka(e)
            c_ = cache[ck]
            if not c_: continue
            for k in ks:
                for sid in c_:
                    Y[(k, e['m'])][idx[sid]] += 1 / len(c_)
                XYL[k].append((e['la'], e['lo'], e['m']))
            continue
        ck = (round(e['la'], 5), round(e['lo'], 5), e['street'])
        if ck not in cache:
            cache[ck] = PV.znaity(e['la'], e['lo'], E.SNAP_M, VR.vulytsia(e['street']))[0]
        s = cache[ck]
        if s is None: continue
        for k in ks:
            Y[(k, e['m'])][idx[s]] += 1; XYL[k].append((e['la'], e['lo'], e['m']))
    log(f'прив\'язка готова, {time.time() - t0:.0f} с')

    # ---- блоки, райони, захід/схід ----
    blok = np.array([int(la * 111.32) * 100000 + int(lo * 111.32 * math.cos(math.radians(50.45))) for la, lo in mid])
    PXY = np.array([[t['la'], t['lo']] for t in TP])
    blokP = np.array([int(la * 111.32) * 100000 + int(lo * 111.32 * math.cos(math.radians(50.45))) for la, lo in PXY])
    import map_problems as MP
    B = json.load(open(os.path.join(E.DATA, 'borders.json'), encoding='utf-8'))
    dn = sorted(B)
    def raion(la, lo):
        for d in dn:
            if MP.in_ring(la, lo, B[d]): return d
        return ''
    rai = np.array([raion(*p) for p in mid]); raiP = np.array([raion(*p) for p in PXY])
    fold = np.array([(dn.index(r) % 5 + 1) if r else 0 for r in rai])
    foldP = np.array([(dn.index(r) % 5 + 1) if r else 0 for r in raiP])
    west = mid[:, 1] <= np.median(mid[:, 1]); westP = PXY[:, 1] <= np.median(mid[:, 1])
    lenP = np.full(NP_, TOCHKA_M)

    # ---- ознаки точок і люди ----
    XP, cnameP, ctypP, _cf, _cr = E.oznaky_tochok(raw, TP, SEG, F['byid'], log)
    JL = [cname.index(x) for x in E.LUDY if x in cname]
    CAND = [j for j in range(X.shape[1]) if j not in JL and cname[j] not in E.NE_KANDYDAT]
    JLP = [cnameP.index(x) for x in E.LUDY if x in cnameP]
    CANDP = [j for j in range(XP.shape[1]) if j not in JLP]
    log(f'ознак: лінії {len(CAND)} + люди {len(JL)}; точки {len(CANDP)} + люди {len(JLP)}')

    # R10 — поєднання: «є в 150 м» пар і трійок поширених типів
    def kombinacii(Xm, nm):
        TY = ['бари', 'алкоголь_винос', 'зупинки', 'метро', 'ТЦ', 'супермаркети', 'кафе',
              'фастфуд', 'АЗС', 'ринки', 'школи', 'паркінги', 'обмінники', 'банкомати']
        cols = {t: Xm[:, nm.index(f'{t}_є_150м')] for t in TY if f'{t}_є_150м' in nm}
        ts = sorted(cols, key=lambda t: -cols[t].mean())
        V, N = [], []
        for a in range(len(ts)):
            for b in range(a + 1, len(ts)):
                v = cols[ts[a]] * cols[ts[b]]
                if 0.002 < v.mean() < 0.9: V.append(v); N.append(f'{ts[a]}+{ts[b]}')
        top5 = ts[:5]
        for a in range(5):
            for b in range(a + 1, 5):
                for c in range(b + 1, 5):
                    v = cols[top5[a]] * cols[top5[b]] * cols[top5[c]]
                    if 0.002 < v.mean() < 0.9: V.append(v); N.append(f'{top5[a]}+{top5[b]}+{top5[c]}')
        return (np.column_stack(V) if V else np.zeros((len(Xm), 0))), N
    XK, NK = kombinacii(X, cname); XKP, NKP = kombinacii(XP, cnameP)
    log(f'R10: поєднань лінії {len(NK)}, точки {len(NKP)}')

    log('NTKDE: сусідство відрізків до 800 м...')
    NB_ = sosidy(SEG, sids, 800.0)
    log(f'   пар {len(NB_[0]):,}, {time.time() - t0:.0f} с')
    # сусідство точок для R2 точок — евклідове, до 400 м
    from sklearn.neighbors import BallTree
    tP = BallTree(np.radians(PXY), metric='haversine')
    indP, dP = tP.query_radius(np.radians(PXY), 400 / 6371000.0, return_distance=True)
    PI = np.concatenate([np.full(len(a), i) for i, a in enumerate(indP)])
    PJ = np.concatenate(indP); PD_ = np.concatenate(dP) * 6371000.0
    NBP = (PI, PJ, PD_, np.ones(len(PI)))

    KEYS = [(t, 'тема') for t in six] + [(m, 'механізм') for m in E.MEKH]
    if os.environ.get('VYD'):
        KEYS = [k for k in KEYS if k[0] in os.environ['VYD'].split(',')]

    os.makedirs(OUT, exist_ok=True)
    for key, vyd in KEYS:
        tk = time.time()
        res = perevirka(key, vyd, dict(
            n=n, NP_=NP_, Y=Y, YP=YP, XYL=XYL, XYP=XYP, X=X, XP=XP, cname=cname, ctyp=ctyp,
            cnameP=cnameP, ctypP=ctypP, JL=JL, CAND=CAND, JLP=JLP, CANDP=CANDP, XK=XK, NK=NK,
            XKP=XKP, NKP=NKP, expo=expo, slen=slen, lenP=lenP, mid=mid, PXY=PXY, blok=blok,
            blokP=blokP, rai=rai, raiP=raiP, fold=fold, foldP=foldP, west=west, westP=westP,
            NB_=NB_, NBP=NBP, KNOWN=KNOWN, six=six, sids=sids, names=F['names'], pop300=F['pop300']))
        res['_час_с'] = round(time.time() - tk)
        res['_набір'] = NABIR; res['_подій_у_розрахунках'] = len(ev); res['_остання_дата'] = last
        p = os.path.join(OUT, f'e8_{key}_{NABIR}.json')
        json.dump(res, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        log(f'-> {p} ({res["_час_с"]} с)')


# ---------------------------------------------------------------- один вид
def perevirka(key, vyd, D):
    th = key if vyd == 'тема' else M.simtheme(key)
    nm = L.THEMES.get(key, key) if vyd == 'тема' else M.simname(key)
    log(f'\n=== {nm} ({key}) ===')
    KNOWN = D['KNOWN']

    def cnt(YY, k, ms, size):
        v = np.zeros(size)
        for m in ms:
            a = YY.get((k, m))
            if a is not None: v += a
        return v

    def rozpad(YY, k, T, mon, size, hl=12.0):
        """R1: історія за mon місяців до T зі згасанням (піврозпад 12 міс.)"""
        v = np.zeros(size)
        for a in range(mon):
            m = mshift(T, -a)
            x = YY.get((k, m))
            if x is not None: v += x * 0.5 ** (a / hl)
        return v

    # Зрізи: (T, навчання (T', h) або None). Ознаки — «до T», ціль — 6 і 12 міс. після T.
    # МАЙ, НАС, НАР у 2024 зібрано неповно (МАЙ: 2024 І пів. — 669, 2025 І
    # пів. — 2 472; поправка центрального чату 15.10): модель, навчена на
    # 2024, вчилася б на дірах у даних. Для них історія — 6 міс., головний
    # зріз «2025 ІІ → 2026 І» з навчанням «2025 І → 2025 ІІ»; зрізи з
    # навчанням на 2024 лишаються, але з позначкою.
    nep = th in NEPOVNI
    LB = 6 if nep else 12
    if nep:
        ZR = [('2024-12', ('2024-06', 6)), ('2025-06', ('2024-12', 6)), ('2025-12', ('2025-06', 6))]
        POZN = {'2024-12': 'моделі навчено на 2024', '2025-06': 'моделі навчено на 2024'}
        TUNE, TUNE_H, T7, TWE, HOLH = '2025-06', 6, '2025-06', '2025-06', 6
    else:
        ZR = [('2024-06', None), ('2024-12', ('2024-06', 6)), ('2025-06', ('2024-12', 6)), ('2025-12', ('2024-12', 12))]
        POZN = {}
        TUNE, TUNE_H, T7, TWE, HOLH = '2024-12', 12, '2024-12', '2024-12', 12
    HOL = '2025-12'          # головний зріз
    # кінець цілі головного зрізу: 12 міс. — лише відомі місяці 2026
    HOL_END = min(mshift(HOL, HOLH), KNOWN)
    # E5 — лише повний період: 2026 І пів., без серпня–вересня 2026 (поправка 15.10)
    E5_END = min(mshift(HOL, 6), KNOWN)

    out = dict(вид=key, назва=nm, тема=th, проактивний=th in ('НАР', 'АЛК', 'ДОР'),
               неповні_періоди=nep, історія_міс=LB, позначки=POZN,
               головний=f'{HOL}→{HOLH}м')
    for odin in ('лінії', 'точки'):
        L_ = odin == 'лінії'
        YY = D['Y'] if L_ else D['YP']
        size = D['n'] if L_ else D['NP_']
        length = D['slen'] if L_ else D['lenP']
        expo = D['expo'] if L_ else np.ones(size)
        Xa = D['X'] if L_ else D['XP']
        JL_, CAND_ = (D['JL'], D['CAND']) if L_ else (D['JLP'], D['CANDP'])
        ctyp_ = D['ctyp'] if L_ else D['ctypP']
        cname_ = D['cname'] if L_ else D['cnameP']
        XL = Xa[:, JL_] if JL_ else np.zeros((size, 0))
        XC = Xa[:, CAND_]; tC = [ctyp_[j] for j in CAND_]
        XK, NK = (D['XK'], D['NK']) if L_ else (D['XKP'], D['NKP'])
        fold = D['fold'] if L_ else D['foldP']
        NBx = D['NB_'] if L_ else D['NBP']
        Q = D['mid'] if L_ else D['PXY']
        XY = D['XYL'] if L_ else D['XYP']
        blok = D['blok'] if L_ else D['blokP']
        rai = D['rai'] if L_ else D['raiP']
        west = D['west'] if L_ else D['westP']
        HW = (200, 400, 800) if L_ else (100, 200, 400)
        ntot = cnt(YY, key, misiatsi('2024-12', '2025-12'), size).sum()
        o = dict(подій_2025=int(ntot))
        if ntot < 50:
            o['пропущено'] = f'замало подій: {int(ntot)} у 2025'
            out[odin] = o; log(f'   {odin}: {o["пропущено"]}'); continue

        def r0(T): return cnt(YY, key, misiatsi(mshift(T, -LB), T), size)
        def r2(T, h, base):
            b = r0(T) if base == '12' else rozpad(YY, key, T, 24, size)
            return ntkde(NBx, size, h, b, length)
        def r9(T, h):
            pts = np.array([(a, b) for a, b, m in XY[key] if mshift(T, -LB) < m <= T]) if XY[key] else np.zeros((0, 2))
            return kde_sitka(pts, np.ones(len(pts)), Q, h)

        # ---- налаштування R2 і R9 на першому зрізі (не на головному) ----
        yA = cnt(YY, key, misiatsi(TUNE, mshift(TUNE, TUNE_H)), size)
        best2 = max(((h, b) for h in HW for b in ('12', 'R1')),
                    key=lambda hb: e1e2(r2(TUNE, *hb), yA, length)['10']['PAI'])
        best9 = max((150, 300, 600), key=lambda h: e1e2(r9(TUNE, h), yA, length)['10']['PAI'])
        o['R2_ширина_основа'] = best2; o['R9_ширина'] = best9
        log(f'   {odin}: R2 — {best2[0]} м, основа {best2[1]}; R9 — {best9} м')

        def hst(v, ref=None):
            h = np.log1p(v); r = np.log1p(ref) if ref is not None else h
            return (h - r.mean()) / (r.std() or 1.0)

        def nb_model(Htr, ytr, Hte, Xe_tr=None, Xe_te=None, te_rows=None, tr_rows=None, sel_X=True, typ_e=None):
            """R3-подібна: H (не штрафується) + люди + відбір стійкості серед
            кандидатів (і Xe). Повертає (прогноз, обрані типи, підгонка)."""
            tr = slice(None) if tr_rows is None else tr_rows
            te = slice(None) if te_rows is None else te_rows
            Hcols_tr = [c for c in (Htr if isinstance(Htr, list) else [Htr]) if c is not None]
            Hcols_te = [c for c in (Hte if isinstance(Hte, list) else [Hte]) if c is not None]
            Htr_ = np.column_stack(Hcols_tr + [XL[tr]]) if (Hcols_tr or XL.shape[1]) else None
            Hte_ = np.column_stack(Hcols_te + [XL[te]]) if (Hcols_te or XL.shape[1]) else None
            if sel_X:
                Xs_tr = XC[tr] if Xe_tr is None else np.column_stack([XC[tr], Xe_tr])
                Xs_te = XC[te] if Xe_te is None else np.column_stack([XC[te], Xe_te])
                ts = tC + (typ_e or [])
            else:
                Xs_tr, Xs_te, ts = Xe_tr, Xe_te, typ_e
            s = rtm.stijkist(Xs_tr, ytr, expo[tr], ts, H=Htr_, folds=fold[tr], runs=N_RUNS, log=lambda *a: None)
            A_tr = np.column_stack([x for x in (Htr_, Xs_tr[:, s['cols']]) if x is not None])
            A_te = np.column_stack([x for x in (Hte_, Xs_te[:, s['cols']]) if x is not None])
            f, _ = rtm.nb_fit(A_tr, ytr, expo[tr])
            p = rtm.nb_predict(f, A_te, expo[te])
            typy = sorted({(ts[c] or (cname_[CAND_[c]] if c < len(CAND_) else f'e{c}')) for c in s['cols']})
            return p, typy

        def gbm(Ftr, ytr, Fte, mono, ex_tr):
            """R5: градієнтний бустинг (LightGBM), Пуассон; довжина — експозицією
            через init_score, як у NB; монотонність за історією й людьми"""
            import lightgbm as lgb
            m = lgb.LGBMRegressor(objective='poisson', n_estimators=400, learning_rate=0.03,
                                  num_leaves=31, min_child_samples=40, subsample=0.8, subsample_freq=1,
                                  colsample_bytree=0.7, monotone_constraints=mono, verbose=-1, random_state=7)
            m.fit(Ftr, ytr, init_score=np.log(ex_tr))
            imp = m.booster_.feature_importance('gain')
            return (lambda Fx: m.predict(Fx, raw_score=True)), imp

        # інші види — для R11 (історія, згладжена по мережі)
        inshi = [k for k in D['six'] if k != th]

        rezult = {}     # зріз -> {підхід: щільність}, і прогноз M
        mu_by = {}
        typy_by = collections.defaultdict(dict)
        imp_by = {}
        for T, tr in ZR:
            dens = {}
            mu = {}
            h0 = r0(T)
            dens['R0'] = h0 / length; mu['R0'] = h0 * 12 / LB
            for mon in (24, 36):
                dens[f'R1_{mon}'] = rozpad(YY, key, T, mon, size) / length
            r2v = r2(T, *best2); dens['R2'] = r2v; mu['R2'] = r2v * length * 12 / LB
            dens['R9'] = r9(T, best9)
            if tr is not None:
                Tt, hh = tr
                ytr = cnt(YY, key, misiatsi(Tt, T), size)
                if ytr.sum() >= 30:
                    H_tr, H_te = hst(r0(Tt)), hst(r0(T), r0(Tt))
                    p3, t3 = nb_model(H_tr, ytr, H_te)
                    # горизонт навчання h міс.; прогноз M — на 12 міс.
                    sc = 12 / hh
                    dens['R3'] = p3 / length; mu['R3'] = p3 * sc; typy_by['R3'][T] = t3
                    if not LITE:
                        r2tr, r2te = r2(Tt, *best2) * length, r2v * length
                        G_tr, G_te = hst(r2tr), hst(r2te, r2tr)
                        p4, t4 = nb_model(G_tr, ytr, G_te)
                        dens['R4'] = p4 / length; mu['R4'] = p4 * sc; typy_by['R4'][T] = t4
                        p6, t6 = nb_model(None, ytr, None)
                        dens['R6'] = p6 / length; mu['R6'] = p6 * sc
                        # R5: ті самі ознаки (усі кандидати) + R2; монотонність — історія, люди
                        Ftr = np.column_stack([G_tr, XL, XC]); Fte = np.column_stack([G_te, XL, XC])
                        mono = [1] + [1] * XL.shape[1] + [0] * XC.shape[1]
                        pr, imp = gbm(Ftr, ytr, Fte, mono, expo)
                        lp = pr(Fte)
                        # бустинг вчився без довжини як експозиції в LightGBM лише
                        # через init_score; прогноз — у тих самих одиницях
                        p5 = np.exp(lp) * expo
                        dens['R5'] = p5 / length; mu['R5'] = p5 * sc
                        nmF = ['R2'] + [cname_[j] for j in JL_] + [cname_[j] for j in CAND_]
                        imp_by[T] = [nmF[i] for i in np.argsort(-imp)[:10]]
                        # R10: R3 + поєднання умов
                        if XK.shape[1]:
                            p10, t10 = nb_model(H_tr, ytr, H_te, XK, XK, typ_e=[f'комб:{x}' for x in NK])
                            dens['R10'] = p10 / length; mu['R10'] = p10 * sc
                            typy_by['R10'][T] = [t for t in t10 if str(t).startswith('комб')]
                        # R11: R3 + історія інших видів поруч (згладжена)
                        O_tr = np.column_stack([hst(ntkde(NBx, size, best2[0], cnt(YY, k2, misiatsi(mshift(Tt, -LB), Tt), size), length) * length)
                                                for k2 in inshi])
                        O_te = np.column_stack([hst(ntkde(NBx, size, best2[0], cnt(YY, k2, misiatsi(mshift(T, -LB), T), size), length) * length,
                                                    ntkde(NBx, size, best2[0], cnt(YY, k2, misiatsi(mshift(Tt, -LB), Tt), size), length) * length)
                                                for k2 in inshi])
                        p11, t11 = nb_model(H_tr, ytr, H_te, O_tr, O_te, typ_e=[f'вид:{k2}' for k2 in inshi])
                        dens['R11'] = p11 / length; mu['R11'] = p11 * sc
                        typy_by['R11'][T] = [t for t in t11 if str(t).startswith('вид')]
            rezult[T] = dens; mu_by[T] = mu

        # R7: середній ранг R2 і кращої з R3/R5 — кращу обираємо на першому
        # зрізі з навчанням (T7), щоб не підглядати в головний
        def rank01(v): return np.argsort(np.argsort(v)) / max(len(v) - 1, 1)
        if not LITE and 'R3' in rezult[T7]:
            y1 = cnt(YY, key, misiatsi(T7, mshift(T7, TUNE_H)), size)
            cand = [a for a in ('R3', 'R5') if a in rezult[T7]]
            b7 = max(cand, key=lambda a: e1e2(rezult[T7][a], y1, length)['10']['PAI'])
            o['R7_з'] = b7
            for T in rezult:
                if b7 in rezult[T]:
                    rezult[T]['R7'] = (rank01(rezult[T]['R2']) + rank01(rezult[T][b7])) / 2

        # ---- E1, E2 на всіх зрізах і цілях ----
        tab = {}
        for T, dens in rezult.items():
            for hz in (6, 12):
                end = mshift(T, hz)
                if end > KNOWN:
                    if mshift(T, 4) > KNOWN: continue
                    end = KNOWN
                yt = cnt(YY, key, misiatsi(T, end), size)
                if yt.sum() < 20: continue
                tab[f'{T}→{hz}м'] = dict(до=end, подій=int(yt.sum()),
                                         **{a: e1e2(d, yt, length) for a, d in dens.items()})
        o['E1_E2'] = tab

        # ---- головний зріз: E3, E5, E7 ----
        yH = cnt(YY, key, misiatsi(HOL, HOL_END), size)
        yE5 = cnt(YY, key, misiatsi(HOL, E5_END), size)
        dH = rezult[HOL]
        o['E3'] = butstrep(dH, yH, length, blok)
        o['E5'] = {a: spravdzh(m_ * (len(misiatsi(HOL, E5_END)) / 12), yE5, length)
                   for a, m_ in mu_by[HOL].items()}
        o['E7'] = {a: perekis(d, yH, length, rai) for a, d in dH.items()}

        # ---- E4: стабільність рангу між зрізами 2025-06 і 2025-12 ----
        A6, A12 = rezult['2025-06'], rezult['2025-12']
        o['E4'] = {a: dict(Спірмен=round(spirmen(A6[a], A12[a]), 3), Жаккар_5=round(zhakkar(A6[a], A12[a], length), 3))
                   for a in A12 if a in A6}

        # ---- E6: чинники, спільні між зрізами ----
        e6 = {}
        for a, byT in typy_by.items():
            ss = [set(map(str, v)) for v in byT.values()]
            if len(ss) >= 2:
                e6[a] = dict(за_зрізами={T: list(map(str, v)) for T, v in byT.items()},
                             спільних_усіх=len(set.intersection(*ss)), обраних_разом=len(set.union(*ss)))
        if imp_by:
            ss = [set(v) for v in imp_by.values()]
            e6['R5_топ10'] = dict(за_зрізами=imp_by, спільних_усіх=len(set.intersection(*ss)))
        o['E6'] = e6

        # ---- захід → схід (головний зріз): навчання лише на заході ----
        if not LITE:
            Tt = TWE
            ytr = cnt(YY, key, misiatsi(Tt, HOL), size)
            east = ~west
            if ytr[west].sum() >= 30 and yH[east].sum() >= 20:
                hw = r0(Tt)
                p3, _ = nb_model(hst(hw[west]), ytr[west], hst(r0(HOL)[east], hw[west]), tr_rows=west, te_rows=east)
                r2tr, r2te = r2(Tt, *best2) * length, r2(HOL, *best2) * length
                p4, _ = nb_model(hst(r2tr[west]), ytr[west], hst(r2te[east], r2tr[west]), tr_rows=west, te_rows=east)
                le = length[east]; ye = yH[east]
                o['захід_схід'] = dict(подій=int(ye.sum()), R0=e1e2(r0(HOL)[east] / le, ye, le),
                                       R2=e1e2(r2te[east] / le, ye, le),
                                       R3=e1e2(p3 / le, ye, le), R4=e1e2(p4 / le, ye, le))

        # ---- R12: 1551 за змістом (лише лінії, вікна 1551 як у перенавчанні) ----
        if L_ and not LITE:
            o['R12'] = r12(key, th, D, YY, cnt, nb_model, hst, length, blok)

        out[odin] = o
        # для «разом» і 10 вулиць
        out.setdefault('_dens', {})[odin] = (rezult[HOL], yH, mu_by[HOL])

    # ---- лінії й точки разом: одне мірило, точка = 50 м ----
    dd = out.pop('_dens', {})
    if 'лінії' in dd and 'точки' in dd:
        (dl, yl, ml), (dp, yp, mp) = dd['лінії'], dd['точки']
        ln = np.r_[D['slen'], D['lenP']]; yy = np.r_[yl, yp]
        raz = {}
        for a in ('R0', 'R2', 'R3', 'R5'):
            if a in ml and a in mp:
                raz[a] = e1e2(np.r_[ml[a], mp[a]] / ln, yy, ln)
        out['разом'] = raz
        # 10 вулиць, де R2 і R3 розходяться найбільше (з подіями обох років)
        if 'R3' in dl:
            r2r, r3r = np.argsort(np.argsort(-dl['R2'])), np.argsort(np.argsort(-dl['R3']))
            y25 = cnt(D['Y'], key, misiatsi('2024-12', '2025-12'), D['n'])
            m_ = (y25 > 0) & (yl > 0)
            ix = np.where(m_)[0]
            ix = ix[np.argsort(-np.abs(r2r[ix] - r3r[ix]))][:10]
            out['10_вулиць_R2_R3'] = [dict(вулиця=D['names'][D['sids'][i]], відрізок=D['sids'][i],
                                         місце_R2=int(r2r[i]) + 1, місце_R3=int(r3r[i]) + 1,
                                         подій_2025=round(float(y25[i]), 1), подій_2026=round(float(yl[i]), 1))
                                    for i in ix]
    return out


def r12(key, th, D, YY, cnt, nb_model, hst, length, blok):
    """R12 — R3 + ознаки 1551 за змістом (35.3) кандидатами; вікна 1551 з
    перенавчання (1551 є лише з 08.2025). Порівнюємо з R3 на тих самих
    вікнах — парний бутстреп; приріст має бути понад похибку."""
    import problems as PRB, zbir_1551 as Z
    from sklearn.neighbors import BallTree
    SK = PRB.skargy_hrupy(lambda *a: None)
    if not SK: return dict(пропущено='даних 1551 немає (гілка analiz-1551)')
    EN = list(Z.GRUPY_1551)
    mid, n, pop300 = D['mid'], D['n'], D['pop300']
    sk_mon = np.array([x[0] for x in SK]); sk_g = np.array([EN.index(x[1]) for x in SK])
    ind = BallTree(np.radians(np.array([x[2] for x in SK])), metric='haversine').query_radius(np.radians(mid), E.R_POP / 6371000.0)
    def skargy(a, b):
        ok = (sk_mon >= a) & (sk_mon <= b)
        o = np.zeros((n, len(EN)))
        for i, ix in enumerate(ind):
            ix = ix[ok[ix]]
            if len(ix): o[i] = np.bincount(sk_g[ix], minlength=len(EN))
        return np.where(pop300[:, None] >= E.MIN_LUDEJ, 1000 * o / np.maximum(pop300[:, None], 1), 0.0)
    def zstd(V, ref):
        lr = np.log1p(ref); sd = lr.std(0); sd[sd == 0] = 1
        return (np.log1p(V) - lr.mean(0)) / sd
    (a1, b1), (a2, b2), (a3, b3), (a4, b4) = E.VIKNO_1551
    rng = lambda a, b: [m for m in misiatsi(mshift(a, -1), b)]
    ytr_h, ytr = cnt(YY, key, rng(a1, b1), n), cnt(YY, key, rng(a2, b2), n)
    yte_h, yte = cnt(YY, key, rng(a3, b3), n), cnt(YY, key, rng(a4, b4), n)
    if ytr.sum() < 30 or yte.sum() < 20:
        return dict(пропущено=f'замало подій у вікнах 1551: {int(ytr.sum())} / {int(yte.sum())}')
    S1 = skargy(a1, b1); G_tr, G_te = zstd(S1, S1), zstd(skargy(a3, b3), S1)
    Htr, Hte = hst(ytr_h), hst(yte_h, ytr_h)
    p3, _ = nb_model(Htr, ytr, Hte)
    p12, t12 = nb_model(Htr, ytr, Hte, G_tr, G_te, typ_e=[f'1551:{g}' for g in EN])
    d = {'R3': p3 / length, 'R12': p12 / length}
    bs = butstrep(d, yte, length, blok, ref=('R3',))
    return dict(вікна=E.VIKNO_1551, подій_перевірки=int(yte.sum()),
                R3=e1e2(d['R3'], yte, length), R12=e1e2(d['R12'], yte, length),
                обрано_1551=[t for t in t12 if str(t).startswith('1551')], E3=bs)


if __name__ == '__main__':
    main()
