# -*- coding: utf-8 -*-
"""Крок 6. Звіти, які збираються самі з тих самих даних, що й карта.

З 28.09.2026 — три звіти й методика (PLAN-ZVITY.md, розд. 25; код —
step6_zvity.py):
  problemy.html, skhozhi-umovy.html, stan-mista.html, metodyka.html.

Старі адреси лишаються переадресаціями з тими самими якорями й параметрами:
  doslidzhennya.html (з ?st= і #t-…) -> skhozhi-umovy.html;
  analiz.html, rezyume.html          -> stan-mista.html.
Старі модулі step6_base/intro/research/state/theme видалено 29.09.2026 (аудит 4).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import step6_zvity as Z

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, 'site')

PEREADRES = {'doslidzhennya.html': 'skhozhi-umovy.html',
             'analiz.html': 'stan-mista.html', 'rezyume.html': 'stan-mista.html'}


def pereadresatsiia(kudy):
    # location.replace, а не meta refresh: так зберігаються ?st= і #t-… зі
    # старих посилань у вікнах вулиць, і «назад» не повертає на порожню сторінку
    return ('<!DOCTYPE html><html lang="uk"><head><meta charset="utf-8">'
            f'<title>Переадресація</title><meta http-equiv="refresh" content="0;url={kudy}">'
            f'<script>location.replace("{kudy}"+location.search+location.hash)</script></head>'
            f'<body><a href="{kudy}">Звіт переїхав сюди</a></body></html>')


def build(outdir, A=None, D=None):
    """Кладе звіти й переадресації в задану папку. Міська карта має бути
    вже зібрана в цьому процесі (step5_site так і робить)."""
    os.makedirs(outdir, exist_ok=True)
    made = Z.build(outdir)
    for stare, nove in PEREADRES.items():
        open(os.path.join(outdir, stare), 'w', encoding='utf-8').write(pereadresatsiia(nove))
    return made + list(PEREADRES)


def main():
    import step3_map as S3
    S3.main(out=os.path.join(SITE, os.path.basename(S3.OUT)))
    print('   ' + ', '.join(build(SITE)))
    print('=== ГОТОВО === звіти зібрано')


if __name__ == '__main__':
    main()
