# -*- coding: utf-8 -*-
"""Перехрестя — точне місце (RISHENNYA 33.2.3; завдання 30, ч. 4).

Подія без номера будинку, у фабулі якої названо перехрестя двох вулиць,
стає в точку їх перетину за лініями OSM: спільний вузол або найближча пара
точок ліній у межах 30 м. Одна з назв не знайдена, вулиці не
перетинаються чи перетинів кілька далі за 300 м один від одного — точки
немає, і подія, як і раніше, на карту не йде: вигадувати місце не можна.

Раніше (step2_geocode.cross_point) перехрестя ставилося посередині між
найближчими БУДИНКАМИ двох вулиць у 150 м — це могло бути й за квартал від
самого перетину.

Назви в текстах стоять у відмінках («перехрестя вулиць Здолбунівської та
Ревуцького»), тож назви порівнюються за основами слів, а не цілими.
"""
import math, collections
from step2_geocode import skey

R_PARA = 30        # м: найближчі точки двох ліній — ще перетин
R_KILKA = 300      # м: перетини далі один від одного — перехрестя неоднозначне
KROK = 10          # м: лінії ущільнюємо, щоб перетин посеред ребра не загубився


def mdeg(lat): return 111320.0, 111320.0 * math.cos(math.radians(lat))


def osnovy(name):
    """основи слів назви без типу вулиці; ініціали й короткі слова — геть:
    «Б. Хмельницького» і «Богдана Хмельницького» мають спільне «хмельниц»"""
    out = set()
    for w in skey(name or '').split():
        if len(w) < 3: continue
        out.add(w[:max(4, len(w) - 3)] if len(w) > 5 else w)
    return frozenset(out)


def _shchilno(pts):
    out = []
    for a, b in zip(pts, pts[1:]):
        my, mx = mdeg(a[0])
        d = math.hypot((b[0] - a[0]) * my, (b[1] - a[1]) * mx)
        n = max(1, int(d // KROK))
        out += [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(n)]
    return out + [tuple(pts[-1])]


class Perekhrestia:
    def __init__(s, *layers):
        s.lines = collections.defaultdict(list)      # назва OSM -> точки ліній
        for roads in layers:
            for w in roads or []:
                nm = (w.get('tags') or {}).get('name')
                g = [(p['lat'], p['lon']) for p in w.get('geometry') or []]
                if nm and len(g) > 1: s.lines[nm] += _shchilno(g)
        s.os = {nm: osnovy(nm) for nm in s.lines}
        s._c = {}

    def vulytsia(s, name):
        """назва OSM для назви з тексту, або (None, причина)"""
        q = osnovy(name)
        if not q: return None, 'назву не розібрано'
        # усі основи з тексту мають бути в назві OSM: «Хмельницького» — так,
        # «Богдана Хмельницького» — так; «Лютеранської» ≠ «Лютеранська» не
        # заважає, бо порівнюються основи
        c = [nm for nm, o in s.os.items() if q <= o]
        if not c: return None, 'назву не знайдено в OSM'
        tochni = [nm for nm in c if s.os[nm] == q]
        if len(tochni) == 1: return tochni[0], ''
        if len({s.os[nm] for nm in c}) > 1: return None, 'назва неоднозначна'
        return c[0], ''

    def tochka(s, s1, s2):
        """(lat, lon, '') або (None, None, причина)"""
        k = (s1, s2)
        if k in s._c: return s._c[k]
        a, why = s.vulytsia(s1)
        if not a: r = (None, None, why)
        else:
            b, why = s.vulytsia(s2)
            if not b: r = (None, None, why)
            elif a == b: r = (None, None, 'та сама вулиця')
            else: r = s._peretyn(a, b)
        s._c[k] = r
        return r

    def _peretyn(s, a, b):
        cell = 0.0005
        g = collections.defaultdict(list)
        for q in s.lines[b]: g[(int(q[0] / cell), int(q[1] / cell))].append(q)
        par = []
        for p in s.lines[a]:
            my, mx = mdeg(p[0])
            ci, cj = int(p[0] / cell), int(p[1] / cell)
            best = None
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    for q in g.get((ci + di, cj + dj), ()):
                        d = math.hypot((p[0] - q[0]) * my, (p[1] - q[1]) * mx)
                        if d <= R_PARA and (best is None or d < best[0]): best = (d, q)
            if best: par.append((best[0], ((p[0] + best[1][0]) / 2, (p[1] + best[1][1]) / 2)))
        if not par: return (None, None, 'вулиці не перетинаються')
        pts = [x[1] for x in par]
        my, mx = mdeg(pts[0][0])
        # найдальші точки перетину — за крайніми по широті й довготі
        ext = [min(pts), max(pts), min(pts, key=lambda x: x[1]), max(pts, key=lambda x: x[1])]
        far = max(math.hypot((x[0] - y[0]) * my, (x[1] - y[1]) * mx) for x in ext for y in ext)
        if far > R_KILKA: return (None, None, 'кілька перетинів далі 300 м')
        # найближча пара — найточніше місце перетину
        d, p = min(par)
        return (round(p[0], 6), round(p[1], 6), '')


def adresa(s1, s2):
    """підпис точки: «перехрестя вул. X і вул. Y»"""
    return f'перехрестя {s1} і {s2}'
