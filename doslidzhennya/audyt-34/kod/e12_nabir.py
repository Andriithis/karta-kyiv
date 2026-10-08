"""Е12, перевірка 2 (ZAVDANNYA-35, крок 1): набір подій за RISHENNYA 36.14
і автоматичні частини П2, П4, П6.

Набір: подія йде в розрахунки, якщо речення, з якого взято адресу
(addr_sentence), описує саму подію (дія), а не роль адреси (проживає,
доставлений, складено протокол); ст. 309 — перший будинок місця події
(придбання, без нього — затримання); номер перед «км» — не будинок;
адреса після «м. <не Київ>» — не точка.

Код карти не чіпаємо: правила тут — окремо, для виміру.
Вихід: kod/nabir_36_14.csv.gz і числа в stdout.
"""
import os, re, csv, gzip, glob, sqlite3, json, random, collections, sys
K = os.path.dirname(os.path.abspath(__file__))
R = os.path.abspath(os.path.join(K, '..', '..', '..'))
sys.path.insert(0, os.path.join(R, 'src'))
import labels, addr as A, podii as PD, step1c_teksty as TK
csv.field_size_limit(10**9)

# Дія події в реченні адреси. Список — з 325 розмічених рішень (Е12): дієслова,
# якими суди описують саму подію. Роль адреси — те, що в розмітці давало
# «не місце події» (доставлення, протокол, проживання, облік).
DIIA = re.compile(r"керува|керую|рухал|рухав|рухаю|скоїв|скоїл|допусти|здійсни|розпива|вжива|"
                  r"перебува\w*\s+(?:у|в)\s+(?:громадськ|п`ян|п'ян|стан)|у\s+п[`'’]?яному|"
                  r"викра|заволод|проник|виражав|висловлюв|лаяв|чіпля|ображ|наніс|вдари|бійк|"
                  r"придба|знайш|підібра|забра|зберіга|зупинен|затриман|виявлен|вилучен|викрит|"
                  r"вчини|продава|торгів|реалізу|справля|наїзд|зіткнен|пошкод|відмови|"
                  r"погрожу|кида|поводи|не\s+викона", re.I)
ROL = re.compile(r"прожива|зареєстрован|мешка|доставлен|госпіталіз|складен\w*\s+протокол|"
                 r"протокол\w*\s+(?:\S+\s+){0,3}складен|на\s+обліку|направлен\w*\s+на\s+огляд", re.I)
KM = re.compile(r"\d+\s*-?\s*(?:й|го|ому)?\s*км\b", re.I)
# Чуже місто — лише перед вулицею (≤ 60 знаків, можна через район чи
# область), і не в назві суду, напрямку руху чи станції метро: ручний перегляд
# 30 випадків (П4) дав 11 хибних тривог саме з цих зворотів.
MISTO = re.compile(r"(?<!ж/)\b(?:м\.|місто|місті|смт|с\.)\s*(?!Ки)([А-ЯІЇЄҐ][а-яіїєґ'’\-]{2,}(?:\s+[А-ЯІЇЄҐ][а-яіїєґ'’\-]+)?)"
                   r"(?=[^.]{0,60}?\b(?:вул|просп|пр-т|бул|пл\.|площ|пров|шосе|Шлях))")
MISTO_NE = re.compile(r"(?:суд\w*|напрям\w*|сторон\w*|бік|ст\.|виконавч\w*|юридичн\w*\s+адрес\w*)[^.]{0,40}$", re.I)

def nov_klas(sent, level):
    """1 — у розрахунках, 0 — ні; причина."""
    if level not in ('house', 'cross'): return 0, 'без точного місця'
    if not sent: return 0, 'немає речення адреси'
    if ROL.search(sent) and not DIIA.search(sent): return 0, 'роль адреси'
    return 1, ''

def km_misto(sent, house):
    """Номер будинку, за яким іде «км», і чуже місто перед адресою."""
    km = bool(house) and re.search(re.escape(house.split('/')[0].rstrip('АБВГДЕабвгде-')) + r"\s*-?\s*(?:й|го)?\s*км\b", sent or '', re.I)
    misto = ''
    for m in MISTO.finditer(sent or ''):
        if MISTO_NE.search(sent[max(0, m.start() - 45):m.start()]): continue
        # «м. Київ, с. Троєщина», «м. Київ, с. Бортничі» — частина Києва (перевірка 30 свіжих)
        if re.search(r"Ки[їє]в\w*\s*,?\s*$", sent[max(0, m.start() - 15):m.start()]): continue
        misto = m.group(1); break
    # і після номера: «вул. Грушевського, 8 в м. Житомирі», «…231, с. Солоницівка»
    hm = re.search(r"(?<!\d)" + re.escape((house or '').split('/')[0][:4]), sent or '') if house else None
    if not misto and hm:
        m = re.match(r"[^.]{0,30}?(?:\b(?:у|в)\s+)?(?:\bм\.|місті|\bс\.|смт)\s*(?!Ки)([А-ЯІЇЄҐ][а-яіїєґ'’\-]{2,})", sent[hm.end():])
        if m: misto = m.group(1)
    return bool(km), misto

def lab(c):
    v = labels.CODE.get(c); return v[1] if isinstance(v, tuple) else ''

def p309(fab):
    """36.14.2: перший будинок серед місць події (після відсіву місця замовлення)."""
    t = 'ВСТАНОВИВ: ' + fab
    t = A.fix_typos(t)
    ms = A.mentions(t, A.body_start(t))
    if ms: ms = TK.nar_keep(t, ms)
    for p, lv, st, h in ms:
        if lv == 'house': return st, h, 'house'
    for p, lv, st, h in ms:
        if lv == 'cross': return st, h, 'cross'
    return '', '', ms[0][1] if ms else 'none'

def main():
    T = {}
    for f in sorted(glob.glob(os.path.join(R, 'data', 'teksty', '*.csv.gz'))):
        for r in csv.DictReader(gzip.open(f, 'rt', encoding='utf-8'), delimiter='\t'):
            T[r['doc_id']] = r
    db = sqlite3.connect(os.path.join(R, 'data', 'events.db'))
    cat = dict(db.execute('select doc_id, cat from events'))
    out, st = [], collections.Counter()
    p6 = collections.Counter(); p6pr = collections.defaultdict(list)
    p4 = collections.defaultdict(list)
    for d, r in T.items():
        c = cat.get(d, ''); l = lab(c)
        street, house, level, sent = r['street'], r['house'], r['level'], r['addr_sentence']
        if l.startswith('ст.309 КК') and r['fab']:
            s2, h2, l2 = p309(r['fab'])
            # Місця події у збереженій (обрізаній) фабулі немає, а прохід знайшов
            # його в повному тексті — це обріз фабули, а не правило 36.14.2.
            if l2 not in ('house', 'cross') and level in ('house', 'cross'): s2, h2, l2 = street, house, level
            old = (street, house) if level == 'house' else None
            new = (s2, h2) if l2 == 'house' else None
            k = ('та сама' if old == new or (old and new and A.norm_house(old[1]) == A.norm_house(new[1]) and old[0][-6:] == new[0][-6:])
                 else 'з\'явилась' if new and not old else 'зникла' if old and not new else 'змістилась' if old and new else 'немає й не було')
            p6[k] += 1
            if k not in ('та сама', 'немає й не було') and len(p6pr[k]) < 10: p6pr[k].append((d, old, new))
            if l2 in ('house', 'cross'): street, house, level = s2, h2, l2
        km, misto = km_misto(sent, house) if level == 'house' else (False, '')
        if km: p4['км'].append(d)
        if misto: p4['місто'].append((d, misto))
        v, why = nov_klas(sent, level)
        if v and km: v, why = 0, 'км'
        if v and misto: v, why = 0, 'інше місто'
        stara = 1 if (r['level'] in ('house', 'cross') and r['klass'] == 'B') else 0
        st[(stara, v)] += 1
        if not v and why: st['причина: ' + why] += 1
        out.append((d, c, r['rule'], r['level'], r['klass'], street, house, level, v, why))
    with gzip.open(os.path.join(K, 'nabir_36_14.csv.gz'), 'wt', encoding='utf-8', newline='') as f:
        w = csv.writer(f); w.writerow(['doc_id', 'cat', 'rule', 'level_staryi', 'klass_staryi', 'street', 'house', 'level', 'v_rozrakhunkakh', 'chomu_ni'])
        w.writerows(out)
    print('документів у проході', len(T))
    print('старий набір (точне місце + клас B) × новий (36.14):')
    for a in (1, 0):
        print(f'   старий {a}: новий 1 — {st[(a, 1)]:,}, новий 0 — {st[(a, 0)]:,}')
    for k, n in sorted(st.items(), key=lambda x: str(x[0])):
        if isinstance(k, str): print('  ', k, n)
    print('\nП4: номер + «км»', len(p4['км']), '; чуже місто перед адресою', len(p4['місто']))
    print('   міста:', collections.Counter(m for _, m in p4['місто']).most_common(12))
    json.dump({'km': p4['км'], 'misto': p4['місто']}, open(os.path.join(K, 'e12_p4.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    # П2 на розмітці 325 (Е12): старий клас і новий проти позначки людини
    H = {x['doc_id']: x for x in json.load(open(os.path.join(K, 'e12_vykhid_ekstraktora.json'), encoding='utf-8'))}
    L = {r['doc_id']: r['typ'] for r in csv.DictReader(open(os.path.join(K, '..', 'E12-rozmitka.tsv'), encoding='utf-8'), delimiter='\t')}
    mx = collections.Counter()
    for d, typ in L.items():
        if typ == 'T': continue
        h = H[d]; zoloto = typ in ('H', 'X')
        stara = h['level'] in ('house', 'cross') and h['klass'] == 'B'
        nova = nov_klas(h['addr_sentence'], h['level'])[0] == 1 and not any(km_misto(h['addr_sentence'], h['house']))
        mx[(zoloto, stara, nova)] += 1
    print('\nП2 на розмітці (місце події за людиною, старий, новий):')
    for k, n in sorted(mx.items()): print('  ', k, n)
    # вибірки для ручного перегляду — без класу й без підказки, що вирішило правило
    rnd = random.Random(35)
    cd = [d for d, r in T.items() if r['level'] == 'house' and r['klass'] in ('C', 'D') and d not in L]
    rnd.shuffle(cd)
    with open(os.path.join(K, 'e12_p2_vybirka.txt'), 'w', encoding='utf-8') as f:
        for i, d in enumerate(cd[:100], 1):
            f.write(f"#{i} {d} | {lab(cat.get(d, ''))[:40]}\n{re.sub(r'[ \t\r\n]+', ' ', T[d]['addr_sentence'])[:700]}\n\n")
    with open(os.path.join(K, 'e12_p4_vybirka.txt'), 'w', encoding='utf-8') as f:
        for nm, ids in (('км', p4['км']), ('місто', [x[0] for x in p4['місто']])):
            ids = list(ids); rnd.shuffle(ids)
            for d in ids[:30]:
                f.write(f"[{nm}] {d} | {T[d]['street']}, {T[d]['house']}\n{re.sub(r'[ \t\r\n]+', ' ', T[d]['addr_sentence'])[:400]}\n\n")
    print('\nП6 ст. 309:', dict(p6))
    for k, v in p6pr.items():
        print(' ', k)
        for x in v: print('    ', x)

if __name__ == '__main__':
    main()
