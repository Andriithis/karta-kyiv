# -*- coding: utf-8 -*-
"""Крок 5. Збирає сайт: ОДНА карта й три документи. Версія одна.

Районних файлів більше немає. Карта міста несе межі всіх районів і їхні
власні переліки проблем, а перехід у район — це вибір у панелі або адреса
виду #desna.

З 26.09.2026 (рішення Андрія, PLAN-ZAHALNYI, Г0) головна сторінка сайту — сама
нова карта (index.html), одразу все місто. Оглядової сторінки з плитками
районів більше немає: вона була зайвим кроком між людиною й картою, а район
однаково обирається в панелі. Старі адреси kyiv.html і kyiv-gl.html
переводять на головну; Leaflet-карта — лише запасна для браузера без WebGL
(karta-zapasna.html), посилань на неї немає.

Поділу на викладацьку й слухацьку версії теж немає. Проблеми бачать усі:
перший крок ланцюга — «обрати проблему зі списку», а робота слухача починається
далі, за SARA — встановити причину й перевірити її на місці. Ховати перелік
означало б залишити слухачеві пошук найлюднішої вулиці, тобто ту саму
реактивність, яку проєкт прибирає.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import step3_map as M3
import step6_docs as D6

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
SITE = os.path.join(ROOT, 'site')


def main():
    if not os.path.exists(os.path.join(DATA, 'events.db')):
        print('немає data/events.db'); sys.exit(1)
    out = SITE
    os.makedirs(out, exist_ok=True)
    # Колишня оглядова сторінка з плитками районів могла лишитися в site/ з
    # попередньої збірки — її місце тепер займає карта, тож вона
    # перезапишеться; окремо нічого не прибираємо.
    M3.main(district=None, out=os.path.join(out, os.path.basename(M3.OUT)))
    # крок 6 — після карти: step3_map дорогою будує data/factors.json,
    # без якого в документах не було б розділу «що поруч»
    try:
        made = D6.build(out)
        print('   документи: ' + ', '.join(made))
    except Exception as e:
        print('   документи не зібрано:', e)
    print(f'\n=== ГОТОВО === сайт у папці site/')
    print('   site/index.html — карта (MapLibre), райони обираються в панелі')
    print('   site/karta-zapasna.html — запасна карта для браузера без WebGL')


if __name__ == '__main__':
    main()
