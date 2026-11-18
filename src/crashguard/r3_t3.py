"""T3 (docs/02_preregistration/PREREGISTRATION_V14.md section 3): the detection side of the two-stage alert on real crash data (MEASURED_SOFTWARE).

    python -m crashguard.r3_t3

Reads the stored per-event decisions of ``s6_early`` (seed 42, de-duplicated VZCrash test split; no model is refitted; the test split was already scored once by s6_early and used again by R3, which is
stated in the preregistration). Measures: time from trigger to the provisional and to the full decision, the retraction share at the 1% and 5% false-alarm targets, and the agreement between the
severity class of the truncated window and of the full window on VZCrash crash events and on the NHTSA pulses (sensor model at 16 g, 100 Hz). Keys ``r3.t3.*``. The severity classes are computed
by ``severity.py`` and are crash-severity classes, not injury classes; VZCrash has no severity labels, so the agreement is between two computed classes (stated).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from crashguard import config as C
from crashguard import nhtsa as NH
from crashguard import severity as S
from crashguard import windows_cache as W
from crashguard.early import LENGTHS_MS
from crashguard.results import record_many

ROOT = Path(__file__).resolve().parents[2]
SRC = "src/crashguard/r3_t3.py"
NB = 2000
SEED = 42
TRUNC = LENGTHS_MS[:-1]  # 50, 100, 200, 400, 800 ms after the trigger


def cls_of(acc: np.ndarray, gyro: np.ndarray | None, n_post: int | None) -> int:
    end = C.PRE_N + n_post if n_post is not None else len(acc)
    g = gyro[:end] if gyro is not None else None
    return int(S.severity(acc[:end], C.FS_HZ, C.PRE_N, g)["severity_class"])


def boot_ci(x: np.ndarray, f, rng: np.random.Generator, nb: int = NB) -> tuple[float, float]:
    n = len(x)
    v = np.array([f(x[rng.integers(0, n, n)]) for _ in range(nb)])
    return float(np.quantile(v, 0.025)), float(np.quantile(v, 0.975))


def main() -> None:
    rng = np.random.default_rng(SEED)
    ent: list[dict] = []

    def add(name, value, unit, notes="", origin="MEASURED_SOFTWARE"):
        if isinstance(value, float):
            value = round(value, 6)
        ent.append(dict(name=f"r3.t3.{name}", value=value, unit=unit, origin=origin, source_file=SRC, notes=notes))

    summary: dict = {}
    for alpha, tag in ((0.01, "a1"), (0.05, "a5")):
        ev = pd.read_csv(ROOT / "results" / "tables" / f"s6_events_seed42_{tag}.csv")
        tr = ev[ev.triggered]
        E, F, y, t = tr.alarm_E.to_numpy(bool), tr.alarm_F.to_numpy(bool), tr.y.to_numpy(int), tr.time_ms.to_numpy(float)
        both = E & F & (y == 1)
        d = 1800.0 - t[both]
        med = float(np.median(d))
        lo, hi = boot_ci(d, np.median, rng)
        p_a = float((np.array([np.median(d[rng.integers(0, len(d), len(d))]) for _ in range(NB)]) < 800.0).mean())
        add(f"{tag}.n_triggered", int(len(tr)), "events", f"triggered events of the de-duplicated VZCrash test split, target {alpha:.0%}")
        add(f"{tag}.n_crash_both_alarm", int(both.sum()), "events", "triggered crash events that alarm in both the early-exit stage and the full window")
        add(f"{tag}.provisional_ms_median", float(np.median(t[both])), "ms", "median trigger-to-provisional decision time (window length of the early-exit rule)")
        add(f"{tag}.full_ms", 1800.0, "ms", "full-window decision time")
        add(f"{tag}.earlier_ms_median", med, "ms", "median of (1,800 ms minus the provisional decision time); 95% interval in _lo, _hi")
        add(f"{tag}.earlier_ms_median_lo", lo, "ms", "95% bootstrap interval over events, 2,000 resamples, seed 42")
        add(f"{tag}.earlier_ms_median_hi", hi, "ms", "95% bootstrap interval over events")
        add(f"{tag}.earlier_p", p_a, "p", "one-sided bootstrap p of H0: median earlier time below 800 ms")
        # distribution of provisional decision times
        for m in TRUNC:
            add(f"{tag}.share_decided_at_{m}ms", float(np.mean(t[both] == m)), "fraction", "share of the crash events that alarm in both stages and are decided at this checkpoint")
        # retraction
        prov = int(E.sum())
        retr = float((E & ~F).sum() / prov)
        idx = np.arange(len(E))
        bs = []
        for _ in range(NB):
            j = rng.integers(0, len(E), len(E))
            pv = E[j].sum()
            bs.append((E[j] & ~F[j]).sum() / pv if pv else np.nan)
        bs = np.array(bs)
        add(f"{tag}.n_provisional_alarms", prov, "events", "triggered events with a provisional alarm")
        add(f"{tag}.retraction_share", retr, "fraction", "provisional alarms that the full window does not confirm, over provisional alarms")
        add(f"{tag}.retraction_share_lo", float(np.nanquantile(bs, 0.025)), "fraction", "95% bootstrap interval")
        add(f"{tag}.retraction_share_hi", float(np.nanquantile(bs, 0.975)), "fraction", "95% bootstrap interval")
        add(f"{tag}.retraction_p", float(np.nanmean(bs >= 0.20)), "p", "one-sided bootstrap p of H0: retraction share at least 0.20")
        summary[tag] = dict(median_earlier=med, lo=lo, hi=hi, retraction=retr, retr_hi=float(np.nanquantile(bs, 0.975)), n=int(both.sum()), p_a=p_a, p_b=float(np.nanmean(bs >= 0.20)), idx=len(idx))
    a1 = summary["a1"]
    add("hT3a.criterion_met", int(a1["median_earlier"] >= 800.0 and a1["lo"] >= 800.0), "flag", "median earlier time at least 800 ms with lower 95% limit at least 800 ms, 1% target")
    add("hT3a.p", a1["p_a"], "p", "from the bootstrap above")
    add("hT3b.criterion_met", int(a1["retr_hi"] < 0.20), "flag", "upper 95% limit of the retraction share below 0.20, 1% target")
    add("hT3b.p", a1["p_b"], "p", "from the bootstrap above")

    # severity-class agreement on VZCrash crash events (a 1% target, seed 42)
    d = W.load("test", dedup=True)
    pos = {int(e): i for i, e in enumerate(d["event_id"])}
    ev = pd.read_csv(ROOT / "results" / "tables" / "s6_events_seed42_a1.csv")
    sel = ev[ev.triggered & ev.alarm_E & (ev.y == 1)]
    prov_c, full_c, tms = [], [], []
    for eid, tm in zip(sel.event_id, sel.time_ms):
        i = pos.get(int(eid))
        if i is None:
            continue
        n_post = int(round(tm * C.FS_HZ / 1000.0))
        acc, gy = d["acc"][i].astype(np.float64), d["gyro"][i].astype(np.float64)
        prov_c.append(cls_of(acc, gy, n_post))
        full_c.append(cls_of(acc, gy, None))
        tms.append(tm)
    prov_c, full_c, tms = np.array(prov_c), np.array(full_c), np.array(tms)
    agree = (prov_c == full_c).astype(float)
    within1 = (np.abs(prov_c - full_c) <= 1).astype(float)
    add("vz.n_events", int(len(agree)), "events", "triggered crash events with a provisional alarm, VZCrash de-duplicated test split, 1% target, seed 42")
    add("vz.class_agreement", float(agree.mean()), "fraction", "share with the same severity class (0 to 3) from the window truncated at the provisional decision and from the full window")
    lo, hi = boot_ci(agree, np.mean, rng)
    add("vz.class_agreement_lo", lo, "fraction", "95% bootstrap interval over events")
    add("vz.class_agreement_hi", hi, "fraction", "95% bootstrap interval over events")
    add("vz.class_within_one", float(within1.mean()), "fraction", "share within one class")
    for m in TRUNC:
        k = tms == m
        if k.sum() >= 20:
            add(f"vz.class_agreement_at_{m}ms", float(agree[k].mean()), "fraction", f"{int(k.sum())} events decided at {m} ms")
    add("vz.full_class_counts", json.dumps({int(c): int((full_c == c).sum()) for c in range(4)}), "counts", "full-window class of those events (no severity labels exist for VZCrash)")
    add("vz.share_provisional_lower", float((prov_c < full_c).mean()), "fraction", "share whose provisional class is lower than the full class")

    # NHTSA pulses: agreement at each truncation length, and weighted by the VZCrash decision times
    w_t = {m: float(np.mean(tms == m)) for m in TRUNC}
    res = {}
    for side, name in ((False, "frontal"), (True, "side")):
        sel_t = NH.select(side)
        cls_full, cls_tr = [], {m: [] for m in TRUNC}
        for _t, sig in sel_t:
            a, fs = NH.sensor_like(sig["t"], sig["acc"], C.MPU_RANGE_G)
            w, trig = NH._to_window(a, fs)
            cls_full.append(int(S.severity(w, fs, trig)["severity_class"]))
            for m in TRUNC:
                end = trig + int(round(m * fs / 1000.0))
                cls_tr[m].append(int(S.severity(w[:end], fs, trig)["severity_class"]))
        cf = np.array(cls_full)
        add(f"nhtsa.{name}.n_pulses", int(len(cf)), "pulses", f"NHTSA {name} tests (cached selection of nhtsa.py), sensor model 16 g, 100 Hz")
        ag = {}
        for m in TRUNC:
            ag[m] = float((np.array(cls_tr[m]) == cf).mean())
            add(f"nhtsa.{name}.agreement_at_{m}ms", ag[m], "fraction", "share of pulses with the same class from the window truncated at this post-trigger length and from the full window")
        wa = float(sum(w_t[m] * ag[m] for m in TRUNC))
        add(f"nhtsa.{name}.agreement_weighted", wa, "fraction", "agreement weighted by the VZCrash distribution of provisional decision times")
        res[name] = dict(n=len(cf), ag=ag, weighted=wa, full=np.bincount(cf, minlength=4).tolist())
    add("nhtsa.time_to_decision.status", "NOT_RUN", "status", "no early-exit detector is trained on NHTSA pulses; applying the VZCrash-trained forest to them would be a domain transfer that V14 did not preregister", origin="NOT_RUN")
    record_many(ent, purge_prefixes=("r3.t3.",))
    (ROOT / "results" / "tables" / "r3_t3_summary.json").write_text(json.dumps(dict(summary=summary, nhtsa=res, vz=dict(n=int(len(agree)), agree=float(agree.mean()))), indent=1, default=float), encoding="utf-8")
    print(json.dumps(summary, default=float))
    print(res)
    print("vz class agreement", agree.mean(), "within one", within1.mean(), "n", len(agree))


if __name__ == "__main__":
    main()
