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
import os, sys, re, glob, json, math, gzip, csv, collections, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import labels as L
import mech as M
import podii as PD
import vidrizky as VR

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
REPORT = os.path.join(DATA, 'problems_report.json')
D1551 = os.path.join(DATA, '1551')

PRAVYLA = 'В1 з поправками 29–30.09.2026 (METODYKA, розд. 2–3; RISHENNYA, розд. 32–33)'
R_MISCE = 30          # м: адреси з тим самим механізмом ближче — одне місце
# Р3 (RISHENNYA 32, затверджено 29.09): 5–6 подій за 3 роки — збіг, а не
# проблема. ≥12 подій за останні 2 роки — у середньому раз на два місяці — і
# ≥5 різних кварталів з 8.
MIN_POD = 12          # Р3: окремих подій за останні KV_VIKNO кварталів
MIN_KV = 5            # Р3: різних кварталів з останніх 8
KV_VIKNO = 8
# Ділянка (завдання 29, п. 4): точки-проблеми одного механізму на тій самій
# вулиці ближче R_DILIANKA — одна проблема; ланцюжком, але не довша за
# DILIANKA_MAX. 30 м склеювання для Хрещатика, 19 / 21 / 23 / 36 замало.
R_DILIANKA = 250
DILIANKA_MAX = 500
# «Проблема, яку фіксує поліція» (RISHENNYA 32): проактивне скупчення з тим
# самим порогом Р3 і Р8. Наркотики й сп'яніння за кермом — ні: там
# скупчення — місця роботи патрулів, а не безлад.
NE_FIKSUIE = {'НАР', 'ДОР'}   # ДОР — «Порушення на дорозі» (ZAVDANNYA-31, 4.4)
NE_FIKSUIE_SIM = {"ДОР_сп'яніння"}
# Місце без мешканців (завдання 30, ч. 2): голосу мешканців там немає кому
# подати, і «мовчать» було б неправдою.
R_MESHK = 50
SVIZHIST_DNIV = 365   # Р3: остання подія не старша за рік
ZATRYMKA_DNIV = 50    # Р3: медіанна затримка рішення від події (тест 22.09)
ZAYAVNI_MIN = 0.5     # Р2
SNAP_M = 120          # як у step4_engine: подія -> відрізок вулиці
KAT = set(L.ORDER)   # сім видів (34.3, 35.8)

# 1551: вид звернень -> вид карти; для решти видів 1551 мовчить (розд. 5.1)
# дорожні скарги (переходи, світлофори, тротуари) — про безпеку людей, тобто ДТП
VYD1551 = {'1_PUBLIC_ORDER': 'ГП', '2_ALCOHOL_TRADE': 'АЛК', '6_TRAFFIC': 'ДТП'}
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
# «Бари» — окремо від «рекреації»: посібник POP #1 «Assaults in and Around
# Bars» написано про бари й клуби, а рекреація — це й кожне кафе. Інакше
# Майдан Незалежності, 1 отримував посібник про бари за кав'ярнями поруч.
SERED_BARY = {'b1_bars', 'bar_on'}
# Ключових слів фабули як запасного джерела середовища більше немає
# (завдання 30, ч. 2): слово «кафе» в описі — не об'єкт у 50 м.
#
# Тип місця з фабул (ZAVDANNYA-31, 7.2) — інше: не одне слово, а те, що
# називає щонайменше третина фабул пари («у приміщенні ТРЦ», «у підземному
# переході»). Суд описує саме місце події, тож це надійніше за OSM у 50 м:
# Майдан, 1 — підземний перехід, а не «бари поруч». Хто керує — лише
# загальною назвою ролі, без вигаданих установ (CLAUDE.md).
# (тип місця, шаблон у фабулі, середовище для посібника, хто керує)
FAB_MISCE = [
    ('ТЦ', r'\bтрц\b|\bтц\b|торг(?:ов|івел)\w*[\s-]+(?:розважальн\w*\s+)?(?:центр|комплекс)', 'торгівля', 'адміністрація ТЦ'),
    ('підземний перехід', r'підземн\w*\s+(?:пішохідн\w*\s+)?перех', 'транспорт', 'балансоутримувач переходу'),
    ('вокзал', r'вокзал', 'транспорт', 'Укрзалізниця'),
    ('ринок', r'\bринк|\bринок', 'торгівля', 'адміністрація ринку'),
    ('паркінг', r'паркінг|автостоянк|парковк|паркувальн|стоянц', 'паркінг', 'власник паркінгу'),
    ('АЗС', r'\bазс\b|автозаправ', 'торгівля', 'власник АЗС'),
    ('парк', r'\bпарк[уі]?\b|\bсквер', 'рекреація', 'балансоутримувач парку'),
]
FAB_MISCE = [(n, re.compile(p, re.I), s, k) for n, p, s, k in FAB_MISCE]
FAB_CHASTKA = 1 / 3


def misce_z_fabul(evs):
    """(тип, середовище, хто керує, скільки фабул) — якщо тип місця називає
    щонайменше третина фабул пари; інакше None."""
    fabs = [e.get('fab') or '' for e in evs]
    if not fabs: return None
    best = max(((sum(1 for f in fabs if rx.search(f)), n, s, k) for n, rx, s, k in FAB_MISCE), key=lambda x: x[0])
    if best[0] and best[0] >= FAB_CHASTKA * len(fabs):
        return dict(mistse=best[1], ser=best[2], keruye=best[3], fabul=best[0], z=len(fabs))
    return None


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


_SEG = {}
def vidrizky_misto():
    """відрізки між перехрестями і пошук по них — один раз на запуск:
    карта кличе run() для кожного району"""
    if 'seg' not in _SEG:
        rawp = os.path.join(DATA, 'osm_risks_raw.json')
        seg = VR.build(VR.vulytsi(json.load(open(rawp, encoding='utf-8')))) if os.path.exists(rawp) else {}
        _SEG['seg'] = seg
        _SEG['pv'] = VR.Pryviazka(seg) if seg else None
    return _SEG['seg'], _SEG['pv']


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


# ---- «НАТОВП» (RISHENNYA 34.1; ZAVDANNYA-31, 5.4) ----
# Скільки подій механізму дає саме кількість людей: Пуассонова регресія по
# ВСІХ відрізках міста — події за 2 роки ~ log(1 + прохідність) + log(1 +
# населення в 300 м), довжина відрізка — експозиція. Очікуване для місця —
# μ його відрізка. Подій більше, ніж дає натовп, — якщо P(X ≥ n | μ) < 0,05.
# Нікого не відсіюємо — лише кажемо (відсіювати чи ні — після чисел у звіті).
P_NATOVP = 0.05


class Natovp:
    def __init__(s, ev, log=print):
        import numpy as np
        s.ok = False
        SEG, pv = vidrizky_misto()
        if not pv:
            log('   натовп: відрізків немає — не рахується'); return
        sids = sorted(SEG); ix = {k: i for i, k in enumerate(sids)}
        npth = os.path.join(DATA, 'network.json')
        pot = VR.potik(json.load(open(npth, encoding='utf-8')).get('items', [])) if os.path.exists(npth) else {}
        if not pot:
            log('   натовп: прохідності немає (network.json) — не рахується'); return
        mid = [SEG[k]['pts'][len(SEG[k]['pts']) // 2] for k in sids]
        import step2c_network as S2C
        rawp = os.path.join(DATA, 'osm_risks_raw.json')
        hs = S2C.budynky(json.load(open(rawp, encoding='utf-8')), log=lambda *a: None) if os.path.exists(rawp) else []
        pop = np.zeros(len(sids))
        if hs:
            ppl = S2C.naselennia(hs, log=lambda *a: None)
            g = Pts([(h[0], h[1]) for h in hs])
            pop = np.array([sum(ppl[k] for k in g.near(m[0], m[1], 300)) for m in mid])
        L = np.maximum(np.array([SEG[k]['len'] for k in sids]), 20.0)
        s.X = np.column_stack([np.ones(len(sids)), np.log1p([pot.get(k, 0) for k in sids]), np.log1p(pop)])
        s.off = np.log(L / L.mean())
        cnt = collections.defaultdict(lambda: np.zeros(len(sids)))
        s.seg_of = {}
        # ті самі 2 роки, що й у воротах Р3
        lo = (dt.date.fromisoformat(max(e['date'] for e in ev)) - dt.timedelta(days=730)).isoformat()
        for e in ev:
            if e['date'] < lo: continue
            k = e['p']
            if k not in s.seg_of:
                b = pv.blyzki(k[0], k[1], SNAP_M)
                s.seg_of[k] = ix[min(b, key=b.get)] if b else None
            if s.seg_of[k] is not None: cnt[e['sim']][s.seg_of[k]] += 1
        s.cnt, s.pv, s.ix, s.np = cnt, pv, ix, np
        s.beta = {}
        s.ok = True
        log(f'   натовп: {len(sids):,} відрізків, прохідність на {sum(1 for k in sids if pot.get(k)):,}, '
            f'населення з {len(hs):,} будинків')

    def _fit(s, sim):
        np = s.np
        if sim in s.beta: return s.beta[sim]
        y = s.cnt.get(sim)
        if y is None or y.sum() < 30: s.beta[sim] = None; return None
        b = np.zeros(3); b[0] = np.log(y.sum() / np.exp(s.off).sum())
        for _ in range(50):           # IRLS Пуассона: три параметри, без бібліотек
            mu = np.exp(np.clip(s.X @ b + s.off, -30, 30))
            W = mu; z = s.X @ b + (y - mu) / np.maximum(mu, 1e-9)
            A = s.X.T @ (s.X * W[:, None]) + 1e-6 * np.eye(3)
            nb = np.linalg.solve(A, s.X.T @ (W * z))
            if np.abs(nb - b).max() < 1e-7: b = nb; break
            b = nb
        s.beta[sim] = b
        return b

    def __call__(s, sim, pts, n):
        """(очікувано за 2 роки, 'стільки, скільки дає натовп' | 'більше, ніж
        дає натовп') або None"""
        if not s.ok: return None
        b = s._fit(sim)
        if b is None: return None
        ii = {s.seg_of.get(tuple(p)) for p in pts} - {None}
        if not ii: return None
        mu = float(sum(s.np.exp(s.X[i] @ b + s.off[i]) for i in ii))
        p = pois_sf(n, mu)
        return round(mu, 1), ('більше, ніж дає натовп' if p < P_NATOVP else 'стільки, скільки дає натовп')


def skargy_hrupy(log=print):
    """[(місяць 'РРРР-ММ', група за змістом, (lat, lon))] — скарги 1551 груп
    zbir_1551.GRUPY_1551 з точкою (ZAVDANNYA-32, 5.2). Старі файли без
    стовпця grupa — група за змістом тут-таки."""
    import zbir_1551 as Z
    fv = sorted(glob.glob(os.path.join(D1551, 'vidbir-*.tsv.gz')))
    if not fv:
        log('   1551 за змістом: даних немає (data/1551)')
        return []
    idx, skey, nh = geokoder()
    out, st = [], collections.Counter()
    for f in fv:
        with gzip.open(f, 'rt', encoding='utf-8', newline='') as fh:
            for r in csv.DictReader(fh, delimiter='\t'):
                g = r.get('grupa') or Z.grupa(r.get('kind'), r.get('content'))
                if not g: continue
                s_, h = r.get('vulytsya'), r.get('budynok')
                p = None
                if s_ and h and idx:
                    main_ = str(s_).split('(')[0]
                    p = idx.get((skey(main_), nh(str(h))))
                st[(g, bool(p))] += 1
                if p: out.append((r['data'][:7], g, p))
    log('   1551 за змістом (з точкою / усього): ' + ', '.join(
        f'{g} {st[(g, True)]:,}/{st[(g, True)] + st[(g, False)]:,}' for g in Z.GRUPY_1551))
    return out


def golos_misce(G, th, pts, dmap, rad=R_MISCE, bez_meshk=None):
    """Голос мешканців для місця (одна чи кілька точок): скарги того ж виду
    за 12 місяців у rad м проти очікуваного — частка виду серед усіх звернень
    району × усі звернення місця. p < 0,05 — «підтверджують».
    bez_meshk — чому тут немає мешканців (вокзал, ТЦ, площа, парк, жодного
    житлового будинку в 50 м); тоді «не вимірюється», а не «мовчать»."""
    if th in NE_VYMIR: return dict(stan='не вимірюється', chomu='вид')
    if bez_meshk: return dict(stan='не вимірюється', chomu=bez_meshk)
    if G is None: return dict(stan='немає даних')
    if th not in VYD1551.values(): return dict(stan='не вимірюється', chomu='вид')
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
        # точне місце — будинок або перехрестя (RISHENNYA 33.2.3)
        if th not in KAT or r[9] not in ('house', 'cross'): continue
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


def mozhe_fiksuvaty(sim):
    """чи може проактивне скупчення цього механізму мати статус «проблема,
    яку фіксує поліція» (RISHENNYA 32)"""
    return M.simtheme(sim) not in NE_FIKSUIE and sim not in NE_FIKSUIE_SIM


def vorota(evs, S, kind_q, sim=''):
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
    # Р3 рахується на останніх 8 кварталах (2 роки): давні події не мають
    # робити проблемою місце, де зараз тихо
    u8 = [e for e in u if kv(e['date']) > kind_q - KV_VIKNO]
    qs = {kv(e['date']) for e in u8}
    last = max(e['date'] for e in u)
    g['R3_podii'] = len(u8) >= MIN_POD
    g['R3_kvartaly'] = len(qs) >= MIN_KV
    g['R3_svizhist'] = (dt.date.fromisoformat(S) - dt.date.fromisoformat(last)).days <= SVIZHIST_DNIV
    r3 = g['R3_podii'] and g['R3_svizhist'] and g['R3_kvartaly']
    if not g['R2']: st = 'фіксує поліція' if (r3 and mozhe_fiksuvaty(sim)) else 'проактивна'
    elif not g['R3_podii']: st = 'мало'
    elif not g['R3_svizhist']: st = 'згасла'
    elif not g['R3_kvartaly']: st = 'гостра'
    else: st = 'хронічна'
    lo4 = kind_q - 4
    kk = sum(1 for e in u if 'КК' in (L.CODE.get(e['cat']) or ('', ''))[1])
    return g, st, dict(podii=len(u), za_2roky=len(u8), zayavnykh=round(zay, 2), ostannia=last,
                       kvartaly=sorted(kv_name(q) for q in qs),
                       za_4kv=sum(1 for e in u if kv(e['date']) > lo4),
                       otsinnykh=sum(e['otsinna'] for e in u),
                       # Шкода — поле, не сортує (Р6): частка кримінальних
                       # проступків, поки ваги шкоди не перевірені юристом
                       shkoda_kk=round(kk / len(u), 2), evs=u)


PROBLEMA = ('хронічна', 'фіксує поліція')       # статуси, що йдуть у перелік


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
def seredovyshche(evs, FACT):
    """Тип місця (Р5; завдання 29, п. 5, і завдання 30, ч. 2 — на всіх
    рівнях): середовище береться, лише якщо об'єкт цього типу за OSM стоїть
    у 50 м від БІЛЬШОСТІ подій місця. Раніше досить було об'єкта біля однієї
    з трьох адрес чи слова у фабулі — і лінія Лятошинського з 6 хуліганствами
    на 6 адресах отримувала посібник про бари. Немає такого об'єкта —
    «невизначено» і без посібника."""
    env = []
    pts = [e['p'] for e in evs]
    for c in (FACT or {}).get('cats', []):
        s = SERED.get(c.get('k'))
        if not s or not c['pts']: continue
        tt = [s] + (['бари'] if c.get('k') in SERED_BARY else [])
        if all(t in env for t in tt): continue
        g = _FGRID.get(id(c)) or _FGRID.setdefault(id(c), Pts([tuple(q) for q in c['pts']]))
        if pts and sum(1 for p in pts if g.near(p[0], p[1], R_SERED)) * 2 > len(pts):
            env += [t for t in tt if t not in env]
    return env, ('OSM' if env else '')


class BezMeshk:
    """Чому в місці немає мешканців, яких могла б почути 1551 (завдання 30,
    ч. 2): вокзал, ТЦ, площа, парк — або жодного житлового будинку OSM
    (apartments, residential, house, dormitory) у 50 м. Будинків у кеші OSM
    немає — ця ознака не рахується, лишаються вокзал, ТЦ, площа й парк."""
    def __init__(s, log=print):
        rawp = os.path.join(DATA, 'osm_risks_raw.json')
        raw = json.load(open(rawp, encoding='utf-8')) if os.path.exists(rawp) else {}
        def pts(items, ok=lambda t: True):
            out = []
            for el in items or []:
                t = el.get('tags') or {}
                la = el.get('lat') or (el.get('center') or {}).get('lat')
                lo = el.get('lon') or (el.get('center') or {}).get('lon')
                b = el.get('bounds')
                if not la and b:      # будинки зі знімка — лише рамка
                    la, lo = (b['minlat'] + b['maxlat']) / 2, (b['minlon'] + b['maxlon']) / 2
                if la and lo and ok(t): out.append((la, lo))
            return Pts(out) if out else None
        s.houses = pts(raw.get('houses'))
        # вокзал — залізнична станція, не станція метро: над метро на
        # Хрещатику живуть люди
        s.vokzal = pts(raw.get('b1_metro'), lambda t: t.get('railway') == 'station'
                       and t.get('station') != 'subway' and 'subway' not in (t.get('subway') or ''))
        s.tc = pts(raw.get('b1_mall'))
        s.park = pts(raw.get('park'))
        if s.houses is None:
            log('   УВАГА: житлових будинків OSM (houses) у кеші немає — «не вимірюється» ставиться лише за '
                'типом місця (вокзал, ТЦ, площа, парк), ознака «жодного житла в 50 м» не рахується; '
                'повне перезавантаження OSM — лише галочкою')
        else:
            log(f'   місця без мешканців: житлових будинків OSM {len(s.houses.p):,}')
        if s.park is None: log('   парків OSM (park) у кеші немає — ознака «парк» не рахується')

    def __call__(s, pts, adresy):
        near = lambda g: g is not None and any(g.near(p[0], p[1], R_MESHK) for p in pts)
        a = ' '.join(adresy[:3]).lower()
        if near(s.vokzal) or 'вокзал' in a: return 'вокзал'
        if a.startswith('пл.') or a.startswith('майдан'): return 'площа'
        # ТЦ чи парк у 50 м не роблять місце безлюдним, якщо поруч житло:
        # Велика Васильківська, 72 — житловий будинок біля ТЦ, мешканці там
        # скаржаться (ZAVDANNYA-31, 7.3). Без будинків у кеші — як раніше.
        if s.houses is not None and near(s.houses): return None
        if near(s.tc): return 'ТЦ'
        if near(s.park): return 'парк'
        if s.houses is not None: return 'житла в 50 м немає'
        return None


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
        if r['status'] in PROBLEMA and r['riven'] == 'точка':
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
        inwin = q >= 0
        # місця реальних проблем і скільки там подій за 2 роки (Р3 рахує їх)
        tgt = [(r, pmap.get(min(pts, key=lambda p: dist(p, r['p'])) if tuple(r['p']) not in pmap
                        else tuple(r['p'])), r['za_2roky']) for r in real.get(sim, [])]
        ge = np.zeros(len(tgt)); npass = []
        for _ in range(N_PEREST):
            a = rng.choice(nP, size=len(es), p=w)
            cnt = np.bincount(a[inwin], minlength=nP)
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
    rk = os.path.join(DATA, 'risk.json')
    if G is None or not os.path.exists(rk): return None
    import step4_engine as E4
    layers = json.load(open(rk, encoding='utf-8')).get('layers', {})
    # пул випадкових — ті самі відрізки між перехрестями, що й у моделі
    segs = [v['pts'] for v in vidrizky_misto()[0].values()]
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

    BM = BezMeshk(log)
    NT = Natovp(ev, log)

    # ---- рівень «точка» ----
    place = mistsia(ev)
    pary = collections.defaultdict(list)
    for i, e in enumerate(ev): pary[place[i]].append(e)
    funnel = {'точка': collections.Counter(), 'лінія': collections.Counter(),
              'дорожні ділянки': collections.Counter()}
    zapysy, formue, is_problem_ev = [], [], set()
    GATES = (('R1', 'Р1 клас B'), ('R2', 'Р2 заявні ≥50%'), ('R3_podii', f'Р3 ≥{MIN_POD} подій за 2 роки'),
             ('R3_svizhist', 'Р3 остання ≤12 міс.'), ('R3_kvartaly', f'Р3 ≥{MIN_KV} кварталів з 8'))
    POLICE = 'пройшли Р3 як проактивні: «фіксує поліція»'

    def zbir(sim, evs, riven, pts, rep):
        """запис місця × механізму з підсумками воріт — без воронки"""
        th = M.simtheme(sim)
        g, st, s = vorota(evs, S, kind_q, sim)
        u = s.pop('evs', [])
        addrs = collections.Counter(e['adr'] for e in u)
        rec = dict(riven=riven, sim=sim, vyd=th, mekhanizm=M.simname(sim), status=st, vorota=g,
                   p=list(rep), adresy=[a for a, _ in addrs.most_common()],
                   adresy_n=addrs.most_common(), klas='B', **s)
        if u:
            # doc_id подій, що їх порахували ворота, — картка на карті показує
            # саме їх, з усіх адрес місця (завдання 29, п. 2)
            rec['docs'] = [e['doc'] for e in u]
            rec['statti'] = collections.Counter(e['cat'] for e in u).most_common()
            rec['roky'] = sorted({e['date'][:4] for e in u})
        if u and g.get('R3_podii'):
            mf = misce_z_fabul(u)
            if mf:
                rec['typ'] = M.problem_type(sim, [mf['ser']])
                rec['typ'].update(mistse=mf['mistse'], keruye=mf['keruye'],
                                  dzherelo_seredovyshcha=f"у {mf['fabul']} з {mf['z']} фабул")
            else:
                env, dz = seredovyshche(u, FACT)
                rec['typ'] = M.problem_type(sim, env)
                rec['typ']['dzherelo_seredovyshcha'] = dz or 'невизначено'
            rec['proaktyvnykh'] = round(1 - s['zayavnykh'], 2)
            rec['golos'] = golos_misce(G, th, pts, dmap, bez_meshk=BM(pts, rec['adresy']))
            rec['raion'] = dmap(tuple(rep))
            nt = NT(sim, pts, len(u))
            if nt: rec['natovp'] = dict(ochikuvano=nt[0], stan=nt[1])
        return rec, u

    def zapys(key, evs, riven, pts):
        sim, _t, rep = key
        th = M.simtheme(sim)
        dor = sim == 'ДОР_ДТП'                    # Р4: окремий клас
        track = 'дорожні ділянки' if dor else riven
        rec, u = zbir(sim, evs, track, pts, rep)
        g, st = rec['vorota'], rec['status']
        f = funnel[track]; f['пар на вході'] += 1
        for gk, lab in GATES:
            if gk not in g: break
            if not g[gk]:
                f['відпало: ' + lab] += 1; break
        else:
            f['пройшли'] += 1
        if st == 'фіксує поліція': f[POLICE] += 1
        if u:
            if st in PROBLEMA:
                is_problem_ev.update(id(e) for e in evs)
            elif not dor:
                ok, fz = formuietsia(u, kind_q)
                if ok:
                    formue.append(dict(riven=track, sim=sim, vyd=th, p=list(rep), adresy=rec['adresy'],
                                       dzherelo='ЄДРСР', prymitka='судові дані запізнюються', **fz,
                                       golos=rec.get('golos') or golos_misce(
                                           G, th, pts, dmap, bez_meshk=BM(pts, rec['adresy']))))
        zapysy.append(rec)
        return rec

    def vidpalo_r8(r, rivn, evs=()):
        f = funnel[rivn]
        if r['status'] == 'хронічна': f['пройшли'] -= 1
        else: f[POLICE] -= 1
        f['відпало: Р8 не густіше за випадок'] += 1
        r['status'] = 'випадкова'
        # події «випадкового» місця знову можуть скласти лінію
        is_problem_ev.difference_update(id(e) for e in evs)

    pary_ev = {}
    for key, evs in pary.items():
        pts = sorted({e['p'] for e in evs}, key=lambda p: -sum(1 for e in evs if e['p'] == p))
        pary_ev[id(zapys((key[0], 'т', pts[0]), evs, 'точка', pts))] = evs

    # ---- Р8: ворота 6 — перевищення над випадковим рівнем ----
    r8 = nulovyi_riven(ev, S, kind_q, zapysy, log)
    for r in zapysy:
        if r['status'] in PROBLEMA and r['riven'] == 'точка' and r['vorota'].get('R8') is False:
            vidpalo_r8(r, 'точка', pary_ev.get(id(r), ()))

    # ---- рівень «ділянка» (завдання 29, п. 4) ----
    # Точки-проблеми одного механізму й статусу на тій самій вулиці ближче
    # 250 м — ланцюжком, доки вся ділянка вкладається в 500 м, — одна
    # проблема з переліком адрес і числом по кожній.
    dilianok = 0
    grp = collections.defaultdict(list)
    for r in zapysy:
        if r['riven'] == 'точка' and r['status'] in PROBLEMA:
            grp[(r['sim'], r['status'])].append(r)
    for (sim, st), rs in grp.items():
        left = sorted(rs, key=lambda r: -r['za_2roky'])
        while left:
            c = [left.pop(0)]
            ws = VR.slova((VR.vulytsia(c[0]['adresy'][0]) or [''])[0])
            grew = True
            while grew:
                grew = False
                for r in list(left):
                    wr = VR.slova((VR.vulytsia(r['adresy'][0]) or [''])[0])
                    if not VR.ta_sama(ws, wr): continue
                    ds = [dist(r['p'], x['p']) for x in c]
                    if min(ds) >= R_DILIANKA or max(ds) > DILIANKA_MAX: continue
                    c.append(r); left.remove(r); grew = True
            if len(c) < 2: continue
            evs = [e for x in c for e in pary_ev.get(id(x), ())]
            pts = [tuple(x['p']) for x in c]
            rec, _u = zbir(sim, evs, 'ділянка', pts, c[0]['p'])
            rec['status'] = st
            rec['vorota']['R8'] = True
            rec['chastyny'] = [dict(p=x['p'], adresy=x['adresy'], podii=x['podii'],
                                    za_2roky=x['za_2roky']) for x in c]
            zapysy.append(rec)
            pary_ev[id(rec)] = evs
            for x in c: x['status'] = 'у ділянці'
            funnel['точка'][f'злито в ділянки (до {DILIANKA_MAX} м уздовж вулиці)'] += len(c)
            dilianok += 1

    # ---- рівень «лінія»: точки не пройшли — відрізок вулиці × механізм ----
    lines = 0
    SEG, PV = vidrizky_misto()
    if SEG:
        segs = {s: v['pts'] for s, v in SEG.items()}
        names = {s: v['name'] for s, v in SEG.items()}
        # Лінія — відрізок СВОЄЇ вулиці між перехрестями (ZAVDANNYA-30,
        # ч. 1): подія прив'язується лише до відрізка з тією самою назвою.
        # Без цього події з Хрещатика «прилипали» до сусіднього відрізка
        # Б. Хмельницького. Відрізка своєї вулиці немає — події в лінію
        # не йдуть (на відміну від моделі, де є запасний найближчий).
        by = collections.defaultdict(list)
        na_vidr = collections.Counter()          # усі події класу B на відрізку — вага Р8
        na_vidr_sim = collections.Counter()      # (механізм, відрізок) — за 2 роки
        cache = {}
        for i, e in enumerate(ev):
            if e['klas'] != 'B': continue
            key = (e['p'], e['adr'].split(',')[0])
            if key not in cache:
                s, svoya = PV.znaity(*e['p'], SNAP_M, VR.vulytsia(e['adr']))
                cache[key] = s if svoya else None
            s = cache[key]
            if s is None: continue
            na_vidr[s] += 1
            if kv(e['date']) > kind_q - KV_VIKNO: na_vidr_sim[(e['sim'], s)] += 1
            if id(e) not in is_problem_ev: by[(e['sim'], s)].append((place[i][2], e))
        # Р8 для ліній (завдання 29, п. 5): 200 перестановок подій механізму
        # між відрізками тієї ж довжини (±25%) у тому ж районі, з вагою за
        # подіями ІНШИХ механізмів — як для точок: «вулиці з тією ж
        # щільністю». Лінія — лише якщо на ній густіше, ніж у 95% випадків.
        import numpy as np
        rng = np.random.default_rng(29)
        seg_d = {s: dmap(tuple(v['pts'][len(v['pts']) // 2])) for s, v in SEG.items()}
        by_d = collections.defaultdict(list)
        for s, d in seg_d.items(): by_d[d].append(s)
        sims_on = collections.defaultdict(collections.Counter)
        for (sm, s), n in na_vidr_sim.items(): sims_on[s][sm] += n

        def r8_linii(sim, sid):
            L0 = SEG[sid]['len']
            for tol in (0.25, 0.5, 1.0):
                pool = [s for s in by_d[seg_d[sid]] if abs(SEG[s]['len'] - L0) <= tol * L0]
                if len(pool) >= 30: break
            if sid not in pool: pool.append(sid)
            own = np.array([na_vidr_sim[(sim, s)] for s in pool], dtype=float)
            w = np.array([na_vidr[s] for s in pool], dtype=float) - own + 1.0
            w /= w.sum()
            t, k, m = pool.index(sid), int(own[pool.index(sid)]), int(own.sum())
            ge = 0
            for _ in range(N_PEREST):
                if np.count_nonzero(rng.choice(len(pool), size=m, p=w) == t) >= k: ge += 1
            return (1 + ge) / (N_PEREST + 1)

        for (sim, sid), lst in by.items():
            mc = collections.Counter(pl for pl, _e in lst)
            # лінія — лише коли події розкидані: ≥3 місця і жодне не тримає більшості
            if len(mc) < 3 or mc.most_common(1)[0][1] * 2 > len(lst): continue
            evs = [e for _pl, e in lst]
            pts = [pl for pl, _n in mc.most_common()]
            rec = zapys((sim, 'л', pts[0]), evs, 'лінія', pts)
            rec['vidrizok'] = dict(id=sid, nazva=names.get(sid, ''), dovzhyna=round(SEG[sid]['len']),
                                   geom=[[round(q[0], 5), round(q[1], 5)] for q in
                                         segs[sid][::max(1, len(segs[sid]) // 12)] + [segs[sid][-1]]])
            pary_ev[id(rec)] = evs
            # дорожні ділянки (Р4) — окремий клас без Р8, як і раніше
            if rec['status'] in PROBLEMA and rec['riven'] == 'лінія':
                pv = r8_linii(sim, sid)
                rec['r8_p'] = round(pv, 4)
                rec['vorota']['R8'] = pv < P_R8
                if pv >= P_R8: vidpalo_r8(rec, 'лінія')
            lines += 1
    else:
        log('   немає osm_risks_raw.json — рівень «лінія» пропущено')

    # ---- одна картка на вид у точці (RISHENNYA 32; завдання 29, п. 7.3) ----
    # Спортивна, 1А: хуліганство, розпивання, куріння — одна картка
    # «громадський порядок» з розбивкою за механізмами, а не три ромби.
    kartky = 0
    pt = [r for r in zapysy if r['riven'] == 'точка' and r['status'] in PROBLEMA]
    used = set()
    for i, r in enumerate(pt):
        if id(r) in used: continue
        c = [r] + [x for x in pt[i + 1:] if id(x) not in used and x['vyd'] == r['vyd']
                   and dist(x['p'], r['p']) <= R_MISCE]
        if len({x['sim'] for x in c}) < 2: continue
        for x in c: used.add(id(x))
        c.sort(key=lambda x: (x['status'] != 'хронічна', -x['za_2roky']))
        g0 = c[0]
        evs = [e for x in c for e in pary_ev.get(id(x), ())]
        adr = collections.Counter()
        for x in c:
            for a, n in x['adresy_n']: adr[a] += n
        rec = dict(g0)
        rec.update(sim=g0['vyd'], mekhanizm=L.THEMES.get(g0['vyd'], g0['vyd']),
                   status='хронічна' if any(x['status'] == 'хронічна' for x in c) else 'фіксує поліція',
                   podii=sum(x['podii'] for x in c), za_2roky=sum(x['za_2roky'] for x in c),
                   za_4kv=sum(x['za_4kv'] for x in c), adresy=[a for a, _ in adr.most_common()],
                   adresy_n=adr.most_common(), docs=[d for x in c for d in x.get('docs', [])],
                   roky=sorted({y for x in c for y in x.get('roky', [])}),
                   ostannia=max(x['ostannia'] for x in c),
                   rozbyvka=[dict(sim=x['sim'], mekhanizm=x['mekhanizm'], status=x['status'],
                                  podii=x['podii'], za_2roky=x['za_2roky'], typ=x.get('typ')) for x in c])
        # Статті з повторами: Counter з генератора склеїв би однакові ключі
        st_ = collections.Counter()
        for x in c:
            for k, n in x.get('statti', []): st_[k] += n
        rec['statti'] = st_.most_common()
        zapysy.append(rec)
        pary_ev[id(rec)] = evs
        for x in c: x['status'] = 'у картці виду'
        kartky += 1

    # ---- «формується (лише мешканці)» — 1551, три види (розд. 3.2) ----
    if G:
        lo3 = (dt.date.fromisoformat(G['last']) - dt.timedelta(days=91)).isoformat()
        lo12 = (dt.date.fromisoformat(G['last']) - dt.timedelta(days=365)).isoformat()
        by = collections.defaultdict(list)
        for d_, th, c, p in G['sk']:
            if d_ >= lo12: by[(th, p)].append(d_)
        probs = [(r['vyd'], tuple(r['p'])) for r in zapysy if r['status'] in PROBLEMA]
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

    problemy = sorted([r for r in zapysy if r['status'] in PROBLEMA and r['riven'] != 'дорожні ділянки'],
                      key=lambda r: (r['status'] != 'хронічна', -r['za_4kv'], -r['podii']))
    dilianky = [r for r in zapysy if r['status'] == 'хронічна' and r['riven'] == 'дорожні ділянки']
    gz = collections.Counter((r['vyd'], r['golos']['stan']) for r in problemy if r.get('golos'))
    rep = dict(
        versiia=dict(pravyla=PRAVYLA, podii_do=S, **({'1551_do': G['last']} if G else {}),
                     skladeno=dt.date.today().isoformat()),
        voronka={k: dict(v) for k, v in funnel.items()},
        problem=len(problemy), linii=sum(1 for r in problemy if r['riven'] == 'лінія'),
        dilianok=sum(1 for r in problemy if r['riven'] == 'ділянка'),
        fiksuie_politsiia=sum(1 for r in problemy if r['status'] == 'фіксує поліція'),
        kartok_vydu=kartky,
        bez_meshkantsiv=dict(collections.Counter(r['golos'].get('chomu') for r in problemy
                                                 if r.get('golos') and r['golos'].get('chomu')
                                                 and r['golos']['chomu'] != 'вид')),
        vidrizkiv=len(SEG or ()),
        dorozhnikh_dilianok=len(dilianky),
        formuietsia=dict(vsogo=len(formue),
                         za_dzherelom=dict(collections.Counter(f['dzherelo'] for f in formue)),
                         lyshe_meshkantsi=sum(1 for f in formue if f.get('status') == 'формується (лише мешканці)')),
        golos={f'{L.THEMES.get(t, t)} — {s}': n for (t, s), n in sorted(gz.items())},
        r8={M.simname(k): v for k, v in r8.items()},
        perelik=problemy, dorozhni_dilianky=dilianky, formuietsia_perelik=formue,
        inshi=[{k: v for k, v in r.items() if k not in ('statti', 'docs')} for r in zapysy
               if r['status'] not in PROBLEMA and r['status'] != 'не перевірена адреса'][:3000])
    try:
        rep['skhozhi_1551'] = skhozhi_1551(G, dmap, log)
    except Exception as e:                       # перевірка — не привід зупиняти карту
        log(f'   1551 на «Схожих умовах» не пораховано: {e}')
    json.dump(rep, open(REPORT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=list)
    for k, v in funnel.items():
        log(f'   {k}: ' + ', '.join(f'{a} {b:,}' for a, b in v.items()))
    log(f'   проблем {len(problemy)} (з них ліній {rep["linii"]}, ділянок {rep["dilianok"]}, '
        f'«фіксує поліція» {rep["fiksuie_politsiia"]}, карток виду {kartky}); '
        f'дорожніх ділянок {len(dilianky)}; формується {len(formue)}; '
        f'без мешканців {rep["bez_meshkantsiv"]} -> data/problems_report.json')
    return rep


if __name__ == '__main__':
    r = run()
    # --1551-md: окремий файл для чату «Проблеми» (1551-SKHOZHI-UMOVY.md)
    if '--1551-md' in sys.argv and r and r.get('skhozhi_1551'):
        zvit_1551_md(r['skhozhi_1551'], os.path.join(ROOT, '1551-SKHOZHI-UMOVY.md'))
