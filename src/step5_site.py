# -*- coding: utf-8 -*-
"""Крок 5. Збирає сайт: оглядова сторінка + 10 районних карт, у двох версіях."""
import os, sys, json, sqlite3, collections, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import labels as L
import step3_map as M3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
SITE = os.path.join(ROOT, 'site')

SLUG = {'Голосіївський':'golosiiv','Дарницький':'darnytsia','Деснянський':'desna',
        'Дніпровський':'dnipro','Оболонський':'obolon','Печерський':'pechersk',
        'Подільський':'podil','Святошинський':'sviatoshyn',"Солом'янський":'solomianka',
        'Шевченківський':'shevchenkivsk'}

def stats():
    """скільки проблем/аномалій/інцидентів і який профіль у кожного району"""
    conn = sqlite3.connect(os.path.join(DATA, 'events.db'))
    rows = conn.execute("""SELECT e.court, e.cat FROM events e
                           JOIN geo g ON g.doc_id=e.doc_id WHERE g.precision='house'""").fetchall()
    per = collections.defaultdict(collections.Counter)
    for court, cat in rows:
        lb = L.CODE.get(cat)
        if lb: per[M3.COURTS.get(court, court)][lb[0]] += 1
    return per

INDEX = """<!DOCTYPE html><html lang="uk"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Проблеми громад Києва</title><style>
*{box-sizing:border-box}body{margin:0;background:#0f1117;color:#e8eaf0;
 font:15px/1.5 system-ui,sans-serif;padding:34px 22px 60px}
.wrap{max-width:1020px;margin:0 auto}
h1{font-size:27px;margin:0 0 6px;letter-spacing:-.02em}
.sub{color:#79839a;font-size:14px;margin-bottom:30px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(232px,1fr));gap:13px}
a.card{display:block;text-decoration:none;color:inherit;background:#171a23;
 border:1px solid #252a37;border-radius:11px;padding:15px 16px;transition:.14s}
a.card:hover{background:#1c2030;border-color:#3a4256;transform:translateY(-2px)}
.nm{font-size:16.5px;font-weight:600;margin-bottom:9px}
.ev{font-size:26px;font-weight:600;letter-spacing:-.02em;line-height:1}
.evl{color:#6d7789;font-size:11.5px;margin:3px 0 11px}
.bar{display:flex;height:5px;border-radius:3px;overflow:hidden;margin-bottom:9px;background:#232838}
.bar i{display:block}
.leg{font-size:11px;color:#79839a;line-height:1.65}
.leg b{color:#c4cbd8;font-weight:500}
.dot{display:inline-block;width:7px;height:7px;border-radius:2px;margin-right:5px}
.note{margin-top:34px;color:#5f6878;font-size:12.5px;line-height:1.65;max-width:660px}
.note b{color:#8b95a8;font-weight:500}
</style></head><body><div class="wrap">
<h1>Проблеми громад Києва</h1>
<div class="sub">Аналіз правопорушень за даними Єдиного державного реєстру судових рішень. Оберіть район.</div>
<div class="grid">__CARDS__</div>
<div class="note">__NOTE__</div>
</div></body></html>"""

COLORS = {'ГП':'#e0533d','АЛК':'#e8a33d','НАР':'#8b5cf6','НАС':'#ef4444',
          'МАЙ':'#3b82f6','ДОР':'#22c55e','СЕР':'#14b8a6','ДОМ':'#94a3b8'}

def build_index(per, mode):
    cards = []
    for d in sorted(per, key=lambda x: -sum(per[x].values())):
        c = per[d]; tot = sum(c.values()) or 1
        bar = ''.join(f'<i style="background:{COLORS.get(k,"#555")};width:{100*v/tot:.1f}%"></i>'
                      for k, v in c.most_common())
        leg = '<br>'.join(
            f'<span class="dot" style="background:{COLORS.get(k,"#555")}"></span>'
            f'{L.THEMES.get(k,k)} <b>{100*v/tot:.0f}%</b>'
            for k, v in c.most_common(3))
        cards.append(f'<a class="card" href="{SLUG[d]}.html"><div class="nm">{d}</div>'
                     f'<div class="ev">{tot:,}</div><div class="evl">подій з адресою</div>'
                     f'<div class="bar">{bar}</div><div class="leg">{leg}</div></a>'.replace(',', ' '))
    note = ('<b>Як читати.</b> Кожна карта показує, де саме в районі концентруються правопорушення '
            'і які умови середовища з ними пов\'язані. ')
    if mode == 'full':
        note += ('Скупчення поділено на <b>проблеми</b> — ті, що пояснюються умовами середовища, '
                 'і <b>аномалії</b> — ті, де причина є, але її немає в даних; такі місця треба '
                 'перевіряти на місці. Поодинокі події позначені як <b>інциденти</b>.')
    else:
        note += ('Ваше завдання — знайти скупчення, висунути гіпотезу про причину '
                 'і перевірити її на місці.')
    note += ('<br><br>Джерело: відкриті дані ЄДРСР (розпорядник — Державна судова адміністрація України) '
             'та OpenStreetMap. Показані лише справи, розглянуті судом.')
    return INDEX.replace('__CARDS__', '\n'.join(cards)).replace('__NOTE__', note)

def main():
    if not os.path.exists(os.path.join(DATA, 'events.db')):
        print('немає data/events.db'); sys.exit(1)
    per = stats()
    for mode, sub in (('full', 'vykladach'), ('student', 'slukhach')):
        out = os.path.join(SITE, sub)
        os.makedirs(out, exist_ok=True)
        print(f'\n=== версія: {sub} ===')
        open(os.path.join(out, 'index.html'), 'w', encoding='utf-8').write(build_index(per, mode))
        for d, sl in SLUG.items():
            if d not in per: continue
            M3.main(district=d, mode=mode, out=os.path.join(out, f'{sl}.html'))
        M3.main(district=None, mode=mode, out=os.path.join(out, 'kyiv.html'))
    print(f'\n=== ГОТОВО === сайт у папці site/')
    print('   site/vykladach/index.html — повна версія')
    print('   site/slukhach/index.html  — версія для слухачів')

if __name__ == '__main__':
    main()
