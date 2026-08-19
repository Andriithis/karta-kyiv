# -*- coding: utf-8 -*-
"""Крок 3. Карта з агрегацією по адресах + рейтинг адрес."""
import os, sys, csv, json, glob, sqlite3, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import labels as L

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data'); DB = os.path.join(DATA, 'events.db')
OUT  = os.path.join(ROOT, 'karta.html')
RISKS = os.path.join(DATA, 'risks.json')
EXCL = os.path.join(DATA, 'vykluchennya.txt')
REVIEW = os.path.join(DATA, 'top100_dlya_pereviryky.txt')

SHARE_LIMIT = 0.015      # адреса, що дає >2% подій свого району, вважається установою
ABS_LIMIT   = 90       # або перевищує цю кількість подій

def load_excl():
    man = set()
    if os.path.exists(EXCL):
        for ln in open(EXCL, encoding='utf-8'):
            ln = ln.split('#')[0].strip()
            if ln: man.add(ln.lower())
    return man

def detect_institutional(rows, manual):
    per_court = collections.Counter(r[1] for r in rows)
    per_addr = collections.Counter()
    addr_court = {}
    for r in rows:
        if not r[5]: continue
        a = (r[5] + ', ' + r[6]) if r[6] else r[5]
        per_addr[a] += 1
        addr_court[a] = r[1]
    auto = {}
    for a, n in per_addr.items():
        tot = per_court[addr_court[a]] or 1
        if n >= ABS_LIMIT or n / tot >= SHARE_LIMIT:
            auto[a] = (n, round(100 * n / tot, 1))
    # звіт: топ-100 адрес із профілем статей, щоб можна було оцінити очима
    prof = collections.defaultdict(collections.Counter)
    for r in rows:
        if not r[5]: continue
        a = (r[5] + ', ' + r[6]) if r[6] else r[5]
        lb = L.CODE.get(r[2])
        prof[a][lb[1] if lb else r[2]] += 1
    with open(REVIEW, 'w', encoding='utf-8') as f:
        f.write('# Топ-100 адрес за кількістю подій, із профілем статей.\n')
        f.write('# Якщо бачите установу (суд, відділ поліції, місце оформлення протоколів) —\n')
        f.write('# скопіюйте її адресу у файл vykluchennya.txt окремим рядком.\n')
        f.write('# Ознака місця оформлення: майже все — ст.130, ст.126, ст.122-4.\n\n')
        for a, n in per_addr.most_common(100):
            mark = ' [ВЖЕ ВИКЛЮЧЕНО]' if a in auto else ''
            f.write(f'{n:6}  {a}{mark}\n')
            for st, k in prof[a].most_common(4):
                f.write(f'          {k:5}  {st}\n')
            f.write('\n')
    print(f'   звіт для перегляду: data/top100_dlya_pereviryky.txt')

    if auto or not os.path.exists(EXCL):
        with open(EXCL, 'w', encoding='utf-8') as f:
            f.write('# Адреси, виключені з карти як установи (суди, відділи поліції).\n')
            f.write('# Визначено автоматично: адреса дає понад 2% подій свого району\n')
            f.write('# або понад 120 подій. Приберіть рядок, якщо адреса справжня.\n')
            f.write('# Один рядок = одна адреса.\n\n')
            for a, (n, pc) in sorted(auto.items(), key=lambda x: -x[1][0]):
                f.write(f'{a}   # {n} подій, {pc}% району\n')
        print(f'   виявлено установ: {len(auto)} -> data/vykluchennya.txt')
        for a, (n, pc) in sorted(auto.items(), key=lambda x: -x[1][0])[:8]:
            print(f'     {n:5}  {pc:4}%  {a}')
    return {a.lower() for a in auto} | manual

COURTS = {'Golosiivskyi':'Голосіївський','Darnytskyi':'Дарницький','Desnianskyi':'Деснянський',
 'Dniprovskyi':'Дніпровський','Obolonskyi':'Оболонський','Pecherskyi':'Печерський',
 'Podilskyi':'Подільський','Sviatoshynskyi':'Святошинський','Solomianskyi':"Солом'янський",
 'Shevchenkivskyi':'Шевченківський'}

def main():
    if not os.path.exists(DB): print('спочатку кроки 1 і 2'); sys.exit(1)
    c = sqlite3.connect(DB)
    if not c.execute("SELECT name FROM sqlite_master WHERE name='geo'").fetchone():
        print('немає таблиці geo — крок 2 не відпрацював'); sys.exit(1)

    extra = {}
    for fp in glob.glob(os.path.join(DATA, 'kyiv_*.csv')):
        with open(fp, encoding='utf-8-sig') as fh:
            for r in csv.DictReader(fh, delimiter='\t'):
                extra[r['doc_id']] = (r['cause_num'], r['doc_url'])

    rows = list(c.execute("""SELECT e.doc_id,e.court,e.cat,e.date,e.tm,e.street,e.house,
        g.lat,g.lon,g.precision FROM events e JOIN geo g ON g.doc_id=e.doc_id"""))
    print(f'подій з координатами: {len(rows):,}')
    if not rows: return

    print('перевірка на адреси установ:')
    excl = detect_institutional(rows, load_excl())
    before = len(rows)
    rows = [r for r in rows
            if ((r[5] + ', ' + r[6]) if (r[5] and r[6]) else (r[5] or '')).lower() not in excl]
    print(f'   вилучено подій: {before - len(rows):,}  ->  залишилось {len(rows):,}')

    # ---- злиття кодів у назви ----
    cnt = collections.Counter()
    for r in rows:
        lb = L.CODE.get(r[2])
        if lb: cnt[lb] += 1
        else: cnt[('СЕР', 'інші (код ' + r[2] + ')')] += 1

    labels = sorted(cnt, key=lambda k: (L.ORDER.index(k[0]) if k[0] in L.ORDER else 9, -cnt[k]))
    li = {k: i for i, k in enumerate(labels)}
    ck = sorted({r[1] for r in rows}); ci = {v: i for i, v in enumerate(ck)}

    yc = collections.Counter(r[3][:4] for r in rows)
    yrs = sorted(y for y, n in yc.items() if n >= 200 and y.isdigit())
    ykeys = yrs + (['раніше'] if sum(n for y, n in yc.items() if y not in yrs) else [])
    yi = {y: i for i, y in enumerate(ykeys)}
    print('роки:', ', '.join(ykeys))
    print(f'статей після злиття: {len(labels)} (було би {len({r[2] for r in rows})} за кодами)')

    agg = collections.defaultdict(list)
    for doc, court, cat, date, tm, street, house, la, lo, prec in rows:
        lb = L.CODE.get(cat) or ('СЕР', 'інші (код ' + cat + ')')
        agg[(round(la, 5), round(lo, 5))].append(
            (ci[court], li[lb], yi.get(date[:4], yi.get('раніше', 0)),
             int(tm[:2]) if tm and tm[:2].isdigit() else -1,
             1 if prec == 'house' else 0, date, street or '', house or '',
             *extra.get(doc, ('', ''))))

    P = []
    for (la, lo), evs in agg.items():
        a = next((f"{e[6]}, {e[7]}" if e[7] else e[6] for e in evs if e[6]), '')
        P.append([la, lo, a, evs[0][4],
                  [[e[0], e[1], e[2], e[3]] for e in evs],
                  [[e[1], e[5], e[3], e[8], e[9]] for e in sorted(evs, key=lambda x: x[5], reverse=True)[:6]]])
    print(f'унікальних адрес: {len(P):,}')

    groups = []
    for t in L.ORDER:
        ids = [li[k] for k in labels if k[0] == t]
        if ids: groups.append([L.THEMES[t], ids, sum(cnt[labels[i]] for i in ids)])
    meta = dict(courts=[COURTS.get(x, x) for x in ck], cats=[k[1] for k in labels],
                counts=[cnt[k] for k in labels], groups=groups, years=ykeys)
    risks = {'points': {}, 'lines': {}}
    if os.path.exists(RISKS):
        risks = json.load(open(RISKS, encoding='utf-8'))
        np_ = sum(len(v['items']) for v in risks.get('points', {}).values())
        nl_ = sum(len(v['items']) for v in risks.get('lines', {}).values())
        print(f'шар ризиків: {np_:,} об\'єктів, {nl_:,} ділянок')
    else:
        print('шар ризиків відсутній (запустіть 2b-RISKS) — карта буде без нього')

    html = TPL.replace('__RISKS__', json.dumps(risks, ensure_ascii=False, separators=(',', ':'))) \
              .replace('__META__', json.dumps(meta, ensure_ascii=False)) \
              .replace('__PTS__', json.dumps(P, ensure_ascii=False, separators=(',', ':')))
    open(OUT, 'w', encoding='utf-8').write(html)
    print(f'готово: karta.html ({os.path.getsize(OUT)/1048576:.1f} МБ)')

TPL = r"""<!DOCTYPE html><html lang="uk"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Карта правопорушень Києва</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>
<style>
*{box-sizing:border-box}html,body{margin:0;height:100%;font:13.5px/1.45 system-ui,sans-serif;background:#0f1117;color:#e8eaf0}
#wrap{display:flex;height:100%}
#side{width:330px;flex:0 0 330px;overflow-y:auto;padding:14px;background:#161922;border-right:1px solid #252a37}
#map{flex:1}h1{font-size:15px;margin:0 0 2px}.sub{color:#79839a;font-size:11.5px}
#cnt{font-size:26px;font-weight:600;margin:12px 0 0;letter-spacing:-.02em}
fieldset{border:0;border-top:1px solid #252a37;padding:11px 0 3px;margin:10px 0 0}
legend{font-size:10.5px;text-transform:uppercase;letter-spacing:.09em;color:#79839a}
label{display:flex;gap:7px;align-items:flex-start;padding:2.5px 0;cursor:pointer}
input[type=checkbox]{accent-color:#e0533d;width:14px;height:14px;margin-top:2px;flex:0 0 auto}
button{width:100%;padding:8px;background:#1f2432;color:#e8eaf0;border:1px solid #303747;border-radius:6px;font:inherit;cursor:pointer;margin-top:7px}
button:hover{background:#28303f}button.act{background:#e0533d;border-color:#e0533d;color:#fff}
.th{font-size:10.5px;text-transform:uppercase;letter-spacing:.07em;color:#5f6878;margin:9px 0 2px}
#hr{display:flex;gap:4px;flex-wrap:wrap}
#hr span{width:25px;text-align:center;padding:4px 0;background:#1f2432;border-radius:4px;font-size:11px;cursor:pointer;user-select:none}
#hr span.on{background:#e0533d;color:#fff}
#top{margin-top:6px}
#top div{display:flex;justify-content:space-between;gap:8px;padding:5px 7px;background:#1c212c;border-radius:5px;margin-bottom:3px;cursor:pointer;font-size:12.5px}
#top div:hover{background:#252c3a}#top b{color:#e0533d;flex:0 0 auto}
.gr{margin-bottom:2px}
.gh{display:flex;align-items:center;gap:7px;padding:5px 6px;background:#1c212c;border-radius:5px;cursor:pointer;user-select:none}
.gh:hover{background:#232a37}.gh .nm{flex:1;font-size:12.5px}
.gh .n{color:#79839a;font-size:11px}.gh .ar{color:#5f6878;font-size:10px;width:9px}
.gb{display:none;padding:4px 0 6px 22px}.gr.open .gb{display:block}
.gr.open .ar{transform:rotate(90deg)}.ar{display:inline-block;transition:transform .12s}
.gb label{font-size:12px;color:#c4cbd8}.gb .n{color:#5f6878;font-size:10.5px;margin-left:auto;flex:0 0 auto}
.hint{font-size:11px;color:#5f6878;margin-top:7px;line-height:1.4}
#fr label{font-size:12px}#fr .n{color:#5f6878;font-size:10.5px;margin-left:auto;flex:0 0 auto}
#fr .sw{width:9px;height:9px;border-radius:2px;flex:0 0 auto}
#fr .rh{font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;color:#5f6878;margin:7px 0 2px}
.lp{font-size:12.5px;max-height:330px;overflow-y:auto}.lp b{display:block;margin-bottom:5px;font-size:13px}
.lp a{color:#c94a34;text-decoration:none}.lp a:hover{text-decoration:underline}
.lp li{margin-bottom:4px;font-size:11.5px}.lp ul{padding-left:15px;margin:3px 0}
.lp .tt{color:#79839a;font-size:11.5px;margin-bottom:7px}
.bd{width:100%;border-collapse:collapse;margin-bottom:8px}
.bd td{padding:2px 0;font-size:12px;vertical-align:top}
.bd td:last-child{text-align:right;padding-left:10px;color:#e0533d;width:44px}
.hg{display:flex;align-items:flex-end;gap:1px;height:24px;margin:2px 0 1px}
.hg i{flex:1;background:#e0533d;opacity:.8;border-radius:1px 1px 0 0}
.hx{display:flex;justify-content:space-between;font-size:9.5px;color:#5f6878;margin-bottom:5px}
.hn{font-size:11px;color:#c4cbd8;background:#232a37;padding:4px 7px;border-radius:4px;margin-bottom:7px}
.ex{font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;color:#5f6878;margin-top:6px}
@media(max-width:760px){#wrap{flex-direction:column}#side{width:100%;flex:0 0 auto;max-height:50%}}
</style></head><body><div id="wrap"><div id="side">
<h1>Карта правопорушень</h1><div class="sub">за даними ЄДРСР · місто Київ</div>
<div id="cnt">0</div><div class="sub" id="cntl"></div>
<button id="heat">Теплова карта</button><button id="reset">Скинути фільтри</button>
<fieldset><legend>Топ адрес за фільтром</legend><div id="top"></div></fieldset>
<fieldset><legend>Район</legend><div id="fc"></div></fieldset>
<fieldset><legend>Правопорушення</legend>
<div style="display:flex;gap:6px"><button id="none" style="margin:0 0 8px">Зняти всі</button>
<button id="all" style="margin:0 0 8px">Обрати всі</button></div><div id="fa"></div></fieldset>
<fieldset><legend>Ризики (OpenStreetMap)</legend><div id="fr"></div>
<div class="hint">Умови середовища, а не події. Вимкнено за замовчуванням.<br><br>Перші три шари спираються на прямі позначки в OSM. Останній — <b>припущення</b> за відсутністю даних: там багато хибних спрацювань, це список для обходу, а не факт.</div></fieldset>
<fieldset><legend>Рік</legend><div id="fy"></div></fieldset>
<fieldset><legend>Година доби</legend><div id="hr"></div>
<div class="hint">Порожній вибір годин = усі. Розмір кола = кількість подій за адресою. Сірі кола — прив'язка лише до вулиці, без номера будинку.</div></fieldset>
</div><div id="map"></div></div>
<script>
const M=__META__, P=__PTS__;
const PALA=['#e0533d','#e8a33d','#8b5cf6','#ef4444','#3b82f6','#22c55e','#14b8a6'];
const CATTH={};M.groups.forEach((g,gi)=>g[1].forEach(i=>CATTH[i]=gi));
const R=__RISKS__;
const map=L.map('map',{preferCanvas:true}).setView([50.45,30.52],11);
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
{attribution:'&copy; OpenStreetMap, CARTO',maxZoom:19}).addTo(map);
let layer=L.layerGroup().addTo(map),heat=null,heatOn=false;
const rlayer=L.layerGroup().addTo(map);
const RCOL={alcohol:'#f59e0b',shop24:'#fbbf24',transit:'#38bdf8',school:'#a3e635',
 abandon:'#a78bfa',no_walk:'#fb7185',no_light:'#facc15',no_cross:'#fb923c',maybe_walk:'#94a3b8'};
{let hh='<div class="rh">Об\'єкти</div>';
 for(const k in R.points||{}) hh+=`<label><input type="checkbox" data-r="${k}">
  <span class="sw" style="background:${RCOL[k]}"></span><span>${R.points[k].title}</span>
  <span class="n">${R.points[k].items.length.toLocaleString('uk')}</span></label>`;
 hh+='<div class="rh">Відсутності</div>';
 for(const k in R.lines||{}) hh+=`<label><input type="checkbox" data-r="${k}">
  <span class="sw" style="background:${RCOL[k]}"></span><span>${R.lines[k].title}</span>
  <span class="n">${R.lines[k].items.length.toLocaleString('uk')}</span></label>`;
 const el=document.getElementById('fr'); if(el) el.innerHTML=hh;}
function drawRisks(){
 rlayer.clearLayers();
 document.querySelectorAll('[data-r]').forEach(cb=>{
  if(!cb.checked) return;
  const k=cb.dataset.r, col=RCOL[k];
  if(R.points&&R.points[k]) R.points[k].items.forEach(it=>
    L.circleMarker([it[0],it[1]],{radius:4,weight:1.4,color:col,fillColor:col,fillOpacity:.25})
     .bindPopup(`<div class="lp"><b>${it[2]||R.points[k].title}</b><div class="tt">${R.points[k].title}</div></div>`)
     .addTo(rlayer));
  if(R.lines&&R.lines[k]) R.lines[k].items.forEach(it=>
    L.polyline(it[0],{color:col,weight:4,opacity:.65})
     .bindPopup(`<div class="lp"><b>${it[1]||'без назви'}</b><div class="tt">${R.lines[k].title} · ${it[2]} м</div></div>`)
     .addTo(rlayer));
 });
}
const $=s=>document.querySelector(s);
$('#fc').innerHTML=M.courts.map((n,i)=>`<label><input type="checkbox" data-c="${i}" checked>${n}</label>`).join('');
$('#fy').innerHTML=M.years.map((n,i)=>`<label><input type="checkbox" data-y="${i}" checked>${n}</label>`).join('');
const fmt=n=>n.toLocaleString('uk');
$('#fa').innerHTML=M.groups.map((g,gi)=>`<div class="gr" data-g="${gi}">
<div class="gh"><span class="ar">&#9656;</span><input type="checkbox" class="gt" data-gt="${gi}" checked>
<span class="nm">${g[0]}</span><span class="n">${fmt(g[2])}</span></div>
<div class="gb">`+g[1].map(i=>`<label><input type="checkbox" data-a="${i}" checked>
<span>${M.cats[i]}</span><span class="n">${fmt(M.counts[i])}</span></label>`).join('')+
`</div></div>`).join('');
document.querySelectorAll('.gh').forEach(el=>el.onclick=e=>{
 if(e.target.tagName==='INPUT')return; el.parentElement.classList.toggle('open')});
document.querySelectorAll('.gt').forEach(el=>el.onchange=()=>{
 M.groups[+el.dataset.gt][1].forEach(i=>{const b=document.querySelector(`[data-a="${i}"]`);if(b)b.checked=el.checked});
 draw()});
function syncThemes(){document.querySelectorAll('.gt').forEach(el=>{
 const ids=M.groups[+el.dataset.gt][1], on=ids.filter(i=>document.querySelector(`[data-a="${i}"]`).checked).length;
 el.checked=on>0; el.indeterminate=on>0&&on<ids.length})}
const hb=$('#hr');for(let x=0;x<24;x++){const s=document.createElement('span');s.textContent=x;s.dataset.h=x;hb.appendChild(s)}
hb.onclick=e=>{if(e.target.dataset.h!==undefined){e.target.classList.toggle('on');draw()}};
const sel=a=>new Set([...document.querySelectorAll(`[data-${a}]`)].filter(x=>x.checked).map(x=>+x.dataset[a]));
function draw(){
 syncThemes();
 const C=sel('c'),A=sel('a'),Y=sel('y');
 const H=new Set([...hb.querySelectorAll('.on')].map(x=>+x.dataset.h));
 let tot=0;const vis=[];
 for(const p of P){let n=0,th=null;
  for(const e of p[4]) if(C.has(e[0])&&A.has(e[1])&&Y.has(e[2])&&(!H.size||H.has(e[3]))){n++;if(th===null)th=CATTH[e[1]]}
  if(n){tot+=n;vis.push([p,n,th])}}
 vis.sort((a,b)=>b[1]-a[1]);
 const rank=vis.filter(v=>v[0][3]&&v[0][2]);
 $('#cnt').textContent=tot.toLocaleString('uk');
 $('#cntl').textContent=`подій на ${vis.length.toLocaleString('uk')} адресах`;
 $('#top').innerHTML=rank.slice(0,15).map((v,i)=>
  `<div data-i="${i}"><span>${v[0][2]}</span><b>${v[1]}</b></div>`).join('')||'<div class="sub">нема даних</div>';
 [...$('#top').children].forEach((el,i)=>el.onclick=()=>{const v=rank[i];map.setView([v[0][0],v[0][1]],17);
  setTimeout(()=>{let best=null,bd=1e9;layer.eachLayer(l=>{const ll=l.getLatLng();
   const d=Math.abs(ll.lat-v[0][0])+Math.abs(ll.lng-v[0][1]);if(d<bd){bd=d;best=l}});
   if(best&&bd<1e-4)best.openPopup()},350)});
 layer.clearLayers();if(heat){map.removeLayer(heat);heat=null}
 if(heatOn){heat=L.heatLayer(vis.flatMap(v=>Array(Math.min(v[1],20)).fill([v[0][0],v[0][1],1])),
  {radius:18,blur:24,maxZoom:16}).addTo(map);return}
 const mx=vis.length?vis[0][1]:1;
 for(const [p,n,th] of vis){
  const r=Math.max(3.2,Math.min(19,3.2+8.5*Math.sqrt(n/Math.max(mx,1))*2));
  L.circleMarker([p[0],p[1]],{radius:r,weight:p[3]?.8:0,color:'#0f1117',
   fillColor:p[3]?(PALA[th%7]):'#5f6878',fillOpacity:p[3]?.72:.35})
  .bindPopup(()=>{
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
   const ex=p[5].filter(e=>A.has(e[0])).slice(0,4);
   return `<div class="lp"><b>${p[2]||'адреса не визначена'}</b>
   <div class="tt">${n} ${n%10===1&&n%100!==11?'подія':'подій'} за поточним фільтром</div>
   <table class="bd">`+rows.map(([i,c])=>
     `<tr><td>${M.cats[i]}</td><td><b>${c}</b></td></tr>`).join('')+`</table>
   ${bars}${hint}
   <div class="ex">Приклади рішень:</div><ul>`+
   ex.map(e=>`<li><span style="color:#79839a">${e[1]}${e[2]>=0?', '+String(e[2]).padStart(2,'0')+':00':''} · ${e[3]}</span> <a href="${e[4]}" target="_blank">відкрити</a></li>`).join('')+
   '</ul></div>'},{maxWidth:360}).addTo(layer)}
}
$('#heat').onclick=e=>{heatOn=!heatOn;e.target.classList.toggle('act');e.target.textContent=heatOn?'Показати точки':'Теплова карта';draw()};
$('#reset').onclick=()=>{document.querySelectorAll('#side input').forEach(x=>x.checked=true);
 hb.querySelectorAll('.on').forEach(x=>x.classList.remove('on'));draw()};
$('#none').onclick=()=>{document.querySelectorAll('[data-a]').forEach(x=>x.checked=false);draw()};
$('#all').onclick=()=>{document.querySelectorAll('[data-a]').forEach(x=>x.checked=true);draw()};
document.querySelectorAll('#side input:not([data-r])').forEach(x=>x.addEventListener('change',draw));
document.querySelectorAll('[data-r]').forEach(x=>x.addEventListener('change',drawRisks));
$('#reset').onclick=()=>{document.querySelectorAll('#side input:not([data-r])').forEach(x=>x.checked=true);
 hb.querySelectorAll('.on').forEach(x=>x.classList.remove('on'));draw()};
draw();drawRisks();
</script></body></html>"""

if __name__ == '__main__':
    main()
