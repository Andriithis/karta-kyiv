# -*- coding: utf-8 -*-
"""Крок 4. «Схожі умови»: де середовище схоже на місця з подіями.

Одиниця аналізу — ВІДРІЗОК ВУЛИЦІ, а не квадрат сітки.
Так робили Davies & Bishop (2013, Crime Science 2(1):10); Rosser та ін. (2017,
JQC 33(3):569-594) показали, що мережа знаходить приблизно на 20% більше подій
за того самого покриття, ніж сітка.

Перенавчання Б1 (PLAN-KROK7.md, затверджено 25.09, поправки 28.09):
  * шість видів (RISHENNYA, розд. 18) — один шар на вид, без механізмів;
  * лише клас B (адресу названо в описі події) і лише точний будинок;
  * роки — за датою події, не рішення;
  * радіус кожного типу об'єкта — за Risk Terrain Modeling (src/rtm.py):
    «є в межах r» і «скільки в межах r» на 50–500 м, elastic net з
    перехресною перевіркою, далі покроково за BIC, одне r на тип;
  * на карту — модель лише середовища (pB): вона не знає, де події вже
    були, тож підсвічує й вулиці, де подій ще немає, а умови ті самі;
  * перевірка — за часом (2024 -> 2025–2026) і за місцем (захід -> схід);
    шар ховається, якщо PAI < 3 або не лишилося жодного чинника.

Перелік типів і радіусів зафіксовано в NAUKA.md до запуску й після
результату не міняється.
"""
import os, sys, json, math, sqlite3, collections, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import labels as L
import mech as M
import podii as PD
import uatext
import rtm

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
DB   = os.path.join(DATA, 'events.db')
RAW  = os.path.join(DATA, 'osm_risks_raw.json')
OUT  = os.path.join(DATA, 'engine_report.json')
RISK = os.path.join(DATA, 'risk.json')
RADF = os.path.join(DATA, 'radiusy.json')
TXT  = os.path.join(ROOT, 'ZVIT-KROK7.md')

SNAP_M  = 120     # подія прив'язується до вулиці в цьому радіусі
RADII   = (50, 100, 150, 250, 400, 500)      # PLAN-KROK7, розд. 3
MIN_EV  = 250

# Скільки вулиць показувати: найдовший перелік із сітки, на якому частка
# вулиць, де події справді сталися в перевірочні роки, ще не впала нижче
# PREC_MIN (зміна 7 вересня; рахується на роках, яких модель не бачила).
TOPN     = int(os.environ.get('TOPN', '25'))
TOPGRID  = 200
NGRID    = (25, 35, 50, 70, 100, 140, 200)
QUIET_N  = int(os.environ.get('QUIET_N', '40'))
PREC_MIN = float(os.environ.get('PREC_MIN', '0.5'))

# Шар щонайменше втричі кращий за випадковий вибір вулиць — інакше його не
# відрізнити від навмання тицьнутого пальця (PLAN-KROK7, розд. 4).
MIN_PAI = 3.0

TRAIN_Y = {'2024'}
TEST_Y  = {'2025', '2026'}
# Запасне вікно для видів, яким одного року замало (рішення 31.08.2026).
TRAIN2  = {'2024', '2025'}
TEST2   = {'2026'}
WINDOWS = (('2024', TRAIN_Y, TEST_Y), ('2024-2025', TRAIN2, TEST2))

# Джерело кожного чинника — NAUKA.md, «Перелік чинників для Б1», і
# PIDKHID.md, додаток В. Фактор без джерела в модель не йде (розд. 7.4).
SOURCES = {
    'бари': 'Roncek, Maier 1991; POP #1',
    'алкоголь_винос': 'Livingston 2008; Gruenewald та ін. 2006',
    'кафе': 'POP #60', 'фастфуд': 'Bernasco, Block 2011',
    'ломбарди': 'Fass, Francis 2004', 'банкомати': 'POP #8',
    'обмінники': 'Bernasco, Block 2011', 'ринки': 'Brantingham 1995',
    'супермаркети': 'Clarke 1999; POP #11', 'ТЦ': 'Clarke 1999; POP #11',
    'лікарні': 'Kennedy та ін. 2016', 'аптеки': 'POP #11',
    'АЗС': 'Dumbaugh, Rae 2009', 'школи': 'POP #6, #50', 'ВНЗ': 'Brantingham 1995',
    'метро': 'Loukaitou-Sideris 1999; Ceccato та ін. 2013',
    'зупинки': 'Loukaitou-Sideris 1999', 'майданчики': 'POP #6',
    'паркінги': 'POP #10', 'покинуті': 'POP #64',
    'переходи_підземні': 'київська гіпотеза; перевіряє модель',
    'гуртожитки': 'Bernasco, Block 2011',
    'гаражі': 'київська гіпотеза; перевіряє модель',
    # ознаки, що лишаються без змін (NAUKA, там само)
    'прохідність': 'Davies, Bishop 2013', 'потік_школи': 'Davies, Bishop 2013',
    'потік_транспорт': 'Davies, Bishop 2013', 'потік_торгівля': 'Davies, Bishop 2013',
    'населення_500м': 'населення як знаменник подій (NAUKA, розд. 2)',
    'клас_дороги': 'будова вулиці (NAUKA, розд. 2)', 'смуг': 'будова вулиці (NAUKA, розд. 2)',
    'проникність': 'будова вулиці (NAUKA, розд. 2)', 'хрестоподібні': 'будова вулиці (NAUKA, розд. 2)',
    'T_подібні': 'будова вулиці (NAUKA, розд. 2)', 'тупик': 'будова вулиці (NAUKA, розд. 2)',
    'звивистість': 'будова вулиці (NAUKA, розд. 2)',
    'перехрестя_всередині': 'будова вулиці (NAUKA, розд. 2)',
}

# Проактивні види (RISHENNYA, розд. 29): такі події поліція здебільшого
# виявляє сама, тож шар показує й те, де вона частіше працює. Рахуються,
# але позначаються. Частку для «частково» рахуємо з даних.
PROAKT_VYD = {'АЛК', 'НАР'}
PROAKT_CHAST = {'ГП', 'ДОР'}


def mdeg(lat): return 111320.0, 111320.0 * math.cos(math.radians(lat))


class SegGrid:
    """пошук найближчого відрізка вулиці до точки"""
    def __init__(s, segs, cell=0.0025):
        s.c = cell; s.g = collections.defaultdict(list)
        for sid, pts in segs.items():
            for p in pts:
                s.g[(int(p[0]/cell), int(p[1]/cell))].append((sid, p))
    def nearest(s, la, lo, rad):
        my, mx = mdeg(la)
        n = int(max(rad/my, rad/mx)/s.c) + 1
        ci, cj = int(la/s.c), int(lo/s.c)
        best, bd = None, 1e18
        for i in range(ci-n, ci+n+1):
            for j in range(cj-n, cj+n+1):
                for sid, p in s.g.get((i, j), ()):
                    d = math.hypot((p[0]-la)*my, (p[1]-lo)*mx)
                    if d < bd: bd, best = d, sid
        return best if bd <= rad else None


def seg_len(pts):
    t = 0
    for a, b in zip(pts, pts[1:]):
        my, mx = mdeg((a[0]+b[0])/2)
        t += math.hypot((a[0]-b[0])*my, (a[1]-b[1])*mx)
    return t


def el_pts(items):
    out = []
    for el in items or []:
        la = el.get('lat') or (el.get('center') or {}).get('lat')
        lo = el.get('lon') or (el.get('center') or {}).get('lon')
        if la and lo: out.append((la, lo))
    return out


def podii(log):
    """Події для навчання — тим самим відбором, що й карта (step3_map.vybir),
    і далі лише клас B на точному будинку, з датою події."""
    import step3_map as S3
    c = sqlite3.connect(DB)
    V = S3.vybir(c, print=lambda *a, **k: None)
    TKD, evy = V['TKD'], V['ev_year']
    out, drop = [], collections.Counter()
    for r in V['rows']:
        th = PD.theme(r[2])
        if th not in L.ORDER or th == 'ДОМ': continue
        kl = (TKD.get(r[0]) or {}).get('klass')
        if kl != 'B': drop[(th, 'не клас B')] += 1; continue
        if r[9] != 'house': drop[(th, 'не точний будинок')] += 1; continue
        out.append((th, r[2], evy.get(r[0], ''), r[7], r[8], M.is_proactive(r[2])))
    log(f'   подій на карті: {len(V["rows"]):,}; клас B на точному будинку: {len(out):,}')
    return out, drop


def main():
    import numpy as np
    from sklearn.neighbors import BallTree
    t0 = time.time()
    log = lambda *a: print(*a, flush=True)

    for f in (DB, RAW):
        if not os.path.exists(f): log(f'немає {f}'); sys.exit(1)
    raw = json.load(open(RAW, encoding='utf-8'))
    import step2b_risks as S2B
    miss = [k for k in S2B.B1 if not raw.get(k)]
    if miss:
        # Порожній тип тихо випав би з моделі, і звіт виглядав би так, ніби
        # модель його відкинула. Краще зупинитися.
        log('у osm_risks_raw.json немає типів Б1: ' + ', '.join(miss) + ' — спершу крок 2b')
        sys.exit(1)
    # стара модель — для порівняння в звіті, до того як файли перезапишуться
    OLD = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
    OLDR = json.load(open(RISK, encoding='utf-8')) if os.path.exists(RISK) else {}

    # ---- 1. відрізки вулиць ----
    segs, names, RD = {}, {}, {}
    for w in raw.get('roads', []):
        g = w.get('geometry')
        if not g or len(g) < 2: continue
        pts = [(p['lat'], p['lon']) for p in g]
        if seg_len(pts) < 40: continue
        segs[w['id']] = pts
        RD[w['id']] = w.get('tags', {}) or {}
        names[w['id']] = RD[w['id']].get('name', '')
    sids = sorted(segs)
    mid = np.array([segs[s][len(segs[s])//2] for s in sids])
    slen = np.array([seg_len(segs[s]) for s in sids])
    # Довжина кварталу (RTMDx радить середню для міста): щоб у звіті було
    # видно, скільки кварталів дає кожен радіус-кандидат.
    blocks_m = int(round(float(slen.mean())))
    log(f'відрізків вулиць: {len(sids):,}; середня довжина (квартал) {blocks_m} м')

    # ---- 2. ознаки-кандидати ----
    log('1) ознаки середовища...')
    tree_m = BallTree(np.radians(mid), metric='haversine')
    R_E = 6371000.0
    cols, cname, ctyp, cform, crad = [], [], [], [], []
    COUNT = {}                   # (тип, r) -> кількість у колі, для чинників вулиці
    for key, (ua, _q) in S2B.B1.items():
        P = el_pts(raw.get(key))
        if not P: continue
        tp = BallTree(np.radians(np.array(P)), metric='haversine')
        for r in RADII:
            cnt = tp.query_radius(np.radians(mid), r / R_E, count_only=True).astype(float)
            COUNT[(ua, r)] = cnt
            if cnt.max() == 0: continue
            cols.append((cnt > 0).astype(float)); cname.append(f'{ua}_є_{r}м')
            ctyp.append(ua); cform.append('є'); crad.append(r)
            cols.append(cnt); cname.append(f'{ua}_{r}м')
            ctyp.append(ua); cform.append('скільки'); crad.append(r)
        log(f'   {ua:18} {len(P):6,}')

    RAWV = {}                    # величина -> сире значення, для чинників вулиці
    def cont(name, v, raw=None):
        # Величини без радіуса — у стандартних відхиленнях, щоб кратність
        # читалася «на одне відхилення», а не «на одного пішохода». Людині ж
        # показуємо сире число (потік, мешканці), яке можна перевірити.
        v = np.asarray(v, dtype=float)
        RAWV[name] = np.asarray(v if raw is None else raw, dtype=float)
        sd = v.std()
        if sd == 0: return
        cols.append((v - v.mean()) / sd); cname.append(name)
        ctyp.append(None); cform.append('величина'); crad.append(None)

    # пішохідні потоки лишаються: без них метро забирає собі все (розд. 7.1)
    npth = os.path.join(DATA, 'network.json')
    if os.path.exists(npth):
        byid = {}
        for it in json.load(open(npth, encoding='utf-8')).get('items', []):
            if len(it) > 6 and it[6] is not None:
                byid[it[6]] = (it[2], it[3], it[4], it[5])
        for j, ua in ((0, 'прохідність'), (1, 'потік_школи'),
                      (2, 'потік_транспорт'), (3, 'потік_торгівля')):
            rv = [byid.get(s, (0, 0, 0, 0))[j] for s in sids]
            cont(ua, np.log1p(rv), rv)
    pp = os.path.join(DATA, 'population.json')
    if os.path.exists(pp):
        Pp = json.load(open(pp, encoding='utf-8'))['items']
        tpp = BallTree(np.radians(np.array([[x[0], x[1]] for x in Pp])), metric='haversine')
        w_ = np.array([x[2] for x in Pp], dtype=float)
        ind = tpp.query_radius(np.radians(mid), 500 / R_E)
        rv = [w_[i].sum() for i in ind]
        cont('населення_500м', np.log1p(rv), rv)
    HW = {'residential': 1, 'living_street': 1, 'unclassified': 2,
          'tertiary': 3, 'secondary': 4, 'primary': 5}
    cont('клас_дороги', [HW.get(RD[s].get('highway', ''), 2) for s in sids])
    cont('смуг', [float(RD[s].get('lanes')) if str(RD[s].get('lanes', '')).isdigit() else 2.0
                  for s in sids])
    ngp = os.path.join(DATA, 'netgeo.json')
    if os.path.exists(ngp):
        NG = json.load(open(ngp, encoding='utf-8'))
        for fld, ua in (('perm', 'проникність'), ('cross4', 'хрестоподібні'),
                        ('cross3', 'T_подібні'), ('dead', 'тупик'),
                        ('sinuo', 'звивистість'), ('inner', 'перехрестя_всередині')):
            cont(ua, [float(NG.get(str(s), {}).get(fld, 0)) for s in sids])
    X = np.column_stack(cols)
    med = np.median(X, axis=0)
    log(f'   змінних-кандидатів: {X.shape[1]} ({sum(1 for t in ctyp if t)} — типи × радіуси × форми)')

    # ЕКСПОЗИЦІЯ: довжина вулиці. Модель вчиться на щільності подій на метр,
    # оцінка множиться назад на довжину.
    expo = np.maximum(slen, 20.0); expo = expo / expo.mean()

    # ---- 3. події -> відрізки ----
    log('2) події...')
    ev, drop = podii(log)
    sg = SegGrid(segs)
    six = [t for t in L.ORDER if t != 'ДОМ']
    idx = {s: i for i, s in enumerate(sids)}
    Y = collections.defaultdict(lambda: np.zeros(len(sids)))   # (вид, рік, заявна?) -> лічильник
    n_snap = collections.Counter(); n_all = collections.Counter(); n_pro = collections.Counter()
    cache = {}
    for th, _cat, y, la, lo, pro in ev:
        n_all[th] += 1; n_pro[th] += pro
        ck = (round(la, 5), round(lo, 5))
        s = cache[ck] if ck in cache else cache.setdefault(ck, sg.nearest(la, lo, SNAP_M))
        if s is None: continue
        n_snap[th] += 1
        Y[(th, y, pro)][idx[s]] += 1

    def cnt(th, years, only_reported=False):
        v = np.zeros(len(sids))
        for (t, y, pro), a in Y.items():
            if t == th and y in years and not (only_reported and pro): v += a
        return v

    lons = mid[:, 1]
    west = lons <= np.median(lons); east = ~west

    def fit(y, yt, mask=None):
        """відбір RTM на навчальних подіях і оцінка на відкладених"""
        if mask is None:
            sel = rtm.select(X, y, expo, ctyp, log=log)
            p = rtm.predict(sel, X, expo)
            return sel, p, rtm.hit_rate(p, yt)
        sel = rtm.select(X[mask], y[mask], expo[mask], ctyp, log=log)
        p = rtm.predict(sel, X[~mask], expo[~mask])
        return sel, p, rtm.hit_rate(p, yt[~mask])

    def hit_together(sel, y, yt):
        """модель «разом» (середовище + історія подій) — лише для звіту"""
        import statsmodels.api as sm
        h = np.log1p(y); h = (h - h.mean()) / (h.std() or 1)
        A = np.column_stack([np.ones(len(y)), h] + [X[:, j] for j in sel['cols']])
        try:
            r = sm.GLM(y, A, family=sm.families.Poisson(), offset=np.log(expo)).fit(maxiter=100)
            return rtm.hit_rate(np.exp(A @ r.params) * expo, yt)
        except Exception:
            return float('nan')

    def factors(sel):
        """таблиця чинників: тип, форма, радіус, кратність з 95% інтервалом"""
        out = []
        if not sel['cols']: return out
        ci = sel['fit'].conf_int()
        for k, j in enumerate(sel['cols'], start=1):
            b = float(sel['fit'].params[k])
            base = ctyp[j] or cname[j]
            out.append(dict(змінна=cname[j], тип=base, форма=cform[j], r=crad[j],
                            кварталів=round(crad[j] / blocks_m, 1) if crad[j] else None,
                            коеф=round(b, 4), RR=round(math.exp(b), 2),
                            RR_від=round(math.exp(ci[k][0]), 2), RR_до=round(math.exp(ci[k][1]), 2),
                            джерело=SOURCES.get(base, '')))
        return sorted(out, key=lambda d: -abs(d['коеф']))

    def street_facts(sel, i, k=3):
        """чинники САМЕ ЦІЄЇ вулиці: внесок = коеф × відхилення від середнього
        (для лог-лінійної моделі це розклад оцінки на доданки). Значення —
        кількість об'єктів у тому самому колі, щоб на місці її можна було
        перерахувати."""
        rows = []
        for k_, j in enumerate(sel['cols'], start=1):
            b = float(sel['fit'].params[k_])
            c = b * (X[i, j] - X[:, j].mean())
            if c <= 0: continue
            if ctyp[j]:
                v = COUNT[(ctyp[j], crad[j])]
                rows.append((c, [f'{ctyp[j]}_{crad[j]}м', round(float(v[i]), 1),
                                 round(float(np.median(v)), 1), round(math.exp(b), 2)]))
            else:
                v = RAWV[cname[j]]
                rows.append((c, [cname[j], round(float(v[i]), 1), round(float(np.median(v)), 1),
                                 round(math.exp(b), 2)]))
        return [r for _c, r in sorted(rows, key=lambda x: -x[0])[:k]]

    def row(sel, i, rk, y, facts=True):
        s = sids[i]
        r = [segs[s][::max(1, len(segs[s])//8)], names[s], round(float(rk[i]), 3), int(y[i])]
        if facts: r.append(street_facts(sel, i))
        return r

    report, layers, radiusy, kinds = {}, {}, {}, {}
    for th in six:
        nm = L.THEMES.get(th, th)
        log(f'\n=== {nm} ===')
        pr = n_pro[th] / max(n_all[th], 1)
        if th in PROAKT_VYD: mark = 'проактивний вид'
        elif th in PROAKT_CHAST: mark = f'частково проактивний, {round(100 * pr)}%'
        else: mark = ''
        kinds[th] = dict(назва=nm, подій=n_all[th], на_вулицях=n_snap[th],
                         проактивних=round(pr, 3), позначка=mark,
                         відсіяно={k[1]: v for k, v in drop.items() if k[0] == th})
        got = None
        for wname, try_, tey_ in WINDOWS:
            y, yt = cnt(th, try_), cnt(th, tey_)
            if y.sum() >= MIN_EV and yt.sum() >= 50:
                got = (wname, try_, tey_, y, yt); break
        if not got:
            y0 = cnt(th, TRAIN2)
            log(f'   замало подій: {int(y0.sum())} за 2024–2025 (потрібно {MIN_EV})')
            report[th] = dict(вид='тема', тема=nm, назва=nm, на_карті=False,
                              сховано='замало подій для навчання', навчання=int(y0.sum()),
                              позначка=mark)
            continue
        wname, try_, tey_, y, yt = got
        log(f'   вікно {wname}: навчання {int(y.sum())}, перевірка {int(yt.sum())}')
        sel, pB, hB = fit(y, yt)
        hA = rtm.hit_rate(y, yt)
        hC = hit_together(sel, y, yt) if sel['cols'] else hA
        hGeo = float('nan')
        if y[west].sum() > 60 and yt[east].sum() > 30:
            log('   перенесення захід -> схід:')
            _sg, _pg, hGeo = fit(y, yt, mask=west)
        facs = factors(sel)
        pai = hB / 0.10
        ok = pai >= MIN_PAI and bool(sel['cols'])
        why = '' if ok else ('elastic net не лишив жодного чинника' if not sel['cols']
                             else f'PAI {pai:.1f} < {MIN_PAI:g}')
        radiusy[nm] = {d['тип']: d['r'] for d in facs if d['r']}

        # друга модель лише на заявних подіях (розд. 7.2): якщо фактори суттєво
        # інші, це йде в звіт одним рядком
        zayav = None
        if th in PROAKT_CHAST:
            yr, ytr = cnt(th, try_, True), cnt(th, tey_, True)
            if yr.sum() >= MIN_EV and ytr.sum() >= 50:
                log('   лише заявні події:')
                sr, _pr, hr = fit(yr, ytr)
                zayav = dict(навчання=int(yr.sum()), перевірка=int(ytr.sum()),
                             PAI=round(hr / 0.10, 2),
                             типи=sorted({ctyp[j] or cname[j] for j in sr['cols']}))

        rk = pB / (pB.max() or 1)
        ordr = np.argsort(-pB, kind='stable')
        prec_curve, n_show, prev = [], TOPN, 0
        for n_ in NGRID:
            if n_ > len(ordr): break
            p_ = float((yt[ordr[:n_]] > 0).mean())
            prec_curve.append([n_, round(p_, 2)])
            if n_ <= TOPN: continue
            if p_ >= PREC_MIN: n_show = n_
            else: break
        shown = ordr[:n_show]
        quiet = [i for i in ordr if y[i] == 0][:QUIET_N]
        e = dict(вид='тема', тема=nm, назва=nm, вікно=wname,
                 навчання=int(y.sum()), перевірка=int(yt.sum()),
                 hit_історія=round(hA, 3), hit_середовище=round(hB, 3),
                 hit_разом=round(hC, 3),
                 hit_інший_район=None if hGeo != hGeo else round(hGeo, 3),
                 PAI_середовище=round(pai, 2), PAI_історія=round(hA / 0.10, 2),
                 PAI_разом=round(hC / 0.10, 2),
                 PAI_інший_район=None if hGeo != hGeo else round(hGeo / 0.10, 2),
                 вулиць_показано=int(n_show),
                 з_них_збулося=int((yt[shown] > 0).sum()),
                 відрізків=len(sids), точність_за_довжиною=prec_curve,
                 модель='Пуассон' if sel['fit'] is None or sel['fam'] == 'P' else 'негативна біноміальна',
                 після_elastic_net=sel['n_enet'], BIC=None if sel['bic'] is None else round(sel['bic'], 1),
                 чинники=facs,
                 # поля, які читають карта й документи (map_layers, step6)
                 фактори=[[d['змінна'], d['коеф']] for d in facs],
                 кратність={(f"{d['тип']}_{d['r']}м" if d['r'] else d['змінна']): d['RR'] for d in facs},
                 позначка=mark, на_карті=ok, сховано=why, заявні=zayav)
        e['метод'] = method_text(e, wname, mark)
        report[th] = e
        if ok:
            layers[th] = dict(kind='theme', theme=th, name=nm, title='Схожі умови: ' + nm,
                              slug=M.anchor(th), window=wname, proakt=mark,
                              hit=round(hB, 3), hit_env=round(hB, 3),
                              items=[row(sel, i, rk, y) for i in shown],
                              quiet=[row(sel, i, rk, y) for i in quiet],
                              grid=[row(sel, i, rk, y, False) for i in ordr[:TOPGRID]])
        log(f'   PAI {pai:.2f} (історія {hA/0.1:.2f}, разом {hC/0.1:.2f}, '
            f'захід->схід {hGeo/0.1:.2f}); чинників {len(facs)}; '
            + ('на карті' if ok else 'СХОВАНО: ' + why))
        for d in facs[:8]:
            log(f"      RR {d['RR']:5.2f}  {d['змінна']}")

    # ---- «Що поруч»: один радіус на тип, той самий відбір по всіх подіях ----
    log('\n=== «Що поруч»: усі шість видів разом ===')
    ya = sum(cnt(th, TRAIN_Y) for th in six)
    sa = rtm.select(X, ya, expo, ctyp, log=log)
    shcho = {ua: 0 for ua, _q in S2B.B1.values()}
    for j in sa['cols']:
        if ctyp[j]: shcho[ctyp[j]] = crad[j]
    json.dump({'blocks_m': blocks_m, 'po_vydah': radiusy, 'shcho_poruch': shcho},
              open(RADF, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    log(f'   -> data/radiusy.json: ' + ', '.join(f'{k} {v}' for k, v in shcho.items() if v))

    json.dump({'layers': layers, 'danger': danger_schools()},
              open(RISK, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    json.dump(report, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    write_report(report, kinds, OLD, OLDR, layers, blocks_m, shcho, len(sids), X.shape[1],
                 factors(sa))
    log(f'\n=== ГОТОВО за {(time.time() - t0) / 60:.0f} хв === шарів на карті: {len(layers)}; '
        f'ZVIT-KROK7.md, data/radiusy.json')


def method_text(e, wname, mark):
    """речення для картки шару на карті. Без «ризику» й «прогнозу»: шар
    показує, де умови схожі на місця з подіями (PLAN-KROK7, розд. 0)."""
    tr_y, te_y = {'2024': ('2024 року', '2025–2026'),
                  '2024-2025': ('2024–2025 років', '2026')}.get(wname, (wname, '—'))
    n1 = f"{e['навчання']:,}".replace(',', ' ')
    n2 = f"{e['перевірка']:,}".replace(',', ' ')
    t = (f"Шар навчено на {n1} подіях {tr_y} — лише там, де адресу названо в "
         f"описі події, з точним будинком, — і перевірено на {n2} подіях "
         f"{te_y}. Він зважує лише те, що поруч, а не те, де події вже були. "
         f"На 10% вулиць з найвищою оцінкою припало {100*e['hit_середовище']:.0f}% "
         f"подій наступних років — у {uatext.raziv(e['PAI_середовище'])} більше, "
         f"ніж навмання.")
    if e.get('hit_інший_район') is not None:
        t += (f" Навчений на західній половині міста, на східній він знаходить "
              f"{100*e['hit_інший_район']:.0f}%.")
    if mark == 'проактивний вид':
        t += (" Проактивний вид: такі події поліція здебільшого виявляє сама, тож "
              "шар показує й те, де вона частіше працює.")
    elif mark:
        t += (f" Частково проактивний ({mark.split(', ')[-1]} подій виявила сама "
              f"поліція): шар почасти показує й те, де вона частіше працює.")
    return t


def danger_schools():
    """Небезпечні підходи до шкіл: потік дітей + немає тротуару. Без змін
    з попередньої редакції двигуна — вона не залежить від моделі."""
    danger = []
    npth2 = os.path.join(DATA, 'network.json')
    rp2 = os.path.join(DATA, 'risks.json')
    if not (os.path.exists(npth2) and os.path.exists(rp2)): return danger
    N2 = json.load(open(npth2, encoding='utf-8'))
    R2 = json.load(open(rp2, encoding='utf-8'))
    sch = {}
    for it in N2.get('items', []):
        if it[1] and len(it) > 3:
            sch[it[1]] = max(sch.get(it[1], 0), it[3])
    nowalk = set()
    for lay in ('no_walk', 'maybe_walk'):
        for it in R2.get('lines', {}).get(lay, {}).get('items', []):
            if it[1]: nowalk.add(it[1])
    ranked = sorted(sch.items(), key=lambda x: -x[1])
    for i, (nm, flow) in enumerate(ranked, 1):
        if flow > 0 and nm in nowalk:
            danger.append({'вулиця': nm, 'потік_до_шкіл': flow,
                           'місце_в_рейтингу': i, 'усього_вулиць': len(ranked)})
    return danger[:60]


def pct(x): return '—' if x is None else f'{100*x:.0f}%'


def write_report(report, kinds, OLD, OLDR, layers, blocks_m, shcho, nseg, ncand, fa):
    """ZVIT-KROK7.md — зміст за PLAN-KROK7, розд. 5 і 7."""
    f = open(TXT, 'w', encoding='utf-8', newline='\n')
    w = f.write
    w('# Звіт кроку 7 (Б1): «Схожі умови» на шести видах\n\n')
    w(f'Складено двигуном (`src/step4_engine.py`, `src/rtm.py`) {time.strftime("%d.%m.%Y")}. '
      'План — `PLAN-KROK7.md` з поправками 28.09; перелік типів і радіусів — '
      '`NAUKA.md`, «Перелік чинників для Б1» (зафіксовано до запуску).\n\n')
    w(f'Одиниця — відрізок вулиці ({nseg:,} шт.; середня довжина, «квартал», '
      f'{blocks_m} м). Змінних-кандидатів {ncand}: кожен тип об\'єкта «є в межах r» і '
      '«скільки в межах r» на 50, 100, 150, 250, 400, 500 м, плюс пішохідні потоки, '
      'населення й будова вулиці. Відбір — elastic net Пуассон з 5-кратною перехресною '
      'перевіркою на роках навчання, далі покроково (Пуассон і негативна біноміальна) '
      'за BIC, одне r на тип.\n\n')
    w('> **PAI** — у скільки разів частка подій наступних років на 10% вулиць з '
      'найвищою оцінкою більша за частку самих вулиць (навмання — 1). **Влучність** — '
      'та сама частка подій. На карту йде модель лише середовища.\n\n')

    w('## 1. Види й події після фільтрів\n\n')
    w('| Вид | Позначка | Клас B, точний будинок | На вулицях | Вікно | Навчання | Перевірка |\n')
    w('|---|---|---|---|---|---|---|\n')
    for th, k in kinds.items():
        e = report.get(th, {})
        w(f"| {k['назва']} | {k['позначка'] or '—'} | {k['подій']:,} | {k['на_вулицях']:,} "
          f"| {e.get('вікно', '—')} | {e.get('навчання', 0):,} | {e.get('перевірка', '—')} |\n")
    w('\nВідсіяно до цього (з подій карти): '
      + '; '.join(f"{k['назва']} — " + ', '.join(f'{a} {b:,}' for a, b in k['відсіяно'].items())
                  for k in kinds.values() if k['відсіяно']) + '.\n\n')

    w('## 2. Перевірка: PAI і влучність\n\n')
    w('| Вид | На карті | PAI середовище | Влучність | Захід → схід | Історія | Разом '
      '| Стара модель (середовище) | Збулося |\n|---|---|---|---|---|---|---|---|---|\n')
    for th, e in report.items():
        o = OLD.get(th, {})
        if 'hit_середовище' not in e:
            w(f"| {e['назва']} | ні — {e['сховано']} | — | — | — | — | — | "
              f"{o.get('PAI_середовище', '—')} | — |\n"); continue
        g = e.get('PAI_інший_район')
        w(f"| {e['назва']} | {'так' if e['на_карті'] else 'ні — ' + e['сховано']} "
          f"| **{e['PAI_середовище']}** | {pct(e['hit_середовище'])} "
          f"| {g if g is not None else '—'} ({pct(e['hit_інший_район'])}) "
          f"| {e['PAI_історія']} | {e['PAI_разом']} "
          f"| {o.get('PAI_середовище', '—')} ({pct(o.get('hit_середовище'))}) "
          f"| {e['з_них_збулося']} з {e['вулиць_показано']} |\n")
    w('\nСтара модель — числа з попереднього `engine_report.json` на тих самих роках '
      '(навчання 2024, перевірка 2025–2026), але на старих адресах, датах рішень і '
      'всіх класах адрес; тож порівняння — для чесності, не умова (PLAN-KROK7, розд. 4).\n\n')
    hid = [(e['назва'], e['сховано']) for e in report.values() if not e.get('на_карті')]
    if hid:
        w('**Сховано на карті:** ' + '; '.join(f'{a} — {b}' for a, b in hid)
          + '. На карті для них — «для цього виду даних замало».\n\n')

    w('## 3. Чинники по видах\n\n')
    w('Кратність (RR) — у скільки разів більше подій: для «є» — там, де об\'єкт є в '
      'колі, проти решти; для «скільки» — на кожен ще один об\'єкт; для величин — на '
      'одне стандартне відхилення. У дужках 95% інтервал. Менше 1 — подій менше.\n\n')
    for th, e in report.items():
        if not e.get('чинники'): continue
        w(f"### {e['назва']}" + (f" · {e['позначка']}" if e.get('позначка') else '') + '\n\n')
        w(f"Модель: {e['модель']}; після elastic net {e['після_elastic_net']} змінних, "
          f"після покрокового відбору {len(e['чинники'])}.\n\n")
        w('| Чинник | Форма | Радіус | Кварталів | RR | 95% | Джерело |\n|---|---|---|---|---|---|---|\n')
        for d in e['чинники']:
            w(f"| {d['тип'].replace('_', ' ')} | {d['форма']} | {str(d['r']) + ' м' if d['r'] else '—'} "
              f"| {d['кварталів'] or '—'} | **{d['RR']}** | {d['RR_від']}–{d['RR_до']} | {d['джерело']} |\n")
        z = e.get('заявні')
        if z:
            ts = {d['тип'] for d in e['чинники']}
            zs = set(z['типи'])
            w(f"\nЛише заявні події ({z['навчання']:,} / {z['перевірка']:,}; PAI {z['PAI']}): "
              + ('ті самі типи.' if zs == ts else
                 f"спільні — {', '.join(sorted(ts & zs)) or 'немає'}; лише в заявних — "
                 f"{', '.join(sorted(zs - ts)) or 'немає'}; лише в усіх — "
                 f"{', '.join(sorted(ts - zs)) or 'немає'}.") + '\n')
        w('\n')

    w('## 4. Радіуси «Що поруч»\n\n')
    w('Той самий відбір на всіх шести видах разом (навчання 2024). 0 — тип не пов\'язаний '
      'з подіями; кнопка «Що поруч» показує його в найменшому колі, бо вона — '
      'спостереження, а не підказка моделі.\n\n| Тип | Радіус | RR | Джерело |\n|---|---|---|---|\n')
    rr = {d['тип']: d for d in fa if d['r']}
    for ua, r in shcho.items():
        d = rr.get(ua)
        w(f"| {ua.replace('_', ' ')} | {str(r) + ' м' if r else '0'} | {d['RR'] if d else '—'} "
          f"| {SOURCES.get(ua, '')} |\n")

    w('\n## 5. Вулиці, що вийшли й зайшли (по 10 на вид)\n\n')
    for th, lay in layers.items():
        old = OLDR.get('layers', {}).get(th, {}).get('items', [])
        on = [x[1] for x in old if x[1]]
        nn = [x[1] for x in lay['items'] if x[1]]
        vyi = [n for n in dict.fromkeys(on) if n not in nn][:10]
        zai = [n for n in dict.fromkeys(nn) if n not in on][:10]
        w(f"**{report[th]['назва']}.** Зайшли: {', '.join(zai) or '—'}. "
          f"Вийшли: {', '.join(vyi) or '—'}.\n\n")
    f.close()


if __name__ == '__main__':
    main()
