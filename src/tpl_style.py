# -*- coding: utf-8 -*-
"""Шапка сторінки й усі стилі карти.

Тут: <!DOCTYPE>, <head>, стилі MapLibre і <style> цілком.
Розміри панелі, вигляд спливних вікон — усе змінюється тут.
Кольори НЕ пишуться літералом: вони живуть у змінних двох тем на початку
блока. Жодного тексту й жодної логіки: підписи — у tpl_body, поведінка —
у tpl_core і рушіях.

Теми й типографіка — з макета PROBA-VYGLIADU.html, картка-навігатор — із
затвердженого макета site/maket-panel.html (версія 4).
"""
# MapLibre 6.x поставляється лише як ES-модуль: dist/maplibre-gl.js більше
# немає, тож сам JS підтягує скрипт сторінки через import (див. step3_tpl).
# Тут лише стилі бібліотеки. Версія точна — оновлення не має приходити саме.

# Сам код — у site_src/ справжніми файлами (ZAVDANNYA-41, 4.5): редактор
# підсвічує JS і CSS, а збірка склеює їх тим самим порядком, що й раніше.
from tpl_fajly import cytaty

LIBS_GL = cytaty('libs_gl.ramka.html').replace('__CSS__', cytaty('libs_gl.css'))
HEAD_TPL = cytaty('head.ramka.html').replace('__CSS__', cytaty('head.css'))
HEAD_GL = HEAD_TPL.replace('__LIBS__', LIBS_GL)
