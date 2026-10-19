"""Е25, крок 2 (ZAVDANNYA-38): нижня частина воронки — точка, карта,
проблеми, ризик — на свіжій базі (workflow «Е25 — воронка»).

Локальна events.db відстає від проходу по текстах (точки старі, нових
документів немає), тож ці чотири кроки рахуються лише тут, після кроків 1–2
тим самим кодом, що й «Оновлення карти». Код карти не міняємо: збираємо
карту в тимчасову теку й лише перехоплюємо, що пішло у відбір проблем.

Вихід: $OUT/mapa.tsv.gz — doc_id, точність точки, на карті, у проблемі, у
ризику. e25_voronka.py підхоплює його, якщо файл лежить у kod/e25_vyhid/.
"""
import os, sys, csv, gzip, sqlite3, collections
K = os.path.dirname(os.path.abspath(__file__))
R = os.path.abspath(os.path.join(K, '..', '..', '..'))
sys.path.insert(0, os.path.join(R, 'src'))
import labels as L, podii as PD
import step3_map as S3, map_problems as MP
OUT = os.environ.get('OUT') or os.path.join(K, 'e25_vyhid')


def main():
    os.makedirs(OUT, exist_ok=True)
    c = sqlite3.connect(os.path.join(R, 'data', 'events.db'))
    geo = dict(c.execute('select doc_id, precision from geo'))

    # DOCIDX (doc -> точка, подія) і точки з проблемами — те, що бачить
    # map_problems.select; підміняємо лише на час збірки
    cap = {}
    orig = MP.select
    def select(*a):
        cap['DOCIDX'] = a[-1]
        res = orig(*a)
        cap['P'] = res[0]
        return res
    S3.map_problems.select = select
    S3.main(out=os.path.join(OUT, '_karta', 'index.html'))
    P, DOCIDX = cap['P'], cap['DOCIDX']
    zvorot = {v: d for d, v in DOCIDX.items()}
    karta = {d for d, (pi, k) in DOCIDX.items() if P[pi][3]}
    probl = set()
    for pi, p in enumerate(P):
        probs = p[7] if len(p) > 7 and isinstance(p[7], list) else []
        for q in probs:
            # події проблеми — q['ev'] (усі її адреси); старий запис без ev —
            # події точки тих статей, що в проблемі (так само step6_zvity)
            labs = {a for a, _n in q.get('arts', [])}
            refs = [tuple(x) for x in q.get('ev') or []] or \
                   [(pi, j) for j, e in enumerate(p[4]) if S3.LAST_KARTA['labels'][e[1]][1] in labs]
            probl.update(zvorot[r] for r in refs if r in zvorot)

    # Ризик — той самий відбір, що step4_engine.podii (клас B, точне місце
    # або вулиця, є місяць події). Повторено тут, бо podii не віддає doc_id.
    # step4_engine не імпортуємо: він тягне numpy/statsmodels заради однієї
    # множини; TOCHNE — та сама, що там.
    TOCHNE = {'house', 'cross'}
    V = S3.LAST_VYBIR
    ryz = set()
    for r in V['rows']:
        if PD.theme(r[2]) not in L.ORDER: continue
        tk = V['TKD'].get(r[0]) or {}
        if tk.get('klass') != 'B': continue
        if r[9] not in TOCHNE and r[9] != 'street': continue
        if len((S3.ev_date(tk, r[3]) or r[3] or '')[:10]) < 7: continue
        ryz.add(r[0])

    with gzip.open(os.path.join(OUT, 'mapa.tsv.gz'), 'wt', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh, delimiter='\t')
        w.writerow(['doc_id', 'precision', 'karta', 'problema', 'ryzyk'])
        for d in sorted(set(geo) | karta | ryz, key=int):
            w.writerow([d, geo.get(d, ''), int(d in karta), int(d in probl), int(d in ryz)])
    print(f'точок: {len(geo):,}; на карті: {len(karta):,}; у проблемах: {len(probl):,}; у ризику: {len(ryz):,}')
    print('у проблемах за видами:', collections.Counter(PD.theme(x) for x in
          (dict(c.execute('select doc_id, cat from events')).get(d, '') for d in probl)).most_common())


if __name__ == '__main__':
    main()
