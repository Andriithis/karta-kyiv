# -*- coding: utf-8 -*-
"""Розмітка панелі.

Порожні гнізда (<div id="...">), які наповнює JavaScript, і нерухомі підписи.
Панель стоїть ПРАВОРУЧ від карти: око починає з міста, а не з переліку
галочок. Блоків три — правопорушення з ризиком усередині, контекст, район, —
плюс режим угорі й документи в підвалі.

Пояснювальних абзаців тут немає навмисно: те, що вони пояснювали, показує сам
елемент — колір біля назви теми, точність біля шару ризику.
"""
BODY = r"""<body data-t="svitla"><div id="wrap"><div id="map"></div><aside id="side">
<div class="brand"><b>Карта правопорушень</b><span>КИЇВ</span></div>
<div class="sub" id="subt">за даними ЄДРСР · місто Київ</div>
<div class="sub" id="cntl"></div>
<div id="backl"></div>
<!-- Режим. Теплова карта тепер теж режим, а не окрема кнопка збоку: це три
     відповіді на одне питання «що показувати», і стояти вони мають поруч. -->
<div class="seg" id="fcat"></div>
<div class="blk">
 <div class="rhead"><span class="lab">Правопорушення</span><span class="lab">подія · ризик</span></div>
 <div class="rows" id="fa"></div>
 <label class="quiet" id="fquietw"><input type="checkbox" id="fquiet"><span>Тихі вулиці: подій не було, а обстановка та сама</span></label>
</div>
<div class="blk">
 <span class="lab">Контекст</span>
 <div class="rows" id="fctx"></div>
 <div class="fine" id="fgroups"></div>
 <div class="fine" id="fzoom"></div>
</div>
<div class="blk" id="fdw">
 <span class="lab">Район</span>
 <div class="dists" id="fd"></div>
</div>
<div class="foot">
 <div class="docs" id="docs"></div>
 <!-- Постійне застереження про адресу. Британський police.uk свого часу
      обпікся саме на цьому: точки, прив'язані до найближчої адреси, читалися
      як «тут це сталося», і правопорушення біля закладу опинялися записані
      на сусідній житловий будинок. Відтоді там тримають таке саме
      попередження на видноті, а не в довідці. -->
 <div class="fine">Адреса — з рішення суду: місце, де подію <b>оформлено</b>. Воно не завжди збігається з місцем, де все сталося. © OpenStreetMap</div>
</div>
<!-- Сховані фільтри. У панелі їх більше немає, але на них спирається draw():
     рік і час доби повертаються на карту окремим кроком (RISHENNYA, розд. 4),
     фільтр за судом дублював перехід у район, а статті вмикаються рядком
     своєї теми. Тут-таки живуть прапорці шарів ризику, населення, потоків і
     видів об'єктів — їх читають drawRisks() і drawFacts(). -->
<div id="hidden-filters" hidden><div id="fy"></div><div id="hr"></div><div id="fc"></div>
<div id="fasub"></div><div id="ffact"></div></div>
</aside>
<div id="pan"><div id="panh"></div><div id="panb"></div></div></div>"""
