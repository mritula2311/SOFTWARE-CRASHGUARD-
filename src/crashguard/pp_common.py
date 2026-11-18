"""Shared pieces of the positive-results push (docs/02_preregistration/PREREGISTRATION_V4.md). Every result key written by these studies starts with ``p.``.

* ``PEntries``: collects results.json entries of one study (prefix ``p.<study>``), purging only ``p.`` keys, so no tagged key can be touched.
* Severity classes (the classes of the UA-SCT study: limits ``config.SEV_DV_KMH`` on the resultant delta-V) and the triage metrics.
* ``freeze`` and ``sealed_gate``: the sealed fold of docs/05_data_code/SEALED_SPLIT.md is scored once per hypothesis, after the model and its settings are frozen in a commit.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import subprocess
from pathlib import Path

import numpy as np

from crashguard import boot as B
from crashguard import config as C
from crashguard.results import record_many

PREFIX = "p."
CLASSES = C.SEV_NAMES  # Low, Moderate, Severe, Critical
EDGES = np.array(C.SEV_DV_KMH)
MODES = ("frontal_barrier", "pole", "side", "other")
RANGES = (16.0, 32.0, 64.0)
RATES = (100, 200)
PRIMARY_RATE = 100
ACCESS_LOG = Path("results/tables/p_sealed_access.csv")
FREEZE_DIR = Path("results/tables")


def cls_of(dv_kmh) -> np.ndarray:
    """Class index 0..3 of resultant delta-V values (km/h)."""
    return np.searchsorted(EDGES, np.asarray(dv_kmh, dtype=float), side="right")


class PEntries:
    """Result entries of one study. ``name`` is relative to ``p.<study>``."""

    def __init__(self, study: str, source: str, origin: str = "MEASURED_SOFTWARE"):
        self.prefix, self.source, self.origin = f"{PREFIX}{study}", source, origin
        self.items: list[dict] = []

    def add(self, name: str, value, unit: str, notes: str = "", origin: str | None = None) -> None:
        if isinstance(value, (np.floating, np.integer)):
            value = value.item()
        if isinstance(value, (bool, np.bool_)):
            value = int(value)
        if isinstance(value, float) and not np.isfinite(value):
            self.items.append(dict(name=f"{self.prefix}.{name}", value="NOT_RUN", unit=unit, origin="NOT_RUN", source_file=self.source, notes=(notes + "; value not finite").strip("; ")))
            return
        self.items.append(dict(name=f"{self.prefix}.{name}", value=value, unit=unit, origin=origin or self.origin, source_file=self.source, notes=notes))

    def ci(self, name: str, triple, unit: str, notes: str = "", d: int = 4, origin: str | None = None) -> None:
        p, lo, hi = triple
        self.add(name, round(float(p), d), unit, notes, origin)
        self.add(name + "_lo", round(float(lo), d), unit, "95% bootstrap interval", origin)
        self.add(name + "_hi", round(float(hi), d), unit, "95% bootstrap interval", origin)

    def not_run(self, name: str, unit: str, reason: str) -> None:
        self.items.append(dict(name=f"{self.prefix}.{name}", value="NOT_RUN", unit=unit, origin="NOT_RUN", source_file=self.source, notes=reason))

    def flush(self, purge: tuple[str, ...] | None = None) -> None:
        for e in self.items:
            if not e["name"].startswith(PREFIX):
                raise ValueError(f"positive-push keys must start with {PREFIX!r}: {e['name']}")
        pp = purge if purge is not None else (f"{self.prefix}.",)
        for p in pp:
            if not p.startswith(PREFIX):
                raise ValueError(f"positive-push studies may only purge {PREFIX!r} keys: {p}")
        lock = Path("results/.results.lock")
        import os
        import time

        for _ in range(600):  # one writer at a time: two studies running in parallel can otherwise read a half-written results.json
            try:
                fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                break
            except FileExistsError:
                time.sleep(0.5)
        else:
            raise RuntimeError("results.json lock not released")
        try:
            record_many(self.items, purge_prefixes=pp)
        finally:
            os.close(fd)
            lock.unlink(missing_ok=True)


# ---- severity triage metrics (definitions fixed in docs/02_preregistration/PREREGISTRATION_V4.md section 0) ----
def macro_f1(y: np.ndarray, p: np.ndarray, k: int = 4) -> float:
    f = []
    for c in range(k):
        tp = float(np.sum((y == c) & (p == c)))
        fp = float(np.sum((y != c) & (p == c)))
        fn = float(np.sum((y == c) & (p != c)))
        d = 2 * tp + fp + fn
        if np.sum(y == c) == 0 and np.sum(p == c) == 0:
            continue  # class absent from the sample: not averaged
        f.append(2 * tp / d if d > 0 else 0.0)
    return float(np.mean(f)) if f else float("nan")


def balanced_acc(y: np.ndarray, p: np.ndarray, k: int = 4) -> float:
    r = [np.mean(p[y == c] == c) for c in range(k) if np.sum(y == c) > 0]
    return float(np.mean(r)) if r else float("nan")


def under_triage(y: np.ndarray, p: np.ndarray) -> float:
    """Share of true Severe or Critical events predicted a lower class than their true class."""
    m = y >= 2
    return float(np.mean(p[m] < y[m])) if m.any() else float("nan")


def over_triage(y: np.ndarray, p: np.ndarray) -> float:
    """Share of true Low or Moderate events predicted a higher class than their true class."""
    m = y <= 1
    return float(np.mean(p[m] > y[m])) if m.any() else float("nan")


def mis_triage(y: np.ndarray, p: np.ndarray) -> float:
    """UA-SCT definition: share of true Severe or Critical events assigned below Severe."""
    m = y >= 2
    return float(np.mean(p[m] < 2)) if m.any() else float("nan")


def escalation(y: np.ndarray, p: np.ndarray) -> float:
    """UA-SCT definition: share of true non-severe events assigned Severe or above."""
    m = y <= 1
    return float(np.mean(p[m] >= 2)) if m.any() else float("nan")


TRIAGE = dict(macro_f1=macro_f1, under_triage=under_triage, over_triage=over_triage, balanced_acc=balanced_acc, mis_triage=mis_triage)


def boot_stat(groups: np.ndarray, fn, n_boot: int = B.N_BOOT, seed: int = B.SEED) -> tuple[float, float, float]:
    """(point, lo, hi) of ``fn(idx)`` (idx = row indices) with whole groups resampled."""
    mem = B.group_members(groups)
    n = sum(len(m) for m in mem)
    pt = float(fn(np.arange(n)))
    draws = np.array([fn(i) for i in B._gidx(mem, n_boot, seed)], dtype=float)
    return pt, float(np.nanquantile(draws, 0.025)), float(np.nanquantile(draws, 0.975))


def boot_draws(groups: np.ndarray, fn, n_boot: int = B.N_BOOT, seed: int = B.SEED) -> tuple[float, np.ndarray]:
    mem = B.group_members(groups)
    n = sum(len(m) for m in mem)
    return float(fn(np.arange(n))), np.array([fn(i) for i in B._gidx(mem, n_boot, seed)], dtype=float)


def summ(pt: float, d: np.ndarray) -> tuple[float, float, float]:
    return pt, float(np.nanquantile(d, 0.025)), float(np.nanquantile(d, 0.975))


def p_below(d: np.ndarray, margin: float = 0.0) -> float:
    """One-sided bootstrap p-value for 'statistic >= margin' (share of resamples at or below the margin); floor 1/(B+1)."""
    d = d[np.isfinite(d)]
    return float(max(np.mean(d <= margin), 1.0 / (len(d) + 1)))


def p_above(d: np.ndarray, margin: float = 0.0) -> float:
    d = d[np.isfinite(d)]
    return float(max(np.mean(d >= margin), 1.0 / (len(d) + 1)))


# ---- freeze and sealed gate ----
def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()


def sha256_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def now() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M")


def freeze(hyp: str, payload: dict, files: list[Path] | None = None, commit: bool = True) -> str:
    """Write ``results/tables/p_freeze_<hyp>.json`` (settings, thresholds, sha256 of every model file) and commit it. Returns the commit hash."""
    import json

    payload = dict(payload, hypothesis=hyp, frozen_at=now(), model_files={str(f): sha256_file(f) for f in (files or [])})
    out = FREEZE_DIR / f"p_freeze_{hyp}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
    if not commit:
        return "NOT_COMMITTED"
    git("add", str(out))
    git("commit", "-m", f"Freeze {hyp}: model and settings fixed on development and validation (before the sealed fold is scored)\n\nCo-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>")
    return git("rev-parse", "HEAD")


def sealed_gate(hyp: str, deviation: str = "") -> str:
    deviation = deviation or __import__("os").environ.get("PP_DEVIATION", "")
    """Allow ONE evaluation of the sealed fold per hypothesis. Requires the freeze file of ``hyp`` to be committed and unchanged; returns the freeze commit hash.

    A second call for the same hypothesis raises unless ``deviation`` gives a reason; the reason is written to the access log (a dated, labelled deviation).
    """
    ACCESS_LOG.parent.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(ACCESS_LOG.open(encoding="utf-8"))) if ACCESS_LOG.exists() else []
    if any(r["hypothesis"] == hyp for r in rows) and not deviation:
        raise RuntimeError(f"the sealed fold was already scored for {hyp}; a repeat needs a stated deviation")
    fz = FREEZE_DIR / f"p_freeze_{hyp}.json"
    if not fz.exists():
        raise RuntimeError(f"no freeze file for {hyp}")
    if git("status", "--porcelain", str(fz)):
        raise RuntimeError(f"freeze file of {hyp} is not committed")
    h = git("log", "-1", "--format=%H", "--", str(fz))
    rows.append(dict(hypothesis=hyp, scored_at=now(), freeze_commit=h, deviation=deviation))
    with ACCESS_LOG.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["hypothesis", "scored_at", "freeze_commit", "deviation"])
        w.writeheader()
        w.writerows(rows)
    return h


def decide(text: str, reason: str = "", effect: str = "None on results") -> None:
    """Append one dated row to docs/07_log/DECISIONS.md (a decision, mistake or fix of the positive-results push)."""
    row = f"| {dt.date.today().isoformat()} | {' '.join(text.split())} | {' '.join(reason.split()) or '-'} | {' '.join(effect.split())} |\n"
    p = Path("docs/07_log/DECISIONS.md")
    s = p.read_text(encoding="utf-8")
    p.write_text(s + ("" if s.endswith("\n") else "\n") + row, encoding="utf-8")


def time_log(task: str, note: str) -> None:
    """Append one row to docs/07_log/TIME_LOG.md."""
    p = Path("docs/07_log/TIME_LOG.md")
    s = p.read_text(encoding="utf-8")
    p.write_text(s + ("" if s.endswith("\n") else "\n") + f"| {now()} | {task} | {note} |\n", encoding="utf-8")


class GBoot:
    """Whole-group bootstrap with the resampled row indices drawn once (1,000 draws, seed 42) so every statistic and every method shares the same draws (paired)."""

    def __init__(self, groups: np.ndarray, n_boot: int = B.N_BOOT, seed: int = B.SEED):
        mem = B.group_members(groups)
        self.n = sum(len(m) for m in mem)
        self.draws = list(B._gidx(mem, n_boot, seed))

    def stat(self, fn) -> tuple[float, np.ndarray]:
        return float(fn(np.arange(self.n))), np.array([fn(i) for i in self.draws], dtype=float)

    def ci(self, fn) -> tuple[float, float, float]:
        pt, d = self.stat(fn)
        return summ(pt, d)
