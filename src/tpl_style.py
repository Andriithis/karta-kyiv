# -*- coding: utf-8 -*-
"""Шапка сторінки й усі стилі карти.

Тут: <!DOCTYPE>, <head>, підключення Leaflet і <style> цілком.
Розміри панелі, вигляд спливних вікон — усе змінюється тут.
Кольори НЕ пишуться літералом: вони живуть у змінних двох тем на початку
блока. Жодного тексту й жодної логіки: підписи — у tpl_body, поведінка —
у tpl_core і рушіях.

Теми й типографіка — з макета PROBA-VYGLIADU.html, картка-навігатор — із
затвердженого макета site/maket-panel.html (версія 4).
"""
LIBS_LEAFLET = r"""<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>"""
# MapLibre 6.x поставляється лише як ES-модуль: dist/maplibre-gl.js більше
# немає, тож сам JS підтягує скрипт сторінки через import (див. step3_tpl).
# Тут лише стилі бібліотеки. Версія точна — оновлення не має приходити саме.
LIBS_GL = r"""<link rel="stylesheet" href="https://unpkg.com/maplibre-gl@6.10.0/dist/maplibre-gl.css">"""
HEAD_TPL = r"""<!DOCTYPE html><html lang="uk"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Карта правопорушень Києва</title>
__LIBS__
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
 --glass:rgba(255,255,255,.80);--shadow:drop-shadow(0 1px 1.5px rgba(16,18,22,.22));
 --card:rgba(255,255,255,.94);--card-shadow:0 6px 24px rgba(20,22,26,.14),0 1px 3px rgba(20,22,26,.10)}
body[data-t="temna"]{--panel:#0f1217;--sunk:#151920;--ink:#eaebef;--dim:#8d94a2;
 --faint:#5b6371;--rule:#1f242b;--ground:#0c0e12;--halo:#0b0d11;
 --glass:rgba(15,18,23,.78);--shadow:drop-shadow(0 1px 2px rgba(0,0,0,.55));
 --card:rgba(20,23,29,.94);--card-shadow:0 6px 24px rgba(0,0,0,.5),0 1px 3px rgba(0,0,0,.4)}
:root{--sans:Commissioner,"Segoe UI",system-ui,sans-serif;
 --mono:"IBM Plex Mono",ui-monospace,Consolas,monospace;
 --disp:Unbounded,Commissioner,sans-serif}
*{box-sizing:border-box}
html,body{margin:0;height:100%;font:14px/1.5 var(--sans);background:var(--ground);color:var(--ink);
 -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
/* ---- КАРТКА-НАВІГАТОР ----
   Карта на все вікно; панель — картка «в повітрі» праворуч угорі, заввишки
   за змістом (RISHENNYA, розд. 18). Значення — з затвердженого макета
   site/maket-panel.html, версія 4: будь-яка зміна вигляду спершу
   узгоджується на макеті, тож тут їх не підбирати на око. */
#wrap{position:relative;height:100%}
#map{position:absolute;inset:0}
aside#side{position:absolute;top:14px;right:14px;z-index:1100;width:292px;
 background:var(--card);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);
 border-radius:6px;box-shadow:var(--card-shadow);padding:14px 16px 12px;color:var(--ink);
 display:flex;flex-direction:column;gap:14px;max-height:calc(100% - 28px);overflow:auto;scrollbar-width:thin}
.search{display:flex;align-items:center;gap:8px;border:1px solid var(--rule);border-radius:4px;
 padding:7px 9px;color:var(--faint);font-size:13px}
.search svg{flex:none}
.search input{border:0;outline:0;background:none;font:inherit;color:var(--ink);flex:1;min-width:0;padding:0}
.search input::placeholder{color:var(--faint)}
.search input::-webkit-search-cancel-button{display:none}
.sugg{display:flex;flex-direction:column;margin-top:-14px;border:1px solid var(--rule);border-top:0;border-radius:0 0 4px 4px}
.sugg[hidden]{display:none}
.sugg button{background:none;border:0;padding:6px 9px;text-align:left;font:400 12.5px var(--sans);color:var(--ink);cursor:pointer}
.sugg button:hover{background:var(--sunk)}
.modes{display:flex;gap:16px;border-bottom:1px solid var(--rule)}
.modes button{background:none;border:0;padding:0 0 7px;font:400 13.5px var(--sans);color:var(--dim);
 cursor:pointer;border-bottom:1.5px solid transparent;margin-bottom:-1px}
.modes button[aria-pressed="true"]{color:var(--ink);border-color:var(--ink)}
.types{display:grid;grid-template-columns:1fr 1fr;gap:2px 10px}
.type{display:flex;align-items:center;gap:8px;background:none;border:0;padding:5px 0;
 font:400 13.5px var(--sans);color:var(--ink);cursor:pointer;text-align:left}
.type i{width:11px;height:11px;border-radius:2px;border:1.5px solid var(--c);background:var(--c);flex:none}
.type[aria-pressed="false"]{color:var(--faint)}
.type[aria-pressed="false"] i{background:transparent}
.sw{display:flex;align-items:center;justify-content:space-between;gap:8px;font-size:13.5px;padding:2px 0;
 background:none;border:0;color:var(--ink);cursor:pointer;width:100%;font-family:var(--sans);text-align:left}
.sw[hidden]{display:none}
.tog{width:28px;height:16px;border-radius:8px;background:var(--rule);position:relative;flex:none;transition:background .15s}
.tog::after{content:"";position:absolute;top:2px;left:2px;width:12px;height:12px;border-radius:50%;
 background:var(--panel);box-shadow:0 1px 2px rgba(0,0,0,.25);transition:left .15s}
.sw[aria-pressed="true"] .tog{background:var(--ink)}
.sw[aria-pressed="true"] .tog::after{left:14px}
/* поріг зуму: поки масштаб замалий — приглушений і не натискається */
.sw[aria-disabled="true"]{color:var(--faint);cursor:default}
.sw[aria-disabled="true"] .tog{opacity:.45}
.chips{display:flex;flex-wrap:wrap;gap:4px 12px;padding:2px 0 0}
.chips[hidden]{display:none}
.chip{background:none;border:0;padding:0 0 1px;font:400 12px var(--sans);color:var(--faint);
 cursor:pointer;border-bottom:1px solid transparent}
.chip[aria-pressed="true"]{color:var(--ink);border-color:var(--ink)}
.grp{display:flex;flex-direction:column;gap:6px;padding-top:12px;border-top:1px solid var(--rule)}
.sel{display:flex;justify-content:space-between;align-items:center;font-size:13.5px;border:0;
 background:none;padding:0;color:var(--ink);cursor:pointer;font-family:var(--sans);width:100%}
.sel[hidden]{display:none}
.sel span:last-child{color:var(--dim);font-size:12px}
.menu{display:flex;flex-direction:column;gap:2px;padding:4px 0 0 0}
.menu[hidden]{display:none}
.menu button,.menu a{background:none;border:0;padding:3px 0;text-align:left;font:400 13px var(--sans);
 color:var(--ink);cursor:pointer;text-decoration:none}
.menu button[aria-pressed="true"]{text-decoration:underline;text-underline-offset:3px}
.menu a span{color:var(--dim)}
.more{background:none;border:0;padding:6px 0 0;font:400 12px var(--sans);color:var(--dim);cursor:pointer}
.more[aria-expanded="true"]{color:var(--ink)}
/* «Розширено» — друга картка ліворуч від основної, під смугою періоду */
.adv{position:absolute;top:62px;right:318px;z-index:1100;width:min(560px,calc(100% - 350px));
 max-height:calc(100% - 76px);overflow:auto;background:var(--card);backdrop-filter:blur(8px);
 -webkit-backdrop-filter:blur(8px);border-radius:6px;box-shadow:var(--card-shadow);padding:14px 16px;color:var(--ink)}
.adv[hidden]{display:none}
.advtop{display:grid;gap:6px;border-bottom:1px solid var(--rule);padding:0 26px 10px 0;margin-bottom:10px}
.advrow{display:grid;grid-template-columns:70px 1fr;align-items:baseline;font-size:12.5px}
.advrow>span{color:var(--dim)}
.advh{display:flex;justify-content:space-between;align-items:center;font-weight:500;margin-bottom:8px}
.advh button{background:none;border:0;font-size:18px;color:var(--dim);cursor:pointer;line-height:1}
.advgrid{columns:2 230px;column-gap:22px}
.ag{break-inside:avoid;margin:0 0 12px}
.ag h4{margin:0 0 3px;font:500 13px var(--sans);display:flex;align-items:center;gap:7px}
.ag h4 i{width:10px;height:10px;border-radius:2px;display:block}
.ag h5{margin:6px 0 2px;font:500 10px var(--mono);letter-spacing:.1em;text-transform:uppercase;
 color:var(--faint);display:flex;justify-content:space-between}
.ag h5 button{background:none;border:0;padding:0;font:inherit;color:var(--dim);cursor:pointer;
 letter-spacing:.1em;text-transform:uppercase}
/* клас .art уже зайнятий переліком статей у картці проблеми — тож лише всередині .adv */
.adv .art{display:grid;grid-template-columns:12px 1fr;gap:7px;align-items:start;padding:2px 0;
 font-size:12.5px;line-height:1.3;cursor:pointer}
.adv .art input{margin:2px 0 0;accent-color:var(--ink)}
.adv .art small{display:block;font:400 10px var(--mono);color:var(--faint)}
.advfoot{border-top:1px solid var(--rule);padding-top:10px;margin-top:4px}
aside#side button:focus-visible,.adv button:focus-visible{outline:2px solid #3d91c4;outline-offset:2px}
@media (max-width:1000px){.adv{right:14px;left:14px;width:auto;top:auto;bottom:14px;max-height:45%}}
/* Телефон: карта на все вікно, картка поверх неї внизу, приблизно половина
   екрана з прокруткою всередині. Шторка, яку тягнуть пальцем, — окремо,
   після MapLibre. */
@media (max-width:700px){aside#side{width:auto;left:14px;top:auto;bottom:14px;max-height:55%}}
/* ---- ПАНЕЛЬ РІШЕНЬ АДРЕСИ ---- */
#pan{position:absolute;top:0;left:0;bottom:0;width:380px;max-width:34vw;z-index:1200;
 background:var(--panel);border-right:1px solid var(--rule);display:flex;flex-direction:column;
 transform:translateX(-100%);transition:transform .22s ease}
#pan.on{transform:none}
#panh{padding:16px 18px 12px;border-bottom:1px solid var(--rule);position:relative;flex:0 0 auto}
#panh .pa{font:500 14.5px/1.25 var(--disp);letter-spacing:-.03em;padding-right:26px}
#panh .ps{font-size:12.5px;color:var(--dim);margin-top:5px}
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
/* застереження про дані — дрібно й блідо, як рядок в атрибуції */
.lp .an{color:var(--faint);font-size:10.5px;margin:-3px 0 5px}
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
/* ---- MapLibre ----
   Ті самі змінні тем, що й для Leaflet: вікно, атрибуція й кнопки масштабу
   мають виглядати однаково в обох збірках, інакше паритет не перевіриш оком.
   На Leaflet-сторінці ці правила просто ні на що не лягають. */
.maplibregl-map{font-family:var(--sans)}
.maplibregl-popup-content{background:var(--panel);color:var(--ink);border-radius:8px;
 padding:12px 14px;box-shadow:0 3px 14px rgba(0,0,0,.25)}
.maplibregl-popup-anchor-bottom .maplibregl-popup-tip{border-top-color:var(--panel)}
.maplibregl-popup-anchor-top .maplibregl-popup-tip{border-bottom-color:var(--panel)}
.maplibregl-popup-anchor-left .maplibregl-popup-tip{border-right-color:var(--panel)}
.maplibregl-popup-anchor-right .maplibregl-popup-tip{border-left-color:var(--panel)}
.maplibregl-ctrl-attrib{background:var(--glass)!important;color:var(--faint);font-size:9.5px}
.maplibregl-ctrl-attrib a{color:var(--dim)}
.maplibregl-ctrl-group{background:var(--panel)}
</style></head>"""
HEAD = HEAD_TPL.replace('__LIBS__', LIBS_LEAFLET)
HEAD_GL = HEAD_TPL.replace('__LIBS__', LIBS_GL)
