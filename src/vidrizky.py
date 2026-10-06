# -*- coding: utf-8 -*-
"""Відрізок вулиці між перехрестями — одиниця моделі ризику, ліній проблем
і пішохідних потоків (ZAVDANNYA-30, частина 1; METODYKA, розд. 4).

Лінія OSM (way) — не квартал: одна лінія тягнеться через кілька перехресть,
а буває, що квартал розрізано на три лінії через зміну покриття чи смуг.
Звідси «середня довжина 180 м», яка насправді була кількома кварталами, і
модель, що порівнювала квартал із трьома кварталами. Тому ріжемо лінії у
вузлах, де сходиться ≥3 вулиць, а шматки коротші за 40 м доклеюємо до
сусіднього шматка тієї ж вулиці: 15 м між двома виїздами — не квартал, а
пара метрів асфальту, на якій подій не буде просто через довжину.

Подія прив'язується до відрізка СВОЄЇ вулиці (завдання 29, п. 6.2): ДТП на
Кадетському Гаю, 3–12 лежать за 44–94 м від осі, і найближчим бував проїзд
у дворі. Відстань — до найближчої точки лінії, а не до вершини: на довгому
прямому відрізку вершин дві, і до них далеко, хоча сама вулиця поруч.
"""
import math, collections

KEY = 5            # знаків після коми у ключі вузла — як step2c_network.key
MIN_M = 40         # коротший шматок — не квартал, доклеюємо до сусіда
CELL = 0.002       # сітка пошуку ребер (~150–220 м)


def mdeg(lat): return 111320.0, 111320.0 * math.cos(math.radians(lat))


def key(la, lo): return (round(la, KEY), round(lo, KEY))


def dovzhyna(pts):
    t = 0.0
    for a, b in zip(pts, pts[1:]):
        my, mx = mdeg((a[0] + b[0]) / 2)
        t += math.hypot((a[0] - b[0]) * my, (a[1] - b[1]) * mx)
    return t


def vulytsi(raw):
    """Шар вулиць з кешу OSM: вулиці кроку 2b (residential … secondary) і
    магістралі (primary, trunk, motorway і їхні _link — рішення Андрія
    30.09). Без магістралей події на проспектах лишалися «поза вулицями»
    (~8,6 тис.), а перехрестя з проспектами не знаходились."""
    return list(raw.get('roads') or []) + list(raw.get('dorogy_velyki') or [])


def stupeni(roads):
    """вузол -> скільки різних сусідів у графі вулиць. Лише шар roads:
    пішохідна доріжка, що перетинає вулицю, — не перехрестя вулиць, інакше
    квартал різало б кожним тротуаром."""
    nb = collections.defaultdict(set)
    for w in roads:
        g = w.get('geometry') or []
        ks = [key(p['lat'], p['lon']) for p in g]
        for u, v in zip(ks, ks[1:]):
            if u != v: nb[u].add(v); nb[v].add(u)
    return {u: len(v) for u, v in nb.items()}


def _zlyty(a, b):
    """дві полілінії зі спільним кінцем -> одна (напрямок першої)"""
    ka, kb = [key(*p) for p in (a[0], a[-1])], [key(*p) for p in (b[0], b[-1])]
    if ka[1] == kb[0]: return a + b[1:]
    if ka[1] == kb[1]: return a + b[::-1][1:]
    if ka[0] == kb[1]: return b + a[1:]
    if ka[0] == kb[0]: return b[::-1] + a[1:]
    return None


def build(roads):
    """{id відрізка: dict(pts, name, tags, way, len)} — порядок стабільний
    (за id лінії OSM і номером шматка), тож id однакові від запуску до запуску
    на тих самих даних. id — «<way>:<n>»."""
    deg = stupeni(roads)
    kus = []                  # [id, pts, name, tags, way]
    for w in sorted(roads, key=lambda w: w.get('id', 0)):
        g = w.get('geometry') or []
        if len(g) < 2: continue
        tags = w.get('tags', {}) or {}
        pts = [(p['lat'], p['lon']) for p in g]
        cut = [0] + [i for i in range(1, len(pts) - 1) if deg.get(key(*pts[i]), 0) >= 3] + [len(pts) - 1]
        ps = [pts[a:b + 1] for a, b in zip(cut, cut[1:]) if b > a]
        # короткі шматки всередині лінії — до сусіднього шматка тієї ж лінії
        # (коротшого з двох: так довгий квартал не ковтає короткий хвіст)
        while len(ps) > 1:
            ln = [dovzhyna(p) for p in ps]
            i = min(range(len(ps)), key=lambda k: ln[k])
            if ln[i] >= MIN_M: break
            j = i - 1 if i == len(ps) - 1 else i + 1 if i == 0 else (i - 1 if ln[i - 1] <= ln[i + 1] else i + 1)
            a, b = min(i, j), max(i, j)
            ps[a:b + 1] = [ps[a] + ps[b][1:]]
        for n, p in enumerate(ps):
            kus.append([f"{w['id']}:{n}", p, tags.get('name', ''), tags, w['id']])
    # Шматок, коротший за 40 м і після цього, — ціла коротка лінія OSM між
    # двома іншими лініями тієї ж вулиці. Доклеюємо до сусіда з тією ж
    # назвою через спільний кінець; без назви чи без сусіда — відкидаємо,
    # як і раніше (такі шматки — з'їзди й розвороти).
    kinets = collections.defaultdict(list)
    for k in kus:
        for p in (k[1][0], k[1][-1]): kinets[key(*p)].append(k)
    live = {id(k) for k in kus}
    for k in sorted(kus, key=lambda k: dovzhyna(k[1])):
        if id(k) not in live or dovzhyna(k[1]) >= MIN_M: continue
        live.discard(id(k))
        if not k[2]: continue
        for p in (k[1][0], k[1][-1]):
            sus = [s for s in kinets[key(*p)] if id(s) in live and s[2] == k[2]]
            if not sus: continue
            s = min(sus, key=lambda s: dovzhyna(s[1]))
            z = _zlyty(s[1], k[1])
            if z:
                s[1] = z
                kinets[key(*z[0])].append(s); kinets[key(*z[-1])].append(s)
                break
    out = {}
    for k in kus:
        if id(k) not in live: continue
        L = dovzhyna(k[1])
        if L < MIN_M: continue
        out[k[0]] = dict(pts=k[1], name=k[2], tags=k[3], way=k[4], len=L)
    return out


def budova(segs, deg):
    """Будова кожного відрізка: тип кінців (тупик, T-подібне, хрестоподібне),
    проникність, звивистість — Johnson & Bowers (2014), J. of Quantitative
    Criminology 30(2). Рахується з графа самих вулиць (stupeni), тож не
    залежить від пішохідної мережі кроку 2c: без неї модель інакше лишалася
    б без будови вулиці зовсім."""
    out = {}
    for sid, s in segs.items():
        pts = [key(*p) for p in s['pts']]
        dg = [deg.get(e, 1) for e in (pts[0], pts[-1])]
        L = s['len']
        straight = math.hypot(*[(a - b) * m for a, b, m in zip(s['pts'][0], s['pts'][-1], mdeg(s['pts'][0][0]))]) or 1.0
        out[sid] = dict(perm=sum(dg), cross4=sum(1 for d in dg if d >= 4),
                        cross3=sum(1 for d in dg if d == 3), dead=sum(1 for d in dg if d <= 1),
                        sinuo=round(L / straight, 3),
                        # після розрізу у вузлах тут лишаються лише перехрестя
                        # всередині доклеєних коротких шматків
                        inner=sum(1 for p in pts[1:-1] if deg.get(p, 2) >= 3), length=round(L))
    return out


def rebra(segs):
    """(вузол, вузол) -> id відрізка — для зведення пішохідних маршрутів
    (step2c_network) по відрізках, а не по лініях OSM"""
    out = {}
    for sid, s in segs.items():
        ks = [key(*p) for p in s['pts']]
        for u, v in zip(ks, ks[1:]):
            if u != v: out[(u, v)] = out[(v, u)] = sid
    return out


def _do_rebra(p, a, b):
    """відстань у метрах від точки p до ребра ab ((lat, lon))"""
    my, mx = mdeg(p[0])
    ax, ay = (a[1] - p[1]) * mx, (a[0] - p[0]) * my
    bx, by = (b[1] - p[1]) * mx, (b[0] - p[0]) * my
    dx, dy = bx - ax, by - ay
    t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / (dx * dx + dy * dy)))
    return math.hypot(ax + t * dx, ay + t * dy)


def slova(s):
    """слова назви вулиці для порівняння «та сама вулиця» — ключ step2_geocode
    без типу вулиці, лише слова від 4 літер: «Ав. Антонова» і
    «Авіаконструктора Антонова» мають спільне «антонова»"""
    from step2_geocode import skey
    return frozenset(w for w in skey(s or '').split() if len(w) >= 4)


def ta_sama(a, b):
    """одна назва повністю входить в іншу: «Ав. Антонова» в
    «Авіаконструктора Антонова» — так, «Північно-Сирецька» у
    «Парково-Сирецьку» — ні (правило ліній problems.py)"""
    return bool(a) and bool(b) and (a <= b or b <= a)


class Pryviazka:
    """пошук відрізка для події: своя вулиця в межах rad, інакше найближчий"""
    def __init__(s, segs):
        s.segs = segs
        s.sl = {sid: slova(v['name']) for sid, v in segs.items()}
        s.g = collections.defaultdict(list)
        for sid, v in segs.items():
            for a, b in zip(v['pts'], v['pts'][1:]):
                c0 = (int(min(a[0], b[0]) / CELL), int(min(a[1], b[1]) / CELL))
                c1 = (int(max(a[0], b[0]) / CELL), int(max(a[1], b[1]) / CELL))
                for i in range(c0[0], c1[0] + 1):
                    for j in range(c0[1], c1[1] + 1):
                        s.g[(i, j)].append((sid, a, b))

    def blyzki(s, la, lo, rad):
        """{id відрізка: відстань до лінії} у межах rad"""
        my, mx = mdeg(la)
        n = int(max(rad / my, rad / mx) / CELL) + 1
        ci, cj = int(la / CELL), int(lo / CELL)
        best = {}
        for i in range(ci - n, ci + n + 1):
            for j in range(cj - n, cj + n + 1):
                for sid, a, b in s.g.get((i, j), ()):
                    d = _do_rebra((la, lo), a, b)
                    if d <= rad and d < best.get(sid, 1e18): best[sid] = d
        return best

    def znaity(s, la, lo, rad, nazvy=()):
        """(id, чи своя вулиця) або (None, False). nazvy — назви вулиць з
        адреси події (для перехрестя — дві)."""
        b = s.blyzki(la, lo, rad)
        if not b: return None, False
        ws = [slova(n) for n in nazvy if n]
        svoi = [sid for sid in b if any(ta_sama(w, s.sl[sid]) for w in ws)]
        if svoi: return min(svoi, key=lambda k: b[k]), True
        return min(b, key=lambda k: b[k]), False


def vulytsia(adr):
    """«вул. Хрещатик, 19А» -> «вул. Хрещатик»; «перехрестя вул. X і вул. Y»
    -> обидві назви"""
    a = (adr or '').split(',')[0].strip()
    if a.startswith('перехрестя '):
        a = a[len('перехрестя '):]
        return [x.strip() for x in a.split(' і ', 1)]
    if ' / ' in a:
        return [x.strip() for x in a.split(' / ', 1)]
    return [a] if a else []


def potik(items):
    """network.json -> {id відрізка: прохідність}. Новий формат (06.10,
    ZAVDANNYA-32, 4.3): [геометрія, назва, potik, id]; старий (до 06.10):
    [геометрія, назва, загальний, школи, транспорт, торгівля, id] — з нього
    береться загальний потік, доки крок 2c не перерахував файл."""
    out = {}
    for it in items or []:
        if len(it) == 4:
            out[it[3]] = it[2]
        elif len(it) > 6 and it[6] is not None:
            out[it[6]] = it[2]
    return out
