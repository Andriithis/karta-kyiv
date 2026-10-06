# -*- coding: utf-8 -*-
"""Ризик точками (RISHENNYA 35.4; ZAVDANNYA-32, ч. 6).

Лінія розмазує вузол на весь квартал, а ДТП збираються на перехрестях
(Highway Safety Manual: перехрестя й перегони рахують окремо), порядок,
крадіжки, наркотики — біля конкретних об'єктів: вихід метро, ринок, ТЦ,
вокзал, кіоск з алкоголем (Eck, Clarke, Guerette 2007 — «ризиковані
об'єкти»). Тому поряд із відрізками — точки.

Кандидати: перехрестя (вузли графа вулиць зі ступенем ≥ 3), об'єкти-
атрактори й адреси з подіями за 2 роки. Точки ближче 25 м — одна
(пріоритет: перехрестя > атрактор > адреса).

Подія належить одній одиниці: ДТП у 30 м від перехрестя — перехрестю;
інша — найближчій точці в 50 м, якщо там уже були події (історія > 0),
інакше відрізку. Модель ліній вчиться на рештці — подвійного рахунку немає.

Змінні — ті самі, що в ліній (середовище в радіусах, прохідність, населення,
1551), плюс тип точки; без довжини. PAI — частка подій на верхніх 5%
точок ÷ 0,05; на карту — якщо PAI ≥ 3.
"""
import math, collections

R_PEREKH = 30.0          # м: ціль і належність ДТП перехрестю
R_TOCHKA = 50.0          # м: ціль і належність решти подій
R_ZLYTTIA = 25.0         # м: точки ближче — одна
TOP = 0.05               # PAI на верхніх 5% точок
MIN_PAI = 3.0
# атрактори: ключ кешу OSM -> тип точки
ATRAKTORY = {'b1_metro': 'метро', 'b1_market': 'ринок', 'b1_mall': 'ТЦ', 'b1_super': 'супермаркет',
             'b1_alk': 'алкоголь на винос', 'b1_bars': 'бар', 'b1_school': 'школа', 'park': 'парк'}
TYPY = ['перехрестя', 'вокзал'] + sorted(set(ATRAKTORY.values())) + ['адреса']
PRIORYTET = {'перехрестя': 0, 'адреса': 2}


def mdeg(lat): return 111320.0, 111320.0 * math.cos(math.radians(lat))


def _el(e):
    la = e.get('lat') or (e.get('center') or {}).get('lat')
    lo = e.get('lon') or (e.get('center') or {}).get('lon')
    return (la, lo) if la and lo else None


def kandydaty(raw, roads, adresy, VR):
    """[dict(la, lo, typ)] — злиті в R_ZLYTTIA за пріоритетом"""
    out = []
    deg = VR.stupeni(roads)
    for k, d in deg.items():
        if d >= 3: out.append((0, k[0], k[1], 'перехрестя'))
    for key, typ in ATRAKTORY.items():
        for e in raw.get(key) or []:
            p = _el(e)
            if not p: continue
            t = (e.get('tags') or {})
            if key == 'b1_metro' and t.get('railway') == 'station' and t.get('station') != 'subway':
                typ_ = 'вокзал'
            else:
                typ_ = typ
            out.append((1, p[0], p[1], typ_))
    for la, lo in adresy:
        out.append((2, la, lo, 'адреса'))
    out.sort()
    C = 0.0005
    g = collections.defaultdict(list)
    keep = []
    for pr, la, lo, typ in out:
        my, mx = mdeg(la)
        ci, cj = int(la / C), int(lo / C)
        blyz = False
        for i in (ci - 1, ci, ci + 1):
            for j in (cj - 1, cj, cj + 1):
                for a, b in g.get((i, j), ()):
                    if math.hypot((a - la) * my, (b - lo) * mx) < R_ZLYTTIA: blyz = True; break
                if blyz: break
            if blyz: break
        if blyz: continue
        g[(ci, cj)].append((la, lo))
        keep.append(dict(la=la, lo=lo, typ=typ))
    return keep


class Sitka:
    def __init__(s, pts, C=0.0006):
        s.C = C; s.g = collections.defaultdict(list); s.p = pts
        for i, (la, lo) in enumerate(pts): s.g[(int(la / C), int(lo / C))].append(i)

    def blyzki(s, la, lo, r):
        my, mx = mdeg(la)
        n = int(max(r / my, r / mx) / s.C) + 1
        ci, cj = int(la / s.C), int(lo / s.C)
        out = []
        for i in range(ci - n, ci + n + 1):
            for j in range(cj - n, cj + n + 1):
                for k in s.g.get((i, j), ()):
                    d = math.hypot((s.p[k][0] - la) * my, (s.p[k][1] - lo) * mx)
                    if d <= r: out.append((d, k))
        return sorted(out)


def nalezhnist(ev, T, istoria):
    """подія -> індекс точки або None (відрізок). istoria[k] — події точки за
    вікно історії (будь-якого виду) у її радіусі: «точка з історією»."""
    S = Sitka([(t['la'], t['lo']) for t in T])
    out = []
    for e in ev:
        if e.get('vul'):
            out.append(None); continue
        b = S.blyzki(e['la'], e['lo'], R_TOCHKA)
        k = None
        if e['th'] == 'ДТП':
            k = next((k_ for d, k_ in b if T[k_]['typ'] == 'перехрестя' and d <= R_PEREKH), None)
        if k is None:
            k = next((k_ for d, k_ in b if istoria[k_] > 0
                      and d <= (R_PEREKH if T[k_]['typ'] == 'перехрестя' else R_TOCHKA)), None)
        out.append(k)
    return out


def pai(score, y, top=TOP):
    """частка подій на верхніх top точок ÷ top"""
    import numpy as np
    if y.sum() == 0: return 0.0
    k = max(1, int(round(len(score) * top)))
    o = np.argsort(-score, kind='stable')[:k]
    return float(y[o].sum() / y.sum() / top)
