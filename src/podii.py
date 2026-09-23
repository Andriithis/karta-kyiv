# -*- coding: utf-8 -*-
"""Що рахується подією (RISHENNYA, розд. 19; ZAVDANNYA-ADRESY.md, п.1).

Подія — лише рішення по суті: вирок (ККУ) чи постанова (КУпАП). Ухвала про
запобіжний захід, про призначення засідання, про надходження обвинувального
акта події не описує; екстрактор брав з неї першу-ліпшу адресу з номером —
установи, учасника, будь-чого. Ухвали лишаються для панелі рішень адреси,
але в підрахунок подій не йдуть.

Одне місце для карти (step3_map), моделі (step4_engine), звітів (step6_base)
і діагностики: розійдися правило між ними — карта й модель рахували б різне.
"""
import os, re, sys, csv, gzip, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
FORMY = os.path.join(DATA, 'formy.csv.gz')

# Коди з довідника judgment_forms.csv дампу ЄДРСР (data/formy_dovidnyk.csv):
# 1 — вирок, 2 — постанова, 5 — ухвала.
EVENT_FORMS = {'1', '2'}

# ---- ЗАПАСНИЙ ШЛЯХ: маркери в тексті ----
# Лише для документів, яких немає у formy.csv.gz. Маркери помиляються в обидва
# боки, і це перевірено на вибірці 22.09: вони пропускають ухвали, що
# починаються з «У провадженні», «знаходиться», «клопотання прокурора про
# закриття», і водночас ловлять вироки — у спрощеному провадженні (ст. 302
# КПК) і вироки з розділом «Історія провадження» теж починаються з «надійшов
# обвинувальний акт». Тому основний шлях — форма рішення з дампу.
#
# Відоме обмеження: маркери дивляться на фабулу, а вона обрізана до 600
# знаків (MAXLEN у step1b_fabula). Повторний прохід по текстах — крок 6
# «Порядку».
PROC_MARK = [
    r'(?:в|у)\s+(?:провадженні|проваджені)\b.{0,160}?(?:перебува|знаходиться)',
    r'(?:в|у)\s+\w+\s+районному\s+суді\b.{0,120}?перебува',
    r'на\s+розгляді\b.{0,160}?перебува',
    r'надійш(?:ов|ло|ли)\b.{0,160}?обвинувальн',
    r'обвинувальн\w*\s+акт\w*\b.{0,80}?надійш',
    r'вступн\w*\s+(?:та|і)\s+резолютивн',
]
PROC_RE = [re.compile(p, re.I | re.S) for p in PROC_MARK]
PROC_WINDOW = 250          # ухвала починається з цих слів; в описі події вони хіба далі
SIMPL = re.compile(r'спрощен\w*\s+провадж', re.I)


def load_formy():
    """doc_id -> код форми рішення; порожньо, якщо файлу ще немає."""
    if not os.path.exists(FORMY):
        return {}
    with gzip.open(FORMY, 'rt', encoding='utf-8', newline='') as fh:
        rd = csv.reader(fh, delimiter='\t'); next(rd, None)
        return {r[0]: r[1] for r in rd if len(r) >= 2}


# ---- ПОСИЛАННЯ НА РІШЕННЯ Й НОМЕРИ СПРАВ МИНУЛИХ РОКІВ ----
# Номер справи й посилання на текст є лише в дампі ЄДРСР (kyiv_*.csv). У
# GitHub Actions ці файли між запусками не живуть: крок 0 качає дамп лише
# поточного року. Тож на сайті в панелі для справ 2024–2025 не було ні
# посилань, ні номерів (перевірено 23.09: 17 із 6 012 справ 2024 року).
# Минулі роки крок 0 кладе сюди — по файлу на рік дампу, щоб щомісячне
# оновлення минулого року не переписувало решту історії.
POSYL = os.path.join(DATA, 'posylannya')

# Усі посилання починаються однаково: .../files/XX/<32 шістнадцяткові>.rtf.
# Зберігаємо лише XX і хеш — решту складає сторінка. Це 34 знаки замість 70.
_REF = re.compile(r'/files/(\w{2})/([0-9a-f]{32})\.rtf$')


def docref(url):
    m = _REF.search(url or '')
    return (m.group(1) + m.group(2)) if m else ''


def load_links():
    """doc_id -> (номер справи, посилання) з data/posylannya/<рік>.csv.gz."""
    out = {}
    if not os.path.isdir(POSYL):
        return out
    for fn in sorted(os.listdir(POSYL)):
        if not fn.endswith('.csv.gz'): continue
        with gzip.open(os.path.join(POSYL, fn), 'rt', encoding='utf-8', newline='') as fh:
            rd = csv.reader(fh, delimiter='\t'); next(rd, None)
            for r in rd:
                if len(r) >= 3: out[r[0]] = (r[1], r[2])
    return out


def load_fab(conn=None):
    """doc_id -> фабула. Спершу таблиця fab у базі (вона є там, де працював
    крок 1b), інакше знімок data/fabuly.csv.gz — так у GitHub Actions, де
    база збирається наново без витягів. Потрібна лише для запасного шляху."""
    if conn is not None and conn.execute(
            "SELECT name FROM sqlite_master WHERE name='fab'").fetchone():
        fab = {r[0]: r[1] for r in conn.execute("SELECT doc_id, txt FROM fab WHERE txt<>''")}
        if fab:
            return fab
    snap = os.path.join(DATA, 'fabuly.csv.gz')
    if not os.path.exists(snap):
        return {}
    with gzip.open(snap, 'rt', encoding='utf-8', newline='') as fh:
        rd = csv.reader(fh, delimiter='\t'); next(rd, None)
        return {r[0]: r[1] for r in rd if len(r) >= 2 and r[1]}


def procedural_text(fab):
    """Чи схожа фабула на процесуальний документ (лише запасний шлях)."""
    if not fab:
        return False
    start = fab[:PROC_WINDOW]
    return any(r.search(start) for r in PROC_RE) and not SIMPL.search(fab)


def is_event(doc_id, fab, formy):
    """Чи рахувати документ подією. Форма з дампу — головна; маркери — лише
    коли форми немає."""
    code = formy.get(str(doc_id))
    if code:
        return code in EVENT_FORMS
    return not procedural_text(fab)


def source(doc_id, formy):
    """Звідки взято рішення — для звітів: 'форма' чи 'маркери'."""
    return 'форма' if formy.get(str(doc_id)) else 'маркери'


# ---- КЛАС АДРЕСИ (ZAVDANNYA-ADRESY.md, п.5; POMYLKA-ADRES.md) ----
# B — вулицю адреси названо в описі події, адресі можна вірити;
# C — опис є, а вулиці в ньому немає: екстрактор міг узяти чужу адресу;
# D — опису немає, перевірити нічим.
# A (ухвала) на карту вже не потрапляє — коміт 1.
#
# Відоме обмеження: опис обрізано до 600 знаків (MAXLEN у step1b_fabula),
# тож межа між B і C тримається на обрізку. Повторний прохід по текстах —
# крок 6 «Порядку».
STREET_TYPES = r'^(?:вул|вулиця|просп|проспект|бульв|бульвар|пл|площа|пров|провулок|' \
               r'наб|набережна|шосе|узвіз|туп|тупик|алея|дорога|майдан|проїзд)\.?\s+'
# Службові слова назви — не ознака конкретної вулиці: «Героїв» є в десятку назв.
STREET_STOP = {'вулиця', 'вулиці', 'проспект', 'бульвар', 'площа', 'провулок', 'шосе',
               'академіка', 'героїв', 'гетьмана', 'генерала', 'маршала', 'полку', 'дорога',
               'набережна', 'київська', 'києва', 'міста', 'сім', 'року'}


def _norm(s):
    return re.sub(r"['’ʼ`«»\"]", '', (s or '').lower())


def street_stems(street):
    """Основи слів назви вулиці, за якими її можна знайти у відмінках."""
    name = re.sub(STREET_TYPES, '', _norm(street).strip())
    words = [w for w in re.findall(r'[а-яіїєґa-z]+', name) if len(w) >= 4 and w not in STREET_STOP]
    # основа — без останніх двох літер: «Берестейський» -> «берестейсь»
    # ловить і «Берестейському», і «Берестейського»
    return [w[:max(4, len(w) - 2)] for w in words]


def addr_class(fab, street, level=None):
    """Клас адреси події, що вже є рішенням по суті: 'B', 'C' чи 'D'.

    Знеособлена адреса (АДРЕСА_N, level='hidden') — D «місце приховане»
    (рішення 22.09, п.2): вулиці в описі немає, перевіряти нічим, хоч опис і є.
    Раніше такі події діставали C, ніби адреса була, але чужа."""
    if not fab or level == 'hidden':
        return 'D'
    stems = street_stems(street)
    return 'B' if stems and any(s in _norm(fab) for s in stems) else 'C'


# ---- ОДНА СПРАВА — ОДНА ПОДІЯ (ZAVDANNYA-ADRESY.md, п.2; відповідь 3) ----
# Ключ — (справа, вид подій), а не (справа, стаття) і не сама справа.
# Крадіжка й наркотики при одному затриманні — два механізми, і зливати їх в
# одну подію не можна. А ст.122-4 і ст.124 КУпАП в одній справі — це одна
# аварія, яка раніше рахувалася двічі.
import labels as _L

_KK = re.compile(r'^ст\.[\d\-]+\s+КК\b')


def theme(cat):
    return (_L.CODE.get(cat) or ('СЕР', ''))[0]


def is_kk(cat):
    return bool(_KK.match((_L.CODE.get(cat) or ('', ''))[1]))


import mech as _M

# Вид стягнення за санкцією першої частини статті (відповідь 22.09, п.2б):
# арешт > позбавлення права > штраф. Лише статті, які затвердив основний чат;
# шкалу по пам'яті не добудовуємо. Розмір штрафу як другий ключ поки ніде не
# знадобився — у таблиці немає двох статей з однаковим видом стягнення.
SANCTION = {
    'ст.122-4 КУпАП': 3,   # адмінарешт
    'ст.130 КУпАП': 2,     # позбавлення права керування
    'ст.124 КУпАП': 1,     # штраф
    'ст.126 КУпАП': 1,     # штраф
}


def article(cat):
    """'ст.130 КУпАП · керування…' -> 'ст.130 КУпАП'"""
    return (_L.CODE.get(cat) or ('', ''))[1].split(' · ')[0]


def _heaviest(cats):
    """Статті, які правило не може розвести між собою."""
    pool = list(cats)
    pool = [c for c in pool if not _M.is_proactive(c)] or pool
    pool = [c for c in pool if is_kk(c)] or pool
    # Стаття поза таблицею не «найлегша», а невідома: порівнюємо лише тоді,
    # коли в таблиці є всі. Інакше 122+126 віддало б 126 без жодної підстави.
    if all(article(c) in SANCTION for c in pool):
        top = max(SANCTION[article(c)] for c in pool)
        pool = [c for c in pool if SANCTION[article(c)] == top]
    return pool


def label_cat(cats, final_cat):
    """Стаття для підпису й механізму події: найтяжча з цього виду в справі.

    (а) Заявна стаття важить більше за проактивну (Р2, src/mech.py). Інакше
        ДТП п'яного водія, підписане ст.130, випало б з дорожніх ділянок.
    (б) За рівності — суворіше стягнення: злочин (ККУ) суворіший за
        адмінправопорушення (КУпАП); всередині кодексу — за таблицею SANCTION.
    Що правило не розводить — стаття підсумкового рішення. Усі статті справи
    подія все одно несе окремим полем."""
    pool = _heaviest(cats)
    return final_cat if final_cat in pool else sorted(pool)[0]


def unresolved(cats):
    """Чи лишилось після правила кілька різних статей — для звіту."""
    return len({article(c) for c in _heaviest(cats)}) > 1


def merge_cases(rows, doc, cat, date, cause, event):
    """Зводить документи в події: одна на (справа, вид).

    rows — будь-які записи; doc, cat, date — як дістати з запису номер
    документа, код статті й дату; cause — doc_id -> номер справи; event —
    чи документ є рішенням по суті. Повертає список (представник, усі
    документи групи, стаття для підпису, усі статті події). Представник —
    підсумкове рішення по суті, тобто найпізніше: це остаточна кваліфікація й
    остаточна адреса. Група з самих ухвал події не дає; ухвали лишаються
    серед документів групи — панель рішень адреси показує й їх.

    Усі статті — коди з рішень по суті, підпис першим. Підпис бере одну
    статтю, а ст.130 у справі про ДТП — теж факт про місце, і губити його
    не можна (відповідь 22.09, п.2)."""
    groups = collections.defaultdict(list)
    for r in rows:
        d = str(doc(r)); cn = cause.get(d)
        groups[(cn, theme(cat(r))) if cn else ('#' + d, theme(cat(r)))].append(r)
    out = []
    for g in groups.values():
        evs = [x for x in g if event(x)]
        if not evs:
            continue
        rep = max(evs, key=lambda x: (date(x) or '', str(doc(x))))
        cats = {cat(x) for x in evs}
        lab = label_cat(cats, cat(rep))
        out.append((rep, g, lab, [lab] + sorted(cats - {lab})))
    return out
