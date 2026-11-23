// ==== КЕШ КІОСКУ (36.122, S-Н.16) ====
// Реєструє його лише кіоск (?kiosk=1, kiosk.js): на звичайних відвідувачів він
// не впливає, і стара версія сторінки в них не застрягне. Кіоск один раз кладе
// в кеш сайт, підкладку Києва й дані турів і далі працює без мережі.
//
// Що звідки:
// - файли з хешем у назві (dani/*.<хеш>.json), vendor/, zvuk/, плитки, шрифти
//   й значки підкладки — спершу кеш: їхній вміст за цією адресою не міняється;
// - сторінка, стиль підкладки, poshuk/skargy/spravy/adresy — спершу мережа (до
//   4 с), без мережі — кеш: так нова збірка приходить сама, а без мережі кіоск
//   бере останню, яку бачив.
const KESH='karta-kiosk-1';
const MEREZHA_MS=4000;
self.addEventListener('install',()=>self.skipWaiting());
self.addEventListener('activate',e=>e.waitUntil(self.clients.claim()));
const stalyi=u=>/\.[0-9a-f]{10}\.json$/.test(u.pathname)||/\/(vendor|zvuk)\//.test(u.pathname)
 ||(u.hostname==='tiles.openfreemap.org'&&/\.(pbf|png|json)$/.test(u.pathname)&&!/^\/styles\//.test(u.pathname)&&u.pathname!=='/planet');
async function keshPershyi(r){const k=await caches.open(KESH), b=await k.match(r);
 if(b) return b;
 const v=await fetch(r); if(v.ok) k.put(r,v.clone()); return v}
async function merezhaPersha(r){const k=await caches.open(KESH);
 try{const v=await Promise.race([fetch(r),new Promise((_,ne)=>setTimeout(()=>ne(new Error('довго')),MEREZHA_MS))]);
  if(v.ok) k.put(r,v.clone()); return v}
 catch(e){const b=await k.match(r); if(b) return b; throw e}}
self.addEventListener('fetch',e=>{const r=e.request; if(r.method!=='GET') return;
 const u=new URL(r.url);
 if(u.origin!==location.origin&&u.hostname!=='tiles.openfreemap.org') return;
 // перевірка нової версії (kiosk.js) — лише мережа, повз кеш
 if(u.searchParams.has('perevirka')) return;
 e.respondWith(stalyi(u)?keshPershyi(r):merezhaPersha(r))});
