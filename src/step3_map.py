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
import mech as M
# HTML-шаблон винесено в окремий файл: разом із ним модуль важив 67 КБ,
# а це один файл на дві дуже різні речі — логіку відбору й розмітку.
from step3_tpl import TPL

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data'); DB = os.path.join(DATA, 'events.db')
OUT  = os.path.join(ROOT, 'karta.html')
RISKS = os.path.join(DATA, 'risks.json')
NETW  = os.path.join(DATA, 'network.json')
RISKF = os.path.join(DATA, 'risk.json')
BORD  = os.path.join(DATA, 'borders.json')
FACTF = os.path.join(DATA, 'factors.json')             # шар чинників середовища (крок 2e)
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

# латинські ярлики — для якорів у doslidzhennya.html (крок 6).
# Кирилиця у фрагменті URL працює, але ламається при копіюванні посилання,
# тому анкори латинські. ЄДИНЕ ДЖЕРЕЛО — mech.py: раніше цей словник жив
# у трьох файлах і вони встигли розійтися.
THSLUG = M.THSLUG

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
# відмінюємо за числᑖвником (1/2-4/5+) — ризик граматичної помилки вищий за
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

    # група подібності (п.7.2) для кожного індекса в `labels`
    LBL2SIM = {}
    for _code, (_th, _lbl) in L.CODE.items():
        LBL2SIM[(_th, _lbl)] = M.simgroup(_code) or f'{_th}_{_code}'
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
            # `th` тепер — або тема ('ДОР'), або механізм ('ДОР_ДТП').
            # Тема, під якою рядок стоїть у панелі, лежить у самому шарі.
            parent = v.get('theme') or M.simtheme(th)
            gi = [i for i, t in enumerate(L.ORDER) if t == parent]
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
                method = (f"Модель навчена на {d.get('навчання', 0):,} подіях зі справ, "
                          f"розглянутих 2024 року, і перевірена на "
                          f"{d.get('перевірка', 0):,} подіях зі справ 2025–2026. "
                          f"У верхніх 10% вулиць за прогнозом опиняється "
                          f"{100*d.get('hit_середовище', 0):.0f}% подій наступних років "
                          f"(у {d.get('PAI_середовище', 0)} рази краще за випадковий відбір).").replace(',', ' ')
            risks.setdefault('lines', {})['risk_' + th] = {
                'title': v.get('name') or L.THEMES.get(th, th),
                'slug': v.get('slug') or M.anchor(th),
                'kind': v.get('kind', 'theme'),
                'group': L.THEMES.get(parent, parent),
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
            'title': L.THEMES.get(_th, _th), 'slug': M.anchor(_th),
            'kind': 'theme', 'group': L.THEMES.get(_th, _th),
            'hit': 0, 'theme': _i,
            'why': '', 'factors': [], 'method': '', 'items': [], 'nodata': True}

    # ---- ШАР ЧИННИКІВ СЕРЕДОВИЩА (крок 2e) ----
    # Якщо файл ще не побудований, будуємо його тут-таки з osm_risks_raw.json.
    # Так карта збереться навіть без окремого кроку 2e у workflow; у межах одного
    # запуску step5_site викликає main() 22 рази — файл будується лише вперше.
    FACT = {}
    _rawp = os.path.join(DATA, 'osm_risks_raw.json')
    if not os.path.exists(FACTF) and os.path.exists(_rawp):
        try:
            import step2e_factors
            step2e_factors.main()
        except SystemExit:
            pass
        except Exception as _e:
            print('шар чинників не побудовано:', _e)
    if os.path.exists(FACTF):
        FACT = json.load(open(FACTF, encoding='utf-8'))
        print(f"чинники середовища: {sum(len(c['pts']) for c in FACT.get('cats', [])):,} об'єктів")

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
        # Спершу питаємо модель ВЛАСНОГО механізму цієї проблеми, і лише якщо
        # для нього моделі немає — загальну модель теми.
        rkey = c['sim'] if c['sim'] in theme_rgrid else th
        risk_pc = pred_theme(rkey, P[c['pi']][0], P[c['pi']][1])
        d = ER.get(rkey, {})
        analysis = None
        if risk_pc > 0 and d:
            analysis = dict(pc=risk_pc, hit=round(100*d.get('hit_середовище', 0)),
                             factors=[[n_, round(float(w), 3)] for n_, w in d.get('фактори', []) if w > 0][:8],
                             train=d.get('навчання', 0), test=d.get('перевірка', 0))
        probs_by_pi[c['pi']].append(dict(
            thi=gi_of_theme.get(th, -1),   # індекс теми — щоб картка ховалась разом із фільтром
            sim=c['sim'], theme=L.THEMES.get(th, th), mech=M.simname(c['sim']),
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
            for _c in FACT.get('cats', []):
                _c['pts'] = [q for q in _c['pts'] if in_ring(q[0], q[1], ring)]
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
              .replace('__FACTS__', json.dumps(FACT, ensure_ascii=False, separators=(',', ':'))) \
              .replace('__RISKS__', json.dumps(risks, ensure_ascii=False, separators=(',', ':'))) \
              .replace('__META__', json.dumps(meta, ensure_ascii=False)) \
              .replace('__PTS__', json.dumps(P, ensure_ascii=False, separators=(',', ':')))
    dst = out or OUT
    os.makedirs(os.path.dirname(dst) or '.', exist_ok=True)
    open(dst, 'w', encoding='utf-8').write(html)
    print(f'готово: {os.path.basename(dst)} ({os.path.getsize(dst)/1048576:.1f} МБ)')
