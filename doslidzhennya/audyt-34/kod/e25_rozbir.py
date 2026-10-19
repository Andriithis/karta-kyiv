"""Е25, крок 3 (ZAVDANNYA-38): скільки точок повертає кращий розбір місця.

Код карти не міняємо — лише міряємо. Беремо події воронки (e25_voronka,
prychyny.tsv.gz), що відпали на «лише вулиця без номера» чи «місця в тексті
не знайдено», і шукаємо в описі (фабула проходу, а без неї — речення
адреси) те, що чинний розбір (addr.py) пропустив:

  А. адреса з номером — широким шаблоном: будь-яке скорочення типу,
     назва з лапками, номер без коми; і чому чинний розбір її не взяв
     (скорочення, лапки, «брудний» контекст, тип після назви, без типу);
  Б. перехрестя — «на перехресті X та/з Y», «X / Y», «X … на перехресті з Y»;
  В. названі об'єкти — метро, ТЦ/ТРЦ, АЗС, міст, шляхопровід, паркінг,
     ринок, вокзал, зупинка;
  Г. лише вулиця — чи є така вулиця у вуличній мережі (на відрізок).

Знайдену адресу звіряємо з довідником адрес (OSM + КМДА) тим самим ключем,
що й геокодер (step2_geocode.norm, nh): «є в довіднику» — нижня межа
точок, які дасть розбір; решта — питання ключа геокодера, не тексту.

Вихід: kod/e25_vyhid/rozbir.md і rozbir_pryklady.txt (по 20 на клас).
"""
import os, re, csv, gzip, json, random, collections, sys
K = os.path.dirname(os.path.abspath(__file__))
R = os.path.abspath(os.path.join(K, '..', '..', '..'))
sys.path.insert(0, os.path.join(R, 'src')); sys.path.insert(0, K)
import addr as A, step2_geocode as G
import e25_voronka as V
csv.field_size_limit(10**9)
OUT = V.OUT
D = os.path.join(R, 'data')

# Тип вулиці — ширше, ніж addr.TYPES: усе, що траплялося в протоколах.
# «пр-кт», «пр.-кт», «напр-т»? — ні: «напр.» у протоколах — «напрямок».
TYP = (r"вул(?:иц\w*)?\.?|в\.|просп\w*\.?|пр-?к?т\w*\.?|пр\.\s*-?\s*к?т\w*\.?|п-т\w*\.?|пр\.|пр-ту|"
       r"бульв\w*\.?|б-р\w*\.?|бул\.?|б\.|пров\w*\.?|пл(?:ощ\w*|\.)|шосе|наб\w*\.?|узв\w+|проїзд\w*|"
       r"майдан\w*|але[яїю]|тупик\w*|дорог\w+")
# Назва: 1–4 слова з великої (або ініціал), лапки й дефіси всередині
NAZ = r"(?:[«\"„“]?[А-ЯІЇЄҐ0-9][\w'’`\-\.]*[»\"“”]?\s+){0,3}[«\"„“]?[А-ЯІЇЄҐ][\w'’`\-]*[»\"“”]?"
NOM = r"(?:,\s*|\s+)(?:(?:буд(?:инок|инку|\.)?|б\.)\s*)?№?\s*(\d{1,4}(?:\s*[/\-]\s*\d{1,3})?(?:-?[А-ЯA-Zа-я](?![а-яА-Я]))?)(?!\s*(?:км|год|хв|м\b|грн|років|р\.|року))"
SHYR_A = re.compile(rf"\b({TYP})\s*({NAZ}){NOM}", re.U)
SHYR_B = re.compile(rf"\b((?:[А-ЯІЇЄҐ][\w'’\-]+\s+){{0,2}}[А-ЯІЇЄҐ][\w'’\-]+)\s+(вулиц\w*|проспект\w*|бульвар\w*|провулк?\w*|"
                    rf"шосе|площ\w*|набережн\w*|узвоз\w*|узвіз){NOM}", re.U)
# Адреса без типу: «м. Київ, Джона Маккейна, 2» / «Джона Маккейна (Івана Кудрі), 2»
SHYR_C = re.compile(rf"\bм\.\s*Ки[їє]в\w*\s*,\s*({NAZ})(?:\s*\([^)]{{1,40}}\))?{NOM}", re.U)
PEREKH = re.compile(rf"перехрест\w*\s+(?:(?:вулиць|вулиці)\s+)?(?:({TYP})\s*)?({NAZ})\s*(?:та|і|й|з|із|/)\s*(?:({TYP})\s*)?({NAZ})"
                    rf"|\b({TYP})\s*({NAZ})\s*/\s*(?:({TYP})\s*)?({NAZ})", re.U)
OBJ = [
    ('метро', re.compile(r"(?:\bст\.?\s*м\.?|станці\w+\s+(?:метро(?:політену)?|м\.)|\bметро)\s*[«\"]?\s*([А-ЯІЇЄҐ][\w'’\-]+(?:\s+[А-ЯІЇЄҐ][\w'’\-]+)?)", re.U)),
    ('ТЦ', re.compile(r"\b(?:ТРЦ|ТЦ|торгов\w+\s+(?:центр\w*|комплекс\w*))\s*[«\"]\s*([^»\"]{2,40})[»\"]", re.U)),
    ('АЗС', re.compile(r"\bАЗС\b|\bавтозаправ\w+", re.U)),
    ('міст', re.compile(r"\b([А-ЯІЇЄҐ][\w'’\-]+)\s+(?:мост\w*|міст)\b|\bмост\w*\s+[«\"]?([А-ЯІЇЄҐ][\w'’\-]+)", re.U)),
    ('шляхопровід', re.compile(r"шляхопровід|шляхопровод\w+|естакад\w+|розв'?язк\w+", re.I | re.U)),
    ('паркінг', re.compile(r"паркінг\w*|парковк\w+|автостоянк\w+|стоянц\w+", re.I | re.U)),
    ('ринок', re.compile(r"\bринк?\w*\s*[«\"]?[А-ЯІЇЄҐ]|\b[А-ЯІЇЄҐ][\w'’\-]+(?:ого|ому|ий)\s+ринк\w*", re.U)),
    ('вокзал', re.compile(r"вокзал\w*", re.I | re.U)),
    ('зупинка', re.compile(r"зупинк\w+\s+(?:громадськ\w+\s+транспорт\w*\s+)?[«\"]\s*[А-ЯІЇЄҐ]", re.U)),
]


def dovidnyk():
    """Ключі адрес (назва без типу, номер) з OSM і переліку КМДА."""
    S = set()
    for st, h, *_ in json.load(open(os.path.join(D, 'osm_kyiv_city.json'), encoding='utf-8')):
        S.add((G.norm(st), G.nh(h)))
    with gzip.open(os.path.join(D, 'geokoder_kmda.csv.gz'), 'rt', encoding='utf-8') as fh:
        for r in csv.DictReader(fh, delimiter='\t'):
            S.add((G.norm(r['street']), G.nh(r['house'])))
    return S


def vulytsi():
    """Назви вулиць мережі (network.json) — для «лише вулиця» на відрізок."""
    N = json.load(open(os.path.join(D, 'network.json'), encoding='utf-8'))
    out = set()
    for it in N.get('items', []):
        for k in ('name', 'n', 'nazva', 'street'):
            if isinstance(it, dict) and it.get(k): out.add(G.norm(it[k]))
        if isinstance(it, list):
            for x in it:
                if isinstance(x, str) and re.search('[а-яі]', x): out.add(G.norm(x))
    return out


def adresa(typ, naz, nom):
    """(вулиця в називному, номер) за правилами addr — щоб ключ був той самий."""
    naz = re.sub(r"[«»\"„“”]", '', naz).strip()
    t = typ
    for rx, canon in ((r'^пр\.?\s*-?\s*к?т|^пр-?к?т|^п-т|^пр\.|^пр-ту|^просп', 'просп.'), (r'^б-р|^бул|^б\.|^бульв', 'бульв.'),
                      (r'^в\.|^вул', 'вул.'), (r'^пров', 'пров.'), (r'^пл', 'пл.'), (r'^наб', 'наб.')):
        if re.match(rx, typ or '', re.I): t = canon; break
    s = A._street(t or 'вул.', naz) if t in [c for _, c in A.TYPES] else A._street('вул.', naz)
    return s, A.norm_house(nom)


def chomu(fab, typ, naz, m0, sa):
    """Чому addr.py не взяв адресу, яку бачить широкий шаблон."""
    if not re.fullmatch(A.TYPE_RE, typ or ''): return 'скорочення типу «' + (typ or '').strip() + '»'
    if re.search(r"[«\"„“]", naz): return 'лапки в назві'
    # без фільтра контексту чинний шаблон бачить — значить, відкинув контекст
    for t, n, h, p in A.find_all(fab):
        if abs(p - m0) < 5 and h: return 'відкинув контекст (суд, поліція, житло поруч)'
    return 'інше (назва, номер)'


def main():
    rows = list(csv.DictReader(gzip.open(os.path.join(OUT, 'prychyny.tsv.gz'), 'rt', encoding='utf-8'), delimiter='\t'))
    T = V.teksty()
    DV = dovidnyk(); VUL = vulytsi()
    cnt = collections.defaultdict(collections.Counter)
    pr = collections.defaultdict(list)
    for r in rows:
        if r['prychyna'] not in ('лише вулиця без номера', 'місця в тексті не знайдено'): continue
        v, d = r['vyd'], r['doc_id']
        t = T.get(d) or {}
        fab = A.fix_typos('ВСТАНОВИВ: ' + (t.get('fab') or t.get('addr_sentence') or ''))
        vul = r['prychyna'].startswith('лише')
        cnt[v]['усього: ' + r['prychyna']] += 1
        klas = None
        m = SHYR_A.search(fab) or SHYR_B.search(fab) or SHYR_C.search(fab)
        if m:
            if m.re is SHYR_A: typ, naz, nom = m.group(1), m.group(2), m.group(3)
            elif m.re is SHYR_B: typ, naz, nom = m.group(2), m.group(1), m.group(3)
            else: typ, naz, nom = '', m.group(1), m.group(2)
            s, h = adresa(typ, naz, nom)
            why = 'без типу вулиці' if m.re is SHYR_C else 'тип після назви' if m.re is SHYR_B else chomu(fab, typ, naz, m.start(), s)
            u = (G.norm(s or ''), G.nh(h)) in DV
            klas = f'А. номер — {why}'
            cnt[v][klas] += 1
            cnt[v]['А. номер — разом'] += 1
            cnt[v]['А. номер — є в довіднику'] += u
            pr[klas].append((d, v, f'{s}, {h} [{"є" if u else "немає"} у довіднику]', fab, m.start()))
        if not klas:
            m = PEREKH.search(fab)
            if m:
                klas = 'Б. перехрестя'
                cnt[v][klas] += 1
                pr[klas].append((d, v, m.group(0)[:80], fab, m.start()))
        if not klas:
            for nm, rx in OBJ:
                m = rx.search(fab)
                if m:
                    klas = 'В. об\'єкт — ' + nm
                    cnt[v][klas] += 1; cnt[v]['В. об\'єкт — разом'] += 1
                    pr[klas].append((d, v, m.group(0)[:60], fab, m.start()))
                    break
        if not klas and vul:
            st = t.get('street') or ''
            na = G.norm(st) in VUL if VUL else None
            klas = 'Г. лише вулиця — ' + ('є в мережі (на відрізок)' if na else 'немає в мережі' if na is False else 'мережа без назв')
            cnt[v][klas] += 1
            pr[klas].append((d, v, st, fab, 0))
        if not klas:
            cnt[v]['Д. нічого не знайдено'] += 1
            pr['Д. нічого не знайдено'].append((d, v, '', fab, 0))

    vydy = [x for x in V.VYDY if cnt[x]] + ['усі']
    tot = sum((cnt[x] for x in V.VYDY), collections.Counter())
    keys = sorted(tot, key=lambda k: (k[:2], -tot[k]))
    o = ['## Що повертає кращий розбір місця (події «лише вулиця» і «місця не знайдено»)\n',
         '| Клас | ' + ' | '.join(vydy) + ' |', '|---' * (len(vydy) + 1) + '|']
    for k in keys:
        o.append(f'| {k} | ' + ' | '.join(f'{(tot if x == "усі" else cnt[x])[k]:,}'.replace(',', ' ') for x in vydy) + ' |')
    open(os.path.join(OUT, 'rozbir.md'), 'w', encoding='utf-8').write('\n'.join(o) + '\n')
    rnd = random.Random(38)
    with open(os.path.join(OUT, 'rozbir_pryklady.txt'), 'w', encoding='utf-8') as fh:
        for k, xs in sorted(pr.items()):
            xs = list(xs); rnd.shuffle(xs)
            fh.write(f'\n######## {k} — {len(xs):,}\n')
            for d, v, what, fab, p in xs[:20]:
                fh.write(f'{d} | {v} | {what}\n   …{re.sub(r"\s+", " ", fab[max(0, p - 120):p + 220])}…\n')
    print('\n'.join(o))


if __name__ == '__main__':
    main()
