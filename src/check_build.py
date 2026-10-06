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
import os, sys, gzip, json, shutil, hashlib, tempfile, subprocess, py_compile, re

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
    m = re.search(r'<script>\n(.*)\n</script>', html, re.S)
    if not m:
        return ['не знайдено <script> у сторінці']
    jsf = os.path.join(tmp, 'x.js')
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
    import collections
    html = open(html_path, encoding='utf-8').read()
    m_ = re.search(r'const M=(\{.*?\}), P=(\[.*?\]);\n', html, re.S)
    if not m_: return None
    M, P = json.loads(m_.group(1)), json.loads(m_.group(2))
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

    CASES = [('міська', dict(district=None)),
             ('районна', dict(district='Деснянський'))]

    now, problems, city_html = {}, [], ''
    try:
        for name, kw in CASES:
            print(f'3. Збірка: {name}')
            dst = os.path.join(tmp, f'{name}.html')
            out = open(os.devnull, 'w')
            keep, sys.stdout = sys.stdout, out
            try:
                step3_map.main(out=dst, **kw)
            finally:
                sys.stdout = keep
                out.close()
            html = open(dst, encoding='utf-8').read()
            if name == 'міська': city_html = html
            now[name] = hashlib.sha256(html.encode('utf-8')).hexdigest()[:16]
            for e in check_markup(html):
                problems.append(f'{name}: розмітка — {e}')
            for e in check_js(html, tmp):
                problems.append(f'{name}: JavaScript — {e}')
            print(f'   {len(html)/1048576:.1f} МБ · {now[name]}')
    finally:
        pass

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
    m_ = re.search(r'const M=.*?, P=(\[.*?\]);\n', city_html or '', re.S)
    if m_:
        addrs = {(p or [None, None, ''])[2] for p in json.loads(m_.group(1))}
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
    print('5. Розмітка і JavaScript')
    if problems:
        for p in problems:
            print('   ПОМИЛКА', p)
        return 1
    print('   чисто')

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
