// ==== ТУР (кнопка «Тур» і кіоск) ====
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
 if(e.target&&e.target.closest&&e.target.closest('#ftur,#fzvuk')) return;
 turStop(true)},true);
// ---- колода (етап 3): щоразу 8–10 зупинок, випадково, але з ритмом ----
// цифра → 2–3 місця → історія → «що робити» → …; не більше двох однакових
// видів поспіль; та сама зупинка в одному турі не повторюється
function kolodaTur(K,n=8+Math.floor(Math.random()*3)){
 const po={}; K.forEach(z=>(po[z.typ]=po[z.typ]||[]).push(z));
 for(const k in po) po[k].sort(()=>Math.random()-.5);
 const ryt=['chyslo','misce','misce','fabula','shcho','misce','chyslo','misce','fabula','shcho','misce','misce'];
 const out=[], buly=new Set(); let i=0, z=0;
 while(out.length<n&&z<60){z++; const t=ryt[i%ryt.length]; i++;
  const st=out.slice(-2); if(st.length===2&&st.every(x=>x.typ===t)) continue;
  const x=(po[t]||[]).find(q=>!buly.has(q.id)); if(!x) continue;
  buly.add(x.id); out.push(x)}
 return out}
// ---- звук (етап 3): тиха фонова музика синтезом Web Audio — без файлу й мережі,
// ліцензія — наш код; за замовчуванням вимкнено, кнопка «звук» ----
let ZVUK=null;
function zvukPerem(){ if(ZVUK){ZVUK.stop(); ZVUK=null; return false}
 const A=new (window.AudioContext||window.webkitAudioContext)(), g=A.createGain(); g.gain.value=0; g.connect(A.destination);
 g.gain.linearRampToValueAtTime(.05,A.currentTime+3);
 // спокійний акорд, що повільно змінюється (м'які синусоїди)
 const akordy=[[220,277.2,329.6],[196,246.9,293.7],[174.6,220,261.6],[196,246.9,329.6]], os=[];
 for(let k=0;k<3;k++){const o=A.createOscillator(), og=A.createGain(); o.type='sine'; og.gain.value=.33; o.connect(og).connect(g); o.start(); os.push(o)}
 let j=0; const krok=()=>{const a=akordy[j++%akordy.length]; os.forEach((o,k)=>o.frequency.setTargetAtTime(a[k],A.currentTime,1.2))};
 krok(); const tm=setInterval(krok,8000);
 ZVUK={stop(){clearInterval(tm); g.gain.setTargetAtTime(0,A.currentTime,.4); setTimeout(()=>A.close(),1500)}};
 return true}
// ---- кнопка «Тур» зліва внизу, над атрибуцією (справа вгорі — панель і «3D») ----
function turKnopka(){let b=document.getElementById('ftur');
 if(!b){b=document.createElement('button'); b.id='ftur'; b.type='button';
  b.onclick=()=>{ if(TUR_STAN) return turStop(true); turPusk(turZupynky(),{nazva:''})};
  map.getContainer().parentElement.appendChild(b);
  // «звук» — поруч з кнопкою туру; видно під час туру й у кіоску
  const s=document.createElement('button'); s.id='fzvuk'; s.type='button'; s.textContent='звук'; s.setAttribute('aria-pressed','false');
  s.onclick=e=>{e.stopPropagation(); s.setAttribute('aria-pressed',String(zvukPerem()))};
  map.getContainer().parentElement.appendChild(s)}
 const sz=document.getElementById('fzvuk'); if(sz) sz.hidden=!TUR_STAN&&!document.body.classList.contains('kiosk');
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
