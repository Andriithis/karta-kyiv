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
import os, re, csv, gzip

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
