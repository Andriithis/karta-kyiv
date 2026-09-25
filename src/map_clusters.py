# -*- coding: utf-8 -*-
"""Дерево кластерів для вигляду «Кільця» нової карти (RISHENNYA, розд. 23).

Чому при збірці, а не в браузері. Кільце при наближенні не зникає, а
розпадається: дочірні кільця виходять із батьківського й розходяться на свої
місця. Для цього браузер мусить знати, хто чий нащадок. Якщо групувати в
браузері кожен рівень окремо (як у макеті), рівні між собою не пов'язані:
частина дочірнього кільця може лежати в сусідньому батьківському, і розпад іде
«не з того» кільця. Тому тут групуємо знизу вгору — кожен рівень збирає вузли
попереднього, дрібнішого, — і кожен кластер цілком лежить в одному батьківському.

Сум за видами дерево не несе (рішення 25.09): період і статті з них однаково не
вивести, тож браузер складає суми з адрес за поточним фільтром, знизу вгору за
батьками. Склад кластерів від фільтра не залежить — фільтр лише зменшує суми,
а кільце від меншої суми лише меншає, тож нових перекриттів не з'являється.
"""
import math, collections

# Зум MapLibre на одиницю менший за зум Leaflet (плитки 512 px проти 256).
# З z15 MapLibre кілець немає — лише адреси (розд. 23, п. 1).
Z_TOP, Z_BOTTOM, DZ = 14.5, 9.5, 0.5
R_MERGE = 48            # px: усе ближче зливається одразу (R у макеті)
CELL = 70               # px: сітка пошуку сусідів; більша за два найбільші радіуси


def r_ring(n, prob):
    """Радіус кільця — той самий, що малює браузер; ромб проблеми з обвідкою
    чорнила вимагає трохи більше місця."""
    return min(30, 10 + 3 * math.log2(max(n, 1))) + (4 if prob else 1.5)


def zoom_mul(zl):
    """Множник кроку 3 за зумом Leaflet (tpl_draw.zoomMul)."""
    return .78 if zl <= 12 else 1 if zl <= 14 else 1.35 if zl <= 16 else 1.7


def r_addr(n, mx, z, prob):
    """Радіус окремої адреси — правило кроку 3, яким її малює вигляд «Адреси»
    (рішення 25.09: адреса в «Кільцях» така сама). mx — найбільша адреса без
    фільтра; під фільтром mx меншає, і крапка може трохи підрости, але крапки
    дрібні й налазили б і на нинішній карті — гарантія «без перекриттів»
    стосується кілець. Адреса з проблемою в «Кільцях» — ромб за розміром
    подій (макет), тож і місця їй треба стільки ж."""
    r = max(2.8, min(14, 2.8 + 9.5 * (n / max(mx, 1)) ** .42)) * zoom_mul(z + 1)
    return max(7, r) * 1.25 + 4.2 if prob else r


def merc(lat, lon, z):
    s = 512 * 2 ** z
    si = math.sin(math.radians(lat))
    return (lon + 180) / 360 * s, (.5 - math.log((1 + si) / (1 - si)) / (4 * math.pi)) * s


def unmerc(x, y, z):
    s = 512 * 2 ** z
    return x / s * 360 - 180, math.degrees(math.atan(math.sinh(math.pi - 2 * math.pi * y / s)))


def build(P):
    """Дерево для P у тому самому порядку, що й серіалізовані точки.

    Повертає {z0, dz, leaf, lv}: leaf — індекси P, що йдуть у кільця (лише
    справжні місця, p[3]; центри вулиць на карту не йдуть — tpl_core); lv[i] —
    рівень зуму z0 + i*dz: c — центри вузлів пласким рядом [lon, lat, …],
    of — для кожного вузла рівня i+1 (для найдрібнішого — для кожної адреси
    з leaf) номер вузла цього рівня, куди він входить.
    """
    leaf = [i for i, p in enumerate(P) if p[3]]
    # Вага — усі події адреси, без фільтра: центр і склад кільця від фільтра
    # не рухаються, інакше кільця стрибали б від кожної галочки.
    W = [len(P[i][4]) for i in leaf]
    PR = [bool(len(P[i]) > 7 and P[i][7]) for i in leaf]
    mx = max(W, default=1)
    # Вузол: вага, чи є проблема, позиція в Меркаторі на z=0 (далі множимо),
    # чи це одна адреса.
    nodes = [dict(n=W[k], pr=PR[k], x=merc(P[i][0], P[i][1], 0)[0],
                  y=merc(P[i][0], P[i][1], 0)[1], one=True)
             for k, i in enumerate(leaf)]
    levels = []
    nz = round((Z_TOP - Z_BOTTOM) / DZ)
    for step in range(nz + 1):
        z = Z_TOP - step * DZ
        k = 2 ** z
        rad = lambda o: (r_addr(o['n'], mx, z, o['pr']) if o['one']
                         else r_ring(o['n'], o['pr']))
        # 1) Усе ближче за R_MERGE — в одну групу, від найбільших вузлів.
        #    Сортування стале (при рівній вазі — за номером), щоб дві збірки
        #    на тих самих даних давали той самий файл.
        order = sorted(range(len(nodes)), key=lambda a: (-nodes[a]['n'], a))
        grid = collections.defaultdict(list)
        for a in order:
            o = nodes[a]
            grid[(int(o['x'] * k // R_MERGE), int(o['y'] * k // R_MERGE))].append(a)
        used = [False] * len(nodes)
        groups = []
        for a in order:
            if used[a]: continue
            used[a] = True
            o, m = nodes[a], [a]
            gi, gj = int(o['x'] * k // R_MERGE), int(o['y'] * k // R_MERGE)
            for u in (gi - 1, gi, gi + 1):
                for v in (gj - 1, gj, gj + 1):
                    for b in grid.get((u, v), ()):
                        if used[b]: continue
                        dx, dy = (nodes[b]['x'] - o['x']) * k, (nodes[b]['y'] - o['y']) * k
                        if dx * dx + dy * dy <= R_MERGE * R_MERGE:
                            used[b] = True; m.append(b)
            groups.append(m)
        # 2) Доки кільця налазять одне на одне — зливаємо. Центр — зважений
        #    за подіями: у Меркаторі це те саме, що зважене середнє адрес, тож
        #    центр не залежить від того, в якому порядку зливалися вузли.
        def group(m):
            n = sum(nodes[b]['n'] for b in m)
            return dict(m=m, n=n, pr=any(nodes[b]['pr'] for b in m),
                        x=sum(nodes[b]['x'] * nodes[b]['n'] for b in m) / n,
                        y=sum(nodes[b]['y'] * nodes[b]['n'] for b in m) / n,
                        one=len(m) == 1 and nodes[m[0]]['one'])
        cur = [group(m) for m in groups]
        for _ in range(100):
            G = collections.defaultdict(list)
            for o in cur:
                o['dead'] = False
                G[(int(o['x'] * k // CELL), int(o['y'] * k // CELL))].append(o)
            merged = False
            for o in sorted(cur, key=lambda o: (-o['n'], o['m'][0])):
                if o['dead']: continue
                gi, gj = int(o['x'] * k // CELL), int(o['y'] * k // CELL)
                for u in (gi - 1, gi, gi + 1):
                    for v in (gj - 1, gj, gj + 1):
                        for q in G.get((u, v), ()):
                            if q is o or q['dead']: continue
                            if math.hypot((q['x'] - o['x']) * k, (q['y'] - o['y']) * k) \
                                    < rad(o) + rad(q) + 1:
                                o.update(group(o['m'] + q['m']))
                                q['dead'] = True; merged = True
            cur = [o for o in cur if not o['dead']]
            if not merged: break
        else:
            print(f'   дерево кластерів: на z{z} перекриття не розійшлися за 100 проходів')
        of = [0] * len(nodes)
        for j, o in enumerate(cur):
            for b in o['m']: of[b] = j
        c = []
        for o in cur:
            lon, lat = unmerc(o['x'], o['y'], 0)
            c += [round(lon, 5), round(lat, 5)]
        levels.append(dict(c=c, of=of))
        nodes = cur
    levels.reverse()            # від міського огляду до найдрібнішого
    return dict(z0=Z_BOTTOM, dz=DZ, leaf=leaf, lv=levels)
