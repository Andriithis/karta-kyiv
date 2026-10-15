# -*- coding: utf-8 -*-
"""Е8, перевірка: зведення e8_<вид>_<набір>.json у таблиці (markdown у stdout).

Правило вибору (протокол Е8): найпростіший підхід, PAI якого на головному
зрізі (10% довжини) не нижчий за нижню межу найкращого (E3) і рангова
стабільність (E4, Спірмен) не гірша за найкращого більше ніж на 0,05.
"""
import os, sys, json, glob

PROSTOTA = ['R0', 'R1_24', 'R1_36', 'R2', 'R9', 'R6', 'R3', 'R4', 'R10', 'R11', 'R7', 'R5']
HOL = '2025-12→12м'


def f(x, k=2):
    return '—' if x is None else f'{x:.{k}f}'.replace('.', ',')


def main(d):
    R = {}
    for p in sorted(glob.glob(os.path.join(d, 'e8_*.json'))):
        r = json.load(open(p, encoding='utf-8'))
        R[(r['вид'], r['_набір'])] = r
    vydy = sorted({k[0] for k in R}, key=lambda v: (('_' in v), v))
    print('# Е8 — перевірка на наших даних: таблиці\n')
    any_ = next(iter(R.values()), {})
    print(f"Набір 36.14: подій у розрахунках {any_.get('_подій_у_розрахунках', '?'):,}; остання дата "
          f"{any_.get('_остання_дата', '?')}. Головний зріз — ознаки до 12.2025, події 2026 (відомі місяці).\n")
    print('PAI — на 10% довжини (точка = 50 м); [межі] — бутстреп блоками 1 км, 500 повторів; '
          'сер. — середнє PAI10 по всіх зрізах і горизонтах; Спірмен — ранги 06.2025 і 12.2025; '
          'M — частка показаних, де подій у межах M/2…2M; перекіс — середній |ln| (частка довжини ÷ частка подій) по районах.\n')
    verdikt = []
    for v in vydy:
        r = R.get((v, '36_14'))
        if not r: continue
        for odin in ('лінії', 'точки'):
            o = r.get(odin) or {}
            if 'пропущено' in o or not o:
                print(f"\n### {r['назва']} — {odin}: {o.get('пропущено', 'немає')}\n"); continue
            t = o['E1_E2']
            hk = r.get('головний', HOL)
            hol = t.get(hk) or t.get(sorted(t)[-1])
            # зрізи з позначкою (моделі навчено на неповному 2024) у середнє не йдуть
            pz = r.get('позначки') or {}
            t_ok = {z: v for z, v in t.items() if z.split('→')[0] not in pz}
            if pz: print(f"\n_{r['назва']}: історія {r.get('історія_міс')} міс.; зрізи {', '.join(pz)} — {next(iter(pz.values()))}, у середнє не йдуть (неповний 2024)._")
            print(f"\n### {r['назва']} — {odin} (головний зріз {hk}, подій у перевірці {hol['подій']}; R2 — {o['R2_ширина_основа']}, "
                  f"R9 — {o['R9_ширина']} м{', R7 з ' + o['R7_з'] if o.get('R7_з') else ''})\n")
            print('| Підхід | PAI 1% | PAI 5% | PAI 10% | [межі] | PAI 20% | PEI 10% | сер. PAI10 (зрізів) | Δ з R0 | Δ з R2 | Спірмен | Жаккар 5% | M | перекіс |')
            print('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
            rows = {}
            for a in PROSTOTA:
                if a not in hol: continue
                e = hol[a]
                vals = [t_ok[z][a]['10']['PAI'] for z in t_ok if a in t_ok[z]]
                b = o['E3'].get(a, {}); s = o['E4'].get(a, {}); m = o['E5'].get(a, {}); p = o['E7'].get(a, {})
                dd = lambda k: ('[' + ', '.join(f(x) for x in b[k]) + ']') if k in b else '—'
                rows[a] = dict(pai=e['10']['PAI'], lo=b.get('lo'), sp=s.get('Спірмен'))
                if not vals: vals = [e['10']['PAI']]
                print(f"| {a} | {f(e['1']['PAI'])} | {f(e['5']['PAI'])} | **{f(e['10']['PAI'])}** | "
                      f"{f(b.get('lo'))}–{f(b.get('hi'))} | {f(e['20']['PAI'])} | {f(e['10']['PEI'])} | "
                      f"{f(sum(vals) / len(vals))} ({len(vals)}) | {dd('різниця_з_R0')} | {dd('різниця_з_R2')} | "
                      f"{f(s.get('Спірмен'))} | {f(s.get('Жаккар_5'))} | {f(m.get('частка_M'))} | {f(p.get('сер_лог'))} |")
            if not rows: continue
            best = max(rows, key=lambda a: rows[a]['pai'])
            lo, sp = rows[best]['lo'] or rows[best]['pai'], rows[best]['sp']
            win = next(a for a in PROSTOTA if a in rows and rows[a]['pai'] >= lo
                       and (sp is None or rows[a]['sp'] is None or rows[a]['sp'] >= sp - 0.05))
            verdikt.append((r['назва'], odin, best, rows[best]['pai'], win, rows[win]['pai'], r.get('проактивний'),
                            (o['E7'].get(win) or {}).get('сер_лог')))
            if 'захід_схід' in o:
                z = o['захід_схід']
                print(f"\nЗахід → схід ({z['подій']} подій): " + ', '.join(f"{a} {f(z[a]['10']['PAI'])}" for a in ('R0', 'R2', 'R3', 'R4')))
            if 'R12' in o:
                q = o['R12']
                if 'пропущено' in q: print(f"\nR12 (1551): {q['пропущено']}")
                else:
                    dd = q['E3'].get('R12', {}).get('різниця_з_R3')
                    print(f"\nR12 (1551, вікна {q['вікна'][2][0]}–{q['вікна'][3][1]}, {q['подій_перевірки']} подій): "
                          f"R3 {f(q['R3']['10']['PAI'])}, R12 {f(q['R12']['10']['PAI'])}, Δ [{', '.join(f(x) for x in dd) if dd else '—'}]; "
                          f"обрано: {', '.join(q['обрано_1551']) or 'нічого'}")
            e6 = o.get('E6') or {}
            for a in ('R3', 'R10', 'R11'):
                if a in e6:
                    print(f"\nE6 {a}: спільних між зрізами {e6[a]['спільних_усіх']} з {e6[a]['обраних_разом']}; "
                          + '; '.join(f"{T}: {', '.join(v) or '—'}" for T, v in e6[a]['за_зрізами'].items()))
            if 'R5_топ10' in e6:
                print(f"\nE6 R5: спільних у топ-10 важливості між зрізами — {e6['R5_топ10']['спільних_усіх']}")
        if r.get('разом'):
            print(f"\nЛінії й точки разом (PAI 10%): " + ', '.join(f"{a} {f(x['10']['PAI'])}" for a, x in r['разом'].items()))
        if r.get('10_вулиць_R2_R3'):
            print('\n10 відрізків, де R2 і R3 розходяться найбільше: ' + '; '.join(
                f"{x['вулиця'] or x['відрізок']} (R2 {x['місце_R2']}, R3 {x['місце_R3']}; {x['подій_2025']}/{x['подій_2026']})"
                for x in r['10_вулиць_R2_R3']))

    print('\n## Вердикт — переможець для кожного виду\n')
    print('| Вид | Одиниці | Найкращий (PAI 10%) | Переможець за правилом | PAI 10% | Перекіс E7 |')
    print('|---|---|---|---|---|---|')
    for nm, odin, b, bp, w, wp, pro, pk in verdikt:
        print(f"| {nm}{' (проактивний)' if pro else ''} | {odin} | {b} ({f(bp)}) | **{w}** | {f(wp)} | {f(pk)} |")

    print('\n## Набір 36.14 проти чинного класу B (головний зріз, PAI 10%)\n')
    print('| Вид | Одиниці | Подій 36.14 / B | R0 | R2 | R3 |')
    print('|---|---|---|---|---|---|')
    for v in vydy:
        a, b = R.get((v, '36_14')), R.get((v, 'B'))
        if not (a and b): continue
        for odin in ('лінії', 'точки'):
            oa, ob = a.get(odin) or {}, b.get(odin) or {}
            ta, tb = (oa.get('E1_E2') or {}).get(a.get('головний', HOL)), (ob.get('E1_E2') or {}).get(b.get('головний', HOL))
            if not (ta and tb): continue
            c = lambda x: f"{f(ta[x]['10']['PAI'])} / {f(tb[x]['10']['PAI'])}" if x in ta and x in tb else '—'
            print(f"| {a['назва']} | {odin} | {ta['подій']} / {tb['подій']} | {c('R0')} | {c('R2')} | {c('R3')} |")


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'e8_vyhid'))
