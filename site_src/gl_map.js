// Дерево кластерів для «Кілець» (TREE, файл tree — у tpl_base) рахується при
// збірці (map_clusters): без нього браузер не знає, хто чий нащадок, і
// розпад кільця при наближенні неможливий. Сум у дереві немає — їх складає
// браузер з адрес за фільтром.
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
// Запасна підкладка — растрові плитки OpenStreetMap, без ключа. Ключ CARTO
// прибрано разом із запасною картою (36.25.3): ключ у коді сторінки — секрет,
// який бачить кожен. Плитки OSM — лише на хвилини, поки OpenFreeMap лежить.
function osmStyle(){
 return {version:8,sources:{base:{type:'raster',tiles:['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
   tileSize:256,maxzoom:19}},layers:[{id:'base',type:'raster',source:'base'}]};
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
// Не прийшов за 8 секунд або прийшов з помилкою — растрові плитки OSM.
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
 setAttr('© OpenStreetMap');
 console.warn('Стиль OpenFreeMap недоступний, підкладка OSM');
 map.setStyle(osmStyle(),{transformStyle:(prev,next)=>carry(prev,next)});
}
const C0=M.center||[50.45,30.52];
const map=new maplibregl.Map({container:'map',center:[C0[1],C0[0]],zoom:M.only?13:11,
  maxZoom:19,attributionControl:false});
// Атрибуція — власним елементом, а не вбудованим. OpenFreeMap кладе свій рядок
// в опис джерела плиток, і стиль його не перебиває; а нам треба саме «OpenFreeMap
// © OpenMapTiles, дані © OpenStreetMap», і при запасній — рядок OSM.
const attrEl=document.createElement('div');
attrEl.className='maplibregl-ctrl maplibregl-ctrl-attrib';
// Рядок — з atrybutsiia.py (M.atr, S-К.20): той самий, що внизу звітів і в
// заголовку файлів адрес. Запасна підкладка — лише її рядок спереду.
// На телефоні рядок згорнутий до «ⓘ», як у MapLibre (36.26.1).
function setAttr(t){attrEl.innerHTML='<button class="k-atr-i" aria-label="Джерела даних" title="Джерела даних">ⓘ</button>'+
 '<div class="maplibregl-ctrl-attrib-inner">'+(t===OFM_ATTR?'':esc(t)+' · ')+(M.atr||'')+'</div>'}
attrEl.addEventListener('click',e=>{ if(e.target.closest('.k-atr-i')) attrEl.classList.toggle('k-atr-vidkr')});
map.addControl({onAdd:()=>attrEl,onRemove(){}},'bottom-right');
// Помилка до того, як стиль устиг завантажитися, — це відмова підкладки.
// Пізніші помилки (окремий тайл не прийшов) підкладку не міняють. Мірило —
// STYLE_OK (подія style.load), а не isStyleLoaded(): той хибний, доки
// вантажаться плитки, і один тайл, що не прийшов після зміни теми, перемикав
// усю карту на запасну підкладку.
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
let nearButton=null;