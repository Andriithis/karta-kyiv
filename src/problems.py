# -*- coding: utf-8 -*-
"""Відбір проблем (В1): ворота Р1–Р7, три рівні місця, стан «формується»,
голос мешканців 1551.

Рішення — NAPRYAM-PROBLEMY.md (Р1–Р8, додатки А–Б) і PIDKHID.md (розд.
3–5). Старий відбір у map_problems.py (поріг 15 епізодів і квоти) лишається
там і вимикається прапорцем NOVYI_VIDBIR — для порівняння.

Коротко:
  * події — ті самі, що на карті (step3_map.vybir), і далі лише точний
    будинок; у підрахунок проблеми йде лише клас B (Р1);
  * пара «місце × механізм»; адреси в 30 м з тим самим механізмом —
    одне місце (Хрещатик 21/23/23А);
  * ворота: Р1 клас B; Р2 заявних ≥ 50%; Р4 ДТП з майновою шкодою — окремо;
    Р3 ≥ 5 окремих подій, ≥ 3 різні квартали з останніх 8, остання не
    старша за 12 місяців;
  * точка не пройшла — пробуємо лінію: відрізок вулиці × механізм, події на
    ≥ 3 адресах і жодна не тримає більшості;
  * «формується» — рахується й зберігається, на карту не йде (розд. 3.2);
  * golos — скарги 1551 того ж виду проти рівня району (розд. 5.1).

Запуск окремо: py -3 src/problems.py (пише data/problems_report.json).
Карта кличе run() сама — step3_map.
"""
import os, sys, glob, json, math, gzip, csv, collections, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import labels as L
import mech as M
import podii as PD

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
REPORT = os.path.join(DATA, 'problems_report.json')
D1551 = os.path.join(DATA, '1551')

PRAVYLA = 'В1, 28.09.2026 (NAPRYAM-PROBLEMY, Р1–Р7; PIDKHID, розд. 3–5)'
R_MISCE = 30          # м: адреси з тим самим механізмом ближче — одне місце
MIN_POD = 5           # Р3: окремих подій
MIN_KV = 3            # Р3: різних кварталів з останніх 8
KV_VIKNO = 8
SVIZHIST_DNIV = 365   # Р3: остання подія не старша за рік
ZATRYMKA_DNIV = 50    # Р3: медіанна затримка рішення від події (тест 22.09)
ZAYAVNI_MIN = 0.5     # Р2
SNAP_M = 120          # як у step4_engine: подія -> відрізок вулиці
KAT = {'ГП', 'АЛК', 'НАР', 'НАС', 'МАЙ', 'ДОР'}   # шість видів, без ДОМ

# 1551: вид звернень -> вид карти; для решти видів 1551 мовчить (розд. 5.1)
VYD1551 = {'1_PUBLIC_ORDER': 'ГП', '2_ALCOHOL_TRADE': 'АЛК', '6_TRAFFIC': 'ДОР'}
NE_VYMIR = {'НАР', 'НАС', 'МАЙ'}

# Середовище місця (Р5): OSM-точки factors.json у 50 м; ключ типу -> середовище
SERED = {'b1_bars': 'рекреація', 'b1_cafe': 'рекреація', 'b1_fastfood': 'рекреація',
         'b1_alk': 'торгівля', 'b1_super': 'торгівля', 'b1_mall': 'торгівля', 'b1_market': 'торгівля',
         'b1_atm': 'фінанси', 'b1_pawn': 'фінанси', 'b1_exchange': 'фінанси',
         'b1_metro': 'транспорт', 'b1_stops': 'транспорт',
         'b1_school': 'освіта', 'b1_univer': 'освіта',
         'b1_parking': 'паркінг', 'b1_garages': 'паркінг',
         'b1_hospital': 'медицина', 'b1_pharmacy': 'медицина', 'b1_dorm': 'житло',
         # старі ключі factors.json — поки двигун Б1 не перебудував файл
         'bar_on': 'рекреація', 'food': 'рекреація', 'bar_off': 'торгівля', 'market': 'торгівля',
         'finance': 'фінанси', 'metro': 'транспорт', 'busstop': 'транспорт',
         'school': 'освіта', 'univer': 'освіта', 'parking': 'паркінг', 'health': 'медицина'}
R_SERED = 50
# Якщо OSM поруч нічого не дав — ключові слова фабули (Р5). Слово має
# траплятися щонайменше в третині подій місця, а не в одній.
FAB_SERED = (('торгівля', ('магазин', 'супермаркет', 'торгов', ' тц ', 'трц', 'гіпермаркет', 'ринк')),
             ('рекреація', ('кафе', 'бар ', 'бару', 'ресторан', 'клуб', 'паб')),
             ('транспорт', ('станці', 'метро', 'зупинк', 'вокзал')),
             ('паркінг', ('паркінг', 'стоянк', 'парковк')),
             ('освіта', ('школ', 'ліцей', 'гімназ', 'університет', 'коледж')),
             ('житло', ("під'їзд", 'підїзд', 'квартир', 'сходов', 'гуртожит')))


def _m(la0):
    return 111320.0, 111320.0 * math.cos(math.radians(la0))


def dist(a, b):
    my, mx = _m(a[0])
    return math.hypot((a[0] - b[0]) * my, (a[1] - b[1]) * mx)


class Pts:
    """сітка для пошуку точок у радіусі"""
    def __init__(s, pts, cell=0.002):
        s.c = cell; s.g = collections.defaultdict(list)
        for k, p in enumerate(pts): s.g[(int(p[0] / cell), int(p[1] / cell))].append(k)
        s.p = pts
    def near(s, la, lo, r):
        my, mx = _m(la)
        n = int(max(r / my, r / mx) / s.c) + 1
        ci, cj = int(la / s.c), int(lo / s.c)
        out = []
        for i in range(ci - n, ci + n + 1):
            for j in range(cj - n, cj + n + 1):
                for k in s.g.get((i, j), ()):
                    q = s.p[k]
                    if math.hypot((q[0] - la) * my, (q[1] - lo) * mx) <= r: out.append(k)
        return out


def kv(d):
    """'2025-09-14' -> номер кварталу"""
    return int(d[:4]) * 4 + (int(d[5:7]) - 1) // 3


def kv_name(q):
    return f'{q // 4}-К{q % 4 + 1}'


def pois_sf(n, lam):
    """P(X ≥ n) для Пуассона з середнім lam"""
    if n <= 0: return 1.0
    if lam <= 0: return 0.0
    t, s = math.exp(-lam), 0.0
    for k in range(n):
        s += t; t *= lam / (k + 1)
    return max(0.0, 1.0 - s)


# ---------------------------------------------------------------- 1551
def geokoder():
    """(ключ вулиці, номер) -> точка з реєстру КМДА — той самий знімок, що
    геокодує події. Адреси, які в реєстрі стоять у двох місцях далі 200 м,
    не беремо: це неоднозначність, а не точка."""
    from step2_geocode import skey, nh, KMDA
    if not os.path.exists(KMDA): return {}, skey, nh
    cand = collections.defaultdict(list)
    with gzip.open(KMDA, 'rt', encoding='utf-8', newline='') as fh:
        for r in csv.DictReader(fh, delimiter='\t'):
            cand[(skey(r['street']), nh(r['house']))].append((float(r['lat']), float(r['lon'])))
    idx = {k: v[0] for k, v in cand.items() if max(dist(a, b) for a in v for b in v) <= 200}
    return idx, skey, nh


def load_1551(log):
    """Скарги (vidbir) і всі звернення на адресу (lichylnyky) з гілки
    analiz-1551. Конвеєр кладе їх у data/1551 перед збіркою; у main вони не
    комітяться. Немає — голос «не виміряно», а не вигаданий нуль."""
    fv = sorted(glob.glob(os.path.join(D1551, 'vidbir-*.tsv.gz')))
    fl = sorted(glob.glob(os.path.join(D1551, 'lichylnyky-*.tsv.gz')))
    if not fv or not fl:
        log('   1551: даних немає (data/1551) — golos «немає даних»')
        return None
    idx, skey, nh = geokoder()

    def geo(st, h):
        if not st or not h or not idx: return None
        st = str(st); h = nh(str(h))
        # давня назва в дужках — запасний варіант: «просп. Берестейський (Перемоги)»
        main_ = st.split('(')[0]
        p = idx.get((skey(main_), h))
        if p is None and '(' in st:
            old = st.split('(', 1)[1].rstrip(') ')
            typ = main_.split()[0] if main_.split() else ''
            p = idx.get((skey(f'{typ} {old}'), h))
        return p

    sk = []          # (дата, вид карти, content, точка)
    nsk = collections.Counter()
    for f in fv:
        with gzip.open(f, 'rt', encoding='utf-8', newline='') as fh:
            for r in csv.DictReader(fh, delimiter='\t'):
                v = VYD1551.get(r.get('vyd'))
                if not v: continue
                p = geo(r.get('vulytsya'), r.get('budynok'))
                nsk['з адресою' if p else 'без точки'] += 1
                if p: sk.append((r['data'][:10], v, r.get('content') or '', p))
    vse = []         # (місяць, точка, n) — усі звернення на адресу, знаменник
    for f in fl:
        mon = os.path.basename(f)[11:18]
        with gzip.open(f, 'rt', encoding='utf-8', newline='') as fh:
            for r in csv.DictReader(fh, delimiter='\t'):
                p = geo(r.get('vulytsya'), r.get('budynok'))
                if p: vse.append((mon, p, int(r.get('n') or 0)))
    last = max(d for d, *_ in sk) if sk else ''
    log(f'   1551: скарг трьох видів {sum(nsk.values()):,}, з точкою {nsk["з адресою"]:,}; '
        f'звернень на адресах {sum(x[2] for x in vse):,}; останнє {last}')
    return dict(sk=sk, vse=vse, last=last, nsk=dict(nsk),
                spt=Pts([x[3] for x in sk]), vpt=Pts([x[1] for x in vse]))


def golos_misce(G, th, pts, dmap, rad=R_MISCE):
    """Голос мешканців для місця (одна чи кілька точок): скарги того ж виду
    за 12 місяців у rad м проти очікуваного — частка виду серед усіх звернень
    району × усі звернення місця. p < 0,05 — «підтверджують»."""
    if th in NE_VYMIR: return dict(stan='не вимірюється')
    if G is None: return dict(stan='немає даних')
    if th not in VYD1551.values(): return dict(stan='не вимірюється')
    lo = (dt.date.fromisoformat(G['last']) - dt.timedelta(days=365)).isoformat()
    ks, kv_ = set(), set()
    for p in pts:
        ks.update(G['spt'].near(p[0], p[1], rad)); kv_.update(G['vpt'].near(p[0], p[1], rad))
    sk = [G['sk'][k] for k in ks if G['sk'][k][1] == th and G['sk'][k][0] >= lo]
    vse = sum(G['vse'][k][2] for k in kv_ if G['vse'][k][0] >= lo[:7])
    d = dmap(pts[0])
    share = G['share'].get((d, th), G['share_misto'].get(th, 0))
    exp = share * vse
    n = len(sk)
    p = pois_sf(n, exp) if exp > 0 else (1.0 if n == 0 else 0.0)
    top = [c for c, _ in collections.Counter(x[2] for x in sk).most_common(3)]
    return dict(stan='підтверджують' if n > 0 and p < 0.05 else 'мовчать', skarg=n,
                ochikuvano=round(exp, 2), vidnoshennia=round(n / exp, 2) if exp > 0 else None,
                p=round(p, 4), kategorii=top, zvernen=vse)


def dolia_raionu(G, dmap):
    """частка кожного виду серед усіх звернень району за 12 місяців"""
    lo = (dt.date.fromisoformat(G['last']) - dt.timedelta(days=365)).isoformat()
    kind = collections.Counter(); allv = collections.Counter()
    for d_, th, _c, p in G['sk']:
        if d_ >= lo: kind[(dmap(p), th)] += 1
    for mon, p, n in G['vse']:
        if mon >= lo[:7]: allv[dmap(p)] += n
    G['share'] = {k: v / allv[k[0]] for k, v in kind.items() if allv[k[0]]}
    tot = sum(allv.values()) or 1
    G['share_misto'] = {th: sum(v for k, v in kind.items() if k[1] == th) / tot
                        for th in VYD1551.values()}


# ---------------------------------------------------------------- події
def podii(V, log):
    """Події карти на точному будинку, з датою події, класом, механізмом і
    тим, чи заявна вона (Р2, з поділом хуліганства за фабулою)."""
    import step3_map as S3
    TKD, fab = V['TKD'], V['fab']
    out, n_ots = [], 0
    for r in V['rows']:
        th = PD.theme(r[2])
        if th not in KAT or r[9] != 'house': continue
        tk = TKD.get(r[0]) or {}
        ed = S3.ev_date(tk, r[3])
        try:
            if ed: dt.date.fromisoformat(ed[:10])
        except ValueError:
            ed = ''              # описка в тексті: «31.11.2025» — дати немає
        otsinna = not ed
        if otsinna:
            # дата події невідома — дата рішення мінус медіанна затримка (Р3)
            if not r[3]: continue
            ed = (dt.date.fromisoformat(r[3][:10]) - dt.timedelta(days=ZATRYMKA_DNIV)).isoformat()
            n_ots += 1
        f = tk.get('fab') or fab.get(r[0], '')
        out.append(dict(doc=r[0], cat=r[2], th=th, sim=M.simgroup(r[2]), date=ed[:10],
                        otsinna=otsinna, klas=tk.get('klass') or '', p=(r[7], r[8]),
                        adr=f'{r[5] or ""}, {r[6] or ""}'.strip(', '), dec=r[3] or '',
                        zayavna=not M.is_proactive_event(r[2], f), fab=(f or '').lower()))
    log(f'   подій на точному будинку: {len(out):,} (дата оцінна: {n_ots:,})')
    return out


def mistsia(ev):
    """(механізм) -> адреси в 30 м склеєні в одне місце. Union-find по
    точках адрес одного механізму."""
    by = collections.defaultdict(list)
    for i, e in enumerate(ev): by[e['sim']].append(i)
    place = {}
    for sim, ids in by.items():
        pts = sorted({ev[i]['p'] for i in ids})
        pi = {p: k for k, p in enumerate(pts)}
        par = list(range(len(pts)))
        def f(x):
            while par[x] != x: par[x] = par[par[x]]; x = par[x]
            return x
        g = Pts(pts)
        for k, p in enumerate(pts):
            for j in g.near(p[0], p[1], R_MISCE):
                a, b = f(k), f(j)
                if a != b: par[a] = b
        for i in ids: place[i] = (sim, 'т', pts[f(pi[ev[i]['p']])])
    return place


def vorota(evs, S, kind_q):
    """Ворота Р1–Р3 для набору подій однієї пари. Повертає (прапорці,
    статус, підсумки). Порядок воріт — як у воронці."""
    b = [e for e in evs if e['klas'] == 'B']
    g = dict(R1=bool(b))
    if not b: return g, 'не перевірена адреса', {}
    # дублі однієї події — та сама дата на тій самій адресі
    uniq = {}
    for e in b: uniq.setdefault((e['adr'], e['date']), e)
    u = list(uniq.values())
    zay = sum(e['zayavna'] for e in u) / len(u)
    g['R2'] = zay >= ZAYAVNI_MIN
    qs = {kv(e['date']) for e in u}
    last = max(e['date'] for e in u)
    g['R3_podii'] = len(u) >= MIN_POD
    g['R3_kvartaly'] = len({q for q in qs if q > kind_q - KV_VIKNO}) >= MIN_KV
    g['R3_svizhist'] = (dt.date.fromisoformat(S) - dt.date.fromisoformat(last)).days <= SVIZHIST_DNIV
    if not g['R2']: st = 'проактивна'
    elif not g['R3_podii']: st = 'мало'
    elif not g['R3_svizhist']: st = 'згасла'
    elif not g['R3_kvartaly']: st = 'гостра'
    else: st = 'хронічна'
    lo4 = kind_q - 4
    kk = sum(1 for e in u if 'КК' in (L.CODE.get(e['cat']) or ('', ''))[1])
    return g, st, dict(podii=len(u), zayavnykh=round(zay, 2), ostannia=last,
                       kvartaly=sorted(kv_name(q) for q in qs if q > kind_q - KV_VIKNO),
                       za_4kv=sum(1 for e in u if kv(e['date']) > lo4),
                       otsinnykh=sum(e['otsinna'] for e in u),
                       # Шкода — поле, не сортує (Р6): частка кримінальних
                       # проступків, поки ваги шкоди не перевірені юристом
                       shkoda_kk=round(kk / len(u), 2), evs=u)


def formuietsia(u, kind_q, n_last=2, n_prev=6, min_n=3):
    """Р3.2: останні n_last кварталів проти попередніх n_prev, тест Пуассона.
    До попередніх додаємо одну подію, щоб місце без історії не отримувало
    p = 0 від будь-якої першої події."""
    last = sum(1 for e in u if kv(e['date']) > kind_q - n_last)
    prev = sum(1 for e in u if kind_q - n_last - n_prev < kv(e['date']) <= kind_q - n_last)
    lam = (prev + 1) * n_last / n_prev
    p = pois_sf(last, lam)
    return (last >= min_n and p < 0.01), dict(ostanni=last, poperedni=prev, p_=round(p, 5))


_FGRID = {}
def seredovyshche(pts, evs, FACT):
    env = []
    for c in (FACT or {}).get('cats', []):
        s = SERED.get(c.get('k'))
        if not s or s in env or not c['pts']: continue
        g = _FGRID.get(id(c)) or _FGRID.setdefault(id(c), Pts([tuple(q) for q in c['pts']]))
        if any(g.near(p[0], p[1], R_SERED) for p in pts[:3]): env.append(s)
    dzherelo = 'OSM' if env else ''
    if not env:
        fabs = [e['fab'] for e in evs if e['fab']]
        for s, words in FAB_SERED:
            k = sum(1 for f in fabs if any(w in f' {f} ' for w in words))
            if fabs and k >= len(fabs) / 3: env.append(s)
        dzherelo = 'фабула' if env else ''
    return env, dzherelo


# ---------------------------------------------------------------- Р8
N_PEREST = 200        # перестановок (NAPRYAM-PROBLEMY, завдання, п. 8)
P_R8 = 0.05           # пара проходить ворота 6, якщо так густо випадково — рідше


def nulovyi_riven(ev, S, kind_q, zapysy, log, seed=28):
    """Р8. Скільки пар пройшли б ворота Р3 випадково.

    Події кожного механізму (клас B) N_PEREST разів розкладаємо заново по
    місцях, де фіксують події, з імовірністю, пропорційною кількості подій
    ІНШИХ механізмів на цьому місці (+1): «будинки з тією ж щільністю».
    Власні події механізму у вагу не йдуть — інакше нульовий рівень сам
    повторював би скупчення, яке ми перевіряємо. Дата кожної події
    лишається її датою, тож квартали й свіжість рахуються чесно.

    Ворота 6 для пари: частка перестановок, де на її місце випало стільки ж
    подій або більше, — менша за P_R8."""
    import numpy as np
    b = [e for e in ev if e['klas'] == 'B']
    pts = sorted({e['p'] for e in b})
    # місця — адреси в 30 м разом, як і в самих парах
    par = list(range(len(pts))); g = Pts(pts)
    def f(x):
        while par[x] != x: par[x] = par[par[x]]; x = par[x]
        return x
    for k, p in enumerate(pts):
        for j in g.near(p[0], p[1], R_MISCE):
            a, c = f(k), f(j)
            if a != c: par[a] = c
    roots = sorted({f(k) for k in range(len(pts))})
    rid = {r: i for i, r in enumerate(roots)}
    pmap = {p: rid[f(k)] for k, p in enumerate(pts)}
    nP = len(roots)
    by = collections.defaultdict(list)
    for e in b: by[e['sim']].append(e)
    tot = np.bincount([pmap[e['p']] for e in b], minlength=nP).astype(float)
    Sd = dt.date.fromisoformat(S).toordinal()
    rng = np.random.default_rng(seed)
    real = collections.defaultdict(list)
    for r in zapysy:
        if r['status'] == 'хронічна' and r['riven'] == 'точка':
            real[r['sim']].append(r)
    out = {}
    for sim, es in by.items():
        if sim == 'ДОР_ДТП' or (sim not in real and sum(e['zayavna'] for e in es) * 2 < len(es)):
            # ДТП з майном — окремий клас (Р4); проактивний механізм пар однаково не дає (Р2)
            continue
        own = np.bincount([pmap[e['p']] for e in es], minlength=nP).astype(float)
        w = tot - own + 1.0; w /= w.sum()
        q = np.array([kv(e['date']) for e in es]); q = np.where(q > kind_q - KV_VIKNO, q, -1)
        d = np.array([dt.date.fromisoformat(e['date']).toordinal() for e in es])
        recent = (Sd - d) <= SVIZHIST_DNIV
        # місця реальних проблем і скільки там подій
        tgt = [(r, pmap.get(min(pts, key=lambda p: dist(p, r['p'])) if tuple(r['p']) not in pmap
                        else tuple(r['p'])), r['podii']) for r in real.get(sim, [])]
        ge = np.zeros(len(tgt)); npass = []
        for _ in range(N_PEREST):
            a = rng.choice(nP, size=len(es), p=w)
            cnt = np.bincount(a, minlength=nP)
            cand = np.nonzero(cnt >= MIN_POD)[0]
            ok = 0
            if len(cand):
                cs = set(cand.tolist())
                qs = collections.defaultdict(set); rc = collections.Counter()
                for k in range(len(es)):
                    if a[k] in cs:
                        if q[k] >= 0: qs[a[k]].add(q[k])
                        if recent[k]: rc[a[k]] += 1
                ok = sum(1 for c in cand if len(qs[c]) >= MIN_KV and rc[c] > 0)
            npass.append(ok)
            for i, (_r, pl, n) in enumerate(tgt):
                if pl is not None and cnt[pl] >= n: ge[i] += 1
        for i, (r, _pl, _n) in enumerate(tgt):
            pv = (1 + ge[i]) / (N_PEREST + 1)
            r['vorota']['R8'] = bool(pv < P_R8)
            r['r8_p'] = round(float(pv), 4)
        out[sim] = dict(realnykh=len(real.get(sim, [])), vypadkovo_serednie=round(float(np.mean(npass)), 2),
                        vypadkovo_95=int(np.percentile(npass, 95)), podii=len(es))
    log('   Р8 (нульовий рівень): ' + '; '.join(
        f"{M.simname(k)} {v['realnykh']} проти {v['vypadkovo_serednie']} випадково"
        for k, v in sorted(out.items(), key=lambda x: -x[1]['realnykh']) if v['realnykh'] or v['vypadkovo_serednie'] >= 1))
    return out


# ------------------------------------------------- 1551 для «Схожих умов»
N_VYPADK = 200        # випадкових наборів вулиць для порівняння
R_VULYTSIA = 30       # м: скарга «на вулиці», якщо ближче до її лінії


def _shchilno(pts, krok=20.0):
    """точки вздовж лінії через ~20 м — щоб «30 м від лінії» рахувалося
    й посередині довгого відрізка, а не лише біля вершин"""
    out = []
    for a, b in zip(pts, pts[1:]):
        n = max(1, int(dist(a, b) // krok))
        out += [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(n)]
    return out + [tuple(pts[-1])]


def skhozhi_1551(G, dmap, log, seed=31):
    """PIDKHID, розд. 3.3 і 5.1: 1551 — не чинник моделі, а незалежна
    перевірка. Скарги того ж виду за 12 місяців на вулицях шару «Схожі умови»
    проти випадкових вулиць — та сама кількість, ті самі райони, N_VYPADK
    разів. Окремо — «тихі вулиці» шару, на які мешканці скаржаться."""
    import numpy as np
    rk = os.path.join(DATA, 'risk.json'); rawp = os.path.join(DATA, 'osm_risks_raw.json')
    if G is None or not os.path.exists(rk) or not os.path.exists(rawp): return None
    import step4_engine as E4
    layers = json.load(open(rk, encoding='utf-8')).get('layers', {})
    segs = []
    for w in json.load(open(rawp, encoding='utf-8')).get('roads', []):
        g = [(q['lat'], q['lon']) for q in w.get('geometry') or []]
        if len(g) > 1 and E4.seg_len(g) >= 40: segs.append(g)
    if not segs: return None
    lo = (dt.date.fromisoformat(G['last']) - dt.timedelta(days=365)).isoformat()
    rng = np.random.default_rng(seed)

    def skargy(pts, th):
        ks = set()
        for p in _shchilno(pts):
            ks.update(G['spt'].near(p[0], p[1], R_VULYTSIA))
        return [G['sk'][k] for k in ks if G['sk'][k][1] == th and G['sk'][k][0] >= lo]

    # район кожної вулиці — за серединою; пул випадкових — усі вулиці району
    rai = [dmap(tuple(s[len(s) // 2])) for s in segs]
    pool = collections.defaultdict(list)
    for i, d in enumerate(rai): pool[d].append(i)
    cache = {}
    out = {}
    for th, lay in layers.items():
        if th not in VYD1551.values(): continue       # про інші види 1551 мовчить
        items = lay.get('items', [])
        if not items: continue
        n_obs = sum(len(skargy(it[0], th)) for it in items)
        d_of = [dmap(tuple(it[0][len(it[0]) // 2])) for it in items]
        need = collections.Counter(d_of)
        sim, simkm = [], []
        # Довша вулиця збирає більше скарг просто тому, що довша; модель
        # ранжує з урахуванням довжини, тож порівнюємо ще й на кілометр.
        km_obs = sum(E4.seg_len(it[0]) for it in items) / 1000
        for _ in range(N_VYPADK):
            tot, km = 0, 0.0
            for d, k in need.items():
                cand = pool.get(d) or list(range(len(segs)))
                for j in rng.choice(len(cand), size=min(k, len(cand)), replace=False):
                    sid = cand[j]
                    if (sid, th) not in cache: cache[(sid, th)] = len(skargy(segs[sid], th))
                    tot += cache[(sid, th)]
                    km += E4.seg_len(segs[sid]) / 1000
            sim.append(tot); simkm.append(tot / km if km else 0)
        mean = float(np.mean(sim))
        pv = (1 + sum(1 for x in sim if x >= n_obs)) / (N_VYPADK + 1)
        tykhi = []
        for it in lay.get('quiet', []):
            sk = skargy(it[0], th)
            if sk:
                tykhi.append(dict(vulytsia=it[1], skarg=len(sk), p=list(it[0][len(it[0]) // 2]),
                                  kategorii=[c for c, _ in collections.Counter(x[2] for x in sk).most_common(3)]))
        tykhi.sort(key=lambda x: -x['skarg'])
        out[th] = dict(vyd=L.THEMES.get(th, th), vulyts=len(items), skarg=n_obs,
                       vypadkovo=round(mean, 1), vypadkovo_95=int(np.percentile(sim, 95)),
                       raziv=round(n_obs / mean, 2) if mean else None, p=round(pv, 3),
                       km=round(km_obs, 1), na_km=round(n_obs / km_obs, 2) if km_obs else None,
                       vypadkovo_na_km=round(float(np.mean(simkm)), 2),
                       p_na_km=round((1 + sum(1 for x in simkm if x >= n_obs / km_obs)) / (N_VYPADK + 1), 3) if km_obs else None,
                       tykhi_zi_skargamy=tykhi, tykhykh=len(lay.get('quiet', [])))
        log(f"   1551 на «Схожих умовах», {L.THEMES.get(th, th)}: {n_obs} скарг на {len(items)} вулицях "
            f"проти {mean:.1f} на випадкових (p {pv:.3f}); на км {out[th]['na_km']} проти {out[th]['vypadkovo_na_km']} "
            f"(p {out[th]['p_na_km']}); тихих зі скаргами {len(tykhi)} з {len(lay.get('quiet', []))}")
    res = dict(do=G['last'], vid=lo, n_vypadk=N_VYPADK, radius_m=R_VULYTSIA, vydy=out)
    json.dump(res, open(os.path.join(DATA, 'skhozhi_1551.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    return res


def zvit_1551_md(res, path):
    """Окремий файл для чату «Проблеми» — ті самі числа, що в методиці."""
    w = [f'# 1551 на вулицях «Схожих умов»\n',
         f'Складено {dt.date.today().strftime("%d.%m.%Y")} (`src/problems.py`, `skhozhi_1551`). Скарги 1551 того ж виду '
         f'за 12 місяців ({res["vid"]} — {res["do"]}) у {res["radius_m"]} м від лінії вулиці. Порівняння — '
         f'{res["n_vypadk"]} наборів випадкових вулиць: та сама кількість, ті самі райони. p — частка випадкових '
         'наборів, де скарг стільки ж або більше. Про наркотики, насильство й майно 1551 мовчить — їх тут немає.\n',
         '| Вид | Вулиць шару | Скарг на них | Випадково (середнє) | 95% випадкових ≤ | Разів | p | Скарг на км: шар / випадково | p на км |',
         '|---|---|---|---|---|---|---|---|---|']
    for v in res['vydy'].values():
        w.append(f"| {v['vyd']} | {v['vulyts']} | {v['skarg']} | {v['vypadkovo']} | {v['vypadkovo_95']} | "
                 f"{v['raziv'] if v['raziv'] is not None else '—'} | {v['p']} | {v['na_km']} / {v['vypadkovo_na_km']} | {v['p_na_km']} |")
    w.append('\nНа кілометр — бо вулиця шару буває довшою за випадкову, а довша вулиця збирає більше скарг '
             'просто довжиною. Висновок про вид тримається, лише якщо p мале в обох стовпцях.')
    for v in res['vydy'].values():
        w.append(f"\n## Тихі вулиці зі скаргами — {v['vyd']}\n")
        w.append(f"Подій за роки навчання не було, умови схожі; мешканці скаржаться: "
                 f"{len(v['tykhi_zi_skargamy'])} з {v['tykhykh']} тихих вулиць.\n")
        if v['tykhi_zi_skargamy']:
            w.append('| Вулиця | Скарг за рік | Найчастіше |\n|---|---|---|')
            for t in v['tykhi_zi_skargamy']:
                w.append(f"| {t['vulytsia'] or 'без назви'} | {t['skarg']} | {'; '.join(t['kategorii'])} |")
    open(path, 'w', encoding='utf-8', newline='\n').write('\n'.join(w) + '\n')


def run(V=None, log=print, FACT=None):
    """Увесь відбір. Повертає звіт і пише data/problems_report.json."""
    if V is None:
        import sqlite3, step3_map as S3
        V = S3.vybir(sqlite3.connect(os.path.join(DATA, 'events.db')), print=lambda *a, **k: None)
    if FACT is None:
        fp = os.path.join(DATA, 'factors.json')
        FACT = json.load(open(fp, encoding='utf-8')) if os.path.exists(fp) else {}
    log('відбір проблем (В1):')
    ev = podii(V, log)
    if not ev: return None
    S = max(e['dec'][:10] for e in ev if e['dec'])          # знімок даних — останнє рішення
    kind_q = kv(S)

    # райони — для рівня 1551 і для карти
    import map_problems as MP
    B = json.load(open(MP.BORD, encoding='utf-8')) if os.path.exists(MP.BORD) else {}
    DB_ = {d: (min(q[0] for q in r), max(q[0] for q in r), min(q[1] for q in r), max(q[1] for q in r))
           for d, r in B.items()}
    dcache = {}
    def dmap(p):
        if p in dcache: return dcache[p]
        res = None
        for d, r in B.items():
            y0, y1, x0, x1 = DB_[d]
            if y0 <= p[0] <= y1 and x0 <= p[1] <= x1 and MP.in_ring(p[0], p[1], r): res = d; break
        dcache[p] = res
        return res

    G = load_1551(log)
    if G: dolia_raionu(G, dmap)

    # ---- рівень «точка» ----
    place = mistsia(ev)
    pary = collections.defaultdict(list)
    for i, e in enumerate(ev): pary[place[i]].append(e)
    funnel = {'точка': collections.Counter(), 'лінія': collections.Counter(),
              'дорожні ділянки': collections.Counter()}
    zapysy, formue, is_problem_ev = [], [], set()

    def zapys(key, evs, riven, pts):
        sim, _t, rep = key
        th = M.simtheme(sim)
        g, st, s = vorota(evs, S, kind_q)
        dor = sim == 'ДОР_ДТП'                    # Р4: окремий клас
        track = 'дорожні ділянки' if dor else riven
        f = funnel[track]; f['пар на вході'] += 1
        for gk, lab in (('R1', 'Р1 клас B'), ('R2', 'Р2 заявні ≥50%'), ('R3_podii', 'Р3 ≥5 подій'),
                        ('R3_svizhist', 'Р3 остання ≤12 міс.'), ('R3_kvartaly', 'Р3 ≥3 квартали з 8')):
            if gk not in g: break
            if not g[gk]:
                f['відпало: ' + lab] += 1; break
        else:
            f['пройшли'] += 1
        u = s.pop('evs', [])
        addrs = collections.Counter(e['adr'] for e in u) if u else collections.Counter()
        rec = dict(riven=track, sim=sim, vyd=th, mekhanizm=M.simname(sim), status=st, vorota=g,
                   p=list(rep), adresy=[a for a, _ in addrs.most_common()], klas='B', **s)
        if u:
            prob = st == 'хронічна'
        if u and g.get('R3_podii'):
            env, dz = seredovyshche(pts, u, FACT)
            rec['typ'] = M.problem_type(sim, env)
            rec['typ']['dzherelo_seredovyshcha'] = dz or 'невизначено'
            if not env: rec['typ']['seredovyshche'] = rec['typ']['seredovyshche'] or 'невизначено'
            rec['proaktyvnykh'] = round(1 - s['zayavnykh'], 2)
            rec['golos'] = golos_misce(G, th, pts, dmap)
            rec['raion'] = dmap(tuple(rep))
        if u:
            rec['statti'] = collections.Counter(e['cat'] for e in u).most_common()
            rec['roky'] = sorted({e['date'][:4] for e in u})
            if prob:
                is_problem_ev.update(id(e) for e in evs)
            elif not dor:
                ok, fz = formuietsia(u, kind_q)
                if ok:
                    formue.append(dict(riven=track, sim=sim, vyd=th, p=list(rep), adresy=rec['adresy'],
                                       dzherelo='ЄДРСР', prymitka='судові дані запізнюються', **fz,
                                       golos=rec.get('golos') or golos_misce(G, th, pts, dmap)))
        zapysy.append(rec)
        return rec

    pary_ev = {}
    for key, evs in pary.items():
        pts = sorted({e['p'] for e in evs}, key=lambda p: -sum(1 for e in evs if e['p'] == p))
        pary_ev[id(zapys((key[0], 'т', pts[0]), evs, 'точка', pts))] = evs

    # ---- Р8: ворота 6 — перевищення над випадковим рівнем ----
    r8 = nulovyi_riven(ev, S, kind_q, zapysy, log)
    for r in zapysy:
        if r['status'] == 'хронічна' and r['riven'] == 'точка' and r['vorota'].get('R8') is False:
            r['status'] = 'випадкова'
            # події «випадкової» точки знову можуть скласти лінію
            is_problem_ev.difference_update(id(e) for e in pary_ev.get(id(r), ()))
            f = funnel['точка']; f['пройшли'] -= 1; f['відпало: Р8 не густіше за випадок'] += 1

    # ---- рівень «лінія»: точки не пройшли — відрізок вулиці × механізм ----
    lines = 0
    rawp = os.path.join(DATA, 'osm_risks_raw.json')
    if os.path.exists(rawp):
        import step4_engine as E4
        raw = json.load(open(rawp, encoding='utf-8'))
        segs, names = {}, {}
        for w in raw.get('roads', []):
            g_ = w.get('geometry')
            if not g_ or len(g_) < 2: continue
            pts = [(q['lat'], q['lon']) for q in g_]
            if E4.seg_len(pts) < 40: continue
            segs[w['id']] = pts; names[w['id']] = (w.get('tags') or {}).get('name', '')
        if segs:
            # Лінія — відрізок СВОЄЇ вулиці: подія прив'язується лише до
            # відрізка з тією самою назвою. Без цього події з Хрещатика
            # «прилипали» до сусіднього відрізка Б. Хмельницького.
            from step2_geocode import skey
            def slova(s):
                return {w for w in skey(s or '').split() if len(w) >= 4}
            sl = {sid: slova(nm) for sid, nm in names.items()}
            by_name = collections.defaultdict(dict)
            for sid in segs:
                for w in sl[sid]: by_name[w][sid] = segs[sid]
            grids = {}
            by = collections.defaultdict(list)
            cache = {}
            for i, e in enumerate(ev):
                if id(e) in is_problem_ev or e['klas'] != 'B': continue
                ws = slova(e['adr'].split(',')[0])
                key = (e['p'], frozenset(ws))
                if key not in cache:
                    best = None
                    for w in ws:
                        if w not in by_name: continue
                        g = grids.get(w) or grids.setdefault(w, E4.SegGrid(by_name[w]))
                        s = g.nearest(*e['p'], SNAP_M)
                        # одна назва має повністю входити в іншу: «Ав. Антонова»
                        # в «Авіаконструктора Антонова» — так, «Північно-Сирецька»
                        # у «Парково-Сирецьку» — ні
                        if s is not None and (ws <= sl[s] or sl[s] <= ws):
                            d = min(dist(e['p'], q) for q in segs[s])
                            if best is None or d < best[0]: best = (d, s)
                    cache[key] = best[1] if best else None
                s = cache[key]
                if s is not None: by[(e['sim'], s)].append((place[i][2], e))
            for (sim, sid), lst in by.items():
                mc = collections.Counter(pl for pl, _e in lst)
                # лінія — лише коли події розкидані: ≥3 місця і жодне не тримає більшості
                if len(mc) < 3 or mc.most_common(1)[0][1] * 2 > len(lst): continue
                evs = [e for _pl, e in lst]
                pts = [pl for pl, _n in mc.most_common()]
                rec = zapys((sim, 'л', pts[0]), evs, 'лінія', pts)
                rec['vidrizok'] = dict(id=sid, nazva=names.get(sid, ''),
                                       geom=segs[sid][::max(1, len(segs[sid]) // 12)])
                lines += 1
    else:
        log('   немає osm_risks_raw.json — рівень «лінія» пропущено')

    # ---- «формується (лише мешканці)» — 1551, три види (розд. 3.2) ----
    if G:
        lo3 = (dt.date.fromisoformat(G['last']) - dt.timedelta(days=91)).isoformat()
        lo12 = (dt.date.fromisoformat(G['last']) - dt.timedelta(days=365)).isoformat()
        by = collections.defaultdict(list)
        for d_, th, c, p in G['sk']:
            if d_ >= lo12: by[(th, p)].append(d_)
        probs = [(r['vyd'], tuple(r['p'])) for r in zapysy if r['status'] == 'хронічна']
        ppt = Pts([p for _t, p in probs])
        evpt = Pts([e['p'] for e in ev])
        for (th, p), ds in by.items():
            n3 = sum(1 for d_ in ds if d_ >= lo3); n9 = len(ds) - n3
            lam = (n9 + 1) / 3
            pv = pois_sf(n3, lam)
            if n3 < 5 or pv >= 0.01: continue
            if any(probs[k][0] == th for k in ppt.near(p[0], p[1], R_MISCE)): continue
            sud = any(ev[k]['th'] == th for k in evpt.near(p[0], p[1], R_MISCE))
            formue.append(dict(riven='точка', vyd=th, p=list(p), dzherelo='1551',
                               status='формується' if sud else 'формується (лише мешканці)',
                               ostanni=n3, poperedni=n9, p_=round(pv, 5)))

    problemy = sorted([r for r in zapysy if r['status'] == 'хронічна' and r['riven'] != 'дорожні ділянки'],
                      key=lambda r: (-r['za_4kv'], -r['podii']))
    dilianky = [r for r in zapysy if r['status'] == 'хронічна' and r['riven'] == 'дорожні ділянки']
    gz = collections.Counter((r['vyd'], r['golos']['stan']) for r in zapysy
                             if r.get('golos') and r['status'] == 'хронічна')
    rep = dict(
        versiia=dict(pravyla=PRAVYLA, podii_do=S, **({'1551_do': G['last']} if G else {}),
                     skladeno=dt.date.today().isoformat()),
        voronka={k: dict(v) for k, v in funnel.items()},
        problem=len(problemy), linii=sum(1 for r in problemy if r['riven'] == 'лінія'),
        dorozhnikh_dilianok=len(dilianky),
        formuietsia=dict(vsogo=len(formue),
                         za_dzherelom=dict(collections.Counter(f['dzherelo'] for f in formue)),
                         lyshe_meshkantsi=sum(1 for f in formue if f.get('status') == 'формується (лише мешканці)')),
        golos={f'{L.THEMES.get(t, t)} — {s}': n for (t, s), n in sorted(gz.items())},
        r8={M.simname(k): v for k, v in r8.items()},
        perelik=problemy, dorozhni_dilianky=dilianky, formuietsia_perelik=formue,
        inshi=[{k: v for k, v in r.items() if k not in ('statti',)} for r in zapysy
               if r['status'] != 'хронічна' and r['status'] != 'не перевірена адреса'][:3000])
    try:
        rep['skhozhi_1551'] = skhozhi_1551(G, dmap, log)
    except Exception as e:                       # перевірка — не привід зупиняти карту
        log(f'   1551 на «Схожих умовах» не пораховано: {e}')
    json.dump(rep, open(REPORT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=list)
    for k, v in funnel.items():
        log(f'   {k}: ' + ', '.join(f'{a} {b:,}' for a, b in v.items()))
    log(f'   проблем {len(problemy)} (з них ліній {rep["linii"]}); дорожніх ділянок {len(dilianky)}; '
        f'формується {len(formue)} -> data/problems_report.json')
    return rep


if __name__ == '__main__':
    r = run()
    # --1551-md: окремий файл для чату «Проблеми» (1551-SKHOZHI-UMOVY.md)
    if '--1551-md' in sys.argv and r and r.get('skhozhi_1551'):
        zvit_1551_md(r['skhozhi_1551'], os.path.join(ROOT, '1551-SKHOZHI-UMOVY.md'))
