"""Bootstrap helpers: 95% percentile intervals from 1,000 resamples (seed 42 unless stated).

``ci`` resamples rows of one sample. ``paired_diff`` resamples the same row indices for two aligned samples (a paired comparison on the same tests or events).
Every severity, estimator and policy result in the report gets its interval from here.
"""
from __future__ import annotations

from typing import Callable

import numpy as np

N_BOOT = 1000
SEED = 42


def _idx(n: int, n_boot: int, seed: int):
    """Yield the resampled row indices one draw at a time (in blocks, so memory stays small for large samples)."""
    rng = np.random.default_rng(seed)
    block = max(1, min(n_boot, 4_000_000 // max(n, 1)))
    done = 0
    while done < n_boot:
        m = min(block, n_boot - done)
        yield from rng.integers(0, n, size=(m, n))
        done += m


def ci(x, stat: Callable[[np.ndarray], float], n_boot: int = N_BOOT, seed: int = SEED, level: float = 0.95) -> tuple[float, float, float]:
    """(point estimate, lower, upper) of ``stat`` over rows of ``x``, resampling rows with replacement."""
    x = np.asarray(x)
    if len(x) == 0:
        return float("nan"), float("nan"), float("nan")
    idx = _idx(len(x), n_boot, seed)
    draws = np.array([stat(x[i]) for i in idx], dtype=np.float64)
    a = (1 - level) / 2
    return float(stat(x)), float(np.nanquantile(draws, a)), float(np.nanquantile(draws, 1 - a))


def paired_diff(a, b, stat: Callable[[np.ndarray], float], n_boot: int = N_BOOT, seed: int = SEED, level: float = 0.95) -> tuple[float, float, float]:
    """(stat(b) - stat(a), lower, upper): the same resampled rows are used for both samples."""
    a, b = np.asarray(a), np.asarray(b)
    if len(a) != len(b):
        raise ValueError("paired samples must have the same length")
    if len(a) == 0:
        return float("nan"), float("nan"), float("nan")
    idx = _idx(len(a), n_boot, seed)
    draws = np.array([stat(b[i]) - stat(a[i]) for i in idx], dtype=np.float64)
    al = (1 - level) / 2
    return float(stat(b) - stat(a)), float(np.nanquantile(draws, al)), float(np.nanquantile(draws, 1 - al))


def p90(x: np.ndarray) -> float:
    return float(np.quantile(x, 0.9))


def share(mask: np.ndarray) -> float:
    return float(np.mean(mask))


# ---- grouped (cluster) bootstrap: every test of a drawn vehicle group is drawn together ----
def group_members(groups) -> list[np.ndarray]:
    """Index arrays, one per distinct group label (sorted by label, so the result does not depend on row order)."""
    g = np.asarray(groups)
    return [np.flatnonzero(g == u) for u in sorted(set(g.tolist()))]


def _gidx(members: list[np.ndarray], n_boot: int, seed: int):
    rng = np.random.default_rng(seed)
    k = len(members)
    for _ in range(n_boot):
        pick = rng.integers(0, k, size=k)
        yield np.concatenate([members[j] for j in pick])


def ci_grouped(x, groups, stat: Callable[[np.ndarray], float], n_boot: int = N_BOOT, seed: int = SEED, level: float = 0.95) -> tuple[float, float, float]:
    """Like ``ci`` but resamples whole groups (vehicles), not rows."""
    x = np.asarray(x)
    if len(x) == 0:
        return float("nan"), float("nan"), float("nan")
    mem = group_members(groups)
    draws = np.array([stat(x[i]) for i in _gidx(mem, n_boot, seed)], dtype=np.float64)
    a = (1 - level) / 2
    return float(stat(x)), float(np.nanquantile(draws, a)), float(np.nanquantile(draws, 1 - a))


def paired_diff_grouped(a, b, groups, stat: Callable[[np.ndarray], float], n_boot: int = N_BOOT, seed: int = SEED, level: float = 0.95) -> tuple[float, float, float]:
    """(stat(b) - stat(a), lower, upper) with whole groups resampled; the same drawn rows feed both samples."""
    a, b = np.asarray(a), np.asarray(b)
    if len(a) != len(b):
        raise ValueError("paired samples must have the same length")
    if len(a) == 0:
        return float("nan"), float("nan"), float("nan")
    mem = group_members(groups)
    draws = np.array([stat(b[i]) - stat(a[i]) for i in _gidx(mem, n_boot, seed)], dtype=np.float64)
    al = (1 - level) / 2
    return float(stat(b) - stat(a)), float(np.nanquantile(draws, al)), float(np.nanquantile(draws, 1 - al))
