# -*- coding: utf-8 -*-
"""Шари контексту під подіями: потоки, ризик, чинники середовища.

Будує три речі, які лягають на карту незалежно від подій:
  * потоки — модельовані пішохідні маршрути з data/network.json;
  * ризик — клікабельні вулиці з data/risk.json плюс сітка для швидкої
    відповіді «чи стоїть ця адреса на ризикованій вулиці» (pred_theme);
  * чинники середовища — data/factors.json, за потреби будується тут-таки
    з osm_risks_raw.json (крок 2e).

Відбір проблем — у map_problems.
"""
import os, sys, json, math, collections
import labels as L
import mech as M
import uatext
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')

NETW  = os.path.join(DATA, 'network.json')
RISKF = os.path.join(DATA, 'risk.json')
FACTF = os.path.join(DATA, 'factors.json')             # шар чинників середовища (крок 2e)

# Назви ознак моделі -> те, що можна прочитати вголос і перевірити на місці.
# Ознака в моделі зветься 'зупинки_500м'; людині треба «зупинок транспорту
# в 500 м». Ознаки без радіуса (клас дороги, потоки, проникність) описуємо
# окремо: у них немає «скільки штук поруч», у них є величина.
FNAME = {
    'бари': 'барів і клубів', 'алкоголь_винос': 'точок алкоголю на винос',
    'магазини': 'магазинів біля дому', 'кафе': 'кафе й ресторанів',
    'ломбарди': 'ломбардів і обмінників', 'гральні': 'гральних закладів',
    'АЗС': 'АЗС', 'паркінги': 'відкритих паркінгів', 'метро': 'метро й вокзалів',
    'зупинки': 'зупинок транспорту', 'ринки': 'ринків і ТЦ', 'школи': 'шкіл і садків',
    'ВНЗ': 'ВНЗ', 'лікарні': 'лікарень і аптек', 'покинуті': 'покинутих будівель',
    'майданчики': 'дитячих майданчиків', 'камери': 'камер спостереження',
    'житло': 'житлових будинків', 'населення': 'мешканців',
    'дерева': 'дерев', 'парки': 'парків', 'трава': 'газонів', 'лавки': 'лавок',
}
# ознаки-величини: назва + як їх називати, коли значення високе
FSCALE = {
    'прохідність':  ('пішохідна прохідність', 'висока'),
    'потік_школи':  ('потік людей до шкіл і садків', 'великий'),
    'потік_транспорт': ('потік людей до транспорту', 'великий'),
    'потік_торгівля':  ('потік людей до магазинів', 'великий'),
    'клас_дороги':  ('клас дороги', 'високий'),
    'смуг':         ('смуг руху', 'багато'),
    'проникність':  ('проникність вулиць', 'висока'),
    'хрестоподібні': ('хрестоподібних перехресть', 'багато'),
    'T_подібні':    ('T-подібних перехресть', 'багато'),
    'тупик':        ('тупиковість', 'висока'),
    'звивистість':  ('звивистість', 'висока'),
    'перехрестя_всередині': ('перехресть на самому відрізку', 'багато'),
}


def fact_human(name):
    """'зупинки_500м' -> ('зупинок транспорту в 500 м', True).
    Другий елемент — чи це «скільки штук поруч» (можна порівнювати з медіаною)."""
    base, _, r = str(name).rpartition('_')
    if base and r.endswith('м') and r[:-1].isdigit():
        # «в 250 м» доводиться читати як «за 250 метрів», і милозвучне
        # «в/у» тут залежить від попереднього слова. «В радіусі» знімає
        # і те, і те, і заразом каже читачеві, що це коло, а не відстань
        # уздовж вулиці.
        return f"{FNAME.get(base, base.replace('_', ' '))} в радіусі {r[:-1]} м", True
    nm = FSCALE.get(name)
    if nm: return nm[0], False
    return str(name).replace('_', ' '), False


def street_facts(raw, ratios):
    """Чинники ОДНІЄЇ вулиці у вигляді, придатному для читання.

    Кожен рядок: [підпис, значення тут, звичайне для міста, кратність, чи штуки].
    Кратність — у скільки разів більше подій там, де ознаки більше за медіану
    (порахована у кроці 4 діленням, не з моделі). None — якщо рахувати її
    чесно не було на чому."""
    out = []
    for f in (raw or [])[:3]:
        if not isinstance(f, (list, tuple)) or len(f) < 3: continue
        label, is_count = fact_human(f[0])
        out.append([label, f[1], f[2], (f[3] if len(f) > 3 else None), is_count])
    return out


def why_text(facs):
    seen, out = set(), []
    for n, c in facs:
        if c <= 0: continue
        base = n.split('_')[0].split(' ×')[0]
        if base in seen or base in ('смуг', 'клас', 'довжина', 'звивистість'): continue
        seen.add(base); out.append(base)
        if len(out) == 3: break
    return ', '.join(out)

# invariant-genitive описувачі теми для заголовка перекосу (п.7.3). Свідомо не
# відмінюємо за кількістю (1/2-4/5+) — ризик граматичної помилки вищий за


def build(district, labels):
    """Повертає (risks, ER, theme_rgrid, pred_theme, FACT)."""
    # ---- шари контексту: ризик, потоки ----
    risks = {'lines': {}}
    if os.path.exists(NETW):
        nw = json.load(open(NETW, encoding='utf-8'))
        it = nw.get('items', [])
        FLOWS = [('flow_school', 3, 'Потік до шкіл і садків', '07:30–08:30, 12:00–14:00'),
                 ('flow_transit', 4, 'Потік до транспорту', 'години пік'),
                 ('flow_shop', 5, 'Потік до торгівлі', 'день, рівномірно')]
        # Геометрія відрізка записувалася тричі — по разу на шар, — а в кожній
        # районній карті ще й наново. Виміряно 3 вересня: три шари з власною
        # геометрією без обмеження важать 2,87 МБ, а геометрія один раз плюс
        # три масиви значень — 1,28 МБ. Це дешевше за нинішні 1,34 МБ за
        # обрізані топ-2500, тому обмеження знято: показуємо всі відрізки.
        #
        # Стеля була потрібна саме через дублювання. На районній карті вона
        # вже й тоді знімалася (перевірено на вул. Кадетський Гай: потік до
        # торгівлі 202, але 3287-е місце по місту — у топ не потрапляв).
        used = sorted({j for _k, idx, _t, _w in FLOWS
                       for j, x in enumerate(it) if len(x) > idx and x[idx] > 0})
        pos = {j: k for k, j in enumerate(used)}
        if used:
            risks['geo'] = [[it[j][0], it[j][1]] for j in used]
        for key, idx, title, when in FLOWS:
            vals = [(pos[j], int(it[j][idx])) for j in used
                    if len(it[j]) > idx and it[j][idx] > 0]
            if not vals: continue
            vals.sort(key=lambda x: -x[1])
            risks.setdefault('lines', {})[key] = {
                'title': title, 'when': when, 'g': 1,
                'items': [[a, b] for a, b in vals]}
            print(f'   {title}: {len(vals):,} відрізків')
    else:
        print('шар потоків відсутній (запустіть 2c-NETWORK) — карта буде без нього')

    ER = {}
    erp = os.path.join(DATA, 'engine_report.json')
    if os.path.exists(erp):
        ER = json.load(open(erp, encoding='utf-8'))

    # ---- шар ризику: ОДНЕ читання risk.json дає і клікабельні лінії на карті (п.7.5),
    # і сітку для пошуку "чи адреса на ризикованій вулиці" в аналізі картки (п.7.4) ----
    theme_rgrid = {}          # тема -> {(ci,cj): [(la,lo,pc)]}
    RC = 0.0025
    if os.path.exists(RISKF):
        RK = json.load(open(RISKF, encoding='utf-8'))
        for th, v in RK.get('layers', {}).items():
            # На карту йде короткий перелік (`items`), у пам'ять для питання
            # «чи адреса на ризикованій вулиці» — довший хвіст (`grid`).
            # Старі risk.json хвоста не мають, тоді беремо те саме, що й на карту.
            it = sorted(v['items'], key=lambda x: -x[2])
            if not it: continue
            gr = sorted(v.get('grid') or it, key=lambda x: -x[2])
            n = len(it)
            ng = len(gr)
            # `th` тепер — або тема ('ДОР'), або механізм ('ДОР_ДТП').
            # Тема, під якою рядок стоїть у панелі, лежить у самому шарі.
            parent = v.get('theme') or M.simtheme(th)
            gi = [i for i, t in enumerate(L.ORDER) if t == parent]
            grid = collections.defaultdict(list)
            items_out = []
            for i, x in enumerate(it):
                # 4-й елемент — скільки подій було на цій вулиці за період
                # навчання. Двигун його рахував завжди, але сюди він не
                # доходив, і карта не могла відрізнити «вулицю, де вже
                # негаразд» від «поки тихо, але умови ті самі».
                # 5-й елемент — чинники САМЕ ЦІЄЇ вулиці (крок 4). Доти
                # вікно кожної вулиці показувало коефіцієнти шару, однакові
                # для всіх двохсот, і виглядало це як поадресний розбір.
                items_out.append([x[0], x[1] or 'без назви', int(100 * (n - i) / n),
                                  int(x[3]) if len(x) > 3 else 0,
                                  street_facts(x[4] if len(x) > 4 else None,
                                               ER.get(th, {}).get('кратність', {}))])
            for i, x in enumerate(gr):
                pc = int(100 * (ng - i) / ng)
                for pnt in x[0]:
                    grid[(int(pnt[0]/RC), int(pnt[1]/RC))].append((pnt[0], pnt[1], pc))
            theme_rgrid[th] = grid
            d = ER.get(th, {})
            # Двигун сам пише речення про роки: частина механізмів навчена
            # на двох роках, і зашитий тут «2024» був би неправдою.
            method = d.get('метод', '')
            if d and not method:
                method = (f"Модель навчена на {d.get('навчання', 0):,} подіях зі справ, "
                          f"розглянутих 2024 року, і перевірена на "
                          f"{d.get('перевірка', 0):,} подіях зі справ 2025–2026. "
                          f"У верхніх 10% вулиць за прогнозом опиняється "
                          f"{100*d.get('hit_середовище', 0):.0f}% подій наступних років "
                          f"(у {uatext.raziv(d.get('PAI_середовище', 0))} краще за випадковий відбір).")
            risks.setdefault('lines', {})['risk_' + th] = {
                'title': v.get('name') or L.THEMES.get(th, th),
                'slug': v.get('slug') or M.anchor(th),
                'kind': v.get('kind', 'theme'),
                'group': L.THEMES.get(parent, parent),
                'hit': int(100 * v['hit']),
                'theme': gi[0] if gi else 0,
                'why': why_text(ER.get(th, {}).get('фактори', [])),
                'factors': [[n_, round(float(c_), 3)] for n_, c_ in ER.get(th, {}).get('фактори', []) if c_ > 0][:12],
                'method': method,
                'items': items_out,
                # Вулиці, де подій ще не було, а умови ті самі. Показуються
                # окремим прапорцем: пунктир серед суцільних ліній на карті
                # не читався (у головних темах його було 0-2 з 200).
                'quiet': [[q[0], q[1] or 'без назви', 0, 0,
                           street_facts(q[4] if len(q) > 4 else None,
                                        ER.get(th, {}).get('кратність', {}))]
                          for q in (v.get('quiet') or [])]}
        dg = RK.get('danger', [])
        if dg:
            print(f'небезпечні підходи до шкіл: {len(dg)}')

    # Панель «Прогноз ризику» має перелічувати ТІ САМІ теми, що й «Правопорушення».
    # Для тем, де подій замало на навчання (поріг MIN_EV у кроці 4 — 250 подій
    # навчального року), модель не будується. Раніше такі теми просто зникали з
    # панелі, і виглядало це як розсинхрон назв. Тепер показуємо їх окремим рядком.
    for _i, _th in enumerate(L.ORDER):
        if _th == 'ДОМ': continue                       # домашнє насильство на карту не йде
        if ('risk_' + _th) in risks.get('lines', {}): continue
        if not any(k[0] == _th for k in labels): continue
        risks.setdefault('lines', {})['risk_' + _th] = {
            'title': L.THEMES.get(_th, _th), 'slug': M.anchor(_th),
            'kind': 'theme', 'group': L.THEMES.get(_th, _th),
            'hit': 0, 'theme': _i,
            'why': '', 'factors': [], 'method': '', 'items': [], 'nodata': True}

    # ---- ШАР ЧИННИКІВ СЕРЕДОВИЩА (крок 2e) ----
    # Якщо файл ще не побудований, будуємо його тут-таки з osm_risks_raw.json.
    # Так карта збереться навіть без окремого кроку 2e у workflow; у межах одного
    # запуску step5_site викликає main() 22 рази — файл будується лише вперше.
    FACT = {}
    _rawp = os.path.join(DATA, 'osm_risks_raw.json')
    if not os.path.exists(FACTF) and os.path.exists(_rawp):
        try:
            import step2e_factors
            step2e_factors.main()
        except SystemExit:
            pass
        except Exception as _e:
            print('шар чинників не побудовано:', _e)
    if os.path.exists(FACTF):
        FACT = json.load(open(FACTF, encoding='utf-8'))
        print(f"чинники середовища: {sum(len(c['pts']) for c in FACT.get('cats', [])):,} об'єктів")

    def pred_theme(th, la, lo, rad=180.0):
        g = theme_rgrid.get(th)
        if not g: return 0
        my = 111320.0; mx = 111320.0 * math.cos(math.radians(la))
        ci_, cj_ = int(la/RC), int(lo/RC); best = 0
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for pa, po, pc in g.get((ci_+di, cj_+dj), ()):
                    if pc > best and math.hypot((pa-la)*my, (po-lo)*mx) <= rad: best = pc
        return best

    return risks, ER, theme_rgrid, pred_theme, FACT
