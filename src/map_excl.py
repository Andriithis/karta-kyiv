# -*- coding: utf-8 -*-
"""Адреси установ: суди, відділи поліції, місця оформлення протоколів.

Такі адреси дають сотні подій, яких там насправді не сталося, і без вилучення
вони очолюють будь-який список. Виявляються автоматично за часткою подій свого
району; результат пишеться в data/vykluchennya.txt — це РЕЗУЛЬТАТ, не вхід,
інакше адреса, раз потрапивши туди, лишалася б виключеною назавжди.

Власний список користувача — data/vykluchennya_moyi.txt — автоматика ніколи
не перезаписує.
"""
import os, sys, collections
import labels as L
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')

EXCL = os.path.join(DATA, 'vykluchennya.txt')           # формується автоматично
MANUAL = os.path.join(DATA, 'vykluchennya_moyi.txt')    # ваш список, ніколи не перезаписується
REVIEW = os.path.join(DATA, 'top100_dlya_pereviryky.txt')

SHARE_LIMIT = 0.015      # частка подій свого району, за якою адреса вважається установою
ABS_LIMIT   = 90         # або стільки подій незалежно від частки

def load_excl():
    man = set()
    if not os.path.exists(MANUAL):
        with open(MANUAL, 'w', encoding='utf-8') as f:
            f.write('# ВАШ список адрес, які треба виключити з карти.\n')
            f.write('# Цей файл автоматика НІКОЛИ не перезаписує.\n')
            f.write('# Один рядок = одна адреса, точно як у vykluchennya.txt\n\n')
    # ЧИТАЄМО ЛИШЕ РУЧНИЙ файл. Автоматичний (EXCL) — це результат, не вхід:
    # інакше адреса, раз потрапивши туди, лишалась би виключеною назавжди.
    if os.path.exists(MANUAL):
        for ln in open(MANUAL, encoding='utf-8'):
            ln = ln.split('#')[0].strip()
            if ln: man.add(ln.lower())
    return man

def detect_institutional(rows, manual):
    per_court = collections.Counter(r[1] for r in rows)
    per_addr = collections.Counter()
    addr_court = {}
    for r in rows:
        if not r[5]: continue
        a = (r[5] + ', ' + r[6]) if r[6] else r[5]
        per_addr[a] += 1
        addr_court[a] = r[1]
    auto = {}
    for a, n in per_addr.items():
        tot = per_court[addr_court[a]] or 1
        if n >= ABS_LIMIT or n / tot >= SHARE_LIMIT:
            auto[a] = (n, round(100 * n / tot, 1))
    # звіт: топ-100 адрес із профілем статей, щоб можна було оцінити очима
    prof = collections.defaultdict(collections.Counter)
    for r in rows:
        if not r[5]: continue
        a = (r[5] + ', ' + r[6]) if r[6] else r[5]
        lb = L.CODE.get(r[2])
        prof[a][lb[1] if lb else r[2]] += 1
    with open(REVIEW, 'w', encoding='utf-8') as f:
        f.write('# Топ-100 адрес за кількістю подій, із профілем статей.\n')
        f.write('# Якщо бачите установу (суд, відділ поліції, місце оформлення протоколів) —\n')
        f.write('# скопіюйте її адресу у файл vykluchennya.txt окремим рядком.\n')
        f.write('# Ознака місця оформлення: майже все — ст.130, ст.126, ст.122-4.\n\n')
        for a, n in per_addr.most_common(100):
            mark = ' [ВЖЕ ВИКЛЮЧЕНО]' if a in auto else ''
            f.write(f'{n:6}  {a}{mark}\n')
            for st, k in prof[a].most_common(4):
                f.write(f'          {k:5}  {st}\n')
            f.write('\n')
    print(f'   звіт для перегляду: data/top100_dlya_pereviryky.txt')

    if auto or not os.path.exists(EXCL):
        with open(EXCL, 'w', encoding='utf-8') as f:
            f.write('# Адреси, виключені з карти як установи (суди, відділи поліції).\n')
            # пороги підставляються з констант, щоб текст не розходився з кодом
            f.write(f'# Визначено автоматично: адреса дає понад {SHARE_LIMIT*100:g}% подій\n')
            f.write(f'# свого району або понад {ABS_LIMIT} подій.\n')
            f.write('# Приберіть рядок, якщо адреса справжня.\n')
            f.write('# Один рядок = одна адреса.\n\n')
            for a, (n, pc) in sorted(auto.items(), key=lambda x: -x[1][0]):
                f.write(f'{a}   # {n} подій, {pc}% району\n')
        print(f'   виявлено установ: {len(auto)} -> data/vykluchennya.txt')
        for a, (n, pc) in sorted(auto.items(), key=lambda x: -x[1][0])[:8]:
            print(f'     {n:5}  {pc:4}%  {a}')
    return {a.lower() for a in auto} | manual
