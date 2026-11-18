"""Near-duplicate scan between sets of trigger-aligned acceleration windows (docs/02_preregistration/EXPERIMENTS_EXTRA.md, S2 and S3).

Pair rule, fixed before any run: correlation above ``CORR_MIN`` (Pearson, per-axis mean removed, axes concatenated) AND maximum absolute difference below ``MAXDIFF_G`` (raw g, all
axes, all samples). The maximum-difference search is exact for that threshold: a pair with a maximum difference below d has an L2 distance below d * sqrt(n_values), so all pairs
within that L2 distance are checked.
"""
from __future__ import annotations

import numpy as np

CORR_MIN = 0.999
MAXDIFF_G = 0.01
CHUNK = 256


def _flat(w: np.ndarray) -> np.ndarray:
    return np.asarray(w, np.float64).reshape(len(w), -1)


def _centred_unit(w: np.ndarray) -> np.ndarray:
    """Per-axis mean removed over time, axes concatenated, scaled to unit norm (rows of zeros stay zero)."""
    x = np.asarray(w, np.float64)
    x = (x - x.mean(axis=1, keepdims=True)).reshape(len(x), -1)
    n = np.linalg.norm(x, axis=1, keepdims=True)
    return np.divide(x, n, out=np.zeros_like(x), where=n > 1e-12)


def scan(query: np.ndarray, ref: np.ndarray, corr_min: float = CORR_MIN, maxdiff_g: float = MAXDIFF_G) -> dict:
    """For every query window: the best correlation, the smallest maximum absolute difference among reference windows within the exact L2 bound, and the pair flags.

    Returns arrays (length len(query)): ``max_corr``, ``min_maxdiff`` (inf if no reference window is within the L2 bound, i.e. the true value is above ``maxdiff_g``),
    ``both`` (some single pair meets both thresholds), ``corr_only`` (max_corr above threshold), ``diff_only`` (min_maxdiff below threshold).
    """
    q, r = np.asarray(query, np.float32), np.asarray(ref, np.float32)
    nq, nv = len(q), q[0].size if len(q) else 0
    qc, rc = _centred_unit(q), _centred_unit(r)
    qf, rf = _flat(q), _flat(r)
    r2 = (rf ** 2).sum(1)
    bound2 = (maxdiff_g ** 2) * nv * (1 + 1e-9) + 1e-9
    max_corr = np.full(nq, -1.0)
    min_md = np.full(nq, np.inf)
    both = np.zeros(nq, bool)
    for a in range(0, nq, CHUNK):
        b = min(nq, a + CHUNK)
        c = qc[a:b] @ rc.T
        max_corr[a:b] = c.max(1)
        d2 = (qf[a:b] ** 2).sum(1)[:, None] + r2[None, :] - 2.0 * (qf[a:b] @ rf.T)
        for i in range(b - a):
            cand = np.flatnonzero(d2[i] <= bound2 + 1e-6)  # 1e-6 absorbs the float rounding of the L2 formula
            if cand.size:
                md = np.abs(rf[cand] - qf[a + i]).max(1)
                min_md[a + i] = md.min()
                both[a + i] = bool(((md < maxdiff_g) & (c[i, cand] > corr_min)).any())
    return dict(max_corr=max_corr, min_maxdiff=min_md, both=both, corr_only=max_corr > corr_min, diff_only=min_md < maxdiff_g)
