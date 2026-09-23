# -*- coding: utf-8 -*-
"""Крок 0. Качає свіжий дамп ЄДРСР з data.gov.ua і фільтрує до kyiv_YYYY.csv

Портал data.gov.ua лягає регулярно. Раніше будь-який його збій валив увесь
прогін: не було свіжого дампа — не робилося нічого, зокрема й перенавчання
моделі, якому свіжі дані взагалі не потрібні. Тепер крок 0 падає лише тоді,
коли працювати справді нема з чим (жодного kyiv_*.csv). Якщо дані вже є —
пише попередження й повертає успіх, а решта кроків іде на наявних даних.
"""
import os, sys, io, csv, json, time, zipfile, datetime, glob, gzip
import urllib.request, urllib.error, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import labels as L

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
CKAN = 'https://data.gov.ua/api/3/action/package_search?q=%D1%81%D1%83%D0%B4%D0%BE%D0%B2%D0%B8%D1%85+%D1%80%D1%96%D1%88%D0%B5%D0%BD%D1%8C&rows=50'
UA = {'User-Agent': 'edrsr-academy-ci/1.0'}
TRIES = 4          # портал часто віддає обірвану відповідь з першого разу
PAUSE = 20         # секунд між спробами

COURTS = {"2601":"Golosiivskyi","2602":"Darnytskyi","2603":"Desnianskyi","2604":"Dniprovskyi",
 "2605":"Obolonskyi","2606":"Pecherskyi","2607":"Podilskyi","2608":"Sviatoshynskyi",
 "2609":"Solomianskyi","2610":"Shevchenkivskyi"}
SKIP_THEME = {'ДОМ'}   # домашнє насильство на публічну карту не йде

def have_data():
    """чи є з чим працювати наступним крокам, якщо дамп не приїхав"""
    return sorted(glob.glob(os.path.join(DATA, 'kyiv_*.csv')))

def give_up(msg):
    """Немає свіжого дампа. Це привід зупинитись лише тоді, коли даних немає
    зовсім. Інакше — гучне попередження й код 0, щоб решта прогону відпрацювала."""
    have = have_data()
    print(msg)
    if not have:
        print('   і жодного kyiv_*.csv у папці data немає — далі йти нема з чим')
        sys.exit(1)
    print('   АЛЕ дані за попередні прогони на місці:')
    for p in have:
        print(f'      {os.path.basename(p)}')
    print('   продовжуємо на них. Свіжі рішення доберемо наступного разу.')
    sys.exit(0)

def find_url(year):
    """шукає посилання на архів за рік через API порталу"""
    for i in range(1, TRIES + 1):
        try:
            with urllib.request.urlopen(urllib.request.Request(CKAN, headers=UA), timeout=90) as r:
                js = json.loads(r.read().decode())
            for pkg in js['result']['results']:
                if str(year) not in pkg.get('title', ''): continue
                for res in pkg.get('resources', []):
                    u = res.get('url', '')
                    if u.endswith(f'edrsr_data_{year}.zip'):
                        return u
            print(f'   у переліку порталу немає архіву за {year} рік')
            return None
        except Exception as e:
            print(f'   спроба {i} з {TRIES}: API порталу недоступне ({type(e).__name__})',
                  flush=True)
            if i < TRIES: time.sleep(PAUSE)
    return None

def download(url, zpath):
    """качає архів; повертає True, якщо файл приїхав"""
    for i in range(1, TRIES + 1):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=1800) as r, \
                 open(zpath, 'wb') as f:
                n = 0
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk: break
                    f.write(chunk); n += len(chunk)
                    if n % (50 << 20) < (1 << 20): print(f'   {n/1048576:.0f} МБ', flush=True)
            print(f'   завантажено {os.path.getsize(zpath)/1048576:.0f} МБ')
            return True
        except Exception as e:
            print(f'   спроба {i} з {TRIES}: завантаження обірвалось ({type(e).__name__})',
                  flush=True)
            if os.path.exists(zpath): os.remove(zpath)
            if i < TRIES: time.sleep(PAUSE)
    return False

# ---- ФОРМА РІШЕННЯ (ZAVDANNYA-ADRESY.md, п.1) ----
# Подія — лише рішення по суті: вирок (ККУ) чи постанова (КУпАП). Ухвала про
# запобіжний захід чи про призначення засідання події не описує, а екстрактор
# брав з неї першу-ліпшу адресу з номером. Форму рішення дамп ЄДРСР дає
# прямо, у judgment_code, — це надійніше за будь-які маркери в тексті.
#
# Зберігається окремим файлом doc_id -> код, а не колонкою в events.csv.gz:
# той файл пише й відновлює крок 1 з фіксованим переліком колонок, і нова
# колонка зачепила б щотижневий цикл. Споживачі приєднують форму за doc_id
# (src/podii.py).
FORMY = os.path.join(DATA, 'formy.csv.gz')
DOVIDNYK = os.path.join(DATA, 'formy_dovidnyk.csv')

def load_formy():
    if not os.path.exists(FORMY): return {}
    with gzip.open(FORMY, 'rt', encoding='utf-8', newline='') as fh:
        rd = csv.reader(fh, delimiter='\t'); next(rd, None)
        return {r[0]: r[1] for r in rd if len(r) >= 2}

def save_formy(d):
    with gzip.open(FORMY, 'wt', encoding='utf-8', newline='') as fh:
        fh.write('doc_id\tjudgment_code\n')
        for k in sorted(d, key=lambda x: int(x) if x.isdigit() else 0):
            fh.write(f'{k}\t{d[k]}\n')

def unmojibake(s):
    """У довіднику дампу назви перекодовано двічі: UTF-8 байти збережено як
    cp1251, і «Вирок» приїжджає як «Р’РёСЂРѕРє». Повертаємо назад лише тоді,
    коли перетворення проходить без втрат — інакше лишаємо як є."""
    try:
        return s.encode('cp1251').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s

def save_dovidnyk(z):
    """Довідник форм із того самого дампу — щоб коди в src/podii.py можна
    було звірити з першоджерелом, а не з пам'яттю."""
    name = next((n for n in z.namelist() if n.endswith('judgment_forms.csv')), None)
    if not name: print('   довідника judgment_forms.csv у дампі немає'); return
    with z.open(name) as fh:
        rows = [[unmojibake(x.strip('"')) for x in ln.rstrip('\r\n').split('\t')]
                for ln in io.TextIOWrapper(fh, encoding='utf-8', errors='replace')]
    with open(DOVIDNYK, 'w', encoding='utf-8', newline='') as o:
        for r in rows:
            o.write('\t'.join(r) + '\n')
    print('   довідник форм рішень:')
    for r in rows[1:]: print('      ' + ' — '.join(r))

def column(hdr, name, default):
    """Номер колонки за назвою з першого рядка дампу, а якщо назви немає —
    звичний номер. Порядок колонок у дампі вже мінявся між роками."""
    h = [x.strip().strip('"') for x in hdr]
    return h.index(name) if name in h else default

def parse(zpath, year, write_kyiv):
    """Розбирає documents.csv дампу. Повертає doc_id -> форму рішення для
    київських документів і, якщо треба, пише kyiv_YYYY.csv."""
    out = os.path.join(DATA, f'kyiv_{year}.csv')
    tmp = out + '.tmp'
    total = found = 0
    grp = collections.Counter()
    forms = {}
    with zipfile.ZipFile(zpath) as z:
        save_dovidnyk(z)
        name = next(n for n in z.namelist() if n.endswith('documents.csv'))
        with z.open(name) as fh:
            txt = io.TextIOWrapper(fh, encoding='utf-8', errors='replace')
            jc = column(txt.readline().rstrip('\n').split('\t'), 'judgment_code', 2)
            # Пишемо в тимчасовий файл і підмінюємо готовим. Якщо розбір
            # обірветься посеред архіву, старий kyiv_YYYY.csv лишиться цілим:
            # обрізаний файл виглядав би як робочий і тихо зменшив би кількість подій.
            o = open(tmp, 'w', encoding='utf-8-sig', newline='') if write_kyiv else None
            if o: o.write('doc_id\tcourt_code\tcourt\tgroup\tcategory_code\tcause_num\tdate\tdoc_url\tjudgment_code\n')
            for line in txt:
                total += 1
                f = line.rstrip('\n').split('\t')
                if len(f) < 12: continue
                if f[1] not in COURTS: continue
                lb = L.CODE.get(f[4])
                if not lb or lb[0] in SKIP_THEME: continue
                if f[10] != '1': continue
                code = f[jc].strip().strip('"')
                forms[f[0]] = code
                if o:
                    d = f[6].replace('"', '')[:10]
                    o.write(f'{f[0]}\t{f[1]}\t{COURTS[f[1]]}\t{lb[0]}\t{f[4]}\t{f[5]}\t{d}\t{f[9]}\t{code}\n')
                found += 1; grp[lb[0]] += 1
            if o: o.close()
    if write_kyiv:
        os.replace(tmp, out)
        print(f'   прочитано {total:,}, відібрано {found:,} -> kyiv_{year}.csv')
        for k, v in grp.most_common(): print(f'      {L.THEMES.get(k,k):28} {v:>8,}')
    else:
        print(f'   прочитано {total:,}, київських документів {found:,}')
    fc = collections.Counter(forms.values())
    print('   форми рішень: ' + ', '.join(f'{k}: {v:,}' for k, v in fc.most_common()))
    return forms

def fetch(year):
    url = find_url(year) or os.environ.get('EDRSR_URL')
    if not url:
        return None, 'НЕ ЗНАЙДЕНО посилання на архів (портал data.gov.ua не відповідає).'
    print(f'   {url}')
    zpath = os.path.join(DATA, f'_dump_{year}.zip')
    if not download(url, zpath):
        return None, 'Архів не завантажився.'
    return zpath, None

def main():
    os.makedirs(DATA, exist_ok=True)
    args = sys.argv[1:]
    # Разовий прохід «лише форми» (workflow «Форма рішення»): дампи кількох
    # років, kyiv_*.csv не чіпаємо й тексти заново не качаємо — лише
    # дописуємо форму рішення до вже відомих документів.
    only_forms = '--formy' in args
    years = [int(a) for a in args if a.isdigit()] or [datetime.date.today().year]
    formy = load_formy()
    for year in years:
        print(f'=== Крок 0: дамп ЄДРСР за {year} рік' + (' — лише форми рішень' if only_forms else '') + ' ===')
        zpath, err = fetch(year)
        if err:
            if only_forms:
                print('   ' + err + ' Рік пропущено.'); continue
            give_up(err)
        try:
            forms = parse(zpath, year, write_kyiv=not only_forms)
        except Exception as e:
            tmp = os.path.join(DATA, f'kyiv_{year}.csv.tmp')
            if os.path.exists(tmp): os.remove(tmp)
            os.remove(zpath)
            if only_forms:
                print(f'   Архів пошкоджений або обірваний ({type(e).__name__}). Рік пропущено.'); continue
            give_up(f'Архів пошкоджений або обірваний ({type(e).__name__}).')
        os.remove(zpath)
        before = len(formy)
        formy.update(forms)
        print(f'   formy.csv.gz: {before:,} -> {len(formy):,} документів')
    save_formy(formy)

if __name__ == '__main__':
    main()
