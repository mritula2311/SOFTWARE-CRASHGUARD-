"""F0: VZCrash-style surrogate window generator (block F; SIMULATED; EXPLORATORY-REVISED use). VZCrash is CC BY-NC 4.0 (Hugging Face revision 42e1482d005c0e545379d6cfa4939486c9fe4249); the fitted parameters are therefore released under
CC BY-NC 4.0 with attribution to the VZCrash authors. Only SUMMARY statistics of the training split are fitted (class balance; per class: distributions of the pre-trigger mean vector and noise level, the peak resultant, the time of the peak,
the decay time, the share of the energy along each axis, post-trigger band-energy shares, the gyro-to-acceleration peak ratio); no individual record is stored. It matches only the marginals that were validated (``validate``); detector scores on
surrogate windows are NOT comparable with real-data scores; the surrogate is not called unbiased. Window: 280 samples x 3 axes at 100 Hz, trigger at sample 100 (|a| >= 2 g there)."""
from __future__ import annotations

import numpy as np
from scipy.signal import butter, sosfiltfilt

from crashguard import config as C

PRE, N = C.PRE_N, 280
BANDS = ((0.5, 2.0), (2.0, 5.0), (5.0, 10.0), (10.0, 25.0), (25.0, 49.0))
FS = 100.0


def _summ(acc: np.ndarray, gyro: np.ndarray) -> dict:
    base = acc[:, : PRE - 5].mean(1)
    pre_sd = acc[:, : PRE - 5].std(1)
    post = acc[:, PRE:] - base[:, None, :]
    res = np.linalg.norm(post, axis=2)
    pk = res.max(1)
    tpk = res.argmax(1).astype(float)
    # decay: samples after the peak until the resultant falls below 20% of the peak (capped at the window end)
    dec = np.array([float(np.argmax(r[int(t):] < 0.2 * p)) if (r[int(t):] < 0.2 * p).any() else float(len(r) - t) for r, t, p in zip(res, tpk, pk)])
    ax_e = (post**2).sum(1)
    ax_share = ax_e / np.maximum(ax_e.sum(1, keepdims=True), 1e-9)
    F = np.abs(np.fft.rfft(res - res.mean(1, keepdims=True), axis=1)) ** 2
    fr = np.fft.rfftfreq(res.shape[1], 1 / FS)
    bs = np.stack([F[:, (fr >= lo) & (fr < hi)].sum(1) for lo, hi in BANDS], axis=1)
    bs = bs / np.maximum(bs.sum(1, keepdims=True), 1e-12)
    gpk = np.linalg.norm(gyro[:, PRE:], axis=2).max(1)
    return dict(base=base, pre_sd=pre_sd, pk=pk, tpk=tpk, dec=dec, ax_share=ax_share, bands=bs, gratio=np.log(np.maximum(gpk, 1e-3) / np.maximum(pk, 1e-3)))


def fit(acc: np.ndarray, gyro: np.ndarray, y: np.ndarray) -> dict:
    """Summary parameters per class (means and covariances of transformed statistics; class share)."""
    out = dict(share_crash=float(y.mean()), n_fit=int(len(y)))
    for c, name in ((1, "crash"), (0, "noncrash")):
        s = _summ(acc[y == c], gyro[y == c])
        X = np.column_stack([np.log(np.maximum(s["pk"], 1e-3)), np.log1p(s["tpk"]), np.log1p(s["dec"]), s["gratio"], np.log(np.maximum(s["pre_sd"].mean(1), 1e-4)), s["base"], np.log(np.maximum(s["bands"], 1e-4))])
        out[name] = dict(mean=X.mean(0).tolist(), cov=np.cov(X.T).tolist(), ax_share_mean=s["ax_share"].mean(0).tolist(), ax_share_conc=float(1.0 / max(s["ax_share"].var(0).mean(), 1e-6) * 0.1))
    return out


def _band(x: np.ndarray, lo: float, hi: float) -> np.ndarray:
    return sosfiltfilt(butter(2, [lo, hi], btype="band", fs=FS, output="sos"), x, axis=0)


def sample(par: dict, n: int, seed: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """n surrogate windows (acc, gyro, label) with the fitted class share."""
    rng = np.random.default_rng(seed)
    yl = (rng.random(n) < par["share_crash"]).astype(int)
    acc = np.zeros((n, N, 3), np.float32)
    gyro = np.zeros((n, N, 3), np.float32)
    t = np.arange(N - PRE, dtype=float)
    for i in range(n):
        p = par["crash" if yl[i] else "noncrash"]
        z = rng.multivariate_normal(np.array(p["mean"]), np.array(p["cov"]))
        pk, tpk, dec, gr, sd = max(float(np.exp(z[0])), 2.05), float(np.expm1(z[1])), float(np.expm1(z[2])), float(z[3]), float(np.exp(z[4]))
        base = z[5:8]
        bs = np.exp(z[8:13])
        bs = bs / bs.sum()
        share = rng.dirichlet(np.maximum(np.array(p["ax_share_mean"]) * p["ax_share_conc"], 0.05))
        sgn = rng.choice([-1.0, 1.0], 3)
        a = np.sqrt(share) * sgn
        # envelope: rises from 2 g at the trigger to the peak at tpk, then decays with time constant dec/1.6 (samples)
        tp = max(tpk, 1.0)
        env = np.where(t <= tp, 2.0 + (pk - 2.0) * (t / tp), pk * np.exp(-(t - tp) / max(dec / 1.6, 1.0)))
        # texture: band-limited noise with the fitted band shares, scaled to 35% of the envelope
        tex = np.zeros(len(t))
        for (lo, hi), s_ in zip(BANDS, bs):
            tex += np.sqrt(s_) * _band(rng.standard_normal(len(t)), lo, hi) / (np.std(_band(rng.standard_normal(len(t)), lo, hi)) + 1e-9)
        tex = tex / (np.std(tex) + 1e-9)
        res = np.maximum(env * (1.0 + 0.35 * tex), 0.0)
        res[0] = max(res[0], 2.05)
        acc[i, PRE:, :] = res[:, None] * a[None, :]
        acc[i, :PRE, :] = rng.normal(0.0, sd, (PRE, 3))
        acc[i] += base[None, :]
        acc[i, PRE, :] = res[0] * a + base  # the trigger sample
        gyro[i, PRE:, :] = (np.exp(gr) * res)[:, None] * rng.choice([-1.0, 1.0], 3)[None, :] * np.abs(a)[None, :] + rng.normal(0, 0.02, (len(t), 3))
        gyro[i, :PRE, :] = rng.normal(0, 0.02, (PRE, 3))
    return acc, gyro, yl
