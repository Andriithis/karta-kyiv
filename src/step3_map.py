# -*- coding: utf-8 -*-
"""Крок 3. Карта з агрегацією по адресах + рейтинг адрес.

Класифікація спрощена до інцидент/проблема (передача, п.7.1): «проблема» —
це членство в кураторському списку ~50 адрес-напрямків (п.7.3), відібраних за
однорідністю СТАТТІ, а не теми (п.7.2). Аномалія як окрема категорія прибрана:
якщо відібраний напрямок не пояснюється моделлю ризику, картка просто каже
«причина встановлюється на місці» (п.7.1, 7.4).
"""
import os, re, sys, csv, gzip, json, glob, math, sqlite3, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import labels as L
import mech as M
import pravo as PR          # офіційні назви статей для картки і листа
# HTML-шаблон винесено в окремий файл: разом із ним модуль важив 67 КБ,
# а це один файл на дві дуже різні речі — логіку відбору й розмітку.
from step3_tpl import TPL, TPL_GL
# Районні файли в MapLibre-збірці вмикаються цим одним рядком — після того, як
# Андрій затвердить паритет і GL стане типовою версією.
GL_DISTRICTS = False
from map_excl import load_excl, detect_institutional, drop_excluded
import map_layers
import map_problems
import podii as PD           # що рахується подією: вирок і постанова, не ухвала
import step1c_teksty as TK   # частини проходу по текстах (крок 6)
from step2_geocode import BESIDE
from map_problems import COURTS, SLUG

LAST_META = {}          # meta останньої збірки — читає крок 5
LAST_DOCS = []          # справи адрес для панелі, паралельно до точок карти

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data'); DB = os.path.join(DATA, 'events.db')
OUT  = os.path.join(ROOT, 'site', 'kyiv.html')
NETW  = os.path.join(DATA, 'network.json')
RISKF = os.path.join(DATA, 'risk.json')
BORD  = os.path.join(DATA, 'borders.json')
FABSNAP = os.path.join(DATA, 'fabuly.csv.gz')   # витяги обставин для збірки в CI
FACTF = os.path.join(DATA, 'factors.json')             # шар чинників середовища (крок 2e)
EXCL = os.path.join(DATA, 'vykluchennya.txt')          # формується автоматично
MANUAL = os.path.join(DATA, 'vykluchennya_moyi.txt')    # ваш список, ніколи не перезаписується
REVIEW = os.path.join(DATA, 'top100_dlya_pereviryky.txt')
# Класи адреси події (podii.addr_class). На карту йде індекс, не літера: на
# 57 тисячах подій це пів сотні кілобайтів. 0 — B, адресу названо в описі.
ACLS = ['B', 'C', 'D']
INITIAL = re.compile(r'\b([А-ЯІЇЄҐ])\.([А-ЯІЇЄҐ])')
# Точність точки (step2_geocode) -> p[3] на карті. 0 — центр вулиці (на
# карту не йде), 1 — будинок з OSM, 2 — перехрестя, 3 — «20Б» біля
# будинку 20, 4 — між сусідніми номерами. Усе, крім 0, — справжнє місце;
# 3 і 4 вікно адреси позначає як приблизні.
PREC = {'house': 1, 'cross': 2, 'base': 3, 'interp': 4}
POINT = {'house', 'base', 'interp'}
MIN_EVENT_DATE = '2023-01-01'

# Посилання стиснуте до 34 знаків — правило одне з кроком 0 (podii.docref).
docref = PD.docref


def main(district=None, out=None):
    """Збирає карту. Версія одна: поділу на викладацьку й слухацьку немає —
    проблеми бачать усі, слухач копає причину далі за SARA."""
    if not os.path.exists(DB): print('спочатку кроки 1 і 2'); sys.exit(1)
    c = sqlite3.connect(DB)
    if not c.execute("SELECT name FROM sqlite_master WHERE name='geo'").fetchone():
        print('немає таблиці geo — крок 2 не відпрацював'); sys.exit(1)

    # Спершу минулі роки з data/posylannya (так на сайті, де kyiv_*.csv є лише
    # за поточний рік), зверху — kyiv_*.csv, якщо вони є: там свіжіше.
    extra = PD.load_links()
    n_links = len(extra)
    for fp in glob.glob(os.path.join(DATA, 'kyiv_*.csv')):
        with open(fp, encoding='utf-8-sig') as fh:
            for r in csv.DictReader(fh, delimiter='\t'):
                extra[r['doc_id']] = (r['cause_num'], docref(r['doc_url']))
    print(f'посилань на рішення: {len(extra):,} (з data/posylannya — {n_links:,})')

    rows = list(c.execute("""SELECT e.doc_id,e.court,e.cat,e.date,e.tm,e.street,e.house,
        g.lat,g.lon,g.precision FROM events e JOIN geo g ON g.doc_id=e.doc_id"""))
    # Прохід по текстах (крок 6): адреса документа — з проходу, так само як
    # у step2_geocode, інакше підпис точки й перевірка на установи брали б
    # стару адресу при новій точці.
    TKD = TK.load_done()
    rows = [(r[:5] + (TKD[r[0]]['street'], TKD[r[0]]['house'] or None) + r[7:]) if r[0] in TKD else r
            for r in rows]
    print(f'подій з координатами: {len(rows):,} (з проходу по текстах: {len(TKD):,})')
    if not rows: return

    # витяги обставин (крок 1b). Може не бути зовсім або бути частково —
    # завантаження довге, а карта має збиратися з тим, що вже є.
    # Витяги обставин (крок 1b). Спершу таблиця в базі — вона є на комп'ютері,
    # де крок 1b і працював. Якщо таблиці немає, читаємо знімок із репозиторію:
    # саме так це відбувається в GitHub Actions, де база збирається наново з
    # events.csv.gz і жодного витягу в ній немає. Без цього на живому сайті
    # панель була б без обставин, хоча вони давно зібрані й лежать поруч.
    fab = PD.load_fab(c)
    if fab:
        print(f'витяги обставин: {len(fab):,}')
    else:
        print('витягів обставин немає — панель покаже перелік рішень без опису')

    print('перевірка на адреси установ:')
    excl = detect_institutional(rows, load_excl())
    # «20Б» біля будинку 20 стоїть на BESIDE північніше — для перевірки за
    # точкою беремо сам будинок: «пл. Вокзальна, 1В» біля вокзалу, що в
    # переліку установ, мусить піти разом із ним.
    rows = drop_excluded(rows, excl, street=lambda r: r[5], house=lambda r: r[6],
                         lat=lambda r: r[7] - (BESIDE if r[9] == 'base' else 0),
                         lon=lambda r: r[8], exact=lambda r: r[9] in POINT)
    print(f'   залишилось {len(rows):,}')

    # ---- ОДНА СПРАВА = ОДНА ПОДІЯ (борг 5.7) ----
    # У двигуні це виправлено 31 серпня, а карта досі рахувала папери. Одна
    # аварія дає ланцюжок документів — обвинувальний акт, призначення розгляду,
    # експертиза, вирок, — і кожен важив як окрема подія. Виміряно 3 вересня:
    # у майнових це 17% зайвого, у насильстві 14%, разом по місту 4%.
    #
    # Папери справи не викидаємо, а лишаємо при представнику: панель показує
    # усі рішення справи, і саме заради цього тут не просто відсів.
    #
    # Подією справи може бути лише рішення по суті, а подія одна на (справа,
    # вид подій) — правило спільне з моделлю й звітами, src/podii.py.
    # Ухвали лишаються серед паперів справи, представником не стають.
    formy = PD.load_formy()
    isev = {r[0]: PD.is_event(r[0], fab.get(r[0], ''), formy) for r in rows}
    nproc = sum(1 for v in isev.values() if not v)
    print(f'   процесуальних документів (ухвали): {nproc:,} з {len(rows):,}; '
          f'форма з дампу є для {sum(1 for d in isev if formy.get(d)):,}')
    cause = {d: v[0] for d, v in extra.items() if v[0]}
    merged = PD.merge_cases(rows, doc=lambda r: r[0], cat=lambda r: r[2], date=lambda r: r[3],
                            cause=cause, event=lambda r: isev[r[0]])
    # Справа, представника якої розібрав прохід по текстах, бере адресу лише
    # з нього. Якщо його самого серед подій з координатами немає (адреса
    # прихована чи місця в тексті не названо), представником став би інший
    # документ справи зі старою адресою — і на карту повернулося б саме те,
    # що прохід прибрав. Такі справи пропускаємо.
    cat_of = dict(c.execute('SELECT doc_id, cat FROM events'))
    tk_cases = {(cause[d], PD.theme(cat_of[d])) for d in TKD if d in cause and d in cat_of}
    reps, case_docs, arts = [], {}, {}
    n_tk_gone = 0
    n_old = collections.Counter()
    for rep, g, lab, cats in merged:
        if rep[0] not in TKD and (cause.get(rep[0]), PD.theme(rep[2])) in tk_cases:
            n_tk_gone += 1
            continue
        # На карту — лише події з датою від 2023 року, за датою самої події,
        # а не рішення (рішення 24.09, п.3). Старіші лишаються в даних.
        ed = (TKD.get(rep[0]) or {}).get('date') or ''
        if ed and ed < MIN_EVENT_DATE:
            n_old[PD.theme(rep[2])] += 1
            continue
        # підпис події — стаття, найтяжча в цьому виді справи (podii.label_cat)
        reps.append(rep[:2] + (lab,) + rep[3:])
        case_docs[rep[0]] = [x[0] for x in sorted(g, key=lambda x: x[3] or '')]
        # решта статей справи — окремим полем: ст.130 у справі про ДТП
        # підпис не бере, але для відбору проблем вона є фактом про місце
        own = PD.article(lab)
        arts[rep[0]] = sorted({PD.article(c) for c in cats} - {own, ''})
    nmulti = sum(1 for v in arts.values() if v)
    print(f'   подій із кількома статтями: {nmulti:,}')
    print(f'   одна подія на (справа, вид): {len(rows):,} документів -> {len(reps):,} подій')
    if n_tk_gone:
        print(f'   справ, яким прохід по текстах прибрав адресу: {n_tk_gone:,}')
    if n_old:
        print(f'   подій з датою до {MIN_EVENT_DATE[:4]} (на карту не йдуть): {sum(n_old.values()):,} — '
              + ', '.join(f'{k} {v:,}' for k, v in n_old.most_common()))
    rows = reps

    # ---- злиття кодів у назви ----
    cnt = collections.Counter()
    for r in rows:
        lb = L.CODE.get(r[2])
        if lb: cnt[lb] += 1
        else: cnt[('СЕР', 'інші (код ' + r[2] + ')')] += 1

    labels = sorted(cnt, key=lambda k: (L.ORDER.index(k[0]) if k[0] in L.ORDER else 9, -cnt[k]))
    li = {k: i for i, k in enumerate(labels)}
    ck = sorted({r[1] for r in rows}); ci = {v: i for i, v in enumerate(ck)}

    yc = collections.Counter(r[3][:4] for r in rows)
    yrs = sorted(y for y, n in yc.items() if n >= 200 and y.isdigit())
    ykeys = yrs + (['раніше'] if sum(n for y, n in yc.items() if y not in yrs) else [])
    yi = {y: i for i, y in enumerate(ykeys)}
    print('роки:', ', '.join(ykeys))
    print(f'статей після злиття: {len(labels)} (було би {len({r[2] for r in rows})} за кодами)')

    # група подібності (п.7.2) для кожного індексу в `labels`
    LBL2SIM = {}
    for _code, (_th, _lbl) in L.CODE.items():
        LBL2SIM[(_th, _lbl)] = M.simgroup(_code) or f'{_th}_{_code}'
    sim_of = [LBL2SIM.get(k, f'{k[0]}_i{i}') for i, k in enumerate(labels)]

    agg = collections.defaultdict(list)
    for doc, court, cat, date, tm, street, house, la, lo, prec in rows:
        lb = L.CODE.get(cat) or ('СЕР', 'інші (код ' + cat + ')')
        tk = TKD.get(doc)
        if tk is not None:
            # фабула й клас — з проходу; шкідлива фабула на сайт не йде
            # (панель покаже рішення з посиланням, без опису), клас у неї D
            # tidy_end — хвіст кваліфікації («тому його дії») і в уже
            # записаних частинах, без їх перезапису
            f = '' if tk['vada'] == 'шкідлива' else TK.tidy_end(tk['fab'])
            kl = tk['klass']
        else:
            f = next((fab[x] for x in case_docs.get(doc, [doc]) if fab.get(x)), '')
            # клас адреси — з опису тієї самої справи, що й показує панель
            kl = PD.addr_class(f, street)
        # Панель показує дату й час самої події з проходу: дата рішення буває
        # на місяць пізніше («2026-04-22 · 23:00» при події 21.03.2026). Нема
        # дати події — дата рішення з позначкою «рішення» (рішення 24.09).
        ed = (tk or {}).get('date') or ''
        et = (tk or {}).get('time') or ''
        if et[:2].isdigit():
            tm = et
        agg[(round(la, 5), round(lo, 5))].append(
            (ci[court], li[lb], yi.get(date[:4], yi.get('раніше', 0)),
             int(tm[:2]) if tm and tm[:2].isdigit() else -1,
             PREC.get(prec, 0), date, street or '', house or '',
             *extra.get(doc, ('', '')),
             [extra.get(x, ('', ''))[1] for x in case_docs.get(doc, [doc])
              if extra.get(x, ('', ''))[1]],
             f, arts.get(doc, []), ACLS.index(kl), ed or date, 0 if ed else 1))
    ncls = collections.Counter(ACLS[e[13]] for evs in agg.values() for e in evs)
    print('   клас адреси подій: ' + ', '.join(f'{k} {ncls[k]:,}' for k in ACLS))

    # ---- ЧЕСНА НАЗВА ТОЧКИ (виправлено 01.09.2026) ----
    # Крок 2 має два режими прив'язки. Коли будинок є в OpenStreetMap, подія
    # стає на свою адресу. Коли будинку немає — подія стає в ЦЕНТР ВУЛИЦІ,
    # і туди ж стають усі інші події цієї вулиці без знайденого будинку.
    # Раніше така купа підписувалася номером першої-ліпшої події: «вул.
    # Міхновського, 42 — 96 подій», хоча на самому будинку 42 сталася одна.
    # Це не установа й не помилка адреси — це загальний осередок вулиці,
    # і називати його треба саме так.
    P = []
    DOCS = []          # паралельно до P: справи адреси для правої панелі
    n_street = 0
    for (la, lo), evs in agg.items():
        hs = [e for e in evs if e[4] and e[6]]
        if hs:
            e = hs[0]
            a = f"{e[6]}, {e[7]}" if e[7] else e[6]
            prec = e[4]            # PREC: будинок, перехрестя, біля будинку, між сусідами
        else:
            e = next((e for e in evs if e[6]), None)
            # Перехрестя (addr.extract, level='cross') — це вже точка, а не
            # вулиця: «вул. X / вул. Y» без хвоста (рішення 23.09).
            a = (e[6] if ' / ' in e[6] else e[6] + ' · вся вулиця') if e else ''
            prec = 0
            n_street += 1
        # «вул. Г.Хоткевича» -> «вул. Г. Хоткевича»: у текстах рішень ініціал
        # пишуть і з пробілом, і без, а підпис має бути один. Лише в підписі —
        # ключі адрес і перелік установ порівнюють сирі рядки.
        a = INITIAL.sub(r'\1. \2', a)
        # p[5] — УСІ справи адреси, найновіші згори: стаття, дата, година,
        # номер справи. Раніше тут було шість прикладів — панелі зі списком
        # рішень цього мало.
        #
        # Посилань на самі документи тут НЕМАЄ навмисно: у шістнадцятковому
        # вигляді вони важать 2,4 МБ на файл. Вони їдуть окремим файлом на
        # район разом із витягами обставин — панель підтягує його, коли її
        # відкривають. Порядок справ у тому файлі той самий, що тут.
        ev_sorted = sorted(evs, key=lambda x: x[14], reverse=True)   # за датою події
        P.append([la, lo, a, prec,
                  # подія: суд, стаття, рік, година, клас адреси (індекс у
                  # ACLS, 0 — B), далі інші статті справи — лише коли вони є
                  # у тому самому порядку, що й DOCS: панель відбирає справи
                  # тим самим фільтром за індексом, і число в кнопці «Усі
                  # рішення» збігається з числом справ у панелі
                  [[e_[0], e_[1], e_[2], e_[3], e_[13]] + ([e_[12]] if e_[12] else [])
                   for e_ in ev_sorted],
                  len(ev_sorted)])
        # DOCS — те, що показує панель: справа, дата події (або рішення),
        # година, номер справи, папери справи, фабула; сьоме поле 1 — дата
        # рішення, бо дати події в описі немає.
        DOCS.append([[e_[1], e_[14], e_[3], e_[8], e_[10], e_[11]] + ([1] if e_[15] else [])
                     for e_ in ev_sorted])
    print(f'унікальних адрес: {len(P):,} '
          f'(з них {n_street:,} — центри вулиць, точного будинку немає)')

    groups_idx = {}
    for ti, t in enumerate(L.ORDER):
        for i, k in enumerate(labels):
            if k[0] == t: groups_idx[i] = ti
    groups = []
    gi_of_theme = {}       # код теми -> її індекс у meta['groups'] (для фільтрації карток)
    for t in L.ORDER:
        ids = [li[k] for k in labels if k[0] == t]
        if ids:
            gi_of_theme[t] = len(groups)
            groups.append([L.THEMES[t], ids, sum(cnt[labels[i]] for i in ids)])
    # law: короткий підпис -> повна назва статті з кодексу. Коротким підписом
    # карта користується в списках, повним — картка проблеми й паспорт SARA,
    # бо лист балансоутримувачу має називати статтю так, як її названо в законі.
    law = {k[1]: PR.nazva(k[1]) for k in labels if PR.nazva(k[1])}
    _no = [k[1] for k in labels if not PR.nazva(k[1])]
    if _no: print(f'   без офіційної назви статті: {len(_no)} — {"; ".join(_no[:3])}')
    meta = dict(courts=[COURTS.get(x, x) for x in ck], cats=[k[1] for k in labels],
                counts=[cnt[k] for k in labels], groups=groups, years=ykeys, law=law)


    # ---- шари контексту: потоки, ризик, чинники (map_layers) ----
    risks, ER, theme_rgrid, pred_theme, FACT = map_layers.build(district, labels)

    # ---- відбір проблем і обрізання до району (map_problems) ----
    P, POP, meta, theme_cnt = map_problems.select(
        P, meta, labels, ck, ykeys, sim_of, gi_of_theme,
        district, risks, ER, FACT, theme_rgrid, pred_theme)

    # Дані серіалізуються один раз і лягають однаково в обидві збірки — і в
    # Leaflet, і в MapLibre. Інакше порівнювати їх на паритет не було б сенсу.
    subst = {'__POP__': json.dumps(POP, separators=(',', ':')),
             '__FACTS__': json.dumps(FACT, ensure_ascii=False, separators=(',', ':')),
             '__RISKS__': json.dumps(risks, ensure_ascii=False, separators=(',', ':')),
             '__META__': json.dumps(meta, ensure_ascii=False),
             '__PTS__': json.dumps(P, ensure_ascii=False, separators=(',', ':'))}
    def fill(tpl):
        for k, v in subst.items():
            tpl = tpl.replace(k, v)
        return tpl
    html = fill(TPL)
    # Крок 5 бере звідси числа районів для плиток — щоб не збирати десять карт
    # заради десяти чисел.
    global LAST_META, LAST_DOCS
    LAST_META = meta
    LAST_DOCS = DOCS

    dst = out or OUT
    os.makedirs(os.path.dirname(dst) or '.', exist_ok=True)

    # ---- СПРАВИ АДРЕС: окремими файлами по районах ----
    # Разом із витягами обставин це десятки мегабайтів — у сторінку такому не
    # місце. Панель тягне файл свого району тоді, коли її відкривають, і одне
    # посилання лишається одним.
    fdir = os.path.join(os.path.dirname(dst) or '.', 'spravy')
    os.makedirs(fdir, exist_ok=True)
    slugs = meta.get('dslug', [])
    by_d = collections.defaultdict(dict)
    for i, p in enumerate(P):
        di = p[8] if len(p) > 8 else -1
        if i < len(DOCS): by_d[di][i] = DOCS[i]
    tot = 0
    for di, v in by_d.items():
        name = slugs[di] if 0 <= di < len(slugs) else 'inshe'
        fp = os.path.join(fdir, name + '.json')
        json.dump(v, open(fp, 'w', encoding='utf-8'),
                  ensure_ascii=False, separators=(',', ':'))
        tot += os.path.getsize(fp)
    print(f'   справи адрес: {len(by_d)} файлів у spravy/ ({tot/1048576:.1f} МБ)')

    open(dst, 'w', encoding='utf-8').write(html)
    print(f'готово: {os.path.basename(dst)} ({os.path.getsize(dst)/1048576:.1f} МБ)')
    # Друга збірка, MapLibre, поруч із першою. Поки що лише міська карта:
    # районні файли переходять разом із перемиканням типової версії, і тоді
    # досить поставити GL_DISTRICTS = True.
    if district is None or GL_DISTRICTS:
        dst_gl = dst[:-len('.html')] + '-gl.html'
        open(dst_gl, 'w', encoding='utf-8').write(fill(TPL_GL))
        print(f'готово: {os.path.basename(dst_gl)} ({os.path.getsize(dst_gl)/1048576:.1f} МБ)')
    return theme_cnt

if __name__ == '__main__':
    main()
