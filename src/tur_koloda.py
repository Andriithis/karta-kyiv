# -*- coding: utf-8 -*-
"""Колода зупинок туру (ZAVDANNYA-41, етап 3; Андрій 31.10: «щоразу інший,
цікавий тур»). Будується при збірці карти; браузер щоразу тягне з неї 8–10
зупинок з ритмом (tpl_tur, kolodaTur).

Види зупинок:
  misce  — проблема з переліку аналізу фабул: місце, сценарій, «N з M»;
  chyslo — місто в цифрах: одне велике число й увесь Київ; рахується з тих
           самих точок P, що «Стан міста» й «Трикутник» (одне джерело);
  fabula — коротка знеособлена історія з data/tur_cikavi.json (відбирає нічний
           аналітик; без справ щодо дітей і домашнього насильства);
  shcho  — «що з цим робити»: техніка зі сторінки «Що робити» на нашому місці.

Фото місць — Mapillary (CC BY-SA, з атрибуцією; обличчя й номери Mapillary
розмиває), лише якщо в середовищі є MAPILLARY_TOKEN (GitHub Secret) — у файли
токен не потрапляє; без токена зупинки без фото.
"""
import os, json, collections, urllib.request, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')


def _pl(n, a, b, c):
    return a if n % 10 == 1 and n % 100 != 11 else b if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else c


def _num(n): return f'{int(round(n)):,}'.replace(',', ' ')
def _pct(x): return f'{100 * x:.0f}%'


def mistse_zupynky(an):
    out = []
    for z in an:
        if z.get('stan') != 'діє' or not z.get('stsenarij'): continue
        n, m = z.get('n_stsenariju', 0), z.get('n_usikh', 0)
        out.append(dict(typ='misce', id='m:' + str(z.get('id')), lat=z['lat'], lon=z['lon'], zum=15.6,
                        mitka='Місце, що повторюється', zagolovok=' / '.join((z.get('adresy') or [])[:2]),
                        tekst=z['stsenarij'], chyslo=f'{n} з {m}', pidpys='подій місця — за цим сценарієм',
                        mekh=z.get('mekhanizm')))
    return out


def chysla_zupynky(P, labels, LZ, TSIL_V, dnames):
    """місто в цифрах — лише з даних збірки"""
    import labels as L
    out = []
    th_of = [lb[0] for lb in labels]
    doma = [(i, p) for i, p in enumerate(P) if p[3] and p[4]]
    adr = sorted((len(p[4]) for _i, p in doma), reverse=True)
    n = sum(adr)
    if not n: return out
    k = s = 0
    while k < len(adr) and s < n / 2: s += adr[k]; k += 1
    out.append(dict(typ='chyslo', id='c:pol', mitka='Місто в цифрах', zagolovok='Половина всіх подій Києва',
                    tekst='стається на малій частці адрес — решта міста тиха', chyslo=_pct(k / len(adr)), pidpys='адрес'))
    po_vydu = collections.Counter(th_of[e[1]] for _i, p in doma for e in p[4])
    th, c = po_vydu.most_common(1)[0]
    out.append(dict(typ='chyslo', id='c:vyd', mitka='Місто в цифрах', zagolovok=f'Найчастіше в судах — {L.THEMES.get(th, th).lower()}',
                    tekst='за подіями з точною адресою', chyslo=_pct(c / n), pidpys='усіх подій'))
    dity = sum(1 for i, p in doma for k_, e in enumerate(p[4])
               if i < len(LZ) and k_ < len(LZ[i]) and LZ[i][k_] and (LZ[i][k_][0] or 0) & 32)
    if dity:
        out.append(dict(typ='chyslo', id='c:dity', mitka='Місто в цифрах', zagolovok='Неповнолітні правопорушники',
                        tekst='стільки подій, де суд прямо написав про неповнолітнього', chyslo=_num(dity),
                        pidpys=_pl(dity, 'подія', 'події', 'подій')))
    berut = collections.Counter()
    for i, p in doma:
        for k_, e in enumerate(p[4]):
            l = LZ[i][k_] if i < len(LZ) and k_ < len(LZ[i]) else None
            for x in (l[2] if l else []) or []:
                kk, v = TSIL_V[x].split('=', 1)
                if kk == 'berut': berut[v] += 1
    if berut:
        v, c = berut.most_common(1)[0]
        out.append(dict(typ='chyslo', id='c:berut', mitka='Місто в цифрах', zagolovok=f'Найчастіше крадуть — {v}',
                        tekst='серед крадіжок, де суд назвав, що взяли', chyslo=_num(c), pidpys=_pl(c, 'раз', 'рази', 'разів')))
    god = collections.Counter(e[3] for _i, p in doma for e in p[4] if e[3] is not None and e[3] >= 0)
    if god:
        h, c = god.most_common(1)[0]
        out.append(dict(typ='chyslo', id='c:hod', mitka='Місто в цифрах', zagolovok='Година пік',
                        tekst='година, на яку припадає найбільше подій з відомим часом', chyslo=f'{h:02d}:00', pidpys=''))
    rai = collections.Counter(p[8] for _i, p in doma if len(p) > 8 and p[8] >= 0 for _e in p[4])
    if rai and dnames:
        d, c = rai.most_common(1)[0]
        out.append(dict(typ='chyslo', id='c:rai', mitka='Місто в цифрах', zagolovok=f'Найбільше подій — {dnames[d]} район',
                        tekst='за подіями з точною адресою', chyslo=_pct(c / n), pidpys='подій міста'))
    return out


def shcho_zupynky(mistsia):
    import shcho_robyty as SR
    out = []
    for kod, mekh, h, _s, vysn, tt, _ne in SR.MEKHANIZMY:
        pr = [m for m in mistsia if m.get('mekh') in mekh]
        if not pr or not tt: continue
        z = max(pr, key=lambda m: int(str(m['chyslo']).split()[0]))
        t, syla, _k = tt[0]
        out.append(dict(typ='shcho', id='s:' + kod, lat=z['lat'], lon=z['lon'], zum=15.6, mitka='Що з цим робити',
                        zagolovok=h, tekst=f'{t[0].upper() + t[1:]} — {syla} за дослідженнями. {vysn}',
                        chyslo=None, pidpys='', posylannia='shcho-robyty.html#' + kod))
    return out


def fabuly_zupynky():
    p = os.path.join(DATA, 'tur_cikavi.json')
    if not os.path.exists(p): return []
    try: d = json.load(open(p, encoding='utf-8'))
    except ValueError: return []
    out = []
    for i, x in enumerate(d):
        # без справ щодо дітей і домашнього насильства (ZAVDANNYA-41, 3.1)
        if x.get('dity') or x.get('dn') or not x.get('tekst'): continue
        out.append(dict(typ='fabula', id='f:' + str(x.get('id', i)), lat=x.get('lat'), lon=x.get('lon'), zum=15.6,
                        mitka='Історія з рішення', zagolovok=x.get('zagolovok', ''), tekst=x['tekst'], chyslo=None, pidpys=''))
    return [x for x in out if x['lat'] and x['lon']]


def mapillary(zup, odir, log=print):
    """мініатюри Mapillary для зупинок-місць — лише з токеном у середовищі"""
    tok = os.environ.get('MAPILLARY_TOKEN')
    if not tok: return 0
    fdir = os.path.join(odir, 'dani', 'foto'); os.makedirs(fdir, exist_ok=True)
    n = 0
    for z in zup:
        if z['typ'] not in ('misce', 'shcho', 'fabula') or not z.get('lat'): continue
        d = .0006
        q = urllib.parse.urlencode(dict(access_token=tok, fields='id,thumb_1024_url,creator',
                                        bbox=f'{z["lon"] - d},{z["lat"] - d},{z["lon"] + d},{z["lat"] + d}', limit=1))
        try:
            with urllib.request.urlopen(f'https://graph.mapillary.com/images?{q}', timeout=30) as r:
                xs = json.load(r).get('data') or []
            if not xs: continue
            x = xs[0]; fn = f'{x["id"]}.jpg'; fp = os.path.join(fdir, fn)
            if not os.path.exists(fp):
                with urllib.request.urlopen(x['thumb_1024_url'], timeout=60) as r: open(fp, 'wb').write(r.read())
            z['foto'] = 'dani/foto/' + fn
            z['foto_avtor'] = f'© {((x.get("creator") or {}).get("username") or "Mapillary")} · Mapillary, CC BY-SA'
            n += 1
        except Exception as e:
            log(f'   Mapillary {z["id"]}: {e}')
    return n


def koloda(P, labels, LZ, TSIL_V, dnames, odir, log=print):
    ap = os.path.join(DATA, 'problemy_analityk.json')
    an = json.load(open(ap, encoding='utf-8')) if os.path.exists(ap) else []
    mistsia = mistse_zupynky(an)
    zup = chysla_zupynky(P, labels, LZ, TSIL_V, dnames) + mistsia + shcho_zupynky(mistsia) + fabuly_zupynky()
    nf = mapillary(zup, odir, log)
    for z in zup: z.pop('mekh', None)
    log(f'   колода туру: {len(zup)} зупинок (' + ', '.join(f'{k} {v}' for k, v in collections.Counter(z["typ"] for z in zup).items())
        + f'); фото Mapillary: {nf if os.environ.get("MAPILLARY_TOKEN") else "без токена — немає"}')
    return zup
