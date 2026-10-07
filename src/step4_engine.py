# -*- coding: utf-8 -*-
"""Крок 4. Модель ризику «разом»: історія подій + середовище.

Одиниця аналізу — ВІДРІЗОК ВУЛИЦІ МІЖ ПЕРЕХРЕСТЯМИ (src/vidrizky.py), а не
квадрат сітки. Так робили Davies & Bishop (2013, Crime Science 2(1):10);
Rosser та ін. (2017, JQC 33(3):569-594) показали, що мережа знаходить
приблизно на 20% більше подій за того самого покриття, ніж сітка.

Ризик — усе, що відомо про ймовірність подій: експозиція (події, що вже
були) і вразливість (середовище), Caplan і Kennedy (2016). Рішення Андрія
29.09 (RISHENNYA 33.2.1), завдання 30, частина 3:
  * види (RISHENNYA, розд. 18) і заявні механізми з ≥250 подіями у вікні
    навчання: хуліганство, залишення місця ДТП, крадіжка, ДТП з майном
    «на дорозі» і «на парковці чи у дворі»; проактивні види — з позначкою;
  * лише клас B (адресу названо в описі події) і лише точне місце;
  * історія — з ПОПЕРЕДНЬОГО періоду: навчання «історія 2024 -> події
    2025», перевірка «історія 2025 -> події 2026» і захід -> схід;
    карта — історія останніх 12 повних місяців (без самопідказки);
  * чинники середовища — відбір стійкості (src/rtm.py): 100 прогонів
    elastic net на половині відрізків, λ блоками за районами, поріг 70%;
    історія не штрафується; остаточна — негативна біноміальна;
  * ранг, колір і PAI — за щільністю на метр і на частку довжини;
    шар ховається, якщо PAI < 3.

Перелік типів і радіусів зафіксовано в NAUKA.md до запуску й після
результату не міняється.
"""
import os, re, sys, json, math, sqlite3, collections, time
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
# вулиць, де події справді сталися в перевірочний рік, ще не впала нижче
# PREC_MIN (зміна 7 вересня; рахується на роках, яких модель не бачила).
TOPN     = int(os.environ.get('TOPN', '25'))
TOPGRID  = 200
NGRID    = (25, 35, 50, 70, 100, 140, 200)
PREC_MIN = float(os.environ.get('PREC_MIN', '0.5'))

# Шар щонайменше втричі кращий за випадковий вибір вулиць — інакше його не
# відрізнити від навмання тицьнутого пальця (PLAN-KROK7, розд. 4). Тепер —
# на частку довжини, не на частку відрізків (3.4).
MIN_PAI = 3.0

# Заявні механізми, які мають власну модель (завдання 30, ч. 2). Проактивні
# механізми (сп'яніння, документи, розпивання…) окремих моделей не
# отримують — вони лишаються у своїх видах (RISHENNYA 33.1).
MEKH = ('ГП_хуліг', 'ДОР_залишення_місця', 'МАЙ_крадіжка', 'ДОР_ДТП_дорога', 'ДОР_ДТП_двір')
# Точне місце — будинок або перехрестя двох названих вулиць (RISHENNYA 33.2.3)
TOCHNE = {'house', 'cross'}

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
    'прохідність': 'Davies, Bishop 2013',
    'населення_500м': 'населення як знаменник подій (NAUKA, розд. 2)',
    'клас_дороги': 'будова вулиці (NAUKA, розд. 2)', 'смуг': 'будова вулиці (NAUKA, розд. 2)',
    'проникність': 'будова вулиці (NAUKA, розд. 2)', 'хрестоподібні': 'будова вулиці (NAUKA, розд. 2)',
    'T_подібні': 'будова вулиці (NAUKA, розд. 2)', 'тупик': 'будова вулиці (NAUKA, розд. 2)',
    'звивистість': 'будова вулиці (NAUKA, розд. 2)',
    'перехрестя_всередині': 'будова вулиці (NAUKA, розд. 2)',
}

# Типи з переліку Б1, що не йдуть у модель (у «Що поруч» лишаються)
NE_CHYNNYK = {'лікарні'}

# Проактивні види (RISHENNYA, розд. 29): такі події поліція здебільшого
# виявляє сама, тож шар показує й те, де вона частіше працює. Рахуються,
# але позначаються. Частку для «частково» рахуємо з даних.
PROAKT_VYD = {'АЛК', 'НАР'}
# ---- ЛЮДИ ЗАВЖДИ В МОДЕЛІ (RISHENNYA 34.1, 35.1; ZAVDANNYA-32, 5.1) ----
# Прохідність і населення в 300 м — поправка на кількість людей, а не
# кандидати: без штрафу elastic net і поза відбором стійкості, як історія.
# Інакше аптеки, школи й кафе «на 400–500 м» заміняли собою натовп.
LUDY = ('прохідність', 'населення_300м')
# населення в 500 м був кандидатом; тепер населення — поправка, і друга
# його мірка в кандидатах лише дублювала б її
NE_KANDYDAT = {'населення_500м'}
R_POP = 300
# ---- 1551 У РИЗИКУ (RISHENNYA 35.3; ZAVDANNYA-32, 5.3–5.4) ----
# Для видів, про які 1551 говорить, — друга мірка «скарги мешканців»
# відповідних груп за змістом; ранг на карті — середнє процентилів обох.
GRUPY_MIRKY = {'ГП': ('шум_заклади', 'безпритульні', 'порядок_інше'),
               'АЛК': ('торгівля_МАФ',),
               'ДТП': ('переходи_світлофори', 'обмежувачі', 'тротуари_дорога', 'паркування')}
# 1551 є лише з 08.2025: навчання «ознаки 08.2025–01.2026 -> ціль 02–05.2026»,
# перевірка — ознаки на 4 місяці пізніше -> ціль 06–09.2026 (як у doslid_1551)
VIKNO_1551 = (('2025-08', '2026-01'), ('2026-02', '2026-05'), ('2025-12', '2026-05'), ('2026-06', '2026-09'))
MIN_LUDEJ = 50            # менше мешканців у 300 м — скарги «не вимірюються» (0)
# Події з самою вулицею (35.1 г; 5.5): у ризик лише коротких вулиць
KOROTKA = (2, 400.0)      # не більше 2 відрізків і 400 м разом
PROAKT_CHAST = {'ГП', 'ДОР'}


def sexp(v):
    """exp для кратності. Коли біля об'єкта подій немає зовсім, модель дає
    коефіцієнт із нескінченним інтервалом (розділення) — пишемо 1e6 («∞» у
    звіті), а не падаємо."""
    if v != v: return None
    return round(math.exp(max(min(v, 13.8), -13.8)), 2)


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
    і далі лише клас B на точному місці (будинок чи перехрестя), з місяцем
    події: історія й ціль рахуються вікнами по 12 місяців (3.2)."""
    import step3_map as S3
    c = sqlite3.connect(DB)
    V = S3.vybir(c, print=lambda *a, **k: None)
    TKD, fab = V['TKD'], V['fab']
    out, drop = [], collections.Counter()
    n_dtp = collections.Counter()
    for r in V['rows']:
        th = PD.theme(r[2])
        if th not in L.ORDER: continue
        tk = TKD.get(r[0]) or {}
        if tk.get('klass') != 'B': drop[(th, 'не клас B')] += 1; continue
        vul = r[9] == 'street'
        if r[9] not in TOCHNE and not vul: drop[(th, 'не точне місце')] += 1; continue
        d = (S3.ev_date(tk, r[3]) or r[3] or '')[:10]
        if len(d) < 7: drop[(th, 'без дати')] += 1; continue
        f = tk.get('fab') or fab.get(r[0], '')
        sim = M.simgroup(r[2]) or ''
        pro = M.is_proactive_event(r[2], f)
        mekh = sim if sim in MEKH and not pro else ''
        if sim == 'ДОР_ДТП':
            # ст. 124 — два механізми за фабулою (завдання 29, п. 6.5)
            mekh = M.dtp_chastyna(f)
            n_dtp[mekh] += 1
        out.append(dict(th=th, sim=sim, mekh=mekh, d=d, m=d[:7], la=r[7], lo=r[8], pro=pro,
                        street=r[5] or '', fab=f, vul=vul))
    log(f'   подій на карті: {len(V["rows"]):,}; клас B на точному місці: {len(out):,}; '
        f'ДТП з майном: ' + ', '.join(f'{M.simname(k)} {v:,}' for k, v in n_dtp.items()))
    return out, drop


def oznaky_tochok(raw, T, SEG, byid, log=print):
    """Змінні точок (ZAVDANNYA-32, 6): ті самі типи середовища в тих самих
    радіусах, що в ліній, прохідність (найбільша серед відрізків у 30 м),
    населення в 300 м і тип точки. -> (X, назви, типи, радіуси, форми)"""
    import numpy as np
    from sklearn.neighbors import BallTree
    import step2b_risks as S2B, vidrizky as VR, rtm_tochky as RT
    R_E = 6371000.0
    P = np.array([[t['la'], t['lo']] for t in T])
    cols, cname, ctyp, cform, crad = [], [], [], [], []
    for key, (ua, _q) in S2B.B1.items():
        if ua in NE_CHYNNYK: continue
        Q = el_pts(raw.get(key))
        if not Q: continue
        tq = BallTree(np.radians(np.array(Q)), metric='haversine')
        for r in RADII:
            c = tq.query_radius(np.radians(P), r / R_E, count_only=True).astype(float)
            if c.max() == 0: continue
            cols += [(c > 0).astype(float), c]; cname += [f'{ua}_є_{r}м', f'{ua}_{r}м']
            ctyp += [ua, ua]; cform += ['є', 'скільки']; crad += [r, r]
    def cont(nm, v):
        v = np.asarray(v, dtype=float); sd = v.std()
        if sd == 0: return
        cols.append((v - v.mean()) / sd); cname.append(nm); ctyp.append(None); cform.append('величина'); crad.append(None)
    PV = VR.Pryviazka(SEG)
    cont('прохідність', np.log1p([max([byid.get(sid, 0) for sid in PV.blyzki(t['la'], t['lo'], 30)] or [0]) for t in T]))
    import step2c_network as S2C
    hs = S2C.budynky(raw, log=lambda *a: None)
    if hs:
        ppl = np.array(S2C.naselennia(hs, log=lambda *a: None))
        th_ = BallTree(np.radians(np.array([[h[0], h[1]] for h in hs])), metric='haversine')
        cont('населення_300м', np.log1p([ppl[i].sum() for i in th_.query_radius(np.radians(P), R_POP / R_E)]))
    for ty in RT.TYPY:
        v = np.array([1.0 if t['typ'] == ty else 0.0 for t in T])
        if 0 < v.sum() < len(v):
            cols.append(v); cname.append('тип: ' + ty); ctyp.append(None); cform.append('тип'); crad.append(None)
    return np.column_stack(cols), cname, ctyp, cform, crad


def oznaky(raw, log=print):
    """Відрізки між перехрестями й змінні-кандидати середовища — одні для
    моделі (main) і для дослідження 1551 (doslid_1551): кандидати мають
    бути ті самі, інакше порівняння «що додає 1551» нечесне."""
    import numpy as np
    from sklearn.neighbors import BallTree
    import step2b_risks as S2B
    byid = {}
    # ---- 1. відрізки вулиць між перехрестями (ZAVDANNYA-30, 1.1) ----
    import vidrizky as VR
    SEG = VR.build(VR.vulytsi(raw))
    segs = {s: v['pts'] for s, v in SEG.items()}
    RD = {s: v['tags'] for s, v in SEG.items()}
    names = {s: v['name'] for s, v in SEG.items()}
    sids = sorted(segs)
    mid = np.array([segs[s][len(segs[s])//2] for s in sids])
    slen = np.array([SEG[s]['len'] for s in sids])
    # Довжина кварталу (RTMDx радить середню для міста): щоб у звіті було
    # видно, скільки кварталів дає кожен радіус-кандидат.
    blocks_m = int(round(float(slen.mean())))
    n_ways = sum(1 for w in VR.vulytsi(raw) if len(w.get('geometry') or []) > 1
                 and seg_len([(p['lat'], p['lon']) for p in w['geometry']]) >= 40)
    log(f'відрізків вулиць: {len(sids):,} між перехрестями (ліній OSM ≥40 м — {n_ways:,}); '
        f'середня довжина (квартал) {blocks_m} м')

    # ---- 2. ознаки-кандидати ----
    log('1) ознаки середовища...')
    tree_m = BallTree(np.radians(mid), metric='haversine')
    R_E = 6371000.0
    cols, cname, ctyp, cform, crad = [], [], [], [], []
    COUNT = {}                   # (тип, r) -> кількість у колі, для чинників вулиці
    for key, (ua, _q) in S2B.B1.items():
        # Лікарні — не чинник (RISHENNYA, розд. 30, п. 5): адреси установ
        # карта прибирає, тож подій біля лікарень немає за визначенням, і
        # модель знаходила «нуль» від вади даних, а не від місця.
        if ua in NE_CHYNNYK: continue
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

    # Прохідність — одна (RISHENNYA 34.1, 35.2): без неї метро забирає собі
    # все (розд. 7.1), а аптеки й кафе заміняють собою натовп (ANALIZ 5.2).
    npth = os.path.join(DATA, 'network.json')
    if os.path.exists(npth):
        byid = VR.potik(json.load(open(npth, encoding='utf-8')).get('items', []))
        # network.json старого формату (до 30.09) рахував потік на лінію OSM
        # (id — число). Доки крок 2c не перерахував його на відрізки, відрізок
        # бере потік своєї лінії: це та сама середня по лінії, що й була.
        if byid and not any(isinstance(k, str) for k in byid):
            log('   network.json — по лініях OSM (старий формат): відрізок бере потік своєї лінії')
            byid = {s: byid[SEG[s]['way']] for s in sids if SEG[s]['way'] in byid}
        rv = [byid.get(s, 0) for s in sids]
        cont('прохідність', np.log1p(rv), rv)
    pp = os.path.join(DATA, 'population.json')
    pop300 = np.zeros(len(sids))
    if os.path.exists(pp):
        Pp = json.load(open(pp, encoding='utf-8'))['items']
        tpp = BallTree(np.radians(np.array([[x[0], x[1]] for x in Pp])), metric='haversine')
        w_ = np.array([x[2] for x in Pp], dtype=float)
        ind = tpp.query_radius(np.radians(mid), 500 / R_E)
        rv = [w_[i].sum() for i in ind]
        cont('населення_500м', np.log1p(rv), rv)
        # Населення в 300 м — з мешканців будинків (шестикутник Kontur, поділений
        # за площею поверхів, як у прохідності, step2c): центри шестикутників
        # стоять через ~500 м, і в 300 м від відрізка їх часто немає зовсім.
        import step2c_network as S2C
        hs = S2C.budynky(raw, log=lambda *a: None)
        if hs:
            ppl = np.array(S2C.naselennia(hs, log=lambda *a: None))
            th_ = BallTree(np.radians(np.array([[h[0], h[1]] for h in hs])), metric='haversine')
            pop300 = np.array([ppl[i].sum() for i in th_.query_radius(np.radians(mid), R_POP / R_E)])
            log(f'   населення в 300 м — з {len(hs):,} будинків')
        else:
            w3 = tpp.query_radius(np.radians(mid), R_POP / R_E)
            pop300 = np.array([w_[i].sum() for i in w3])
            log('   будинків OSM немає — населення в 300 м з центрів шестикутників Kontur')
        cont('населення_300м', np.log1p(pop300), pop300)
    HW = {'residential': 1, 'living_street': 1, 'unclassified': 2,
          'tertiary': 3, 'secondary': 4, 'primary': 5, 'trunk': 6, 'motorway': 6}
    # з'їзд (_link) — того ж класу, що й дорога, до якої він веде
    cont('клас_дороги', [HW.get(RD[s].get('highway', '').replace('_link', ''), 2) for s in sids])
    cont('смуг', [float(RD[s].get('lanes')) if str(RD[s].get('lanes', '')).isdigit() else 2.0
                  for s in sids])
    # Будова вулиці — прямо з графа вулиць (vidrizky.budova), а не з
    # netgeo.json кроку 2c: той крок падає без пішохідної мережі, і тоді
    # модель тихо лишалася без будови вулиці.
    NG = VR.budova(SEG, VR.stupeni(VR.vulytsi(raw)))
    for fld, ua in (('perm', 'проникність'), ('cross4', 'хрестоподібні'),
                    ('cross3', 'T_подібні'), ('dead', 'тупик'),
                    ('sinuo', 'звивистість'), ('inner', 'перехрестя_всередині')):
        cont(ua, [float(NG.get(s, {}).get(fld, 0)) for s in sids])
    X = np.column_stack(cols)
    med = np.median(X, axis=0)
    log(f'   змінних-кандидатів: {X.shape[1]} ({sum(1 for t in ctyp if t)} — типи × радіуси × форми)')

    # ЕКСПОЗИЦІЯ: довжина вулиці. Модель вчиться на щільності подій на метр,
    # оцінка множиться назад на довжину.
    expo = np.maximum(slen, 20.0); expo = expo / expo.mean()

    return dict(SEG=SEG, segs=segs, RD=RD, names=names, sids=sids, mid=mid, slen=slen, blocks_m=blocks_m, n_ways=n_ways, X=X, cname=cname, ctyp=ctyp, cform=cform, crad=crad, COUNT=COUNT, RAWV=RAWV, expo=expo, byid=byid, VR=VR, pop300=pop300)


def main():
    import numpy as np
    from sklearn.neighbors import BallTree
    t0 = time.time()
    log = lambda *a: print(*a, flush=True)

    for f in (DB, RAW):
        if not os.path.exists(f): log(f'немає {f}'); sys.exit(1)
    raw = json.load(open(RAW, encoding='utf-8'))
    import step2b_risks as S2B
    pusti = S2B.raiony_bez(raw.get('roads', []))
    if pusti:
        # Кеш OSM без частини міста (порожня плитка Overpass) — модель
        # тихо навчилася б без центру. Краще не вчитися зовсім.
        log('у osm_risks_raw.json немає вулиць у районах: ' + ', '.join(pusti)
            + ' — перезавантажте шар (галочка «Перезавантажити шар ризиків з OSM»)')
        sys.exit(1)
    if not raw.get('dorogy_velyki'):
        # Без магістралей ~8,7 тис. подій на проспектах лишаються «поза
        # вулицями», і модель тихо вчиться без них (перенавчання 29.09).
        log('у osm_risks_raw.json немає магістралей (dorogy_velyki) — спершу крок 2b '
            '(src/step2b_risks.py докачує їх плитками)')
        sys.exit(1)
    miss = [k for k in S2B.B1 if not raw.get(k)]
    if miss:
        # Порожній тип тихо випав би з моделі, і звіт виглядав би так, ніби
        # модель його відкинула. Краще зупинитися.
        log('у osm_risks_raw.json немає типів Б1: ' + ', '.join(miss) + ' — спершу крок 2b')
        sys.exit(1)
    # стара модель — для порівняння в звіті, до того як файли перезапишуться
    OLD = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
    OLDR = json.load(open(RISK, encoding='utf-8')) if os.path.exists(RISK) else {}

    F = oznaky(raw, log)
    SEG = F['SEG']
    segs = F['segs']
    RD = F['RD']
    names = F['names']
    sids = F['sids']
    mid = F['mid']
    slen = F['slen']
    blocks_m = F['blocks_m']
    n_ways = F['n_ways']
    X = F['X']
    cname = F['cname']
    ctyp = F['ctyp']
    cform = F['cform']
    crad = F['crad']
    COUNT = F['COUNT']
    RAWV = F['RAWV']
    expo = F['expo']
    byid = F['byid']
    VR = F['VR']

    # ---- 3. події -> відрізки ----
    log('2) події...')
    ev, drop = podii(log)
    # ---- точки (ZAVDANNYA-32, 6): кандидати й належність подій ----
    import rtm_tochky as RT
    _last = max(e['d'] for e in ev)
    _ly, _lm = int(_last[:4]), int(_last[5:7])
    _r2 = {f'{(t // 12):04d}-{t % 12 + 1:02d}' for t in range(_ly * 12 + _lm - 24, _ly * 12 + _lm)}
    adresy = {(round(e['la'], 5), round(e['lo'], 5)) for e in ev if not e.get('vul') and e['m'] in _r2}
    TOCHKY = os.environ.get('TOCHKY', '1') != '0'
    TP, nal = [], [None] * len(ev)
    if TOCHKY:
        # адрес серед кандидатів немає (рішення Андрія 06.10; rtm_tochky)
        TP = RT.kandydaty(raw, VR.vulytsi(raw), [], VR)
        S_ = RT.Sitka([(t['la'], t['lo']) for t in TP])
        ist = [0] * len(TP)
        for e in ev:
            if e.get('vul') or e['m'] not in _r2: continue
            for d, k in S_.blyzki(e['la'], e['lo'], RT.R_TOCHKA):
                if d <= (RT.R_PEREKH if TP[k]['typ'] == 'перехрестя' else RT.R_TOCHKA): ist[k] += 1
        nal = RT.nalezhnist(ev, TP, ist)
        log(f'   точок-кандидатів {len(TP):,} (' + ', '.join(f'{k} {v:,}' for k, v in collections.Counter(
            t['typ'] for t in TP).most_common()) + f'); подій, що належать точкам: {sum(1 for x in nal if x is not None):,}')
    NP_ = len(TP)
    YP = collections.defaultdict(lambda: np.zeros(NP_))   # (ключ, місяць) -> події точок
    # Прив'язка — до відрізка СВОЄЇ вулиці в SNAP_M, до найближчої точки
    # лінії (завдання 29, п. 6.2); немає такого — найближчий відрізок. Для
    # звіту рахуємо, скільки подій стало на іншу лінію OSM, ніж давала стара
    # прив'язка (найближча вершина будь-якої лінії).
    PV = VR.Pryviazka(SEG)
    old_way = {}
    for w in raw.get('roads', []):
        g = w.get('geometry')
        if g and len(g) > 1:
            pts = [(p['lat'], p['lon']) for p in g]
            if seg_len(pts) >= 40: old_way[w['id']] = pts
    sg_old = SegGrid(old_way)
    six = list(L.ORDER)   # з 06.10 видів сім: ДТП окремо (34.3), ДОМ — у НАС (35.8)
    # B1_VYDY=ГП,МАЙ_крадіжка — прогнати лише названі види й механізми
    # (перевірка коду на копії даних; перенавчання в Actions рахує всі)
    KEYS = [(t, 'тема') for t in six] + [(m, 'механізм') for m in MEKH]
    if os.environ.get('B1_VYDY'):
        KEYS = [k for k in KEYS if k[0] in os.environ['B1_VYDY'].split(',')]
    idx = {s: i for i, s in enumerate(sids)}
    n = len(sids)
    Y = collections.defaultdict(lambda: np.zeros(n))   # (ключ, 'YYYY-MM') -> події на відрізках
    n_snap = collections.Counter(); n_all = collections.Counter(); n_pro = collections.Counter()
    SNAPST = collections.Counter()
    ev_seg = []                                          # (відрізок, подія) — для пішохідного ризику
    cache = {}
    # Коротка вулиця (≤ 2 відрізки, ≤ 400 м, назва однозначна в 3 км від
    # центру вулиці геокодера) — подія без номера йде на її відрізки порівну
    # (5.5). Довга — ні: місця на ній не вигадуємо. На карту точкою — ні.
    sl_all = {sid: VR.slova(SEG[sid]['name']) for sid in sids}
    po_slovu = collections.defaultdict(list)
    for sid, w_ in sl_all.items():
        for x in w_: po_slovu[x].append(sid)
    def korotka(e):
        ws = VR.slova(e['street'])
        if not ws: return None
        c_ = set.intersection(*[set(po_slovu.get(x, ())) for x in ws]) if ws else set()
        c_ = [sid for sid in c_ if VR.ta_sama(ws, sl_all[sid])
              and VR.dovzhyna([(e['la'], e['lo']), SEG[sid]['pts'][len(SEG[sid]['pts']) // 2]]) <= 3000]
        if not c_ or len(c_) > KOROTKA[0] or sum(SEG[x]['len'] for x in c_) > KOROTKA[1]: return None
        return c_
    n_vul = collections.Counter()
    for ie, e in enumerate(ev):
        th = e['th']
        if nal[ie] is not None:
            # подія належить точці — у ціль ліній не йде (подвійного рахунку немає)
            ks_ = [th] + ([e['mekh']] if e['mekh'] else [])
            for k in ks_:
                n_all[k] += 1; n_pro[k] += e['pro']; YP[(k, e['m'])][nal[ie]] += 1
            SNAPST['належить точці'] += 1
            continue
        ks = [th] + ([e['mekh']] if e['mekh'] else [])
        if e.get('vul'):
            ck = ('vul', e['street'], round(e['la'], 3), round(e['lo'], 3))
            if ck not in cache: cache[ck] = korotka(e)
            c_ = cache[ck]
            if not c_: SNAPST['лише вулиця, не коротка'] += 1; continue
            SNAPST['лише вулиця, коротка'] += 1
            for k in ks:
                n_all[k] += 1; n_pro[k] += e['pro']; n_snap[k] += 1; n_vul[k] += 1
                for sid in c_: Y[(k, e['m'])][idx[sid]] += 1 / len(c_)
            continue
        for k in ks: n_all[k] += 1; n_pro[k] += e['pro']
        ck = (round(e['la'], 5), round(e['lo'], 5), e['street'])
        if ck not in cache:
            s, svoya = PV.znaity(e['la'], e['lo'], SNAP_M, VR.vulytsia(e['street']))
            o = sg_old.nearest(e['la'], e['lo'], SNAP_M)
            cache[ck] = (s, svoya, o)
        s, svoya, o = cache[ck]
        if s is None: SNAPST['поза вулицями'] += 1; continue
        SNAPST['своя вулиця' if svoya else 'найближчий відрізок'] += 1
        if o is None or SEG[s]['way'] != o: SNAPST['інша лінія OSM, ніж раніше'] += 1
        for k in ks:
            n_snap[k] += 1
            Y[(k, e['m'])][idx[s]] += 1
        ev_seg.append((idx[s], e))
    log('   прив\'язка: ' + ', '.join(f'{k} {v:,}' for k, v in SNAPST.most_common()))

    # ---- вікна (ZAVDANNYA-30, 3.2) ----
    # Навчання: історія 2024 -> події 2025. Перевірка: історія 2025 -> події
    # 2026 і захід -> схід. Карта: історія за 12 повних місяців, що
    # закінчуються за 2 місяці до останньої дати (затримка судів), —
    # «що далі» на тих самих коефіцієнтах. Нинішнього hit_together (історія
    # й ціль з того самого року) більше немає.
    last = max(e['d'] for e in ev)
    ly, lm = int(last[:4]), int(last[5:7])
    def mshift(y, m, k):
        t = y * 12 + (m - 1) + k
        return f'{t // 12:04d}-{t % 12 + 1:02d}'
    # останній повний місяць перед «остання дата мінус 2 місяці»
    MAPW = [mshift(ly, lm, -3 - j) for j in range(12)][::-1]
    ROKY2 = [mshift(ly, lm, -j) for j in range(24)]
    ROKY3 = [mshift(ly, lm, -j) for j in range(36)]
    def cnt(k, months):
        v = np.zeros(n)
        for m in months:
            a = Y.get((k, m))
            if a is not None: v += a
        return v
    def rik(y): return [f'{y}-{m:02d}' for m in range(1, 13)]
    log(f'   остання дата події {last}; вікно карти {MAPW[0]} — {MAPW[-1]}')

    # райони відрізків — для перехресної перевірки блоками (3.3)
    fold = np.zeros(n, dtype=int)
    bp = os.path.join(DATA, 'borders.json')
    if os.path.exists(bp):
        import map_problems as MP
        B = json.load(open(bp, encoding='utf-8'))
        dn = sorted(B)
        # десять районів — п'ять блоків по два: удвічі швидше, а сусідні
        # відрізки однієї вулиці однаково лишаються в одному блоці
        for i in range(n):
            for di, d in enumerate(dn):
                if MP.in_ring(mid[i][0], mid[i][1], B[d]): fold[i] = di % 5 + 1; break
    lons = mid[:, 1]
    west = lons <= np.median(lons); east = ~west

    # люди — поправка (5.1), решта — кандидати
    JL = [cname.index(x) for x in LUDY if x in cname]
    CAND = [j for j in range(X.shape[1]) if j not in JL and cname[j] not in NE_KANDYDAT]
    XL = X[:, JL]
    log(f'   поправка на людей: {", ".join(cname[j] for j in JL) or "НЕМАЄ (network.json, population.json)"}; '
        f'кандидатів {len(CAND)}')
    def vidbir(y, H, rows=None, runs=None, Xe=None, te=None):
        """відбір стійкості серед кандидатів CAND (і Xe — додаткових, напр.
        1551); H — нештрафовані стовпці. cols — індекси в X, далі ('e', k)."""
        r_ = slice(None) if rows is None else rows
        Xc = X[r_][:, CAND] if Xe is None else np.column_stack([X[r_][:, CAND], Xe[r_]])
        tc = [ctyp[j] for j in CAND] + ([None] * Xe.shape[1] if Xe is not None else [])
        s_ = rtm.stijkist(Xc, y, expo[r_], tc, H=H, folds=fold[r_], runs=runs, log=log)
        mp = lambda c: CAND[c] if c < len(CAND) else ('e', c - len(CAND))
        return dict(cols=[mp(c) for c in s_['cols']], chastka={mp(c): v for c, v in s_['chastka'].items()},
                    typy=s_['typy'], lam=s_['lam'])
    def stovp(cols, Xe=None, rows=None):
        r_ = slice(None) if rows is None else rows
        return np.column_stack([X[r_][:, c] if not isinstance(c, tuple) else Xe[r_][:, c[1]]
                                for c in cols]) if cols else np.zeros((len(expo[r_]), 0))
    def A_(H, cols, Xe=None, rows=None):
        r_ = slice(None) if rows is None else rows
        return np.column_stack([H, XL[r_], stovp(cols, Xe, rows)])

    def hst(v, mu=None, sd=None):
        h = np.log1p(v)
        if mu is None: mu, sd = h.mean(), (h.std() or 1.0)
        return (h - mu) / sd, mu, sd

    def pai(dens, yt):
        return rtm.pai_dovzhyna(dens, yt, slen)

    def factors(fit, cols, sel, k0=1):
        """таблиця чинників: тип, форма, радіус, кратність з 95% інтервалом,
        частка прогонів відбору стійкості — для типу (будь-який його радіус чи
        форма), бо саме за нею тип лишається в моделі"""
        chast, typy = sel['chastka'], sel['typy']
        out = []
        ci = fit.conf_int()
        for k, j in enumerate(cols, start=1 + k0):
            b = float(fit.params[k])
            if isinstance(j, tuple):
                out.append(dict(змінна=EN[j[1]], тип=EN[j[1]], форма='на 1000 мешканців', r=R_POP,
                                кварталів=None, коеф=round(b, 4), RR=sexp(b), RR_від=sexp(ci[k][0]),
                                RR_до=sexp(ci[k][1]), частка_прогонів=round(chast.get(j, 0), 2),
                                джерело='1551 за змістом (RISHENNYA 35.3)'))
                continue
            base = ctyp[j] or cname[j]
            out.append(dict(змінна=cname[j], тип=base, форма=cform[j], r=crad[j],
                            кварталів=round(crad[j] / blocks_m, 1) if crad[j] else None,
                            коеф=round(b, 4), RR=sexp(b), RR_від=sexp(ci[k][0]), RR_до=sexp(ci[k][1]),
                            частка_прогонів=round(typy.get(ctyp[j], chast.get(j, 0)), 2),
                            джерело=SOURCES.get(base, '')))
        return sorted(out, key=lambda d: -abs(d['коеф']))

    def street_facts(fit, cols, i, k0=1, k=3):
        """до трьох стійких чинників, які піднімають оцінку САМЕ ТУТ: внесок
        = коеф × відхилення від середнього (для лог-лінійної моделі це
        розклад оцінки на доданки). Значення — кількість об'єктів у тому
        самому колі, щоб на місці її можна було перерахувати."""
        rows = []
        for k_, j in enumerate(cols, start=1 + k0):
            if isinstance(j, tuple): continue
            b = float(fit.params[k_])
            c = b * (X[i, j] - X[:, j].mean())
            if c <= 0: continue
            if ctyp[j]:
                v = COUNT[(ctyp[j], crad[j])]
                rows.append((c, [f'{ctyp[j]}_{crad[j]}м', round(float(v[i]), 1),
                                 round(float(np.median(v)), 1), sexp(b)]))
            else:
                v = RAWV[cname[j]]
                rows.append((c, [cname[j], round(float(v[i]), 1), round(float(np.median(v)), 1), sexp(b)]))
        return [r for _c, r in sorted(rows, key=lambda x: -x[0])[:k]]

    def vylucheno(cols):
        """6.3: потоки й будова вулиці — завжди кандидати; кого відбір не
        взяв, — з ким він сильно пов'язаний серед обраних (кореляція)"""
        out = []
        for nm_ in ('прохідність', 'клас_дороги', 'смуг'):
            if nm_ not in cname: continue
            j = cname.index(nm_)
            if j in cols: continue
            best = None
            for c in cols:
                r = float(np.corrcoef(X[:, j], X[:, c])[0, 1])
                if r == r and (best is None or abs(r) > abs(best[1])): best = (cname[c], r)
            out.append(dict(змінна=nm_, пов_язана_з=best[0] if best and abs(best[1]) >= 0.3 else None,
                            r=round(best[1], 2) if best else None))
        return out

    def row(i, rk, n2, facts, grid=False, pct=None, mu=None):
        s = sids[i]
        g = [[round(q[0], 5), round(q[1], 5)] for q in segs[s][::max(1, len(segs[s]) // 8)]]
        if g[-1] != [round(segs[s][-1][0], 5), round(segs[s][-1][1], 5)]:
            g.append([round(segs[s][-1][0], 5), round(segs[s][-1][1], 5)])
        r = [g, names[s], round(float(rk[i]), 3), int(n2[i])]
        if not grid:
            # 5-й — стійкі чинники тут; 6-й — «тихий» (подій за 2 роки немає)
            r += [facts, 1 if n2[i] == 0 else 0]
            # 7-й — місце серед УСІХ відрізків міста (верхні N%), 8-й — прогноз
            # подій за 12 місяців (ZAVDANNYA-32, 7.10): карта бере їх, а не
            # місце в короткому переліку показаних
            r += [None if pct is None else round(float(pct[i]), 2), None if mu is None else round(float(mu[i]), 2)]
        return r

    # ---- скарги 1551 за змістом на відрізках (5.2) ----
    import problems as PRB
    import zbir_1551 as Z
    SK = PRB.skargy_hrupy(log)
    EN = list(Z.GRUPY_1551)               # порядок груп = стовпці ознак 1551
    pop300 = F['pop300']
    SKG = {}
    if SK:
        sk_mon = np.array([x[0] for x in SK]); sk_g = np.array([EN.index(x[1]) for x in SK])
        sk_tree = BallTree(np.radians(np.array([x[2] for x in SK])), metric='haversine')
        sk_ind = sk_tree.query_radius(np.radians(mid), R_POP / 6371000.0)
        def skargy(m0, m1, gr=None):
            """відрізки × групи: скарг у 300 м за місяці [m0, m1]"""
            ok = (sk_mon >= m0) & (sk_mon <= m1)
            out = np.zeros((n, len(EN)))
            for i, ix in enumerate(sk_ind):
                ix = ix[ok[ix]]
                if len(ix): out[i] = np.bincount(sk_g[ix], minlength=len(EN))
            return out
        def na_1000(Cn):
            """скарги на 1 000 мешканців у 300 м; менше MIN_LUDEJ — 0 («не вимірюється»)"""
            v = np.where(pop300[:, None] >= MIN_LUDEJ, 1000 * Cn / np.maximum(pop300[:, None], 1), 0.0)
            return v
        def zstd(V, ref):
            lr = np.log1p(ref); sd_ = lr.std(0); sd_[sd_ == 0] = 1
            return (np.log1p(V) - lr.mean(0)) / sd_
        (a1, b1), (a2, b2), (a3, b3), (a4, b4) = VIKNO_1551
        S_tr, S_t1 = skargy(a1, b1), skargy(a2, b2)        # ознаки навчання, ціль навчання
        S_te, S_t2 = skargy(a3, b3), skargy(a4, b4)        # ознаки перевірки, ціль перевірки
        G_tr = zstd(na_1000(S_tr), na_1000(S_tr)); G_te = zstd(na_1000(S_te), na_1000(S_tr))
        last_m = max(sk_mon)
        lm6 = mshift(int(last_m[:4]), int(last_m[5:7]), -5)
        S_map = skargy(lm6, last_m)
        G_map = zstd(na_1000(S_map), na_1000(S_tr))
        SKG = dict(tr=S_tr, t1=S_t1, te=S_te, t2=S_t2, map=S_map)
        log(f'   1551: вікно ознак навчання {a1}—{b1}, ціль {a2}—{b2}; перевірка {a3}—{b3} -> {a4}—{b4}; '
            f'карта — {lm6}—{last_m}')
    def mirka(key):
        th_ = key if key in GRUPY_MIRKY else M.simtheme(key)
        return [EN.index(g) for g in GRUPY_MIRKY.get(th_, ())]

    report, layers, radiusy, kinds = {}, {}, {}, {}
    rk_by = {}
    tochky_out = {}
    XP = None
    if NP_:
        XP, cnameP, ctypP, _cf, _cr = oznaky_tochok(raw, TP, SEG, byid, log)
        JLP = [cnameP.index(x) for x in LUDY if x in cnameP]
        XPL = XP[:, JLP] if JLP else np.zeros((NP_, 0))
        CANDP = [j for j in range(XP.shape[1]) if j not in JLP]
        foldP = np.zeros(NP_, dtype=int)
        if os.path.exists(bp):
            for i, t in enumerate(TP):
                for di, d in enumerate(dn):
                    if MP.in_ring(t['la'], t['lo'], B[d]): foldP[i] = di % 5 + 1; break
        log(f'   змінних точок: {XP.shape[1]}')
    for key, vyd in KEYS:
        th = key if vyd == 'тема' else M.simtheme(key)
        nm = L.THEMES.get(key, key) if vyd == 'тема' else M.simname(key)
        log(f'\n=== {nm} ===')
        pr = n_pro[key] / max(n_all[key], 1)
        if vyd == 'тема' and th in PROAKT_VYD: mark = 'проактивний вид'
        elif vyd == 'тема' and th in PROAKT_CHAST: mark = f'частково проактивний, {round(100 * pr)}%'
        else: mark = ''
        kinds[key] = dict(назва=nm, вид=vyd, подій=n_all[key], на_вулицях=n_snap[key],
                          проактивних=round(pr, 3), позначка=mark,
                          відсіяно={k[1]: v for k, v in drop.items() if k[0] == key})
        y24, y25, y26 = cnt(key, rik(2024)), cnt(key, rik(2025)), cnt(key, rik(2026))
        if y25.sum() < MIN_EV or y26.sum() < 50:
            log(f'   замало подій: {int(y25.sum())} у 2025 (потрібно {MIN_EV}), {int(y26.sum())} у 2026')
            report[key] = dict(вид=vyd, тема=L.THEMES.get(th, th), назва=nm, на_карті=False,
                               сховано='замало подій для навчання', навчання=int(y25.sum()),
                               позначка=mark)
            continue
        Htr, mu, sd = hst(y24)
        Hte, _m, _s = hst(y25, mu, sd)
        Hmap, _m, _s = hst(cnt(key, MAPW), mu, sd)
        n2 = cnt(key, ROKY2)
        log(f'   навчання: історія 2024 ({int(y24.sum())}) -> 2025 ({int(y25.sum())}); '
            f'перевірка: 2025 -> 2026 ({int(y26.sum())})')
        # разом: історія + люди (без штрафу) + середовище (відбір стійкості)
        HL = np.column_stack([Htr, XL])
        sT = vidbir(y25, HL)
        fT, famT = rtm.nb_fit(A_(Htr, sT['cols']), y25, expo)
        pT = rtm.nb_predict(fT, A_(Hte, sT['cols']), expo)
        K0 = 1 + XL.shape[1]
        # ДО поправки на людей — як до 06.10, для звіту (5.1): люди — кандидати
        s0 = rtm.stijkist(X, y25, expo, ctyp, H=Htr, folds=fold, runs=max(20, rtm.N_STAB // 5), log=log)
        f0, _f0 = rtm.nb_fit(np.column_stack([Htr, X[:, s0['cols']]]), y25, expo)
        p0 = rtm.nb_predict(f0, np.column_stack([Hte, X[:, s0['cols']]]), expo)
        PAI_0, _h0 = pai(p0 / slen, y26)
        # лише середовище (з поправкою на людей) — для порівняння у звіті
        sE = vidbir(y25, XL if XL.shape[1] else None)
        fE, _fe = rtm.nb_fit(np.column_stack([XL, stovp(sE['cols'])]), y25, expo)
        pE = rtm.nb_predict(fE, np.column_stack([XL, stovp(sE['cols'])]), expo)
        # щільність — оцінка ÷ довжина: ранг, колір, відбір і PAI (3.4)
        dT, dE, dH = pT / slen, pE / slen, y25 / slen
        PAI_T, hT = pai(dT, y26); PAI_E, hE = pai(dE, y26); PAI_H, hH = pai(dH, y26)
        star = dict(разом=round(rtm.hit_rate(pT, y26) / 0.10, 2),
                    середовище=round(rtm.hit_rate(pE, y26) / 0.10, 2),
                    історія=round(rtm.hit_rate(y25, y26) / 0.10, 2))
        # захід -> схід: відбір і коефіцієнти — лише на заході
        PAI_G = hG = None
        if y25[west].sum() > 60 and y26[east].sum() > 30:
            log('   перенесення захід -> схід:')
            sG = vidbir(y25[west], np.column_stack([Htr[west], XL[west]]), rows=west, runs=max(20, rtm.N_STAB // 2))
            fG, _fg = rtm.nb_fit(A_(Htr[west], sG['cols'], rows=west), y25[west], expo[west])
            pG = rtm.nb_predict(fG, A_(Hte[east], sG['cols'], rows=east), expo[east])
            PAI_G, hG = rtm.pai_dovzhyna(pG / slen[east], y26[east], slen[east])
        # стійкість між роками (6.3): та сама модель, навчена на 2025 -> 2026
        H25, mu5, sd5 = hst(y25)
        sB = vidbir(y26, np.column_stack([H25, XL]), runs=max(20, rtm.N_STAB // 2))
        fB, _fb = rtm.nb_fit(A_(H25, sB['cols']), y26, expo)
        HmapB, _m, _s = hst(cnt(key, MAPW), mu5, sd5)
        pmB = rtm.nb_predict(fB, A_(HmapB, sB['cols']), expo)
        # карта: ті самі коефіцієнти, історія — останні 12 повних місяців;
        # pm — прогноз подій на наступні 12 місяців для кожного відрізка (7.10)
        pm = rtm.nb_predict(fT, A_(Hmap, sT['cols']), expo)
        dm = pm / slen
        facs = factors(fT, sT['cols'], sT, k0=K0)
        facsE = factors(fE, sE['cols'], sE, k0=XL.shape[1])
        facs0 = factors(f0, s0['cols'], s0)
        # з 95% інтервалом, як у factors(): RR людей без інтервалу не каже,
        # чи прохідність справді щось додає (Андрій 07.10)
        ciT = fT.conf_int()
        ludy = {cname[j]: dict(RR=sexp(float(fT.params[2 + k])), RR_від=sexp(ciT[2 + k][0]),
                               RR_до=sexp(ciT[2 + k][1]))
                for k, j in enumerate(JL)}

        # ---- дві мірки — суд і скарги (35.3) ----
        dvi = None
        gm = mirka(key) if SKG else []
        if gm:
            def per(v):
                o = np.argsort(np.argsort(v)); return o / max(len(v) - 1, 1)
            a1, b1 = VIKNO_1551[0]; a2, b2 = VIKNO_1551[1]; a3, b3 = VIKNO_1551[2]; a4, b4 = VIKNO_1551[3]
            mon = lambda a, b: [m for m in sorted({e['m'] for e in ev}) if a <= m <= b]
            yA_tr, yA_t1 = cnt(key, mon(a1, b1)), cnt(key, mon(a2, b2))
            yA_te, yA_t2 = cnt(key, mon(a3, b3)), cnt(key, mon(a4, b4))
            yB_tr, yB_t1 = SKG['tr'][:, gm].sum(1), SKG['t1'][:, gm].sum(1)
            yB_te, yB_t2 = SKG['te'][:, gm].sum(1), SKG['t2'][:, gm].sum(1)
            if yA_t1.sum() >= 30 and yB_t1.sum() >= 30:
                log('   дві мірки (суд і скарги 1551):')
                hA, muA, sdA = hst(yA_tr); hA2, _a, _b = hst(yA_te, muA, sdA)
                hB, muB, sdB = hst(yB_tr); hB2, _a, _b = hst(yB_te, muB, sdB)
                runs2 = max(20, rtm.N_STAB // 2)
                # модель А: суд; 1551 за змістом — кандидати поряд із середовищем (5.4)
                sA = vidbir(yA_t1, np.column_stack([hA, XL]), runs=runs2, Xe=G_tr)
                fA, _ = rtm.nb_fit(A_(hA, sA['cols'], G_tr), yA_t1, expo)
                pA2 = rtm.nb_predict(fA, A_(hA2, sA['cols'], G_te), expo)
                # модель Б: скарги мешканців тих самих груп, ті самі змінні
                sBb = vidbir(yB_t1, np.column_stack([hB, XL]), runs=runs2, Xe=G_tr)
                fBb, _ = rtm.nb_fit(A_(hB, sBb['cols'], G_tr), yB_t1, expo)
                pB2 = rtm.nb_predict(fBb, A_(hB2, sBb['cols'], G_te), expo)
                razom = (per(pA2 / slen) + per(pB2 / slen)) / 2
                PA_sud, _ = pai(pA2 / slen, yA_t2); PA_sk, _ = pai(pA2 / slen, yB_t2)
                PR_sud, _ = pai(razom, yA_t2); PR_sk, _ = pai(razom, yB_t2)
                bere = PR_sud >= 0.95 * PA_sud and PR_sk > PA_sk
                vyb1551 = [EN[c[1]] for c in sA['cols'] if isinstance(c, tuple)]
                dvi = dict(PAI_суд_лише_А=round(PA_sud, 2), PAI_скарги_лише_А=round(PA_sk, 2),
                           PAI_суд_разом=round(PR_sud, 2), PAI_скарги_разом=round(PR_sk, 2),
                           на_карті=bere, групи=[EN[g] for g in gm], у_моделі_А_1551=vyb1551,
                           причина='' if bere else (
                               f'PAI на судових подіях упав більше ніж на 5% ({PA_sud:.2f} -> {PR_sud:.2f})'
                               if PR_sud < 0.95 * PA_sud else
                               f'PAI на скаргах не зріс ({PA_sk:.2f} -> {PR_sk:.2f})'),
                           чинники_А=factors(fA, sA['cols'], sA, k0=K0),
                           чинники_Б=factors(fBb, sBb['cols'], sBb, k0=K0))
                log(f'      PAI суд: А {PA_sud:.2f}, разом {PR_sud:.2f}; PAI скарги: А {PA_sk:.2f}, разом {PR_sk:.2f}'
                    f' -> ' + ('ранг — середнє двох мірок' if bere else 'лише судові події: ' + dvi['причина'])
                    + (f'; 1551 у моделі А: {", ".join(vyb1551)}' if vyb1551 else ''))
                if bere:
                    # карта: процентиль прогнозу А (головна модель) і Б на
                    # останніх 6 місяцях скарг
                    hBm, _a, _b = hst(SKG['map'][:, gm].sum(1), muB, sdB)
                    pBm = rtm.nb_predict(fBb, A_(hBm, sBb['cols'], G_map), expo)
                    dm = (per(dm) + per(pBm / slen)) / 2
            else:
                dvi = dict(на_карті=False, причина=f'замало: суд {int(yA_t1.sum())}, скарг {int(yB_t1.sum())} у вікні 1551')
        ok = PAI_T >= MIN_PAI
        why = '' if ok else f'PAI на довжину {PAI_T:.1f} < {MIN_PAI:g}'
        if vyd == 'тема': radiusy[nm] = {d['тип']: d['r'] for d in facs if d['r']}
        # скільки вулиць показувати: найдовший перелік із сітки, на якому
        # частка вулиць, де події справді сталися в перевірочному році, ще не
        # впала нижче PREC_MIN (зміна 7 вересня) — тепер у порядку щільності
        ot = np.argsort(-dT, kind='stable')
        prec_curve, n_show = [], TOPN
        for n_ in NGRID:
            if n_ > len(ot): break
            p_ = float((y26[ot[:n_]] > 0).mean())
            prec_curve.append([n_, round(p_, 2)])
            if n_ <= TOPN: continue
            if p_ >= PREC_MIN: n_show = n_
            else: break
        om = np.argsort(-dm, kind='stable')
        shown = om[:n_show]
        shownB = set(np.argsort(-(pmB / slen), kind='stable')[:n_show].tolist())
        ts = lambda fs: {d['тип'] for d in fs}
        facsB = factors(fB, sB['cols'], sB)
        e = dict(вид=vyd, тема=L.THEMES.get(th, th), назва=nm, ключ=key, позначка=mark,
                 вікно='історія 2024 → події 2025; перевірка: історія 2025 → події 2026',
                 вікно_карти=[MAPW[0], MAPW[-1]],
                 історія_навчання=int(y24.sum()), навчання=int(y25.sum()), перевірка=int(y26.sum()),
                 PAI_разом=round(PAI_T, 2), PAI_історія=round(PAI_H, 2), PAI_середовище=round(PAI_E, 2),
                 hit_разом=round(hT, 3), hit_історія=round(hH, 3), hit_середовище=round(hE, 3),
                 PAI_інший_район=None if PAI_G is None else round(PAI_G, 2),
                 hit_інший_район=None if hG is None else round(hG, 3),
                 PAI_як_рахувалося=star,
                 вулиць_показано=int(n_show), з_них_збулося=int((y26[ot[:n_show]] > 0).sum()),
                 відрізків=n, точність_за_довжиною=prec_curve,
                 модель='негативна біноміальна' if famT == 'NB' else 'Пуассон',
                 λ_стійкості=sT['lam'],
                 коеф_історії=round(float(fT.params[1]), 3), RR_історії=sexp(float(fT.params[1])),
                 чинники=facs, чинники_середовище=facsE,
                 стійкість=dict(чинники_2025=sorted(ts(facsB)), спільних_чинників=len(ts(facs) & ts(facsB)),
                                чинників_2024=len(ts(facs)), спільних_вулиць=len(set(shown.tolist()) & shownB),
                                вулиць=int(n_show)),
                 вилучено=vylucheno([c for c in sT['cols'] if not isinstance(c, tuple)]),
                 # 5.1: до й після поправки на людей; кратність людей
                 PAI_до_поправки=round(PAI_0, 2), чинники_до_поправки=facs0, люди=ludy,
                 події_лише_вулиця=int(n_vul[key]),
                 дві_мірки=dvi,
                 # поля, які читають карта й документи (map_layers, step6)
                 фактори=[[d['змінна'], d['коеф']] for d in facs],
                 кратність={(f"{d['тип']}_{d['r']}м" if d['r'] else d['змінна']): d['RR'] for d in facs},
                 на_карті=ok, сховано=why)
        e['метод'] = method_text(e, mark)
        report[key] = e
        rk_by[key] = set(shown.tolist())
        if ok:
            rk = dm / (dm.max() or 1)
            # місце серед усіх відрізків міста, верхні N% (7.10)
            orr = np.argsort(-dm, kind='stable'); pct_c = np.empty(n); pct_c[orr] = 100 * (np.arange(n) + 1) / n
            layers[key] = dict(kind='theme' if vyd == 'тема' else 'mech', theme=th, name=nm,
                               title='Схожі умови: ' + nm, slug=M.anchor(key), window=e['вікно'],
                               proakt=mark, hit=round(hT, 3), pai=round(PAI_T, 2), n2=1,
                               dvi_mirky=bool(dvi and dvi.get('на_карті')),
                               items=[row(i, rk, n2, street_facts(fT, sT['cols'], i, k0=K0), pct=pct_c, mu=pm)
                                      for i in shown],
                               grid=[row(i, rk, n2, None, True) for i in om[:TOPGRID]])
        # ---- точки (6) ----
        if NP_ and XP is not None:
            def cntp(months):
                v = np.zeros(NP_)
                for m in months:
                    a = YP.get((key, m))
                    if a is not None: v += a
                return v
            p24, p25, p26 = cntp(rik(2024)), cntp(rik(2025)), cntp(rik(2026))
            if p25.sum() >= 50 and p26.sum() >= 20:
                hP, muP, sdP = hst(p24); hP2, _a, _b = hst(p25, muP, sdP); hPm, _a, _b = hst(cntp(MAPW), muP, sdP)
                one = np.ones(NP_)
                AP = lambda H, cols: np.column_stack([H, XPL, XP[:, cols]] if cols else [H, XPL])
                sP = rtm.stijkist(XP[:, CANDP], p25, one, [ctypP[j] for j in CANDP], H=np.column_stack([hP, XPL]),
                                  folds=foldP, runs=max(20, rtm.N_STAB // 2), log=log)
                colsP = [CANDP[c] for c in sP['cols']]
                fP, _ = rtm.nb_fit(AP(hP, colsP), p25, one)
                PAI_P = RT.pai(rtm.nb_predict(fP, AP(hP2, colsP), one), p26)
                PAI_PH = RT.pai(p25, p26)
                pmP = rtm.nb_predict(fP, AP(hPm, colsP), one)
                e['точки'] = dict(PAI=round(PAI_P, 2), PAI_історія=round(PAI_PH, 2), подій_навчання=int(p25.sum()),
                                  на_карті=PAI_P >= RT.MIN_PAI,
                                  чинники=[cnameP[j] for j in colsP])
                log(f'   точки: PAI на верхніх 5% точок {PAI_P:.2f} (історія {PAI_PH:.2f}); '
                    + ('на карті' if PAI_P >= RT.MIN_PAI else 'СХОВАНО'))
                if PAI_P >= RT.MIN_PAI:
                    oP = np.argsort(-pmP, kind='stable'); pctP = np.empty(NP_); pctP[oP] = 100 * (np.arange(NP_) + 1) / NP_
                    n2P = cntp(ROKY2)
                    kP = min(300, max(20, NP_ // 100))
                    def facP(i):
                        rows = []
                        for k_, j in enumerate(colsP, start=1 + 1 + XPL.shape[1]):
                            c = float(fP.params[k_]) * (XP[i, j] - XP[:, j].mean())
                            if c > 0 and ctypP[j]: rows.append((c, cnameP[j]))
                        return [r for _c, r in sorted(rows, reverse=True)[:3]]
                    tochky_out[key] = dict(theme=th, name=nm, pai=round(PAI_P, 2), items=[
                        [round(TP[i]['la'], 5), round(TP[i]['lo'], 5), TP[i]['typ'], int(n2P[i]),
                         round(float(pctP[i]), 2), round(float(pmP[i]), 2), facP(i)] for i in oP[:kP]])
            else:
                e['точки'] = dict(на_карті=False, причина=f'замало подій на точках: {int(p25.sum())} у 2025')
        log(f'   PAI на довжину: разом {PAI_T:.2f}, історія {PAI_H:.2f}, середовище {PAI_E:.2f}, '
            f'захід->схід {PAI_G if PAI_G is None else round(PAI_G, 2)}; як рахувалося — разом {star["разом"]}; '
            f'чинників {len(facs)}; спільних з навчанням на 2025: {e["стійкість"]["спільних_чинників"]} чинників, '
            f'{e["стійкість"]["спільних_вулиць"]} з {n_show} вулиць; ' + ('на карті' if ok else 'СХОВАНО: ' + why))
        for d in facs[:8]:
            log(f"      RR {d['RR']:5.2f}  {d['змінна']}  ({d['частка_прогонів']:.0%})")

    # ---- «Що поруч»: один радіус на тип, той самий відбір по всіх подіях ----
    log('\n=== «Що поруч»: усі шість видів разом ===')
    ya = sum(cnt(th, rik(2025)) for th in six)
    sa = vidbir(ya, XL if XL.shape[1] else None, runs=max(20, rtm.N_STAB // 2))
    fa, _f = rtm.nb_fit(np.column_stack([XL, stovp(sa['cols'])]), ya, expo)
    shcho = {ua: 0 for ua, _q in S2B.B1.values()}      # лікарні — 0: у 50 м
    for j in sa['cols']:
        if ctyp[j]: shcho[ctyp[j]] = crad[j]
    json.dump({'blocks_m': blocks_m, 'po_vydah': radiusy, 'shcho_poruch': shcho},
              open(RADF, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    log(f'   -> data/radiusy.json: ' + ', '.join(f'{k} {v}' for k, v in shcho.items() if v))

    danger = pishokhidnyi(ev_seg, sids, names, segs, byid, ROKY3, log)
    versiia = dict(дата=time.strftime('%Y-%m-%d'), остання_подія=last,
                   вікно='історія 2024 → події 2025; перевірка: історія 2025 → події 2026',
                   вікно_карти=[MAPW[0], MAPW[-1]], відрізків=n, ліній_OSM=n_ways,
                   середня_довжина=blocks_m, прив_язка=dict(SNAPST),
                   відбір=f'стійкість: {rtm.N_STAB} прогонів elastic net на половині відрізків, '
                          f'λ — перехресна перевірка блоками за районами, поріг {rtm.STAB_POROG:.0%}; '
                          'остаточна — негативна біноміальна з довжиною як експозицією',
                   шари={k: dict(PAI=v['PAI_разом'], чинники=[d['змінна'] for d in v['чинники']])
                         for k, v in report.items() if 'PAI_разом' in v})
    json.dump({'layers': layers, 'tochky': tochky_out, 'danger': danger, 'versiia': versiia},
              open(RISK, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    rep = dict(report); rep['_версія'] = versiia
    json.dump(rep, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    write_report(report, kinds, OLD, OLDR, layers, blocks_m, shcho, n, X.shape[1],
                 factors(fa, sa['cols'], sa, k0=XL.shape[1]), versiia, danger)
    log(f'\n=== ГОТОВО за {(time.time() - t0) / 60:.0f} хв === шарів на карті: {len(layers)}; '
        f'ZVIT-KROK7.md, data/radiusy.json')


def method_text(e, mark):
    """речення для картки шару на карті. Без «причини»: шар каже, де події
    ймовірні далі за тим, що вже було, і за умовами довкола (RISHENNYA 33.2.1)."""
    n1 = f"{e['навчання']:,}".replace(',', ' ')
    n2 = f"{e['перевірка']:,}".replace(',', ' ')
    t = (f"Шар навчено на подіях 2025 року ({n1}) за історією 2024-го й умовами довкола — лише "
         f"там, де адресу названо в описі події, з точним будинком, — і перевірено на подіях "
         f"2026-го ({n2}) за історією 2025-го. На вулицях з найвищою оцінкою на метр, що разом "
         f"займають 10% довжини вулиць міста, припало {100*e['hit_разом']:.0f}% подій — у "
         f"{uatext.raziv(e['PAI_разом'])} більше, ніж навмання.")
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


# Пішохідний ризик (завдання 29, п. 6.4; METODYKA, розд. 4): не модель, а
# прозоре правило — перелік на аудит. ДТП з потерпілими в судових даних майже
# немає, тож безпеку пішоходів напряму не виміряти; беремо відрізки з
# найбільшим модельованим потоком, де вже були ДТП з ознаками конфлікту.
KONFLIKT = re.compile(r"припаркован|паркуван|об['’]?їзд|боков\w*\s+інтервал|задн\w*\s+ход|пішох[іо]д", re.I)
# Один перелік — за прохідністю (RISHENNYA 34.1; ZAVDANNYA-31, 5.5)
POTOKY = (('прохідність', 0),)


def pishokhidnyi(ev_seg, sids, names, segs, byid, ROKY3, log):
    """{потік: [відрізки у верхніх 5% за потоком, де за 3 роки ≥3 ДТП з
    ознаками конфлікту у фабулі або втечі з місця ДТП]}"""
    if not byid:
        log('   пішохідний ризик: потоків немає (network.json) — перелік порожній')
        return {}
    r3 = set(ROKY3)
    kf = collections.Counter(); vt = collections.Counter()
    for i, e in ev_seg:
        if e['th'] != 'ДТП' or e['m'] not in r3: continue
        if e['sim'] == 'ДОР_залишення_місця': kf[i] += 1; vt[i] += 1
        elif KONFLIKT.search(e['fab'] or ''): kf[i] += 1
    out = {}
    for nm_, j in POTOKY:
        v = [(byid.get(s, 0), i) for i, s in enumerate(sids)]
        vals = sorted(x for x, _i in v if x > 0)
        if not vals: continue
        por = vals[int(len(vals) * 0.95)]
        lst = [dict(вулиця=names[sids[i]] or 'без назви', відрізок=sids[i], потік=int(x),
                    дтп=kf[i], з_них_втеча=vt[i], p=list(segs[sids[i]][len(segs[sids[i]]) // 2]))
               for x, i in v if x >= por and kf[i] >= 3]
        out[nm_] = sorted(lst, key=lambda d: (-d['дтп'], -d['потік']))
        log(f'   пішохідний ризик, {nm_}: {len(lst)} відрізків (верхні 5% потоку ≥ {int(por)}, ≥3 ДТП за 3 роки)')
    return out


def sp(n):
    """12345 -> '12 345'; нечислове — як є"""
    return f'{n:,}'.replace(',', ' ') if isinstance(n, int) else n


def inf(x): return '∞' if x is not None and x >= 1e5 else x


def pct(x): return '—' if x is None else f'{100*x:.0f}%'


def write_report(report, kinds, OLD, OLDR, layers, blocks_m, shcho, nseg, ncand, fa, versiia, danger):
    """ZVIT-KROK7.md — версія моделі (ZAVDANNYA-30, 3.6): дата, вікно,
    чинники, PAI і порівняння з попередньою версією."""
    f = open(TXT, 'w', encoding='utf-8', newline='\n')
    w = f.write
    w('# Звіт кроку 7: модель ризику «разом» — історія подій + середовище\n\n')
    w(f'Складено двигуном (`src/step4_engine.py`, `src/rtm.py`) {time.strftime("%d.%m.%Y")}. '
      'Рішення — RISHENNYA 33.2.1; методика — `METODYKA.md`, розд. 4; перелік типів і радіусів — '
      '`NAUKA.md`, «Перелік чинників для Б1» (не змінювався).\n\n')
    w('## Версія\n\n')
    w(f"- Дата: {versiia['дата']}; остання подія в даних: {versiia['остання_подія']}.\n"
      f"- Вікно: {versiia['вікно']}; історія для карти — {versiia['вікно_карти'][0]} — {versiia['вікно_карти'][1]} "
      '(12 повних місяців, що закінчуються за 2 місяці до останньої дати).\n'
      f"- Одиниця: відрізок вулиці між перехрестями — {sp(nseg)} шт. (ліній OSM ≥40 м — {sp(versiia['ліній_OSM'])}), "
      f'середня довжина {blocks_m} м.\n'
      f"- Відбір: {versiia['відбір']}. Змінних-кандидатів {ncand}: кожен тип «є в межах r» і «скільки в "
      'межах r» на 50–500 м, пішохідні потоки, населення, будова вулиці; історія '
      '`log(1 + подій попередніх 12 місяців)` не штрафується.\n'
      '- Прив\'язка подій: ' + ', '.join(f'{k} {sp(v)}' for k, v in versiia['прив_язка'].items()) + '.\n\n')
    w('> **PAI на довжину** — частка подій перевірки на вулицях з найвищою оцінкою на метр, що разом '
      'займають 10% довжини вулиць, ÷ 0,10 (навмання — 1). «Як рахувалося» — стара міра: верхні 10% '
      'відрізків за оцінкою без поділу на довжину. На карту йде модель «разом», якщо PAI ≥ 3.\n\n')

    w('## 1. Види, механізми й події\n\n')
    w('| Вид / механізм | Позначка | Клас B, точний будинок | На вулицях | Історія 2024 | Навчання 2025 | Перевірка 2026 |\n')
    w('|---|---|---|---|---|---|---|\n')
    for k, kd in kinds.items():
        e = report.get(k, {})
        w(f"| {kd['назва']}{' (механізм)' if kd['вид'] == 'механізм' else ''} | {kd['позначка'] or '—'} "
          f"| {sp(kd['подій'])} | {sp(kd['на_вулицях'])} | {sp(e.get('історія_навчання', '—'))} "
          f"| {sp(e.get('навчання', 0))} | {sp(e.get('перевірка', '—'))} |\n")

    w('\n## 2. Перевірка: PAI на довжину\n\n')
    w('| Вид / механізм | На карті | Разом | Історія | Середовище | Захід → схід | Як рахувалося (разом / історія / середовище) '
      '| Попередня версія | Вулиць показано | Збулося |\n|---|---|---|---|---|---|---|---|---|---|\n')
    for k, e in report.items():
        o = OLD.get(k, {}) if isinstance(OLD.get(k), dict) else {}
        old = o.get('PAI_разом_довжина') or o.get('PAI_середовище', '—')
        if 'PAI_разом' not in e:
            w(f"| {e['назва']} | ні — {e['сховано']} | — | — | — | — | — | {old} | — | — |\n"); continue
        s = e['PAI_як_рахувалося']
        w(f"| {e['назва']} | {'так' if e['на_карті'] else 'ні — ' + e['сховано']} | **{e['PAI_разом']}** "
          f"| {e['PAI_історія']} | {e['PAI_середовище']} | {e['PAI_інший_район'] if e['PAI_інший_район'] is not None else '—'} "
          f"| {s['разом']} / {s['історія']} / {s['середовище']} | {old} "
          f"| {e['вулиць_показано']} | {e['з_них_збулося']} |\n")
    w('\n«Попередня версія» — PAI з попереднього `engine_report.json` (там — модель лише середовища і стара '
      'міра на лініях OSM), тож порівняння — для чесності, не умова.\n\n')

    w('## 3. Стійкість між роками\n\n')
    w('Та сама модель, навчена на 2025 → 2026: скільки стійких чинників спільні з навченою на 2024 → 2025 і '
      'скільки вулиць спільні серед показаних (прогноз на карту — на тій самій історії останніх 12 місяців).\n\n')
    w('| Вид / механізм | Чинників (2024) | Спільних | Вулиць показано | Спільних вулиць |\n|---|---|---|---|---|\n')
    for k, e in report.items():
        s = e.get('стійкість')
        if not s: continue
        w(f"| {e['назва']} | {s['чинників_2024']} | {s['спільних_чинників']} | {s['вулиць']} "
          f"| {s['спільних_вулиць']} ({pct(s['спільних_вулиць'] / max(s['вулиць'], 1))}) |\n")

    w('\n## 4. Стійкі чинники\n\n')
    w('Кратність (RR) — у скільки разів більше подій: для «є» — там, де об\'єкт є в колі, проти решти; для '
      '«скільки» — на кожен ще один об\'єкт; для величин — на одне стандартне відхилення. У дужках 95% '
      'інтервал. «Прогонів» — частка з 100 прогонів відбору стійкості, де тип обрано.\n\n')
    for k, e in report.items():
        if 'чинники' not in e: continue
        w(f"### {e['назва']}" + (f" · {e['позначка']}" if e.get('позначка') else '') + '\n\n')
        w(f"Модель: {e['модель']}; історія подій — RR {e['RR_історії']} на одне стандартне відхилення "
          f"`log(1 + подій)`.\n\n")
        if e['чинники']:
            w('| Чинник | Форма | Радіус | RR | 95% | Прогонів | Джерело |\n|---|---|---|---|---|---|---|\n')
            for d in e['чинники']:
                w(f"| {d['тип'].replace('_', ' ')} | {d['форма']} | {str(d['r']) + ' м' if d['r'] else '—'} "
                  f"| **{d['RR']}** | {inf(d['RR_від'])}–{inf(d['RR_до'])} | {pct(d['частка_прогонів'])} | {d['джерело']} |\n")
        else:
            w('Жоден чинник середовища не пройшов поріг стійкості — оцінку дає історія подій.\n')
        es = e.get('чинники_середовище') or []
        w('\nМодель лише середовища (для порівняння): '
          + (', '.join(f"{d['тип'].replace('_', ' ')} {d['RR']}" for d in es) or 'жодного стійкого чинника') + '.\n')
        vy = e.get('вилучено') or []
        if vy:
            w('\nПотоки й будова вулиці, яких відбір не взяв: ' + '; '.join(
                f"{d['змінна'].replace('_', ' ')} — " + (f"вилучено: сильно пов'язаний з {d['пов_язана_з'].replace('_', ' ')} (r = {d['r']})"
                                                      if d['пов_язана_з'] else 'не пройшов поріг стійкості')
                for d in vy) + '.\n')
        w('\n')

    w('## 5. Зміни від попередньої версії\n\n')
    for k, e in report.items():
        if 'чинники' not in e: continue
        o = OLD.get(k, {}) if isinstance(OLD.get(k), dict) else {}
        ot = {d.get('тип') for d in o.get('чинники', []) if isinstance(d, dict)}
        nt = {d['тип'] for d in e['чинники']}
        old_items = {x[1] for x in OLDR.get('layers', {}).get(k, {}).get('items', []) if x[1]}
        new_items = {x[1] for x in layers.get(k, {}).get('items', []) if x[1]}
        w(f"**{e['назва']}.** Чинники зайшли: {', '.join(sorted(nt - ot)) or '—'}; вийшли: "
          f"{', '.join(sorted(ot - nt)) or '—'}. Вулиць (за назвою) серед показаних: спільних "
          f"{len(old_items & new_items)} з {len(new_items)} нових і {len(old_items)} попередніх.\n\n")

    w('## 6. Пішохідний ризик — перелік на аудит\n\n')
    w('Не модель, а правило: відрізки у верхніх 5% модельованого потоку, де за 3 роки ≥3 ДТП класу B з '
      'ознакою конфлікту у фабулі (припаркований, об\'їзд, боковий інтервал, заднім ходом, пішохід) або '
      'втечею з місця ДТП.\n\n')
    for nm_, lst in (danger or {}).items():
        w(f"**{nm_}** — {len(lst)}: " + ('; '.join(f"{d['вулиця']} ({d['дтп']} ДТП, потік {d['потік']})"
                                                 for d in lst[:15]) or '—') + '.\n\n')

    w('## 7. Радіуси «Що поруч»\n\n')
    w('Той самий відбір стійкості на всіх шести видах разом (події 2025, лише середовище). 0 — тип не пов\'язаний '
      'з подіями; кнопка «Що поруч» показує його в найменшому колі.\n\n| Тип | Радіус | RR | Джерело |\n|---|---|---|---|\n')
    rr = {d['тип']: d for d in fa if d['r']}
    for ua, r in shcho.items():
        d = rr.get(ua)
        w(f"| {ua.replace('_', ' ')} | {str(r) + ' м' if r else '0'} | {d['RR'] if d else '—'} "
          f"| {SOURCES.get(ua, '')} |\n")
    f.close()


if __name__ == '__main__':
    main()
