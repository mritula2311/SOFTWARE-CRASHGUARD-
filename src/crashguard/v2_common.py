"""Shared helpers of the v2 studies (docs/02_preregistration/PREREGISTRATION_V2.md). Every entry written by a v2 study has a name that starts with ``v2.``, and a study may only purge ``v2.`` prefixes, so no tagged key can be
overwritten (an earlier collision happened in round 3)."""
from __future__ import annotations

import numpy as np

from crashguard.results import record_many


def record_v2(entries: list[dict], purge_prefixes: tuple[str, ...]) -> None:
    for e in entries:
        if not e["name"].startswith("v2."):
            raise ValueError(f"v2 entries must start with 'v2.': {e['name']}")
    for p in purge_prefixes:
        if not p.startswith("v2."):
            raise ValueError(f"v2 studies may only purge 'v2.' prefixes: {p}")
    record_many(entries, purge_prefixes=purge_prefixes)


class Entries:
    """Collects result entries of one study with a fixed prefix, source file and default origin."""

    def __init__(self, prefix: str, source: str, origin: str):
        self.prefix, self.source, self.origin = prefix, source, origin
        self.items: list[dict] = []

    def add(self, name: str, value, unit: str, notes: str = "", origin: str | None = None) -> None:
        if isinstance(value, (np.floating, np.integer)):
            value = value.item()
        if isinstance(value, float) and not np.isfinite(value):
            self.items.append(dict(name=f"{self.prefix}.{name}", value="NOT_RUN", unit=unit, origin="NOT_RUN", source_file=self.source, notes=(notes + "; value not finite").strip("; ")))
            return
        self.items.append(dict(name=f"{self.prefix}.{name}", value=value, unit=unit, origin=origin or self.origin, source_file=self.source, notes=notes))

    def ci(self, name: str, triple, unit: str, notes: str = "", d: int = 4, origin: str | None = None) -> None:
        p, lo, hi = triple
        self.add(name, round(float(p), d), unit, notes, origin)
        self.add(name + "_lo", round(float(lo), d), unit, "95% bootstrap interval", origin)
        self.add(name + "_hi", round(float(hi), d), unit, "95% bootstrap interval", origin)

    def flush(self) -> None:
        record_v2(self.items, (f"{self.prefix}.",))


def holm(p: dict[str, float]) -> dict[str, float]:
    """Holm-adjusted p-values (step-down), keys preserved."""
    names = sorted(p, key=lambda k: p[k])
    m, out, run = len(names), {}, 0.0
    for i, k in enumerate(names):
        run = max(run, min(1.0, (m - i) * p[k]))
        out[k] = run
    return out


def mean_of_cells(diffs: list[np.ndarray], n_boot: int = 1000, seed: int = 42) -> tuple[float, np.ndarray]:
    """Mean over cells of the mean paired difference, with draws that resample the seeds inside every cell (the ``s11_sct.agg_diff`` rule)."""
    rng = np.random.default_rng(seed)
    point = float(np.mean([d.mean() for d in diffs]))
    draws = np.array([np.mean([d[rng.integers(0, len(d), len(d))].mean() for d in diffs]) for _ in range(n_boot)])
    return point, draws


def paired_diffs(R, cells: list[str], a: str, b: str, metric: str) -> list[np.ndarray]:
    """b minus a per cell, paired by seed hour; ``R`` has columns cell, cfg, hour and the metric."""
    out = []
    for c in cells:
        sub = R[R.cell == c]
        pa = sub[sub.cfg == a].sort_values("hour")[metric].to_numpy(float)
        pb = sub[sub.cfg == b].sort_values("hour")[metric].to_numpy(float)
        m = ~(np.isnan(pa) | np.isnan(pb))
        if m.sum() >= 3:
            out.append((pb - pa)[m])
    return out
