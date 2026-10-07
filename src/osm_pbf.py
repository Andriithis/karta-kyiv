# -*- coding: utf-8 -*-
"""Знімок OSM з файлу Geofabrik замість Overpass (рішення Андрія 07.10).

Overpass тижнями віддавав 504, і чотиригодинний «Знімок OSM» обривався на
важких шарах. Файл України з Geofabrik оновлюється щодня й качається за
хвилину; з нього той самий знімок збирається локально, без чужого сервера.

  py -3 src/osm_pbf.py mezha <вихід.geojson>   межа Києва + 2 км для osmium extract
  py -3 src/osm_pbf.py <kyiv.osm.pbf>          data/osm_risks_raw.json і osm_kyiv_city.json

Запити НЕ переписуються вдруге: беруться ті самі рядки Overpass QL з
step2b (LIGHT, HEAVY, PLYTKY, OUTMODE) і розбираються тут. Нова категорія в
step2b одразу з'являється і в знімку з Geofabrik, а формат файлів той самий,
тож кроки 2, 2b, 2c не міняються. Overpass лишається запасним шляхом
(osm.yml, «джерело: overpass»).
"""
import os, sys, re, json, math, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import step2b_risks as B

DATA = B.DATA
OSM_ADR = os.path.join(DATA, 'osm_kyiv_city.json')
BUFER_M = 2000

# Підмножина Overpass QL, якою написано step2b: тип, фільтри тегів, (area.k)
ST = re.compile(r'(nwr|node|way|rel(?:ation)?)((?:\["[^"]+"(?:(?:=|~|!=)"[^"]*")?\])+)')
FL = re.compile(r'\["([^"]+)"(?:(=|~|!=)"([^"]*)")?\]')


def zapyty():
    """{ключ: (оператори, режим out)}; оператор — (типи, [(тег, оп, значення)])."""
    out = {}
    def rozbir(q):
        ops = []
        for typ, fl in ST.findall(q):
            t = {'nwr': {'n', 'w', 'r'}, 'node': {'n'}, 'way': {'w'}}.get(typ, {'r'})
            ops.append((t, [(k, op, re.compile(v) if op == '~' else v) for k, op, v in FL.findall(fl)]))
        return ops
    for k, q in B.LIGHT.items():
        out[k] = (rozbir(q), q[q.rindex('out'):])
    for k, sel in list(B.HEAVY.items()) + list(B.PLYTKY.items()):
        out[k] = (rozbir(sel), B.OUTMODE.get(k, 'out center;'))
    for k, (ops, _m) in out.items():
        assert ops, f'запит {k} не розібрано — розширте ST у osm_pbf.py'
    return out


def pidkhodyt(tags, filtry):
    for k, op, v in filtry:
        x = tags.get(k)
        if x is None: return False
        if op == '=' and x != v: return False
        if op == '!=' and x == v: return False
        if op == '~' and not v.search(x): return False
    return True


def mezha_kyieva(pbf):
    """Межа міста — та сама область, що area.k в Overpass (admin_level 4)."""
    import osmium, shapely
    from shapely.geometry import Polygon, MultiPolygon
    fp = osmium.FileProcessor(pbf).with_areas(osmium.filter.TagFilter(('boundary', 'administrative')))
    for o in fp:
        if not o.is_area() or o.from_way(): continue
        t = {x.k: x.v for x in o.tags}
        if t.get('admin_level') == '4' and t.get('name') == 'Київ':
            polys = []
            for outer in o.outer_rings():
                ext = [(n.lon, n.lat) for n in outer]
                holes = [[(n.lon, n.lat) for n in inner] for inner in o.inner_rings(outer)]
                polys.append(Polygon(ext, holes))
            g = MultiPolygon(polys).buffer(0)
            shapely.prepare(g)
            return g
    # Обрізаний витяг (не --strategy smart) втрачає частину кілець межі — тоді
    # межа з районів data/borders.json: та сама лінія, лише без зайвих точок
    from shapely.ops import unary_union
    print('   межі Києва (admin_level 4) у файлі немає — беру райони з data/borders.json')
    rings = json.load(open(os.path.join(DATA, 'borders.json'), encoding='utf-8')).values()
    g = unary_union([Polygon([(lo, la) for la, lo in r]).buffer(0) for r in rings])
    shapely.prepare(g)
    return g


def mezha_bufer(vyhid):
    """Межа Києва з data/borders.json (райони) + 2 км — для osmium extract."""
    from shapely.geometry import Polygon, mapping
    from shapely.ops import unary_union, transform
    rings = json.load(open(os.path.join(DATA, 'borders.json'), encoding='utf-8')).values()
    kx = 111320 * math.cos(math.radians(50.45))
    m = unary_union([Polygon([(lo * kx, la * 111320) for la, lo in r]).buffer(0) for r in rings])
    g = transform(lambda x, y: (x / kx, y / 111320), m.buffer(BUFER_M).simplify(50))
    json.dump({'type': 'Feature', 'properties': {}, 'geometry': mapping(g)}, open(vyhid, 'w'))
    print(f'межа + {BUFER_M} м -> {vyhid}')


def main(pbf):
    import osmium, numpy as np, shapely
    Q = zapyty()
    # індекс за першим тегом оператора — інакше кожен об'єкт перевірявся б
    # усіма ~50 запитами
    idx = collections.defaultdict(list)
    for k, (ops, _m) in Q.items():
        for typ, fl in ops: idx[fl[0][0]].append((k, typ, fl))
    kliuchi = set(idx) | {'addr:housenumber'}
    misto = mezha_kyieva(pbf)

    def u_misti(xs, ys):
        return bool(shapely.contains_xy(misto, np.asarray(xs), np.asarray(ys)).any())

    raw = {k: [] for k in Q}
    adr = []
    st = collections.Counter()
    fp = (osmium.FileProcessor(pbf).with_locations().with_areas()
          .with_filter(osmium.filter.KeyFilter(*kliuchi)))
    for o in fp:
        if o.is_node(): typ = 'n'
        elif o.is_way(): typ = 'w'
        elif o.is_area():
            # закриті лінії вже прийшли як way; з площ беремо лише відносини
            if o.from_way(): continue
            typ = 'r'
        else: continue
        tags = {x.k: x.v for x in o.tags}
        hits = [k for t in tags for (k, ty, fl) in idx.get(t, ()) if typ in ty and pidkhodyt(tags, fl)]
        is_adr = typ != 'r' and 'addr:housenumber' in tags and 'addr:street' in tags
        if not hits and not is_adr: continue
        # геометрія: вузол — точка; лінія — вершини; відношення — зовнішні кільця
        if typ == 'n':
            if not o.location.valid(): continue
            pts = [(o.location.lat, o.location.lon)]
        elif typ == 'w':
            pts = [(n.location.lat, n.location.lon) for n in o.nodes if n.location.valid()]
        else:
            pts = [(n.lat, n.lon) for r in o.outer_rings() for n in r]
        if not pts: st['без координат'] += 1; continue
        # (area.k) в Overpass: об'єкт хоч частиною в межах міста
        if not u_misti([p[1] for p in pts], [p[0] for p in pts]):
            st['поза Києвом'] += 1; continue
        las, los = [p[0] for p in pts], [p[1] for p in pts]
        bb = {'minlat': round(min(las), 7), 'minlon': round(min(los), 7),
              'maxlat': round(max(las), 7), 'maxlon': round(max(los), 7)}
        c = {'lat': round((bb['minlat'] + bb['maxlat']) / 2, 7), 'lon': round((bb['minlon'] + bb['maxlon']) / 2, 7)}
        oid = o.orig_id() if typ == 'r' else o.id
        tname = {'n': 'node', 'w': 'way', 'r': 'relation'}[typ]
        if is_adr:
            p = pts[0] if typ == 'n' else (c['lat'], c['lon'])
            adr.append([tags['addr:street'], tags['addr:housenumber'], round(p[0], 6), round(p[1], 6)])
        for k in dict.fromkeys(hits):
            mode = Q[k][1]
            el = {'type': tname, 'id': oid}
            if typ == 'n':
                el['lat'], el['lon'] = round(pts[0][0], 7), round(pts[0][1], 7)
            elif 'geom' in mode:
                el['bounds'] = bb
                el['geometry'] = [{'lat': round(a, 7), 'lon': round(b_, 7)} for a, b_ in pts]
            else:
                if 'center' in mode: el['center'] = c
                if ' bb' in mode: el['bounds'] = bb
            if 'skel' not in mode: el['tags'] = tags
            raw[k].append(B.stysnuty(k, el) if k in B.HEAVY else el)
    # порядок як в Overpass: вузли, лінії, відношення, усередині — за id
    por = {'node': 0, 'way': 1, 'relation': 2}
    for k in raw: raw[k].sort(key=lambda e: (por[e['type']], e['id']))
    print('пропущено: ' + ', '.join(f'{k} {v:,}' for k, v in st.items()))
    for k in raw: print(f'   {k:16} {len(raw[k]):>8,}')
    print(f'   {"адреси":16} {len(adr):>8,}')
    nema = [k for k in B.OBOV if not raw.get(k)]
    if nema: sys.exit('порожні обов\'язкові категорії: ' + ', '.join(nema))
    B.zberehty(raw)
    tmp = OSM_ADR + '.tmp'
    json.dump(adr, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False)
    os.replace(tmp, OSM_ADR)
    print(f'готово: {B.RAW}, {OSM_ADR}')


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == 'mezha':
        mezha_bufer(sys.argv[2])
    elif len(sys.argv) == 2:
        main(sys.argv[1])
    else:
        sys.exit(__doc__)
