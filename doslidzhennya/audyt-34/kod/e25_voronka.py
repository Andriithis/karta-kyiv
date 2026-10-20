"""Е25, крок 2 (ZAVDANNYA-38): воронка втрат для всіх видів подій — від дампу
ЄДРСР до карти, проблем і ризику.

Рахує незалежно від першого проходу центрального чату (E25, таблиця): інший
код, інше джерело фабули (прохід по текстах, data/teksty, а не старий витяг
fabuly.csv.gz). Код карти не чіпаємо — лише читаємо його відбір.

Кроки:
  1 дамп       — рішення з kyiv_*.csv (дата рішення 2024–2026)
  2 форма      — вирок чи постанова (formy.csv.gz; без форми — маркери, як у podii)
  2а подія     — представник справи: одна подія на (справа, вид), як у карті
  3 текст      — представник пройшов прохід по текстах (data/teksty)
  4 фабула     — у проході є опис події
  5 місце      — у тексті названо місце (будь-якого рівня)
  6 адреса     — розібрано будинок чи перехрестя
  7 точка      — є координата точного місця (events.db/geo)
  8 набір      — у наборі 36.14 (kod/nabir_36_14.csv.gz)
  9 карта      — серед подій карти (step3_map.vybir + відсіви zbirka)
 10 проблеми   — у точці чи лінії проблеми
 11 ризик      — у навчальних подіях моделі (step4_engine.podii)

Кроки 7, 9–11 правдиві лише на свіжій базі: їх дає workflow «Е25 — воронка»
(e25_mapa.py -> kod/e25_vyhid/mapa.tsv.gz). Дамп 2024–2026 є лише локально,
тож сама воронка рахується тут. Без mapa.tsv.gz точка береться з локальної
events.db (відстає — лише для попереднього погляду), а 9–11 не рахуються.

Вихід: kod/e25_vyhid/voronka.md (таблиці), prychyny.tsv (кожна втрата),
pryklady.txt (по 20 прикладів на причину — для читання очима).
"""
import os, re, csv, gzip, glob, sqlite3, json, random, collections, sys
K = os.path.dirname(os.path.abspath(__file__))
R = os.path.abspath(os.path.join(K, '..', '..', '..'))
sys.path.insert(0, os.path.join(R, 'src'))
import labels as L, podii as PD
csv.field_size_limit(10**9)
D = os.path.join(R, 'data')
OUT = os.environ.get('OUT') or os.path.join(K, 'e25_vyhid')
ROKY = ('2024', '2025', '2026')
VYDY = ['ГП', 'АЛК', 'НАР', 'НАС', 'МАЙ', 'ДТП', 'ДОР', 'ДОМ', 'СЕР', 'поза видами']
# Втрати, які не є втратою події: подію несе інший документ справи
NE_VTRATA = {'другий документ тієї самої справи (не втрата)'}
KROKY = ['дамп', 'форма', 'подія', 'текст', 'фабула', 'місце', 'адреса', 'точка', 'набір 36.14', 'карта', 'проблеми', 'ризик']
POINT = {'house', 'cross', 'base', 'interp'}


def vyd(cat, grp=''):
    # Вид — за статтею, як у карті (labels.CODE), не за групою дампу.
    # Домашнє насильство в карті — частина НАС (35.8); окремим рядком «ДОМ»,
    # щоб його втрати (АДРЕСА_N, група 8_DOMESTIC) не ховалися в НАС.
    if L.SIMGROUP.get(cat) == 'НАС_домашнє' or grp == '8_DOMESTIC': return 'ДОМ'
    v = L.CODE.get(cat)
    return v[0] if isinstance(v, tuple) and v[0] in VYDY else 'поза видами'


def dump():
    """doc_id -> (cat, дата рішення, група, номер справи).

    Дамп — kyiv_*.csv разом з events.csv.gz. Локальні kyiv_*.csv старші за
    статті, додані 30.09 (RISHENNYA 34): ці документи (ст. 51 і 173 КУпАП,
    домашнє насильство та ін., понад 30 тис. рішень по суті) є лише в
    events.csv.gz, з групою-видом замість групи дампу. Без них воронка
    губила третину МАЙ і НАС (VIDPOVID-38, п. 1)."""
    out = {}
    for f in sorted(glob.glob(os.path.join(D, 'kyiv_*.csv'))):
        with open(f, encoding='utf-8-sig') as fh:
            for r in csv.DictReader(fh, delimiter='\t'):
                out[r['doc_id']] = (r['category_code'], r['date'], r['group'], r['cause_num'])
    with gzip.open(os.path.join(D, 'events.csv.gz'), 'rt', encoding='utf-8', newline='') as fh:
        for r in csv.DictReader(fh, delimiter='\t'):
            if r['doc_id'].isdigit() and r['doc_id'] not in out:
                out[r['doc_id']] = (r['cat'], r['date'], r['grp'], '')
    return out


def predstavnyky(DU, FO):
    """Події, а не папери: один представник на (справа, вид) — тим самим
    PD.merge_cases, що й черга проходу по текстах (step1c_teksty.queue_docs).
    Без цього кроку «немає тексту» змішує втрачені події з другими
    рішеннями тієї самої справи, які подією й не мали бути."""
    with gzip.open(os.path.join(D, 'events.csv.gz'), 'rt', encoding='utf-8', newline='') as fh:
        rows = [r for r in csv.DictReader(fh, delimiter='\t') if r.get('doc_id', '').isdigit()]
    links = PD.load_links()
    cause = {d: c for d, (c, _r) in links.items() if c}
    cause.update({d: v[3] for d, v in DU.items() if v[3]})
    reps = {rep['doc_id'] for rep, *_ in PD.merge_cases(
        rows, doc=lambda r: r['doc_id'], cat=lambda r: r['cat'], date=lambda r: r['date'],
        cause=cause, event=lambda r: FO.get(r['doc_id']) in PD.EVENT_FORMS)}
    return {r['doc_id'] for r in rows}, reps


def teksty():
    T = {}
    for f in sorted(glob.glob(os.path.join(D, 'teksty', '*.csv.gz'))):
        for r in csv.DictReader(gzip.open(f, 'rt', encoding='utf-8'), delimiter='\t'):
            T[r['doc_id']] = r
    return T


def stara_fabula():
    """Витяг кроку 1b (fabuly.csv.gz і таблиця fab) — джерело, з якого, за
    всім видно, рахувався перший прохід центрального чату."""
    f = {}
    with gzip.open(os.path.join(D, 'fabuly.csv.gz'), 'rt', encoding='utf-8') as fh:
        rd = csv.reader(fh, delimiter='\t'); next(rd)
        for r in rd:
            if len(r) >= 2 and r[1]: f[r[0]] = r[1]
    return f


def mapa_i_ryzyk():
    """Точка, карта, проблеми, ризик — з mapa.tsv.gz workflow «Е25 — воронка»
    (e25_mapa.py на свіжій базі). Файлу немає — None, і ці кроки «—»."""
    f = os.path.join(OUT, 'mapa.tsv.gz')
    if not os.path.exists(f): return None
    geo, karta, probl, ryz = {}, set(), set(), set()
    for r in csv.DictReader(gzip.open(f, 'rt', encoding='utf-8'), delimiter='\t'):
        if r['precision']: geo[r['doc_id']] = r['precision']
        if r['karta'] == '1': karta.add(r['doc_id'])
        if r['problema'] == '1': probl.add(r['doc_id'])
        if r['ryzyk'] == '1': ryz.add(r['doc_id'])
    return dict(geo=geo, karta=karta, ryz=ryz, probl=probl)


def main():
    os.makedirs(OUT, exist_ok=True)
    DU = dump(); FO = PD.load_formy(); T = teksty()
    N = {r['doc_id']: r for r in csv.DictReader(gzip.open(os.path.join(K, 'nabir_36_14.csv.gz'), 'rt', encoding='utf-8'))}
    SF = stara_fabula()
    M = mapa_i_ryzyk()
    geo_lok = {}
    if not M and os.path.exists(os.path.join(D, 'events.db')):
        geo_lok = dict(sqlite3.connect(os.path.join(D, 'events.db')).execute('select doc_id, precision from geo'))

    cnt = collections.defaultdict(collections.Counter)    # вид -> крок -> к-сть
    why = collections.defaultdict(collections.Counter)    # (вид, крок) -> причина -> к-сть
    pr = collections.defaultdict(list)                    # (крок, причина) -> doc_id
    sf_cnt = collections.defaultdict(collections.Counter)  # стара фабула для порівняння
    rows = []
    EVD, REPS = predstavnyky(DU, FO)
    for d, (cat, date, grp, _c) in DU.items():
        if date[:4] not in ROKY: continue
        v = vyd(cat, grp)
        stage, reason = None, ''
        cnt[v]['дамп'] += 1
        sf_cnt[v]['рішень'] += 1
        sf_cnt[v]['стара фабула'] += d in SF
        f = FO.get(d)
        t = T.get(d)
        # форма: без коду в дампі — маркери, як у podii.is_event
        if f:
            if f not in PD.EVENT_FORMS:
                stage, reason = 'форма', {'5': 'ухвала', '3': 'рішення (цивільне)', '4': 'судовий наказ'}.get(f, f'форма {f}')
        elif not PD.is_event(d, (t or {}).get('fab', '') or SF.get(d, ''), FO):
            stage, reason = 'форма', 'без форми, за маркерами — ухвала'
        if not stage:
            sf_cnt[v]['рішень по суті'] += 1
            sf_cnt[v]['стара фабула по суті'] += d in SF
            cnt[v]['форма'] += 1
            if d not in EVD:
                stage, reason = 'подія', ('група 8_DOMESTIC — крок 1 не бере (приватні адреси)' if grp == '8_DOMESTIC'
                                          else 'немає в events.csv')
            elif d not in REPS:
                stage, reason = 'подія', 'другий документ тієї самої справи (не втрата)'
        if not stage:
            cnt[v]['подія'] += 1
            if not t: stage, reason = 'текст', 'представник справи без проходу по текстах'
        if not stage:
            cnt[v]['текст'] += 1
            # Фабула не відсіває: карта бере адресу з речення адреси, і без
            # фабули подія йде далі (лише клас адреси стає D). Тому тут — окремий
            # лічильник, а не крок, на якому подія губиться.
            if t['fab']: cnt[v]['фабула'] += 1
            else:
                rs = ('кінець опису не знайдено' if t['end_found'] == '0' else 'опис порожній') + \
                     (', адреса є' if t['level'] in ('house', 'cross') else ', адреси немає')
                why[(v, 'фабула (не відсіває)')][rs] += 1
                pr[('фабула (не відсіває)', rs)].append(d)
        if not stage:
            lv = t['level']
            if lv == 'none': stage, reason = 'місце', 'місця в тексті не знайдено'
            elif lv == 'hidden': stage, reason = 'місце', 'знеособлено судом (АДРЕСА_N)'
        if not stage:
            cnt[v]['місце'] += 1
            if t['level'] == 'street': stage, reason = 'адреса', 'лише вулиця без номера'
            elif t['level'] not in ('house', 'cross'): stage, reason = 'адреса', 'рівень ' + t['level']
        if not stage:
            cnt[v]['адреса'] += 1
            p = (M['geo'] if M else geo_lok).get(d)
            if p in POINT: cnt[v]['точка'] += 1
            elif not stage: stage, reason = 'точка', 'немає координати' if p is None else f'точність {p}'
        if not stage:
            n = N.get(d)
            if n and n['v_rozrakhunkakh'] == '1': cnt[v]['набір 36.14'] += 1
            else: stage, reason = 'набір 36.14', (n or {}).get('chomu_ni') or 'немає в наборі'
        if not stage and M:
            if d in M['karta']: cnt[v]['карта'] += 1
            else: stage, reason = 'карта', 'відсіяно відбором карти'
            if not stage:
                if d in M['probl']: cnt[v]['проблеми'] += 1
                if d in M['ryz']: cnt[v]['ризик'] += 1
        if stage:
            why[(v, stage)][reason] += 1
            pr[(stage, reason)].append(d)
        rows.append((d, v, cat, date, stage or '', reason))

    with gzip.open(os.path.join(OUT, 'prychyny.tsv.gz'), 'wt', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh, delimiter='\t'); w.writerow(['doc_id', 'vyd', 'cat', 'data', 'vidpalo_na', 'prychyna']); w.writerows(rows)

    kroky = KROKY if M else [k for k in KROKY if k not in ('карта', 'проблеми', 'ризик')]
    o = []
    o.append('## Воронка за видами (рішення 2024–2026, дата рішення)\n')
    o.append('Частка — від дампу; у дужках — від попереднього кроку.\n')
    # kyiv_*.csv у .gitignore — є лише там, де дамп качали. Без них дамп = events.csv.gz,
    # і з рядка «дамп» випадають документи, яких у events немає (19.10 — ДОМ 2024, 13 905)
    if not glob.glob(os.path.join(D, 'kyiv_*.csv')):
        o.append('**Дамп kyiv_*.csv тут немає — рядок «дамп» = events.csv.gz.** Документів, яких '
                 'немає в events, воронка не бачить: 19.10 це були 13 905 рішень ДОМ 2024 '
                 '(архів 2024 після 30.09 не перечитано; ZVIT-38, п. 5). Від кроку «подія» — без змін.\n')
    o.append('| Вид | ' + ' | '.join(kroky) + ' |')
    o.append('|---' * (len(kroky) + 1) + '|')
    for v in VYDY + ['усі']:
        c = cnt[v] if v != 'усі' else sum((cnt[x] for x in VYDY), collections.Counter())
        if not c['дамп']: continue
        cells, prev = [], c['дамп']
        for k in kroky:
            n = c[k]
            cells.append(f'{n:,}'.replace(',', ' ') + ('' if k == 'дамп' else f' ({100 * n / c["дамп"]:.0f}% / {100 * n / prev:.0f}%)' if prev else ''))
            if k not in ('фабула', 'проблеми', 'ризик'): prev = n or prev
        o.append(f'| {v} | ' + ' | '.join(cells) + ' |')
    o.append('\n«фабула» не відсіває — частка від кроку «текст»; «місце» — частка від «текст».\n')
    o.append('\n## Причини втрат (кожне рішення — один раз, на першому кроці, де відпало)\n')
    for v in VYDY:
        if not cnt[v]['дамп']: continue
        o.append(f'\n**{v}**\n')
        for k in kroky[:4] + ['фабула (не відсіває)'] + kroky[5:]:
            for rs, n in why[(v, k)].most_common():
                o.append(f'- {k}: {rs} — ' + f'{n:,}'.replace(',', ' '))
    o.append('\n## Фабула: прохід по текстах проти старого витягу (fabuly.csv.gz)\n')
    o.append('| Вид | рішень | по суті | стара фабула (усі) | стара фабула (по суті) | фабула в проході (по суті з текстом) |')
    o.append('|---|---|---|---|---|---|')
    for v in VYDY:
        s = sf_cnt[v]
        if not s['рішень']: continue
        p = lambda a, b: f'{a:,} ({100 * a / b:.0f}%)'.replace(',', ' ') if b else '—'
        o.append(f"| {v} | {s['рішень']:,} | {s['рішень по суті']:,} | {p(s['стара фабула'], s['рішень'])} | "
                 f"{p(s['стара фабула по суті'], s['рішень по суті'])} | {p(cnt[v]['фабула'], cnt[v]['текст'])} |".replace(',', ' '))
    open(os.path.join(OUT, 'voronka.md'), 'w', encoding='utf-8').write('\n'.join(o) + '\n')

    # по 20 прикладів на причину — для читання очима
    rnd = random.Random(38)
    with open(os.path.join(OUT, 'pryklady.txt'), 'w', encoding='utf-8') as fh:
        for (k, rs), ids in sorted(pr.items(), key=lambda x: -len(x[1])):
            ids = list(ids); rnd.shuffle(ids)
            fh.write(f'\n######## {k}: {rs} — {len(ids):,}\n')
            for d in ids[:20]:
                t = T.get(d) or {}
                cat = DU[d][0]
                lab = (L.CODE.get(cat) or ('', 'код ' + cat))[1]
                txt = t.get('addr_sentence') or t.get('fab') or SF.get(d, '')
                fh.write(f"{d} | {lab[:45]} | форма {FO.get(d, '—')} | {t.get('level', '')} {t.get('street', '')} {t.get('house', '')}\n"
                         f"   {re.sub(r'\s+', ' ', txt)[:500]}\n")
    print('\n'.join(o))


if __name__ == '__main__':
    main()
