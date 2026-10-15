# -*- coding: utf-8 -*-
"""Е12б (ZAVDANNYA-36): розклад набору 36.14 до точки, А3 — повнота, А4 —
пошук, А5 — відмінки. Код карти не чіпаємо: тут — копії правил з
виправленнями, які йдуть у першу хвилю (не в src/).

Виправлення в копіях (вказівка центрального чату 15.10):
  * norm() — тип вулиці вирізаємо лише цілим словом: у step2_geocode.norm
    шаблон без меж слова ріже «наб»/«пров» усередині назви («Газопровідна»
    -> «газо ідна»; 82 назви, різні вулиці не злипаються);
  * перейменування з 1551 («нова (стара)») відкидаємо лише тоді, коли стара
    назва чинна в OSM, а не будь-де в КМДА: КМДА ще тримає старі назви
    (154 вулиці, «проспект Перемоги»).

Запуск: python e12b_adresy.py <тека даних зі свіжими events.db,
nabir_36_14.csv.gz і 1551/> [rozklad|a3|a4|a5 ...]
"""
import os, sys, re, csv, gzip, json, math, time, glob, random, sqlite3, collections
K = os.path.dirname(os.path.abspath(__file__))
R = os.path.abspath(os.path.join(K, '..', '..', '..'))
sys.path.insert(0, os.path.join(R, 'src'))
import step2_geocode as G
csv.field_size_limit(10 ** 9)

TYPEWORDS = (r'(?<![а-яіїєґ])(вулиця|вулиці|вулицю|вул\.?|проїзд\w*|проспект[уі]?|просп\.?|пр-т|пр\.|'
             r'бульвар[уі]?|бульв\.?|б-р|провулок|провулку|пров\.?|площа|площі|пл\.?|шосе|набережна|'
             r'набережної|наб\.?|узвіз|узвозу|алея|алеї|тупик|тракт|мікрорайон)(?![а-яіїєґ])')


def norm(s):
    """step2_geocode.norm з межами слова для типу вулиці"""
    if not s: return ''
    s = s.lower().replace('’', "'").replace('`', "'").replace('ʼ', "'")
    s = re.sub(TYPEWORDS, ' ', s)
    s = re.sub(r"[^а-яіїєґ0-9' \-]", ' ', s)
    s = s.replace('-', ' ').replace("'", '')
    return re.sub(r'\s+', ' ', s).strip()


def skey(s): return ' '.join(sorted(norm(s).split()))
def nh(h): return G.nh(h or '').replace('-', '')


# ---------------------------------------------------------------- довідник
class Dovidnyk:
    """Чинні назви й будинки OSM і КМДА; перейменування 1551; розгортання
    ініціалів — як adr_kliuch.Kliuch, але з правками вище."""
    def __init__(s, D1551):
        s.osm = json.load(open(os.path.join(R, 'data', 'osm_kyiv_city.json'), encoding='utf-8'))
        s.kmda = list(csv.DictReader(gzip.open(os.path.join(R, 'data', 'geokoder_kmda.csv.gz'), 'rt', encoding='utf-8'), delimiter='\t'))
        s.full_osm = {skey(r[0]) for r in s.osm} - {''}
        s.full_kmda = {skey(r['street']) for r in s.kmda} - {''}
        s.full = s.full_osm | s.full_kmda
        s.bud = collections.defaultdict(list)          # (ключ, номер) -> [(la, lo, джерело)]
        for st, h, la, lo in s.osm: s.bud[(skey(st), nh(h))].append((la, lo, 'osm'))
        for r in s.kmda: s.bud[(skey(r['street']), nh(r['house']))].append((float(r['lat']), float(r['lon']), 'kmda'))
        s.by_word = collections.defaultdict(set)
        for k in s.full:
            for w in k.split():
                if len(w) > 2: s.by_word[w].add(k)
        s.rename, s.rename_stara = {}, {}
        n_kmda_old = 0
        for f in sorted(glob.glob(os.path.join(D1551, 'lichylnyky-*.tsv.gz'))):
            for r in csv.DictReader(gzip.open(f, 'rt', encoding='utf-8'), delimiter='\t'):
                m = re.match(r'^(\S+)\s+(.+?)\s*\((.+)\)\s*$', r.get('vulytsya') or '')
                if not m: continue
                new, old = skey(f'{m.group(1)} {m.group(2)}'), skey(f'{m.group(1)} {m.group(3)}')
                if old and new and old != new:
                    # чинна (adr_kliuch: будь-де в довіднику) -> лише OSM (поправка 15.10)
                    if old not in s.full_osm: s.rename[old] = new
                    if old not in s.full: s.rename_stara[old] = new
        s.n_rename_dodano = len(set(s.rename) - set(s.rename_stara))
        s.adr_dodano = sum(1 for r in s.kmda if skey(r['street']) in s.rename and skey(r['street']) not in s.rename_stara)
        s._c = {}

    def vulytsia(s, street):
        if street in s._c: return s._c[street]
        k = skey(street)
        if k in s.rename: k = s.rename[k]
        ws = k.split()
        ini = [w for w in ws if len(w) <= 2]
        if ini and k not in s.full:
            rest = [w for w in ws if len(w) > 2]
            if rest:
                cand = set.intersection(*(s.by_word.get(w, set()) for w in rest))
                cand = [c for c in cand if len(c.split()) == len(ws)
                        and all(any(x.startswith(i) and len(x) > 2 for x in c.split()) for i in ini)]
                if len(cand) == 1: k = cand[0]
        s._c[street] = k
        return k


# ---------------------------------------------------------------- відмінки
ZAKIN = [('ській', ('ська',)), ('цькій', ('цька',)), ('зькій', ('зька',)), ('ній', ('на', 'ня')),
         ('ій', ('а', 'я')), ('ському', ('ський', 'ське')), ('цькому', ('цький', 'цьке')),
         ('ому', ('ий', 'е', 'ій')), ('ім', ('ий',)), ('ці', ('ка',)), ('зі', ('га',)), ('сі', ('ха',)),
         ('і', ('а', 'я'))]


def nazyvnyi(k, full):
    """ключ (слова за абеткою) -> варіанти в називному, що є в довіднику; сама
    форма в довіднику — не відмінок («Верхній Вал» лишається)"""
    if k in full: return []
    ws = k.split(); out = []
    import itertools
    ch = []
    for w in ws:
        v = [w]
        for z, nz in ZAKIN:
            if w.endswith(z) and len(w) > len(z) + 2:
                v += [w[:-len(z)] + e for e in nz]; break
        ch.append(v)
    for comb in itertools.product(*ch):
        nn = ' '.join(sorted(comb))
        if nn != k and nn in full and nn not in out: out.append(nn)
    return out


# ---------------------------------------------------------------- розклад
def rozklad(DD, Dv):
    """Набір 36.14 -> подія карти -> дата -> точка -> у розрахунках Е8.
    Для подій без точки — чому: вулиці немає в довіднику / будинку немає /
    база чи інтерполяція (у розрахунки не йдуть) / відсіяно картою."""
    import step3_map as S3, labels as L, podii as PD
    NB = {r['doc_id']: r for r in csv.DictReader(gzip.open(os.path.join(DD, 'nabir_36_14.csv.gz'), 'rt', encoding='utf-8'))}
    v1 = {d for d, r in NB.items() if r['v_rozrakhunkakh'] == '1'}
    c = sqlite3.connect(os.path.join(DD, 'events.db'))
    cat = dict(c.execute('select doc_id, cat from events'))
    geo = {r[0]: r[1:] for r in c.execute('select doc_id, lat, lon, precision, source from geo')}
    V = S3.vybir(c, print=lambda *a, **k: None)
    rows = {r[0]: r for r in V['rows']}
    out = collections.Counter(); prych = collections.Counter(); po_vydu = collections.defaultdict(collections.Counter)
    for d in v1:
        th = PD.theme(cat.get(d, ''))
        if th not in L.ORDER: out['0 поза сімома видами'] += 1; continue
        out['1 у наборі, сім видів'] += 1
        g = geo.get(d)
        pr = g[2] if g else None
        if pr in ('house', 'cross'):
            out['2 з точним будинком чи перехрестям (геокодування)'] += 1
            if d in rows:
                out['3 подія карти (після злиття справ, установ, дати від 2023)'] += 1
                tk = V['TKD'].get(d) or {}
                dd = (S3.ev_date(tk, rows[d][3]) or rows[d][3] or '')[:10]
                if len(dd) >= 7: out['4 з місяцем події — у розрахунках Е8'] += 1; po_vydu[th]['в Е8'] += 1
                else: out['4- без дати'] += 1
            else:
                prych['відсіяно картою: інший документ справи, установа, дата до 2023, площа без номера'] += 1
            continue
        po_vydu[th]['без точки'] += 1
        r = NB[d]
        k = Dv.vulytsia(r['street']) if r['street'] else ''
        if pr in ('base', 'interp'):
            prych[f'точка «{pr}» (сусідній будинок) — у розрахунки не йде'] += 1
        elif not k or not r['house']:
            prych['немає вулиці чи номера в адресі'] += 1
        elif k not in Dv.full:
            kn = nazyvnyi(k, Dv.full)
            prych['назва вулиці не збіглася з довідником' + (' — відмінок, називний є' if kn else '')] += 1
        elif (k, nh(r['house'])) not in Dv.bud:
            prych['вулиця є, будинку з таким номером в OSM/КМДА немає'] += 1
        else:
            prych['адреса є в довіднику, а точки немає (ключ геокодера не збігся)'] += 1
    print(f'набір 36.14: документів {len(NB):,}, у розрахунках (v=1) {len(v1):,}')
    for k_, v in sorted(out.items()): print(f'  {k_}: {v:,}')
    print('без точки на карті й відсіяні — чому:')
    for k_, v in prych.most_common(): print(f'  {v:7,}  {k_}')
    print('за видами (у Е8 / без точки):', {k_: dict(v) for k_, v in po_vydu.items()})
    return dict(etapy=dict(out), prychyny=dict(prych), po_vydu={k_: dict(v) for k_, v in po_vydu.items()})


# ---------------------------------------------------------------- А3
def a3(P, Dv):
    """Скільки адрес довідника клікабельні на карті зараз і скільки КБ дасть
    перелік усіх адрес."""
    na_karti = set()
    for p in P:
        m = re.match(r'^(.+?),\s*(.+)$', p[2] or '')
        if p[3] == 1 and m: na_karti.add((Dv.vulytsia(m.group(1)), nh(m.group(2))))
    kmda = {(Dv.vulytsia(r['street']), nh(r['house'])) for r in Dv.kmda}
    osm = {(Dv.vulytsia(st), nh(h)) for st, h, _a, _b in Dv.osm}
    vsi = kmda | osm
    res = dict(адрес_на_карті=len(na_karti), КМДА=len(kmda), OSM=len(osm), разом=len(vsi),
               КМДА_клікабельні=len(kmda & na_karti), OSM_клікабельні=len(osm & na_karti),
               разом_клікабельні=len(vsi & na_karti), на_карті_поза_довідником=len(na_karti - vsi),
               перейменувань_1551=len(Dv.rename), з_них_додано_поправкою=Dv.n_rename_dodano,
               адрес_КМДА_під_старою_назвою=Dv.adr_dodano)
    # вага: [lat, lon, «вулиця, номер»] — рядок без подій; окремим файлом, бо
    # першого завантаження не має збільшувати (Е10)
    pts = {}
    for st, h, la, lo in Dv.osm: pts.setdefault((Dv.vulytsia(st), nh(h)), (la, lo, f'{st}, {h}'))
    for r in Dv.kmda: pts.setdefault((Dv.vulytsia(r['street']), nh(r['house'])), (float(r['lat']), float(r['lon']), f"{r['street']}, {r['house']}"))
    extra = [[round(a, 5), round(b, 5), t] for k, (a, b, t) in pts.items() if k not in na_karti]
    raw = json.dumps(extra, ensure_ascii=False, separators=(',', ':')).encode()
    import zlib
    gz = len(zlib.compress(raw, 9))
    # той самий перелік, поділений на клітинки ~2 км: підвантаження за масштабом
    cell = collections.defaultdict(list)
    for a, b, t in extra: cell[(int(a / 0.018), int(b / 0.028))].append([a, b, t])
    sz = sorted(len(zlib.compress(json.dumps(v, ensure_ascii=False).encode(), 9)) for v in cell.values())
    res.update(додати_адрес=len(extra), КБ_сирий=round(len(raw) / 1024), КБ_стиснутий=round(gz / 1024),
               клітинок_2км=len(cell), КБ_клітинка_медіана=round(sz[len(sz) // 2] / 1024, 1),
               КБ_клітинка_макс=round(sz[-1] / 1024, 1))
    for k_, v in res.items(): print(f'  {k_}: {v:,}' if isinstance(v, int) else f'  {k_}: {v}')
    return res


# ---------------------------------------------------------------- А4
TYPY_POVNI = {'вул': 'вулиця', 'просп': 'проспект', 'бульв': 'бульвар', 'пров': 'провулок', 'пл': 'площа',
              'наб': 'набережна', 'шосе': 'шосе', 'узвіз': 'узвіз', 'проїзд': 'проїзд', 'алея': 'алея'}


def zapyty(P, Dv, n=150, seed=36):
    """150 запитів, як пишуть люди: тип повністю, скорочено, без крапки, після
    назви; відмінок; стара назва; «12-а», «12 А», «12/2», «корп. 2»; помилка
    в літері; без типу. Ціль — адреса з карти (P з точкою)."""
    rnd = random.Random(seed)
    adr = []
    for i, p in enumerate(P):
        m = re.match(r'^((вул|просп|бульв|пров|пл|наб|шосе|узвіз|проїзд|алея)\.?)\s+(.+?),\s*(.+)$', p[2] or '')
        if p[3] == 1 and m: adr.append((i, m.group(2), m.group(3), m.group(4)))
    rnd.shuffle(adr)
    stari = collections.defaultdict(list)
    for old, new in Dv.rename.items(): stari[new].append(old)
    Q = []
    def dodaj(i, q, vyd): Q.append(dict(i=i, q=q, vyd=vyd, ціль=P[i][2]))
    vydy = ['тип повністю', 'тип без крапки', 'тип після назви', 'без типу', 'малими', 'номер з дефісом',
            'номер з пробілом', 'відмінок', 'помилка в літері', 'стара назва', 'дріб', 'корпус']
    # квота на кожен вид окремо: рідкісний вид («корпус») не має з'їдати перелік адрес
    kvota = n // len(vydy) + 1
    for vyd in vydy:
      zrob = 0
      for i, t, nm, h in adr:
        if zrob >= kvota or len(Q) >= n: break
        k = 1; n0 = len(Q)
        tp = TYPY_POVNI.get(t, t)
        hb = re.match(r'^(\d+)([А-ЯІЇЄҐ]?)$', h.replace('-', ''))
        if vyd == 'тип повністю': dodaj(i, f'{tp} {nm} {h}', vyd)
        elif vyd == 'тип без крапки': dodaj(i, f'{t} {nm.lower()} {h}', vyd)
        elif vyd == 'тип після назви': dodaj(i, f'{nm} {t}. {h}', vyd)
        elif vyd == 'без типу': dodaj(i, f'{nm} {h}', vyd)
        elif vyd == 'малими': dodaj(i, f'{t} {nm.lower().replace(chr(39), "").replace("’", "")}, {h}', vyd)
        elif vyd in ('номер з дефісом', 'номер з пробілом'):
            if not (hb and hb.group(2)): k -= 1; continue
            dodaj(i, f'{nm} {hb.group(1)}' + ('-' if vyd == 'номер з дефісом' else ' ') + hb.group(2).lower(), vyd)
        elif vyd == 'відмінок':
            w = nm.split()[-1]
            loc = re.sub(r'ська$', 'ській', re.sub(r'цька$', 'цькій', re.sub(r'на$', 'ній', w)))
            if loc == w: k -= 1; continue
            dodaj(i, f'{t}. {" ".join(nm.split()[:-1] + [loc])} {h}', vyd)
        elif vyd == 'помилка в літері':
            if len(nm) < 6: k -= 1; continue
            j = rnd.randrange(1, len(nm) - 1)
            if not nm[j].isalpha(): k -= 1; continue
            zam = {'и': 'і', 'і': 'и', 'е': 'є', 'о': 'а', 'а': 'о', 'с': 'ш', 'к': 'г'}.get(nm[j], 'а')
            dodaj(i, f'{nm[:j]}{zam}{nm[j + 1:]} {h}', vyd)
        elif vyd == 'стара назва':
            st = stari.get(Dv.vulytsia(f'{t}. {nm}'))
            if not st: k -= 1; continue
            dodaj(i, f'{st[0]} {h}', vyd)
        elif vyd == 'дріб':
            if '/' not in h: k -= 1; continue
            dodaj(i, f'{nm} {h.replace("/", " / ")}', vyd)
        elif vyd == 'корпус':
            m = re.match(r'^(\d+)\s*(?:корп\.?|к\.?)\s*(\d+)$', h, re.I)
            if not m: k -= 1; continue
            dodaj(i, f'{nm} {m.group(1)} корп. {m.group(2)}', vyd)
        zrob += len(Q) > n0
    return Q


def a4(P, Dv, Q):
    """Чотири підходи до пошуку; мірило — правильна адреса першою (top-1) і
    серед перших трьох (top-3), час на запит, розмір індексу."""
    jsnorm = lambda s: re.sub(r'\s+', ' ', re.sub(r"['’ʼ`]", '', (s or '').lower())).strip()
    PN = [jsnorm(p[2]) for p in P]
    cnt = [len(p[4]) for p in P]
    def s0(q):
        """чинний: підрядок мітки, спершу ті, що з нього починаються"""
        q = jsnorm(q); pre, mid = [], []
        for i, n in enumerate(PN):
            k = n.find(q)
            if k == 0: pre.append(i)
            elif k > 0: mid.append(i)
        key = lambda i: -cnt[i]
        return sorted(pre, key=key) + sorted(mid, key=key)
    # нормалізований індекс: ключ вулиці (без типу, слова за абеткою, у
    # називному, перейменування) і номер без дефіса й пробілів
    HN = re.compile(r'(\d+(?:\s*[-/]?\s*[а-яіїєґa-z](?![а-яіїєґ]))?(?:\s*/\s*\d+[а-яіїєґ]?)?(?:\s*(?:корп\.?|к\.?)\s*\d+)?)\s*$', re.I)
    def rozibraty(q, pereim):
        q = q.lower().replace('’', "'")
        m = HN.search(q)
        h = ''
        if m and m.group(1):
            h = re.sub(r'\s*(?:корп\.?|к\.?)\s*', 'К', m.group(1), flags=re.I)
            h = re.sub(r'[\s\-]', '', h).upper(); q = q[:m.start()]
        ws = norm(q).split()
        k = ' '.join(sorted(ws))
        if k not in Dv.full:
            kn = nazyvnyi(k, Dv.full)
            if kn: k = kn[0]
        if pereim and k in Dv.rename: k = Dv.rename[k]
        return k, h
    IDX = []
    for i, p in enumerate(P):
        m = re.match(r'^(.+?),\s*(.+)$', p[2] or '')
        if p[3] == 1 and m:
            IDX.append((i, Dv.vulytsia(m.group(1)).split(), nh(m.group(2)).upper()))
    tri = lambda w: {w[j:j + 3] for j in range(max(1, len(w) - 2))}
    def sN(q, fuzzy=False, pereim=False):
        k, h = rozibraty(q, pereim)
        qs = k.split()
        if not qs: return []
        res = []
        for i, ws, hh in IDX:
            sc = 0
            for w in qs:
                if any(x.startswith(w) for x in ws): sc += 2
                elif fuzzy and len(w) >= 4 and any(len(tri(w) & tri(x)) / max(len(tri(w) | tri(x)), 1) >= 0.4 for x in ws): sc += 1
                else: sc = -1; break
            if sc < 0: continue
            if h:
                if hh == h: sc += 3
                elif hh.startswith(h): sc += 1
                else: continue
            res.append((-sc, -cnt[i], i))
        return [x[2] for x in sorted(res)]
    PIDKH = {'S0 чинний': s0, 'S1 нормалізація': sN,
             'S2 + нечіткий збіг': lambda q: sN(q, fuzzy=True),
             'S3 + перейменування': lambda q: sN(q, fuzzy=True, pereim=True)}
    tab = {}
    for nm_, f in PIDKH.items():
        t0 = time.perf_counter(); top1 = top3 = 0; po = collections.defaultdict(lambda: [0, 0])
        for x in Q:
            r = f(x['q'])[:3]
            ok1 = bool(r) and P[r[0]][2] == x['ціль']; ok3 = any(P[i][2] == x['ціль'] for i in r)
            top1 += ok1; top3 += ok3; po[x['vyd']][0] += ok1; po[x['vyd']][1] += 1
        ms = (time.perf_counter() - t0) * 1000 / len(Q)
        tab[nm_] = dict(top1=round(top1 / len(Q), 3), top3=round(top3 / len(Q), 3), мс_на_запит_ПК_Python=round(ms, 1),
                        за_видами={k_: f'{a}/{b}' for k_, (a, b) in po.items()})
        print(f'  {nm_}: top-1 {top1}/{len(Q)}, top-3 {top3}/{len(Q)}, {ms:.1f} мс')
    # вага індексу S1–S3 у сторінці: ключі вулиць (унікальні) + номери
    vul = {' '.join(ws) for _i, ws, _h in IDX}
    import zlib
    tab['_вага_індексу_КБ_стиснуто'] = round(len(zlib.compress(json.dumps(sorted(vul), ensure_ascii=False).encode(), 9)) / 1024, 1)
    tab['_перейменувань_у_довіднику'] = len(Dv.rename)
    return tab


# ---------------------------------------------------------------- А5
def a5(DD, Dv):
    """Відмінки в адресах подій (адреса з тексту: прохід, без нього — знімок):
    скільки зіллється з основною адресою, скільки отримає точку, чи не
    злипаються різні вулиці (назва в кількох окремих місцях міста)."""
    import step1c_teksty as TK
    TKD = TK.load_done()
    ref = collections.defaultdict(list)
    for (k, h), v in Dv.bud.items(): ref[k] += [(a, b) for a, b, _s in v]
    def skupchennia(k):
        cl = {(int(a * 111.32), int(b * 71.0)) for a, b in ref[k]}
        n_, seen = 0, set()
        for c in cl:
            if c in seen: continue
            n_ += 1; st = [c]
            while st:
                x = st.pop()
                if x in seen: continue
                seen.add(x); st += [(x[0] + i, x[1] + j) for i in (-1, 0, 1) for j in (-1, 0, 1) if (x[0] + i, x[1] + j) in cl]
        return n_
    st = collections.Counter(); zl = collections.Counter(); bagato = collections.Counter()
    adr_do, adr_pislia = set(), set()
    c = sqlite3.connect(os.path.join(DD, 'events.db'))
    for d, s_, h_ in c.execute('select doc_id, street, house from events'):
        tk = TKD.get(d)
        if tk: s_, h_ = tk.get('street'), tk.get('house')
        if not (s_ and h_): continue
        st['документів з вулицею й номером'] += 1
        k = Dv.vulytsia(s_); h = nh(h_); tp = G.stype(s_)
        adr_do.add((tp, k, h))
        if k in Dv.full: adr_pislia.add((tp, k, h)); continue
        kn = nazyvnyi(k, Dv.full)
        if len(kn) != 1:
            st['поза довідником, називного немає' if not kn else 'кілька називних — не міняємо'] += 1
            adr_pislia.add((tp, k, h)); continue
        nn = kn[0]
        st['відмінок -> називний'] += 1
        if skupchennia(nn) > 1: st['  назва в кількох окремих місцях міста'] += 1; bagato[(s_.split(',')[0], nn)] += 1
        st['  будинок знайдеться' if (nn, h) in Dv.bud else '  будинку з таким номером немає'] += 1
        zl[(re.sub(r'\s+', ' ', s_), nn)] += 1
        adr_pislia.add((tp, nn, h))
    for k_, v in sorted(st.items(), key=lambda x: x[0].startswith('  ')): print(f'  {k_}: {v:,}')
    print(f'  адрес (тип, вулиця, номер): до {len(adr_do):,}, після {len(adr_pislia):,}')
    print('  найбільші злиття:', zl.most_common(15))
    print('  назва в кількох місцях:', bagato.most_common(10))
    return dict(st=dict(st), adres_do=len(adr_do), adres_pislia=len(adr_pislia),
                zlyttia=[[a, b, v] for (a, b), v in zl.most_common(60)],
                kilka_mists=[[a, b, v] for (a, b), v in bagato.most_common(30)])


def main():
    DD = sys.argv[1]
    shcho = sys.argv[2:] or ['rozklad', 'a3', 'a4', 'a5']
    Dv = Dovidnyk(os.path.join(DD, '1551'))
    print(f'довідник: назв OSM {len(Dv.full_osm):,}, КМДА {len(Dv.full_kmda):,}; перейменувань 1551 {len(Dv.rename):,} '
          f'(з них {Dv.n_rename_dodano} — лише за поправкою 15.10, {Dv.adr_dodano:,} адрес КМДА)')
    out_p = os.path.join(K, 'e12b_adresy.json')
    out = json.load(open(out_p, encoding='utf-8')) if os.path.exists(out_p) else {}
    P = json.load(open(os.path.join(os.environ.get('TEMP', '.'), 'claude', 'P.json'), encoding='utf-8')) \
        if any(x in shcho for x in ('a3', 'a4')) else None
    if 'rozklad' in shcho: print('\n== розклад набору 36.14 =='); out['rozklad'] = rozklad(DD, Dv)
    if 'a3' in shcho: print('\n== А3 =='); out['a3'] = a3(P, Dv)
    if 'a4' in shcho:
        print('\n== А4 ==')
        Q = zapyty(P, Dv)
        json.dump(Q, open(os.path.join(K, 'e12b_a4_zapyty.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
        print(f'  запитів {len(Q)}: ' + ', '.join(f'{k} {v}' for k, v in collections.Counter(x['vyd'] for x in Q).items()))
        out['a4'] = a4(P, Dv, Q)
    if 'a5' in shcho: print('\n== А5 =='); out['a5'] = a5(DD, Dv)
    json.dump(out, open(out_p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
