# -*- coding: utf-8 -*-
"""Знімки карти за сценами — для workflow «Перевірка збірки» (RISHENNYA 36.49).

На ПК Андрія мало пам'яті (0,5 ГБ вільної), локальна збірка йде годинами,
тож очима перевіряємо знімками з Actions: сцени — JSON-файл
(`znimky/*.json`), кожна сцена — назва, розмір вікна, тема, адреса чи
центр і зум, вигляд, «Ризик», додатковий JS. Знімки — у vykhid/znimky-perevirka/,
workflow кладе їх артефактом. Сайт не публікується.

py -3 src/znimky.py znimky/etap1.json
"""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_uzhodzhenist as TU

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'vykhid', 'znimky-perevirka')


def stsena(br, url, s):
    w, h = s.get('vikno', [1366, 768])
    tel = w < 768
    ct = br.new_context(viewport={'width': w, 'height': h}, is_mobile=tel, has_touch=tel,
                        device_scale_factor=2 if tel else 1,
                        color_scheme='dark' if s.get('tema') == 'temna' else 'light')
    pg = ct.new_page()
    q = s.get('query', '')
    if s.get('storinka'):
        # сторінка звіту, не карта: без очікування KT
        pg.goto(url.replace('index.html', s['storinka']))
        time.sleep(s.get('chekaty', 1))
        os.makedirs(OUT, exist_ok=True)
        pg.screenshot(path=os.path.join(OUT, s['nazva'] + '.png'), full_page=s.get('cila', False))
        ct.close(); print(f'   {s["nazva"]}: {w}×{h}'); return
    pg.goto(url + (('?' + q) if q else ''))
    pg.wait_for_function('window.KT&&KT.ready', timeout=120000)
    js = []
    if s.get('vyhliad'): js.append(f'KT.setView({s["vyhliad"]!r})')
    # змінні сторінки закриті в її області видимості — стан перемикача беремо з aria-pressed
    if 'ryzyk' in s: js.append(f'{{const b=document.querySelector("#frisk"); if((b.getAttribute("aria-pressed")==="true")!=={str(bool(s["ryzyk"])).lower()}) b.click()}}')
    if s.get('adresa'):
        js.append(f'(()=>{{const i=KT.P.findIndex(p=>(p[2]||"").includes({s["adresa"]!r}));'
                  f'if(i<0) return; KT.map.jumpTo({{center:[KT.P[i][1],KT.P[i][0]],zoom:{s.get("zum", 17)}}});'
                  + ('KT.openAt(i);' if s.get('vidkryty', True) else '') + '})()')
    elif s.get('tsentr'):
        js.append(f'KT.map.jumpTo({{center:{json.dumps(s["tsentr"])},zoom:{s.get("zum", 12)}}})')
    if s.get('js'): js.append(s['js'])
    for j in js:
        try: pg.evaluate(j)
        except Exception as e: print(f'   {s["nazva"]}: JS не виконано — {e}')
    pg.evaluate('new Promise(r=>{KT.map.once("idle",r); setTimeout(r,6000)})')
    time.sleep(s.get('chekaty', 1))
    os.makedirs(OUT, exist_ok=True)
    f = os.path.join(OUT, s['nazva'] + '.png')
    pg.screenshot(path=f)
    ct.close()
    print(f'   {s["nazva"]}: {w}×{h} -> {os.path.relpath(f, ROOT)}')


def main(fail):
    from playwright.sync_api import sync_playwright
    stseny = json.load(open(fail, encoding='utf-8'))
    srv = TU.server()
    url = f'http://127.0.0.1:{srv.server_address[1]}/index.html'
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        for s in stseny:
            try: stsena(br, url, s)
            except Exception as e: print(f'   {s.get("nazva")}: знімка немає — {e}')
        br.close()
    srv.shutdown()


if __name__ == '__main__':
    for f in sys.argv[1:]: main(f)
