// Без WebGL векторна карта не намалюється зовсім. Запасної Leaflet-збірки
// більше немає (36.8): друга карта вдвічі збільшувала код і розходилася з
// головною. Тоді — один рядок замість карти, щоб не було порожнього екрана.
function bezKarty(t){const m=document.getElementById('map');
 if(m) m.innerHTML='<div class="k-bez">'+t+'</div>'}
{let ok=false;
 try{const c=document.createElement('canvas');ok=!!(c.getContext('webgl2')||c.getContext('webgl'))}catch(e){}
 if(!ok){bezKarty('Цей браузер не показує карту: потрібен WebGL.');throw new Error('немає WebGL')}}
// MapLibre 6.x — лише ES-модуль, глобального maplibregl більше немає.
// Точна версія: оновлення бібліотеки має бути нашим рішенням, а не сюрпризом.
// Лежить поруч із сайтом (vendor/, ZAVDANNYA-41 4.5): кіоск і карта без CDN.
let maplibregl;
try{const m_=await import('./vendor/maplibre-gl-6.10.0/maplibre-gl.mjs');
 maplibregl=m_.default||m_}
catch(e){bezKarty('Карта не завантажилася. Оновіть сторінку.');throw e}