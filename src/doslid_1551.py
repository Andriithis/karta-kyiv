# -*- coding: utf-8 -*-
"""Закономірності 1551 -> судові події (ZAVDANNYA-30, 3.7; RISHENNYA 33.2.5).

Чи передбачають скарги мешканців подій, установлених судом, — не лише
«скарга того ж виду», а й перехресні (приклад Андрія: шум -> насильство).
Спершу дослідження й звіт — Андрій дивиться, — і лише потім, окремим
рішенням, пройдені групи йдуть у модель ризику. Цей скрипт у модель нічого
не вмикає.

Як рахуємо, щоб не знайти випадкове:
  * лише вперед у часі: скарги 08.2025–01.2026 -> події з датою події
    02.2026 і пізніше, на тому самому відрізку між перехрестями;
  * з поправкою на те, що вже є в моделі: історія подій (12 місяців до
    02.2026) і середовище — ті самі кандидати, що в кроці 4 (oznaky);
  * групи 1551 — кандидати поряд із чинниками середовища в тому самому
    відборі стійкості (100 прогонів, поріг 70%);
  * «пройшла» — обрана в ≥70% прогонів І покращила PAI на довжину на
    відкладеному періоді (події 06.2026 і пізніше), якого відбір не бачив;
  * де подій замало, зв'язок не перевіряється — так і пишемо.

Прив'язка скарги — як голос мешканців (problems.py): адреса за реєстром КМДА,
відрізок у 30 м від лінії.

Запуск: py -3 src/doslid_1551.py  (пише ZVIT-1551-ZAKONOMIRNOSTI.md)
"""
import os, sys, glob, gzip, csv, json, time, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import labels as L
import mech as M
import rtm
import step4_engine as E
import problems as PR
import vidrizky as VR

ROOT = E.ROOT
DATA = E.DATA
TXT = os.path.join(ROOT, 'ZVIT-1551-ZAKONOMIRNOSTI.md')

VIKNO = ['2025-08', '2025-09', '2025-10', '2025-11', '2025-12', '2026-01']
ISTORIIA = [f'2025-{m:02d}' for m in range(2, 13)] + ['2026-01']
TSIL_A = ['2026-02', '2026-03', '2026-04', '2026-05']       # відбір і коефіцієнти
# відкладений період — від 06.2026 до кінця даних
N_GRUP = 30
MIN_GRUPA = 200
R_1551 = 30
MIN_PODII = 150      # подій у періоді відбору — менше: зв'язок не перевіряємо


def main():
    import numpy as np
    t0 = time.time()
    log = lambda *a: print(*a, flush=True)
    raw = json.load(open(E.RAW, encoding='utf-8'))
    F = E.oznaky(raw, log)
    SEG, sids, slen, X, ctyp, cname, expo = (F[k] for k in ('SEG', 'sids', 'slen', 'X', 'ctyp', 'cname', 'expo'))
    mid = F['mid']
    n = len(sids); idx = {s: i for i, s in enumerate(sids)}
    PV = VR.Pryviazka(SEG)

    # ---- скарги 1551 на відрізках ----
    kmda, skey, nh = PR.geokoder()
    def geo(st, h):
        if not st or not h: return None
        main_ = st.split('(')[0]
        return kmda.get((skey(main_), nh(h)))
    C = collections.defaultdict(lambda: np.zeros(n))
    nz = collections.Counter()
    for f in sorted(glob.glob(os.path.join(DATA, '1551', 'lichylnyky-*.tsv.gz'))):
        mon = os.path.basename(f)[11:18]
        if mon not in VIKNO: continue
        with gzip.open(f, 'rt', encoding='utf-8', newline='') as fh:
            for r in csv.DictReader(fh, delimiter='\t'):
                k = int(r.get('n') or 0)
                p = geo(r.get('vulytsya'), r.get('budynok'))
                if p is None: nz['без точки'] += k; continue
                b = PV.blyzki(p[0], p[1], R_1551)
                if not b: nz[f'далі {R_1551} м від вулиць'] += k; continue
                C[r['kind']][idx[min(b, key=b.get)]] += k
                nz['на відрізках'] += k
    tot = {k: v.sum() for k, v in C.items()}
    top = [k for k, v in sorted(tot.items(), key=lambda x: -x[1]) if v >= MIN_GRUPA][:N_GRUP - 1]
    grupy = {k: C[k] for k in top}
    inshi = sum((C[k] for k in C if k not in top), np.zeros(n))
    if inshi.sum() >= MIN_GRUPA: grupy['інші дрібні категорії'] = inshi
    gn = list(grupy)
    G = np.column_stack([np.log1p(grupy[g]) for g in gn])
    G = (G - G.mean(0)) / np.where(G.std(0) > 0, G.std(0), 1)
    log(f'1551 {VIKNO[0]} — {VIKNO[-1]}: ' + ', '.join(f'{k} {v:,}' for k, v in nz.items())
        + f'; груп {len(gn)}')

    # ---- судові події на відрізках ----
    ev, _drop = E.podii(log)
    Y = collections.defaultdict(lambda: np.zeros(n))
    cache = {}
    for e in ev:
        ck = (round(e['la'], 5), round(e['lo'], 5), e['street'])
        if ck not in cache: cache[ck] = PV.znaity(e['la'], e['lo'], E.SNAP_M, VR.vulytsia(e['street']))[0]
        s = cache[ck]
        if s is None: continue
        for k in [e['th']] + ([e['mekh']] if e['mekh'] else []):
            Y[(k, e['m'])][idx[s]] += 1
    last = max(e['m'] for e in ev)
    ms = sorted({m for (_k, m) in Y})
    TSIL_B = [m for m in ms if '2026-06' <= m <= last]
    cnt = lambda k, mm: sum((Y.get((k, m), np.zeros(n)) for m in mm), np.zeros(n))

    import map_problems as MP
    B = json.load(open(os.path.join(DATA, 'borders.json'), encoding='utf-8'))
    dn = sorted(B); fold = np.zeros(n, dtype=int)
    for i in range(n):
        for di, d in enumerate(dn):
            if MP.in_ring(mid[i][0], mid[i][1], B[d]): fold[i] = di % 5 + 1; break

    KEYS = [(t, 'вид') for t in L.ORDER if t != 'ДОМ'] + [(m, 'механізм') for m in E.MEKH]
    if os.environ.get('B1_VYDY'):
        KEYS = [k for k in KEYS if k[0] in os.environ['B1_VYDY'].split(',')]
    rez = {}
    for key, vyd in KEYS:
        nm = L.THEMES.get(key, key) if vyd == 'вид' else M.simname(key)
        yA, yB, yh = cnt(key, TSIL_A), cnt(key, TSIL_B), cnt(key, ISTORIIA)
        log(f'\n=== {nm}: відбір {int(yA.sum())}, відкладено {int(yB.sum())} ===')
        if yA.sum() < MIN_PODII or yB.sum() < 30:
            rez[key] = dict(nazva=nm, vyd=vyd, zamalo=True, A=int(yA.sum()), B=int(yB.sum()))
            continue
        H = np.log1p(yh); H = (H - H.mean()) / (H.std() or 1)
        # базова модель: історія + середовище
        s0 = rtm.stijkist(X, yA, expo, ctyp, H=H, folds=fold, log=log)
        f0, _ = rtm.nb_fit(np.column_stack([H, X[:, s0['cols']]]), yA, expo)
        p0 = rtm.nb_predict(f0, np.column_stack([H, X[:, s0['cols']]]), expo)
        pai0, _h = rtm.pai_dovzhyna(p0 / slen, yB, slen)
        # групи 1551 — кандидати поряд із середовищем
        XG = np.column_stack([X, G])
        s1 = rtm.stijkist(XG, yA, expo, list(ctyp) + [None] * len(gn), H=H, folds=fold, log=log)
        k0 = X.shape[1]
        gsel = [j - k0 for j in s1['cols'] if j >= k0]
        cols1 = [j for j in s1['cols'] if j < k0]
        pai1 = pai0
        if gsel:
            A1 = np.column_stack([H, X[:, cols1], G[:, gsel]])
            f1, _ = rtm.nb_fit(A1, yA, expo)
            p1 = rtm.nb_predict(f1, A1, expo)
            pai1, _h = rtm.pai_dovzhyna(p1 / slen, yB, slen)
        rows = []
        for g, name in enumerate(gn):
            # кратність кожної групи — окремо, поверх історії й стійкого середовища
            A = np.column_stack([H, X[:, s0['cols']], G[:, g]])
            f, _ = rtm.nb_fit(A, yA, expo)
            b = float(f.params[-1]); ci = f.conf_int()[-1]
            fr = s1['chastka'].get(k0 + g, 0.0)
            rows.append(dict(grupa=name, RR=E.sexp(b), vid=E.sexp(ci[0]), do=E.sexp(ci[1]), chastka=round(fr, 2),
                             proishla=bool(g in gsel and pai1 > pai0)))
        rez[key] = dict(nazva=nm, vyd=vyd, A=int(yA.sum()), B=int(yB.sum()), PAI_bez=round(pai0, 2),
                        PAI_z=round(pai1, 2), obrano=[gn[g] for g in gsel], rows=rows)
        log(f'   PAI на довжину, відкладений період: без 1551 {pai0:.2f}, з обраними групами {pai1:.2f}; '
            f'обрано: {", ".join(gn[g] for g in gsel) or "жодної"}')
    zvit(rez, gn, nz, TSIL_B, grupy)
    log(f'\n=== ГОТОВО за {(time.time() - t0) / 60:.0f} хв -> ZVIT-1551-ZAKONOMIRNOSTI.md')


def zvit(rez, gn, nz, TSIL_B, grupy):
    w = []
    w.append('# 1551 → судові події: закономірності\n')
    w.append(f'Складено {time.strftime("%d.%m.%Y")} (`src/doslid_1551.py`). Завдання 30, п. 3.7; RISHENNYA 33.2.5. '
             '**Це дослідження, у модель ризику нічого не ввімкнено** — спершу звіт, потім рішення Андрія.\n')
    if len(rez) < len(L.ORDER) - 1 + len(E.MEKH) or rtm.N_STAB < 100:
        w.append(f'> **Попередній звіт — перевірка коду**: {len(rez)} вид(и), {rtm.N_STAB} прогонів стійкості. '
                 'Повний — з перенавчанням моделі в Actions (галочка «Перенавчити модель ризику»).\n')
    w.append('## Як рахувалося\n')
    w.append(f'- Скарги 1551 за {VIKNO[0]} — {VIKNO[-1]} (лічильники «адреса × категорія × місяць»), адреса — за '
             f'реєстром КМДА, відрізок між перехрестями в {R_1551} м від лінії: '
             + ', '.join(f'{k} {int(v):,}'.replace(',', ' ') for k, v in nz.items()) + '.')
    w.append(f'- Групи: {len(gn)} — найбільші категорії окремо (кожна ≥{MIN_GRUPA} скарг у вікні), решта разом. '
             'Змінна — `log(1 + скарг за 6 місяців)` на відрізку, стандартизована.')
    w.append(f'- Ціль — судові події (клас B, точне місце) з датою події {TSIL_A[0]} — {TSIL_A[-1]} для відбору й '
             f'коефіцієнтів і {TSIL_B[0] if TSIL_B else "—"} — {TSIL_B[-1] if TSIL_B else "—"} — відкладений період.')
    w.append('- У моделі вже є історія подій (12 місяців до 02.2026) і середовище — ті самі кандидати, що в кроці 4; '
             'тобто міряється, що 1551 **додає** до них.')
    na = nz.get('на відрізках', 0) / max(sum(nz.values()), 1)
    w.append(f'- **Покриття:** у {R_1551} м від лінії вулиці — лише {100 * na:.0f}% скарг з адресою: житлові будинки '
             'здебільшого стоять глибше від осі вулиці, ніж 30 м. Правило «30 м від лінії» — як у голосу мешканців; '
             'чи ширшати його — питання до Андрія.')
    w.append(f'- Відбір — стійкості ({rtm.N_STAB} прогонів elastic net на половині відрізків, λ блоками за районами), групи 1551 — '
             'кандидати поряд із середовищем. **Пройшла** — обрана в ≥70% прогонів **і** модель з обраними групами '
             'дала вищий PAI на довжину на відкладеному періоді.')
    w.append('- Кратність (RR) — у скільки разів більше подій на одне стандартне відхилення скарг, окремо для кожної '
             'групи поверх історії й стійкого середовища; у дужках 95% інтервал.\n')
    w.append('## Підсумок\n')
    w.append('| Вид / механізм | Подій: відбір / відкладено | PAI без 1551 | PAI з обраними | Обрані групи (≥70%) | Пройшли |')
    w.append('|---|---|---|---|---|---|')
    for k, r in rez.items():
        if r.get('zamalo'):
            w.append(f"| {r['nazva']} | {r['A']} / {r['B']} | — | — | подій замало для перевірки | — |"); continue
        pr = [x['grupa'] for x in r['rows'] if x['proishla']]
        w.append(f"| {r['nazva']} | {r['A']} / {r['B']} | {r['PAI_bez']} | {r['PAI_z']} | "
                 f"{', '.join(r['obrano']) or '—'} | {', '.join(pr) or '—'} |")
    zam = [r['nazva'] for r in rez.values() if r.get('zamalo')]
    if zam:
        w.append(f"\n**Подій замало для перевірки:** {', '.join(zam)} — менше {MIN_PODII} подій у періоді відбору "
                 "або 30 у відкладеному. Зв'язок зі скаргами тут не перевіряється і не вгадується.")
    w.append('\n## Група скарг → вид подій\n')
    w.append('Лише пари, де 95% інтервал не перетинає 1 або групу обрано в ≥50% прогонів; повні числа — у '
             'виводі скрипта.\n')
    w.append('| Група скарг | Вид / механізм | RR | 95% | Частка прогонів | Пройшла |')
    w.append('|---|---|---|---|---|---|')
    for k, r in rez.items():
        for x in r.get('rows', []):
            if x['chastka'] >= 0.5 or (x['vid'] or 0) > 1 or (x['do'] or 9) < 1:
                w.append(f"| {x['grupa']} | {r['nazva']} | {x['RR']} | {x['vid']}–{x['do']} | "
                         f"{round(100 * x['chastka'])}% | {'так' if x['proishla'] else 'ні'} |")
    w.append('\n## Що далі\n')
    w.append('Групи з позначкою «так» — кандидати в модель ризику «разом». Вмикати їх — окремим рішенням Андрія '
             'після перегляду цього звіту (ZAVDANNYA-30, 3.7). Проблема лише з 1551 не малюється (RISHENNYA 33.2.5).')
    open(TXT, 'w', encoding='utf-8', newline='\n').write('\n'.join(w) + '\n')


if __name__ == '__main__':
    main()
