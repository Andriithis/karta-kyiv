"""Е12, П1: частка хибних подій на топ-100 точках живої карти.

Ручна розмітка 496 рішень (по 5 на точку, наосліп щодо точки) показала один
тип помилки, що збирається в точках, — кілометр траси як номер будинку
(«Харківське шосе, 19 км» → точка «Харківське шосе, 19»). Інших помилок
у вибірці — поодинокі. Тож рахуємо по ВСІХ рішеннях кожної точки ті самі
ознаки, що й набір 36.14 (км, чуже місто, роль адреси), плюс ручні позначки.
"""
import os, re, csv, gzip, glob, json, collections, sys
K = os.path.dirname(os.path.abspath(__file__))
R = os.path.abspath(os.path.join(K, '..', '..', '..'))
sys.path.insert(0, K); sys.path.insert(0, os.path.join(R, 'src'))
import e12_nabir as N
from e12_p1_vybirka import kl, top, T, po

# ручні позначки розмітки П1 (решта 496 — «місце події», див. E12-adresy.md)
RUCHNI = {
    '131470878': 'км', '131521158': 'км', '125778884': 'км', '129413496': 'км',
    '124601608': 'км', '134482557': 'км',
    '134035366': 'протокол і подія в одному реченні',
}
rows = []
for i, p in enumerate(top, 1):
    st, _, hn = p[2].rpartition(', ')
    ds = po.get(kl(st, hn), [])
    c = collections.Counter()
    for d in ds:
        r = T[d]
        km, misto = N.km_misto(r['addr_sentence'], r['house'])
        v, why = N.nov_klas(r['addr_sentence'], r['level'])
        if km: c['км'] += 1
        elif misto: c['чуже місто'] += 1
        elif not v: c['роль'] += 1
    bad = sum(c.values())
    rows.append((i, p[2], len(p[4]), len(ds), bad, round(bad / len(ds), 3) if ds else 0, dict(c)))
pod = sum(r[2] for r in rows)
bad_w = sum(r[2] * r[5] for r in rows)
print(f'топ-100: подій на карті {pod:,}; хибних (зважено на події точки) {bad_w:,.0f} = {100 * bad_w / pod:.1f}%')
print('точки з хибними > 20%:')
for r in rows:
    if r[5] > 0.2: print('  ', r)
print('точки з хибними 5–20%:')
for r in rows:
    if 0.05 < r[5] <= 0.2: print('  ', r)
with open(os.path.join(K, 'e12_p1_top100.tsv'), 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f, delimiter='\t')
    w.writerow(['mistse', 'adresa', 'podii_na_karti', 'rishen_u_prokhodi', 'khybnykh', 'chastka', 'chomu'])
    w.writerows(rows)
print('ручних позначок не «місце події»:', len(RUCHNI), 'з 496')
