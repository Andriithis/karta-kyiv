# -*- coding: utf-8 -*-
"""Е25, крок 2 (ZAVDANNYA-38): чому адреса з номером не стає точкою.

Воронка (e25_voronka.py) дає два числа на кроці «точка»: «немає координати»
(геокодер нічого не поставив) і «точність street» (лише вулиця). Тут — розклад
обох тими самими правилами довідника, що в Е12б (e12b_adresy.Dovidnyk:
виправлений norm, перейменування 1551, відмінок у називний): вулиці немає в
довіднику / будинку з таким номером немає / адреса є, а точки немає — тоді
це ключ геокодера чи однойменні вулиці, а не текст.

Запуск: python e25_tochka.py [тека з 1551/, за замовчуванням data]
Вихід: kod/e25_vyhid/tochka.md і tochka_pryklady.txt (по 20 на причину).
"""
import os, sys, csv, gzip, random, collections
K = os.path.dirname(os.path.abspath(__file__))
R = os.path.abspath(os.path.join(K, '..', '..', '..'))
sys.path.insert(0, K); sys.path.insert(0, os.path.join(R, 'src'))
from e12b_adresy import Dovidnyk, nh, nazyvnyi
import step1c_teksty as TK

OUT = os.path.join(K, 'e25_vyhid')
VYDY = ['ГП', 'АЛК', 'НАР', 'НАС', 'МАЙ', 'ДТП', 'ДОР', 'ДОМ']


def main():
    D1551 = os.path.join(sys.argv[1] if len(sys.argv) > 1 else os.path.join(R, 'data'), '1551')
    Dv = Dovidnyk(D1551)
    TKD = TK.load_done()
    # однойменні: та сама пара (ключ, номер) у довіднику в кількох місцях далі 500 м
    import step2_geocode as G
    bagato = {k for k, v in Dv.bud.items() if len(v) > 1 and G.spread_km([(a, b) for a, b, _s in v]) > G.R_ODNA}
    st = collections.defaultdict(collections.Counter); pr = collections.defaultdict(list)
    for r in csv.DictReader(gzip.open(os.path.join(OUT, 'prychyny.tsv.gz'), 'rt', encoding='utf-8'), delimiter='\t'):
        if r['vidpalo_na'] != 'точка': continue
        tk = TKD.get(r['doc_id']) or {}
        s_, h_ = tk.get('street') or '', tk.get('house') or ''
        k = Dv.vulytsia(s_) if s_ else ''
        key = (k, nh(h_))
        # «вул. X / вул. Y» без номера — перехрестя, яке геокодер не знайшов
        if ' / ' in s_ and not h_: why = 'перехрестя — геокодер не знайшов (відмінок, назва без імені)'
        elif not k or not h_: why = 'у проході немає вулиці чи номера'
        elif k not in Dv.full:
            if nazyvnyi(k, Dv.full): why = 'вулиці немає в довіднику — відмінок, називний є'
            else:
                # «Заболотного», «Лобановського» — назва без імені: усі слова є
                # в одній-єдиній назві довідника
                ws = [w for w in k.split() if len(w) > 2]
                c_ = set.intersection(*(Dv.by_word.get(w, set()) for w in ws)) if ws else set()
                why = 'вулиці немає в довіднику — неповна назва, збіг однозначний' if len(c_) == 1 else \
                      'вулиці немає в довіднику — неповна назва, кілька збігів' if c_ else 'вулиці немає в довіднику'
        elif key not in Dv.bud: why = 'вулиця є, будинку з таким номером немає'
        elif key in bagato: why = 'адреса є — однойменна в кількох місцях міста'
        else: why = 'адреса є в довіднику — ключ геокодера не збігся'
        why = f"{r['prychyna']}: {why}"
        st[why][r['vyd']] += 1
        pr[why].append(f"{r['doc_id']}\t{r['vyd']}\t{s_}, {h_}")
    o = ['## Чому адреса з номером не стає точкою (Е25, крок 2)\n',
         'Розклад кроку «точка» воронки правилами довідника Е12б. Подій:\n',
         '| Причина | ' + ' | '.join(VYDY) + ' | усі |', '|---' * (len(VYDY) + 2) + '|']
    for k_, v in sorted(st.items(), key=lambda x: -sum(x[1].values())):
        o.append(f'| {k_} | ' + ' | '.join(f'{v[x]:,}'.replace(',', ' ') for x in VYDY) + f" | {sum(v.values()):,} |".replace(',', ' '))
    open(os.path.join(OUT, 'tochka.md'), 'w', encoding='utf-8').write('\n'.join(o) + '\n')
    rnd = random.Random(38)
    with open(os.path.join(OUT, 'tochka_pryklady.txt'), 'w', encoding='utf-8') as fh:
        for k_, v in pr.items():
            fh.write(f'\n== {k_} ({len(v)})\n')
            for x in rnd.sample(v, min(20, len(v))): fh.write(x + '\n')
    print('\n'.join(o))


if __name__ == '__main__':
    main()
