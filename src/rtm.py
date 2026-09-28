# -*- coding: utf-8 -*-
"""Відбір чинників і радіусів так, як це робить Risk Terrain Modeling.

Caplan, Kennedy & Neudecker (2020); утиліта RTMDx — Caplan, Kennedy & Piza
(2013). План — PLAN-KROK7.md, розд. 3; методика — NAUKA.md, розд. 3.

1. elastic net Пуассон з перехресною перевіркою відсіює змінні, чиї
   коефіцієнти стискаються до нуля;
2. двонапрямна покрокова регресія (Пуассон і негативна біноміальна) на тих,
   що лишилися; на кожному кроці BIC, зупинка, коли він більше не кращає;
3. одне r на тип: якщо лишилися два радіуси (чи дві форми) одного типу,
   лишаємо той, без якого BIC гірший;
4. вага — відносний ризик exp(коеф.).

Своя реалізація elastic net, бо в scikit-learn Пуассон буває лише з L2, а
тягти в Actions ще одну бібліотеку заради одного методу не варто.
"""
import math, warnings
import numpy as np

# Покроковий відбір перебирає тисячі моделей; частина з них (майже порожні
# змінні) дає попередження про збіжність — такі моделі й так програють за BIC,
# а тисячі рядків попереджень ховають у журналі те, що важливо.
warnings.filterwarnings('ignore', module='statsmodels')

L1_RATIO = 0.5          # «справжній» elastic net: половина L1, половина L2
N_LAMBDA = 24
N_FOLDS = 5


def _fit_enet(X, y, off, lam, l1, b=None, b0=None, iters=400, tol=1e-6):
    """Пуассон з offset і штрафом lam*(l1*|b| + (1-l1)/2*b²) — FISTA з
    пошуком кроку. X уже стандартизований; вільний член не штрафується."""
    n, p = X.shape
    b = np.zeros(p) if b is None else b.copy()
    b0 = math.log(max(y.sum(), 1e-9) / np.exp(off).sum()) if b0 is None else b0

    def loss(bb, bb0):
        eta = np.clip(X @ bb + bb0 + off, -30, 30)
        return (np.exp(eta) - y * eta).mean() + lam * (1 - l1) / 2 * (bb @ bb)

    zb, zb0, t, step = b.copy(), b0, 1.0, 1.0
    f_old = None
    for _ in range(iters):
        eta = np.clip(X @ zb + zb0 + off, -30, 30)
        mu = np.exp(eta)
        g = X.T @ (mu - y) / n + lam * (1 - l1) * zb
        g0 = (mu - y).mean()
        fz = (mu - y * eta).mean() + lam * (1 - l1) / 2 * (zb @ zb)
        while True:
            nb = zb - step * g
            nb = np.sign(nb) * np.maximum(np.abs(nb) - step * lam * l1, 0)
            nb0 = zb0 - step * g0
            d, d0 = nb - zb, nb0 - zb0
            if loss(nb, nb0) <= fz + g @ d + g0 * d0 + (d @ d + d0 * d0) / (2 * step) + 1e-12:
                break
            step *= 0.5
            if step < 1e-10: break
        t2 = (1 + math.sqrt(1 + 4 * t * t)) / 2
        zb = nb + (t - 1) / t2 * (nb - b)
        zb0 = nb0 + (t - 1) / t2 * (nb0 - b0)
        b, b0, t = nb, nb0, t2
        f = loss(b, b0) + lam * l1 * np.abs(b).sum()
        if f_old is not None and abs(f_old - f) < tol * max(1.0, abs(f)):
            break
        f_old = f
        step = min(step * 2, 1.0)
    return b, b0


def _dev(y, mu):
    """пуассонівська девіація — міра, якою порівнюємо λ на відкладених частинах"""
    with np.errstate(divide='ignore', invalid='ignore'):
        t = np.where(y > 0, y * np.log(y / mu), 0.0)
    return 2 * float((t - (y - mu)).sum())


def enet_cv(X, y, expo, seed=7, log=print):
    """Elastic net з 5-кратною перехресною перевіркою лише на даних навчання.
    Повертає індекси змінних з ненульовим коефіцієнтом при найкращому λ."""
    mean, sd = X.mean(0), X.std(0)
    sd[sd == 0] = 1
    Z = (X - mean) / sd
    off = np.log(expo)
    n = len(y)
    g = (Z.T @ (y - y.sum() / expo.sum() * expo)) / n
    lmax = float(np.abs(g).max() / L1_RATIO) or 1e-3
    lams = lmax * np.logspace(0, -3, N_LAMBDA)
    fold = np.random.default_rng(seed).integers(0, N_FOLDS, n)
    cv = np.zeros(N_LAMBDA)
    for k in range(N_FOLDS):
        tr, te = fold != k, fold == k
        b = b0 = None
        for i, lam in enumerate(lams):
            b, b0 = _fit_enet(Z[tr], y[tr], off[tr], lam, L1_RATIO, b, b0)
            mu = np.exp(np.clip(Z[te] @ b + b0 + off[te], -30, 30))
            cv[i] += _dev(y[te], mu)
    best = int(np.argmin(cv))
    b = b0 = None
    for lam in lams[:best + 1]:            # теплий старт по шляху, як у glmnet
        b, b0 = _fit_enet(Z, y, off, lam, L1_RATIO, b, b0)
    keep = [j for j in range(X.shape[1]) if abs(b[j]) > 1e-8]
    log(f'      elastic net: λ {lams[best]:.2e} ({best + 1}/{N_LAMBDA}), лишилось {len(keep)} з {X.shape[1]}')
    return keep


def _glm(X, y, expo, cols, fam, alpha=None):
    import statsmodels.api as sm
    A = np.column_stack([np.ones(len(y))] + [X[:, j] for j in cols])
    f = sm.families.Poisson() if fam == 'P' else sm.families.NegativeBinomial(alpha=alpha)
    try:
        r = sm.GLM(y, A, family=f, offset=np.log(expo)).fit(maxiter=100)
    except Exception:
        return None
    if not np.all(np.isfinite(r.params)): return None
    return r


def bic(r, n, fam):
    # у NB параметр розсіяння теж оцінено, тож він штрафується як ще одна змінна
    k = len(r.params) + (1 if fam == 'NB' else 0)
    return -2 * r.llf + k * math.log(n)


def stepwise(X, y, expo, cand, fam, alpha=None, log=print):
    """Двонапрямна покрокова регресія за BIC, стартує з порожньої моделі.
    На кожному кроці пробуємо і додати кожну з кандидатів, і прибрати кожну з
    моделі; беремо найкращий хід, доки BIC кращає."""
    n = len(y)
    cur = []
    r = _glm(X, y, expo, cur, fam, alpha)
    best = bic(r, n, fam)
    while True:
        moves = [('+', j) for j in cand if j not in cur] + [('-', j) for j in cur]
        top = None
        for sgn, j in moves:
            cols = cur + [j] if sgn == '+' else [c for c in cur if c != j]
            rr = _glm(X, y, expo, cols, fam, alpha)
            if rr is None: continue
            b = bic(rr, n, fam)
            if top is None or b < top[0]: top = (b, cols)
        if top is None or top[0] >= best - 1e-6: break
        best, cur = top
    return cur, best


def one_r_per_type(X, y, expo, cols, typ, fam, alpha=None):
    """Якщо в модель потрапили кілька радіусів чи форм одного типу, лишаємо
    ту, прибравши яку BIC погіршується найбільше (PLAN-KROK7, розд. 3)."""
    n = len(y)
    cols = list(cols)
    while True:
        by = {}
        for j in cols:
            if typ[j]: by.setdefault(typ[j], []).append(j)
        dup = next((v for v in by.values() if len(v) > 1), None)
        if not dup: return cols
        # BIC без кожної: чим він гірший без змінної, тим вона потрібніша
        worse = []
        for j in dup:
            rr = _glm(X, y, expo, [c for c in cols if c != j], fam, alpha)
            worse.append((bic(rr, n, fam) if rr is not None else float('inf'), j))
        keep = max(worse)[1]
        cols = [c for c in cols if c == keep or c not in dup]


def nb_alpha(X, y, expo, cols):
    """Розсіяння для негативної біноміальної — один раз, на моделі з усіма
    змінними після elastic net: так покроковий відбір порівнює моделі з
    однаковим α і BIC між ними чесний."""
    import statsmodels.api as sm
    A = np.column_stack([np.ones(len(y))] + [X[:, j] for j in cols])
    try:
        r = sm.NegativeBinomial(y, A, offset=np.log(expo)).fit(disp=0, maxiter=200)
        a = float(r.params[-1])
        return a if np.isfinite(a) and a > 1e-4 else None
    except Exception:
        return None


def select(X, y, expo, typ, log=print):
    """Увесь відбір RTM для одного набору подій. Повертає словник:
    cols, fam ('P'/'NB'), alpha, модель statsmodels, bic, скільки після enet."""
    keep = enet_cv(X, y, expo, log=log)
    if not keep:
        return dict(cols=[], fam='P', alpha=None, fit=None, bic=None, n_enet=0)
    out = []
    cp, bp = stepwise(X, y, expo, keep, 'P', log=log)
    cp = one_r_per_type(X, y, expo, cp, typ, 'P')
    rp = _glm(X, y, expo, cp, 'P')
    out.append((bic(rp, len(y), 'P'), 'P', None, cp, rp))
    a = nb_alpha(X, y, expo, keep)
    if a:
        cn, _bn = stepwise(X, y, expo, keep, 'NB', a, log=log)
        cn = one_r_per_type(X, y, expo, cn, typ, 'NB', a)
        rn = _glm(X, y, expo, cn, 'NB', a)
        if rn is not None:
            out.append((bic(rn, len(y), 'NB'), 'NB', a, cn, rn))
    b, fam, a, cols, r = min(out, key=lambda x: x[0])
    log(f'      покроково ({"Пуассон" if fam == "P" else "негативна біноміальна"}, BIC {b:,.0f}): '
        f'{len(cols)} змінних')
    return dict(cols=cols, fam=fam, alpha=a, fit=r, bic=b, n_enet=len(keep))


def predict(sel, X, expo):
    """очікувана кількість подій на відрізку (з довжиною)"""
    if not sel['cols'] or sel['fit'] is None:
        return expo * 0 + 1.0
    A = np.column_stack([np.ones(len(expo))] + [X[:, j] for j in sel['cols']])
    return np.exp(np.clip(A @ sel['fit'].params, -30, 30)) * expo


def hit_rate(score, actual, pct=0.10):
    """частка подій наступного періоду на верхніх pct відрізків"""
    k = max(1, int(len(score) * pct))
    top = np.argsort(-score, kind='stable')[:k]
    return float(actual[top].sum() / max(actual.sum(), 1))
