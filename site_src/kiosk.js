// ==== КІОСК (?kiosk=1) ====
// Тур — спільний рушій tpl_tur (turPusk); кіоск лише вирішує, коли тур іде:
// на заставці — по колу, після дотику — зупинка, 90 с простою — знову тури
if(new URLSearchParams(location.search).has('kiosk')){(async()=>{
 document.body.classList.add('kiosk'); TUR_KIOSK=true; turKnopka();
 const TURY=DANI.tury?await vantazh(DANI.tury):[]; if(!TURY_D) TURY_D=TURY;
 if(!TUR_KOLODA&&DANI.koloda) TUR_KOLODA=await vantazh(DANI.koloda);
 const vsogo=M.podii_vsogo??P.reduce((a,p)=>a+(p[3]?p[4].length:0),0);
 const root=map.getContainer().parentElement;
 const zast=turEl(`<div class="ki-zast"><div class="ki-t">Карта правопорушень Києва</div>
  <div class="ki-n">${fmt(vsogo)} ${pl(vsogo,'подія','події','подій')} з рішень судів</div></div>`);
 const dotyk=turEl(`<div class="ki-dotyk">Торкніться екрана</div>`);
 const panel=turEl(`<div class="ki-p" hidden><div class="ki-ph">Тури</div><div class="ki-tury"></div>
  <div class="ki-ph">Види</div><div class="ki-vydy"></div><div class="ki-ph">Райони</div><div class="ki-rai"></div></div>`);
 const verkh=turEl(`<div class="ki-v" hidden>${[['soty','Соти'],['rings','Кільця'],['addr','Адреси']].map(([k,n])=>`<button data-kv="${k}">${n}</button>`).join('')}</div>`);
 const start=turEl(`<button class="ki-start" hidden>На старт</button>`);
 [zast,dotyk,panel,verkh,start].forEach(x=>root.appendChild(x));
 // «Мікс» — колода (етап 3), далі іменовані тури
 const TURY_K=[...(TUR_KOLODA&&TUR_KOLODA.length?[{nazva:'Мікс',zup:null}]:[]),
  ...TURY.map(t=>({nazva:t.nazva,zup:t.zupynky.map(z=>turIzTury(z,t.nazva))}))];
 panel.querySelector('.ki-tury').innerHTML=TURY_K.map((t,i)=>`<button data-kt="${i}">${esc(t.nazva)}</button>`).join('');
 panel.querySelector('.ki-vydy').innerHTML=M.groups.map((g,gi)=>`<button data-kg="${gi}"><i style="background:${PALA[gi%PALA.length]}"></i>${esc(shortOf(gi))}</button>`).join('');
 panel.querySelector('.ki-rai').innerHTML=DN.map((d,i)=>`<button data-kr="${i}">${esc(d)}</button>`).join('');
 let OST=Date.now(), ZASTAVKA=true;
 const turK=i=>{const t=TURY_K[i]; if(!t) return; turPusk(t.zup||turZupynky(),{nazva:t.zup?t.nazva:'',kolom:true})};
 // на заставці — колода (якщо є), інакше всі іменовані тури поспіль
 const turVsi=()=>turPusk(turZupynky(),{kolom:true});
 function naZastavku(){ZASTAVKA=true; panel.hidden=verkh.hidden=start.hidden=true; zast.hidden=dotyk.hidden=false;
  if(CURD>=0) exitDistrict(); turVsi()}
 function rozbudyty(){ZASTAVKA=false; zast.hidden=dotyk.hidden=true; panel.hidden=verkh.hidden=start.hidden=false; turStop(false)}
 // дотик будь-де: на заставці — будить, під час туру — зупиняє тур
 root.addEventListener('pointerdown',e=>{OST=Date.now();
  if(ZASTAVKA){e.stopPropagation(); rozbudyty(); return}
  if(turIde()&&!e.target.closest('[data-kt]')) turStop(false)},true);
 panel.onclick=e=>{const t=e.target.closest('[data-kt]'); if(t) return turK(+t.dataset.kt);
  const g=e.target.closest('[data-kg]'); if(g){const b=document.querySelector(`#fa .type[data-g="${g.dataset.kg}"]`); if(b) b.click();
   g.classList.toggle('ki-off',b&&!typeOn(+g.dataset.kg)); return}
  const r=e.target.closest('[data-kr]'); if(r) enterDistrict(+r.dataset.kr)};
 verkh.onclick=e=>{const b=e.target.closest('[data-kv]'); if(b) setView(b.dataset.kv)};
 start.onclick=naZastavku;
 setInterval(()=>{const t=(Date.now()-OST)/1000;
  if(!ZASTAVKA&&t>180) naZastavku();
  else if(!ZASTAVKA&&t>90&&!turIde()) turVsi()},1000);
 naZastavku();
})()}
