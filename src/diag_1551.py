# -*- coding: utf-8 -*-
"""Діагностика: чи придатні звернення 1551 для карти (PIDKHID.md, розд. 3.2).

Разовий замір, не частина конвеєра карти. Запускається workflow'ом
«Аналіз 1551» на GitHub, бо з машин чатів домен data.1551.gov.ua закритий.

Що робить:
  1. Метадані набору з data.gov.ua (опис полів, ресурси).
  2. Кілька місяців з API https://data.1551.gov.ua/api/data/РРРР/ММ.
  3. Для кожного місяця — сирі записи (gzip JSONL, щоб чат «Проблеми» міг
     сам розібрати) і профіль: скільки записів, які поля, частка заповнення,
     приклади, найчастіші значення категорійних полів.

Структуру відповіді API ми наперед не знаємо, тому розбір навмисно
загальний: список записів шукаємо як найбільший список у відповіді,
вкладені словники розгортаємо в «ключ.підключ». Висновки про придатність
робить людина по профілю, а не цей скрипт.

Запуск: python src/diag_1551.py 2025-09 2026-03 2026-08   (результат — data/1551/)
"""
import os, sys, json, gzip, time, collections, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', '1551')
API = 'https://data.1551.gov.ua/api/data/{y}/{m}'
META = 'https://data.gov.ua/api/3/action/package_show?id=4df91028-83af-43ca-8e28-36419dd24fa7'
UA = {'User-Agent': 'karta-kyiv-academy/1.0 (navchalnyi proekt)'}


def get(url, tries=4, timeout=300):
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read(), r.headers.get('Content-Type', '')
        except Exception as e:           # мережа нестабільна — чекаємо й пробуємо ще
            last = e
            print(f'   {url}: {type(e).__name__} {e} — спроба {i + 1}', flush=True)
            time.sleep(20 * (i + 1))
    raise RuntimeError(f'{url}: {last}')


def records(js):
    """Список записів у відповіді довільної форми: сама відповідь-список
    або найбільший список серед значень словника (рекурсивно)."""
    if isinstance(js, list):
        return js
    best = []
    if isinstance(js, dict):
        for v in js.values():
            r = records(v)
            if len(r) > len(best):
                best = r
    return best


def flat(d, pre=''):
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            out.update(flat(v, f'{pre}{k}.'))
    elif isinstance(d, list):
        out[pre[:-1]] = json.dumps(d, ensure_ascii=False)[:300]
    else:
        out[pre[:-1]] = d
    return out


def profile(rows):
    keys = collections.Counter()
    vals = collections.defaultdict(collections.Counter)
    ex = collections.defaultdict(list)
    for r in rows:
        f = flat(r)
        for k, v in f.items():
            if v in (None, '', 'null'):
                continue
            keys[k] += 1
            s = str(v)[:120]
            if len(vals[k]) < 5000:
                vals[k][s] += 1
            if len(ex[k]) < 3 and s not in ex[k]:
                ex[k].append(s)
    n = len(rows)
    pr = {}
    for k, c in keys.most_common():
        distinct = len(vals[k])
        pr[k] = {'заповнено': round(c / n, 3) if n else 0, 'різних': distinct, 'приклади': ex[k]}
        if distinct <= 400:          # категорійне поле — показуємо розподіл
            pr[k]['найчастіші'] = vals[k].most_common(40)
    return pr


def main():
    months = sys.argv[1:] or ['2025-09', '2026-03', '2026-08']
    os.makedirs(OUT, exist_ok=True)
    rep = {'місяці': {}, 'помилки': {}}
    try:
        body, _ = get(META, timeout=60)
        json.dump(json.loads(body), open(os.path.join(OUT, 'metadani.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        print('метадані data.gov.ua — є')
    except Exception as e:
        rep['помилки']['metadani'] = str(e)
    for ym in months:
        y, m = ym.split('-')
        try:
            body, ctype = get(API.format(y=y, m=m))
            print(f'{ym}: {len(body) / 1e6:.1f} МБ, {ctype}', flush=True)
            open(os.path.join(OUT, f'pochatok-{ym}.txt'), 'wb').write(body[:3000])
            js = json.loads(body)
            rows = records(js)
            with gzip.open(os.path.join(OUT, f'syri-{ym}.jsonl.gz'), 'wt', encoding='utf-8') as fh:
                for r in rows:
                    fh.write(json.dumps(r, ensure_ascii=False) + '\n')
            rep['місяці'][ym] = {'байт': len(body), 'тип': ctype, 'записів': len(rows),
                                 'корінь': type(js).__name__,
                                 'ключі_кореня': list(js)[:30] if isinstance(js, dict) else None,
                                 'поля': profile(rows)}
            print(f'   записів: {len(rows):,}', flush=True)
        except Exception as e:
            rep['помилки'][ym] = str(e)
            print(f'{ym}: ПОМИЛКА {e}', flush=True)
    json.dump(rep, open(os.path.join(OUT, 'profil.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('готово: data/1551/profil.json')


if __name__ == '__main__':
    main()
