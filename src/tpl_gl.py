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
 USING_FALLBACK=false; clearTimeout(styleTimer); setAttr(OFM_ATTR);
 styleTimer=setTimeout(()=>fallback(t),8000);
 map.setStyle(OFM[t],{transformStyle:(prev,next)=>carry(prev,patchStyle(next))});
}
function fallback(t){
 if(USING_FALLBACK) return;
 USING_FALLBACK=true; clearTimeout(styleTimer);
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
 ' · адреси — з текстів рішень ЄДРСР</div>'}
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
function onStyleReady(){}
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
// стане справжньою у своєму коміті: ризик і потоки — 6, чинники — 8.
let heatOn=false;
function drawRisks(){}
function drawFacts(){}
function showNear(){return 0}
function showAllNear(){return 0}
// Пошук: поки позначок немає, лише наближаємо; вікно адреси — у коміті вікна.
function focusAddress(i){const p=P[i]; map.flyTo({center:[p[1],p[0]],zoom:17})}
function focusBounds(pts){map.fitBounds(bboxOf(pts),{padding:40,maxZoom:17})}
function focusStreet(i,pts){focusBounds(pts)}"""

JS_GL_DRAW = r"""// Позначки адрес — коміт 4. Поки що draw() лише перераховує, що видно:
// від цього залежать лічильники панелі, і вони мають працювати вже зараз.
function draw(){computeVis()}
// Підписки на панель — ті самі, що в tpl_draw, без подій карти Leaflet.
document.querySelectorAll('#side input:not([data-r]):not([data-f]):not(#fquiet)').forEach(x=>x.addEventListener('change',draw));
document.querySelectorAll('[data-r]').forEach(x=>x.addEventListener('change',drawRisks));
{const fq=$('#fquiet'); if(fq) fq.addEventListener('change',drawRisks);}
document.querySelectorAll('[data-f]').forEach(x=>x.addEventListener('change',drawFacts));
map.on('zoomend',paintZoomGates);
paintRows();draw();drawRisks();drawFacts();paintZoomGates();
{const i=DSLUG.indexOf(decodeURIComponent(location.hash.slice(1)).toLowerCase());
 if(i>=0&&!M.only) enterDistrict(i,false); else paintDistrictList();}"""
