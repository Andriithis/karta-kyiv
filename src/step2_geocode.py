# -*- coding: utf-8 -*-
"""Крок 2. Адресна база СУВОРО в межах міста Києва + зіставлення."""
import os, re, sys, json, time, sqlite3, math, urllib.request, urllib.parse, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
DB   = os.path.join(DATA, 'events.db')
OSM  = os.path.join(DATA, 'osm_kyiv_city.json')

ENDPOINTS = ['https://overpass-api.de/api/interpreter',
             'https://overpass.kumi.systems/api/interpreter',
             'https://overpass.osm.ch/api/interpreter']

QUERY = """[out:json][timeout:600];
area["boundary"="administrative"]["admin_level"="4"]["name"="Київ"]->.k;
(node["addr:housenumber"]["addr:street"](area.k);
 way["addr:housenumber"]["addr:street"](area.k);
 relation["addr:housenumber"]["addr:street"](area.k););
out center tags;"""

TYPEWORDS = r'(вулиця|вулиці|вулицю|вул\.?|проспект[уі]?|просп\.?|бульвар[уі]?|бульв\.?|б-р|провулок|провулку|пров\.?|площа|площі|пл\.?|шосе|набережна|набережної|наб\.?|узвіз|узвозу|алея|алеї|тупик|тракт|мікрорайон)'

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

def fetch():
    if os.path.exists(OSM):
        print('   база вже завантажена (щоб перезавантажити - видаліть data/osm_kyiv_city.json)')
        return json.load(open(OSM, encoding='utf-8'))
    data = urllib.parse.urlencode({'data': QUERY}).encode()
    for ep in ENDPOINTS:
        try:
            print(f'   запит до {ep.split("/")[2]} ... (до 10 хв, це один великий запит)', flush=True)
            req = urllib.request.Request(ep, data=data, headers={'User-Agent': 'edrsr-academy/2.0'})
            with urllib.request.urlopen(req, timeout=700) as r:
                js = json.loads(r.read().decode())
            out = []
            for el in js.get('elements', []):
                t = el.get('tags', {})
                lat = el.get('lat') or (el.get('center') or {}).get('lat')
                lon = el.get('lon') or (el.get('center') or {}).get('lon')
                if lat and lon and t.get('addr:street'):
                    out.append([t['addr:street'], t.get('addr:housenumber', ''), round(lat, 6), round(lon, 6)])
            if out:
                json.dump(out, open(OSM, 'w', encoding='utf-8'), ensure_ascii=False)
                print(f'   отримано {len(out):,} адрес міста Києва')
                return out
        except Exception as ex:
            print(f'   збій: {type(ex).__name__} — пробую наступний сервер')
            time.sleep(4)
    return []

def spread_km(pts):
    la = [p[0] for p in pts]; lo = [p[1] for p in pts]
    return max(max(la)-min(la)*1, 0)*111 + (max(lo)-min(lo))*71

def main():
    if not os.path.exists(DB): print('спочатку крок 1'); return
    print('1) адресна база OpenStreetMap, тільки місто Київ')
    rows = fetch()
    if not rows: print('   не вдалось. спробуйте пізніше.'); return

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

    todo = list(conn.execute("SELECT doc_id, street, house FROM events WHERE street IS NOT NULL"))
    print(f'2) зіставлення заново: {len(todo):,} записів')

    tail = collections.defaultdict(list)
    for k in centro:
        p = k.split()
        if len(p) > 1: tail[p[-1]].append(k)

    out = []; st = collections.Counter()
    for doc, street, house in todo:
        ns, h = norm(street), nh(house)
        hit = None
        if h and (ns, h) in exact:
            hit = (*exact[(ns, h)], 'house')
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
