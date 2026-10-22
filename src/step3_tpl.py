# -*- coding: utf-8 -*-
"""HTML-шаблон карти (index.html, MapLibre). Збирається з частин.

    tpl_style    шапка сторінки і стилі
    tpl_body     розмітка панелі
    tpl_base     завантаження даних, палітра, теми, константи
    tpl_gl       бібліотека, підкладка, карта, шари, позначки
    tpl_core     панель, паспорт SARA, картка проблеми, computeVis
    tpl_vyhlyady вигляди, картки адреси й соти, пошук, телефон

Запасну Leaflet-збірку (karta-zapasna.html) прибрано разом з tpl_map і
tpl_draw (36.8). Дані в сторінку не вшиваються: їх тягне tpl_base з окремих
файлів dani/<назва>.<хеш>.json за переліком __DANI__ (36.22), який підставляє
step3_map.main(). Тут немає жодного обчислення — тільки те, що бачить
і натискає користувач.
"""
from tpl_style import HEAD_GL
from tpl_body import BODY
from tpl_base import JS_BASE
from tpl_core import JS_CORE
from tpl_gl import JS_GL_LOAD, JS_GL_MAP, JS_GL_DRAW
from tpl_vyhlyady import JS_VYHLYADY

# MapLibre 6.x — лише ES-модуль, тому сторінка вся в <script type="module">:
# бібліотеку підтягує import усередині JS_GL_LOAD, дані — await у tpl_base.
# Модуль виконується після розбору сторінки, як і звичайний скрипт у кінці
# <body>. Порядок частин важить: tpl_base дає дані й палітру, tpl_gl створює
# карту, tpl_core будує панель, останні малюють уже по готовому.
TPL_GL = (HEAD_GL + BODY + '\n<script type="module">\n'
          + JS_GL_LOAD + '\n' + JS_BASE + '\n' + JS_GL_MAP + '\n' + JS_CORE + '\n' + JS_GL_DRAW
          + '\n' + JS_VYHLYADY
          + '\n</script></body></html>')

# Слова «прогноз» в інтерфейсі нової карти немає (розд. 23, п. 8): карта не
# передбачає злочин. Шар моделі — «Ризик» (36.28.4, S-К.8, S-К.10; колишні
# «Схожі умови»): місця, де події ймовірні далі. Тексти в tpl_core писалися
# ще під дві збірки, тож заміни лишаються тут. Кожна мусить знайтися: інакше
# після правки тексту старе слово тихо повернулося б на карту.
GL_SLOVA = [
    ('<span>Прогноз ризику</span>', '<span>Ризик</span>'),
    ('`прогнозом моделі для цієї теми.', '`оцінкою моделі для цієї теми.'),
    ('за прогнозом потрапляє', 'за оцінкою моделі потрапляє'),
    ('«Прогноз ризику»', '«Ризик»'),
]
for _a, _b in GL_SLOVA:
    assert _a in TPL_GL, 'немає тексту для заміни: ' + _a
    TPL_GL = TPL_GL.replace(_a, _b)
