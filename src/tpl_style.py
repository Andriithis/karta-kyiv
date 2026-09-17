# -*- coding: utf-8 -*-
"""Шапка сторінки й усі стилі карти.

Тут: <!DOCTYPE>, <head>, підключення Leaflet і <style> цілком.
Розміри панелі, вигляд спливних вікон — усе змінюється тут.
Кольори НЕ пишуться літералом: вони живуть у змінних трьох тем на початку
блока. Жодного тексту й жодної логіки: підписи — у tpl_body, поведінка —
у tpl_map і tpl_popup.

Панель узята з погодженого макета PROBA-VYGLIADU.html: жодних залитих
кнопок, карток, тіней і заокруглень; активний стан — підкреслення,
розділення — волосяна лінія.
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
*{box-sizing:border-box}
html,body{margin:0;height:100%;font:14px/1.5 var(--sans);background:var(--ground);color:var(--ink);
 -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
/* ---- ПАНЕЛЬ ----
   Карта ліворуч, панель праворуч: погляд починає з міста, а не з переліку
   галочок. Ширина 360 px — з макета. */
#wrap{display:flex;height:100%}
#map{flex:1;min-width:0}
aside#side{width:360px;flex:0 0 360px;background:var(--panel);color:var(--ink);
 border-left:1px solid var(--rule);display:flex;flex-direction:column;gap:26px;
 padding:26px 22px 0;overflow-y:auto;scrollbar-width:thin}
.brand{display:flex;justify-content:space-between;align-items:baseline;gap:8px}
.brand b{font:500 15px/1 var(--disp);letter-spacing:-.03em}
.brand span{font:400 9px/1 var(--mono);letter-spacing:.24em;color:var(--faint)}
.sub{color:var(--dim);font-size:11.5px}
#cntl{font:400 11.5px var(--mono);color:var(--dim);font-variant-numeric:tabular-nums}
#backl a{color:var(--ink);font-size:12px;text-decoration:none}
#backl a:hover{text-decoration:underline}
.lab{font:500 9px/1 var(--mono);letter-spacing:.2em;text-transform:uppercase;color:var(--faint)}
.blk{display:flex;flex-direction:column;gap:12px}
/* режим: активний підкреслений, не залитий */
.seg{display:flex;gap:18px;border-bottom:1px solid var(--rule)}
.seg button{all:unset;cursor:pointer;font-size:13.5px;color:var(--dim);padding-bottom:9px;
 border-bottom:1.5px solid transparent;margin-bottom:-1px;transition:color .16s}
.seg button:hover{color:var(--ink)}
.seg button[aria-pressed="true"]{color:var(--ink);border-bottom-color:var(--ink)}
.seg button i{font-style:normal;font-family:var(--mono);font-size:10px;color:var(--faint);margin-left:5px}
.rhead{display:flex;justify-content:space-between;align-items:baseline}
/* рядок теми: квадрат вмикає події, риска — прогноз ризику тієї самої теми,
   праворуч від риски дрібним точність шару */
.rows{display:flex;flex-direction:column}
.row{display:grid;grid-template-columns:14px 1fr auto 20px 30px;align-items:center;gap:12px;
 padding:9px 0;border-bottom:1px solid var(--rule);cursor:pointer}
.row:last-child{border-bottom:0}
.row .sq{width:12px;height:12px;justify-self:center;border-radius:2px;transition:all .16s}
.row .nm{font-size:13.5px;letter-spacing:-.004em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.row .n{font:400 11.5px var(--mono);color:var(--dim);font-variant-numeric:tabular-nums;text-align:right}
.row .ln{width:20px;height:3px;border-radius:2px;background:var(--rule);transition:background .16s}
.row .acc{font:400 10px var(--mono);color:var(--faint);text-align:right;font-variant-numeric:tabular-nums}
.row[data-on="0"] .nm,.row[data-on="0"] .n{color:var(--faint)}
.row[data-on="0"] .sq{background:transparent!important;box-shadow:inset 0 0 0 1.5px var(--faint)}
.row[data-nod="1"] .ln{opacity:.3}
.quiet{display:flex;gap:8px;align-items:flex-start;font-size:11.5px;color:var(--dim);cursor:pointer;line-height:1.4}
.quiet input{margin:2px 0 0;flex:none;width:13px;height:13px;accent-color:var(--ink)}
.dists{display:flex;flex-wrap:wrap;gap:5px 14px}
.dists span{font-size:12px;color:var(--dim);cursor:pointer;border-bottom:1.5px solid transparent;padding-bottom:2px}
.dists span:hover{color:var(--ink)}
.dists span.on{color:var(--ink);border-bottom-color:var(--ink)}
.dists span i{font-style:normal;font-family:var(--mono);font-size:9.5px;color:var(--faint);margin-left:4px}
.docs{display:flex;flex-direction:column}
.docs a{display:flex;justify-content:space-between;align-items:baseline;gap:8px;text-decoration:none;
 color:var(--ink);font-size:13px;padding:8px 0;border-bottom:1px solid var(--rule);transition:opacity .16s}
.docs a:hover{opacity:.62}
.docs a em{font:400 9.5px var(--mono);font-style:normal;color:var(--faint);letter-spacing:.1em}
.foot{margin-top:auto;padding:18px 0 26px;border-top:1px solid var(--rule)}
.fine{font-size:10.5px;line-height:1.5;color:var(--faint);margin-top:10px}
.fine b{color:var(--dim)}
/* ---- ПАНЕЛЬ РІШЕНЬ АДРЕСИ ---- */
#pan{position:absolute;top:0;left:0;bottom:0;width:380px;max-width:34vw;z-index:1200;
 background:var(--panel);border-right:1px solid var(--rule);display:flex;flex-direction:column;
 transform:translateX(-100%);transition:transform .22s ease}
#pan.on{transform:none}
#panh{padding:16px 18px 12px;border-bottom:1px solid var(--rule);position:relative;flex:0 0 auto}
#panh .pa{font:500 14.5px/1.25 var(--disp);letter-spacing:-.03em;padding-right:26px}
#panh .ps{font:400 11px var(--mono);color:var(--faint);margin-top:5px}
#panx{position:absolute;top:12px;right:14px;width:22px;height:22px;padding:0;margin:0;
 background:none;border:0;color:var(--dim);font-size:16px;line-height:1;cursor:pointer}
#panx:hover{color:var(--ink)}
#panb{flex:1;overflow-y:auto;padding:10px 18px 22px}
.cs{border-top:1px solid var(--rule);padding:10px 0}
.cs:first-child{border-top:0}
.cd{font-size:12.5px;color:var(--dim)}
.cd b{color:var(--ink);font-weight:600}
.cn{font:400 10.5px var(--mono);color:var(--faint);margin-top:2px}
.cx{font-size:12.5px;color:var(--dim);line-height:1.5;margin-top:6px}
.cl{margin-top:6px;display:flex;flex-wrap:wrap;gap:10px}
.cl a{font-size:11.5px;color:var(--ink);text-decoration:none;border-bottom:1px solid var(--rule)}
.cl a:hover{opacity:.62}
#panb .sub{font-size:12px;color:var(--faint);padding:8px 0}
@media(max-width:900px){#pan{width:100%;max-width:100%}}
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
.cbadge{display:inline-block;padding:1px 7px;border-radius:99px;font-size:10.5px;
 text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px}
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
.pbtn2{width:100%;padding:6px;background:var(--sunk);color:var(--ink);border:1px solid var(--rule);
 border-radius:6px;font:inherit;font-size:11.5px;cursor:pointer;margin-top:5px}
.pbtn2:hover{background:var(--rule)}
/* значок виду об'єкта: коло, обведене кольором ролі, всередині символ виду */
.fic{display:flex;align-items:center;justify-content:center;width:20px;height:20px;
 border-radius:99px;border:1.5px solid;font-size:11px;line-height:1;
 background:var(--panel);box-shadow:0 0 0 1px var(--ground)}
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
@media(max-width:900px){#wrap{flex-direction:column}#map{height:58%;flex:none}
 aside#side{width:auto;flex:1;border-left:0;border-top:1px solid var(--rule);padding:18px 16px 0}}
</style></head>"""
