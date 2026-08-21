# -*- coding: utf-8 -*-
"""Крок 2c. Мережевий аналіз: betweenness (потенційна прохідність) вуличних відрізків.

Ідея (Davies & Bishop, 2014): рахуємо, як часто відрізок вулиці потрапляє
у найкоротші шляхи між житлом і цільовими об'єктами. Це модель пішохідного
потоку, побудована лише з геометрії мережі — без даних про реальний потік,
яких в Україні не існує.
"""
import os, sys, json, math, time, heapq, random, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
RAW  = os.path.join(DATA, 'osm_risks_raw.json')
OUT  = os.path.join(DATA, 'network.json')

SNAP   = 5          # округлення координат вузла, знаків після коми (~1 м)
MAX_M  = 1800       # максимальна довжина пішого маршруту, метрів
SAMPLE = int(os.environ.get('ROUTES', '6000'))   # скільки пар «житло -> ціль» моделювати
random.seed(17)

def mdeg(lat): return 111320.0, 111320.0 * math.cos(math.radians(lat))

def dist_m(a, b):
    my, mx = mdeg((a[0] + b[0]) / 2)
    return math.hypot((a[0]-b[0]) * my, (a[1]-b[1]) * mx)

def key(lat, lon): return (round(lat, SNAP), round(lon, SNAP))

def build_graph(ways):
    """вузли = точки геометрії, ребра = відрізки між сусідніми точками"""
    adj = collections.defaultdict(list)
    seg = {}          # (u,v) -> (way_id, name, довжина)
    for w in ways:
        g = w.get('geometry')
        if not g or len(g) < 2: continue
        t = w.get('tags', {})
        nm = t.get('name', '')
        wid = w.get('id')
        pts = [key(p['lat'], p['lon']) for p in g]
        for u, v in zip(pts, pts[1:]):
            if u == v: continue
            d = dist_m(u, v)
            if d <= 0: continue
            adj[u].append((v, d)); adj[v].append((u, d))
            seg[(u, v)] = seg[(v, u)] = (wid, nm, d)
    return adj, seg

def nearest_node(adj_keys_grid, lat, lon, cell=0.002, rad=250):
    my, mx = mdeg(lat)
    n = int(max(rad/my, rad/mx)/cell) + 1
    ci, cj = int(lat/cell), int(lon/cell)
    best, bd = None, 1e18
    for i in range(ci-n, ci+n+1):
        for j in range(cj-n, cj+n+1):
            for p in adj_keys_grid.get((i, j), ()):
                d = math.hypot((p[0]-lat)*my, (p[1]-lon)*mx)
                if d < bd: bd, best = d, p
    return best if bd <= rad else None

def dijkstra_path(adj, src, dst, limit):
    """найкоротший шлях; повертає список ребер або None"""
    dist = {src: 0.0}; prev = {}
    pq = [(0.0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == dst: break
        if d > dist.get(u, 1e18): continue
        if d > limit: return None
        for v, w in adj[u]:
            nd = d + w
            if nd < dist.get(v, 1e18):
                dist[v] = nd; prev[v] = u
                heapq.heappush(pq, (nd, v))
    if dst not in dist: return None
    path, cur = [], dst
    while cur != src:
        p = prev[cur]; path.append((p, cur)); cur = p
    return path

def main():
    if not os.path.exists(RAW):
        print('немає data/osm_risks_raw.json — спершу запустіть 2b-RISKS'); sys.exit(1)
    raw = json.load(open(RAW, encoding='utf-8'))
    roads = raw.get('roads', []); foot = raw.get('foot', [])
    houses = raw.get('houses', [])
    print(f'дороги: {len(roads):,}   пішохідні шляхи: {len(foot):,}   будинки: {len(houses):,}')

    print('1) будую граф пішохідної мережі...')
    adj, seg = build_graph(roads + foot)
    print(f'   вузлів: {len(adj):,}   ребер: {len(seg)//2:,}')

    grid = collections.defaultdict(list)
    for p in adj: grid[(int(p[0]/0.002), int(p[1]/0.002))].append(p)

    def centers(els):
        out = []
        for el in els:
            la = el.get('lat') or (el.get('center') or {}).get('lat')
            lo = el.get('lon') or (el.get('center') or {}).get('lon')
            if la and lo: out.append((la, lo))
        return out

    origins = centers(houses)
    targets = []
    for k in ('school', 'transit', 'alcohol', 'shop24'):
        targets += centers(raw.get(k, []))
    print(f'2) початки (житло): {len(origins):,}   цілі: {len(targets):,}')

    print(f'3) моделюю {SAMPLE:,} маршрутів (це найдовша частина)...')
    load = collections.Counter()
    ok = 0; t0 = time.time()
    for i in range(SAMPLE):
        if i and i % 500 == 0:
            print(f'   {i:,} / {SAMPLE:,}   вдалих {ok:,}   {time.time()-t0:.0f} c', flush=True)
        o = random.choice(origins); d = random.choice(targets)
        if dist_m(o, d) > MAX_M: continue
        no = nearest_node(grid, *o); nd = nearest_node(grid, *d)
        if not no or not nd or no == nd: continue
        path = dijkstra_path(adj, no, nd, MAX_M * 1.6)
        if not path: continue
        ok += 1
        for e in path: load[e] += 1

    print(f'   вдалих маршрутів: {ok:,}')
    if not ok: print('нема маршрутів — перевірте дані'); sys.exit(1)

    print('4) зводжу навантаження по вулицях...')
    by_way = collections.defaultdict(lambda: [0, '', 0.0])
    for e, c in load.items():
        if e not in seg: continue
        wid, nm, d = seg[e]
        by_way[wid][0] += c
        by_way[wid][1] = nm
        by_way[wid][2] += d
    # геометрія відрізків для карти
    geo = {}
    for w in roads:
        g = w.get('geometry')
        if g and w.get('id') in by_way:
            step = max(1, len(g)//10)
            geo[w['id']] = [[round(p['lat'],5), round(p['lon'],5)] for p in g[::step]]

    items = []
    for wid, (c, nm, d) in by_way.items():
        if wid in geo and c > 0:
            items.append([geo[wid], nm, c, int(d/2)])
    items.sort(key=lambda x: -x[2])
    json.dump({'title': 'Модельована прохідність (пішохідна)', 'items': items},
              open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',',':'))
    print(f'   відрізків з навантаженням: {len(items):,}  -> data/network.json')

    # рейтинг по вулицях
    by_name = collections.Counter()
    for g_, nm, c, d in items:
        if nm: by_name[nm] += c
    rank = by_name.most_common()

    print('\n=== ТОП-25 найнавантаженіших вулиць ===')
    for i, (nm, c) in enumerate(rank[:25], 1):
        print(f'   {i:3}. {c:6}  {nm}')

    # перевірка конкретної вулиці: python step2c_network.py "Кадетський"
    if len(sys.argv) > 1:
        q = sys.argv[1].lower()
        print(f'\n=== ПЕРЕВІРКА: "{sys.argv[1]}" ===')
        found = [(i, nm, c) for i, (nm, c) in enumerate(rank, 1) if q in nm.lower()]
        if not found:
            print('   не знайдено в результатах — можливо, маршрути туди не будувались')
        for i, nm, c in found:
            pct = 100 * i / len(rank)
            print(f'   місце {i} з {len(rank)}  (верхні {pct:.1f}%)   навантаження {c}   {nm}')
    else:
        print('\n(щоб перевірити конкретну вулицю: додайте її назву аргументом)')

if __name__ == '__main__':
    main()
