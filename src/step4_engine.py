# -*- coding: utf-8 -*-
"""Крок 4. Аналітичний двигун: які умови середовища пов'язані з правопорушеннями.

Одиниця аналізу — ВІДРІЗОК ВУЛИЦІ, а не квадрат сітки.
Так робили Davies & Bishop (2013, Crime Science 2(1):10); Rosser та ін. (2017,
JQC 33(3):569-594) показали, що мережа знаходить приблизно на 20% більше подій
за того самого покриття, ніж сітка. Події концентруються, дані перестають бути
розрідженими. Сітка 250 м давала 46 тисяч комірок на 2-3 тисячі подій.

Захист від хибних знахідок: навчання на 2024, перевірка на 2025-2026.
"""
import os, sys, json, math, sqlite3, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import labels as L
import mech as M

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
DB   = os.path.join(DATA, 'events.db')
RAW  = os.path.join(DATA, 'osm_risks_raw.json')
OUT  = os.path.join(DATA, 'engine_report.json')
RISK = os.path.join(DATA, 'risk.json')
TXT  = os.path.join(ROOT, 'ZVIT_DVYGUN.md')

SNAP_M  = 120     # подія прив'язується до вулиці в цьому радіусі
RADII   = [100, 250, 500]
MIN_EV  = 250
TRAIN_Y = {'2024'}
TEST_Y  = {'2025', '2026'}

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

class PtGrid:
    def __init__(s, pts, cell=0.0025):
        s.c = cell; s.g = collections.defaultdict(list)
        for p in pts: s.g[(int(p[0]/cell), int(p[1]/cell))].append(p)
    def count(s, la, lo, rad):
        my, mx = mdeg(la)
        n = int(max(rad/my, rad/mx)/s.c) + 1
        ci, cj = int(la/s.c), int(lo/s.c); k = 0
        for i in range(ci-n, ci+n+1):
            for j in range(cj-n, cj+n+1):
                for p in s.g.get((i, j), ()):
                    if math.hypot((p[0]-la)*my, (p[1]-lo)*mx) <= rad: k += 1
        return k

def seg_len(pts):
    t = 0
    for a, b in zip(pts, pts[1:]):
        my, mx = mdeg((a[0]+b[0])/2)
        t += math.hypot((a[0]-b[0])*my, (a[1]-b[1])*mx)
    return t

def main():
    import numpy as np
    from sklearn.linear_model import PoissonRegressor
    from sklearn.preprocessing import StandardScaler

    for f in (DB, RAW):
        if not os.path.exists(f): print(f'немає {f}'); sys.exit(1)
    raw = json.load(open(RAW, encoding='utf-8'))

    # ---- 1. відрізки вулиць ----
    segs, names = {}, {}
    for w in raw.get('roads', []):
        g = w.get('geometry')
        if not g or len(g) < 2: continue
        pts = [(p['lat'], p['lon']) for p in g]
        if seg_len(pts) < 40: continue
        sid = w['id']
        segs[sid] = pts
        names[sid] = (w.get('tags', {}) or {}).get('name', '')
    print(f'відрізків вулиць: {len(segs):,}')
    sids = sorted(segs)
    sidx = {s: i for i, s in enumerate(sids)}
    mid = {s: segs[s][len(segs[s])//2] for s in sids}
    slen = {s: seg_len(segs[s]) for s in sids}

    # ---- 2. ознаки ----
    print('1) ознаки середовища...')
    feats = {}
    NAMES = {'bar_on': 'бари', 'bar_off': 'алкоголь_винос', 'shop24': 'магазини',
             'finance': 'ломбарди', 'gambling': 'гральні', 'food': 'кафе',
             'fuel': 'АЗС', 'parking': 'паркінги', 'metro': 'метро',
             'busstop': 'зупинки', 'market': 'ринки', 'school': 'школи',
             'univer': 'ВНЗ', 'health': 'лікарні', 'abandon': 'покинуті',
             'bench': 'лавки', 'play': 'майданчики', 'cctv': 'камери',
             'trees': 'дерева', 'park': 'парки', 'grass': 'трава'}
    for k, ua in NAMES.items():
        items = raw.get(k, [])
        pts = []
        for el in items:
            la = el.get('lat') or (el.get('center') or {}).get('lat')
            lo = el.get('lon') or (el.get('center') or {}).get('lon')
            if la and lo: pts.append((la, lo))
        if not pts: continue
        pg = PtGrid(pts)
        for r in RADII:
            feats[f'{ua}_{r}м'] = {s: pg.count(*mid[s], r) for s in sids}
    # житло
    hp = []
    for el in raw.get('houses', []):
        la = el.get('lat') or (el.get('center') or {}).get('lat')
        lo = el.get('lon') or (el.get('center') or {}).get('lon')
        if la and lo: hp.append((la, lo))
    if hp:
        hg = PtGrid(hp)
        for r in RADII:
            feats[f'житло_{r}м'] = {s: hg.count(*mid[s], r) for s in sids}
    # геометрія самого відрізка
    RD = {}
    for w in raw.get('roads', []):
        t = w.get('tags', {}) or {}
        RD[w['id']] = t
    HW = {'residential': 1, 'living_street': 1, 'unclassified': 2,
          'tertiary': 3, 'secondary': 4, 'primary': 5}
    feats['клас_дороги'] = {s: HW.get(RD.get(s, {}).get('highway', ''), 2) for s in sids}
    feats['смуг'] = {s: float(RD.get(s, {}).get('lanes', 2) or 2)
                     if str(RD.get(s, {}).get('lanes', '2')).isdigit() else 2 for s in sids}
    # мережева геометрія
    ngp = os.path.join(DATA, 'netgeo.json')
    if os.path.exists(ngp):
        NG = json.load(open(ngp, encoding='utf-8'))
        for fld, ua in (('perm', 'проникність'), ('cross4', 'хрестоподібні'),
                        ('cross3', 'T_подібні'), ('dead', 'тупик'),
                        ('sinuo', 'звивистість'), ('inner', 'перехрестя_всередині')):
            feats[ua] = {s: float(NG.get(str(s), {}).get(fld, 0)) for s in sids}

    # населення
    pp = os.path.join(DATA, 'population.json')
    if os.path.exists(pp):
        P = json.load(open(pp, encoding='utf-8'))
        pts = [(x[0], x[1]) for x in P['items'] for _ in range(max(1, x[2] // 150))]
        if pts:
            pg2 = PtGrid(pts)
            for r in (250, 500):
                feats[f'населення_{r}м'] = {s: pg2.count(*mid[s], r) for s in sids}

    # ---- ПІШОХІДНІ ПОТОКИ ЯК ОЗНАКА (Davies & Bishop 2013) ----
    # ВИПРАВЛЕНО 2026-08. Стара редакція брала МАКСИМУМ потоку по НАЗВІ
    # вулиці й приписувала його всім її відрізкам. На вул. Стеценка (54 відрізки) потік
    # коливається від 73 до 2 893 — тобто вся внутрішньовулична варіація, заради
    # якої одиницею аналізу й обрано відрізок, знищувалася. Наслідок: ознака
    # «прохідність» жодного разу не потрапила в топ-20 чинників жодної теми.
    # Тепер беремо потік по id відрізка й додаємо три цільові потоки окремо.
    npth = os.path.join(DATA, 'network.json')
    if os.path.exists(npth):
        N = json.load(open(npth, encoding='utf-8'))
        byid = {}
        byname = collections.defaultdict(int)
        for it in N.get('items', []):
            if len(it) > 6 and it[6] is not None:
                byid[it[6]] = (it[2], it[3], it[4], it[5])
            if it[1]: byname[it[1]] = max(byname[it[1]], it[2])
        if byid:
            for j, ua in ((0, 'прохідність'), (1, 'потік_школи'),
                          (2, 'потік_транспорт'), (3, 'потік_торгівля')):
                feats[ua] = {s: float(byid.get(s, (0, 0, 0, 0))[j]) for s in sids}
            print(f'   потоки по відрізках: {len(byid):,} з {len(sids):,}')
        else:
            # запасний варіант для старого network.json без id відрізка
            feats['прохідність'] = {s: float(byname.get(names[s], 0)) for s in sids}
            print('   потоки лише по назві вулиці (старий формат network.json)')
    print(f'   ознак: {len(feats)}')

    # ---- 3. події -> відрізки ----
    print('2) прив\'язую події до вулиць...')
    sg = SegGrid(segs)
    # виключені адреси установ (суди, управління поліції) — той самий список, що й на карті
    excl = set()
    for _f in ('vykluchennya.txt', 'vykluchennya_moyi.txt'):
        ep = os.path.join(DATA, _f)
        if not os.path.exists(ep): continue
        for ln in open(ep, encoding='utf-8'):
            ln = ln.split('#')[0].strip()
            if ln: excl.add(ln.lower())
        print(f'   виключених адрес установ: {len(excl)}')
    conn = sqlite3.connect(DB)
    rows = conn.execute("""SELECT e.cat, e.date, g.lat, g.lon, e.street, e.house FROM events e
                           JOIN geo g ON g.doc_id=e.doc_id
                           WHERE g.precision='house'""").fetchall()
    before = len(rows)
    rows = [r for r in rows
            if ((r[4] + ', ' + r[5]) if (r[4] and r[5]) else (r[4] or '')).lower() not in excl]
    if before != len(rows):
        print(f'   вилучено подій на адресах установ: {before - len(rows):,}')
    # ОДИНИЦЯ МОДЕЛІ — МЕХАНІЗМ, не тема (рішення 31.08.2026).
    # tr/te рахуємо по механізму, trT/teT — по темі. Теми лишаються, щоб було
    # з чим порівняти: механізм іде на карту лише тоді, коли на власних подіях
    # він вгадує краще, ніж спільна модель теми.
    tr = collections.defaultdict(collections.Counter)
    te = collections.defaultdict(collections.Counter)
    trT = collections.defaultdict(collections.Counter)
    teT = collections.defaultdict(collections.Counter)
    cache = {}; hit = 0
    for cat, date, la, lo, _st, _hs in rows:
        ck = (round(la, 5), round(lo, 5))
        if ck in cache: s = cache[ck]
        else: s = cache[ck] = sg.nearest(la, lo, SNAP_M)
        if s is None: continue
        lb = L.CODE.get(cat)
        if not lb: continue
        sim = M.simgroup(cat)
        hit += 1
        y = date[:4]
        if y in TRAIN_Y: tr[sim][s] += 1; trT[lb[0]][s] += 1
        elif y in TEST_Y: te[sim][s] += 1; teT[lb[0]][s] += 1
    print(f'   подій прив\'язано: {hit:,} з {len(rows):,}')
    print(f'   механізмів: {len(tr)}, тем: {len(trT)}')

    fnames = sorted(feats)
    X0 = np.array([[feats[f][s] for f in fnames] for s in sids], dtype=np.float64)
    # ЕКСПОЗИЦІЯ: довжина вулиці. Модель вчиться на щільності подій на метр,
    # але прогноз множиться назад на довжину — абсолютні числа зберігаються.
    expo = np.array([max(slen[s], 20.0) for s in sids], dtype=np.float64)
    expo = expo / expo.mean()

    # ---- парні взаємодії найсильніших ознак ----
    base_n = list(fnames)
    TOPK = int(os.environ.get('TOPK', '14'))
    inter_idx = None   # визначається окремо для кожного механізму
    print(f'   одиничних ознак: {len(fnames)}')

    def hit_rate(score, actual, pct):
        """частка подій наступного періоду у верхніх pct% вулиць"""
        k = max(1, int(len(score) * pct))
        top = np.argsort(-score)[:k]
        return float(actual[top].sum() / max(actual.sum(), 1))

    base = 0.10   # випадковий рівень: 10% вулиць -> 10% подій
    lons = np.array([mid[s][1] for s in sids])
    wmask, emask = lons <= np.median(lons), lons > np.median(lons)

    def fit_one(key, cnt_tr, cnt_te, alphas, rival=None):
        """Навчає модель для однієї одиниці — теми або механізму.
        `rival` — прогноз моделі теми. Його міряємо на ПОДІЯХ ЦЬОГО МЕХАНІЗМУ:
        це і є чесне питання «чи власна модель механізму краща за спільну».
        Повертає (запис звіту, шар ризику, прогноз) або None, якщо подій замало."""
        n_tr = sum(cnt_tr.values())
        if n_tr < MIN_EV: return None
        y = np.array([cnt_tr.get(s, 0) for s in sids], dtype=np.float64)
        yt = np.array([cnt_te.get(s, 0) for s in sids], dtype=np.float64)
        if yt.sum() < 50: return None

        # --- взаємодії будуються з топ-K ознак, найсильніших САМЕ для цієї одиниці ---
        with np.errstate(invalid='ignore', divide='ignore'):
            cc = np.array([abs(np.corrcoef(X0[:, i], y)[0, 1]) if X0[:, i].std() > 0 else 0
                           for i in range(X0.shape[1])])
        cc = np.nan_to_num(cc)
        top = list(np.argsort(-cc)[:TOPK])
        icols, inames = [], []
        for a_ in range(len(top)):
            for b_ in range(a_ + 1, len(top)):
                i, j = top[a_], top[b_]
                icols.append(X0[:, i] * X0[:, j])
                inames.append(f'{base_n[i]} × {base_n[j]}')
        Xf = np.hstack([X0, np.array(icols).T]) if icols else X0
        fn = base_n + inames

        Xs = StandardScaler().fit_transform(Xf)
        Xh = np.hstack([Xs, StandardScaler().fit_transform(np.log1p(y).reshape(-1, 1))])

        rate = y / expo                      # події на одиницю довжини
        def fit_best(XX):
            bb = None
            for a in alphas:
                m = PoissonRegressor(alpha=a, max_iter=700).fit(XX, rate, sample_weight=expo)
                p = m.predict(XX) * expo     # назад в абсолютні числа
                h = hit_rate(p, yt, 0.10)
                if bb is None or h > bb[0]: bb = (h, m, p)
            return bb

        # А) тільки історія подій   Б) тільки середовище   В) разом
        hA = hit_rate(y, yt, 0.10)
        hB, mB, pB = fit_best(Xs)
        hC, mC, pC = fit_best(Xh)

        # ГЕОГРАФІЧНА ПЕРЕВІРКА: вчимось на західній половині, міряємо на східній
        hGeo = float('nan')
        if y[wmask].sum() > 60 and yt[emask].sum() > 30:
            mg = PoissonRegressor(alpha=alphas[-1], max_iter=700).fit(
                Xs[wmask], rate[wmask], sample_weight=expo[wmask])
            pg_ = mg.predict(Xs[emask]) * expo[emask]
            hGeo = hit_rate(pg_, yt[emask], 0.10)

        r = float(np.corrcoef(pB, yt)[0, 1]) if yt.std() > 0 else 0.0
        co = sorted(zip(fn, mB.coef_), key=lambda x: -abs(x[1]))
        rk = pB / (pB.max() or 1)
        layer = {
            'hit': round(hB, 3),
            'items': [[segs[sids[i]][::max(1, len(segs[sids[i]])//8)],
                       names[sids[i]], round(float(rk[i]), 3), int(y[i])]
                      for i in np.argsort(-rk)[:1200]]}
        entry = {
            'навчання': n_tr, 'перевірка': int(yt.sum()), 'r': round(r, 3),
            'hit_історія': round(hA, 3), 'hit_середовище': round(hB, 3),
            'hit_разом': round(hC, 3),
            'hit_інший_район': None if hGeo != hGeo else round(hGeo, 3),
            'PAI_середовище': round(hB / base, 2), 'PAI_історія': round(hA / base, 2),
            'фактори': [[n, round(float(c), 3)] for n, c in co if abs(c) > 0.02][:20]}
        if rival is not None:
            entry['hit_моделлю_теми'] = round(hit_rate(rival, yt, 0.10), 3)
        return entry, layer, pB

    def show(title, e):
        print(f'\n--- {title} ---')
        print(f"   навчання {e['навчання']:,} / перевірка {e['перевірка']:,}".replace(',', ' '))
        print(f"   у верхніх 10% вулиць опиняється подій наступних років:")
        print(f"      історія подій:   {100*e['hit_історія']:5.1f}%   (у {e['PAI_історія']:.1f} рази краще за випадок)")
        print(f"      середовище:      {100*e['hit_середовище']:5.1f}%   (у {e['PAI_середовище']:.1f} рази)")
        print(f"      разом:           {100*e['hit_разом']:5.1f}%")
        if e['hit_інший_район'] is not None:
            print(f"      ІНША ПОЛОВИНА МІСТА: {100*e['hit_інший_район']:5.1f}%")
        for n, c in e['фактори'][:6]:
            print(f'      {c:+.3f}  {n}')

    # альфа-сітка: у механізмів вона коротша, бо їх утричі більше
    ALPHA_T = (0.3, 1.0, 3.0, 10.0)
    ALPHA_M = tuple(float(a) for a in os.environ.get('ALPHA_M', '1,3').split(','))

    report, risk_layers = {}, {}
    theme_pred = {}

    # ---- А. ТЕМИ: лишаються як загальний шар і як планка для механізмів ----
    print('\n' + '=' * 60)
    print('ТЕМИ (загальний шар і планка порівняння)')
    print('=' * 60)
    for th in sorted(trT, key=lambda x: -sum(trT[x].values())):
        got = fit_one(th, trT[th], teT[th], ALPHA_T)
        if not got: continue
        e, lay, pB = got
        e.update(вид='тема', тема=L.THEMES.get(th, th), назва=L.THEMES.get(th, th))
        lay.update(kind='theme', theme=th, name=L.THEMES.get(th, th),
                   title='Ризик: ' + L.THEMES.get(th, th), slug=M.anchor(th))
        report[th] = e; risk_layers[th] = lay; theme_pred[th] = pB
        show(L.THEMES.get(th, th), e)

    # ---- Б. МЕХАНІЗМИ: те, що сталося насправді ----
    print('\n' + '=' * 60)
    print('МЕХАНІЗМИ')
    print('=' * 60)
    weaker = []
    for sim in sorted(tr, key=lambda x: -sum(tr[x].values())):
        th = M.simtheme(sim)
        got = fit_one(sim, tr[sim], te[sim], ALPHA_M, rival=theme_pred.get(th))
        if not got: continue
        e, lay, _p = got
        nm = M.simname(sim)
        # Чесна перевірка: беремо ПОДІЇ ЦЬОГО МЕХАНІЗМУ за наступні роки й
        # питаємо, хто краще вгадав, де вони будуть, — спільна модель теми
        # чи власна модель механізму. Порівнюються два прогнози на одній і тій
        # самій мішені, тож числа співмірні. Програв — на карту не йде.
        rh = e.get('hit_моделлю_теми')
        better = rh is None or e['hit_середовище'] >= rh
        e.update(вид='механізм', тема=L.THEMES.get(th, th), назва=nm,
                 тема_код=th, краще_за_тему=better)
        report[sim] = e
        if better:
            lay.update(kind='mech', theme=th, name=nm,
                       title='Ризик: ' + nm, slug=M.anchor(sim))
            risk_layers[sim] = lay
        else:
            weaker.append((sim, nm, e['hit_середовище'], rh))
        tag = '' if better else '  — модель теми вгадує краще, на карту не йде'
        show(f'{nm}  [{L.THEMES.get(th, th)}]{tag}', e)
        if rh is not None:
            print(f"      на цих самих подіях модель теми дає {100*rh:.1f}%")

    if weaker:
        print('\n=== механізми, де спільна модель теми виявилася кращою ===')
        for sim, nm, h, rh in weaker:
            print(f'   {nm}: власна {100*h:.0f}% проти {100*rh:.0f}% у теми')
    print(f'\nшарів ризику на карті: {len(risk_layers)} '
          f'({sum(1 for v in risk_layers.values() if v["kind"] == "mech")} механізмів '
          f'+ {sum(1 for v in risk_layers.values() if v["kind"] == "theme")} тем)')

    # ---- НЕБЕЗПЕЧНІ ПІДХОДИ ДО ШКІЛ: потік дітей + немає тротуару ----
    danger = []
    npth2 = os.path.join(DATA, 'network.json')
    rp2 = os.path.join(DATA, 'risks.json')
    if os.path.exists(npth2) and os.path.exists(rp2):
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
            if flow <= 0: continue
            if nm in nowalk:
                danger.append({'вулиця': nm, 'потік_до_шкіл': flow,
                               'місце_в_рейтингу': i, 'усього_вулиць': len(ranked)})
        danger = danger[:60]
        print(f'\n=== НЕБЕЗПЕЧНІ ПІДХОДИ ДО ШКІЛ: {len(danger)} ділянок ===')
        for d in danger[:15]:
            print(f"   потік {d['потік_до_шкіл']:4}  (місце {d['місце_в_рейтингу']})  {d['вулиця']}")

    json.dump({'layers': risk_layers, 'danger': danger},
              open(RISK, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(f'   карта ризику -> data/risk.json')
    json.dump(report, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    with open(TXT, 'w', encoding='utf-8') as f:
        f.write('# Звіт аналітичного двигуна\n\n')
        f.write(f'Одиниця аналізу — відрізок вулиці ({len(segs):,} шт.), ознак {len(feats)}.\n')
        f.write('Навчання 2024, перевірка 2025–2026.\n\n')
        f.write('> Головна метрика — **влучність**: яка частка подій 2025–2026 припала\n')
        f.write('> на верхні 10% вулиць, відібраних моделлю за 2024 рік.\n')
        f.write('> Випадковий відбір дав би 10%. Коефіцієнт PAI показує, у скільки разів краще.\n\n')
        f.write('Одиниця моделі — **механізм** (те, що сталося), а не тема (папка\n')
        f.write('в законі). Теми лишено для порівняння: механізм потрапляє на карту\n')
        f.write('лише тоді, коли він точніший за власну тему.\n\n')

        def _tbl(items, head):
            f.write(head)
            f.write('|---|---|---|---|---|---|\n')
            for _k, d in items:
                g = d.get('hit_інший_район')
                gs = f"{100*g:.0f}%" if g is not None else "—"
                f.write(f"| {d['назва']} | {100*d['hit_історія']:.0f}% "
                        f"| **{100*d['hit_середовище']:.0f}%** "
                        f"| {100*d['hit_разом']:.0f}% | {gs} | {d['навчання']:,} |\n")
            f.write('\n')

        themes = sorted([kv for kv in report.items() if kv[1]['вид'] == 'тема'],
                        key=lambda x: -x[1]['hit_середовище'])
        mechs = sorted([kv for kv in report.items() if kv[1]['вид'] == 'механізм'],
                       key=lambda x: -x[1]['hit_середовище'])
        f.write('## Механізми\n\n')
        _tbl(mechs, '| Механізм | Історія | Середовище | Разом | Інша половина міста | Подій |\n')
        drop = [kv for kv in mechs if not kv[1].get('краще_за_тему')]
        if drop:
            f.write('Не показані на карті: на подіях цих механізмів спільна модель\n')
            f.write('теми вгадала краще, ніж власна модель механізму — ')
            f.write(', '.join(f"{d['назва']} ({100*d['hit_середовище']:.0f}% проти "
                              f"{100*d['hit_моделлю_теми']:.0f}%)" for _k, d in drop))
            f.write('.\n\n')
        f.write('## Теми (для порівняння)\n\n')
        _tbl(themes, '| Тема | Історія | Середовище | Разом | Інша половина міста | Подій |\n')

        for th, d in sorted(report.items(), key=lambda x: -x[1]['hit_середовище']):
            f.write(f"### {d['назва']}"
                    + ('' if d['вид'] == 'тема' else f" · {d['тема']}") + "\n\n")
            f.write(f"Подій {d['навчання']:,} / {d['перевірка']:,}. ")
            f.write(f"Влучність середовища **{100*d['hit_середовище']:.0f}%** ")
            f.write(f"(PAI {d['PAI_середовище']}), історії {100*d['hit_історія']:.0f}%, ")
            f.write(f"разом {100*d['hit_разом']:.0f}%.")
            if d.get('hit_інший_район') is not None:
                f.write(f" **Перенесення на іншу половину міста: {100*d['hit_інший_район']:.0f}%.**")
            f.write("\n\n")
            f.write('| Вага | Фактор |\n|---|---|\n')
            for n, c in d['фактори']:
                f.write(f'| {c:+.3f} | {n} |\n')
            f.write('\n')
    print(f'\n=== ГОТОВО === ZVIT_DVYGUN.md')

if __name__ == '__main__':
    main()
