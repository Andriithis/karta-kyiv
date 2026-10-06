# -*- coding: utf-8 -*-
"""Крок 6: три звіти й методика (PLAN-ZVITY.md, затверджено 27.09; розд. 25).

  problemy.html      — «Проблеми»: перелік і сторінка на кожну (#p-<номер>);
  skhozhi-umovy.html — «Схожі умови» за видами;
  stan-mista.html    — «Стан міста» коротко;
  metodyka.html      — спільний додаток.

Старі адреси (doslidzhennya, analiz, rezyume) переводять сюди з тими самими
якорями — step6_docs.

Одне джерело чисел (PLAN-ZVITY, п. 2): звіти беруть точки міської карти
(step3_map.LAST_KARTA), а не базу окремо. Події без номера будинку — лише
рядком у «Стані міста». Збірка падає, якщо сума подій звіту не дорівнює
сумі на карті.

Жодних оцінних слів і пояснень, яких немає в даних (CLAUDE.md): лише
виміряне й «як перевірити на місці». Слів «ризик», «прогноз», «причина»
немає — шар зветься «Схожі умови».
"""
import os, sys, json, math, collections, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import labels as L
import mech as M

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')

VYDY = list(L.ORDER)
KOROTKO = {'ГП': 'Порядок', 'АЛК': 'Торгівля', 'НАР': 'Наркотики', 'НАС': 'Насильство',
           'МАЙ': 'Майно', 'ДТП': 'ДТП', 'ДОР': 'Порушення на дорозі'}
DOROZHNI = {'ДТП', 'ДОР'}
# палітра «Яскрава», світла (розд. 23) — та сама, що на карті; сьомий колір —
# «Порушення на дорозі» (34.3), перевірений на дальтонізм разом з рештою
KOLIR = dict(zip(VYDY, ['#DF6D40', '#28AB7D', '#5244A5', '#D85151', '#367BCE', '#118412', '#8a7e9c']))
MIS = ['січ', 'лют', 'бер', 'кві', 'тра', 'чер', 'лип', 'сер', 'вер', 'жов', 'лис', 'гру']


def esc(t):
    return (str(t).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;'))


def num(n):
    return f'{int(round(n)):,}'.replace(',', ' ')


def pct(x, d=0):
    return (f'{100 * x:.{d}f}').replace('.', ',') + '%'


def dec(x, d=1):
    return f'{x:.{d}f}'.replace('.', ',')


def pl(n, a, b, c):
    n = abs(int(n)) % 100
    if 11 <= n <= 14: return c
    return a if n % 10 == 1 else b if 2 <= n % 10 <= 4 else c


# ------------------------------------------------------------- оболонка
CSS = """
:root{--bg:#fff;--ink:#1d232b;--dim:#5b636e;--faint:#6f7680;--rule:#e3e6ea;--sunk:#f5f6f8;--acc:#2f5fa8}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#15181d;--ink:#e6e9ee;--dim:#a9b1bd;
 --faint:#8a92a0;--rule:#2a2f37;--sunk:#1d2127;--acc:#8ab4f0}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif;padding:0 16px 80px}
.wrap{max-width:880px;margin:0 auto}
a{color:var(--acc)}
header{padding:26px 0 14px;border-bottom:1px solid var(--rule);margin-bottom:22px}
.nav{font-size:13px;display:flex;gap:14px;flex-wrap:wrap}
.nav a{color:var(--dim);text-decoration:none}.nav a[aria-current]{color:var(--ink);font-weight:600}
h1{font-size:26px;letter-spacing:-.02em;margin:14px 0 4px}
h2{font-size:19px;margin:34px 0 8px;padding-top:12px;border-top:1px solid var(--rule)}
h3{font-size:15.5px;margin:22px 0 6px}
.sub,.muted{color:var(--dim);font-size:13.5px}
.muted{font-size:12.5px}
table{border-collapse:collapse;width:100%;margin:10px 0;font-size:13.5px}
th,td{padding:6px 8px;text-align:left;border-bottom:1px solid var(--rule);vertical-align:top}
th{color:var(--dim);font-weight:500;font-size:12px}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.tw{overflow-x:auto}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:10px;margin:12px 0}
.card{background:var(--sunk);border-radius:9px;padding:11px 13px}
.card .lab{color:var(--dim);font-size:12px}.card .big{font-size:24px;font-weight:600}
.sw{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px;vertical-align:0}
.bar{height:8px;background:var(--rule);border-radius:4px;overflow:hidden;min-width:60px}
.bar i{display:block;height:100%}
.box{background:var(--sunk);border-radius:9px;padding:12px 14px;margin:12px 0}
.empty{border:1px dashed var(--faint);border-radius:8px;padding:8px 12px;color:var(--dim);font-size:13px;margin:8px 0}
.hist{display:flex;align-items:flex-end;gap:2px;height:60px;margin:8px 0 2px}
.hist i{flex:1;background:var(--acc);opacity:.75;border-radius:2px 2px 0 0;min-height:1px}
.hist i.part{opacity:.3}
.hx{display:flex;justify-content:space-between;font-size:11px;color:var(--faint)}
.tag{display:inline-block;font-size:12px;border:1px solid var(--rule);border-radius:10px;padding:0 8px;margin:0 4px 4px 0}
.prob{border-top:1px solid var(--rule);padding-top:10px;margin-top:24px}
@media print{body{background:#fff;color:#111;padding:0}.nav{display:none}.card,.box{background:none;border:1px solid #ccc}
 .prob{break-before:page;border:0}a{color:#111;text-decoration:none}}
"""

STORINKY = [('problemy.html', 'Проблеми'), ('skhozhi-umovy.html', 'Схожі умови'),
            ('stan-mista.html', 'Стан міста'), ('metodyka.html', 'Методика')]


def page(fn, title, lead, body, script=''):
    nav = ''.join(f'<a href="{f}"' + (' aria-current="page"' if f == fn else '') + f'>{esc(t)}</a>'
                  for f, t in STORINKY)
    return ('<!DOCTYPE html><html lang="uk"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(title)}</title><style>{CSS}</style></head><body><div class="wrap">'
            f'<header><div class="nav"><a href="index.html">← карта</a>{nav}</div>'
            f'<h1>{esc(title)}</h1><div class="sub">{lead}</div></header>{body}'
            f'<p class="muted" style="margin-top:40px">Складено {dt.date.today().strftime("%d.%m.%Y")} з тих самих даних, '
            'що й карта. Адреси — з текстів рішень ЄДРСР: це місце, де подію оформлено, і воно не '
            'завжди збігається з місцем, де все сталося.</p></div>'
            f'{script}</body></html>')


def hist(vals, labels_=None, part=()):
    mx = max(vals) or 1
    h = '<div class="hist">' + ''.join(
        f'<i{" class=part" if i in part else ""} style="height:{max(2, round(58 * v / mx))}px" '
        f'title="{esc(labels_[i] if labels_ else i)} — {num(v)}"></i>' for i, v in enumerate(vals)) + '</div>'
    if labels_:
        h += f'<div class="hx"><span>{esc(labels_[0])}</span><span>{esc(labels_[len(labels_) // 2])}</span><span>{esc(labels_[-1])}</span></div>'
    return h


# ------------------------------------------------------------- дані карти
def dani():
    """Точки міської карти й усе, що до них треба. Карта мусить бути зібрана
    в цьому ж процесі (step5_site: спершу карта, потім звіти)."""
    import step3_map as S3
    K = S3.LAST_KARTA
    if not K: raise RuntimeError('немає міської карти в пам\'яті — спершу step3_map')
    meta, labels = K['meta'], K['labels']
    th_of = [lb[0] for lb in labels]
    D = dict(K)
    D['th_of'] = th_of
    D['doma'] = [p for p in K['P'] if p[3]]          # точний будинок
    D['vulytsi'] = [p for p in K['P'] if not p[3]]   # центр вулиці — на карті немає
    D['mon0'] = meta.get('mon0', '2023-01')
    D['mon_n'] = meta.get('mon_n', 45)
    D['dnames'] = meta.get('dnames', [])
    def js(n):
        pth = os.path.join(DATA, n)
        return json.load(open(pth, encoding='utf-8')) if os.path.exists(pth) else {}
    D['PR'] = js('problems_report.json')
    D['RAD'] = js('radiusy.json')
    D['POPJ'] = js('population.json')
    D['BORD'] = js('borders.json')
    # затримка публікації: від дати події до дати рішення, для подій із датою
    zt = []
    V = S3.LAST_VYBIR or {}
    for r in V.get('rows', []):
        ed = S3.ev_date(V['TKD'].get(r[0]), r[3])
        if ed and r[3]:
            try: zt.append((dt.date.fromisoformat(r[3][:10]) - dt.date.fromisoformat(ed[:10])).days)
            except ValueError: pass
    zt.sort()
    D['zatrymka'] = (zt[len(zt) // 2], zt[int(len(zt) * .9)]) if zt else None
    D['plosha'] = V.get('plosha')
    # події, поставлені на перехрестя (завдання 30, 4.4)
    D['perekhrestia'] = sum(1 for r in V['rows'] if r[9] == 'cross')
    return D


def mon_label(D, i):
    y0, m0 = int(D['mon0'][:4]), int(D['mon0'][5:7])
    k = (m0 - 1) + i
    return f'{MIS[k % 12]} {y0 + k // 12}'


# ============================================================ СТАН МІСТА
def stan_mista(D):
    doma, th_of = D['doma'], D['th_of']
    ev = [(p, e) for p in doma for e in p[4]]
    n = len(ev)
    by_th = collections.Counter(th_of[e[1]] for _p, e in ev)
    n_vul = sum(len(p[4]) for p in D['vulytsi'])
    b = []
    b.append('<div class="cards">' + f'<div class="card"><div class="lab">подій на карті</div><div class="big">{num(n)}</div></div>'
             + f'<div class="card"><div class="lab">адрес</div><div class="big">{num(len(doma))}</div></div>'
             + ''.join(f'<div class="card"><div class="lab"><span class="sw" style="background:{KOLIR[t]}"></span>{KOROTKO[t]}</div>'
                       f'<div class="big">{num(by_th[t])}</div><div class="muted">{pct(by_th[t] / n if n else 0)}</div></div>'
                       for t in VYDY if by_th[t]) + '</div>')
    b.append(f'<p class="muted">Ще {num(n_vul)} {pl(n_vul, "подія", "події", "подій")} з назвою вулиці, але без номера '
             'будинку, — на карту й у підрахунки звітів не йдуть.</p>')

    # ---- концентрація ----
    cnt = sorted((len(p[4]) for p in doma), reverse=True)
    b.append('<h2>Концентрація</h2><table><tr><th>Частка адрес</th><th class="n">Адрес</th><th class="n">Частка подій</th></tr>')
    for s in (0.01, 0.05, 0.10):
        k = max(1, int(len(cnt) * s))
        b.append(f'<tr><td>верхні {pct(s)}</td><td class="n">{num(k)}</td><td class="n">{pct(sum(cnt[:k]) / n if n else 0)}</td></tr>')
    once = sum(1 for c in cnt if c == 1)
    b.append(f'</table><p class="muted">На {pct(once / len(cnt) if cnt else 0)} адрес — одна подія за весь період.</p>')

    # ---- райони на 10 тис. мешканців ----
    import map_problems as MP
    dn = D['dnames']
    if dn:
        pop = collections.Counter()
        for la, lo, pp in (D['POPJ'] or {}).get('items', []):
            for d, ring in (D['BORD'] or {}).items():
                if MP.in_ring(la, lo, ring): pop[d] += pp; break
        dc = collections.Counter(); dth = collections.defaultdict(collections.Counter)
        for p in doma:
            di = p[8] if len(p) > 8 else -1
            if di >= 0:
                dc[dn[di]] += len(p[4])
                for e in p[4]: dth[dn[di]][th_of[e[1]]] += 1
        b.append('<h2>Райони</h2><p class="muted">Населення — оцінка кількості мешканців '
                 '(data/population.json).</p><div class="tw"><table><tr><th>Район</th>'
                 '<th class="n">Подій</th><th class="n">На 10 тис. мешканців</th>'
                 + ''.join(f'<th class="n">{KOROTKO[t]}</th>' for t in VYDY) + '</tr>')
        for d in sorted(dn, key=lambda d: -dc[d] / max(pop[d], 1)):
            b.append(f'<tr><td>{esc(d)}</td><td class="n">{num(dc[d])}</td>'
                     f'<td class="n">{dec(1e4 * dc[d] / pop[d]) if pop[d] else "—"}</td>'
                     + ''.join(f'<td class="n">{num(dth[d][t])}</td>' for t in VYDY) + '</tr>')
        b.append('</table></div>')

    # ---- час доби ----
    h = [0] * 24
    for _p, e in ev:
        if e[3] >= 0: h[e[3]] += 1
    nk = sum(h)
    # нічне вікно — те саме, що в картці місця
    night = sum(h[20:]) + sum(h[:4])
    b.append('<h2>Час доби</h2>' + hist(h, [f'{i}:00' for i in range(24)])
             + f'<p>Година відома для {pct(nk / n if n else 0)} подій. З них {pct(night / nk if nk else 0)} — '
             'між 20:00 і 04:00.</p>')

    # ---- динаміка ----
    mm = [0] * D['mon_n']
    for _p, e in ev:
        if 0 <= e[5] < len(mm): mm[e[5]] += 1
    part = {len(mm) - 1, len(mm) - 2}
    b.append('<h2>Динаміка за датою події</h2>' + hist(mm, [mon_label(D, i) for i in range(len(mm))], part)
             + '<p class="muted">Блідіші — останні два місяці: рішення публікують із затримкою, тож ці місяці '
             'ще неповні. Дата — дата самої події з тексту рішення; де її немає — дата рішення.</p>')
    kv = collections.Counter()
    for _p, e in ev:
        if e[5] >= 0:
            y0 = int(D['mon0'][:4]); k = e[5]
            kv[(y0 + k // 12, k % 12 // 3 + 1)] += 1
    b.append('<div class="tw"><table><tr><th>Рік</th>' + ''.join(f'<th class="n">К{q}</th>' for q in range(1, 5))
             + '<th class="n">Разом</th></tr>' + ''.join(
                 f'<tr><td>{y}</td>' + ''.join(f'<td class="n">{num(kv[(y, q)]) if kv[(y, q)] else "—"}</td>' for q in range(1, 5))
                 + f'<td class="n">{num(sum(kv[(y, q)] for q in range(1, 5)))}</td></tr>'
                 for y in sorted({k[0] for k in kv})) + '</table></div>')

    # ---- перекоси даних ----
    ACLS = ['B', 'A', 'C', 'D', '']
    try:
        import step3_map as S3
        ACLS = S3.ACLS
    except Exception:
        pass
    kl = collections.Counter(ACLS[e[4]] if e[4] < len(ACLS) else '' for _p, e in ev)
    dtp = sum(1 for _p, e in ev if th_of[e[1]] in DOROZHNI)
    b.append('<h2>Що треба знати про ці дані</h2><ul>'
             '<li>Це лише події, які дійшли до суду й мають опубліковане рішення в ЄДРСР. Чого не оформили '
             'протоколом чи вироком, тут немає.</li>'
             f'<li>ДТП і порушення на дорозі — {pct(dtp / n if n else 0)} усіх подій, тож загальні суми здебільшого про '
             'дороги; кожен вид варто читати окремо.</li>'
             f'<li>Адресу підтверджено в описі самої події (клас B) для {pct(kl["B"] / n if n else 0)} подій; '
             f'класи C і D — {pct((kl["C"] + kl["D"]) / n if n else 0)}. Проблеми й «Схожі умови» рахуються лише на '
             'класі B.</li>'
             + (f'<li>Площа без номера будинку в тексті рішення — не точний будинок: таких подій знято '
                f'{len(D["plosha"])} ({esc("; ".join(D["plosha"][:20]))}). Справжні «площа, буд. 1» лишаються.</li>'
                if D.get('plosha') is not None else '')
             + (f'<li>Подій на перехрестях — без номера будинку, але з перехрестям двох вулиць в описі, '
                f'поставлених у точку перетину вулиць: {num(D["perekhrestia"])}.</li>'
                if D.get('perekhrestia') else '')
             + (f'<li>Між подією й рішенням минає в середньому (медіана) {D["zatrymka"][0]} днів, у кожної '
                f'десятої події — понад {D["zatrymka"][1]}. Тому останні місяці завжди неповні.</li>'
                if D.get('zatrymka') else '') +
             f'<li>Події без номера будинку ({num(n_vul)}) на карту не йдуть.</li></ul>')
    return b, n


# ============================================================ НОВІ РОЗРАХУНКИ (PLAN-ZVITY, 5)
def binom_sf(k, n, p):
    """P(X ≥ k) для біноміального розподілу — нормальне наближення з
    поправкою на неперервність; для n ≥ 20 цього досить."""
    if n <= 0: return 1.0
    mu, sd = n * p, math.sqrt(n * p * (1 - p)) or 1e-9
    z = (k - 0.5 - mu) / sd
    return 0.5 * math.erfc(z / math.sqrt(2))


def zaklady(D, rng):
    """5.1. Серед закладів одного типу — які кілька дають більшість подій
    поруч (J-крива, Ек і Кларк). Події — усі, крім дорожнього руху (ДТП біля
    ТЦ — про паркінг, а не про заклад), у 50 м від закладу."""
    import problems as PRB
    zj = os.path.join(DATA, 'zaklady.json')
    if not os.path.exists(zj): return []
    Z = json.load(open(zj, encoding='utf-8'))
    doma, th_of = D['doma'], D['th_of']
    pts = [(p[0], p[1]) for p in doma]
    w = [sum(1 for e in p[4] if th_of[e[1]] not in DOROZHNI) for p in doma]
    g = PRB.Pts(pts)
    b = ['<h2 id="zaklady">Заклади, біля яких подій найбільше</h2><p>Для кожного типу закладів — скільки подій '
         '(без дорожнього руху) в 50 м від кожного і яку частку всіх таких подій дають верхні 10% закладів. '
         'Поруч — скільки дали б верхні 10%, якби ті самі події розкидати між закладами навмання. Це '
         'близькість, а не пояснення: адреса в рішенні — місце, де подію оформлено.</p>'
         '<div class="tw"><table><tr><th>Тип</th><th class="n">Закладів з подіями</th><th class="n">Верхні 10% дають</th>'
         '<th class="n">Навмання</th><th>Найбільше подій поруч</th></tr>']
    for k, c in Z.items():
        cnt = []
        for (la, lo), nm in zip(c['pts'], c['nm']):
            n = sum(w[j] for j in g.near(la, lo, 50))
            cnt.append((n, nm, la, lo))
        tot = sum(x[0] for x in cnt)
        if tot < 30 or len(cnt) < 20: continue
        srt = sorted(cnt, key=lambda x: -x[0])
        k10 = max(1, len(srt) // 10)
        top = sum(x[0] for x in srt[:k10]) / tot
        # навмання: ті самі tot подій рівномірно між закладами, 20 разів
        rnd = []
        for _ in range(20):
            a = rng.multinomial(tot, [1 / len(cnt)] * len(cnt))
            a.sort(); rnd.append(a[::-1][:k10].sum() / tot)
        names = []
        for n, nm, la, lo in srt[:5]:
            if not n: break
            near = min(range(len(pts)), key=lambda j: (pts[j][0] - la) ** 2 + (pts[j][1] - lo) ** 2)
            # назви закладів у публічному звіті не показуємо (розд. 30, п. 6;
            # розд. 28) — лише адреса найближчої точки карти
            names.append(f'{esc(doma[near][2])} — {n}')
        b.append(f'<tr><td>{esc(c["n"])}</td><td class="n">{sum(1 for x in cnt if x[0])} з {len(cnt)}</td>'
                 f'<td class="n">{pct(top)}</td><td class="n">{pct(sum(rnd) / len(rnd))}</td>'
                 f'<td class="muted">{"; ".join(names)}</td></tr>')
    b.append('</table></div>')
    return b


def near_repeat(D, rng, R=200, T=14, N=99):
    """5.2. Тест Нокса (як Near Repeat Calculator, Ratcliffe): чи пар подій
    «до 200 м і до 14 днів» більше, ніж коли дати перемішати між тими
    самими місцями. Лише події з датою події з тексту й точним будинком."""
    import numpy as np, problems as PRB
    doma, th_of, DOCS = D['doma'], D['th_of'], D.get('DOCS') or []
    idx_of = {id(p): i for i, p in enumerate(D['P'])}
    by = collections.defaultdict(list)
    for p in doma:
        i = idx_of[id(p)]
        for j, e in enumerate(p[4]):
            if i < len(DOCS) and j < len(DOCS[i]):
                x = DOCS[i][j]
                if len(x) > 6 and x[6]: continue          # дата рішення, не події
                try: d = dt.date.fromisoformat(str(x[1])[:10]).toordinal()
                except ValueError: continue
                by[th_of[e[1]]].append((p[0], p[1], d))
    b = ['<h2 id="povtorni">Повторні й сусідні події</h2><p>Чи йде за подією інша того самого виду поблизу '
         f'(до {R} м) і невдовзі (до {T} днів) частіше, ніж випадково. Випадковість — ті самі місця, але дати '
         f'перемішані між ними {N} разів (тест Нокса).</p><table><tr><th>Вид</th><th class="n">Подій з датою</th>'
         '<th class="n">Пар «близько й невдовзі»</th><th class="n">Випадково</th><th class="n">У скільки разів більше</th><th class="n">p</th></tr>']
    for t in VYDY:
        ev = by.get(t, [])
        if len(ev) < 100: continue
        if t in DOROZHNI:
            b.append(f'<tr><td>{KOROTKO[t]}</td><td class="n">{num(len(ev))}</td><td colspan="4" class="muted">'
                     'не рахується: близьких пар десятки мільйонів (ДТП біля тих самих ТЦ)</td></tr>')
            continue
        pts = [(a, c) for a, c, _d in ev]
        g = PRB.Pts(pts)
        I, J = [], []
        for i, (la, lo) in enumerate(pts):
            for j in g.near(la, lo, R):
                if j > i: I.append(i); J.append(j)
        I, J = np.array(I, dtype=np.int64), np.array(J, dtype=np.int64)
        d = np.array([x[2] for x in ev])
        obs = int((np.abs(d[I] - d[J]) <= T).sum()) if len(I) else 0
        sim = []
        for _ in range(N):
            dd = rng.permutation(d)
            sim.append(int((np.abs(dd[I] - dd[J]) <= T).sum()) if len(I) else 0)
        exp = sum(sim) / N
        pv = (1 + sum(1 for s in sim if s >= obs)) / (N + 1)
        b.append(f'<tr><td>{KOROTKO[t]}</td><td class="n">{num(len(ev))}</td><td class="n">{num(obs)}</td>'
                 f'<td class="n">{dec(exp)}</td><td class="n">{dec(obs / exp, 2) if exp else "—"}</td>'
                 f'<td class="n">{dec(pv, 2)}</td></tr>')
    b.append('</table><p class="muted">p — частка перемішувань, у яких пар було стільки ж або більше; '
             f'менше 0,05 — надлишок не випадковий. Найменше можливе p тут — {dec(1 / (N + 1), 2)}.</p>')
    return b


def khronichni(D):
    """5.3. Хронічні проти спалахових місць: адреси з ≥ 10 подіями — у скількох
    кварталах були події; «хронічне» — у половині кварталів і більше;
    «спалах» — понад половина подій в одному кварталі. Стійкість — чи
    лишається клас, якщо відкинути один рік."""
    y0 = int(D['mon0'][:4]); nq = (D['mon_n'] + 2) // 3
    def klas(evs, drop=None):
        qs = collections.Counter(e[5] // 3 for e in evs if e[5] >= 0 and (drop is None or y0 + e[5] // 12 != drop))
        n = sum(qs.values())
        if n < 10: return None
        nq_ = nq - (4 if drop is not None else 0)
        if max(qs.values()) * 2 > n: return 'спалах'
        if len(qs) * 2 >= nq_: return 'хронічне'
        return 'між ними'
    res = collections.Counter(); stale = 0; tot = 0; prykl = collections.defaultdict(list)
    for p in D['doma']:
        k = klas(p[4])
        if not k: continue
        res[k] += 1; tot += 1
        if len(prykl[k]) < 6: prykl[k].append(p[2])
        years = {y0 + e[5] // 12 for e in p[4] if e[5] >= 0}
        if all(klas(p[4], y) in (k, None) for y in years): stale += 1
    if not tot: return []
    return [f'<h2 id="khronichni">Хронічні й спалахові місця</h2><p>Адреси з 10 і більше подіями ({num(tot)}): '
            f'у скількох із {nq} кварталів були події.</p><table><tr><th>Клас</th><th class="n">Адрес</th><th>Приклади</th></tr>'
            + ''.join(f'<tr><td>{k}</td><td class="n">{num(res[k])}</td><td class="muted">{esc("; ".join(prykl[k]))}</td></tr>'
                      for k in ('хронічне', 'між ними', 'спалах') if res[k])
            + f'</table><p class="muted">Хронічне — події в половині кварталів і більше; спалах — понад половина подій '
            f'в одному кварталі. Якщо відкинути будь-який один рік, клас лишається тим самим для {pct(stale / tot)} адрес.</p>']


def mistse_hodyna(D):
    """5.4. Вулиці, де частка нічних (20:00–04:00) чи денних подій помітно
    відрізняється від міської: ≥ 20 подій з відомою годиною, біноміальний
    тест, p < 0,001 (вулиць сотні — поріг суворий, щоб не ловити випадок)."""
    # «вул. О. Екстер» і «вул. Олександри Екстер» — одна вулиця: групуємо за
    # ключем геокодера без ініціалів, показуємо найчастіше написання
    from step2_geocode import skey
    st = collections.defaultdict(lambda: [0, 0]); nm = collections.defaultdict(collections.Counter)
    for p in D['doma']:
        s0 = (p[2] or '').split(',')[0].strip()
        s = ' '.join(w for w in skey(s0).split() if len(w) > 1)
        nm[s][s0] += len(p[4])
        for e in p[4]:
            if e[3] >= 0:
                st[s][0] += 1
                if e[3] >= 20 or e[3] < 4: st[s][1] += 1
    N = sum(v[0] for v in st.values()); K = sum(v[1] for v in st.values())
    if not N: return []
    p0 = K / N
    nich, den = [], []
    for s, (n, k) in st.items():
        if n < 20 or not s: continue
        s1 = nm[s].most_common(1)[0][0]
        if binom_sf(k, n, p0) < 0.001: nich.append((k / n, s1, n))
        elif binom_sf(n - k, n, 1 - p0) < 0.001: den.append((k / n, s1, n))
    row = lambda x: f'<tr><td>{esc(x[1])}</td><td class="n">{x[2]}</td><td class="n">{pct(x[0])}</td></tr>'
    head = '<table><tr><th>Вулиця</th><th class="n">Подій з годиною</th><th class="n">Нічних</th></tr>'
    b = [f'<h2 id="hodyna">Місце й година</h2><p>По місту {pct(p0)} подій з відомою годиною — між 20:00 і 04:00 '
         '(як у розділі «Час доби»). Вулиці, де ця частка значуще інша (≥ 20 подій, біноміальний тест, p &lt; 0,001).</p>']
    if nich: b.append(f'<h3>Нічних більше — {len(nich)}</h3>' + head + ''.join(row(x) for x in sorted(nich, reverse=True)[:20]) + '</table>')
    if den: b.append(f'<h3>Денних більше — {len(den)}</h3>' + head + ''.join(row(x) for x in sorted(den)[:20]) + '</table>')
    return b


# ============================================================ СХОЖІ УМОВИ
def nazva_chynnyka(base):
    """'бари' -> 'Бари, клуби'; величини — людською назвою з map_layers"""
    import step2e_factors as F2, map_layers as ML
    for _k, n, b, _g in F2.CATS:
        if b == base: return n
    s = ML.FSCALE.get(base)
    return (s[0][0].upper() + s[0][1:]) if s else base.replace('_', ' ')


def rr_int(d):
    a, b_ = d.get('RR_від'), d.get('RR_до')
    if a is None or b_ is None: return '—'
    f = lambda x: '∞' if x >= 1e5 else '0' if x < 0.005 else dec(x, 2)
    return f'{f(a)}–{f(b_)}'


def skhozhi_umovy(D):
    ER = D.get('ER') or {}
    RK = (D.get('risks') or {}).get('lines', {})
    # Модель «разом» (RISHENNYA 33.2.1; ZAVDANNYA-30, ч. 3) — з перенавчання
    # 30.09; до нього в engine_report лежить модель лише середовища
    novi = any('PAI_як_рахувалося' in v for v in ER.values() if isinstance(v, dict))
    b = ['<p>Шар показує вулиці, де події ймовірні далі, за всім, що про них відомо: події, що вже були, і '
         'середовище довкола (Caplan, Kennedy). Він не пояснює подій: гіпотезу, чому тут, висуває людина на місці.</p>']
    if not novi:
        b.append('<div class="empty">Модель ще не перенавчена за завданням 30: числа нижче — з попередньої '
                 'моделі лише середовища. Після перенавчання звіт оновиться сам.</div>')
    b.append('<div class="box"><b>Як читати.</b> Вулиці впорядковано за оцінкою на метр. <i>Влучність</i> — '
             'яка частка подій наступного року припала на вулиці з найвищою оцінкою, що разом займають 10% '
             'довжини вулиць міста; навмання було б 10%. <i>PAI</i> — у скільки разів це краще за навмання. '
             'Модель вчилася на історії 2024 і подіях 2025, а перевірялася на історії 2025 і подіях 2026; і окремо — '
             'вчилася на західній половині міста, а перевірялася на східній. Для порівняння — та сама перевірка '
             'лише для історії подій і лише для середовища.</div>')
    keys = [t for t in VYDY if isinstance(ER.get(t), dict)] + \
           [k for k, v in ER.items() if isinstance(v, dict) and v.get('вид') == 'механізм']
    b.append('<div class="tw"><table><tr><th>Вид / механізм</th><th>На карті</th><th class="n">Влучність</th>'
             '<th class="n">PAI</th><th class="n">лише історія</th><th class="n">лише середовище</th>'
             '<th class="n">Захід → схід</th><th class="n">Вулиць показано / з подіями потім</th></tr>')
    for t in keys:
        e = ER[t]
        th = M.simtheme(t)
        on = e.get('на_карті', bool(RK.get('risk_' + t, {}).get('items')))
        nm = KOROTKO.get(t) or e.get('назва') or t
        hit = e.get('hit_разом', e.get('hit_середовище')) if novi else e.get('hit_середовище')
        pai_ = e.get('PAI_разом', e.get('PAI_середовище')) if novi else e.get('PAI_середовище')
        b.append(f'<tr><td><span class="sw" style="background:{KOLIR.get(th, "#888")}"></span><a href="#t-{M.anchor(t)}">{esc(nm)}</a>'
                 + (f'<div class="muted">{esc(e["позначка"])}</div>' if e.get('позначка') else '') + '</td>'
                 f'<td>{"так" if on else "ні — " + esc(e.get("сховано") or "даних замало")}</td>'
                 f'<td class="n">{pct(hit) if hit is not None else "—"}</td>'
                 f'<td class="n">{dec(pai_) if pai_ is not None else "—"}</td>'
                 f'<td class="n">{dec(e["PAI_історія"]) if novi and "PAI_історія" in e else "—"}</td>'
                 f'<td class="n">{dec(e["PAI_середовище"]) if novi and "PAI_середовище" in e else "—"}</td>'
                 f'<td class="n">{pct(e["hit_інший_район"]) if e.get("hit_інший_район") is not None else "—"}</td>'
                 f'<td class="n">{str(e.get("вулиць_показано", "—"))} / {str(e.get("з_них_збулося", "—"))}</td></tr>')
    b.append('</table></div>')
    for t in keys:
        e = ER[t]
        th = M.simtheme(t)
        b.append(f'<h2 id="t-{M.anchor(t)}"><span class="sw" style="background:{KOLIR.get(th, "#888")}"></span>'
                 f'{esc(L.THEMES.get(t) or e.get("назва") or t)}</h2>')
        if e.get('позначка'):
            b.append(f'<p><span class="tag">{esc(e["позначка"])}</span> ' + (
                'Такі події поліція здебільшого виявляє сама: шар показує й те, де вона частіше працює.'
                if e['позначка'] == 'проактивний вид' else
                'Частину таких подій поліція виявляє сама: шар почасти показує й те, де вона частіше працює.') + '</p>')
        if novi and e.get('метод'): b.append(f'<p>{esc(e["метод"])}</p>')
        if e.get('сховано') and not e.get('на_карті', True):
            b.append(f'<div class="empty">На карті цього шару немає: {esc(e["сховано"])}. '
                     'Для цього виду даних замало, і малювати його з натяжкою не будемо.</div>')
        ch = e.get('чинники')
        if ch:
            b.append('<h3>Що поруч там, де подій більше</h3><div class="tw"><table><tr><th>Чинник</th><th>Як виміряно</th>'
                     '<th class="n">Подій частіше, разів</th><th class="n">95%</th><th>Джерело</th></tr>')
            for d in ch:
                form = (f'є в {d["r"]} м' if d['форма'] == 'є' else f'кожен ще один у {d["r"]} м'
                        if d['форма'] == 'скільки' else 'на одне стандартне відхилення')
                b.append(f'<tr><td>{esc(nazva_chynnyka(d["тип"]))}</td><td>{form}</td><td class="n"><b>{dec(d["RR"], 2)}</b></td>'
                         f'<td class="n">{rr_int(d)}</td><td class="muted">{esc(d["джерело"])}</td></tr>')
            b.append('</table></div><p class="muted">Менше за 1 — подій там менше. Число — з моделі, у якій '
                     'історія подій і всі стійкі чинники разом; це близькість, а не пояснення.</p>')
            nesk = [nazva_chynnyka(d['тип']) for d in ch if (d.get('RR_до') or 0) >= 1e5]
            if nesk:
                # «0–∞»: у колі цього типу подій виду немає зовсім (розділення).
                # Адреси установ карта прибирає (map_excl), тож біля них подій
                # може не бути саме через це — пишемо лише факт.
                b.append(f'<p class="muted">{esc(", ".join(nesk))}: у цьому колі подій цього виду немає '
                         'зовсім, тому кратність і її межі не визначені («0–∞»). Адреси установ карта не '
                         'показує, і це могло спричинити нуль.</p>')
        elif novi and 'чинники' in e:
            b.append('<p>Жоден чинник середовища не пройшов відбір стійкості — оцінку дає історія подій.</p>')
        elif not novi:
            b.append('<div class="empty">Чинники — після перенавчання.</div>')
        lay = RK.get('risk_' + t) or {}
        it = [x for x in lay.get('items', []) if x[1] and x[1] != 'без назви']
        if it:
            b.append('<h3>Вулиці з найвищою оцінкою</h3><div class="tw"><table class="st"><tr><th>#</th><th>Вулиця</th>'
                     f'<th class="n">{"Подій за 2 роки" if lay.get("n2") else "Подій за роки навчання"}</th></tr>' + ''.join(
                         f'<tr data-st="{esc(x[1])}"><td class="n">{i + 1}</td><td>{esc(x[1])}</td><td class="n">{x[3]}</td></tr>'
                         for i, x in enumerate(it[:40])) + '</table></div>')
    # ?st=<вулиця> — посилання з вікна вулиці на карті підсвічує її рядок
    script = ('<script>{const s=new URLSearchParams(location.search).get("st");if(s){'
              'const r=[...document.querySelectorAll("tr[data-st]")].find(x=>x.dataset.st===s);'
              'if(r){r.style.background="var(--sunk)";r.style.fontWeight="600";if(!location.hash)r.scrollIntoView({block:"center"})}}}</script>')
    return b, script


# ============================================================ ПРОБЛЕМИ
GOLOS = {'підтверджують': 'підтверджують', 'мовчать': 'мовчать',
         'не вимірюється': 'не вимірюється — про цей вид 1551 мовчить', 'немає даних': 'даних 1551 немає'}


def near_objs(D, p, lim=15):
    out = []
    my, mx = 111320.0, 111320.0 * math.cos(math.radians(p[0]))
    for c in (D.get('FACT') or {}).get('cats', []):
        r = c.get('r') or 250
        for q in c['pts']:
            d = math.hypot((q[0] - p[0]) * my, (q[1] - p[1]) * mx)
            if d <= r: out.append((round(d), c['n']))
    return sorted(out)[:lim]


def problemy(D):
    P, DOCS, labels, th_of = D['P'], D.get('DOCS') or [], D['labels'], D['th_of']
    cats = D['meta']['cats']
    rep_ = D.get('PR') or {}
    items = []
    for i, p in enumerate(P):
        for q in (p[7] if len(p) > 7 else []):     # p[7] — проблеми точки (map_problems)
            if q.get('city'): items.append((i, q))
    # порядок — як у відборі (Р6): події за останні 4 квартали, далі за весь час
    order = {(r['sim'], (r.get('adresy') or [''])[0]): k for k, r in enumerate(rep_.get('perelik', []))}
    # запис відбору для проблеми карти: тип місця й посібник живуть лише тут,
    # у звіті, — на карту вони не йдуть (завдання 30, ч. 2)
    rec_of = {(r['sim'], (r.get('adresy') or [''])[0]): r for r in rep_.get('perelik', [])}
    items.sort(key=lambda x: order.get((x[1]['sim'], (x[1].get('adresy') or [''])[0]), 1e9))
    dn = D['dnames']
    b = ['<p>Проблема — пара «місце × механізм», яка пройшла всі ворота: адресу підтверджено в описі '
         'події; більшість подій заявні, а не виявлені поліцією; щонайменше 12 окремих подій за останні '
         '2 роки у 5 різних кварталах з 8; остання — не старша за рік; і місце густіше, ніж дало б випадкове '
         'розкидання тих самих подій (<a href="metodyka.html#vorota">ворота</a>). Скупчення, яке з тим самим '
         'порогом виявляє сама поліція (розпивання, стихійна торгівля), — «проблема, яку фіксує поліція»; '
         'наркотики й сп\'яніння за кермом сюди не йдуть. Квот за видами й районами немає: у переліку все, '
         'що пройшло.</p>']
    if rep_:
        b.append(f'<p class="muted">Окремо, не в переліку: {num(rep_.get("dorozhnikh_dilianok", 0))} дорожніх ділянок '
                 'з ДТП без потерпілих (інша природа — знаменник тут транспортний потік) і '
                 f'{num((rep_.get("formuietsia") or {}).get("vsogo", 0))} місць, де проблема, можливо, формується '
                 '(на карту — після рішення про 1551).</p>')
    b.append('<div class="tw"><table><tr><th>#</th><th>Місце</th><th>Що відбувається</th><th>Район</th>'
             '<th class="n">Подій</th><th>Мешканці (1551)</th></tr>')
    for k, (i, q) in enumerate(items, 1):
        p = P[i]
        b.append(f'<tr><td class="n">{k}</td><td><a href="#p-{k}">{esc(p[2])}</a>'
                 + (f' <span class="tag">{esc(q["riven"])}</span>' if q.get('riven') in ('лінія', 'ділянка') else '')
                 + (' <span class="tag">фіксує поліція</span>' if q.get('status') == 'фіксує поліція' else '') + '</td>'
                 f'<td><span class="sw" style="background:{KOLIR.get(M.simtheme(q["sim"]), "#888")}"></span>{esc(q["mech"])}</td>'
                 f'<td>{esc(dn[p[8]] if len(p) > 8 and 0 <= p[8] < len(dn) else "—")}</td><td class="n">{q["n"]}</td>'
                 f'<td>{esc(((q.get("golos") or {}).get("stan")) or "—")}</td></tr>')
    b.append('</table></div>')
    for k, (i, q) in enumerate(items, 1):
        p = P[i]
        th = M.simtheme(q['sim'])
        labs = {a for a, _n in q.get('arts', [])}
        # Події проблеми — саме ті, що їх рахували ворота, з усіх її адрес
        # (q['ev'], завдання 29, п. 2); старий запис без ev — події точки
        refs = [tuple(x) for x in q.get('ev') or []] or \
               [(i, j) for j, e in enumerate(p[4]) if cats[e[1]] in labs and e[4] == 0]
        evs = [P[a][4][j] for a, j in refs]
        b.append(f'<div class="prob" id="p-{k}"><h2 style="border:0;margin-top:0">{k}. {esc(p[2])}</h2>')
        b.append(f'<p><span class="sw" style="background:{KOLIR.get(th, "#888")}"></span><b>{esc(q["mech"])}</b> · '
                 f'{esc(L.THEMES.get(th, th))} · {esc(dn[p[8]] if len(p) > 8 and 0 <= p[8] < len(dn) else "")} · '
                 f'<a href="https://www.openstreetmap.org/?mlat={p[0]}&mlon={p[1]}#map=18/{p[0]}/{p[1]}" target="_blank" rel="noopener">на мапі OSM ↗</a></p>')
        ad = q.get('adresy') or []
        rec = rec_of.get((q['sim'], (q.get('adresy') or [''])[0])) or {}
        if q.get('status') == 'фіксує поліція':
            b.append('<p><b>Проблема, яку фіксує поліція:</b> більшість подій виявила сама поліція, а не '
                     'повідомили люди; скупчення стійке (той самий поріг, що й для заявних).</p>')
        if rec.get('rozbyvka'):
            b.append('<p>Механізми цього виду тут: ' + esc('; '.join(
                f"{x['mekhanizm']} — {x['podii']}" + (' (фіксує поліція)' if x['status'] == 'фіксує поліція' else '')
                for x in rec['rozbyvka'])) + '.</p>')
        if q.get('riven') == 'лінія':
            b.append(f'<p>Лінія{": " + esc(q["vidrizok"]) if q.get("vidrizok") else ""} — події на {len(ad)} адресах: {esc("; ".join(ad))}.</p>')
        elif q.get('riven') == 'ділянка':
            an_ = rec.get('adresy_n') or [(a, '') for a in ad]
            b.append(f'<p>Ділянка вулиці (точки-проблеми ближче 250 м, разом до 500 м): '
                     + esc('; '.join(f'{a} — {n}' for a, n in an_)) + '.</p>')
        elif len(ad) > 1:
            b.append(f'<p>Одне місце, {len(ad)} написання чи сусідні номери: {esc("; ".join(ad))}.</p>')
        b.append(f'<p>{q["n"]} {pl(q["n"], "подія", "події", "подій")} з підтвердженою адресою за {len(q.get("years", []))} '
                 f'{pl(len(q.get("years", [])), "рік", "роки", "років")} ({", ".join(q.get("years", []))}). Статті: '
                 + esc('; '.join(f'{a} — {n}' for a, n in q.get('arts', []))) + '.</p>')
        # кварталами — за датою події, з точки карти
        kv = collections.Counter()
        y0 = int(D['mon0'][:4])
        for e in evs:
            if e[5] >= 0: kv[(y0 + e[5] // 12, e[5] % 12 // 3 + 1)] += 1
        if kv:
            ks = [(y, qq) for y in range(y0, max(k_[0] for k_ in kv) + 1) for qq in range(1, 5)]
            ks = ks[:len(ks) - next((j for j, kk in enumerate(reversed(ks)) if kv[kk]), 0)]
            b.append('<h3>За кварталами</h3>' + hist([kv[x] for x in ks], [f'{y} К{qq}' for y, qq in ks]))
        h = [0] * 24
        for e in evs:
            if e[3] >= 0: h[e[3]] += 1
        if sum(h) >= 5:
            b.append('<h3>Година доби</h3>' + hist(h, [f'{x}:00' for x in range(24)])
                     + f'<p class="muted">Година відома для {sum(h)} з {len(evs)} подій.</p>')
        # 2–3 описи: клас адреси B, найсвіжіші
        ex = []
        for a, j in sorted(refs, key=lambda r: -(P[r[0]][4][r[1]][5])):
            if P[a][4][j][4] == 0 and a < len(DOCS) and j < len(DOCS[a]) and DOCS[a][j][5]:
                ex.append(DOCS[a][j])
            if len(ex) == 3: break
        if ex:
            b.append('<h3>Як це описано в рішеннях</h3>' + ''.join(
                f'<div class="box"><div class="muted">{esc(x[1])}{" · дата рішення" if len(x) > 6 and x[6] else ""}'
                f'{" · справа " + esc(x[3]) if x[3] else ""}</div>{esc(x[5])}</div>' for x in ex))
        ty = rec.get('typ') or {}
        b.append('<h3>Тип проблеми</h3>')
        ser = ty.get('seredovyshche') or 'невизначено'
        if ty.get('povedinka'):
            b.append(f'<p>За Еком і Кларком: <b>{esc(ty["povedinka"])} × {esc(ser)}</b>'
                     + (' <span class="muted">(середовище — об\'єкт OSM у 50 м від більшості подій)</span>'
                        if ser != 'невизначено' else '')
                     + '.' + (f' Хто керує місцем: {esc(ty["keruye"])}.' if ty.get('keruye') else '') + '</p>')
        else:
            b.append('<div class="empty">Тип не визначено: механізму немає в таблиці NAPRYAM-PROBLEMY, додаток Б.</div>')
        if ser == 'невизначено':
            b.append('<div class="empty">Тип місця невизначено: у 50 м від більшості подій немає об\'єкта з '
                     'переліку, тож посібника й «хто керує місцем» немає.</div>')
        elif ty.get('posibnyk'):
            b.append(f'<p>Посібник POP Center: {esc(ty["posibnyk"])}. Техніки ситуаційного запобігання: '
                     f'{", ".join(map(str, ty.get("tekhniky", [])))} (<a href="metodyka.html#tekhniky">перелік</a>).</p>')
        else:
            b.append('<div class="empty">Посібника POP Center для цієї пари «механізм × середовище» немає — '
                     'приблизним не заповнюємо.</div>')
        g = q.get('golos') or {}
        if g.get('stan'):
            s = GOLOS.get(g['stan'], g['stan'])
            if g['stan'] == 'не вимірюється' and g.get('chomu') and g['chomu'] != 'вид':
                s = ('не вимірюється: ' + ('поруч немає житла' if g['chomu'] == 'житла в 50 м немає' else g['chomu'])
                     + ' — мешканців, які скаржилися б, тут немає')
            if g['stan'] in ('підтверджують', 'мовчать'):
                s += (f': {g.get("skarg", 0)} {pl(g.get("skarg", 0), "скарга", "скарги", "скарг")} того ж виду за рік у 30 м '
                      f'при очікуваних {dec(g.get("ochikuvano", 0))} для такої кількості звернень у цьому районі')
                if g.get('kategorii'): s += '; найчастіше — ' + '; '.join(g['kategorii'])
            b.append(f'<h3>Голос мешканців</h3><p>{esc(s)}.</p>')
        nr = near_objs(D, p)
        if nr:
            b.append('<h3>Що поруч</h3><p class="muted">Кожен тип — у своєму радіусі (як на карті). Які з цих об\'єктів '
                     'пов\'язані з подіями — перевіряє той, хто вийде на місце.</p><p>'
                     + '; '.join(f'{esc(n)} — {d} м' for d, n in nr) + '.</p>')
        an = q.get('analysis')
        b.append('<h3>Схожі умови тут</h3><p>' + (
            f'Вулиця — серед вулиць зі схожими умовами для цього виду.' if an else
            'Вулиця не входить до переліку вулиць зі схожими умовами для цього виду.') + '</p>')
        b.append('<div class="empty">Що перевірити на місці — визначає слухач за SARA; карта дає лише виміряне.</div></div>')
    return b, len(items)


# ============================================================ МЕТОДИКА
TEKHNIKY = [('Більше зусиль', ['Ускладнити ціль', 'Обмежити доступ', 'Контроль виходів', 'Відвести правопорушника', 'Контроль засобів']),
            ('Більший ризик', ['Розширити опіку', 'Допомогти природному нагляду', 'Зменшити анонімність',
                               'Задіяти того, хто керує місцем', 'Посилити формальний нагляд']),
            ('Менша вигода', ['Сховати ціль', 'Прибрати ціль', 'Позначити майно', 'Зруйнувати ринок збуту', 'Позбавити вигоди']),
            ('Менше провокацій', ['Зменшити роздратування і тиск', 'Уникати сварок', 'Знизити емоційне збудження',
                                  'Зняти тиск групи', 'Не давати наслідувати']),
            ('Без виправдань', ['Установити правила', 'Розмістити вказівники', 'Звернутися до сумління',
                                'Полегшити дотримання правил', 'Контроль алкоголю і наркотиків'])]


def metodyka(D):
    rep_ = D.get('PR') or {}
    b = ['<h2 id="dani">Дані</h2><ul>'
         '<li><b>ЄДРСР</b> — рішення судів Києва по суті (вироки й постанови, не ухвали); одна справа — одна подія '
         'на вид. Адреса, дата й година події — з тексту рішення (прохід по текстах).</li>'
         '<li><b>Клас адреси.</b> B — адресу названо в описі самої події; A, C, D — адреса з іншої частини '
         'тексту (місце проживання, суду, лікарні). Проблеми й «Схожі умови» рахуються лише на класі B.</li>'
         '<li><b>Точне місце.</b> Будинок або перехрестя: подія без номера будинку, в описі якої названо '
         'перехрестя двох вулиць, стає в точку їх перетину за OSM і рахується нарівні з будинком. Решта подій '
         'без номера, «20Б → 20» і «між сусідами» на карту не йдуть.</li>'
         '<li><b>OpenStreetMap</b> — вулиці й об\'єкти поруч (лише «що є»: шари «чого немає» в OSM Києва неповні).</li>'
         '<li><b>1551</b> — скарги мешканців Києва з 08.2025, відкриті дані КМДА; без координат і тексту, з адресою.</li>'
         '<li><b>Модельований пішохідний потік</b> і оцінка населення — знаменники для вулиць.</li></ul>']
    b.append('<h2 id="vorota">Ворота проблеми</h2><ol>'
             '<li><b>Р1.</b> Лише події з адресою класу B.</li>'
             '<li><b>Р2.</b> Щонайменше половина подій пари — заявні (про них повідомили люди), а не виявлені самою '
             'поліцією; дрібне хуліганство, спрямоване на поліцейських, — проактивне. Проактивне скупчення, що '
             'проходить Р3 і Р8, — «проблема, яку фіксує поліція»; наркотики й сп\'яніння за кермом — ні: там '
             'скупчення — місця роботи патрулів.</li>'
             '<li><b>Р3.</b> ≥ 12 окремих подій за останні 2 роки (та сама дата на тій самій адресі — одна), у ≥ 5 '
             'різних кварталах з 8, остання — не старша за 12 місяців. Дати події немає — дата рішення мінус 50 днів.</li>'
             '<li><b>Р4.</b> ДТП без потерпілих — окремим класом «дорожні ділянки», не в переліку.</li>'
             '<li><b>Р5.</b> Тип за Еком і Кларком — з таблиці механізмів (NAPRYAM-PROBLEMY, додаток Б). Тип місця, '
             'хто ним керує, посібник POP Center і техніки — лише якщо об\'єкт цього типу за OSM стоїть у 50 м від '
             'більшості подій; інакше «невизначено» і без посібника. На карті їх немає — лише тут.</li>'
             '<li><b>Р6.</b> Порядок — події за останні 4 квартали, далі за весь час. Тяжкість не сортує.</li>'
             '<li><b>Р7.</b> Квот за видами й районами немає.</li>'
             '<li><b>Р8.</b> Місце має бути густішим, ніж дало б випадкове розкидання тих самих подій: 200 разів '
             'події механізму розкладаються заново по місцях, де фіксують події, пропорційно подіям інших '
             'механізмів там; якщо так густо випадало в ≥ 5% розкладів — пара не проходить.</li></ol>'
             '<p>Адреси в 30 м з тим самим механізмом — одне місце; кілька механізмів одного виду в одному місці — '
             'одна картка з розбивкою. Точки-проблеми одного механізму на тій самій вулиці ближче 250 м '
             '(ланцюжком, разом до 500 м) — одна проблема рівня «ділянка». Коли місце не проходить, а події '
             'механізму розкидані по відрізку вулиці між перехрестями (≥ 3 адреси, жодна не тримає більшості), '
             'пробується лінія; вона теж проходить Р8 — перестановками між відрізками тієї ж довжини в тому ж '
             'районі.</p>')
    for riven, f in (rep_.get('voronka') or {}).items():
        if not f: continue
        b.append(f'<h3>Воронка: {esc(riven)}</h3><table>' + ''.join(
            f'<tr><td>{esc(k)}</td><td class="n">{num(v)}</td></tr>' for k, v in f.items()) + '</table>')
    r8 = rep_.get('r8') or {}
    if r8:
        b.append('<h3>Р8: скільки пар пройшло б ворота випадково</h3><table><tr><th>Механізм</th><th class="n">Проблем</th>'
                 '<th class="n">Випадково в середньому</th><th class="n">95% розкладів — не більше</th></tr>' + ''.join(
                     f'<tr><td>{esc(k)}</td><td class="n">{v["realnykh"]}</td><td class="n">{dec(v["vypadkovo_serednie"])}</td>'
                     f'<td class="n">{v["vypadkovo_95"]}</td></tr>'
                     for k, v in sorted(r8.items(), key=lambda x: -x[1]['realnykh']) if v['realnykh'] or v['vypadkovo_serednie'] >= .5)
                 + '</table><p class="muted">Де «випадково» близько до числа проблем, частина переліку могла скластися '
                 'й без справжнього скупчення; кожна пара окремо все одно перевірена своїм розкладом.</p>')
    b.append('<h2 id="golos">Голос мешканців (1551)</h2><p>Для кожної проблеми — скарги того ж виду за 12 місяців '
             'у 30 м проти очікуваного: частка цього виду серед усіх звернень району × усі звернення цих адрес. '
             'Тест Пуассона, p &lt; 0,05 — «підтверджують», інакше «мовчать». Про наркотики, насильство й крадіжки '
             '1551 мовчить — «не вимірюється»; так само там, де мешканців немає: вокзал, ТЦ, площа, парк або жодного '
             'житлового будинку в 50 м. 1551 не ворота: він доповнює суд, а не замінює.</p>')
    if rep_.get('golos'):
        b.append('<table>' + ''.join(f'<tr><td>{esc(k)}</td><td class="n">{v}</td></tr>' for k, v in rep_['golos'].items()) + '</table>')
    b.append('<h2 id="skhozhi">Схожі умови</h2><p>Модель «разом» за Risk Terrain Modeling (Caplan, Kennedy): '
             'історія подій (експозиція) і середовище (вразливість). Історія — <code>log(1 + подій попередніх '
             '12 місяців)</code>: навчання «історія 2024 → події 2025», перевірка «історія 2025 → події 2026». '
             'Кожен тип об\'єкта виміряно двома способами — «є в межах r» і «скільки в межах r» — на 50–500 м, '
             'плюс пішохідні потоки, населення й будова вулиці. Відбір — стійкості: 100 разів elastic net на '
             'випадковій половині відрізків (λ — перехресною перевіркою блоками за районами); чинник лишається, '
             'якщо його обрано в ≥ 70% прогонів; остаточна — негативна біноміальна з довжиною як експозицією. '
             'Одиниця — відрізок вулиці між перехрестями; подія прив\'язується до відрізка своєї вулиці. Ранг — '
             'за оцінкою на метр; PAI — на частку довжини вулиць; вид чи механізм ховається, якщо PAI &lt; 3.</p>'
             '<p><b>Як це на карті.</b> Картка вулиці каже, звідки ризик: «тут уже були події» і/або «умови як '
             'біля подій». У «Що поруч» кожен тип об\'єкта показано у своєму радіусі — тому, на якому він '
             'пов\'язаний з подіями (таблиця нижче); найбільше коло — 500 м.</p>')
    s1 = (rep_ or {}).get('skhozhi_1551') or {}
    if s1.get('vydy'):
        b.append('<h3 id="skhozhi-1551">Перевірка скаргами 1551</h3><p>1551 — не чинник моделі, а незалежна '
                 f'перевірка: скарги того ж виду за 12 місяців ({esc(s1["vid"])} — {esc(s1["do"])}) у '
                 f'{s1["radius_m"]} м від лінії вулиці шару проти {s1["n_vypadk"]} наборів випадкових вулиць — '
                 'та сама кількість, ті самі райони. Окремо — на кілометр: вулиця шару буває довшою, а довша '
                 'вулиця збирає більше скарг просто довжиною.</p><div class="tw"><table><tr><th>Вид</th>'
                 '<th class="n">Скарг на вулицях шару</th><th class="n">Випадково</th><th class="n">p</th>'
                 '<th class="n">На км: шар / випадково</th><th class="n">p на км</th><th class="n">Тихих вулиць зі скаргами</th></tr>'
                 + ''.join(f'<tr><td>{esc(v["vyd"])}</td><td class="n">{v["skarg"]}</td><td class="n">{dec(v["vypadkovo"])}</td>'
                           f'<td class="n">{dec(v["p"], 3)}</td><td class="n">{dec(v["na_km"] or 0, 2)} / {dec(v["vypadkovo_na_km"], 2)}</td>'
                           f'<td class="n">{dec(v["p_na_km"] or 1, 3)}</td><td class="n">{len(v["tykhi_zi_skargamy"])} з {v["tykhykh"]}</td></tr>'
                           for v in s1['vydy'].values())
                 + '</table></div><p class="muted">p — частка випадкових наборів, де скарг стільки ж або більше. '
                 'Про наркотики, насильство й майно 1551 мовчить.</p>')
    rad = D.get('RAD') or {}
    if rad.get('shcho_poruch'):
        bm = rad.get('blocks_m') or 1
        b.append(f'<h3>Радіуси «Що поруч»</h3><p class="muted">Квартал (середня довжина відрізка вулиці) — {bm} м. '
                 '0 — тип не пов\'язаний з подіями; на карті його показано в 50 м.</p><table><tr><th>Тип</th>'
                 '<th class="n">Радіус</th><th class="n">Кварталів</th></tr>' + ''.join(
                     f'<tr><td>{esc(nazva_chynnyka(k))}</td><td class="n">{v or 0} м</td><td class="n">{dec(v / bm) if v else "—"}</td></tr>'
                     for k, v in rad['shcho_poruch'].items()) + '</table>')
    b.append('<h2 id="tekhniky">25 технік ситуаційного запобігання</h2><p class="muted">Cornish, Clarke (2003). '
             'Номери — ті, що стоять у картці проблеми.</p><div class="tw"><table><tr>'
             + ''.join(f'<th>{esc(g)}</th>' for g, _ in TEKHNIKY) + '</tr>' + ''.join(
                 '<tr>' + ''.join(f'<td>{5 * gi + r + 1}. {esc(TEKHNIKY[gi][1][r])}</td>' for gi in range(5)) + '</tr>'
                 for r in range(5)) + '</table></div>')
    b.append('<h2 id="mezha">Межа</h2><p>Модель і звіти міряють, що поруч і як часто, а не через що сталася подія. '
             'Гіпотезу, чому саме тут, висуває людина на місці. Адреса — місце, де подію оформлено.</p>')
    return b


# ============================================================ ЗБІРКА
def build(outdir):
    D = dani()
    made = []
    b, n = stan_mista(D)
    import numpy as np
    rng = np.random.default_rng(25)
    for f in (zaklady, near_repeat):
        try: b += f(D, rng)
        except Exception as e: print(f'   {f.__name__}: {e}')
    b += khronichni(D) + mistse_hodyna(D)
    # одне джерело чисел: сума подій звіту — сума на карті (PLAN-ZVITY, п. 2)
    na_karti = sum(len(p[4]) for p in D['doma'])
    if n != na_karti:
        raise RuntimeError(f'«Стан міста»: {n} подій проти {na_karti} на карті')
    open(os.path.join(outdir, 'stan-mista.html'), 'w', encoding='utf-8').write(
        page('stan-mista.html', 'Стан міста', 'Коротко: скільки, де, коли — за подіями карти.', ''.join(b)))
    made.append('stan-mista.html')
    b, script = skhozhi_umovy(D)
    open(os.path.join(outdir, 'skhozhi-umovy.html'), 'w', encoding='utf-8').write(
        page('skhozhi-umovy.html', 'Схожі умови', 'Де середовище схоже на місця з подіями — за видами, '
             'з перевіркою на роках і частині міста, яких модель не бачила.', ''.join(b), script))
    made.append('skhozhi-umovy.html')
    b, npr = problemy(D)
    open(os.path.join(outdir, 'problemy.html'), 'w', encoding='utf-8').write(
        page('problemy.html', 'Проблеми', f'{npr} {pl(npr, "проблема", "проблеми", "проблем")} — з чого почати на місці. '
             'Сторінка на кожну; друкується на A4.', ''.join(b)))
    made.append('problemy.html')
    open(os.path.join(outdir, 'metodyka.html'), 'w', encoding='utf-8').write(
        page('metodyka.html', 'Методика', 'Спільний додаток до трьох звітів: дані, ворота проблем, голос '
             'мешканців, «Схожі умови».', ''.join(metodyka(D))))
    made.append('metodyka.html')
    return made
