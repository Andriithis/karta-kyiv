# -*- coding: utf-8 -*-
"""Будь-яка адреса Києва клікабельна (S-А.15, RISHENNYA 36.18.4).

Адреси без подій (OSM ∪ КМДА) — окремими файлами site/adresy/<клітинка>.json
клітинками ~2 км: карта тягне їх лише з z15 і лише видимі, тож перше
завантаження не росте (36.22). Клік по такій адресі — картка «0 подій» з
вкладкою «Скарги», якщо мешканці скаржились на той самий будинок (той самий
ключ «вулиця + будинок», що й у map_skargy).

Формат клітинки: [[шир×1e5, довг×1e5, підпис, [номери скарг у skargy.json]], …].
Підпис — назва вулиці як в OSM (pidpys), для адрес лише з КМДА — назва OSM тієї
самої вулиці: підпис КМДА пише прізвище наперед («бульвар Шевченка Тараса»).
"""
import os, json, glob, shutil, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
KLITYNKA = (0.018, 0.028)      # градуси ≈ 2 × 2 км на широті Києва


# адреси без подій останньої збірки: (ключ, шир, довг, підпис) — бере map_poshuk
PORO = []


def kl(la, lo):
    """ключ клітинки — однаковий у Python і JS (tpl_vyhlyady, adresyKl)"""
    return f'{int(la // KLITYNKA[0])}_{int(lo // KLITYNKA[1])}'


def zibraty(P, dst_dir, log=print):
    import step2_geocode as G
    import map_skargy as MS
    from step2_geocode import skey, nh
    osm = os.path.join(DATA, 'osm_kyiv_city.json')
    if not os.path.exists(osm):
        log('   перелік адрес: немає знімка OSM — порожні адреси не клікабельні'); return None
    rows = json.load(open(osm, encoding='utf-8'))
    nazva, streets, adr = {}, collections.defaultdict(list), {}
    for st, h, la, lo in rows:
        k = (skey(st), nh(h))
        if not k[0] or not k[1]: continue
        nazva.setdefault(k[0], G.pidpys(st))
        streets[k[0]].append((la, lo))
        adr.setdefault(k, (la, lo, f'{G.pidpys(st)}, {h}'))
    n_osm = len(adr)
    if G.KMDA_ON:
        for k, c in G.kmda_index(streets).items():
            # однойменна адреса в кількох місцях — неоднозначна, без точки (як у геокодері)
            if k in adr or G.spread_km([(a, b) for a, b, _t, _s in c]) > G.R_ODNA: continue
            adr[k] = (c[0][0], c[0][1], f'{nazva.get(k[0]) or G.pidpys(c[0][3])}, {k[1]}')
    # адреси з подіями вже є на карті — їх картка своя
    na_karti = set()
    for p in P:
        if p and p[3] and p[2] and ', ' in p[2]:
            v, b = p[2].rsplit(', ', 1); na_karti.add((skey(v), nh(b)))
    sk = getattr(MS, 'PO_KL', None) or {}
    kl_sk = lambda lab: MS.kliuch(*lab.rsplit(', ', 1)) if ', ' in lab else None
    out = collections.defaultdict(list); n_sk = 0
    PORO.clear()
    for k, (la, lo, lab) in adr.items():
        if k in na_karti: continue
        PORO.append((k, la, lo, lab))
        js = sk.get(kl_sk(lab)) or []
        n_sk += bool(js)
        out[kl(la, lo)].append([round(la * 1e5), round(lo * 1e5), lab, js])
    d = os.path.join(dst_dir, 'adresy')
    shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    for key, xs in out.items():
        json.dump(xs, open(os.path.join(d, key + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    tot = sum(len(x) for x in out.values())
    mb = sum(os.path.getsize(f) for f in glob.glob(os.path.join(d, '*.json'))) / 1048576
    log(f'   адреси без подій (36.18.4): {tot:,} (OSM {n_osm:,}, разом з КМДА {len(adr):,}; на карті з подіями '
        f'{len(na_karti):,}), зі скаргами {n_sk:,}; {len(out)} клітинок, {mb:.1f} МБ -> adresy/')
    return tot
