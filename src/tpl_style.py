# -*- coding: utf-8 -*-
"""Шапка сторінки й усі стилі карти.

Тут: <!DOCTYPE>, <head>, підключення Leaflet і <style> цілком.
Розміри бічної панелі, вигляд спливних вікон — усе змінюється тут.
Кольори НЕ пишуться літералом: вони живуть у змінних трьох тем на початку
блока. Жодного тексту й жодної логіки: підписи — у tpl_body, поведінка —
у tpl_map і tpl_popup.
"""
HEAD = r"""<!DOCTYPE html><html lang="uk"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Карта правопорушень Києва</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Unbounded:wght@400;500;600&family=Commissioner:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* ---- ТРИ ТЕМИ ----
   Набори змінних узято з погодженого макета PROBA-VYGLIADU.html. Колір ніде
   не стоїть літералом навмисно: інакше світла тема лишилася б темною в тих
   місцях, куди не дійшли руки. Набір обирає атрибут data-t на <body> —
   його ставить tpl_map з localStorage. Перший набір продубльовано на голий
   body, щоб сторінка мала кольори навіть до того, як відпрацює скрипт. */
body,body[data-t="svitla"]{--panel:#fff;--sunk:#f7f7f5;--ink:#14161a;--dim:#5f6771;
 --faint:#9aa0a9;--rule:#e7e6e3;--ground:#f6f6f4;--halo:#fff;
 --glass:rgba(255,255,255,.80);--shadow:drop-shadow(0 1px 1.5px rgba(16,18,22,.22))}
body[data-t="temna"]{--panel:#0f1217;--sunk:#151920;--ink:#eaebef;--dim:#8d94a2;
 --faint:#5b6371;--rule:#1f242b;--ground:#0c0e12;--halo:#0b0d11;
 --glass:rgba(15,18,23,.78);--shadow:drop-shadow(0 1px 2px rgba(0,0,0,.55))}
body[data-t="kolir"]{--panel:#12161b;--sunk:#181d23;--ink:#eaebef;--dim:#8d94a2;
 --faint:#5f6775;--rule:#212730;--ground:#1a2430;--halo:#101820;
 --glass:rgba(18,22,27,.78);--shadow:drop-shadow(0 1px 2px rgba(0,0,0,.5))}
:root{--sans:Commissioner,"Segoe UI",system-ui,sans-serif;
 --mono:"IBM Plex Mono",ui-monospace,Consolas,monospace;
 --disp:Unbounded,Commissioner,sans-serif}
*{box-sizing:border-box}html,body{margin:0;height:100%;font:13.5px/1.45 var(--sans);background:var(--ground);color:var(--ink)}
#wrap{display:flex;height:100%}
#side{width:330px;flex:0 0 330px;overflow-y:auto;padding:14px;background:var(--panel);border-right:1px solid var(--rule)}
#map{flex:1}h1{font-size:15px;margin:0 0 2px;font-family:var(--disp);font-weight:500;letter-spacing:-.03em}
.sub{color:var(--dim);font-size:11.5px}
#cnt{font-size:26px;font-weight:600;margin:12px 0 0;letter-spacing:-.02em;font-family:var(--disp)}
fieldset{border:0;border-top:1px solid var(--rule);padding:11px 0 3px;margin:10px 0 0}
legend{font-size:10.5px;text-transform:uppercase;letter-spacing:.09em;color:var(--dim)}
label{display:flex;gap:7px;align-items:flex-start;padding:2.5px 0;cursor:pointer}
input[type=checkbox]{accent-color:var(--ink);width:14px;height:14px;margin-top:2px;flex:0 0 auto}
button{width:100%;padding:8px;background:var(--sunk);color:var(--ink);border:1px solid var(--rule);border-radius:6px;font:inherit;cursor:pointer;margin-top:7px}
button:hover{background:var(--rule)}button.act{background:var(--ink);border-color:var(--ink);color:var(--panel)}
.th{font-size:10.5px;text-transform:uppercase;letter-spacing:.07em;color:var(--faint);margin:9px 0 2px}
#hr{display:grid;grid-template-columns:1fr 1fr;gap:5px}
#hr span{padding:7px 4px;background:var(--sunk);border-radius:6px;font-size:12px;cursor:pointer;
 user-select:none;text-align:center;line-height:1.15;transition:background .12s}
#hr span:hover{background:var(--rule)}
#hr span i{display:block;font-style:normal;font-size:10px;color:var(--dim);margin-top:1px}
#hr span.on{background:var(--ink);color:var(--panel)}#hr span.on i{color:var(--panel)}
#top{margin-top:6px}
#top div{display:flex;justify-content:space-between;gap:8px;padding:5px 7px;background:var(--sunk);border-radius:5px;margin-bottom:3px;cursor:pointer;font-size:12.5px}
#top div:hover{background:var(--rule)}#top b{color:var(--ink);flex:0 0 auto;font-family:var(--mono);font-weight:400}
.gr{margin-bottom:2px}
.gh{display:flex;align-items:center;gap:7px;padding:5px 6px;background:var(--sunk);border-radius:5px;cursor:pointer;user-select:none}
.gh:hover{background:var(--rule)}.gh .nm{flex:1;font-size:12.5px}
.gh .n{color:var(--dim);font-size:11px;font-family:var(--mono)}.gh .ar{color:var(--faint);font-size:10px;width:9px}
.gb{display:none;padding:4px 0 6px 22px}.gr.open .gb{display:block}
.gr.open .ar{transform:rotate(90deg)}.ar{display:inline-block;transition:transform .12s}
.gb label{font-size:12px;color:var(--dim)}.gb .n{color:var(--faint);font-size:10.5px;margin-left:auto;flex:0 0 auto;font-family:var(--mono)}
.hint{font-size:11px;color:var(--faint);margin-top:7px;line-height:1.4}
#backl a{color:var(--ink);font-size:12px;text-decoration:none;display:inline-block;margin-top:2px}
#pan{position:absolute;top:0;right:0;bottom:0;width:380px;max-width:34vw;z-index:1200;
 background:var(--panel);border-left:1px solid var(--rule);display:flex;flex-direction:column;
 transform:translateX(100%);transition:transform .22s ease;box-shadow:-14px 0 34px rgba(0,0,0,.18)}
#pan.on{transform:none}
#panh{padding:13px 14px 10px;border-bottom:1px solid var(--rule);position:relative;flex:0 0 auto}
#panh .pa{font-size:14.5px;font-weight:600;padding-right:26px;line-height:1.25}
#panh .ps{font-size:11.5px;color:var(--dim);margin-top:3px}
#panx{position:absolute;top:9px;right:10px;width:24px;height:24px;padding:0;margin:0;
 background:var(--sunk);border:1px solid var(--rule);border-radius:6px;color:var(--dim);
 font-size:15px;line-height:1;cursor:pointer}
#panx:hover{background:var(--rule);color:var(--ink)}
#panb{flex:1;overflow-y:auto;padding:10px 14px 22px}
.cs{border-top:1px solid var(--rule);padding:9px 0}
.cs:first-child{border-top:0}
.cd{font-size:12.5px;color:var(--dim)}
.cd b{color:var(--ink);font-weight:600}
.cn{font-size:11px;color:var(--faint);margin-top:1px}
.cx{font-size:12px;color:var(--dim);line-height:1.45;margin-top:5px}
.cl{margin-top:5px;display:flex;flex-wrap:wrap;gap:6px}
.cl a{font-size:11px;color:var(--ink);text-decoration:none;border:1px solid var(--rule);
 border-radius:5px;padding:2px 7px}
.cl a:hover{background:var(--sunk)}
#panb .sub{font-size:12px;color:var(--faint);padding:8px 0}
@media(max-width:900px){#pan{width:100%;max-width:100%}}
#fd{display:grid;grid-template-columns:1fr 1fr;gap:5px}
#fd span{padding:6px 5px;background:var(--sunk);border-radius:6px;font-size:11.5px;cursor:pointer;
 user-select:none;text-align:center;line-height:1.15;transition:background .12s}
#fd span:hover{background:var(--rule)}
#fd span i{display:block;font-style:normal;font-size:10px;color:var(--dim);margin-top:1px}
#fd span.on{background:var(--ink);color:var(--panel)}#fd span.on i{color:var(--panel)}
#backl a:hover{text-decoration:underline}
#fr label,#frisk label,#fctx label{font-size:12px}
#fr .n,#frisk .n,#fctx .n{color:var(--faint);font-size:10.5px;margin-left:auto;flex:0 0 auto;font-family:var(--mono)}
#fr .sw,#frisk .sw,#fctx .sw{width:9px;height:9px;border-radius:2px;flex:0 0 auto}
#fcat{display:grid;grid-template-columns:1fr 1fr;gap:5px}
#fcat span{padding:7px 5px;background:var(--sunk);border-radius:6px;font-size:12px;cursor:pointer;
 user-select:none;text-align:center;line-height:1.15;transition:background .12s;position:relative}
#fcat span:hover{background:var(--rule)}
#fcat span i{display:block;font-style:normal;font-size:10px;color:var(--dim);margin-top:1px}
#fcat span.on{background:var(--sunk);box-shadow:inset 0 0 0 1.5px currentColor}
#fcat span.c2{color:var(--ink)}#fcat span.cA{color:var(--dim)}
.skew{font-size:11.5px;color:var(--ink);background:var(--sunk);border-left:3px solid var(--ink);
 border-radius:5px;padding:7px 9px;margin-top:9px;line-height:1.4}
.env{margin:8px 0 0}
.env .eh{font-size:10px;text-transform:uppercase;letter-spacing:.07em;color:var(--dim);margin-bottom:4px}
.dirs{margin:7px 0}.dirs .row{display:flex;gap:7px;align-items:center;font-size:11.5px;margin-bottom:3px}
.dirs .bar2{flex:1;height:4px;background:var(--rule);border-radius:2px;overflow:hidden}
.dirs .bar2 i{display:block;height:100%;background:var(--ink)}
.miss{font-size:11px;color:var(--dim);background:var(--sunk);border-left:2px solid var(--rule);
 padding:5px 8px;border-radius:4px;margin-top:7px}
.cbadge{display:inline-block;padding:1px 7px;border-radius:99px;font-size:10.5px;
 text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px}
#fr .rh{font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;color:var(--faint);margin:9px 0 2px}
/* ---- прогноз ризику ---- */
#frisk .rw{margin-bottom:5px;border-radius:6px;background:var(--sunk);padding:6px 8px;
  border-left:3px solid transparent;transition:background .12s}
#frisk .rw:hover{background:var(--rule)}
#frisk .rl{display:flex;align-items:center;gap:7px;cursor:pointer}
#frisk .nm{flex:1;font-size:12.5px;line-height:1.2}
#frisk .acc{font-size:10px;color:var(--dim);padding:1px 5px;border:1px solid var(--rule);border-radius:99px;font-family:var(--mono)}
#frisk .why{font-size:10.5px;color:var(--faint);margin:3px 0 0 22px;line-height:1.35}
#frisk .rw.nod{opacity:.5}#frisk .rw.nod .rl{cursor:default}
#frisk .rg{margin-bottom:6px;border-radius:6px;background:var(--sunk);border:1px solid var(--rule)}
#frisk .rg>summary{list-style:none;cursor:pointer;display:flex;align-items:center;gap:7px;
 padding:6px 9px;font-size:12px;color:var(--dim);user-select:none}
#frisk .rg>summary::-webkit-details-marker{display:none}
#frisk .rg>summary::before{content:'\25B8';color:var(--faint);font-size:9px;transition:.15s}
#frisk .rg[open]>summary::before{transform:rotate(90deg)}
#frisk .rg>summary .gn{flex:1;font-weight:500}
#frisk .rg>summary .gc{font-size:10px;color:var(--faint);padding:1px 6px;border:1px solid var(--rule);border-radius:99px;font-family:var(--mono)}
#frisk .rg .rw{margin:0 6px 5px}#frisk .rg .rw:first-of-type{margin-top:2px}
.lgd{display:flex;align-items:center;gap:6px;font-size:10px;color:var(--faint);margin-top:8px}
.lgd i{height:3px;flex:1;border-radius:2px;background:linear-gradient(90deg,var(--rule) 0%,currentColor 100%)}
/* Підкладка більше не інвертується: інверсія світлих плиток OSM — це не тема,
   а саме інверсія, звідси й болотяний відтінок. Тепер кожна тема має власний
   набір плиток, він у tpl_map. */
.leaflet-container{background:var(--ground);font-family:var(--sans)}
/* Тінь під точками й лініями. У макеті вона стоїть на svg, а в нас усе
   малюється в canvas (preferCanvas), тож фільтр — на полотні. Фільтр
   розмиває силует УСЬОГО полотна на кожному кадрі, а на міському огляді це
   11 686 адрес, і глибини там однаково не видно. Тому тінь вмикається лише
   зблизька: клас deep вішає tpl_popup на контейнер карти на zoomend. */
.deep .leaflet-overlay-pane canvas{filter:var(--shadow)}
/* перемикач тем у куті карти */
.tsw{display:flex;gap:2px;background:var(--glass);backdrop-filter:blur(16px) saturate(1.3);
 -webkit-backdrop-filter:blur(16px) saturate(1.3);border:1px solid var(--rule)}
.tsw button{all:unset;cursor:pointer;font:12px var(--sans);color:var(--dim);padding:6px 11px;transition:color .16s}
.tsw button:hover{color:var(--ink)}
.tsw button[aria-pressed="true"]{color:var(--ink);background:var(--sunk)}
.leaflet-control-attribution{background:var(--glass)!important;color:var(--faint)!important;
 font-size:9.5px!important;padding:2px 6px!important}
.leaflet-control-attribution a{color:var(--dim)!important}
.leaflet-bar a{background:var(--panel)!important;color:var(--ink)!important;
 border-bottom-color:var(--rule)!important}
.leaflet-popup-content-wrapper{background:var(--panel);color:var(--ink);border-radius:8px}
.leaflet-popup-tip{background:var(--panel)}
.leaflet-tooltip.rt{background:var(--panel);border:1px solid var(--rule);color:var(--ink);
  font:12px var(--sans);border-radius:6px;box-shadow:0 4px 16px rgba(0,0,0,.18);padding:6px 9px}
.leaflet-tooltip.rt:before{display:none}
.leaflet-tooltip.rt b{display:block;margin-bottom:2px}
.leaflet-tooltip.rt span{color:var(--dim);font-size:11px}
/* висота в частках екрана, інакше висока картка вилазить за верх вікна */
.lp{font-size:12.5px;max-height:min(420px,58vh);overflow-y:auto;overscroll-behavior:contain}
.lp b{display:block;margin-bottom:5px;font-size:13px}
.lp a{color:var(--ink);text-decoration:none}.lp a:hover{text-decoration:underline}
.lp li{margin-bottom:4px;font-size:11.5px}.lp ul{padding-left:15px;margin:3px 0}
.lp .tt{color:var(--dim);font-size:11.5px;margin-bottom:7px}
.bd{width:100%;border-collapse:collapse;margin-bottom:8px}
.bd td{padding:2px 0;font-size:12px;vertical-align:top}
.bd td:last-child{text-align:right;padding-left:10px;color:var(--ink);width:44px;font-family:var(--mono)}
.hg{display:flex;align-items:flex-end;gap:1px;height:24px;margin:2px 0 1px}
.hg i{flex:1;background:var(--ink);opacity:.8;border-radius:1px 1px 0 0}
.hx{display:flex;justify-content:space-between;font-size:9.5px;color:var(--faint);margin-bottom:5px;font-family:var(--mono)}
.hn{font-size:11px;color:var(--dim);background:var(--sunk);padding:4px 7px;border-radius:4px;margin-bottom:7px}
.pcard{background:var(--sunk);border-left:3px solid var(--ink);border-radius:5px;padding:8px 9px;margin:8px 0}
.pcard .ph{font-size:10px;text-transform:uppercase;letter-spacing:.07em;color:var(--dim);margin-bottom:3px}
.pcard .pt{font-size:13px;font-weight:600;margin-bottom:5px;line-height:1.25}
.pcard .pm{font-size:11.5px;color:var(--dim);margin-bottom:2px}
.pcard .pm b{color:var(--ink)}
.pcard .art{margin:3px 0 5px}
.pcard .art li{list-style:none;margin-bottom:4px}
.pcard .art .sh{font-size:11.5px;color:var(--ink)}
.pcard .art .ln{display:block;font-size:10.5px;color:var(--dim);line-height:1.35;margin-top:1px}
.pcard .pf{font-size:10.5px;color:var(--faint);margin-top:4px;line-height:1.4}
.pcard .why{font-size:11px;color:var(--dim);background:var(--panel);border-radius:4px;padding:6px 8px;margin-top:5px}
.pbtn{width:100%;padding:7px;background:var(--ink);color:var(--panel);border:0;border-radius:6px;
 font:inherit;font-size:12px;cursor:pointer;margin-top:7px}
.pbtn:hover{opacity:.85}
/* ---- шар чинників середовища ---- */
.fgh{font-size:10px;text-transform:uppercase;letter-spacing:.07em;color:var(--dim);margin:9px 0 2px}
/* Групи інфраструктури — згорнуті, як і групи ризику: сімнадцять прапорців
   поспіль читалися як звалище. Стиль повторює #frisk .rg навмисно, щоб
   панель мала одну мову. */
#ffact .fg{margin-bottom:6px;border-radius:6px;background:var(--sunk);border:1px solid var(--rule)}
#ffact .fg>summary{list-style:none;cursor:pointer;display:flex;align-items:center;gap:7px;
  padding:7px 9px;font-size:12px;color:var(--dim)}
#ffact .fg>summary::-webkit-details-marker{display:none}
#ffact .fg>summary::before{content:'\25B8';color:var(--faint);font-size:9px;transition:.15s}
#ffact .fg[open]>summary::before{transform:rotate(90deg)}
#ffact .fg>summary .gn{flex:1;font-weight:500}
#ffact .fg>summary .gc{font-size:10px;color:var(--faint);padding:1px 6px;border:1px solid var(--rule);border-radius:99px;font-family:var(--mono)}
#ffact .fg label{margin:0 8px 4px}
/* Прапорець «тихих» вулиць стоїть НАД поясненням і відокремлений рискою:
   це не ще один шар ризику, а інший погляд на ті самі теми. */
#fquietw{display:flex;align-items:flex-start;gap:7px;margin:8px 0 6px;padding-top:8px;
  border-top:1px solid var(--rule);font-size:11.5px;color:var(--dim);cursor:pointer;line-height:1.4}
#fquietw input{margin-top:2px;flex:none}
/* Постійне застереження про походження адреси. Помітне, але не кричить: воно
   має читатися щоразу, а не лякати. */
.warnbar{margin:8px 0 2px;padding:7px 9px;border-radius:6px;font-size:11.5px;
  line-height:1.45;color:var(--dim);background:var(--sunk);border:1px solid var(--rule)}
.warnbar b{color:var(--ink)}
#ffact label{font-size:12px}
#ffact .n{color:var(--faint);font-size:10.5px;margin-left:auto;flex:0 0 auto;font-family:var(--mono)}
#ffact .sw{width:9px;height:9px;border-radius:99px;flex:0 0 auto;margin-top:3px}
/* значок виду об'єкта: коло, обведене кольором ролі, всередині символ виду */
.fic{display:flex;align-items:center;justify-content:center;width:20px;height:20px;
 border-radius:99px;border:1.5px solid;font-size:11px;line-height:1;
 background:var(--panel);box-shadow:0 0 0 1px var(--ground)}
#ffact .sw2{width:18px;height:18px;font-size:10px;flex:0 0 auto;margin-top:0;
 box-shadow:none}
.pbtn2{width:100%;padding:6px;background:var(--sunk);color:var(--ink);border:1px solid var(--rule);
 border-radius:6px;font:inherit;font-size:11.5px;cursor:pointer;margin-top:5px}
.pbtn2:hover{background:var(--rule)}
.ex{font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;color:var(--faint);margin-top:6px}
.rpop b{display:block;margin-bottom:4px;font-size:13px}
.rpop .rmeth{font-size:11px;color:var(--dim);margin:6px 0;line-height:1.4}
.rpop table{width:100%;border-collapse:collapse;margin-top:4px}
.rpop td{padding:1.5px 0;font-size:11px}
.rpop td:last-child{text-align:right;color:var(--ink);font-family:var(--mono)}
.rpop .rdoc{display:block;margin-top:8px;font-size:11.5px;color:var(--ink);text-decoration:none}
.rpop .rdoc:hover{text-decoration:underline}
/* Чинники окремої вулиці. Ліворуч — що виміряно, праворуч — скільки тут
   і скільки буває звичайно. Кратність окремим тонким рядком під назвою:
   вона пояснює, чому ця ознака взагалі в переліку. */
.rpop .rwhy{margin:8px 0 3px;font-size:11px;color:var(--dim);
  text-transform:uppercase;letter-spacing:.04em}
.rpop table.fx td{padding:3px 0;font-size:11.5px;vertical-align:top;color:var(--dim)}
.rpop table.fx td.fv{text-align:right;color:var(--dim);white-space:nowrap;padding-left:10px}
.rpop table.fx td.fv b{display:inline;font-size:12px;color:var(--ink);margin:0}
.rpop table.fx td.fv i{font-style:normal;color:var(--faint);font-size:10.5px}
.rpop table.fx .fr{color:var(--dim);font-size:10.5px;margin-top:1px;line-height:1.35}
#docs a{display:block;font-size:12.5px;color:var(--ink);text-decoration:none;padding:3px 0}
#docs a:hover{text-decoration:underline}
@media(max-width:760px){#wrap{flex-direction:column}#side{width:100%;flex:0 0 auto;max-height:50%}}
</style></head>"""
