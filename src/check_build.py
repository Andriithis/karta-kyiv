# -*- coding: utf-8 -*-
"""Самоперевірка збірки карти. Запускати після кожної правки.

Що робить:
  1. зносить __pycache__ і компілює всі файли в src/ — ловить друкарські
     помилки, зіпсовані символи й збірку зі старого кешу;
  2. розпаковує зменшену базу data/events_test.db.gz (22 тисячі подій,
     усі десять районів) — справжня база для цього не потрібна;
  3. збирає дві карти: міську й обрізану до одного району;
  4. витягає з кожної <script> і перевіряє синтаксис через node, якщо він є;
  5. перевіряє, що відомі установи не просочилися на карту;
  6. рахує баланс тегів розмітки;
  6. порівнює контрольні суми з попереднім запуском і каже, чи змінився
     результат.

Порядок роботи з пунктом 6: перед правкою запустіть `python src/check_build.py
--save` — це запам'ятає еталон. Після правки запустіть без ключа. Якщо ви лише
переставляли код, а не міняли поведінку, всі три карти мають лишитися
незмінними. Якщо змінилися — ви бачите, які саме.

Еталон лежить у data/_check_last.json і в репозиторій не потрапляє.
"""
import os, sys, gzip, glob, json, shutil, hashlib, tempfile, subprocess, py_compile, re

SRCD = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SRCD)
DATA = os.path.join(ROOT, 'data')
TESTGZ = os.path.join(DATA, 'events_test.db.gz')
TESTDB = os.path.join(DATA, 'events_test.db')      # data/*.db у .gitignore
STATE = os.path.join(DATA, '_check_last.json')
sys.path.insert(0, SRCD)

VOID = {'meta', 'link', 'br', 'hr', 'img', 'input', 'source',
        'area', 'base', 'col', 'embed', 'track', 'wbr'}

# ---- АДРЕСИ, ЯКИХ НА КАРТІ БУТИ НЕ МАЄ ----
# Це відділи поліції та місця оформлення протоколів. Кожну з них колись уже
# ловили, і кожна колись поверталася — бо ловилися вони правилом, а не
# перевіркою. Тепер повернення видно одразу.
#
# Додавайте сюди щоразу, коли знаходите установу на карті: спершу рядок тут,
# і аж потім правило, яке її ловить.
NE_MAE_BUTY = [
    'вул. Відпочинку, 18',
    'вул. Чорних Запорожців, 20',
    'вул. Святослава Хороброго, 9',
    'вул. С. Хороброго, 9',
    'вул. Бродівська, 79',
    'вул. Радосинська, 140',
    # СІЗО: адресу в описі названо (події в ізоляторі), тож ловиться лише
    # ознакою «закрита установа» (amenity=prison в OSM, 30.09)
    'вул. Дегтярівська, 13',
]


# ---- СПЕЦИФІКАЦІЯ ↔ ТЕСТИ (RISHENNYA 36.31.4) ----
# Правило в SPECYFIKATSIYA.md посилається на перевірку як `test:назва`; тут —
# реєстр наявних перевірок (назва -> крок цієї збірки). Назва без ⏳, якої
# тут немає, — червона збірка: інакше правило вдає перевірене, хоча тест
# прибрали чи перейменували. `⏳test:` — тест ухвалено, ще не написано.
SPEC = os.path.join(ROOT, 'SPECYFIKATSIYA.md')
TESTY = {
    'kompiliatsiia': '1. Компіляція src/',
    'rozmitka': '5. Розмітка',
    'js': '5. JavaScript',
    'ustanovy': '4. Установи не просочилися на карту',
    'sud_raion': '4б. Суд ↔ район точки',
    'pai_ryzyku': '4а. Шари ризику: PAI ≥ 3',
    'specyfikatsiia': '0. Специфікація ↔ тести',
    'dzherelo_tochky': '4в. Точки карти: «база» й «між сусідами» — 0',
    'zahlushky': '4г. Фабули в показі: заглушок 0, шапок і посилань ≤1%',
    'zhakkar': '4д. Стабільність ризику: спільних ліній з попередньою збіркою ≥0,7',
    'chyslo_problem': '4е. Число проблем: карта = «Проблеми» = problems_report',
    'uzhodzhenist': '7. Узгодженість у браузері: підказка = картка = сума видів',
    'telefon': '7. Телефон 375×812: точка й +/− над шторкою, одна висота, 14 px, 44 px',
    'kandydaty': '4ж. Кандидати для аналізу фабул: файл є, непорожній, ≤20 МБ, ДТП з полем mitky',
    # окремим запуском (test_determinizm.py), не в check_build: дві збірки — ~6 хв
    'determinizm': 'test_determinizm.py: збірка двічі — той самий хеш (щомісяця в «Оновленні карти»)',
    'histerezys_pravyla': '4л. Гістерезис не тримає проблему, чиї події пішли через правила',
    'bez_nomera': '4й. Події з точністю «вулиця» — 0 у точках будинків і перехресть',
    'bez_naselennia': '4к. Шару «Населення» на карті немає: ні перемикача, ні шару, ні файлу',
    'vaga': '4и. Вага першого завантаження: ≤3 МБ розпаковано (жовта), ≤5 МБ і ≤1 МБ мережею (червона)',
    'atrybutsiia': '4з. Атрибуція: п\'ять джерел і умови OSM на карті, у звітах і файлах адрес',
    'poshuk_143': '8. Пошук: 143 запити Е12б — першим ≥131',
    'poshuk_opysky': '8. Пошук: описки — у перших п\'яти ≥12 з 13',
    'poshuk_andrii': '8. Пошук: запити Андрія — вулиця в перших трьох, ≤100 мс на телефоні',
}

# S-Р.11, 36.24.2: менше — жовта збірка (публікується, але з переліком і причиною)
ZHAKKAR_MIN = .7


def ryzyk_klyuchi(r):
    """шар -> множина показаних ліній (назва + кінці) і точок (координати)"""
    out = {}
    for k, v in (r.get('layers') or {}).items():
        out['лінії ' + k] = {(x[1], tuple(x[0][0]), tuple(x[0][-1])) for x in v.get('items', []) if x and x[0]}
    for k, v in (r.get('tochky') or {}).items():
        out['точки ' + k] = {(x[0], x[1]) for x in v.get('items', [])}
    return out


def zhakkar(rp):
    """[(шар, частка, зникло, з'явилось)] проти data/risk.json з HEAD; None —
    попередньої немає чи файл не мінявся (тиждень без перенавчання)."""
    import subprocess
    try:
        old = subprocess.run(['git', 'show', 'HEAD:data/risk.json'], cwd=ROOT, capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if old.returncode or not old.stdout: return None
    new = open(rp, 'rb').read()
    if new == old.stdout: return []
    a, b = ryzyk_klyuchi(json.loads(old.stdout.decode('utf-8'))), ryzyk_klyuchi(json.loads(new.decode('utf-8')))
    res = []
    for k in sorted(set(a) | set(b)):
        x, y = a.get(k, set()), b.get(k, set())
        res.append((k, len(x & y) / max(len(x | y), 1), len(x - y), len(y - x)))
    return res

# Фабули на сайті (S-П.8; 36.19.1–3): що бачить слухач — site/spravy/*.json
ZAHLUSHKY = re.compile(r'ОСОБА_\d|ІНФОРМАЦІЯ_\d|НОМЕР_\d|АДРЕСА_\d')
SHAPKA_POKAZ = re.compile(r'^\s*(?:У\s+протокол|У\s+відповідності|Відповідно\s+до\s+висунутого|'
                          r'Складеного\s+відносно|З\s+огляду\s+на\s+викладене|Згідно\s+(?:з\s+)?протокол)', re.I)
PRAVO_POKAZ = re.compile(r'(?:в|у)\s+порушення\s+(?:вимог\w*\s+)?(?:п\.\s*п\.|пп\.|п\.|пункт)|'
                         r'всупереч\s+вимогам\s+(?:ст|статт)', re.I)


def fabuly_saitu(d):
    """(фабул, із заглушками, з шапкою, з юридичним посиланням) у site/spravy"""
    import glob as _g
    n = z = s = p = 0
    for f in _g.glob(os.path.join(d, '*.json')):
        txt = open(f, encoding='utf-8').read()
        # фабули — рядки JSON довші за 60 знаків з кириличним текстом
        for m in re.finditer(r'"((?:[^"\\]|\\.){60,})"', txt):
            t = m.group(1)
            if not re.search(r'[а-яіїєґ]{4}', t): continue
            n += 1; z += bool(ZAHLUSHKY.search(t)); s += bool(SHAPKA_POKAZ.match(t)); p += bool(PRAVO_POKAZ.search(t))
    return n, z, s, p


def tochky_karty(html_path):
    """Лічильник p[3] (точність) точок зібраної карти: 0 — центр вулиці,
    3 — «база», 4 — між сусідами (step3_map.PREC). S-А.3 і S-А.4 вимагають,
    щоб їх не було зовсім."""
    import collections, map_dani
    d = map_dani.chytaty(html_path, 'pts')
    if not d: return None
    return collections.Counter(p[3] for p in d['pts'] if len(p) > 3)


def spec_testy():
    """(помилки, підсумок): тести без ⏳, яких немає в TESTY, і скільки правил
    чим перевіряються. Розбір — за рядками таблиць `| S-… | правило | джерело |
    перевірка |`: остання колонка й є перевірка."""
    if not os.path.exists(SPEC):
        return [f'немає {os.path.basename(SPEC)}'], {}
    import collections
    st = collections.Counter(); bad = []
    # ≤ 50 КБ (36.31.1, 36.38.2): файл читається цілком на початку кожної
    # роботи; 40 змушувало стискати правила до неясності
    kb = os.path.getsize(SPEC) / 1024
    st['КБ'] = round(kb, 1)
    if kb > 50: bad.append(f'{os.path.basename(SPEC)} — {kb:.1f} КБ, межа 50')
    for ln in open(SPEC, encoding='utf-8'):
        m = re.match(r'^\| (S-[^\s|]+) \|(.*)\|\s*$', ln)
        if not m: continue
        st['правил'] += 1
        perev = m.group(2).split('|')[-1]
        gotovi = [t for p, t in re.findall(r'(⏳?)test:([a-z0-9_]+)', perev) if not p]
        plan = re.findall(r'⏳test:([a-z0-9_]+)', perev)
        for t in gotovi:
            if t not in TESTY: bad.append(f'{m.group(1)}: test:{t} немає в check_build')
        if gotovi: st['з тестом'] += 1
        elif plan: st['тест ухвалено, ще не написано'] += 1
        elif 'очима' in perev: st['очима'] += 1
        else: st['без перевірки'] += 1
    return bad, dict(st)


def drop_cache():
    """Прибрати __pycache__ перед перевіркою.

    Знайдено 3 вересня: збірка взяла старий .pyc і зібрала карту з коду, якого
    вже не було у файлах. Перевірка при цьому казала «чисто». Тому кеш зносимо
    завжди — інакше слово «перевірено» нічого не варте.
    """
    d = os.path.join(SRCD, '__pycache__')
    if os.path.isdir(d):
        shutil.rmtree(d, ignore_errors=True)


def compile_all():
    bad = []
    for f in sorted(os.listdir(SRCD)):
        if not f.endswith('.py'):
            continue
        try:
            py_compile.compile(os.path.join(SRCD, f), doraise=True)
        except Exception as e:
            bad.append(f'{f}: {e}')
    return bad


def unpack():
    if not os.path.exists(TESTGZ):
        return f'немає {os.path.relpath(TESTGZ, ROOT)}'
    with gzip.open(TESTGZ, 'rb') as g, open(TESTDB, 'wb') as f:
        shutil.copyfileobj(g, f)
    return None


def check_markup(html):
    from html.parser import HTMLParser

    class P(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.st, self.err = [], []

        def handle_starttag(self, t, a):
            if t not in VOID:
                self.st.append(t)

        def handle_endtag(self, t):
            if t in VOID:
                return
            if not self.st:
                self.err.append(f'зайвий </{t}>')
            elif self.st[-1] != t:
                self.err.append(f'очікував </{self.st[-1]}>, отримав </{t}>')
            else:
                self.st.pop()

    p = P()
    p.feed(html)
    return p.err + [f'не закрито <{t}>' for t in p.st]


def check_js(html, tmp):
    # сторінка — ES-модуль (import MapLibre, await даних), тож .mjs
    m = re.search(r'<script type="module">\n(.*)\n</script>', html, re.S)
    if not m:
        return ['не знайдено <script type="module"> у сторінці']
    jsf = os.path.join(tmp, 'x.mjs')
    with open(jsf, 'w', encoding='utf-8') as f:
        f.write(m.group(1))
    if not shutil.which('node'):
        return []                       # node не встановлено — мовчки пропускаємо
    r = subprocess.run(['node', '--check', jsf], capture_output=True, text=True)
    return [] if r.returncode == 0 else [r.stderr.strip().split('\n')[-1]]


# ---- СУД ↔ РАЙОН (ZAVDANNYA-32, 2.2) ----
# Адмінсправу розглядає суд району, де вчинено порушення (ст. 276 КУпАП),
# кримінальну — переважно теж. Тож район точки має збігатися з районом суду.
# Незбіг — верхня межа помилок геокодера: частина законна (вулиці-межі,
# передача справ), але 06.10 до лікування однойменних вулиць він був 5,7%.
# Більше 8% — щось зламалося, сайт не публікується.
SUD_MEZHA = 0.08
SUD_ADRESA_MIN, SUD_ADRESA_CHASTKA = 5, 0.5


def sud_raion(html_path):
    """(частка незбігу, по видах, по районах, підозрілі адреси) з готової
    карти: точні точки (будинок, перехрестя) й районні суди."""
    import collections, map_dani
    d = map_dani.chytaty(html_path, 'meta', 'pts')
    if not d: return None
    M, P = d['meta'], d['pts']
    courts, dn = M.get('courts', []), M.get('dnames', [])
    gi = {}
    for g, (nm, ids, _n) in enumerate(M.get('groups', [])):
        for i in ids: gi[i] = nm
    vyd, raion, adr = (collections.defaultdict(lambda: [0, 0]) for _ in range(3))
    for p in P:
        if p[3] not in (1, 2) or len(p) < 9 or not (0 <= p[8] < len(dn)): continue
        d = dn[p[8]]
        for e in p[4]:
            c = courts[e[0]] if e[0] < len(courts) else ''
            if c not in dn: continue                 # апеляційний та інші — не районні
            bad = int(c != d)
            for t in (vyd[gi.get(e[1], '?')], raion[d], adr[p[2]]):
                t[0] += 1; t[1] += bad
    n = sum(v[0] for v in raion.values()); b = sum(v[1] for v in raion.values())
    pidozr = sorted(((a, v[0], round(v[1] / v[0], 2)) for a, v in adr.items()
                     if v[0] >= SUD_ADRESA_MIN and v[1] >= SUD_ADRESA_CHASTKA * v[0]), key=lambda x: -x[1])
    return (b / n if n else 0, {k: round(v[1] / v[0], 3) for k, v in vyd.items() if v[0]},
            {k: round(v[1] / v[0], 3) for k, v in raion.items() if v[0]}, pidozr, n)


def main(save=False):
    print('0. Специфікація ↔ тести (RISHENNYA 36.31.4)')
    bad, st = spec_testy()
    for b in bad: print('   ПОМИЛКА', b)
    if bad: return 1
    print('   ' + '; '.join(f'{k} {v}' for k, v in st.items()))

    print('1. Компіляція src/')
    drop_cache()
    bad = compile_all()
    if bad:
        for b in bad:
            print('   ПОМИЛКА', b)
        return 1
    print('   усі файли компілюються')

    print('2. Тестова база')
    err = unpack()
    if err:
        print('   ПОМИЛКА', err)
        return 1
    print(f'   {os.path.relpath(TESTDB, ROOT)} розпаковано')

    import step3_map, map_excl
    step3_map.DB = TESTDB
    # Перевірка не має чіпати справжні дані. Раніше вона переписувала
    # data/vykluchennya.txt переліком, порахованим на зменшеній базі, — і цей
    # перелік потрапляв у коміт. Вихідні файли відводимо у тимчасову папку;
    # ваші власні списки (vykluchennya_moyi, vykluchennya_ne) лишаються вхідними.
    tmp = tempfile.mkdtemp(prefix='karta_check_')
    map_excl.EXCL = os.path.join(tmp, 'vykluchennya.txt')
    map_excl.REVIEW = os.path.join(tmp, 'top100.txt')
    # Те саме зі звітом проблем: перевірка на тестовій базі (події до 08.2026)
    # переписувала data/problems_report.json, і в main ішов він, а не звіт
    # живої збірки (19.10: у main 7 проблем, на карті 53). Гістерезис читає
    # саме цей файл як минулу збірку.
    import problems
    problems.REPORT = os.path.join(tmp, 'problems_report.json.gz')
    problems.SKHOZHI = os.path.join(tmp, 'skhozhi_1551.json')
    problems.KANDYDATY = os.path.join(tmp, 'kandydaty.json.gz')
    problems.ZMINY = os.path.join(tmp, 'ZMINY-METODYKY.md')      # 36.40: журнал не чіпаємо

    CASES = [('міська', dict(district=None)),
             ('районна', dict(district='Деснянський'))]

    now, problems, city_html, tochnist_mista = {}, [], '', {}
    try:
        for name, kw in CASES:
            print(f'3. Збірка: {name}')
            # кожна збірка — у своїй папці: dani/ прибирає файли, на які її
            # сторінка не посилається, і районна стерла б міські
            os.makedirs(os.path.join(tmp, name), exist_ok=True)
            dst = os.path.join(tmp, name, 'index.html')
            out = open(os.devnull, 'w')
            keep, sys.stdout = sys.stdout, out
            try:
                step3_map.main(out=dst, **kw)
            finally:
                sys.stdout = keep
                out.close()
            html = open(dst, encoding='utf-8').read()
            if name == 'міська':
                city_html = dst
                tochnist_mista = dict(step3_map.LAST_TOCHNIST)
            now[name] = hashlib.sha256(html.encode('utf-8')).hexdigest()[:16]
            for e in check_markup(html):
                problems.append(f'{name}: розмітка — {e}')
            for e in check_js(html, tmp):
                problems.append(f'{name}: JavaScript — {e}')
            print(f'   {len(html)/1048576:.1f} МБ · {now[name]}')
    finally:
        pass

    print('4л. Гістерезис не тримає проблему, чиї події пішли через правила (36.40, S-ПР.13)')
    # Штучна минула збірка: проблема X з двома подіями. Цього разу (1) обидві на
    # місці, але подій замало — гістерезис тримає; (2) одна пішла з даних
    # (стаття поза видами) — не тримає й пише в BEZ_HISTEREZYSU.
    # у main() ім'я problems — список помилок, тож модуль — окремим ім'ям
    import problems as PRH_
    rep_ = PRH_.REPORT
    # звіт — .json.gz, як справжній (histerezys читає саме його)
    PRH_.REPORT = os.path.join(tmp, 'hist_test.json.gz')

    def minula_(d):
        with gzip.open(PRH_.REPORT, 'wt', encoding='utf-8') as fh: json.dump(d, fh)
    minula_(dict(versiia=dict(podii_do='2026-01-01'),
                 perelik=[dict(sim='X', p=[50.4, 30.5], status='хронічна', riven='точка', docs=['a', 'b'])]))
    z1 = [dict(riven='точка', status='мало', sim='X', p=(50.4, 30.5), docs=['a', 'b'], podii=2)]
    z2 = [dict(riven='точка', status='мало', sim='X', p=(50.4, 30.5), docs=['a'], podii=1)]
    t1 = bool(PRH_.histerezys(z1, '2026-02-01', log=lambda *a: None))
    t2 = bool(PRH_.histerezys(z2, '2026-02-01', log=lambda *a: None)) or not PRH_.BEZ_HISTEREZYSU
    # (3) проблему вже тримає гістерезис; її документи — з часу, коли вона
    # була проблемою (стан histerezys), а не слабкі нинішні
    minula_(dict(versiia=dict(podii_do='2026-02-01'),
                 perelik=[dict(sim='X', p=[50.4, 30.5], status='хронічна', riven='точка', docs=['a'])],
                 histerezys=[dict(sim='X', p=[50.4, 30.5], nyzhche_80=0, docs=['a', 'b'])]))
    t3 = bool(PRH_.histerezys(z2, '2026-03-01', log=lambda *a: None))
    PRH_.REPORT = rep_
    t2 = t2 or t3
    print(f'   події на місці — тримає: {"так" if t1 else "НІ"}; подія пішла через правила — не тримає: {"так" if not t2 else "НІ"}')
    if not t1 or t2:
        print('   ПОМИЛКА гістерезис не за 36.40'); return 1

    print('4й. Події без номера будинку — не в точках будинків (S-А.3, Е25 Н1)')
    # Точність кожної події — з геокодера (geo.precision тестової бази), точка
    # — з тієї самої збірки. Центр вулиці збігався з будинком (Електротехнічна,
    # 16), і події без номера ставали подіями будинку.
    import sqlite3
    with sqlite3.connect(TESTDB) as cx_:
        prec_ = dict(cx_.execute('select doc_id, precision from geo'))
    zli_ = [d for d, t in tochnist_mista.items() if t in (1, 2) and prec_.get(d) not in step3_map.POINT]
    print(f'   подій у точках будинків і перехресть: {sum(1 for t in tochnist_mista.values() if t in (1, 2)):,}; '
          f'з точністю «вулиця» серед них: {len(zli_)}')
    if zli_:
        print(f'   ПОМИЛКА події без номера в точці будинку, напр. {zli_[:5]}'); return 1

    print('4. Установи не просочилися на карту')
    # Дві перевірки, бо однієї мало. Перелік виключень — те, що вирішило
    # правило. Підписи точок — те, що врешті побачить людина: одна будівля
    # буває записана і як «9», і як «9А», тож адреса може вилетіти з переліку,
    # а точка лишитися під сусіднім написанням.
    excl_txt = ''
    if os.path.exists(map_excl.EXCL):
        excl_txt = open(map_excl.EXCL, encoding='utf-8').read().lower()
    # Ваш ручний список (vykluchennya_moyi.txt) теж прибирає точки з карти —
    # без нього тут «пропущено» помилково, якщо адреса виключена саме ним,
    # а не автоматикою (знайдено 3 вересня на вул. С. Хороброго, 9).
    if os.path.exists(map_excl.MANUAL):
        excl_txt += '\n' + open(map_excl.MANUAL, encoding='utf-8').read().lower()
    missed = [a for a in NE_MAE_BUTY if a.lower() not in excl_txt]
    leaked = []
    import map_dani
    d_ = map_dani.chytaty(city_html, 'pts') if city_html else None
    if d_:
        addrs = {(p or [None, None, ''])[2] for p in d_['pts']}
        leaked = [a for a in NE_MAE_BUTY if a in addrs]
    else:
        print('   не знайшов перелік точок у сторінці')
    for a in missed: print(f'   ПОМИЛКА не потрапила у виключення: {a}')
    for a in leaked: print(f'   ПОМИЛКА лишилася точкою на карті: {a}')
    if not missed and not leaked:
        print(f'   усі {len(NE_MAE_BUTY)} відомих установ виключено й на карті їх немає')
    if missed or leaked:
        return 1

    print('4б. Суд ↔ район точки (ZAVDANNYA-32, 2.2)')
    # На справжній карті (site/index.html, крок 3 у Actions іде перед
    # перевіркою), а не на тестовій базі: частка незбігу тестової вибірки
    # нічого не каже про живу карту.
    sr = sud_raion(os.path.join(ROOT, 'site', 'index.html')) if os.path.exists(
        os.path.join(ROOT, 'site', 'index.html')) else None
    if sr is None:
        print('   site/index.html немає — пропущено')
    else:
        ch, po_vyd, po_r, pidozr, n_ = sr
        print(f'   незбіг {100 * ch:.1f}% з {n_:,} подій на точних адресах районних судів (межа {100 * SUD_MEZHA:.0f}%)')
        print('   по видах: ' + '; '.join(f'{k} {100 * v:.1f}%' for k, v in sorted(po_vyd.items(), key=lambda x: -x[1])))
        print('   по районах: ' + '; '.join(f'{k} {100 * v:.1f}%' for k, v in sorted(po_r.items(), key=lambda x: -x[1])))
        print(f'   адрес з ≥{SUD_ADRESA_MIN} подіями й незбігом ≥{100 * SUD_ADRESA_CHASTKA:.0f}%: {len(pidozr)} '
              '(кандидати в установи чи однойменні) — data/_check_last.json')
        try:
            st_ = json.load(open(STATE)) if os.path.exists(STATE) else {}
        except Exception:
            st_ = {}
        st_['sud_raion'] = dict(chastka=round(ch, 4), po_vydah=po_vyd, po_raionah=po_r,
                                adresy=[dict(adresa=a, podii=k, nezbig=r) for a, k, r in pidozr])
        json.dump(st_, open(STATE, 'w'), ensure_ascii=False, indent=1)
        if ch > SUD_MEZHA:
            print(f'   ПОМИЛКА незбіг суду й району {100 * ch:.1f}% > {100 * SUD_MEZHA:.0f}%')
            return 1

    print('4в. Точки карти: «база» й «між сусідами» — 0 (S-А.4)')
    # На живій карті (site/index.html після кроку 3 у workflow): тестова база
    # має старе геокодування, на ній «база» ще є.
    sp = os.path.join(ROOT, 'site', 'index.html')
    tk = tochky_karty(sp) if os.path.exists(sp) else None
    if tk is None:
        print('   site/index.html немає — пропущено')
    else:
        # 0 (центр вулиці) — поки лише для вікна пошуку вулиці; прибирається
        # разом із карткою пошуку (S-А.3, етап В) — тоді й тест bez_nomera
        pogani = {k: v for k, v in tk.items() if k in (3, 4)}
        if pogani:
            print(f'   ПОМИЛКА точок «база» (3) / «між сусідами» (4): {pogani}')
            return 1
        print(f'   точок {sum(tk.values()):,}: ' + ', '.join(f'{k}: {v:,}' for k, v in sorted(tk.items())))

    print('4г. Фабули в показі (S-П.8): заглушок 0, шапок і посилань ≤1%')
    sd = os.path.join(ROOT, 'site', 'spravy')
    if not os.path.isdir(sd):
        print('   site/spravy немає — пропущено')
    else:
        n, z, s, p = fabuly_saitu(sd)
        print(f'   фабул {n:,}: із заглушками {z:,}, з шапкою {s:,} ({100 * s / max(n, 1):.2f}%), '
              f'з юридичним посиланням {p:,} ({100 * p / max(n, 1):.2f}%)')
        if z or s > 0.01 * n or p > 0.01 * n:
            print('   ПОМИЛКА фабули в показі не відповідають S-П.8')
            return 1

    print('4а. Шари ризику: PAI на довжину ≥ 3')
    # Шар, гірший за втричі від навмання, на карту не йде (ZAVDANNYA-30, ч. 5).
    # risk.json до перенавчання моделі «разом» PAI на довжину не має — тоді
    # попередження, а не помилка: інакше тиждень без перенавчання не
    # публікувався б зовсім.
    rp = os.path.join(DATA, 'risk.json')
    if os.path.exists(rp):
        lay = json.load(open(rp, encoding='utf-8')).get('layers', {})
        bez = [k for k, v in lay.items() if 'pai' not in v]
        slabki = [f"{k} ({v['pai']})" for k, v in lay.items() if 'pai' in v and v['pai'] < 3]
        for s in slabki: print(f'   ПОМИЛКА шар з PAI на довжину < 3: {s}')
        if bez: print(f'   попередження: {len(bez)} шарів старого формату без PAI на довжину — перенавчіть модель')
        if slabki: return 1
        if not bez: print(f'   усі {len(lay)} шарів — PAI ≥ 3')

    print('4д. Стабільність ризику (S-Р.11): спільних ліній з попередньою збіркою ≥0,7')
    zh = zhakkar(rp) if os.path.exists(rp) else None
    if zh is None:
        print('   попередньої risk.json немає (git недоступний чи файла в HEAD немає) — пропущено')
    elif not zh:
        print('   risk.json не змінився — модель цього разу не перенавчали')
    else:
        slabki = [z for z in zh if z[1] < ZHAKKAR_MIN]
        print('   ' + '; '.join(f'{k} {c:.2f}' for k, c, _z, _n in zh))
        for k, c, zn, no in slabki:
            # жовта, а не червона: перенавчання законно міняє перелік, але
            # людина має бачити, скільки й чому (36.24.2)
            print(f'::warning::ЖОВТА: {k} — спільних {c:.2f} < {ZHAKKAR_MIN}; зникло {zn}, з\'явилось {no}. '
                  'Причина: перенавчання, нові дані чи зміна методики — див. ZMINY-METODYKY.md')

    print('4е. Число проблем (S-ПР.14): карта = «Проблеми» = problems_report')
    # На живій збірці: site/index.html (M.chyslo) і site/problemy.html проти
    # data/problems_report.json.gz — одне джерело, окремо місця, лінії, ділянки
    import problems as PRB_
    rpp = os.path.join(DATA, 'problems_report.json.gz')
    sp_, pp_ = os.path.join(ROOT, 'site', 'index.html'), os.path.join(ROOT, 'site', 'problemy.html')
    if not (os.path.exists(rpp) and os.path.exists(sp_)):
        print('   звіту проблем чи site/index.html немає — пропущено')
    else:
        ch = PRB_.chyslo_problem(json.load(gzip.open(rpp, 'rt', encoding='utf-8')))
        import map_dani
        na_karti = ((map_dani.chytaty(sp_, 'meta') or {}).get('meta') or {}).get('chyslo')
        tekst = PRB_.chyslo_tekst(ch)
        v_zvity = os.path.exists(pp_) and tekst in open(pp_, encoding='utf-8').read()
        print(f'   звіт: {tekst} (+ {ch["dorozhnikh"]} дорожніх ділянок); на карті: {na_karti}; у «Проблемах»: {"так" if v_zvity else "НІ"}')
        if na_karti != ch or (os.path.exists(pp_) and not v_zvity):
            print('   ПОМИЛКА число проблем розходиться між картою, «Проблемами» й звітом')
            return 1
    print('4ж. Кандидати для аналізу фабул (36.37): data/kandydaty.json.gz є, непорожній, ≤20 МБ, ДТП з mitky')
    kp_ = os.path.join(DATA, 'kandydaty.json.gz')
    if not os.path.exists(kp_):
        print('   ПОМИЛКА data/kandydaty.json.gz немає — аналізу в хмарі нічого читати'); return 1
    mb_ = os.path.getsize(kp_) / 1048576
    kd_ = json.load(gzip.open(kp_, 'rt', encoding='utf-8'))
    n_ = len(kd_)
    # аналіз фабул групує ДТП за полем mitky (S-ПР.15) — без нього сценарію не видно
    dtp_ = [x for k in kd_ if k['sim'] == 'ДОР_ДТП' for x in k['podii']]
    bez_m = sum('mitky' not in x for x in dtp_)
    print(f'   {n_:,} пар, {mb_:.1f} МБ; ДТП {len(dtp_):,}, з мітками {sum(bool(x.get("mitky")) for x in dtp_):,}')
    if not n_ or mb_ > 20 or bez_m or not dtp_:
        print(f'   ПОМИЛКА файл кандидатів порожній, понад 20 МБ чи ДТП без поля mitky ({bez_m})'); return 1
    print('4и. Вага першого завантаження (S-Н.5, 36.22): ≤3 МБ розпаковано, ≤1 МБ мережею')
    import map_dani
    if not os.path.exists(sp_):
        print('   site/index.html немає — пропущено')
    else:
        rozp_, mer_, fs_ = map_dani.vaga(sp_)
        print(f'   {rozp_ / 1048576:.2f} МБ розпаковано, {mer_ / 1048576:.2f} МБ мережею (gzip); '
              + ', '.join(f'{n} {b / 1048576:.2f}' for n, b in fs_[:4]))
        if rozp_ > 5 * 1048576 or mer_ > 1048576:
            print('   ПОМИЛКА перше завантаження понад 5 МБ чи понад 1 МБ мережею'); return 1
        if rozp_ > 3 * 1048576:
            print(f'::warning::ЖОВТА: перше завантаження {rozp_ / 1048576:.2f} МБ > 3 МБ; найважчі — '
                  + ', '.join(n for n, _ in fs_[:3]))
    print('4к. Шару «Населення» на карті немає (36.39, S-К.10)')
    if os.path.exists(sp_):
        t_ = open(sp_, encoding='utf-8').read()
        sliv_ = [s for s in ('data-ctx="pop"', "'k-pop'", '>Населення<') if s in t_]
        if 'pop' in (map_dani.perelik(t_) or {}): sliv_.append('dani/pop')
        if sliv_:
            print('   ПОМИЛКА на карті лишився шар «Населення»: ' + ', '.join(sliv_)); return 1
        print('   немає ні перемикача, ні шару, ні файлу')
    print('4з. Атрибуція (S-К.20, S-З.7, S-Б.7): п\'ять джерел і умови OSM')
    import atrybutsiia as ATR_
    bez = []
    sd_ = os.path.join(ROOT, 'site')
    stor = [os.path.join(sd_, 'index.html')] + sorted(glob.glob(os.path.join(sd_, '*.html')))
    for f in dict.fromkeys(stor):
        if not os.path.exists(f) or os.path.basename(f) in ('kyiv.html', 'kyiv-gl.html'): continue
        t = open(f, encoding='utf-8').read()
        # рядок атрибуції карти — у meta (M.atr), а не в самій сторінці (36.22)
        pr_ = map_dani.perelik(t)
        if pr_: t += open(os.path.join(sd_, pr_['meta']), encoding='utf-8').read()
        if '<meta http-equiv="refresh"' in t: continue        # переадресації
        nema = [d for d in ATR_.DZHERELA if d not in t]
        if nema: bez.append(f'{os.path.basename(f)}: немає {", ".join(nema)}')
    fa = sorted(glob.glob(os.path.join(sd_, 'adresy', '*.json')))[:1]
    if fa and ATR_.OSM_COPYRIGHT not in open(fa[0], encoding='utf-8').read(2000): bez.append('adresy/: немає рядка ліцензії')
    if not os.path.exists(os.path.join(ROOT, 'LICENSE-DATA.md')): bez.append('немає LICENSE-DATA.md')
    for b in bez: print('   ПОМИЛКА', b)
    if bez: return 1
    print(f'   на карті, у {len(stor) - 1} сторінках і файлах адрес — усе; LICENSE-DATA.md є')
    print('5. Розмітка і JavaScript')
    if problems:
        for p in problems:
            print('   ПОМИЛКА', p)
        return 1
    print('   чисто')

    print('7. Узгодженість у браузері (S-К.14, 36.23.6): підказка = картка = сума видів, колір, кільця')
    # Справжній браузер на живій збірці: число й колір рахує JS, і лише так
    # видно, чи підказка, картка й карта кажуть одне. Playwright ставить workflow.
    try:
        import test_uzhodzhenist as TU
        import playwright  # noqa: F401
    except ImportError:
        TU = None
    if TU is None or not os.path.exists(os.path.join(ROOT, 'site', 'index.html')):
        print('   Playwright чи site/index.html немає — пропущено')
    elif TU.main(int(os.environ.get('N_UZHODZH', '300'))):
        print('   ПОМИЛКА підказка, картка й карта розходяться')
        return 1

    print('8. Пошук (S-Ш.1, S-Ш.2, S-Ш.5): 143 запити, описки, запити Андрія, час')
    if TU is None or not os.path.exists(os.path.join(ROOT, 'site', 'poshuk.json')):
        print('   Playwright чи site/poshuk.json немає — пропущено')
    else:
        import test_poshuk as TP
        if TP.main():
            print('   ПОМИЛКА пошук не дотягує до меж S-Ш')
            return 1

    shutil.rmtree(tmp, ignore_errors=True)

    print('6. Порівняння з попереднім запуском')
    def zberehty(d):
        try:
            old = json.load(open(STATE)) if os.path.exists(STATE) else {}
        except Exception:
            old = {}
        if 'sud_raion' in old: d = dict(d, sud_raion=old['sud_raion'])
        json.dump(d, open(STATE, 'w'), ensure_ascii=False, indent=1)
    if save:
        zberehty(now)
        print('   еталон збережено')
        return 0
    if not os.path.exists(STATE):
        zberehty(now)
        print('   еталона не було — збережено поточний результат')
        return 0
    before = json.load(open(STATE))
    same = True
    for name, _ in CASES:
        was, is_ = before.get(name), now[name]
        if was == is_:
            print(f'   {name}: без змін')
        else:
            same = False
            print(f'   {name}: ЗМІНИЛАСЯ  було {was}  стало {is_}')
    zberehty(now)
    if same:
        print('\n=== ГОТОВО === результат не змінився')
    else:
        print('\n=== ГОТОВО === результат змінився. Якщо ви лише переставляли\n'
              'код, це помилка. Якщо міняли поведінку — так і має бути.')
    return 0


if __name__ == '__main__':
    sys.exit(main(save='--save' in sys.argv))
