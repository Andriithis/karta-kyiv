# -*- coding: utf-8 -*-
"""Крок 2. Адресна база СУВОРО в межах міста Києва + зіставлення."""
import os, re, sys, json, time, sqlite3, math, urllib.request, urllib.parse, urllib.error, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import step1c_teksty as TK      # частини проходу по текстах (крок 6)
import addr as A
import podii as PD

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

# ---- ТИП ВУЛИЦІ ОКРЕМО ВІД НАЗВИ (ZAVDANNYA-32, 2.1) ----
# norm() викидає тип: «бульв. Лесі Українки» = «вул. Лесі Українки». Для
# ключа це правильно — суди пишуть тип як завгодно, — але 651 пара «вулиця +
# номер» існує в OSM у кількох місцях далі 500 м, і геокодер брав першу
# ліпшу. Тепер тип — окрема підказка, а останнє слово за районом суду.
TYPE_CANON = [  # порядок важливий: довші спершу
    (r'просп\w*|пр-т|пр\.', 'просп'), (r'бульв\w*|б-р', 'бульв'),
    (r'пров\w*', 'пров'), (r'пл\.|площ\w*|майдан', 'пл'), (r'наб\w*', 'наб'),
    (r'шосе', 'шосе'), (r'узв\w*', 'узвіз'), (r'проїзд\w*', 'проїзд'),
    (r'алея|алеї', 'алея'), (r'тупик', 'тупик'), (r'вул\w*', 'вул'),
]
TYPE_CANON = [(re.compile(r'(?:^|\s)(?:' + p + r')(?:\s|$|\.)'), c) for p, c in TYPE_CANON]
# Тип, який суди пишуть замість справжнього: «вул. Перемоги» про проспект.
# Конкретний тип у тексті (пл., пров., бульв.), якого немає серед кандидатів,
# — інша вулиця: «пл. Тараса Шевченка, 2» (Оболонь) ставала на «провулок
# Тараса Шевченка, 2» біля Майдану (2.2а).
TYPE_LOOSE = {'', 'вул'}
R_ODNA = 0.5            # км: далі — це вже різні місця з однаковою адресою


def stype(s):
    """Тип вулиці з назви OSM чи з адреси рішення; '' — не названо."""
    t = ' ' + (s or '').lower() + ' '
    for rx, canon in TYPE_CANON:
        if rx.search(t):
            return canon
    return ''


# Підпис адреси — назва вулиці як в OSM (2.3): «шосе Набережне, 25» і «вул.
# Набережне шосе, 25» в одній картці — одним підписом. Тип скорочено, як
# пишуть на карті.
# Тип у кінці назви OSM («Інститутська вулиця») — наперед, як решта підписів
# карти («вул. Інститутська»); «Набережне шосе», «Андріївський узвіз» — як є.
SKOR = [(r'^вулиця\s', 'вул. '), (r'^проспект\s', 'просп. '), (r'^бульвар\s', 'бульв. '),
        (r'^провулок\s', 'пров. '), (r'^площа\s', 'пл. '), (r'^набережна\s', 'наб. '),
        (r'^(.+)\sвулиця$', r'вул. \1'), (r'^(.+)\sпроспект$', r'просп. \1'), (r'^(.+)\sбульвар$', r'бульв. \1'),
        (r'^(.+)\sпровулок$', r'пров. \1'), (r'^(.+)\sплоща$', r'пл. \1')]


def pidpys(st):
    for a, b in SKOR:
        st = re.sub(a, b, st)
    return st


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

# Перехрестя — src/perekhrestia.py (завдання 30, ч. 4): точка перетину ліній
# OSM, а не середина між найближчими будинками двох вулиць, як було тут.

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


# ---- ГЕОКОДЕР МІСТА (КМДА) — друге джерело точних будинків ----
# Шар «Повна адреса (геокодер)» з ГІС-сервера КМДА: ~47 тис. адрес з
# координатами. Будинків, яких немає в OSM, у ньому ~1/6 (звіт 25.09); Андрій
# дозволив брати без листа (PLAN-ZAHALNYI.md, А4б). Правила ті самі, що й для
# OSM: лише точний будинок. Якщо будинок є і в OSM, лишається OSM.
#
# Знімок лежить у data/ і в git, щоб «Оновлення карти» не залежало від
# доступності ГІС-сервера. Оновити: видалити data/geokoder_kmda.csv.gz і
# запустити цей крок — він завантажить шар заново.
KMDA_ON = True          # False — точки КМДА зникають з усього (карта, модель)
KMDA = os.path.join(DATA, 'geokoder_kmda.csv.gz')
# Робочий сервер, а не stage: шар той самий (46 742 записи на обох, 06.10),
# а stage можуть вимкнути без попередження.
KMDA_URL = ('https://gisserver.kyivcity.gov.ua/mayno/rest/services/KYIV_API/'
            + urllib.parse.quote('Адреси') + '/FeatureServer/0/query')
# У 1% адрес геокодер і OSM розходяться на кілометри — однакові назви вулиць у
# різних кінцях міста, садові товариства. Тому точку КМДА беремо, лише якщо
# вона лежить біля СВОЄЇ вулиці за геометрією OSM і в межах Києва.
KMDA_NEAR = 150         # м: будинок не далі за стільки від осі своєї вулиці
KMDA_DUP = 200          # м: дві точки з тією самою адресою далі — адреса неоднозначна


def fetch_kmda():
    """[(вулиця з типом, номер, lat, lon)] зі знімка або з ГІС-сервера."""
    import csv, gzip
    if not os.path.exists(KMDA):
        print('   геокодер КМДА: завантаження шару', flush=True)
        rows, off = [], 0
        while True:
            q = urllib.parse.urlencode({'where': '1=1', 'outFields': 'type_vul,ukrnamef,addrnumb1',
                                        'returnGeometry': 'true', 'outSR': 4326, 'orderByFields': 'objectid',
                                        'resultOffset': off, 'resultRecordCount': 20000, 'f': 'json'})
            rq = urllib.request.Request(KMDA_URL + '?' + q, headers={'User-Agent': 'edrsr-academy/4.0'})
            with urllib.request.urlopen(rq, timeout=300) as r:
                js = json.loads(r.read().decode('utf-8'))
            fs = js.get('features', [])
            for f in fs:
                a, g = f['attributes'], f.get('geometry')
                if g and a.get('ukrnamef') and a.get('addrnumb1'):
                    rows.append((f"{a.get('type_vul') or ''} {a['ukrnamef']}".strip(), a['addrnumb1'],
                                 round(g['y'], 6), round(g['x'], 6)))
            if not js.get('exceededTransferLimit'):
                break
            off += len(fs)
        with gzip.open(KMDA, 'wt', encoding='utf-8', newline='') as fh:
            w = csv.writer(fh, delimiter='\t', lineterminator='\n')
            w.writerow(['street', 'house', 'lat', 'lon'])
            w.writerows(sorted(rows))
    with gzip.open(KMDA, 'rt', encoding='utf-8', newline='') as fh:
        return [(r['street'], r['house'], float(r['lat']), float(r['lon']))
                for r in csv.DictReader(fh, delimiter='\t')]


def skey(s):
    """Ключ вулиці без порядку слів: у геокодері «Корольова Академіка», у
    текстах і в OSM — «Академіка Корольова»."""
    return ' '.join(sorted(norm(s).split()))


def _m(la, lo, la0):
    return la * 111320, lo * 111320 * math.cos(math.radians(la0))


def _seg_dist(p, a, b):
    """Відстань у метрах від точки p до відрізка ab ((lat, lon))."""
    px, py = _m(*p, p[0]); ax, ay = _m(*a, p[0]); bx, by = _m(*b, p[0])
    dx, dy = bx - ax, by - ay
    t = 0 if dx == dy == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def street_lines(streets):
    """Ключ вулиці -> відрізки й точки OSM, біля яких мусить лежати будинок:
    осі вулиць (шар roads кроку 2b і мережа кроку 2c) і, про запас, самі
    адреси OSM цієї вулиці — малих провулків у шарі доріг буває немає."""
    lines = collections.defaultdict(list)
    raw = os.path.join(DATA, 'osm_risks_raw.json')
    if os.path.exists(raw):
        import vidrizky as VR
        for w in VR.vulytsi(json.load(open(raw, encoding='utf-8'))):
            nm = (w.get('tags') or {}).get('name')
            g = [(q['lat'], q['lon']) for q in w.get('geometry') or []]
            if nm and len(g) > 1: lines[skey(nm)] += list(zip(g, g[1:]))
    net = os.path.join(DATA, 'network.json')
    if os.path.exists(net):
        for it in json.load(open(net, encoding='utf-8')).get('items', []):
            g = [tuple(q) for q in it[0]]
            if it[1] and len(g) > 1: lines[skey(it[1])] += list(zip(g, g[1:]))
    for ns, pts in streets.items():
        lines[skey(ns)] += [(p, p) for p in pts]
    return lines


R_LANKA = 0.4          # км: сусідні адреси однієї вулиці не далі


def komponenty(keys, streets_t):
    """(назва, тип, точка) -> номер зв'язної частини адрес вулиці."""
    out = {}
    for ns, typ in keys:
        pts = sorted(set(streets_t.get((ns, typ), [])))
        par = list(range(len(pts)))
        def root(i):
            while par[i] != i:
                par[i] = par[par[i]]; i = par[i]
            return i
        for i in range(len(pts)):
            for j in range(i + 1, len(pts)):
                if abs(pts[j][0] - pts[i][0]) * 111 > R_LANKA: break   # sorted за широтою
                if spread_km([pts[i], pts[j]]) <= R_LANKA:
                    par[root(i)] = root(j)
        for i, p in enumerate(pts):
            out[(ns, typ, p)] = (ns, typ, root(i))
    return out


def district_of(p, borders):
    """Назва району, у якому точка (data/borders.json), або None."""
    for name, ring in borders.items():
        if in_kyiv(p, [ring]):
            return name
    return None


def in_kyiv(p, rings):
    """Точка в одному з районів (data/borders.json, кільця [lat, lon])."""
    la, lo = p
    for ring in rings:
        inside = False
        for (a1, o1), (a2, o2) in zip(ring, ring[1:] + ring[:1]):
            if (o1 > lo) != (o2 > lo) and la < (a2 - a1) * (lo - o1) / (o2 - o1) + a1:
                inside = not inside
        if inside:
            return True
    return False


def kmda_index(streets):
    """(ключ вулиці, номер) -> (lat, lon) лише для перевірених точок КМДА."""
    rows = fetch_kmda()
    lines = street_lines(streets)
    rings = list(json.load(open(os.path.join(DATA, 'borders.json'), encoding='utf-8')).values())
    st = collections.Counter(); cand = collections.defaultdict(list)
    for s, h, la, lo in rows:
        k = skey(s); p = (la, lo)
        if not in_kyiv(p, rings):
            st['поза Києвом'] += 1; continue
        near = min((_seg_dist(p, a, b) for a, b in lines.get(k, ())), default=None)
        if near is None:
            st['вулиці немає в OSM'] += 1; continue
        if near > KMDA_NEAR:
            st[f'далі {KMDA_NEAR} м від своєї вулиці'] += 1; continue
        cand[(k, nh(h))].append((la, lo, stype(s), s))
    # Однакова адреса в кількох місцях — тепер не викидається одразу: усі
    # кандидати з типом ідуть у pick(), як і в OSM (2.1). Викидаються лише
    # ті, що й з типом лишаються неоднозначними.
    idx = {}
    for key, ps in cand.items():
        idx[key] = ps; st['прийнято'] += len(ps)
        if spread_km([(a, b) for a, b, _t, _s in ps]) > KMDA_DUP / 1000:
            st['кілька місць (вирішує тип чи суд)'] += len(ps)
    print(f'   геокодер КМДА: {len(rows):,} адрес; ' + ', '.join(f'{k} {v:,}' for k, v in st.most_common()))
    return idx


def main():
    if not os.path.exists(DB): print('спочатку крок 1'); sys.exit(1)
    print('1) адресна база OpenStreetMap, тільки місто Київ')
    rows = fetch()
    if not rows:
        print('   ПОМИЛКА: адресну базу не отримано. Спробуйте пізніше.')
        sys.exit(1)

    # Усі кандидати адреси, а не перший (2.1): (назва, номер) -> [(lat, lon,
    # тип, назва OSM)] — «kand», бо «cand» нижче вже зайняте хвостом назви. exact — лише однозначні: усі кандидати в R_ODNA; на
    # ньому тримаються «20Б → 20» і розстановка між сусідами.
    kand = collections.defaultdict(list); streets = collections.defaultdict(list)
    streets_t = collections.defaultdict(list)
    for st, h, la, lo in rows:
        ns = norm(st)
        if not ns: continue
        kand[(ns, nh(h))].append((la, lo, stype(st), st))
        streets[ns].append((la, lo)); streets_t[(ns, stype(st))].append((la, lo))
    exact = {k: (c[0][0], c[0][1]) for k, c in kand.items()
             if spread_km([(a, b) for a, b, _t, _s in c]) <= R_ODNA}
    n_bagato = sum(1 for k, c in kand.items() if k not in exact)
    print(f'   адрес OSM у кількох місцях далі {R_ODNA * 1000:.0f} м: {n_bagato:,}')
    # Та сама адреса далі 500 м — не завжди однойменні вулиці: «просп.
    # Академіка Глушкова, 1» — кілька будівель Експоцентру на одній вулиці.
    # Однойменні вулиці — розірвані скупчення адрес (Лугова на Оболоні й у
    # Бортничах); одна вулиця — неперервний ланцюжок адрес. Тож для вулиць
    # з такими адресами — зв'язні частини адрес з кроком до R_LANKA.
    KOMP = komponenty({(k[0], x[2]) for k, c in kand.items() if k not in exact for x in c}, streets_t)

    # центроїд вулиці - лише якщо вулиця компактна (не розкидана по місту)
    centro = {}
    for k, v in streets.items():
        if spread_km(v) <= 6.0:
            centro[k] = (sum(a for a, b in v)/len(v), sum(b for a, b in v)/len(v))
    # центроїд з типом: «бульв. Лесі Українки» і «вул. Лесі Українки» — різні
    centro_t = {k: (sum(a for a, b in v)/len(v), sum(b for a, b in v)/len(v))
                for k, v in streets_t.items() if k[1] and spread_km(v) <= 6.0}
    print(f'   вулиць: {len(streets):,}, з них придатні для прив\'язки без номера: {len(centro):,}')

    conn = sqlite3.connect(DB)
    conn.execute('DROP TABLE IF EXISTS geo')
    # source — звідки точка: osm | kmda. Щоб точки геокодера можна було
    # зняти одним фільтром, не перераховуючи решти. adresa — підпис точки,
    # якщо він не з адреси документа: «перехрестя вул. X і вул. Y».
    conn.execute('CREATE TABLE geo(doc_id TEXT PRIMARY KEY, lat REAL, lon REAL, precision TEXT, source TEXT, '
                 'adresa TEXT)')
    conn.commit()
    # Перехрестя — точкою перетину ліній OSM (завдання 30, ч. 4) за шаром
    # вулиць разом із магістралями (vidrizky.vulytsi)
    import perekhrestia as PX
    rawp = os.path.join(DATA, 'osm_risks_raw.json')
    rw = json.load(open(rawp, encoding='utf-8')) if os.path.exists(rawp) else {}
    import vidrizky as VR
    PXI = PX.Perekhrestia(VR.vulytsi(rw))
    if not rw.get('dorogy_velyki'):
        print('   магістралей (dorogy_velyki) у кеші OSM немає — перехрестя з проспектами не знайдуться')
    del rw
    PXST = collections.Counter(); PXPR = []

    # Адреса з проходу по текстах (крок 6, data/teksty) перемагає адресу
    # кроку 1: її взято чинним addr.extract() з повного тексту. Документ,
    # у якого прохід адреси не знайшов або вона прихована (АДРЕСА_N), на
    # карту вже не йде, хоч би що колись знайшов старий витяг.
    tk = TK.load_done()
    # Прийменник, що прилип до номера старим розбором («1/5 у м.Києві» ->
    # «1/5У», «11 в м.Києві» -> «11В»), знімаємо тут, за текстом, з якого
    # взято адресу, — тим самим addr.unglue, що й підпис точки в step3_map.
    fab = PD.load_fab(conn)
    todo = []; n_unglued = 0
    COURT_D = {}
    from map_problems import COURTS
    for doc, court in conn.execute("SELECT doc_id, court FROM events"):
        COURT_D[doc] = COURTS.get(court)      # лише районні суди; решта — None
    for doc, street, house in conn.execute("SELECT doc_id, street, house FROM events"):
        r = tk.get(doc)
        if r is not None:
            street, house = r['street'] or None, r['house'] or None
        h2 = A.unglue(house, (r['addr_sentence'] or r['fab']) if r else fab.get(doc, ''))
        n_unglued += h2 != house
        # Подія без номера будинку — шукаємо у фабулі перехрестя двох вулиць
        # (завдання 30, 4.1): «на перехресті вул. X та вул. Y», «на розі …»
        px = None
        if not h2:
            if street and ' / ' in street: px = tuple(street.split(' / ', 1))
            elif r is not None: px = A.perekhrestia(r['fab'] or '')
        if px:
            todo.append((doc, street or px[0], None, r['klass'] if r else '', px))
        elif street:
            todo.append((doc, street, h2, r['klass'] if r else '', None))
    print(f'   номер без прилиплого прийменника («1/5У» -> «1/5»): {n_unglued:,}')
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

    kmda = kmda_index(streets) if KMDA_ON else {}
    borders = json.load(open(os.path.join(DATA, 'borders.json'), encoding='utf-8'))
    _dcache = {}
    def dist_of(la, lo):
        k = (la, lo)
        if k not in _dcache: _dcache[k] = district_of(k, borders)
        return _dcache[k]
    PICK = collections.Counter(); PRYKL = []

    def pick(c, typ, court_d, ns=''):
        """Точка для адреси з кандидатів [(lat, lon, тип, назва OSM)].
        Однойменні вулиці: спершу тип, потім район суду; лишилось кілька далі
        R_ODNA одна від одної — точки немає (краще без точки, ніж у іншому
        кінці міста). -> (кандидат | None, як вирішено)"""
        spread = lambda xs: spread_km([(a, b) for a, b, _t, _s in xs])
        if not c: return None, ''
        if spread(c) <= R_ODNA: return c[0], ''
        def odna(xs):
            """усі на одній зв'язній вулиці -> центральний кандидат"""
            ids = {KOMP.get((ns, x[2], (x[0], x[1]))) for x in xs}
            if len(ids) == 1 and None not in ids:
                return min(xs, key=lambda x: sum(spread_km([(x[0], x[1]), (y[0], y[1])]) for y in xs))
            return None
        x = odna(c)
        if x: return x, 'одна вулиця, кілька будівель'
        def vyrish(xs, why):
            if xs and spread(xs) <= R_ODNA: return xs[0], why
            x = odna(xs) if xs else None
            return (x, why) if x else (None, '')
        # Конкретний тип у тексті (пл., пров., бульв.) — сильна підказка; «вул.»
        # суди пишуть і про проспект, і про бульвар, тому вона — після суду:
        # інакше «вул. Лесі Українки, 3» Печерського суду ставала на вулицю
        # Лесі Українки на Троєщині замість бульвару.
        if typ and typ not in TYPE_LOOSE:
            same = [x for x in c if x[2] == typ]
            if not same:
                # такого типу серед кандидатів немає — лише «вулиці»; інакше
                # це інша вулиця
                same = [x for x in c if x[2] in TYPE_LOOSE]
                if not same: return None, 'тип не збігся'
            c = same
            r = vyrish(c, 'тип')
            if r[0]: return r
        if court_d:
            vr = [x for x in c if dist_of(x[0], x[1]) == court_d]
            r = vyrish(vr, 'район суду')
            if r[0]: return r
            # У районі суду — комплекс будівель з цією адресою і одна далека
            # точка (Лугова, 12 на Оболоні: 12 будівель і одна за 6 км, теж
            # в Оболонському). Скупчення з ≥ 80% кандидатів (і ≥ 3) — воно.
            if len(vr) >= 3:
                gr = collections.defaultdict(list)
                for x in vr: gr[KOMP.get((ns, x[2], (x[0], x[1])))].append(x)
                big = max(gr.values(), key=len)
                if len(big) >= 3 and len(big) >= .8 * len(vr):
                    return min(big, key=lambda x: sum(spread_km([(x[0], x[1]), (y[0], y[1])]) for y in big)), 'район суду'
        if typ in TYPE_LOOSE and typ:
            r = vyrish([x for x in c if x[2] == typ], 'тип')
            if r[0]: return r
        return None, 'неоднозначна'

    out = []; st = collections.Counter()
    for doc, street, house, klass, px in todo:
        ns, h = norm(street), nh(house)
        typ = stype(street)
        hit = None; src = 'osm'; adr = None
        if px:
            # перехрестя: точка перетину ліній OSM або нічого (4.2)
            PXST['знайдено у фабулі'] += 1
            la, lo, why = PXI.tochka(*px)
            if la is not None:
                hit = (la, lo, 'cross'); adr = PX.adresa(*px)
                PXST['поставлено'] += 1
                PXPR.append((doc, px, la, lo))
            else:
                PXST['відкинуто: ' + why] += 1
                # як і раніше: центр вулиці, на карту не йде
                if ns in centro: hit = (*centro[ns], 'street')
        elif ' / ' in street:
            hit = None
        elif h and (ns, h) in kand:
            x, why = pick(kand[(ns, h)], typ, COURT_D.get(doc), ns)
            PICK[why or 'одна'] += 1
            if x:
                hit = (x[0], x[1], 'house'); adr = pidpys(x[3])
                if why and len(PRYKL) < 400:
                    PRYKL.append((street, house, why, kand[(ns, h)][0], x))
            elif len(PRYKL) < 400:
                PRYKL.append((street, house, why, kand[(ns, h)][0], None))
        # Точний будинок КМДА — раніше за «20Б біля 20»: це сам будинок, а
        # не місце поруч.
        elif h and (skey(street), h) in kmda:
            x, why = pick(kmda[(skey(street), h)], typ, COURT_D.get(doc))
            PICK['КМДА: ' + (why or 'одна')] += 1
            # підпис КМДА не беремо: там «бульвар Шевченка Тараса» — прізвищем наперед
            if x: hit = (x[0], x[1], 'house'); src = 'kmda'
        elif h and klass == 'B' and (near := nearby(ns, h, exact, nums)):
            hit = near
        elif typ and (ns, typ) in centro_t:
            hit = (*centro_t[(ns, typ)], 'street')
        elif ns in centro:
            hit = (*centro[ns], 'street')
        else:
            cand = tail.get(ns.split()[-1], []) if ns else []
            if len(cand) == 1:
                k = cand[0]
                hit = (*(exact.get((k, h)) or centro[k]), 'house' if (k, h) in exact else 'street')
        if hit:
            out.append((doc, hit[0], hit[1], hit[2], src, adr))
            st[hit[2] + (' (КМДА)' if src == 'kmda' else '')] += 1
        else: st['не знайдено'] += 1
    conn.executemany('INSERT OR REPLACE INTO geo VALUES(?,?,?,?,?,?)', out)
    conn.commit()
    print('\n=== ГОТОВО ===')
    for k, v in st.most_common():
        print(f'  {k:14} {v:8,}  {100*v/max(len(todo),1):5.1f}%')
    print('перехрестя: ' + ', '.join(f'{k} {v:,}' for k, v in PXST.most_common()))
    # Журнал однойменних (2.1): скільки вирішено типом, районом суду, скільки
    # без точки, і приклади «було (перший кандидат) -> стало»
    print('однойменні адреси: ' + ', '.join(f'{k} {v:,}' for k, v in PICK.most_common()))
    import random
    for s_, h_, why, was, now in random.Random(32).sample(PRYKL, min(10, len(PRYKL))):
        print(f'   {s_}, {h_}: {why}; було {was[3]} ({was[0]:.4f}, {was[1]:.4f}) -> '
              + (f'{now[3]} ({now[0]:.4f}, {now[1]:.4f})' if now else 'без точки'))
    # 20 випадкових для ручної перевірки (адреса з фабули -> точка)
    import random
    for doc, px, la, lo in random.Random(30).sample(PXPR, min(20, len(PXPR))):
        print(f'   {doc}  {PX.adresa(*px)}  ->  {la}, {lo}')

if __name__ == '__main__':
    main()
