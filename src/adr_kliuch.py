# -*- coding: utf-8 -*-
"""Єдиний ключ адреси — один модуль для геокодера, карти, проблем і пошуку
(SPECYFIKATSIYA S-А.5–6, S-Ш.1; RISHENNYA 36.18.2, 36.18.6, 36.30.6).

«Берковецька, 6-Д» і «6Д», «вул. Братиславська» і «просп. Братиславська»,
«Івана Дзюби» й «І.Дзюби», «Харківське Шосе» й «шосе» — одна будівля, а
на карті це були дві точки: геокодер і карта нормалізували кожен по-своєму.
Тепер нормалізація лише тут; решта модулів викликають її.

Ключ вулиці: назва без типу й без порядку слів, далі за довідником (OSM ∪
КМДА) по черзі:
  1. ключ є в довіднику — він;
  2. перейменування з 1551 («нова (стара)») — лише коли стара назва не
     чинна в OSM: КМДА ще тримає старі назви («проспект Перемоги»), і
     правило «будь-де в довіднику» губило 154 вулиці (Е12б, А3);
  3. ініціали («І.Дзюби») — розгорнути, якщо збіг один;
  4. відмінок → називний («Відрадному» → «Відрадний») — лише якщо такий
     називний є в довіднику: інакше «Верхній Вал» став би «Верхній Вала»;
  5. неповна назва («Заболотного» → «Академіка Заболотного») — лише якщо
     вулиця з усіма цими словами в Києві одна: хибна точка гірша за
     відсутню (36.18.6).
Номер — у верхньому регістрі без дефіса й пробілів.

Довідник перейменувань — з самих даних 1551: там вулиця пишеться «нова
(стара)». Немає 1551 — перейменування просто не застосовуються.
"""
import os, glob, gzip, csv, json, re, itertools, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')

# Тип вулиці вирізаємо лише цілим словом: шаблон без меж слова різав
# «пров» у «Газопровідна» і «наб» у «Набережне» (82 назви, Е12б).
TYPEWORDS = (r'(?<![а-яіїєґ])(вулиця|вулиці|вулицю|вул\.?|проїзд\w*|проспект[уі]?|просп\.?|пр-т|пр\.|'
             r'бульвар[уі]?|бульв\.?|б-р|провулок|провулку|пров\.?|площа|площі|пл\.?|шосе|набережна|'
             r'набережної|наб\.?|узвіз|узвозу|алея|алеї|тупик|тракт|мікрорайон)(?![а-яіїєґ])')


def norm(s):
    """назва вулиці без типу, малими, без розділових знаків"""
    if not s: return ''
    s = s.lower().replace('’', "'").replace('`', "'").replace('ʼ', "'")
    s = re.sub(TYPEWORDS, ' ', s)
    s = re.sub(r"[^а-яіїєґ0-9' \-]", ' ', s)
    s = s.replace('-', ' ').replace("'", '')
    return re.sub(r'\s+', ' ', s).strip()


def skey(s):
    """Ключ вулиці без порядку слів: у геокодері «Корольова Академіка», у
    текстах і в OSM — «Академіка Корольова»."""
    return ' '.join(sorted(norm(s).split()))


def nh(h):
    """номер будинку: «6-Д», «6 д», «6Д» — один ключ"""
    if not h: return ''
    h = h.upper().replace(' ', '').replace('\\', '/')
    return re.sub(r'[^0-9A-ZА-Я/]', '', h)


# Закінчення місцевого й родового відмінків -> можливі називні. Перевіряється
# лише довідником: варіант, якого немає серед чинних назв, не береться.
ZAKIN = [('ській', ('ська',)), ('цькій', ('цька',)), ('зькій', ('зька',)), ('ній', ('на', 'ня')),
         ('ій', ('а', 'я')), ('ському', ('ський', 'ське')), ('цькому', ('цький', 'цьке')),
         ('ому', ('ий', 'е', 'ій')), ('ім', ('ий',)), ('ці', ('ка',)), ('зі', ('га',)), ('сі', ('ха',)),
         ('ської', ('ська',)), ('цької', ('цька',)), ('ної', ('на',)), ('ої', ('а',)),
         ('і', ('а', 'я'))]


def nazyvni(k, full):
    """ключ (слова за абеткою) -> варіанти в називному, що є в довіднику"""
    if k in full: return []
    ch = []
    for w in k.split():
        v = [w]
        for z, nz in ZAKIN:
            if w.endswith(z) and len(w) > len(z) + 2:
                v += [w[:-len(z)] + e for e in nz]; break
        ch.append(v)
    out = []
    for comb in itertools.product(*ch):
        nn = ' '.join(sorted(comb))
        if nn != k and nn in full and nn not in out: out.append(nn)
    return out


class Kliuch:
    def __init__(s, data=DATA):
        s.full_osm, s.full_kmda = set(), set()
        kmda = os.path.join(data, 'geokoder_kmda.csv.gz')
        if os.path.exists(kmda):
            with gzip.open(kmda, 'rt', encoding='utf-8', newline='') as fh:
                for r in csv.DictReader(fh, delimiter='\t'):
                    s.full_kmda.add(skey(r['street']))
        osm = os.path.join(data, 'osm_kyiv_city.json')
        if os.path.exists(osm):
            for r in json.load(open(osm, encoding='utf-8')):
                s.full_osm.add(skey(r[0]))
        s.full_osm.discard(''); s.full_kmda.discard('')
        s.full = s.full_osm | s.full_kmda
        # слово -> повні назви з ним: для ініціалів і неповних назв
        s.by_word = collections.defaultdict(set)
        for k in s.full:
            for w in k.split():
                if len(w) > 2: s.by_word[w].add(k)
        s.rename = {}
        for f in sorted(glob.glob(os.path.join(data, '1551', 'lichylnyky-*.tsv.gz'))):
            with gzip.open(f, 'rt', encoding='utf-8', newline='') as fh:
                for r in csv.DictReader(fh, delimiter='\t'):
                    m = re.match(r'^(\S+)\s+(.+?)\s*\((.+)\)\s*$', r.get('vulytsya') or '')
                    if not m: continue
                    new, old = skey(f'{m.group(1)} {m.group(2)}'), skey(f'{m.group(1)} {m.group(3)}')
                    if old and new and old != new and old not in s.full_osm:
                        s.rename[old] = new
        s._c = {}

    def rozibraty(s, street):
        """(ключ вулиці, правило). Правило — котре зіставило: '' (ключ є в
        довіднику як є), 'перейменування', 'ініціали', 'відмінок', 'неповна
        назва'; None — у довіднику не знайдено (ключ тоді — як є)."""
        if street in s._c: return s._c[street]
        k = skey(street); pr = None
        if k in s.full: pr = ''
        elif k in s.rename and s.rename[k] in s.full: k, pr = s.rename[k], 'перейменування'
        else:
            ws = k.split()
            ini = [w for w in ws if len(w) <= 2]
            rest = [w for w in ws if len(w) > 2]
            if ini and rest:
                c_ = set.intersection(*(s.by_word.get(w, set()) for w in rest))
                c_ = [c for c in c_ if len(c.split()) == len(ws)
                      and all(any(x.startswith(i) and len(x) > 2 for x in c.split()) for i in ini)]
                if len(c_) == 1: k, pr = c_[0], 'ініціали'
            if pr is None:
                kn = nazyvni(k, s.full)
                if len(kn) == 1: k, pr = kn[0], 'відмінок'
            # ініціал у тексті має бути початком слова назви: інакше «Л.України»
            # ставало «Кубанської України» замість Лесі Українки (50 очима, 39)
            # (лише однолітерний: «Ак.», «Ген.» — скорочені звання, у назві їх
            # буває немає — «вул. Ак. Щусєва» це «вулиця Щусєва»)
            pidkh = lambda c: all(any(x.startswith(i) for x in c.split()) for i in ini if len(i) == 1)
            if pr is None and rest:
                # усі змістовні слова тексту — в одній-єдиній назві довідника
                c_ = {c for c in set.intersection(*(s.by_word.get(w, set()) for w in rest)) if pidkh(c)}
                if len(c_) == 1: k, pr = next(iter(c_)), 'неповна назва'
                else:
                    # слово з опискою («Олесі Гончара», «Роналльда Рейгана») не
                    # трапляється в жодній назві — не зважаємо на нього, якщо
                    # решта (хоч одне слово від 5 літер) вказує на одну вулицю.
                    # Раніше це робив «хвостовий» збіг за останнім словом, але
                    # без вимоги, щоб відомі слова збігалися всі.
                    vidomi = [w for w in rest if w in s.by_word]
                    # «вул. Здолбунівської та вул. Харківське шосе» — дві вулиці,
                    # «невідоме» слово тут — інша вулиця, а не описка
                    dvi = re.search(r'\s(та|і|й)\s+(вул|просп|бульв|пров|пл|шосе|наб|узв)', (street or '').lower())
                    if vidomi and not dvi and len(vidomi) < len(rest) and max(map(len, vidomi)) >= 5:
                        c_ = {c for c in set.intersection(*(s.by_word[w] for w in vidomi)) if pidkh(c)}
                        if len(c_) == 1: k, pr = next(iter(c_)), 'неповна назва (описка)'
        s._c[street] = (k, pr)
        return k, pr

    def vulytsia(s, street):
        return s.rozibraty(street)[0]

    def __call__(s, street, house):
        """(ключ вулиці, номер) або None, якщо номера немає"""
        if not street or not house: return None
        return (s.vulytsia(street), nh(house))
