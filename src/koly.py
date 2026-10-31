# -*- coding: utf-8 -*-
"""«Коли» — дивні залежності в часі (ZAVDANNYA-40 6.4, ZAVDANNYA-41 2.4–2.5;
метод — doslidzhennya/audyt-34/E27-koly.md).

Фаза місяця, спека, дощ і сніг, повітряні тривоги, перехід на літній час,
свята, п'ятниця 13-те — змінюють не «де», а «коли». На карту не йде нічого;
результат — сторінка `koly.html` у «Дослідженні».

Метод (той самий, що в Е27): денна кількість подій виду з датою події з тексту
(без дати рішення); квазі-Пуассонова регресія з поправкою на день тижня,
календарний місяць і рік; ефект — відношення (IRR) з 95% межами; перевірок
багато, тож поправка Бенджаміні — Гохберга. «Ефект» — лише коли він за
межами похибки після поправки; інакше — «міф спростовано» / «не відрізняється».
Суд бачить роботу поліції (рейди, ст.130), а не всі події — це речення на
сторінці. Без numpy-залежностей поза numpy і без мережі збірка не падає:
джерело не відповіло — розділ пише, що даних немає.
"""
import os, json, math, datetime as dt, urllib.request, collections
from html import escape as esc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KESH = os.path.join(ROOT, 'vykhid', 'koly')
LAT, LON = 50.45, 30.52
POCHATOK = dt.date(2024, 1, 1)
# Затримка публікації (медіана 46 днів, p90 ~ 3 міс.): останні 4 місяці неповні
ZATRYMKA_DNIV = 120
VYDY = [('ДТП', 'ДТП'), ('ДОР', 'порушення на дорозі'), ('ГП', 'громадський порядок'),
        ('МАЙ', 'майнові'), ('НАС', 'насильство'), ('НАР', 'наркотики'), ('АЛК', 'алкоголь і торгівля')]

DZHERELA = {
    'meteo': ('Open-Meteo Historical Weather API (без ключа)', 'https://open-meteo.com/en/docs/historical-weather-api'),
    'tryvohy': ('Історія повітряних тривог (Vadimkin/ukrainian-air-raid-sirens-dataset, офіційні дані)',
                'https://github.com/Vadimkin/ukrainian-air-raid-sirens-dataset'),
    'dst': ('Fritz та ін., 2020: перехід на літній час і ризик ДТП (Current Biology)', 'https://doi.org/10.1016/j.cub.2019.12.045'),
    'pylok': ('Chalfin, Danagoulian, Deza, 2019: пилок і насильство (Journal of Health Economics)', 'https://doi.org/10.1016/j.jhealeco.2019.102230'),
    'speka': ('Heilmann, Kahn, Tang, 2021: спека й злочинність у містах (Journal of Public Economics)', 'https://doi.org/10.1016/j.jpubeco.2021.104408'),
}


def _json(url, f):
    """з кешу vykhid/koly (не в git), інакше з мережі; None — джерело мовчить"""
    os.makedirs(KESH, exist_ok=True)
    p = os.path.join(KESH, f)
    if os.path.exists(p):
        try: return json.load(open(p, encoding='utf-8'))
        except ValueError: pass
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'karta-kyiv'}), timeout=60) as r:
            raw = r.read().decode('utf-8')
    except Exception as e:
        print(f'   «Коли»: {f} не завантажено — {e}'); return None
    d = json.loads(raw) if f.endswith('.json') else raw
    json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False)
    return d


def pohoda(do):
    d = _json(f'https://archive-api.open-meteo.com/v1/archive?latitude={LAT}&longitude={LON}'
              f'&start_date={POCHATOK}&end_date={do}&daily=temperature_2m_max,precipitation_sum,snowfall_sum'
              f'&timezone=Europe%2FKyiv', f'pohoda-{do}.json')
    if not d or 'daily' not in d: return None
    x = d['daily']
    return {t: (tm, pr, sn) for t, tm, pr, sn in zip(x['time'], x['temperature_2m_max'], x['precipitation_sum'], x['snowfall_sum'])}


def tryvohy():
    """дата -> годин тривоги в Києві (за київським часом, з розбиттям через північ)"""
    raw = _json('https://raw.githubusercontent.com/Vadimkin/ukrainian-air-raid-sirens-dataset/main/datasets/official_data_uk.csv',
                'tryvohy.csv')
    if not raw: return None
    hod = collections.Counter()
    kyiv = dt.timezone(dt.timedelta(hours=2))
    iv = []
    for row in raw.splitlines()[1:]:
        c = row.split(',')
        if len(c) < 6 or c[0] != 'м. Київ': continue
        try:
            iv.append((dt.datetime.fromisoformat(c[4]).astimezone(kyiv), dt.datetime.fromisoformat(c[5]).astimezone(kyiv)))
        except ValueError: continue
    # записи перекриваються (місто й громада) — спершу злити, інакше доба має >24 год
    zlyti = []
    for a, b in sorted(iv):
        if zlyti and a <= zlyti[-1][1]: zlyti[-1][1] = max(zlyti[-1][1], b)
        else: zlyti.append([a, b])
    for a, b in zlyti:
        while a < b:
            kin = min(b, dt.datetime.combine(a.date() + dt.timedelta(days=1), dt.time(0), kyiv))
            hod[a.date().isoformat()] += (kin - a).total_seconds() / 3600; a = kin
    return hod


def faza(d):
    """фаза місяця 0..1 (0 — новий, 0,5 — повня); точність ~0,5 доби достатня для ±1,85"""
    n = (dt.datetime(d.year, d.month, d.day, 12) - dt.datetime(2000, 1, 6, 18, 14)).total_seconds() / 86400
    return (n / 29.530588853) % 1


def vyhidni_ukr(y):
    """свята, що лишились у календарі людей і під час воєнного стану (вихідних немає,
    але святкують): Новий рік, Різдво, 8 березня, Великдень (православний), День Незалежності"""
    a, b, c = y % 4, y % 7, y % 19
    d = (19 * c + 15) % 30; e = (2 * a + 4 * b - d + 34) % 7
    m, dd = divmod(d + e + 114, 31)
    velykden = dt.date(y, m, dd + 1) + dt.timedelta(days=13)
    return {dt.date(y, 1, 1), dt.date(y, 12, 25), dt.date(y, 3, 8), dt.date(y, 8, 24), velykden, dt.date(y, 12, 31)}


def ostannia_nedilia(y, mis):
    d = dt.date(y, mis + 1, 1) - dt.timedelta(days=1) if mis < 12 else dt.date(y, 12, 31)
    return d - dt.timedelta(days=(d.weekday() + 1) % 7)


def kvazi_puasson(y, X):
    """IRLS для Пуассона з поправкою на надмірну дисперсію (квазі-Пуассон):
    коефіцієнти й стандартні похибки"""
    import numpy as np
    b = np.zeros(X.shape[1]); b[0] = math.log(max(y.mean(), 1e-6))
    for _ in range(50):
        mu = np.exp(np.clip(X @ b, -30, 30)); z = X @ b + (y - mu) / mu
        W = mu; XtW = X.T * W
        nb = np.linalg.solve(XtW @ X + 1e-8 * np.eye(X.shape[1]), XtW @ z)
        if np.max(np.abs(nb - b)) < 1e-8: b = nb; break
        b = nb
    mu = np.exp(X @ b)
    phi = max(1.0, float(((y - mu) ** 2 / mu).sum() / max(1, len(y) - X.shape[1])))
    cov = np.linalg.inv((X.T * mu) @ X) * phi
    return b, np.sqrt(np.diag(cov))


def p_z(z):
    return math.erfc(abs(z) / math.sqrt(2))


def bh(ps, q=.05):
    o = sorted(range(len(ps)), key=lambda i: ps[i]); m = len(ps); ok = set()
    for r, i in enumerate(o, 1):
        if ps[i] <= q * r / m: ok = set(o[:r])
    return ok


def dni_podij(D):
    """вид -> Counter(дата): лише дата події з тексту (без «дата рішення»)"""
    th_of = D['th_of']
    out = collections.defaultdict(collections.Counter)
    for docs in D.get('DOCS') or []:
        for c in docs:
            if len(c) > 6 and c[6]: continue
            d = c[1]
            if not d or len(d) < 10: continue
            out[th_of[c[0]]][d[:10]] += 1
    return out


def testy(D):
    import numpy as np
    po = dni_podij(D)
    ost = max((max(c) for c in po.values() if c), default=None)
    if not ost: return None, None
    kin = dt.date.fromisoformat(ost) - dt.timedelta(days=ZATRYMKA_DNIV)
    dni = [POCHATOK + dt.timedelta(days=i) for i in range((kin - POCHATOK).days + 1)]
    pg = pohoda(kin.isoformat()); tr = tryvohy()
    rokiv = sorted({d.year for d in dni})
    # поправки: день тижня, місяць, рік
    def baza(d):
        return [1.0] + [1.0 if d.weekday() == k else 0.0 for k in range(1, 7)] + \
               [1.0 if d.month == k else 0.0 for k in range(2, 13)] + [1.0 if d.year == r else 0.0 for r in rokiv[1:]]
    B = np.array([baza(d) for d in dni])
    svyata = set().union(*(vyhidni_ukr(r) for r in rokiv))
    dst = set()
    for r in rokiv:
        s = ostannia_nedilia(r, 3); dst |= {s + dt.timedelta(days=k) for k in range(1, 8)}
    chynnyky = [
        ('povnia', 'Повня (±1,85 доби)', lambda d: abs(faza(d) - .5) <= 1.85 / 29.53, None),
        ('speka', 'Спека: максимум ≥ 28 °C', (lambda d: pg[d.isoformat()][0] is not None and pg[d.isoformat()][0] >= 28) if pg else None, 'meteo'),
        ('doshch', 'Дощ ≥ 5 мм за добу', (lambda d: (pg[d.isoformat()][1] or 0) >= 5) if pg else None, 'meteo'),
        ('snih', 'Сніг (снігопад за добу)', (lambda d: (pg[d.isoformat()][2] or 0) > 0) if pg else None, 'meteo'),
        ('tryvoha', 'Тривога 3 год і довше за добу', (lambda d: tr.get(d.isoformat(), 0) >= 3) if tr is not None else None, 'tryvohy'),
        ('dst', 'Тиждень після переходу на літній час', lambda d: d in dst, 'dst'),
        ('svyato', 'Свята (Новий рік, Різдво, 8 березня, Великдень, 24 серпня, 31 грудня)', lambda d: d in svyata, None),
        ('p13', "П'ятниця 13-те", lambda d: d.day == 13 and d.weekday() == 4, None),
    ]
    rez = []
    for kod, nazva, f, dzh in chynnyky:
        if f is None:
            rez.append(dict(kod=kod, nazva=nazva, dzh=dzh, nema=True)); continue
        try: x = np.array([1.0 if f(d) else 0.0 for d in dni])
        except KeyError: rez.append(dict(kod=kod, nazva=nazva, dzh=dzh, nema=True)); continue
        X = np.column_stack([B, x]); ryad = []
        for th, vn in VYDY:
            y = np.array([po[th].get(d.isoformat(), 0) for d in dni], dtype=float)
            if y.sum() < 300 or x.sum() < 3: continue
            b, se = kvazi_puasson(y, X)
            k, s = b[-1], se[-1]
            ryad.append(dict(vyd=vn, podij=int(y.sum()), dniv=int(x.sum()), irr=math.exp(k),
                             vid=math.exp(k - 1.96 * s), do=math.exp(k + 1.96 * s), p=p_z(k / s if s else 0)))
        rez.append(dict(kod=kod, nazva=nazva, dzh=dzh, ryady=ryad))
    vsi = [r for t in rez for r in t.get('ryady', [])]
    zn = bh([r['p'] for r in vsi])
    for i, r in enumerate(vsi): r['znachushchyi'] = i in zn
    return rez, (POCHATOK, kin, len(dni))


VYSNOVOK_SVIT = {
    'povnia': 'У світі «ефект повні» не відтворюється (Е27; огляди травматології й кримінології).',
    'speka': 'У містах США спека пов\'язана з більшою кількістю насильницьких злочинів.',
    'dst': 'У Німеччині в тиждень після переходу на літній час ДТП трохи частішають.',
    'pylok': 'Високий пилок — менше насильства (США).',
}


def storinka(D, num, pct):
    r, per = testy(D)
    if r is None: return '<p>Дат подій немає — сторінку не пораховано.</p>'
    p0, p1, nd = per
    b = [f'<p>Події з датою з тексту рішення, {p0.strftime("%d.%m.%Y")} — {p1.strftime("%d.%m.%Y")} ({num(nd)} днів; '
         f'останні 4 місяці не беремо — рішення ще публікуються). Поправка на день тижня, місяць і рік; '
         f'перевірок багато — 1 з 20 «спрацює» випадково, тому поправка Бенджаміні — Гохберга.</p>'
         '<p class="muted">Суд бачить роботу поліції (рейди, ст.130), а не всі події: «більше в спеку» може означати «більше '
         'рейдів у спеку».</p>']
    for t in r:
        if t.get('nema'):
            b.append(f'<div class="card" style="margin:12px 0"><h3 style="margin:0">{esc(t["nazva"])}</h3><p class="muted">Джерело '
                     'не відповіло під час збірки — перевірку не пораховано.</p></div>'); continue
        ry = t['ryady']
        if not ry: continue
        zn = [x for x in ry if x['znachushchyi']]
        if zn:
            vysn = '; '.join(f'{x["vyd"]} {("+" if x["irr"] > 1 else "−")}{abs(x["irr"] - 1) * 100:.0f}%' for x in zn)
            mitka, zag = 'несподівано' if t['kod'] in ('povnia', 'p13') else 'сильно', f'{t["nazva"]}: {vysn}'
        else:
            mitka, zag = 'міф спростовано' if t['kod'] in ('povnia', 'p13') else 'не відрізняється', f'{t["nazva"]}: різниці немає'
        kl = {'сильно': '#2e7d32', 'несподівано': '#ef6c00', 'міф спростовано': '#607d8b', 'не відрізняється': '#9e9e9e'}[mitka]
        tab = ''.join(f'<tr><td>{esc(x["vyd"])}</td><td class="n">{num(x["podij"])}</td><td class="n">{x["dniv"]}</td>'
                      f'<td class="n">{(x["irr"] - 1) * 100:+.1f}%</td><td class="n">[{(x["vid"] - 1) * 100:+.1f}; {(x["do"] - 1) * 100:+.1f}]</td>'
                      f'<td>{"так" if x["znachushchyi"] else "ні"}</td></tr>' for x in ry)
        dz = t.get('dzh')
        b.append(f'<div class="card" style="margin:14px 0"><h3 style="margin:0 0 6px">{esc(zag)} '
                 f'<span style="font-size:12px;border-radius:9px;padding:0 8px;background:{kl};color:#fff">{mitka}</span></h3>'
                 f'<div class="tw"><table><tr><th>Вид</th><th>Подій</th><th>Таких днів</th><th>Зміна</th><th>95% межі</th>'
                 f'<th>Поза похибкою</th></tr>{tab}</table></div>'
                 f'<p><b>Що це означає.</b> {"Зміна за межами випадкової після поправки на множинність." if zn else "Відхилення в межах випадкового — на кількість подій цей чинник не впливає помітно."} '
                 f'{esc(VYSNOVOK_SVIT.get(t["kod"], ""))}</p>'
                 f'<p><b>Як використати.</b> {"Планувати присутність і профілактику на такі дні." if zn else "Не будувати графіки й рейди під цей чинник."}</p>'
                 + (f'<p class="muted">Джерело: <a href="{DZHERELA[dz][1]}" target="_blank" rel="noopener">{esc(DZHERELA[dz][0])}</a></p>' if dz else '')
                 + '</div>')
    b.append('<p class="muted">Для порівняння зі світом: '
             + '; '.join(f'<a href="{u}" target="_blank" rel="noopener">{esc(n)}</a>' for k, (n, u) in DZHERELA.items() if k in ('dst', 'pylok', 'speka'))
             + '.</p>')
    return ''.join(b)
