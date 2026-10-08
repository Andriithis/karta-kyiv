"""Е12, П5: названі місця без номера (позначка O в розмітці) — чи знаходяться
однозначно в OSM і чи компактні (36.12: станція чи вхід метро, ТЦ, ринок,
вокзал, сквер до ~300 м; великі парки й мости — без точки).

Джерело — data/osm_risks_raw.json (той самий знімок Geofabrik, що й модель).
"""
import os, json, math, collections, re
K = os.path.dirname(os.path.abspath(__file__))
R = os.path.abspath(os.path.join(K, '..', '..', '..'))
O = json.load(open(os.path.join(R, 'data', 'osm_risks_raw.json'), encoding='utf-8'))

def km(a, b):
    return 6371 * math.hypot(math.radians(b[0] - a[0]), math.radians(b[1] - a[1]) * math.cos(math.radians(a[0])))
def pt(e):
    return (e['lat'], e['lon']) if 'lat' in e else (e['center']['lat'], e['center']['lon'])
def rozmir(e):
    b = e.get('bounds')
    return km((b['minlat'], b['minlon']), (b['maxlat'], b['maxlon'])) * 1000 if b else 0

metro = collections.defaultdict(list)
for e in O['metro']:
    n = (e.get('tags', {}).get('name') or '').strip()
    if n: metro[n.lower()].append(pt(e))

# 23 позначки O з розмітки E12 (номер — рядок розмітки): що названо в тексті
MISTSIA = [
    (11, 'метро', 'Святошин'), (41, 'метро', 'Деміївська'), (86, 'метро', 'Лівобережна'),
    (87, 'метро', 'Лісова'), (135, 'метро', 'Дарниця'), (166, 'метро', 'Лук\'янівська'),
    (180, 'метро', 'Осокорки'), (199, 'метро', 'Славутич'), (207, 'метро', 'Теремки'),
    (220, 'метро', 'Деміївська'), (223, 'метро', 'Святошин'), (232, 'метро', 'Вокзальна'),
    (253, 'метро', 'Теремки'), (264, 'метро', 'Червоний хутір'), (303, 'метро', 'Кловська'),
    (315, 'метро', 'Олімпійська'),
    (12, 'парк', 'Райдужне'), (196, 'парк', 'Нивки'), (245, 'парк', 'Юність'),
    (113, 'міст', 'Південний'), (168, 'АЗС', 'ANP'), (300, 'вокзал', 'Центральний залізничний вокзал'),
    (321, 'площа', 'Майдан Незалежності'),
]
def poshuk(vyd, nazva):
    if vyd == 'метро':
        ps = metro.get(nazva.lower().replace('\'', '’')) or metro.get(nazva.lower())
        if not ps: return 'не знайдено', None, None
        r = max((km(a, b) for a in ps for b in ps), default=0) * 1000
        return f'входів {len(ps)}', round(r), r <= 300
    if vyd == 'парк':
        hit = [e for e in O['park'] if nazva.lower() in (e.get('tags', {}).get('name') or '').lower()]
        if not hit: return 'не знайдено', None, False
        r = max(rozmir(e) for e in hit)
        return f'об\'єктів {len(hit)}', round(r), r <= 300
    if vyd == 'АЗС':
        hit = [e for e in O['fuel'] if nazva.lower() in json.dumps(e.get('tags', {}), ensure_ascii=False).lower()]
        return f'АЗС {nazva} у місті: {len(hit)} — неоднозначно без адреси', None, False
    if vyd == 'вокзал':
        return 'вокзал — однозначний (пл. Вокзальна, 1)', None, True
    if vyd == 'міст':
        return 'міст — понад 1 км', None, False
    return 'площа — понад 300 м', None, False

rows = []
for n, vyd, nazva in MISTSIA:
    opys, rozm, komp = poshuk(vyd, nazva)
    rows.append((n, vyd, nazva, opys, rozm, komp))
    print(n, vyd, nazva, opys, rozm, 'точка' if komp else 'без точки')
tochka = sum(1 for r in rows if r[5])
print(f'\nоднозначно й компактно: {tochka} з {len(rows)}')
json.dump(rows, open(os.path.join(K, 'e12_p5.json'), 'w', encoding='utf-8'), ensure_ascii=False)
