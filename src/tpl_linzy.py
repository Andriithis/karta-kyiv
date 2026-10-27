# -*- coding: utf-8 -*-
"""Лінзи «Місце · Порушник · Ціль» (36.41; мінімальна версія 28.10 —
doslidzhennya/linzy/MVP-28-10.md; макет «Три лінзи карти»).

Лінза керує лише картою: які події яскраві (computeVis рахує тільки їх).
Картка адреси завжди показує всі три сторони — Місце, Порушник, Ціль, — і від
лінзи не залежить. Дані — dani/linzy.<хеш>.json (map_dani, step3_map), на
вимогу: при першому вмиканні лінзи чи першій картці.

Числа — те, що суд написав (мінімум), а не все, що було. Пояснень на карті
немає (S-К.3): «ⓘ» біля «Порушник» веде в «Дослідження».
"""
JS_LINZY = r"""// ==== ЛІНЗИ (36.41) ====
// var, а не let: computeVis (tpl_core) питає лінзу ще під час першої
// перемальовки, до цього місця модуля
var LINZA='misce', LZD=null, LZ_P=null, OZ_ON=new Set([1]), TSIL_ON=null;
// поле цілі -> вид (шторка «Ціль» групує за видом, макет трикутника, п. 7)
const TSIL_VYD={berut:'Майно',u_koho:'Майно',zitknennia:'ДТП',na_koho:'Хуліганство',rechovyna:'Наркотики',
 sposib:'Наркотики',shcho_prodaiut:'Торгівля'};
const zavantazhLinzy=()=>LZ_P||(LZ_P=vantazh(DANI.linzy).then(d=>{LZD=d;
 // ознаки й ціль — властивостями самих подій: evOn і картки бачать їх одразу
 d.e.forEach((evs,i)=>{const pe=P[i]&&P[i][4]; if(pe) evs.forEach((x,k)=>{const e=pe[k]; if(e){e.oz=x[0]; e.st=x[1]; e.ts=x[2]}})});
 if(TSIL_ON===null){const t=d.v.indexOf('berut=телефон'); TSIL_ON=t>=0?t:0}
 if(LINZA!=='misce') draw(); else lzPanel();
 if(PLACE) renderPlace()}));
function ozMaska(){let m=0; OZ_ON.forEach(b=>m|=b); return m}
// чи подія яскрава в поточній лінзі (лише для карти — computeVis)
function lzOn(e){
 // до виконання цього місця модуля LINZA ще undefined — це «Місце»
 if(LINZA!=='porush'&&LINZA!=='tsil') return true;
 if(!LZD) return false;
 if(LINZA==='porush') return !!((e.oz||0)&ozMaska());
 return !!(e.ts&&e.ts.includes(TSIL_ON))}
// Підпис цілі — коротка фраза, що читається без заголовка групи («зіткнення
// з авто 45», а не «інше авто 45»)
const LZ_FRAZA={'zitknennia=інше авто':'зіткнення з авто','zitknennia=припарковане авто':'наїзд на припарковане авто',
 'zitknennia=опора, огорожа':'наїзд на опору, огорожу','zitknennia=пішохід':'наїзд на пішохода',
 'zitknennia=велосипед, самокат':'зіткнення з велосипедом, самокатом','u_koho=людина':'у людини','u_koho=магазин':'у магазину',
 'na_koho=перехожі':'на перехожих','na_koho=поліція':'на поліцію','na_koho=персонал закладу':'на персонал закладу',
 'na_koho=майно':'пошкодження майна','shcho_prodaiut=тютюн і вейпи':'продаж тютюну й вейпів','shcho_prodaiut=алкоголь':'продаж алкоголю',
 'sposib=закладка':'закладка','sposib=онлайн':'купівля онлайн','sposib=пошта':'поштою'};
const lzNazva=c=>LZ_FRAZA[LZD.v[c]]||LZD.v[c].split('=')[1];
// лінза ввімкнена — «Проблеми» сховані повністю: і перемикач, і контури (макет)
// (оголошення функції, не const: карта питає її ще до цього місця модуля)
function lzActive(){return LINZA==='porush'||LINZA==='tsil'}
// ---- ПАНЕЛЬ: перемикач, рядок вибору, шторка ----
$('#sugg').insertAdjacentHTML('afterend',
 `<div class="lz-seg" id="flinza" role="tablist">${[['misce','Місце'],['porush','Порушник'],['tsil','Ціль']].map(([k,n])=>
  `<button role="tab" data-lz="${k}" aria-selected="${k==='misce'}">${n}</button>`).join('')}</div>
 <button class="lz-sel" id="flsel" hidden aria-expanded="false"><span id="flselt"></span><span class="lz-n" id="flseln"></span></button>
 <div class="lz-dd" id="fldd" hidden></div>`);
$('#flinza').onclick=e=>{const b=e.target.closest('[data-lz]'); if(!b) return;
 LINZA=b.dataset.lz; document.querySelectorAll('#flinza [data-lz]').forEach(x=>x.setAttribute('aria-selected',x===b));
 // у лінзах «Проблеми» й «Ризик» сховані (MVP, п. 2)
 const lens=LINZA!=='misce';
 const fp=$('#fprob'); if(fp){ if(lens&&ONLYP){ONLYP=false; swSet(fp,false)} fp.hidden=lens}
 const fr=$('#frisk'); if(fr){ if(lens&&RISK_ON) fr.click(); fr.parentElement.hidden=lens}
 $('#flsel').hidden=!lens; $('#fldd').hidden=true; $('#flsel').setAttribute('aria-expanded','false');
 if(lens) zavantazhLinzy();
 draw()};
$('#flsel').onclick=()=>{const dd=$('#fldd'); dd.hidden=!dd.hidden; $('#flsel').setAttribute('aria-expanded',!dd.hidden); lzPanel()};
$('#fldd').onclick=e=>{
 const o=e.target.closest('[data-oz]'); if(o){const b=+o.dataset.oz; OZ_ON.has(b)?OZ_ON.delete(b):OZ_ON.add(b); draw(); return}
 const t=e.target.closest('[data-ts]'); if(t){TSIL_ON=+t.dataset.ts; $('#fldd').hidden=true; $('#flsel').setAttribute('aria-expanded','false'); draw()}};
// Числа — події (не рішення) за поточним фільтром, кожен пункт окремо
function lzLich(){
 const C=sel('c'),A=sel('a'),Y=sel('y'),H=hoursSel(), oz={}, ts={}, vyd={}, m=ozMaska();
 for(const p of P){ if(!p[3]||!inScope(p)) continue;
  for(const e of p[4]){ if(!evOn(e,C,A,Y,H)) continue;
   for(const [b] of LZD.oz) if((e.oz||0)&b) oz[b]=(oz[b]||0)+1;
   if(e.ts) for(const c of e.ts) ts[c]=(ts[c]||0)+1;
   if(LINZA!=='misce'&&lzOn(e)){const g=CATTH[e[1]]; vyd[g]=(vyd[g]||0)+1}}}
 return {oz,ts,vyd}}
function lzPanel(){
 if(!document.getElementById('flinza')) return;     // панель лінз ще не вставлено
 const lens=LINZA==='porush'||LINZA==='tsil';
 document.querySelectorAll('#fa .type').forEach(b=>{let s=b.querySelector('.lz-n');
  if(!lens||!LZD){ if(s) s.remove(); b.classList.remove('lz-blid'); return}
  // span, не i: «i» в кнопці виду — кольорова мітка (tpl_style .type i)
  if(!s){s=document.createElement('span'); s.className='lz-n'; b.appendChild(s)}});
 if(!lens||!LZD){ if(lens){$('#flselt').textContent='…'; $('#flseln').textContent=''} return}
 const L=lzLich();
 document.querySelectorAll('#fa .type').forEach(b=>{const n=L.vyd[+b.dataset.g]||0;
  b.querySelector('.lz-n').textContent=fmt(n); b.classList.toggle('lz-blid',!n)});
 if(LINZA==='porush'){
  const n=[...OZ_ON].reduce((a,b)=>a+(L.oz[b]||0),0);
  $('#flselt').textContent='Ознака: '+([...OZ_ON].sort().join()==='1'?'основні':[...OZ_ON].length?'обрані':'жодної');
  $('#flseln').textContent=fmt(Object.values(L.vyd).reduce((a,b)=>a+b,0))+' ▾';
  const it=(b,nm)=>`<button class="lz-it" data-oz="${b}" aria-pressed="${OZ_ON.has(b)}"><span>${esc(nm)}</span><i>${fmt(L.oz[b]||0)}</i></button>`;
  const nm=b=>(LZD.oz.find(x=>x[0]===b)||[0,''])[1];
  $('#fldd').innerHTML=`<div class="lz-h">Основні</div>${it(1,nm(1))}
   <div class="lz-h">Адміністративні</div>${it(4,nm(4)+' (переважно водії)')}`;
 } else {
  const t=TSIL_ON!==null&&LZD.v[TSIL_ON]?lzNazva(TSIL_ON):'—';
  $('#flselt').textContent='Ціль: '+t; $('#flseln').textContent=fmt(L.ts[TSIL_ON]||0)+' ▾';
  const gr={}; LZD.v.forEach((c,i)=>{const k=c.split('=')[0]; const h=TSIL_VYD[k]+' · '+(LZD.tn[k]||k).toLowerCase();
   (gr[h]=gr[h]||[]).push(i)});
  $('#fldd').innerHTML=Object.entries(gr).map(([h,ii])=>`<div class="lz-h">${esc(h)}</div>`+
   ii.sort((a,b)=>(L.ts[b]||0)-(L.ts[a]||0)).map(i=>`<button class="lz-it" data-ts="${i}" aria-pressed="${i===TSIL_ON}"><span>${esc(lzNazva(i))}</span><i>${fmt(L.ts[i]||0)}</i></button>`).join('')).join('');
 }}
// ---- КАРТКА АДРЕСИ: три рядки (MVP, п. 4) ----
// Ранг адреси за числом подій — серед точних адрес міста
let RANG=null;
function rangAdresy(i){
 if(!RANG){const a=P.map((p,j)=>[j,p[3]?p[4].length:-1]).filter(x=>x[1]>=0).sort((x,y)=>y[1]-x[1]);
  RANG={n:a.length,r:new Map()}; let r=0, prev=-1; a.forEach(([j,n],k)=>{if(n!==prev){r=k+1; prev=n} RANG.r.set(j,r)})}
 return RANG.r.get(i)}
const fmtTys=n=>n>=1000?Math.round(n/1000)+' тис.':fmt(n);
function triHTML(d){
 const {p,evs}=d, n=evs.length, i=PLACE.i;
 const r=p[3]?rangAdresy(i):null;
 const misce=`${fmt(n)} ${pl(n,'подія','події','подій')}`+(r?` · ${r}-га адреса міста з ${fmtTys(RANG.n)}`:'');
 let por='…', tsl='…';
 if(LZD){
  const E=evs.map(EVR), z=E.filter(e=>e.oz);
  if(!z.length) por='—';
  else{const c={}; z.forEach(e=>LZD.oz.forEach(([b])=>{if(e.oz&b) c[b]=(c[b]||0)+1}));
   por=`<button class="kp-lnk" data-kp-os="1">${fmt(z.length)} з ${fmt(n)} з ознакою</button>`+
    LZD.oz.filter(([b])=>c[b]).map(([b,nm])=>` · ${esc(nm.toLowerCase())} ${fmt(c[b])}`).join('')}
  const t={}; E.forEach(e=>(e.ts||[]).forEach(x=>t[x]=(t[x]||0)+1));
  const top=Object.entries(t).sort((a,b)=>b[1]-a[1]).slice(0,3);
  tsl=top.length?top.map(([x,k])=>`${esc(lzNazva(+x))} ${fmt(k)}`).join(' · '):'—'}
 return `<div class="kp-tri"><b>Місце</b><span>${misce}</span>
  <b>Порушник <a class="kp-i" href="doslidzhennya.html" target="_blank" rel="noopener" title="Що видно про правопорушника">ⓘ</a></b><span>${por}</span>
  <b>Ціль</b><span>${tsl}</span></div>`}
// ---- СПИСОК ОСІБ (MVP, п. 5): одне рішення з ознакою — один рядок ----
function osobyHTML(d){
 const E=d.evs.filter(r=>EVR(r).oz);
 const nm=e=>LZD.oz.filter(([b])=>e.oz&b).map(([,n])=>n.toLowerCase()).join(', ');
 return `<div class="kp-osh"><button class="kp-lnk" data-kp-os="0">‹ огляд</button> ${fmt(E.length)} ${pl(E.length,'особа','особи','осіб')} з ознакою · нові зверху</div>`+
  (E.length?E.map(r=>{const e=EVR(r), st=e.st===1?'Ч., ':e.st===2?'Ж., ':'';
   return `<div class="kp-os" role="button" tabindex="0" data-kp-osoba="${r.join('-')}"><b>${st}${esc(nm(e))}</b>`+
    `<span>${esc(M.cats[e[1]].split(' · ')[0])}${M.mon0?' · '+monName(e[5]):''}</span></div>`}).join('')
   :'<div class="kp-empty">—</div>')}
function monName(m){const [y,mm]=M.mon0.split('-').map(Number), t=(y*12+mm-1)+m;
 return String(t%12+1).padStart(2,'0')+'.'+Math.floor(t/12)}
"""
