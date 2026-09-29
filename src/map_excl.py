# -*- coding: utf-8 -*-
"""Адреси установ: суди, відділи поліції, місця оформлення протоколів.

Такі адреси дають сотні подій, яких там насправді не сталося, і без вилучення
вони очолюють будь-який список. Виявляються автоматично: адресу установи
не названо в описі самої події (завдання 29, п. 1), вона стоїть на будівлі
установи чи має склад статей місця оформлення протоколів. Результат
пишеться в data/vykluchennya.txt — це РЕЗУЛЬТАТ, не вхід,
інакше адреса, раз потрапивши туди, лишалася б виключеною назавжди.

Власний список користувача — data/vykluchennya_moyi.txt — автоматика ніколи
не перезаписує.
"""
import os, sys, json, collections
import labels as L
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')

EXCL = os.path.join(DATA, 'vykluchennya.txt')           # формується автоматично
MANUAL = os.path.join(DATA, 'vykluchennya_moyi.txt')    # ваш список, ніколи не перезаписується
REVIEW = os.path.join(DATA, 'top100_dlya_pereviryky.txt')

# ---- ОЗНАКА «НЕ ПІДТВЕРДЖЕНА» (завдання 29, п. 1; 29.09.2026) ----
# Раніше установою вважалася адреса з понад 1,5% подій району чи понад 90
# подій. Так вилетіли вокзал, ТЦ, парковки — найсильніші справжні місця: на
# вироках і постановах вулиця адреси є в описі події у 84–100% випадків.
# Велика кількість подій була ознакою установи, поки подіями рахувалися
# ухвали. Адреса суду, поліції, лікарні видає себе інакше: її НЕМАЄ в описі
# події (класи C/D проходу по текстах). Тож виключаємо адресу, лише коли її
# підтверджено в описі менш ніж у половині подій — за обсягом чи біля
# будівлі установи.
POTV_MIN    = 0.5        # частка подій, в описі яких названо вулицю адреси
POTV_N      = 10         # від стількох подій непідтверджена адреса — установа

# ---- ДРУГА ОЗНАКА: ПРОФІЛЬ СТАТЕЙ ----
# Знайдено 3 вересня: вул. Святослава Хороброго, 9 — відділ поліції — давала
# 50 подій, тобто 0,68% свого району. Обидва пороги вище вона не перетинала й
# лишалася на карті як скупчення ДТП.
#
# Але місце оформлення протоколів видно не обсягом, а СКЛАДОМ. Керування у
# стані сп'яніння (ст.130) і залишення місця ДТП (ст.122-4) — це те, що
# оформлюють у відділі, а не там, де сталося. Справжній небезпечний перехрестя
# дає ст.124, і майже не дає ст.130.
#
# На всьому місті ця ознака ловить вісім адрес — рівно тих, що й мала.
PROC_MIN   = 20          # хоча б стільки подій на адресі
PROC_SHARE = 0.5         # і стільки маркерних статей серед них
MARKERS = {k for k, v in L.CODE.items()
           if v[1].startswith('ст.130 ') or v[1].startswith('ст.122-4 ')}

# Список «це справжня адреса, не чіпати». Потрібен тому, що автоматичний файл
# перезаписується щоразу: викреслити з нього рядок назавжди неможливо.
KEEP = os.path.join(DATA, 'vykluchennya_ne.txt')

# ---- ПЕРША ОЗНАКА, НАЙНАДІЙНІША: БУДІВЛЯ УСТАНОВИ ----
# Відділи поліції, суди й прокуратура з OpenStreetMap (крок 2b). Порівнюємо
# КООРДИНАТИ, а не рядки: текстовий перелік адрес спіткала б та сама біда,
# що й решту адрес у цих даних — «вул. С. Хороброго, 9» і «вул. Святослава
# Хороброго, 9» різні рядки, а будівля одна.
#
# Радіус малий навмисно. Геокодування ставить усі події адреси в одну точку,
# тож 60 метрів це «та сама будівля», а не «той самий квартал»: інакше разом
# із відділом вилітали б сусідні будинки, де події справжні.
USTANOVY = os.path.join(DATA, 'ustanovy.json')
NEAR_M = 60
_MLAT = 111320.0                    # метрів в одному градусі широти
_MLON = 111320.0 * 0.6374           # ...і довготи на широті Києва

def load_ustanovy():
    """(lat, lon, закрита?) установ; порожньо, якщо крок 2b ще не збирав їх.
    Закрита установа — СІЗО, колонія (amenity=prison): четверте поле 1."""
    if not os.path.exists(USTANOVY):
        return []
    try:
        return [(float(x[0]), float(x[1]), bool(x[3]) if len(x) > 3 else False,
                 x[4] if len(x) > 4 else None) for x in json.load(open(USTANOVY, encoding='utf-8'))]
    except Exception as e:
        print('   не прочитав data/ustanovy.json:', e)
        return []


def load_keep():
    """адреси, які НЕ виключати, хоч би що вирішила автоматика"""
    if not os.path.exists(KEEP):
        with open(KEEP, 'w', encoding='utf-8') as f:
            f.write('# Адреси, які НЕ треба виключати з карти,\n')
            f.write('# навіть якщо автоматика вважає їх установою.\n')
            f.write('# Автоматика цей файл НІКОЛИ не перезаписує.\n')
            f.write('# Один рядок = одна адреса, точно як у vykluchennya.txt\n\n')
    keep = set()
    for ln in open(KEEP, encoding='utf-8'):
        ln = ln.split('#')[0].strip()
        if ln: keep.add(ln.lower())
    return keep


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

def drop_excluded(rows, excl, street, house, lat, lon, exact):
    """Відсіює події на адресах установ — за рядком адреси І за точкою.

    Рядка мало: «вул. Братиславська, 3» і «вул. Братиславській, 3» — різні
    рядки, а лікарня одна, і геокодер ставить обидва в ту саму точку. Тому
    виключена адреса забирає з собою все, що стоїть у її точці. Лише для
    точних адрес: центр вулиці спільний для всієї вулиці, і розширення за
    ним вилучило б її цілком."""
    def addr(r):
        s, h = street(r), house(r)
        return ((s + ', ' + h) if (s and h) else (s or '')).lower()
    def pt(r):
        return (round(lat(r), 5), round(lon(r), 5))
    bad = {pt(r) for r in rows if exact(r) and addr(r) in excl}
    keep = [r for r in rows if addr(r) not in excl and not (exact(r) and pt(r) in bad)]
    by_str = sum(1 for r in rows if addr(r) in excl)
    print(f'   вилучено подій: {by_str:,} за адресою, ще {len(rows) - len(keep) - by_str:,} '
          f'за точкою (інше написання тієї самої адреси)')
    return keep


def detect_institutional(rows, manual, potv=None):
    """potv: doc_id -> (подія по суті?, вулицю адреси названо в описі?).
    Без нього (стара база без проходу) підтвердження вважається відсутнім
    для всіх — і діє лише будівля й склад, як запасний режим."""
    per_court = collections.Counter(r[1] for r in rows)
    per_addr = collections.Counter()
    addr_court = {}
    n_ev, n_potv = collections.Counter(), collections.Counter()
    for r in rows:
        if not r[5]: continue
        a = (r[5] + ', ' + r[6]) if r[6] else r[5]
        per_addr[a] += 1
        addr_court[a] = r[1]
        ev, ok = (potv or {}).get(r[0], (False, False))
        # Частка — на вироках і постановах: ухвала адресу події не
        # підтверджує й не спростовує, вона про процедуру
        if ev:
            n_ev[a] += 1; n_potv[a] += ok
    # склад статей кожної адреси — для ознаки «місце оформлення»
    prof_mark = collections.Counter()
    for r in rows:
        if not r[5]: continue
        if r[2] in MARKERS:
            prof_mark[(r[5] + ', ' + r[6]) if r[6] else r[5]] += 1

    # координати кожної адреси — з події на точному будинку, якщо така є:
    # та сама адреса буває й «центром вулиці» (будинку не знайшлося в
    # старому геокодуванні), і перша-ліпша подія ставила СІЗО на
    # Дегтярівській у центр вулиці за 1,5 км від ізолятора
    addr_pt = {}
    for r in rows:
        if not r[5] or not (r[7] and r[8]): continue
        a = (r[5] + ', ' + r[6]) if r[6] else r[5]
        if a not in addr_pt or (r[9] != 'street' and addr_pt[a][2] == 'street'):
            addr_pt[a] = (r[7], r[8], r[9])
    addr_pt = {a: (la, lo) for a, (la, lo, _p) in addr_pt.items()}

    ust = load_ustanovy()
    on_ust, on_zakr = set(), set()
    if ust:
        # сітка на 0,001° (~110 м), щоб не міряти кожну адресу до кожної установи
        cell = collections.defaultdict(list)
        zakr = [(la, lo, bb) for la, lo, zk, bb in ust if zk]
        for la, lo, zk, _bb in ust:
            if not zk: cell[(int(la * 1000), int(lo * 1000))].append((la, lo))
        for a, (la, lo) in addr_pt.items():
            ci, cj = int(la * 1000), int(lo * 1000)
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    for ula, ulo in cell.get((ci + di, cj + dj), ()):
                        if ((la - ula) * _MLAT) ** 2 + ((lo - ulo) * _MLON) ** 2 <= NEAR_M ** 2:
                            on_ust.add(a)
            # Закрита установа — адреса в межах її території (прямокутник меж
            # з OSM) або в NEAR_M від точки, якщо меж немає. Не до центру:
            # центр ізолятора на Дегтярівській за 71 м від адреси входу. І не
            # «60 м від меж»: прямокутник уже більший за сам ізолятор, і з
            # запасом вилітали сусідні будинки Бердичівської й Лобановського.
            for zla, zlo, bb in zakr:
                if bb:
                    y0, x0, y1, x1 = bb
                    if y0 <= la <= y1 and x0 <= lo <= x1: on_zakr.add(a)
                elif ((la - zla) * _MLAT) ** 2 + ((lo - zlo) * _MLON) ** 2 <= NEAR_M ** 2:
                    on_zakr.add(a)
        print(f'   установ з OpenStreetMap: {len(ust)} (закритих {sum(1 for x in ust if x[2])}); '
              f'адрес на них: {len(on_ust | on_zakr)}')
    else:
        print('   data/ustanovy.json немає — установи ловляться лише за числами '
              '(запустіть крок 2b (src/step2b_risks.py), щоб додати будівлі з OpenStreetMap)')

    # ---- ОДНА АДРЕСА — ОДИН КЛЮЧ (завдання 29, п. 3) ----
    # «вул. С. Хороброго, 9» і «вул. Святослава Хороброго, 9» — один відділ
    # поліції. Рахуємо й вирішуємо за ключем адреси (adr_kliuch), а
    # виключаємо всі написання ключа — без ручного списку.
    import adr_kliuch
    KL = adr_kliuch.Kliuch()
    parts = {}
    for r in rows:
        if r[5]:
            a = (r[5] + ', ' + r[6]) if r[6] else r[5]
            if a not in parts: parts[a] = (r[5], r[6])
    gkey = {a: (KL(s, h) or a.lower()) for a, (s, h) in parts.items()}
    grp = collections.defaultdict(list)
    for a, k in gkey.items(): grp[k].append(a)

    keep = load_keep()
    auto = {}
    for k, adrs in grp.items():
        n = sum(per_addr[a] for a in adrs)
        ne = sum(n_ev[a] for a in adrs)
        pv = sum(n_potv[a] for a in adrs) / ne if ne else 0.0
        mark = sum(prof_mark[a] for a in adrs) / n if n else 0
        nepotv = pv < POTV_MIN
        # Закрита установа — завжди, незалежно від підтвердження: адресу
        # СІЗО в описі названо, бо подія сталася всередині ізолятора, а
        # публічного простору це не стосується
        why = ('закрита установа' if any(a in on_zakr for a in adrs)
               else 'будівля' if any(a in on_ust for a in adrs) and nepotv
               else 'не підтверджена' if (ne >= POTV_N and nepotv)
               else ('склад' if (n >= PROC_MIN and mark >= PROC_SHARE) else None))
        if not why: continue
        for a in adrs:
            if a.lower() not in keep:
                auto[a] = (per_addr[a], round(100 * pv), why, round(100 * mark))
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
            f.write('# Визначено автоматично за чотирма ознаками (усі написання однієї адреси — разом):\n')
            f.write(f'#   закрита установа — СІЗО, колонія за OpenStreetMap у {NEAR_M} м, завжди;\n')
            f.write('#   будівля — адреса стоїть на відділі поліції, суді чи прокуратурі\n')
            f.write(f'#             за даними OpenStreetMap (радіус {NEAR_M} м), і в описі\n')
            f.write(f'#             подій її названо менш ніж у {POTV_MIN*100:g}%;\n')
            # пороги підставляються з констант, щоб текст не розходився з кодом
            f.write(f'#   не підтверджена — від {POTV_N} вироків і постанов, і в описі\n')
            f.write(f'#             подій вулицю адреси названо менш ніж у {POTV_MIN*100:g}%;\n')
            f.write(f'#   склад — від {PROC_MIN} подій, з яких понад {PROC_SHARE*100:g}% це\n')
            f.write('#           ст.130 і ст.122-4, тобто те, що оформлюють у відділі.\n')
            f.write('#\n')
            f.write('# ЦЕЙ ФАЙЛ ПЕРЕЗАПИСУЄТЬСЯ ЩОРАЗУ. Викреслити рядок назавжди не\n')
            f.write('# вийде: якщо адреса справжня, впишіть її у vykluchennya_ne.txt.\n')
            f.write('# Один рядок = одна адреса.\n\n')
            for a, (n, pc, why, mk) in sorted(auto.items(), key=lambda x: -x[1][0]):
                tail = ({'закрита установа': f'{n} подій, закрита установа (СІЗО, колонія) за OpenStreetMap',
                         'будівля': f'{n} подій, будівля установи за OpenStreetMap, в описі {pc}%',
                         'не підтверджена': f'{n} подій, вулицю названо в описі {pc}%'}
                        .get(why, f'{n} подій, {mk}% ст.130 і ст.122-4'))
                f.write(f'{a}   # {tail}\n')
        by_why = collections.Counter(v[2] for v in auto.values())
        print(f'   виявлено установ: {len(auto)} -> data/vykluchennya.txt  ('
              + ', '.join(f'{n} за {w}' for w, n in by_why.most_common()) + ')')
        for a, (n, pc, why, mk) in sorted(auto.items(), key=lambda x: -x[1][0])[:8]:
            print(f'     {n:5}  {pc:4}%  {a}')
    return {a.lower() for a in auto} | manual
