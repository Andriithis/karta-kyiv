# -*- coding: utf-8 -*-
"""Тури карти для огляду міста й кіоску (ZAVDANNYA-40, 6.2; 36.44, 36.55).

Зупинки — лише з перевірених даних: проблеми переліку аналізу фабул
(problemy_analityk.json, «діє»), де сценарій уже знеособлено аналітиком.
Тур збирається правилом, а не руками, щоб із новим циклом аналізу зупинки
оновлювались самі й не лишалось зупинок, яких на карті вже немає.
Тур «Міфи й прикмети» — після 6.4 («Дивні залежності»), поки не збирається.
"""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANALITYK = os.path.join(ROOT, 'data', 'problemy_analityk.json')
MAX_ZUPYNOK = 7

# (код, назва, відбір: механізми, вираз у сценарії; порожній — будь-який)
TURY = [
    ('nich', 'Нічний Київ', ('ГП_хуліг', 'ГП_пиятика'), r'вноч|ввечер|ніч'),
    ('povoroty', 'Підступні повороти', ('ДОР_ДТП',), r'ліворуч|поворот|розворот'),
    ('telefony', 'Де зникають телефони', ('МАЙ_крадіжка', 'МАЙ_шахрайство'), r''),
    ('pidlitky', 'Підлітки міста', ('ГП_пиятика', 'ГП_куріння', 'ГП_хуліг'), r'неповнолітн|підлітк|студент|молод'),
    ('parkovky', 'Парковки ТРЦ — «зачепив і поїхав»', ('ДОР_залишення_місця',), r''),
    ('torhivlia', 'Торгівля з рук біля метро', ('АЛК_стихторгівля', 'АЛК_торгівля'), r'метро|перех|вокзал|ринк'),
]


def tury(fail=ANALITYK):
    """[{kod, nazva, zupynky:[{lat, lon, zum, adresa, vyd, istoriia, chyslo, z}]}] —
    тури з ≥3 зупинками; зупинки — найбільші за числом подій сценарію"""
    if not os.path.exists(fail): return []
    an = [z for z in json.load(open(fail, encoding='utf-8')) if z.get('stan') == 'діє']
    out = []
    for kod, nazva, mekh, rx in TURY:
        zz = [z for z in an if z.get('mekhanizm') in mekh and (not rx or re.search(rx, z.get('stsenarij') or '', re.I))]
        zz.sort(key=lambda z: (-z.get('n_stsenariju', 0), z.get('id', '')))
        if len(zz) < 3: continue
        out.append(dict(kod=kod, nazva=nazva, zupynky=[
            dict(lat=z['lat'], lon=z['lon'], zum=16.5, adresa=(z.get('adresy') or [''])[0], vyd=z.get('vyd'),
                 istoriia=z.get('stsenarij') or '', chyslo=z.get('n_stsenariju', 0), z=z.get('n_usikh', 0))
            for z in zz[:MAX_ZUPYNOK]]))
    return out


if __name__ == '__main__':
    t = tury()
    for x in t: print(x['nazva'], len(x['zupynky']))
