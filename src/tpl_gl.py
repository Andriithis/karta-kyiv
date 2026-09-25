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
 ringColors(); ADDR_VIS=null;
 draw();
}
function draw(){
 const st=computeVis(); LASTST=st;
 heatOn=(MODE==='heat');
 ringSums(st); map.triggerRepaint();
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
// ---- КІЛЬЦЯ (розд. 23, п. 1 і 5) ----
// Склад кілець — з дерева TREE (map_clusters): рівні з кроком 0,5 зуму, від
// міського огляду до z14,5, кожен вузол цілком лежить в одному батьківському.
// Браузер нічого не групує сам — лише складає суми за поточним фільтром і
// анімує перехід між сусідніми рівнями. Рівень NL — самі адреси: з z15 кілець
// немає, адреси малює шар GL.
const TZ0=TREE.z0, TDZ=TREE.dz, LV=TREE.lv, NL=LV.length, LEAF=TREE.leaf, NG=M.groups.length;
// Палітра «Яскрава» (розд. 23, п. 4) — кольори сайту, приглушені на 12%.
// Вибір палітри глядачем — окремим комітом; порядок — як у M.groups.
const YASKRAVA=['#DF6D40','#28AB7D','#5244A5','#D85151','#367BCE','#118412','#DD7DA2'];
const RING_OP=.86;
const nOf=i=>i===NL?LEAF.length:LV[i].c.length/2;
// Батько вузла j рівня i (i>=1) — на рівні i-1.
const parOf=(i,j)=>LV[i-1].of[j];
// Скільки дітей у вузла — сталий склад, від фільтра не залежить: кільце з
// одним нащадком на наступному рівні — те саме кільце, його не анімуємо.
const KIDS=[]; for(let i=0;i<NL;i++){const a=new Int32Array(nOf(i)); for(const p of LV[i].of) a[p]++; KIDS.push(a)}
// Межі адрес кожного вузла — куди летіти після кліку по кільцю.
const BB=[]; for(let i=0;i<NL;i++){const a=new Float64Array(nOf(i)*4); for(let j=0;j<a.length;j+=4){a[j]=a[j+1]=180;a[j+2]=a[j+3]=-180} BB.push(a)}
LEAF.forEach((pi,k)=>{const j=LV[NL-1].of[k]*4, b=BB[NL-1], la=P[pi][0], lo=P[pi][1];
 b[j]=Math.min(b[j],lo); b[j+1]=Math.min(b[j+1],la); b[j+2]=Math.max(b[j+2],lo); b[j+3]=Math.max(b[j+3],la)});
for(let i=NL-2;i>=0;i--){const c=BB[i+1], b=BB[i];
 LV[i].of.forEach((p,j)=>{const q=p*4, s=j*4;
  b[q]=Math.min(b[q],c[s]); b[q+1]=Math.min(b[q+1],c[s+1]); b[q+2]=Math.max(b[q+2],c[s+2]); b[q+3]=Math.max(b[q+3],c[s+3])})}
// Суми за фільтром. SUM — події за видами, TOT — усього, ACT — скільки адрес
// вузла мають події, ONE — одна з них (коли ACT=1, кільце стає крапкою на
// місці цієї адреси, як у вигляді «Адреси»; рішення 25.09).
let SUM=[], TOT=[], ACT=[], ONE=[], LEAFV=[];
function ringSums(st){
 const vm=new Map(st.vis.map(v=>[v[0],v])), mx=st.vis.length?st.vis[0][1]:1;
 SUM=[];TOT=[];ACT=[];ONE=[];
 for(let i=0;i<=NL;i++){const n=nOf(i); SUM.push(new Int32Array(n*NG)); TOT.push(new Int32Array(n)); ACT.push(new Int32Array(n)); ONE.push(new Int32Array(n).fill(-1))}
 LEAFV=LEAF.map((pi,k)=>{const v=vm.get(P[pi]); if(!v) return null;
  TOT[NL][k]=v[1]; ACT[NL][k]=1; ONE[NL][k]=k;
  for(const g in v[4]) SUM[NL][k*NG+(+g)]=v[4][g];
  return {n:v[1], th:v[2], r0:Math.max(2.8,Math.min(14,2.8+9.5*Math.pow(v[1]/Math.max(mx,1),.42)))}});
 for(let i=NL;i>=1;i--){const s=SUM[i],t=TOT[i],a=ACT[i],o=ONE[i],ps=SUM[i-1],pt=TOT[i-1],pa=ACT[i-1],po=ONE[i-1];
  const n=nOf(i);
  for(let j=0;j<n;j++){ if(!t[j]) continue; const p=parOf(i,j);
   pt[p]+=t[j]; pa[p]+=a[j]; if(po[p]<0) po[p]=o[j];
   for(let g=0;g<NG;g++) ps[p*NG+g]+=s[j*NG+g]}}
}
const rRing=n=>Math.min(30,10+3*Math.log2(Math.max(n,1)));
const fmtN=v=>v>=10000?Math.round(v/1000)+'k':v>=1000?(v/1000).toFixed(1).replace('.',',')+'k':String(v);
// Що малює вузол j рівня i: кільце в центрі вузла, крапку на місці єдиної
// адреси з подіями або нічого (подій за фільтром немає).
// box — межі видимого з запасом: вузли поза ним не створюються зовсім. На
// z14 у рівні тисячі вузлів, і об'єкт на кожен у кожному кадрі з'їдав
// половину частоти кадрів.
function nodeAt(i,j,box){
 if(!TOT.length||!TOT[i][j]) return null;
 const one=ACT[i][j]===1, k=one?ONE[i][j]:-1;
 const lon=one?P[LEAF[k]][1]:LV[i].c[2*j], lat=one?P[LEAF[k]][0]:LV[i].c[2*j+1];
 if(box&&(lon<box[0]||lon>box[2]||lat<box[1]||lat>box[3])) return null;
 if(one) return {dot:true,k,lon,lat,n:TOT[i][j]};
 return {dot:false,lon,lat,n:TOT[i][j],s:SUM[i].subarray(j*NG,(j+1)*NG),i,j};
}
// ---- ПОЛОТНО ----
// Над полотном GL, під вікнами й кнопками. Перемальовується на подію render
// самої карти — у тому самому кадрі, тож кільця не відстають від підкладки.
// Розмір — з devicePixelRatio, інакше кільця й числа розмиті.
const cv=document.createElement('canvas');
cv.style.cssText='position:absolute;left:0;top:0;pointer-events:none';
map.getCanvasContainer().appendChild(cv);
const cx=cv.getContext('2d'); let DPR=1, VIS=[];
function fitCanvas(){const c=map.getCanvas(); DPR=devicePixelRatio||1;
 const w=c.clientWidth, h=c.clientHeight;
 cv.width=Math.round(w*DPR); cv.height=Math.round(h*DPR); cv.style.width=w+'px'; cv.style.height=h+'px'}
fitCanvas(); map.on('resize',fitCanvas);
function drawRing(o,x,y,al){
 const r=rRing(o.n), inner=r*.62; let a0=-Math.PI/2;
 cx.globalAlpha=RING_OP*al;
 // Дірка прозора: крізь кільце видно підкладку.
 for(let g=0;g<NG;g++){const c=o.s[g]; if(!c) continue; const a1=a0+c/o.n*2*Math.PI;
  cx.beginPath(); cx.arc(x,y,r,a0,a1); cx.arc(x,y,inner,a1,a0,true); cx.closePath();
  cx.fillStyle=YASKRAVA[g%YASKRAVA.length]; cx.fill(); a0=a1}
 cx.globalAlpha=al;
 const t=fmtN(o.n);
 cx.font=`600 ${Math.max(9,Math.min(13,inner*.9))}px "IBM Plex Mono",ui-monospace,monospace`;
 cx.textAlign='center'; cx.textBaseline='middle'; cx.lineJoin='round';
 cx.lineWidth=3; cx.strokeStyle=HALO_C; cx.strokeText(t,x,y+.5); cx.fillStyle=INK_C; cx.fillText(t,x,y+.5);
 cx.globalAlpha=1;
}
// Крапка — та сама, що в шарі GL вигляду «Адреси»: колір, розмір, гало.
function drawDot(o,x,y,al,z){const v=LEAFV[o.k]; if(!v) return;
 cx.globalAlpha=.94*al; cx.beginPath(); cx.arc(x,y,v.r0*zmulAt(z),0,7);
 cx.fillStyle=PALA[v.th%PALA.length]; cx.fill();
 cx.lineWidth=1.5; cx.strokeStyle=HALO_C; cx.stroke(); cx.globalAlpha=1}
let HALO_C='#fff', INK_C='#111';
const easeIO=t=>t<.5?2*t*t:1-Math.pow(-2*t+2,2)/2;
let CANVAS_ON=false, CANVAS_DRAWN=false;
// Кольори теми — з CSS, але не в кожному кадрі: getComputedStyle на кадр
// коштував помітну частку частоти кадрів. Оновлюються зі зміною теми.
function ringColors(){HALO_C=cssv('--halo')||'#fff'; INK_C=cssv('--ink')||'#111'}
ringColors();
// Видимість шару адрес міняємо лише тоді, коли вона справді змінилася.
let ADDR_VIS=null;
function addrLayerVisible(v){
 if(v===ADDR_VIS&&map.getLayer('k-addr')&&(map.getLayoutProperty('k-addr','visibility')!=='none')===v) return;
 ADDR_VIS=v;
 for(const id of ['k-addr','k-addr-shadow']) if(map.getLayer(id)) map.setLayoutProperty(id,'visibility',v?'visible':'none');
}
function renderRings(){
 const W=cv.width/DPR, H=cv.height/DPR, z=map.getZoom();
 const f0=Math.max(0,(z-TZ0)/TDZ), zi=Math.min(NL,Math.floor(f0+1e-9));
 const on=MODE==='rings'&&zi<NL&&TOT.length>0;
 // З z15 і у вигляді «Адреси» — лише шар GL; у кільцях нижче z15 адреси
 // малює полотно разом з кільцями, щоб вони розходились із батьківського.
 if(STYLE_OK) addrLayerVisible(MODE!=='rings'||zi>=NL);
 CANVAS_ON=on; VIS=[];
 if(!on&&!CANVAS_DRAWN) return;
 cx.setTransform(DPR,0,0,DPR,0,0); cx.clearRect(0,0,W,H); CANVAS_DRAWN=on;
 if(!on) return;
 const b=map.getBounds(), pad=.25*(b.getNorth()-b.getSouth());
 const box=[b.getWest()-pad,b.getSouth()-pad,b.getEast()+pad,b.getNorth()+pad];
 const inB=o=>o.lon>box[0]&&o.lon<box[2]&&o.lat>box[1]&&o.lat<box[3];
 const pr=o=>{const q=map.project([o.lon,o.lat]); o.x=q.x; o.y=q.y; return o};
 // Перетікання — лише коли змінюється зум. Під час перетягування — один
 // набір: інакше на місці кільця з'являлися б два, батьківське й дочірні.
 const fr=f0-zi, e=zi+1>NL?0:(map.isZooming()?easeIO(Math.min(1,fr)):Math.round(fr));
 const out=[];
 if(e<=0||e>=1){const i=e>=1?zi+1:zi;
  if(i>=NL) return;
  for(let j=0,n=nOf(i);j<n;j++){const o=nodeAt(i,j,box); if(o) out.push([pr(o),1])}
 } else {
  const i0=zi, i1=zi+1, par=new Map();
  for(let j=0,n=nOf(i0);j<n;j++){const o=nodeAt(i0,j,box); if(o) par.set(j,pr(o))}
  const still=new Set();
  for(let j=0,n=nOf(i1);j<n;j++){
   const pj=parOf(i1,j), p=par.get(pj);
   // Дочірнє кільце поза видимим, чий батько теж поза ним, — не потрібне.
   const o=nodeAt(i1,j,p?null:box); if(!o) continue;
   if(!p){ if(inB(o)){pr(o); out.push([o,e])} continue }
   pr(o);
   // Той самий склад або одна адреса з подіями — те саме кільце чи та сама
   // крапка: лишається на місці, без перетікання.
   if((i0<NL&&KIDS[i0][pj]===1)||p.dot){out.push([o,1]); still.add(pj); continue}
   o.x=p.x+(o.x-p.x)*e; o.y=p.y+(o.y-p.y)*e; out.push([o,e]);
  }
  for(const [j,p] of par) if(!still.has(j)) out.unshift([p,1-e]);
 }
 // Крапки знизу, кільця зверху; великі під дрібними.
 out.sort((a,b2)=>(a[0].dot?0:1)-(b2[0].dot?0:1)||b2[0].n-a[0].n);
 for(const [o,al] of out){ if(o.x<-60||o.y<-60||o.x>W+60||o.y>H+60) continue;
  if(o.dot) drawDot(o,o.x,o.y,al,z); else drawRing(o,o.x,o.y,al);
  if(al>=.5) VIS.push(o)}
}
map.on('render',renderRings);
// Кінець руху — ще один кадр: після зуму перетікання має стати на рівень.
map.on('moveend',()=>requestAnimationFrame(()=>map.triggerRepaint()));
// Клік: кільце — переліт до його адрес, не глибше ніж на 2,5 кроку зуму від
// поточного (розд. 23, п. 6); крапка — вікно адреси, як у шарі GL.
function hitRing(pt){let best=null, bd=1e9; const z=map.getZoom();
 for(const o of VIS){const r=o.dot?Math.max(6,LEAFV[o.k]?LEAFV[o.k].r0*zmulAt(z)+3:6):rRing(o.n)+3;
  const d=Math.hypot(o.x-pt.x,o.y-pt.y); if(d<=r&&d<bd){bd=d;best=o}}
 return best}
map.on('click',e=>{
 if(!CANVAS_ON) return;
 const o=hitRing(e.point); if(!o) return;
 if(o.dot) return openAt(LEAF[o.k]);
 const q=o.j*4, bb=BB[o.i], z=map.getZoom();
 const side=$('#side'), W=map.getContainer().clientWidth;
 const right=side&&side.offsetWidth&&W>700?side.offsetWidth+40:40;
 let cam=null;
 try{cam=map.cameraForBounds([[bb[q],bb[q+1]],[bb[q+2],bb[q+3]]],
   {padding:{top:40,bottom:40,left:40,right},maxZoom:Math.min(18,z+2.5)})}catch(err){}
 if(!cam||!cam.center) cam={center:[o.lon,o.lat],zoom:z+1.5};
 map.flyTo({center:cam.center,zoom:Math.min(z+2.5,Math.max(cam.zoom,z+.6)),duration:1400,curve:1.3,essential:true});
});
map.on('mousemove',e=>{ if(!CANVAS_ON) return;
 map.getCanvas().style.cursor=hitRing(e.point)?'pointer':''});
// Перевірка з консолі (розд. 23, перевірка п. 3): для кожного видимого
// кільця — число на ньому і сума подій його адрес за фільтром, порахована
// окремо, прямо з computeVis, а не з дерева.
window.kartaKilcia=()=>{const vm=new Map(LASTST.vis.map(v=>[v[0],v[1]]));
 // Діти вузла рівня i — ті вузли рівня i+1 (або адреси), чий LV[i].of — він.
 const CH=LV.map((l,i)=>{const c=Array.from({length:nOf(i)},()=>[]); l.of.forEach((p,k)=>c[p].push(k)); return c});
 return VIS.filter(o=>!o.dot).map(o=>{let s=0, a=0;
  const walk=(i,j)=>{ if(i===NL){const n=vm.get(P[LEAF[j]]); if(n){s+=n;a++} return}
   for(const c of CH[i][j]) walk(i+1,c)};
  walk(o.i,o.j); return {na_kilci:o.n, suma_adres:s, adres:a}})};
// ---- ВИГЛЯД: «Кільця · Адреси · Теплова» (розд. 23, п. 7) ----
// Замість «Події · Проблеми · Теплова» спільної панелі — лише в GL-збірці.
// Окремого режиму «лише проблеми» немає: ромби проблем лягають поверх (коміт 5).
{const VIEWS=[['rings','Кільця'],['addr','Адреси'],['heat','Теплова']];
 let v=null; try{v=localStorage.getItem('karta-vyhlyad')}catch(e){}
 MODE=VIEWS.some(x=>x[0]===v)?v:'rings';
 const seg=$('#fcat');
 seg.innerHTML=VIEWS.map(([k,n])=>`<button data-m="${k}" aria-pressed="${k===MODE}">${n}</button>`).join('');
 seg.onclick=e=>{const b=e.target.closest('[data-m]'); if(!b) return;
  MODE=b.dataset.m; try{localStorage.setItem('karta-vyhlyad',MODE)}catch(err){}
  seg.querySelectorAll('button').forEach(x=>swSet(x,x===b)); draw()};}
// Підписки на панель — ті самі, що в tpl_draw, без подій карти Leaflet.
document.querySelectorAll('#side input:not([data-r]):not([data-f]):not(#fquiet)').forEach(x=>x.addEventListener('change',draw));
document.querySelectorAll('[data-r]').forEach(x=>x.addEventListener('change',drawRisks));
{const fq=$('#fquiet'); if(fq) fq.addEventListener('change',drawRisks);}
document.querySelectorAll('[data-f]').forEach(x=>x.addEventListener('change',drawFacts));
map.on('zoomend',paintZoomGates);
paintRows();draw();drawRisks();drawFacts();paintZoomGates();
{const i=DSLUG.indexOf(decodeURIComponent(location.hash.slice(1)).toLowerCase());
 if(i>=0&&!M.only) enterDistrict(i,false); else paintDistrictList();}"""
