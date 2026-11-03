"""AI/ML experiment: estimating the Schumann fundamental f1 from noisy spectra.

Synthetic but physically shaped spectra (Lorentzian modes 1-2, 1/f-like
background, multiplicative Welch-type noise, and - in 35 % of cases - a
narrow anthropogenic interference line) are generated with SplitMix64, so
the dataset is bit-identical on every machine. Five estimators are compared:

  argmax        peak picking on the raw spectrum
  lm            Levenberg-Marquardt Lorentzian fit (relative weights)
  lm_robust     the same with Cauchy IRLS re-weighting (interference-tolerant)
  ridge         ridge regression on the standardised log-spectrum (ML)
  hybrid        ridge prediction used to initialise lm_robust (AI + physics)
"""
from __future__ import annotations

import math

from .prng import SplitMix64

F_LO, F_STEP, N_BINS = 5.0, 0.05, 121          # 5.00 ... 11.00 Hz
GRID = [round(F_LO + F_STEP * i, 10) for i in range(N_BINS)]
SIGMA_NOISE = 0.12
P_INTERFERENCE = 0.35


def lorentz(f: float, f0: float, hw: float) -> float:
    u = (f - f0) / hw
    return 1.0 / (1.0 + u * u)


def make_sample(rng: SplitMix64) -> dict:
    f1 = rng.range(7.4, 8.2)
    hw1 = rng.range(1.2, 2.6) / 2
    a1 = rng.range(0.6, 1.4)
    f2 = rng.range(13.6, 14.8)
    hw2 = rng.range(1.8, 3.4) / 2
    a2 = a1 * rng.range(0.5, 0.9)
    b0 = rng.range(0.03, 0.15)
    b1 = rng.range(0.0, 0.4)
    has_int = rng.uniform() < P_INTERFERENCE
    fi = rng.range(5.5, 10.5)
    ai = a1 * rng.range(0.8, 2.0)
    spectrum = []
    for f in GRID:
        s = a1 * lorentz(f, f1, hw1) + a2 * lorentz(f, f2, hw2) + b0 + b1 * (8.0 / f)
        if has_int:
            s += ai * math.exp(-0.5 * ((f - fi) / 0.04) ** 2)
        noise = max(0.05, 1.0 + SIGMA_NOISE * rng.normal())
        spectrum.append(s * noise)
    return {"f1": f1, "interference": has_int, "fi": fi if has_int else None, "y": spectrum}


def make_dataset(seed: int, n: int) -> list[dict]:
    rng = SplitMix64(seed)
    return [make_sample(rng) for _ in range(n)]


# -- estimators -------------------------------------------------------------
def est_argmax(y: list[float]) -> float:
    best = max((i for i in range(N_BINS) if 6.0 <= GRID[i] <= 10.0), key=lambda i: y[i])
    return GRID[best]


def _smooth(y: list[float], k: int = 2) -> list[float]:
    out = []
    for i in range(N_BINS):
        lo, hi = max(0, i - k), min(N_BINS, i + k + 1)
        out.append(sum(y[lo:hi]) / (hi - lo))
    return out


def _solve(a: list[list[float]], b: list[float]) -> list[float]:
    """Gaussian elimination with partial pivoting (small dense systems)."""
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(m[r][c]))
        if abs(m[p][c]) < 1e-300:
            raise ArithmeticError("singular")
        m[c], m[p] = m[p], m[c]
        for r in range(c + 1, n):
            fac = m[r][c] / m[c][c]
            if fac:
                for k in range(c, n + 1):
                    m[r][k] -= fac * m[c][k]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        x[r] = (m[r][n] - sum(m[r][k] * x[k] for k in range(r + 1, n))) / m[r][r]
    return x


def _model(p: list[float], f: float) -> tuple[float, list[float]]:
    a, f0, hw, c0, c1 = p
    u = (f - f0) / hw
    d = 1.0 + u * u
    val = a / d + c0 + c1 * (f - 8.0)
    jac = [1.0 / d, a * 2 * u / (hw * d * d), a * 2 * u * u / (hw * d * d), 1.0, f - 8.0]
    return val, jac


def _clamp(p: list[float]) -> list[float]:
    a, f0, hw, c0, c1 = p
    return [max(1e-6, a), min(10.5, max(5.5, f0)), min(3.0, max(0.2, hw)), c0, c1]


def lm_fit(y: list[float], f0_init: float, robust: bool, rounds: int = 4, iters: int = 25) -> list[float]:
    ys = _smooth(y)
    base = [1.0 / max(v, 1e-6) ** 2 for v in ys]          # relative-error weights
    p = _clamp([max(ys) - min(ys), f0_init, 0.9, min(ys), 0.0])
    w_rob = [1.0] * N_BINS
    for _ in range(rounds if robust else 1):
        w = [base[i] * w_rob[i] for i in range(N_BINS)]

        def cost(pp):
            return sum(w[i] * (y[i] - _model(pp, GRID[i])[0]) ** 2 for i in range(N_BINS))

        lam = 1e-2
        c_old = cost(p)
        for _ in range(iters):
            jtj = [[0.0] * 5 for _ in range(5)]
            jtr = [0.0] * 5
            for i, f in enumerate(GRID):
                val, jac = _model(p, f)
                r = y[i] - val
                wi = w[i]
                for a_ in range(5):
                    ja = wi * jac[a_]
                    jtr[a_] += ja * r
                    row = jtj[a_]
                    for b_ in range(a_, 5):
                        row[b_] += ja * jac[b_]
            for a_ in range(5):
                for b_ in range(a_):
                    jtj[a_][b_] = jtj[b_][a_]
            damped = [[jtj[r][c] * (1 + lam if r == c else 1) for c in range(5)] for r in range(5)]
            try:
                dp = _solve(damped, jtr)
            except ArithmeticError:
                break
            cand = _clamp([p[k] + dp[k] for k in range(5)])
            c_new = cost(cand)
            if c_new < c_old:
                p, c_old, lam = cand, c_new, max(lam / 3, 1e-7)
                if abs(dp[1]) < 1e-6:
                    break
            else:
                lam = min(lam * 4, 1e7)
        if robust:
            res = [(y[i] - _model(p, GRID[i])[0]) * math.sqrt(base[i]) for i in range(N_BINS)]
            med = sorted(abs(r) for r in res)[N_BINS // 2]
            scale = max(1.4826 * med, 1e-9)
            w_rob = [1.0 / (1.0 + (r / (2.385 * scale)) ** 2) for r in res]
    return p


# -- ridge regression (ML) ---------------------------------------------------
def _features(y: list[float]) -> list[float]:
    return [math.log(max(v, 1e-9)) for v in y]


class Ridge:
    def fit(self, xs: list[list[float]], ys: list[float], lam: float) -> "Ridge":
        n, d = len(xs), len(xs[0])
        self.mu = [sum(x[j] for x in xs) / n for j in range(d)]
        self.sd = [max(1e-9, math.sqrt(sum((x[j] - self.mu[j]) ** 2 for x in xs) / n)) for j in range(d)]
        self.ymu = sum(ys) / n
        z = [[(x[j] - self.mu[j]) / self.sd[j] for j in range(d)] for x in xs]
        a = [[0.0] * d for _ in range(d)]
        b = [0.0] * d
        for row, yv in zip(z, ys):
            yc = yv - self.ymu
            for i in range(d):
                ri = row[i]
                b[i] += ri * yc
                ai = a[i]
                for j in range(i, d):
                    ai[j] += ri * row[j]
        for i in range(d):
            for j in range(i):
                a[i][j] = a[j][i]
            a[i][i] += lam
        self.w = _solve(a, b)
        return self

    def predict(self, x: list[float]) -> float:
        return self.ymu + sum(self.w[j] * (x[j] - self.mu[j]) / self.sd[j] for j in range(len(x)))


# -- experiment ---------------------------------------------------------------
def _metrics(errors: list[float]) -> dict:
    n = len(errors)
    ab = sorted(abs(e) for e in errors)
    return {"n": n, "mae_hz": round(sum(ab) / n, 4), "rmse_hz": round(math.sqrt(sum(e * e for e in errors) / n), 4),
            "p95_hz": round(ab[min(n - 1, int(math.ceil(0.95 * n)) - 1)], 4),
            "fail_rate_gt_0_2hz": round(sum(1 for e in ab if e > 0.2) / n, 4),
            "bias_hz": round(sum(errors) / n, 4)}


def run(seed_train: int = 7831, seed_test: int = 7832, n_train: int = 1200, n_test: int = 400) -> dict:
    train = make_dataset(seed_train, n_train)
    test = make_dataset(seed_test, n_test)
    xs = [_features(s["y"]) for s in train]
    ys = [s["f1"] for s in train]
    cut = n_train - 200
    lam_scores = {}
    for lam in (0.1, 1.0, 10.0, 100.0, 1000.0, 10000.0):
        model = Ridge().fit(xs[:cut], ys[:cut], lam)
        lam_scores[lam] = sum(abs(model.predict(x) - t) for x, t in zip(xs[cut:], ys[cut:])) / (n_train - cut)
    best_lam = min(lam_scores, key=lambda k: (lam_scores[k], k))
    ridge = Ridge().fit(xs, ys, best_lam)

    errs = {m: {"all": [], "clean": [], "interference": []} for m in ("argmax", "lm", "lm_robust", "ridge", "hybrid")}
    example = None
    for idx, s in enumerate(test):
        y = s["y"]
        am = est_argmax(y)
        rp = ridge.predict(_features(y))
        preds = {
            "argmax": am,
            "lm": lm_fit(y, am, robust=False)[1],
            "lm_robust": lm_fit(y, am, robust=True)[1],
            "ridge": rp,
            "hybrid": lm_fit(y, min(8.6, max(7.0, rp)), robust=True)[1],
        }
        sub = "interference" if s["interference"] else "clean"
        for m, v in preds.items():
            e = v - s["f1"]
            errs[m]["all"].append(e)
            errs[m][sub].append(e)
        if example is None and s["interference"] and abs(preds["argmax"] - s["f1"]) > 0.5:
            fit = lm_fit(y, min(8.6, max(7.0, rp)), robust=True)
            example = {"index": idx, "f1_true": round(s["f1"], 4), "f_interference": round(s["fi"], 4),
                       "argmax": round(am, 4), "hybrid": round(fit[1], 4),
                       "y": [round(v, 4) for v in y],
                       "fit": [round(_model(fit, f)[0], 4) for f in GRID]}
    return {
        "grid": {"f_lo_hz": F_LO, "step_hz": F_STEP, "bins": N_BINS},
        "dataset": {"seed_train": seed_train, "seed_test": seed_test, "n_train": n_train, "n_test": n_test,
                    "noise_sigma": SIGMA_NOISE, "p_interference": P_INTERFERENCE,
                    "n_test_interference": sum(1 for s in test if s["interference"])},
        "ridge": {"lambda": best_lam, "val_mae_by_lambda": {str(k): round(v, 4) for k, v in lam_scores.items()}},
        "metrics": {m: {k: _metrics(v) for k, v in d.items()} for m, d in errs.items()},
        "example": example,
    }
