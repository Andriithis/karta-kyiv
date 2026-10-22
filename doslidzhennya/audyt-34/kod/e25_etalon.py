# -*- coding: utf-8 -*-
"""ZAVDANNYA-38, крок 5 (ZAVDANNYA-39, Д.1; Андрій 22.10): еталон ззовні —
топ-50 місць за скаргами 1551 (порядок, торгівля алкоголем, безпека руху —
ті самі групи, що «голос мешканців», S-ПР.12) і п'ять місць з пілоту
центрального чату. Для кожного: чи є воно в data/kandydaty.json.gz (сито
36.36/36.37) і в переліку проблем; якщо немає — чому, числами.

    py -3 doslidzhennya/audyt-34/kod/e25_etalon.py   -> e25_etalon.json

Мірило — частка еталона, яку знаходить сито. «Знаходить» = пара сита того
самого виду в R м від місця (R_M = 60: точка 1551 — будинок заявника, подія —
будинок у рішенні; ріг чи сусідній будинок — те саме місце).
"""
import collections, gzip, json, math, os, sqlite3, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, 'src'))
DATA = os.path.join(ROOT, 'data')
R_M = 60
# Групи 1551 за змістом (zbir_1551.GRUPY_1551) -> вид подій карти. Освітлення
# й стан доріг — не порушення: еталоном для карти правопорушень бути не можуть.
GR_VYD = {'шум_заклади': 'ГП', 'безпритульні': 'ГП', 'порядок_інше': 'ГП', 'торгівля_МАФ': 'АЛК',
          'паркування': 'ДОР', 'переходи_світлофори': 'ДТП', 'обмежувачі': 'ДТП'}
PILOT = [('вул. Васильківська, 30 / вул. Сумська', 'ДТП', 'лівий поворот'),
         ('вул. Васильківська, 29/22 / пров. Коломийський', 'ДТП', 'лівий поворот'),
         ('вул. Кільцева дорога, 3-А', 'ДТП', 'перестроювання'),
         ('вул. Кільцева дорога, 1 (ТРЦ «Республіка»)', 'ДТП_залишення', 'паркування'),
         ('вул. Велика Васильківська, 72', 'ГП_пиятика', 'вечір')]


def d_m(a, b):
    return math.hypot((a[0] - b[0]) * 111320, (a[1] - b[1]) * 111320 * math.cos(math.radians(a[0])))


def vyd_pary(sim):
    if sim.startswith('ДОР_ДТП') or sim.startswith('ДОР_залишення'): return 'ДТП'
    return sim.split('_')[0]


def main():
    import problems as PR
    K = json.load(gzip.open(os.path.join(DATA, 'kandydaty.json.gz'), 'rt', encoding='utf-8'))
    rep = json.load(gzip.open(os.path.join(DATA, 'problems_report.json.gz'), 'rt', encoding='utf-8'))
    probl = [(r['sim'], tuple(r['p'])) for r in rep.get('perelik', [])]
    sk = PR.skargy_hrupy(log=lambda *a: None)
    mista = collections.Counter(); adr = {}
    for _m, g, p in sk:
        if g not in GR_VYD: continue
        k = (round(p[0], 4), round(p[1], 4), GR_VYD[g]); mista[k] += 1
    top = mista.most_common(50)
    out = []
    for (la, lo, vyd), n in top:
        p = (la, lo)
        kand = [k for k in K if vyd_pary(k['sim']) == vyd and d_m(p, (k['lat'], k['lon'])) <= R_M]
        pr_ = [s for s, q in probl if vyd_pary(s) == vyd and d_m(p, q) <= R_M]
        out.append(dict(p=p, vyd=vyd, skarg=n, kandydaty=[(k['sim'], k['adresy'][:2], len(k['podii'])) for k in kand],
                        problema=pr_))
    zn = sum(1 for o in out if o['kandydaty'])
    # чому немає: судових подій того виду поруч (з точок карти)
    import map_dani
    pts = map_dani.chytaty(os.path.join(ROOT, 'site', 'index.html'), 'meta', 'pts')
    M, P = pts['meta'], pts['pts']
    gr = {}
    for gi, (nm, ids, _n) in enumerate(M['groups']):
        for i in ids: gr[i] = nm
    VYD_NM = {'ГП': 'Громадський порядок', 'АЛК': 'Алкоголь і торгівля', 'ДТП': 'ДТП',
              'ДОР': 'Порушення на дорозі'}
    for o in out:
        if o['kandydaty']: continue
        ev = [e for q in P if d_m(o['p'], (q[0], q[1])) <= R_M for e in q[4] if gr.get(e[1]) == VYD_NM[o['vyd']]]
        o['podii_poruch'] = len(ev)
        o['chomu'] = ('судових подій цього виду поруч немає' if not ev else
                      f'подій {len(ev)} — менше сита 5 у 3 кварталах' if len(ev) < 5 else
                      'подій ≥5, але за останні 2 роки менше 5 чи менше 3 кварталів (сито)')
    # адреса — найближча точка карти, щоб місце читалося
    for o in out:
        bl = min(P, key=lambda q: d_m(o['p'], (q[0], q[1])))
        o['adresa'] = bl[2] if d_m(o['p'], (bl[0], bl[1])) <= R_M else '(точки карти в 60 м немає)'
    # п'ять місць пілоту центрального чату: пара в ситі, подій, мітки сценарію
    pilot = []
    for nazva, vyd, mitka in PILOT:
        osn = nazva.split(' / ')[0].split(' (')[0].replace('вул. ', '')
        pary = [k for k in K if any(osn in a for a in k['adresy'])
                and (vyd.startswith('ДТП') and k['sim'].startswith('ДОР_' + ('залишення' if 'залиш' in vyd else 'ДТП'))
                     or vyd == k['sim'])]
        rr = []
        for k in pary:
            ev = k['podii']
            if mitka == 'вечір':
                n_m = sum(1 for e in ev if (e.get('time') or '')[:2].isdigit() and int(e['time'][:2]) >= 18)
            else:
                n_m = sum(1 for e in ev if mitka in e.get('mitky', []))
            rr.append(dict(sim=k['sim'], status=k['status'], adresy=k['adresy'][:3], podii=len(ev), zi_stsenariiem=n_m))
        pilot.append(dict(misce=nazva, vyd=vyd, stsenarij=mitka, v_syti=bool(rr), pary=rr))
    for x in pilot:
        print(f"пілот: {x['misce']} — " + ('; '.join(f"{r['sim']} {r['status']}: {r['podii']} подій, «{x['stsenarij']}» {r['zi_stsenariiem']}"
                                                   for r in x['pary']) or 'у ситі немає'))
    json.dump(dict(R_M=R_M, top50=out, znajdeno=zn, pilot=pilot), open(os.path.join(HERE, 'e25_etalon.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f'топ-50 1551: у ситі {zn} з {len(out)}; у переліку проблем {sum(1 for o in out if o["problema"])}')
    print('без кандидата: ' + str(collections.Counter(o.get('chomu') for o in out if not o['kandydaty'])))
    print('за видами: ' + str({v: (sum(1 for o in out if o['vyd'] == v and o['kandydaty']), sum(1 for o in out if o['vyd'] == v))
                              for v in set(GR_VYD.values())}))


if __name__ == '__main__':
    main()
