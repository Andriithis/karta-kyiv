# -*- coding: utf-8 -*-
"""Єдиний ключ адреси для точки карти (завдання 29, п. 3).

«Берковецька, 6-Д» і «6Д», «вул. Братиславська» і «просп. Братиславська»,
«Івана Дзюби» й «І.Дзюби», «Харківське Шосе» й «шосе» — одна будівля, а
на карті це були дві точки: геокодер ставив їх у різні місця (OSM і КМДА,
сусідні номери), і події однієї будівлі розходилися. Проблема їх склеювала
(30 м), карта — ні.

Ключ: вулиця без типу й без порядку слів (step2_geocode.skey), ініціали
розгорнуто за реєстром вулиць (КМДА й OSM), стара назва замінена новою за
довідником перейменувань; номер — у верхньому регістрі без дефіса й
пробілів (step2_geocode.nh).

Довідник перейменувань — з самих даних 1551: там вулиця пишеться «нова
(стара)», «просп. Берестейський (Перемоги)». Окремого довідника в
репозиторії немає; немає 1551 — перейменування просто не застосовуються.
"""
import os, glob, gzip, csv, json, re, collections
from step2_geocode import skey, nh, norm

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')


class Kliuch:
    def __init__(s):
        full = set()                          # ключі чинних назв
        kmda = os.path.join(DATA, 'geokoder_kmda.csv.gz')
        if os.path.exists(kmda):
            with gzip.open(kmda, 'rt', encoding='utf-8', newline='') as fh:
                for r in csv.DictReader(fh, delimiter='\t'):
                    full.add(skey(r['street']))
        osm = os.path.join(DATA, 'osm_kyiv_city.json')
        if os.path.exists(osm):
            for r in json.load(open(osm, encoding='utf-8')):
                full.add(skey(r[0]))
        full.discard('')
        s.full = full
        # слово прізвища -> повні назви з ним: для розгортання ініціалів
        s.by_word = collections.defaultdict(set)
        for k in full:
            for w in k.split():
                if len(w) > 2: s.by_word[w].add(k)
        s.rename = {}
        for f in sorted(glob.glob(os.path.join(DATA, '1551', 'lichylnyky-*.tsv.gz'))):
            with gzip.open(f, 'rt', encoding='utf-8', newline='') as fh:
                for r in csv.DictReader(fh, delimiter='\t'):
                    v = r.get('vulytsya') or ''
                    m = re.match(r'^(\S+)\s+(.+?)\s*\((.+)\)\s*$', v)
                    if not m: continue
                    new, old = skey(f'{m.group(1)} {m.group(2)}'), skey(f'{m.group(1)} {m.group(3)}')
                    # стара назва, що й досі є чинною назвою іншої вулиці, —
                    # не перейменування, а збіг: не чіпаємо
                    if old and new and old != new and old not in full:
                        s.rename[old] = new
        s._c = {}

    def vulytsia(s, street):
        if street in s._c: return s._c[street]
        k = skey(street)
        if k in s.rename: k = s.rename[k]
        ws = k.split()
        ini = [w for w in ws if len(w) <= 2]
        if ini and k not in s.full:
            rest = [w for w in ws if len(w) > 2]
            if rest:
                cand = set.intersection(*(s.by_word.get(w, set()) for w in rest))
                cand = [c for c in cand if len(c.split()) == len(ws)
                        and all(any(x.startswith(i) and len(x) > 2 for x in c.split()) for i in ini)]
                if len(cand) == 1: k = cand[0]
        s._c[street] = k
        return k

    def __call__(s, street, house):
        """(ключ вулиці, номер) або None, якщо номера немає"""
        if not street or not house: return None
        return (s.vulytsia(street), nh(house).replace('-', ''))
