# -*- coding: utf-8 -*-
"""Діагностика: перша перевірка факторів ризику на київських даних.

Додаток В до PIDKHID.md. Не частина конвеєра карти — окремий замір.

Що робить:
  1. Бере події з data/events.csv.gz, клас адреси — з data/teksty/*.csv.gz
     (B = адресу підтверджено в описі події; C/D/без тексту — ні).
  2. Геокодує точним збігом «вулиця + будинок» з data/geokoder_kmda.csv.gz.
  3. Для кожного будинку з адресного реєстру КМДА: чи є в радіусі 150 м
     об'єкт кожного фактора (data/factors.json, data/ustanovy.json).
  4. Пуассонівська регресія «кількість подій на будинок ~ усі фактори разом
     + щільність забудови», стійкі похибки. exp(коеф.) = скоригований
     відносний ризик (RR). * — 95% інтервал не перетинає 1.

Обмеження: одиниця — будинок, не відрізок вулиці; фактори лише з OSM;
геокодовано ≈45% подій класу B (перейменовані вулиці не збігаються).
Для відбору факторів у RTM цього досить, для самої моделі — ні.

Запуск: python src/diag_faktory.py   (≈1 хв; потрібні statsmodels і scikit-learn)
"""
import os, sys, glob, json, warnings
import numpy as np, pandas as pd
import statsmodels.api as sm
from sklearn.neighbors import BallTree
warnings.filterwarnings('ignore')
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE); DATA = os.path.join(ROOT, 'data')
import mech as M
from step2_geocode import norm, nh

R = 6371000.0; RAD = 150; YEARS = ('2023', '2024', '2025', '2026')

def load():
    T = pd.concat(pd.read_csv(f, sep='\t', dtype=str,
                              usecols=['doc_id', 'klass', 'street', 'house'])
                  for f in sorted(glob.glob(os.path.join(DATA, 'teksty', '*.csv.gz'))))
    T = T.drop_duplicates('doc_id', keep='last').rename(columns={'street': 'ts', 'house': 'th'})
    E = pd.read_csv(os.path.join(DATA, 'events.csv.gz'), sep='\t', dtype=str)
    E['mech'] = E.cat.map(M.simgroup); E['theme'] = E.mech.fillna('').str.split('_').str[0]
    X = E.merge(T, on='doc_id', how='left')
    G = pd.read_csv(os.path.join(DATA, 'geokoder_kmda.csv.gz'), sep='\t', dtype=str)
    G['k'] = G.street.map(norm) + '|' + G.house.map(nh)
    G = G.drop_duplicates('k').dropna(subset=['lat']).reset_index(drop=True)
    G[['lat', 'lon']] = G[['lat', 'lon']].astype(float)
    X['k'] = X.ts.fillna(X.street).fillna('').map(norm) + '|' + X.th.fillna(X.house).fillna('').map(nh)
    X = X[X.k.isin(set(G.k)) & X.date.str[:4].isin(YEARS)]
    return X, G

def factors():
    F = json.load(open(os.path.join(DATA, 'factors.json'), encoding='utf-8'))
    fac = {c['n']: np.array(c['pts']) for c in F['cats'] if len(c['pts']) >= 50}
    fac['Поліція, суди, прокуратура'] = np.array(
        [[a, b] for a, b, _ in json.load(open(os.path.join(DATA, 'ustanovy.json'), encoding='utf-8'))])
    return fac

def near(pts, P, r):
    t = BallTree(np.radians(P), metric='haversine')
    return t.query_radius(np.radians(pts), r / R, count_only=True) > 0

LAYERS = {
    'Хуліганство':            lambda X, B: B & (X.mech == 'ГП_хуліг'),
    'Розпивання (П)':         lambda X, B: B & (X.mech == 'ГП_пиятика'),
    'Торгівля (П)':           lambda X, B: B & (X.theme == 'АЛК'),
    'Наркотики (П)':          lambda X, B: B & (X.theme == 'НАР'),
    'Насильство':             lambda X, B: B & (X.theme == 'НАС'),
    'Крадіжка':               lambda X, B: B & (X.mech == 'МАЙ_крадіжка'),
    'Грабіж, розбій':         lambda X, B: B & (X.mech == 'МАЙ_силове'),
    'ДТП з потерпілими':      lambda X, B: B & (X.mech == 'ДОР_ДТП_потерпілі'),
    'ДТП майнові':            lambda X, B: B & (X.mech == 'ДОР_ДТП'),
    "Сп'яніння за кермом (П)": lambda X, B: B & (X.mech == "ДОР_сп'яніння"),
    'Залишення місця ДТП':    lambda X, B: B & (X.mech == 'ДОР_залишення_місця'),
    'КОНТРОЛЬ: майно, адреса не перевірена':     lambda X, B: ~B & (X.theme == 'МАЙ'),
    'КОНТРОЛЬ: наркотики, адреса не перевірена': lambda X, B: ~B & (X.theme == 'НАР'),
}

def main():
    X, G = load(); fac = factors(); P = G[['lat', 'lon']].values
    D = pd.DataFrame({f: near(P, pts, RAD).astype(float) for f, pts in fac.items()})
    t = BallTree(np.radians(P), metric='haversine')
    D['щільність забудови (лог)'] = np.log1p(t.query_radius(np.radians(P), 250 / R, count_only=True))
    Z = sm.add_constant(D); B = X.klass == 'B'; out = {}
    for name, sel in LAYERS.items():
        m = sel(X, B); y = G.k.map(X[m].groupby('k').size()).fillna(0).values
        if y.sum() < 100:
            out[f'{name} (n={int(y.sum())})'] = ['мало'] * D.shape[1]; continue
        fit = sm.GLM(y, Z, family=sm.families.Poisson()).fit(cov_type='HC0')
        ci = fit.conf_int()
        out[f'{name} (n={int(y.sum())})'] = [
            f'{np.exp(fit.params[c]):.1f}' + ('' if ci[0][c] <= 0 <= ci[1][c] else '*') for c in D.columns]
    res = pd.DataFrame(out, index=D.columns).T
    pd.set_option('display.width', 400); print(res.to_string())
    print('\nЧастка будинків у радіусі', RAD, 'м від фактора:')
    for f in fac: print(f'   {f:30} {len(fac[f]):5}  {D[f].mean():.2f}')

if __name__ == '__main__':
    main()
