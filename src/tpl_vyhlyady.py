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
 const NG_=M.groups.length;
 for(const G of HEXG){const B=new Map();
  for(const v of st.vis){const p=v[0]; if(!p[3]) continue;
   const [k,cx,cy]=hexAt(p[0],p[1],G.R);
   let b=B.get(k); if(!b){b={n:0,g:new Array(NG_).fill(0),ad:[],pr:0,cx,cy,k}; B.set(k,b)}
   b.n+=v[1]; b.ad.push(PIDX.get(p)); for(const g in v[4]) b.g[g]+=v[4][g];
   if(probsOf(p).some(q=>q.thi===undefined||q.thi<0||st.GVIS.has(q.thi))) b.pr=1}
  // Колір — та сама функція, що в кола адреси (S-К.6, 36.34; kolirMisca): вид,
  // якого тут більше, ніж у середньому по місту; проблема — лише контуром.
  const bs=[...B.values()].sort((a,b)=>a.n-b.n), L_=bs.length;
  bs.forEach((b,i)=>{
   b.gi=b.n?kolirMisca(b.g,st.MG,st.tot):-1; const rank=L_>1?i/(L_-1):1;
   b.a=isDark()?Math.min(.7,.12+.7*rank*rank):Math.min(.6,.05+.6*rank*rank);
   // сота лише з сірими подіями фільтра — блідо-сіра, не схована (S-К.25)
   if(!b.n) b.a=isDark()?.22:.28;
   // контур проблеми на майже прозорій соті виглядав би порожнім
   if(b.pr) b.a=Math.max(b.a,.45);
   b.rank=rank});
  HEXB[G.id]=B}
}
function hexData(G,cols){
 const B=HEXB[G.id];
 const ns=[...B.values()].map(b=>b.n).sort((a,b)=>a-b), med=ns.length?ns[ns.length>>1]:0;
 // Висота 3D — від 95-го перцентиля групи, а не від найбільшої комірки міста:
 // одна комірка вокзалу робила решту стовпчиків «шайбами» (ZAVDANNYA-41, 0.1)
 const mx=Math.max(1,ns.length?ns[Math.min(ns.length-1,Math.floor(ns.length*.95))]:1);
 return {type:'FeatureCollection',features:[...B.values()].filter(b=>!cols||b.n>=med).map(b=>({type:'Feature',
  geometry:{type:'Polygon',coordinates:hexPoly(b.cx,b.cy,G.R,cols?.62:1)},
  // cl — світліший колір вибраного стовпчика, поки відкрита картка (33, В6)
  properties:{k:b.k,c:kolirV(b.gi),cl:svitlishe(kolirV(b.gi)),gi:b.gi,a:b.a,pr:b.pr,n:b.n,h:G.R*7*(.12+.88*Math.sqrt(Math.min(1,b.n/mx)))}}))}}
function svitlishe(c){const m=/^#?([0-9a-f]{6})$/i.exec(c||''); if(!m) return c;
 const v=parseInt(m[1],16), f=x=>Math.round(x+(255-x)*.45);
 return '#'+[v>>16,(v>>8)&255,v&255].map(f).map(x=>x.toString(16).padStart(2,'0')).join('')}
const HEX_FADE={L:[[0,1],[12.3,1],[12.8,0]],S:[[12.0,0],[12.4,1],[14.3,1],[14.7,0]],X:[[14.3,0],[14.7,1]]};
const fadeBy=(id,v)=>['interpolate',['linear'],['zoom'],...HEX_FADE[id].flatMap(([z,f])=>[z,f?v:0])];
// 3D — ті самі комірки, що соти на цьому зумі (36.55, макет «3D», верхній ряд):
// наблизив — стовпчики менші й їх більше. Між групами — осідання й виростання,
// прив'язане до зуму, а не до часу (ZAVDANNYA-41, етап 1; Андрій: «великі
// стовпчики одразу міняються на малі»): у смузі ±0,4 навколо порогу стара група
// плавно опускається до 0, нова виростає від 0. Поза смугою шар групи не
// малюється зовсім (minzoom/maxzoom) — рівно один шар, без привидів.
// Колір — як у сот (36.56, S-К.6); висота нормована в межах групи (hexData).
const COL_POROHY=[12.3,14.5], COL_SMUHA=.4;
const colG=(z=map.getZoom())=>z<COL_POROHY[0]?'L':z<COL_POROHY[1]?'S':'X';
// [minzoom, maxzoom) шару й висота за зумом — від повної до 0 у смузі
const COL_ZUM={L:[0,COL_POROHY[0]+COL_SMUHA],S:[COL_POROHY[0]-COL_SMUHA,COL_POROHY[1]+COL_SMUHA],X:[COL_POROHY[1]-COL_SMUHA,24]};
function colVysota(id){const [a,b]=COL_ZUM[id], h=['get','h'], st=[];
 if(a>0) st.push(a,0,a+2*COL_SMUHA,h); else st.push(0,h);
 if(b<24) st.push(b-2*COL_SMUHA,h,b,0);
 return st.length>2?['interpolate',['linear'],['zoom'],...st]:h}
// нахил від зуму: огляд ~55°, з наближенням плавно до ~20°
const pitch3d=(z=map.getZoom())=>Math.round(55-35*Math.min(1,Math.max(0,(z-11)/5)));
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
   // Стовпчики — колір комірки, як у сот (36.56: «один колір» 7.3 скасовано)
   map.addLayer({id:'k-col-'+id,type:'fill-extrusion',source:'k-col-'+id,minzoom:COL_ZUM[id][0],maxzoom:COL_ZUM[id][1],paint:{
    'fill-extrusion-color':['case',['boolean',['feature-state','sel'],false],['get','cl'],['get','c']],
    'fill-extrusion-height':colVysota(id),
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
  // у 3D дані всіх трьох груп одразу: перехід — лише вираз висоти за зумом,
  // без setData під час щипка (на телефоні це й ламало 3D)
  map.getSource('k-col-'+G.id).setData(stovp?hexData(G,true):{type:'FeatureCollection',features:[]});
  for(const l of ['k-hex-','k-hexl-']) layerVis(l+G.id,soty);
  // контур соти-проблеми — не в лінзах «Порушник» і «Ціль» (36.41: «Проблеми» сховані)
  layerVis('k-hexp-'+G.id,soty&&!lzActive());
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
// Ризик у картці — одне правило для адреси й соти (S-К.15, 36.23.4): лінії
// ризику ввімкнених видів, що заходять у коло R м навколо місця (адреса — 50 м,
// сота — її радіус). Нуль — рядка немає: «вулиці в переліку немає» було
// пояснювальним реченням (36.2).
function rizykPoruch(la,lo,R_){ if(!RSEG.length) return 0;
 const cx=lo*MX_, cy=la*MY_;
 return RSEG.filter(s=>s.kinds.some(x=>typeOn(x.gi))&&s.g.some(q=>{const dx=q[1]*MX_-cx,dy=q[0]*MY_-cy; return dx*dx+dy*dy<=R_*R_})).length}
const rizykRiadok=kr=>kr?`<div class="tt kc-risk"><i></i>Ризик: ${kr} ${pl(kr,'вулиця','вулиці','вулиць')} поруч</div>`:'';
function riskData(){
 const on=s=>s.kinds.filter(x=>typeOn(x.gi));
 const val=x=>x.pct==null?50:Math.max(0,100-x.pct);
 const L1=RSEG.map((s,i)=>[i,on(s)]).filter(x=>x[1].length), P1=RPT.map((s,i)=>[i,on(s)]).filter(x=>x[1].length);
 const all=[...L1,...P1].map(([,ks])=>Math.max(...ks.map(val)));
 const lo=Math.min(...all,100), hi=Math.max(...all,0), nr=v=>hi>lo?(v-lo)/(hi-lo):1;
 const lines={type:'FeatureCollection',features:L1.map(([i,ks])=>lineF(RSEG[i].g,{i,r:nr(Math.max(...ks.map(val)))}))};
 const pts={type:'FeatureCollection',features:P1.map(([i,ks])=>({type:'Feature',geometry:{type:'Point',
  coordinates:[RPT[i].lo,RPT[i].la]},properties:{i,r:nr(Math.max(...ks.map(val)))}}))};
 // Соти ризику на огляді прибрано (36.46, S-К.28): червона заливка закривала
 // події навіть у вигляді «Адреси». Ризик — лише лінії й точки на будь-якому зумі.
 return {lines,pts}}
function riskReady(){
 if(!map.getSource('k-risk')){
  // Ризик — під лініями-проблемами (36.51): проблема завжди видна поверх смуги
  const before=map.getLayer('k-probl-h')?'k-probl-h':map.getLayer('k-rings')?'k-rings':undefined;
  map.addSource('k-risk',{type:'geojson',data:{type:'FeatureCollection',features:[]}});
  map.addSource('k-riskpt',{type:'geojson',data:{type:'FeatureCollection',features:[]}});
  // М'яка смуга під вулицею без облямівки (36.51, варіант А): Андрію ризик не
  // має бути ляпистим і заважати проблемам. Ширина й прозорість — за рангом:
  // на z15 10–18 px і 0,20–0,42, на огляді — тонко, як було
  const W=['interpolate',['linear'],['zoom'],10,['+',.6,['*',.8,['get','r']]],12.5,['+',2.5,['*',3,['get','r']]],15,['+',10,['*',8,['get','r']]],18,['+',16,['*',12,['get','r']]]];
  const OP=['interpolate',['linear'],['zoom'],10,['+',.25,['*',.4,['get','r']]],13,['+',.2,['*',.22,['get','r']]]];
  map.addLayer({id:'k-risk',type:'line',source:'k-risk',layout:{'line-cap':'round','line-join':'round'},
   paint:{'line-width':W,'line-opacity':OP}},before);
  map.addLayer({id:'k-riskpt',type:'circle',source:'k-riskpt',
   paint:{'circle-radius':['interpolate',['linear'],['zoom'],10,1.5,15,['+',6,['*',4,['get','r']]]],'circle-blur':.3,
    'circle-opacity':OP}},before);
 }
 const c=RISK_C[THEME]||RISK_C.svitla, h=cssv('--halo')||'#fff';
 map.setPaintProperty('k-risk','line-color',c); map.setPaintProperty('k-riskpt','circle-color',c);
 riskDraw();
}
function riskDraw(){
 if(!map.getSource('k-risk')) return;
 const d=RISK_ON?riskData():{lines:{type:'FeatureCollection',features:[]},pts:{type:'FeatureCollection',features:[]}};
 map.getSource('k-risk').setData(d.lines); map.getSource('k-riskpt').setData(d.pts);
 for(const id of ['k-risk','k-riskpt']) layerVis(id,RISK_ON);
}
// «серед N% найризикованіших вулиць Києва · очікується ~M подій за рік» —
// N — місце серед УСІХ відрізків міста, вгору до цілого (< 1 → «1%»); M —
// прогноз моделі на 12 місяців (Андрій 06.10). Види — без дублікатів.
// M не справджується в жодному виді (0–45% при порозі 60%) — прибрано
// (RISHENNYA 36.17.3, S-Р.8); «серед N%» лишається.
const pctCity=p=>p==null?null:Math.max(1,Math.ceil(p));
function riskRows(s,pt){
 const seen=new Set(), ks=s.kinds.filter(x=>typeOn(x.gi)).sort((a,b)=>(a.pct??99)-(b.pct??99))
  .filter(x=>!seen.has(x.title)&&seen.add(x.title));
 return ks.map(x=>{const n=pctCity(x.pct);
  return `${esc(x.title)}${n?` — серед ${n}% найризикованіших ${pt?'місць':'вулиць'} Києва`:''}`})}
// «Умови як біля подій» — з моделі ліній; лінії переходять на історію зі
// згасанням без середовища, тож для ліній рядок прибирається (RISHENNYA 36.17.1)
// «Умов як біля подій» немає ні в лінії, ні в точці (S-Р.8; центральний чат 01.11:
// на точці супермаркету вони ще лишались) — ризик тепер історія, не умови
function riskWhence(s,pt){const n=Math.max(0,...s.kinds.map(x=>x.n2)), fx=[];
 const out=[]; if(n>0) out.push(`Тут уже були події: ${n} за 2 роки`); if(fx.length) out.push(`Умови як біля подій: ${fx.join(', ')}`);
 return out}
function riskAt(p){ if(!RISK_ON||!map.getLayer('k-risk')) return null;
 const f=map.queryRenderedFeatures([[p.x-4,p.y-4],[p.x+4,p.y+4]],{layers:['k-riskpt','k-risk']})[0];
 if(!f) return null; const pt=f.layer.id==='k-riskpt'; return {pt,s:(pt?RPT:RSEG)[f.properties.i]}}
function riskTip(o){const s=o.s;
 return `<b>Ризик${o.pt?' · '+esc(s.typ):s.name?' · '+esc(s.name):''}</b>`+riskRows(s,o.pt).map(t=>`<span>${t}</span>`).join('')+
  riskWhence(s,o.pt).map(t=>`<span class="rtw">${esc(t)}</span>`).join('')}
// «Тут раніше: <ціль, топ-2> · <ознака порушника, якщо ≥30%>» — описово, з
// подій у 30 м від лінії (50 м від точки) за 24 місяці; модель ризику не
// міняється: підвиди за ціллю надто малі для прогнозу (36.52 п. 4, S-Р.2)
function tutRanishe(o){ if(!LZD) return '';
 const R_=o.pt?50:30, pts=o.pt?[[o.s.la,o.s.lo]]:o.s.g, vid=(M.mon_n||1)-24, E=[];
 P.forEach(p=>{ if(!p[3]) return;
  if(!pts.some(q=>{const dx=(q[1]-p[1])*MX_, dy=(q[0]-p[0])*MY_; return dx*dx+dy*dy<=R_*R_})) return;
  p[4].forEach(e=>{ if(e[5]>=vid&&typeOn(CATTH[e[1]])) E.push(e)})});
 if(E.length<3) return '';
 const t={}; E.forEach(e=>(e.ts||[]).forEach(x=>t[x]=(t[x]||0)+1));
 const top=Object.entries(t).sort((a,b)=>b[1]-a[1]).slice(0,2).map(([x])=>lzNazva(+x));
 const oz=LZD.oz.map(([b,nm])=>[nm,E.filter(e=>(e.oz||0)&b).length]).filter(([,n])=>n>=.3*E.length).map(([nm])=>nm.toLowerCase());
 const r=[...top,...oz]; return r.length?`Тут раніше: ${r.join(' · ')}`:''}
function riskPopup(o,ll){
 const s=o.s;
 if(!LZD&&typeof zavantazhLinzy==='function') zavantazhLinzy().then(()=>{ if(POPUP&&POPUP._sk===o) riskPopup(o,ll)});
 const tr=tutRanishe(o);
 let h=`<div class="rpop"><b>${o.pt?esc(s.typ):esc(s.name||'без назви')}</b>`+
  riskRows(s,o.pt).map(t=>`<div class="sub">${t}</div>`).join('')+riskWhence(s,o.pt).map(t=>`<div class="rmeth">${esc(t)}</div>`).join('')+
  (tr?`<div class="rmeth">${esc(tr)}</div>`:'');
 // Скарги 1551 у 50 м (перехрестя — 30 м): рядок, що розгортає список, —
 // у вікні ризику вкладок немає (RISHENNYA 35.10)
 const sk=skRyzyk(o);
 if(sk&&sk.length) h+=`<button class="rsk-b" data-rsk="1" aria-expanded="false">Скарги (${fmt(sk.length)})</button><div class="rsk" hidden>${skHTML(sk,50,true)}</div>`;
 h+=`<div class="rmeth"><a class="rdoc" style="display:inline;margin:0" href="ryzyk.html" target="_blank" rel="noopener">Як пораховано ↗</a>`+
  ` · <a class="rdoc" style="display:inline;margin:0" href="shcho-robyty.html#ryzyk" target="_blank" rel="noopener">Що робити ›</a></div></div>`;
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
 if(POPUP) POPUP.remove(); closePlace(); PORO=null;
 CELL={kind,ad,tab:'ogl',open:-1,page:1,hex,ll};
 // у стовпчиках контуру на землі немає — вибраний стовпчик світліший (33, В6)
 if(hex&&MODE==='stovp'){const k=hexAt(hex[1]/MY_,hex[0]/MX_,hex[2])[0];
  CELL.colSel=k; CELL.colG=colG(); map.setFeatureState({source:'k-col-'+CELL.colG,id:k},{sel:true})}
 else if(hex) map.getSource('k-hexsel').setData({type:'FeatureCollection',features:[{type:'Feature',
  geometry:{type:'Polygon',coordinates:hexPoly(hex[0],hex[1],hex[2])},properties:{}}]});
 renderCell(); if(hex) nadShtorkoyu(hex[1]/MY_,hex[0]/MX_)}
function closeCell(){
 if(CELL&&CELL.colSel!==undefined&&map.getSource('k-col-'+CELL.colG)) map.setFeatureState({source:'k-col-'+CELL.colG,id:CELL.colSel},{sel:false});
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
  if(CELL.hex){const [cx,cy,R_]=CELL.hex; body+=rizykRiadok(rizykPoruch(cy/MY_,cx/MX_,R_))}
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
 const x=t.closest('[data-kp="close"]'); if(x){e.stopImmediatePropagation(); return closeCell()}
 const ct=t.closest('[data-ct]'); if(ct){CELL.tab=ct.dataset.ct; SK_LIM=50; return renderCell()}
 const cv=t.closest('[data-cv]'); if(cv){const gi=+cv.dataset.cv; CELL.open=CELL.open===gi?-1:gi; return renderCell()}
 const cp=t.closest('[data-cp]'); if(cp){const i=+cp.dataset.cp; closeCell(); return openAt(i)}
 if(t.closest('[data-cmore]')){CELL.page++; return renderCell()}
 // «Показати адреси» — вигляд «Адреси» на тому самому місці й масштабі; на
 // телефоні фільтри не розгортаються, лише підказка з поверненням (36.27.2)
 if(t.closest('[data-ca]')){closeCell(); setView('addr'); return adresyPidkazka()}
 if(t.closest('[data-link]')) return kopiyuvaty(CELL.hex?`c=${CELL.hex[2]},${(CELL.hex[1]/MY_).toFixed(5)},${(CELL.hex[0]/MX_).toFixed(5)}`:'',t.closest('[data-link]'));
 if(t.closest('[data-cz]')){let s=90,w=180,n=-90,ea=-180;
  for(const i of CELL.ad){const p=P[i]; if(p[0]<s)s=p[0]; if(p[0]>n)n=p[0]; if(p[1]<w)w=p[1]; if(p[1]>ea)ea=p[1]}
  map.fitBounds([[w,s],[ea,n]],{padding:sidePad(),maxZoom:16.5,duration:900})}
},true);
document.addEventListener('keydown',e=>{ if(e.key!=='Escape') return; bezPosylannia(); if(CELL) closeCell()});
// ==== ПОСИЛАННЯ НА МІСЦЕ (SPECYFIKATSIYA S-К.23; RISHENNYA 35.9) ====
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
  // посилання на проблему відкриває саме її картку (S-К.23); без механізму — адресу
  afterMove(()=>{openAt(best); if(mech){PLACE.pi=j; PLACE.prob=true; renderPlace()}});
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
// ==== ВИГЛЯДИ: «Соти · Кільця · Адреси» + «3D» у сотах (36.55) ====
// «Проблеми» — перемикач «лише проблеми» в рядку з «Ризиком» (36.65). За замовчуванням — соти;
// вибір пам'ятає браузер. 3D (усередині MODE 'stovp') — кнопка над картою
// лише в сотах; нахил — від зуму, вимкнули — 0°.
function setView(v){
 const was=MODE; MODE=v; try{localStorage.setItem('karta-vyhlyad',v)}catch(e){}
 document.querySelectorAll('#fcat [data-m]').forEach(x=>swSet(x,x.dataset.m===v||(v==='stovp'&&x.dataset.m==='soty')));
 d3Btn();
 if(v==='stovp'&&was!=='stovp') map.easeTo({pitch:pitch3d(),duration:700});
 if(v!=='stovp'&&was==='stovp') map.easeTo({pitch:0,duration:700});
 // Зміна вигляду скидає вибір і контури попереднього (33, В4): шестикутник
 // вибраної соти висів у «Кільцях» поруч із кільцем
 if(v!==was){ if(CELL) closeCell(); if(POPUP) POPUP.remove(); bezPosylannia();
  if(map.getSource('k-hexsel')) map.getSource('k-hexsel').setData({type:'FeatureCollection',features:[]})}
 draw()}
// Кругла кнопка «3D»/«2D» справа вгорі, ≥44 px; видно лише в сотах
function d3Btn(){let b=$('#f3d');
 if(!b){b=document.createElement('button'); b.id='f3d'; b.type='button';
  b.onclick=()=>setView(MODE==='stovp'?'soty':'stovp'); map.getContainer().appendChild(b)}
 b.hidden=!(MODE==='soty'||MODE==='stovp'); b.textContent=MODE==='stovp'?'2D':'3D';
 b.setAttribute('aria-pressed',String(MODE==='stovp'))}
// Перетнули поріг зуму — стара група стовпчиків порожніє, виділення з неї
// знімається; нахил — за новим зумом
// вибраний стовпчик старої групи осів — виділення знімається
map.on('zoomend',()=>{ if(MODE==='stovp'&&CELL&&CELL.colSel!==undefined&&CELL.colG!==colG()) closeCell()});
map.on('zoomend',()=>{ if(MODE==='stovp'&&Math.abs(map.getPitch()-pitch3d())>2) map.easeTo({pitch:pitch3d(),duration:300})});
{const VIEWS=[['soty','Соти'],['rings','Кільця'],['addr','Адреси']];
 let v=null; try{v=localStorage.getItem('karta-vyhlyad')}catch(e){}
 const seg=$('#fcat');
 seg.innerHTML=VIEWS.map(([k,n])=>`<button data-m="${k}" title="${n}" aria-pressed="false">${n}</button>`).join('');
 seg.onclick=e=>{const b=e.target.closest('[data-m]'); if(b) setView(b.dataset.m)};
 MODE=VIEWS.some(x=>x[0]===v)||v==='stovp'?v:'soty';
 seg.querySelectorAll('[data-m]').forEach(x=>swSet(x,x.dataset.m===MODE||(MODE==='stovp'&&x.dataset.m==='soty')));
 d3Btn();
 const fp=$('#fprob'); fp.hidden=false; swSet(fp,false);
 fp.onclick=e=>{ONLYP=!ONLYP; swSet(fp,ONLYP); draw()};
 if(MODE==='stovp') map.once('load',()=>map.easeTo({pitch:pitch3d(),duration:0}));}
// ---- клік і наведення по сотах і стовпчиках ----
function hexHit(p){ if(MODE!=='soty'&&MODE!=='stovp') return null;
 const ids=[]; for(const G of HEXG) ids.push((MODE==='soty'?'k-hex-':'k-col-')+G.id);
 const f=map.queryRenderedFeatures(p,{layers:ids.filter(id=>map.getLayer(id))});
 if(!f.length) return null;
 // з кількох сіток — та, що зараз видніша
 const id=colG(), g=f.find(x=>x.layer.id.endsWith(id))||f[0];
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
  VTIP.setLngLat(e.lngLat).setHTML(pidkazkaSoty(h.b)).addTo(map); return}
 VTIP.remove()});
// над стовпчиком — лише він сам: скільки подій і чий колір (33, В6); окремою
// функцією — її ж викликає перевірка узгодженості (window.KT)
function pidkazkaSoty(b){const a=new Set(b.ad).size;
 return MODE==='stovp'?`<b>${fmt(b.n)} ${pl(b.n,'подія','події','подій')} · ${esc(lc(shortOf(b.gi)))}</b>`
  :`<b>${fmt(b.n)} ${pl(b.n,'подія','події','подій')} · ${fmt(a)} ${pl(a,'адреса','адреси','адрес')}</b>`}
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
// ==== ТЕЛЕФОН (36.27, макет «Картка на телефоні») ====
const telefon=()=>matchMedia('(max-width:700px)').matches;
// Дотик до шапки будь-якої картки — шторка на весь екран і назад
placeEl().addEventListener('click',e=>{ if(!telefon()) return;
 if(e.target.closest('.kp-head')&&!e.target.closest('button,a')) placeEl().classList.toggle('kp-tall')});
// «Показати адреси»: коротка підказка замість розгорнутих фільтрів (п. 5 макета)
function adresyPidkazka(){ if(!telefon()) return;
 let h=document.getElementById('kadresy-hint');
 if(!h){h=document.createElement('div'); h.id='kadresy-hint'; map.getContainer().appendChild(h);
  h.addEventListener('click',e=>{ if(e.target.closest('button')){setView('soty'); h.hidden=true}})}
 h.innerHTML='Показано адреси · <button>Соти ↺</button>'; h.hidden=false;
 clearTimeout(h._t); h._t=setTimeout(()=>{h.hidden=true},6000)}
// ==== БУДЬ-ЯКА АДРЕСА КИЄВА КЛІКАБЕЛЬНА (S-А.15, RISHENNYA 36.18.4) ====
// Адреси без подій — файлами adresy/<клітинка>.json (map_adresy.py), лише з
// z15 і лише видимі клітинки: перше завантаження не росте. На карті їх не
// видно — клік у вигляді «Адреси» по будинку без подій відкриває картку
// «0 подій» з вкладкою «Скарги», якщо мешканці скаржились на цей будинок.
const ADR_Z=15, ADR_KL=[0.018,0.028], ADRESY=new Map();
const adresyKl=(la,lo)=>Math.floor(la/ADR_KL[0])+'_'+Math.floor(lo/ADR_KL[1]);
function adresyZavantazhyty(){ if(map.getZoom()<ADR_Z) return;
 const b=map.getBounds();
 for(let la=Math.floor(b.getSouth()/ADR_KL[0]);la<=Math.floor(b.getNorth()/ADR_KL[0]);la++)
  for(let lo=Math.floor(b.getWest()/ADR_KL[1]);lo<=Math.floor(b.getEast()/ADR_KL[1]);lo++){const k=la+'_'+lo;
   if(ADRESY.has(k)) continue; ADRESY.set(k,null);
   fetch('adresy/'+k+'.json').then(r=>r.ok?r.json():{}).catch(()=>({})).then(d=>ADRESY.set(k,(d.a||[]).map(x=>[x[0]/1e5,x[1]/1e5,x[2],x[3]])))}}
map.on('moveend',adresyZavantazhyty);
// найближча порожня адреса в 14 px від кліку
function porozhniaAt(pt){ if(MODE!=='addr'||map.getZoom()<ADR_Z) return null;
 const ll=map.unproject(pt), k=adresyKl(ll.lat,ll.lng); let best=null,bd=Math.max(14,HIT_R);
 for(const [kk,xs] of ADRESY){ if(!xs) continue; const [a,b]=kk.split('_').map(Number), [c,d]=k.split('_').map(Number);
  if(Math.abs(a-c)>1||Math.abs(b-d)>1) continue;
  for(const x of xs){const q=map.project([x[1],x[0]]), dd=Math.hypot(q.x-pt.x,q.y-pt.y); if(dd<bd){bd=dd;best=x}}}
 return best}
let PORO=null;   // {a:[шир, довг, підпис, [скарги]], tab}
function openPorozhnia(a){ if(POPUP) POPUP.remove(); closePlace(); closeCell(); PORO={a,tab:'ogl'}; renderPorozhnia(); nadShtorkoyu(a[0],a[1])}
function renderPorozhnia(){const el=placeEl(); if(!PORO) return;
 const [la,lo,lab,js]=PORO.a, sk=js.length&&skargy()?js:[];
 if(js.length&&!SKG&&SKG_P) SKG_P.then(()=>{if(PORO&&PORO.a[2]===lab) renderPorozhnia()});
 if(PORO.tab==='skarg'&&!sk.length) PORO.tab='ogl';
 el.innerHTML=`<div class="kp-head"><b class="kp-title">${esc(lab)}</b><div class="kp-sum">0 подій</div>
  <button class="kp-x" data-kp="close" aria-label="Закрити (Esc)" title="Закрити (Esc)">×</button></div>
  <div class="kp-tabs" role="tablist"><button role="tab" data-pt="ogl" aria-selected="${PORO.tab==='ogl'}">Огляд</button>`+
  (sk.length?`<button role="tab" data-pt="skarg" aria-selected="${PORO.tab==='skarg'}">Скарги (${fmt(sk.length)})</button>`:'')+`</div>
  <div class="kp-body">${PORO.tab==='skarg'?skHTML(sk,SK_LIM):rizykRiadok(rizykPoruch(la,lo,50))}</div>`;
 el.hidden=false; el.classList.remove('kp-cell','kp-tall'); document.body.classList.add('kp-open')}
function closePorozhnia(){ if(!PORO) return; PORO=null; const el=placeEl();
 if(!PLACE&&!CELL){el.hidden=true; document.body.classList.remove('kp-open')}}
placeEl().addEventListener('click',e=>{ if(!PORO) return;
 const t=e.target.closest('[data-pt]'); if(t){PORO.tab=t.dataset.pt; SK_LIM=50; return renderPorozhnia()}
 if(e.target.closest('[data-kp="close"]')){e.stopImmediatePropagation(); closePorozhnia()}},true);
document.addEventListener('keydown',e=>{ if(e.key==='Escape') closePorozhnia()});
map.on('click',e=>{ if(CLICK_TAKEN||iconAt(e.point)||addrAt(e.point)) return;
 const a=porozhniaAt(e.point); if(a){CLICK_TAKEN=true; openPorozhnia(a)}});
// ==== ПОШУК (S-Ш.1–5, RISHENNYA 36.18.5, 36.18.7, 36.35) ====
// Індекс — poshuk.json (map_poshuk.py): слова назв рахує той самий adr_kliuch,
// що й геокодер; тут запит чиститься тим самим виразом типів (tw) і слова
// порівнюються з допуском на відмінок і описку. Файл тягнемо при першому
// введенні — перше завантаження карти не росте.
let PSH=null, PSH_P=null;
function poshukIndeks(){
 if(!PSH_P) PSH_P=fetch('poshuk.json').then(r=>r.ok?r.json():null).catch(()=>null).then(d=>{
  if(!d) return PSH=false;
  d.re=new RegExp(d.tw,'g'); d.w=d.s.map(x=>x[1].split(' ').filter(Boolean));
  d.alt=d.s.map(x=>x[2].map(a=>a.split(' ').filter(Boolean)));
  d.adr=new Map(); d.ps.forEach((sid,i)=>{ if(sid>=0&&P[i][3]) (d.adr.get(sid)||d.adr.set(sid,[]).get(sid)).push(i)});
  return PSH=d});
 return PSH_P}
// так само, як adr_kliuch.norm і nh
const pNorm=s=>s.toLowerCase().replace(/[’`ʼ]/g,"'").replace(PSH.re,' ').replace(/[^а-яіїєґ0-9' \-]/g,' ')
 .replace(/-/g,' ').replace(/'/g,'').replace(/\s+/g,' ').trim();
const pNh=h=>(h||'').toUpperCase().replace(/[^0-9A-ZА-ЯІЇЄҐ/]/g,'');
// номер будинку в кінці запиту: «22», «12-а», «19 б», «34 / 2», «30-32»
const P_NOMER=/(?:^|[\s,])(\d{1,4}(?:\s*-\s*\d{1,4})?(?:\s*-?\s*[а-яіїєґa-z](?![а-яіїєґa-z']))?(?:\s*\/\s*\d{1,4}(?:\s*-?\s*[а-яіїєґ](?![а-яіїєґ']))?)?)\s*$/i;
// Дамерау–Левенштейн з межею: далі межі — m+1
function pDl(a,b,m){ if(Math.abs(a.length-b.length)>m) return m+1;
 let p2=null,p=Array.from({length:b.length+1},(_,j)=>j);
 for(let i=1;i<=a.length;i++){const c=[i]; let mn=i;
  for(let j=1;j<=b.length;j++){let v=Math.min(p[j]+1,c[j-1]+1,p[j-1]+(a[i-1]===b[j-1]?0:1));
   if(p2&&i>1&&j>1&&a[i-1]===b[j-2]&&a[i-2]===b[j-1]) v=Math.min(v,p2[j-2]+1);
   c.push(v); if(v<mn) mn=v}
  if(mn>m) return m+1; p2=p; p=c}
 return p[b.length]}
// Слово запиту проти слова назви: збіг, початок, відмінок, описка (S-Ш.2:
// до 3 літер — точно, 4–7 — одна помилка, від 8 — дві). null — не те слово.
function pSlovo(w,x,vilno){
 if(x===w) return 0;
 if(x.startsWith(w)) return w.length<=2?.05:.1;
 if(w.length<=2) return null;
 if(w.length>=4&&x.length>=4){let c=0; while(c<w.length&&c<x.length&&w[c]===x[c]) c++;
  if(c>=Math.max(4,x.length-2)&&c>=w.length-3&&Math.abs(w.length-x.length)<=3) return .3}
 const lim=(w.length<=3?0:w.length<=7?1:2)+(vilno?1:0); if(!lim) return null;
 // дешевий відсів до відстані редагування: літер, яких у слові назви немає
 // зовсім, не може бути більше за допуск (S-Ш.5: ≤100 мс на телефоні)
 let chuzhi=0; for(const ch of w) if(x.indexOf(ch)<0&&++chuzhi>lim) return null;
 const d=Math.min(pDl(w,x,lim),x.length>w.length?pDl(w,x.slice(0,w.length),lim):lim+1);
 return d<=lim?d:null}
// Тип із запиту (як step2_geocode.stype) — підказка порядку: «Вокзальна площа 1»
// — спершу площа, «вул.» суди й люди пишуть про будь-що, тож вона важить мало
const P_TYPY=[[/просп|пр-т|пр\./,'просп'],[/бульв|б-р/,'бульв'],[/пров/,'пров'],[/пл\.|площ|майдан/,'пл'],
 [/(^|\s)наб/,'наб'],[/шосе/,'шосе'],[/узв/,'узвіз'],[/проїзд/,'проїзд'],[/алея|алеї/,'алея'],[/вул/,'вул']];
const pTyp=q=>{q=(q||'').toLowerCase(); for(const [re,t] of P_TYPY) if(re.test(q)) return t; return ''};
function pVulytsi(slova,vilno,typ){const out=[];
 PSH.s.forEach((v,sid)=>{let best=null;
  for(const ws of [PSH.w[sid],...PSH.alt[sid]]){let sum=0;
   for(const w of slova){let b=null; for(const x of ws){const s_=pSlovo(w,x,vilno); if(s_!==null&&(b===null||s_<b)) b=s_}
    if(b===null){sum=null; break} sum+=b}
   if(sum!==null&&(best===null||sum<best)) best=sum}
  if(best===null) return;
  const t=v[4]||'';
  if(typ&&typ!=='вул'&&t!==typ) best+=.5;
  else if(typ==='вул'&&(t==='пров'||t==='пл')) best+=.2;
  out.push([best,sid])});
 return out.sort((a,b)=>a[0]-b[0]||PSH.s[b[1]][3]-PSH.s[a[1]][3])}
// Рядки підказки: [{t:'v'|'a'|'p'|'m'|'0', підпис, n, …}]
function poshuk(q){
 if(!PSH) return [];
 q=(q||'').trim(); if(q.replace(/\s/g,'').length<3) return [];
 let dim='', m=P_NOMER.exec(q);
 // «40 жовтня річчя» — число в назві, а не номер: номер лише після слів назви
 if(m&&q.slice(0,m.index).replace(/[\s,]/g,'')){dim=pNh(m[1]); q=q.slice(0,m.index)}
 const slova=pNorm(q).split(' ').filter(Boolean); if(!slova.length) return [];
 const typ=pTyp(q); let vs=pVulytsi(slova,false,typ), mozh=false;
 if(!vs.length){vs=pVulytsi(slova,true,typ); mozh=true}
 if(!vs.length) return [{t:'0',pidpys:'Нічого не знайдено'}];
 if(mozh) return [{t:'m',pidpys:'Можливо:'}].concat(vs.slice(0,3).map(([s_,sid])=>({t:'v',sid,pidpys:PSH.s[sid][0],n:PSH.s[sid][3],slova})));
 if(dim){const out=[];
  for(const [sc,sid] of vs.slice(0,6)){
   for(const i of PSH.adr.get(sid)||[]){const h=pNh(P[i][2].split(', ').pop());
    if(h.startsWith(dim)) out.push({t:'a',i,pidpys:P[i][2],n:P[i][4].length,k:[h===dim?0:1,sc,-P[i][4].length,h.length]})}
   for(const a of PSH.a[sid]||[]){const h=pNh(a[0]);
    if(h.startsWith(dim)) out.push({t:'p',a,pidpys:PSH.s[sid][0]+', '+a[0],n:0,k:[h===dim?0:1,sc,0,h.length]})}}
  out.sort((x,y)=>{for(let j=0;j<4;j++) if(x.k[j]!==y.k[j]) return x.k[j]-y.k[j]; return 0});
  if(out.length) return out.slice(0,5)}
 return vs.slice(0,5).map(([s_,sid])=>({t:'v',sid,pidpys:PSH.s[sid][0],n:PSH.s[sid][3],slova}))}
// Збіг з набраним — жирним: слова підпису, що починаються як слова запиту
function pZhyrno(pidpys,q){const ws=pNorm(q.replace(P_NOMER,'')).split(' ').filter(w=>w.length>=2);
 return esc(pidpys).replace(/[А-Яа-яІіЇїЄєҐґ'’ʼ\-]+/g,s=>ws.some(w=>s.toLowerCase().replace(/['’ʼ]/g,'').startsWith(w.slice(0,Math.max(2,Math.min(w.length,4)))))?`<b>${s}</b>`:s)}
let PRY=[], PACT=0;
function pPokazaty(){const q=qEl.value;
 if(!PSH){ if(q.trim().length>=3&&PSH!==false) poshukIndeks().then(()=>pPokazaty()); PRY=[]; sg.hidden=true; return}
 PRY=poshuk(q); PACT=0;
 sg.innerHTML=PRY.map((r,k)=>r.t==='m'||r.t==='0'?`<div class="sgnone">${esc(r.pidpys)}</div>`
  :`<button data-k="${k}" role="option" aria-selected="${k===PACT||(PRY[0].t==='m'&&k===1)}"><span>${pZhyrno(r.pidpys,q)}</span><span class="n">${fmt(r.n)}</span></button>`).join('');
 if(PRY.length&&PRY[0].t==='m') PACT=1;
 sg.hidden=!PRY.length}
function pVybraty(r){ if(!r||r.t==='m'||r.t==='0') return;
 sg.hidden=true; qEl.value=r.pidpys; qEl.blur();
 if(r.t==='a') return focusAddress(r.i);
 if(r.t==='p'){const la=r.a[1]/1e5, lo=r.a[2]/1e5, kk=adresyKl(la,lo);
  setView('addr'); map.flyTo({center:[lo,la],zoom:17.5});
  // картка — з тієї самої клітинки, що й клік: з її скаргами
  return fetch('adresy/'+kk+'.json').then(x=>x.ok?x.json():{}).catch(()=>({})).then(d=>{
   const a=(d.a||[]).find(x=>x[0]===r.a[1]&&x[1]===r.a[2]); openPorozhnia(a?[a[0]/1e5,a[1]/1e5,a[2],a[3]]:[la,lo,r.pidpys,[]])})}
 const pts=(PSH.adr.get(r.sid)||[]).map(i=>[P[i][0],P[i][1]]).concat((PSH.a[r.sid]||[]).map(a=>[a[1]/1e5,a[2]/1e5]));
 if(pts.length) focusBounds(pts)}
qEl.removeEventListener('input',suggest);
qEl.addEventListener('input',pPokazaty);
qEl.addEventListener('focus',()=>{poshukIndeks(); if(qEl.value) pPokazaty()});
qEl.addEventListener('keydown',e=>{ if(sg.hidden) return;
 const ok=PRY.map((r,k)=>r.t==='m'||r.t==='0'?-1:k).filter(k=>k>=0); if(!ok.length) return;
 if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();
  const j=ok.indexOf(PACT), n=ok[(j+(e.key==='ArrowDown'?1:ok.length-1))%ok.length]; PACT=n;
  sg.querySelectorAll('[data-k]').forEach(b=>b.setAttribute('aria-selected',+b.dataset.k===n?'true':'false'))}
 if(e.key==='Enter'){e.preventDefault(); e.stopImmediatePropagation(); pVybraty(PRY[PACT])}
 if(e.key==='Escape'){sg.hidden=true}},true);
sg.onclick=e=>{const b=e.target.closest('[data-k]'); if(b) pVybraty(PRY[+b.dataset.k])};
document.addEventListener('click',e=>{ if(!e.target.closest('.search')&&!e.target.closest('#sugg')) sg.hidden=true});
// Місток для автоматичної перевірки узгодженості (test_uzhodzhenist.py, S-К.14):
// скрипт — модуль, і ззовні його змінних не видно. Лише читання й ті самі дії,
// що й кліки людини; на вигляд карти не впливає.
// Картки будуються тими самими renderPlace / renderCell, але без зсуву карти
// (openAt підсуває точку з-під картки, а переліт у браузері без відеокарти
// коштує секунди) — так 300 місць перевіряються за одне відкриття сторінки.
const ktNum=s=>{const m=/\d[\d\s  ]*/.exec(s||''); return m?+m[0].replace(/\D/g,''):null};
window.KT={get ready(){return STYLE_OK&&!!LASTST}, get st(){return LASTST}, map, P, PIDX,
 pala:g=>PALA[g%PALA.length], probsOf, setView, openAt, closePlace, openCell, closeCell, hexb:id=>HEXB[id], MX_, MY_,
 kolirMisca, pidkazkaAdresy, pidkazkaSoty, poshuk, poshukIndeks, kolaAdres:()=>ADDR_F, soty:id=>hexData(HEXG.find(G=>G.id===id),false).features,
 kartkaAdresy(i,pi=null){PLACE={i,tab:'ogl',open:-1,pi:pi??0,prob:pi!==null,allArts:true,near:[],hl:0}; renderPlace();
  const el=placeEl(), r={sum:ktNum(el.querySelector('.kp-sum')?.textContent),
   statti:[...el.querySelectorAll('.kp-body .bd td b')].map(b=>ktNum(b.textContent)),
   ryzyk:ktNum(el.querySelector('.kc-risk')?.textContent)??0, badge:el.querySelector('.kp-badge')?.textContent||''};
  PLACE=null; renderPlace(); return r},
 kartkaSoty(b,R){openCell('СОТА',b.ad,[b.cx,b.cy,R],null); const el=placeEl();
  const r={sum:ktNum(el.querySelector('.kp-sum')?.textContent),
   vydy:[...el.querySelectorAll('.kc-vydy button b')].map(x=>ktNum(x.textContent)),
   ryzyk:ktNum(el.querySelector('.kc-risk')?.textContent)??0};
  closeCell(); return r},
 rizykPoruch};
"""
