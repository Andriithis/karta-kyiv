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
const esc=t=>String(t==null?'':t).replace(/[&<>"]/g,c=>
 ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const lc=s=>s?s.charAt(0).toLowerCase()+s.slice(1):s;
$('#fc').innerHTML=M.courts.map((n,i)=>`<label><input type="checkbox" data-c="${i}" checked>${n}</label>`).join('');
$('#fy').innerHTML=M.years.map((n,i)=>`<label><input type="checkbox" data-y="${i}" checked>${n}</label>`).join('');
const fmt=n=>n.toLocaleString('uk');
// ---- КАРТКА-НАВІГАТОР ----
// Панель — навігатор, а не аналіз (RISHENNYA, розд. 18): жодного числа й
// жодного пояснювального напису. Числа живуть у звітах і в кільці на карті.
//
// Прапорці окремих статей лишаються, але схованими: draw() і GVIS спираються
// саме на них. Вид у сітці вмикає всі свої статті разом, «Статті» — кожну
// окремо; і те, й те пише в ці самі прапорці.
$('#fasub').innerHTML=M.groups.map(g=>g[1].map(i=>
 `<input type="checkbox" data-a="${i}" checked>`).join('')).join('');
// Шар ризику кожного виду. Окремої риски біля виду більше немає: один
// перемикач «Прогноз ризику» вмикає шари саме тих видів, що ввімкнені вище.
const RISKOF={};                         // індекс виду -> ключ його шару ризику
Object.keys(R.lines||{}).forEach(k=>{const v=R.lines[k];
 if(k.startsWith('risk_')&&(v.kind==='theme'||v.nodata)&&RISKOF[v.theme|0]===undefined)
  RISKOF[v.theme|0]=k});
$('#fasub').insertAdjacentHTML('beforeend',Object.keys(RISKOF).map(gi=>
 `<input type="checkbox" data-r="${RISKOF[gi]}">`).join('')+'<input type="checkbox" id="fquiet">');
// Короткі назви видів з макета. До перегрупування (крок 6) видів лишається
// сім; ключ — повна назва з M.groups, щоб не залежати від порядку.
const SHORT={'Громадський порядок':'Порядок','Алкоголь і торгівля':'Торгівля',
 'Наркотики':'Наркотики','Насильство проти особи':'Насильство','Майнові':'Майно',
 'Дорожній рух':'Дорожній рух','Середовище і майно громади':'Середовище'};
const shortOf=gi=>SHORT[M.groups[gi][0]]||M.groups[gi][0];
const artOn=i=>{const b=document.querySelector(`[data-a="${i}"]`);return !!(b&&b.checked)};
const setArt=(i,v)=>{const b=document.querySelector(`[data-a="${i}"]`);if(b)b.checked=v};
const typeOn=gi=>M.groups[gi][1].some(artOn);
const swSet=(b,v)=>b.setAttribute('aria-pressed',v?'true':'false');
$('#fa').innerHTML=M.groups.map((g,gi)=>
 `<button class="type" data-g="${gi}" aria-pressed="true"><i></i>${shortOf(gi)}</button>`).join('');
// Колір квадрата залежить від теми, тож стоїть інлайном. Перебудовувати сітку
// при зміні теми не можна — загубився б стан, тому фарбуємо на місці.
function paintRows(){
 document.querySelectorAll('#fa .type').forEach(b=>b.style.setProperty('--c',PALA[+b.dataset.g%PALA.length]));
 document.querySelectorAll('#advgrid h4 i').forEach(x=>x.style.background=PALA[+x.dataset.g%PALA.length]);
}
function syncThemes(){
 document.querySelectorAll('#fa .type').forEach(b=>swSet(b,typeOn(+b.dataset.g)));
 document.querySelectorAll('#advgrid [data-art]').forEach(x=>x.checked=artOn(+x.dataset.art));
}
$('#fa').onclick=e=>{
 const b=e.target.closest('.type'); if(!b) return;
 const gi=+b.dataset.g, on=typeOn(gi);
 M.groups[gi][1].forEach(i=>setArt(i,!on));
 syncRisk(); draw()};
// ---- ПРОГНОЗ РИЗИКУ ----
// Один перемикач. Шари ризику ставить код: лише для ввімкнених видів і лише
// там, де модель навчена. Вимкнули вид — зник і його ризик.
let RISK_ON=false;
function syncRisk(){
 Object.keys(RISKOF).forEach(gi=>{
  const k=RISKOF[gi], inp=document.querySelector(`[data-r="${k}"]`);
  if(inp) inp.checked=RISK_ON&&!R.lines[k].nodata&&typeOn(+gi)});
 drawRisks();
}
$('#frisk').onclick=()=>{RISK_ON=!RISK_ON; swSet($('#frisk'),RISK_ON);
 $('#friskx').hidden=!RISK_ON; syncRisk()};
// «Тихі вулиці» — інший погляд на ті самі шари ризику, тож їх видно лише
// тоді, коли прогноз увімкнено.
$('#fquietc').onclick=()=>{const q=$('#fquiet'); q.checked=!q.checked;
 swSet($('#fquietc'),q.checked); drawRisks()};
// ---- КОНТЕКСТ ----
// Потоки — один перемикач на всі три: розділяються вони на самій карті.
const CTX={pop:['pop'],flows:['flow_school','flow_transit','flow_shop']};
// Поріг зуму для шарів, які з міського огляду нечитабельні. Замість напису
// «наблизьте карту» стан показує сам перемикач: поки масштаб замалий, він
// приглушений і не натискається. Новий шар із порогом — один рядок тут.
const ZGATE={facts:FZOOM};
{const has={pop:POP.length>0,flows:CTX.flows.some(k=>R.lines&&R.lines[k]),
            facts:(F.cats||[]).some(c=>c.pts.length)};
 document.querySelectorAll('#fctx [data-ctx]').forEach(b=>{if(!has[b.dataset.ctx]) b.hidden=true});}
$('#fctx').onclick=e=>{
 const b=e.target.closest('[data-ctx]'); if(!b||b.getAttribute('aria-disabled')==='true') return;
 const k=b.dataset.ctx, v=b.getAttribute('aria-pressed')!=='true'; swSet(b,v);
 if(k==='facts'){document.querySelectorAll('[data-f]').forEach(x=>x.checked=v); drawFacts(); return}
 CTX[k].forEach(r=>{const inp=document.querySelector(`[data-r="${r}"]`); if(inp) inp.checked=v});
 drawRisks()};
function paintZoomGates(){
 const z=map.getZoom();
 document.querySelectorAll('#fctx [data-ctx]').forEach(b=>{
  const need=ZGATE[b.dataset.ctx];
  b.setAttribute('aria-disabled',need!==undefined&&z<need?'true':'false')});
}
const PERIODS=[['Ранок','6–11',[6,7,8,9,10,11]],['День','12–17',[12,13,14,15,16,17]],
 ['Вечір','18–23',[18,19,20,21,22,23]],['Ніч','0–5',[0,1,2,3,4,5]]];
// Звіти кроку 6 — три посилання на виду. Версія одна для всіх.
$ify('#docs',
 '<a href="doslidzhennya.html" target="_blank" rel="noopener">Дослідження ризиків <span>↗</span></a>'+
 '<a href="rezyume.html" target="_blank" rel="noopener">Резюме на одну сторінку <span>↗</span></a>'+
 '<a href="analiz.html" target="_blank" rel="noopener">Аналіз поточного стану <span>↗</span></a>');
// Три режими — три відповіді на одне питання «що показувати». Теплова карта
// доти була окремою кнопкою збоку й читалася як ще один фільтр поверх решти.
const MODES=[['all','Події'],['prob','Проблеми'],['heat','Теплова']];
let MODE='all';
const cb_=$('#fcat');
cb_.innerHTML=MODES.map(([k,n])=>
 `<button data-m="${k}" aria-pressed="${k===MODE}">${n}</button>`).join('');
cb_.onclick=e=>{const b=e.target.closest('[data-m]'); if(!b) return;
 MODE=b.dataset.m;
 cb_.querySelectorAll('button').forEach(x=>swSet(x,x===b));
 draw()};
const CATNAME={2:['Проблема','var(--ink)','у кураторському списку'],0:null};
const hb=$('#hr');
PERIODS.forEach((p,i)=>{const s=document.createElement('span');
 s.innerHTML=`${p[0]}<i>${p[1]}</i>`;s.dataset.p=i;hb.appendChild(s)});
hb.onclick=e=>{const t=e.target.closest('[data-p]');if(t){t.classList.toggle('on');draw()}};
const sel=a=>new Set([...document.querySelectorAll(`[data-${a}]`)].filter(x=>x.checked).map(x=>+x.dataset[a]));
// ---- «РОЗШИРЕНО»: КОЖНА СТАТТЯ ОКРЕМО ----
// Підпис статті в даних — «ст.124 КУпАП · ДТП з пошкодженням майна»:
// назву звичайними словами показуємо рядком, номер статті — дрібно під нею.
const splitArt=s=>{const m=/^(ст\.[^·]+?)\s*·\s*(.+)$/.exec(s||'');return m?[m[2],m[1]]:[s,'']};
// Дорожній рух — найбільший вид, тож усередині поділений на три частини
// (склад — RISHENNYA, розд. 18). Це групування, а не окремий вид і не
// окремий колір: сьомий колір на темній темі не проходить перевірку для
// дальтоніків. Стаття руху, якої немає в переліку, іде в «Інше».
const ROAD={'ДТП':['124 КУпАП','122-4 КУпАП','123 КУпАП','286 КК'],
 'За кермом':['130 КУпАП','126 КУпАП','122-2 КУпАП','121 КУпАП','122 КУпАП','287 КК'],
 'Інше':['139 КУпАП','140 КУпАП','127 КУпАП','277 КК']};
const roadPart=label=>{const m=/^ст\.([\d\-]+)\s+(КУпАП|КК)/.exec(label||'');
 if(m){const key=m[1]+' '+m[2]; for(const part in ROAD) if(ROAD[part].includes(key)) return part}
 return 'Інше'};
const ROADGI=M.groups.findIndex(g=>g[0]==='Дорожній рух');
$('#advgrid').innerHTML=M.groups.map((g,gi)=>{
 // порядок усередині виду — за кількістю подій; самі числа не показуємо
 const ids=g[1].slice().sort((a,b)=>(M.counts[b]||0)-(M.counts[a]||0));
 const art=i=>{const [nm,no]=splitArt(M.cats[i]);
  return `<label class="art"><input type="checkbox" data-art="${i}" checked>`+
         `<span>${esc(nm)}<small>${esc(no)}</small></span></label>`};
 let h=`<div class="ag"><h4><i data-g="${gi}"></i>${shortOf(gi)}</h4>`;
 if(gi===ROADGI){
  for(const part of Object.keys(ROAD)){
   const inPart=ids.filter(i=>roadPart(M.cats[i])===part); if(!inPart.length) continue;
   h+=`<h5><span>${part}</span><button data-only="${part}">лише це</button></h5>`+inPart.map(art).join('');
  }
 } else h+=ids.map(art).join('');
 return h+'</div>'}).join('');
$('#advgrid').onchange=e=>{const x=e.target.closest('[data-art]'); if(!x) return;
 setArt(+x.dataset.art,x.checked); syncThemes(); syncRisk(); draw()};
// «лише це» вмикає статті однієї частини руху й вимикає решту статей руху;
// інших видів не чіпає.
$('#advgrid').onclick=e=>{const b=e.target.closest('[data-only]'); if(!b) return;
 M.groups[ROADGI][1].forEach(i=>setArt(i,roadPart(M.cats[i])===b.dataset.only));
 syncThemes(); syncRisk(); draw()};
function advOpen(v){$('#adv').hidden=!v; $('#advbtn').setAttribute('aria-expanded',v?'true':'false');
 $('#advbtn').textContent=v?'Розширено ‹':'Розширено ›'}
$('#advbtn').onclick=()=>advOpen($('#adv').hidden);
$('#advx').onclick=()=>advOpen(false);
// Лише точні адреси: лише події класу B (e[4]===0) — вулицю адреси названо
// в описі самої події (ZAVDANNYA-ADRESY.md, п.5). Решта могла взяти адресу з
// чужого речення. Центрів вулиць на карті немає й без перемикача
// (computeVis). Сам перемикач тимчасовий — до кінця кроку 6 (RISHENNYA, 19).
let PRECISE=false;
const evOn=(e,C,A,Y,H)=>C.has(e[0])&&A.has(e[1])&&Y.has(e[2])&&(!H.size||H.has(e[3]))
  &&(!PRECISE||e[4]===0);
$('#fprec').onclick=()=>{PRECISE=!PRECISE; swSet($('#fprec'),PRECISE); draw()};
// ---- ПОШУК АДРЕСИ ----
// Без урахування регістру й апострофів: «Солом'янську» пишуть і з ', і з ’,
// і без нього. Спершу ті, що з цього починаються, далі решта; усередині —
// де подій більше.
const norm=s=>(s||'').toLowerCase().replace(/['’ʼ`]/g,'').replace(/\s+/g,' ').trim();
const PNORM=P.map(p=>norm(p[2]));
const qEl=$('#q'), sg=$('#sugg');
let SUG=[];
function suggest(){
 const q=norm(qEl.value); SUG=[];
 if(q){
  const pre=[],mid=[];
  PNORM.forEach((n,i)=>{const k=n.indexOf(q); if(k===0) pre.push(i); else if(k>0) mid.push(i)});
  const byN=(a,b)=>P[b][4].length-P[a][4].length;
  SUG=pre.sort(byN).concat(mid.sort(byN)).slice(0,8);
 }
 sg.innerHTML=SUG.map((i,k)=>`<button data-k="${k}">${esc(P[i][3]?P[i][2]:streetName(P[i])+' — без номера будинку')}</button>`).join('');
 sg.hidden=!SUG.length;
}
// Адреса — наближення й відкрите вікно адреси. Вулиця — наближення до меж
// її будинків і вікно подій без номера: позначки в центрі вулиці на карті
// більше немає, це вигадане місце (сотні подій в одній точці).
const streetName=p=>(p[2]||'').replace(/ · вся вулиця$/,'');
function pick(i){
 const p=P[i]; sg.hidden=true; qEl.value=p[3]?p[2]:streetName(p); qEl.blur();
 if(p[3]) return focusAddress(i);
 // «вул. Г.Хоткевича» і «вул. Г. Хоткевича» — одна вулиця: порівнюємо без
 // крапок і пробілів
 const key=s=>norm(s).replace(/[\s.]/g,''), st=key(streetName(p))+',';
 const pts=P.filter(x=>x[3]&&key(x[2]).startsWith(st)).map(x=>[x[0],x[1]]);
 focusStreet(i,pts.length?pts:[[p[0],p[1]]]);
}
qEl.addEventListener('input',suggest);
qEl.addEventListener('keydown',e=>{
 if(e.key==='Enter'&&SUG.length){e.preventDefault();pick(SUG[0])}
 if(e.key==='Escape'){qEl.value='';suggest()}});
sg.onclick=e=>{const b=e.target.closest('[data-k]'); if(b) pick(SUG[+b.dataset.k])};
// ---- ПРАВА ПАНЕЛЬ: усі рішення адреси ----
// Витяг обставин і посилання на папери лежать окремо від сторінки: на сайті
// це файл spravy/<район>.json, який тягнемо, коли панель відкривають уперше.
// У сторінці, відкритій з диска, DOCS уже вкладено — тоді нічого не тягнемо.
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
  `<div class="pa">${esc(p[3]?(p[2]||'адреса не визначена'):streetName(p)+' — події без номера будинку')}</div>`+
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
    vis.length===cs.length ? `${cs.length} ${pl(cs.length,'справа','справи','справ')}`
    : `${vis.length} з ${cs.length} ${pl(cs.length,'справи','справ','справ')} за поточним фільтром`;
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
// ---- РАЙОН ----
// Згорнутий список «Район · усе місто ▾». У щільному центрі клікнути по
// багатокутнику майже неможливо — його закривають позначки подій, тому
// головний шлях у район саме тут, а клік по карті лишається доповненням.
// Чисел біля районів більше немає: панель без чисел.
{const menu=$('#fd');
 if(!M.only){
  menu.innerHTML=[['-1','усе місто']].concat(DN.map((n,i)=>[String(i),n])).map(([i,n])=>
   `<button data-d="${i}">${n}</button>`).join('');
  menu.onclick=e=>{const t=e.target.closest('[data-d]'); if(!t) return;
   const i=+t.dataset.d; menu.hidden=true;
   if(i<0){if(CURD>=0) exitDistrict()} else if(i!==CURD) enterDistrict(i)};
 }else{
  // Окремий файл району: усі десять районів, щоб між ними можна було
  // переходити. Поточний — підкреслений, решта — на міську карту з відкритим
  // районом, «усе місто» — на оглядову сторінку.
  menu.innerHTML='<a href="index.html">усе місто</a>'+DN.map((n,i)=>n===M.only
   ?`<button data-d="${i}" aria-pressed="true">${n}</button>`
   :`<a href="kyiv.html#${DSLUG[i]}">${n}</a>`).join('');
 }
 $('#dbtn').onclick=()=>{menu.hidden=!menu.hidden};
 if(!DN.length&&!M.only) $('#dbtn').hidden=true;
}
function paintDistrictList(){
 $('#dval').textContent=(M.only||(CURD>=0?DN[CURD]:'усе місто'))+' ▾';
 if(!M.only) document.querySelectorAll('#fd [data-d]').forEach(el=>swSet(el,+el.dataset.d===CURD));
}
function onScopeChange(){
 paintDistrictList();
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
     `прогнозом моделі для цієї теми. Модель навчена на ${pr.analysis.train} ${pl(pr.analysis.train,'події','подіях','подіях')} `+
     `і перевірена на ${pr.analysis.test} ${pl(pr.analysis.test,'події','подіях','подіях')} наступних років: у верхні 10% вулиць `+
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
  // Центр вулиці на карту не йде зовсім — ні позначкою, ні в теплову: події
  // з вулицею без номера стоять у вигаданій точці. Вони є лише в пошуку.
  if(!p[3]) continue;
  const ownProbs=probsOf(p);
  // проблема за прихованим напрямком — не проблема для поточного вигляду:
  // саме звідси в переліку бралися адреси з трьома подіями. У вікні підпис
  // про інший напрямок лишається, він корисний.
  const visProbs=ownProbs.filter(pr=>pr.thi===undefined||pr.thi<0||GVIS.has(pr.thi));
  if(CF>=0&&!visProbs.length) continue;
  let n=0;const cnt={};
  for(const e of p[4]) if(evOn(e,C,A,Y,H)){
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
 // Чисел панель більше не показує (RISHENNYA, розд. 18) — ні подій, ні адрес,
 // ні проблем. tot і vis лишаються в результаті: з них кільце у вікні й
 // перевірки паритету.
 return {vis,tot,C,A,Y,H,GVIS,CF};
}
// ---- ВІКНО АДРЕСИ ----
// Готовий вузол DOM: склад подій, розклад доби, картки проблем, кнопки.
// Рушій лише показує його — у Leaflet це bindPopup, у MapLibre setDOMContent.
function popupHTML(p,n,th,byProblem,cnt,thMaj,st){
   const C=st.C,A=st.A,Y=st.Y,H=st.H,GVIS=st.GVIS;
   const ev=p[4].filter(e=>evOn(e,C,A,Y,H));
   // Застереження про дані, не пояснення інтерфейсу: адресу більшості
   // показаних подій опис самої події не називає (клас C чи D).
   // Або так само не підтверджено саму адресу — більшість УСІХ її подій, без
   // фільтра: інакше фільтр, що вибрав кілька подій класу B, знімав би
   // застереження з адреси, якій загалом вірити не можна.
   // Але рядок описує те, що людина бачить: якщо всі показані події класу B
   // («Лише точні адреси»), над ними він був би неправдою — тоді його немає.
   // Правило цілком — RISHENNYA.md, розд. 19, уточнення 23.09.
   const nB=ev.filter(e=>e[4]===0).length;
   const aB=p[4].filter(e=>e[4]===0).length;
   const anote=nB<ev.length&&(2*nB<ev.length||2*aB<p[4].length)
    ?'<div class="an">адресу не підтверджено описом події</div>':'';
   // Будинку немає в адресній базі OSM — точка приблизна (PLAN-TEKSTY.md,
   // 4б; step2_geocode.nearby). Застереження про дані, як і рядок вище.
   const bn=((p[2]||'').match(/,\s*(\d+)/)||[])[1];
   const approx=p[3]===3?`<div class="an">будинку немає в адресній базі — точку поставлено біля № ${bn}</div>`
    :p[3]===4?'<div class="an">будинку немає в адресній базі — точку поставлено між сусідніми номерами</div>':'';
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
   const gvis=allp.filter(pr=>pr.thi===undefined||pr.thi<0||GVIS.has(pr.thi));
   const hidden=allp.length-gvis.length;
   // Картка без жодної показаної події своєї проблеми — порожня: рік, година
   // чи «Лише точні адреси» відсіяли все, про що вона говорить. Таку ховаємо
   // мовчки; підказку «увімкніть напрямок» лишаємо лише для прихованої теми.
   const shownArts=new Set(ev.map(e=>M.cats[e[1]]));
   const probs=gvis.filter(pr=>pr.arts.some(a=>shownArts.has(a[0])));
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
     h+=`<div class="pm"><b>Чому проблема:</b> ${pr.n} ${pl(pr.n,'однорідна подія','однорідні події','однорідних подій')} за ${pr.years.length} `+
        `${pl(pr.years.length,'рік','роки','років')} (${pr.years.join(', ')}), `+
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
   <b>${p[2]||'адреса не визначена'}</b>${anote}${approx}
   <div class="tt">${n} ${pl(n,'подія','події','подій')} за поточним фільтром</div>
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
// ---- ВІКНА З ПОШУКУ, КОЛИ ПОЗНАЧКИ НЕМАЄ ----
// Людина обрала адресу — вікно мусить відкритися, навіть якщо фільтр
// (вид, рік, година, «Лише точні адреси») позначку сховав. Інакше пошук
// виглядає зламаним: карта наблизилась, а нічого не сталося.
function lpWrap(html,p){
 const w=document.createElement('div');w.innerHTML=html;
 w.querySelectorAll('[data-all]').forEach(b=>b.onclick=()=>openPanel(P.indexOf(p)));
 return w;
}
function hiddenHTML(p){
 const N=p[4].length, ncase=typeof p[5]==='number'?p[5]:(p[5]||[]).length;
 return lpWrap(`<div class="lp"><b>${esc(p[2]||'адреса не визначена')}</b>
  <div class="tt">за поточним фільтром подій тут немає</div>
  <div class="tt">усього тут ${N} ${pl(N,'подія','події','подій')}</div>
  <button class="pbtn2" data-all="1">Усі рішення (${ncase})</button></div>`,p);
}
// Вулиця без номера: не місце, а перелік. Той самий склад статей за фільтром,
// що й у вікні адреси, і той самий шлях до рішень.
// Статей на довгій вулиці буває півтора десятка, і кнопка «Усі рішення»
// опинялася під прокруткою. Тому показуємо вісім найчастіших, решту — одним
// рядком: головний шлях звідси — саме до переліку рішень.
const STREET_ROWS=8;
function streetHTML(p,st){
 const N=p[4].length, ncase=typeof p[5]==='number'?p[5]:(p[5]||[]).length;
 const ev=p[4].filter(e=>evOn(e,st.C,st.A,st.Y,st.H));
 const bc={};ev.forEach(e=>{bc[e[1]]=(bc[e[1]]||0)+1});
 const rows=Object.entries(bc).sort((a,b)=>b[1]-a[1]);
 const top=rows.slice(0,STREET_ROWS), rest=rows.slice(STREET_ROWS);
 const nrest=rest.reduce((s,r)=>s+r[1],0);
 const flt=ev.length===N?'':ev.length
   ?`<div class="tt">${ev.length} за поточним фільтром</div>`
   :'<div class="tt">за поточним фільтром подій немає</div>';
 return lpWrap(`<div class="lp"><b>${esc(streetName(p))}</b>
  <div class="tt">${N} ${pl(N,'подія','події','подій')} без номера будинку</div>
  ${flt}
  <table class="bd">`+top.map(([i,c])=>
   `<tr><td title="${LAW(M.cats[i])}">${M.cats[i]}</td><td><b>${c}</b></td></tr>`).join('')+
  (rest.length?`<tr><td>інші статті (${rest.length})</td><td><b>${nrest}</b></td></tr>`:'')+`</table>
  <button class="pbtn2" data-all="1">Усі рішення (${ncase})</button></div>`,p);
}
"""
