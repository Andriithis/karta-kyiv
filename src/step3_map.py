# -*- coding: utf-8 -*-
"""Крок 3. Карта з агрегацією по адресах + рейтинг адрес.

Класифікація спрощена до інцидент/проблема (передача, п.7.1): «проблема» —
це членство в кураторському списку ~50 адрес-напрямків (п.7.3), відібраних за
однорідністю СТАТТІ, а не теми (п.7.2). Аномалія як окрема категорія прибрана:
якщо відібраний напрямок не пояснюється моделлю ризику, картка просто каже
«причина встановлюється на місці» (п.7.1, 7.4).
"""
import os, sys, csv, json, glob, math, sqlite3, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import labels as L

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data'); DB = os.path.join(DATA, 'events.db')
OUT  = os.path.join(ROOT, 'karta.html')
RISKS = os.path.join(DATA, 'risks.json')
NETW  = os.path.join(DATA, 'network.json')
RISKF = os.path.join(DATA, 'risk.json')
BORD  = os.path.join(DATA, 'borders.json')
EXCL = os.path.join(DATA, 'vykluchennya.txt')          # формується автоматично
MANUAL = os.path.join(DATA, 'vykluchennya_moyi.txt')    # ваш список, ніколи не перезаписується
REVIEW = os.path.join(DATA, 'top100_dlya_pereviryky.txt')

SHARE_LIMIT = 0.015      # адреса, що дає >2% подій свого району, вважається установою
ABS_LIMIT   = 90       # або перевищує цю кількість подій

# ---- ВІДБІР ПРОБЛЕМ (п.7.3) ----
MIN_EPISODES = 15   # мінімум однорідних епізодів (за групою подібності, п.7.2) на адресу
GUARANTEE    = 2    # обов'язкових проблем з кожного району
CITYWIDE     = 30   # + найгостріших по місту понад гарантовані районні

# Квота за напрямком (теми). На реальних даних дорожній рух — 85% усіх кандидатів
# (утричі більше подій за наступну тему), тож без обмежень він займав 48 з 50 місць,
# а насильство/середовище не потрапляли жодного разу. Квота дорожнього руху свідомо
# більша за інші — це найчисельніша тема, і повне вирівнювання було б нечесним щодо
# реальності. Якщо в темі просто немає кандидатів (як у насильства чи середовища),
# її квота лишається незаповненою — місця йдуть наступним найгострішим, а не пропадають.
CAP_THEME   = {'ДОР': 18}
CAP_DEFAULT = 10

def load_excl():
    man = set()
    if not os.path.exists(MANUAL):
        with open(MANUAL, 'w', encoding='utf-8') as f:
            f.write('# ВАШ список адрес, які треба виключити з карти.\n')
            f.write('# Цей файл автоматика НІКОЛИ не перезаписує.\n')
            f.write('# Один рядок = одна адреса, точно як у vykluchennya.txt\n\n')
    # ЧИТАЄМО ЛИШЕ РУЧНИЙ файл. Автоматичний (EXCL) — це результат, не вхід:
    # інакше адреса, раз потрапивши туди, лишалась би виключеною назавжди.
    if os.path.exists(MANUAL):
        for ln in open(MANUAL, encoding='utf-8'):
            ln = ln.split('#')[0].strip()
            if ln: man.add(ln.lower())
    return man

def detect_institutional(rows, manual):
    per_court = collections.Counter(r[1] for r in rows)
    per_addr = collections.Counter()
    addr_court = {}
    for r in rows:
        if not r[5]: continue
        a = (r[5] + ', ' + r[6]) if r[6] else r[5]
        per_addr[a] += 1
        addr_court[a] = r[1]
    auto = {}
    for a, n in per_addr.items():
        tot = per_court[addr_court[a]] or 1
        if n >= ABS_LIMIT or n / tot >= SHARE_LIMIT:
            auto[a] = (n, round(100 * n / tot, 1))
    # звіт: топ-100 адрес із профілем статей, щоб можна було оцінити очима
    prof = collections.defaultdict(collections.Counter)
    for r in rows:
        if not r[5]: continue
        a = (r[5] + ', ' + r[6]) if r[6] else r[5]
        lb = L.CODE.get(r[2])
        prof[a][lb[1] if lb else r[2]] += 1
    with open(REVIEW, 'w', encoding='utf-8') as f:
        f.write('# Топ-100 адрес за кількістю подій, із профілем статей.\n')
        f.write('# Якщо бачите установу (суд, відділ поліції, місце оформлення протоколів) —\n')
        f.write('# скопіюйте її адресу у файл vykluchennya.txt окремим рядком.\n')
        f.write('# Ознака місця оформлення: майже все — ст.130, ст.126, ст.122-4.\n\n')
        for a, n in per_addr.most_common(100):
            mark = ' [ВЖЕ ВИКЛЮЧЕНО]' if a in auto else ''
            f.write(f'{n:6}  {a}{mark}\n')
            for st, k in prof[a].most_common(4):
                f.write(f'          {k:5}  {st}\n')
            f.write('\n')
    print(f'   звіт для перегляду: data/top100_dlya_pereviryky.txt')

    if auto or not os.path.exists(EXCL):
        with open(EXCL, 'w', encoding='utf-8') as f:
            f.write('# Адреси, виключені з карти як установи (суди, відділи поліції).\n')
            f.write('# Визначено автоматично: адреса дає понад 2% подій свого району\n')
            f.write('# або понад 120 подій. Приберіть рядок, якщо адреса справжня.\n')
            f.write('# Один рядок = одна адреса.\n\n')
            for a, (n, pc) in sorted(auto.items(), key=lambda x: -x[1][0]):
                f.write(f'{a}   # {n} подій, {pc}% району\n')
        print(f'   виявлено установ: {len(auto)} -> data/vykluchennya.txt')
        for a, (n, pc) in sorted(auto.items(), key=lambda x: -x[1][0])[:8]:
            print(f'     {n:5}  {pc:4}%  {a}')
    return {a.lower() for a in auto} | manual

COURTS = {'Golosiivskyi':'Голосіївський','Darnytskyi':'Дарницький','Desnianskyi':'Деснянський',
 'Dniprovskyi':'Дніпровський','Obolonskyi':'Оболонський','Pecherskyi':'Печерський',
 'Podilskyi':'Подільський','Sviatoshynskyi':'Святошинський','Solomianskyi':"Солом'янський",
 'Shevchenkivskyi':'Шевченківський'}

def in_ring(la, lo, ring):
    """чи точка всередині багатокутника (промінь праворуч)"""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        yi, xi = ring[i]; yj, xj = ring[j]
        if (yi > la) != (yj > la):
            xx = xi + (la - yi) * (xj - xi) / ((yj - yi) or 1e-12)
            if lo < xx: inside = not inside
        j = i
    return inside

# людські назви факторів для короткої підказки "чому"
def why_text(facs):
    seen, out = set(), []
    for n, c in facs:
        if c <= 0: continue
        base = n.split('_')[0].split(' ×')[0]
        if base in seen or base in ('смуг', 'клас', 'довжина', 'звивистість'): continue
        seen.add(base); out.append(base)
        if len(out) == 3: break
    return ', '.join(out)

# invariant-genitive описувачі теми для заголовка перекосу (п.7.3). Свідомо не
# відмінюємо за числівником (1/2-4/5+) — ризик граматичної помилки вищий за
# користь; читається нормально для будь-якої кількості.
THEME_SKEW = {
 'ГП': 'громадського порядку', 'АЛК': "пов'язаних з алкоголем", 'НАР': 'наркотичних',
 'НАС': 'насильства', 'МАЙ': 'майнових', 'ДОР': 'дорожніх', 'СЕР': 'середовища громади',
}

def main(district=None, mode='full', out=None):
    if not os.path.exists(DB): print('спочатку кроки 1 і 2'); sys.exit(1)
    c = sqlite3.connect(DB)
    if not c.execute("SELECT name FROM sqlite_master WHERE name='geo'").fetchone():
        print('немає таблиці geo — крок 2 не відпрацював'); sys.exit(1)

    extra = {}
    for fp in glob.glob(os.path.join(DATA, 'kyiv_*.csv')):
        with open(fp, encoding='utf-8-sig') as fh:
            for r in csv.DictReader(fh, delimiter='\t'):
                extra[r['doc_id']] = (r['cause_num'], r['doc_url'])

    rows = list(c.execute("""SELECT e.doc_id,e.court,e.cat,e.date,e.tm,e.street,e.house,
        g.lat,g.lon,g.precision FROM events e JOIN geo g ON g.doc_id=e.doc_id"""))
    print(f'подій з координатами: {len(rows):,}')
    if not rows: return

    print('перевірка на адреси установ:')
    excl = detect_institutional(rows, load_excl())
    before = len(rows)
    rows = [r for r in rows
            if ((r[5] + ', ' + r[6]) if (r[5] and r[6]) else (r[5] or '')).lower() not in excl]
    print(f'   вилучено подій: {before - len(rows):,}  ->  залишилось {len(rows):,}')

    # ---- злиття кодів у назви ----
    cnt = collections.Counter()
    for r in rows:
        lb = L.CODE.get(r[2])
        if lb: cnt[lb] += 1
        else: cnt[('СЕР', 'інші (код ' + r[2] + ')')] += 1

    labels = sorted(cnt, key=lambda k: (L.ORDER.index(k[0]) if k[0] in L.ORDER else 9, -cnt[k]))
    li = {k: i for i, k in enumerate(labels)}
    ck = sorted({r[1] for r in rows}); ci = {v: i for i, v in enumerate(ck)}

    yc = collections.Counter(r[3][:4] for r in rows)
    yrs = sorted(y for y, n in yc.items() if n >= 200 and y.isdigit())
    ykeys = yrs + (['раніше'] if sum(n for y, n in yc.items() if y not in yrs) else [])
    yi = {y: i for i, y in enumerate(ykeys)}
    print('роки:', ', '.join(ykeys))
    print(f'статей після злиття: {len(labels)} (було би {len({r[2] for r in rows})} за кодами)')

    # група подібності (п.7.2) для кожного індексу в `labels`
    LBL2SIM = {}
    for _code, (_th, _lbl) in L.CODE.items():
        LBL2SIM[(_th, _lbl)] = L.SIMGROUP.get(_code, f'{_th}_{_code}')
    sim_of = [LBL2SIM.get(k, f'{k[0]}_i{i}') for i, k in enumerate(labels)]

    agg = collections.defaultdict(list)
    for doc, court, cat, date, tm, street, house, la, lo, prec in rows:
        lb = L.CODE.get(cat) or ('СЕР', 'інші (код ' + cat + ')')
        agg[(round(la, 5), round(lo, 5))].append(
            (ci[court], li[lb], yi.get(date[:4], yi.get('раніше', 0)),
             int(tm[:2]) if tm and tm[:2].isdigit() else -1,
             1 if prec == 'house' else 0, date, street or '', house or '',
             *extra.get(doc, ('', ''))))

    P = []
    for (la, lo), evs in agg.items():
        a = next((f"{e[6]}, {e[7]}" if e[7] else e[6] for e in evs if e[6]), '')
        P.append([la, lo, a, evs[0][4],
                  [[e[0], e[1], e[2], e[3]] for e in evs],
                  [[e[1], e[5], e[3], e[8], e[9]] for e in sorted(evs, key=lambda x: x[5], reverse=True)[:6]]])
    print(f'унікальних адрес: {len(P):,}')

    groups_idx = {}
    for ti, t in enumerate(L.ORDER):
        for i, k in enumerate(labels):
            if k[0] == t: groups_idx[i] = ti
    groups = []
    gi_of_theme = {}       # код теми -> її індекс у meta['groups'] (для фільтрації карток)
    for t in L.ORDER:
        ids = [li[k] for k in labels if k[0] == t]
        if ids:
            gi_of_theme[t] = len(groups)
            groups.append([L.THEMES[t], ids, sum(cnt[labels[i]] for i in ids)])
    meta = dict(courts=[COURTS.get(x, x) for x in ck], cats=[k[1] for k in labels],
                counts=[cnt[k] for k in labels], groups=groups, years=ykeys)

    # ---- шари контексту: ризик, потоки ----
    risks = {'lines': {}}
    if os.path.exists(NETW):
        nw = json.load(open(NETW, encoding='utf-8'))
        it = nw.get('items', [])
        FLOWS = [('flow_school', 3, 'Потік до шкіл і садків', '07:30–08:30, 12:00–14:00'),
                 ('flow_transit', 4, 'Потік до транспорту', 'години пік'),
                 ('flow_shop', 5, 'Потік до торгівлі', 'день, рівномірно')]
        # На РАЙОННІЙ карті показуємо ВСІ ненульові потоки — інакше тихі квартали
        # виглядають порожніми, хоча потік там є (перевірено на вул. Кадетський Гай:
        # потік до торгівлі 202, але 3287-е місце по місту -> не потрапляв у топ).
        # На єдиній міській карті ліміт лишається, бо інакше вона нечитабельна.
        FLOW_CAP = None if district else 2500
        for key, idx, title, when in FLOWS:
            vals = [x for x in it if len(x) > idx and x[idx] > 0]
            if not vals: continue
            vals.sort(key=lambda x: -x[idx])
            top = vals if FLOW_CAP is None else vals[:FLOW_CAP]
            risks.setdefault('lines', {})[key] = {
                'title': title, 'when': when,
                'items': [[x[0], x[1], int(x[idx])] for x in top]}
            print(f'   {title}: {len(top):,} відрізків з {len(vals):,}')
    else:
        print('шар потоків відсутній (запустіть 2c-NETWORK) — карта буде без нього')

    ER = {}
    erp = os.path.join(DATA, 'engine_report.json')
    if os.path.exists(erp):
        ER = json.load(open(erp, encoding='utf-8'))

    # ---- шар ризику: ОДНЕ читання risk.json дає і клікабельні лінії на карті (п.7.5),
    # і сітку для пошуку "чи адреса на ризикованій вулиці" в аналізі картки (п.7.4) ----
    theme_rgrid = {}          # тема -> {(ci,cj): [(la,lo,pc)]}
    RC = 0.0025
    if os.path.exists(RISKF):
        RK = json.load(open(RISKF, encoding='utf-8'))
        for th, v in RK.get('layers', {}).items():
            it = sorted(v['items'], key=lambda x: -x[2])
            if not it: continue
            top = it[:600]
            n = len(top)
            gi = [i for i, t in enumerate(L.ORDER) if t == th]
            grid = collections.defaultdict(list)
            items_out = []
            for i, x in enumerate(top):
                pc = int(100 * (n - i) / n)
                items_out.append([x[0], x[1] or 'без назви', pc])
                for pnt in x[0]:
                    grid[(int(pnt[0]/RC), int(pnt[1]/RC))].append((pnt[0], pnt[1], pc))
            theme_rgrid[th] = grid
            d = ER.get(th, {})
            method = ''
            if d:
                method = (f"Модель навчена на {d.get('навчання', 0):,} подіях 2024 року, "
                          f"перевірена на {d.get('перевірка', 0):,} подіях 2025–2026. "
                          f"У верхніх 10% вулиць за прогнозом опиняється "
                          f"{100*d.get('hit_середовище', 0):.0f}% подій наступних років "
                          f"(у {d.get('PAI_середовище', 0)} рази краще за випадковий відбір).").replace(',', ' ')
            risks.setdefault('lines', {})['risk_' + th] = {
                'title': L.THEMES.get(th, th),
                'hit': int(100 * v['hit']),
                'theme': gi[0] if gi else 0,
                'why': why_text(ER.get(th, {}).get('фактори', [])),
                'factors': [[n_, round(float(c_), 3)] for n_, c_ in ER.get(th, {}).get('фактори', []) if c_ > 0][:12],
                'method': method,
                'items': items_out}
        dg = RK.get('danger', [])
        if dg:
            print(f'небезпечні підходи до шкіл: {len(dg)}')

    # Панель «Прогноз ризику» має перелічувати ТІ САМІ теми, що й «Правопорушення».
    # Для тем, де подій замало на навчання (поріг MIN_EV у кроці 4 — 250 подій
    # навчального року), модель не будується. Раніше такі теми просто зникали з
    # панелі, і виглядало це як розсинхрон назв. Тепер показуємо їх окремим рядком.
    for _i, _th in enumerate(L.ORDER):
        if _th == 'ДОМ': continue                       # домашнє насильство на карту не йде
        if ('risk_' + _th) in risks.get('lines', {}): continue
        if not any(k[0] == _th for k in labels): continue
        risks.setdefault('lines', {})['risk_' + _th] = {
            'title': L.THEMES.get(_th, _th), 'hit': 0, 'theme': _i,
            'why': '', 'factors': [], 'method': '', 'items': [], 'nodata': True}

    def pred_theme(th, la, lo, rad=180.0):
        g = theme_rgrid.get(th)
        if not g: return 0
        my = 111320.0; mx = 111320.0 * math.cos(math.radians(la))
        ci_, cj_ = int(la/RC), int(lo/RC); best = 0
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for pa, po, pc in g.get((ci_+di, cj_+dj), ()):
                    if pc > best and math.hypot((pa-la)*my, (po-lo)*mx) <= rad: best = pc
        return best

    POP = []

    # ---- ВІДБІР ПРОБЛЕМ (п.7.1–7.4): інцидент / проблема. «Проблема» = членство
    # в кураторському списку ~50 адрес-напрямків. Кілька напрямків на одній
    # адресі, що подолали поріг, — кілька окремих проблем (розд.6 передачі). ----
    CORE = {'ГП', 'АЛК', 'НАР', 'НАС', 'МАЙ', 'ДОР', 'СЕР'}   # усе, крім домашнього насильства

    ALL_BORDERS = {}
    if os.path.exists(BORD):
        ALL_BORDERS = json.load(open(BORD, encoding='utf-8'))

    def addr_district(la, lo):
        for d, ring in ALL_BORDERS.items():
            if in_ring(la, lo, ring): return d
        return None

    candidates = []
    for pi, p in enumerate(P):
        by_sim = collections.defaultdict(lambda: [0, set(), collections.Counter()])
        core_n = 0
        for e in p[4]:
            th, lbl = labels[e[1]]
            if th not in CORE: continue
            core_n += 1
            sim = sim_of[e[1]]
            rec = by_sim[sim]
            rec[0] += 1
            rec[1].add(ykeys[e[2]] if e[2] < len(ykeys) else 'раніше')
            rec[2][lbl] += 1
        if not by_sim: continue
        dist = addr_district(p[0], p[1])
        for sim, (n, yrs, arts) in by_sim.items():
            if n < MIN_EPISODES: continue
            th = sim.split('_', 1)[0]
            score = n * (1 + 0.15 * len(yrs))
            candidates.append(dict(pi=pi, sim=sim, th=th, n=n, core_n=core_n,
                                    district=dist, years=sorted(yrs),
                                    arts=arts.most_common(), score=score))
    candidates.sort(key=lambda c: -c['score'])

    chosen = {}
    used_theme = collections.Counter()   # спільний лічильник квоти по темах (п.7.3, за проханням користувача)

    def try_take(c):
        cap = CAP_THEME.get(c['th'], CAP_DEFAULT)
        if used_theme[c['th']] >= cap: return False
        key = (c['pi'], c['sim'])
        if key in chosen: return False
        chosen[key] = c; used_theme[c['th']] += 1
        return True

    for d in ALL_BORDERS:
        got = 0
        for c in candidates:
            if got >= GUARANTEE: break
            if c['district'] != d: continue
            if try_take(c): got += 1
    got = 0
    for c in candidates:
        if got >= CITYWIDE: break
        if try_take(c): got += 1

    problems = sorted(chosen.values(), key=lambda c: -c['score'])
    skew = collections.Counter(c['th'] for c in problems)
    skew_txt = ''
    if problems:
        parts = [f"{n} {THEME_SKEW.get(t, L.THEMES.get(t, t))}" for t, n in skew.most_common()]
        skew_txt = f"З {len(problems)} відібраних проблем: " + ', '.join(parts) + '.'
    print(f'   відібрано проблем: {len(problems)} з {len(candidates)} кандидатів (поріг {MIN_EPISODES} епізодів)')
    if skew_txt: print('   ' + skew_txt)

    probs_by_pi = collections.defaultdict(list)
    for c in problems:
        th = c['th']
        risk_pc = pred_theme(th, P[c['pi']][0], P[c['pi']][1])
        d = ER.get(th, {})
        analysis = None
        if risk_pc > 0 and d:
            analysis = dict(pc=risk_pc, hit=round(100*d.get('hit_середовище', 0)),
                             factors=[[n_, round(float(w), 3)] for n_, w in d.get('фактори', []) if w > 0][:8],
                             train=d.get('навчання', 0), test=d.get('перевірка', 0))
        probs_by_pi[c['pi']].append(dict(
            thi=gi_of_theme.get(th, -1),   # індекс теми — щоб картка ховалась разом із фільтром
            sim=c['sim'], theme=L.THEMES.get(th, th), mech=L.GROUPNAME.get(c['sim'], c['sim']),
            n=c['n'], core_n=c['core_n'], years=c['years'], arts=c['arts'],
            analysis=analysis))

    for pi, p in enumerate(P):
        probs = probs_by_pi.get(pi, [])
        p.append(2 if probs else 0)     # кат.: 0 інцидент, 2 проблема (п.7.1)
        p.append(probs)

    pp2 = os.path.join(DATA, 'population.json')
    if os.path.exists(pp2):
        POP = [[x[0], x[1], x[2]] for x in json.load(open(pp2, encoding='utf-8'))['items'] if x[2] > 30]
        print(f'населення: {len(POP):,} комірок')

    meta['skew'] = skew_txt
    meta['n_problems'] = len(problems)

    if district:
        ring = ALL_BORDERS.get(district)
        if ring:
            # ГЕОГРАФІЧНЕ обрізання: лишаємо тільки те, що фізично в межах району
            before = len(P)
            P = [p for p in P if in_ring(p[0], p[1], ring)]
            print(f'   район {district}: {len(P):,} адрес (за межами відсіяно {before-len(P):,})')
            for k, v in list(risks.get('lines', {}).items()):
                v['items'] = [x for x in v['items']
                              if any(in_ring(q[0], q[1], ring) for q in x[0])]
                if not v['items'] and not v.get('nodata'): risks['lines'].pop(k, None)
            POP = [x for x in POP if in_ring(x[0], x[1], ring)]
            la_ = [q[0] for q in ring]; lo_ = [q[1] for q in ring]
            meta['bounds'] = [[min(la_), min(lo_)], [max(la_), max(lo_)]]
            meta['border'] = ring
        else:
            keep = {i for i, c in enumerate(ck) if COURTS.get(c, c) == district}
            P = [p for p in P if any(e[0] in keep for e in p[4])]
            for p in P: p[4] = [e for e in p[4] if e[0] in keep]
            P = [p for p in P if p[4]]
            print(f'   район {district}: {len(P):,} адрес (за судом — межі не завантажені)')
        meta['courts'] = [COURTS.get(x, x) for x in ck]
        meta['only'] = district
        if P and 'bounds' not in meta:
            meta['center'] = [round(sum(x[0] for x in P)/len(P), 5),
                              round(sum(x[1] for x in P)/len(P), 5)]
    meta['mode'] = mode
    if mode == 'student':
        for k in list(risks.get('lines', {})):
            if k.startswith('risk_'):
                risks['lines'][k]['why'] = ''
                risks['lines'][k]['factors'] = []
                risks['lines'][k]['method'] = ''
        for p in P:
            if len(p) > 6: p[6] = -1        # категорію приховуємо
            if len(p) > 7: p[7] = []         # і розбір причини — теж (розд.6 передачі)
        meta['skew'] = ''
    html = TPL.replace('__POP__', json.dumps(POP, separators=(',', ':'))) \
              .replace('__RISKS__', json.dumps(risks, ensure_ascii=False, separators=(',', ':'))) \
              .replace('__META__', json.dumps(meta, ensure_ascii=False)) \
              .replace('__PTS__', json.dumps(P, ensure_ascii=False, separators=(',', ':')))
    dst = out or OUT
    os.makedirs(os.path.dirname(dst) or '.', exist_ok=True)
    open(dst, 'w', encoding='utf-8').write(html)
    print(f'готово: {os.path.basename(dst)} ({os.path.getsize(dst)/1048576:.1f} МБ)')

TPL = r"""<!DOCTYPE html><html lang="uk"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Карта правопорушень Києва</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>
<style>
*{box-sizing:border-box}html,body{margin:0;height:100%;font:13.5px/1.45 system-ui,sans-serif;background:#0f1117;color:#e8eaf0}
#wrap{display:flex;height:100%}
#side{width:330px;flex:0 0 330px;overflow-y:auto;padding:14px;background:#161922;border-right:1px solid #252a37}
#map{flex:1}h1{font-size:15px;margin:0 0 2px}.sub{color:#79839a;font-size:11.5px}
#cnt{font-size:26px;font-weight:600;margin:12px 0 0;letter-spacing:-.02em}
fieldset{border:0;border-top:1px solid #252a37;padding:11px 0 3px;margin:10px 0 0}
legend{font-size:10.5px;text-transform:uppercase;letter-spacing:.09em;color:#79839a}
label{display:flex;gap:7px;align-items:flex-start;padding:2.5px 0;cursor:pointer}
input[type=checkbox]{accent-color:#e0533d;width:14px;height:14px;margin-top:2px;flex:0 0 auto}
button{width:100%;padding:8px;background:#1f2432;color:#e8eaf0;border:1px solid #303747;border-radius:6px;font:inherit;cursor:pointer;margin-top:7px}
button:hover{background:#28303f}button.act{background:#e0533d;border-color:#e0533d;color:#fff}
.th{font-size:10.5px;text-transform:uppercase;letter-spacing:.07em;color:#5f6878;margin:9px 0 2px}
#hr{display:grid;grid-template-columns:1fr 1fr;gap:5px}
#hr span{padding:7px 4px;background:#1f2432;border-radius:6px;font-size:12px;cursor:pointer;
 user-select:none;text-align:center;line-height:1.15;transition:background .12s}
#hr span:hover{background:#28303f}
#hr span i{display:block;font-style:normal;font-size:10px;color:#6d7789;margin-top:1px}
#hr span.on{background:#e0533d;color:#fff}#hr span.on i{color:#ffd9d0}
#top{margin-top:6px}
#top div{display:flex;justify-content:space-between;gap:8px;padding:5px 7px;background:#1c212c;border-radius:5px;margin-bottom:3px;cursor:pointer;font-size:12.5px}
#top div:hover{background:#252c3a}#top b{color:#e0533d;flex:0 0 auto}
.gr{margin-bottom:2px}
.gh{display:flex;align-items:center;gap:7px;padding:5px 6px;background:#1c212c;border-radius:5px;cursor:pointer;user-select:none}
.gh:hover{background:#232a37}.gh .nm{flex:1;font-size:12.5px}
.gh .n{color:#79839a;font-size:11px}.gh .ar{color:#5f6878;font-size:10px;width:9px}
.gb{display:none;padding:4px 0 6px 22px}.gr.open .gb{display:block}
.gr.open .ar{transform:rotate(90deg)}.ar{display:inline-block;transition:transform .12s}
.gb label{font-size:12px;color:#c4cbd8}.gb .n{color:#5f6878;font-size:10.5px;margin-left:auto;flex:0 0 auto}
.hint{font-size:11px;color:#5f6878;margin-top:7px;line-height:1.4}
#fr label,#frisk label,#fctx label{font-size:12px}
#fr .n,#frisk .n,#fctx .n{color:#5f6878;font-size:10.5px;margin-left:auto;flex:0 0 auto}
#fr .sw,#frisk .sw,#fctx .sw{width:9px;height:9px;border-radius:2px;flex:0 0 auto}
#fcat{display:grid;grid-template-columns:1fr 1fr;gap:5px}
#fcat span{padding:7px 5px;background:#1f2432;border-radius:6px;font-size:12px;cursor:pointer;
 user-select:none;text-align:center;line-height:1.15;transition:background .12s;position:relative}
#fcat span:hover{background:#28303f}
#fcat span i{display:block;font-style:normal;font-size:10px;color:#6d7789;margin-top:1px}
#fcat span.on{background:#2b3243;box-shadow:inset 0 0 0 1.5px currentColor}
#fcat span.c2{color:#f87171}#fcat span.cA{color:#a8b2c4}
.skew{font-size:11.5px;color:#c4cbd8;background:#1c2230;border-left:3px solid #e0533d;
 border-radius:5px;padding:7px 9px;margin-top:9px;line-height:1.4}
.env{margin:8px 0 0}
.env .eh{font-size:10px;text-transform:uppercase;letter-spacing:.07em;color:#8b95a8;margin-bottom:4px}
.dirs{margin:7px 0}.dirs .row{display:flex;gap:7px;align-items:center;font-size:11.5px;margin-bottom:3px}
.dirs .bar2{flex:1;height:4px;background:#232838;border-radius:2px;overflow:hidden}
.dirs .bar2 i{display:block;height:100%;background:#e0533d}
.miss{font-size:11px;color:#8b95a8;background:#1a2030;border-left:2px solid #3b82f6;
 padding:5px 8px;border-radius:4px;margin-top:7px}
.cbadge{display:inline-block;padding:1px 7px;border-radius:99px;font-size:10.5px;
 text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px}
#fr .rh{font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;color:#5f6878;margin:9px 0 2px}
/* ---- прогноз ризику ---- */
#frisk .rw{margin-bottom:5px;border-radius:6px;background:#1a1f2a;padding:6px 8px;
  border-left:3px solid transparent;transition:background .12s}
#frisk .rw:hover{background:#212836}
#frisk .rl{display:flex;align-items:center;gap:7px;cursor:pointer}
#frisk .nm{flex:1;font-size:12.5px;line-height:1.2}
#frisk .acc{font-size:10px;color:#7c8698;padding:1px 5px;border:1px solid #333c4d;border-radius:99px}
#frisk .why{font-size:10.5px;color:#6d7789;margin:3px 0 0 22px;line-height:1.35}
#frisk .rw.nod{opacity:.5}#frisk .rw.nod .rl{cursor:default}
.lgd{display:flex;align-items:center;gap:6px;font-size:10px;color:#5f6878;margin-top:8px}
.lgd i{height:3px;flex:1;border-radius:2px;background:linear-gradient(90deg,#5f6878 0%,currentColor 100%)}
.leaflet-popup-content-wrapper{background:#161922;color:#e8eaf0;border-radius:8px}
.leaflet-popup-tip{background:#161922}
.leaflet-tooltip.rt{background:#161922;border:1px solid #2c3444;color:#e8eaf0;
  font:12px system-ui;border-radius:6px;box-shadow:0 4px 16px rgba(0,0,0,.5);padding:6px 9px}
.leaflet-tooltip.rt:before{display:none}
.leaflet-tooltip.rt b{display:block;margin-bottom:2px}
.leaflet-tooltip.rt span{color:#8b95a8;font-size:11px}
/* висота в частках екрана, інакше висока картка вилазить за верх вікна */
.lp{font-size:12.5px;max-height:min(420px,58vh);overflow-y:auto;overscroll-behavior:contain}
.lp b{display:block;margin-bottom:5px;font-size:13px}
.lp a{color:#c94a34;text-decoration:none}.lp a:hover{text-decoration:underline}
.lp li{margin-bottom:4px;font-size:11.5px}.lp ul{padding-left:15px;margin:3px 0}
.lp .tt{color:#79839a;font-size:11.5px;margin-bottom:7px}
.bd{width:100%;border-collapse:collapse;margin-bottom:8px}
.bd td{padding:2px 0;font-size:12px;vertical-align:top}
.bd td:last-child{text-align:right;padding-left:10px;color:#e0533d;width:44px}
.hg{display:flex;align-items:flex-end;gap:1px;height:24px;margin:2px 0 1px}
.hg i{flex:1;background:#e0533d;opacity:.8;border-radius:1px 1px 0 0}
.hx{display:flex;justify-content:space-between;font-size:9.5px;color:#5f6878;margin-bottom:5px}
.hn{font-size:11px;color:#c4cbd8;background:#232a37;padding:4px 7px;border-radius:4px;margin-bottom:7px}
.pcard{background:#1c2230;border-left:3px solid #f87171;border-radius:5px;padding:8px 9px;margin:8px 0}
.pcard .ph{font-size:10px;text-transform:uppercase;letter-spacing:.07em;color:#8b95a8;margin-bottom:3px}
.pcard .pt{font-size:13px;font-weight:600;margin-bottom:5px;line-height:1.25}
.pcard .pm{font-size:11.5px;color:#c4cbd8;margin-bottom:2px}
.pcard .pm b{color:#e8eaf0}
.pcard .pf{font-size:10.5px;color:#6d7789;margin-top:4px;line-height:1.4}
.pcard .why{font-size:11px;color:#c4cbd8;background:#161c28;border-radius:4px;padding:6px 8px;margin-top:5px}
.pbtn{width:100%;padding:7px;background:#e0533d;color:#fff;border:0;border-radius:6px;
 font:inherit;font-size:12px;cursor:pointer;margin-top:7px}
.pbtn:hover{background:#c94a34}
.ex{font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;color:#5f6878;margin-top:6px}
.rpop b{display:block;margin-bottom:4px;font-size:13px}
.rpop .rmeth{font-size:11px;color:#8b95a8;margin:6px 0;line-height:1.4}
.rpop table{width:100%;border-collapse:collapse;margin-top:4px}
.rpop td{padding:1.5px 0;font-size:11px}
.rpop td:last-child{text-align:right;color:#e0533d}
@media(max-width:760px){#wrap{flex-direction:column}#side{width:100%;flex:0 0 auto;max-height:50%}}
</style></head><body><div id="wrap"><div id="side">
<h1>Карта правопорушень</h1><div class="sub" id="subt">за даними ЄДРСР · місто Київ</div>
<div id="backl"></div>
<div id="skew"></div>
<div id="cnt">0</div><div class="sub" id="cntl"></div>
<button id="heat">Теплова карта</button><button id="reset">Скинути фільтри</button>
<fieldset><legend>Що показувати</legend><div id="fcat"></div>
<div class="hint" id="cathint"></div></fieldset>
<fieldset><legend>Топ адрес за фільтром</legend><div id="top"></div></fieldset>
<fieldset><legend>Район</legend><div id="fc"></div></fieldset>
<fieldset><legend>Правопорушення</legend>
<div style="display:flex;gap:6px"><button id="none" style="margin:0 0 8px">Зняти всі</button>
<button id="all" style="margin:0 0 8px">Обрати всі</button></div><div id="fa"></div></fieldset>
<fieldset><legend>Прогноз ризику</legend><div id="frisk"></div>
<div class="hint">Модель оцінює <b>кожну вулицю</b> за умовами середовища, незалежно від того, чи були там події. Клікніть на вулицю — розбір чинників і методики відкриється в спливному вікні. У кружечку — влучність: яка частка подій наступних років припала на верхні 10% відібраних вулиць.</div>
</fieldset>
<fieldset><legend>Контекст</legend><div id="fctx"></div>
<div class="hint">Населення — фон під картою, за даними Kontur (комірки 400 м). Потоки — модельовані пішохідні маршрути від житла до цілей, з урахуванням населення. Товщина = кількість людей.</div></fieldset>
<fieldset><legend>Рік</legend><div id="fy"></div></fieldset>
<fieldset><legend>Час доби</legend><div id="hr"></div>
<div class="hint">Порожній вибір = усі. Розмір кола = кількість подій за адресою. Сірі кола — прив'язка лише до вулиці, без номера будинку.</div></fieldset>
</div><div id="map"></div></div>
<script>
const M=__META__, P=__PTS__;
const PALA=['#e0533d','#e8a33d','#8b5cf6','#ef4444','#3b82f6','#22c55e','#14b8a6'];
const CATTH={};M.groups.forEach((g,gi)=>g[1].forEach(i=>CATTH[i]=gi));
const R=__RISKS__, POP=__POP__;
const map=L.map('map',{preferCanvas:true}).setView(M.center||[50.45,30.52],M.only?13:11);
map.createPane('popPane'); map.getPane('popPane').style.zIndex=350;
map.createPane('maskPane'); map.getPane('maskPane').style.zIndex=345;
if(M.bounds){
 const b=L.latLngBounds(M.bounds);
 map.fitBounds(b,{padding:[24,24]});
 // за межі району не випускаємо: запас ~10% від розміру району
 const dy=(M.bounds[1][0]-M.bounds[0][0])*0.10, dx=(M.bounds[1][1]-M.bounds[0][1])*0.10;
 const lim=L.latLngBounds([M.bounds[0][0]-dy,M.bounds[0][1]-dx],
                          [M.bounds[1][0]+dy,M.bounds[1][1]+dx]);
 map.setMaxBounds(lim);
 map.setMinZoom(map.getBoundsZoom(lim));
}
if(M.border){
 // затемнення всього поза межами району: великий прямокутник з "дірою" по контуру
 const W=[[-85,-360],[-85,360],[85,360],[85,-360]];
 L.polygon([W,M.border],{pane:'maskPane',color:'#0f1117',weight:0,
   fillColor:'#0f1117',fillOpacity:.82,interactive:false}).addTo(map);
 L.polygon(M.border,{color:'#6b7890',weight:1.8,opacity:.9,
   fill:false,dashArray:'6,5',interactive:false}).addTo(map);
}
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
{attribution:'&copy; OpenStreetMap, CARTO',maxZoom:19}).addTo(map);
let layer=L.layerGroup().addTo(map),heat=null,heatOn=false;
const rlayer=L.layerGroup().addTo(map);
const poplayer=L.layerGroup();          // фон під усім іншим
const RCOL={metro:'#38bdf8',busstop:'#7dd3fc',
 flow_school:'#fbbf24',flow_transit:'#38bdf8',flow_shop:'#f472b6'};
// ризик успадковує колір своєї теми — той самий, що в подіях
Object.keys(R.lines||{}).forEach(k=>{if(k.startsWith('risk_'))RCOL[k]=PALA[(R.lines[k].theme||0)%7]});;
if(M.skew) $ify('#skew', `<div class="skew">${M.skew}</div>`);
function $ify(sel,html){const el=document.querySelector(sel);if(el)el.innerHTML=html}
{
 // --- прогноз ризику ---
 let rh='';
 const rkeys=Object.keys(R.lines||{}).filter(k=>k.startsWith('risk_'))
   .sort((a,b)=>R.lines[b].hit-R.lines[a].hit);
 rkeys.forEach(k=>{const v=R.lines[k],c=RCOL[k];
  if(v.nodata){
   // тема є в списку правопорушень, але подій замало на навчання моделі
   rh+=`<div class="rw nod" style="border-left-color:#3a4256">
    <label class="rl"><input type="checkbox" disabled>
     <span class="sw" style="background:#3a4256"></span>
     <span class="nm">${v.title}</span>
     <span class="acc">—</span></label>
    <div class="why">замало подій для навчання моделі</div></div>`;
   return}
  rh+=`<div class="rw" style="border-left-color:${c}">
   <label class="rl"><input type="checkbox" data-r="${k}">
    <span class="sw" style="background:${c}"></span>
    <span class="nm">${v.title}</span>
    <span class="acc">${v.hit}%</span></label>
   ${v.why?`<div class="why">${v.why}</div>`:''}</div>`});
 if(rkeys.length) rh+=`<div class="lgd" style="color:${RCOL[rkeys[0]]}"><span>менший</span><i></i><span>більший</span></div>`;
 $ify('#frisk',rh);

 // --- контекст ---
 let ch='';
 if(POP.length) ch+=`<label><input type="checkbox" data-r="pop">
   <span class="sw" style="background:#3b4a63"></span><span>Щільність населення</span>
   <span class="n">${POP.length.toLocaleString('uk')}</span></label>`;
 ['flow_school','flow_transit','flow_shop'].forEach(k=>{const v=R.lines&&R.lines[k];if(!v)return;
  ch+=`<label><input type="checkbox" data-r="${k}">
   <span class="sw" style="background:${RCOL[k]}"></span><span>${v.title}</span>
   <span class="n">${v.items.length.toLocaleString('uk')}</span></label>`});
 $ify('#fctx',ch);
}
function riskPopup(k,it){
 const v=R.lines[k];
 let h=`<div class="rpop"><b>${it[1]}</b><span class="sub">${v.title} — верхні ${101-it[2]}% за ризиком</span>`;
 if(v.method) h+=`<div class="rmeth">${v.method}</div>`;
 if(v.factors&&v.factors.length){
  h+='<table>'+v.factors.map(f=>`<tr><td>${f[0]}</td><td>+${f[1]}</td></tr>`).join('')+'</table>';
 }
 h+='</div>';
 return h;
}
function drawRisks(){
 rlayer.clearLayers();
 const pc=document.querySelector('[data-r="pop"]');
 if(pc&&pc.checked){
  if(!map.hasLayer(poplayer)){
   if(!poplayer.getLayers().length){
    const mx=Math.max(...POP.map(p=>p[2]));
    POP.forEach(p=>L.circleMarker([p[0],p[1]],{pane:'popPane',
      radius:5+16*Math.sqrt(p[2]/mx),weight:0,fillColor:'#4b6fa8',
      fillOpacity:.10+.28*Math.sqrt(p[2]/mx)})
      .bindTooltip(`${p[2].toLocaleString('uk')} осіб`,{className:'rt',sticky:true})
      .addTo(poplayer));
   }
   poplayer.addTo(map); poplayer.bringToBack();
  }
 } else map.removeLayer(poplayer);

 document.querySelectorAll('[data-r]').forEach(cb=>{
  if(!cb.checked||cb.dataset.r==='pop') return;
  const k=cb.dataset.r, col=RCOL[k];
  if(!(R.lines&&R.lines[k])) return;
  const isRisk=k.startsWith('risk_'), v=R.lines[k];
  if(isRisk){
   // п.7.5: без теплового світіння (блокувало кліки) — самі лінії, товщі й клікабельні
   v.items.forEach(it=>
     L.polyline(it[0],{color:col,weight:Math.max(2,1.5+it[2]/16),
       opacity:Math.max(.35,.85*it[2]/100)})
      .bindTooltip(`<b>${it[1]}</b><span>${v.title} — верхні ${101-it[2]}% за ризиком, клікніть для деталей</span>`,
        {className:'rt',sticky:true})
      .on('click',ev=>{L.popup({maxWidth:320}).setLatLng(ev.latlng)
        .setContent(riskPopup(k,it)).openOn(map)})
      .addTo(rlayer));
  } else {
   const mxf=Math.max(...v.items.map(x=>x[2]))||1;
   v.items.forEach(it=>
    L.polyline(it[0],{color:col,weight:Math.max(1.5,1+5*Math.sqrt(it[2]/mxf)),
      opacity:Math.max(.25,.75*Math.sqrt(it[2]/mxf))})
     .bindTooltip(`<b>${it[1]||'без назви'}</b><span>${v.title} — ~${it[2].toLocaleString('uk')} осіб</span>`+
       (v.when?`<span>${v.when}</span>`:''),{className:'rt',sticky:true}).addTo(rlayer));
  }
 });
}
const $=s=>document.querySelector(s);
if(M.only){$('#subt').textContent=M.only+' район · за даними ЄДРСР';
 $('#backl').innerHTML='<a href="index.html" style="color:#e0533d;font-size:12px;text-decoration:none">← всі райони</a>';}
$('#fc').innerHTML=M.courts.map((n,i)=>`<label><input type="checkbox" data-c="${i}" checked>${n}</label>`).join('');
$('#fy').innerHTML=M.years.map((n,i)=>`<label><input type="checkbox" data-y="${i}" checked>${n}</label>`).join('');
const fmt=n=>n.toLocaleString('uk');
$('#fa').innerHTML=M.groups.map((g,gi)=>`<div class="gr" data-g="${gi}">
<div class="gh"><span class="ar">&#9656;</span><input type="checkbox" class="gt" data-gt="${gi}" checked>
<span class="nm">${g[0]}</span><span class="n">${fmt(g[2])}</span></div>
<div class="gb">`+g[1].map(i=>`<label><input type="checkbox" data-a="${i}" checked>
<span>${M.cats[i]}</span><span class="n">${fmt(M.counts[i])}</span></label>`).join('')+
`</div></div>`).join('');
document.querySelectorAll('.gh').forEach(el=>el.onclick=e=>{
 if(e.target.tagName==='INPUT')return; el.parentElement.classList.toggle('open')});
document.querySelectorAll('.gt').forEach(el=>el.onchange=()=>{
 M.groups[+el.dataset.gt][1].forEach(i=>{const b=document.querySelector(`[data-a="${i}"]`);if(b)b.checked=el.checked});
 draw()});
function syncThemes(){document.querySelectorAll('.gt').forEach(el=>{
 const ids=M.groups[+el.dataset.gt][1], on=ids.filter(i=>document.querySelector(`[data-a="${i}"]`).checked).length;
 el.checked=on>0; el.indeterminate=on>0&&on<ids.length})}
const PERIODS=[['Ранок','6–11',[6,7,8,9,10,11]],['День','12–17',[12,13,14,15,16,17]],
 ['Вечір','18–23',[18,19,20,21,22,23]],['Ніч','0–5',[0,1,2,3,4,5]]];
const STUDENT = M.mode==='student';
// п.7.7: замість чотирьох кнопок категорій — лише "Усі" й "Тільки проблеми"
const CATS=STUDENT?[['Усі','подій ≥1','cA',-1]]
 :[['Усі','подій ≥1','cA',-1],['Тільки проблеми','з відібраних 50','c2',2]];
const cb_=$('#fcat');
CATS.forEach((c,i)=>{const sp=document.createElement('span');
 sp.className=c[2]+(i===0?' on':'');sp.innerHTML=`${c[0]}<i>${c[1]}</i>`;sp.dataset.c=c[3];cb_.appendChild(sp)});
cb_.onclick=e=>{const t=e.target.closest('[data-c]');if(!t)return;
 [...cb_.children].forEach(x=>x.classList.remove('on'));t.classList.add('on');draw()};
const CATNAME={2:['Проблема','#f87171','у кураторському списку'],0:null};
const hb=$('#hr');
PERIODS.forEach((p,i)=>{const s=document.createElement('span');
 s.innerHTML=`${p[0]}<i>${p[1]}</i>`;s.dataset.p=i;hb.appendChild(s)});
hb.onclick=e=>{const t=e.target.closest('[data-p]');if(t){t.classList.toggle('on');draw()}};
const sel=a=>new Set([...document.querySelectorAll(`[data-${a}]`)].filter(x=>x.checked).map(x=>+x.dataset[a]));
function buildPassport(p,pr){
 const today=new Date().toISOString().slice(0,10);
 let t=`# Паспорт проблеми (SARA)\n\n`;
 t+=`**Адреса:** ${p[2]||'не визначена'}\n`;
 t+=`**Механізм:** ${pr.mech}\n**Дата формування:** ${today}\n\n`;
 t+=`## Scanning\n\n`;
 t+=`- Подій за напрямком: **${pr.n}** (усього на адресі — ${pr.core_n})\n`;
 t+=`- Роки повторення: ${pr.years.join(', ')}\n`;
 t+=`- Склад: `+pr.arts.map(a=>`${a[0]} — ${a[1]}`).join('; ')+`\n\n`;
 t+=`## Analysis\n\n`;
 if(pr.analysis){
  t+=`Адреса потрапляє у верхні ${100-pr.analysis.pc}% вулиць за прогнозом моделі для цієї теми `+
     `(влучність моделі ${pr.analysis.hit}%, навчання на ${pr.analysis.train}, перевірка на ${pr.analysis.test} подіях).\n\n`;
  t+=`Чинники середовища:\n`+pr.analysis.factors.map(f=>`- ${f[0]} (вага ${f[1]})`).join('\n')+`\n\n`;
 } else {
  t+=`Модель не пояснює це скупчення умовами середовища — причину треба встановити на місці `+
     `(польовий підрахунок, опитування, огляд).\n\n`;
 }
 t+=`**Гіпотеза причини (заповнити на місці):**\n\n_____\n\n`;
 t+=`## Response\n\n**Тип втручання:** _____\n**Адресат:** _____\n**Горизонт:** _____\n\n`;
 t+=`## Assessment\n\n**Критерій спростування (як дізнатись, що не спрацювало):** _____\n\n`;
 t+=`**Дата повторної перевірки:** _____\n`;
 return t;
}
function downloadPassport(p,pr){
 const txt=buildPassport(p,pr);
 const blob=new Blob([txt],{type:'text/markdown;charset=utf-8'});
 const a=document.createElement('a');
 a.href=URL.createObjectURL(blob);
 a.download='pasport_'+(p[2]||'problema').replace(/[^a-zA-Zа-яА-ЯіїєІЇЄ0-9]+/g,'_').slice(0,60)+'.md';
 document.body.appendChild(a);a.click();document.body.removeChild(a);
}
window.__downloadPassport=downloadPassport;
function draw(){
 syncThemes();
 const C=sel('c'),A=sel('a'),Y=sel('y');
 // які теми зараз видимі за фільтром статей — картки проблем ховаються разом з ними,
 // інакше при фільтрі «Насильство» знизу висіла картка про ДТП
 const GVIS=new Set();M.groups.forEach((g,gi)=>{if(g[1].some(i=>A.has(i)))GVIS.add(gi)});
 const CF=+(cb_.querySelector('.on')||{dataset:{c:-1}}).dataset.c;
 const H=new Set();
 hb.querySelectorAll('.on').forEach(x=>PERIODS[+x.dataset.p][2].forEach(h=>H.add(h)));
 let tot=0;const vis=[];
 for(const p of P){
  if(CF>=0&&p[6]!==CF) continue;
  let n=0,th=null;
  for(const e of p[4]) if(C.has(e[0])&&A.has(e[1])&&Y.has(e[2])&&(!H.size||H.has(e[3]))){n++;if(th===null)th=CATTH[e[1]]}
  if(n){tot+=n;vis.push([p,n,th])}}
 vis.sort((a,b)=>b[1]-a[1]);
 // у версії для слухачів категорія прихована (p[6]=-1), тому фільтр по ===2 давав
 // порожній список і «Топ адрес» завжди показував «нема даних». Слухачам перелік
 // найгарячіших адрес потрібен саме для самостійного пошуку скупчень.
 const rank=vis.filter(v=>v[0][3]&&(STUDENT||v[0][6]===2));
 $('#cnt').textContent=tot.toLocaleString('uk');
 $('#cntl').textContent=`подій на ${vis.length.toLocaleString('uk')} адресах`;
 {let q=0;P.forEach(p=>{if(p[6]===2)q++});
  $('#cathint').innerHTML=q?`У поточних межах: <b style="color:#f87171">${q.toLocaleString('uk')}</b> проблем.`:'';}
 $('#top').innerHTML=rank.slice(0,15).map((v,i)=>
  `<div data-i="${i}"><span>${v[0][2]}</span><b>${v[1]}</b></div>`).join('')||'<div class="sub">нема даних</div>';
 [...$('#top').children].forEach((el,i)=>el.onclick=()=>{const v=rank[i];map.setView([v[0][0],v[0][1]],17);
  setTimeout(()=>{let best=null,bd=1e9;layer.eachLayer(l=>{const ll=l.getLatLng();
   const d=Math.abs(ll.lat-v[0][0])+Math.abs(ll.lng-v[0][1]);if(d<bd){bd=d;best=l}});
   if(best&&bd<1e-4)best.openPopup()},350)});
 layer.clearLayers();if(heat){map.removeLayer(heat);heat=null}
 if(heatOn){heat=L.heatLayer(vis.flatMap(v=>Array(Math.min(v[1],20)).fill([v[0][0],v[0][1],1])),
  {radius:18,blur:24,maxZoom:16}).addTo(map);return}
 const mx=vis.length?vis[0][1]:1;
 for(const [p,n,th] of vis){
  const r=Math.max(3.2,Math.min(19,3.2+8.5*Math.sqrt(n/Math.max(mx,1))*2));
  L.circleMarker([p[0],p[1]],{radius:r,weight:p[3]?.8:0,color:'#0f1117',
   fillColor:p[3]?(PALA[th%7]):'#5f6878',fillOpacity:p[3]?.72:.35})
  .bindPopup(()=>{
   const ev=p[4].filter(e=>C.has(e[0])&&A.has(e[1])&&Y.has(e[2])&&(!H.size||H.has(e[3])));
   const bc={},hh=new Array(24).fill(0);let nk=0;
   ev.forEach(e=>{bc[e[1]]=(bc[e[1]]||0)+1;if(e[3]>=0){hh[e[3]]++;nk++}});
   const rows=Object.entries(bc).sort((a,b)=>b[1]-a[1]);
   const mxh=Math.max(...hh,1);
   let bars='';
   if(nk>=8){bars='<div class="hg">'+hh.map((v,i)=>
     `<i style="height:${Math.max(2,Math.round(22*v/mxh))}px" title="${i}:00 — ${v}"></i>`).join('')+
     '</div><div class="hx"><span>0</span><span>6</span><span>12</span><span>18</span><span>23</span></div>';}
   const night=hh.slice(20).concat(hh.slice(0,4)).reduce((a,b)=>a+b,0);
   const hint = nk>=8 ? `<div class="hn">${Math.round(100*night/nk)}% подій припадає на 20:00–04:00</div>` : '';
   // ---- КАРТКИ ПРОБЛЕМ (п.7.4): по одній на кожен відібраний напрямок адреси ----
   let pblock='';
   const allp=p[7]||[];
   const probs=allp.filter(pr=>pr.thi===undefined||pr.thi<0||GVIS.has(pr.thi));
   const hidden=allp.length-probs.length;
   if(!STUDENT&&!probs.length&&hidden)
    pblock=`<div class="hn">Ця адреса — у списку проблем, але за іншим напрямком `+
     `(${allp.map(x=>x.theme).join(', ')}). Увімкніть відповідні правопорушення, щоб побачити картку.</div>`;
   if(!STUDENT&&probs.length){
    pblock=probs.map((pr,pi)=>{
     let h=`<div class="pcard"><div class="ph">Проблема · ${pr.theme}</div>`;
     h+=`<div class="pt">${pr.mech}</div>`;
     h+=`<div class="pm"><b>Правопорушення:</b> `+pr.arts.map(a=>`${a[0]} — ${a[1]}`).join('; ')+`</div>`;
     h+=`<div class="pm"><b>Чому проблема:</b> ${pr.n} однорідних подій за ${pr.years.length} `+
        `${pr.years.length===1?'рік':'роки'} (${pr.years.join(', ')}), `+
        `${Math.round(100*pr.n/Math.max(pr.core_n,1))}% усіх подій адреси цього роду.</div>`;
     if(pr.analysis){
      h+=`<div class="why"><b>Аналіз:</b> адреса — у верхніх ${100-pr.analysis.pc}% вулиць за `+
         `прогнозом моделі (${pr.theme.toLowerCase()}), влучність ${pr.analysis.hit}%. `+
         `Чинники: `+pr.analysis.factors.slice(0,5).map(f=>f[0]).join(', ')+`.</div>`;
     } else {
      h+=`<div class="why"><b>Аналіз:</b> модель не пояснює — причина встановлюється на місці.</div>`;
     }
     h+=`<button class="pbtn" data-pp="${pi}">Взяти в роботу — паспорт SARA</button></div>`;
     return h;
    }).join('');
    if(probs.length>1) pblock+='<div class="hn" style="margin-top:4px">Кілька напрямків на адресі — кілька окремих проблем із різними причинами.</div>';
   }
   const ex=p[5].filter(e=>A.has(e[0])).slice(0,4);
   const cinf=(p[6]===2&&probs.length)?CATNAME[2]:null;
   const html=`<div class="lp">
   ${cinf?`<span class="cbadge" style="background:${cinf[1]}22;color:${cinf[1]}">${cinf[0]}</span>`:''}
   <b>${p[2]||'адреса не визначена'}</b>
   <div class="tt">${n} ${n%10===1&&n%100!==11?'подія':'подій'} за поточним фільтром</div>
   <table class="bd">`+rows.map(([i,c])=>
     `<tr><td>${M.cats[i]}</td><td><b>${c}</b></td></tr>`).join('')+`</table>
   ${bars}${hint}${pblock}
   <div class="ex">Приклади рішень:</div><ul>`+
   ex.map(e=>`<li><span style="color:#79839a">${e[1]}${e[2]>=0?', '+String(e[2]).padStart(2,'0')+':00':''} · ${e[3]}</span> <a href="${e[4]}" target="_blank">відкрити</a></li>`).join('')+
   '</ul></div>';
   const wrap=document.createElement('div');wrap.innerHTML=html;
   wrap.querySelectorAll('[data-pp]').forEach(b=>b.onclick=()=>downloadPassport(p,probs[+b.dataset.pp]));
   return wrap},{maxWidth:360,autoPanPaddingTopLeft:[14,14],autoPanPaddingBottomRight:[14,14]}).addTo(layer)}
}
$('#heat').onclick=e=>{heatOn=!heatOn;e.target.classList.toggle('act');e.target.textContent=heatOn?'Показати точки':'Теплова карта';draw()};
$('#reset').onclick=()=>{document.querySelectorAll('#side input:not([data-r])').forEach(x=>x.checked=true);
 hb.querySelectorAll('.on').forEach(x=>x.classList.remove('on'));draw()};
$('#none').onclick=()=>{document.querySelectorAll('[data-a]').forEach(x=>x.checked=false);draw()};
$('#all').onclick=()=>{document.querySelectorAll('[data-a]').forEach(x=>x.checked=true);draw()};
document.querySelectorAll('#side input:not([data-r])').forEach(x=>x.addEventListener('change',draw));
document.querySelectorAll('[data-r]').forEach(x=>x.addEventListener('change',drawRisks));
draw();drawRisks();
</script></body></html>"""

if __name__ == '__main__':
    main()
