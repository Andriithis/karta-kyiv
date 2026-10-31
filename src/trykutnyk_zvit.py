# -*- coding: utf-8 -*-
"""«Дослідження» за трикутником — ціль, порушник, район (ZAVDANNYA-40,
етап 5; RISHENNYA 36.43).

Андрій 29.10: «дивишся табличку — цифри, пояснення немає». Тому кожна
таблиця: висновок заголовком (рахується з даних, не пишеться наперед), під
нею «Що це означає» і «Як використати», оцінка — сильно / слабко /
несподівано / не відрізняється. Усі числа — мінімум: те, що суд написав у
фабулі (linzy.py, tsil.py). Порівнюємо частки, а «помітно більше» — лише
коли відхилення поза випадковим (Пуассон з поправкою Бенджаміні — Гохберга
на кількість районів); причин не пишемо (CLAUDE.md).
"""
import collections, math
from html import escape as esc

POLE = {'berut': 'беруть', 'u_koho': 'у кого', 'zitknennia': 'зіткнення з', 'na_koho': 'на кого',
        'rechovyna': 'речовина', 'sposib': 'як', 'shcho_prodaiut': 'продають'}


def pois_sf(k, lam):
    """P(X ≥ k) для Пуассона — без scipy, як у problems.py"""
    if k <= 0: return 1.0
    s, t = 0.0, math.exp(-lam)
    for i in range(k):
        s += t; t *= lam / (i + 1)
    return max(0.0, 1 - s)


def bh(ps, q=.05):
    """Бенджаміні — Гохберг: які з p лишаються значущими"""
    o = sorted(range(len(ps)), key=lambda i: ps[i]); m = len(ps); ok = set()
    for r, i in enumerate(o, 1):
        if ps[i] <= q * r / m: ok = set(o[:r])
    return ok


def otsinka(s):
    kl = {'сильно': '#2e7d32', 'слабко': '#9e9e9e', 'несподівано': '#ef6c00', 'не відрізняється': '#607d8b'}[s]
    return f'<span style="display:inline-block;font-size:12px;border-radius:9px;padding:0 8px;background:{kl};color:#fff">{s}</span>'


def blok(vysnovok, tabl, oznachaie, vykorystaty, ots):
    return (f'<div class="card" style="margin:14px 0"><h3 style="margin:0 0 6px">{esc(vysnovok)} {otsinka(ots)}</h3>{tabl}'
            f'<p><b>Що це означає.</b> {esc(oznachaie)}</p><p><b>Як використати.</b> {esc(vykorystaty)}</p></div>')


def storinka(D, num, pct, theme_name):
    P, LZ, V, th_of = D['P'], D.get('LZ') or [], D.get('TSIL_V') or [], D['th_of']
    dn = D.get('dnames') or []
    po_vydu = collections.defaultdict(list)          # вид -> [(точка, подія, [ознаки, стать, ціль])]
    for i, p in enumerate(P):
        if not p[3]: continue
        lz = LZ[i] if i < len(LZ) else []
        for k, e in enumerate(p[4]):
            po_vydu[th_of[e[1]]].append((p, e, lz[k] if k < len(lz) else None))
    b = ['<p>Що повторюється в місці, у правопорушнику й у цілі — за всіма видами. Числа — мінімум: '
         'те, що суд написав у фабулі.</p>']
    # 5.1 Ціль — топи по видах
    b.append('<h2 id="tsil">Ціль</h2>')
    for th, evs in sorted(po_vydu.items(), key=lambda x: -len(x[1])):
        c = collections.Counter(V[x] for _p, _e, l in evs if l for x in (l[2] or []))
        if not c: continue
        z_tsillu = sum(1 for _p, _e, l in evs if l and l[2])
        pol = collections.defaultdict(list)
        for kod, n in c.most_common():
            k, v = kod.split('=', 1); pol[k].append((v, n))
        ryad = ''.join(f'<tr><td>{esc(POLE.get(k, k))}</td><td>' + ' · '.join(f'{esc(v)} <b>{num(n)}</b> ({pct(n / z_tsillu)})'
                                                                            for v, n in xs[:5]) + '</td></tr>'
                       for k, xs in pol.items())
        k0, xs0 = next(iter(pol.items()))
        v0, n0 = xs0[0]; sh = n0 / z_tsillu
        b.append(blok(f'{theme_name(th)}: {POLE.get(k0, k0)} — найчастіше {v0} ({pct(sh)} подій з ціллю)',
                      f'<div class="tw"><table>{ryad}</table></div><p class="muted">Ціль названо в {num(z_tsillu)} з {num(len(evs))} подій виду.</p>',
                      'Ціль повторюється так само, як місце: одна й та сама річ чи людина в багатьох рішеннях.',
                      'Захищайте саме цю ціль — сховати, прибрати, попередити (див. «Що робити», розділ «Ціль»).',
                      'сильно' if sh >= .4 and z_tsillu >= 200 else 'слабко'))
    # 5.2 Порушник — ознаки по видах
    import linzy as LZM
    b.append('<h2 id="porushnyk">Порушник</h2>')
    ozn = [(bt, nm) for bt, _k, nm, _g in LZM.OZNAKY]
    rows, naiv = [], (None, 0, 0)
    for th, evs in sorted(po_vydu.items(), key=lambda x: -len(x[1])):
        n = len(evs); cnt = {bt: sum(1 for _p, _e, l in evs if l and (l[0] or 0) & bt) for bt, _ in ozn}
        rows.append(f'<tr><td>{esc(theme_name(th))}</td><td class="n">{num(n)}</td>' +
                    ''.join(f'<td class="n">{pct(cnt[bt] / n, 1) if n else "—"}</td>' for bt, _ in ozn) + '</tr>')
        for bt, nm in ozn:
            if n >= 200 and cnt[bt] / n > naiv[1]: naiv = (f'{theme_name(th)} — {nm.lower()}', cnt[bt] / n, n)
    b.append(blok(f'Найпомітніша ознака: {naiv[0]} ({pct(naiv[1], 1)})' if naiv[0] else 'Ознаки правопорушника за видами',
                  '<div class="tw"><table><tr><th>Вид</th><th>Подій</th>' + ''.join(f'<th>{esc(nm)}</th>' for _b, nm in ozn) +
                  '</tr>' + ''.join(rows) + '</table></div>',
                  'Частка подій, де суд прямо написав ознаку. Суди пишуть про судимість по-різному — частки між районами не порівнювати.',
                  'Де частка повторних велика, працює не лише місце, а й робота з особою (див. «Що робити», розділ «Порушник»).',
                  'слабко'))
    # 5.2 за що діти: вид серед подій з неповнолітнім правопорушником проти всіх
    ditu_v = collections.Counter(th for th, evs in po_vydu.items() for _p, _e, l in evs if l and (l[0] or 0) & 32)
    vsi_v = {th: len(evs) for th, evs in po_vydu.items()}
    Nd, Nv = sum(ditu_v.values()), sum(vsi_v.values())
    if Nd >= 50:
        rows = ''.join(f'<tr><td>{esc(theme_name(th))}</td><td class="n">{num(n)}</td><td class="n">{pct(n / Nd)}</td>'
                       f'<td class="n">{pct(vsi_v[th] / Nv)}</td></tr>' for th, n in ditu_v.most_common())
        top = ditu_v.most_common(1)[0]
        b.append('<h2 id="dity">За що діти</h2>')
        b.append(blok(f'Діти-правопорушники найчастіше — {theme_name(top[0]).lower()} ({pct(top[1] / Nd)} їхніх подій)',
                      f'<div class="tw"><table><tr><th>Вид</th><th>Подій з неповнолітнім</th><th>Частка серед дітей</th><th>Частка серед усіх</th></tr>{rows}</table></div>',
                      'Порівнюйте два останні стовпці: вид, якого серед дітей помітно більше, ніж серед усіх, — «дитячий».',
                      'Ювенальна превенція й школи — з тих видів, де частка дітей вища за загальну.', 'слабко'))
    # 5.4 ціль × час доби — телефони, гроші, велосипеди: коли беруть
    chas = lambda h: 'ніч (22–6)' if h < 6 or h >= 22 else 'ранок (6–12)' if h < 12 else 'день (12–18)' if h < 18 else 'вечір (18–22)'
    tsh = collections.defaultdict(collections.Counter)
    for _p, e, l in po_vydu.get('МАЙ', []):
        if not l or e[3] is None or e[3] < 0: continue
        for x in l[2] or []:
            k, v = V[x].split('=', 1)
            if k == 'berut': tsh[v][chas(e[3])] += 1
    tsh = {v: c for v, c in tsh.items() if sum(c.values()) >= 40}
    if tsh:
        sl = ['ранок (6–12)', 'день (12–18)', 'вечір (18–22)', 'ніч (22–6)']
        rows = ''.join(f'<tr><td>{esc(v)}</td>' + ''.join(f'<td class="n">{pct(c[s] / sum(c.values()))}</td>' for s in sl) +
                       f'<td class="n">{num(sum(c.values()))}</td></tr>' for v, c in sorted(tsh.items(), key=lambda x: -sum(x[1].values())))
        nich = max(tsh.items(), key=lambda x: x[1]['ніч (22–6)'] / sum(x[1].values()))
        b.append('<h2 id="tsil-chas">Ціль × час доби</h2>')
        b.append(blok(f'Найбільше вночі беруть {nich[0]} ({pct(nich[1]["ніч (22–6)"] / sum(nich[1].values()))})',
                      f'<div class="tw"><table><tr><th>Беруть</th>' + ''.join(f'<th>{esc(s)}</th>' for s in sl) + f'<th>Подій з часом</th></tr>{rows}</table></div>',
                      'Частки — серед подій, де суд назвав і ціль, і годину.',
                      'Попередження й присутність — у ті години, коли цю ціль беруть найчастіше.', 'слабко'))
    # 5.5 Київ і світ: концентрація на адресах (Weisburd 2015 — на вуличних відрізках)
    adr = sorted((len(p[4]) for p in P if p[3] and p[4]), reverse=True)
    if adr:
        n_ = sum(adr); m_ = len(adr)
        def chastka_adres(dolia):
            s = k = 0
            while k < m_ and s < dolia * n_: s += adr[k]; k += 1
            return k / m_
        p50, p25 = chastka_adres(.5), chastka_adres(.25)
        b.append('<h2 id="svit">Київ і світ</h2>')
        b.append(blok(f'Половина подій — на {pct(p50, 1)} адрес, чверть — на {pct(p25, 1)}',
                      f'<div class="tw"><table><tr><th></th><th>Київ (адреси)</th><th>Світ (вуличні відрізки, Weisburd 2015)</th></tr>'
                      f'<tr><td>50% подій</td><td class="n">{pct(p50, 1)}</td><td class="n">~2–6%</td></tr>'
                      f'<tr><td>25% подій</td><td class="n">{pct(p25, 1)}</td><td class="n">~0,4–1,6%</td></tr></table></div>'
                      '<p class="muted">Київ рахуємо за адресами з подіями, світ — за всіма відрізками вулиць; у Києві знаменник '
                      'менший, тож частки не тотожні. Джерело: <a href="https://doi.org/10.1111/1745-9125.12070" target="_blank" '
                      'rel="noopener">Weisburd, 2015, «The law of crime concentration and the criminology of place»</a>.</p>',
                      'Як і в інших містах, події стягуються в малу частку місць — працювати є де зосередитись.',
                      'Почніть з адрес верхньої частки: там більшість подій, і зміна місця дасть найбільше.',
                      'сильно' if p50 < .1 else 'слабко'))
    # 5.4 район × неповнолітні
    vsi, ditu = collections.Counter(), collections.Counter()
    for evs in po_vydu.values():
        for p, _e, l in evs:
            di = p[8] if len(p) > 8 else -1
            if di < 0: continue
            vsi[di] += 1
            if l and (l[0] or 0) & 32: ditu[di] += 1
    N, K = sum(vsi.values()), sum(ditu.values())
    if N and K:
        ds = sorted(vsi); ps = [pois_sf(ditu[d], K / N * vsi[d]) for d in ds]; zn = bh(ps)
        rows = ''.join(f'<tr><td>{esc(dn[d] if d < len(dn) else str(d))}</td><td class="n">{num(vsi[d])}</td><td class="n">{num(ditu[d])}</td>'
                       f'<td class="n">{pct(ditu[d] / vsi[d], 2)}</td><td>{"помітно більше" if i in zn else "не відрізняється"}</td></tr>'
                       for i, d in enumerate(ds))
        bilshe = [dn[ds[i]] for i in zn if ds[i] < len(dn)]
        b.append('<h2 id="rajony">Район × неповнолітні</h2>')
        b.append(blok(('Неповнолітніх правопорушників помітно більше: ' + ', '.join(bilshe)) if bilshe
                      else 'Частка неповнолітніх правопорушників у районах не відрізняється від міської',
                      f'<div class="tw"><table><tr><th>Район</th><th>Подій</th><th>З неповнолітнім</th><th>Частка</th><th>Проти міста ({pct(K / N, 2)})</th></tr>{rows}</table></div>',
                      '«Помітно більше» — лише коли так багато випадково буває рідше ніж в одному з двадцяти разів, '
                      'з поправкою на те, що районів десять.',
                      'Ювенальна превенція району бачить, де концентрація саме дітей-правопорушників, і з якими видами.',
                      'несподівано' if bilshe else 'не відрізняється'))
    return ''.join(b)
