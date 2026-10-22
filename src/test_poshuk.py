# -*- coding: utf-8 -*-
"""Перевірка пошуку на зібраній карті (S-Ш.1, S-Ш.2, S-Ш.5; RISHENNYA 36.18.5,
36.18.7): той самий JS-пошук (window.KT.poshuk), що й у полі пошуку.

  poshuk_143    — 143 запити Е12б, як їх пишуть люди: першим — ≥131;
  poshuk_opysky — 13 запитів з помилкою в літері: у перших п'яти — ≥12;
  poshuk_andrii — запити Андрія: правильна вулиця в перших трьох — усі;
і час відповіді (ПК; на телефоні межа 100 мс — S-Ш.5).

Запуск: py -3 src/test_poshuk.py. Код 1 — не пройдено.
"""
import os, sys, json, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZAPYTY = os.path.join(ROOT, 'doslidzhennya', 'audyt-34', 'kod', 'e12b_a4_zapyty.json')
ANDRII = [('Хрещатик 22', 'хрещатик'), ('Хрещатика 22', 'хрещатик'), ('Вокзальна площа 1', 'вокзальна'),
          ('Теліги 13', 'теліги'), ('Олени Теліги 13', 'теліги'), ('хрищатик', 'хрещатик'),
          ('грушевсьго', 'грушевського'), ('бесарабська', 'бессарабська')]
MEZHI = dict(poshuk_143=131, poshuk_opysky=12)

JS = r"""async ([Q, A]) => {
 await KT.poshukIndeks();
 const r={vidp:[], andrii:[], chas:[]};
 for(const x of Q){const t0=performance.now(), rows=KT.poshuk(x.q).filter(y=>y.t==='a'||y.t==='p'||y.t==='v'); r.chas.push(performance.now()-t0);
  r.vidp.push(rows.slice(0,5).map(y=>y.pidpys))}
 for(const [q,st] of A){const t0=performance.now(), rows=KT.poshuk(q).filter(y=>y.t!=='m'&&y.t!=='0'); r.chas.push(performance.now()-t0);
  r.andrii.push([q, rows.slice(0,3).some(y=>y.pidpys.toLowerCase().includes(st)), rows.slice(0,3).map(y=>y.pidpys)])}
 return r}"""


def main(znimky=False):
    from playwright.sync_api import sync_playwright
    import test_uzhodzhenist as TU
    Q = json.load(open(ZAPYTY, encoding='utf-8'))
    srv = TU.server()
    url = f'http://127.0.0.1:{srv.server_address[1]}/index.html'
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        pg = br.new_page(viewport={'width': 1366, 'height': 768})
        pg.goto(url)
        pg.wait_for_function('window.KT&&KT.ready', timeout=90000)
        r = pg.evaluate(JS, [Q, ANDRII])
        # телефон — процесор ×4 повільніший (Chrome DevTools, «4x slowdown»)
        cdp = pg.context.new_cdp_session(pg)
        cdp.send('Emulation.setCPUThrottlingRate', {'rate': 4})
        r['tel'] = pg.evaluate('''(A)=>A.map(([q])=>{const t0=performance.now(); KT.poshuk(q); return performance.now()-t0})''', ANDRII)
        cdp.send('Emulation.setCPUThrottlingRate', {'rate': 1})
        if znimky:
            # 36.35: знімки списку на ПК і телефоні для чотирьох запитів;
            # спершу — підкладка, щоб на знімку була карта, а не «завантажується»
            pg.evaluate('new Promise(r=>{KT.map.once("idle",r); setTimeout(r,15000)})')
            os.makedirs(TU.ZNIMKY, exist_ok=True)
            for w, h, nm in ((1366, 768, 'pk'), (375, 812, 'telefon')):
                pg.set_viewport_size({'width': w, 'height': h})
                for q in ('хрищ', 'Теліги 1', 'грушевсьго', 'ццц'):
                    pg.fill('#q', ''); pg.type('#q', q); pg.wait_for_timeout(400)
                    pg.screenshot(path=os.path.join(TU.ZNIMKY, f'poshuk-{nm}-{q.replace(" ", "_")}.png'))
        br.close()
    srv.shutdown()
    # Ціль і відповідь порівнюються ключем adr_kliuch (вулиця + номер), а не
    # текстом: «вул. Л. Лук`яненка, 4-Б» і «вул. Левка Лукʼяненка, 4-Б» — одна адреса
    import adr_kliuch as AK
    K = AK.Kliuch()
    def kl(s):
        v, _, b = (s or '').rpartition(', ')
        return (K.vulytsia(v), AK.nh(b)) if v else (K.vulytsia(s), '')
    r['t143'] = r['op5'] = r['nop'] = 0; r['n143'] = len(Q); r['promah'] = []
    for x, rows in zip(Q, r['vidp']):
        cil = kl(x['ціль'])
        if rows and kl(rows[0]) == cil: r['t143'] += 1
        elif len(r['promah']) < 15: r['promah'].append(f"{x['vyd']}: «{x['q']}» -> {rows[0] if rows else '—'} (ціль {x['ціль']})")
        if x['vyd'] == 'помилка в літері':
            r['nop'] += 1
            r['op5'] += any(kl(y)[0] == cil[0] for y in rows[:5])
    ch = sorted(r['chas'])
    print(f"   143 запити: першим {r['t143']} з {r['n143']} (межа {MEZHI['poshuk_143']}); описки: у перших п'яти "
          f"{r['op5']} з {r['nop']} (межа {MEZHI['poshuk_opysky']}); час: медіана {ch[len(ch) // 2]:.1f} мс, макс {ch[-1]:.1f} мс (ПК), "
          f"телефон (процесор ×4) — макс {max(r['tel']):.0f} мс (межа 100)")
    bad = 0
    if max(r['tel']) > 100: bad += 1; print('   ПОМИЛКА відповідь на телефоні довша за 100 мс')
    for q, ok, top in r['andrii']:
        if not ok: bad += 1; print(f'   ПОМИЛКА запит Андрія «{q}» — у перших трьох {top}')
    for p in r['promah']: print('   промах', p)
    if r['t143'] < MEZHI['poshuk_143'] or r['op5'] < MEZHI['poshuk_opysky']: bad += 1
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main('--znimky' in sys.argv))
