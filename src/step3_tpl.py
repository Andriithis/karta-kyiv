# -*- coding: utf-8 -*-
"""HTML-шаблон карти. Збирається з чотирьох частин.

    tpl_style   шапка сторінки і стилі
    tpl_body    розмітка панелі
    tpl_map     карта, шари, підсвітка «що поруч» (Leaflet)
    tpl_core    панель, паспорт SARA, картка проблеми, computeVis — спільне
    tpl_draw    малювання позначок (Leaflet)

Плейсхолдери __META__, __PTS__, __RISKS__, __POP__, __FACTS__ підставляє
step3_map.main(). Тут немає жодного обчислення — тільки те, що бачить
і натискає користувач.

Розділено 2 вересня 2026: правка в одній частині більше не пересилає
весь шаблон цілком.
"""
from tpl_style import HEAD
from tpl_body import BODY
from tpl_map import JS_MAP
from tpl_core import JS_CORE
from tpl_draw import JS_DRAW

# Порядок частин у скрипті важить: tpl_map створює карту, шари й PALA, tpl_core
# на них спирається, коли будує панель, а tpl_draw малює вже по готовому.
TPL = (HEAD + BODY + '\n<script>\n'
       + JS_MAP + '\n' + JS_CORE + '\n' + JS_DRAW
       + '\n</script></body></html>')
