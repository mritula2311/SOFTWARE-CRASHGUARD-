"""Shared helpers of the redesign round (docs/02_preregistration/PREREGISTRATION_V12.md): result recording under the ``rd.`` prefix, paired bootstrap over events, exact tests, Holm.

SIMULATED unless a function says otherwise. Nothing here reads ``data/hardware``.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from crashguard.results import record_many

SEED = 42
NB = 2000  # bootstrap resamples


class Rec:
    """Collects result entries for one study and writes them with a purge of the study's own prefix."""

    def __init__(self, prefix: str, src: str, default_origin: str = "SIMULATED"):
        self.prefix, self.src, self.origin = prefix, src, default_origin
        self.ent: list[dict] = []

    def add(self, name: str, value, unit: str, notes: str = "", origin: str | None = None) -> None:
        if isinstance(value, float):
            value = round(value, 6)
        self.ent.append(dict(name=f"{self.prefix}{name}", value=value, unit=unit, origin=origin or self.origin, source_file=self.src, notes=notes))

    def write(self) -> None:
        record_many(self.ent, purge_prefixes=(self.prefix,))

    def get(self, name: str):
        for e in self.ent:
            if e["name"] == f"{self.prefix}{name}":
                return e["value"]
        raise KeyError(name)


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha256_json(obj) -> str:
    return sha256_text(json.dumps(obj, sort_keys=True, default=str))


def boot_mean(x: np.ndarray, seed: int = SEED, nb: int = NB) -> tuple[float, float, float]:
    """Mean and 95% percentile interval of ``x`` over ``nb`` resamples (of the units of ``x``)."""
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    if len(x) == 0:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), (nb, len(x)))
    m = x[idx].mean(1)
    return float(x.mean()), float(np.quantile(m, 0.025)), float(np.quantile(m, 0.975))


def paired_event_test(d: np.ndarray, margin: float, alt: str = "greater", seed: int = SEED, nb: int = NB) -> dict:
    """Paired bootstrap over events. ``d`` = per-event difference (new minus old, each 0/1 or a share), already paired.

    alt 'greater': H0: mean(d) <= margin, p = share of resampled means <= margin (floored at 1/(nb+1)).
    Returns the point estimate, the 95% interval, the one-sided lower 95% bound, and p.
    """
    d = np.asarray(d, float)
    d = d[~np.isnan(d)]
    if len(d) == 0:
        return dict(n=0, pt=float("nan"), lo=float("nan"), hi=float("nan"), lb95=float("nan"), p=1.0)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), (nb, len(d)))
    m = d[idx].mean(1)
    p = float((m <= margin).sum() + 1) / (nb + 1) if alt == "greater" else float((m >= margin).sum() + 1) / (nb + 1)
    return dict(n=int(len(d)), pt=float(d.mean()), lo=float(np.quantile(m, 0.025)), hi=float(np.quantile(m, 0.975)), lb95=float(np.quantile(m, 0.05)), p=p)


def _cluster_sums(d: np.ndarray, groups: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    ok = ~np.isnan(d)
    _u, inv = np.unique(groups, return_inverse=True)
    return np.bincount(inv, weights=np.where(ok, d, 0.0)), np.bincount(inv, weights=ok.astype(float))


def paired_cluster_test(d: np.ndarray, groups: np.ndarray, margin: float, seed: int = SEED, nb: int = NB) -> dict:
    """As ``paired_event_test`` but the simulated hour (``groups``) is resampled, so that events of the same hour (one channel episode, one burst) are not treated as independent. Mean = ratio of resampled sums."""
    S, C = _cluster_sums(np.asarray(d, float), np.asarray(groups))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(S), (nb, len(S)))
    m = S[idx].sum(1) / C[idx].sum(1)
    pt = float(S.sum() / C.sum())
    return dict(n=int(C.sum()), pt=pt, lo=float(np.quantile(m, 0.025)), hi=float(np.quantile(m, 0.975)), lb95=float(np.quantile(m, 0.05)), p=float((m <= margin).sum() + 1) / (nb + 1))


def holm(ps: dict[str, float]) -> dict[str, float]:
    """Holm-adjusted p-values (step-down, monotone)."""
    items = sorted(ps.items(), key=lambda kv: kv[1])
    m = len(items)
    out, run = {}, 0.0
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, (m - i) * p))
        out[k] = run
    return out
