# -*- coding: utf-8 -*-
"""Фільтри «Порушник ▾» і «Ціль ▾» — колишні лінзи (36.41, 36.53; MVP 28.10 —
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
var LZD=null, LZ_P=null, OZ_ON=null, TSIL_ON=null;
// «основні» — усі ознаки, крім «повторно протягом року» (біт 4): там переважно
// водії без прав, 3,7 тис. подій, і вони затулили б решту
const OZ_ZAMOVCH=b=>b!==4;
// поле цілі -> вид (шторка «Ціль» групує за видом, макет трикутника, п. 7)
const TSIL_VYD={berut:'Майно',u_koho:'Майно',zitknennia:'ДТП',na_koho:'Хуліганство',rechovyna:'Наркотики',
 sposib:'Наркотики',shcho_prodaiut:'Торгівля'};
const zavantazhLinzy=()=>LZ_P||(LZ_P=vantazh(DANI.linzy).then(d=>{LZD=d;
 // ознаки й ціль — властивостями самих подій: evOn і картки бачать їх одразу
 d.e.forEach((evs,i)=>{const pe=P[i]&&P[i][4]; if(pe) evs.forEach((x,k)=>{const e=pe[k]; if(e){e.oz=x[0]; e.st=x[1]; e.ts=x[2]; if(x[3]) e.os=x[3]}})});
 if(TSIL_ON===null){const t=d.v.indexOf('berut=телефон'); TSIL_ON=t>=0?t:0}
 if(OZ_ON===null) OZ_ON=new Set(d.oz.map(x=>x[0]).filter(OZ_ZAMOVCH));
 if(lzFiltr()) draw(); else lzPanel();
 if(PLACE) renderPlace()}));
function ozMaska(){let m=0; if(OZ_ON) OZ_ON.forEach(b=>m|=b); return m}
// Лінзи стали двома фільтрами під видами (36.53, макет «Трикутник у
// картках»): «Порушник ▾» і «Ціль ▾» діють разом — подія яскрава, коли
// проходить обидва ввімкнені.
var OZ_F=false, TS_F=false;
function lzOn(e){
 if(!OZ_F&&!TS_F) return true;
 if(!LZD) return false;
 if(OZ_F&&!((e.oz||0)&ozMaska())) return false;
 if(TS_F&&!(e.ts&&e.ts.includes(TSIL_ON))) return false;
 return true}
// Підпис цілі — коротка фраза, що читається без заголовка групи («зіткнення
// з авто 45», а не «інше авто 45»)
const LZ_FRAZA={'zitknennia=інше авто':'зіткнення з авто','zitknennia=припарковане авто':'наїзд на припарковане авто',
 'zitknennia=опора, огорожа':'наїзд на опору, огорожу','zitknennia=пішохід':'наїзд на пішохода',
 'zitknennia=велосипед, самокат':'зіткнення з велосипедом, самокатом','u_koho=людина':'у людини','u_koho=магазин':'у магазину',
 'na_koho=перехожі':'на перехожих','na_koho=поліція':'на поліцію','na_koho=персонал закладу':'на персонал закладу',
 'na_koho=майно':'пошкодження майна','shcho_prodaiut=тютюн і вейпи':'продаж тютюну й вейпів','shcho_prodaiut=алкоголь':'продаж алкоголю',
 'sposib=закладка':'закладка','sposib=онлайн':'купівля онлайн','sposib=пошта':'поштою'};
const lzNazva=c=>LZ_FRAZA[LZD.v[c]]||LZD.v[c].split('=')[1];
// Фільтри не ховають ні «Проблеми», ні «Ризик» (36.53: діють разом із видами й
// виглядами); функція лишається, бо її питає малювання контурів
function lzActive(){return false}
function lzFiltr(){return OZ_F||TS_F}
// ---- ПАНЕЛЬ: два фільтри під видами, одна шторка ----
let LZ_DD=null;   // 'porush' | 'tsil' — яку шторку відкрито
$('#advbtn').insertAdjacentHTML('beforebegin',
 `<div class="lz-f" id="flf"><button class="lz-sel" id="flpor" aria-expanded="false"><span id="flport">Порушник</span><span class="lz-n" id="flporn">▾</span></button>
 <button class="lz-sel" id="fltsil" aria-expanded="false"><span id="fltsilt">Ціль</span><span class="lz-n" id="fltsiln">▾</span></button></div>
 <div class="lz-dd" id="fldd" hidden></div>`);
function lzVidkryty(k){
 const dd=$('#fldd'), same=LZ_DD===k&&!dd.hidden;
 LZ_DD=k; dd.hidden=same;
 $('#flpor').setAttribute('aria-expanded',String(!dd.hidden&&k==='porush'));
 $('#fltsil').setAttribute('aria-expanded',String(!dd.hidden&&k==='tsil'));
 zavantazhLinzy().then(lzPanel)}
$('#flpor').onclick=()=>lzVidkryty('porush');
$('#fltsil').onclick=()=>lzVidkryty('tsil');
$('#fldd').onclick=e=>{
 if(e.target.closest('[data-vsi]')){ if(LZ_DD==='porush') OZ_F=false; else TS_F=false;
  $('#fldd').hidden=true; draw(); return}
 const o=e.target.closest('[data-oz]'); if(o){const b=+o.dataset.oz; OZ_F=true; OZ_ON.has(b)?OZ_ON.delete(b):OZ_ON.add(b); draw(); return}
 const t=e.target.closest('[data-ts]'); if(t){TSIL_ON=+t.dataset.ts; TS_F=true; $('#fldd').hidden=true; draw()}};
// Числа — події (не рішення) за поточним фільтром, кожен пункт окремо
function lzLich(){
 const C=sel('c'),A=sel('a'),Y=sel('y'),H=hoursSel(), oz={}, ts={}, vyd={}, m=ozMaska();
 for(const p of P){ if(!p[3]||!inScope(p)) continue;
  for(const e of p[4]){ if(!evOn(e,C,A,Y,H)) continue;
   for(const [b] of LZD.oz) if((e.oz||0)&b) oz[b]=(oz[b]||0)+1;
   if(e.ts) for(const c of e.ts) ts[c]=(ts[c]||0)+1;
   if(lzFiltr()&&lzOn(e)){const g=CATTH[e[1]]; vyd[g]=(vyd[g]||0)+1}}}
 return {oz,ts,vyd}}
function lzPanel(){
 if(!document.getElementById('flf')) return;     // панель фільтрів ще не вставлено
 const lens=lzFiltr();
 $('#flpor').classList.toggle('lz-on',OZ_F); $('#fltsil').classList.toggle('lz-on',TS_F);
 document.querySelectorAll('#fa .type').forEach(b=>{let s=b.querySelector('.lz-n');
  if(!lens||!LZD){ if(s) s.remove(); b.classList.remove('lz-blid'); return}
  // span, не i: «i» в кнопці виду — кольорова мітка (tpl_style .type i)
  if(!s){s=document.createElement('span'); s.className='lz-n'; b.appendChild(s)}});
 if(!LZD){$('#flport').textContent='Порушник'; $('#fltsilt').textContent='Ціль'; return}
 const L=lzLich();
 if(lens) document.querySelectorAll('#fa .type').forEach(b=>{const n=L.vyd[+b.dataset.g]||0;
  b.querySelector('.lz-n').textContent=fmt(n); b.classList.toggle('lz-blid',!n)});
 const zam=LZD.oz.every(([b])=>OZ_ON.has(b)===OZ_ZAMOVCH(b));
 $('#flport').textContent='Порушник'+(OZ_F?': '+(zam?'основні':OZ_ON.size?'обрано '+OZ_ON.size:'жодної'):'');
 $('#fltsilt').textContent='Ціль'+(TS_F&&LZD.v[TSIL_ON]?': '+lzNazva(TSIL_ON):'');
 $('#flporn').textContent=(OZ_F?fmt(Object.values(L.oz).length?LZD.oz.filter(([b])=>OZ_ON.has(b)).reduce((a,[b])=>a+(L.oz[b]||0),0):0)+' ':'')+'▾';
 $('#fltsiln').textContent=(TS_F?fmt(L.ts[TSIL_ON]||0)+' ':'')+'▾';
 if($('#fldd').hidden) return;
 const vsi=`<button class="lz-it" data-vsi="1" aria-pressed="${LZ_DD==='porush'?!OZ_F:!TS_F}"><span>усі події</span><i></i></button>`;
 if(LZ_DD==='porush'){
  const it=([b,nm])=>`<button class="lz-it" data-oz="${b}" aria-pressed="${OZ_F&&OZ_ON.has(b)}"><span>${esc(nm+(b===4?' (переважно водії)':''))}</span><i>${fmt(L.oz[b]||0)}</i></button>`;
  // групи — як на сторінці «Заходи»: Діти / Дорослі (Андрій 27.10)
  const gr=[...new Set(LZD.oz.map(x=>x[2]))];
  $('#fldd').innerHTML=vsi+gr.map(g=>`<div class="lz-h">${esc(g)}</div>`+LZD.oz.filter(x=>x[2]===g).map(it).join('')).join('');
 } else {
  const gr={}; LZD.v.forEach((c,i)=>{const k=c.split('=')[0]; const h=TSIL_VYD[k]+' · '+(LZD.tn[k]||k).toLowerCase();
   (gr[h]=gr[h]||[]).push(i)});
  $('#fldd').innerHTML=vsi+Object.entries(gr).map(([h,ii])=>`<div class="lz-h">${esc(h)}</div>`+
   ii.sort((a,b)=>(L.ts[b]||0)-(L.ts[a]||0)).map(i=>`<button class="lz-it" data-ts="${i}" aria-pressed="${TS_F&&i===TSIL_ON}"><span>${esc(lzNazva(i))}</span><i>${fmt(L.ts[i]||0)}</i></button>`).join('')).join('');
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
  tsl=tsilPoVydakh(E)}
 return `<div class="kp-tri"><b>Місце</b><span>${misce}</span>
  <b>Порушник <a class="kp-i" href="doslidzhennya.html" target="_blank" rel="noopener" title="Що видно про правопорушника">ⓘ</a></b><span>${por}</span>
  <b>Ціль</b><span>${tsl}</span></div>`}
// Ціль — по кожному виду окремим підблоком (36.52, 36.53, S-К.26): змішаний
// рядок «зіткнення з авто 45 · у людини 38 · телефон 27» на пл. Вокзальній, 1
// складав різні види в один перелік. Підпис поля — з linzy.TSIL_NAZVA.
function tsilPoVydakh(E){
 const po={}; E.forEach(e=>{const g=CATTH[e[1]]; (po[g]=po[g]||[]).push(e)});
 const vydy=Object.entries(po).sort((a,b)=>b[1].length-a[1].length);
 if(!vydy.length) return '—';
 return vydy.map(([g,es])=>{const pole={};
  es.forEach(e=>(e.ts||[]).forEach(x=>{const [k]=LZD.v[x].split('='); (pole[k]=pole[k]||{})[x]=(pole[k][x]||0)+1}));
  const ryad=Object.entries(pole).map(([k,c])=>`<i>${esc((LZD.tn[k]||k).toLowerCase())}:</i> `+
   Object.entries(c).sort((a,b)=>b[1]-a[1]).slice(0,3).map(([x,n])=>`${esc(LZD.v[x].split('=')[1])} ${fmt(n)}`).join(' · ')).join('<br>');
  return `<div class="kp-tv"><b><i class="kp-tc" style="background:${PALA[g%PALA.length]}"></i>${esc(shortOf(+g))} · ${fmt(es.length)}</b>`+
   `<span>${ryad||'—'}</span></div>`}).join('')}
// ---- КАРТКА ОСОБИ над фабулою (36.41, S-К.26; поля — src/osoba.py) ----
// Лише прямо написане в рішенні; порожнє — «— у рішенні не вказано». Рішення,
// які нічний прохід ще не перечитав за новим правилом, картки не мають.
const OS_RYADKY=[['Судимості',o=>o.sudymosti===0?'не судимий':o.sudymosti?'раніше судимий':null],
 ['Іспитовий / звільнення',o=>[o.ispytovyi?'вчинив під час іспитового строку':'',o.zvilnenyi?'звільнений з місць позбавлення волі':''].filter(Boolean).join('; ')||null],
 ['Робота',o=>o.robota===undefined?null:{'ні':'не працює','так':'працює'}[o.robota]||o.robota],
 ["Сім'я",o=>o.simja===undefined&&!o.utrymantsi?null:[o.simja||'',o.utrymantsi?'має утриманців':''].filter(Boolean).join(', ')],
 ['Освіта',o=>o.osvita||null],
 ['Нарколог / психіатр',o=>o.narkolog===undefined&&o.psykhiatr===undefined?null:
  [o.narkolog===1?'на обліку в нарколога':o.narkolog===0?'у нарколога не на обліку':'',o.psykhiatr===1?'на обліку в психіатра':o.psykhiatr===0?'у психіатра не на обліку':''].filter(Boolean).join('; ')],
 ['Інше',o=>[o.bez_zhytla?'без постійного житла':'',o.viiskovyi?'військовослужбовець':'',o.vpo?'ВПО':'',o.inozemets?'іноземець':'',o.kharakterystyka?'характеризується '+o.kharakterystyka:''].filter(Boolean).join(', ')||null],
 ['Суд призначив',o=>o.pryznacheno||null]];
function kartkaOsoby(e){const o=e&&e.os; if(!o) return '';
 return `<div class="kp-osk">`+OS_RYADKY.map(([n,f])=>{const v=f(o);
  return `<b>${esc(n)}</b><span>${v?esc(v):'— у рішенні не вказано'}</span>`}).join('')+
  (o.vartist||o.povernuto?`<b>Ціль</b><span>${[o.vartist?'шкода '+fmt(o.vartist)+' грн':'',o.povernuto?'повернуто власнику':''].filter(Boolean).join(', ')}</span>`:'')+`</div>`}
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
