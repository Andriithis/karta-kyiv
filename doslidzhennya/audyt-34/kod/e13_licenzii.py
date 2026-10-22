# -*- coding: utf-8 -*-
"""Е13 / RISHENNYA 36.29: ліцензії на роздрібну торгівлю алкоголем (ДПС,
Register4.1, data.gov.ua fd69efae…) — Київ, геокодування тим самим ключем,
що й карта (adr_kliuch, 36.18.2), свіжість набору.

    py -3 doslidzhennya/audyt-34/kod/e13_licenzii.py <reg.csv>

Файл набору (42 МБ) у репозиторій не кладемо: його качають з data.gov.ua
(ресурс Register4.1_2022-02-23.csv). Заголовок файлу переплутаний: колонки
насправді NM;TIN;VDNM;LICNUM;LICBEG;LICEND;TRADEADDRESS — адреса остання,
дати перед нею (перевірено на перших рядках: «№0102…;06.09.2021;06.09.2022;
"УКРАЇНА, …"»). Вихід — e13_licenzii.json поруч.
"""
import csv, gzip, json, os, re, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, 'src'))
import adr_kliuch as AK

KYIV = re.compile(r'^\s*УКРАЇНА\s*,\s*М\.?\s*КИЇВ')
# Тип вулиці й назва до коми чи цифри, далі номер (з «буд.», «б.» чи без).
TYP = r'(вулиця|вул|проспект|просп|пр-кт|пр-т|пр|бульвар|бульв|б-р|провулок|пров|площа|пл|шосе|набережна|наб|узвіз|алея)'
# Номер: «24-а», «№24-а», «Б 72»; літера — лише окремою («12 ЛІТЕРА Б» — це 12).
NOM = r'(?:буд(?:инок)?\.?|б\.?)?\s*№?\s*(\d+(?:\s*-?\s*[А-ЯІЇЄA-Zа-яіїєa-z](?![А-ЯІЇЄA-Zа-яіїєa-z]))?(?:\s*/\s*\d+)?)(?!\d)'
VUL = re.compile(TYP + r'\.?\s*([^,0-9№(]+?)\s*,?\s*' + NOM, re.I)
# тип після назви: «Столичне шосе, буд.103», «Пирогівський шлях 169Г»
VUL2 = re.compile(r"(?:Р-Н|КИЇВ)\s*,?\s*(?:вулиця\s+)?([А-ЯІЇЄа-яіїє'’\- ]+?\s+(?:шосе|шлях|проспект|бульвар|провулок|площа|узвіз))\s*,?\s*" + NOM, re.I)
BN = re.compile(r'\bб/н\b', re.I)


def dmy(s):
    return s[6:10] + '-' + s[3:5] + '-' + s[:2]


def main(reg):
    rows = list(csv.reader(open(reg, encoding='utf-8'), delimiter=';'))[1:]
    beg_all = max(dmy(r[4]) for r in rows)
    k = [r for r in rows if KYIV.match(r[6].upper())]
    K = AK.Kliuch()
    # довідник точок: (ключ вулиці, номер) -> (шир, довг); OSM першим (S-А.4)
    tochky = {}
    for st, h, la, lo in json.load(open(os.path.join(AK.DATA, 'osm_kyiv_city.json'), encoding='utf-8')):
        tochky.setdefault((AK.skey(st), AK.nh(h.split()[0] if h else '')), (la, lo))
    with gzip.open(os.path.join(AK.DATA, 'geokoder_kmda.csv.gz'), 'rt', encoding='utf-8', newline='') as fh:
        for r in csv.DictReader(fh, delimiter='\t'):
            tochky.setdefault((AK.skey(r['street']), AK.nh(r['house'])), (float(r['lat']), float(r['lon'])))
    st = collections.Counter(); vyd = collections.Counter(); out = []; pryklady = collections.defaultdict(list)
    for r in k:
        a = r[6]
        vyd[r[2]] += 1
        m = VUL.search(a)
        m2 = VUL2.search(a) if not m or m.group(2).strip().upper() in ('ШОСЕ', 'ШЛЯХ') else None
        if m2: vul, nom = m2.group(1).strip(), re.sub(r'\s+', '', m2.group(2))
        elif m: vul, nom = f'{m.group(1)} {m.group(2).strip()}', re.sub(r'\s+', '', m.group(3))
        else:
            pr = 'б/н' if BN.search(a) else 'вулицю з номером не розібрано'
            st[pr] += 1; pryklady[pr].append(a); continue
        kl, pravylo = K.rozibraty(vul)
        p = tochky.get((kl, AK.nh(nom)))
        if p is None:
            pr = 'вулиці немає в довіднику' if pravylo is None else 'будинку немає в довіднику'
            st[pr] += 1; pryklady[pr].append(a); continue
        st['точка будинку'] += 1
        out.append([round(p[0], 6), round(p[1], 6), r[2], dmy(r[4]), dmy(r[5])])
    n = len(k)
    zvit = dict(
        dzherelo='data.gov.ua fd69efae-fd6a-445d-88a1-7b8aeff0c07b, Register4.1_2022-02-23.csv',
        riadkiv=len(rows), kyiv=n, najnovisha_licenziia_vsia_ukraina=beg_all,
        najnovisha_licenziia_kyiv=max(dmy(r[4]) for r in k),
        dijut_na_22_10_2026=sum(dmy(r[5]) >= '2026-10-22' for r in k),
        rozklad=dict(st.most_common()), chastka_z_budynkom=round(st['точка будинку'] / n, 3) if n else 0,
        vydy=dict(vyd.most_common()), pryklady={k_: v[:20] for k_, v in pryklady.items()})
    json.dump(dict(zvit=zvit, tochky=out), open(os.path.join(HERE, 'e13_licenzii.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(json.dumps({k_: v for k_, v in zvit.items() if k_ != 'pryklady'}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main(sys.argv[1])
