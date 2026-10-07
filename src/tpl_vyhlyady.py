# -*- coding: utf-8 -*-
"""Чотири вигляди подій, проблема — контуром, ризик однією лінією, картка
соти (RISHENNYA 35.4а, 35.6, 35.9; ZAVDANNYA-32, ч. 7).

Іде в GL-збірку останнім, після JS_GL_DRAW: спирається на карту, P, PALA,
computeVis, картку місця (#kplace) і перемикачі панелі. Кільця малює
власний шар tpl_gl; тут — соти, стовпчики, крапки адрес і ризик.
"""
JS_VYHLYADY = r"""// ==== СОТИ Й СТОВПЧИКИ (35.6; макети «Соти і стовпчики», «Чотири вигляди») ====
// Сітка — у метрах, у локальній проєкції Києва; три розміри (рішення Андрія
// 06.10): 330 м до z12,3, 130 м z12,4–14,5, 30 м (≈ 50 м між краями) з z14,5.
// Соти й стовпчики лишаються сотами на всіх масштабах — у крапки адрес не
// переходять; крапки — вигляд «Адреси» (кнопка в картці соти).
const MX_=111320*Math.cos(50.45*Math.PI/180), MY_=111320;
const HEXG=[{id:'L',R:330},{id:'S',R:130},{id:'X',R:30}];
// колір ризику — один для всіх видів (7.10); контраст до підкладки й сот ≥ 3:1
const RISK_C={svitla:'#d42a2a',temna:'#ff6b6b'};
const isDark=()=>THEME==='temna';
function hexAt(la,lo,R){const w=Math.sqrt(3)*R,h=1.5*R,x=lo*MX_,y=la*MY_, r0=Math.round(y/h);
 let best=null,bd=1e30;
 for(let dr=-1;dr<=1;dr++){const row=r0+dr, c0=Math.round((x-(row&1)*w/2)/w);
  for(let dc=-1;dc<=1;dc++){const col=c0+dc, cx=col*w+(row&1)*w/2, cy=row*h, d=(cx-x)**2+(cy-y)**2;
   if(d<bd){bd=d;best=[row+':'+col,cx,cy]}}}
 return best}
function hexPoly(cx,cy,R,k=1){const out=[];
 for(let a=0;a<6;a++){const t=Math.PI/180*(60*a+30); out.push([(cx+k*R*Math.cos(t))/MX_,(cy+k*R*Math.sin(t))/MY_])}
 out.push(out[0]); return [out]}
let HEXB={L:new Map(),S:new Map()};   // ключ -> {n, g[], ad[], pr, cx, cy}
function binHex(st){
 const NG_=M.groups.length, cityG=new Array(NG_).fill(0); let cityN=0;
 for(const v of st.vis){ if(!v[0][3]) continue; for(const g in v[4]){cityG[g]+=v[4][g]; cityN+=v[4][g]}}
 for(const G of HEXG){const B=new Map();
  for(const v of st.vis){const p=v[0]; if(!p[3]) continue;
   const [k,cx,cy]=hexAt(p[0],p[1],G.R);
   let b=B.get(k); if(!b){b={n:0,g:new Array(NG_).fill(0),ad:[],pr:0,cx,cy,k}; B.set(k,b)}
   b.n+=v[1]; b.ad.push(PIDX.get(p)); for(const g in v[4]) b.g[g]+=v[4][g];
   if(probsOf(p).some(q=>q.thi===undefined||q.thi<0||st.GVIS.has(q.thi))) b.pr=1}
  // Колір — вид, якого тут БІЛЬШЕ, НІЖ У СЕРЕДНЬОМУ ПО МІСТУ (35.6): найбільше
  // (частка в соті) / (частка в місті) серед видів з ≥ max(3, 10% соти) подій —
  // щоб одна подія не фарбувала соту. Раніше ще й поріг 1,5 і запасний
  // «найчисленніший вид» — і майже все було зелене, ДТП (33, В2). Найчисленніший
  // лишився лише для соти, де жоден вид не набрав мінімуму.
  const bs=[...B.values()].sort((a,b)=>a.n-b.n), L_=bs.length;
  bs.forEach((b,i)=>{let gi=b.g.indexOf(Math.max(...b.g)), best=0;
   const min=Math.max(3,.1*b.n);
   for(let g=0;g<NG_;g++){ if(b.g[g]<min||!cityG[g]) continue;
    const r=(b.g[g]/b.n)/(cityG[g]/cityN); if(r>best){best=r; gi=g}}
   b.gi=gi; const rank=L_>1?i/(L_-1):1;
   b.a=isDark()?Math.min(.7,.12+.7*rank*rank):Math.min(.6,.05+.6*rank*rank);
   // контур проблеми на майже прозорій соті виглядав би порожнім
   if(b.pr) b.a=Math.max(b.a,.45);
   b.rank=rank});
  HEXB[G.id]=B}
}
function hexData(G,cols){
 const B=HEXB[G.id], mx=Math.max(1,...[...B.values()].map(b=>b.n));
 const ns=[...B.values()].map(b=>b.n).sort((a,b)=>a-b), med=ns.length?ns[ns.length>>1]:0;
 const dim=RISK_ON?.35:1;
 return {type:'FeatureCollection',features:[...B.values()].filter(b=>!cols||b.n>=med).map(b=>({type:'Feature',
  geometry:{type:'Polygon',coordinates:hexPoly(b.cx,b.cy,G.R,cols?.62:1)},
  // cl — світліший колір вибраного стовпчика, поки відкрита картка (33, В6)
  properties:{k:b.k,c:PALA[b.gi%PALA.length],cl:svitlishe(PALA[b.gi%PALA.length]),gi:b.gi,a:b.a*dim,pr:b.pr,n:b.n,h:G.R*7*Math.sqrt(b.n/mx)}}))}}
function svitlishe(c){const m=/^#?([0-9a-f]{6})$/i.exec(c||''); if(!m) return c;
 const v=parseInt(m[1],16), f=x=>Math.round(x+(255-x)*.45);
 return '#'+[v>>16,(v>>8)&255,v&255].map(f).map(x=>x.toString(16).padStart(2,'0')).join('')}
const HEX_FADE={L:[[0,1],[12.3,1],[12.8,0]],S:[[12.0,0],[12.4,1],[14.3,1],[14.7,0]],X:[[14.3,0],[14.7,1]]};
const fadeBy=(id,v)=>['interpolate',['linear'],['zoom'],...HEX_FADE[id].flatMap(([z,f])=>[z,f?v:0])];
// Стовпчики — одна сота 330 м на всіх масштабах (33, В6; макет
// MAKET-STOVPCHYKY): розмір у метрах від масштабу не залежить, як у kepler.gl
// і deck.gl. Розпад на 130 і 30 м давав «привидів» і голки; соти (2D) — як були.
const COL_G='L';
function hexReady(){
 const before=map.getLayer('k-addr-shadow')?'k-addr-shadow':undefined;
 for(const G of HEXG){const id=G.id;
  if(!map.getSource('k-hex-'+id)){
   map.addSource('k-hex-'+id,{type:'geojson',data:{type:'FeatureCollection',features:[]}});
   map.addSource('k-col-'+id,{type:'geojson',promoteId:'k',data:{type:'FeatureCollection',features:[]}});
   map.addLayer({id:'k-hex-'+id,type:'fill',source:'k-hex-'+id,paint:{'fill-color':['get','c'],
    'fill-opacity':fadeBy(id,['get','a'])}},before);
   map.addLayer({id:'k-hexl-'+id,type:'line',source:'k-hex-'+id,paint:{'line-width':.6,
    'line-opacity':fadeBy(id,1)}},before);
   // проблема — контур чорнила, тонший на огляді міста (Андрій 06.10)
   map.addLayer({id:'k-hexp-'+id,type:'line',source:'k-hex-'+id,filter:['==',['get','pr'],1],
    paint:{'line-width':['interpolate',['linear'],['zoom'],10,.6,12,.9,13,1.3],'line-opacity':fadeBy(id,1)}},before);
   // Стовпчики — один колір (стопка видів шарами вводила в оману, 7.3); не
   // «осідають» (рішення Андрія 06.10): лишаються стовпчиками на всіх масштабах.
   map.addLayer({id:'k-col-'+id,type:'fill-extrusion',source:'k-col-'+id,paint:{
    'fill-extrusion-color':['case',['boolean',['feature-state','sel'],false],['get','cl'],['get','c']],
    'fill-extrusion-height':['get','h'],
    'fill-extrusion-opacity':.8}},before);
  }}
 if(!map.getSource('k-hexsel')){
  map.addSource('k-hexsel',{type:'geojson',data:{type:'FeatureCollection',features:[]}});
  map.addLayer({id:'k-hexselh',type:'line',source:'k-hexsel',paint:{'line-width':5}});
  map.addLayer({id:'k-hexsel',type:'line',source:'k-hexsel',paint:{'line-width':2.5}});
 }
 hexPaint();
}
function hexPaint(){
 if(!map.getLayer('k-hex-L')) return;
 const ln=isDark()?'rgba(0,0,0,.35)':'rgba(255,255,255,.4)', ink=cssv('--ink');
 for(const G of HEXG){map.setPaintProperty('k-hexl-'+G.id,'line-color',ln);
  map.setPaintProperty('k-hexp-'+G.id,'line-color',ink);
  map.setPaintProperty('k-col-'+G.id,'fill-extrusion-opacity',isDark()?.85:.8)}
 map.setPaintProperty('k-hexsel','line-color',ink); map.setPaintProperty('k-hexselh','line-color',cssv('--halo')||'#fff');
}
function drawHex(st){
 if(!STYLE_OK||!map.getSource('k-hex-L')) return;
 binHex(st);
 const soty=MODE==='soty', stovp=MODE==='stovp';
 for(const G of HEXG){
  map.getSource('k-hex-'+G.id).setData(soty?hexData(G,false):{type:'FeatureCollection',features:[]});
  map.getSource('k-col-'+G.id).setData(stovp&&G.id===COL_G?hexData(G,true):{type:'FeatureCollection',features:[]});
  for(const l of ['k-hex-','k-hexl-','k-hexp-']) layerVis(l+G.id,soty);
  layerVis('k-col-'+G.id,stovp)}
}
// ==== АДРЕСИ (7.5–7.6) ====
// Крапка кольору свого найчисленнішого виду, радіус 0,8 + 0,25·√n на z10 →
// 3 + 1,2·√n на z16; проблема — обвідка чорнила навколо крапки (7.7).
// Зсув (тінь, обвідка проблеми) — усередині кожної точки інтерполяції:
// зум дозволений лише як вхід верхнього interpolate, і ['+', ADDR_R, 1.5]
// MapLibre мовчки відкидав разом із шаром (знайдено 06.10).
const addrR=(d=0)=>['interpolate',['linear'],['zoom'],10,['+',.8+d,['*',.25,['sqrt',['get','n']]]],
 16,['+',3+d,['*',1.2,['sqrt',['get','n']]]],19,['+',5+d,['*',1.8,['sqrt',['get','n']]]]];
const ADDR_R=addrR(0);
function addrProbReady(){
 if(map.getLayer('k-addr-pr')) return;
 map.addLayer({id:'k-addr-pr',type:'circle',source:'k-addr',filter:['==',['get','pr'],1],
  paint:{'circle-radius':addrR(2.5),'circle-color':'rgba(0,0,0,0)','circle-stroke-width':1.2}});
}
// ==== РИЗИК: ОДНА ЛІНІЯ, ОДИН КОЛІР (7.10) ====
// Рахується окремо для кожного виду й механізму (крок 4), показується одним
// шаром. Відрізок — якщо він серед показаних хоча б одного ввімкненого виду;
// товщина й насиченість — за найвищим місцем по місту серед них.
const RSEG=[], RPT=[];
{const byK=new Map();
 Object.keys(R.lines||{}).forEach(k=>{const v=R.lines[k]; if(!k.startsWith('risk_')||v.nodata) return;
  (v.items||[]).forEach(it=>{const key=(it[1]||'')+'|'+it[0][0].join(',');
   let s=byK.get(key); if(!s){s={g:it[0],name:it[1],kinds:[]}; byK.set(key,s); RSEG.push(s)}
   s.kinds.push({k,gi:v.theme|0,title:v.title,pct:it[5],mu:it[6],n2:it[3]|0,fx:it[4]||[]})})});
 Object.keys(R.tochky||{}).forEach(k=>{const v=R.tochky[k];
  (v.items||[]).forEach(x=>{const key=x[0]+','+x[1];
   let s=RPT.find(t=>t.key===key); if(!s){s={key,la:x[0],lo:x[1],typ:x[2],kinds:[]}; RPT.push(s)}
   // «кафе_є_150м» -> «кафе в 150 м»: назва ознаки моделі -> людська
   const lyud=f=>String(f).replace(/_є_(\d+)м$/,' в $1 м').replace(/_(\d+)м$/,' в $1 м').replace(/_/g,' ');
   s.kinds.push({k,gi:v.theme|0,title:v.title,pct:x[4],mu:x[5],n2:x[3]|0,fx:(x[6]||[]).map(f=>[lyud(f)])})})});}
function riskData(){
 const on=s=>s.kinds.filter(x=>typeOn(x.gi));
 const val=x=>x.pct==null?50:Math.max(0,100-x.pct);
 const L1=RSEG.map((s,i)=>[i,on(s)]).filter(x=>x[1].length), P1=RPT.map((s,i)=>[i,on(s)]).filter(x=>x[1].length);
 const all=[...L1,...P1].map(([,ks])=>Math.max(...ks.map(val)));
 const lo=Math.min(...all,100), hi=Math.max(...all,0), nr=v=>hi>lo?(v-lo)/(hi-lo):1;
 const lines={type:'FeatureCollection',features:L1.map(([i,ks])=>lineF(RSEG[i].g,{i,r:nr(Math.max(...ks.map(val)))}))};
 const pts={type:'FeatureCollection',features:P1.map(([i,ks])=>({type:'Feature',geometry:{type:'Point',
  coordinates:[RPT[i].lo,RPT[i].la]},properties:{i,r:nr(Math.max(...ks.map(val)))}}))};
 // огляд міста — соти 600 м того самого кольору, за найвищим рангом у соті
 const H=new Map();
 const add=(la,lo,r)=>{const [k,cx,cy]=hexAt(la,lo,600); const h=H.get(k); if(!h||h.r<r) H.set(k,{cx,cy,r})};
 lines.features.forEach(f=>{const c=f.geometry.coordinates[0]; add(c[1],c[0],f.properties.r)});
 pts.features.forEach(f=>{const c=f.geometry.coordinates; add(c[1],c[0],f.properties.r)});
 const hex={type:'FeatureCollection',features:[...H.values()].map(h=>({type:'Feature',
  geometry:{type:'Polygon',coordinates:hexPoly(h.cx,h.cy,600)},properties:{r:h.r}}))};
 return {lines,pts,hex}}
function riskReady(){
 if(!map.getSource('k-risk')){
  const before=map.getLayer('k-rings')?'k-rings':undefined;
  map.addSource('k-risk',{type:'geojson',data:{type:'FeatureCollection',features:[]}});
  map.addSource('k-riskpt',{type:'geojson',data:{type:'FeatureCollection',features:[]}});
  map.addSource('k-riskhex',{type:'geojson',data:{type:'FeatureCollection',features:[]}});
  map.addLayer({id:'k-riskhex',type:'fill',source:'k-riskhex',maxzoom:13,
   paint:{'fill-opacity':['interpolate',['linear'],['zoom'],11.5,['+',.12,['*',.45,['get','r']]],12.5,0]}},before);
  const W=(a,b)=>['interpolate',['linear'],['zoom'],11,['+',a[0],['*',a[1],['get','r']]],15,['+',b[0],['*',b[1],['get','r']]]];
  map.addLayer({id:'k-riskh',type:'line',source:'k-risk',minzoom:11.8,layout:{'line-cap':'round'},
   paint:{'line-width':['+',2,W([1.2,2],[2.5,4])],'line-opacity':['interpolate',['linear'],['zoom'],11.8,0,12.5,.85]}},before);
  map.addLayer({id:'k-risk',type:'line',source:'k-risk',minzoom:11.8,layout:{'line-cap':'round'},
   paint:{'line-width':W([1.2,2],[2.5,4]),'line-opacity':['interpolate',['linear'],['zoom'],11.8,0,12.5,['+',.35,['*',.6,['get','r']]]]}},before);
  map.addLayer({id:'k-riskpt',type:'circle',source:'k-riskpt',minzoom:11.8,
   paint:{'circle-radius':3.5,'circle-stroke-width':1.5,
    'circle-opacity':['interpolate',['linear'],['zoom'],11.8,0,12.5,['+',.35,['*',.6,['get','r']]]]}},before);
 }
 const c=RISK_C[THEME]||RISK_C.svitla, h=cssv('--halo')||'#fff';
 map.setPaintProperty('k-risk','line-color',c); map.setPaintProperty('k-riskh','line-color',h);
 map.setPaintProperty('k-riskhex','fill-color',c);
 map.setPaintProperty('k-riskpt','circle-color',c); map.setPaintProperty('k-riskpt','circle-stroke-color',h);
 riskDraw();
}
function riskDraw(){
 if(!map.getSource('k-risk')) return;
 const d=RISK_ON?riskData():{lines:{type:'FeatureCollection',features:[]},pts:{type:'FeatureCollection',features:[]},hex:{type:'FeatureCollection',features:[]}};
 map.getSource('k-risk').setData(d.lines); map.getSource('k-riskpt').setData(d.pts); map.getSource('k-riskhex').setData(d.hex);
 for(const id of ['k-risk','k-riskh','k-riskpt','k-riskhex']) layerVis(id,RISK_ON);
}
// «серед N% найризикованіших вулиць Києва · очікується ~M подій за рік» —
// N — місце серед УСІХ відрізків міста, вгору до цілого (< 1 → «1%»); M —
// прогноз моделі на 12 місяців (Андрій 06.10). Види — без дублікатів.
const pctCity=p=>p==null?null:Math.max(1,Math.ceil(p));
const muTxt=m=>m==null?'':m<1?' · менше 1 події за рік':` · очікується ~${Math.round(m)} ${pl(Math.round(m),'подія','події','подій')} за рік`;
function riskRows(s,pt){
 const seen=new Set(), ks=s.kinds.filter(x=>typeOn(x.gi)).sort((a,b)=>(a.pct??99)-(b.pct??99))
  .filter(x=>!seen.has(x.title)&&seen.add(x.title));
 return ks.map(x=>{const n=pctCity(x.pct);
  return `${esc(x.title)}${n?` — серед ${n}% найризикованіших ${pt?'місць':'вулиць'} Києва`:''}${muTxt(x.mu)}`})}
function riskWhence(s){const n=Math.max(0,...s.kinds.map(x=>x.n2)), fx=[...new Set(s.kinds.flatMap(x=>(x.fx||[]).map(f=>f[0])))];
 const out=[]; if(n>0) out.push(`Тут уже були події: ${n} за 2 роки`); if(fx.length) out.push(`Умови як біля подій: ${fx.join(', ')}`);
 return out}
function riskAt(p){ if(!RISK_ON||!map.getLayer('k-risk')) return null;
 const f=map.queryRenderedFeatures([[p.x-4,p.y-4],[p.x+4,p.y+4]],{layers:['k-riskpt','k-risk']})[0];
 if(!f) return null; const pt=f.layer.id==='k-riskpt'; return {pt,s:(pt?RPT:RSEG)[f.properties.i]}}
function riskTip(o){const s=o.s;
 return `<b>Ризик${o.pt?' · '+esc(s.typ):s.name?' · '+esc(s.name):''}</b>`+riskRows(s,o.pt).map(t=>`<span>${t}</span>`).join('')+
  riskWhence(s).map(t=>`<span class="rtw">${esc(t)}</span>`).join('')}
function riskPopup(o,ll){
 const s=o.s;
 let h=`<div class="rpop"><b>${o.pt?esc(s.typ):esc(s.name||'без назви')}</b>`+
  riskRows(s,o.pt).map(t=>`<div class="sub">${t}</div>`).join('')+riskWhence(s).map(t=>`<div class="rmeth">${esc(t)}</div>`).join('');
 const k0=s.kinds.filter(x=>typeOn(x.gi))[0]; if(k0) h+=factRows(k0.fx&&k0.fx[0]&&k0.fx[0].length>1?k0.fx:null);
 // Скарги 1551 у 50 м (перехрестя — 30 м): рядок, що розгортає список, —
 // у вікні ризику вкладок немає (RISHENNYA 35.10)
 const sk=skRyzyk(o);
 if(sk&&sk.length) h+=`<button class="rsk-b" data-rsk="1" aria-expanded="false">Скарги (${fmt(sk.length)})</button><div class="rsk" hidden>${skHTML(sk,50,true)}</div>`;
 h+=`<div class="rmeth"><a class="rdoc" style="display:inline;margin:0" href="skhozhi-umovy.html" target="_blank" rel="noopener">Як пораховано ↗</a></div></div>`;
 if(POPUP) POPUP.remove(); clearNear();
 const w=document.createElement('div'); w.innerHTML=h;
 const rb=w.querySelector('[data-rsk]');
 if(rb) rb.onclick=()=>{const l=w.querySelector('.rsk'); l.hidden=!l.hidden; rb.setAttribute('aria-expanded',String(!l.hidden))};
 // файл скарг ще їде — вікно домалюється, коли прийде, якщо воно ще відкрите
 if(sk===null&&SKG===null&&SKG_P) SKG_P.then(()=>{ if(POPUP&&POPUP._sk===o) riskPopup(o,ll)});
 POPUP=new maplibregl.Popup({maxWidth:'340px',anchor:'bottom',focusAfterOpen:false,closeOnClick:false}).setLngLat(ll).setDOMContent(w).addTo(map);
 POPUP._sk=o;
 keepClear(POPUP,[ll.lng,ll.lat],0)}
// ==== СКАРГИ 1551 — вкладка «Скарги (N)» (RISHENNYA 35.10; ZAVDANNYA-32, ч. 9) ====
// Файл skargy.json поруч (map_skargy.py) тягнемо, коли вперше відкривають
// картку; поки його немає, вкладки немає, а прийшов — картка малюється знову.
// Скарги видно завжди, навіть якщо на ризик вони не впливають: це голос
// мешканців місця. Без пояснень і без «причини» — лише дата, зміст, результат.
let SKG=null, SKG_P=null, SK_LIM=50, SK_POPUP=null;
function skargy(){
 if(!SKG_P) SKG_P=fetch('skargy.json').then(r=>r.ok?r.json():null).catch(()=>null).then(d=>{
  if(!d){SKG=false; return SKG}
  const d0=Date.parse(d.d0), C=0.001, g=new Map();
  d.la=d.s.map(x=>x[0]/1e5); d.lo=d.s.map(x=>x[1]/1e5);
  d.dt=d.s.map(x=>new Date(d0+x[2]*864e5).toISOString().slice(0,10));
  d.la.forEach((la,j)=>{const k=Math.floor(la/C)+','+Math.floor(d.lo[j]/C); (g.get(k)||g.set(k,[]).get(k)).push(j)});
  d.g=g; SKG=d;
  if(CELL) renderCell(); else if(PLACE) renderPlace();
  return SKG});
 return SKG}
// усі скарги в r м від будь-якої з точок [[шир, довг], …]
function skBlyzko(pts,r){const d=SKG, C=0.001, out=new Set();
 for(const [la,lo] of pts){const my=111320, mx=111320*Math.cos(la*Math.PI/180);
  const ci=Math.floor(la/C), cj=Math.floor(lo/C), n=Math.ceil(r/(C*mx))+1;
  for(let i=ci-n;i<=ci+n;i++) for(let j=cj-n;j<=cj+n;j++) for(const k of d.g.get(i+','+j)||[])
   if(Math.hypot((d.la[k]-la)*my,(d.lo[k]-lo)*mx)<=r) out.add(k)}
 return [...out].sort((a,b)=>a-b)}      // файл уже впорядкований: новіші вгорі
// кожні ~5 м точок уздовж лінії — щоб «50 м від відрізка», а не від вершин
function skLinia(g,r){const pts=[];
 for(let i=0;i+1<g.length;i++){const a=g[i], b=g[i+1], L=Math.hypot((b[0]-a[0])*111320,(b[1]-a[1])*71000), n=Math.max(1,Math.ceil(L/5));
  for(let t=0;t<n;t++) pts.push([a[0]+(b[0]-a[0])*t/n,a[1]+(b[1]-a[1])*t/n])}
 if(g.length) pts.push(g[g.length-1]);
 return skBlyzko(pts,r)}
// для картки: адреса — той самий будинок; проблема — її адреси й 30 м
// (R_MISCE, як у голосі мешканців, але всі види); сота — скарги в соті
function skMisce(d){ if(!skargy()) return null;
 if(d.pr){const ii=[...new Set((d.pr.ev&&d.pr.ev.length?d.pr.ev:[[PLACE.i,0]]).map(r=>r[0]))];
  return skBlyzko(ii.map(i=>[P[i][0],P[i][1]]),30)}
 return d.p[3]?(SKG.a[PLACE.i]||[]):[]}
function skHex(hex){ if(!skargy()) return null;
 const [cx,cy,R_]=hex, out=[];
 for(const k of skBlyzko([[cy/MY_,cx/MX_]],R_*1.01)){const [_k,x,y]=hexAt(SKG.la[k],SKG.lo[k],R_);
  if(Math.abs(x-cx)<1&&Math.abs(y-cy)<1) out.push(k)}
 return out}
function skRyzyk(o){ if(!skargy()) return null;
 return o.pt?skBlyzko([[o.s.la,o.s.lo]],/перехрест/i.test(o.s.typ||'')?30:50):skLinia(o.s.g,50)}
function skHTML(ids,lim,bezShche){const d=SKG;
 return ids.slice(0,lim).map(k=>`<div class="kp-dec kp-sk"><div class="l1"><b>${esc(fmtDate(d.dt[k]))}</b></div>`+
   `<div class="l2">${esc(d.c[d.s[k][3]])}</div><div class="l3">${esc(d.r[d.s[k][4]])}</div></div>`).join('')+
  (ids.length>lim?(bezShche?`<div class="tt">ще ${fmt(ids.length-lim)}</div>`:`<button class="kp-lnk" data-skmore="1">ще ${Math.min(50,ids.length-lim)}</button>`):'')}
document.addEventListener('click',e=>{ if(!e.target.closest('[data-skmore]')) return;
 SK_LIM+=50; if(CELL) renderCell(); else if(PLACE) renderPlace()},true);
// ==== КАРТКА СОТИ / КІЛЬЦЯ (7.11, макет «Картка соти», версія 2) ====
let CELL=null;   // {kind:'СОТА'|'КІЛЬЦЕ', ad:[індекси P], tab, open, page, hex:[cx,cy,R]|null, ll}
function cellEvs(ad){const st=LASTST||computeVis(), out=[];
 for(const i of ad){const p=P[i]; if(!p||!p[3]) continue;
  p[4].forEach((e,k)=>{if(evOn(e,st.C,st.A,st.Y,st.H)) out.push([i,k])})}
 return out.sort((a,b)=>(EVR(b)[5]??-1)-(EVR(a)[5]??-1))}
function openCell(kind,ad,hex,ll){
 if(POPUP) POPUP.remove(); closePlace();
 CELL={kind,ad,tab:'ogl',open:-1,page:1,hex,ll};
 // у стовпчиках контуру на землі немає — вибраний стовпчик світліший (33, В6)
 if(hex&&MODE==='stovp'){const k=hexAt(hex[1]/MY_,hex[0]/MX_,hex[2])[0];
  CELL.colSel=k; map.setFeatureState({source:'k-col-'+COL_G,id:k},{sel:true})}
 else if(hex) map.getSource('k-hexsel').setData({type:'FeatureCollection',features:[{type:'Feature',
  geometry:{type:'Polygon',coordinates:hexPoly(hex[0],hex[1],hex[2])},properties:{}}]});
 renderCell()}
function closeCell(){
 if(CELL&&CELL.colSel!==undefined&&map.getSource('k-col-'+COL_G)) map.setFeatureState({source:'k-col-'+COL_G,id:CELL.colSel},{sel:false});
 CELL=null; if(map.getSource('k-hexsel')) map.getSource('k-hexsel').setData({type:'FeatureCollection',features:[]});
 const el=placeEl(); if(!PLACE){el.hidden=true; el.classList.remove('kp-cell','kp-tall'); document.body.classList.remove('kp-open')}}
let CELL_DOCS={key:'',cs:undefined};
function renderCell(){
 const el=placeEl(); if(!CELL){return}
 const evs=cellEvs(CELL.ad), n=evs.length;
 const adN=new Set(evs.map(r=>r[0])).size;
 const byA=new Map(); evs.forEach(r=>byA.set(r[0],(byA.get(r[0])||0)+1));
 const top=[...byA.entries()].sort((a,b)=>b[1]-a[1])[0];
 const g=new Array(M.groups.length).fill(0); evs.forEach(r=>g[CATTH[EVR(r)[1]]]++);
 const probs=CELL.ad.map(i=>[i,probsOf(P[i])]).filter(x=>x[1].length);
 const sk=CELL.hex?skHex(CELL.hex):null;
 if(CELL.tab==='skarg'&&!(sk&&sk.length)) CELL.tab='ogl';
 let body='';
 if(CELL.tab==='skarg') body=skHTML(sk,SK_LIM);
 else if(CELL.tab==='ogl'){
  if(probs.length) body+=probs.slice(0,3).map(([i,ps])=>`<div class="kp-pc" role="button" tabindex="0" data-cp="${i}"><div class="kp-pch">Проблема · ${esc(ps[0].theme)}</div>`+
   `<div class="kp-pct">${esc(ps[0].mech)}</div><div class="tt">${esc(P[i][2])}</div></div>`).join('');
  body+=`<div class="kc-vydy">${g.map((v,gi)=>v?`<button data-cv="${gi}" aria-expanded="${CELL.open===gi}"><i style="background:${PALA[gi%PALA.length]}"></i>${esc(shortOf(gi))}<b>${fmt(v)}</b></button>`+
   (CELL.open===gi?`<div class="kc-art">${(()=>{const c={}; evs.forEach(r=>{const e=EVR(r); if(CATTH[e[1]]===gi) c[e[1]]=(c[e[1]]||0)+1});
    return Object.entries(c).sort((a,b)=>b[1]-a[1]).slice(0,4).map(([a,k])=>`<div>${esc(splitArt(M.cats[a])[0])} <b>${k}</b></div>`).join('')})()}</div>`:''):'').join('')}</div>`;
  body+=placeHist(null,evs);
  if(RSEG.length&&CELL.hex){const [cx,cy,R_]=CELL.hex;
   const kr=RSEG.filter(s=>s.kinds.some(x=>typeOn(x.gi))&&s.g.some(q=>{const dx=q[1]*MX_-cx,dy=q[0]*MY_-cy; return dx*dx+dy*dy<=R_*R_})).length;
   if(kr) body+=`<div class="tt kc-risk"><i></i>Ризик: ${kr} ${pl(kr,'вулиця','вулиці','вулиць')}</div>`}
  body+=`<button class="pbtn2" data-cz="1">Наблизити</button><button class="pbtn2" data-ca="1">Показати адреси</button>`+
   `<button class="pbtn2" data-link="1">Посилання</button>`;
 } else {
  const key=CELL.ad.join(',');
  if(CELL_DOCS.key!==key){CELL_DOCS={key,cs:undefined}; docsForRefs(evs).then(cs=>{if(CELL_DOCS.key===key){CELL_DOCS.cs=cs; renderCell()}})}
  const cs=CELL_DOCS.cs;
  if(cs===undefined) body='<div class="kp-empty">завантажую…</div>';
  else if(cs===null) body='<div class="kp-empty">Перелік рішень лежить окремим файлом поруч, а браузер не дає сторінці з диска його читати. Відкрийте карту з сайту або через PODYVYTYSYA.bat.</div>';
  else {const it=evs.slice(0,50*CELL.page).map(r=>[r,(cs[r[0]]||[])[r[1]]]).filter(x=>x[1]);
   body=it.map(([r,c])=>`<div class="kp-dec open"><div class="l1"><b>${esc(fmtDate(c[1]))}</b><span class="h">${esc(P[r[0]][2])}</span></div>`+
    `<div class="l2">${esc(M.cats[c[0]])}</div><div class="l3">${esc(c[5]||'опису в рішенні немає')}</div></div>`).join('')+
    (evs.length>50*CELL.page?`<button class="kp-lnk" data-cmore="1">ще ${Math.min(50,evs.length-50*CELL.page)}</button>`:'')}
 }
 el.innerHTML=`<div class="kp-head"><div class="kp-badge">${CELL.kind}</div>
  <b class="kp-title">${top?'Навколо '+esc(P[top[0]][2]):'—'}</b>
  <div class="kp-sum">${fmt(n)} ${pl(n,'подія','події','подій')} · ${fmt(adN)} ${pl(adN,'адреса','адреси','адрес')}</div>
  <div class="kc-strip">${g.map((v,gi)=>v?`<i style="flex:${v};background:${PALA[gi%PALA.length]}"></i>`:'').join('')}</div>
  <button class="kp-x" data-kp="close" aria-label="Закрити (Esc)" title="Закрити (Esc)">×</button></div>
  <div class="kp-tabs" role="tablist"><button role="tab" data-ct="ogl" aria-selected="${CELL.tab==='ogl'}">Огляд</button><button role="tab" data-ct="rish" aria-selected="${CELL.tab==='rish'}">Рішення (${fmt(n)})</button>`+
  (sk&&sk.length?`<button role="tab" data-ct="skarg" aria-selected="${CELL.tab==='skarg'}">Скарги (${fmt(sk.length)})</button>`:'')+`</div>
  <div class="kp-body">${body}</div>`;
 el.hidden=false; el.classList.add('kp-cell'); document.body.classList.add('kp-open');
}
// Закрили картку — посилання на неї з адреси сторінки прибираємо: інакше
// оновлення сторінки відкривало її знову (перевірка 06.10)
const bezPosylannia=()=>{ if(/^#(m|c)=/.test(location.hash)) history.replaceState(null,'',location.pathname+location.search)};
placeEl().addEventListener('click',e=>{ if(e.target.closest('[data-kp="close"]')) bezPosylannia(); if(!CELL) return;
 const t=e.target;
 if(t.closest('.kp-head')&&!t.closest('[data-kp]')&&matchMedia('(max-width:700px)').matches){placeEl().classList.toggle('kp-tall'); return}
 const x=t.closest('[data-kp="close"]'); if(x){e.stopImmediatePropagation(); return closeCell()}
 const ct=t.closest('[data-ct]'); if(ct){CELL.tab=ct.dataset.ct; SK_LIM=50; return renderCell()}
 const cv=t.closest('[data-cv]'); if(cv){const gi=+cv.dataset.cv; CELL.open=CELL.open===gi?-1:gi; return renderCell()}
 const cp=t.closest('[data-cp]'); if(cp){const i=+cp.dataset.cp; closeCell(); return openAt(i)}
 if(t.closest('[data-cmore]')){CELL.page++; return renderCell()}
 // «Показати адреси» — вигляд «Адреси» на тому самому місці й масштабі
 if(t.closest('[data-ca]')){closeCell(); return setView('addr')}
 if(t.closest('[data-link]')) return kopiyuvaty(CELL.hex?`c=${CELL.hex[2]},${(CELL.hex[1]/MY_).toFixed(5)},${(CELL.hex[0]/MX_).toFixed(5)}`:'',t.closest('[data-link]'));
 if(t.closest('[data-cz]')){let s=90,w=180,n=-90,ea=-180;
  for(const i of CELL.ad){const p=P[i]; if(p[0]<s)s=p[0]; if(p[0]>n)n=p[0]; if(p[1]<w)w=p[1]; if(p[1]>ea)ea=p[1]}
  map.fitBounds([[w,s],[ea,n]],{padding:sidePad(),maxZoom:16.5,duration:900})}
},true);
document.addEventListener('keydown',e=>{ if(e.key!=='Escape') return; bezPosylannia(); if(CELL) closeCell()});
// ==== ПОСИЛАННЯ НА МІСЦЕ (KARTA-1.0 №15; RISHENNYA 35.9) ====
// Адреса сторінки з #m=<lat>,<lon>[,<механізм проблеми>] (адреса, проблема)
// чи #c=<R>,<lat>,<lon> (сота); відкриття — карта на місці з карткою.
// Проблема — за адресою й механізмом, а не за порядковим номером: номер
// міняється щопонеділка, і посилання, яке викладач дав слухачам, ламалося б
// (ZAVDANNYA-33, А2).
function kopiyuvaty(h,btn){ if(!h) return;
 const u=location.origin+location.pathname+location.search+'#'+h;
 history.replaceState(null,'','#'+h);
 // На телефоні — меню «Поділитися»: посилання йде одразу в месенджер
 if(navigator.share&&matchMedia('(pointer:coarse)').matches){navigator.share({url:u}).catch(()=>{}); return}
 // Відповідь — на самій кнопці; буфер обміну браузер може не дати (стара
 // сторінка, заборона) — тоді посилання лишається в адресному рядку.
 const skazaty=s=>{ if(!btn){const t=document.createElement('div'); t.id='kcopy'; t.textContent=s;
   map.getContainer().appendChild(t); return setTimeout(()=>t.remove(),1600)}
  const t0=btn.dataset.t0||(btn.dataset.t0=btn.textContent); btn.textContent=s;
  clearTimeout(btn._t); btn._t=setTimeout(()=>{btn.textContent=t0},1500)};
 const ne=()=>skazaty('в адресному рядку');
 try{navigator.clipboard.writeText(u).then(()=>skazaty('скопійовано'),ne)}catch(e){ne()}}
function zPosylannia(){
 const h=decodeURIComponent(location.hash.slice(1));
 let m=/^m=(-?[\d.]+),(-?[\d.]+)(?:,(.+))?$/.exec(h);
 if(m){const la=+m[1], lo=+m[2], mech=m[3]; let best=-1,bd=1e9;
  P.forEach((p,i)=>{if(!p[3]) return; const d=Math.hypot((p[0]-la)*MY_,(p[1]-lo)*MX_); if(d<bd){bd=d;best=i}});
  const j=best>=0&&bd<=30&&mech?probsOf(P[best]).findIndex(q=>q.mech===mech):0;
  // адреси чи проблеми після оновлення немає — те саме місце, без картки
  if(best<0||bd>30||j<0) return map.jumpTo({center:[lo,la],zoom:16});
  afterMove(()=>{openAt(best); if(j>0){PLACE.pi=j; renderPlace()}});
  const w=placeEl().offsetWidth||396;
  map.flyTo({center:[P[best][1],P[best][0]],zoom:16,offset:[window.innerWidth>700?w/2:0,0]}); return}
 m=/^c=(\d+),(-?[\d.]+),(-?[\d.]+)$/.exec(h);
 if(m){const R_=+m[1], la=+m[2], lo=+m[3], cx=lo*MX_, cy=la*MY_;
  if(!HEXG.some(G=>G.R===R_)) return;
  setView('soty');
  const ad=[]; P.forEach((p,i)=>{if(!p[3]) return; const [k,x,y]=hexAt(p[0],p[1],R_); if(Math.abs(x-cx)<1&&Math.abs(y-cy)<1) ad.push(i)});
  if(ad.length){map.jumpTo({center:[lo,la],zoom:R_===330?12:R_===130?13.4:15.5}); openCell('СОТА',ad,[cx,cy,R_],null)}}
}
// кнопка «Посилання» в картці адреси й проблеми
{const _r=renderPlace;
 renderPlace=function(){_r(); const el=placeEl(); if(!PLACE||el.hidden) return;
  if(CELL){CELL=null; if(map.getSource('k-hexsel')) map.getSource('k-hexsel').setData({type:'FeatureCollection',features:[]})}
  el.classList.remove('kp-cell','kp-tall');
  const b=el.querySelector('.kp-body'); if(!b||el.querySelector('[data-plink]')) return;
  const p=P[PLACE.i]; b.insertAdjacentHTML('beforeend',`<button class="pbtn2" data-plink="1">Посилання</button>`);
  const bt=el.querySelector('[data-plink]');
  bt.onclick=()=>{const pr=placeData().pr;
   kopiyuvaty(`m=${p[0].toFixed(5)},${p[1].toFixed(5)}`+(pr?','+encodeURIComponent(pr.mech):''),bt)}}}
// ==== ВИГЛЯДИ: «Соти · Стовпчики · Кільця · Адреси» (RISHENNYA 35.9) ====
// «◆ Проблеми» — окремий перемикач «лише проблеми». За замовчуванням — соти;
// вибір пам'ятає браузер. Стовпчики — з нахилом 55°, решта — без нахилу.
function setView(v){
 const was=MODE; MODE=v; try{localStorage.setItem('karta-vyhlyad',v)}catch(e){}
 document.querySelectorAll('#fcat [data-m]').forEach(x=>swSet(x,x.dataset.m===v));
 if(v==='stovp'&&was!=='stovp') map.easeTo({pitch:55,duration:700});
 if(v!=='stovp'&&was==='stovp') map.easeTo({pitch:0,duration:700});
 // Зміна вигляду скидає вибір і контури попереднього (33, В4): шестикутник
 // вибраної соти висів у «Кільцях» поруч із кільцем
 if(v!==was){ if(CELL) closeCell(); if(POPUP) POPUP.remove(); bezPosylannia();
  if(map.getSource('k-hexsel')) map.getSource('k-hexsel').setData({type:'FeatureCollection',features:[]})}
 draw()}
{const VIEWS=[['soty','Соти'],['stovp','Стовпчики'],['rings','Кільця'],['addr','Адреси']];
 let v=null; try{v=localStorage.getItem('karta-vyhlyad')}catch(e){}
 const seg=$('#fcat');
 seg.innerHTML=VIEWS.map(([k,n])=>`<button data-m="${k}" title="${n}" aria-pressed="false">${n}</button>`).join('');
 seg.onclick=e=>{const b=e.target.closest('[data-m]'); if(b) setView(b.dataset.m)};
 MODE=VIEWS.some(x=>x[0]===v)?v:'soty';
 seg.querySelectorAll('[data-m]').forEach(x=>swSet(x,x.dataset.m===MODE));
 const fp=$('#fprob'); fp.hidden=false; swSet(fp,false);
 fp.onclick=e=>{ONLYP=!ONLYP; swSet(fp,ONLYP); draw()};
 if(MODE==='stovp') map.once('load',()=>map.easeTo({pitch:55,duration:0}));}
// ---- клік і наведення по сотах і стовпчиках ----
function hexHit(p){ if(MODE!=='soty'&&MODE!=='stovp') return null;
 const ids=[]; for(const G of HEXG) ids.push((MODE==='soty'?'k-hex-':'k-col-')+G.id);
 const f=map.queryRenderedFeatures(p,{layers:ids.filter(id=>map.getLayer(id))});
 if(!f.length) return null;
 // з кількох сіток — та, що зараз видніша
 const z=map.getZoom(), id=MODE==='stovp'?COL_G:z<12.55?'L':z<14.5?'S':'X', g=f.find(x=>x.layer.id.endsWith(id))||f[0];
 const G=HEXG.find(x=>g.layer.id.endsWith(x.id)), b=HEXB[G.id].get(g.properties.k);
 return b?{G,b}:null}
map.on('click',e=>{ if(CLICK_TAKEN||iconAt(e.point)) return;
 const rk=riskAt(e.point); if(rk&&!addrAt(e.point)){CLICK_TAKEN=true; return riskPopup(rk,e.lngLat)}
 const h=hexHit(e.point); if(!h) return;
 CLICK_TAKEN=true; openCell('СОТА',h.b.ad,[h.b.cx,h.b.cy,h.G.R],e.lngLat)});
map.on('mousemove',e=>{
 const rk=riskAt(e.point);
 if(rk&&!addrAt(e.point)&&!(RINGS_ON&&hitRing(e.point))){map.getCanvas().style.cursor='pointer';
  VTIP.setLngLat(e.lngLat).setHTML(riskTip(rk)).addTo(map); return}
 const h=hexHit(e.point);
 if(h){map.getCanvas().style.cursor='pointer';
  const a=new Set(h.b.ad).size;
  // над стовпчиком — лише він сам: скільки подій і чий колір (33, В6)
  VTIP.setLngLat(e.lngLat).setHTML(MODE==='stovp'
   ?`<b>${fmt(h.b.n)} ${pl(h.b.n,'подія','події','подій')} · ${esc(lc(shortOf(h.b.gi)))}</b>`
   :`<b>${fmt(h.b.n)} ${pl(h.b.n,'подія','події','подій')} · ${fmt(a)} ${pl(a,'адреса','адреси','адрес')}</b>`).addTo(map); return}
 VTIP.remove()});
const VTIP=new maplibregl.Popup({closeButton:false,closeOnClick:false,className:'k-tip',offset:14,maxWidth:'320px'});
map.on('mouseout',()=>VTIP.remove());
// ---- готовність стилю: власні шари й перефарбування в кольори теми ----
// setStyle скидає їх разом із підкладкою; carry переносить джерела й шари k-*,
// а кольори теми ставимо тут заново (7.8: без цього шари зникали).
let ZPOS=false;
function vyhReady(){ hexReady(); addrProbReady(); riskReady();
 map.setPaintProperty('k-addr-pr','circle-stroke-color',cssv('--ink'));
 draw();
 if(!ZPOS){ZPOS=true; setTimeout(zPosylannia,400)}}
window.addEventListener('hashchange',()=>{if(/^#(m|c)=/.test(location.hash)) zPosylannia()});
"""
