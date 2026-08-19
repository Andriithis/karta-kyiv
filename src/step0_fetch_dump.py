# -*- coding: utf-8 -*-
"""Крок 0. Качає свіжий дамп ЄДРСР з data.gov.ua і фільтрує до kyiv_YYYY.csv"""
import os, sys, io, csv, json, zipfile, datetime, urllib.request, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import labels as L

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
CKAN = 'https://data.gov.ua/api/3/action/package_search?q=%D1%81%D1%83%D0%B4%D0%BE%D0%B2%D0%B8%D1%85+%D1%80%D1%96%D1%88%D0%B5%D0%BD%D1%8C&rows=50'
UA = {'User-Agent': 'edrsr-academy-ci/1.0'}

COURTS = {"2601":"Golosiivskyi","2602":"Darnytskyi","2603":"Desnianskyi","2604":"Dniprovskyi",
 "2605":"Obolonskyi","2606":"Pecherskyi","2607":"Podilskyi","2608":"Sviatoshynskyi",
 "2609":"Solomianskyi","2610":"Shevchenkivskyi"}
SKIP_THEME = {'ДОМ'}   # домашнє насильство на публічну карту не йде

def find_url(year):
    """шукає посилання на архів за рік через API порталу"""
    try:
        with urllib.request.urlopen(urllib.request.Request(CKAN, headers=UA), timeout=90) as r:
            js = json.loads(r.read().decode())
        for pkg in js['result']['results']:
            if str(year) not in pkg.get('title', ''): continue
            for res in pkg.get('resources', []):
                u = res.get('url', '')
                if u.endswith(f'edrsr_data_{year}.zip'):
                    return u
    except Exception as e:
        print(f'   API порталу недоступне ({type(e).__name__})')
    return None

def main():
    year = int(sys.argv[1]) if len(sys.argv) > 1 else datetime.date.today().year
    os.makedirs(DATA, exist_ok=True)
    print(f'=== Крок 0: дамп ЄДРСР за {year} рік ===')

    url = find_url(year) or os.environ.get('EDRSR_URL')
    if not url:
        print('НЕ ЗНАЙДЕНО посилання на архів. Вкажіть у змінній EDRSR_URL.'); sys.exit(1)
    print(f'   {url}')

    zpath = os.path.join(DATA, f'_dump_{year}.zip')
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=1800) as r, \
         open(zpath, 'wb') as f:
        n = 0
        while True:
            chunk = r.read(1 << 20)
            if not chunk: break
            f.write(chunk); n += len(chunk)
            if n % (50 << 20) < (1 << 20): print(f'   {n/1048576:.0f} МБ', flush=True)
    print(f'   завантажено {os.path.getsize(zpath)/1048576:.0f} МБ')

    out = os.path.join(DATA, f'kyiv_{year}.csv')
    total = found = 0
    grp = collections.Counter()
    with zipfile.ZipFile(zpath) as z:
        name = next(n for n in z.namelist() if n.endswith('documents.csv'))
        with z.open(name) as fh, open(out, 'w', encoding='utf-8-sig', newline='') as o:
            o.write('doc_id\tcourt_code\tcourt\tgroup\tcategory_code\tcause_num\tdate\tdoc_url\n')
            txt = io.TextIOWrapper(fh, encoding='utf-8', errors='replace')
            txt.readline()
            for line in txt:
                total += 1
                f = line.rstrip('\n').split('\t')
                if len(f) < 12: continue
                if f[1] not in COURTS: continue
                lb = L.CODE.get(f[4])
                if not lb or lb[0] in SKIP_THEME: continue
                if f[10] != '1': continue
                d = f[6].replace('"', '')[:10]
                o.write(f'{f[0]}\t{f[1]}\t{COURTS[f[1]]}\t{lb[0]}\t{f[4]}\t{f[5]}\t{d}\t{f[9]}\n')
                found += 1; grp[lb[0]] += 1
    os.remove(zpath)
    print(f'   прочитано {total:,}, відібрано {found:,} -> kyiv_{year}.csv')
    for k, v in grp.most_common(): print(f'      {L.THEMES.get(k,k):28} {v:>8,}')

if __name__ == '__main__':
    main()
