# -*- coding: utf-8 -*-
"""Читання коду сторінки карти з site_src/ (ZAVDANNYA-41, 4.5): JS, CSS і
розмітка, які раніше жили рядками в src/tpl_*.py. Збірка (step3_tpl)
склеює їх тим самим порядком; результат — байт у байт той самий, крім шляху
до MapLibre (vendor/ поруч із сайтом, кіоск працює без CDN)."""
import os

TEKA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'site_src')


def cytaty(nazva):
    # текстовий режим: git на Windows може видати файл з CRLF, а збірка має
    # бути однаковою на будь-якій машині
    with open(os.path.join(TEKA, nazva), encoding='utf-8') as f:
        return f.read()
