# -*- coding: utf-8 -*-
"""Е12б, А5 (ZAVDANNYA-36): назва вулиці в місцевому відмінку як окрема адреса.

Суди пишуть «на вул. Братиславській, 3», і подія стає адресою «вул.
Братиславській, 3» поруч із «вул. Братиславська, 3». Міряємо: скільки подій
з будинком мають назву не в називному, скільки з них зіллються з основною
адресою після нормалізації і чи не злипнуться різні вулиці.

Правило нормалізації — лише з довідником: форму міняємо, якщо її НЕМАЄ
серед назв вулиць OSM і КМДА, а називна — Є. Без довідника «Верхній Вал»
(називний!) став би «Верхня Вал». Злипання: точка події далі 2 км від
будинків вулиці, на яку переводимо, — підозра на іншу вулицю.

Код карти не чіпаємо. Вихід — числа в stdout і kod/e12b_a5.json.
"""
import os, sys, re, json, gzip, csv, math, collections
K = os.path.dirname(os.path.abspath(__file__))
R = os.path.abspath(os.path.join(K, '..', '..', '..'))
sys.path.insert(0, os.path.join(R, 'src'))
import step2_geocode as G

# закінчення місцевого (і давального) відмінка -> можливі називні
ZAKIN = [('ській', ('ська',)), ('цькій', ('цька',)), ('зькій', ('зька',)), ('ній', ('на', 'ня')),
         ('ій', ('а', 'я')), ('ському', ('ський', 'ське')), ('цькому', ('цький', 'цьке')),
         ('ому', ('ий', 'е', 'ій')), ('ім', ('ий',)), ('ці', ('ка',)), ('зі', ('га',)), ('сі', ('ха',)),
         ('і', ('а', 'я'))]


def pidpys_nom(s, nn):
    """підпис з типом вулиці з тексту й назвою в називному — щоб «вул.» і
    «пл.» Вокзальна лишались окремими, як зараз (зливаємо лише відмінок)"""
    return (G.stype(s) or '') + ' ' + nn


def main():
    osm = json.load(open(os.path.join(R, 'data', 'osm_kyiv_city.json'), encoding='utf-8'))
    ref = collections.defaultdict(list)          # нормована назва -> [(la, lo)]
    for st, h, la, lo in osm: ref[G.norm(st)].append((la, lo))
    with gzip.open(os.path.join(R, 'data', 'geokoder_kmda.csv.gz'), 'rt', encoding='utf-8') as fh:
        for r in csv.DictReader(fh, delimiter='\t'):
            ref[G.norm(r['street'])].append((float(r['lat']), float(r['lon'])))
    refset = set(ref)
    # Адреса будинку в довіднику — (назва, номер): так геокодер (крок 2)
    # знаходить точний будинок. Підпис карти вже канонічний (назва OSM), тож
    # відмінок видно лише в адресі, витягнутій з тексту, — її й беремо:
    # прохід по текстах (TKD), без нього — знімок events.csv.gz.
    budynky = set()
    for st, h, la, lo in osm: budynky.add((G.norm(st), G.nh(h)))
    with gzip.open(os.path.join(R, 'data', 'geokoder_kmda.csv.gz'), 'rt', encoding='utf-8') as fh:
        for r in csv.DictReader(fh, delimiter='\t'):
            budynky.add((G.norm(r['street']), G.nh(r['house'])))
    import step1c_teksty as TK
    TKD = TK.load_done()
    rows = []
    for r in csv.DictReader(gzip.open(os.path.join(R, 'data', 'events.csv.gz'), 'rt', encoding='utf-8'), delimiter='\t'):
        tk = TKD.get(r['doc_id'])
        st_, h_ = (tk.get('street'), tk.get('house')) if tk else (r['street'], r['house'])
        if st_ and h_: rows.append((r['doc_id'], st_, h_))
    print(f'документів з вулицею й номером: {len(rows):,}')
    # точки — центр вулиці в довіднику (для перевірки злипання)
    cen = {k: (sum(p[0] for p in v) / len(v), sum(p[1] for p in v) / len(v)) for k, v in ref.items()}

    def kandydaty(n):
        """нормована назва -> [називні варіанти з довідника]"""
        ws = n.split()
        out = []
        for i, w in enumerate(ws):
            for z, nz in ZAKIN:
                if w.endswith(z) and len(w) > len(z) + 2:
                    for e in nz:
                        nn = ' '.join(ws[:i] + [w[:-len(z)] + e] + ws[i + 1:])
                        if nn in refset and nn not in out: out.append(nn)
                    break
        # дві змінені частини: «Лесі Українки» не міняється, а «Героїв
        # Сталінградській» — так; пробуємо й обидва слова, що відмінюються
        if not out and len(ws) >= 2:
            ch = []
            for w in ws:
                v = [w]
                for z, nz in ZAKIN:
                    if w.endswith(z) and len(w) > len(z) + 2:
                        v += [w[:-len(z)] + e for e in nz]; break
                ch.append(v)
            import itertools
            for comb in itertools.product(*ch):
                nn = ' '.join(comb)
                if nn != n and nn in refset: out.append(nn)
        return out

    st = collections.Counter()
    zlyv = collections.Counter()                # (з, на) -> подій
    daleko = collections.Counter()
    prykl = collections.defaultdict(list)
    adr_do, adr_pislia = set(), set()
    def skupchennia(nn, krok=1.0):
        """скільки окремих скупчень будинків має назва (клітинки ~1 км, сусідні
        — одне скупчення): довга вулиця — одне, дві різні вулиці з однаковою
        назвою в різних кінцях міста — два"""
        cl = {(int(a * 111.32 / krok), int(b * 71.0 / krok)) for a, b in ref[nn]}
        n_, seen = 0, set()
        for c in cl:
            if c in seen: continue
            n_ += 1; stack = [c]
            while stack:
                x = stack.pop()
                if x in seen: continue
                seen.add(x)
                stack += [(x[0] + i, x[1] + j) for i in (-1, 0, 1) for j in (-1, 0, 1) if (x[0] + i, x[1] + j) in cl]
        return n_
    _sk = {}
    def rozkyd(nn):
        if nn not in _sk: _sk[nn] = skupchennia(nn)
        return 9.9 if _sk[nn] > 1 else 0.0
    for doc, s_, h_ in rows:
        n = G.norm(s_); h = G.nh(h_)
        tp = G.stype(s_); adr_do.add((tp, n, h))
        if n in refset:
            st['назва є в довіднику'] += 1; adr_pislia.add((tp, n, h)); continue
        c = kandydaty(n)
        if not c:
            st['немає ні в довіднику, ні називного'] += 1; prykl['немає'].append(s_); adr_pislia.add((tp, n, h)); continue
        if len(c) > 1:
            st['кілька називних — не міняємо'] += 1; prykl['кілька'].append((s_, c)); adr_pislia.add((tp, n, h)); continue
        nn = c[0]
        st['відмінок -> називний'] += 1
        # Злипання: назва вулиці, на яку переводимо, стоїть у довіднику в
        # кількох місцях далі 3 км — це вже дві вулиці; геокодер розводить їх
        # районом суду, але тут ризик злипнути різні вулиці найбільший.
        if rozkyd(nn) > 3.0:
            daleko[(s_, nn)] += 1; st['  з них — назва в кількох окремих місцях міста'] += 1
        if (nn, h) in budynky: st['  з них — знайдеться будинок'] += 1
        else: st['  з них — будинку з таким номером у довіднику немає'] += 1
        zlyv[(s_, nn)] += 1
        adr_pislia.add((tp, nn, h))
    print('\n'.join(f'  {k}: {v:,}' for k, v in sorted(st.items(), key=lambda x: x[0].startswith('  '))))
    print(f'адрес (вулиця + будинок): до {len(adr_do):,}, після {len(adr_pislia):,} (−{len(adr_do) - len(adr_pislia):,})')
    print('\nнайбільші злиття:')
    for (a, b), v in zlyv.most_common(25): print(f'  {v:5}  {a}  ->  {b}')
    print('\nназва в кількох окремих місцях — ризик злипання різних вулиць:')
    for (a, b), v in daleko.most_common(20): print(f'  {v:5}  {a}  ->  {b}')
    print('\nкілька називних:')
    for a, c in prykl['кілька'][:10]: print(f'  {a} -> {c}')
    print('\nнайчастіші назви, яких немає в довіднику і для яких називного не знайдено:')
    for a, v in collections.Counter(prykl['немає']).most_common(25): print(f'  {v:5}  {a}')
    json.dump(dict(st=dict(st), adres_do=len(adr_do), adres_pislia=len(adr_pislia),
                   zlyttia=[[a, b, v] for (a, b), v in zlyv.most_common()],
                   daleko=[[a, b, v] for (a, b), v in daleko.most_common()]),
              open(os.path.join(K, 'e12b_a5.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
