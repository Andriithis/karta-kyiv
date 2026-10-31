# -*- coding: utf-8 -*-
"""Тур картою — один рушій для кнопки «Тур» на звичайній карті й для кіоску
(ZAVDANNYA-41, етапи 2.1 і 3; 36.44, 36.55).

Тур летить від зупинки до зупинки в 3D (нахил 50–60°, плавна дуга flyTo, на
зупинці — повільне обертання ~10°), знизу — картка зупинки. Будь-який дотик,
клік, клавіша чи коліщатко зупиняє тур і повертає карту, як було (вигляд,
камера). Зупинки — з колоди (tur_koloda, етап 3) або з іменованого туру
(tury.py); формат зупинки один:
  {typ: 'misce'|'chyslo'|'fabula'|'shcho', lat, lon, zum, mitka, zagolovok,
   tekst, chyslo, pidpys, foto?, foto_avtor?}
"""
JS_TUR = r"""// ==== ТУР (кнопка «Тур» і кіоск) ====
var TUR_STAN=null;          // {zup, i, tajmer, kruty, bulo:{MODE,center,zoom,pitch,bearing}, naKinets}
const TUR_ZUPYNKA_MS=8500, TUR_LIT_MS=3800;
const turEl=(h)=>{const d=document.createElement('div'); d.innerHTML=h.trim(); return d.firstChild};
const TUR_K=turEl(`<div class="tur-k" hidden><div class="tur-kh"></div><div class="tur-kz"></div><div class="tur-kt"></div><div class="tur-kn"></div><img class="tur-kf" alt="" hidden><div class="tur-ka"></div></div>`);
map.getContainer().parentElement.appendChild(TUR_K);
function turKartka(z,i,n,nazva){TUR_K.hidden=false;
 TUR_K.dataset.typ=z.typ||'misce';
 TUR_K.querySelector('.tur-kh').textContent=(nazva?nazva+' · ':'')+(i+1)+'/'+n+(z.mitka?' · '+z.mitka:'');
 TUR_K.querySelector('.tur-kz').textContent=z.zagolovok||'';
 TUR_K.querySelector('.tur-kt').textContent=z.tekst||'';
 TUR_K.querySelector('.tur-kn').innerHTML=z.chyslo!=null?`<b>${esc(String(z.chyslo))}</b> ${esc(z.pidpys||'')}`:'';
 const f=TUR_K.querySelector('.tur-kf'), a=TUR_K.querySelector('.tur-ka');
 if(z.foto){f.src=z.foto; f.hidden=false; a.textContent=z.foto_avtor||''} else {f.hidden=true; f.removeAttribute('src'); a.textContent=''}}
function turKrok(){const S=TUR_STAN; if(!S) return;
 if(S.i>=S.zup.length){ if(S.kolom){S.i=0} else return turStop(true)}
 const z=S.zup[S.i], misto=z.typ==='chyslo';
 // місто в цифрах — увесь Київ згори; місце — близько, з нахилом
 const cam=misto?{center:[30.52,50.45],zoom:10.6,pitch:45}:{center:[z.lon,z.lat],zoom:z.zum||15.6,pitch:55};
 map.flyTo({...cam,bearing:(map.getBearing()+20)%360,duration:TUR_LIT_MS,curve:1.6,essential:true});
 turKartka(z,S.i,S.zup.length,S.nazva);
 clearTimeout(S.tajmer);
 // на зупинці — повільне обертання ~10° за час зупинки
 S.tajmer=setTimeout(()=>{ if(TUR_STAN!==S) return;
  map.easeTo({bearing:map.getBearing()+10,duration:TUR_ZUPYNKA_MS-TUR_LIT_MS-300,easing:t=>t,essential:true});
  S.tajmer=setTimeout(()=>{ if(TUR_STAN!==S) return; S.i++; turKrok()},TUR_ZUPYNKA_MS-TUR_LIT_MS)},TUR_LIT_MS);}
// zup — зупинки; kolom — по колу (кіоск); nazva — підпис туру
function turPusk(zup,{nazva='',kolom=false,naKinets=null}={}){
 turStop(false); if(!zup||!zup.length) return;
 const c=map.getCenter();
 TUR_STAN={zup,i:0,nazva,kolom,naKinets,tajmer:null,
  bulo:{MODE,center:[c.lng,c.lat],zoom:map.getZoom(),pitch:map.getPitch(),bearing:map.getBearing()}};
 if(typeof closePlace==='function') closePlace(); if(CELL) closeCell();
 if(MODE!=='stovp') setView('stovp');
 document.body.classList.add('tur-ide'); turKnopka();
 turKrok()}
// povernuty — повернути карту, як була до туру (кнопка «Тур»); кіоск керує сам
function turStop(povernuty=true){const S=TUR_STAN; if(!S) return;
 clearTimeout(S.tajmer); TUR_STAN=null; TUR_K.hidden=true; map.stop();
 document.body.classList.remove('tur-ide'); turKnopka();
 if(povernuty&&S.bulo){ if(MODE!==S.bulo.MODE) setView(S.bulo.MODE);
  map.easeTo({center:S.bulo.center,zoom:S.bulo.zoom,pitch:S.bulo.pitch,bearing:S.bulo.bearing,duration:900})}
 if(S.naKinets) S.naKinets()}
const turIde=()=>!!TUR_STAN;
// Будь-який дотик чи клік зупиняє тур і повертає, як було (ZAVDANNYA-41, 2.1).
// Кіоск ставить свій обробник раніше й сам вирішує, що робити (TUR_KIOSK).
var TUR_KIOSK=false;
for(const ev of ['pointerdown','wheel','keydown']) window.addEventListener(ev,e=>{
 if(!TUR_STAN||TUR_KIOSK) return;
 if(e.target&&e.target.closest&&e.target.closest('#ftur')) return;
 turStop(true)},true);
// ---- кнопка «Тур» зліва внизу, над атрибуцією (справа вгорі — панель і «3D») ----
function turKnopka(){let b=document.getElementById('ftur');
 if(!b){b=document.createElement('button'); b.id='ftur'; b.type='button';
  b.onclick=()=>{ if(TUR_STAN) return turStop(true); turPusk(turZupynky(),{nazva:''})};
  map.getContainer().parentElement.appendChild(b)}
 const ide=!!TUR_STAN; b.textContent=ide?'■':'▶'; b.setAttribute('aria-label',ide?'Зупинити тур':'Тур');
 b.title=ide?'Зупинити тур':'Тур'; b.setAttribute('aria-pressed',String(ide));
 b.hidden=document.body.classList.contains('kiosk')}
// зупинки туру для кнопки: колода (етап 3), інакше — іменовані тури по черзі
var TUR_KOLODA=null, TURY_D=null;
function turZupynky(){
 if(TUR_KOLODA&&TUR_KOLODA.length&&typeof kolodaTur==='function') return kolodaTur(TUR_KOLODA);
 return (TURY_D||[]).flatMap(t=>t.zupynky.slice(0,2).map(z=>turIzTury(z,t.nazva))).slice(0,10)}
const turIzTury=(z,nazva)=>({typ:'misce',lat:z.lat,lon:z.lon,zum:Math.min(z.zum||16,15.8),mitka:nazva,
 zagolovok:z.adresa,tekst:z.istoriia,chyslo:z.chyslo,pidpys:pl(z.chyslo,'раз','рази','разів')+' за цим сценарієм'});
// дані турів — на вимогу, щоб не важчало перше завантаження (36.22)
(async()=>{try{
 if(DANI.tury) TURY_D=await vantazh(DANI.tury);
 if(DANI.koloda) TUR_KOLODA=await vantazh(DANI.koloda);
}catch(e){} turKnopka()})();
"""

CSS_TUR = r"""
/* тур: картка зупинки знизу, кнопка «Тур» зліва внизу (ZAVDANNYA-41) */
.tur-k{position:absolute;left:50%;transform:translateX(-50%);bottom:42px;z-index:6;width:min(760px,calc(100% - 24px));box-sizing:border-box;
 background:var(--panel,#fff);color:var(--ink);border-radius:14px;padding:14px 18px;box-shadow:0 2px 16px rgba(0,0,0,.3);pointer-events:none}
.tur-k[hidden]{display:none}
.tur-kh{font-size:13px;opacity:.7}.tur-kz{font:700 18px/1.25 var(--sans,system-ui);margin:3px 0}
.tur-kt{font-size:15px;line-height:1.4}.tur-kn{margin-top:6px;font-size:15px}.tur-kn b{font-size:26px}
.tur-k[data-typ="chyslo"] .tur-kn b{font-size:44px}
.tur-kf{display:block;max-width:100%;max-height:160px;border-radius:8px;margin-top:8px;object-fit:cover}
.tur-ka{font-size:11px;opacity:.6;margin-top:2px}
#ftur{position:absolute;left:10px;bottom:34px;z-index:4;width:48px;height:48px;border-radius:50%;border:1px solid rgba(127,127,127,.35);
 background:var(--panel,#fff);color:var(--ink,#111);font:600 18px/1 system-ui,sans-serif;box-shadow:0 1px 4px rgba(0,0,0,.2);cursor:pointer}
#ftur[aria-pressed="true"]{background:var(--ink,#111);color:var(--panel,#fff)}
#ftur[hidden]{display:none}
body.kiosk .tur-k{width:min(1100px,70vw);padding:22px 30px;border-radius:18px}
body.kiosk .tur-kh{font-size:clamp(16px,1.2vw,24px)}body.kiosk .tur-kz{font-size:clamp(22px,2vw,40px)}
body.kiosk .tur-kt{font-size:clamp(18px,1.4vw,30px)}body.kiosk .tur-kn{font-size:clamp(18px,1.4vw,28px)}
body.kiosk .tur-kn b{font-size:clamp(32px,3vw,64px)}body.kiosk .tur-k[data-typ="chyslo"] .tur-kn b{font-size:clamp(60px,6vw,120px)}
body.kiosk .tur-kf{max-height:30vh}
@media (max-width:767px){.tur-k{bottom:auto;top:10px;padding:10px 12px}.tur-kz{font-size:16px}.tur-kt{font-size:14px}}
"""
