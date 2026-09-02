# -*- coding: utf-8 -*-
"""Відбір проблем і обрізання карти до району.

«Проблема» — не будь-яке скупчення, а пара «адреса + механізм», яка подолала
поріг однорідних епізодів. Інцидент стався раз випадково; проблема повторюється
роками, і причина в місці. Тут же збирається аналітична частина картки — роки,
розклад доби, підказка моделі ризику — і паспорт для SARA.

Далі: районна карта обрізає точки, межі, населення й лічильники до одного
району, бо дільничний працює районом, а не містом.

Шари під подіями — у map_layers.
"""
import os, sys, json, collections
import labels as L
import mech as M
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')

BORD  = os.path.join(DATA, 'borders.json')

# ---- ВІДБІР ПРОБЛЕМ (п.7.3) ----
MIN_EPISODES = 15   # мінімум однорідних епізодів (за групою подібності, п.7.2) на адресу
GUARANTEE    = 2    # обов'язкових проблем з кожного району
CITYWIDE     = 30   # + найгостріших по місту понад гарантовані

# Квота за напрямком (теми). На реальних даних дорожній рух — 85% усіх кандидатів
# (утричі більше подій за наступну тему), тож без обмежень він займав 48 з 50 місць,
# а насильство/середовище не потрапляли жодного разу. Квота дорожнього руху свідомо
# більша за інші — це найчисельніша тема, і повне вирівнювання було б нечесним щодо
# реальності. Якщо в темі просто немає кандидатів (як у насильства чи середовища),
# її квота лишається незаповненою — місця йдуть наступним найгострішим, а не пропадають.
CAP_THEME   = {'ДОР': 18}
CAP_DEFAULT = 10

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


THEME_SKEW = {
 'ГП': 'громадського порядку', 'АЛК': "пов'язаних з алкоголем", 'НАР': 'наркотичних',
 'НАС': 'насильства', 'МАЙ': 'майнових', 'ДОР': 'дорожніх', 'СЕР': 'середовища громади',
}



def select(P, meta, labels, ck, ykeys, sim_of, gi_of_theme,
           district, mode, risks, ER, FACT, theme_rgrid, pred_theme):
    """Повертає (P, POP, meta, theme_cnt)."""
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
    skipped_street = 0
    for pi, p in enumerate(P):
        # Проблема — це МІСЦЕ, куди можна приїхати. Центр вулиці місцем не є:
        # там зібрані події з усієї вулиці лише тому, що будинків не знайшлося
        # в OpenStreetMap. Такі точки в кандидати не беремо — інакше кожна
        # довга вулиця автоматично ставала б «проблемою» з великим числом.
        if not p[3]:
            skipped_street += 1
            continue
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
    if skipped_street:
        print(f'   не розглядали {skipped_street:,} центрів вулиць — це не місця, а вулиці загалом')
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

        # Лічильники бічної панелі рахувалися ДО обрізання району, тому на
        # районній карті стояли міські числа: у Деснянському було написано
        # «Дорожній рух 47 981» — це весь Київ. Перераховуємо по тому, що
        # справді лишилося на карті.
        cnt2 = collections.Counter()
        for p in P:
            for e in p[4]: cnt2[e[1]] += 1
        meta['counts'] = [cnt2.get(i, 0) for i in range(len(labels))]
        for g in meta['groups']:
            g[2] = sum(meta['counts'][i] for i in g[1])

    # Скільки подій лишилося на цій карті, за темами. Крок 5 будує з цього
    # плитки оглядової сторінки, щоб її числа збігалися з числами карти:
    # раніше плитка рахувала за судом, а карта — за географією району.
    theme_cnt = collections.Counter()
    for p in P:
        for e in p[4]: theme_cnt[labels[e[1]][0]] += 1

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
    return P, POP, meta, theme_cnt
