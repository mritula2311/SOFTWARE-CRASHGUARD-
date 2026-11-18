"""S2 (H-S1 and H-S2): the repository's trigger and impact-side rules on the simulated hardware-format variants (SIMULATED_HW_FORMAT).

Design and criteria: docs/02_preregistration/PREREGISTRATION_V11.md sections 2.2, 2.3 and 3 (committed before this ran). The base variant is correct by construction; the result that
matters is the failure map. Nothing here is hardware evidence. Keys ``sh.s2.*``.

    python -m crashguard.sh_s2
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.stats import binom

from crashguard import config as C
from crashguard import features as FEAT
from crashguard import hwsim_v2 as H
from crashguard import sh_events as E
from crashguard.results import record_many

SRC = "src/crashguard/sh_s2.py"
SENSOR_VARIANTS = [n for _i, n, _p, k in H.VARIANTS if "sensor" in k]
FAMILIES = {  # fault family -> ordered variants from no fault to the largest fault
    "tilt about x": ["V00_base", "T_x15", "T_x30"], "tilt about y": ["V00_base", "T_y15", "T_y30"], "axis sign flip x": ["V00_base", "F_x"], "axis sign flip y": ["V00_base", "F_y"],
    "sampling rate": ["V00_base", "S_10Hz"], "timestamp jitter": ["V00_base", "S_jit1"], "dropped samples": ["V00_base", "S_drop05"], "noise": ["V00_base", "N_x2", "N_x4"],
    "bias": ["V00_base", "B_08"], "crash peak (decreasing)": ["P_8", "V00_base", "P_3"],
}
SWEEP = (1.5, 2.0, 2.5, 3.0)
N_BOOT, SEED = 2000, C.SEED


def evaluate(events: list[dict], signs, thr: float = C.TRIGGER_G) -> pd.DataFrame:
    rows = []
    for e in events:
        i0 = E.trigger_index(e, thr)
        pred = None
        if i0 is not None and e["label"] == "crash":
            pred = E.side_rule(e, i0, signs)[0]
        rows.append(dict(name=e["name"], label=e["label"], side=e["side"], kind=e["kind"], triggered=i0 is not None, pred=pred))
    return pd.DataFrame(rows)


def boot_ci(x: np.ndarray, rng) -> tuple[float, float]:
    x = np.asarray(x, float)
    if len(x) == 0:
        return float("nan"), float("nan")
    d = x[rng.integers(0, len(x), (N_BOOT, len(x)))].mean(axis=1)
    return float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975))


def metrics(df: pd.DataFrame, rng) -> dict:
    hz = df[(df.label == "crash") & df.side.isin(E.HORIZONTAL)]
    acc_all = (hz.pred == hz.side).to_numpy()
    cr = df[df.label == "crash"]
    nc = df[df.label == "non_crash"]
    m = dict(n_horizontal=len(hz), side_correct=int(acc_all.sum()), side_acc=float(acc_all.mean()), n_triggered_horizontal=int(hz.triggered.sum()),
             side_acc_triggered=float((hz[hz.triggered].pred == hz[hz.triggered].side).mean()) if hz.triggered.any() else float("nan"),
             n_crash=len(cr), recall=float(cr.triggered.mean()), recall_hits=int(cr.triggered.sum()), n_noncrash=len(nc), far=float(nc.triggered.mean()), far_hits=int(nc.triggered.sum()))
    m["side_acc_lo"], m["side_acc_hi"] = boot_ci(acc_all.astype(float), rng)
    m["recall_lo"], m["recall_hi"] = boot_ci(cr.triggered.to_numpy(float), rng)
    m["far_lo"], m["far_hi"] = boot_ci(nc.triggered.to_numpy(float), rng)
    m["p_side"] = float(binom.sf(m["side_correct"] - 1, m["n_horizontal"], 0.90))  # P(X >= x; n, 0.90)
    p_rec = float(binom.sf(m["recall_hits"] - 1, m["n_crash"], 0.90))
    p_far = float(binom.cdf(m["far_hits"], m["n_noncrash"], 0.10))  # P(X <= x; n, 0.10)
    m["p_detect"] = max(p_rec, p_far)
    m["pass_side"] = int(m["side_acc"] >= 0.90)
    m["pass_detect"] = int(m["recall"] >= 0.90 and m["far"] <= 0.10)
    for side in E.HORIZONTAL:
        h = hz[hz.side == side]
        m[f"acc_{side}"] = float((h.pred == side).mean())
    v = df[(df.label == "crash") & (df.side == "vertical")]
    m["vertical_triggered"] = float(v.triggered.mean()) if len(v) else float("nan")
    return m


def confusion(df: pd.DataFrame) -> dict:
    hz = df[(df.label == "crash") & df.side.isin(E.HORIZONTAL)]
    out = {}
    for side in E.HORIZONTAL:
        h = hz[hz.side == side]
        out[side] = {p: int((h.pred == p).sum()) for p in E.HORIZONTAL}
        out[side]["no_trigger"] = int((~h.triggered).sum())
    return out


def transfer(events: list[dict], bundle) -> dict:
    """Secondary: the 15-tree forest trained on VZCrash windows applied to the bench windows (trigger at 2 g, resampled to 100 Hz). Tests plumbing and scale, not real transfer."""
    model, thr = bundle["model"], float(bundle["thr_f1"])
    res = []
    for e in events:
        i0 = E.trigger_index(e)
        if i0 is None:
            res.append((e["label"], False, np.nan))
            continue
        a, g = E.resample_window(e)
        tr = int(round(e["t"][i0] / 10.0))
        s = tr - C.PRE_N
        idx = np.clip(np.arange(s, s + C.WIN_N), 0, len(a) - 1)
        f = FEAT.compute_features(a[idx][None], g[idx][None])
        p = float(model.predict_proba(f)[0, 1])
        res.append((e["label"], p >= thr, p))
    d = pd.DataFrame(res, columns=["label", "alarm", "p"])
    return dict(recall=float(d[d.label == "crash"].alarm.mean()), far=float(d[d.label == "non_crash"].alarm.mean()), n_crash=int((d.label == "crash").sum()), n_noncrash=int((d.label == "non_crash").sum()))


def main() -> None:
    signs = E.calibration_signs()
    rng = np.random.default_rng(SEED)
    bundle = joblib.load(C.PROCESSED / "rf15_seed42.joblib")
    sets = {"supplied": (E.load_dir(E.SUPPLIED), False)}
    for n in SENSOR_VARIANTS:
        sets[n] = (E.load_dir(E.VARIANT_ROOT / n, relaxed=True), True)
    ent: list[dict] = []
    table = []
    conf = {}

    def add(name, value, unit, notes=""):
        ent.append(dict(name=f"sh.s2.{name}", value=value, unit=unit, origin="SIMULATED_HW_FORMAT", source_file=SRC, notes=notes))

    for name, (events, _rel) in sets.items():
        df = evaluate(events, signs)
        m = metrics(df, rng)
        conf[name] = confusion(df)
        tr = transfer(events, bundle)
        sweep = {}
        for thr in SWEEP:
            d2 = evaluate(events, signs, thr)
            sweep[thr] = (float(d2[d2.label == "crash"].triggered.mean()), float(d2[d2.label == "non_crash"].triggered.mean()))
        table.append(dict(variant=name, **m, transfer_recall=tr["recall"], transfer_far=tr["far"], **{f"recall_{t:g}g": v[0] for t, v in sweep.items()}, **{f"far_{t:g}g": v[1] for t, v in sweep.items()}))
        for k, v in m.items():
            add(f"{name}.{k}", round(v, 5) if isinstance(v, float) else v, "fraction" if isinstance(v, float) else "count", "bootstrap interval: 2,000 resamples of events, seed 42" if k.endswith(("_lo", "_hi")) else "")
        add(f"{name}.transfer.recall", round(tr["recall"], 5), "fraction", "SECONDARY: forest rf15 (VZCrash-trained, validation F1 threshold) on bench windows, plumbing check only")
        add(f"{name}.transfer.far", round(tr["far"], 5), "fraction", "SECONDARY: see transfer.recall")
        for t, v in sweep.items():
            add(f"{name}.sweep.recall_{t:g}g", round(v[0], 5), "fraction", "trigger sweep, secondary")
            add(f"{name}.sweep.far_{t:g}g", round(v[1], 5), "fraction", "trigger sweep, secondary")
    T = pd.DataFrame(table)
    Path("results/tables").mkdir(parents=True, exist_ok=True)
    T.to_csv("results/tables/sh_s2_variants.csv", index=False)
    json.dump(conf, open("results/tables/sh_s2_confusion.json", "w"), indent=1)
    # failure map per fault family
    byv = T.set_index("variant")
    fmap = {}
    for fam, order in FAMILIES.items():
        row = {}
        for label, col, ok in (("side accuracy below 0.90", "side_acc", lambda v: v >= 0.90), ("crash recall below 0.90", "recall", lambda v: v >= 0.90), ("non-crash false-alarm rate above 0.10", "far", lambda v: v <= 0.10)):
            first_bad = next((v for v in order if not ok(byv.loc[v, col])), None)
            row[label] = first_bad
        fmap[fam] = row
        for lab, v in row.items():
            add(f"failure_map.{fam.replace(' ', '_')}.{lab.replace(' ', '_')}", v if v is not None else "none in the grid", "variant", "smallest fault of this family, in the preregistered order, at which the criterion fails")
    # hypotheses: all sensor variants plus the supplied set
    allv = T
    h1 = bool((allv.side_acc >= 0.90).all())
    p1 = float(allv.p_side.max())
    h2 = bool(((allv.recall >= 0.90) & (allv.far <= 0.10)).all())
    p2 = float(allv.p_detect.max())
    add("hS1.criterion_met", int(h1), "flag", "side accuracy >= 0.90 in every sensor variant and in the supplied set")
    add("hS1.p_raw", round(p1, 6), "p", "largest exact one-sided binomial p over variants (intersection-union)")
    add("hS1.n_variants_below_0.90", int((allv.side_acc < 0.90).sum()), "count", "of the 15 sensor variants plus the supplied set")
    add("hS2.criterion_met", int(h2), "flag", "crash recall >= 0.90 and non-crash false-alarm rate <= 0.10 in every sensor variant")
    add("hS2.p_raw", round(p2, 6), "p", "largest over variants of the larger of the two exact one-sided binomial p-values")
    add("hS2.n_variants_recall_ok", int((allv.recall >= 0.90).sum()), "count", "variants (of 16 including the supplied set) with crash recall >= 0.90")
    add("hS2.n_variants_far_ok", int((allv.far <= 0.10).sum()), "count", "variants (of 16 including the supplied set) with false-alarm rate <= 0.10")
    record_many(ent, purge_prefixes=("sh.s2.",))
    print(T[["variant", "side_acc", "recall", "far", "transfer_recall", "transfer_far"]].round(3).to_string())
    print(fmap)
    print("hS1", h1, p1, "hS2", h2, p2)


if __name__ == "__main__":
    main()
