# -*- coding: utf-8 -*-
"""Збір звернень 1551 — «голос мешканців» (RISHENNYA, розд. 31; PIDKHID.md, розд. 5.1).

Запускається workflow'ом «Аналіз 1551» на GitHub (домен data.1551.gov.ua
закритий з машин чатів). Результат — гілка analiz-1551, у main не йде.

Що зберігає на кожен місяць (data/1551/):
  vidbir-РРРР-ММ.tsv.gz    — лише звернення потрібних категорій (КАТ нижче):
                             id, дата, вид карти, kind, content, вулиця, будинок,
                             спосіб подання, результат. Персональних даних
                             у наборі немає (імен, телефонів, тексту скарги).
  lichylnyky-РРРР-ММ.tsv.gz — усі звернення, порахунок на (вулиця, будинок, kind):
                             знаменник «схильності скаржитися» адреси й району
                             (переважно комунальні скарги).
  zvit.json                — обсяги, частка з адресою, по місяцях і видах.

Завантажує місяці з 2025-08 до поточного. Уже збережені місяці не качає
повторно, крім двох останніх (статуси й пізні звернення ще змінюються).

Запуск: python src/zbir_1551.py           (або з переліком РРРР-ММ)
"""
import os, sys, json, gzip, csv, time, datetime, collections, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', '1551')
API = 'https://data.1551.gov.ua/api/data/{y}/{m}'
UA = {'User-Agent': 'karta-kyiv-academy/1.0 (navchalnyi proekt)'}
START = (2025, 8)

# Категорії 1551 (поле content) → вид карти. Відібрано 28.09 на трьох місяцях
# (2025-09, 2026-03, 2026-08; 243 579 звернень). Про наркотики (22 за 3 міс.),
# насильство (2) і крадіжки (категорії немає) 1551 мовчить — їх тут немає.
KAT = {
    # Громадський порядок
    'Незручності від промислових та побутових шумів': '1_PUBLIC_ORDER',
    'Порушення правил тиші (після 22:00)': '1_PUBLIC_ORDER',
    'Порушення громадського порядку безпритульними людьми': '1_PUBLIC_ORDER',
    'Виявлення; запобігання та розслідування протиправних дій': '1_PUBLIC_ORDER',
    'Розпивання пива; алкогольних; слабоалкогольних напоїв у заборонених законом місцях': '1_PUBLIC_ORDER',
    'Куріння тютюнових виробів у заборонених місцях': '1_PUBLIC_ORDER',
    'Розпалювання вогнищ та проведення гулянь в парку та лісопарковій зоні': '1_PUBLIC_ORDER',
    'Незручності для проживання мешканців від роботи закладів торгівлі та ресторанного господарства': '1_PUBLIC_ORDER',
    # Торгівля (у т.ч. алкоголь)
    'Несанкціонована торгівля': '2_ALCOHOL_TRADE',
    'Продаж спиртних/слабоалкогольних напоїв та тютюнових виробів особам молодше 18р.': '2_ALCOHOL_TRADE',
    # Безпека руху
    'Встановлення та експлуатація пристроїв примусового зниження швидкості': '6_TRAFFIC',
    'Встановлення та робота світлофора': '6_TRAFFIC',
    'Нанесення дорожньої розмітки': '6_TRAFFIC',
    'Встановлення штучних обмежувачів руху для проїзду авто': '6_TRAFFIC',
    'Зберігання транспортних засобів; порушення правил паркування': '6_TRAFFIC',
    # Середовище для ризику (не вид правопорушення)
    'Відсутність освітлення на опорних стовпах': 'KONTEKST_SVITLO',
    'Незадовільний стан опори для освітлення': 'KONTEKST_SVITLO',
    'Відсутність опори освітлення (не передбачено проєктом забудови)': 'KONTEKST_SVITLO',
    # Пішохідна інфраструктура (ризик для пішоходів: тротуари, паркування на узбіччі)
    'Технічний стан проїжджих частин вулиць та тротуарів': 'KONTEKST_PISHOHID',
    'Встановлення сигнальних стовпчиків; бар’єрних огороджень; бордюрів': 'KONTEKST_PISHOHID',
    'Встановлення сигнальних стовпчиків; бар`єрних огороджень;бордюрів': 'KONTEKST_PISHOHID',
    'Облаштування підземного/надземного пішохідного переходу': 'KONTEKST_PISHOHID',
    # Наркотики — лічимо окремо, щоб бачити, чи з'явиться сигнал
    'Продаж та вживання наркотичних речовин у громадських місцях': '3_DRUGS',
    # Групи за змістом для ризику (ZAVDANNYA-32, 5.2): переходи, стан доріг
    'Облаштування наземного пішохідного переходу': '6_TRAFFIC',
    "Технічний стан об'єктів дорожньо-транспортної інфраструктури": 'KONTEKST_PISHOHID',
    'Графік роботи освітлення вуличних ліхтарів': 'KONTEKST_SVITLO',
}
# Розділи (kind), які відбираються цілком: МАФи — торгівля на вулиці
KAT_KIND = {'Функціонування МАФ': '2_ALCOHOL_TRADE',
            'Утримання МАФ та прилеглої до нього території': '2_ALCOHOL_TRADE'}

# ---- ГРУПИ ЗА ЗМІСТОМ (RISHENNYA 35.3; ZAVDANNYA-32, 5.2) ----
# Не за розділом: «Опалення, Ліфт → наркотики» в дослідженні 29.09 було
# густотою житла, а не закономірністю. Група — те, про що скаржаться на
# вулиці; «Взаємовідносини з сусідами» не беремо: це житло, не публічний
# простір. Одне місце для карти, моделі й дослідження.
GRUPY_1551 = {
    'шум_заклади': ['Незручності для проживання мешканців від роботи закладів торгівлі та ресторанного господарства',
                    'Незручності від промислових та побутових шумів', 'Порушення правил тиші (після 22:00)'],
    'безпритульні': ['Порушення громадського порядку безпритульними людьми'],
    'порядок_інше': ['Виявлення; запобігання та розслідування протиправних дій',
                     'Куріння тютюнових виробів у заборонених місцях',
                     'Розпивання пива; алкогольних; слабоалкогольних напоїв у заборонених законом місцях'],
    'торгівля_МАФ': ['Несанкціонована торгівля', 'kind:Функціонування МАФ',
                     'kind:Утримання МАФ та прилеглої до нього території'],
    'освітлення': ['Відсутність освітлення на опорних стовпах', 'Незадовільний стан опори для освітлення',
                   'Відсутність опори освітлення (не передбачено проєктом забудови)',
                   'Графік роботи освітлення вуличних ліхтарів'],
    'тротуари_дорога': ['Технічний стан проїжджих частин вулиць та тротуарів',
                        "Технічний стан об'єктів дорожньо-транспортної інфраструктури"],
    'паркування': ['Зберігання транспортних засобів; порушення правил паркування'],
    'переходи_світлофори': ['Облаштування наземного пішохідного переходу',
                            'Облаштування підземного/надземного пішохідного переходу',
                            'Встановлення та робота світлофора', 'Нанесення дорожньої розмітки'],
    'обмежувачі': ['Встановлення штучних обмежувачів руху для проїзду авто',
                   'Встановлення та експлуатація пристроїв примусового зниження швидкості'],
}
# «Проти демонтажу МАФ» — скарга на демонтаж, а не на торгівлю
NE_HRUPA = {'Проти демонтажу МАФ'}


def _n(s):
    return ' '.join((s or '').replace('`', "'").replace('’', "'").split()).lower()


_ZMIST = {_n(c): g for g, cs in GRUPY_1551.items() for c in cs if not c.startswith('kind:')}
_ROZDIL = {_n(c[5:]): g for g, cs in GRUPY_1551.items() for c in cs if c.startswith('kind:')}
_KAT = {_n(k): v for k, v in KAT.items()}


def grupa(kind, content):
    """група за змістом або '' (не в жодній)"""
    if _n(content) in {_n(x) for x in NE_HRUPA}: return ''
    return _ZMIST.get(_n(content)) or _ROZDIL.get(_n(kind)) or ''


def vyd_of(kind, content):
    return _KAT.get(_n(content)) or KAT_KIND.get(' '.join((kind or '').split()))


# Версія відбору: інша — усі місяці перекачуються (стовпець grupa, нові змісти)
VERSIIA = 2
POLYA = ['id', 'data', 'vyd', 'kind', 'content', 'vulytsya', 'budynok', 'sposib', 'rezultat', 'grupa']


def clean(v):
    v = (v or '').strip() if isinstance(v, str) else ('' if v is None else str(v))
    return '' if v.lower() == 'null' else v


def get(url, tries=4, timeout=300):
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read()
        except Exception as e:
            last = e
            print(f'   {url}: {type(e).__name__} {e} — спроба {i + 1}', flush=True)
            time.sleep(20 * (i + 1))
    raise RuntimeError(f'{url}: {last}')


def records(js):
    if isinstance(js, list):
        return js
    best = []
    if isinstance(js, dict):
        for v in js.values():
            r = records(v)
            if len(r) > len(best):
                best = r
    return best


def months_default():
    now = datetime.datetime.utcnow()
    y, m, out = START[0], START[1], []
    while (y, m) <= (now.year, now.month):
        out.append(f'{y}-{m:02d}')
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def one(ym, zvit):
    y, m = ym.split('-')
    rows = records(json.loads(get(API.format(y=y, m=m))))
    lich = collections.Counter()
    vyd = collections.Counter()
    z_adr = 0
    with gzip.open(os.path.join(OUT, f'vidbir-{ym}.tsv.gz'), 'wt', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh, delimiter='\t'); w.writerow(POLYA)
        for r in rows:
            st, bd, kind = clean(r.get('addressThoroughfare')), clean(r.get('addressLocatorDesignator')), clean(r.get('kind'))
            lich[(st, bd, kind)] += 1
            v = vyd_of(kind, clean(r.get('content')))
            if not v:
                continue
            vyd[v] += 1
            z_adr += bool(st and bd)
            w.writerow([r.get('Id', ''), clean(r.get('receivedDateTime'))[:16], v, kind, clean(r.get('content')),
                        st, bd, clean(r.get('accrualMethod')), clean(r.get('result')),
                        grupa(kind, clean(r.get('content')))])
    with gzip.open(os.path.join(OUT, f'lichylnyky-{ym}.tsv.gz'), 'wt', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh, delimiter='\t'); w.writerow(['vulytsya', 'budynok', 'kind', 'n'])
        for (st, bd, kind), n in sorted(lich.items()):
            w.writerow([st, bd, kind, n])
    zvit['місяці'][ym] = {'усіх': len(rows),
                          'з_адресою': round(sum(n for (s, b, _), n in lich.items() if s and b) / max(len(rows), 1), 3),
                          'відібрано': sum(vyd.values()), 'відібрано_з_адресою': round(z_adr / max(sum(vyd.values()), 1), 3),
                          'за_видами': dict(vyd)}
    print(f'{ym}: {len(rows):,} звернень, відібрано {sum(vyd.values()):,}', flush=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    months = sys.argv[1:] or months_default()
    zp = os.path.join(OUT, 'zvit.json')
    zvit = json.load(open(zp, encoding='utf-8')) if os.path.exists(zp) else {'місяці': {}}
    zvit['помилки'] = {}
    svizhi = set(months_default()[-2:])
    nova = zvit.get('versiia') != VERSIIA
    if nova: print(f'відбір змінився (версія {VERSIIA}) — перекачую всі місяці')
    for ym in months:
        if (not nova and ym not in svizhi and os.path.exists(os.path.join(OUT, f'vidbir-{ym}.tsv.gz'))
                and ym in zvit['місяці']):
            continue
        try:
            one(ym, zvit)
        except Exception as e:
            zvit['помилки'][ym] = str(e)
            print(f'{ym}: ПОМИЛКА {e}', flush=True)
    zvit['оновлено'] = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M')
    zvit['категорії'] = KAT
    zvit['versiia'] = VERSIIA
    zvit['групи'] = GRUPY_1551
    json.dump(zvit, open(zp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('готово: data/1551/zvit.json')


if __name__ == '__main__':
    main()
