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
# Перельоти коштують ~10 с кожен — знімків мало: увесь тест ≤ 2 хв
MISCIA_ZNIMKIV = [('pl-vokzalna-1', 'пл. Вокзальна, 1')]

# Телефон 375×812 (S-К.21, 36.27; test:telefon): обрана точка над шторкою,
# одна висота шторки для адреси й соти, текст ≥14 px, вкладки 44 px, +/− над шторкою
JS_TELEFON = r"""async (adr) => {
 const i=KT.P.findIndex(p=>p[3]&&(p[2]||'').includes(adr)); if(i<0) return {bad:['немає адреси '+adr]};
 KT.setView('addr'); KT.map.jumpTo({center:[KT.P[i][1],KT.P[i][0]],zoom:17}); KT.openAt(i);
 await new Promise(r=>{KT.map.once('idle',r); setTimeout(r,6000)});
 const el=document.getElementById('kplace'), c=el.getBoundingClientRect(), m=KT.map.getContainer().getBoundingClientRect();
 const q=KT.map.project([KT.P[i][1],KT.P[i][0]]), bad=[];
 if(m.top+q.y>c.top-8) bad.push(`точка під шторкою: y ${Math.round(m.top+q.y)}, шторка від ${Math.round(c.top)}`);
 const px=s=>parseFloat(getComputedStyle(s).fontSize);
 const sum=el.querySelector('.kp-sum'); if(sum&&px(sum)<14) bad.push(`текст картки ${px(sum)} px < 14`);
 for(const b of el.querySelectorAll('.kp-tabs button')) if(b.getBoundingClientRect().height<43.5){bad.push(`вкладка ${Math.round(b.getBoundingClientRect().height)} px < 44`); break}
 const ctl=document.querySelector('.maplibregl-ctrl-bottom-right').getBoundingClientRect();
 if(ctl.bottom>c.top+1) bad.push(`+/− під шторкою: низ ${Math.round(ctl.bottom)}, шторка від ${Math.round(c.top)}`);
 const hA=Math.round(c.height);
 const B=[...KT.hexb('S').values()].find(b=>b.ad.includes(i));
 if(B){KT.openCell('СОТА',B.ad,[B.cx,B.cy,130],null); await new Promise(r=>setTimeout(r,300));
  const hS=Math.round(el.getBoundingClientRect().height); if(Math.abs(hS-hA)>2) bad.push(`висота шторки: адреса ${hA}, сота ${hS}`);
  KT.closeCell(); KT.openAt(i)}
 return {bad, hA}}"""

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
        # Блоки проблем у картці адреси (Андрій 26.10): «X з Y подій адреси» —
        # X (події проблеми на цій адресі) не більше Y (усі події адреси).
        # Усі адреси з проблемою, не вибірка: їх кілька сотень.
        bloky = pg.evaluate(r'''()=>{const out={n:0,bad:[]};
          KT.P.forEach((p,i)=>{ if(!p[3]||!KT.probsOf(p).length) return;
            KT.kartkaAdresy(i);
            document.querySelectorAll('#kplace [data-kp-prob] .tt').forEach(t=>{out.n++;
              const m=t.textContent.replace(/ | /g,'').match(/^(\d+)з(\d+)/);
              if(!m||+m[1]>+m[2]) out.bad.push(p[2]+': '+t.textContent)})});
          KT.closePlace(); return out}''')
        res['bad'] += [f'блок проблеми: {b}' for b in bloky['bad']]
        res['n']['blokiv'] = bloky['n']
        t_perevirky = time.time() - t1
        # 3D за логікою сот (36.55, S-К.4, test:vyhliady_3d): вигляди — три;
        # кнопка «3D» лише в сотах; на кожному зумі з даними — рівно один шар k-col-*
        d3 = pg.evaluate(r'''async()=>{const bad=[], vy=[...document.querySelectorAll('#fcat [data-m]')].map(b=>b.dataset.m);
          if(vy.join()!=='soty,rings,addr') bad.push('вигляди: '+vy.join());
          const b3=()=>document.querySelector('#f3d');
          KT.setView('addr'); if(b3()&&!b3().hidden) bad.push('кнопка 3D в адресах');
          KT.setView('soty'); if(!b3()||b3().hidden) bad.push('немає кнопки 3D у сотах');
          KT.setView('stovp');
          for(const z of [11,13,15.5]){KT.map.jumpTo({center:[30.52,50.45],zoom:z});
            await new Promise(r=>{KT.map.once('idle',r); setTimeout(r,4000)});
            const vis=['L','S','X'].filter(id=>KT.map.getLayer('k-col-'+id)&&KT.map.getLayoutProperty('k-col-'+id,'visibility')!=='none'
              &&KT.map.querySourceFeatures('k-col-'+id).length);
            if(vis.length!==1) bad.push('z'+z+': шарів стовпчиків '+vis.length)}
          KT.setView('soty'); return bad}''')
        res['bad'] += [f'3D: {b}' for b in d3]
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
        # телефон: окремий контекст з дотиком (pointer:coarse, як на справжньому)
        ct = br.new_context(viewport={'width': 375, 'height': 812}, is_mobile=True, has_touch=True, device_scale_factor=2)
        tp = ct.new_page()
        tp.route('**/tiles.openfreemap.org/fonts/**', lambda r: r.abort())
        tp.goto(url)
        tp.wait_for_function('window.KT&&KT.ready', timeout=90000)
        tel = tp.evaluate(JS_TELEFON, 'пл. Вокзальна, 1')
        if znimky:
            os.makedirs(ZNIMKY, exist_ok=True); tp.screenshot(path=os.path.join(ZNIMKY, 'telefon-pl-vokzalna-1.png'))
        ct.close()
        br.close()
    srv.shutdown()
    bad, c = res['bad'] + [f'телефон: {b}' for b in tel['bad']], res['n']
    print(f"   телефон 375×812: шторка {tel.get('hA')} px, точка над нею, +/− над нею; помилок {len(tel['bad'])}")
    print(f"   адрес {c['adres']} (з них з проблемою {c['z_problemoiu']}), сот {c['sot']}, проблем {c['problem']}, "
          f"кілець {c['kilets']}, блоків проблем у картках {c.get('blokiv', 0)}; розбіжностей {len(bad)}; {time.time() - t0:.0f} с (перевірка {t_perevirky:.0f} с)"
          + (f'; знімки — {os.path.relpath(ZNIMKY, ROOT)}' if znimky else ''))
    for b in bad[:40]: print('   ПОМИЛКА', b)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(int(sys.argv[1]) if len(sys.argv) > 1 else 300))
