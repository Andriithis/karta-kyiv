# -*- coding: utf-8 -*-
"""HTML-шаблон карти: розмітка, стилі й уся клієнтська логіка Leaflet.

Плейсхолдери __META__, __PTS__, __RISKS__, __POP__, __FACTS__ підставляє
step3_map.main(). Тут немає жодного обчислення — тільки те, що бачить
і натискає користувач.
"""
TPL = r"""<!DOCTYPE html><html lang="uk"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Карта правопорушень Києва</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>
<style>
*{box-sizing:border-box}html,body{margin:0;height:100%;font:13.5px/1.45 system-ui,sans-serif;background:#0f1117;color:#e8eaf0}
#wrap{display:flex;height:100%}
#side{width:330px;flex:0 0 330px;overflow-y:auto;padding:14px;background:#161922;border-right:1px solid #252a37}
#map{flex:1}h1{font-size:15px;margin:0 0 2px}.sub{color:#79839a;font-size:11.5px}
#cnt{font-size:26px;font-weight:600;margin:12px 0 0;letter-spacing:-.02em}
fieldset{border:0;border-top:1px solid #252a37;padding:11px 0 3px;margin:10px 0 0}
legend{font-size:10.5px;text-transform:uppercase;letter-spacing:.09em;color:#79839a}
label{display:flex;gap:7px;align-items:flex-start;padding:2.5px 0;cursor:pointer}
input[type=checkbox]{accent-color:#e0533d;width:14px;height:14px;margin-top:2px;flex:0 0 auto}
button{width:100%;padding:8px;background:#1f2432;color:#e8eaf0;border:1px solid #303747;border-radius:6px;font:inherit;cursor:pointer;margin-top:7px}
button:hover{background:#28303f}button.act{background:#e0533d;border-color:#e0533d;color:#fff}
.th{font-size:10.5px;text-transform:uppercase;letter-spacing:.07em;color:#5f6878;margin:9px 0 2px}
#hr{display:grid;grid-template-columns:1fr 1fr;gap:5px}
#hr span{padding:7px 4px;background:#1f2432;border-radius:6px;font-size:12px;cursor:pointer;
 user-select:none;text-align:center;line-height:1.15;transition:background .12s}
#hr span:hover{background:#28303f}
#hr span i{display:block;font-style:normal;font-size:10px;color:#6d7789;margin-top:1px}
#hr span.on{background:#e0533d;color:#fff}#hr span.on i{color:#ffd9d0}
#top{margin-top:6px}
#top div{display:flex;justify-content:space-between;gap:8px;padding:5px 7px;background:#1c212c;border-radius:5px;margin-bottom:3px;cursor:pointer;font-size:12.5px}
#top div:hover{background:#252c3a}#top b{color:#e0533d;flex:0 0 auto}
.gr{margin-bottom:2px}
.gh{display:flex;align-items:center;gap:7px;padding:5px 6px;background:#1c212c;border-radius:5px;cursor:pointer;user-select:none}
.gh:hover{background:#232a37}.gh .nm{flex:1;font-size:12.5px}
.gh .n{color:#79839a;font-size:11px}.gh .ar{color:#5f6878;font-size:10px;width:9px}
.gb{display:none;padding:4px 0 6px 22px}.gr.open .gb{display:block}
.gr.open .ar{transform:rotate(90deg)}.ar{display:inline-block;transition:transform .12s}
.gb label{font-size:12px;color:#c4cbd8}.gb .n{color:#5f6878;font-size:10.5px;margin-left:auto;flex:0 0 auto}
.hint{font-size:11px;color:#5f6878;margin-top:7px;line-height:1.4}
#fr label,#frisk label,#fctx label{font-size:12px}
#fr .n,#frisk .n,#fctx .n{color:#5f6878;font-size:10.5px;margin-left:auto;flex:0 0 auto}
#fr .sw,#frisk .sw,#fctx .sw{width:9px;height:9px;border-radius:2px;flex:0 0 auto}
#fcat{display:grid;grid-template-columns:1fr 1fr;gap:5px}
#fcat span{padding:7px 5px;background:#1f2432;border-radius:6px;font-size:12px;cursor:pointer;
 user-select:none;text-align:center;line-height:1.15;transition:background .12s;position:relative}
#fcat span:hover{background:#28303f}
#fcat span i{display:block;font-style:normal;font-size:10px;color:#6d7789;margin-top:1px}
#fcat span.on{background:#2b3243;box-shadow:inset 0 0 0 1.5px currentColor}
#fcat span.c2{color:#f87171}#fcat span.cA{color:#a8b2c4}
.skew{font-size:11.5px;color:#c4cbd8;background:#1c2230;border-left:3px solid #e0533d;
 border-radius:5px;padding:7px 9px;margin-top:9px;line-height:1.4}
.env{margin:8px 0 0}
.env .eh{font-size:10px;text-transform:uppercase;letter-spacing:.07em;color:#8b95a8;margin-bottom:4px}
.dirs{margin:7px 0}.dirs .row{display:flex;gap:7px;align-items:center;font-size:11.5px;margin-bottom:3px}
.dirs .bar2{flex:1;height:4px;background:#232838;border-radius:2px;overflow:hidden}
.dirs .bar2 i{display:block;height:100%;background:#e0533d}
.miss{font-size:11px;color:#8b95a8;background:#1a2030;border-left:2px solid #3b82f6;
 padding:5px 8px;border-radius:4px;margin-top:7px}
.cbadge{display:inline-block;padding:1px 7px;border-radius:99px;font-size:10.5px;
 text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px}
#fr .rh{font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;color:#5f6878;margin:9px 0 2px}
/* ---- прогноз ризику ---- */
#frisk .rw{margin-bottom:5px;border-radius:6px;background:#1a1f2a;padding:6px 8px;
  border-left:3px solid transparent;transition:background .12s}
#frisk .rw:hover{background:#212836}
#frisk .rl{display:flex;align-items:center;gap:7px;cursor:pointer}
#frisk .nm{flex:1;font-size:12.5px;line-height:1.2}
#frisk .acc{font-size:10px;color:#7c8698;padding:1px 5px;border:1px solid #333c4d;border-radius:99px}
#frisk .why{font-size:10.5px;color:#6d7789;margin:3px 0 0 22px;line-height:1.35}
#frisk .rw.nod{opacity:.5}#frisk .rw.nod .rl{cursor:default}
.lgd{display:flex;align-items:center;gap:6px;font-size:10px;color:#5f6878;margin-top:8px}
.lgd i{height:3px;flex:1;border-radius:2px;background:linear-gradient(90deg,#5f6878 0%,currentColor 100%)}
.leaflet-popup-content-wrapper{background:#161922;color:#e8eaf0;border-radius:8px}
.leaflet-popup-tip{background:#161922}
.leaflet-tooltip.rt{background:#161922;border:1px solid #2c3444;color:#e8eaf0;
  font:12px system-ui;border-radius:6px;box-shadow:0 4px 16px rgba(0,0,0,.5);padding:6px 9px}
.leaflet-tooltip.rt:before{display:none}
.leaflet-tooltip.rt b{display:block;margin-bottom:2px}
.leaflet-tooltip.rt span{color:#8b95a8;font-size:11px}
/* висота в частках екрана, інакше висока картка вилазить за верх вікна */
.lp{font-size:12.5px;max-height:min(420px,58vh);overflow-y:auto;overscroll-behavior:contain}
.lp b{display:block;margin-bottom:5px;font-size:13px}
.lp a{color:#c94a34;text-decoration:none}.lp a:hover{text-decoration:underline}
.lp li{margin-bottom:4px;font-size:11.5px}.lp ul{padding-left:15px;margin:3px 0}
.lp .tt{color:#79839a;font-size:11.5px;margin-bottom:7px}
.bd{width:100%;border-collapse:collapse;margin-bottom:8px}
.bd td{padding:2px 0;font-size:12px;vertical-align:top}
.bd td:last-child{text-align:right;padding-left:10px;color:#e0533d;width:44px}
.hg{display:flex;align-items:flex-end;gap:1px;height:24px;margin:2px 0 1px}
.hg i{flex:1;background:#e0533d;opacity:.8;border-radius:1px 1px 0 0}
.hx{display:flex;justify-content:space-between;font-size:9.5px;color:#5f6878;margin-bottom:5px}
.hn{font-size:11px;color:#c4cbd8;background:#232a37;padding:4px 7px;border-radius:4px;margin-bottom:7px}
.pcard{background:#1c2230;border-left:3px solid #f87171;border-radius:5px;padding:8px 9px;margin:8px 0}
.pcard .ph{font-size:10px;text-transform:uppercase;letter-spacing:.07em;color:#8b95a8;margin-bottom:3px}
.pcard .pt{font-size:13px;font-weight:600;margin-bottom:5px;line-height:1.25}
.pcard .pm{font-size:11.5px;color:#c4cbd8;margin-bottom:2px}
.pcard .pm b{color:#e8eaf0}
.pcard .pf{font-size:10.5px;color:#6d7789;margin-top:4px;line-height:1.4}
.pcard .why{font-size:11px;color:#c4cbd8;background:#161c28;border-radius:4px;padding:6px 8px;margin-top:5px}
.pbtn{width:100%;padding:7px;background:#e0533d;color:#fff;border:0;border-radius:6px;
 font:inherit;font-size:12px;cursor:pointer;margin-top:7px}
.pbtn:hover{background:#c94a34}
/* ---- шар чинників середовища ---- */
.fgh{font-size:10px;text-transform:uppercase;letter-spacing:.07em;color:#8b95a8;margin:9px 0 2px}
#ffact label{font-size:12px}
#ffact .n{color:#5f6878;font-size:10.5px;margin-left:auto;flex:0 0 auto}
#ffact .sw{width:9px;height:9px;border-radius:99px;flex:0 0 auto;margin-top:3px}
.pbtn2{width:100%;padding:6px;background:#2b3243;color:#e8eaf0;border:1px solid #3a4256;
 border-radius:6px;font:inherit;font-size:11.5px;cursor:pointer;margin-top:5px}
.pbtn2:hover{background:#343d52}
.ex{font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;color:#5f6878;margin-top:6px}
.rpop b{display:block;margin-bottom:4px;font-size:13px}
.rpop .rmeth{font-size:11px;color:#8b95a8;margin:6px 0;line-height:1.4}
.rpop table{width:100%;border-collapse:collapse;margin-top:4px}
.rpop td{padding:1.5px 0;font-size:11px}
.rpop td:last-child{text-align:right;color:#e0533d}
.rpop .rdoc{display:block;margin-top:8px;font-size:11.5px;color:#7cb2ff;text-decoration:none}
.rpop .rdoc:hover{text-decoration:underline}
#docs a{display:block;font-size:12.5px;color:#7cb2ff;text-decoration:none;padding:3px 0}
#docs a:hover{text-decoration:underline}
@media(max-width:760px){#wrap{flex-direction:column}#side{width:100%;flex:0 0 auto;max-height:50%}}
</style></head><body><div id="wrap"><div id="side">
<h1>Карта правопорушень</h1><div class="sub" id="subt">за даними ЄДРСР · місто Київ</div>
<div id="backl"></div>
<div id="skew"></div>
<div id="cnt">0</div><div class="sub" id="cntl"></div>
<button id="heat">Теплова карта</button><button id="reset">Скинути фільтри</button>
<fieldset><legend>Що показувати</legend><div id="fcat"></div>
<div class="hint" id="cathint"></div></fieldset>
<fieldset><legend>Топ адрес за фільтром</legend><div id="top"></div></fieldset>
<fieldset><legend>Район</legend><div id="fc"></div></fieldset>
<fieldset><legend>Правопорушення</legend>
<div style="display:flex;gap:6px"><button id="none" style="margin:0 0 8px">Зняти всі</button>
<button id="all" style="margin:0 0 8px">Обрати всі</button></div><div id="fa"></div></fieldset>
<fieldset><legend>Прогноз ризику</legend><div id="frisk"></div>
<div class="hint">Модель оцінює <b>кожну вулицю</b> за умовами середовища, незалежно від того, чи були там події. Клікніть на вулицю — розбір чинників і методики відкриється в спливному вікні. У кружечку — влучність: яка частка подій наступних років припала на верхні 10% відібраних вулиць.</div>
</fieldset>
<fieldset><legend>Документи</legend><div id="docs"></div>
<div class="hint">Збираються автоматично з тих самих даних, що й карта.</div></fieldset>
<fieldset><legend>Середовище</legend><div id="ffact"></div>
<div class="hint" id="fzoom"></div>
<button id="fclear">Прибрати підсвітку</button>
<div class="hint" id="fhint"></div></fieldset>
<fieldset><legend>Контекст</legend><div id="fctx"></div>
<div class="hint">Населення — фон під картою, за даними Kontur (комірки 400 м). Потоки — модельовані пішохідні маршрути від житла до цілей, з урахуванням населення. Товщина = кількість людей.</div></fieldset>
<fieldset><legend>Рік</legend><div id="fy"></div></fieldset>
<fieldset><legend>Час доби</legend><div id="hr"></div>
<div class="hint">Порожній вибір = усі. Розмір кола = кількість подій за адресою. Сірі кола — прив'язка лише до вулиці, без номера будинку.</div></fieldset>
</div><div id="map"></div></div>
<script>
const M=__META__, P=__PTS__;
const PALA=['#e0533d','#e8a33d','#8b5cf6','#ef4444','#3b82f6','#22c55e','#14b8a6'];
const CATTH={};M.groups.forEach((g,gi)=>g[1].forEach(i=>CATTH[i]=gi));
const R=__RISKS__, POP=__POP__, F=__FACTS__;
const map=L.map('map',{preferCanvas:true}).setView(M.center||[50.45,30.52],M.only?13:11);
map.createPane('popPane'); map.getPane('popPane').style.zIndex=350;
map.createPane('maskPane'); map.getPane('maskPane').style.zIndex=345;
if(M.bounds){
 const b=L.latLngBounds(M.bounds);
 map.fitBounds(b,{padding:[24,24]});
 // за межі району не випускаємо: запас ~10% від розміру району
 const dy=(M.bounds[1][0]-M.bounds[0][0])*0.10, dx=(M.bounds[1][1]-M.bounds[0][1])*0.10;
 const lim=L.latLngBounds([M.bounds[0][0]-dy,M.bounds[0][1]-dx],
                          [M.bounds[1][0]+dy,M.bounds[1][1]+dx]);
 map.setMaxBounds(lim);
 map.setMinZoom(map.getBoundsZoom(lim));
}
if(M.border){
 // затемнення всього поза межами району: великий прямокутник з "дірою" по контуру
 const W=[[-85,-360],[-85,360],[85,360],[85,-360]];
 L.polygon([W,M.border],{pane:'maskPane',color:'#0f1117',weight:0,
   fillColor:'#0f1117',fillOpacity:.82,interactive:false}).addTo(map);
 L.polygon(M.border,{color:'#6b7890',weight:1.8,opacity:.9,
   fill:false,dashArray:'6,5',interactive:false}).addTo(map);
}
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
{attribution:'&copy; OpenStreetMap, CARTO',maxZoom:19}).addTo(map);
let layer=L.layerGroup().addTo(map),heat=null,heatOn=false;
const rlayer=L.layerGroup().addTo(map);
const poplayer=L.layerGroup();          // фон під усім іншим
const flayer=L.layerGroup().addTo(map); // чинники середовища за чекбоксами
const hlayer=L.layerGroup().addTo(map); // підсвітка «чинники поруч» для конкретного місця
const FCOL=['#f59e0b','#38bdf8','#a3a3a3'];   // притягують / збирають людей / стан
const FZOOM=14;                               // ближче за цей масштаб — показуємо позначки
const RCOL={metro:'#38bdf8',busstop:'#7dd3fc',
 flow_school:'#fbbf24',flow_transit:'#38bdf8',flow_shop:'#f472b6'};
// ризик успадковує колір своєї теми — той самий, що в подіях
Object.keys(R.lines||{}).forEach(k=>{if(k.startsWith('risk_'))RCOL[k]=PALA[(R.lines[k].theme||0)%7]});;
if(M.skew) $ify('#skew', `<div class="skew">${M.skew}</div>`);
function $ify(sel,html){const el=document.querySelector(sel);if(el)el.innerHTML=html}
{
 // --- прогноз ризику ---
 let rh='';
 const rkeys=Object.keys(R.lines||{}).filter(k=>k.startsWith('risk_'))
   .sort((a,b)=>R.lines[b].hit-R.lines[a].hit);
 rkeys.forEach(k=>{const v=R.lines[k],c=RCOL[k];
  if(v.nodata){
   // тема є в списку правопорушень, але подій замало на навчання моделі
   rh+=`<div class="rw nod" style="border-left-color:#3a4256">
    <label class="rl"><input type="checkbox" disabled>
     <span class="sw" style="background:#3a4256"></span>
     <span class="nm">${v.title}</span>
     <span class="acc">—</span></label>
    <div class="why">замало подій для навчання моделі</div></div>`;
   return}
  rh+=`<div class="rw" style="border-left-color:${c}">
   <label class="rl"><input type="checkbox" data-r="${k}">
    <span class="sw" style="background:${c}"></span>
    <span class="nm">${v.title}</span>
    <span class="acc">${v.hit}%</span></label>
   ${v.why?`<div class="why">${v.why}</div>`:''}</div>`});
 if(rkeys.length) rh+=`<div class="lgd" style="color:${RCOL[rkeys[0]]}"><span>менший</span><i></i><span>більший</span></div>`;
 $ify('#frisk',rh);

 // --- контекст ---
 let ch='';
 if(POP.length) ch+=`<label><input type="checkbox" data-r="pop">
   <span class="sw" style="background:#3b4a63"></span><span>Щільність населення</span>
   <span class="n">${POP.length.toLocaleString('uk')}</span></label>`;
 ['flow_school','flow_transit','flow_shop'].forEach(k=>{const v=R.lines&&R.lines[k];if(!v)return;
  ch+=`<label><input type="checkbox" data-r="${k}">
   <span class="sw" style="background:${RCOL[k]}"></span><span>${v.title}</span>
   <span class="n">${v.items.length.toLocaleString('uk')}</span></label>`});
 $ify('#fctx',ch);

 // --- середовище: чинники, згруповані за роллю ---
 let ff='';
 (F.cats||[]).forEach((c,ci)=>c._i=ci);
 (F.groups||[]).forEach((gn,gi)=>{
  const inG=(F.cats||[]).filter(c=>c.g===gi&&c.pts.length);
  if(!inG.length) return;
  ff+=`<div class="fgh">${gn}</div>`;
  inG.forEach(c=>{ff+=`<label><input type="checkbox" data-f="${c._i}">
    <span class="sw" style="background:${FCOL[gi]}"></span><span>${c.n}</span>
    <span class="n">${c.pts.length.toLocaleString('uk')}</span></label>`});
 });
 $ify('#ffact',ff||'<div class="sub">шар чинників недоступний</div>');
 $ify('#fhint','Об’єкти, які модель рахує як чинники ризику. З’являються від масштабу '+
   FZOOM+' — інакше карта нечитабельна.'+
   (M.mode==='student'
     ? ' У вікні будь-якої адреси та ризикованої вулиці є кнопка «Що поруч» — '+
       'вона підсвічує все, що є в радіусі 250 м, із відстанню до кожного об’єкта. '+
       'Які з них справді пояснюють скупчення — визначаєте ви.'
     : ' У картці проблеми та у вікні ризикованої вулиці є кнопка '+
       '«Показати чинники поруч» — вона підсвічує саме ті об’єкти, що дали цьому місцю ризик.'));
}
// підсвічує об'єкти, які модель порахувала для конкретної точки, з колами радіусів
function showNear(la,lo,factors){
 hlayer.clearLayers();
 if(!(F.cats||[]).length||!factors||!factors.length) return 0;
 const need={};
 factors.forEach(f=>String(f[0]).split(' × ').forEach(part=>{
  const m=part.match(/^(.+)_(\d+)м$/);
  if(m) need[m[1]]=Math.max(need[m[1]]||0,+m[2]);
 }));
 const my=111320, mx=111320*Math.cos(la*Math.PI/180);
 const rads=new Set(); let shown=0;
 Object.keys(need).forEach(base=>{
  const c=F.cats.find(x=>x.b===base); if(!c) return;
  const rad=need[base]; rads.add(rad);
  c.pts.forEach(p=>{
   const d=Math.hypot((p[0]-la)*my,(p[1]-lo)*mx);
   if(d>rad) return;
   shown++;
   L.circleMarker(p,{radius:6,weight:2,color:'#fbbf24',
     fillColor:FCOL[c.g],fillOpacity:.95})
    .bindTooltip(`${c.n} — ${Math.round(d)} м`,{className:'rt'}).addTo(hlayer)});
 });
 rads.forEach(r=>L.circle([la,lo],{radius:r,color:'#fbbf24',weight:1,opacity:.45,
   fill:false,dashArray:'4,4',interactive:false}).addTo(hlayer));
 L.circleMarker([la,lo],{radius:5,weight:2,color:'#fbbf24',
   fillColor:'#fbbf24',fillOpacity:1,interactive:false}).addTo(hlayer);
 return shown;
}
// те саме, але БЕЗ підказки моделі: просто все, що є довкола в заданому радіусі.
// Для слухачів — це спостереження, а не готова відповідь: які саме з цих об'єктів
// пояснюють скупчення, вони мають визначити самі.
function showAllNear(la,lo,rad){
 hlayer.clearLayers();
 if(!(F.cats||[]).length) return 0;
 const my=111320, mx=111320*Math.cos(la*Math.PI/180);
 let shown=0;
 F.cats.forEach(c=>c.pts.forEach(p=>{
  const d=Math.hypot((p[0]-la)*my,(p[1]-lo)*mx);
  if(d>rad) return;
  shown++;
  L.circleMarker(p,{radius:6,weight:2,color:'#fbbf24',
    fillColor:FCOL[c.g],fillOpacity:.95})
   .bindTooltip(`${c.n} — ${Math.round(d)} м`,{className:'rt'}).addTo(hlayer)}));
 L.circle([la,lo],{radius:rad,color:'#fbbf24',weight:1,opacity:.45,
   fill:false,dashArray:'4,4',interactive:false}).addTo(hlayer);
 L.circleMarker([la,lo],{radius:5,weight:2,color:'#fbbf24',
   fillColor:'#fbbf24',fillOpacity:1,interactive:false}).addTo(hlayer);
 return shown;
}
function drawFacts(){
 flayer.clearLayers();
 const zo=map.getZoom()<FZOOM;
 const el=document.querySelector('#fzoom');
 const on=[...document.querySelectorAll('[data-f]')].some(x=>x.checked);
 if(el) el.textContent = (zo&&on) ? 'Наблизьте карту, щоб побачити позначки' : '';
 if(zo) return;
 const b=map.getBounds();
 document.querySelectorAll('[data-f]').forEach(cb=>{
  if(!cb.checked) return;
  const c=F.cats[+cb.dataset.f]; if(!c) return;
  const col=FCOL[c.g];
  c.pts.forEach(p=>{
   if(!b.contains(p)) return;
   L.circleMarker(p,{radius:4,weight:1,color:'#0f1117',fillColor:col,fillOpacity:.9})
    .bindTooltip(c.n,{className:'rt'}).addTo(flayer)});
 });
}
function riskPopup(k,it){
 const v=R.lines[k];
 let h=`<div class="rpop"><b>${it[1]}</b><span class="sub">${v.title} — верхні ${101-it[2]}% за ризиком</span>`;
 if(v.method) h+=`<div class="rmeth">${v.method}</div>`;
 if(v.factors&&v.factors.length){
  h+='<table>'+v.factors.map(f=>`<tr><td>${f[0]}</td><td>+${f[1]}</td></tr>`).join('')+'</table>';
 }
 // відсилка на документ дослідження. Викладачеві — одразу на рядок цієї вулиці
 // (?st= підсвічує його й прокручує туди), слухачеві — на методику теми:
 // поіменного переліку в його версії документа немає.
 const an=v.slug?('#t-'+v.slug):'';
 h+=STUDENT
   ? `<a class="rdoc" href="doslidzhennya.html${an}" target="_blank" rel="noopener">Як рахується цей ризик ↗</a>`
   : `<a class="rdoc" href="doslidzhennya.html${(it[1]&&it[1]!=='без назви')?('?st='+encodeURIComponent(it[1])):''}${an}" target="_blank" rel="noopener">Розбір цієї вулиці в дослідженні ↗</a>`;
 h+='</div>';
 return h;
}
function drawRisks(){
 rlayer.clearLayers();
 const pc=document.querySelector('[data-r="pop"]');
 if(pc&&pc.checked){
  if(!map.hasLayer(poplayer)){
   if(!poplayer.getLayers().length){
    const mx=Math.max(...POP.map(p=>p[2]));
    POP.forEach(p=>L.circleMarker([p[0],p[1]],{pane:'popPane',
      radius:5+16*Math.sqrt(p[2]/mx),weight:0,fillColor:'#4b6fa8',
      fillOpacity:.10+.28*Math.sqrt(p[2]/mx)})
      .bindTooltip(`${p[2].toLocaleString('uk')} осіб`,{className:'rt',sticky:true})
      .addTo(poplayer));
   }
   poplayer.addTo(map); poplayer.bringToBack();
  }
 } else map.removeLayer(poplayer);

 document.querySelectorAll('[data-r]').forEach(cb=>{
  if(!cb.checked||cb.dataset.r==='pop') return;
  const k=cb.dataset.r, col=RCOL[k];
  if(!(R.lines&&R.lines[k])) return;
  const isRisk=k.startsWith('risk_'), v=R.lines[k];
  if(isRisk){
   // п.7.5: без теплового світіння (блокувало кліки) — самі лінії, товщі й клікабельні
   v.items.forEach(it=>
     L.polyline(it[0],{color:col,weight:Math.max(2,1.5+it[2]/16),
       opacity:Math.max(.35,.85*it[2]/100)})
      .bindTooltip(`<b>${it[1]}</b><span>${v.title} — верхні ${101-it[2]}% за ризиком, клікніть для деталей</span>`,
        {className:'rt',sticky:true})
      .on('click',ev=>{
        const w=document.createElement('div'); w.innerHTML=riskPopup(k,it);
        if(v.factors&&v.factors.length&&(F.cats||[]).length){
         const bt=document.createElement('button'); bt.className='pbtn2';
         bt.textContent='Показати чинники поруч';
         bt.onclick=()=>{const q=showNear(ev.latlng.lat,ev.latlng.lng,v.factors);
           bt.textContent=q?`Підсвічено об’єктів: ${q}`:'Поруч нічого з чинників немає'};
         w.appendChild(bt);
        } else if(STUDENT&&(F.cats||[]).length){
         // слухачам — те саме вікно, але без підказки моделі: просто околиці
         const bt=document.createElement('button'); bt.className='pbtn2';
         bt.textContent='Що поруч (250 м)';
         bt.onclick=()=>{const q=showAllNear(ev.latlng.lat,ev.latlng.lng,250);
           bt.textContent=q?`Показано об’єктів: ${q}`:'Поруч нічого не знайдено'};
         w.appendChild(bt);
        }
        L.popup({maxWidth:320}).setLatLng(ev.latlng).setContent(w).openOn(map)})
      .addTo(rlayer));
  } else {
   const mxf=Math.max(...v.items.map(x=>x[2]))||1;
   v.items.forEach(it=>
    L.polyline(it[0],{color:col,weight:Math.max(1.5,1+5*Math.sqrt(it[2]/mxf)),
      opacity:Math.max(.25,.75*Math.sqrt(it[2]/mxf))})
     .bindTooltip(`<b>${it[1]||'без назви'}</b><span>${v.title} — ~${it[2].toLocaleString('uk')} осіб</span>`+
       (v.when?`<span>${v.when}</span>`:''),{className:'rt',sticky:true}).addTo(rlayer));
  }
 });
}
const $=s=>document.querySelector(s);
if(M.only){$('#subt').textContent=M.only+' район · за даними ЄДРСР';
 $('#backl').innerHTML='<a href="index.html" style="color:#e0533d;font-size:12px;text-decoration:none">← всі райони</a>';}
$('#fc').innerHTML=M.courts.map((n,i)=>`<label><input type="checkbox" data-c="${i}" checked>${n}</label>`).join('');
$('#fy').innerHTML=M.years.map((n,i)=>`<label><input type="checkbox" data-y="${i}" checked>${n}</label>`).join('');
const fmt=n=>n.toLocaleString('uk');
$('#fa').innerHTML=M.groups.map((g,gi)=>`<div class="gr" data-g="${gi}">
<div class="gh"><span class="ar">&#9656;</span><input type="checkbox" class="gt" data-gt="${gi}" checked>
<span class="nm">${g[0]}</span><span class="n">${fmt(g[2])}</span></div>
<div class="gb">`+g[1].map(i=>`<label><input type="checkbox" data-a="${i}" checked>
<span>${M.cats[i]}</span><span class="n">${fmt(M.counts[i])}</span></label>`).join('')+
`</div></div>`).join('');
document.querySelectorAll('.gh').forEach(el=>el.onclick=e=>{
 if(e.target.tagName==='INPUT')return; el.parentElement.classList.toggle('open')});
document.querySelectorAll('.gt').forEach(el=>el.onchange=()=>{
 M.groups[+el.dataset.gt][1].forEach(i=>{const b=document.querySelector(`[data-a="${i}"]`);if(b)b.checked=el.checked});
 draw()});
function syncThemes(){document.querySelectorAll('.gt').forEach(el=>{
 const ids=M.groups[+el.dataset.gt][1], on=ids.filter(i=>document.querySelector(`[data-a="${i}"]`).checked).length;
 el.checked=on>0; el.indeterminate=on>0&&on<ids.length})}
const PERIODS=[['Ранок','6–11',[6,7,8,9,10,11]],['День','12–17',[12,13,14,15,16,17]],
 ['Вечір','18–23',[18,19,20,21,22,23]],['Ніч','0–5',[0,1,2,3,4,5]]];
const STUDENT = M.mode==='student';
// Документи кроку 6. «Аналіз поточного стану» будується лише для викладацької
// версії, тож слухачам на нього не посилаємося — інакше буде мертве посилання.
$ify('#docs',
 '<a href="doslidzhennya.html" target="_blank" rel="noopener">Дослідження ризиків ↗</a>'+
 '<a href="rezyume.html" target="_blank" rel="noopener">Резюме на одну сторінку ↗</a>'+
 (STUDENT?'':'<a href="analiz.html" target="_blank" rel="noopener">Аналіз поточного стану ↗</a>'));
// п.7.7: замість чотирьох кнопок категорій — лише "Усі" й "Тільки проблеми"
const CATS=STUDENT?[['Усі','подій ≥1','cA',-1]]
 :[['Усі','подій ≥1','cA',-1],['Тільки проблеми','з відібраних 50','c2',2]];
const cb_=$('#fcat');
CATS.forEach((c,i)=>{const sp=document.createElement('span');
 sp.className=c[2]+(i===0?' on':'');sp.innerHTML=`${c[0]}<i>${c[1]}</i>`;sp.dataset.c=c[3];cb_.appendChild(sp)});
cb_.onclick=e=>{const t=e.target.closest('[data-c]');if(!t)return;
 [...cb_.children].forEach(x=>x.classList.remove('on'));t.classList.add('on');draw()};
const CATNAME={2:['Проблема','#f87171','у кураторському списку'],0:null};
const hb=$('#hr');
PERIODS.forEach((p,i)=>{const s=document.createElement('span');
 s.innerHTML=`${p[0]}<i>${p[1]}</i>`;s.dataset.p=i;hb.appendChild(s)});
hb.onclick=e=>{const t=e.target.closest('[data-p]');if(t){t.classList.toggle('on');draw()}};
const sel=a=>new Set([...document.querySelectorAll(`[data-${a}]`)].filter(x=>x.checked).map(x=>+x.dataset[a]));
function buildPassport(p,pr){
 const today=new Date().toISOString().slice(0,10);
 let t=`# Паспорт проблеми (SARA)\n\n`;
 t+=`**Адреса:** ${p[2]||'не визначена'}\n`;
 t+=`**Механізм:** ${pr.mech}\n**Дата формування:** ${today}\n\n`;
 t+=`## Scanning\n\n`;
 t+=`- Подій за напрямком: **${pr.n}** (усього на адресі — ${pr.core_n})\n`;
 t+=`- Роки повторення: ${pr.years.join(', ')}\n`;
 t+=`- Склад: `+pr.arts.map(a=>`${a[0]} — ${a[1]}`).join('; ')+`\n\n`;
 t+=`## Analysis\n\n`;
 if(pr.analysis){
  t+=`Адреса потрапляє у верхні ${100-pr.analysis.pc}% вулиць за прогнозом моделі для цієї теми `+
     `(влучність моделі ${pr.analysis.hit}%, навчання на ${pr.analysis.train}, перевірка на ${pr.analysis.test} подіях).\n\n`;
  t+=`Чинники середовища:\n`+pr.analysis.factors.map(f=>`- ${f[0]} (вага ${f[1]})`).join('\n')+`\n\n`;
 } else {
  t+=`Модель не пояснює це скупчення умовами середовища — причину треба встановити на місці `+
     `(польовий підрахунок, опитування, огляд).\n\n`;
 }
 t+=`**Гіпотеза причини (заповнити на місці):**\n\n_____\n\n`;
 t+=`## Response\n\n**Тип втручання:** _____\n**Адресат:** _____\n**Горизонт:** _____\n\n`;
 t+=`## Assessment\n\n**Критерій спростування (як дізнатись, що не спрацювало):** _____\n\n`;
 t+=`**Дата повторної перевірки:** _____\n`;
 return t;
}
function downloadPassport(p,pr){
 const txt=buildPassport(p,pr);
 const blob=new Blob([txt],{type:'text/markdown;charset=utf-8'});
 const a=document.createElement('a');
 a.href=URL.createObjectURL(blob);
 a.download='pasport_'+(p[2]||'problema').replace(/[^a-zA-Zа-яА-ЯіїєІЇЄ0-9]+/g,'_').slice(0,60)+'.md';
 document.body.appendChild(a);a.click();document.body.removeChild(a);
}
window.__downloadPassport=downloadPassport;
function draw(){
 syncThemes();
 const C=sel('c'),A=sel('a'),Y=sel('y');
 // які теми зараз видимі за фільтром статей — картки проблем ховаються разом з ними,
 // інакше при фільтрі «Насильство» знизу висіла картка про ДТП
 const GVIS=new Set();M.groups.forEach((g,gi)=>{if(g[1].some(i=>A.has(i)))GVIS.add(gi)});
 const CF=+(cb_.querySelector('.on')||{dataset:{c:-1}}).dataset.c;
 const H=new Set();
 hb.querySelectorAll('.on').forEach(x=>PERIODS[+x.dataset.p][2].forEach(h=>H.add(h)));
 let tot=0;const vis=[];
 for(const p of P){
  if(CF>=0&&p[6]!==CF) continue;
  let n=0,th=null;
  for(const e of p[4]) if(C.has(e[0])&&A.has(e[1])&&Y.has(e[2])&&(!H.size||H.has(e[3]))){n++;if(th===null)th=CATTH[e[1]]}
  if(n){tot+=n;vis.push([p,n,th])}}
 vis.sort((a,b)=>b[1]-a[1]);
 // у версії для слухачів категорія прихована (p[6]=-1), тому фільтр по ===2 давав
 // порожній список і «Топ адрес» завжди показував «нема даних». Слухачам перелік
 // найгарячіших адрес потрібен саме для самостійного пошуку скупчень.
 const rank=vis.filter(v=>v[0][3]&&(STUDENT||v[0][6]===2));
 $('#cnt').textContent=tot.toLocaleString('uk');
 $('#cntl').textContent=`подій на ${vis.length.toLocaleString('uk')} адресах`;
 {let q=0;P.forEach(p=>{if(p[6]===2)q++});
  $('#cathint').innerHTML=q?`У поточних межах: <b style="color:#f87171">${q.toLocaleString('uk')}</b> проблем.`:'';}
 $('#top').innerHTML=rank.slice(0,15).map((v,i)=>
  `<div data-i="${i}"><span>${v[0][2]}</span><b>${v[1]}</b></div>`).join('')||'<div class="sub">нема даних</div>';
 [...$('#top').children].forEach((el,i)=>el.onclick=()=>{const v=rank[i];map.setView([v[0][0],v[0][1]],17);
  setTimeout(()=>{let best=null,bd=1e9;layer.eachLayer(l=>{const ll=l.getLatLng();
   const d=Math.abs(ll.lat-v[0][0])+Math.abs(ll.lng-v[0][1]);if(d<bd){bd=d;best=l}});
   if(best&&bd<1e-4)best.openPopup()},350)});
 layer.clearLayers();if(heat){map.removeLayer(heat);heat=null}
 if(heatOn){heat=L.heatLayer(vis.flatMap(v=>Array(Math.min(v[1],20)).fill([v[0][0],v[0][1],1])),
  {radius:18,blur:24,maxZoom:16}).addTo(map);return}
 const mx=vis.length?vis[0][1]:1;
 for(const [p,n,th] of vis){
  const r=Math.max(3.2,Math.min(19,3.2+8.5*Math.sqrt(n/Math.max(mx,1))*2));
  L.circleMarker([p[0],p[1]],{radius:r,weight:p[3]?.8:0,color:'#0f1117',
   fillColor:p[3]?(PALA[th%7]):'#5f6878',fillOpacity:p[3]?.72:.35})
  .bindPopup(()=>{
   const ev=p[4].filter(e=>C.has(e[0])&&A.has(e[1])&&Y.has(e[2])&&(!H.size||H.has(e[3])));
   const bc={},hh=new Array(24).fill(0);let nk=0;
   ev.forEach(e=>{bc[e[1]]=(bc[e[1]]||0)+1;if(e[3]>=0){hh[e[3]]++;nk++}});
   const rows=Object.entries(bc).sort((a,b)=>b[1]-a[1]);
   const mxh=Math.max(...hh,1);
   let bars='';
   if(nk>=8){bars='<div class="hg">'+hh.map((v,i)=>
     `<i style="height:${Math.max(2,Math.round(22*v/mxh))}px" title="${i}:00 — ${v}"></i>`).join('')+
     '</div><div class="hx"><span>0</span><span>6</span><span>12</span><span>18</span><span>23</span></div>';}
   const night=hh.slice(20).concat(hh.slice(0,4)).reduce((a,b)=>a+b,0);
   const hint = nk>=8 ? `<div class="hn">${Math.round(100*night/nk)}% подій припадає на 20:00–04:00</div>` : '';
   // ---- КАРТКИ ПРОБЛЕМ (п.7.4): по одній на кожен відібраний напрямок адреси ----
   let pblock='';
   const allp=p[7]||[];
   const probs=allp.filter(pr=>pr.thi===undefined||pr.thi<0||GVIS.has(pr.thi));
   const hidden=allp.length-probs.length;
   if(!STUDENT&&!probs.length&&hidden)
    pblock=`<div class="hn">Ця адреса — у списку проблем, але за іншим напрямком `+
     `(${allp.map(x=>x.theme).join(', ')}). Увімкніть відповідні правопорушення, щоб побачити картку.</div>`;
   if(!STUDENT&&probs.length){
    pblock=probs.map((pr,pi)=>{
     let h=`<div class="pcard"><div class="ph">Проблема · ${pr.theme}</div>`;
     h+=`<div class="pt">${pr.mech}</div>`;
     h+=`<div class="pm"><b>Правопорушення:</b> `+pr.arts.map(a=>`${a[0]} — ${a[1]}`).join('; ')+`</div>`;
     h+=`<div class="pm"><b>Чому проблема:</b> ${pr.n} однорідних подій за ${pr.years.length} `+
        `${pr.years.length===1?'рік':'роки'} (${pr.years.join(', ')}), `+
        `${Math.round(100*pr.n/Math.max(pr.core_n,1))}% усіх подій адреси цього роду.</div>`;
     if(pr.analysis){
      h+=`<div class="why"><b>Аналіз:</b> адреса — у верхніх ${100-pr.analysis.pc}% вулиць за `+
         `прогнозом моделі (${pr.theme.toLowerCase()}), влучність ${pr.analysis.hit}%. `+
         `Чинники: `+pr.analysis.factors.slice(0,5).map(f=>f[0]).join(', ')+`.</div>`;
     } else {
      h+=`<div class="why"><b>Аналіз:</b> модель не пояснює — причина встановлюється на місці.</div>`;
     }
     if(pr.analysis&&pr.analysis.factors&&pr.analysis.factors.length&&(F.cats||[]).length)
      h+=`<button class="pbtn2" data-nf="${pi}">Показати чинники поруч</button>`;
     h+=`<button class="pbtn" data-pp="${pi}">Взяти в роботу — паспорт SARA</button></div>`;
     return h;
    }).join('');
    if(probs.length>1) pblock+='<div class="hn" style="margin-top:4px">Кілька напрямків на адресі — кілька окремих проблем із різними причинами.</div>';
   }
   // слухачам кнопка потрібна в КОЖНІЙ адресі — це їхній основний хід:
   // побачив скупчення -> подивився, що довкола -> висунув гіпотезу
   if(STUDENT&&(F.cats||[]).length)
    pblock+='<button class="pbtn2" data-na="1">Що поруч (250 м)</button>';
   const ex=p[5].filter(e=>A.has(e[0])).slice(0,4);
   const cinf=(p[6]===2&&probs.length)?CATNAME[2]:null;
   const html=`<div class="lp">
   ${cinf?`<span class="cbadge" style="background:${cinf[1]}22;color:${cinf[1]}">${cinf[0]}</span>`:''}
   <b>${p[2]||'адреса не визначена'}</b>
   <div class="tt">${n} ${n%10===1&&n%100!==11?'подія':'подій'} за поточним фільтром</div>
   <table class="bd">`+rows.map(([i,c])=>
     `<tr><td>${M.cats[i]}</td><td><b>${c}</b></td></tr>`).join('')+`</table>
   ${bars}${hint}${pblock}
   <div class="ex">Приклади рішень:</div><ul>`+
   ex.map(e=>`<li><span style="color:#79839a">${e[1]}${e[2]>=0?', '+String(e[2]).padStart(2,'0')+':00':''} · ${e[3]}</span> <a href="${e[4]}" target="_blank">відкрити</a></li>`).join('')+
   '</ul></div>';
   const wrap=document.createElement('div');wrap.innerHTML=html;
   wrap.querySelectorAll('[data-pp]').forEach(b=>b.onclick=()=>downloadPassport(p,probs[+b.dataset.pp]));
   wrap.querySelectorAll('[data-nf]').forEach(b=>b.onclick=()=>{
    const q=showNear(p[0],p[1],probs[+b.dataset.nf].analysis.factors);
    b.textContent=q?`Підсвічено об’єктів: ${q}`:'Поруч нічого з чинників немає'});
   wrap.querySelectorAll('[data-na]').forEach(b=>b.onclick=()=>{
    const q=showAllNear(p[0],p[1],250);
    b.textContent=q?`Показано об’єктів: ${q}`:'Поруч нічого не знайдено'});
   return wrap},{maxWidth:360,autoPanPaddingTopLeft:[14,14],autoPanPaddingBottomRight:[14,14]}).addTo(layer)}
}
$('#heat').onclick=e=>{heatOn=!heatOn;e.target.classList.toggle('act');e.target.textContent=heatOn?'Показати точки':'Теплова карта';draw()};
$('#reset').onclick=()=>{document.querySelectorAll('#side input:not([data-r]):not([data-f])').forEach(x=>x.checked=true);
 hb.querySelectorAll('.on').forEach(x=>x.classList.remove('on'));draw()};
$('#none').onclick=()=>{document.querySelectorAll('[data-a]').forEach(x=>x.checked=false);draw()};
$('#all').onclick=()=>{document.querySelectorAll('[data-a]').forEach(x=>x.checked=true);draw()};
document.querySelectorAll('#side input:not([data-r]):not([data-f])').forEach(x=>x.addEventListener('change',draw));
document.querySelectorAll('[data-r]').forEach(x=>x.addEventListener('change',drawRisks));
document.querySelectorAll('[data-f]').forEach(x=>x.addEventListener('change',drawFacts));
map.on('zoomend moveend',drawFacts);
{const fc=$('#fclear'); if(fc) fc.onclick=()=>hlayer.clearLayers();}
draw();drawRisks();drawFacts();
</script></body></html>"""
