# -*- coding: utf-8 -*-
"""Дані карти — окремими файлами з хешем у назві (36.22, S-Н.5).

Раніше все лежало в index.html (6,9 МБ, 1,8 МБ мережею), і кожен відвідувач
тягнув «Прохідність» і «Що поруч», яких здебільшого не вмикає. Тепер:

    dani/meta.<хеш>.json     M — підписи, райони, межі
    dani/pts.<хеш>.json      P — адреси з подіями (події — рядком, див. нижче)
    dani/ryzyk.<хеш>.json    R без «Прохідності»: лінії ризику (polyline), точки
    dani/tree.<хеш>.json     дерево кілець
    dani/prokhid.<хеш>.json  «Прохідність» — коли шар увімкнено
    dani/poruch.<хеш>.json   «Що поруч» — при першому відкритті картки

Хеш у назві: браузер тримає файл у кеші, доки збірка не змінила його вміст, і
не тягне старий після оновлення. Шару «Населення» на карті немає (36.39) —
і файлу теж. Перше завантаження — HTML і перші чотири
(PERSHI); check_build міряє саме їх (test:vaga).
"""
import base64, gzip, hashlib, json, os, re

PERSHI = ('meta', 'pts', 'ryzyk', 'tree')
NA_VYMOHU = ('prokhid', 'poruch', 'linzy')

# ---- ПОДІЇ РЯДКОМ ----
# Подія — шість чисел [суд, стаття, рік, година, ознака, місяць]. Масивом це
# ~17 байт, а подій 100 тис.: 1,7 МБ із 2,9 МБ точок. П'ять полів без суду
# пакуються в 23 біти — чотири знаки base64url. Суд у адреси майже завжди
# один, тож пишеться раз: «K» + суд + події; різні суди — «V» + суд кожної
# події + події. Межі полів перевіряються: число не влізло — збірка падає, а
# не мовчки псує подію (тоді розширити BITY тут і в tpl_base).
ABC = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
BITY = ((1, 7), (2, 2), (3, 5), (4, 2), (5, 7))   # (поле, біт); година +1 (−1 — невідома)


def podiia_v_znaky(e):
    v, zsuv = 0, 0
    for i, b in BITY:
        x = e[i] + (1 if i == 3 else 0)
        if not 0 <= x < (1 << b):
            raise ValueError(f'поле {i} події {e} не влазить у {b} біт — розширте BITY тут і в tpl_base')
        v |= x << zsuv; zsuv += b
    return ''.join(ABC[(v >> (6 * k)) & 63] for k in range(4))


def znaky_v_podiiu(sud, s):
    v = sum(ABC.index(ch) << (6 * k) for k, ch in enumerate(s))
    e, zsuv = [sud, 0, 0, 0, 0, 0], 0
    for i, b in BITY:
        e[i] = ((v >> zsuv) & ((1 << b) - 1)) - (1 if i == 3 else 0); zsuv += b
    return e


def pakuvaty_P(P):
    """{v: вулиці, p: точки}. Точка з подіями лише з шести полів — події
    рядком. Сьоме поле (інші статті справи) рідкісне — така точка лишається
    масивами. Адреса «вулиця, номер» — [номер вулиці в v, номер будинку]:
    3 тис. вулиць на 16 тис. адрес, і назва вулиці не повторюється."""
    vul = {}
    for p in P:
        if ', ' in p[2]: vul.setdefault(p[2].rpartition(', ')[0], len(vul))
    out = []
    for p in P:
        if ', ' in p[2]:
            s, _, h = p[2].rpartition(', ')
            p = p[:2] + [[vul[s], h]] + p[3:]
        ev = p[4]
        if ev and all(len(e) == 6 for e in ev):
            if any(not 0 <= e[0] < 64 for e in ev): raise ValueError(f'суд поза 0..63: {p[2]}')
            sudy = {e[0] for e in ev}
            pre = 'K' + ABC[ev[0][0]] if len(sudy) == 1 else 'V' + ''.join(ABC[e[0]] for e in ev)
            p = p[:4] + [pre + ''.join(podiia_v_znaky(e) for e in ev)] + p[5:]
        out.append(p)
    return {'v': list(vul), 'p': out}


def rozpakuvaty_ev(s):
    if s[0] == 'K':
        sud = ABC.index(s[1])
        return [znaky_v_podiiu(sud, s[k:k + 4]) for k in range(2, len(s), 4)]
    n = (len(s) - 1) // 5
    return [znaky_v_podiiu(ABC.index(s[1 + j]), s[1 + n + 4 * j:5 + n + 4 * j]) for j in range(n)]


def rozpakuvaty_P(d):
    out = []
    for p in d['p']:
        if isinstance(p[2], list): p = p[:2] + [d['v'][p[2][0]] + ', ' + p[2][1]] + p[3:]
        if isinstance(p[4], str): p = p[:4] + [rozpakuvaty_ev(p[4])] + p[5:]
        out.append(p)
    return out


def pakuvaty_tree(T):
    """Центри кілець (c: [довгота, широта, …]) — polyline: −40% дерева."""
    return {**T, 'lv': [{**l, 'c': polyline([l['c'][i:i + 2] for i in range(0, len(l['c']), 2)])}
                        for l in T['lv']]}


# ---- ЛІНІЇ — POLYLINE ----
# Кодування Google, 5 знаків (≈1 м): дельти координат замість повних чисел,
# ~60% менше (36.22.4). Розкодування — polyDek у tpl_base.
def polyline(pts):
    out, pl, pn = [], 0, 0
    for la, lo in pts:
        a, b = round(la * 1e5), round(lo * 1e5)
        for d in (a - pl, b - pn):
            d = ~(d << 1) if d < 0 else d << 1
            while d >= 0x20:
                out.append(chr((0x20 | (d & 0x1f)) + 63)); d >>= 5
            out.append(chr(d + 63))
        pl, pn = a, b
    return ''.join(out)


def polyline_dek(s):
    pts, i, la, lo = [], 0, 0, 0
    while i < len(s):
        r = []
        for _ in range(2):
            v = sh = 0
            while True:
                b = ord(s[i]) - 63; i += 1
                v |= (b & 0x1f) << sh; sh += 5
                if b < 0x20: break
            r.append(~(v >> 1) if v & 1 else v >> 1)
        la += r[0]; lo += r[1]
        pts.append([la / 1e5, lo / 1e5])
    return pts


def rozdilyty_R(R):
    """(ryzyk, prokhid): «Прохідність» (потік і R.geo, на яку посилається лише
    вона) — окремо; у ryzyk від неї лишається заголовок з позначкою lazy, щоб
    перемикач був на місці. Лінії ризику — polyline."""
    ryzyk = {k: v for k, v in R.items() if k not in ('geo', 'lines')}
    ryzyk['lines'], prokhid = {}, {'lines': {}}
    for k, v in (R.get('lines') or {}).items():
        if v.get('g'):
            prokhid['lines'][k] = v['items']
            ryzyk['lines'][k] = {**{a: b for a, b in v.items() if a != 'items'}, 'items': [], 'lazy': 1}
        else:
            ryzyk['lines'][k] = {**v, 'items': [[polyline(it[0])] + list(it[1:]) for it in v.get('items', [])]}
    prokhid['geo'] = [[polyline(g[0])] + list(g[1:]) for g in R.get('geo', [])]
    return ryzyk, prokhid


# ---- ФАЙЛИ ----
def zapysaty(odir, nabir):
    """{назва: об'єкт} -> {назва: 'dani/назва.хеш.json'}; файли, на які нова
    збірка не посилається, прибираються (інакше dani/ росла б щотижня)."""
    ddir = os.path.join(odir, 'dani')
    os.makedirs(ddir, exist_ok=True)
    out = {}
    for k, v in nabir.items():
        b = json.dumps(v, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        h = hashlib.sha256(b).hexdigest()[:10]
        nm = f'{k}.{h}.json'
        fp = os.path.join(ddir, nm)
        if not os.path.exists(fp):
            with open(fp, 'wb') as f: f.write(b)
        out[k] = 'dani/' + nm
    zhyvi = {os.path.basename(v) for v in out.values()}
    for f in os.listdir(ddir):
        if f.endswith('.json') and f not in zhyvi:
            os.remove(os.path.join(ddir, f))
    return out


def perelik(html):
    m = re.search(r'const DANI=(\{.*?\});', html)
    return json.loads(m.group(1)) if m else None


def chytaty(html_path, *nazvy):
    """Дані зібраної карти для перевірок: {назва: об'єкт}; pts — уже
    розпакований (події масивами), як у браузері."""
    odir = os.path.dirname(html_path)
    pr = perelik(open(html_path, encoding='utf-8').read())
    if pr is None: return None
    out = {}
    for k in nazvy or pr:
        v = json.load(open(os.path.join(odir, pr[k]), encoding='utf-8'))
        out[k] = rozpakuvaty_P(v) if k == 'pts' else v
    return out


def vaga(html_path):
    """Перше завантаження: (розпаковано, мережею — gzip, [(файл, байт)]) —
    HTML і файли PERSHI. Мережею — gzip рівня 6, як віддає GitHub Pages."""
    odir = os.path.dirname(html_path)
    html = open(html_path, 'rb').read()
    pr = perelik(html.decode('utf-8')) or {}
    fs = [(os.path.basename(html_path), html)] + [
        (pr[k], open(os.path.join(odir, pr[k]), 'rb').read()) for k in PERSHI if k in pr]
    return (sum(len(b) for _, b in fs), sum(len(gzip.compress(b, 6)) for _, b in fs),
            sorted(((n, len(b)) for n, b in fs), key=lambda x: -x[1]))
