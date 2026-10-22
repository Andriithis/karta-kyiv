# -*- coding: utf-8 -*-
"""Індекс пошуку адрес (S-Ш.1–5, RISHENNYA 36.18.5, 36.18.7, 36.35).

Ключі вулиць рахує той самий модуль adr_kliuch, що й геокодер (36.30.6): JS
лише порівнює слова запиту зі словами індексу, а назви не нормалізує
по-своєму — інакше карта й пошук розходились би. Регулярний вираз типів
вулиць іде в індекс з adr_kliuch, щоб і запит чистився тим самим правилом.

site/poshuk.json (окремим файлом, тягнеться при першому введенні в пошук —
перше завантаження карти не росте):
  tw — TYPEWORDS з adr_kliuch;
  s  — вулиці: [підпис як в OSM, слова назви (norm), [старі назви з 1551], подій,
       тип (stype)]; тип запиту — лише підказка порядку, не фільтр;
  ps — для кожної точки карти P — номер вулиці або -1;
  a  — адреси без подій: {номер вулиці: [[номер будинку, шир×1e5, довг×1e5], …]}.
Вулиця — пара (ключ, тип): Голосіївський проспект і провулок — різні.
"""
import os, json, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')


def zibraty(P, dst_dir, log=print):
    import adr_kliuch as AK, step2_geocode as G, map_adresy as MA
    osm = os.path.join(DATA, 'osm_kyiv_city.json')
    if not os.path.exists(osm):
        log('   пошук: немає знімка OSM — індексу немає'); return None
    K = AK.Kliuch()
    sid, s = {}, []
    po_kl = collections.defaultdict(list)            # ключ -> номери вулиць різних типів

    def vulytsia(k, typ, pidpys):
        if (k, typ) not in sid:
            sid[(k, typ)] = len(s); po_kl[k].append(len(s))
            s.append([pidpys, AK.norm(pidpys), [], 0, typ])
        return sid[(k, typ)]
    for st, _h, _la, _lo in json.load(open(osm, encoding='utf-8')):
        k = AK.skey(st)
        if k: vulytsia(k, G.stype(st), G.pidpys(st))
    # вулиці лише з КМДА («Добринінська») — теж шукаються; підпис КМДА, бо
    # назви OSM для них немає
    if G.KMDA_ON:
        for st, _h, _la, _lo in G.fetch_kmda():
            k = AK.skey(st)
            if k and k not in po_kl: vulytsia(k, G.stype(st), G.pidpys(st))
    # перейменування з 1551: стара назва веде на нову вулицю
    for old, new in K.rename.items():
        for i in po_kl.get(new, []):
            if old not in s[i][2]: s[i][2].append(old)

    def znaity(vul):
        k = K.vulytsia(vul); typ = G.stype(vul)
        c = po_kl.get(k, [])
        return sid.get((k, typ), c[0] if len(c) == 1 or c and typ in G.TYPE_LOOSE else -1) if c else -1
    ps = []
    for p in P:
        i = -1
        if p and p[2]:
            vul = p[2].rsplit(', ', 1)[0] if p[3] and ', ' in p[2] else p[2].replace(' · вся вулиця', '')
            i = znaity(vul)
            if i >= 0: s[i][3] += len(p[4])
        ps.append(i)
    a = collections.defaultdict(list)
    for _k, la, lo, lab in getattr(MA, 'PORO', []):
        vul, bud = lab.rsplit(', ', 1)
        i = znaity(vul)
        if i >= 0: a[i].append([bud, round(la * 1e5), round(lo * 1e5)])
    out = dict(tw=AK.TYPEWORDS, s=s, ps=ps, a=a)
    fp = os.path.join(dst_dir, 'poshuk.json')
    json.dump(out, open(fp, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    log(f'   пошук: вулиць {len(s):,} (з перейменуваннями {sum(1 for x in s if x[2]):,}), точок карти на вулицях '
        f'{sum(1 for x in ps if x >= 0):,} з {len(ps):,}, адрес без подій {sum(len(v) for v in a.values()):,} '
        f'-> poshuk.json ({os.path.getsize(fp) / 1048576:.1f} МБ)')
    return len(s)
