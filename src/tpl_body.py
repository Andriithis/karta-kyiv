# -*- coding: utf-8 -*-
"""Розмітка панелі.

Порожні гнізда, які наповнює JavaScript (tpl_core), і нерухомі підписи.
Панель — картка-навігатор над картою праворуч угорі (RISHENNYA, розд. 18):
пошук, режим, види подій, «Розширено», прогноз ризику, контекст, район і
звіти. Друга картка, «Статті», відкривається ліворуч від неї.

Жодного числа й жодного пояснювального напису — навмисно. Вигляд узято з
затвердженого макета site/maket-panel.html; будь-яка його зміна спершу
узгоджується на макеті.
"""
BODY = r"""<body data-t="svitla"><div id="wrap"><div id="map"></div>
<div class="adv" id="adv" hidden>
 <div class="advtop">
  <div class="advrow"><span>Рік</span><div class="chips" id="fyc"></div></div>
  <div class="advrow"><span>Час доби</span><div class="chips" id="hr"></div></div>
 </div>
 <div class="advh"><span>Статті</span><button id="advx" aria-label="Закрити">×</button></div>
 <div class="advgrid" id="advgrid"></div>
 <div class="advfoot"><button class="sw" id="fprec" aria-pressed="false"><span>Лише точні адреси</span><span class="tog"></span></button></div>
</div>
<aside id="side">
 <label class="search"><svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><circle cx="7" cy="7" r="5"/><path d="M11 11l3.5 3.5"/></svg><input id="q" type="search" placeholder="Адреса або вулиця" autocomplete="off" spellcheck="false"></label>
 <div class="sugg" id="sugg" hidden></div>
 <div class="modes" id="fcat"></div>
 <div>
  <div class="types" id="fa"></div>
  <button class="more" id="advbtn" aria-expanded="false">Розширено ›</button>
 </div>
 <div>
  <button class="sw" id="frisk" aria-pressed="false"><span>Прогноз ризику</span><span class="tog"></span></button>
  <div class="chips" id="friskx" hidden><button class="chip" id="fquietc" aria-pressed="false">тихі вулиці</button></div>
 </div>
 <div class="grp" id="fctx">
  <button class="sw" data-ctx="pop" aria-pressed="false"><span>Населення</span><span class="tog"></span></button>
  <button class="sw" data-ctx="flows" aria-pressed="false"><span>Потоки людей</span><span class="tog"></span></button>
  <button class="sw" data-ctx="facts" aria-pressed="false"><span>Об'єкти довкола</span><span class="tog"></span></button>
 </div>
 <div class="grp">
  <button class="sel" id="dbtn"><span>Район</span><span id="dval">усе місто ▾</span></button>
  <div class="menu" id="fd" hidden></div>
  <div class="menu" id="docs"></div>
 </div>
 <!-- Сховані фільтри. На них спирається draw(): прапорці років (їх
      перемикають чипи «Рік» у «Розширено»), фільтр за судом дублював
      перехід у район, статті вмикає сітка видів і картка «Статті». Тут-таки
      прапорці шарів ризику, населення, потоків і видів об'єктів — їх читають
      drawRisks() і drawFacts(). -->
 <div id="hidden-filters" hidden><div id="fy"></div><div id="fc"></div>
 <div id="fasub"></div><div id="ffact"></div></div>
</aside>
<div id="pan"><div id="panh"></div><div id="panb"></div></div></div>"""
