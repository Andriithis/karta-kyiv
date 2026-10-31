# -*- coding: utf-8 -*-
"""Основа клієнтського JavaScript карти.

Тут: завантаження даних, палітра й теми, константи районів, значки й
кольори шарів контексту і побудова блока «Контекст» у панелі. Жодного
звертання до MapLibre: решта коду на цей файл спирається.
"""
JS_BASE = r"""// ---- ДАНІ (36.22, S-Н.5) ----
// Дані не вшиті в сторінку, а лежать поруч файлами dani/<назва>.<хеш>.json
// (map_dani): браузер тягне їх паралельно й тримає в кеші, доки збірка не
// змінить вміст. Одразу — чотири файли, потрібні першій карті;
// «Прохідність» і «Що поруч» — на вимогу (zavantazhProkhid, zavantazhF).
const DANI=__DANI__;
const vantazh=u=>fetch(u).then(r=>{if(!r.ok) throw new Error(u+': '+r.status); return r.json()});
// Polyline (Google, 5 знаків): дельти координат замість повних чисел.
function polyDek(s){const out=[]; let i=0,a=0,b=0;
 while(i<s.length){const r=[0,0];
  for(let k=0;k<2;k++){let v=0,sh=0,c; do{c=s.charCodeAt(i++)-63; v|=(c&31)<<sh; sh+=5}while(c>=32);
   r[k]=v&1?~(v>>1):v>>1}
  a+=r[0]; b+=r[1]; out.push([a/1e5,b/1e5])}
 return out}
// Події адреси — рядком по чотири знаки (map_dani.pakuvaty_P): 23 біти
// [стаття 7, рік 2, година+1 5, ознака 2, місяць 7]; суд — раз на адресу
// («K») чи окремо для кожної події («V»). Розгортаємо в ті самі масиви
// [суд, стаття, рік, година, ознака, місяць], з якими працює решта коду.
const ABC64='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_', A64={};
[...ABC64].forEach((c,i)=>A64[c]=i);
function podiiaZ(sud,s,o){const v=A64[s[o]]|A64[s[o+1]]<<6|A64[s[o+2]]<<12|A64[s[o+3]]<<18;
 return [sud,v&127,(v>>7)&3,((v>>9)&31)-1,(v>>14)&3,(v>>16)&127]}
function rozpakuvatyP(d){
 return d.p.map(p=>{
  if(Array.isArray(p[2])) p[2]=d.v[p[2][0]]+', '+p[2][1];
  const s=p[4];
  if(typeof s==='string'){const ev=[];
   if(s[0]==='K'){const sud=A64[s[1]]; for(let o=2;o<s.length;o+=4) ev.push(podiiaZ(sud,s,o))}
   else {const n=(s.length-1)/5; for(let j=0;j<n;j++) ev.push(podiiaZ(A64[s[1+j]],s,1+n+4*j))}
   p[4]=ev}
  return p})}
let M,P,R,TREE;
try{let p_;
 [M,p_,R,TREE]=await Promise.all(['meta','pts','ryzyk','tree'].map(k=>vantazh(DANI[k])));
 P=rozpakuvatyP(p_)}
catch(e){bezKarty('Дані карти не завантажилися. Оновіть сторінку.'); throw e}
Object.values(R.lines||{}).forEach(v=>{if(!v.lazy) v.items.forEach(it=>{if(typeof it[0]==='string') it[0]=polyDek(it[0])})});
TREE.lv.forEach(l=>{if(typeof l.c==='string') l.c=polyDek(l.c).flat()});
// Числівник і іменник узгоджуються за останніми цифрами: 1, 21 подія;
// 2–4, 22 події; 5–20, 11–14 подій. Одне правило на всю сторінку — інакше
// кожне місце вигадувало б своє, і десь лишалося б «44 подій».
const pl=(n,one,few,many)=>{const a=n%10,b=n%100;
 return a===1&&b!==11?one:(a>=2&&a<=4&&(b<12||b>14))?few:many};
// ---- ТЕМИ Й ПАЛІТРА ----
// Порядок кольорів — як у M.groups (ГП, АЛК, НАР, НАС, МАЙ, ДОР); «Середовища»
// з 27.09 немає (розд. 18), сьомий колір лишився незадіяним запасом.
// Стару палітру прибрано: у ній громадський порядок і насильство були майже
// однаковим червоним. Ці два набори перевірено на розрізнення при
// дальтонізмі — світліший лягає на світлу підкладку, темніший на решту.
// Восьмий колір у кінці — запас для домашнього насильства: у M.groups воно не
// входить, але без запасу %8 віддавало б йому колір громадського порядку.
// Сьомий — «Порушення на дорозі» (34.3), той самий бузковий, що на GL-карті.
const PAL={
 svitla:['#eb6834','#1baf7a','#4a3aa7','#e34948','#2a78d6','#008300','#8a7e9c','#7a6f63'],
 temna: ['#d95926','#199e70','#9085e9','#e66767','#3987e5','#008300','#d890ba','#8d94a2']};
// Тем дві. Кольорову прибрано (RISHENNYA, розд. 18); хто її колись обрав,
// тепер бачить світлу — і в пам'яті браузера теж лишається світла, щоб
// прибрана тема не поверталася з кожним відкриттям.
const THNAMES=[['svitla','Світла'],['temna','Темна']];
let THEME=null;
try{THEME=localStorage.getItem('karta-tema')}catch(e){}
// Перший запуск — тема системи (ZAVDANNYA-31, 8.5), далі — збережена.
if(!PAL[THEME]){
 let dark=false; try{dark=matchMedia('(prefers-color-scheme: dark)').matches}catch(e){}
 THEME=dark?'temna':'svitla'; try{localStorage.setItem('karta-tema',THEME)}catch(e){}}
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
// Справи адрес для правої панелі лежать у файлах spravy/<район>.json поруч
// зі сторінкою. Панель тягне свій файл тоді, коли її відкривають уперше.
const DOCCACHE={};
// «Прохідність» — на вимогу: файл prokhid тягнеться, коли шар увімкнули.
// Потоки приїжджають стисло: геометрія кожного відрізка лежить один раз у
// geo, а шари несуть тільки номер відрізка й число. Розгортаємо в R.lines,
// щоб решта коду працювала як раніше; позначка lazy знімається.
let PROKHID_P=null;
const zavantazhProkhid=()=>PROKHID_P||(PROKHID_P=vantazh(DANI.prokhid).then(d=>{
 const geo=d.geo.map(g=>[polyDek(g[0]),g[1]]);
 for(const k in d.lines){const v=R.lines[k]; if(!v) continue;
  v.items=d.lines[k].map(x=>[geo[x[0]][0],geo[x[0]][1],x[1]]); delete v.lazy}}));
// «Що поруч» — при першому відкритті картки (там число в назві вкладки).
// Доки файл їде, F порожній: картка показує вкладку без числа й
// перемальовується, коли він прийде (PO_F).
let F={cats:[]}, F_P=null; const PO_F=[];
const zavantazhF=()=>F_P||(F_P=vantazh(DANI.poruch).then(f=>{
 F=f; (F.cats||[]).forEach((c,ci)=>c._i=ci); PO_F.forEach(cb=>cb())}));
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
 metro:'Ⓜ',busstop:'🚏',play:'🧸',abandon:'🏚',parking:'🅿',cctv:'📹',
 // перелік Б1 (METODYKA.md, ч. III, 28.09) — step2e_factors
 b1_bars:'🍺',b1_alk:'🍾',b1_cafe:'🍽',b1_fastfood:'🍔',b1_pawn:'💍',b1_atm:'🏧',
 b1_exchange:'💱',b1_fuel:'⛽',b1_school:'🎒',b1_univer:'🎓',b1_dorm:'🛏',
 b1_hospital:'🏥',b1_pharmacy:'✚',b1_market:'🧺',b1_super:'🛒',b1_mall:'🏬',
 b1_metro:'Ⓜ',b1_stops:'🚏',b1_play:'🧸',b1_underpass:'⤵',b1_abandon:'🏚',
 b1_parking:'🅿',b1_garages:'🚗'};
const FZOOM=14;                               // ближче за цей масштаб — показуємо позначки
const RCOL={metro:'#38bdf8',busstop:'#7dd3fc',
 potik:'#94a3b8'};
// ризик успадковує колір своєї теми — той самий, що в подіях
Object.keys(R.lines||{}).forEach(k=>{if(k.startsWith('risk_'))RCOL[k]=PALA[(R.lines[k].theme||0)%PALA.length]});;
function $ify(sel,html){const el=document.querySelector(sel);if(el)el.innerHTML=html}
{
 // --- КОНТЕКСТ ---
 // Прапорці окремих видів об'єктів, населення й потоків лишаються схованими:
 // drawFacts() і drawRisks() читають саме їх. Вмикають їх три перемикачі в
 // картці (tpl_core). Поділ об'єктів на «притягують / збирають людей»
 // прибрано ще раніше — слухачеві він нічого не давав, а місця займав
 // більше за самі об'єкти.
 (F.cats||[]).forEach((c,ci)=>c._i=ci);
 $ify('#ffact',(F.cats||[]).map(c=>`<input type="checkbox" data-f="${c._i}">`).join('')
   +['potik'].map(k=>
     `<input type="checkbox" data-r="${k}">`).join(''));
}"""
