# -*- coding: utf-8 -*-
"""Крок 2e. Шар чинників середовища для карти.

Витягає з osm_risks_raw.json координати тих об'єктів, які модель ризику
(крок 4) рахує як ознаки, і складає компактний data/factors.json.
Сам osm_risks_raw.json на карту не годиться — він важить десятки мегабайт.

Радіус «Що поруч» для кожного типу — з data/radiusy.json (крок 4, RTM).

Дерева, трава й лавки свідомо не входять: їх на порядок більше за решту,
а ваги в моделі мізерні — карта стала б важкою без користі для аналізу.

Групування — за криміналістичною роллю об'єкта, а не за абеткою:
  0) притягують правопорушення — місця, куди люди йдуть по те, що створює привід;
  1) збирають людей — генератори потоку, самі по собі не «погані»;
  2) стан середовища — ознаки занедбаності або, навпаки, догляду.
Свідомо НЕ підписуємо «підвищує/знижує ризик»: напрямок впливу видно з ваги
в engine_report.json, і він буває несподіваним (напр., дитячі майданчики за
даними моделі ризик наркотиків підвищують).
"""
import os, sys, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
RAW  = os.path.join(DATA, 'osm_risks_raw.json')
OUT  = os.path.join(DATA, 'factors.json')

# ключ у RAW | назва для людей | база ознаки в моделі (як у step4_engine) | група
# Перелік Б1 (NAUKA.md, 28.09): ломбарди, банкомати й обмінники, ринки,
# супермаркети й ТЦ, лікарні й аптеки — окремо, бо механізми різні.
CATS = [
    ('b1_bars',      'Бари, клуби',            'бари',              0),
    ('b1_alk',       'Алкоголь на винос',      'алкоголь_винос',    0),
    ('b1_cafe',      'Кафе, ресторани',        'кафе',              0),
    ('b1_fastfood',  'Фастфуд',                'фастфуд',           0),
    ('b1_pawn',      'Ломбарди',               'ломбарди',          0),
    ('b1_atm',       'Банкомати',              'банкомати',         0),
    ('b1_exchange',  'Обмінники, перекази',    'обмінники',         0),
    ('b1_fuel',      'АЗС',                    'АЗС',               0),
    ('b1_school',    'Школи, садки',           'школи',             1),
    ('b1_univer',    'ВНЗ',                    'ВНЗ',               1),
    ('b1_dorm',      'Гуртожитки, хостели',    'гуртожитки',        1),
    ('b1_hospital',  'Лікарні, клініки',       'лікарні',           1),
    ('b1_pharmacy',  'Аптеки',                 'аптеки',            1),
    ('b1_market',    'Ринки',                  'ринки',             1),
    ('b1_super',     'Супермаркети',           'супермаркети',      1),
    ('b1_mall',      'ТЦ',                     'ТЦ',                1),
    ('b1_metro',     'Метро, вокзали',         'метро',             1),
    ('b1_stops',     'Зупинки транспорту',     'зупинки',           1),
    ('b1_play',      'Дитячі майданчики',      'майданчики',        1),
    ('b1_underpass', 'Підземні переходи',      'переходи_підземні', 2),
    ('b1_abandon',   'Покинуті будівлі',       'покинуті',          2),
    ('b1_parking',   'Відкриті паркінги',      'паркінги',          2),
    ('b1_garages',   'Гаражні кооперативи',    'гаражі',            2),
]
# типи закладів, чиї назви з OSM потрібні звіту 5.1
ZAKLADY = {'b1_bars', 'b1_alk', 'b1_cafe', 'b1_fastfood', 'b1_pawn', 'b1_exchange',
           'b1_super', 'b1_mall', 'b1_market', 'b1_fuel', 'b1_pharmacy', 'b1_dorm'}
# Найменше коло RTM (PLAN-KROK7, розд. 3): у ньому «Що поруч» показує типи,
# не пов'язані з подіями, — кнопка лишається спостереженням, а не підказкою.
R_MIN = 50
# Поки двигун Б1 не відпрацював (radiusy.json немає), усе — у 250 м, як було.
R_OLD = 250
GROUPS = ['Притягують правопорушення', 'Збирають людей', 'Стан середовища']

def main():
    if not os.path.exists(RAW):
        print('немає data/osm_risks_raw.json — спершу крок 2b')
        sys.exit(1)
    raw = json.load(open(RAW, encoding='utf-8'))
    rp = os.path.join(DATA, 'radiusy.json')
    shcho = json.load(open(rp, encoding='utf-8')).get('shcho_poruch', {}) if os.path.exists(rp) else None
    out, total, zaklady = [], 0, {}
    for key, name, base, grp in CATS:
        pts, nms = [], []
        for el in raw.get(key, []):
            la = el.get('lat') or (el.get('center') or {}).get('lat')
            lo = el.get('lon') or (el.get('center') or {}).get('lon')
            if la and lo:
                pts.append([round(la, 5), round(lo, 5)])
                nms.append((el.get('tags') or {}).get('name', ''))
        r = R_OLD if shcho is None else (shcho.get(base) or R_MIN)
        out.append({'k': key, 'n': name, 'b': base, 'g': grp, 'r': r, 'pts': pts})
        total += len(pts)
        if key in ZAKLADY: zaklady[key] = {'n': name, 'pts': pts, 'nm': nms}
        print(f'   {name:30} {len(pts):6,}  у {r} м')
    json.dump({'groups': GROUPS, 'cats': out},
              open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    # Назви закладів — окремим файлом для звіту «заклади, біля яких подій найбільше»
    # (PLAN-ZVITY, 5.1; RISHENNYA, розд. 25): у карту вони не йдуть, щоб
    # factors.json, вбудований у сторінку, не важчав.
    json.dump(zaklady, open(os.path.join(DATA, 'zaklady.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, separators=(',', ':'))
    print(f"\n=== ГОТОВО === {total:,} об'єктів -> data/factors.json "
          f'({os.path.getsize(OUT)/1048576:.1f} МБ)')

if __name__ == '__main__':
    main()
