# -*- coding: utf-8 -*-
"""Е12б, А2 (ZAVDANNYA-36): будівлі OSM з адресами — еталон точності точок.

Знімок OSM карти (osm_kyiv_city.json) має для адреси лише одну точку —
вузол або центр прямокутника будівлі; полігонів будівель з адресами в нас
немає. Беремо їх з того самого файлу Geofabrik, що й «Знімок OSM»
(Overpass — лише запасний шлях: CLAUDE.md, приклад 07.10).

Вихід (gzip JSON): {"adr": [[вулиця, номер, джерело ('way'|'node'|'rel'),
точка_як_у_знімку [lat, lon], центроїд будівлі [lat, lon] | null, площа м²,
полігон [[lat, lon], ...] (≤ 40 вершин) | null]],
"ob": [[назва, тип, центроїд, площа, полігон]]} — названі великі об'єкти
(ТЦ, ринки, вокзали, станції), для підходу «сам об'єкт».

Запуск: python e12b_budivli.py kyiv.osm.pbf vyhid.json.gz
"""
import sys, json, gzip, math, collections


def main(pbf, out):
    import osmium, shapely
    from shapely.geometry import Polygon, Point
    from shapely import STRtree
    R = 6371000.0
    def plosha(poly):
        c = poly.centroid
        k = (math.pi / 180) * R
        return abs(poly.area) * k * k * math.cos(math.radians(c.y))
    def sproshch(poly):
        g = poly.exterior.coords
        step = max(1, len(g) // 40)
        return [[round(y, 6), round(x, 6)] for x, y in list(g)[::step]]
    blds, adr_nodes, ob = [], [], []
    OB = lambda t: (t.get('shop') == 'mall' or t.get('amenity') in ('marketplace',) or
                    t.get('railway') == 'station' or t.get('public_transport') == 'station' or
                    (t.get('building') in ('retail', 'commercial', 'train_station', 'supermarket') and t.get('name')))
    fp = osmium.FileProcessor(pbf).with_locations().with_areas()
    for o in fp:
        tags = {x.k: x.v for x in o.tags}
        if o.is_node():
            if 'addr:housenumber' in tags and 'addr:street' in tags and o.location.valid():
                adr_nodes.append((tags['addr:street'], tags['addr:housenumber'], o.location.lat, o.location.lon))
            continue
        if not o.is_area(): continue
        if not ('building' in tags or OB(tags)): continue
        try:
            rings = list(o.outer_rings())
            if not rings: continue
            r0 = max(rings, key=lambda r: len(r))
            poly = Polygon([(n.lon, n.lat) for n in r0])
            if not poly.is_valid: poly = poly.buffer(0)
            if poly.is_empty or poly.geom_type != 'Polygon': continue
        except Exception:
            continue
        typ = 'way' if o.from_way() else 'rel'
        a = plosha(poly)
        if OB(tags):
            ob.append([tags.get('name', ''), tags.get('shop') or tags.get('amenity') or tags.get('railway') or tags.get('building'),
                       [round(poly.centroid.y, 6), round(poly.centroid.x, 6)], round(a), sproshch(poly)])
        if 'building' in tags:
            minx, miny, maxx, maxy = poly.bounds
            blds.append((poly, tags.get('addr:street'), tags.get('addr:housenumber'), typ,
                         ((miny + maxy) / 2, (minx + maxx) / 2), a))
    print(f'будівель {len(blds):,}, вузлів-адрес {len(adr_nodes):,}, названих об\'єктів {len(ob):,}', flush=True)
    tree = STRtree([b[0] for b in blds])
    adr = []
    for poly, st, h, typ, bbc, a in blds:
        if st and h:
            adr.append([st, h, typ, [round(bbc[0], 6), round(bbc[1], 6)],
                        [round(poly.centroid.y, 6), round(poly.centroid.x, 6)], round(a), sproshch(poly)])
    n_in = 0
    for st, h, la, lo in adr_nodes:
        ix = tree.query(Point(lo, la), predicate='within')
        if len(ix):
            poly, _s, _h, _t, _c, a = blds[int(ix[0])]
            n_in += 1
            adr.append([st, h, 'node', [round(la, 6), round(lo, 6)],
                        [round(poly.centroid.y, 6), round(poly.centroid.x, 6)], round(a), sproshch(poly)])
        else:
            adr.append([st, h, 'node', [round(la, 6), round(lo, 6)], None, None, None])
    print(f'адрес: {len(adr):,} (вузлів усередині будівлі {n_in:,})', flush=True)
    json.dump(dict(adr=adr, ob=ob), gzip.open(out, 'wt', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
