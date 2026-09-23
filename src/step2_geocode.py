# -*- coding: utf-8 -*-
"""Крок 2. Адресна база СУВОРО в межах міста Києва + зіставлення."""
import os, re, sys, json, time, sqlite3, math, urllib.request, urllib.parse, urllib.error, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import step1c_teksty as TK      # частини проходу по текстах (крок 6)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
DB   = os.path.join(DATA, 'events.db')
OSM  = os.path.join(DATA, 'osm_kyiv_city.json')

ENDPOINTS = ['https://overpass-api.de/api/interpreter',
             'https://overpass.kumi.systems/api/interpreter',
             'https://overpass-api.de/api/interpreter',
             'https://overpass.kumi.systems/api/interpreter']
BBOX  = (50.21, 30.24, 50.59, 30.83)
TILES = 3

QHEAD = '[out:json][timeout:600];area["boundary"="administrative"]["admin_level"="4"]["name"="Київ"]->.k;'

TYPEWORDS = r'(вулиця|вулиці|вулицю|вул\.?|проїзд\w*|проспект[уі]?|просп\.?|бульвар[уі]?|бульв\.?|б-р|провулок|провулку|пров\.?|площа|площі|пл\.?|шосе|набережна|набережної|наб\.?|узвіз|узвозу|алея|алеї|тупик|тракт|мікрорайон)'

def norm(s):
    if not s: return ''
    s = s.lower().replace('\u2019', "'").replace('`', "'").replace('\u02bc', "'")
    s = re.sub(TYPEWORDS, ' ', s)
    s = re.sub(r"[^а-яіїєґ0-9' \-]", ' ', s)
    s = s.replace('-', ' ').replace("'", '')
    return re.sub(r'\s+', ' ', s).strip()

def nh(h):
    if not h: return ''
    h = h.upper().replace(' ', '').replace('\\', '/')
    return re.sub(r'[^0-9A-ZА-Я/]', '', h)

def _ask(body, label):
    data = urllib.parse.urlencode({'data': QHEAD + body}).encode()
    for ep in ENDPOINTS * 2:
        try:
            print(f'   {label:9} <- {ep.split("/")[2]:24}', end=' ', flush=True)
            rq = urllib.request.Request(ep, data=data, headers={'User-Agent': 'edrsr-academy/4.0'})
            with urllib.request.urlopen(rq, timeout=650) as r:
                js = json.loads(r.read().decode('utf-8', 'replace'))
            els = js.get('elements', [])
            print(f'{len(els):,}')
            return els
        except urllib.error.HTTPError as e:
            wait = 45 if e.code in (429, 504) else 10
            print(f'HTTP {e.code} — пауза {wait} c'); time.sleep(wait)
        except Exception as e:
            print(f'{type(e).__name__} — пауза 15 c'); time.sleep(15)
    print(f'   !!! {label} не завантажено')
    return None

def fetch():
    """адреси міста Києва, плитками (один великий запит сервер не витримує)"""
    if os.path.exists(OSM):
        print('   база вже завантажена (видаліть data/osm_kyiv_city.json щоб оновити)')
        return json.load(open(OSM, encoding='utf-8'))
    s_, w_, n_, e_ = BBOX
    dla, dlo = (n_ - s_) / TILES, (e_ - w_) / TILES
    out, seen, failed = [], set(), 0
    for i in range(TILES):
        for j in range(TILES):
            bb = f'{s_+i*dla:.4f},{w_+j*dlo:.4f},{s_+(i+1)*dla:.4f},{w_+(j+1)*dlo:.4f}'
            body = (f'(node["addr:housenumber"]["addr:street"](area.k)({bb});'
                    f'way["addr:housenumber"]["addr:street"](area.k)({bb}););out tags center;')
            els = _ask(body, f'{i*TILES+j+1}/{TILES*TILES}')
            if els is None:
                failed += 1; continue
            for el in els:
                if el.get('id') in seen: continue
                seen.add(el.get('id'))
                t = el.get('tags', {})
                lat = el.get('lat') or (el.get('center') or {}).get('lat')
                lon = el.get('lon') or (el.get('center') or {}).get('lon')
                if lat and lon and t.get('addr:street'):
                    out.append([t['addr:street'], t.get('addr:housenumber', ''), round(lat, 6), round(lon, 6)])
            time.sleep(4)
    if failed > TILES * TILES // 3:
        print(f'   ЗАБАГАТО невдалих плиток ({failed}) — база неповна, не зберігаю')
        return []
    if out:
        json.dump(out, open(OSM, 'w', encoding='utf-8'), ensure_ascii=False)
        print(f'   отримано {len(out):,} адрес міста Києва')
    return out

def spread_km(pts):
    la = [p[0] for p in pts]; lo = [p[1] for p in pts]
    return max(max(la)-min(la)*1, 0)*111 + (max(lo)-min(lo))*71

CROSS_M = 150      # далі за це найближчі будинки двох вулиць — вулиці не перетинаються

def _street_key(s, streets, tail):
    ns = norm(s)
    if ns in streets: return ns
    cand = tail.get(ns.split()[-1], []) if ns else []
    return cand[0] if len(cand) == 1 else None

def cross_point(s1, s2, streets, centro, tail):
    """Перехрестя двох вулиць. Перехресть в адресній базі немає — лише
    будинки, тож беремо середину між найближчими будинками двох вулиць.
    Не знайшли — центр першої вулиці з рівнем 'street': точку перехрестя
    не вигадуємо."""
    k1, k2 = _street_key(s1, streets, tail), _street_key(s2, streets, tail)
    if k1 and k2 and k1 != k2:
        cell = collections.defaultdict(list)
        for la, lo in streets[k2]:
            cell[(int(la * 500), int(lo * 500))].append((la, lo))
        best = None
        for la, lo in streets[k1]:
            ci, cj = int(la * 500), int(lo * 500)
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    for la2, lo2 in cell.get((ci + di, cj + dj), ()):
                        d = ((la - la2) * 111320) ** 2 + ((lo - lo2) * 71000) ** 2
                        if best is None or d < best[0]:
                            best = (d, (la + la2) / 2, (lo + lo2) / 2)
        if best and best[0] <= CROSS_M ** 2:
            return (round(best[1], 6), round(best[2], 6), 'cross')
    k = k1 if k1 in centro else None
    return (*centro[k], 'street') if k else None

# ---- БУДИНКИ, ЯКИХ НЕМАЄ В OSM (PLAN-TEKSTY.md, 4б) ----
# Лише для подій класу B — чужу адресу розстановка зробила б точнішою, ніж
# вона є. Перевірка на установи — далі, у step3_map, як для всіх адрес.
NEIGHBOUR = 8           # сусід того самого боку — не далі за 8 номерів
# «20Б» стає поруч із будинком 20, а не на ньому: інакше точка злилася б з
# подіями самого будинку 20 і його підпис став би чужим. ~4 м на північ.
BESIDE = 0.00004


def nearby(ns, h, exact, nums):
    """(lat, lon, 'base' | 'interp') або None."""
    m = re.match(r'^(\d+)', h)
    if not m:
        return None
    n = int(m.group(1))
    if h != str(n) and (ns, str(n)) in exact:
        la, lo = exact[(ns, str(n))]
        return (round(la + BESIDE, 6), lo, 'base')
    nn = nums.get(ns) or {}
    lo_ = [x for x in nn if x < n and x % 2 == n % 2 and n - x <= NEIGHBOUR]
    hi_ = [x for x in nn if x > n and x % 2 == n % 2 and x - n <= NEIGHBOUR]
    if not (lo_ and hi_):
        return None
    a, b = max(lo_), min(hi_)
    f = (n - a) / (b - a)
    (la1, lo1), (la2, lo2) = nn[a], nn[b]
    return (round(la1 + f * (la2 - la1), 6), round(lo1 + f * (lo2 - lo1), 6), 'interp')


def main():
    if not os.path.exists(DB): print('спочатку крок 1'); sys.exit(1)
    print('1) адресна база OpenStreetMap, тільки місто Київ')
    rows = fetch()
    if not rows:
        print('   ПОМИЛКА: адресну базу не отримано. Спробуйте пізніше.')
        sys.exit(1)

    exact = {}; streets = collections.defaultdict(list)
    for st, h, la, lo in rows:
        ns = norm(st)
        if not ns: continue
        exact.setdefault((ns, nh(h)), (la, lo))
        streets[ns].append((la, lo))

    # центроїд вулиці - лише якщо вулиця компактна (не розкидана по місту)
    centro = {}
    for k, v in streets.items():
        if spread_km(v) <= 6.0:
            centro[k] = (sum(a for a, b in v)/len(v), sum(b for a, b in v)/len(v))
    print(f'   вулиць: {len(streets):,}, з них придатні для прив\'язки без номера: {len(centro):,}')

    conn = sqlite3.connect(DB)
    conn.execute('DROP TABLE IF EXISTS geo')
    conn.execute('CREATE TABLE geo(doc_id TEXT PRIMARY KEY, lat REAL, lon REAL, precision TEXT)')
    conn.commit()

    # Адреса з проходу по текстах (крок 6, data/teksty) перемагає адресу
    # кроку 1: її взято чинним addr.extract() з повного тексту. Документ,
    # у якого прохід адреси не знайшов або вона прихована (АДРЕСА_N), на
    # карту вже не йде, хоч би що колись знайшов старий витяг.
    tk = TK.load_done()
    todo = []
    for doc, street, house in conn.execute("SELECT doc_id, street, house FROM events"):
        r = tk.get(doc)
        if r is not None:
            street, house = r['street'] or None, r['house'] or None
        if street:
            todo.append((doc, street, house, r['klass'] if r else ''))
    print(f'2) зіставлення заново: {len(todo):,} записів (з проходу по текстах: {len(tk):,})')

    tail = collections.defaultdict(list)
    for k in centro:
        p = k.split()
        if len(p) > 1: tail[p[-1]].append(k)

    # Номери будинків вулиці цифрою — для «20Б → 20» і розстановки між
    # сусідами (PLAN-TEKSTY.md, 4б; RISHENNYA, розд. 21).
    nums = collections.defaultdict(dict)
    for (k, h), ll in exact.items():
        if h.isdigit(): nums[k].setdefault(int(h), ll)

    out = []; st = collections.Counter()
    for doc, street, house, klass in todo:
        ns, h = norm(street), nh(house)
        hit = None
        if ' / ' in street:
            # перехрестя (addr.extract, level='cross'): «вул. X / вул. Y»
            hit = cross_point(*street.split(' / ', 1), streets, centro, tail)
        elif h and (ns, h) in exact:
            hit = (*exact[(ns, h)], 'house')
        elif h and klass == 'B' and (near := nearby(ns, h, exact, nums)):
            hit = near
        elif ns in centro:
            hit = (*centro[ns], 'street')
        else:
            cand = tail.get(ns.split()[-1], []) if ns else []
            if len(cand) == 1:
                k = cand[0]
                hit = (*(exact.get((k, h)) or centro[k]), 'house' if (k, h) in exact else 'street')
        if hit: out.append((doc, hit[0], hit[1], hit[2])); st[hit[2]] += 1
        else: st['не знайдено'] += 1
    conn.executemany('INSERT OR REPLACE INTO geo VALUES(?,?,?,?)', out)
    conn.commit()
    print('\n=== ГОТОВО ===')
    for k, v in st.most_common():
        print(f'  {k:14} {v:8,}  {100*v/max(len(todo),1):5.1f}%')

if __name__ == '__main__':
    main()
