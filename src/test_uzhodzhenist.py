# -*- coding: utf-8 -*-
"""Автоматична перевірка узгодженості карти (S-К.14, RISHENNYA 36.23.6).

Зібрана карта (site/index.html) у справжньому браузері (Playwright, Chromium),
одне відкриття сторінки, без перельотів: через місток window.KT (tpl_vyhlyady)
викликаються ті самі функції, що й при наведенні та кліку, — підказка,
картка, колір. Для N випадкових місць кожного вигляду:
  * адреса: число на карті = підказка = картка = сума статей; колір кола =
    kolirMisca; ризик у картці = rizykPoruch у 50 м;
  * сота (усі три сітки): число = підказка = картка = сума видів; колір соти =
    kolirMisca; ризик у картці = rizykPoruch у межах соти;
  * 50 проблем: окрема картка проблеми = число подій проблеми; картка адреси з
    проблемою — усі події адреси, як і в будь-якої іншої (S-К.12);
  * кільця: число на кільці = сума подій його адрес (kartaKilcia).

Перельоти — лише для знімків (ZNIMKY): пл. Вокзальна, 1, Хрещатик 22, Теліги 13
і соти Києва на z11, у vykhid/znimky. Переліт у браузері без відеокарти коштує
~10 с; увесь тест має вкладатися у 2 хвилини (ліміт «Оновлення карти»).

Запуск: py -3 src/test_uzhodzhenist.py [N]. Код 1 — є розбіжності.
"""
import os, sys, time, threading, functools, http.server, socketserver

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, 'site')
ZNIMKY = os.path.join(ROOT, 'vykhid', 'znimky')
MISCIA_ZNIMKIV = [('pl-vokzalna-1', 'пл. Вокзальна, 1'), ('khreshchatyk-22', 'вул. Хрещатик, 22'),
                  ('telihy-13', 'Теліги, 13')]

# Уся перевірка — один виклик у сторінці: 300 місць × вигляд за секунди
JS = r"""async ([N, seed]) => {
 let s=seed>>>0; const rnd=()=>{s=(s+0x6D2B79F5)>>>0; let t=s; t=Math.imul(t^t>>>15,t|1); t^=t+Math.imul(t^t>>>7,t|61); return ((t^t>>>14)>>>0)/4294967296};
 const vybir=(xs,k)=>{const a=xs.slice(); for(let i=a.length-1;i>0;i--){const j=Math.floor(rnd()*(i+1)); [a[i],a[j]]=[a[j],a[i]]} return a.slice(0,k)};
 const num=s=>{const m=/\d[\d\s  ]*/.exec(s||''); return m?+m[0].replace(/\D/g,''):null};
 const bad=[], n={adres:0, z_problemoiu:0, sot:0, problem:0, kilets:0};
 const st=KT.st, MG=st.MG, tot=st.tot;
 // ---- адреси ----
 const F=new Map(KT.kolaAdres().map(f=>[f.properties.i,f.properties.c]));
 for(const v of vybir(st.vis,N)){const p=v[0], i=KT.PIDX.get(p); n.adres++;
  const kol=KT.pala(KT.kolirMisca(v[4],MG,tot));
  if(F.get(i)!==kol) bad.push(`адреса ${p[2]}: колір кола ${F.get(i)} ≠ kolirMisca ${kol}`);
  const t=/<span>([^<]*)/.exec(KT.pidkazkaAdresy(i)), tip=num(t&&t[1]);
  if(KT.probsOf(p).length) n.z_problemoiu++;
  const k=KT.kartkaAdresy(i), suma=k.statti.reduce((a,b)=>a+b,0), rz=KT.rizykPoruch(p[0],p[1],50);
  if(!(v[1]===tip&&tip===k.sum&&k.sum===suma)) bad.push(`адреса ${p[2]}: карта ${v[1]}, підказка ${tip}, картка ${k.sum}, сума статей ${suma}`);
  if(k.ryzyk!==rz) bad.push(`адреса ${p[2]}: ризик у картці ${k.ryzyk}, rizykPoruch ${rz}`)}
 // ---- соти: усі три сітки ----
 KT.setView('soty');
 for(const [id,R] of [['L',330],['S',130],['X',30]]){const B=KT.hexb(id), Fs=KT.soty(id);
  for(const f of vybir(Fs,Math.ceil(N/3))){const b=B.get(f.properties.k); if(!b) continue; n.sot++;
   const kol=KT.pala(KT.kolirMisca(b.g,MG,tot));
   if(f.properties.c!==kol) bad.push(`сота ${id} ${b.k}: колір ${f.properties.c} ≠ kolirMisca ${kol}`);
   const tip=num(KT.pidkazkaSoty(b)), k=KT.kartkaSoty(b,R), suma=k.vydy.reduce((a,c)=>a+c,0);
   const rz=KT.rizykPoruch(b.cy/KT.MY_,b.cx/KT.MX_,R);
   if(!(b.n===tip&&tip===k.sum&&k.sum===suma)) bad.push(`сота ${id} ${b.k}: карта ${b.n}, підказка ${tip}, картка ${k.sum}, сума видів ${suma}`);
   if(k.ryzyk!==rz) bad.push(`сота ${id} ${b.k}: ризик у картці ${k.ryzyk}, rizykPoruch ${rz}`)}}
 // ---- проблеми ----
 const pr=[]; KT.P.forEach((p,i)=>KT.probsOf(p).forEach((q,j)=>pr.push([i,j,q])));
 for(const [i,j,q] of vybir(pr,50)){n.problem++;
  const k=KT.kartkaAdresy(i,j), ma=(q.ev&&q.ev.length)?q.ev.length:q.n;
  if(k.sum!==ma) bad.push(`проблема ${KT.P[i][2]} (${q.mech}): картка ${k.sum}, подій проблеми ${ma}`);
  // картка адреси тієї самої точки — усі події адреси, як у підказці
  const v=st.vis.find(x=>x[0]===KT.P[i]); if(!v) continue;
  const ka=KT.kartkaAdresy(i), t=/<span>([^<]*)/.exec(KT.pidkazkaAdresy(i)), tip=num(t&&t[1]);
  if(!(v[1]===tip&&tip===ka.sum)) bad.push(`адреса проблеми ${KT.P[i][2]}: карта ${v[1]}, підказка ${tip}, картка адреси ${ka.sum}`)}
 // ---- кільця ----
 for(const k of (window.kartaKilcia?kartaKilcia(N):[])){n.kilets++;
  if(k.na_kilci!==k.suma_adres) bad.push(`кільце: на кільці ${k.na_kilci}, сума адрес ${k.suma_adres} (${k.adres} адрес)`)}
 return {bad,n}}"""


def server():
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=SITE)
    h.log_message = lambda *a, **k: None
    s = socketserver.TCPServer(('127.0.0.1', 0), h)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s


def main(n=300, seed=36, znimky=True):
    from playwright.sync_api import sync_playwright
    t0 = time.time()
    srv = server()
    url = f'http://127.0.0.1:{srv.server_address[1]}/index.html'
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        pg = br.new_page(viewport={'width': 1366, 'height': 768})
        pg.goto(url)
        pg.wait_for_function('window.KT&&KT.ready', timeout=90000)
        t1 = time.time()
        res = pg.evaluate(JS, [n, seed])
        t_perevirky = time.time() - t1
        if znimky:
            os.makedirs(ZNIMKY, exist_ok=True)
            pg.evaluate('KT.closeCell(); KT.setView("soty"); KT.map.jumpTo({center:[30.52,50.45],zoom:11})')
            pg.evaluate('new Promise(r=>{KT.map.once("idle",r); setTimeout(r,5000)})')
            pg.screenshot(path=os.path.join(ZNIMKY, 'soty-z11.png'))
            for nazva, adr in MISCIA_ZNIMKIV:
                i = pg.evaluate(f'KT.P.findIndex(p=>p[3]&&(p[2]||"").includes({adr!r}))')
                if i < 0: continue
                pg.evaluate(f'KT.setView("addr"); KT.map.jumpTo({{center:[KT.P[{i}][1],KT.P[{i}][0]],zoom:17}}); KT.openAt({i})')
                pg.evaluate('new Promise(r=>{KT.map.once("idle",r); setTimeout(r,5000)})')
                pg.screenshot(path=os.path.join(ZNIMKY, nazva + '.png'))
        br.close()
    srv.shutdown()
    bad, c = res['bad'], res['n']
    print(f"   адрес {c['adres']} (з них з проблемою {c['z_problemoiu']}), сот {c['sot']}, проблем {c['problem']}, "
          f"кілець {c['kilets']}; розбіжностей {len(bad)}; {time.time() - t0:.0f} с (перевірка {t_perevirky:.0f} с)"
          + (f'; знімки — {os.path.relpath(ZNIMKY, ROOT)}' if znimky else ''))
    for b in bad[:40]: print('   ПОМИЛКА', b)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(int(sys.argv[1]) if len(sys.argv) > 1 else 300))
