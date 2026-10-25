# -*- coding: utf-8 -*-
"""Детермінізм (36.24.4, S-Р.11): дві збірки з тими самими даними дають той
самий результат — хеш до байта.

    py -3 src/test_determinizm.py           збірка двічі: problems_report і dani/
    py -3 src/test_determinizm.py --ryzyk   ще раз модель (крок 4) проти data/risk.json

Збірка — крок 3 двічі в тимчасові папки (~6 хв). Відбір проблем, Р8 і кільця
мають власні сіди; розбіжність означає, що десь з'явився порядок множини,
час чи випадковість без сіду, і перелік проблем мигатиме між однаковими
даними. Модель — ще одне навчання (1,7–2,7 год) у тимчасову папку проти щойно
натренованої data/risk.json; поле versiia.дата не порівнюється (це дата).

Запускає «Оновлення карти» в перший понеділок місяця (збірка) і галочкою
«Перевірити детермінізм» (збірка, а з перенавчанням — і модель). Розбіжність —
жовта збірка з переліком, що саме відрізняється: сайт однаково публікується.
"""
import gzip, hashlib, io, json, os, sys, tempfile, contextlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')


def h(b):
    return hashlib.sha256(b).hexdigest()[:16]


def zbirka(tmp, nazva):
    """крок 3 у tmp/nazva: (хеш problems_report, перелік dani/)"""
    import step3_map, problems, map_excl, map_problems
    d = os.path.join(tmp, nazva); os.makedirs(d, exist_ok=True)
    # відбір кешується на процес (міська й районна збірки рахують його раз) —
    # друга збірка інакше взяла б перелік першої, і тест нічого б не міряв
    map_problems._PR = None
    # Вихідні файли — у тимчасову папку: справжні data/ не чіпаємо. Гістерезис
    # читає минулий звіт з того самого шляху — в обох збірок його немає, тож
    # умови однакові.
    rep = os.path.join(d, 'problems_report.json.gz')
    problems.REPORT, problems.SKHOZHI, problems.KANDYDATY = rep, os.path.join(d, 's.json'), os.path.join(d, 'k.json.gz')
    problems.ZMINY = os.path.join(d, 'zminy.md')
    map_excl.EXCL, map_excl.REVIEW = os.path.join(d, 'excl.txt'), os.path.join(d, 'top.txt')
    with contextlib.redirect_stdout(io.StringIO()):
        step3_map.main(out=os.path.join(d, 'site', 'index.html'))
    import map_dani
    dani = map_dani.perelik(open(os.path.join(d, 'site', 'index.html'), encoding='utf-8').read())
    zvit = json.load(gzip.open(rep, 'rt', encoding='utf-8'))
    return h(gzip.decompress(open(rep, 'rb').read())), dani, zvit


def riznytsia(a, b, shliakh='', out=None, mezha=8):
    """перші відмінності двох JSON — щоб у журналі було видно, що саме"""
    out = [] if out is None else out
    if len(out) >= mezha: return out
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            riznytsia(a.get(k), b.get(k), f'{shliakh}.{k}', out, mezha)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            riznytsia(x, y, f'{shliakh}[{i}]', out, mezha)
    elif a != b:
        out.append(f'{shliakh or "/"}: {str(a)[:80]} ≠ {str(b)[:80]}')
    return out


def ryzyk(tmp):
    """ще одне навчання моделі в tmp проти data/risk.json; None — збіг"""
    import step4_engine as S4
    ref = json.load(open(S4.RISK, encoding='utf-8'))
    S4.RISK, S4.OUT, S4.RADF = (os.path.join(tmp, n) for n in ('risk.json', 'engine_report.json', 'radiusy.json'))
    S4.main()
    nov = json.load(open(S4.RISK, encoding='utf-8'))
    for r in (ref, nov): (r.get('versiia') or {}).pop('дата', None)
    return riznytsia(ref, nov) or None


def main(z_ryzykom=False):
    tmp = tempfile.mkdtemp(prefix='karta_determinizm_')
    zh = []
    ha, da, za = zbirka(tmp, 'a')
    hb, db, zb = zbirka(tmp, 'b')
    print(f'   збірка двічі: problems_report {ha} / {hb}; файлів dani {len(da)}, різних {sum(da[k] != db.get(k) for k in da)}')
    if ha != hb:
        zh.append('problems_report: ' + '; '.join(riznytsia(za, zb)))
    for k in da:
        if da[k] != db.get(k): zh.append(f'dani/{k}: {da[k]} ≠ {db.get(k)}')
    if z_ryzykom:
        r = ryzyk(tmp)
        print('   модель ще раз: ' + ('risk.json той самий' if not r else 'risk.json інший'))
        if r: zh.append('risk.json: ' + '; '.join(r))
    for z in zh:
        print(f'::warning::ЖОВТА: недетермінована збірка (36.24.4) — {z}')
    return 1 if zh else 0


if __name__ == '__main__':
    sys.exit(main('--ryzyk' in sys.argv))
