# -*- coding: utf-8 -*-
"""Повнота останніх місяців за видами (S-Р.9, RISHENNYA 36.20.2).

Рішення суду виходить через тижні чи місяці після події, і ця затримка дуже
різна за видами: ДТП «доростають» до 94% за 3 місяці, крадіжки — до 93% лише
за рік (E3-onovlennya.md). Перевірка, що бере свіжі місяці як «після»,
бачить спад, якого немає. Тому ціль будь-якої перевірки «після» (ризик,
проблеми, Е7, Е24) — лише місяці, де очікувана повнота свого виду ≥ 90%.

Таблицю рахуємо з даних при кожній збірці, а не беремо числа з E3: затримка
міняється разом із судами. Беруться події з датою з тексту (не «рішення мінус
50 днів»), що сталися не пізніше ніж за рік до найновішого рішення, — у них
уже видно хвіст затримки.
"""
import collections, datetime as dt

POROH = .90
MAX_MIS = 18          # більше — вид без надійної дати; не відрізаємо пів року навмання


def _d(s):
    try: return dt.date.fromisoformat(s[:10])
    except (TypeError, ValueError): return None


def mezhi(podii):
    """podii — (вид, дата події з тексту | '', дата рішення). -> (вид -> скільки
    останніх місяців відкинути з цілі, остання дата рішення)."""
    xs = [(th, _d(e), _d(r)) for th, e, r in podii]
    ostannie = max((r for _t, _e, r in xs if r), default=None)
    if not ostannie: return {}, None
    hranycia = ostannie - dt.timedelta(days=365)
    zatr = collections.defaultdict(list)
    for th, e, r in xs:
        if e and r and e <= hranycia and r >= e:
            zatr[th].append((r - e).days)
    out = {}
    for th, z in zatr.items():
        z.sort()
        dni = z[min(len(z) - 1, int(len(z) * POROH))]       # 90-й перцентиль затримки
        out[th] = min(MAX_MIS, -(-dni // 30))                # місяців, угору
    return out, ostannie


def z_vybir(V):
    """Таблиця з відбору карти (step3_map.vybir): вид, дата з тексту, дата рішення."""
    import podii as PD, step3_map as S3
    return mezhi((PD.theme(r[2]), S3.ev_date(V['TKD'].get(r[0]), r[3]), r[3] or '') for r in V['rows'])


def ostannii_povnyi(th, mezha, ostannie):
    """Останній місяць ('YYYY-MM'), який ще можна брати ціллю для виду th."""
    k = mezha.get(th, 0)
    t = ostannie.year * 12 + ostannie.month - 1 - k
    return f'{t // 12:04d}-{t % 12 + 1:02d}'
