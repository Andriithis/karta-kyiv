# -*- coding: utf-8 -*-
"""Самоперевірка збірки карти. Запускати після кожної правки.

Що робить:
  1. компілює всі файли в src/ — ловить друкарські помилки й зіпсовані символи;
  2. розпаковує зменшену базу data/events_test.db.gz (22 тисячі подій,
     усі десять районів) — справжня база для цього не потрібна;
  3. збирає три карти: міську, районну й слухацьку;
  4. витягає з кожної <script> і перевіряє синтаксис через node, якщо він є;
  5. рахує баланс тегів розмітки;
  6. порівнює контрольні суми з попереднім запуском і каже, чи змінився
     результат.

Порядок роботи з пунктом 6: перед правкою запустіть `python src/check_build.py
--save` — це запам'ятає еталон. Після правки запустіть без ключа. Якщо ви лише
переставляли код, а не міняли поведінку, всі три карти мають лишитися
незмінними. Якщо змінилися — ви бачите, які саме.

Еталон лежить у data/_check_last.json і в репозиторій не потрапляє.
"""
import os, sys, gzip, json, shutil, hashlib, tempfile, subprocess, py_compile, re

SRCD = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SRCD)
DATA = os.path.join(ROOT, 'data')
TESTGZ = os.path.join(DATA, 'events_test.db.gz')
TESTDB = os.path.join(DATA, 'events_test.db')      # data/*.db у .gitignore
STATE = os.path.join(DATA, '_check_last.json')
sys.path.insert(0, SRCD)

VOID = {'meta', 'link', 'br', 'hr', 'img', 'input', 'source',
        'area', 'base', 'col', 'embed', 'track', 'wbr'}


def compile_all():
    bad = []
    for f in sorted(os.listdir(SRCD)):
        if not f.endswith('.py'):
            continue
        try:
            py_compile.compile(os.path.join(SRCD, f), doraise=True)
        except Exception as e:
            bad.append(f'{f}: {e}')
    return bad


def unpack():
    if not os.path.exists(TESTGZ):
        return f'немає {os.path.relpath(TESTGZ, ROOT)}'
    with gzip.open(TESTGZ, 'rb') as g, open(TESTDB, 'wb') as f:
        shutil.copyfileobj(g, f)
    return None


def check_markup(html):
    from html.parser import HTMLParser

    class P(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.st, self.err = [], []

        def handle_starttag(self, t, a):
            if t not in VOID:
                self.st.append(t)

        def handle_endtag(self, t):
            if t in VOID:
                return
            if not self.st:
                self.err.append(f'зайвий </{t}>')
            elif self.st[-1] != t:
                self.err.append(f'очікував </{self.st[-1]}>, отримав </{t}>')
            else:
                self.st.pop()

    p = P()
    p.feed(html)
    return p.err + [f'не закрито <{t}>' for t in p.st]


def check_js(html, tmp):
    m = re.search(r'<script>\n(.*)\n</script>', html, re.S)
    if not m:
        return ['не знайдено <script> у сторінці']
    jsf = os.path.join(tmp, 'x.js')
    with open(jsf, 'w', encoding='utf-8') as f:
        f.write(m.group(1))
    if not shutil.which('node'):
        return []                       # node не встановлено — мовчки пропускаємо
    r = subprocess.run(['node', '--check', jsf], capture_output=True, text=True)
    return [] if r.returncode == 0 else [r.stderr.strip().split('\n')[-1]]


def main(save=False):
    print('1. Компіляція src/')
    bad = compile_all()
    if bad:
        for b in bad:
            print('   ПОМИЛКА', b)
        return 1
    print('   усі файли компілюються')

    print('2. Тестова база')
    err = unpack()
    if err:
        print('   ПОМИЛКА', err)
        return 1
    print(f'   {os.path.relpath(TESTDB, ROOT)} розпаковано')

    import step3_map
    step3_map.DB = TESTDB

    CASES = [('міська', dict(district=None, mode='full')),
             ('районна', dict(district='Деснянський', mode='full')),
             ('слухацька', dict(district=None, mode='student'))]

    tmp = tempfile.mkdtemp(prefix='karta_check_')
    now, problems = {}, []
    try:
        for name, kw in CASES:
            print(f'3. Збірка: {name}')
            dst = os.path.join(tmp, f'{name}.html')
            out = open(os.devnull, 'w')
            keep, sys.stdout = sys.stdout, out
            try:
                step3_map.main(out=dst, **kw)
            finally:
                sys.stdout = keep
                out.close()
            html = open(dst, encoding='utf-8').read()
            now[name] = hashlib.sha256(html.encode('utf-8')).hexdigest()[:16]
            for e in check_markup(html):
                problems.append(f'{name}: розмітка — {e}')
            for e in check_js(html, tmp):
                problems.append(f'{name}: JavaScript — {e}')
            print(f'   {len(html)/1048576:.1f} МБ · {now[name]}')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print('4. Розмітка і JavaScript')
    if problems:
        for p in problems:
            print('   ПОМИЛКА', p)
        return 1
    print('   чисто')

    print('5. Порівняння з попереднім запуском')
    if save:
        json.dump(now, open(STATE, 'w'))
        print('   еталон збережено')
        return 0
    if not os.path.exists(STATE):
        json.dump(now, open(STATE, 'w'))
        print('   еталона не було — збережено поточний результат')
        return 0
    before = json.load(open(STATE))
    same = True
    for name, _ in CASES:
        was, is_ = before.get(name), now[name]
        if was == is_:
            print(f'   {name}: без змін')
        else:
            same = False
            print(f'   {name}: ЗМІНИЛАСЯ  було {was}  стало {is_}')
    json.dump(now, open(STATE, 'w'))
    if same:
        print('\n=== ГОТОВО === результат не змінився')
    else:
        print('\n=== ГОТОВО === результат змінився. Якщо ви лише переставляли\n'
              'код, це помилка. Якщо міняли поведінку — так і має бути.')
    return 0


if __name__ == '__main__':
    sys.exit(main(save='--save' in sys.argv))
