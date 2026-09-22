# -*- coding: utf-8 -*-
"""Діагностика: чи адреса події справді є місцем події (POMYLKA-ADRES.md).

Нічого не змінює в даних — лише рахує й друкує. Класи:

    A  процесуальний документ (ухвала): за формою рішення з дампу ЄДРСР, а
       де форми немає — за маркерами на початку фабули (src/podii.py);
    B  вулиця адреси названа в описі події — адресі можна вірити;
    C  фабула є, але вулиці адреси в ній немає — підозра, що екстрактор
       «провалився» до чужої адреси з номером;
    D  фабули немає, перевірити неможливо.

Набір подій той самий, що бачить карта: рівень «будинок», установи відсіяно
тим самим правилом detect_institutional. Рахує по документах (як у діагнозі)
і після злиття справи в одну подію (як на карті).

Відоме обмеження: фабула обрізана до 600 знаків (MAXLEN у step1b_fabula),
тож межа між B і C тримається на обрізку. Повторний прохід по текстах —
крок 6 «Порядку».

Запуск:  py -3 src\\diag_addr_class.py            — таблиця класів
         py -3 src\\diag_addr_class.py --sample   — ще й по 10 випадкових
                                                    подій класів A і C
"""
import os, sys, csv, gzip, re, random, sqlite3, tempfile, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import labels as L
import map_excl
import podii as PD

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
THEMES = ['МАЙ', 'НАР', 'НАС', 'СЕР', 'ДОР', 'ГП', 'АЛК']

# Тип вулиці на початку назви й службові слова — не ознака конкретної вулиці.
STREET_TYPES = r'^(?:вул|вулиця|просп|проспект|бульв|бульвар|пл|площа|пров|провулок|' \
               r'наб|набережна|шосе|узвіз|туп|тупик|алея|дорога|майдан|проїзд)\.?\s+'
STOP = {'вулиця', 'вулиці', 'проспект', 'бульвар', 'площа', 'провулок', 'шосе',
        'академіка', 'героїв', 'гетьмана', 'генерала', 'маршала', 'полку', 'дорога',
        'набережна', 'київська', 'києва', 'міста', 'сім', 'року'}


def norm(s):
    return re.sub(r"['’ʼ`«»\"]", '', (s or '').lower())


def street_stems(street):
    """Основи слів назви вулиці, за якими її можна знайти у відмінках."""
    name = re.sub(STREET_TYPES, '', norm(street).strip())
    words = [w for w in re.findall(r'[а-яіїєґa-z]+', name) if len(w) >= 4 and w not in STOP]
    # основа — без останніх двох літер: «Берестейський» -> «берестейсь»
    # ловить і «Берестейському», і «Берестейського»
    return [w[:max(4, len(w) - 2)] for w in words]


def classify(doc, fab, street, formy):
    if not PD.is_event(doc, fab, formy):
        return 'A'
    if not fab:
        return 'D'
    stems = street_stems(street)
    if not stems:
        return 'C'
    return 'B' if any(s in norm(fab) for s in stems) else 'C'


def institutions():
    """Адреси установ — тим самим правилом, що й карта (step3_map).

    Ручного списку мало: більшість установ карта знаходить сама, за
    координатами й складом статей, а координати є лише в events.db.
    detect_institutional пише свої звіти в data/ — діагностика даних не
    міняє, тож ці файли спрямовано в тимчасову папку.
    """
    db = os.path.join(DATA, 'events.db')
    if not os.path.exists(db):
        return map_excl.load_excl()
    tmp = tempfile.mkdtemp(prefix='diag_addr_')
    map_excl.EXCL = os.path.join(tmp, 'vykluchennya.txt')
    map_excl.REVIEW = os.path.join(tmp, 'top100.txt')
    c = sqlite3.connect(db)
    rows = list(c.execute("""SELECT e.doc_id,e.court,e.cat,e.date,e.tm,e.street,e.house,
        g.lat,g.lon,g.precision FROM events e JOIN geo g ON g.doc_id=e.doc_id"""))
    return map_excl.detect_institutional(rows, map_excl.load_excl())


def main(sample=False):
    excl = institutions()
    formy = PD.load_formy()
    fab = PD.load_fab()
    cause = {}
    for fp in sorted(os.listdir(DATA)):
        if fp.startswith('kyiv_') and fp.endswith('.csv'):
            with open(os.path.join(DATA, fp), encoding='utf-8-sig') as fh:
                for r in csv.DictReader(fh, delimiter='\t'):
                    if r.get('cause_num'):
                        cause[r['doc_id']] = r['cause_num']

    ev = []
    with gzip.open(os.path.join(DATA, 'events.csv.gz'), 'rt', encoding='utf-8', newline='') as fh:
        for r in csv.DictReader(fh, delimiter='\t'):
            if r['level'] != 'house':
                continue
            if (r['street'] + ', ' + r['house']).lower() in excl:
                continue
            th = (L.CODE.get(r['cat']) or ('СЕР', ''))[0]
            if th not in THEMES:
                continue
            f = fab.get(r['doc_id'], '')
            ev.append(dict(doc=r['doc_id'], th=th, cat=r['cat'], street=r['street'],
                           house=r['house'], date=r['date'], fab=f,
                           src=PD.source(r['doc_id'], formy),
                           k=classify(r['doc_id'], f, r['street'], formy)))

    # Одна подія на (справа, вид), як на карті — тим самим src/podii.py.
    merged = PD.merge_cases(ev, doc=lambda e: e['doc'], cat=lambda e: e['cat'],
                            date=lambda e: e['date'], cause=cause, event=lambda e: e['k'] != 'A')
    reps = [rep for rep, _g, _l in merged]
    print('\nодна подія на (справа, вид):')
    print(f'{"тема":<5}{"рішень по суті":>16}{"подій":>8}{"дублів":>8}{"різні адреси":>14}')
    for th in THEMES:
        nd = sum(1 for e in ev if e['th'] == th and e['k'] != 'A')
        grp_th = [(r, g) for r, g, _l in merged if r['th'] == th]
        # справа, де кілька рішень по суті стоять на різних адресах: саме тут
        # вибір представника міняє точку на карті
        split = sum(1 for _r, g in grp_th
                    if len({x['street'] + ', ' + x['house'] for x in g if x['k'] != 'A'}) > 1)
        print(f'{th:<5}{nd:>16,}{len(grp_th):>8,}{nd - len(grp_th):>8,}{split:>14,}'.replace(',', ' '))

    def table(rows, title, classes='ABCD'):
        print(f'\n{title}')
        print(f'{"тема":<5}' + ''.join(f'{k:>7}' for k in classes) + f'{"подій":>9}')
        for th in THEMES:
            sub = [x for x in rows if x['th'] == th]
            if not sub:
                continue
            c = collections.Counter(x['k'] for x in sub); n = len(sub)
            print(f'{th:<5}' + ''.join(f'{100 * c[k] / n:6.0f}%' for k in classes)
                  + f'{n:9,}'.replace(',', ' '))

    print(f'подій (будинок, без установ): {len(ev):,} документів'.replace(',', ' '))
    have = sum(1 for e in ev if e['src'] == 'форма')
    print(f'форма рішення з дампу є для {have:,} з {len(ev):,} ({100 * have / max(len(ev), 1):.0f}%); '
          f'решта — за маркерами'.replace(',', ' '))
    table(ev, 'ПО ДОКУМЕНТАХ')
    table(reps, 'ПОДІЇ НА КАРТІ — рішення по суті, одна справа одна подія', 'BCD')

    print('\nадреси з діагнозу (по документах):')
    for st, ho in [('Хоткевича', '20'), ('Володимирська', '26'), ('Ревуцького', '54'),
                   ('Братиславська', '3'), ('Бродських', '6'), ('Докучаєвська', '4'),
                   ('Єреванська', '32')]:
        sub = [e for e in ev if st.lower() in e['street'].lower() and e['house'] == ho]
        if sub:
            c = collections.Counter(e['k'] for e in sub)
            print(f'  {st}, {ho}: {len(sub)} — ' + ' '.join(f'{k}{c[k]}' for k in 'ABCD'))

    if sample:
        rnd = random.Random(20260922)
        for th in ['МАЙ', 'НАР', 'НАС']:
            for k in 'AC':
                pool = [e for e in ev if e['th'] == th and e['k'] == k]
                print(f'\n==== {th} · клас {k} · 10 з {len(pool)} ====')
                for e in rnd.sample(pool, min(10, len(pool))):
                    t = ' '.join(e['fab'].split())
                    print(f'-- [{e["doc"]}] {e["street"]}, {e["house"]} | '
                          f'{L.CODE.get(e["cat"], ("", ""))[1]} | {e["src"]}')
                    print('   ' + t[:520])


if __name__ == '__main__':
    main(sample='--sample' in sys.argv)
