# -*- coding: utf-8 -*-
"""Кіоск для сенсорного екрана академії — `index.html?kiosk=1` (36.45, 36.55;
ZAVDANNYA-40, 6.3; макет «3D», нижній ряд). Перша версія, чернетка поза меню.

Заставка — великий заголовок, число подій, карта сама йде турами (tury.py),
знизу картка зупинки, справа «Торкніться екрана». Після дотику — ліва панель
(тури, види, райони), над картою вигляди й «3D», справа — «На старт». Без
пошуку й клавіатури, цілі дотику ≥64 px. 90 с без дотику — тури по колу;
дотик зупиняє тур; 3 хв простою — назад на заставку. Звичайна карта цей код
не виконує (без ?kiosk=1 — одразу вихід).
"""
JS_KIOSK = r"""// ==== КІОСК (?kiosk=1) ====
// Тур — спільний рушій tpl_tur (turPusk); кіоск лише вирішує, коли тур іде:
// на заставці — по колу, після дотику — зупинка, 90 с простою — знову тури
if(new URLSearchParams(location.search).has('kiosk')){(async()=>{
 document.body.classList.add('kiosk'); TUR_KIOSK=true; turKnopka();
 const TURY=DANI.tury?await vantazh(DANI.tury):[]; if(!TURY_D) TURY_D=TURY;
 const vsogo=M.podii_vsogo??P.reduce((a,p)=>a+(p[3]?p[4].length:0),0);
 const root=map.getContainer().parentElement;
 const zast=turEl(`<div class="ki-zast"><div class="ki-t">Карта правопорушень Києва</div>
  <div class="ki-n">${fmt(vsogo)} ${pl(vsogo,'подія','події','подій')} з рішень судів</div></div>`);
 const dotyk=turEl(`<div class="ki-dotyk">Торкніться екрана</div>`);
 const panel=turEl(`<div class="ki-p" hidden><div class="ki-ph">Тури</div><div class="ki-tury"></div>
  <div class="ki-ph">Види</div><div class="ki-vydy"></div><div class="ki-ph">Райони</div><div class="ki-rai"></div></div>`);
 const verkh=turEl(`<div class="ki-v" hidden>${[['soty','Соти'],['rings','Кільця'],['addr','Адреси']].map(([k,n])=>`<button data-kv="${k}">${n}</button>`).join('')}</div>`);
 const start=turEl(`<button class="ki-start" hidden>На старт</button>`);
 [zast,dotyk,panel,verkh,start].forEach(x=>root.appendChild(x));
 // «Мікс» — колода (етап 3), далі іменовані тури
 const TURY_K=[...(TUR_KOLODA&&TUR_KOLODA.length?[{nazva:'Мікс',zup:null}]:[]),
  ...TURY.map(t=>({nazva:t.nazva,zup:t.zupynky.map(z=>turIzTury(z,t.nazva))}))];
 panel.querySelector('.ki-tury').innerHTML=TURY_K.map((t,i)=>`<button data-kt="${i}">${esc(t.nazva)}</button>`).join('');
 panel.querySelector('.ki-vydy').innerHTML=M.groups.map((g,gi)=>`<button data-kg="${gi}"><i style="background:${PALA[gi%PALA.length]}"></i>${esc(shortOf(gi))}</button>`).join('');
 panel.querySelector('.ki-rai').innerHTML=DN.map((d,i)=>`<button data-kr="${i}">${esc(d)}</button>`).join('');
 let OST=Date.now(), ZASTAVKA=true;
 const turK=i=>{const t=TURY_K[i]; if(!t) return; turPusk(t.zup||turZupynky(),{nazva:t.zup?t.nazva:'',kolom:true})};
 // на заставці — колода (якщо є), інакше всі іменовані тури поспіль
 const turVsi=()=>turPusk(turZupynky(),{kolom:true});
 function naZastavku(){ZASTAVKA=true; panel.hidden=verkh.hidden=start.hidden=true; zast.hidden=dotyk.hidden=false;
  if(CURD>=0) exitDistrict(); turVsi()}
 function rozbudyty(){ZASTAVKA=false; zast.hidden=dotyk.hidden=true; panel.hidden=verkh.hidden=start.hidden=false; turStop(false)}
 // дотик будь-де: на заставці — будить, під час туру — зупиняє тур
 root.addEventListener('pointerdown',e=>{OST=Date.now();
  if(ZASTAVKA){e.stopPropagation(); rozbudyty(); return}
  if(turIde()&&!e.target.closest('[data-kt]')) turStop(false)},true);
 panel.onclick=e=>{const t=e.target.closest('[data-kt]'); if(t) return turK(+t.dataset.kt);
  const g=e.target.closest('[data-kg]'); if(g){const b=document.querySelector(`#fa .type[data-g="${g.dataset.kg}"]`); if(b) b.click();
   g.classList.toggle('ki-off',b&&!typeOn(+g.dataset.kg)); return}
  const r=e.target.closest('[data-kr]'); if(r) enterDistrict(+r.dataset.kr)};
 verkh.onclick=e=>{const b=e.target.closest('[data-kv]'); if(b) setView(b.dataset.kv)};
 start.onclick=naZastavku;
 setInterval(()=>{const t=(Date.now()-OST)/1000;
  if(!ZASTAVKA&&t>180) naZastavku();
  else if(!ZASTAVKA&&t>90&&!turIde()) turVsi()},1000);
 naZastavku();
})()}
"""

CSS_KIOSK = r"""
/* кіоск (?kiosk=1): цілі дотику ≥64 px, без пошуку й наведення */
body.kiosk #side,body.kiosk #kstrip,body.kiosk #adv{display:none!important}
body.kiosk .ki-zast{position:absolute;left:4vw;top:5vh;z-index:5;color:var(--ink);text-shadow:0 0 12px var(--halo,#fff);pointer-events:none}
body.kiosk .ki-t{font:700 clamp(36px,5vw,96px)/1.05 var(--sans,system-ui)}
body.kiosk .ki-n{font:500 clamp(22px,2.4vw,48px)/1.3 var(--sans,system-ui);margin-top:1vh}
body.kiosk .ki-dotyk{position:absolute;right:4vw;top:50%;z-index:5;font:600 clamp(20px,2vw,40px) var(--sans,system-ui);
 padding:20px 28px;border-radius:40px;background:var(--panel,#fff);box-shadow:0 2px 12px rgba(0,0,0,.25);pointer-events:none}
body.kiosk .ki-p{position:absolute;left:16px;top:16px;bottom:16px;z-index:5;width:min(900px,47vw);overflow:auto;
 background:var(--panel,#fff);border-radius:16px;padding:12px;box-shadow:0 2px 12px rgba(0,0,0,.25)}
body.kiosk .ki-ph{font:700 24px var(--sans,system-ui);margin:12px 4px 8px}
/* тури, види й райони — сіткою, щоб усе вміщалось без прокрутки (центральний чат 31.10) */
body.kiosk .ki-tury,body.kiosk .ki-vydy{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}
body.kiosk .ki-rai{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
body.kiosk .ki-p button,body.kiosk .ki-v button,body.kiosk .ki-start{min-height:64px;min-width:64px;font:600 22px var(--sans,system-ui);
 border:1px solid var(--rule,#ccc);border-radius:12px;background:var(--panel,#fff);color:var(--ink);cursor:pointer}
body.kiosk .ki-p button{display:flex;align-items:center;gap:10px;width:100%;margin:0;padding:6px 14px;text-align:left;line-height:1.2}
body.kiosk .ki-p button i{width:16px;height:16px;border-radius:50%;flex:none}
body.kiosk .ki-p button.ki-off{opacity:.4}
body.kiosk .ki-v{position:absolute;left:50%;transform:translateX(-50%);top:16px;z-index:5;display:flex;gap:8px}
body.kiosk .ki-v button{padding:0 22px}
body.kiosk .ki-start{position:absolute;right:16px;top:16px;z-index:5;padding:0 22px}
body.kiosk #f3d{width:72px;height:72px;top:96px;font-size:22px}
body.kiosk .maplibregl-ctrl-group button{width:64px;height:64px}
body.kiosk .maplibregl-ctrl-group button .maplibregl-ctrl-icon{background-size:36px}
body.kiosk [hidden]{display:none!important}
"""
