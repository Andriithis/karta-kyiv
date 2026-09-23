# -*- coding: utf-8 -*-
"""Малювання позначок подій на Leaflet.

Спільне — які адреси видно, якого кольору крапка і що написано у вікні —
лежить у tpl_core і входить в обидві збірки. Тут лише те, що знає про рушій:
кола, теплова карта, розмір позначки від масштабу й підписка на події карти.
Для MapLibre те саме робить tpl_gl.
"""
JS_DRAW = r"""// Радіус у Leaflet — у пікселях і від масштабу не залежить, тому на зумі 18
// одинична подія виходила пилинкою, у яку не влучиш пальцем. Множник підганяє
// позначку під масштаб: на міському огляді нічого не злипається, зблизька
// крапка впевнена.
const zoomMul=z=>z<=12?.78:z<=14?1:z<=16?1.35:1.7;
// Від цього зуму вмикається тінь під позначками (див. tpl_style).
const DEEP_Z=15;
let lastMul=null, zTimer=null;
function applyZoom(){
 const z=map.getZoom();
 map.getContainer().classList.toggle('deep',z>=DEEP_Z);
 // Перемальовуємо не на кожен зум, а лише коли множник справді змінився, та
 // ще й із затримкою: під час плавного зуму zoomend приходить чергою, і без
 // паузи одинадцять тисяч позначок перемальовувалися б по кілька разів.
 if(zoomMul(z)===lastMul) return;
 clearTimeout(zTimer); zTimer=setTimeout(draw,140);
}
function draw(){
 const st=computeVis(), vis=st.vis;
 heatOn=(MODE==='heat');
 // MK чистимо до виходу теплової: інакше пошук знаходив би позначку з
 // попереднього режиму, якої на карті вже немає, і вікно не відкривалося.
 MK.clear();
 layer.clearLayers();if(heat){map.removeLayer(heat);heat=null}
 if(heatOn){heat=L.heatLayer(vis.flatMap(v=>Array(Math.min(v[1],20)).fill([v[0][0],v[0][1],1])),
  {radius:18,blur:24,maxZoom:16}).addTo(map);return}
 const mx=vis.length?vis[0][1]:1;
 // Обвідка тепер світла (гало), а не темна: вона відділяє точку від підкладки,
 // не забруднюючи сам колір теми. Радіус із макета — удвічі менший за
 // колишній на максимумі, бо щільний центр колами зливався в суцільну пляму.
 const HALO=cssv('--halo'), zm=zoomMul(map.getZoom());
 lastMul=zm;
 for(const [p,n,th,byProblem,cnt,thMaj] of vis){
  const r=(Math.max(2.8,Math.min(14,2.8+9.5*Math.pow(n/Math.max(mx,1),.42))))*zm;
  MK.set(p,L.circleMarker([p[0],p[1]],{radius:r,weight:1.5,color:HALO,
   fillColor:PALA[th%PALA.length],fillOpacity:.94})
  .bindPopup(()=>popupHTML(p,n,th,byProblem,cnt,thMaj,st),POPOPT)
  .addTo(layer))}
}
const POPOPT={maxWidth:360,autoPanPaddingTopLeft:[14,14],autoPanPaddingBottomRight:[14,14]};
const MK=new Map();      // адреса -> її позначка в поточному перемальовуванні
// ---- ПОШУК: КУДИ НАБЛИЖАТИ ----
// Вікно відкриваємо, коли карта ВЖЕ стала на місце і позначки перемальовано
// під новий масштаб, — а не через 400 мс навмання. На повільному комп'ютері
// перемальовка займає понад секунду, і таймер відкривав вікно на позначці,
// яку за мить знімали.
function afterMove(go){
 map.once('moveend',()=>{clearTimeout(zTimer);draw();go()});
}
function openAt(i,ll){
 const p=P[i], m=MK.get(p);
 if(m) return m.openPopup();
 // Позначки немає: сховав фільтр, теплова карта або це вулиця без номера.
 const st=computeVis(), v=st.vis.find(x=>x[0]===p);
 const node=!p[3]?streetHTML(p,st):v?popupHTML(...v,st):hiddenHTML(p);
 L.popup(POPOPT).setLatLng(ll||[p[0],p[1]]).setContent(node).openOn(map);
}
function focusAddress(i){
 const p=P[i]; afterMove(()=>openAt(i)); map.setView([p[0],p[1]],17);
}
function focusStreet(i,pts){
 afterMove(()=>openAt(i,map.getCenter()));
 map.fitBounds(L.latLngBounds(pts),{padding:[40,40],maxZoom:17});
}
// Кнопок «Теплова карта», «Скинути фільтри», «Зняти всі» й «Обрати всі» більше
// немає: теплова стала режимом угорі, а решту робить сам перелік тем.
// #fquiet перемальовує ШАРИ РИЗИКУ, а не позначки подій — тому його треба
// і виключити із загального правила, і підписати окремо. Інакше прапорець
// ніби працює (draw() відпрацьовує), але пунктир не з'являється.
document.querySelectorAll('#side input:not([data-r]):not([data-f]):not(#fquiet)').forEach(x=>x.addEventListener('change',draw));
document.querySelectorAll('[data-r]').forEach(x=>x.addEventListener('change',drawRisks));
{const fq=$('#fquiet'); if(fq) fq.addEventListener('change',drawRisks);}
document.querySelectorAll('[data-f]').forEach(x=>x.addEventListener('change',drawFacts));
map.on('zoomend moveend',drawFacts);
map.on('zoomend',applyZoom);
map.on('zoomend',paintZoomGates);
{const fc=$('#fclear'); if(fc) fc.onclick=()=>hlayer.clearLayers();}
// Підсвітка «Що поруч» знімається кліком по вільному місці карти.
// Ловимо саме popupclose, а не click: клік по позначці в Leaflet теж
// доходить до карти, і по кліку підсвітка гасла б одразу після появи.
// Закриття вікна — це і є «користувач пішов з цього місця».
map.on('popupclose',()=>hlayer.clearLayers());
paintRows();draw();drawRisks();drawFacts();applyZoom();paintZoomGates();
// Посилання виду kyiv.html#desna відкриває одразу потрібний район:
// викладач може дати групі адресу конкретного району, а не «знайдіть самі».
{const i=DSLUG.indexOf(decodeURIComponent(location.hash.slice(1)).toLowerCase());
 if(i>=0&&!M.only) enterDistrict(i,false); else paintDistrictList();}"""
