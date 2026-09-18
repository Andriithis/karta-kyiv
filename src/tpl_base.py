# -*- coding: utf-8 -*-
"""Спільна основа клієнтського JavaScript для обох рушіїв карти.

Тут: підстановка даних, палітра й теми, ключ і адреси запасних плиток
CARTO, константи районів, значки й кольори шарів контексту і побудова
блока «Контекст» у панелі. Жодного звертання ні до Leaflet, ні до
MapLibre: цей файл входить в обидві збірки першим, решта на нього
спирається.
"""
JS_BASE = r"""const M=__META__, P=__PTS__;
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
// ---- РАЙОНИ В МЕЖАХ ОДНОГО ФАЙЛУ ----
// Міська карта несе межі всіх десяти районів і їхні власні переліки проблем.
// Клік по району не веде на інший файл: карта під'їжджає, затемнює решту
// міста й перемикає панель. Фільтри при цьому лишаються — раніше вони гинули
// разом із перезавантаженням сторінки.
const DN=M.dnames||[], DBORD=M.borders||[], DSLUG=M.dslug||[];
let CURD=-1;                       // -1 = все місто, інакше індекс району
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
}"""
