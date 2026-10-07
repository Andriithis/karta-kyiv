# -*- coding: utf-8 -*-
"""Карта на MapLibre GL — головна сторінка сайту (index.html) з 26.09.2026.

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
// запасну Leaflet-збірку з тими самими параметрами адреси, щоб посилання на
// район (#desna) не губилося. Не на kyiv.html: це тепер переадресація сюди ж,
// і вийшло б коло.
const ZAPAS='karta-zapasna.html';
{let ok=false;
 try{const c=document.createElement('canvas');ok=!!(c.getContext('webgl2')||c.getContext('webgl'))}catch(e){}
 if(!ok){location.replace(ZAPAS+location.search+location.hash);throw new Error('немає WebGL')}}
// MapLibre 6.x — лише ES-модуль, глобального maplibregl більше немає.
// Точна версія: оновлення бібліотеки має бути нашим рішенням, а не сюрпризом.
let maplibregl;
try{const m_=await import('https://unpkg.com/maplibre-gl@6.10.0/dist/maplibre-gl.mjs');
 maplibregl=m_.default||m_}
catch(e){location.replace(ZAPAS+location.search+location.hash);throw e}"""

JS_GL_MAP = r"""// Дерево кластерів для «Кілець» рахується при збірці (map_clusters): без
// нього браузер не знає, хто чий нащадок, і розпад кільця при наближенні
// неможливий. Сум у дереві немає — їх складає браузер з адрес за фільтром.
const TREE=__TREE__;
// ---- ТЕМИ ----
// Кольорову тему прибрано (RISHENNYA, розд. 18), GL-збірка одразу будується
// на двох. Збережене «kolir» читаємо як світлу.
// ---- ПАЛІТРИ НОВОЇ КАРТИ (розд. 23, п. 4, затверджено 25.09) ----
// Одна палітра для кілець, крапок і ромбів; на вибір глядача. Колір
// прив'язаний до НАЗВИ виду, а не до номера в переліку: «Середовище»
// зникло (розд. 18, 27.09) разом зі своїм сьомим кольором (#DD7DA2), а решта
// кольорів лишилася на своїх видах. Крейдяна на темній темі — ті самі світлі
// значення: підібрана окремо губила крейдяний вигляд, а ΔE між видами від
// підкладки не залежить. Запасна карта — на PAL.
// Сьомий вид — «Порушення на дорозі» (34.3, 06.10): ДТП лишилося зеленим
// «Дорожнього руху», порушенням — приглушений бузковий. Перевірено, як у
// розд. 2: до кожного з шести кольорів ΔE2000 ≥ 20 при звичайному зорі й
// ≥ 12,0 (світла) / 11,1 (темна) при дейтеранопії й протанопії — більше за
// найгіршу пару чинної палітри (6,9 / 6,3); контраст до підкладки ≥ 3:1;
// далеко від чорнила (контур проблеми) і від червоного ризику.
const KINDS_ORDER=['Громадський порядок','Алкоголь і торгівля','Наркотики','Насильство проти особи',
 'Майнові','ДТП','Порушення на дорозі'];
const GLPAL_HEX={
 yaskrava:{svitla:['#DF6D40','#28AB7D','#5244A5','#D85151','#367BCE','#118412','#8a7e9c'],
           temna: ['#CC592D','#14976B','#938BE2','#EA5C5F','#357ED7','#1D8219','#d890ba']},
 kreida:  {svitla:['#FFA76E','#5ADAB7','#9B99F0','#F78265','#8AC0F1','#85BB8F','#d890ba'],
           temna: ['#FFA76E','#5ADAB7','#9B99F0','#F78265','#8AC0F1','#85BB8F','#d890ba']},
 hrafit:  {svitla:['#A54D09','#009178','#5056B0','#BD5460','#3C74C2','#417341','#8a7e9c'],
           temna: ['#B03D03','#007C56','#7B73C7','#CE4148','#1965BC','#166E13','#8a7e9c']}};
// Палітра прив'язана до теми (розд. 30, рішення Андрія 28.09): світла —
// Графітова, темна — Крейдяна. Перемикача палітр більше немає: вибір
// «якими кольорами» глядачеві нічого не давав, а на проєкторі потрібна саме
// пара «тема — палітра». Яскрава лишається в коді запасною.
const PAL_OF_THEME={svitla:'hrafit',temna:'kreida'};
let PALK=PAL_OF_THEME[THEME]||'hrafit';
// Масив у порядку M.groups; вид без свого кольору (якщо такий з'явиться) — з
// PAL, а восьмий, запасний, як і там, — у кінці.
function glPal(theme){PALK=PAL_OF_THEME[theme]||'hrafit';
 const src=GLPAL_HEX[PALK][theme]||GLPAL_HEX[PALK].svitla;
 const by={}; KINDS_ORDER.forEach((n,i)=>by[n]=src[i]);
 return M.groups.map((g,gi)=>by[g[0]]||PAL[theme][gi%PAL[theme].length]).concat(PAL[theme].slice(M.groups.length))}
if(THEME!=='svitla'&&THEME!=='temna'){THEME='svitla';document.body.dataset.t=THEME}
PALA=glPal(THEME);
// Лінії ризику tpl_base пофарбував ще палітрою сайту — перефарбовуємо.
Object.keys(R.lines||{}).forEach(k=>{if(k.startsWith('risk_'))RCOL[k]=PALA[(R.lines[k].theme||0)%PALA.length]});
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
// Шрифт підписів підкладки — ним же пишемо номери «Що поруч»: він точно є на
// сервері гліфів.
let BASEFONT=null;
// Темна тема — сутінковий сірий (розд. 25, рішення 27.09): стиль dark
// OpenFreeMap майже чорний (земля #0c0c0c), вода й дороги ледь відрізнялися
// від тла, і на проєкторі карта ставала чорною плямою. Ті самі кольори, що
// в затвердженому MAKET-KROK10. Кольори видів — з розд. 23, п. 4.
const DUSK={background:'#2b2f36',water:'#27384b',waterway:'#27384b',landuse_residential:'#2f333b',
 landcover_wood:'#2e3831',landuse_park:'#2e3831',building:'#373c45',highway_path:'#3c414a',highway_minor:'#434953',
 highway_major_casing:'rgba(20,22,26,.55)',highway_major_inner:'#50565f',highway_major_subtle:'#4a5059',
 highway_motorway_casing:'rgba(20,22,26,.55)',highway_motorway_inner:'#5b626d',highway_motorway_subtle:'#4a5059',
 railway:'#555b65',railway_transit:'#555b65',railway_minor:'#4d535c',railway_dashline:'#2b2f36',
 railway_transit_dashline:'#2b2f36',railway_minor_dashline:'#2b2f36',boundary_state:'#666d78',
 'boundary_country_z0-4':'#666d78','boundary_country_z5-':'#666d78','aeroway-area':'#33373f','aeroway-runway':'#3b4048'};
const DUSK_TEXT='#b9c0cb';   // підписи: 7,3:1 до землі
function duskStyle(layers){
 for(const l of layers){
  if(l.type==='symbol'){l.paint={...(l.paint||{}),'text-color':DUSK_TEXT,'text-halo-color':DUSK.background}; continue}
  const c=DUSK[l.id]; if(!c) continue;
  const k=l.type==='background'?'background-color':l.type==='fill'?'fill-color':l.type==='line'?'line-color':null;
  if(k) l.paint={...(l.paint||{}),[k]:c}}
}
function patchStyle(s,t){
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
   font=l.layout['text-font']; BASEFONT=font; const p=l.paint||{};
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
 // Наші підписи (парки, метро, номери) додано вище — перефарбовуються разом
 // із підписами стилю.
 if(t==='temna') duskStyle(layers);
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
 map.setStyle(OFM[t],{transformStyle:(prev,next)=>carry(prev,patchStyle(next,t))});
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
// Пізніші помилки (окремий тайл не прийшов) підкладку не міняють. Мірило —
// STYLE_OK (подія style.load), а не isStyleLoaded(): той хибний, доки
// вантажаться плитки, і один тайл, що не прийшов після зміни теми, перемикав
// усю карту на CARTO.
map.on('error',e=>{if(!STYLE_OK){console.warn('Помилка стилю:',e&&e.error&&e.error.message); fallback(THEME)}});
// У стилях OpenFreeMap шар лісу просить картинку wood-pattern, якої в
// їхньому наборі немає, — у консолі сипалися попередження. Бракує картинки
// підкладки — ставимо порожню; наші (k-…) додаються з кожним стилем самі.
// Саме резолвером, а не подією styleimagemissing: у 6.10 подія приходить
// разом із попередженням, тобто вже пізно; резолвер питають раніше, і він
// переходить у кожен новий стиль сам.
map.setMissingStyleImageResolver(id=>{ if(!String(id).startsWith(OURS)&&!map.hasImage(id))
 map.addImage(id,{width:1,height:1,data:new Uint8Array(4)})});
map.on('style.load',()=>clearTimeout(styleTimer));
setBase(THEME);
// Кільця й адреси — лише разом із підкладкою (розд. 25, А3): інакше на
// старті вони секунду-дві висіли на порожньому тлі, і карта здавалася
// зламаною. До першого повного кадру (load) — тонка смужка завантаження.
let BASE_READY=false;
// Заставка (ZAVDANNYA-31, 8.1): до першого кадру — назва й «завантажується…»,
// а не порожні межі районів, які читалися як зламана карта.
{const bar=document.createElement('div'); bar.id='kload'; map.getContainer().appendChild(bar);
 const spl=document.createElement('div'); spl.id='ksplash';
 spl.innerHTML='<b>Карта правопорушень Києва</b><span>завантажується…</span>';
 map.getContainer().appendChild(spl);
 const ready=()=>{ if(BASE_READY) return; BASE_READY=true; bar.remove();
  spl.classList.add('off'); setTimeout(()=>spl.remove(),400); addrPaint(); map.triggerRepaint()};
 map.once('load',ready);
 // load чекає на всі плитки першого кадру; якщо якась так і не прийде,
 // кільця не мають зникнути назавжди — не довше 6 с.
 setTimeout(ready,6000);}
// Масштаб — унизу праворуч (розд. 30): лівий верхній кут займає смуга часу,
// лівий бік — картка місця.
map.addControl(new maplibregl.NavigationControl({showCompass:false}),'bottom-right');
// У модулі змінні не глобальні, а паритет перевіряють з консолі браузера
// (розміри позначок, шари, частота кадрів). Один явний вихід — сама карта.
window.kartaMap=map;
// Тема — кнопка ☀/☾ у смузі часу (розд. 30), її будує JS_GL_DRAW
// (stripReady).
// Після кожного завантаження стилю: сюди наступні коміти додаватимуть
// картинки (addImage не переживає setStyle) і фарбування наших шарів у
// кольори теми.
function onStyleReady(){STYLE_OK=true; addrReady(); ctxReady(); distReady(); nearReady(); nearPaint();
 drawRisks(); paintScope(); drawFacts(); vyhReady()}
map.on('style.load',onStyleReady);
function setTheme(t){
 if(!OFM[t]||t===THEME) return;
 THEME=t; try{localStorage.setItem('karta-tema',t)}catch(e){}
 document.body.dataset.t=t; PALA=glPal(t);
 paintStrip();
 Object.keys(R.lines||{}).forEach(k=>{
   if(k.startsWith('risk_'))RCOL[k]=PALA[(R.lines[k].theme||0)%PALA.length]});
 paintRows();
 setBase(t);
}
// ---- РАЙОНИ ----
// Вхід і вихід — з панелі (меню «Район») або адресою #desna; межі, маску й
// підсвітку малює paintScope у JS_GL_DRAW.
const CITY={c:C0,z:11};
function bboxOf(ring){let s=90,w=180,n=-90,e=-180;
 for(const q of ring){if(q[0]<s)s=q[0];if(q[0]>n)n=q[0];if(q[1]<w)w=q[1];if(q[1]>e)e=q[1]}
 return [[w,s],[e,n]]}
// Відступи для fitBounds: картка праворуч (на телефоні — знизу) закриває
// частину карти, і місто чи район мають лягти на вільну частину.
function sidePad(){
 const cont=map.getContainer(), cw=cont.clientWidth, ch=cont.clientHeight, p={top:24,bottom:24,left:24,right:24};
 const side=document.getElementById('side');
 if(side&&side.offsetWidth){const m=cont.getBoundingClientRect(), s=side.getBoundingClientRect();
  // На телефоні картка знизу може бути з пів екрана — межа, щоб місту
  // лишилося місце.
  if(s.left-m.left<=cw/2) p.bottom=Math.min(ch*.55,m.bottom-s.top+16);
  else p.right=Math.min(cw*.6,m.right-s.left+16)}
 return p}
// Межі всього міста — з меж районів.
function cityBox(){let s=90,w=180,n=-90,e=-180;
 for(const r of DBORD) for(const q of r){if(q[0]<s)s=q[0];if(q[0]>n)n=q[0];if(q[1]<w)w=q[1];if(q[1]>e)e=q[1]}
 return DBORD.length?[[w,s],[e,n]]:null}
// Увесь Київ (розд. 25, А3): на старті й після виходу з району. Раніше тут
// був сталий центр і z11 — на вузькому екрані частина міста лишалася за
// краєм, на широкому — під карткою.
// Зум — рівно на рівень дерева кілець (кратний кроку 0,5), трохи дрібніше
// за «впритул»: поза рухом зуму береться найближчий рівень, а його кільця
// розраховані на свій зум; між рівнями, на z9,8, два кільця вже налазили.
function fitCity(duration){const b=cityBox();
 if(!b) return map.flyTo({center:[CITY.c[1],CITY.c[0]],zoom:CITY.z,duration});
 let cam=null; try{cam=map.cameraForBounds(b,{padding:sidePad()})}catch(e){}
 if(!cam) return map.fitBounds(b,{padding:sidePad(),duration});
 const z=Math.max(TZ0,TZ0+Math.floor((cam.zoom-TZ0)/TDZ+1e-6)*TDZ);
 map.easeTo({center:cam.center,zoom:z,duration})}
function enterDistrict(i,fly){
 if(M.only||!(i>=0&&i<DN.length)) return;
 CURD=i; paintScope();
 map.fitBounds(bboxOf(DBORD[i]),{padding:sidePad(),duration:fly===false?0:1150});
 if(location.hash.slice(1)!==DSLUG[i]) history.replaceState(null,'','#'+DSLUG[i]);
 onScopeChange();
}
function exitDistrict(){
 CURD=-1; paintScope();
 fitCity(1000);
 history.replaceState(null,'',location.pathname+location.search);
 onScopeChange();
}
window.addEventListener('hashchange',()=>{
 const i=DSLUG.indexOf(decodeURIComponent(location.hash.slice(1)).toLowerCase());
 if(i>=0){if(i!==CURD)enterDistrict(i)} else if(CURD>=0)exitDistrict();
});
// Ті самі імена, що й у Leaflet-збірці, — tpl_core кличе саме їх:
// drawRisks, drawFacts, showNear, showAllNear, clearNear — у JS_GL_DRAW.
// Кнопка «Що поруч» у вікні адреси (tpl_core) пам'ятає себе в nearButton.
let nearButton=null;"""

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
// Радіус адреси без множника зуму. Найменший — 3,6 px, а не 2,8, як у
// Leaflet (розд. 25, А5): адреса з однією подією на огляді була пилинкою,
// і в неї не влучали ні оком, ні мишею.
const R0_MIN=3.6;
const r0Of=(n,mx)=>Math.max(R0_MIN,Math.min(14,R0_MIN+9.5*Math.pow(n/Math.max(mx,1),.42)));
// Невидима зона кліку — не менше 16 px у діаметрі навколо центру адреси
// (WCAG 2.5.8 просить 24 px на ціль; на щільній карті це з'їло б сусідів,
// тож 16 — і з сусідів береться найближча до курсора).
const HIT_R=8;
function addrAt(p){ if(RINGS_ON||!map.getLayer('k-addr')) return null;
 // у сотах і стовпчиках крапок адрес немає — клік належить соті
 if(MODE==='soty'||MODE==='stovp') return null;
 const fs=map.queryRenderedFeatures([[p.x-HIT_R-14,p.y-HIT_R-14],[p.x+HIT_R+14,p.y+HIT_R+14]],{layers:['k-addr']});
 let best=null, bd=1e9; const zm=zmulAt(map.getZoom());
 for(const f of fs){const q=map.project(f.geometry.coordinates), d=Math.hypot(q.x-p.x,q.y-p.y);
  if(d<=Math.max(HIT_R,f.properties.r0*zm+1.5)&&d<bd){bd=d; best=f}}
 return best}
// Від цього зуму — тінь під позначками, як клас deep у Leaflet (там z15).
const DEEP_Z=14;
const PIDX=new Map(P.map((p,i)=>[p,i]));
let LASTST=null;
function addrReady(){
 if(!map.getSource('k-addr')){
  // Лінія-проблема — відрізком вулиці, а не значком на одній з її адрес
  // (завдання 29, п. 2): події лінії розкидані вздовж усього відрізка.
  map.addSource('k-probl',{type:'geojson',data:{type:'FeatureCollection',features:[]}});
  map.addLayer({id:'k-probl',type:'line',source:'k-probl',layout:{'line-cap':'round'},
   paint:{'line-color':['get','c'],'line-width':['interpolate',['linear'],['zoom'],11,3,16,7],'line-opacity':.75}});
  map.addSource('k-addr',{type:'geojson',data:{type:'FeatureCollection',features:[]}});
  // Тінь — другий шар кола, розмитий і трохи зсунутий донизу, під основним.
  // У Leaflet це filter:drop-shadow на полотні; у GL фільтрів полотна немає,
  // а розмите коло дає ту саму м'яку тінь.
  map.addLayer({id:'k-addr-shadow',type:'circle',source:'k-addr',minzoom:DEEP_Z,
   layout:{'circle-sort-key':['get','k']},
   paint:{'circle-radius':addrR(1.5),'circle-blur':.45,'circle-translate':[0,1]}});
  map.addLayer({id:'k-addr',type:'circle',source:'k-addr',
   // Малюється за зростанням ключа: великі адреси знизу, дрібні зверху, як у
   // Leaflet; адреси-проблеми — поверх усіх.
   layout:{'circle-sort-key':['get','k']},
   // радіус і обвідка — 7.5 (0,6 px кольору підкладки)
   paint:{'circle-radius':ADDR_R,'circle-color':['get','c'],'circle-opacity':RING_A,
    'circle-stroke-width':.6}});
 }
 // Гало й тінь — кольори теми з CSS: шари переходять у новий стиль як є,
 // а колір теми міняється тут.
 const sh=(cssv('--shadow').match(/rgba?\([^)]*\)/)||['rgba(0,0,0,.25)'])[0];
 map.setPaintProperty('k-addr','circle-stroke-color',cssv('--halo'));
 map.setPaintProperty('k-addr-shadow','circle-color',sh);
 ringColors(); ADDR_VIS=null; ringsReady();
 draw();
}
function draw(){
 // «Лише проблеми» (ONLYP) — computeVis лишає самі адреси з проблемами.
 const st=computeVis(); LASTST=st;
 ringSums(st); map.triggerRepaint();
 emptyState(st);
 if(!STYLE_OK||!map.getSource('k-addr')) return;
 addrPaint(); drawHex(st);
 if(CELL) renderCell();
 // Картка місця йде за фільтром і періодом так само, як карта.
 if(PLACE) renderPlace();
 const vis=st.vis, mx=vis.length?vis[0][1]:1;
 map.getSource('k-addr').setData({type:'FeatureCollection',features:vis.map(([p,n,th,_bp,_c,thM])=>({
  type:'Feature',geometry:{type:'Point',coordinates:[p[1],p[0]]},
  // колір — найчисленніший вид адреси (7.5), не вид проблеми: проблему
  // позначає контур (7.7)
  properties:{i:PIDX.get(p),c:PALA[(thM??th)%PALA.length],n,r0:r0Of(n,mx),
   pr:probsOf(p).some(q=>q.thi===undefined||q.thi<0||st.GVIS.has(q.thi))?1:0,
   k:(probsOf(p).length?1e6:0)-n}}))});
 // Відрізки ліній-проблем — там, де видно ромби проблем
 const ln=[];
 vis.forEach(([p])=>probsOf(p).forEach(q=>{
  if(q.riven==='лінія'&&q.geom&&(q.thi===undefined||q.thi<0||st.GVIS.has(q.thi)))
   ln.push({type:'Feature',geometry:{type:'LineString',coordinates:q.geom.map(x=>[x[1],x[0]])},
    properties:{c:INK_C}})}));
 if(map.getSource('k-probl')) map.getSource('k-probl').setData({type:'FeatureCollection',features:ln});
}
// ---- КАРТКА МІСЦЯ (розд. 30; MAKET-KROK10, друга редакція) ----
// Одна картка ліворуч, завжди на тому самому місці, замість вікна над точкою,
// панелі рішень праворуч і значків «Що поруч» окремо (AUDYT-3, № 4): вікно
// над точкою закривало саме місце, про яке розповідало, а три панелі водночас
// не вміщалися. Вкладки «Огляд · Рішення (N) · Що поруч (N)»; над точкою —
// лише підказка при наведенні. Вміст рахується з тих самих даних і тим самим
// фільтром (evOn), що й карта, тож числа в картці й на карті — одні.
let POPUP=null;   // лише вікно вулиці «Схожих умов»
let PLACE=null;   // {i, tab, open, pi, allArts, near, hl}
{const c=document.createElement('div'); c.id='kplace'; c.hidden=true;
 c.setAttribute('role','dialog'); c.setAttribute('aria-label','Картка місця');
 map.getContainer().appendChild(c);}
const placeEl=()=>document.getElementById('kplace');
const NEAR_R=250;
// Радіус кожного типу — з моделі (radiusy.json -> factors.json, поле r): тип
// показується в колі, на якому він пов'язаний з подіями; не пов'язаний — у
// найменшому, 50 м (PLAN-KROK7, розд. 3). До перенавчання — усі 250 м.
const nearR=c=>c.r||NEAR_R;
const NEAR_MAX=(F.cats||[]).length?Math.max(...F.cats.map(nearR)):NEAR_R;
// Події місця за поточним фільтром — індекси в p[4] (у тому самому порядку, що
// й справи у spravy/<район>.json). Для проблеми — лише події її статей:
// картка проблеми говорить тільки про проблему (рішення 28.09), решта подій
// адреси туди не потрапляє зовсім.
// Подія картки — посилання [точка, номер у p[4]]: у проблеми з кількох
// адрес (лінія, ділянка, «6-Д» і «6Д») події лежать на різних точках, а
// картка показує їх усі (завдання 29, п. 2).
const EVR=r=>P[r[0]][4][r[1]];
function placeData(){
 const i=PLACE.i, p=P[i], st=LASTST||computeVis();
 const on=r=>evOn(EVR(r),st.C,st.A,st.Y,st.H);
 const probs=p[3]?probsOf(p).filter(q=>q.thi===undefined||q.thi<0||st.GVIS.has(q.thi)):[];
 const pr=probs.length?probs[Math.min(PLACE.pi,probs.length-1)]:null;
 let evs, all;
 if(pr&&pr.ev&&pr.ev.length){all=pr.ev.length; evs=pr.ev.filter(on)}
 else {
  const own=p[4].map((e,k)=>[i,k]), labs=pr?new Set(pr.arts.map(a=>a[0])):null;
  const mine=labs?own.filter(r=>labs.has(M.cats[EVR(r)[1]])):own;
  all=mine.length; evs=mine.filter(on)}
 return {p,st,probs,pr,evs,all};
}
function placeSum(p,evs){
 const n=evs.length; if(!n) return 'за поточним фільтром подій немає';
 const g=new Array(M.groups.length).fill(0); evs.forEach(r=>g[CATTH[EVR(r)[1]]]++);
 const gi=g.indexOf(Math.max(...g)), k=g[gi], nm=lc(shortOf(gi));
 return `${fmt(n)} ${pl(n,'подія','події','подій')} · `+(k===n?`усі — ${nm}`:`переважає ${nm}, ${fmt(k)}`)}
function placeHist(p,evs){
 const h=new Array(24).fill(0); let nk=0; evs.forEach(r=>{const x=EVR(r)[3]; if(x>=0){h[x]++; nk++}});
 if(nk<8) return '';
 const mx=Math.max(...h,1), night=h.slice(20).concat(h.slice(0,4)).reduce((a,b)=>a+b,0);
 return `<div class="hg">${h.map((v,x)=>`<i style="height:${Math.max(2,Math.round(22*v/mx))}px" title="${x}:00 — ${v}"></i>`).join('')}</div>
  <div class="hx"><span>0</span><span>6</span><span>12</span><span>18</span><span>23</span></div><div class="hxl">година доби</div>
  <div class="hn">${Math.round(100*night/nk)}% подій — 20:00–04:00</div>`}
function placeArts(p,evs){
 const c={}; evs.forEach(r=>{const a=EVR(r)[1]; c[a]=(c[a]||0)+1});
 const rows=Object.entries(c).sort((a,b)=>b[1]-a[1]), show=PLACE.allArts?rows:rows.slice(0,5);
 return `<table class="bd">${show.map(([a,n])=>`<tr><td>${esc(M.cats[a])}</td><td><b>${n}</b></td></tr>`).join('')}</table>`+
  (rows.length>show.length?`<button class="kp-lnk" data-kp="arts">ще ${rows.length-show.length} ${pl(rows.length-show.length,'стаття','статті','статей')}</button>`:'')}
// В1 (METODYKA, розд. 2–3): рівень місця, розбивка за механізмами й голос
// мешканців — по рядку, без пояснень, яких немає в даних. Тип місця,
// посібник POP Center, «хто керує» й техніки — лише у звіті «Проблеми»
// (завдання 30, ч. 2): на карті їх читали як висновок про місце.
function probMore(pr){
 let h='';
 const ad=pr.adresy||[];
 if(pr.status==='фіксує поліція') h+=`<div class="tt">Фіксує поліція</div>`;
 if((pr.rozbyvka||[]).length) h+=`<div class="tt">${pr.rozbyvka.map(x=>`${esc(x[0])} — ${x[1]}${x[2]==='фіксує поліція'?' (фіксує поліція)':''}`).join(' · ')}</div>`;
 if(pr.riven==='лінія') h+=`<div class="tt">Лінія${pr.vidrizok?': '+esc(pr.vidrizok):''} — події на ${ad.length} адресах: ${esc(ad.join('; '))}</div>`;
 else if(pr.riven==='ділянка') h+=`<div class="tt">Ділянка вулиці — ${ad.length} ${pl(ad.length,'адреса','адреси','адрес')}: ${esc(ad.join('; '))}</div>`;
 else if(ad.length>1) h+=`<div class="tt">Одне місце, ${ad.length} ${pl(ad.length,'адреса','адреси','адрес')}: ${esc(ad.join('; '))}</div>`;
 const g=pr.golos;
 if(g&&g.stan){
  const t=g.stan==='підтверджують'?`підтверджують — ${g.skarg} ${pl(g.skarg,'скарга','скарги','скарг')} 1551 за рік`+(g.vidnoshennia?`, ×${String(g.vidnoshennia).replace('.',',')} до району`:'')
   :g.stan==='мовчать'?`мовчать — ${g.skarg||0} ${pl(g.skarg||0,'скарга','скарги','скарг')} 1551 за рік`
   :g.stan==='не вимірюється'?(g.chomu&&g.chomu!=='вид'?`не вимірюється (${esc(g.chomu==='житла в 50 м немає'?'без житла':g.chomu)})`:'не вимірюється'):'даних 1551 немає';
  h+=`<div class="tt">Голос мешканців: ${t}</div>`}
 return h}
function oglHTML(d){
 const {p,pr,evs}=d;
 let h='';
 if(pr){
  // «Проблема · вид» — уже в шапці картки; тут удруге не повторюємо (33, В5)
  h+=`<div class="kp-pc"><div class="kp-pct">${esc(pr.mech)}</div>
   <div class="tt">${pr.n} ${pl(pr.n,'однорідна подія','однорідні події','однорідних подій')} за ${pr.years.length} ${pl(pr.years.length,'рік','роки','років')} (${pr.years.join(', ')})</div>${probMore(pr)}</div>`;
 }
 h+=placeArts(p,evs)+placeHist(p,evs);
 // Модель — одним рядком, без пояснень, яких немає в даних (CLAUDE.md).
 if(pr) h+=`<div class="tt kp-mod">${pr.analysis?`Ризик: вулиця в переліку (${esc(lc(pr.theme))})`
   :'Ризик: вулиці в переліку немає'}</div>`;
 return h;
}
function rishHTML(d,cs){
 if(cs===undefined) return '<div class="kp-empty">завантажую…</div>';
 if(cs===null) return '<div class="kp-empty">Перелік рішень лежить окремим файлом поруч, а браузер не дає сторінці з диска його читати. Відкрийте карту з сайту або через PODYVYTYSYA.bat.</div>';
 const it=d.evs.map(r=>[r.join('-'),(cs[r[0]]||[])[r[1]]]).filter(x=>x[1]);
 if(!it.length) return '<div class="kp-empty">За поточним фільтром рішень немає.</div>';
 return it.map(([k,c])=>{const open=PLACE.open===k;
  return `<div class="kp-dec${open?' open':''}" data-dec="${k}" role="button" tabindex="0" aria-expanded="${open}">
   <div class="l1"><b>${esc(fmtDate(c[1]))}</b>${c[6]?'<span class="h">рішення</span>':c[2]>=0?`<span class="h">${String(c[2]).padStart(2,'0')}:00</span>`:''}</div>
   <div class="l2">${esc(M.cats[c[0]])}</div>
   <div class="l3">${esc(c[5]||'опису в рішенні немає')}</div>
   ${open?`<div class="l4">${c[3]?`справа ${esc(c[3])} · `:''}${(c[4]||[]).map((h,j)=>`<a href="${docUrl(h)}" target="_blank" rel="noopener">${(c[4].length>1?'рішення '+(j+1):'відкрити рішення')} ↗</a>`).join(' · ')}</div>`:''}
  </div>`}).join('')}
// До 5 найближчих на тип і лише типи з радіусом моделі > 0 (ZAVDANNYA-31,
// 8.2): тип, не пов'язаний з подіями жодного виду, у «Що поруч» не йде, а
// десять кафе одного кварталу закривали решту переліку. Поки радіусів немає
// (до перенавчання) — усі типи в 250 м, як раніше.
const NEAR_PER=5, RADII=(F.cats||[]).some(c=>c.r>0);
function nearList(p){
 if(!(F.cats||[]).length) return [];
 const my=111320, mx=111320*Math.cos(p[0]*Math.PI/180), out=[];
 F.cats.forEach(c=>{ if(RADII&&!(c.r>0)) return;
  const mine=[];
  c.pts.forEach(q=>{const dd=Math.hypot((q[0]-p[0])*my,(q[1]-p[1])*mx);
   if(dd<=nearR(c)) mine.push({c,q,d:Math.round(dd)})});
  out.push(...mine.sort((a,b)=>a.d-b.d).slice(0,NEAR_PER))});
 return out.sort((a,b)=>a.d-b.d);
}
// Без пояснювальних речень (правило Андрія 29.09): що кожен тип — у своєму
// радіусі, сказано в методиці; радіус видно з кола на карті й відстаней.
function nearHTML(){
 const L=PLACE.near;
 if(!L.length) return `<div class="kp-empty">Поруч об'єктів із переліку немає.</div>`;
 // позначки проактивності тут немає — лише у звітах (RISHENNYA 34.5)
 return `
<ol class="kp-near">${L.map((o,j)=>`<li data-near="${j+1}"${PLACE.hl===j+1?' class="hl"':''}><span class="kp-nn">${j+1}</span><span class="kp-ni">${FICON[o.c.k]||'•'}</span>${esc(o.c.n)}<span class="kp-nd">${o.d} м</span></li>`).join('')}</ol>`}
// Справи для картки — з файлів районів тих точок, де лежать події картки:
// у проблеми з кількох адрес їх буває кілька. cs — {точка: справи}.
let DOCS_NOW={key:'',cs:undefined};
function docsForRefs(refs){
 const ids=[...new Set(refs.map(r=>r[0]))];
 return Promise.all(ids.map(docsFor)).then(a=>{
  if(a.some(x=>x===null)) return null;
  const o={}; ids.forEach((pi,j)=>o[pi]=a[j]); return o})}
function renderPlace(){
 const el=placeEl(); if(!PLACE){el.hidden=true; document.body.classList.remove('kp-open'); return}
 const d=placeData(), {p,pr,probs,evs}=d;
 const dkey=PLACE.i+'|'+PLACE.pi;
 const body=el.querySelector('.kp-body'), top=body?body.scrollTop:0;
 const nDec=evs.length;
 // «Скарги (N)» — поруч із «Рішення» (RISHENNYA 35.10); скарг немає — вкладки немає
 const sk=skMisce(d);
 const tabs=[['ogl','Огляд'],['rish',`Рішення (${nDec})`]].concat(sk&&sk.length?[['skarg',`Скарги (${fmt(sk.length)})`]]:[])
  .concat(p[3]?[['near',`Що поруч (${PLACE.near.length})`]]:[]);
 if(!tabs.some(t=>t[0]===PLACE.tab)) PLACE.tab='ogl';
 const title=p[3]?(p[2]||'адреса не визначена'):streetName(p)+' · вся вулиця';
 el.innerHTML=`<div class="kp-head">
   ${pr?`<div class="kp-badge">Проблема · ${esc(pr.theme)}</div>`:''}
   <b class="kp-title">${esc(title)}</b>
   <div class="kp-sum">${pr?(evs.length===d.all?`${d.all} ${pl(d.all,'подія','події','подій')} проблеми`:`${d.all} ${pl(d.all,'подія','події','подій')} проблеми, за фільтром ${evs.length}`):esc(placeSum(p,evs))}${p[3]?'':' · без номера будинку'}</div>
   ${probs.length>1?`<div class="kp-probs">${probs.map((q,j)=>`<button data-kp-pi="${j}" aria-pressed="${j===Math.min(PLACE.pi,probs.length-1)}">${esc(q.mech)}</button>`).join('')}</div>`:''}
   <button class="kp-x" data-kp="close" aria-label="Закрити (Esc)" title="Закрити (Esc)">×</button>
  </div>
  <div class="kp-tabs" role="tablist">${tabs.map(([k,n])=>`<button role="tab" data-kp-tab="${k}" aria-selected="${k===PLACE.tab}">${n}</button>`).join('')}</div>
  <div class="kp-body">${PLACE.tab==='ogl'?oglHTML(d):PLACE.tab==='rish'?rishHTML(d,DOCS_NOW.key===dkey?DOCS_NOW.cs:undefined):PLACE.tab==='skarg'?skHTML(sk,SK_LIM):nearHTML()}</div>`;
 el.hidden=false; document.body.classList.add('kp-open');
 el.querySelector('.kp-body').scrollTop=top;
 // «Що поруч» — на карті лише поки відкрита його вкладка, з тими самими
 // номерами, що в переліку (рішення 28.09).
 if(PLACE.tab==='near') nearNumbered(p,PLACE.near); else clearNear(true);
 if(PLACE.tab==='rish'&&DOCS_NOW.key!==dkey){
  // усі події картки, а не лише за фільтром: фільтр міняється без перезавантаження
  const refs=(pr&&pr.ev&&pr.ev.length)?pr.ev:[[PLACE.i,0]];
  docsForRefs(refs).then(cs=>{DOCS_NOW={key:dkey,cs}; if(PLACE&&PLACE.i+'|'+PLACE.pi===dkey&&PLACE.tab==='rish') renderPlace()})}
}
function openAt(i){
 if(POPUP) POPUP.remove();
 advOpen(false); closePanel();
 const same=PLACE&&PLACE.i===i;
 PLACE={i,tab:same?PLACE.tab:'ogl',open:-1,pi:0,allArts:false,near:P[i][3]?nearList(P[i]):[],hl:0};
 renderPlace(); placeKeepVisible(i);
}
function closePlace(){ if(!PLACE) return; PLACE=null; clearNear(); renderPlace()}
// Місце пішло за край екрана — картка про нього вже ні до чого й лише
// закриває карту (ZAVDANNYA-31, 8.4).
map.on('moveend',()=>{ if(!PLACE) return; const p=P[PLACE.i];
 if(p&&!map.getBounds().contains([p[1],p[0]])) closePlace()});
// Місце не має лишитися під карткою: карту зсуваємо так, щоб точка лягла
// на вільну частину між карткою й навігатором (на телефоні — над карткою),
// без наближення.
function placeKeepVisible(i){
 const p=P[i]; if(!p) return;
 const cont=map.getContainer(), m=cont.getBoundingClientRect(), el=placeEl(), side=$('#side');
 const c=el.getBoundingClientRect(), q=map.project([p[1],p[0]]), W=cont.clientWidth, H=cont.clientHeight;
 const phone=c.left-m.left<24&&c.width>W*.8;
 let dx=0, dy=0;
 if(phone){const top=c.top-m.top; if(q.y>top-24) dy=q.y-top/2}
 else {const L=c.right-m.left+24, s=side&&side.offsetWidth?side.getBoundingClientRect():null, R=s?s.left-m.left-24:W-24;
  if(q.x<L||q.x>R) dx=q.x-(L+Math.max(0,R-L)/2);
  // Біля верхнього чи нижнього краю коло «Що поруч» (250 м) виходило б за
  // екран — тоді й по вертикалі до середини.
  if(q.y<H*.2||q.y>H*.8) dy=q.y-H/2}
 if(dx||dy) map.panBy([dx,dy],{duration:450});
}
placeEl().addEventListener('click',e=>{
 if(!PLACE) return;
 const t=e.target.closest('[data-kp-tab]'); if(t){PLACE.tab=t.dataset.kpTab; PLACE.open=-1; SK_LIM=50; renderPlace(); return}
 const pi=e.target.closest('[data-kp-pi]'); if(pi){PLACE.pi=+pi.dataset.kpPi; PLACE.open=-1; renderPlace(); return}
 const k=e.target.closest('[data-kp]'); if(k){ if(k.dataset.kp==='close') closePlace(); else if(k.dataset.kp==='arts'){PLACE.allArts=true; renderPlace()} return}
 if(e.target.closest('a')) return;
 const dc=e.target.closest('[data-dec]'); if(dc){const n=dc.dataset.dec; PLACE.open=PLACE.open===n?-1:n; renderPlace(); return}
 const nr=e.target.closest('[data-near]'); if(nr){nearHighlight(+nr.dataset.near,true); return}
});
placeEl().addEventListener('keydown',e=>{const dc=e.target.closest('[data-dec]');
 if(dc&&(e.key==='Enter'||e.key===' ')){e.preventDefault(); dc.click()}});
placeEl().addEventListener('mouseover',e=>{const nr=e.target.closest('[data-near]'); if(nr) nearHighlight(+nr.dataset.near,false)});
// Підсвітка об'єкта «Що поруч»: у переліку й на карті одночасно; з карти —
// ще й прокрутка переліку до рядка.
function nearHighlight(n,scroll){
 if(!PLACE) return;
 if(PLACE.hl&&map.getSource('k-near')) map.setFeatureState({source:'k-near',id:PLACE.hl},{hl:false});
 PLACE.hl=n;
 if(n&&map.getSource('k-near')) map.setFeatureState({source:'k-near',id:n},{hl:true});
 placeEl().querySelectorAll('[data-near]').forEach(li=>li.classList.toggle('hl',+li.dataset.near===n));
 if(scroll){const li=placeEl().querySelector(`[data-near="${n}"]`); if(li) li.scrollIntoView({block:'nearest'})}
}
// Вікно вулиці «Схожих умов» не має опинитися під карткою-навігатором. Карту зсуваємо рівно
// настільки, щоб вікно лягло на вільну частину, — без наближення: людина
// має бачити, де вона, а різкий зум це губить (розд. 23, п. 6).
// Межі вікна рахуємо від точки адреси й розміру вікна, а не від його
// прямокутника на екрані: у перші кадри MapLibre ще не поставив вікно на
// місце, і прямокутник показував лівий верхній кут карти.
//
// Вікно видно цілком (розд. 23, п. 9): висоту обмежуємо вільним місцем по
// вертикалі — високе вікно прокручується всередині, а не вилазить за край;
// кнопки масштабу й теми ліворуч угорі вікно теж не закриває.
function keepClear(pp,at,off){
 const el=pp&&pp.getElement(); if(!el) return;
 const cont=map.getContainer(), cw=cont.clientWidth, ch=cont.clientHeight, pad=12, TIP=12;
 const box=e=>{ if(!e||!e.offsetWidth) return null;
  const m=cont.getBoundingClientRect(), s=e.getBoundingClientRect();
  return {left:s.left-m.left,right:s.right-m.left,top:s.top-m.top,bottom:s.bottom-m.top}};
 let L=pad, R=cw-pad, T=pad, B=ch-pad;
 // Картка праворуч угорі на широкому екрані, знизу на всю ширину на телефоні.
 const c=box($('#side')), phone=!!c&&c.left<=cw/2;
 if(phone) B=Math.min(B,c.top-pad);
 // Кнопки ліворуч угорі. Якщо поруч із ними вікну не вміститися (вузький
 // екран), вікно стоїть нижче за них.
 const k=box(cont.querySelector('.maplibregl-ctrl-top-left'));
 if(k&&cw-(k.right+pad)-pad<el.offsetWidth) T=Math.max(T,k.bottom+pad);
 // Прокрутка — у вмісті вікна (.lp — адреса й вулиця, .rpop — вулиця
 // «Схожих умов»); 24 — внутрішні поля вікна.
 const sc=el.querySelector('.lp,.rpop');
 if(sc) sc.style.maxHeight=Math.max(120,Math.min(560,B-T-off-TIP-24))+'px';
 const w=el.offsetWidth, h=el.offsetHeight, q=map.project(at);
 const r={left:q.x-w/2,right:q.x+w/2,top:q.y-off-TIP-h,bottom:q.y};
 if(c&&!phone&&r.top<c.bottom&&r.bottom>c.top) R=Math.min(R,c.left-pad);
 let dx=0,dy=0;
 if(r.right>R) dx=r.right-R;
 if(r.left-dx<L) dx=r.left-L;
 if(r.bottom>B) dy=r.bottom-B;
 if(r.top-dy<T) dy=r.top-T;
 // Вікно, що налізло на кнопки ліворуч угорі, опускаємо під них, а якщо
 // знизу місця немає — зсуваємо праворуч від них.
 if(k){const t=r.top-dy, b=r.bottom-dy, l=r.left-dx;
  if(l<k.right+pad&&t<k.bottom+pad){
   const down=k.bottom+pad-t, right=k.right+pad-l;
   if(b+down<=B) dy-=down; else if(r.right-dx+right<=R) dx-=right}}
 if(dx||dy) map.panBy([dx,dy],{duration:450});
}
// Esc закриває вікно адреси чи вулиці й «Розширено» (панель рішень Esc
// закриває сама, tpl_core).
document.addEventListener('keydown',e=>{ if(e.key!=='Escape') return;
 if(POPUP) POPUP.remove(); advOpen(false); $('#fd').hidden=true; closePlace()});
// Меню «Район» закривається кліком повз нього (AUDYT-3, № 6): відкрите, воно
// лишалося висіти над переліком посилань, доки не оберуть район.
document.addEventListener('click',e=>{ const fd=$('#fd');
 if(fd&&!fd.hidden&&!e.target.closest('#fd,#dbtn')) fd.hidden=true});
// Одна відкрита панель за раз (розд. 25, А7): «Розширено» і вікно адреси
// водночас не відкриті — картка «Статті» лягала поверх вікна.
$('#advbtn').addEventListener('click',()=>{ if(!$('#adv').hidden){ if(POPUP) POPUP.remove(); closePlace()}});
// Поки видно кільця, шар адрес лише прозорий, не вимкнений (addrLayerVisible):
// клік і курсор над ним тоді належать кільцям (addrAt це враховує). Клік —
// за зоною addrAt, а не за самим колом: дрібну адресу інакше не влучити.
map.on('click',e=>{ if(iconAt(e.point)) return;
 const f=addrAt(e.point); if(f){CLICK_TAKEN=true; openAt(f.properties.i)}});
// Клік уже відкрив вікно чи повів до кільця — загальний обробник (ctxEvents)
// його не чіпає. Питати карту «що під курсором» там уже пізно: вікно
// зсуває карту під себе, а з «меншим рухом» у системі — миттєво, і клік по
// адресі виглядав би кліком по порожньому місцю, що закриває вікно.
let CLICK_TAKEN=false;
map.on('mousedown',()=>{CLICK_TAKEN=false});
map.on('touchstart',()=>{CLICK_TAKEN=false});
// ---- ПОШУК: КУДИ НАБЛИЖАТИ ----
// Вікно відкриваємо, коли карта вже стала на місце, а не таймером навмання
// (причину див. у tpl_draw, afterMove).
function afterMove(go){map.once('moveend',go)}
// z16 тут — той самий масштаб, що z17 у Leaflet-версії.
function focusAddress(i){
 const p=P[i]; afterMove(()=>openAt(i));
 // Зсув — щоб адреса опинилася праворуч від картки місця, а не під нею.
 const w=placeEl().offsetWidth||396;
 map.flyTo({center:[p[1],p[0]],zoom:16,offset:[window.innerWidth>700?w/2:0,0]});
}
function focusBounds(pts){map.fitBounds(bboxOf(pts),{padding:40,maxZoom:16})}
function focusStreet(i,pts){afterMove(()=>openAt(i)); focusBounds(pts)}
// ---- КІЛЬЦЯ (розд. 23, п. 1 і 5) ----
// Склад кілець — з дерева TREE (map_clusters): рівні з кроком 0,5 зуму, від
// міського огляду до z14,5, кожен вузол цілком лежить в одному батьківському.
// Браузер нічого не групує сам — лише складає суми за поточним фільтром і
// анімує перехід між сусідніми рівнями. Рівень NL — самі адреси: з z15 кілець
// немає, адреси малює шар GL.
const TZ0=TREE.z0, TDZ=TREE.dz, LV=TREE.lv, NL=LV.length, LEAF=TREE.leaf, NG=M.groups.length;
// Непрозорість ~86% — однакова для кілець і крапок (розд. 23, п. 3).
// Поки ввімкнено «Схожі умови» чи потоки, кільця й крапки прозоріші (~0,45):
// смуги лежать під ними, і повна заливка їх закривала б (доповнення 17.09).
const RING_OP=.6, RING_DIM=.45;   // 0,6 — макет «Проблема — контуром» (35.6)
let RING_A=RING_OP;
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
// NP — скільки проблем у вузлі, PT — вид проблеми найбільшої з його адрес
// (PTN — її подій): ромб на краю кільця має цей колір. PROBK — адреси з
// проблемами за поточним фільтром, для ромбів вигляду «Адреси».
let NP=[], PT=[], PTN=[], PROBK=[];
// SX, SY — суми координат адрес вузла з подіями за фільтром. У районі
// кільце стає в їхній центр, а не в центр кластера з дерева: дерево рахує
// центр за всіма адресами міста, і кільце з подіями Подолу могло стояти
// за межею Подолу, під затемненням.
let SX=[], SY=[];
function ringSums(st){
 const vm=new Map(st.vis.map(v=>[v[0],v])), mx=st.vis.length?st.vis[0][1]:1;
 SUM=[];TOT=[];ACT=[];ONE=[];NP=[];PT=[];PTN=[];PROBK=[];SX=[];SY=[];
 for(let i=0;i<=NL;i++){const n=nOf(i); SUM.push(new Int32Array(n*NG)); TOT.push(new Int32Array(n)); ACT.push(new Int32Array(n)); ONE.push(new Int32Array(n).fill(-1));
  NP.push(new Int32Array(n)); PT.push(new Int32Array(n).fill(-1)); PTN.push(new Int32Array(n));
  SX.push(new Float64Array(n)); SY.push(new Float64Array(n))}
 NMAX=[];
 LEAFV=LEAF.map((pi,k)=>{const v=vm.get(P[pi]); if(!v) return null;
  TOT[NL][k]=v[1]; ACT[NL][k]=1; ONE[NL][k]=k; SX[NL][k]=P[pi][1]; SY[NL][k]=P[pi][0];
  for(const g in v[4]) SUM[NL][k*NG+(+g)]=v[4][g];
  // Проблеми — тим самим правилом, що й у computeVis і у вікні адреси:
  // проблема за прихованим видом для цього вигляду не проблема.
  const pr=probsOf(P[pi]).filter(q=>q.thi===undefined||q.thi<0||st.GVIS.has(q.thi));
  // Колір ромба — вид проблеми, як колір крапки-проблеми (computeVis).
  const pt=v[3]?v[2]:((pr.find(q=>q.thi>=0)||{}).thi??v[2]);
  if(pr.length){NP[NL][k]=pr.length; PT[NL][k]=pt; PTN[NL][k]=v[1]; PROBK.push(k)}
  return {n:v[1], th:v[2], np:pr.length, pt, r0:r0Of(v[1],mx)}});
 for(let i=NL;i>=1;i--){const s=SUM[i],t=TOT[i],a=ACT[i],o=ONE[i],ps=SUM[i-1],pt=TOT[i-1],pa=ACT[i-1],po=ONE[i-1];
  // (n_max рахується нижче, після сум)
  const np=NP[i],pq=PT[i],pn=PTN[i],pnp=NP[i-1],ppq=PT[i-1],ppn=PTN[i-1];
  const n=nOf(i);
  for(let j=0;j<n;j++){ if(!t[j]) continue; const p=parOf(i,j);
   pt[p]+=t[j]; pa[p]+=a[j]; if(po[p]<0) po[p]=o[j];
   SX[i-1][p]+=SX[i][j]; SY[i-1][p]+=SY[i][j];
   if(np[j]){pnp[p]+=np[j]; if(pn[j]>ppn[p]){ppn[p]=pn[j]; ppq[p]=pq[j]}}
   for(let g=0;g<NG;g++) ps[p*NG+g]+=s[j*NG+g]}}
 for(let i=0;i<=NL;i++){let m=1; const t=TOT[i]; for(let j=0;j<t.length;j++) if(t[j]>m) m=t[j]; NMAX.push(m)}
}
// Кільця рівнів міського огляду (до z11) — на 30% менші (розд. 30, MAKET-START
// «Б»). Множник той самий, що в map_clusters.ring_k: дерево розраховане саме
// під ці радіуси, інакше кільця знову налізли б одне на одне.
const ringK=i=>TZ0+i*TDZ<11?.7:1;
// Площа кільця ∝ кількості (34.4): 6 + 26·√(n / n_max), n_max — найбільше
// кільце рівня за поточним фільтром; на огляді міста ×0,7.
let NMAX=[];
const rRing=(n,i)=>(6+26*Math.sqrt(Math.max(n,1)/Math.max(1,(NMAX[i]||n))))*(i===undefined?1:ringK(i));
const fmtN=v=>v>=10000?Math.round(v/1000)+'k':v>=1000?(v/1000).toFixed(1).replace('.',',')+'k':String(v);
// Що малює вузол j рівня i: кільце в центрі вузла, крапку на місці єдиної
// адреси з подіями або нічого (подій за фільтром немає).
// box — межі видимого з запасом: вузли поза ним не створюються зовсім. На
// z14 у рівні тисячі вузлів, і об'єкт на кожен у кожному кадрі з'їдав
// половину частоти кадрів.
function nodeAt(i,j,box){
 if(!TOT.length||!TOT[i][j]) return null;
 const one=ACT[i][j]===1, k=one?ONE[i][j]:-1;
 const own=CURD>=0&&!one;
 const lon=one?P[LEAF[k]][1]:own?SX[i][j]/ACT[i][j]:LV[i].c[2*j],
       lat=one?P[LEAF[k]][0]:own?SY[i][j]/ACT[i][j]:LV[i].c[2*j+1];
 if(box&&(lon<box[0]||lon>box[2]||lat<box[1]||lat>box[3])) return null;
 if(one) return {dot:true,k,lon,lat,n:TOT[i][j]};
 return {dot:false,lon,lat,n:TOT[i][j],s:SUM[i].subarray(j*NG,(j+1)*NG),i,j,np:NP[i][j],pt:PT[i][j]};
}
// ---- МАЛЮВАННЯ: ВЛАСНИЙ ШАР WEBGL ----
// Кільця, крапки й числа малює власний шар MapLibre (type 'custom') у тому
// самому проході WebGL, що й карта. Спершу тут було 2D-полотно поверх карти:
// власний код брав ~5 мс на кадр, а накладання окремого полотна на карту
// роняло зум міста до 36–39 кадрів/с на Intel HD 630 (24 з процесором ×4).
// Розд. 16: плавність — головна вимога, тож окремого полотна немає.
//
// Позиції рахуємо на процесорі (map.project, CSS-пікселі), як і раніше, — це
// дешево; GPU лише зафарбовує квадрат навколо кожного кільця: дуги за
// видами, дірка 0,62 r, згладжений край. Числа — з атласу цифр (одна
// текстура, квадрат на літеру), а не шаром symbol: той брав би дані через
// setData і фоновий воркер і під час розпаду відставав би на кадр-два.
let VIS=[], HALO_C='#fff', INK_C='#111', SHOWP=true;
const easeIO=t=>t<.5?2*t*t:1-Math.pow(-2*t+2,2)/2;
let RINGS_ON=false;
// Кольори теми — з CSS, але не в кожному кадрі: getComputedStyle на кадр
// коштував помітну частку частоти кадрів. Оновлюються зі зміною теми.
function ringColors(){HALO_C=cssv('--halo')||'#fff'; INK_C=cssv('--ink')||'#111'}
ringColors();
const rgb=h=>{h=(h||'#000').trim().replace('#',''); if(h.length===3) h=h.split('').map(c=>c+c).join('');
 return [0,2,4].map(i=>parseInt(h.substr(i,2),16)/255)};
// Шар адрес ховаємо прозорістю, а не visibility: шар із visibility:none
// фоновий потік не розбирає, і після ввімкнення адреси з'являлися лише за
// мить — на межі кілець і адрес карта блимала порожньою. Прозорість
// міняється в тому самому кадрі. Міняємо лише тоді, коли справді змінилося.
let ADDR_VIS=null;
function addrLayerVisible(v){
 if(v===ADDR_VIS) return;
 ADDR_VIS=v; addrPaint();
}
// Прозорість шару адрес: схований (кільця) — 0; у «Проблемах» крапки
// невидимі, але лишаються під ромбами, щоб по ромбу можна було клікнути;
// поки ввімкнено «Схожі умови» чи потоки — приглушені (RING_A).
function addrPaint(){
 if(!map.getLayer('k-addr')) return;
 // Соти й стовпчики в крапки адрес не переходять (рішення Андрія 06.10):
 // крапки — у вигляді «Адреси» й на місці кілець, що розпалися.
 const hexy=MODE==='soty'||MODE==='stovp';
 const on=BASE_READY&&!hexy&&ADDR_VIS!==false;
 const a=RING_A;
 // зблизька крапок мало й вони великі — щільніше (на темній темі 0,6 читалося
 // блідо, перевірка 06.10)
 const up=Math.min(.92,a+.3);
 const op=!on?0:['interpolate',['linear'],['zoom'],14.5,a,15.5,up];
 const op1=!on?0:1;
 map.setPaintProperty('k-addr','circle-opacity',op);
 map.setPaintProperty('k-addr','circle-stroke-opacity',op1);
 map.setPaintProperty('k-addr-shadow','circle-opacity',op1);
 if(map.getLayer('k-addr-pr')) map.setPaintProperty('k-addr-pr','circle-stroke-opacity',op1);
}
// Що видно в цьому кадрі: [[вузол з x, y], непрозорість]. Та сама логіка,
// що й була: рівень за зумом, перетікання до наступного — лише під час зуму.
function frameList(){
 const z=map.getZoom(), f0=Math.max(0,(z-TZ0)/TDZ), zi=Math.min(NL,Math.floor(f0+1e-9));
 RINGS_ON=MODE==='rings'&&zi<NL&&TOT.length>0; VIS=[];
 if(!RINGS_ON) return [];
 const b=map.getBounds(), pad=.25*(b.getNorth()-b.getSouth());
 const box=[b.getWest()-pad,b.getSouth()-pad,b.getEast()+pad,b.getNorth()+pad];
 const inB=o=>o.lon>box[0]&&o.lon<box[2]&&o.lat>box[1]&&o.lat<box[3];
 const pr=o=>{const q=map.project([o.lon,o.lat]); o.x=q.x; o.y=q.y; return o};
 // Перетікання — лише коли змінюється зум. Під час перетягування — один
 // набір: інакше на місці кільця з'являлися б два, батьківське й дочірні.
 const fr=f0-zi, e=zi+1>NL?0:(map.isZooming()?easeIO(Math.min(1,fr)):Math.round(fr));
 const out=[];
 if(e<=0||e>=1){const i=e>=1?zi+1:zi;
  // Рівень «самі адреси» (з z14,75 без руху зуму, округленням) — кілець
  // немає, адреси малює шар GL. Досі тут кільця зникали, а шар адрес
  // чекав рівно z15 — і між ними карта була порожня (помилка 26.09).
  // Шар адрес стане видимим лише з наступного кадру (прозорість міняють
  // після кадру) — на цей один кадр адреси крапками малює шар кілець.
  if(i>=NL){RINGS_ON=false;
   if(ADDR_VIS!==true){for(let j=0,n=nOf(NL);j<n;j++){const o=nodeAt(NL,j,box); if(o) out.push([pr(o),1])} map.triggerRepaint()}
   return out}
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
 // Для кліку й перевірки з консолі — лише те, що на екрані.
 const W=map.getCanvas().clientWidth, H=map.getCanvas().clientHeight;
 for(const [o,al] of out) if(al>=.5&&o.x>-60&&o.y>-60&&o.x<W+60&&o.y<H+60) VIS.push(o);
 return out;
}
// ---- ШЕЙДЕРИ ----
// GLSL 100 — працює і в WebGL 2, і в WebGL 1. Без похідних (fwidth):
// координати квадрата вже в CSS-пікселях, тож згладжування — ±0,5 px.
const VS_DISC=`attribute vec2 a_c; attribute vec2 a_o; attribute vec4 a_m; attribute vec4 a_q0; attribute vec4 a_q1; attribute vec3 a_col;
uniform vec2 u_view; varying vec2 v_p; varying vec4 v_m; varying vec4 v_q0; varying vec4 v_q1; varying vec3 v_col;
void main(){ vec2 s=(a_c+a_o)/u_view*2.0-1.0; gl_Position=vec4(s.x,-s.y,0.0,1.0);
 v_p=a_o; v_m=a_m; v_q0=a_q0; v_q1=a_q1; v_col=a_col; }`;
// v_m: r, внутрішній радіус, вид (0 — кільце, 1 — крапка, 2 — ромб, 3 —
// суцільний контур кольору v_col), непрозорість.
// v_q0, v_q1: межі дуг — накопичені частки видів 1..7 (порядок M.groups).
const FS_DISC=`precision mediump float;
uniform vec3 u_col[7]; uniform vec3 u_halo; uniform vec3 u_ink;
varying vec2 v_p; varying vec4 v_m; varying vec4 v_q0; varying vec4 v_q1; varying vec3 v_col;
void main(){ float d=length(v_p), r=v_m.x;
 if(v_m.z<0.5){
  float cov=(1.0-smoothstep(r-0.5,r+0.5,d))*smoothstep(v_m.y-0.5,v_m.y+0.5,d);
  if(cov<=0.0) discard;
  // кут від верху за годинниковою стрілкою, як дуги на полотні
  float a=atan(v_p.x,-v_p.y)/6.2831853; if(a<0.0) a+=1.0;
  vec3 c=u_col[6];
  if(a<v_q1.z) c=u_col[6]; if(a<v_q1.y) c=u_col[5]; if(a<v_q1.x) c=u_col[4];
  if(a<v_q0.w) c=u_col[3]; if(a<v_q0.z) c=u_col[2]; if(a<v_q0.y) c=u_col[1]; if(a<v_q0.x) c=u_col[0];
  float al=cov*v_m.w; gl_FragColor=vec4(c*al,al);
 } else if(v_m.z<1.5){
  // крапка: заливка до r, гало 1,5 px по краю — як обвідка в шарі GL
  float cov=1.0-smoothstep(r+0.25,r+1.25,d); if(cov<=0.0) discard;
  vec3 c=mix(v_col,u_halo,smoothstep(r-1.25,r-0.25,d));
  float al=cov*v_m.w; gl_FragColor=vec4(c*al,al);
 } else if(v_m.z<2.5){
  // ромб: відстань «по діагоналях»; заливка до r, просвіт до r+2,2, чорнило до r+4,2
  float e=(abs(v_p.x)+abs(v_p.y))*0.7071, h=r*0.7071;
  float cov=1.0-smoothstep(h+2.97-0.5,h+2.97+0.5,e); if(cov<=0.0) discard;
  vec3 c=mix(u_halo,u_ink,smoothstep(h+1.56-0.5,h+1.56+0.5,e));
  c=mix(v_col,c,smoothstep(h-0.5,h+0.5,e));
  float al=cov*v_m.w; gl_FragColor=vec4(c*al,al);
 } else {
  float cov=(1.0-smoothstep(r-0.5,r+0.5,d))*smoothstep(v_m.y-0.5,v_m.y+0.5,d);
  if(cov<=0.0) discard; float al=cov*v_m.w; gl_FragColor=vec4(v_col*al,al);
 } }`;
const VS_TXT=`attribute vec2 a_p; attribute vec2 a_uv; attribute float a_a; uniform vec2 u_view;
varying vec2 v_uv; varying float v_a;
void main(){ vec2 s=a_p/u_view*2.0-1.0; gl_Position=vec4(s.x,-s.y,0.0,1.0); v_uv=a_uv; v_a=a_a; }`;
// Атлас у два рядки: угорі — самі цифри, унизу — їхнє гало, тим самим
// розташуванням. Гало під цифрами, як strokeText під fillText.
const FS_TXT=`precision mediump float; uniform sampler2D u_tex; uniform vec3 u_ink; uniform vec3 u_halo; uniform float u_ha;
varying vec2 v_uv; varying float v_a;
void main(){ float f=texture2D(u_tex,v_uv).a, h=texture2D(u_tex,v_uv+vec2(0.0,0.5)).a*u_ha;
 float al=max(f,h)*v_a; if(al<=0.0) discard;
 vec3 c=mix(u_halo,u_ink,f/max(max(f,h),1e-3)); gl_FragColor=vec4(c*al,al); }`;
// ---- АТЛАС ЦИФР ----
// Шрифт — той самий IBM Plex Mono 600. Малюємо вдвічі більшим за найбільший
// розмір на кільці (13 px) і зменшуємо на GPU: різко на будь-якому екрані.
const GLYPHS='0123456789,k', ATL_PX=26*Math.max(1,Math.min(2,devicePixelRatio||1));
let ATLAS=null, ATLAS_VER=0;
function buildAtlas(){
 const c=document.createElement('canvas'), g=c.getContext('2d');
 const font=`600 ${ATL_PX}px "IBM Plex Mono",ui-monospace,monospace`;
 g.font=font; const adv=Math.ceil(g.measureText('0').width), pad=Math.ceil(ATL_PX*.25);
 const cw=adv+2*pad, ch=Math.ceil(ATL_PX*1.3)+2*pad;
 c.width=cw*GLYPHS.length; c.height=ch*2;
 g.font=font; g.textAlign='center'; g.textBaseline='middle'; g.lineJoin='round';
 g.fillStyle='#fff'; g.strokeStyle='#fff'; g.lineWidth=ATL_PX*3/13;
 [...GLYPHS].forEach((s,k)=>{const x=k*cw+cw/2;
  g.fillText(s,x,ch/2); g.strokeText(s,x,ch+ch/2); g.fillText(s,x,ch+ch/2)});
 ATLAS={canvas:c, cw, ch, adv}; ATLAS_VER++; map.triggerRepaint();
}
(document.fonts&&document.fonts.load?document.fonts.load(`600 ${ATL_PX}px "IBM Plex Mono"`):Promise.resolve())
 .catch(()=>{}).then(buildAtlas);
function glProgram(gl,vs,fs){
 const sh=(t,s)=>{const o=gl.createShader(t); gl.shaderSource(o,s); gl.compileShader(o);
  if(!gl.getShaderParameter(o,gl.COMPILE_STATUS)) throw new Error('шейдер: '+gl.getShaderInfoLog(o)); return o};
 const p=gl.createProgram(); gl.attachShader(p,sh(gl.VERTEX_SHADER,vs)); gl.attachShader(p,sh(gl.FRAGMENT_SHADER,fs));
 gl.linkProgram(p); if(!gl.getProgramParameter(p,gl.LINK_STATUS)) throw new Error('програма: '+gl.getProgramInfoLog(p));
 return p;
}
// Вершини: 6 на квадрат (два трикутники), без розширення інстансів — так
// шар однаково працює на WebGL 1 і 2.
const DISC_F=19, TXT_F=5, CORNERS=[[-1,-1],[1,-1],[1,1],[-1,-1],[1,1],[-1,1]];
let discBuf=new Float32Array(6*DISC_F*512), txtBuf=new Float32Array(6*TXT_F*2048);
const ringLayer={id:'k-rings', type:'custom', renderingMode:'2d',
 onAdd(m,gl){
  this.pd=glProgram(gl,VS_DISC,FS_DISC); this.pt=glProgram(gl,VS_TXT,FS_TXT);
  this.bd=gl.createBuffer(); this.bt=gl.createBuffer(); this.tex=gl.createTexture(); this.texVer=-1;
  this.vao=gl.bindVertexArray?null:gl.getExtension('OES_vertex_array_object');
 },
 onRemove(m,gl){gl.deleteProgram(this.pd); gl.deleteProgram(this.pt); gl.deleteBuffer(this.bd); gl.deleteBuffer(this.bt); gl.deleteTexture(this.tex)},
 render(gl){
  if(!BASE_READY) return;
  const out=frameList();
  // Ромби вигляду «Адреси» (і кілець з z15, де адреси малює шар GL):
  // сталого розміру на кожній адресі з проблемою за фільтром.
  // У режимі «Проблеми» ромби — усе, що є на карті, тож кнопка їх не гасить.
  // ромбів більше немає (35.6): проблема — контур; адреси малює шар GL
  const addrDiamonds=false;
  if(!out.length&&!(addrDiamonds&&PROBK.length)) return;
  const cvs=map.getCanvas(), W=cvs.clientWidth, H=cvs.clientHeight, z=map.getZoom();
  let nd=0, nt=0;
  const need=(out.length*3+PROBK.length+8)*6*DISC_F; if(discBuf.length<need) discBuf=new Float32Array(need*2);
  const Q1=[1,1,1,1,1,1,1,1], C0=[0,0,0];
  const quad=(x,y,ext,r,inner,kind,a,q,col)=>{
   for(const [cx_,cy_] of CORNERS){const b=nd*DISC_F;
    discBuf[b]=x; discBuf[b+1]=y; discBuf[b+2]=cx_*ext; discBuf[b+3]=cy_*ext;
    discBuf[b+4]=r; discBuf[b+5]=inner; discBuf[b+6]=kind; discBuf[b+7]=a;
    for(let g=0;g<8;g++) discBuf[b+8+g]=q[g];
    discBuf[b+16]=col[0]; discBuf[b+17]=col[1]; discBuf[b+18]=col[2]; nd++}};
  // Ромб: половина діагоналі h; навколо — просвіт кольору підкладки й
  // контур чорнила (+2,2 і +4,2 px, як у макеті). Непрозорий: сигнал
  // тримається формою, а не кольором.
  const diamond=(x,y,h,a,col)=>quad(x,y,h+6,h,0,2,a,Q1,col);
  const texts=[], ptexts=[], later=[];
  const ink=rgb(INK_C);
  // ---- кільця й крапки ----
  for(const [o,al] of out){ if(o.x<-60||o.y<-60||o.x>W+60||o.y>H+60) continue;
   if(o.dot){const v=LEAFV[o.k]; if(!v) continue; const r=v.r0*zmulAt(z);
    quad(o.x,o.y,r+2,r,0,1,RING_A*al,Q1,rgb(PALA[v.th%PALA.length]));
    // окрема адреса з проблемою — обвідка навколо крапки замість ромба (7.4)
    if(v.np){const rr=Math.max(5,r)+2.5; quad(o.x,o.y,rr+1.5,rr+.6,rr-.6,3,al,Q1,ink)}
    continue}
   // До 5 подій — крапка без числа; найменше кільце з числом — 11 px;
   // внутрішній радіус 0,76 (35.6, макет «Проблема — контуром»).
   const small=o.n<=5, r=small?4.5:Math.max(11,rRing(o.n,o.i)), inner=small?0:r*.76, q=[1,1,1,1,1,1,1,1];
   let acc=0; for(let g=0;g<7;g++){acc+=g<NG?o.s[g]:0; q[g]=acc/o.n}
   quad(o.x,o.y,r+2,r,inner,0,RING_A*al,q,C0);
   if(!small) texts.push([o.x,o.y+.5,fmtN(o.n),Math.max(9,Math.min(13,inner*.8)),al]);
   if(o.np){
    // проблема — лише обвідка кільця чорнилом, без ромба й числа проблем;
    // на огляді міста тонша (0,6 / 0,9 / 1,2 px)
    const rr=r+3, th=z<11.5?.3:z<12.5?.45:.6;
    quad(o.x,o.y,rr+1.5,rr+th,rr-th,3,al,Q1,ink)}
  }
  if(addrDiamonds){
   const b=map.getBounds(), pad=.1*(b.getNorth()-b.getSouth());
   for(const k of PROBK){const pi=LEAF[k], la=P[pi][0], lo=P[pi][1], v=LEAFV[k];
    if(lo<b.getWest()-pad||lo>b.getEast()+pad||la<b.getSouth()-pad||la>b.getNorth()+pad) continue;
    const q_=map.project([lo,la]);
    // Сталий розмір: на тисячах крапок великі ромби різали очі й закривали
    // сусідів. Колір — той самий, що в крапки-проблеми під ним.
    later.push(()=>diamond(q_.x,q_.y,5.5,1,rgb(PALA[v.pt%PALA.length])))}
  }
  for(const f of later) f();
  // ---- літери чисел ----
  const glyphs=(list)=>{ if(!ATLAS) return;
   const A=ATLAS, tw=A.canvas.width, th=A.canvas.height;
   let chars=0; for(const t_ of list) chars+=t_[2].length;
   if(txtBuf.length<(nt+chars)*6*TXT_F) {const nb=new Float32Array((nt+chars)*6*TXT_F*2); nb.set(txtBuf.subarray(0,nt*TXT_F)); txtBuf=nb}
   for(const [cx0,y,s,fs,al] of list){const k=fs/ATL_PX;
    const cw=A.cw*k, ch=A.ch*k, adv=A.adv*k; let x=cx0-adv*s.length/2+adv/2;
    for(const c of s){const gi=GLYPHS.indexOf(c); if(gi<0){x+=adv;continue}
     const u0=gi*A.cw/tw, u1=(gi+1)*A.cw/tw, v0=0, v1=A.ch/th;
     const x0=x-cw/2, x1=x+cw/2, y0=y-ch/2, y1=y+ch/2;
     for(const [px,py,u,v] of [[x0,y0,u0,v0],[x1,y0,u1,v0],[x1,y1,u1,v1],[x0,y0,u0,v0],[x1,y1,u1,v1],[x0,y1,u0,v1]]){
      const b=nt*TXT_F; txtBuf[b]=px; txtBuf[b+1]=py; txtBuf[b+2]=u; txtBuf[b+3]=v; txtBuf[b+4]=al; nt++}
     x+=adv}}};
  glyphs(texts); const ntRing=nt; glyphs(ptexts);
  // ---- стан GL ----
  // MapLibre після власного шару сам відновлює свій стан (setDirty), але
  // масиви вершин прив'язані до його VAO — тож свій малюємо на порожньому.
  if(gl.bindVertexArray) gl.bindVertexArray(null); else if(this.vao) this.vao.bindVertexArrayOES(null);
  gl.disable(gl.DEPTH_TEST); gl.disable(gl.STENCIL_TEST); gl.disable(gl.CULL_FACE);
  gl.enable(gl.BLEND); gl.blendFunc(gl.ONE,gl.ONE_MINUS_SRC_ALPHA);
  const bind=(p,buf,data,n,F,attrs)=>{gl.useProgram(p); gl.bindBuffer(gl.ARRAY_BUFFER,buf);
   gl.bufferData(gl.ARRAY_BUFFER,data.subarray(0,n*F),gl.STREAM_DRAW);
   const locs=[]; let off=0;
   for(const [name,size] of attrs){const l=gl.getAttribLocation(p,name);
    if(l>=0){gl.enableVertexAttribArray(l); gl.vertexAttribPointer(l,size,gl.FLOAT,false,F*4,off*4); locs.push(l)}
    off+=size}
   gl.uniform2f(gl.getUniformLocation(p,'u_view'),W,H); return locs};
  const unbind=locs=>locs.forEach(l=>gl.disableVertexAttribArray(l));
  if(nd){const locs=bind(this.pd,this.bd,discBuf,nd,DISC_F,[['a_c',2],['a_o',2],['a_m',4],['a_q0',4],['a_q1',4],['a_col',3]]);
   gl.uniform3fv(gl.getUniformLocation(this.pd,'u_col'),new Float32Array(PALA.slice(0,7).flatMap(rgb)));
   gl.uniform3fv(gl.getUniformLocation(this.pd,'u_halo'),rgb(HALO_C));
   gl.uniform3fv(gl.getUniformLocation(this.pd,'u_ink'),ink);
   gl.drawArrays(gl.TRIANGLES,0,nd); unbind(locs)}
  if(nt){gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D,this.tex);
   if(this.texVer!==ATLAS_VER){gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL,false);
    gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,ATLAS.canvas);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
    this.texVer=ATLAS_VER}
   const locs=bind(this.pt,this.bt,txtBuf,nt,TXT_F,[['a_p',2],['a_uv',2],['a_a',1]]);
   gl.uniform1i(gl.getUniformLocation(this.pt,'u_tex'),0);
   const uInk=gl.getUniformLocation(this.pt,'u_ink'), uHalo=gl.getUniformLocation(this.pt,'u_halo'), uHa=gl.getUniformLocation(this.pt,'u_ha');
   // Числа на кільцях — чорнилом з гало кольору підкладки.
   gl.uniform3fv(uInk,ink); gl.uniform3fv(uHalo,rgb(HALO_C)); gl.uniform1f(uHa,1);
   if(ntRing) gl.drawArrays(gl.TRIANGLES,0,ntRing);
   // Число на ромбі — біле з темною обвідкою: читається на будь-якому кольорі виду.
   if(nt>ntRing){gl.uniform3fv(uInk,[1,1,1]); gl.uniform3fv(uHalo,[0,0,0]); gl.uniform1f(uHa,.6);
    gl.drawArrays(gl.TRIANGLES,ntRing,nt-ntRing)}
   unbind(locs)}
 }};
// Шар кілець — найвищий з наших: над адресами. Власний шар не переживає
// setStyle (його не можна описати в стилі), тож додаємо після кожного стилю.
// Значки «Що поруч» — над кільцями, як маркери Leaflet над полотном: після
// зміни стилю кільця стають під них, а не на самий верх.
// Кільця — над підписами підкладки й районів (33, В4: «Київ» лежав на кільці),
// але під номерами «Що поруч»: шар іде одразу після останнього шару підписів.
function ringsReady(){ if(map.getLayer('k-rings')) return;
 const L=map.getStyle().layers; let last=-1;
 L.forEach((l,i)=>{ if(l.type==='symbol'&&!l.id.startsWith('k-near')) last=i});
 const nxt=L.slice(last+1).find(l=>l.id.startsWith('k-near'));
 map.addLayer(ringLayer,nxt?nxt.id:undefined) }
// Видимість шару адрес — після кадру, а не всередині шару: міняти стиль
// посеред малювання не можна. Мірило — чи малював цей кадр кільця
// (RINGS_ON з frameList), а не поріг зуму: так між кільцями й адресами
// немає проміжку, коли не видно ні тих, ні тих.
map.on('render',()=>{ if(!STYLE_OK) return;
 addrLayerVisible(MODE!=='rings'||!RINGS_ON)});
// Кінець руху — ще один кадр: після зуму перетікання має стати на рівень.
map.on('moveend',()=>requestAnimationFrame(()=>map.triggerRepaint()));
// Клік: кільце — переліт до його адрес, не глибше ніж на 2,5 кроку зуму від
// поточного (розд. 23, п. 6); крапка — вікно адреси, як у шарі GL.
function hitRing(pt){let best=null, bd=1e9; const z=map.getZoom();
 for(const o of VIS){const r=o.dot?Math.max(6,LEAFV[o.k]?LEAFV[o.k].r0*zmulAt(z)+3:6):rRing(o.n,o.i)+3;
  const d=Math.hypot(o.x-pt.x,o.y-pt.y); if(d<=r&&d<bd){bd=d;best=o}}
 return best}
map.on('click',e=>{
 if(!RINGS_ON||iconAt(e.point)) return;
 const o=hitRing(e.point); if(!o) return;
 CLICK_TAKEN=true;
 if(o.dot) return openAt(LEAF[o.k]);
 // Кільце картки не має (рішення Андрія 06.10): клік наближує, кільце
 // розпадається на дрібніші, потім на адреси; вікно попереднього місця
 // зайве там, куди летимо.
 if(POPUP) POPUP.remove();
 const q=o.j*4, bb=BB[o.i], z=map.getZoom();
 const side=$('#side'), W=map.getContainer().clientWidth;
 const right=side&&side.offsetWidth&&W>700?side.offsetWidth+40:40;
 let cam=null;
 try{cam=map.cameraForBounds([[bb[q],bb[q+1]],[bb[q+2],bb[q+3]]],
   {padding:{top:40,bottom:40,left:40,right},maxZoom:Math.min(18,z+2.5)})}catch(err){}
 if(!cam||!cam.center) cam={center:[o.lon,o.lat],zoom:z+1.5};
 map.flyTo({center:cam.center,zoom:Math.min(z+2.5,Math.max(cam.zoom,z+.6)),duration:1400,curve:1.3,essential:true});
});
map.on('mousemove',e=>{ if(!RINGS_ON) return;
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
  walk(o.i,o.j); return {na_kilci:o.n, suma_adres:s, adres:a, lon:o.lon, lat:o.lat}})};
// ---- ШАРИ ПІД ПОДІЯМИ: СХОЖІ УМОВИ, ПОТОКИ, НАСЕЛЕННЯ, ТЕПЛОВА ----
// Видимість шару міняємо лише тоді, коли вона справді змінилася.
function layerVis(id,v){ if(!map.getLayer(id)) return;
 const want=v?'visible':'none'; if(map.getLayoutProperty(id,'visibility')!==want) map.setLayoutProperty(id,'visibility',want)}
// Лінія в координатах MapLibre і завжди в одному напрямку (захід -> схід).
// line-offset відкладається від напрямку лінії: той самий відрізок,
// записаний у двох видах навспак, поклав би обидві смуги на один бік — і
// вони б перекрилися. Тож напрямок вирівнюємо самі.
const lineLL=pts=>{const c=pts.map(q=>[q[1],q[0]]), a=c[0], b=c[c.length-1];
 return (a[0]>b[0]||(a[0]===b[0]&&a[1]>b[1]))?c.reverse():c};
// «Схожі умови» (розд. 23, п. 8) — нинішній шар моделі під новою назвою:
// карта показує, де середовище схоже на місця з подіями, а не передбачає
// їх (VYZNACHENNYA-PROBLEMY, 7.2 і 9). Мало б іти модель лише середовища
// (pB), але в нинішньому risk.json вулиці впорядковано моделлю «разом»
// (pC, середовище + історія подій; step4_engine, зміна 7 вересня), а pB є
// лише в переліку «тихих вулиць». Лишаємо pC до перенавчання (Б1).
//
// Окремий шар line на кожен вид зі сталим зсувом: вид завжди на своєму
// місці довкола осі вулиці, симетрично, тож смуги лежать поруч і не
// перекриваються, хоч скільки видів увімкнено. Крок ~2,5 px на міському
// огляді й більший зблизька, товщина трохи менша за крок — між смугами
// лишається просвіт.
// Паралельних смуг видів більше немає (ZAVDANNYA-32, 7.10): ризик — одна
// лінія одного кольору (tpl_vyhlyady). SIMK лишається порожнім.
const SIMK=[];
// Під перемикачем шару нічого не пишемо (RISHENNYA 34.5): позначка
// проактивності й «даних замало» — лише на сторінці «Схожі умови» й у методиці.
const SIM_STEP=[[10,2.2],[13,2.5],[15,3.5],[17,5.5],[19,8]];
const zStep=f=>['interpolate',['linear'],['zoom'],...SIM_STEP.flatMap(([z,s])=>[z,f(s)])];
const simOff=k=>zStep(s=>(k-(SIMK.length-1)/2)*s);
// Прохідність (RISHENNYA 34.1, 35.2): одна лінія кольору чорнила, товщина ∝
// √потоку. Колір подій їй не дістається: інакше потік читався б як ще один
// вид правопорушень. Чотирьох потоків (школи, транспорт, торгівля, разом)
// більше немає.
const FLOWS=[['potik',0,'🚶']].filter(f=>R.lines&&R.lines[f[0]]);
const fc=features=>({type:'FeatureCollection',features});
const lineF=(pts,props)=>({type:'Feature',geometry:{type:'LineString',coordinates:lineLL(pts)},properties:props});
// Значки потоків — картинками (addImage), а не текстом-емодзі в шарі
// symbol: емодзі сервер гліфів MapLibre не малює. addImage не переживає
// setStyle, тож картинки — після кожного стилю, у кольорах теми.
function flowImages(){
 const d=Math.max(1,Math.min(2,devicePixelRatio||1)), s=Math.round(22*d);
 for(const [k,,ch] of FLOWS){const id='k-ic-'+k; if(map.hasImage(id)) map.removeImage(id);
  const c=document.createElement('canvas'); c.width=c.height=s; const g=c.getContext('2d');
  g.fillStyle=cssv('--panel')||'#fff'; g.strokeStyle=cssv('--ink')||'#111'; g.lineWidth=1.2*d;
  g.beginPath(); g.arc(s/2,s/2,s/2-1.5*d,0,2*Math.PI); g.fill(); g.stroke();
  g.font=`${Math.round(12*d)}px "Segoe UI Emoji","Apple Color Emoji","Noto Color Emoji",sans-serif`;
  g.textAlign='center'; g.textBaseline='middle'; g.fillText(ch,s/2,s/2+.5*d);
  map.addImage(id,g.getImageData(0,0,s,s),{pixelRatio:d})}
}
// Скільки найбільших відрізків кожного потоку отримують значок. Решту
// значків, що налізли б на сусідні, прибирає сама карта (без накладання).
const FLOW_ICONS=80;
let CTX_EVENTS=false;
function ctxReady(){
 flowImages();
 if(map.getSource('k-pop')) return;   // джерела й шари пережили setStyle (carry)
 const before=map.getLayer('k-addr-shadow')?'k-addr-shadow':undefined;
 const add=(l)=>map.addLayer({...l,layout:{...(l.layout||{}),visibility:'none'}},before);
 // Населення — найнижче, під усім: це тло, а не сигнал.
 const pmx=Math.max(1,...POP.map(p=>p[2]));
 map.addSource('k-pop',{type:'geojson',data:fc(POP.map(p=>({type:'Feature',
  geometry:{type:'Point',coordinates:[p[1],p[0]]},properties:{n:p[2],s:Math.sqrt(p[2]/pmx)}})))});
 add({id:'k-pop',type:'circle',source:'k-pop',
  paint:{'circle-radius':['+',5,['*',16,['get','s']]],'circle-color':'#4b6fa8',
   'circle-opacity':['+',.10,['*',.28,['get','s']]]}});
 for(const [k,off] of FLOWS){const v=R.lines[k], mx=Math.max(1,...v.items.map(x=>x[2]));
  map.addSource('k-flow-'+k,{type:'geojson',data:fc(v.items.map((it,i)=>lineF(it[0],{i,s:Math.sqrt(it[2]/mx)})))});
  add({id:'k-flow-'+k,type:'line',source:'k-flow-'+k,layout:{'line-cap':'round'},
   paint:{'line-offset':off,'line-width':['+',.8,['*',3.2,['get','s']]],
    'line-opacity':['max',.10,['*',.42,['get','s']]]}});
 }
 SIMK.forEach((gi,k)=>{const v=R.lines[RISKOF[gi]];
  map.addSource('k-sim-'+gi,{type:'geojson',data:fc(
   v.items.map((it,i)=>lineF(it[0],{i,q:0,rk:it[2]})))});
 });
 // Спершу світлі підкладки всіх видів, потім самі смуги: підкладка
 // сусіднього виду не лягає поверх смуги (на строкатій підкладці тонка
 // лінія інакше губиться серед вулиць — узято з tpl_map).
 SIMK.forEach((gi,k)=>add({id:'k-simh-'+gi,type:'line',source:'k-sim-'+gi,filter:['==',['get','q'],0],
  layout:{'line-cap':'round'},paint:{'line-offset':simOff(k),'line-width':zStep(s=>s+2),'line-opacity':.5}}));
 SIMK.forEach((gi,k)=>{
  add({id:'k-sim-'+gi,type:'line',source:'k-sim-'+gi,filter:['==',['get','q'],0],
   layout:{'line-cap':'round'},
   // Прозорість за рангом вулиці: верх переліку — насичено, хвіст — блідо.
   paint:{'line-offset':simOff(k),'line-width':zStep(s=>s*.85),
    'line-opacity':['max',.35,['*',.85,['/',['get','rk'],100]]]}});
  // Окремого шару «тихих вулиць» немає (RISHENNYA 33.2.1): шар один.
 });
 // Значки потоків — на найбільших відрізках, над лініями.
 map.addSource('k-flow-ic',{type:'geojson',data:fc(FLOWS.flatMap(([k])=>
  R.lines[k].items.slice().sort((a,b)=>b[2]-a[2]).slice(0,FLOW_ICONS).map(it=>{
   const c=lineLL(it[0]); return {type:'Feature',geometry:{type:'Point',coordinates:c[c.length>>1]},
    properties:{f:k,n:it[2]}}})))});
 add({id:'k-flow-ic',type:'symbol',source:'k-flow-ic',minzoom:11,
  layout:{'icon-image':['concat','k-ic-',['get','f']],'icon-allow-overlap':false,'icon-padding':4,
   'symbol-sort-key':['-',0,['get','n']]}});
 // Теплової на новій карті немає (розд. 23, п. 9): на міському огляді вона
 // була суцільною червоною плямою й нічого не розрізняла.
 if(!CTX_EVENTS){CTX_EVENTS=true; ctxEvents()}
}
const rOn=k=>{const x=document.querySelector(`[data-r="${k}"]`); return !!(x&&x.checked)};
function drawRisks(){
 if(!STYLE_OK||!map.getSource('k-pop')) return;
 const halo=cssv('--halo'), ink=cssv('--ink');
 let dim=false;
 SIMK.forEach(gi=>{const on=rOn(RISKOF[gi]); dim=dim||on;
  layerVis('k-simh-'+gi,on); layerVis('k-sim-'+gi,on);
  map.setPaintProperty('k-simh-'+gi,'line-color',halo);
  map.setPaintProperty('k-sim-'+gi,'line-color',PALA[gi%PALA.length])});
 const fOn=FLOWS.filter(([k])=>rOn(k)).map(([k])=>k);
 for(const [k] of FLOWS){layerVis('k-flow-'+k,fOn.includes(k)); map.setPaintProperty('k-flow-'+k,'line-color',ink)}
 map.setFilter('k-flow-ic',['in',['get','f'],['literal',fOn]]); layerVis('k-flow-ic',fOn.length>0);
 dim=dim||fOn.length>0;
 layerVis('k-pop',rOn('pop'));
 dim=dim||RISK_ON;
 RING_A=dim?RING_DIM:RING_OP;
 addrPaint(); if(typeof riskDraw==='function'&&map.getSource('k-risk')){riskDraw(); if(LASTST) drawHex(LASTST)}
 map.triggerRepaint();
}
// ---- РАЙОНИ: МЕЖІ, МАСКА, ПІДСВІТКА ----
// Те саме, що в tpl_map: на міському огляді — межі всіх районів пунктиром і
// ледь помітна заливка, під курсором район підсвічується; у районі — лише
// його межа суцільною лінією, решта міста під затемненням кольору підкладки.
// Входять і виходять з району в панелі (меню «Район») — клік по карті
// лишається за кільцями й адресами: у щільному центрі межу району однаково
// не влучити, її закривають позначки.
// Затемнення — багатокутник на весь світ з діркою-районом. У Leaflet рамку
// доводилося перебудовувати з кожним рухом (полотно обрізало великий
// багатокутник); MapLibre малює світовий багатокутник як є.
const WORLD=[[-180,-85],[180,-85],[180,85],[-180,85],[-180,-85]];
const ringLL=r=>{const c=r.map(q=>[q[1],q[0]]); const a=c[0], b=c[c.length-1];
 if(a[0]!==b[0]||a[1]!==b[1]) c.push(a); return c};
let DIST_HOVER=-1;
const DIST_TIP_Z=13;
function distReady(){
 if(!DN.length||M.only||map.getSource('k-dist')) return;
 const before=map.getLayer('k-pop')?'k-pop':(map.getLayer('k-addr-shadow')?'k-addr-shadow':undefined);
 map.addSource('k-dist',{type:'geojson',data:fc(DN.map((nm,i)=>({type:'Feature',id:i,
  geometry:{type:'Polygon',coordinates:[ringLL(DBORD[i])]},properties:{i}})))});
 map.addSource('k-mask',{type:'geojson',data:fc([])});
 map.addLayer({id:'k-mask',type:'fill',source:'k-mask',paint:{'fill-opacity':.78}},before);
 map.addLayer({id:'k-dist-fill',type:'fill',source:'k-dist',
  paint:{'fill-opacity':['case',['boolean',['feature-state','hover'],false],.13,.05]}},before);
 // Пунктир 7/5 px, як у Leaflet: у MapLibre довжини рисок — у товщинах лінії.
 map.addLayer({id:'k-dist-line',type:'line',source:'k-dist',
  // з z14 межа тоншає й блідне (ZAVDANNYA-31, 8.3): на рівні кварталу вона
  // перекривала вулиці й адреси
  paint:{'line-width':['interpolate',['linear'],['zoom'],13,1.8,14.5,.9],'line-dasharray':[7/1.8,5/1.8],
   'line-opacity':['interpolate',['linear'],['zoom'],13,['case',['boolean',['feature-state','hover'],false],.95,.85],
    14.5,['case',['boolean',['feature-state','hover'],false],.6,.4]]}},before);
 map.addLayer({id:'k-dist-sel',type:'line',source:'k-dist',filter:['==',['get','i'],-1],
  paint:{'line-width':1.8,'line-opacity':1}},before);
}
function paintScope(){
 if(!STYLE_OK||!map.getSource('k-dist')) return;
 const dim=cssv('--dim'), ground=cssv('--ground'), city=CURD<0;
 map.setPaintProperty('k-dist-fill','fill-color',dim);
 for(const id of ['k-dist-line','k-dist-sel']) map.setPaintProperty(id,'line-color',dim);
 map.setPaintProperty('k-mask','fill-color',ground);
 layerVis('k-dist-fill',city); layerVis('k-dist-line',city);
 map.setFilter('k-dist-sel',['==',['get','i'],CURD]);
 map.getSource('k-mask').setData(fc(city?[]:[{type:'Feature',properties:{},
  geometry:{type:'Polygon',coordinates:[WORLD,ringLL(DBORD[CURD])]}}]));
 if(!city) distHover(-1);
}
function distHover(i){
 if(i===DIST_HOVER) return;
 if(DIST_HOVER>=0) map.setFeatureState({source:'k-dist',id:DIST_HOVER},{hover:false});
 DIST_HOVER=i;
 if(i>=0) map.setFeatureState({source:'k-dist',id:i},{hover:true});
}
// ---- «ЩО ПОРУЧ» ----
// Те саме, що в tpl_map. Об'єкт на карті — номер у кружечку з жовтою
// обвідкою, як коло радіуса; вид об'єкта — значком у переліку картки місця.
// Не кольором виду подій: заливка кольором ролі збігалася з Порядком і
// Майном, і об'єкт читався як ще одна подія.
const NEAR_C='#fbbf24';
// Шару «Об'єкти довкола» на новій карті немає (розд. 25, А; AUDYT-3): об'єкти —
// лише довкола конкретного місця, у вкладці «Що поруч». Ім'я лишається, бо
// спільна панель (tpl_core) кличе drawFacts.
function drawFacts(){}
function nearReady(){
 if(!(F.cats||[]).length) return;
 if(map.getSource('k-near')) return;
 // «Що поруч»: коло радіуса пунктиром, центр і значки об'єктів у колі.
 map.addSource('k-near',{type:'geojson',data:fc([])});
 map.addLayer({id:'k-near-ring',type:'line',source:'k-near',filter:['==',['geometry-type'],'LineString'],
  paint:{'line-color':NEAR_C,'line-width':1,'line-opacity':.45,'line-dasharray':[4,4]}});
 map.addLayer({id:'k-near-c',type:'circle',source:'k-near',filter:['==',['get','t'],'c'],
  paint:{'circle-radius':5,'circle-color':NEAR_C,'circle-stroke-color':NEAR_C,'circle-stroke-width':2}});
 // Об'єкти — кружечок із номером, як у переліку картки місця (розд. 30):
 // так рядок «7. Аптека — 64 м» знаходиться на карті одним поглядом.
 // Підсвічений (наведення чи клік у переліку або на карті) — більший і з
 // обвідкою чорнила.
 const hl=['boolean',['feature-state','hl'],false];
 map.addLayer({id:'k-near-num',type:'circle',source:'k-near',filter:['==',['get','t'],'o'],
  paint:{'circle-radius':['case',hl,12,9],'circle-color':cssv('--panel')||'#fff',
   'circle-stroke-color':['case',hl,cssv('--ink')||'#111',NEAR_C],'circle-stroke-width':['case',hl,3,2]}});
 if(BASEFONT) map.addLayer({id:'k-near-lbl',type:'symbol',source:'k-near',filter:['==',['get','t'],'o'],
  layout:{'text-field':['to-string',['get','n']],'text-font':BASEFONT,'text-size':10.5,
   'text-allow-overlap':true,'text-ignore-placement':true},
  paint:{'text-color':cssv('--ink')||'#111'}});
}
// Кольори кружечків — з теми (шари переходять у новий стиль як є).
function nearPaint(){ if(!map.getLayer('k-near-num')) return;
 const hl=['boolean',['feature-state','hl'],false];
 map.setPaintProperty('k-near-num','circle-color',cssv('--panel'));
 map.setPaintProperty('k-near-num','circle-stroke-color',['case',hl,cssv('--ink'),NEAR_C]);
 if(map.getLayer('k-near-lbl')) map.setPaintProperty('k-near-lbl','text-color',cssv('--ink'))}
// Коло радіуса r метрів довкола точки — лінією, 64 вершини.
function circleLL(la,lo,r){const dy=r/111320, dx=r/(111320*Math.cos(la*Math.PI/180)), c=[];
 for(let k=0;k<=64;k++){const a=k/64*2*Math.PI; c.push([lo+dx*Math.cos(a),la+dy*Math.sin(a)])}
 return {type:'Feature',geometry:{type:'LineString',coordinates:c},properties:{t:'r'}}}
// Об'єкти нумеруються від найближчого — так само, як перелік у картці.
function nearShow(la,lo,objs,rads){
 if(!map.getSource('k-near')) return 0;
 objs.sort((a,b)=>a.properties.d-b.properties.d).forEach((o,j)=>{o.id=j+1; o.properties.n=j+1});
 map.getSource('k-near').setData(fc([...rads].map(r=>circleLL(la,lo,r)).concat(
  [{type:'Feature',geometry:{type:'Point',coordinates:[lo,la]},properties:{t:'c'}}],objs)));
 return objs.length;
}
const nearObj=(c,p,d)=>({type:'Feature',geometry:{type:'Point',coordinates:[p[1],p[0]]},
 properties:{t:'o',k:c.k,d:Math.round(d),s:`${c.n} — ${Math.round(d)} м`}});
// Перелік картки місця — на карту тими самими номерами.
function nearNumbered(p,list){
 nearShow(p[0],p[1],list.map(o=>nearObj(o.c,o.q,o.d)),[NEAR_MAX]);
 if(PLACE&&PLACE.hl) map.setFeatureState({source:'k-near',id:PLACE.hl},{hl:true});
}
// Підсвічує об'єкти, які модель порахувала для конкретної точки, з колами
// радіусів (як showNear у tpl_map).
function showNear(la,lo,factors){
 clearNear(true);
 if(!(F.cats||[]).length||!factors||!factors.length) return 0;
 const need={};
 factors.forEach(f=>String(f[0]).split(' × ').forEach(part=>{
  const m=part.match(/^(.+)_(\d+)м$/);
  if(m) need[m[1]]=Math.max(need[m[1]]||0,+m[2]);
 }));
 const my=111320, mx=111320*Math.cos(la*Math.PI/180), rads=new Set(), objs=[];
 Object.keys(need).forEach(base=>{
  const c=F.cats.find(x=>x.b===base); if(!c) return;
  const rad=need[base]; rads.add(rad);
  c.pts.forEach(p=>{const d=Math.hypot((p[0]-la)*my,(p[1]-lo)*mx); if(d<=rad) objs.push(nearObj(c,p,d))});
 });
 return nearShow(la,lo,objs,rads);
}
// Те саме, але БЕЗ підказки моделі: усе, що є довкола в заданому радіусі.
// Для слухачів — це спостереження, а не готова відповідь: які саме з цих
// об'єктів пояснюють скупчення, вони мають визначити самі.
function showAllNear(la,lo,rad){
 clearNear(true);
 if(!(F.cats||[]).length) return 0;
 const my=111320, mx=111320*Math.cos(la*Math.PI/180), objs=[];
 F.cats.forEach(c=>c.pts.forEach(p=>{const d=Math.hypot((p[0]-la)*my,(p[1]-lo)*mx);
  if(d<=rad) objs.push(nearObj(c,p,d))}));
 return nearShow(la,lo,objs,[rad]);
}
// keepBtn — лише прибрати підсвітку, не скидаючи кнопку: tpl_core спершу
// кличе clearNear, потім showAllNear і лише тоді запам'ятовує кнопку.
function clearNear(keepBtn){
 if(map.getSource('k-near')) map.getSource('k-near').setData(fc([]));
 if(keepBtn===true) return;
 if(nearButton) nearButton.setAttribute('aria-pressed','false');
 nearButton=null;
}
// Значок «Що поруч» під курсором — він лежить над кільцями, тож клік по
// ньому не має летіти в кільце чи відкривати адресу.
function iconAt(p){ if(!map.getLayer('k-near-num')) return null;
 return map.queryRenderedFeatures([[p.x-3,p.y-3],[p.x+3,p.y+3]],{layers:['k-near-num']})[0]||null}
const iconTip=f=>`<b>${f.properties.n}. ${esc(f.properties.s)}</b>`;
// ---- ПІДКАЗКИ Й ВІКНО ВУЛИЦІ ----
// Скільки разів — з правильним відмінком (той самий raz, що в tpl_map).
function raz(n){
 const v=Math.round(n*10)/10, t=String(v).replace('.',',');
 if(!Number.isInteger(v)) return t+' раза';
 const a=v%10, b=v%100;
 if(a===1&&b!==11) return t+' раз';
 if(a>=2&&a<=4&&(b<12||b>14)) return t+' рази';
 return t+' разів';
}
const nfmt=n=>(Math.round(n*10)/10).toLocaleString('uk');
// Чинники САМЕ ЦІЄЇ вулиці — як factRows у tpl_map. Кожен рядок — виміряна
// річ, яку можна перевірити на місці. Слова «причина» тут немає навмисно.
function factRows(fx){
 if(!fx||!fx.length) return '';
 const rows=fx.map(f=>{
  const [label,val,med,ratio,isCount]=f;
  const cmp=(med===null||med===undefined) ? ''
    : (isCount&&!med) ? ' <i>на більшості вулиць — жодного</i>'
    // «звичайно 0» читалося як «так і має бути» (розд. 25, А8)
    : ` <i>у середньому по місту ${nfmt(med)}</i>`;
  const r='';   // кратність — у звіті «Схожі умови», не реченням на карті (RISHENNYA 34.5)
  return `<tr><td>${label}${r}</td><td class="fv"><b>${nfmt(val)}</b>${cmp}</td></tr>`;
 }).join('');
 return `<div class="rwhy">Що виміряно на цьому відрізку</div><table class="fx">${rows}</table>`;
}
// Рядок про вулицю — спільний для підказки й вікна. Місце вулиці — серед
// усіх відрізків міста (розд. 25, А8). «Верхні 97%» було місцем у переліку
// з 200 вулиць, а читалося як «гірша за 97% міста», тобто навпаки. Доки
// двигун не записав, скільки відрізків оцінював (nseg, з перенавчанням Б1),
// кажемо чесно: місце в переліку.
const pctUA=x=>(x<1?(Math.ceil(x*10)/10):Math.ceil(x)).toLocaleString('uk');
function simPlace(v,i){
 return v.nseg?`серед ${pctUA(100*(i+1)/v.nseg)}% вулиць міста з найсхожішими умовами`
  :`місце ${i+1} із ${v.items.length} вулиць міста з найсхожішими умовами`}
// Звідки ризик (ZAVDANNYA-30, 3.5): «Тут уже були події: N за 2 роки»
// і/або «Умови як біля подій: …». Слова «причина» немає: модель міряє, що
// поруч, а не через що.
function simWhence(v,it){
 const n=it[3]|0, fx=(it[4]||[]).map(f=>f[0]), out=[];
 if(n>0) out.push(`Тут уже були події: ${n} за 2 роки`);
 if(fx.length) out.push(`Умови як біля подій: ${fx.join(', ')}`);
 if(!out.length) out.push('Подій тут за 2 роки не було');
 return out}
function simLine(v,it,quiet,i){
 if(v.n2) return v.title+' — '+simPlace(v,i);
 return v.title+' — '+simPlace(v,i)+((it[3]|0)>0?`, подій уже було: ${it[3]}`:', подій ще не було')}
function simItem(f){const gi=+f.layer.id.split('-').pop(), v=R.lines[RISKOF[gi]], i=f.properties.i;
 return {v,q:false,i,it:v.items[i]}}
function simPopup(f,ll){
 const {v,q,i,it}=simItem(f);
 let h=`<div class="rpop"><b>${esc(it[1])}</b><span class="sub">${esc(simLine(v,it,q,i))}</span>`;
 if(v.n2) h+=simWhence(v,it).map(t=>`<div class="rmeth">${esc(t)}</div>`).join('');
 // Чинники цієї вулиці — головне у вікні, тому стоять першими, до методики.
 h+=factRows(it[4]);
 if(!v.n2&&!(it[4]&&it[4].length))
  h+='';
 // звичайним текстом, не класом rwhy: той набраний великими, як заголовок
 // позначка проактивності — лише в звіті й методиці (RISHENNYA 34.5)
 // Про модель — один рядок і посилання на звіт (розд. 25, А8): абзац методики
 // у вікні вулиці ніхто не читав, а головне в ньому — чинники — уже вище.
 // Посилання — на розбір вулиці у звіті «Схожі умови» (?st= підсвічує її рядок).
 const an=v.slug?('#t-'+v.slug):'';
 // Речення «оцінка за умовами довкола…» перенесено в методику (29.09):
 // карта без пояснювальних текстів, лише посилання.
 h+=`<div class="rmeth"><a class="rdoc" style="display:inline;margin:0" href="skhozhi-umovy.html${(it[1]&&it[1]!=='без назви')?('?st='+encodeURIComponent(it[1])):''}${an}" target="_blank" rel="noopener">Як пораховано ↗</a></div></div>`;
 advOpen(false);
 const w=document.createElement('div'); w.innerHTML=h;
 // Чинники моделі поруч — якщо модель їх назвала; інакше просто все, що є
 // в 250 м (як bindRisk у tpl_map).
 if((F.cats||[]).length){
  const bt=document.createElement('button'); bt.className='pbtn2'; w.appendChild(bt);
  if(v.factors&&v.factors.length){bt.textContent='Показати чинники поруч';
   bt.onclick=()=>{const n=showNear(ll.lat,ll.lng,v.factors);
    bt.textContent=n?`Підсвічено об’єктів: ${n}`:'Поруч нічого з чинників немає'}}
  else {bt.textContent='Що поруч (250 м)';
   bt.onclick=()=>{const n=showAllNear(ll.lat,ll.lng,250);
    bt.textContent=n?`Показано об’єктів: ${n}`:'Поруч нічого не знайдено'}}
 }
 if(POPUP) POPUP.remove();
 clearNear();
 POPUP=new maplibregl.Popup({maxWidth:'320px',anchor:'bottom',focusAfterOpen:false,closeOnClick:false}).setLngLat(ll).setDOMContent(w).addTo(map);
 POPUP.on('close',()=>clearNear());
 keepClear(POPUP,[ll.lng,ll.lat],0);
}
const simIds=()=>SIMK.map(gi=>'k-sim-'+gi).filter(id=>map.getLayer(id)&&map.getLayoutProperty(id,'visibility')==='visible');
function ctxEvents(){
 // Підказка при наведенні — як sticky tooltip у Leaflet.
 const TIP=new maplibregl.Popup({closeButton:false,closeOnClick:false,className:'k-tip',offset:14,maxWidth:'280px'});
 const tip=(e,h)=>{ if(!h){TIP.remove();return} TIP.setLngLat(e.lngLat).setHTML(h).addTo(map)};
 // Смуга тонка — ловимо її з запасом у кілька пікселів.
 const near=(p,ids)=>ids.length?map.queryRenderedFeatures([[p.x-4,p.y-4],[p.x+4,p.y+4]],{layers:ids}):[];
 const onEvent=p=>RINGS_ON?!!hitRing(p):!!addrAt(p);
 map.on('mousemove',e=>{
  const ic=iconAt(e.point);
  if(ic){ if(map.getSource('k-dist')) distHover(-1);
   // Наведення на номер підсвічує й рядок у картці місця (розд. 30).
   if(PLACE&&PLACE.tab==='near') nearHighlight(ic.properties.n,false);
   return tip(e,iconTip(ic))}
  if(onEvent(e.point)){ if(map.getSource('k-dist')) distHover(-1);
   // Кільце — що в ньому: «1 300 подій · 12 адрес · 2 проблеми» (розд. 25,
   // А6). Число в центрі кільця скорочене (1,3k), тут — повне.
   const o=RINGS_ON&&hitRing(e.point);
   if(o&&!o.dot){const a=ACT[o.i][o.j], np=NP[o.i][o.j];
    return tip(e,`<b>${fmt(o.n)} ${pl(o.n,'подія','події','подій')} · ${fmt(a)} ${pl(a,'адреса','адреси','адрес')}`+
     (np?` · ${np} ${pl(np,'проблема','проблеми','проблем')}`:'')+'</b>')}
   // Над точкою — лише коротка підказка: адреса й скільки подій (розд. 30);
   // усе інше — у картці місця за кліком.
   const ai=o&&o.dot?LEAF[o.k]:!RINGS_ON?(addrAt(e.point)||{properties:{}}).properties.i:undefined;
   const av=ai!==undefined&&LASTST&&LASTST.vis.find(x=>x[0]===P[ai]);
   if(av) tip(e,`<b>${esc(P[ai][2])}</b><span>${fmt(av[1])} ${pl(av[1],'подія','події','подій')}${probsOf(P[ai]).length?' · проблема':''}</span>`);
   else TIP.remove();
   // Над кільцем курсор ставить обробник кілець; над адресою — тут.
   if(!RINGS_ON) map.getCanvas().style.cursor='pointer'; return}
  const s=near(e.point,simIds())[0];
  if(s){const {v,q,i,it}=simItem(s); map.getCanvas().style.cursor='pointer';
   return tip(e,`<b>${esc(it[1])}</b><span>${esc(simLine(v,it,q,i))}. Клікніть для деталей</span>`)}
  const fl=near(e.point,FLOWS.map(([k])=>'k-flow-'+k).filter(id=>map.getLayoutProperty(id,'visibility')==='visible'))[0];
  if(fl){const k=fl.layer.id.slice(7), v=R.lines[k], it=v.items[fl.properties.i];
   return tip(e,`<b>${esc(it[1]||'без назви')}</b><span>≈ ${it[2].toLocaleString('uk')} осіб на добу (модель)</span>`)}
  const pp=map.getLayoutProperty('k-pop','visibility')==='visible'&&map.queryRenderedFeatures(e.point,{layers:['k-pop']})[0];
  if(pp) return tip(e,`<b>${pp.properties.n.toLocaleString('uk')} осіб</b>`);
  // Над сотою, стовпчиком чи ризиком своя підказка (tpl_vyhlyady) — район
  // тоді мовчить: дві підказки накладалися й закривали число соти (Андрій 07.10)
  // у стовпчиках підказки району немає зовсім — лише межа й підпис (33, В6)
  if(MODE==='stovp'||hexHit(e.point)||riskAt(e.point)){ if(map.getSource('k-dist')) distHover(-1); TIP.remove(); return}
  if(!RINGS_ON) map.getCanvas().style.cursor='';
  // Район під курсором — підсвітка й назва, лише на міському огляді (до
  // z13, розд. 25, А4): ближче вона спливала над кожною вулицею й заважала.
  const d=CURD<0&&map.getZoom()<DIST_TIP_Z&&map.getLayer('k-dist-fill')&&map.queryRenderedFeatures(e.point,{layers:['k-dist-fill']})[0];
  if(d){const i=d.properties.i, np=(M.dprob||[])[i]||0; distHover(i);
   return tip(e,`<b>${esc(DN[i])}</b>`+(np?`<span>${np} ${pl(np,'проблема','проблеми','проблем')}</span>`:''))}
  if(map.getSource('k-dist')) distHover(-1);
  tip(e,null);
 });
 map.on('mouseout',()=>{TIP.remove(); if(map.getSource('k-dist')) distHover(-1)});
 // Клік по смузі — вікно вулиці. Кільце чи адреса під курсором важливіші:
 // їхні власні обробники вже відкривають своє.
 map.on('click',e=>{
  // Значок — підказка й на дотик: на телефоні наведення немає.
  const ic=iconAt(e.point);
  if(ic){ if(PLACE&&PLACE.tab==='near') nearHighlight(ic.properties.n,true); return tip(e,iconTip(ic))}
  if(CLICK_TAKEN||onEvent(e.point)) return;
  const s=near(e.point,simIds())[0]; if(s){TIP.remove(); return simPopup(s,e.lngLat)}
  // Клік по порожній карті закриває все, що відкрито над нею, — і панель
  // рішень теж (AUDYT-3, № 5).
  if(POPUP) POPUP.remove(); advOpen(false); closePanel(); closePlace()});
}
// ---- ВИГЛЯД: «Кільця · Адреси · Проблеми» (розд. 23, п. 7 і 9) ----
// Замість «Події · Проблеми · Теплова» спільної панелі — лише в GL-збірці.
// «Проблеми» — самі ромби проблем, без подій, як колишній режим «Проблеми»
// (MODE 'prob' спільного computeVis). Теплову прибрано 26.09. Збережена в
// браузері «Теплова» відкривається як «Кільця».
// Вкладки «Соти · Стовпчики · Кільця · Адреси» й «◆ Проблеми» — у
// tpl_vyhlyady (RISHENNYA 35.9); тут лише кнопка.
$('#fcat').insertAdjacentHTML('afterend','<button id="fprob" class="pbtn2" aria-pressed="false" '+
  'style="width:auto;align-self:flex-start;margin:6px 0 0;padding:4px 10px">◆ Проблеми</button>');
// Пошук без збігів — так і кажемо (AUDYT-3, № 7): досі підказки просто
// зникали, і було незрозуміло, чи пошук узагалі спрацював. Обробник стоїть
// після спільного (tpl_core suggest), тож SUG уже пораховано.
qEl.addEventListener('input',()=>{ if(norm(qEl.value)&&!SUG.length){
 sg.innerHTML='<div class="sgnone">Такої адреси немає серед подій карти</div>'; sg.hidden=false}});
// Фільтр без жодної події (AUDYT-3, № 8): порожня карта без пояснення
// читалася як збій. Рядок над картою — лише що саме порожнє; порада «що
// змінити» була пояснювальним реченням (RISHENNYA 34.5).
{const e=document.createElement('div'); e.id='kempty'; e.hidden=true; map.getContainer().appendChild(e);}
// Елемент шукаємо за id, а не тримаємо в const: draw() може прийти раніше,
// ніж виконається рядок вище.
function emptyState(st){
 const EMPTY=document.getElementById('kempty'); if(!EMPTY) return;
 const none=!st.vis.length;
 EMPTY.hidden=!none; if(!none) return;
 EMPTY.textContent=MODE==='prob'
  ?'За поточним фільтром проблем немає'
  :CURD>=0?'У цьому районі за поточним фільтром подій немає'
  :'За поточним фільтром подій немає';
}
// На телефоні навігатор згорнутий до рядка пошуку й кнопки «Фільтри»
// (AUDYT-3, № 3): розгорнутий, він займав 55% екрана, і карті лишалося
// 322 px із 844. На широкому екрані кнопки не видно й нічого не згортається.
{const s=$('#side'), b=document.createElement('button');
 b.id='kfold'; b.type='button'; b.setAttribute('aria-expanded','false'); b.textContent='Фільтри ▾';
 s.insertBefore(b,s.querySelector('#fcat')); s.classList.add('kmin');
 b.onclick=()=>{const open=s.classList.toggle('kmin')===false;
  b.setAttribute('aria-expanded',String(open)); b.textContent=open?'Згорнути ▴':'Фільтри ▾'};}
// Перемикача «Об'єкти довкола» в панелі нової карти немає (розд. 23, п. 9):
// об'єкти — лише через «Що поруч» у вікні адреси. Розмітка панелі спільна з
// запасною картою, тож кнопку прибираємо тут.
{const b=document.querySelector('#fctx [data-ctx="facts"]'); if(b) b.remove();}
// ---- СМУГА ЧАСУ ЗЛІВА ВГОРІ (розд. 30; розд. 4 і 17) ----
// Час — те, чим гортають карту, а не ще один фільтр у картці: крок «Усі · Рік
// · Квартал · Місяць» і «‹ значення ›». Без випадних меню (рішення 28.09):
// крок видно весь одразу. Стрілки гортають обраним кроком, через межу року —
// самі; на краю даних стрілка неактивна; «Усі» ховає стрілки. При зміні
// кроку лишаємося в тому самому місці часу: якір CM — місяць, і кожен крок
// показує період, що його містить (вересень 2025 → III кв. 2025 → 2025).
// Фільтр — за місяцем події (PERF у tpl_core.evOn), тож діє однаково на
// кільця, адреси, проблеми й картку місця.
const MON_A0=(+M.mon0.slice(0,4))*12+(+M.mon0.slice(5,7))-1, MON_LAST=Math.max(0,(M.mon_n||1)-1);
const MISN=['січень','лютий','березень','квітень','травень','червень','липень','серпень','вересень','жовтень','листопад','грудень'];
const QN=['I','II','III','IV'];
let STEP='all', CM=MON_LAST, TOD=-1;
function perRange(){
 if(STEP==='all') return null;
 const A=MON_A0+CM, y=Math.floor(A/12), mo=A%12;
 let a=STEP==='year'?y*12-MON_A0:STEP==='quarter'?A-mo%3-MON_A0:CM;
 let b=STEP==='year'?a+11:STEP==='quarter'?a+2:CM;
 return [Math.max(0,a),Math.min(MON_LAST,b)]}
function perLabel(){
 const A=MON_A0+CM, y=Math.floor(A/12), mo=A%12;
 return STEP==='year'?String(y):STEP==='quarter'?`${QN[Math.floor(mo/3)]} кв. ${y}`:`${MISN[mo]} ${y}`}
function perSet(){PERF=perRange(); paintStrip(); draw()}
function perNav(d){const r=perRange(); if(!r) return;
 if(d<0&&r[0]>0) CM=r[0]-1; else if(d>0&&r[1]<MON_LAST) CM=r[1]+1; else return;
 perSet()}
const STEPS=[['all','Усі'],['year','Рік'],['quarter','Квартал'],['month','Місяць']];
// Час доби — маленька кнопка з меню; вибір пише в ті самі чипи #hr, з яких
// рахує hoursSel (tpl_core): одне джерело правди для карти й картки.
function todSet(i){TOD=i; document.querySelectorAll('#hr [data-p]').forEach(b=>swSet(b,i<0||+b.dataset.p===i)); paintStrip(); draw()}
const todName=()=>TOD<0?'уся доба':`${PERIODS[TOD][0]} ${PERIODS[TOD][1]}`;
function paintStrip(){const s=$('#kstrip'); if(!s) return;
 const r=perRange(), incomplete=r&&r[1]>=MON_LAST-1;
 s.querySelectorAll('[data-st]').forEach(b=>swSet(b,b.dataset.st===STEP));
 s.querySelector('.ks-per').hidden=STEP==='all';
 s.querySelector('[data-nav="-1"]').disabled=!r||r[0]<=0;
 s.querySelector('[data-nav="1"]').disabled=!r||r[1]>=MON_LAST;
 s.querySelector('.ks-val').innerHTML=r?`${perLabel()}${incomplete?'<small>неповний</small>':''}`:'';
 s.querySelector('.ks-val').classList.toggle('inc',!!incomplete);
 s.querySelector('.ks-tod').textContent='🕘 '+todName();
 const th=s.querySelector('.ks-theme'); th.textContent=THEME==='temna'?'☀':'☾';
 th.title=THEME==='temna'?'Світла тема':'Темна тема'; th.setAttribute('aria-label',th.title);
 s.querySelector('.ks-phone').textContent=(r?perLabel():'Усі роки')+' ▾'}
class StripCtl{
 onAdd(){const d=document.createElement('div'); d.id='kstrip'; d.className='kstrip maplibregl-ctrl';
  d.innerHTML=`<button class="ks-phone" aria-expanded="false"></button>
   <div class="ks-steps" role="group" aria-label="Крок періоду">${STEPS.map(([k,n])=>`<button data-st="${k}">${n}</button>`).join('')}</div>
   <span class="ks-per"><button data-nav="-1" aria-label="Попередній період">‹</button><span class="ks-val" aria-live="polite"></span><button data-nav="1" aria-label="Наступний період">›</button></span>
   <span class="ks-sep"></span><span class="ks-todw"><button class="ks-tod" aria-haspopup="menu" aria-expanded="false"></button>
   <div class="ks-menu" role="menu" hidden>${[[-1,'уся доба']].concat(PERIODS.map((p,i)=>[i,p[0]+' '+p[1]])).map(([i,n])=>`<button role="menuitem" data-tod="${i}">${n}</button>`).join('')}</div></span>
   <span class="ks-sep"></span><button class="ks-theme"></button>`;
  d.addEventListener('click',e=>{
   const st=e.target.closest('[data-st]'); if(st){STEP=st.dataset.st; perSet(); return}
   const nv=e.target.closest('[data-nav]'); if(nv){perNav(+nv.dataset.nav); return}
   const menu=d.querySelector('.ks-menu');
   if(e.target.closest('.ks-tod')){menu.hidden=!menu.hidden; d.querySelector('.ks-tod').setAttribute('aria-expanded',String(!menu.hidden)); return}
   const td=e.target.closest('[data-tod]'); if(td){menu.hidden=true; todSet(+td.dataset.tod); return}
   if(e.target.closest('.ks-theme')){setTheme(THEME==='temna'?'svitla':'temna'); return}
   if(e.target.closest('.ks-phone')){d.classList.toggle('open'); e.target.setAttribute('aria-expanded',String(d.classList.contains('open')))}});
  return d}
 onRemove(){}}
map.addControl(new StripCtl(),'top-left');
paintStrip();
// Меню часу доби закривається кліком повз нього й Esc.
document.addEventListener('click',e=>{ if(!e.target.closest('.ks-todw')){const m=document.querySelector('#kstrip .ks-menu'); if(m) m.hidden=true}});
// ← → гортають період, коли фокус на карті (розд. 30). Перехоплюємо раніше
// за MapLibre, який ними зсуває карту; на «Усі» стрілки лишаються за картою.
document.addEventListener('keydown',e=>{
 if(STEP==='all'||(e.key!=='ArrowLeft'&&e.key!=='ArrowRight')||e.altKey||e.ctrlKey||e.metaKey) return;
 if(!map.getContainer().contains(document.activeElement)||document.activeElement.closest('input,textarea,select')) return;
 e.preventDefault(); e.stopPropagation(); perNav(e.key==='ArrowLeft'?-1:1)},true);
// Перевірка з консолі: скільки адрес із проблемами й скільки самих проблем
// за поточним фільтром і районом — те, що карта показує ромбами.
window.kartaProblemy=()=>({adres:PROBK.length, problem:PROBK.reduce((s,k)=>s+LEAFV[k].np,0)});
// Колір адреси за назвою («Володимирська, 26») — перевірка палітр з консолі:
// яким кольором її намальовано і якого виду цей колір.
window.kartaAdresa=q=>{const i=P.findIndex(p=>(p[2]||'').includes(q)); if(i<0) return null;
 const v=(LASTST||computeVis()).vis.find(v=>v[0]===P[i]);
 return v?{adresa:P[i][2], kolir:PALA[v[2]%PALA.length], vyd:M.groups[v[2]][0], problema:!!v[3]}:{adresa:P[i][2], kolir:null}};
// Підписки на панель — ті самі, що в tpl_draw, без подій карти Leaflet.
document.querySelectorAll('#side input:not([data-r]):not([data-f]):not(#fquiet)').forEach(x=>x.addEventListener('change',draw));
document.querySelectorAll('[data-r]').forEach(x=>x.addEventListener('change',drawRisks));
{const fq=$('#fquiet'); if(fq) fq.addEventListener('change',drawRisks);}
document.querySelectorAll('[data-f]').forEach(x=>x.addEventListener('change',drawFacts));
map.on('zoomend',paintZoomGates);
paintRows();draw();drawRisks();drawFacts();paintZoomGates();
{const i=DSLUG.indexOf(decodeURIComponent(location.hash.slice(1)).toLowerCase());
 if(i>=0&&!M.only) enterDistrict(i,false); else {paintDistrictList(); fitCity(0)}}"""
