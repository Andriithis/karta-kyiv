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
    o += pririst(Dv, TKD, bagato)
    open(os.path.join(OUT, 'tochka.md'), 'w', encoding='utf-8').write('\n'.join(o) + '\n')
    rnd = random.Random(38)
    with open(os.path.join(OUT, 'tochka_pryklady.txt'), 'w', encoding='utf-8') as fh:
        for k_, v in pr.items():
            fh.write(f'\n== {k_} ({len(v)})\n')
            for x in rnd.sample(v, min(20, len(v))): fh.write(x + '\n')
    print('\n'.join(o))


def pririst(Dv, TKD, bagato):
    """VIDPOVID-38 (20.10, друга), п. 3–4: скільки точок додасть кожне
    правило першої хвилі окремо — кожна подія в першому правилі, що
    спрацювало (ключ 36.18.2 → відмінок 36.18.2 → неповна назва 36.18.6 →
    перехрестя). Точка буде, лише якщо після зіставлення пара «вулиця +
    номер» є в довіднику і не однойменна; для перехрестя — обидві вулиці
    знаходяться. І розклад «будинку немає» за вулицями."""
    def odnoznachna(k):
        ws = [w for w in k.split() if len(w) > 2]
        c_ = set.intersection(*(Dv.by_word.get(w, set()) for w in ws)) if ws else set()
        return next(iter(c_)) if len(c_) == 1 else None
    def vulytsia(s_):
        """(ключ довідника, правило) або (None, '')"""
        k = Dv.vulytsia(s_)
        if k in Dv.full: return k, 'ключ'
        kn = nazyvnyi(k, Dv.full)
        if len(kn) == 1: return kn[0], 'відмінок'
        x = odnoznachna(k)
        return (x, 'неповна назва') if x else (None, '')
    PR = {'ключ': '36.18.2 — ключ (ініціали, скорочення)', 'відмінок': '36.18.2 — відмінок у називний',
          'неповна назва': '36.18.6 — неповна назва, збіг однозначний', 'перехрестя': 'перехрестя (відмінок, неповна назва)'}
    pr = collections.defaultdict(collections.Counter)
    nemaie = collections.Counter(); nemaie_dtp = collections.Counter(); n_nem = collections.Counter()
    for r in csv.DictReader(gzip.open(os.path.join(OUT, 'prychyny.tsv.gz'), 'rt', encoding='utf-8'), delimiter='\t'):
        if r['vidpalo_na'] != 'точка': continue
        tk = TKD.get(r['doc_id']) or {}
        s_, h_ = tk.get('street') or '', tk.get('house') or ''
        if ' / ' in s_ and not h_:
            a, b = (vulytsia(x)[0] for x in s_.split(' / ', 1))
            pr[PR['перехрестя']]['подій'] += 1
            if a and b: pr[PR['перехрестя']]['точка буде'] += 1; pr[PR['перехрестя']][r['vyd']] += 1
            continue
        if not s_ or not h_: continue
        k, pravylo = vulytsia(s_)
        key = (k, nh(h_))
        if k and key in Dv.bud and key not in bagato:
            # «ключ» з будинком у довіднику — саме той випадок, де геокодер не збігся
            pr[PR[pravylo]]['подій'] += 1; pr[PR[pravylo]]['точка буде'] += 1; pr[PR[pravylo]][r['vyd']] += 1
        elif k and pravylo != 'ключ':
            pr[PR[pravylo]]['подій'] += 1
            pr[PR[pravylo]]['вулиця знайдеться, будинку немає'] += 1
        if k and key not in Dv.bud and pravylo == 'ключ':
            # «будинку немає в OSM і КМДА» — для окремого дослідження (п. 4)
            nemaie[k] += 1; n_nem[r['vyd']] += 1
            if r['vyd'] == 'ДТП': nemaie_dtp[k] += 1
    o = ['\n## Приріст точок за правилами першої хвилі (кожна подія — у першому правилі)\n',
         '| Правило | точка буде | з них ДТП | вулиця знайдеться, будинку немає |', '|---|---|---|---|']
    for k_ in PR.values():
        v = pr[k_]
        n_ = lambda x: f'{x:,}'.replace(',', ' ')
        o.append(f"| {k_} | {n_(v['точка буде'])} | {n_(v['ДТП'])} | {n_(v['вулиця знайдеться, будинку немає'])} |")
    vs = sum(pr[k_]['точка буде'] for k_ in PR.values())
    o.append(f"| **разом** | **{vs:,}** | {sum(pr[k_]['ДТП'] for k_ in PR.values()):,} | |".replace(',', ' '))
    tot = sum(nemaie.values())
    top = nemaie.most_common(20)
    o += [f'\n## «Будинку немає в OSM і КМДА» — 20 найчастіших вулиць\n',
          f"Подій {tot:,}, з них ДТП {n_nem['ДТП']:,}; на 20 вулицях — {sum(v for _, v in top):,} "
          f"(ДТП {sum(nemaie_dtp[k] for k, _ in top):,}).\n".replace(',', ' '),
          '| Вулиця (ключ довідника) | подій | ДТП |', '|---|---|---|']
    for k, v in top: o.append(f'| {k} | {v:,} | {nemaie_dtp[k]:,} |'.replace(',', ' '))
    return o


if __name__ == '__main__':
    main()
