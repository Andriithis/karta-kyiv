# -*- coding: utf-8 -*-
"""Крок 2b. Кеш OpenStreetMap: вулиці, об'єкти середовища, установи.

Лише «що є»: шари «чого немає» (тротуари, освітлення, переходи) прибрано —
RISHENNYA 27 визнав їх хибними, а data/risks.json з ними більше ніхто не
читав (ZAVDANNYA-30, ч. 5)."""
import os, sys, json, time, math, urllib.request, urllib.parse, urllib.error, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
RAW  = os.path.join(DATA, 'osm_risks_raw.json')

# overpass.osm.ch виключено: стабільно повертає порожню відповідь замість помилки
ENDPOINTS = ['https://overpass-api.de/api/interpreter',
             'https://overpass.kumi.systems/api/interpreter',
             'https://overpass-api.de/api/interpreter',
             'https://overpass.kumi.systems/api/interpreter']

AREA = 'area["boundary"="administrative"]["admin_level"="4"]["name"="Київ"]->.k;'

# лёгкі шари - одним запитом; важкі - плитками
LIGHT = {
 # --- атрактори за літературою ---
 'alcohol': '(nwr["amenity"~"^(bar|pub|nightclub|biergarten)$"](area.k);'
            'nwr["shop"~"^(alcohol|wine|beverages)$"](area.k););out tags center;',
 'bar_on':  '(nwr["amenity"~"^(bar|pub|nightclub|biergarten)$"](area.k););out tags center;',
 'bar_off': '(nwr["shop"~"^(alcohol|wine|beverages)$"](area.k););out tags center;',
 'shop24':  '(nwr["shop"="convenience"](area.k);'
            'nwr["amenity"="fast_food"](area.k););out tags center;',
 'finance': '(nwr["shop"~"^(pawnbroker|money_lender)$"](area.k);'
            'nwr["amenity"~"^(bureau_de_change|money_transfer)$"](area.k);'
            'nwr["amenity"="atm"](area.k);node["amenity"="atm"](area.k););out tags center;',
 'gambling':'(nwr["amenity"~"^(casino|gambling)$"](area.k);'
            'nwr["shop"="bookmaker"](area.k);'
            'nwr["leisure"="adult_gaming_centre"](area.k););out tags center;',
 'food':    '(nwr["amenity"~"^(restaurant|cafe)$"](area.k););out tags center;',
 'fuel':    '(nwr["amenity"="fuel"](area.k););out tags center;',
 'parking': '(nwr["amenity"="parking"](area.k););out tags center;',
 # --- генератори ---
 'metro':   '(node["railway"="subway_entrance"](area.k);'
            'nwr["railway"="station"](area.k););out tags center;',
 'busstop': '(node["highway"="bus_stop"](area.k);'
            'node["public_transport"="platform"](area.k););out tags center;',
 'market':  '(nwr["amenity"="marketplace"](area.k);'
            'nwr["shop"~"^(mall|department_store|supermarket)$"](area.k););out tags center;',
 'transit': '(node["railway"="subway_entrance"](area.k);'
            'nwr["amenity"="bus_station"](area.k);'
            'nwr["railway"="station"](area.k);'
            'nwr["amenity"="marketplace"](area.k););out tags center;',
 'school':  '(nwr["amenity"~"^(school|kindergarten)$"](area.k););out tags center;',
 'univer':  '(nwr["amenity"~"^(university|college)$"](area.k););out tags center;',
 'health':  '(nwr["amenity"~"^(hospital|clinic|pharmacy)$"](area.k););out tags center;',
 # --- установи, у яких оформлюють протоколи ---
 # Відділи поліції, суди, прокуратура. Потрібні не як чинник ризику, а щоб
 # викидати їх з карти: подія, записана на адресу відділу, сталася не там.
 # Беремо саме з OSM, бо це КООРДИНАТИ — текстовий перелік адрес спіткала б
 # та сама біда, що й решту адрес тут: «вул. С. Хороброго, 9» і «вул. Святослава
 # Хороброго, 9» різні рядки, а будівля одна.
 'ustanovy':'(nwr["amenity"~"^(police|courthouse|prosecutor)$"](area.k);'
            'nwr["government"~"^(police|prosecutor)$"](area.k););out tags center;',
 # Закриті установи — СІЗО, колонії (завдання 30, ч. 0 і 2): події всередині
 # ізолятора не стосуються публічного простору, адреса виключається завжди.
 # Окремий ключ, щоб наявний кеш докачав його сам. З межами (bb): ізолятор —
 # велика територія, і центр її точки буває за 70 м від адреси входу.
 'zakryti': '(nwr["amenity"="prison"](area.k););out tags center bb;',
 # Магістралі й проспекти (primary, trunk) — лише для точки перехрестя
 # (завдання 30, ч. 4): у шарі roads їх немає, а «перехрестя просп. Перемоги
 # та вул. …» без них не знайти. У модель ризику вони не йдуть.
 'dorogy_velyki': '(way["highway"~"^(primary|trunk|primary_link)$"](area.k););out tags geom;',
 # --- занедбаність ---
 'abandon': '(nwr["building"~"^(ruins|abandoned|construction)$"](area.k);'
            'nwr["abandoned"="yes"](area.k);nwr["ruins"="yes"](area.k);'
            'nwr["disused"="yes"](area.k););out tags center;',
 # --- благоустрій, "очі на вулиці" ---
  'play':    '(nwr["leisure"~"^(playground|fitness_station)$"](area.k););out tags center;',
  # --- зелень: крони і трава ОКРЕМО (у літературі знаки різні) ---
  'park':    '(nwr["leisure"~"^(park|garden)$"](area.k););out tags center;',
  # --- інфраструктура руху ---
 'lamps':   '(node["highway"="street_lamp"](area.k););out skel;',
 'cross':   '(node["highway"="crossing"](area.k);node["crossing"~"."](area.k););out skel;',
 'calming': '(node["traffic_calming"~"."](area.k);'
            'node["highway"="traffic_signals"](area.k););out skel;',
}
# ---- ПЕРЕЛІК ЧИННИКІВ Б1 (NAUKA.md, «Перелік чинників для Б1», 28.09.2026) ----
# Рівно ті запити, що зафіксовані до запуску; після результату не міняються.
# Окремі ключі b1_*, а не правка старих: старі категорії («finance» —
# ломбарди разом із банкоматами, «market» — ринки з ТЦ) змішували різні
# механізми (PLAN-KROK7, розд. 7.1), а ними ще користуються інші кроки.
# Лише «що є»: шари «чого немає» — під забороною (RISHENNYA, розд. 27).
# name — для звітів (ризиковані заклади) і «Що поруч».
B1 = {
 'b1_bars':     ('бари',          '(nwr["amenity"~"^(bar|pub|nightclub|biergarten)$"](area.k););'),
 'b1_alk':      ('алкоголь_винос','(nwr["shop"~"^(alcohol|wine|beverages)$"](area.k););'),
 'b1_cafe':     ('кафе',          '(nwr["amenity"~"^(restaurant|cafe)$"](area.k););'),
 'b1_fastfood': ('фастфуд',       '(nwr["amenity"="fast_food"](area.k););'),
 'b1_pawn':     ('ломбарди',      '(nwr["shop"~"^(pawnbroker|money_lender)$"](area.k););'),
 'b1_atm':      ('банкомати',     '(nwr["amenity"="atm"](area.k););'),
 'b1_exchange': ('обмінники',     '(nwr["amenity"~"^(bureau_de_change|money_transfer)$"](area.k););'),
 'b1_market':   ('ринки',         '(nwr["amenity"="marketplace"](area.k););'),
 'b1_super':    ('супермаркети',  '(nwr["shop"="supermarket"](area.k););'),
 'b1_mall':     ('ТЦ',            '(nwr["shop"~"^(mall|department_store)$"](area.k););'),
 'b1_hospital': ('лікарні',       '(nwr["amenity"~"^(hospital|clinic)$"](area.k););'),
 'b1_pharmacy': ('аптеки',        '(nwr["amenity"="pharmacy"](area.k););'),
 'b1_fuel':     ('АЗС',           '(nwr["amenity"="fuel"](area.k););'),
 'b1_school':   ('школи',         '(nwr["amenity"~"^(school|kindergarten)$"](area.k););'),
 'b1_univer':   ('ВНЗ',           '(nwr["amenity"~"^(university|college)$"](area.k););'),
 'b1_metro':    ('метро',         '(node["railway"="subway_entrance"](area.k);nwr["railway"="station"](area.k););'),
 'b1_stops':    ('зупинки',       '(node["highway"="bus_stop"](area.k);node["public_transport"="platform"](area.k););'),
 'b1_play':     ('майданчики',    '(nwr["leisure"~"^(playground|fitness_station)$"](area.k););'),
 'b1_parking':  ('паркінги',      '(nwr["amenity"="parking"](area.k););'),
 'b1_abandon':  ('покинуті',      '(nwr["building"~"^(ruins|abandoned)$"](area.k);nwr["abandoned"="yes"](area.k);'
                                  'nwr["disused"="yes"](area.k););'),
 'b1_underpass':('переходи_підземні', '(way["highway"~"^(footway|steps|pedestrian)$"]["tunnel"="yes"](area.k);'
                                  'way["highway"~"^(footway|steps|pedestrian)$"]["layer"~"^-"](area.k););'),
 'b1_dorm':     ('гуртожитки',    '(nwr["building"="dormitory"](area.k);nwr["tourism"="hostel"](area.k););'),
 'b1_garages':  ('гаражі',        '(nwr["landuse"="garages"](area.k);nwr["building"="garages"](area.k););'),
}
for _k, (_ua, _q) in B1.items():
    LIGHT[_k] = _q + 'out tags center;'
HEAVY = {
 'roads':  'way["highway"~"^(residential|tertiary|secondary|unclassified|living_street)$"]',
 'foot':   'way["highway"~"^(footway|path|pedestrian)$"]',
 'houses': 'way["building"~"^(apartments|residential|house|dormitory)$"]',
}
BBOX = (50.21, 30.24, 50.59, 30.83)
TILES = 3

def fetch(name, body, label='', allow_empty=False, retry_empty=False):
    """retry_empty — для плиток: порожня відповідь спершу вважається збоєм
    сервера й повторюється на всіх; лише коли всі сервери всі рази кажуть 0,
    плитка справді порожня (кут рамки за межами Києва). 28.09 kumi.systems
    віддав 0 на центральну плитку — без повтору модель вчилася б без центру."""
    zeros = 0
    q = '[out:json][timeout:600];' + AREA + body
    data = urllib.parse.urlencode({'data': q}).encode()
    for attempt, ep in enumerate(ENDPOINTS * 2):
        try:
            print(f'   {name:8}{label:8} <- {ep.split("/")[2]:22}', end=' ', flush=True)
            rq = urllib.request.Request(ep, data=data, headers={'User-Agent': 'edrsr-academy/3.0'})
            with urllib.request.urlopen(rq, timeout=650) as r:
                raw = r.read().decode('utf-8', 'replace')
            try:
                js = json.loads(raw)
            except Exception:
                msg = ' '.join(raw.split())[:200]
                print(f'НЕ JSON: {msg}')
                time.sleep(8); continue
            els = js.get('elements', [])
            n = len(els)
            if n == 0 and (not allow_empty or retry_empty):
                zeros += 1
                if retry_empty and zeros >= len(ENDPOINTS):
                    print('0 — усі сервери кажуть 0, плитка порожня')
                    return els
                print('0 — підозріло, пробую інший сервер')
                time.sleep(20); continue
            print(f'{n:,}')
            return els
        except urllib.error.HTTPError as e:
            wait = 45 if e.code in (429, 504) else 10
            print(f'HTTP {e.code} — пауза {wait} c')
            time.sleep(wait)
        except Exception as e:
            print(f'збій {type(e).__name__}: {str(e)[:70]}')
            time.sleep(15)
    print(f'   !!! {name}{label} НЕ ЗАВАНТАЖЕНО')
    return None

def raiony_bez(roads, min_n=50):
    """Райони (data/borders.json), у яких менше min_n вулиць: ознака того,
    що плитку повернуто порожньою. Меж немає — перевірки немає."""
    bp = os.path.join(DATA, 'borders.json')
    if not os.path.exists(bp) or not roads: return []
    B = json.load(open(bp, encoding='utf-8'))
    def inside(la, lo, ring):
        c = False
        for (a1, o1), (a2, o2) in zip(ring, ring[1:] + ring[:1]):
            if (o1 > lo) != (o2 > lo) and la < (a2 - a1) * (lo - o1) / (o2 - o1) + a1: c = not c
        return c
    n = collections.Counter()
    for w in roads:
        g = w.get('geometry') or []
        if not g: continue
        p = g[len(g) // 2]
        for d, ring in B.items():
            if inside(p['lat'], p['lon'], ring): n[d] += 1; break
    return [d for d in B if n[d] < min_n]


def center(el):
    if 'lat' in el: return el['lat'], el['lon']
    c = el.get('center')
    if c: return c['lat'], c['lon']
    g = el.get('geometry')
    if g: return sum(p['lat'] for p in g)/len(g), sum(p['lon'] for p in g)/len(g)
    b = el.get('bounds')      # «out bb» дає межі замість центру
    if b: return (b['minlat'] + b['maxlat']) / 2, (b['minlon'] + b['maxlon']) / 2
    return None

def heavy(k):
    """важкий шар плитками; None — якщо хоч одна плитка не завантажилась"""
    s_, w_, n_, e_ = BBOX
    dla, dlo = (n_ - s_) / TILES, (e_ - w_) / TILES
    acc, seen = [], set()
    outmode = 'out tags geom;' if k in ('roads', 'foot') else 'out center;'
    for i in range(TILES):
        for j in range(TILES):
            bb = f'{s_+i*dla:.4f},{w_+j*dlo:.4f},{s_+(i+1)*dla:.4f},{w_+(j+1)*dlo:.4f}'
            els = fetch(k, f'({HEAVY[k]}(area.k)({bb}););{outmode}',
                        f'{i*TILES+j+1}/{TILES*TILES}', allow_empty=True, retry_empty=True)
            if els is None:
                print(f'   !!! {k} {i*TILES+j+1}/{TILES*TILES} не завантажено')
                return None
            for el in els:
                if el.get('id') not in seen:
                    seen.add(el.get('id')); acc.append(el)
            time.sleep(5)
    print(f'   {k}: разом {len(acc):,}')
    return acc


def main():
    os.makedirs(DATA, exist_ok=True)
    if os.path.exists(RAW):
        raw = json.load(open(RAW, encoding='utf-8'))
        miss = [k for k in LIGHT if not raw.get(k)]
        if miss:
            print(f'сирі дані є, але порожні шари: {", ".join(miss)} — докачую')
            for k in miss:
                r_ = fetch(k, LIGHT[k])
                if r_: raw[k] = r_
                time.sleep(5)
            json.dump(raw, open(RAW, 'w', encoding='utf-8'), ensure_ascii=False)
        else:
            # Докачуємо лише те, чого в кеші немає. Раніше поява нової категорії
            # означала перезавантаження всіх 25 хвилин; тепер це хвилина.
            miss = [k for k in LIGHT if k not in raw]
            if miss:
                print('докачую нові категорії:', ', '.join(miss))
                for k in miss:
                    r_ = fetch(k, LIGHT[k])
                    raw[k] = r_ if r_ is not None else []
                    time.sleep(5)
                json.dump(raw, open(RAW, 'w', encoding='utf-8'), ensure_ascii=False)
            else:
                print('сирі дані OSM вже є (видаліть data/osm_risks_raw.json щоб перезавантажити)')
        # Важкі шари докачуємо так само. Кеш, зібраний лише з вулицями й
        # об'єктами Б1, не мав будинків і пішохідних доріжок — і крок 2c
        # мовчки не рахував потоків, а голос мешканців не знав, де мешканці.
        hmiss = [k for k in HEAVY if not raw.get(k)]
        if hmiss:
            print('докачую важкі шари плитками:', ', '.join(hmiss))
            for k in hmiss:
                acc = heavy(k)
                if acc is not None:
                    raw[k] = acc
                    json.dump(raw, open(RAW, 'w', encoding='utf-8'), ensure_ascii=False)
    else:
        print('1) завантаження з OpenStreetMap (10-25 хв):')
        raw = {}
        for k, q in LIGHT.items():
            r_ = fetch(k, q)
            raw[k] = r_ if r_ is not None else []
            time.sleep(5)
        for k in HEAVY:
            acc = heavy(k)
            if acc is None:
                # плитку не завантажено — не зберігаємо діряві дані в кеш
                print('   зупиняюсь'); sys.exit(1)
            raw[k] = acc
        pusti = raiony_bez(raw.get('roads', []))
        if pusti:
            print('   !!! немає жодної вулиці в районах: ' + ', '.join(pusti) + ' — кеш не зберігаю')
            sys.exit(1)
        json.dump(raw, open(RAW, 'w', encoding='utf-8'), ensure_ascii=False)

    print('\n2) обробка')
    # data/risks.json (точки й шари «чого немає») більше не пишеться: його читав
    # лише danger_schools() на шарі OSM «немає тротуару», який RISHENNYA 27
    # визнав хибним (ZAVDANNYA-30, ч. 5). Сирі дані лишаються в кеші для
    # кроків 2c, 2e і 4.

    # --- установи: окремий маленький файл для виключення з карти ---
    ust = []
    for k in ('ustanovy', 'zakryti'):
        for el in raw.get(k, []):
            c = center(el)
            if c:
                t = el.get('tags', {})
                # 4-те поле: 1 — закрита установа (виключається завжди, map_excl);
                # 5-те — межі її території [мін. шир., мін. довг., макс. шир., макс. довг.]
                b = el.get('bounds') or {}
                ust.append([round(c[0], 5), round(c[1], 5),
                            (t.get('name') or t.get('amenity') or '')[:60], 1 if k == 'zakryti' else 0]
                           + ([[b['minlat'], b['minlon'], b['maxlat'], b['maxlon']]] if b else []))
    if ust:
        up = os.path.join(DATA, 'ustanovy.json')
        json.dump(ust, open(up, 'w', encoding='utf-8'),
                  ensure_ascii=False, separators=(',', ':'))
        print(f'   установи (поліція, суди, прокуратура): {len(ust):,} -> data/ustanovy.json')

    print('\n=== ГОТОВО === кеш OSM і data/ustanovy.json')
