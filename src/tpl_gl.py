# -*- coding: utf-8 -*-
"""Карта на MapLibre GL — друга збірка, kyiv-gl.html.

Мета кроку 5 — паритет із Leaflet-версією: те саме, нічого більше. Цей файл
будується комітами. У каркасі: завантаження бібліотеки, перевірка WebGL,
підкладка OpenFreeMap і запасна CARTO, дві теми, перемикач, атрибуція,
перехід між районами. Адреси, ризик, райони на карті й чинники — наступні
коміти; поки що на їхньому місці заглушки з тими самими іменами, щоб
спільні tpl_base і tpl_core працювали без жодної правки.

JS_GL_LOAD стоїть першим у модулі, JS_GL_MAP — після tpl_base, JS_GL_DRAW —
після tpl_core. Порядок той самий, що й у Leaflet-збірці.
"""
JS_GL_LOAD = r"""// Без WebGL векторна карта не намалюється зовсім — тоді одразу на
// Leaflet-версію з тими самими параметрами адреси, щоб посилання на район
// (#desna) не губилося.
{let ok=false;
 try{const c=document.createElement('canvas');ok=!!(c.getContext('webgl2')||c.getContext('webgl'))}catch(e){}
 if(!ok){location.replace('kyiv.html'+location.search+location.hash);throw new Error('немає WebGL')}}
// MapLibre 6.x — лише ES-модуль, глобального maplibregl більше немає.
// Точна версія: оновлення бібліотеки має бути нашим рішенням, а не сюрпризом.
let maplibregl;
try{const m_=await import('https://unpkg.com/maplibre-gl@6.10.0/dist/maplibre-gl.mjs');
 maplibregl=m_.default||m_}
catch(e){location.replace('kyiv.html'+location.search+location.hash);throw e}"""

JS_GL_MAP = r"""// Дерево кластерів для «Кілець» рахується при збірці (map_clusters): без
// нього браузер не знає, хто чий нащадок, і розпад кільця при наближенні
// неможливий. Сум у дереві немає — їх складає браузер з адрес за фільтром.
const TREE=__TREE__;
// ---- ТЕМИ ----
// Кольорову тему прибрано (RISHENNYA, розд. 18), GL-збірка одразу будується
// на двох. Збережене «kolir» читаємо як світлу.
if(THEME!=='svitla'&&THEME!=='temna'){THEME='svitla';document.body.dataset.t=THEME;PALA=PAL[THEME]}
const GLTH=[['svitla','Світла'],['temna','Темна']];
const OFM={svitla:'https://tiles.openfreemap.org/styles/positron',
           temna:'https://tiles.openfreemap.org/styles/dark'};
const OFM_ATTR='OpenFreeMap © OpenMapTiles, дані © OpenStreetMap';
// Усі наші джерела й шари мають цей префікс: за ним transformStyle відрізняє
// їх від шарів підкладки при зміні теми.
const OURS='k-';
let USING_FALLBACK=false;
// STYLE_OK — чи можна вже додавати джерела. isStyleLoaded() тут не годиться:
// він чекає ще й на всі плитки, і позначки з'являлися б лише після них.
// Оголошено тут, до першого setBase: let нижче за виклик — це помилка, а не
// «ще не визначено», і модуль падав би цілком (той самий урок, що з FICON).
let STYLE_OK=false;
// Запасна підкладка — растрові плитки CARTO за нашим ключем тієї самої теми.
// {r} MapLibre не розуміє, тож @2x підставляємо самі.
function cartoStyle(t){
 const src=CARTO_KEY?TILES[t]:TILES.osm, r=devicePixelRatio>1?'@2x':'';
 return {version:8,sources:{base:{type:'raster',tiles:[src.u.replace('{r}',r)],
   tileSize:256,attribution:src.a}},layers:[{id:'base',type:'raster',source:'base'}]};
}
// ---- ПРАВКИ СТИЛЮ ПІДКЛАДКИ ----
// Стилі OpenFreeMap підписують «name:latin + name:nonlatin», і в Києві
// виходить «Khreshchatyk Street Хрещатик». Беремо українську назву, а де її
// немає — основну з OSM (у Києві вона теж українська).
const UK_NAME=['coalesce',['get','name:uk'],['get','name']];
function patchStyle(s){
 // Щити доріг: у positron три шари щитів (два — американські), їхній фільтр
 // порівнює ref_length, якого в наших плитках немає, — звідси попередження в
 // консолі на кожне завантаження. Номери трас на карті правопорушень не
 // потрібні, тож шари прибираємо, а не лагодимо. Значки закладів (poi)
 // прибираємо з тієї ж причини, що й раніше: вони змагаються з нашими
 // позначками. У positron і dark їх зараз немає, правило — на майбутнє.
 const layers=s.layers.filter(l=>!(l.type==='symbol'&&
   (/shield/.test(l.id)||l['source-layer']==='poi')));
 let font=null, tc='#888', th='#fff';
 for(const l of layers){
  if(l.type!=='symbol'||!l.layout) continue;
  const tf=l.layout['text-field'];
  // Лише підписи з назвою; номер траси (ref) лишається номером.
  if(tf&&JSON.stringify(tf).includes('name')) l.layout['text-field']=UK_NAME;
  // Шрифт і кольори для наших підписів — з підписів вулиць самого стилю:
  // так вони однаково лягають і на світлу, і на темну тему, а шрифт
  // гарантовано є на сервері гліфів.
  if(!font&&l['source-layer']==='transportation_name'&&l.layout['text-font']){
   font=l.layout['text-font']; const p=l.paint||{};
   if(typeof p['text-color']==='string') tc=p['text-color'];
   if(typeof p['text-halo-color']==='string') th=p['text-halo-color'];
  }
 }
 const src=Object.keys(s.sources).find(k=>s.sources[k].type==='vector');
 if(src&&font){
  const txt=(id,sl,minzoom,filter,size,extra)=>({id:'base-'+id,type:'symbol',source:src,
   'source-layer':sl,minzoom,...(filter?{filter}:{}),
   layout:{'text-field':UK_NAME,'text-font':font,'text-size':size,...extra},
   paint:{'text-color':tc,'text-halo-color':th,'text-halo-width':1.2}});
  layers.push(
   // Назви парків і станцій метро — орієнтири, за якими слухач впізнає
   // місце. У стилях OpenFreeMap їх немає, тож додаємо самі, лише текстом,
   // без значків.
   // Парки — з poi, а не з шару park: точки-підписи в park є лише на
   // дрібних масштабах, на z14+ їх там немає.
   txt('park','poi',14,['==',['get','class'],'park'],11,{'text-max-width':8}),
   txt('metro','poi',13,['all',['==',['get','class'],'railway'],
     ['in',['get','subclass'],['literal',['station','subway']]]],11,
     {'text-max-width':8,'text-offset':[0,.2]}),
   // Номери будинків — на тому ж масштабі, що й на Leaflet-карті з z17
   // (зум MapLibre на одиницю менший: плитки 512 px проти 256).
   {id:'base-housenumber',type:'symbol',source:src,'source-layer':'housenumber',minzoom:16,
    layout:{'text-field':['get','housenumber'],'text-font':font,'text-size':10,
     'text-padding':2},
    paint:{'text-color':tc,'text-halo-color':th,'text-halo-width':1,'text-opacity':.75}});
 }
 return {...s,layers};
}
// setStyle скидає все, що ми додали. transformStyle (є в 6.10) переносить
// наші джерела й шари з попереднього стилю в новий як є — без перестворення
// й без повторного setData на одинадцять тисяч адрес — і заразом дає змогу
// поправити сам стиль підкладки до показу.
function carry(prev,next){
 if(!prev) return next;
 const srcs={}; for(const k in prev.sources) if(k.startsWith(OURS)) srcs[k]=prev.sources[k];
 return {...next,sources:{...next.sources,...srcs},
         layers:[...next.layers,...prev.layers.filter(l=>l.id.startsWith(OURS))]};
}
// Стиль віддаємо бібліотеці адресою, а не прочитаним об'єктом: об'єкт MapLibre
// розбирає лише в наступному кадрі анімації, адресу — одразу, як прийде.
// Не прийшов за 8 секунд або прийшов з помилкою — растрові плитки CARTO.
let styleTimer=null;
function setBase(t){
 STYLE_OK=false;
 USING_FALLBACK=false; clearTimeout(styleTimer); setAttr(OFM_ATTR);
 styleTimer=setTimeout(()=>fallback(t),8000);
 map.setStyle(OFM[t],{transformStyle:(prev,next)=>carry(prev,patchStyle(next))});
}
function fallback(t){
 if(USING_FALLBACK) return;
 USING_FALLBACK=true; clearTimeout(styleTimer); STYLE_OK=false;
 setAttr(CARTO_KEY?'© CARTO, © OpenStreetMap':'© OpenStreetMap');
 console.warn('Стиль OpenFreeMap недоступний, підкладка CARTO');
 map.setStyle(cartoStyle(t),{transformStyle:(prev,next)=>carry(prev,next)});
}
const C0=M.center||[50.45,30.52];
const map=new maplibregl.Map({container:'map',center:[C0[1],C0[0]],zoom:M.only?13:11,
  maxZoom:19,attributionControl:false});
// Атрибуція — власним елементом, а не вбудованим. OpenFreeMap кладе свій рядок
// в опис джерела плиток, і стиль його не перебиває; а нам треба саме «OpenFreeMap
// © OpenMapTiles, дані © OpenStreetMap», і при запасній CARTO — рядок CARTO.
const attrEl=document.createElement('div');
attrEl.className='maplibregl-ctrl maplibregl-ctrl-attrib';
// Рядок про адреси — той самий, що й у Leaflet-збірці (причину див. у tpl_map):
// він не залежить від підкладки, тож стоїть за будь-якою з них.
function setAttr(t){attrEl.innerHTML='<div class="maplibregl-ctrl-attrib-inner">'+t+
 ' · адреси — з текстів рішень ЄДРСР · адреси © КМДА</div>'}
map.addControl({onAdd:()=>attrEl,onRemove(){}},'bottom-right');
// Помилка до того, як стиль устиг завантажитися, — це відмова підкладки.
// Пізніші помилки (окремий тайл не прийшов) підкладку не міняють.
map.on('error',()=>{if(!map.isStyleLoaded()) fallback(THEME)});
map.on('style.load',()=>clearTimeout(styleTimer));
setBase(THEME);
map.addControl(new maplibregl.NavigationControl({showCompass:false}),'top-left');
// У модулі змінні не глобальні, а паритет перевіряють з консолі браузера
// (розміри позначок, шари, частота кадрів). Один явний вихід — сама карта.
window.kartaMap=map;
// Перемикач тем — той самий, що в Leaflet-збірці, лише вбудований як
// елемент керування MapLibre.
class ThemeCtl{
 onAdd(){const d=document.createElement('div');d.className='tsw maplibregl-ctrl';
  d.innerHTML=GLTH.map(([k,n])=>
    `<button data-t="${k}"${k===THEME?' aria-pressed="true"':''}>${n}</button>`).join('');
  d.onclick=e=>{const b=e.target.closest('[data-t]'); if(b) setTheme(b.dataset.t)};
  return d}
 onRemove(){}
}
// Тимчасово ліворуч угорі під кнопками масштабу: правий верхній кут займає
// картка-навігатор. На кроці 8 перемикач переїде у смугу періоду.
map.addControl(new ThemeCtl(),'top-left');
// Після кожного завантаження стилю: сюди наступні коміти додаватимуть
// картинки (addImage не переживає setStyle) і фарбування наших шарів у
// кольори теми.
function onStyleReady(){STYLE_OK=true; addrReady()}
map.on('style.load',onStyleReady);
function setTheme(t){
 if(!OFM[t]||t===THEME) return;
 THEME=t; try{localStorage.setItem('karta-tema',t)}catch(e){}
 document.body.dataset.t=t; PALA=PAL[t];
 document.querySelectorAll('.tsw button').forEach(b=>
   b.setAttribute('aria-pressed',b.dataset.t===t?'true':'false'));
 Object.keys(R.lines||{}).forEach(k=>{
   if(k.startsWith('risk_'))RCOL[k]=PALA[(R.lines[k].theme||0)%PALA.length]});
 paintRows();
 setBase(t);
}
// ---- РАЙОНИ ----
// Перехід у район працює вже в каркасі: від нього залежать лічильники панелі.
// Маска й межі на карті — у коміті районів.
const CITY={c:C0,z:11};
function bboxOf(ring){let s=90,w=180,n=-90,e=-180;
 for(const q of ring){if(q[0]<s)s=q[0];if(q[0]>n)n=q[0];if(q[1]<w)w=q[1];if(q[1]>e)e=q[1]}
 return [[w,s],[e,n]]}
function paintScope(){}
function enterDistrict(i,fly){
 if(M.only||!(i>=0&&i<DN.length)) return;
 CURD=i; paintScope();
 map.fitBounds(bboxOf(DBORD[i]),{padding:28,duration:fly===false?0:1150});
 if(location.hash.slice(1)!==DSLUG[i]) history.replaceState(null,'','#'+DSLUG[i]);
 onScopeChange();
}
function exitDistrict(){
 CURD=-1; paintScope();
 map.flyTo({center:[CITY.c[1],CITY.c[0]],zoom:CITY.z,duration:1000});
 history.replaceState(null,'',location.pathname+location.search);
 onScopeChange();
}
window.addEventListener('hashchange',()=>{
 const i=DSLUG.indexOf(decodeURIComponent(location.hash.slice(1)).toLowerCase());
 if(i>=0){if(i!==CURD)enterDistrict(i)} else if(CURD>=0)exitDistrict();
});
// ---- ЗАГЛУШКИ ----
// Ті самі імена, що й у Leaflet-збірці, — tpl_core кличе саме їх. Кожна
// стане справжньою у своєму коміті (крок 9): ризик, потоки й теплова — 7,
// чинники й «Що поруч» — 9.
let heatOn=false;
function drawRisks(){}
function drawFacts(){}
function showNear(){return 0}
function showAllNear(){return 0}
// Кнопка «Що поруч» у вікні адреси (tpl_core) кличе clearNear і пам'ятає
// себе в nearButton — без них клік падав би з помилкою ще до коміту 9.
let nearButton=null;
function clearNear(){
 if(nearButton) nearButton.setAttribute('aria-pressed','false');
 nearButton=null;
}"""

JS_GL_DRAW = r"""// ---- АДРЕСИ ----
// Одне джерело GeoJSON, одна точка на адресу. Фільтр міняє лише дані
// (setData), шари лишаються ті самі: перестворення шарів на кожну галочку
// давало б блимання, від якого й тікаємо з Leaflet.
//
// Розмір — правило кроку 3 з tpl_draw, один в один: той самий радіус від
// кількості й той самий множник за зумом. Лише множник тут не стрибає на
// zoomend, а тече з зумом (interpolate) і на цілих зумах дорівнює
// Leaflet-овому. Зум MapLibre на одиницю менший (плитки 512 px): z12 Leaflet
// тут — z11, тож і сходинки зсунуті на одиницю.
const ZMUL=[[11,.78],[12,1],[13,1],[14,1.35],[15,1.35],[16,1.7]];
const zmulAt=z=>{if(z<=ZMUL[0][0])return ZMUL[0][1];
 for(let k=1;k<ZMUL.length;k++){const [z1,m1]=ZMUL[k],[z0,m0]=ZMUL[k-1];
  if(z<=z1) return m0+(m1-m0)*(z-z0)/(z1-z0)}
 return ZMUL[ZMUL.length-1][1]};
const radiusBy=add=>['interpolate',['linear'],['zoom'],
 ...ZMUL.flatMap(([z,m])=>[z,['+',['*',['get','r0'],m],add]])];
// Від цього зуму — тінь під позначками, як клас deep у Leaflet (там z15).
const DEEP_Z=14;
const PIDX=new Map(P.map((p,i)=>[p,i]));
let LASTST=null;
function addrReady(){
 if(!map.getSource('k-addr')){
  map.addSource('k-addr',{type:'geojson',data:{type:'FeatureCollection',features:[]}});
  // Тінь — другий шар кола, розмитий і трохи зсунутий донизу, під основним.
  // У Leaflet це filter:drop-shadow на полотні; у GL фільтрів полотна немає,
  // а розмите коло дає ту саму м'яку тінь.
  map.addLayer({id:'k-addr-shadow',type:'circle',source:'k-addr',minzoom:DEEP_Z,
   layout:{'circle-sort-key':['get','k']},
   paint:{'circle-radius':radiusBy(1.5),'circle-blur':.45,'circle-translate':[0,1]}});
  map.addLayer({id:'k-addr',type:'circle',source:'k-addr',
   // Малюється за зростанням ключа: великі адреси знизу, дрібні зверху, як у
   // Leaflet; адреси-проблеми — поверх усіх.
   layout:{'circle-sort-key':['get','k']},
   paint:{'circle-radius':radiusBy(0),'circle-color':['get','c'],'circle-opacity':.94,
    'circle-stroke-width':1.5}});
 }
 // Гало й тінь — кольори теми з CSS: шари переходять у новий стиль як є,
 // а колір теми міняється тут.
 const sh=(cssv('--shadow').match(/rgba?\([^)]*\)/)||['rgba(0,0,0,.25)'])[0];
 map.setPaintProperty('k-addr','circle-stroke-color',cssv('--halo'));
 map.setPaintProperty('k-addr-shadow','circle-color',sh);
 draw();
}
function draw(){
 const st=computeVis(); LASTST=st;
 heatOn=(MODE==='heat');
 if(!STYLE_OK||!map.getSource('k-addr')) return;
 // Теплова — у коміті ризику й потоків; поки що в цьому режимі позначок немає.
 const vis=heatOn?[]:st.vis, mx=vis.length?vis[0][1]:1;
 map.getSource('k-addr').setData({type:'FeatureCollection',features:vis.map(([p,n,th])=>({
  type:'Feature',geometry:{type:'Point',coordinates:[p[1],p[0]]},
  properties:{i:PIDX.get(p),c:PALA[th%PALA.length],
   r0:Math.max(2.8,Math.min(14,2.8+9.5*Math.pow(n/Math.max(mx,1),.42))),
   k:(probsOf(p).length?1e6:0)-n}}))});
}
// Радіус позначки зараз — щоб хвостик вікна ставав на її край, а не в центр.
function rNow(i){
 const st=LASTST, v=st&&st.vis.find(x=>x[0]===P[i]);
 if(!v) return 0;
 const mx=st.vis[0][1];
 return Math.max(2.8,Math.min(14,2.8+9.5*Math.pow(v[1]/Math.max(mx,1),.42)))*zmulAt(map.getZoom())+1.5;
}
// ---- ВІКНО АДРЕСИ ----
// Вміст — той самий вузол, що й у Leaflet (popupHTML з tpl_core): склад
// подій, картки проблем, «Усі рішення (N)».
let POPUP=null;
function openAt(i,ll){
 const p=P[i], st=LASTST||computeVis(), v=st.vis.find(x=>x[0]===p);
 const node=!p[3]?streetHTML(p,st):v?popupHTML(...v,st):hiddenHTML(p);
 if(POPUP) POPUP.remove();
 clearNear();
 const off=ll?0:rNow(i), at=ll||[p[1],p[0]];
 // Вікно завжди над адресою. Без сталого боку MapLibre сам перебирав, куди
 // його ставити, і зсув карти під картку виходив непередбачуваним.
 POPUP=new maplibregl.Popup({maxWidth:'360px',offset:off,anchor:'bottom',focusAfterOpen:false})
  .setLngLat(at).setDOMContent(node).addTo(map);
 // Закрите вікно — людина пішла з цього місця: гасимо й «Що поруч».
 POPUP.on('close',clearNear);
 keepClear(POPUP,at,off);
}
// Адреса не має опинитися під карткою-навігатором. Карту зсуваємо рівно
// настільки, щоб вікно лягло на вільну частину, — без наближення: людина
// має бачити, де вона, а різкий зум це губить (розд. 23, п. 6).
// Межі вікна рахуємо від точки адреси й розміру вікна, а не від його
// прямокутника на екрані: у перші кадри MapLibre ще не поставив вікно на
// місце, і прямокутник показував лівий верхній кут карти.
function keepClear(pp,at,off){
 const el=pp&&pp.getElement(); if(!el) return;
 const w=el.offsetWidth, h=el.offsetHeight, q=map.project(at);
 const cw=map.getContainer().clientWidth, ch=map.getContainer().clientHeight, pad=12;
 const r={left:q.x-w/2,right:q.x+w/2,top:q.y-off-h,bottom:q.y};
 let L=pad, R=cw-pad, T=pad, B=ch-pad;
 const side=$('#side');
 if(side&&side.offsetWidth){
  const m=map.getContainer().getBoundingClientRect(), s=side.getBoundingClientRect();
  const c={left:s.left-m.left,right:s.right-m.left,top:s.top-m.top,bottom:s.bottom-m.top};
  // Праворуч угорі на широкому екрані, знизу на всю ширину на телефоні.
  if(c.left<=cw/2) B=Math.min(B,c.top-pad);
  else if(r.top<c.bottom&&r.bottom>c.top) R=Math.min(R,c.left-pad);
 }
 let dx=0,dy=0;
 if(r.right>R) dx=r.right-R;
 if(r.left-dx<L) dx=r.left-L;
 if(r.bottom>B) dy=r.bottom-B;
 if(r.top-dy<T) dy=r.top-T;
 if(dx||dy) map.panBy([dx,dy],{duration:450});
}
map.on('click','k-addr',e=>{const f=e.features&&e.features[0]; if(f) openAt(f.properties.i)});
map.on('mouseenter','k-addr',()=>{map.getCanvas().style.cursor='pointer'});
map.on('mouseleave','k-addr',()=>{map.getCanvas().style.cursor=''});
// ---- ПОШУК: КУДИ НАБЛИЖАТИ ----
// Вікно відкриваємо, коли карта вже стала на місце, а не таймером навмання
// (причину див. у tpl_draw, afterMove).
function afterMove(go){map.once('moveend',go)}
// z16 тут — той самий масштаб, що z17 у Leaflet-версії.
function focusAddress(i){
 const p=P[i]; afterMove(()=>openAt(i));
 map.flyTo({center:[p[1],p[0]],zoom:16});
}
function focusBounds(pts){map.fitBounds(bboxOf(pts),{padding:40,maxZoom:16})}
function focusStreet(i,pts){afterMove(()=>openAt(i,map.getCenter())); focusBounds(pts)}
// Підписки на панель — ті самі, що в tpl_draw, без подій карти Leaflet.
document.querySelectorAll('#side input:not([data-r]):not([data-f]):not(#fquiet)').forEach(x=>x.addEventListener('change',draw));
document.querySelectorAll('[data-r]').forEach(x=>x.addEventListener('change',drawRisks));
{const fq=$('#fquiet'); if(fq) fq.addEventListener('change',drawRisks);}
document.querySelectorAll('[data-f]').forEach(x=>x.addEventListener('change',drawFacts));
map.on('zoomend',paintZoomGates);
paintRows();draw();drawRisks();drawFacts();paintZoomGates();
{const i=DSLUG.indexOf(decodeURIComponent(location.hash.slice(1)).toLowerCase());
 if(i>=0&&!M.only) enterDistrict(i,false); else paintDistrictList();}"""
