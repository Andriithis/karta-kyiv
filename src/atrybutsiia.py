# -*- coding: utf-8 -*-
"""Атрибуція — один рядок для карти, звітів «Дослідження» й файлів переліку
адрес (S-К.20, S-З.7, S-Б.7; RISHENNYA 36.26). Тут — єдине місце: карта,
звіти й файли беруть звідси, тож назви й ліцензії не розходяться.

Рядок «адреси подій — з текстів рішень» не прибирати: текст суду не завжди
точний, і це має бути видно (VIDPOVID-39).
"""
OSM_COPYRIGHT = 'https://www.openstreetmap.org/copyright'

HTML = ('Підкладка: <a href="https://openfreemap.org" target="_blank" rel="noopener">OpenFreeMap</a> © '
        '<a href="https://openmaptiles.org" target="_blank" rel="noopener">OpenMapTiles</a> · дані © '
        f'<a href="{OSM_COPYRIGHT}" target="_blank" rel="noopener">OpenStreetMap</a> (ODbL) · події: '
        '<a href="https://reyestr.court.gov.ua" target="_blank" rel="noopener">ЄДРСР</a>, ДСА України '
        '(<a href="https://creativecommons.org/licenses/by/4.0/deed.uk" target="_blank" rel="noopener">CC BY</a>), '
        'адреси подій — з текстів рішень · адреси: '
        '<a href="https://kyivcity.gov.ua" target="_blank" rel="noopener">КМДА</a>, OpenStreetMap · звернення: '
        '<a href="https://1551.gov.ua" target="_blank" rel="noopener">1551</a>')

# для файлів даних — без розмітки
TEKST = ('Адреси й вулиці, похідні від OpenStreetMap, — ODbL 1.0 (© OpenStreetMap, ' + OSM_COPYRIGHT +
         '); адреси КМДА; події — ЄДРСР, ДСА України, CC BY 4.0.')

# що перевіряє check_build (test:atrybutsiia): п'ять джерел і посилання на умови OSM
DZHERELA = ('OpenFreeMap', 'OpenStreetMap', 'ЄДРСР', 'КМДА', '1551', OSM_COPYRIGHT)
