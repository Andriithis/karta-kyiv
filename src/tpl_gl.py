# -*- coding: utf-8 -*-
"""Карта на MapLibre GL — головна сторінка сайту (index.html) з 26.09.2026.

Єдина збірка карти: запасну Leaflet-карту прибрано (36.8). Тут:
завантаження бібліотеки, перевірка WebGL, підкладка OpenFreeMap і запасна
OSM, дві теми, атрибуція, перехід між районами, позначки, кільця, ризик.

JS_GL_LOAD стоїть першим у модулі, JS_GL_MAP — після tpl_base, JS_GL_DRAW —
після tpl_core.
"""

# Сам код — у site_src/ справжніми файлами (ZAVDANNYA-41, 4.5): редактор
# підсвічує JS і CSS, а збірка склеює їх тим самим порядком, що й раніше.
from tpl_fajly import cytaty

JS_GL_LOAD = cytaty('gl_load.js')
JS_GL_MAP = cytaty('gl_map.js')
JS_GL_DRAW = cytaty('gl_draw.js')
