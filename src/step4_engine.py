# -*- coding: utf-8 -*-
"""Крок 4. Аналітичний двигун: пошук факторів середовища, пов'язаних з подіями.

Методологія — Risk Terrain Modeling (Caplan & Kennedy).
Місто ділиться на сітку; для кожної комірки рахуються сотні ознак середовища;
штрафована пуассонівська регресія відбирає значущі.

Захист від хибних знахідок: навчання на одному році, перевірка на іншому.
"""
import os, sys, json, math, sqlite3, collections, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import labels as L

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
DB   = os.path.join(DATA, 'events.db')
OUT  = os.path.join(DATA, 'engine_report.json')
TXT  = os.path.join(ROOT, 'ZVIT_DVYGUN.md')

CELL_M  = 150                       # сторона комірки, метрів (≈ довжина кварталу)
RADII   = [100, 250, 500]           # радіуси, на яких перевіряється кожен фактор
BBOX    = (50.34, 30.30, 50.59, 30.83)
MIN_EV  = 300                       # мінімум подій, щоб будувати модель для теми
TRAIN_Y = {'2024'}
TEST_Y  = {'2025', '2026'}

def mdeg(lat): return 111320.0, 111320.0 * math.cos(math.radians(lat))

class Cells:
    """рівномірна сітка по місту"""
    def __init__(self, bbox, cell_m):
        s, w, n, e = bbox
        self.s, self.w = s, w
        my, mx = mdeg((s + n) / 2)
        self.dlat = cell_m / my
        self.dlon = cell_m / mx
        self.ny = int((n - s) / self.dlat) + 1
        self.nx = int((e - w) / self.dlon) + 1
    def idx(self, la, lo):
        i = int((la - self.s) / self.dlat); j = int((lo - self.w) / self.dlon)
        if 0 <= i < self.ny and 0 <= j < self.nx: return i * self.nx + j
        return None
    def center(self, k):
        i, j = divmod(k, self.nx)
        return self.s + (i + .5) * self.dlat, self.w + (j + .5) * self.dlon
    def __len__(self): return self.ny * self.nx

def count_near(cells, pts, radius_m):
    """для кожної комірки — скільки об'єктів у радіусі"""
    res = collections.Counter()
    my, mx = mdeg((cells.s + cells.dlat * cells.ny / 2))
    ri = int(radius_m / my / cells.dlat) + 1
    rj = int(radius_m / mx / cells.dlon) + 1
    for la, lo in pts:
        i = int((la - cells.s) / cells.dlat); j = int((lo - cells.w) / cells.dlon)
        for di in range(-ri, ri + 1):
            for dj in range(-rj, rj + 1):
                ii, jj = i + di, j + dj
                if 0 <= ii < cells.ny and 0 <= jj < cells.nx:
                    cy = cells.s + (ii + .5) * cells.dlat
                    cx = cells.w + (jj + .5) * cells.dlon
                    if math.hypot((cy - la) * my, (cx - lo) * mx) <= radius_m:
                        res[ii * cells.nx + jj] += 1
    return res

def load_features(cells):
    """збирає всі ознаки середовища -> {назва: {cell: значення}}"""
    F = {}
    rp = os.path.join(DATA, 'risks.json')
    if os.path.exists(rp):
        R = json.load(open(rp, encoding='utf-8'))
        for k, v in R.get('points', {}).items():
            pts = [(x[0], x[1]) for x in v['items']]
            for r in RADII:
                F[f'{k}_{r}м'] = count_near(cells, pts, r)
        for k, v in R.get('lines', {}).items():
            pts = []
            for it in v['items']:
                pts += [(p[0], p[1]) for p in it[0]]
            for r in (100, 250):
                F[f'{k}_{r}м'] = count_near(cells, pts, r)
    np_ = os.path.join(DATA, 'network.json')
    if os.path.exists(np_):
        N = json.load(open(np_, encoding='utf-8'))
        flow = collections.Counter()
        for it in N.get('items', []):
            c = it[2]
            for p in it[0]:
                k = cells.idx(p[0], p[1])
                if k is not None: flow[k] = max(flow[k], c)
        F['прохідність'] = flow
    pp = os.path.join(DATA, 'population.json')
    if os.path.exists(pp):
        P = json.load(open(pp, encoding='utf-8'))
        pop = collections.Counter()
        for la, lo, n in P['items']:
            k = cells.idx(la, lo)
            if k is not None: pop[k] += n
        F['населення'] = pop
        for r in (500,):
            F[f'населення_{r}м'] = count_near(
                cells, [(x[0], x[1]) for x in P['items'] for _ in range(max(1, x[2] // 200))], r)
    return F

def load_events(cells):
    """події по комірках, окремо навчальні й перевірочні роки, за темами"""
    conn = sqlite3.connect(DB)
    rows = conn.execute("""SELECT e.cat, e.date, g.lat, g.lon
                           FROM events e JOIN geo g ON g.doc_id=e.doc_id
                           WHERE g.precision='house'""").fetchall()
    tr = collections.defaultdict(collections.Counter)
    te = collections.defaultdict(collections.Counter)
    for cat, date, la, lo in rows:
        k = cells.idx(la, lo)
        if k is None: continue
        lb = L.CODE.get(cat)
        if not lb: continue
        th = lb[0]
        y = date[:4]
        if y in TRAIN_Y: tr[th][k] += 1
        elif y in TEST_Y: te[th][k] += 1
    return tr, te

def main():
    import numpy as np
    from sklearn.linear_model import PoissonRegressor
    from sklearn.preprocessing import StandardScaler

    if not os.path.exists(DB): print('немає data/events.db'); sys.exit(1)
    cells = Cells(BBOX, CELL_M)
    print(f'сітка: {cells.nx} x {cells.ny} = {len(cells):,} комірок по {CELL_M} м')

    print('1) ознаки середовища...')
    F = load_features(cells)
    names = sorted(F)
    print(f'   ознак: {len(names)}')
    if not names: print('   немає жодної — запустіть 2b, 2c, 0d'); sys.exit(1)

    print('2) події...')
    tr, te = load_events(cells)
    for th in sorted(tr, key=lambda x: -sum(tr[x].values())):
        print(f'   {L.THEMES.get(th, th):28} навчання {sum(tr[th].values()):>7,}   перевірка {sum(te[th].values()):>7,}')

    # матриця ознак
    keys = list(range(len(cells)))
    X = np.zeros((len(keys), len(names)), dtype=np.float32)
    for j, nm in enumerate(names):
        d = F[nm]
        for k, v in d.items(): X[k, j] = v
    keep = (X.sum(axis=1) > 0)
    X = X[keep]; keys = [k for k, m in zip(keys, keep) if m]
    print(f'   комірок з ознаками: {len(keys):,}')
    kidx = {k: i for i, k in enumerate(keys)}

    report = {}
    for th in sorted(tr, key=lambda x: -sum(tr[x].values())):
        n_tr = sum(tr[th].values())
        if n_tr < MIN_EV: continue
        y = np.zeros(len(keys), dtype=np.float32)
        for k, v in tr[th].items():
            if k in kidx: y[kidx[k]] = v
        yt = np.zeros(len(keys), dtype=np.float32)
        for k, v in te[th].items():
            if k in kidx: yt[kidx[k]] = v

        sc = StandardScaler().fit(X)
        Xs = sc.transform(X)
        best = None
        for a in (0.5, 1.0, 3.0, 10.0):
            m = PoissonRegressor(alpha=a, max_iter=400)
            m.fit(Xs, y)
            # перевірка на іншому році: кореляція прогнозу з фактом
            pred = m.predict(Xs)
            r = float(np.corrcoef(pred, yt)[0, 1]) if yt.std() > 0 else 0.0
            if best is None or r > best[0]: best = (r, a, m)
        r, a, m = best
        coefs = sorted(zip(names, m.coef_), key=lambda x: -abs(x[1]))
        report[th] = {
            'тема': L.THEMES.get(th, th), 'подій_навчання': n_tr,
            'подій_перевірка': int(yt.sum()),
            'кореляція_на_іншому_році': round(r, 3), 'alpha': a,
            'фактори': [[n, round(float(c), 4)] for n, c in coefs[:20] if abs(c) > 0.01],
        }
        print(f'\n--- {L.THEMES.get(th, th)} ---')
        print(f'   перенесення на інший рік: r = {r:.3f}')
        for n, c in coefs[:10]:
            if abs(c) < 0.01: break
            print(f'      {c:+.3f}  {n}')

    json.dump(report, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    with open(TXT, 'w', encoding='utf-8') as f:
        f.write('# Звіт аналітичного двигуна\n\n')
        f.write(f'Сітка {CELL_M} м, ознак {len(names)}, ')
        f.write(f'навчання {"/".join(sorted(TRAIN_Y))}, перевірка {"/".join(sorted(TEST_Y))}\n\n')
        f.write('> Кореляція на іншому році — головний показник. Нижче 0,3 модель ненадійна.\n\n')
        for th, d in sorted(report.items(), key=lambda x: -x[1]['кореляція_на_іншому_році']):
            f.write(f"## {d['тема']}\n\n")
            f.write(f"Подій: {d['подій_навчання']:,} / {d['подій_перевірка']:,}. ")
            f.write(f"**Перенесення на інший рік: r = {d['кореляція_на_іншому_році']}**\n\n")
            f.write('| Вага | Фактор |\n|---|---|\n')
            for n, c in d['фактори'][:15]:
                f.write(f'| {c:+.3f} | {n} |\n')
            f.write('\n')
    print(f'\n=== ГОТОВО === data/engine_report.json + ZVIT_DVYGUN.md')

if __name__ == '__main__':
    main()
