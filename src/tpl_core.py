# -*- coding: utf-8 -*-
"""Спільна частина клієнтського JavaScript — та, що не знає про рушій карти.

Тут: побудова панелі, панель рішень адреси, паспорт проблеми за SARA,
computeVis() — хто саме зараз видимий і якого кольору, — і popupHTML(),
вміст вікна адреси разом із карткою проблеми.

Жодного звертання до Leaflet чи MapLibre: цей файл входить в обидві збірки,
щоб правило кольору й склад переліку були однакові в обох. Малювання —
у tpl_draw (Leaflet) і tpl_gl (MapLibre); карта й шари — у tpl_map.

Правка картки проблеми чіпає лише цей файл.
"""
JS_CORE = r"""const $=s=>document.querySelector(s);
if(M.only){$('#subt').textContent=M.only+' район · за даними ЄДРСР';
 $('#backl').innerHTML='<a href="index.html" style="color:var(--ink);font-size:12px;text-decoration:none">← всі райони</a>';}
$('#fc').innerHTML=M.courts.map((n,i)=>`<label><input type="checkbox" data-c="${i}" checked>${n}</label>`).join('');
// На карті одного району перелік з усіх десяти районів безглуздий. Ховаємо
// саму рамку, а прапорці лишаємо в розмітці — на них спирається фільтр draw().
if(M.only){const w_=$('#fcw'); if(w_) w_.style.display='none';}
$('#fy').innerHTML=M.years.map((n,i)=>`<label><input type="checkbox" data-y="${i}" checked>${n}</label>`).join('');
const fmt=n=>n.toLocaleString('uk');
// Прапорці окремих статей лишаються, але схованими: підрівня статей у панелі
// більше немає, рядок вмикає всю тему разом. draw() і GVIS спираються саме на
// них, тому просто прибрати їх не можна.
$('#fasub').innerHTML=M.groups.map(g=>g[1].map(i=>
 `<input type="checkbox" data-a="${i}" checked>`).join('')).join('');
// Один перелік тем замість двох блоків: квадрат вмикає ПОДІЇ теми, риска
// поруч — ПРОГНОЗ РИЗИКУ тієї самої теми, праворуч від риски точність шару.
// Доти ті самі сім кольорів жили окремо в «Правопорушеннях» і в «Прогнозі
// ризику», і це плутало: здавалося, що це два різні переліки.
const RISKOF={};                         // індекс теми -> ключ її шару ризику
Object.keys(R.lines||{}).forEach(k=>{const v=R.lines[k];
 if(k.startsWith('risk_')&&(v.kind==='theme'||v.nodata)&&RISKOF[v.theme|0]===undefined)
  RISKOF[v.theme|0]=k});
$('#fasub').insertAdjacentHTML('beforeend',Object.keys(RISKOF).map(gi=>
 `<input type="checkbox" data-r="${RISKOF[gi]}">`).join(''));
$('#fa').innerHTML=M.groups.map((g,gi)=>{
 const rk=RISKOF[gi], nod=(!rk||R.lines[rk].nodata)?1:0;
 return `<div class="row" data-g="${gi}" data-on="1" data-nod="${nod}">
  <span class="sq"></span><span class="nm">${g[0]}</span><span class="n">${fmt(g[2])}</span>
  <span class="ln" data-rk="${rk||''}"></span><span class="acc"></span></div>`}).join('');
function paintRow(row){
 const gi=+row.dataset.g, ln=row.querySelector('.ln'), k=ln.dataset.rk;
 const inp=k?document.querySelector(`[data-r="${k}"]`):null, on=!!(inp&&inp.checked);
 row.querySelector('.sq').style.background=PALA[gi%PALA.length];
 ln.style.background=on?RCOL[k]:'';
 row.querySelector('.acc').textContent=
   on&&R.lines[k]&&R.lines[k].hit!=null?R.lines[k].hit+'%':'';
}
function paintRows(){document.querySelectorAll('#fa .row').forEach(paintRow)}
$('#fa').onclick=e=>{
 const row=e.target.closest('.row'); if(!row) return;
 if(e.target.classList.contains('ln')){
  if(row.dataset.nod==='1') return;      // замало подій для навчання моделі
  const inp=document.querySelector(`[data-r="${e.target.dataset.rk}"]`);
  inp.checked=!inp.checked; paintRow(row); drawRisks(); return}
 const on=row.dataset.on!=='0';
 M.groups[+row.dataset.g][1].forEach(i=>{
  const b=document.querySelector(`[data-a="${i}"]`); if(b) b.checked=!on});
 row.dataset.on=on?'0':'1'; draw()};
function syncThemes(){document.querySelectorAll('#fa .row').forEach(row=>{
 const ids=M.groups[+row.dataset.g][1];
 row.dataset.on=ids.some(i=>document.querySelector(`[data-a="${i}"]`).checked)?'1':'0'})}
const PERIODS=[['Ранок','6–11',[6,7,8,9,10,11]],['День','12–17',[12,13,14,15,16,17]],
 ['Вечір','18–23',[18,19,20,21,22,23]],['Ніч','0–5',[0,1,2,3,4,5]]];
// Документи кроку 6. Версія одна, тож посилання однакові для всіх.
$ify('#docs',
 '<a href="doslidzhennya.html" target="_blank" rel="noopener">Дослідження ризиків<em>HTML</em></a>'+
 '<a href="rezyume.html" target="_blank" rel="noopener">Резюме на одну сторінку<em>HTML</em></a>'+
 '<a href="analiz.html" target="_blank" rel="noopener">Аналіз поточного стану<em>HTML</em></a>');
// Три режими — три відповіді на одне питання «що показувати». Теплова карта
// доти була окремою кнопкою збоку й читалася як ще один фільтр поверх решти.
const MODES=[['all','Усі'],['prob','Проблеми'],['heat','Теплова']];
let MODE='all';
const cb_=$('#fcat');
cb_.innerHTML=MODES.map(([k,n])=>
 `<button data-m="${k}"${k===MODE?' aria-pressed="true"':''}>${n}`+
 (k==='prob'?`<i>${M.n_problems||''}</i>`:'')+'</button>').join('');
cb_.onclick=e=>{const b=e.target.closest('[data-m]'); if(!b) return;
 MODE=b.dataset.m;
 cb_.querySelectorAll('button').forEach(x=>
   x.setAttribute('aria-pressed',x===b?'true':'false'));
 draw()};
const CATNAME={2:['Проблема','var(--ink)','у кураторському списку'],0:null};
const hb=$('#hr');
PERIODS.forEach((p,i)=>{const s=document.createElement('span');
 s.innerHTML=`${p[0]}<i>${p[1]}</i>`;s.dataset.p=i;hb.appendChild(s)});
hb.onclick=e=>{const t=e.target.closest('[data-p]');if(t){t.classList.toggle('on');draw()}};
const sel=a=>new Set([...document.querySelectorAll(`[data-${a}]`)].filter(x=>x.checked).map(x=>+x.dataset[a]));
// ---- ПРАВА ПАНЕЛЬ: усі рішення адреси ----
// Витяг обставин і посилання на папери лежать окремо від сторінки: на сайті
// це файл spravy/<район>.json, який тягнемо, коли панель відкривають уперше.
// У сторінці, відкритій з диска, DOCS уже вкладено — тоді нічого не тягнемо.
const esc=t=>String(t==null?'':t).replace(/[&<>"]/g,c=>
 ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const lc=s=>s?s.charAt(0).toLowerCase()+s.slice(1):s;
const REESTR='https://od.reyestr.court.gov.ua/files/';
const docUrl=h=>REESTR+h.slice(0,2)+'/'+h.slice(2)+'.rtf';
function docsFor(i){
 const sl=(M.dslug||[])[(P[i]||[])[8]]||'inshe';
 if(!DOCCACHE[sl]) DOCCACHE[sl]=fetch('spravy/'+sl+'.json')
   .then(r=>r.ok?r.json():{}).catch(()=>null);
 return DOCCACHE[sl].then(o=>o?(o[i]||[]):null);
}
function closePanel(){$('#pan').classList.remove('on')}
function openPanel(i){
 const p=P[i]; if(!p) return;
 $('#pan').classList.add('on');
 $('#panh').innerHTML='<button id="panx" title="Закрити">&times;</button>'+
  `<div class="pa">${esc(p[2]||'адреса не визначена')}</div>`+
  '<div class="ps">завантажую…</div>';
 $('#panx').onclick=closePanel;
 $('#panb').innerHTML='';
 docsFor(i).then(cs=>{
  if(cs===null){
   $('#panh').querySelector('.ps').textContent='перелік рішень недоступний';
   $('#panb').innerHTML='<div class="sub">Карту відкрито як файл із диска, а '+
     'перелік рішень лежить окремим файлом поруч — браузер такому файлу читати '+
     'сусідів не дозволяє. Відкрийте карту з сайту або запустіть '+
     '<b>PODYVYTYSYA.bat</b>.</div>';
   return;
  }
  // панель слухається тих самих фільтрів, що й карта: інакше в ній були б
  // рішення, яких на карті зараз не видно
  const A=sel('a'), Y=new Set([...sel('y')].map(k=>M.years[k]));
  const H=new Set(); hb.querySelectorAll('.on').forEach(x=>
    PERIODS[+x.dataset.p][2].forEach(h=>H.add(h)));
  const vis=cs.filter(c=>A.has(c[0])
    && (Y.has((c[1]||'').slice(0,4))||Y.has('раніше'))
    && (!H.size||H.has(c[2])));
  $('#panh').querySelector('.ps').textContent =
    vis.length===cs.length ? `${cs.length} ${cs.length===1?'справа':'справ'}`
    : `${vis.length} з ${cs.length} справ за поточним фільтром`;
  $('#panb').innerHTML = vis.length ? vis.map(c=>{
   // повну назву статті тут не повторюємо на кожному рядку — вона є в картці
   // проблеми й у підказці таблиці; тут важать дата, стаття й обставини
   return '<div class="cs">'+
    `<div class="cd" title="${esc(LAW(M.cats[c[0]]))}"><b>${esc(c[1]||'')}</b>${c[2]>=0?' · '+String(c[2]).padStart(2,'0')+':00':''} · ${esc(M.cats[c[0]])}</div>`+
    (c[3]?`<div class="cn">справа ${esc(c[3])}</div>`:'')+
    (c[5]?`<div class="cx">${esc(c[5])}</div>`:'')+
    ((c[4]||[]).length?'<div class="cl">'+c[4].map((h,k)=>
      `<a href="${docUrl(h)}" target="_blank" rel="noopener">${(c[4].length>1?'рішення '+(k+1):'відкрити рішення')}</a>`).join('')+'</div>':'')+
    '</div>';
  }).join('') : '<div class="sub">За поточним фільтром рішень немає.</div>';
 });
}
document.addEventListener('keydown',e=>{if(e.key==='Escape')closePanel()});
// Що доречно для поточного вигляду. У місті — міський перелік проблем,
// у районі — перелік цього району. Район точки порахований у Python (p[8]),
// тому перемикання коштує одного порівняння чисел, а не геометрії.
const probsOf=p=>{const a=p[7]||[];
 return CURD<0?a.filter(q=>q.city):a.filter(q=>q.d===CURD&&q.loc)};
const inScope=p=>CURD<0||p[8]===CURD;
// Лічильники бічної панелі рахуються з того, що справді видно: у районі
// стояли б міські числа, а це та сама помилка, що вже виправлялася раніше.
function recount(){
 const c=new Array(M.cats.length).fill(0);
 for(const p of P){if(!inScope(p))continue;for(const e of p[4])c[e[1]]++}
 return c;
}
// Перелік районів у панелі. У щільному центрі клікнути по багатокутнику майже
// неможливо — його закривають позначки подій, тому головний шлях у район саме
// тут, а клік по карті лишається зручним доповненням.
if(DN.length&&!M.only){
 const dev=(M.dtheme||[]).map(o=>Object.values(o||{}).reduce((a,b)=>a+b,0));
 $('#fd').innerHTML=DN.map((n,i)=>{
  const np=(M.dprob||[])[i]||0;
  const sub=np?`${np} ${np===1?'проблема':'проблем'}`:(dev[i]?fmt(dev[i])+' подій':'');
  return `<span data-d="${i}">${n}<i>${sub}</i></span>`}).join('');
 $('#fd').onclick=e=>{const t=e.target.closest('[data-d]'); if(!t)return;
  const i=+t.dataset.d; if(i===CURD) exitDistrict(); else enterDistrict(i)};
}else{const w=$('#fdw'); if(w) w.style.display='none'}
function paintDistrictList(){
 document.querySelectorAll('#fd [data-d]').forEach(el=>
  el.classList.toggle('on', +el.dataset.d===CURD));
}
function onScopeChange(){
 if(M.only){draw();return}                    // окремий файл району — перемикати нічого
 paintDistrictList();
 const c=recount();
 document.querySelectorAll('#fa .row').forEach(row=>{
  const g=M.groups[+row.dataset.g];
  row.querySelector('.n').textContent=fmt(g[1].reduce((a,i)=>a+c[i],0))});
 if(CURD<0){
  $('#subt').textContent='за даними ЄДРСР · місто Київ';
  $('#backl').innerHTML='';
 }else{
  $('#subt').textContent=DN[CURD]+' район';
  $('#backl').innerHTML='<a href="#" class="upl">← усе місто</a>';
  $('#backl').querySelector('.upl').onclick=e=>{e.preventDefault();exitDistrict()};
 }
 draw();
}
function buildPassport(p,pr){
 const today=new Date().toISOString().slice(0,10);
 let t=`# Паспорт проблеми (SARA)\n\n`;
 t+=`**Адреса:** ${p[2]||'не визначена'}\n`;
 t+=`**Механізм:** ${pr.mech}\n**Дата формування:** ${today}\n\n`;
 t+=`## Scanning\n\n`;
 t+=`- Подій за напрямком: **${pr.n}** (усього на адресі — ${pr.core_n})\n`;
 t+=`- Роки повторення: ${pr.years.join(', ')}\n`;
 t+=`- Склад:\n`+pr.arts.map(a=>{const ln=LAW(a[0]);
   return `    - ${a[0]} — ${a[1]}`+(ln?`\n      ${ln}`:'')}).join('\n')+`\n\n`;
 t+=`## Analysis\n\n`;
 // Паспорт іде до балансоутримувача — тут ціна перебільшення найвища.
 // Доти сюди писалися «чинники середовища» з вагами («ринки_250м (вага
 // 0.068)»): це коефіцієнти ШАРУ, однакові для всіх адрес теми, і виглядали
 // вони як розбір саме цієї адреси. Лист із таким рядком не витримав би
 // першого ж питання «з чого ви це взяли».
 if(pr.analysis){
  t+=`Вулиця, на якій стоїть адреса, входить у верхні ${100-pr.analysis.pc}% міста за `+
     `прогнозом моделі для цієї теми. Модель навчена на ${pr.analysis.train} подіях `+
     `і перевірена на ${pr.analysis.test} подіях наступних років: у верхні 10% вулиць `+
     `за прогнозом потрапляє ${pr.analysis.hit}% подій тих років.\n\n`;
  t+=`Які саме умови підняті на цьому відрізку — у вікні вулиці на карті, шар `+
     `«Прогноз ризику». Сюди їх свідомо не переписано: модель міряє умови ВУЛИЦІ, `+
     `а не будинку, і видавати їх за розбір адреси було б перебільшенням.\n\n`;
 } else {
  t+=`Модель не пояснює це скупчення умовами середовища — причину треба встановити на місці `+
     `(польовий підрахунок, опитування, огляд).\n\n`;
 }
 t+=`**Гіпотеза причини (заповнити на місці):**\n\n_____\n\n`;
 t+=`## Response\n\n**Тип втручання:** _____\n**Адресат:** _____\n**Горизонт:** _____\n\n`;
 t+=`## Assessment\n\n**Критерій спростування (як дізнатись, що не спрацювало):** _____\n\n`;
 t+=`**Дата повторної перевірки:** _____\n`;
 return t;
}
function downloadPassport(p,pr){
 const txt=buildPassport(p,pr);
 const blob=new Blob([txt],{type:'text/markdown;charset=utf-8'});
 const a=document.createElement('a');
 a.href=URL.createObjectURL(blob);
 a.download='pasport_'+(p[2]||'problema').replace(/[^a-zA-Zа-яА-ЯіїєІЇЄ0-9]+/g,'_').slice(0,60)+'.md';
 document.body.appendChild(a);a.click();document.body.removeChild(a);
}
window.__downloadPassport=downloadPassport;
// ---- ЩО ЗАРАЗ ВИДНО ----
// Чиста частина малювання: які адреси показувати, скільки на них подій за
// фільтром і якого кольору кожна крапка. Жодного звертання до карти — цим
// користуються обидві збірки, щоб правило кольору лишалося одне на дві.
function computeVis(){
 syncThemes();
 const C=sel('c'),A=sel('a'),Y=sel('y');
 // які теми зараз видимі за фільтром статей. Від цього набору залежать картки
 // проблем, склад переліку проблем і лічильник — інакше при фільтрі
 // «Насильство» знизу висіла картка про ДТП. Період сюди свідомо не входить:
 // обраний рік — це «покажи події цього року», а не «адреса перестала бути
 // проблемою», і перелік від періоду не пересортовується.
 const GVIS=new Set();M.groups.forEach((g,gi)=>{if(g[1].some(i=>A.has(i)))GVIS.add(gi)});
 const CF=MODE==='prob'?2:-1;
 const H=new Set();
 hb.querySelectorAll('.on').forEach(x=>PERIODS[+x.dataset.p][2].forEach(h=>H.add(h)));
 let tot=0;const vis=[];
 for(const p of P){
  if(!inScope(p)) continue;
  const ownProbs=probsOf(p);
  // проблема за прихованим напрямком — не проблема для поточного вигляду:
  // саме звідси в переліку бралися адреси з трьома подіями. У вікні підпис
  // про інший напрямок лишається, він корисний.
  const visProbs=ownProbs.filter(pr=>pr.thi===undefined||pr.thi<0||GVIS.has(pr.thi));
  if(CF>=0&&!visProbs.length) continue;
  let n=0;const cnt={};
  for(const e of p[4]) if(C.has(e[0])&&A.has(e[1])&&Y.has(e[2])&&(!H.size||H.has(e[3]))){
   n++;const t_=CATTH[e[1]];cnt[t_]=(cnt[t_]||0)+1}
  if(!n) continue;
  // Напрямок адреси-проблеми: тема, за якою епізодів більше. Рахується з
  // самих проблем, тому фільтри його не зрушують — Володимирська лишається
  // майновою, хоч би які галочки знімали.
  // Рівність в обох виборах нижче віддає першій темі за порядком M.groups:
  // сіре вже означає «центр вулиці», і нічия не має виглядати так само.
  let thProblem=null;
  if(ownProbs.length){
   const byTheme=new Array(M.groups.length).fill(0);
   for(const pr of ownProbs) if(pr.thi>=0) byTheme[pr.thi]+=pr.n;
   let bestN=0;
   for(let gi=0;gi<byTheme.length;gi++) if(byTheme[gi]>bestN){bestN=byTheme[gi];thProblem=gi}
  }
  // Переважна тема серед ПОКАЗАНОГО, за кількістю. Доти колір брався з першої
  // події в масиві — звідси й синя Борщагівська, де найбільше ДТП. Рахується
  // окремо від кольору, бо йде ще й у рядок частки у вікні.
  let thMaj=null,bestC=0;
  for(let gi=0;gi<M.groups.length;gi++) if((cnt[gi]||0)>bestC){bestC=cnt[gi];thMaj=gi}
  // Колір описує саме цю намальовану крапку, тож перевіряємо не галочку теми,
  // а чи є події напрямку за фільтром, з роком і часом доби: інакше точка
  // світилася б темою, якої за обраний рік на ній немає.
  const byProblem=thProblem!==null&&cnt[thProblem]>0;
  const th=byProblem?thProblem:thMaj;
  tot+=n;vis.push([p,n,th,byProblem,cnt,thMaj])}
 vis.sort((a,b)=>b[1]-a[1]);
 // Переліку адрес у панелі більше немає — він переїздить у звіт. Лишається
 // одне число: скільки подій і на скількох адресах зараз видно.
 $('#cntl').textContent=
   `${tot.toLocaleString('uk')} подій на ${vis.length.toLocaleString('uk')} адресах`;
 // Скільки проблем у поточних межах — числом біля самого режиму, за тим самим
 // правилом, що й перелік: проблема за прихованим напрямком не рахується,
 // інакше число не сходилося б з тим, що видно на карті.
 {let q=0;P.forEach(p=>{if(inScope(p)&&probsOf(p).some(pr=>
   pr.thi===undefined||pr.thi<0||GVIS.has(pr.thi)))q++});
  const pi_=cb_.querySelector('[data-m="prob"] i');
  if(pi_) pi_.textContent=q?q.toLocaleString('uk'):'';}
 return {vis,tot,C,A,Y,H,GVIS,CF};
}
// ---- ВІКНО АДРЕСИ ----
// Готовий вузол DOM: склад подій, розклад доби, картки проблем, кнопки.
// Рушій лише показує його — у Leaflet це bindPopup, у MapLibre setDOMContent.
function popupHTML(p,n,th,byProblem,cnt,thMaj,st){
   const C=st.C,A=st.A,Y=st.Y,H=st.H,GVIS=st.GVIS;
   const ev=p[4].filter(e=>C.has(e[0])&&A.has(e[1])&&Y.has(e[2])&&(!H.size||H.has(e[3])));
   const bc={},hh=new Array(24).fill(0);let nk=0;
   ev.forEach(e=>{bc[e[1]]=(bc[e[1]]||0)+1;if(e[3]>=0){hh[e[3]]++;nk++}});
   const rows=Object.entries(bc).sort((a,b)=>b[1]-a[1]);
   const mxh=Math.max(...hh,1);
   let bars='';
   if(nk>=8){bars='<div class="hg">'+hh.map((v,i)=>
     `<i style="height:${Math.max(2,Math.round(22*v/mxh))}px" title="${i}:00 — ${v}"></i>`).join('')+
     '</div><div class="hx"><span>0</span><span>6</span><span>12</span><span>18</span><span>23</span></div>';}
   const night=hh.slice(20).concat(hh.slice(0,4)).reduce((a,b)=>a+b,0);
   const hint = nk>=8 ? `<div class="hn">${Math.round(100*night/nk)}% подій припадає на 20:00–04:00</div>` : '';
   // ---- КАРТКИ ПРОБЛЕМ (п.7.4): по одній на кожен відібраний напрямок адреси ----
   let pblock='';
   const allp=probsOf(p);
   const probs=allp.filter(pr=>pr.thi===undefined||pr.thi<0||GVIS.has(pr.thi));
   const hidden=allp.length-probs.length;
   if(!probs.length&&hidden)
    pblock=`<div class="hn">Ця адреса — у списку проблем, але за іншим напрямком `+
     `(${allp.map(x=>x.theme).join(', ')}). Увімкніть відповідні правопорушення, щоб побачити картку.</div>`;
   if(probs.length){
    pblock=probs.map((pr,pi)=>{
     let h=`<div class="pcard"><div class="ph">Проблема · ${pr.theme}</div>`;
     h+=`<div class="pt">${pr.mech}</div>`;
     // Статті названо і коротко, і юридично точно: лист балансоутримувачу
     // пишеться повною назвою з кодексу, інакше він не має ваги.
     h+=`<div class="pm"><b>Правопорушення:</b></div><ul class="art">`+
        pr.arts.map(a=>{const ln=LAW(a[0]);
         return `<li><span class="sh">${a[0]} — <b>${a[1]}</b></span>`+
                (ln?`<span class="ln">${ln}</span>`:'')+`</li>`}).join('')+`</ul>`;
     h+=`<div class="pm"><b>Чому проблема:</b> ${pr.n} однорідних подій за ${pr.years.length} `+
        `${pr.years.length===1?'рік':'роки'} (${pr.years.join(', ')}), `+
        `${Math.round(100*pr.n/Math.max(pr.core_n,1))}% усіх подій адреси цього роду.</div>`;
     // Раніше тут стояв перелік ознак моделі — «ринки_100м, ринки_250м ×
     // школи_500м». Це були коефіцієнти ШАРУ, однакові для всіх адрес теми:
     // виглядало як розбір саме цієї адреси, а було переказом моделі.
     // Тепер картка каже лише те, що справді стосується адреси — місце її
     // вулиці в міському переліку, — а виміряні умови показує кнопка.
     if(pr.analysis){
      h+=`<div class="why"><b>Що каже модель:</b> вулиця, на якій стоїть ця адреса, — `+
         `у верхніх ${100-pr.analysis.pc}% міста за ризиком (${pr.theme.toLowerCase()}). `+
         `Які саме умови тут підняті — кнопка нижче.</div>`;
     } else {
      h+=`<div class="why"><b>Що каже модель:</b> ця вулиця не входить до переліку ризикованих. `+
         `Отже, скупчення пояснюється не обстановкою вулиці, а чимось на самій адресі — `+
         `це видно тільки на місці.</div>`;
     }
     if(pr.analysis&&pr.analysis.factors&&pr.analysis.factors.length&&(F.cats||[]).length)
      h+=`<button class="pbtn2" data-nf="${pi}">Показати чинники поруч</button>`;
     h+=`<button class="pbtn" data-pp="${pi}">Взяти в роботу — паспорт SARA</button></div>`;
     return h;
    }).join('');
    if(probs.length>1) pblock+='<div class="hn" style="margin-top:4px">Кілька напрямків на адресі — кілька окремих проблем із різними причинами.</div>';
   }
   // Кнопка потрібна в КОЖНІЙ адресі, не лише у відібраних проблемах — це
   // основний хід слухача: побачив скупчення -> подивився, що довкола ->
   // висунув гіпотезу. Кнопка нічого не підказує, лише показує околиці.
   if((F.cats||[]).length)
    pblock+='<button class="pbtn2" data-na="1">Що поруч (250 м)</button>';
   const ncase=typeof p[5]==='number'?p[5]:(p[5]||[]).length;
   const cinf=probs.length?CATNAME[2]:null;
   // Частка стоїть у кожній адресі з номером будинку. Коли точку пофарбовано
   // напрямком проблеми, а подій за фільтром більше в іншої теми, це кажемо
   // окремим реченням — інакше колір і таблиця нижче суперечили б мовчки.
   const nm=gi=>esc(lc(M.groups[gi][0]));
   const majTxt=p[3]&&thMaj!==null
    ?`<div class="tt">${byProblem&&th!==thMaj?`Колір — за напрямком проблеми (${nm(th)}). `:''}`+
     `За поточним фільтром тут переважає ${nm(thMaj)}, ${cnt[thMaj]} із ${n}.</div>`:'';
   const html=`<div class="lp">
   ${cinf?`<span class="cbadge" style="background:var(--sunk);color:${cinf[1]}">${cinf[0]}</span>`:''}
   <b>${p[2]||'адреса не визначена'}</b>
   <div class="tt">${n} ${n%10===1&&n%100!==11?'подія':'подій'} за поточним фільтром</div>
   ${majTxt}
   <table class="bd">`+rows.map(([i,c])=>
     `<tr><td title="${LAW(M.cats[i])}">${M.cats[i]}</td><td><b>${c}</b></td></tr>`).join('')+`</table>
   ${bars}${hint}${pblock}
   <button class="pbtn2" data-all="1">Усі рішення (${ncase})</button>
   </div>`;
   const wrap=document.createElement('div');wrap.innerHTML=html;
   wrap.querySelectorAll('[data-pp]').forEach(b=>b.onclick=()=>downloadPassport(p,probs[+b.dataset.pp]));
   wrap.querySelectorAll('[data-nf]').forEach(b=>b.onclick=()=>{
    const q=showNear(p[0],p[1],probs[+b.dataset.nf].analysis.factors);
    b.textContent=q?`Підсвічено об’єктів: ${q}`:'Поруч нічого з чинників немає'});
   wrap.querySelectorAll('[data-all]').forEach(b=>b.onclick=()=>openPanel(P.indexOf(p)));
   wrap.querySelectorAll('[data-na]').forEach(b=>b.onclick=()=>{
    const q=showAllNear(p[0],p[1],250);
    b.textContent=q?`Показано об’єктів: ${q}`:'Поруч нічого не знайдено'});
   return wrap;
}
"""
