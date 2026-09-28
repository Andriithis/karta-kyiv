# -*- coding: utf-8 -*-
"""Камери автоматичної фіксації швидкості (Нацполіція, data.gov.ua) — для ризику ДТП.

Рішення Андрія 28.09: камери долучаються до аналізу проблем і ризиків.
data.gov.ua закритий з машин чатів, тож качає workflow «Аналіз 1551» на
GitHub; результат — гілка analiz-1551, data/vidkryti/kamery/.

Зберігає метадані набору й усі його ресурси як є; розбір полів і відбір
Києва — після першого завантаження (структуру наперед не знаємо).
Запуск: python src/zbir_kamery.py
"""
import os, json, re, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'vidkryti', 'kamery')
ID = 'b7b6349c-d109-45e7-af37-b73310f73cf5'
META = f'https://data.gov.ua/api/3/action/package_show?id={ID}'
UA = {'User-Agent': 'karta-kyiv-academy/1.0 (navchalnyi proekt)'}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        return r.read()


def main():
    os.makedirs(OUT, exist_ok=True)
    zvit = {'ресурси': [], 'помилки': {}}
    try:
        meta = json.loads(get(META))
        json.dump(meta, open(os.path.join(OUT, 'metadani.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        for r in meta.get('result', {}).get('resources', []):
            url = r.get('url') or ''
            name = re.sub(r'[^\w.\-]+', '_', os.path.basename(url.split('?')[0]) or r.get('id', 'res'))
            try:
                body = get(url)
                open(os.path.join(OUT, name), 'wb').write(body)
                zvit['ресурси'].append({'файл': name, 'байт': len(body), 'назва': r.get('name'), 'оновлено': r.get('last_modified')})
            except Exception as e:
                zvit['помилки'][name] = str(e)
    except Exception as e:
        zvit['помилки']['metadani'] = str(e)
    json.dump(zvit, open(os.path.join(OUT, 'zvit.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(zvit, ensure_ascii=False)[:500])


if __name__ == '__main__':
    main()
