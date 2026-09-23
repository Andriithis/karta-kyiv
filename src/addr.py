# -*- coding: utf-8 -*-
import re

TYPES = [
 (r'вул(?:иц[іяею])?\.?', 'вул.'),
 # «пр-т», «пр-ту», «бул.» — так пишуть у протоколах; без них «бул.Чоколівський,
 # 19» не знаходився зовсім (вибірка 23.09, ZVIT-TEKSTY-1.md, №3)
 (r'просп(?:ект[уі]?)?\.?|пр-т\w*\.?', 'просп.'),
 (r'бульв(?:ар[уі]?)?\.?|б-р\.?|бул\.', 'бульв.'),
 (r'пров(?:улок|улку|\.)?', 'пров.'),
 (r'площ[аіі]|пл\.', 'пл.'),
 (r'шосе', 'шосе'),
 (r'наб(?:ережн\w*)?\.?', 'наб.'),
 (r'узвіз|узвозу', 'узвіз'),
 (r'алея|алеї', 'алея'),
 (r'мікрорайон|м-н', 'мкр.'),
]
TYPE_RE = '(?:' + '|'.join(t for t,_ in TYPES) + ')'
NAME = r"[А-ЯІЇЄҐ][А-Яа-яІіЇїЄєҐґ'`’\-\s\.]{1,40}?"
# Літера-індекс і через дефіс: «1-Б», «20-Д». Без дефіса в шаблоні «шосе
# Столичному, 1-Б» давало будинок «1» — інший будинок.
HOUSE = r"(\d{1,4}\s*(?:[-/]\s*\d{1,3})?\s*(?:-?\s*[А-ЯA-Za-zа-я])?)"

# variant A: type before name   "вул. Лугова, 16"
PA = re.compile(rf"\b({TYPE_RE})\s*({NAME})[,\s]+(?:буд(?:инок|\.)?\s*)?№?\s*{HOUSE}\b", re.U)
# variant B: name before type   "Дніпровська набережна, буд. 33"
PB = re.compile(rf"\b({NAME})\s+(вулиц[іяею]|проспект[уі]?|бульвар[уі]?|провулок|провулку|набережн\w+|площ[аіі]|шосе|узвіз)[,\s]+(?:буд(?:инок|\.)?\s*)?№?\s*{HOUSE}\b", re.U)
# street only, no house
PS = re.compile(rf"\b({TYPE_RE})\s*({NAME})(?=[,\.\s])", re.U)

TIME = re.compile(r"(?:о|близько|приблизно|орієнтовно)?\s*(\d{1,2})\s*(?:год|:)\s*(\d{2})?", re.U)
# Слова перед адресою, що виказують чуже місце: установу, житло учасника,
# лікарню, куди доставили потерпілого, експертизу. Друга половина переліку —
# з діагнозу 22.09 (ZAVDANNYA-ADRESY.md, п.4): саме ці адреси лікарень і
# бюро збирали на себе чужі події. «проживає» розширено до «прожива», бо
# «проживаючого за адресою» трапляється не рідше. Реєстрація — лише «місце
# реєстрації»: голе «реєстрац» глушило «реєстраційний номер» автомобіля, що
# стоїть у кожному описі ДТП перед місцем.
NOISE = re.compile(r"(суд|прокурат|поліці|управлінн|відділ|райвідділ|адвокат|канцеляр|"
                   r"прожива|зареєстрован|місц\w*\s+реєстрац|мешка|місце проживання|УПП|ГУ\s?НП|РУП|майданчик|"
                   r"лікарн|госпітал|травмпункт|експерт|НДЕКЦ|СІЗО|ізолятор|огляд|"
                   r"доставлен|морг|бюро)", re.I|re.U)
# «огляд місця події» — не лікарняний огляд, а саме місце події; його слова
# «огляд» не повинно глушити.
NOISE_OK = re.compile(r"огляд\w*\s+місц\w*\s+(?:події|пригоди|ДТП)", re.I|re.U)
STOP = {'києва','київ','києві','україни','район','районного','районний','місто','міста'}

# ---- НАЗВА З ДАВАЛЬНОГО ВІДМІНКА ----
# «по вул. Діловій», «по шосе Столичному», «по просп. Литовському» — у
# протоколах назва стоїть у давальному чи місцевому відмінку, а в адресній
# базі OSM — у називному, і такі адреси не геокодувалися. Зводимо лише
# прикметникові закінчення (-ій жіночого роду, -ому чоловічого й середнього)
# і лише після прикметникового суфікса: «Наталії Ужвій» — прізвище, його не
# чіпаємо. Родовий («Ярослава Мудрого», «Марини Цвєтаєвої») — теж ні: це і є
# назва вулиці.
_ADJ = r"(?:ськ|цьк|зьк|ов|ев|єв|ів|їв|ин|ін|їн|ичн|ічн|альн|ьн|ен|ан|ян|к)"
_GENDER = {'вул.': 'f', 'наб.': 'f', 'пл.': 'f', 'алея': 'f', 'шосе': 'n'}


def nominative(t, n):
    g = _GENDER.get(t, 'm')

    def one(m):
        stem, end = m.group(1), m.group(2)
        if end == 'ій' and g == 'f':
            return stem + 'а'
        if end == 'ому':
            return stem + ('е' if g == 'n' else 'ий')
        return m.group(0)
    return re.sub(rf"\b([А-ЯІЇЄҐ][а-яіїєґ'’]*{_ADJ})(ій|ому)\b", one, n)


def norm_street(t, n):
    n = re.sub(r'\s+', ' ', n).strip(" ,.-'`’")
    n = re.sub(r'\s*(м\.?\s*Києв\w*|міста Києва|Київ\w*)\s*$', '', n, flags=re.I).strip()
    for pat, canon in TYPES:
        if re.fullmatch(pat, t, re.U): t = canon; break
    return t, nominative(t, n)

def norm_house(h):
    h = re.sub(r'\s+', '', h).upper().strip('.,')
    # "буд. 6 у м. Києві" -> парсер ловить "6У"; літера У як індекс будинку не вживається
    h = re.sub(r'У$', '', h)
    # провідні нулі: "04" -> "4"
    h = re.sub(r'^0+(\d)', r'\1', h)
    return h or None

def find_all(text):
    """returns list of (street_type, street_name, house|None, position)"""
    out = []
    for m in PA.finditer(text):
        t, n = norm_street(m.group(1), m.group(2))
        if not n or n.lower() in STOP or len(n) < 3: continue
        out.append((t, n, norm_house(m.group(3)), m.start()))
    for m in PB.finditer(text):
        raw_t = m.group(2)
        t = ('наб.' if 'абережн' in raw_t else 'вул.' if 'улиц' in raw_t
             else 'просп.' if 'роспект' in raw_t else 'бульв.' if 'ульвар' in raw_t
             else 'пров.' if 'ровул' in raw_t else 'пл.' if 'лощ' in raw_t
             else 'шосе' if 'шосе' in raw_t else 'узвіз')
        n = re.sub(r'\s+',' ',m.group(1)).strip(" ,.-'`")
        if not n or n.lower() in STOP or len(n) < 3: continue
        out.append((t, nominative(t, n), norm_house(m.group(3)), m.start()))
    return out

def context_ok(text, pos, win=170, floor=0):
    """чи немає перед адресою слів, що виказують адресу установи.
    `floor` не дає вікну зазирнути в шапку: слова «суд», «прокуратура»
    там стоять завжди й не стосуються адреси, названої вже у фабулі."""
    seg = NOISE_OK.sub(' ', text[max(floor, pos-win):pos])
    return not NOISE.search(seg)

# Фабула починається після слова ВСТАНОВИВ. Усе, що ДО нього, — шапка:
# назва суду, склад суду й АДРЕСА ПРИМІЩЕННЯ СУДУ. Саме звідти бралася
# адреса у 63% кримінальних справ (у КУпАП — лише 3,5%, бо там місце
# вчинення названо в самому протоколі).
BODY = re.compile(r'(?:в|у)\s*с\s*т\s*а\s*н\s*о\s*в\s*и\s*(?:в|л[аио])\s*[:,\.]?', re.I|re.U)

def body_start(text):
    """позиція, з якої починається опис події; 0 — якщо маркера немає"""
    best = None
    for m in BODY.finditer(text):
        # маркер-заголовок: з нового рядка або з двокрапкою після
        head = (m.start() == 0 or text[m.start()-1] in '\n\r\t ')
        colon = m.group(0).rstrip().endswith(':')
        if head and colon: return m.end()
        if best is None: best = m.end()
    return best or 0

# ---- МІСЦЕ БЕЗ НОМЕРА: вулиця, перехрестя, знеособлена адреса ----
# Назва вулиці — підряд слова з великої літери: «Г. Хоткевича», «Героїв
# Сталінграду». Регулярний вираз NAME тут не годиться: він лінивий і
# обриває «Героїв Сталінграду» на першому слові.
_TYPE_AT = re.compile(rf"\b({TYPE_RE})\s*(?=[А-ЯІЇЄҐ])", re.U)
_WORD = re.compile(r"[А-ЯІЇЄҐ][А-Яа-яІіЇїЄєҐґ'`’\-]*\.?", re.U)
CROSS = re.compile(r"перехрест\w*\s+(?:(?:вулиць|вулиці|вул\.)\s*)?", re.I | re.U)
CROSS_JOIN = re.compile(rf"\s*(?:та|і|й|з|із|–|—|-|/)\s*(?:({TYPE_RE})\s*)?", re.U)
HIDDEN = re.compile(r"АДРЕСА_\d+", re.U)
# Номер ПЕРЕД вулицею: «біля буд. № 23 по вул. Юрія Клена», «навпроти
# будинку №7/20 по вул. Шолом-Алейхема». В описах подій це найчастіший
# зворот, а PA/PB його не бачать. Між номером і вулицею — до 60 знаків без
# цифр і крапки з комою: «будинком №19, що розташований за адресою: вул. …».
# Літера-індекс лише впритул і не початок слова: «5 по вул.» — не «5П».
_HOUSE_PH = r"(\d{1,4}(?:\s*[-/]\s*\d{1,3})?(?:-?[А-Яа-яA-Za-z](?![А-Яа-яA-Za-z]))?)"
PH = re.compile(rf"\bбуд(?:ин\w*|\.)?\s*№?\s*{_HOUSE_PH}[^\d;]{{0,60}}?\b({TYPE_RE})\s*(?=[А-ЯІЇЄҐ])", re.U)
# Скорочення, після яких крапка не кінчає речення: «м. Києві», «буд. 5».
ABBR = {'м', 'вул', 'просп', 'бульв', 'пров', 'наб', 'пл', 'буд', 'кв', 'обл',
        'смт', 'с', 'ст', 'ч', 'п', 'р', 'год', 'хв', 'грн', 'тис', 'див', 'б-р', 'м-н'}


def street_name(text, pos):
    """Назва вулиці з великої літери, що починається з pos; (назва, кінець)."""
    words, end = [], pos
    while len(words) < 4:
        m = _WORD.match(text, end)
        if not m:
            break
        w = m.group(0)
        core = w.rstrip('.')
        # ОСОБА_1, АДРЕСА_1 і подібне — не частина назви
        if len(core) >= 3 and core.isupper():
            break
        words.append(w); end = m.end()
        # крапка після повного слова — кінець речення, не ініціал
        if w.endswith('.') and len(core) > 2:
            break
        # після ініціала пробілу може й не бути: «пр-т С.Бандери»
        initial = w.endswith('.') and len(core) <= 2
        sp = re.match(r"[ \t]*" if initial else r"[ \t]+", text[end:])
        if not sp:
            break
        end += sp.end()
    name = ' '.join(words).strip(" ,.-'`’")
    return name, end


def _street(t, n):
    t, n = norm_street(t, n)
    return f"{t} {n}" if n and n.lower() not in STOP and len(n) >= 3 else None


def mentions(text, floor):
    """Усі згадки місця після floor: (позиція, рівень, вулиця, будинок).

    Рівні: house — вулиця з номером; cross — перехрестя двох вулиць;
    street — вулиця без номера; hidden — знеособлена адреса АДРЕСА_N.
    Згадки з «брудним» контекстом (установа, житло, лікарня) відкинуто."""
    out = []
    # Слово-шум стосується найближчої адреси після нього: «проживаючий за
    # адресою: АДРЕСА_1, … по вул. Хрещатик керував» — житло тут АДРЕСА_1,
    # а Хрещатик — місце події. Тому вікно контексту починається після
    # кінця попередньої адреси, а не за 170 знаків назад.
    ends = sorted([m.end() for m in PA.finditer(text)] + [m.end() for m in PB.finditer(text)]
                  + [m.end() for m in HIDDEN.finditer(text)]
                  + [street_name(text, m.end())[1] for m in _TYPE_AT.finditer(text)])

    def clean(p):
        prev = [e for e in ends if e <= p]
        return context_ok(text, p, floor=max(floor, prev[-1] if prev else 0))

    houses = {c[3] for c in find_all(text)}
    for t, n, h, p in find_all(text):
        if p >= floor and h and clean(p):
            out.append((p, 'house', f"{t} {n}", h))
    for m in PH.finditer(text, floor):
        n, _e = street_name(text, m.end())
        s, h = _street(m.group(2), n), norm_house(m.group(1))
        if s and h and clean(m.start()):
            out.append((m.start(), 'house', s, h))
    for m in CROSS.finditer(text, floor):
        p = m.start()
        if not clean(p):
            continue
        t1 = re.match(rf"({TYPE_RE})\s*", text[m.end():])
        a0 = m.end() + (t1.end() if t1 else 0)
        n1, e1 = street_name(text, a0)
        j = CROSS_JOIN.match(text, e1)
        if not (n1 and j):
            continue
        n2, _e2 = street_name(text, j.end())
        s1 = _street(t1.group(1) if t1 else 'вул.', n1)
        s2 = _street(j.group(1) or 'вул.', n2) if n2 else None
        if s1 and s2:
            out.append((p, 'cross', f"{s1} / {s2}", None))
    for m in _TYPE_AT.finditer(text, floor):
        p = m.start()
        # «вийде на вулицю. Іван сказав» — повне слово з крапкою кінчає
        # речення, а не скорочує тип вулиці, як «вул.» чи «просп.»
        if m.group(1).endswith('.') and len(m.group(1)) > 6:
            continue
        if p in houses or not clean(p):
            continue
        n, _e = street_name(text, m.end())
        s = _street(m.group(1), n)
        if s:
            out.append((p, 'street', s, None))
    for m in HIDDEN.finditer(text, floor):
        if clean(m.start()):
            out.append((m.start(), 'hidden', None, None))
    return sorted(out, key=lambda x: x[0])


def sentence_end(text, pos, cap=400):
    """Кінець речення, в якому стоїть pos."""
    lim = min(len(text), pos + cap)
    for m in re.finditer(r"\.\s+(?=[А-ЯІЇЄҐ])|;|\n", text[pos:lim]):
        if m.group(0).startswith('.'):
            w = re.search(r"([\w\-]+)$", text[pos:pos + m.start()])
            if w and (w.group(1).lower() in ABBR or len(w.group(1)) <= 1):
                continue
        return pos + m.start()
    return lim


# Порядок переваги ВСЕРЕДИНІ речення, де вперше названо місце.
RANK = {'house': 0, 'cross': 1, 'street': 2, 'hidden': 3}


def extract(text):
    """Місце події: dict(street, house, level, time).

    level: house | cross | street | hidden | none.

    ПРАВИЛО (ZAVDANNYA-ADRESY.md, п.3). Місце події — ПЕРША чиста згадка
    місця в описі події (після ВСТАНОВИВ), а не перша адреса з номером.
    Раніше функція шукала саме номер і, коли в описі стояло «на перехресті»
    чи «по вул. Х» без номера, «провалювалася» далі по тексту — до адреси
    лікарні, експертизи, будь-чиєї. Так вул. Братиславська, 3 (лікарня)
    збирала на себе чужі ДТП. Це той самий клас помилки, що й адреса суду в
    шапці нижче, і правило одне: не брати адресу, якої в описі події немає.

    У реченні першої згадки номер, якщо він там є, важить більше: «по вул.
    Х, біля буд. 5 по вул. Х» — це будинок 5. Далі за це речення не йдемо.

    Знеособлена адреса (АДРЕСА_N) — відповідь 22.09, п.2: номер з іншого
    місця тексту не брати; вулицю в тому самому реченні названо — street;
    інакше hidden, «місце приховане», на карту як точна не йде.

    Відоме обмеження: нові правила діють лише на тексти, завантажені після
    цієї зміни. Наявні події отримають їх у повторному проході по текстах
    (крок 6 «Порядку», черга — там само)."""
    bs = body_start(text)
    ms = mentions(text, bs)
    if not ms and bs:
        # Опису не знайшлося — шукаємо по всьому тексту. Шапка з адресою суду
        # тут не загроза: її відсіює той самий контекст («суд»).
        #
        # Свідомо НЕ повертаємось до відкинутих кандидатів. Колись тут стояло
        # `pool = good if good else cands`, і коли чистих не було, функція
        # віддавала адресу суду з позначкою level='house' — тобто вигадувала
        # місце події. Краще чесне «адреси немає», ніж хибна точність.
        ms = mentions(text, 0)
    if not ms:
        return dict(street=None, house=None, level='none', time=None, pos=None)
    p0 = ms[0][0]
    end = sentence_end(text, p0)
    same = [m for m in ms if m[0] <= end]
    p, lvl, st, h = min(same, key=lambda m: (RANK[m[1]], m[0]))
    # pos — де саме в тексті названо місце: прохід по текстах (крок 6) бере
    # звідси речення адреси, щоб було видно, з чого її взято
    return dict(street=st, house=h, level=lvl, time=find_time(text, p), pos=p)


def sentence_start(text, pos, cap=400):
    """Початок речення, в якому стоїть pos (дзеркало sentence_end)."""
    lo = max(0, pos - cap)
    best = lo
    for m in re.finditer(r"\.\s+(?=[А-ЯІЇЄҐ])|;|\n", text[lo:pos]):
        if m.group(0).startswith('.'):
            w = re.search(r"([\w\-]+)$", text[lo:lo + m.start()])
            if w and (w.group(1).lower() in ABBR or len(w.group(1)) <= 1):
                continue
        best = lo + m.end()
    return best

def find_time(text, pos=None):
    seg = text[max(0,(pos or 0)-320):(pos or 0)+120] if pos else text[:2500]
    best=None
    for m in re.finditer(r"(?:о|близько|приблизно|орієнтовно)\s*(\d{1,2})\s*(?:год|:)\s*(\d{2})?", seg, re.U):
        hh=int(m.group(1)); mm=int(m.group(2) or 0)
        if 0<=hh<=23 and 0<=mm<=59: best=f"{hh:02d}:{mm:02d}"
    return best
