# -*- coding: utf-8 -*-
"""Карта й шари: перша половина клієнтського JavaScript.

Тут: підстановка даних (__META__, __PTS__, __RISKS__, __POP__, __FACTS__),
створення карти Leaflet, підкладка й шари — населення, потоки, ризики,
чинники середовища, теплова карта — і підсвітка «що поруч».

Функції: $ify, showNear, showAllNear, drawFacts, riskPopup, drawRisks.
Друга половина (бічна панель, спливні вікна, картка проблеми) — у tpl_popup.
"""
JS_MAP = r"""const M=__META__, P=__PTS__;
// ---- ТЕМИ Й ПАЛІТРА ----
// Порядок кольорів — як у M.groups (ГП, АЛК, НАР, НАС, МАЙ, ДОР, СЕР).
// Стару палітру прибрано: у ній громадський порядок і насильство були майже
// однаковим червоним. Ці два набори перевірено на розрізнення при
// дальтонізмі — світліший лягає на світлу підкладку, темніший на решту.
// Восьмий колір у кінці — запас для домашнього насильства: у M.groups воно не
// входить, але без запасу %8 віддавало б йому колір громадського порядку.
const PAL={
 svitla:['#eb6834','#1baf7a','#4a3aa7','#e34948','#2a78d6','#008300','#e87ba4','#7a6f63'],
 temna: ['#d95926','#199e70','#9085e9','#e66767','#3987e5','#008300','#d55181','#8d94a2'],
 kolir: ['#d95926','#199e70','#9085e9','#e66767','#3987e5','#008300','#d55181','#8d94a2']};
// Ключ CARTO. Безкоштовний, без картки, до 5 млн тайлів на місяць — для
// Академії це нескінченність. Він клієнтський і однаково лежить у коді
// сторінки, тому ховати його немає від кого. Параметр називається саме
// key=, не api_key=: з неправильною назвою ключ мовчки не діє, і виглядає
// це як зіпсований ключ. Атрибуція CARTO і OpenStreetMap обов'язкова
// завжди — це умова безкоштовного користування.
const CARTO_KEY='cb1_3n60_1_74a848e36e851efba49b510b';
const ck_=CARTO_KEY?('?key='+CARTO_KEY):'';
// {r} дає @2x на екранах з подвоєною щільністю — саме через нього підкладка
// виглядає різкою. Esri прибрано: у Києві його растрові тайли обриваються на
// зумі 16 («Map data not yet available»), а карта про номер будинку ходить
// до 19. Звичайний OSM лишається запасним: якщо ключ колись відвалиться,
// карта втратить вигляд, але лишиться робочою.
const TILES={
 svitla:{u:'https://basemaps.cartocdn.com/rastertiles/light_all/{z}/{x}/{y}{r}.png'+ck_,
         a:'&copy; CARTO, &copy; OpenStreetMap'},
 temna:{u:'https://basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}{r}.png'+ck_,
         a:'&copy; CARTO, &copy; OpenStreetMap'},
 kolir:{u:'https://basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png'+ck_,
         a:'&copy; CARTO, &copy; OpenStreetMap'},
 osm:{u:'https://tile.openstreetmap.org/{z}/{x}/{y}.png', a:'&copy; OpenStreetMap'}};
const THNAMES=[['svitla','Світла'],['temna','Темна'],['kolir','Кольорова']];
let THEME=localStorage.getItem('karta-tema');
if(!PAL[THEME]) THEME='svitla';
document.body.dataset.t=THEME;
let PALA=PAL[THEME];
// Маски, межі й гало малює JS, а кольори теми живуть у CSS. Щоб вони не
// розходилися, JS бере їх звідти ж: інакше на світлій темі затемнення поза
// районом лишилося б чорною плямою.
const cssv=v=>getComputedStyle(document.body).getPropertyValue(v).trim();
const CATTH={};M.groups.forEach((g,gi)=>g[1].forEach(i=>CATTH[i]=gi));
// Повна назва статті з кодексу за коротким підписом (src/pravo.py).
// Порожньо, якщо назви немає: приблизна назва в листі гірша за її відсутність.
const LAW=s=>(M.law&&M.law[s])||'';
const R=__RISKS__, POP=__POP__, F=__FACTS__;
// Справи адрес для правої панелі лежать у файлах spravy/<район>.json поруч
// зі сторінкою. Панель тягне свій файл тоді, коли її відкривають уперше.
const DOCCACHE={};
// Потоки приїжджають стисло: геометрія кожного відрізка лежить один раз у
// R.geo, а шари несуть тільки номер відрізка й число. Розгортаємо тут-таки,
// щоб решта коду працювала як раніше.
if(R.geo) Object.values(R.lines||{}).forEach(v=>{
 if(v.g) v.items=v.items.map(x=>[R.geo[x[0]][0], R.geo[x[0]][1], x[1]]);
});
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
// Зовнішня рамка затемнення. Раніше тут стояв нерухомий прямокутник на весь
// світ (довготи -360..360). Полотно Leaflet обрізає такий багатокутник, і на
// широкому екрані ліворуч та вгорі лишалася незатемнена смуга — видно на
// живому сайті. Тепер рамка будується від поточного вигляду з добрим запасом
// і перебудовується під час руху карти.
function maskRing(){
 const b=map.getBounds().pad(2.5);
 return [[b.getSouth(),b.getWest()],[b.getSouth(),b.getEast()],
         [b.getNorth(),b.getEast()],[b.getNorth(),b.getWest()]];
}
let cityMask=null, cityLine=null;
if(M.border){
 cityMask=L.polygon([maskRing(),M.border],{pane:'maskPane',color:cssv('--ground'),weight:0,
   fillColor:cssv('--ground'),fillOpacity:.82,interactive:false}).addTo(map);
 map.on('moveend zoomend',()=>cityMask.setLatLngs([maskRing(),M.border]));
 cityLine=L.polygon(M.border,{color:cssv('--dim'),weight:1.8,opacity:.9,
   fill:false,dashArray:'6,5',interactive:false}).addTo(map);
}
// Плитки міняються разом із темою, тож шар тримаємо у змінній і перестворюємо.
let tileL=null;
function tiles(){
 // Порожній ключ означає, що CARTO більше не наш: тоді всі теми падають на
 // звичайний OSM. Вигляд гірший, зате карта лишається робочою.
 const t=CARTO_KEY?TILES[THEME]:TILES.osm;
 if(tileL) map.removeLayer(tileL);
 tileL=L.tileLayer(t.u,{attribution:t.a,maxZoom:19,detectRetina:true}).addTo(map);
 tileL.bringToBack();
}
tiles();
let layer=L.layerGroup().addTo(map),heat=null,heatOn=false;
const rlayer=L.layerGroup().addTo(map);
const poplayer=L.layerGroup();          // фон під усім іншим
const flayer=L.layerGroup().addTo(map); // чинники середовища за чекбоксами
const hlayer=L.layerGroup().addTo(map); // підсвітка «чинники поруч» для конкретного місця
// ---- РАЙОНИ В МЕЖАХ ОДНОГО ФАЙЛУ ----
// Міська карта несе межі всіх десяти районів і їхні власні переліки проблем.
// Клік по району не веде на інший файл: карта під'їжджає, затемнює решту
// міста й перемикає панель. Фільтри при цьому лишаються — раніше вони гинули
// разом із перезавантаженням сторінки.
const DN=M.dnames||[], DBORD=M.borders||[], DSLUG=M.dslug||[];
let CURD=-1;                       // -1 = все місто, інакше індекс району
// Клік по вікні проблеми, коли воно відкрите, мав закривати саме вікно — а
// закривав вікно (стандартна поведінка Leaflet) І одночасно відкривав район,
// бо межі району клікабельні майже по всій площі міста. Перший клік «повз»
// відкрите вікно тепер лише закриває його; район відкриє вже наступний клік.
let popupWasOpen=false;
map.on('preclick',()=>{popupWasOpen=!!map._popup});
let dmask=null;
const dlayer=L.layerGroup().addTo(map);
const dshapes=[];
const CITY={c:M.center||[50.45,30.52], z:11};
const dBounds=i=>L.latLngBounds(DBORD[i]);
if(DN.length&&!M.only) DN.forEach((nm,i)=>{
 const pg=L.polygon(DBORD[i],{color:cssv('--dim'),weight:1.8,opacity:.85,dashArray:'7,5',
   fillColor:cssv('--dim'),fillOpacity:.05});
 const np=(M.dprob||[])[i]||0;
 pg.bindTooltip(`<b>${nm}</b><span>`+(np?`${np} проблем · `:'')+`натисніть, щоб відкрити</span>`,
   {className:'rt',sticky:true});
 pg.on('mouseover',()=>{if(CURD<0)pg.setStyle({fillOpacity:.13,opacity:.9})});
 pg.on('mouseout', ()=>{if(CURD<0)pg.setStyle({fillOpacity:.04,opacity:.45})});
 pg.on('click',    ()=>{if(popupWasOpen){popupWasOpen=false;return}if(CURD<0)enterDistrict(i)});
 pg.addTo(dlayer); dshapes.push(pg);
});
// Межі решти районів у вибраному районі гасимо, а не ховаємо: під затемненням
// вони все одно не читаються, зате перемикання лишається однією дією.
function paintScope(){
 dshapes.forEach((pg,i)=>pg.setStyle(CURD<0
   ? {color:cssv('--dim'),fillColor:cssv('--dim'),opacity:.85,fillOpacity:.05,dashArray:'7,5'}
   : {color:cssv('--dim'),opacity:i===CURD?1:0,fillOpacity:0,dashArray:null}));
 if(dmask){map.removeLayer(dmask);dmask=null}
 if(CURD>=0){
  dmask=L.polygon([maskRing(),DBORD[CURD]],{pane:'maskPane',color:cssv('--ground'),weight:0,
    fillColor:cssv('--ground'),fillOpacity:.78,interactive:false}).addTo(map);
 }
}
// рамка затемнення має встигати за картою, інакше при від'їзді з'являються
// незатемнені краї
map.on('moveend zoomend',()=>{if(dmask)dmask.setLatLngs([maskRing(),DBORD[CURD]])});
function enterDistrict(i,fly){
 if(!(i>=0&&i<DN.length)) return;
 CURD=i; paintScope();
 if(fly===false) map.fitBounds(dBounds(i),{padding:[28,28]});
 else map.flyToBounds(dBounds(i),{padding:[28,28],duration:1.15,easeLinearity:.22});
 if(location.hash.slice(1)!==DSLUG[i]) history.replaceState(null,'','#'+DSLUG[i]);
 onScopeChange();
}
function exitDistrict(){
 CURD=-1; paintScope();
 map.flyTo(CITY.c,CITY.z,{duration:1.0});
 history.replaceState(null,'',location.pathname+location.search);
 onScopeChange();
}
window.addEventListener('hashchange',()=>{
 const i=DSLUG.indexOf(decodeURIComponent(location.hash.slice(1)).toLowerCase());
 if(i>=0){if(i!==CURD)enterDistrict(i)} else if(CURD>=0)exitDistrict();
});
const FCOL=['#f59e0b','#38bdf8','#a3a3a3'];   // притягують / збирають людей / стан
// Кожен вид об'єкта — свій значок, а не однаковий кружечок: магазин, зупинка
// й покинута будівля мають читатися з першого погляду. Колір кола лишається
// за роллю (притягує / збирає людей / стан середовища), значок — за видом.
//
// ОГОЛОШЕННЯ МАЄ СТОЯТИ ТУТ, ДО бічної панелі. 8 вересня сайт зламався саме
// через це: FICON лежав нижче, поруч із drawFacts, а список чинників у панелі
// звертався до нього раніше. Для `const` це не «ще не визначено», а помилка —
// увесь скрипт сторінки падав, і карта не будувалася зовсім. У пісочниці це
// не спливло, бо там factors.json порожній і цикл, що читає FICON, не
// виконувався жодного разу.
const FICON={bar_on:'🍺',bar_off:'🍾',shop24:'🛒',food:'🍽',finance:'💱',
 gambling:'🎰',fuel:'⛽',school:'🎒',univer:'🎓',health:'✚',market:'🏬',
 metro:'Ⓜ',busstop:'🚏',play:'🧸',abandon:'🏚',parking:'🅿',cctv:'📹'};
const FZOOM=14;                               // ближче за цей масштаб — показуємо позначки
const RCOL={metro:'#38bdf8',busstop:'#7dd3fc',
 flow_school:'#fbbf24',flow_transit:'#38bdf8',flow_shop:'#f472b6'};
// ризик успадковує колір своєї теми — той самий, що в подіях
Object.keys(R.lines||{}).forEach(k=>{if(k.startsWith('risk_'))RCOL[k]=PALA[(R.lines[k].theme||0)%PALA.length]});;
function $ify(sel,html){const el=document.querySelector(sel);if(el)el.innerHTML=html}
{
 // --- КОНТЕКСТ: населення, потоки й один вимикач на всю інфраструктуру ---
 // Прогноз ризику звідси пішов у рядки тем (tpl_popup): ті самі сім кольорів
 // жили у двох різних блоках, і панель читалася як два переліки про одне.
 // Поділ об'єктів на «притягують / збирають людей» теж прибрано — слухачеві
 // він нічого не давав, а місця займав більше за самі об'єкти.
 const ctxRow=(k,name,col,n)=>`<div class="row" data-ctx="${k}" data-on="0">
  <span class="sq" style="background:${col}"></span><span class="nm">${name}</span>
  <span class="n">${n.toLocaleString('uk')}</span>
  <span class="ln" style="visibility:hidden"></span><span class="acc"></span></div>`;
 let ch='';
 if(POP.length) ch+=ctxRow('pop','Щільність населення','#4b6fa8',POP.length);
 ['flow_school','flow_transit','flow_shop'].forEach(k=>{const v=R.lines&&R.lines[k];if(!v)return;
  ch+=ctxRow(k,v.title,RCOL[k],v.items.length)});
 const fcnt=(F.cats||[]).reduce((a,c)=>a+c.pts.length,0);
 if(fcnt) ch+=ctxRow('facts','Об’єкти довкола','var(--dim)',fcnt);
 $ify('#fctx',ch);
 // Прапорці окремих видів об'єктів і шарів контексту лишаються схованими:
 // drawFacts() і drawRisks() читають саме їх, а вмикає їх тепер рядок вище.
 (F.cats||[]).forEach((c,ci)=>c._i=ci);
 $ify('#ffact',(F.cats||[]).map(c=>`<input type="checkbox" data-f="${c._i}">`).join('')
   +['pop','flow_school','flow_transit','flow_shop'].map(k=>
     `<input type="checkbox" data-r="${k}">`).join(''));
 $ify('#fgroups',(F.groups||[]).join(' · '));
 {const box=document.querySelector('#fctx');
  if(box) box.onclick=e=>{
   const row=e.target.closest('[data-ctx]'); if(!row) return;
   const k=row.dataset.ctx, on=row.dataset.on!=='0';
   row.dataset.on=on?'0':'1';
   if(k==='facts'){document.querySelectorAll('[data-f]').forEach(x=>x.checked=!on);
     drawFacts(); return}
   const inp=document.querySelector(`[data-r="${k}"]`);
   if(inp){inp.checked=!on; drawRisks()}
  };}
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
const FICO_CACHE={};
function ficon(k,g){
 const key=k+'|'+g;
 if(!FICO_CACHE[key]) FICO_CACHE[key]=L.divIcon({className:'',iconSize:[20,20],
   iconAnchor:[10,10],
   html:`<span class="fic" style="border-color:${FCOL[g]}">${FICON[k]||'•'}</span>`});
 return FICO_CACHE[key];
}
// Скільки значків малюємо за один перемальовок. Понад це — вертаємось до
// простих кружечків: інакше на дрібному масштабі з увімкненими зупинками
// карта підвисає на кілька секунд.
const FMAX=900;
function drawFacts(){
 flayer.clearLayers();
 const zo=map.getZoom()<FZOOM;
 const el=document.querySelector('#fzoom');
 const on=[...document.querySelectorAll('[data-f]')].some(x=>x.checked);
 if(el) el.textContent = (zo&&on) ? 'Наблизьте карту, щоб побачити позначки' : '';
 if(zo) return;
 const b=map.getBounds();
 // спершу рахуємо, скільки об'єктів узагалі потрапляє у вікно
 let want=0;
 document.querySelectorAll('[data-f]').forEach(cb=>{
  if(!cb.checked) return;
  const c=F.cats[+cb.dataset.f]; if(!c) return;
  c.pts.forEach(p=>{if(b.contains(p))want++});
 });
 const plain=want>FMAX, HALO=cssv('--halo');
 document.querySelectorAll('[data-f]').forEach(cb=>{
  if(!cb.checked) return;
  const c=F.cats[+cb.dataset.f]; if(!c) return;
  const col=FCOL[c.g], ic=ficon(c.k,c.g);
  c.pts.forEach(p=>{
   if(!b.contains(p)) return;
   (plain
     ? L.circleMarker(p,{radius:4,weight:1,color:HALO,fillColor:col,fillOpacity:.9})
     : L.marker(p,{icon:ic}))
    .bindTooltip(c.n,{className:'rt'}).addTo(flayer)});
 });
 if(el&&plain) el.textContent='Забагато об’єктів у вікні — показано кружечками; '
   +'наблизьте карту, щоб побачити значки за видом';
}
// Скільки разів — з правильним відмінком. «у 1,8 раза», «у 2 рази», «у 5 разів».
function raz(n){
 const v=Math.round(n*10)/10, t=String(v).replace('.',',');
 if(!Number.isInteger(v)) return t+' раза';
 const a=v%10, b=v%100;
 if(a===1&&b!==11) return t+' раз';
 if(a>=2&&a<=4&&(b<12||b>14)) return t+' рази';
 return t+' разів';
}
const nfmt=n=>(Math.round(n*10)/10).toLocaleString('uk');
// Чинники САМЕ ЦІЄЇ вулиці. Кожен рядок — виміряна річ, яку можна перевірити,
// вийшовши на місце й порахувавши: скільки тут і скільки буває звичайно.
// Слова «причина» тут немає навмисно: модель міряє, що поруч, а не доводить,
// через що саме сталася подія. Причину називає той, хто виїхав.
function factRows(fx){
 if(!fx||!fx.length) return '';
 const rows=fx.map(f=>{
  const [label,val,med,ratio,isCount]=f;
  // «звичайно 0» читається як помилка. Якщо на більшості вулиць таких
  // об'єктів немає взагалі, так і кажемо — це найсильніша частина
  // порівняння, а не найслабша.
  const cmp=(med===null||med===undefined) ? ''
    : (isCount&&!med) ? ' <i>на більшості вулиць — жодного</i>'
    : ` <i>звичайно ${nfmt(med)}</i>`;
  let right=`<b>${nfmt(val)}</b>`+cmp;
  const r=(ratio&&ratio>=1.2)?`<div class="fr">де цього більше — подій у ${raz(ratio)} більше</div>`:'';
  return `<tr><td>${label}${r}</td><td class="fv">${right}</td></tr>`;
 }).join('');
 return `<div class="rwhy">Що виміряно на цьому відрізку</div><table class="fx">${rows}</table>`;
}
function riskPopup(k,it,quiet){
 const v=R.lines[k];
 const hot=(it[3]|0)>0;
 let h=`<div class="rpop"><b>${it[1]}</b><span class="sub">${v.title} — `
  +(quiet
    ? 'подій не зафіксовано, але обстановка така сама, як на ризикованих вулицях'
    : `верхні ${101-it[2]}% за ризиком`
      +(hot?`, подій уже було: ${it[3]}`:', подій ще не було'))+`</span>`;
 // Чинники цієї вулиці — головне у вікні, тому стоять першими, до методики.
 h+=factRows(it[4]);
 if(!(it[4]&&it[4].length))
  h+=`<div class="rwhy">Модель не виділила на цьому відрізку жодної піднятої ознаки — оцінку дала здебільшого історія подій.</div>`;
 if(v.method) h+=`<div class="rmeth">${v.method}</div>`;
 // відсилка на документ дослідження. Викладачеві — одразу на рядок цієї вулиці
 // (?st= підсвічує його й прокручує туди), слухачеві — на методику теми:
 // поіменного переліку в його версії документа немає.
 const an=v.slug?('#t-'+v.slug):'';
 h+=`<a class="rdoc" href="doslidzhennya.html${(it[1]&&it[1]!=='без назви')?('?st='+encodeURIComponent(it[1])):''}${an}" target="_blank" rel="noopener">Розбір вулиці в дослідженні ↗</a>`;
 h+='</div>';
 return h;
}
// Спільне для «гарячих» і «тихих» вулиць: підказка й вікно з розбором.
function bindRisk(pl,k,it,quiet){
 const v=R.lines[k];
 pl.bindTooltip(`<b>${it[1]}</b><span>${v.title} — `
   +(quiet?'подій не зафіксовано, але умови ті самі'
          :`верхні ${101-it[2]}% за ризиком`
            +((it[3]|0)>0?`, подій уже було: ${it[3]}`:', подій ще не було'))
   +`. Клікніть для деталей</span>`,{className:'rt',sticky:true});
 pl.on('click',ev=>{
   const w=document.createElement('div'); w.innerHTML=riskPopup(k,it,quiet);
   if(v.factors&&v.factors.length&&(F.cats||[]).length){
    const bt=document.createElement('button'); bt.className='pbtn2';
    bt.textContent='Показати чинники поруч';
    bt.onclick=()=>{const q=showNear(ev.latlng.lat,ev.latlng.lng,v.factors);
      bt.textContent=q?`Підсвічено об’єктів: ${q}`:'Поруч нічого з чинників немає'};
    w.appendChild(bt);
   } else if((F.cats||[]).length){
    const bt=document.createElement('button'); bt.className='pbtn2';
    bt.textContent='Що поруч (250 м)';
    bt.onclick=()=>{const q=showAllNear(ev.latlng.lat,ev.latlng.lng,250);
      bt.textContent=q?`Показано об’єктів: ${q}`:'Поруч нічого не знайдено'};
    w.appendChild(bt);
   }
   L.popup({maxWidth:320}).setLatLng(ev.latlng).setContent(w).openOn(map)});
 return pl;
}
function drawRisks(){
 rlayer.clearLayers();
 const quietOn=!!(document.querySelector('#fquiet')||{}).checked;
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
   // п.7.5: без теплового світіння (блокувало кліки) — самі лінії, товщі й клікабельні.
   //
   // it[2] — місце вулиці у переліку, у відсотках (100 = найризикованіша).
   // it[3] — скільки подій там уже було за період навчання моделі.
   //
   // Пунктир БІЛЬШЕ НЕ означає «подій ще не було» всередині цього переліку:
   // на теперішніх даних таких вулиць тут майже немає (0-2 з 200), бо модель
   // зважує й історію. Вулиці без подій ідуть окремим переліком v.quiet і
   // вмикаються прапорцем — там пунктир і має сенс.
   // Під кольоровою лінією світлий ореол: на строкатій підкладці тонка лінія
   // ризику інакше губиться серед вулиць. Узято з макета.
   const halo=cssv('--halo');
   v.items.forEach(it=>{
     const w=Math.max(2,1.5+it[2]/16);
     L.polyline(it[0],{color:halo,weight:w+4,opacity:.5,lineCap:'round',
       interactive:false}).addTo(rlayer);
     bindRisk(L.polyline(it[0],{color:col,weight:w,lineCap:'round',
       opacity:Math.max(.35,.85*it[2]/100)}),k,it,false).addTo(rlayer);});
   if(quietOn) (v.quiet||[]).forEach(it=>{
     bindRisk(L.polyline(it[0],{color:col,weight:2,opacity:.5,dashArray:'7,5'}),
       k,it,true).addTo(rlayer);});
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
// ---- ПЕРЕМИКАЧ ТЕМ ----
// Три слова в куті карти, вибір запам'ятовується: тему обирають раз і надовго
// (в аудиторії проєктор — світла, вдома — темна), і питати щоразу немає за що.
const tswCtl=L.control({position:'topright'});
tswCtl.onAdd=()=>{const d=L.DomUtil.create('div','tsw');
 d.innerHTML=THNAMES.map(([k,n])=>
   `<button data-t="${k}"${k===THEME?' aria-pressed="true"':''}>${n}</button>`).join('');
 L.DomEvent.disableClickPropagation(d);
 d.onclick=e=>{const b=e.target.closest('[data-t]'); if(b) setTheme(b.dataset.t)};
 return d};
tswCtl.addTo(map);
function setTheme(t){
 if(!PAL[t]||t===THEME) return;
 THEME=t; try{localStorage.setItem('karta-tema',t)}catch(e){}
 document.body.dataset.t=t; PALA=PAL[t];
 document.querySelectorAll('.tsw button').forEach(b=>
   b.setAttribute('aria-pressed',b.dataset.t===t?'true':'false'));
 Object.keys(R.lines||{}).forEach(k=>{
   if(k.startsWith('risk_'))RCOL[k]=PALA[(R.lines[k].theme||0)%PALA.length]});
 // Кольори в рядках тем проставлені інлайном при побудові переліку. Перебудувати
 // перелік не можна: разом з ним загинули б і поставлені галочки, і підписки
 // на них, — тому міняємо колір на місці.
 paintRows();
 if(cityMask) cityMask.setStyle({color:cssv('--ground'),fillColor:cssv('--ground')});
 if(cityLine) cityLine.setStyle({color:cssv('--dim')});
 tiles(); paintScope(); draw(); drawRisks(); drawFacts();
}"""
