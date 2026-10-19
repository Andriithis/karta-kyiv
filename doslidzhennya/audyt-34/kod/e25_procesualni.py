"""Е25 (VIDPOVID-38, п. 3): скільки «подій» — процесуальні постанови.

Форма «постанова» з дампу не завжди подія: виправлення описки, відстрочка
чи розстрочка штрафу, об'єднання справ, доля речових доказів, привід,
повернення протоколу. Адреси в них зазвичай немає, тож у воронці вони
осідають на «місця в тексті не знайдено». Повних текстів локально немає —
беремо випадкову вибірку цієї причини, тексти зі сторінки реєстру
(e25_teksty), і рахуємо частку за ознаками в перших 1500 знаках після
«ВСТАНОВИВ». Частку переносимо на всю причину по кожному виду.

Запуск: py -3 e25_procesualni.py [розмір вибірки, 200]
Вихід: kod/e25_vyhid/procesualni.md і procesualni_pryklady.txt.
"""
import os, re, csv, gzip, random, collections, sys, math
K = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, K)
import e25_voronka as V, e25_teksty as ET

# Ознаки процесуальної постанови — те, чим вона починається після
# «ВСТАНОВИВ»; список — з прочитаних 40 прикладів кроку 2
PROC = re.compile(r"описк|відстроч|розстроч|об['`’]?єдна\w*\s+(?:в|у)\s+одне\s+провадж|об['`’]?єднати|"
                  r"речов\w+\s+доказ|дол\w+\s+речов|застосовано\s+привід|застосувати\s+привід|"
                  r"поверну\w*\s+(?:до|на)\s+(?:доопрацюван|належн)|для\s+належного\s+оформлен|"
                  r"направ\w+\s+(?:за\s+підсудністю|для\s+розгляду\s+за\s+місцем)|роз['`’]?ясн\w+\s+постанов|"
                  r"виконанн\w+\s+постанов|зупин\w+\s+виконанн|закри\w+\s+провадженн\w+\s+.{0,40}строк\w*\s+накладенн",
                  re.I | re.S)


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    rows = [r for r in csv.DictReader(gzip.open(os.path.join(V.OUT, 'prychyny.tsv.gz'), 'rt', encoding='utf-8'), delimiter='\t')
            if r['prychyna'] == 'місця в тексті не знайдено']
    vsi = collections.Counter(r['vyd'] for r in rows)
    rnd = random.Random(38); rnd.shuffle(rows)
    vyb = rows[:n]
    so = collections.Counter(); proc = collections.Counter(); pr = []
    for r in vyb:
        t = re.sub(r'\s+', ' ', ET.tekst(r['doc_id']))
        m = re.search(r'встанови\w*|установи\w*', t, re.I)
        poch = t[(m.start() if m else 0):][:1500]
        p = bool(PROC.search(poch))
        so[r['vyd']] += 1; proc[r['vyd']] += p
        pr.append((p, r['doc_id'], r['vyd'], poch[:400]))
    o = ['## Процесуальні постанови серед «місця в тексті не знайдено»\n',
         f'Вибірка {n} з {len(rows):,} (випадкова, seed 38); частка — за ознаками в тексті.\n'.replace(',', ' '),
         '| Вид | у причині | у вибірці | процесуальних у вибірці | оцінка на всю причину |', '|---|---|---|---|---|']
    tot = 0
    for v in V.VYDY:
        if not vsi[v]: continue
        est = vsi[v] * proc[v] / so[v] if so[v] else 0
        tot += est
        o.append(f'| {v} | {vsi[v]:,} | {so[v]} | {proc[v]} | ~{est:,.0f} |'.replace(',', ' '))
    p = sum(proc.values()) / max(sum(so.values()), 1)
    se = math.sqrt(p * (1 - p) / max(sum(so.values()), 1))
    o.append(f'| усі | {len(rows):,} | {sum(so.values())} | {sum(proc.values())} ({100*p:.0f}% ± {196*se:.0f}) | ~{tot:,.0f} |'.replace(',', ' '))
    open(os.path.join(V.OUT, 'procesualni.md'), 'w', encoding='utf-8').write('\n'.join(o) + '\n')
    with open(os.path.join(V.OUT, 'procesualni_pryklady.txt'), 'w', encoding='utf-8') as fh:
        for p_, d, v, s in sorted(pr, key=lambda x: not x[0]):
            fh.write(f"{'ПРОЦ' if p_ else 'ПОДІЯ?'} | {d} | {v}\n   {s}\n")
    print('\n'.join(o))


if __name__ == '__main__':
    main()
