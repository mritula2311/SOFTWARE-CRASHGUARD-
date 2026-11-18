"""Sensor-error robustness of the detectors (SIMULATED: the perturbations are ours, the events are VZCrash).

Every perturbation is applied to the raw accelerometer (and, for misalignment, gyro) signal of every de-duplicated test event BEFORE the sensor
clip, the trigger and the window, so the trigger rate changes too. The models are the ones trained on the unperturbed training split (seed 42);
thresholds come from the unperturbed validation split. Reported per model: model-level AP (triggered events), system recall, system false-alarm rate
and the trigger rate, with a paired bootstrap interval for the change in recall and false-alarm rate.

Perturbations (all ours, not measured on a car): gain error +-5% and +-10%; constant offset 0.5 g on one axis (x, y, z, and -z) and 0.25 g on all axes
(the car's resting reading showed 0.5 g); axis misalignment +-5, +-10 and +-20 degrees about each axis (acceleration and gyro rotated together);
added Gaussian noise of 0.02, 0.05 and 0.10 g rms per axis; a 50 Hz down-sampling (every second sample kept, linearly interpolated back to 100 Hz).
"""
from __future__ import annotations


import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

from crashguard import boot as B
from crashguard import config as C
from crashguard import detector_extra as D
from crashguard.data import iter_events
from crashguard.features import _align_gyro, _cut, compute_features
from crashguard.models import op_thresholds

MODELS = ("rf15", D.SEL, "rule")
SRC = "results/tables/robustness_sensor_errors.csv"


def _rot(axis: int, deg: float) -> np.ndarray:
    c, s = np.cos(np.radians(deg)), np.sin(np.radians(deg))
    i, j = [k for k in range(3) if k != axis]
    r = np.eye(3)
    r[i, i], r[i, j], r[j, i], r[j, j] = c, -s, s, c
    return r


def perturbations() -> dict[str, dict]:
    p: dict[str, dict] = {"baseline": dict(kind="baseline")}
    for g in (-0.10, -0.05, 0.05, 0.10):
        p[f"gain_{g:+.2f}"] = dict(kind="gain", g=g)
    for nm, vec in (("x+0.5g", (0.5, 0, 0)), ("y+0.5g", (0, 0.5, 0)), ("z+0.5g", (0, 0, 0.5)), ("z-0.5g", (0, 0, -0.5)), ("all+0.25g", (0.25, 0.25, 0.25))):
        p[f"offset_{nm}"] = dict(kind="offset", v=np.array(vec, float))
    for ax, an in enumerate("xyz"):
        for d in (-20, -10, -5, 5, 10, 20):
            p[f"misalign_{an}{d:+d}deg"] = dict(kind="rot", r=_rot(ax, d))
    for s in (0.02, 0.05, 0.10):
        p[f"noise_{s:.2f}g"] = dict(kind="noise", s=s)
    p["downsample_50Hz"] = dict(kind="ds")
    return p


def family(name: str) -> str:
    return name.split("_")[0]


def apply(pert: dict, acc: np.ndarray, gyro: np.ndarray, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    k = pert["kind"]
    if k == "gain":
        return acc * (1 + pert["g"]), gyro
    if k == "offset":
        return acc + pert["v"], gyro
    if k == "rot":
        return acc @ pert["r"].T, (gyro @ pert["r"].T if len(gyro) else gyro)
    if k == "noise":
        return acc + rng.normal(0.0, pert["s"], acc.shape), gyro
    if k == "ds":
        n = len(acc)
        idx = np.arange(0, n, 2)
        return np.stack([np.interp(np.arange(n), idx, acc[idx, a]) for a in range(3)], axis=1), gyro
    return acc, gyro


def load_events(ids: set[int]) -> list[tuple]:
    out = []
    for path in sorted((C.RAW_DIR / "data").glob("test-*.parquet")):
        for _split, eid, _label, _vs, _hd, acc, gyro, _gps in iter_events(path):
            if eid in ids:
                out.append((eid, acc.astype(np.float32), gyro.astype(np.float32)))
    return out


def windows_for(events: list[tuple], pert: dict, seed: int = C.SEED) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Firmware-style windows after the perturbation: (accelerometer windows, gyro windows, triggered mask). Windows exist only for triggered events."""
    wa, wg = [], []
    trig = np.zeros(len(events), bool)
    for i, (_eid, acc, gyro) in enumerate(events):
        a, g = apply(pert, acc.astype(np.float64), gyro.astype(np.float64), np.random.default_rng(seed * 1_000_003 + i))
        n = len(a)
        a = np.clip(a, -C.MPU_RANGE_G, C.MPU_RANGE_G)
        gg = np.clip(_align_gyro(g, n), -C.MPU_GYRO_RANGE_DPS, C.MPU_GYRO_RANGE_DPS)
        hit = np.flatnonzero(np.linalg.norm(a, axis=1) > C.TRIGGER_G)
        if len(hit):
            s = int(hit[0]) - C.PRE_N
            wa.append(_cut(a, s, C.WIN_N))
            wg.append(_cut(gg, s, C.WIN_N))
            trig[i] = True
    empty = np.zeros((0, C.WIN_N, 3))
    return (np.stack(wa) if wa else empty), (np.stack(wg) if wg else empty), trig


def features_for(events: list[tuple], pert: dict, seed: int = C.SEED) -> pd.DataFrame:
    """Window features of every event after the perturbation: columns event_id, triggered and the 14 features."""
    wa, wg, trig = windows_for(events, pert, seed)
    df = pd.DataFrame({"event_id": [e[0] for e in events], "triggered": trig})
    if len(wa):
        f = pd.DataFrame(compute_features(wa, wg), columns=list(C.FEATURES))
        f.index = df.index[trig]
        df = df.join(f)
    for c in C.FEATURES:
        if c not in df:
            df[c] = np.nan
    return df


def run(seed: int = C.SEED) -> tuple[pd.DataFrame, dict]:
    tr, va, te = D.frames_full()
    va_trig = va[va.triggered]
    events = load_events(set(te.event_id))
    order = {e[0]: i for i, e in enumerate(events)}
    te = te[te.event_id.isin(order)].copy()
    te["_o"] = te.event_id.map(order)
    te = te.sort_values("_o").reset_index(drop=True)
    events = [events[order[e]] for e in te.event_id]  # same order as te
    y, lab = te.y.to_numpy(), te.label.to_numpy()
    fitted = {}
    for m in MODELS:
        scorer, _ = D.fit(m, seed, tr, va_trig)
        thr, _ = op_thresholds(va_trig.y.to_numpy(), scorer(va_trig))
        fitted[m] = (scorer, thr)
    rows, base_pred = [], {}
    chk: dict = {}
    for name, pert in perturbations().items():
        f = features_for(events, pert, seed)
        f["y"] = y
        f["label"] = lab
        trig = f.triggered.to_numpy(bool)
        if name == "baseline":  # check against the pipeline's own features
            both = f[trig].merge(te[["event_id"] + list(C.FEATURES)], on="event_id", suffixes=("", "_ref"))
            chk = dict(n_match=int(len(both)), max_abs_diff=float(max(np.abs(both[c] - both[c + "_ref"]).max() for c in C.FEATURES)), trigger_equal=bool((trig == te.triggered.to_numpy(bool)).all()))
        for m, (scorer, thr) in fitted.items():
            s = np.full(len(f), -1.0)
            if trig.any():
                s[trig] = scorer(f[trig])
            pred = (s >= thr).astype(int)
            rec = float(pred[y == 1].mean())
            fpr = float(pred[y == 0].mean())
            ap = float(average_precision_score(y[trig], s[trig])) if trig.any() else float("nan")
            row = dict(perturbation=name, family=family(name), model=m, trigger_rate=float(trig.mean()), ap=ap, sys_recall=rec, sys_fpr=fpr, n=len(f))
            if name == "baseline":
                base_pred[m] = pred
            else:
                dr = B.paired_diff(base_pred[m][y == 1].astype(float), pred[y == 1].astype(float), np.mean)
                df_ = B.paired_diff(base_pred[m][y == 0].astype(float), pred[y == 0].astype(float), np.mean)
                row.update(d_recall=dr[0], d_recall_lo=dr[1], d_recall_hi=dr[2], d_fpr=df_[0], d_fpr_lo=df_[1], d_fpr_hi=df_[2])
            rows.append(row)
        print(name, {m: round(r["sys_recall"], 3) for m in MODELS for r in rows[-3:] if r["model"] == m}, flush=True)
    out = pd.DataFrame(rows)
    base = out[out.perturbation == "baseline"].set_index("model")
    out["d_ap"] = out.apply(lambda r: r.ap - base.loc[r.model, "ap"], axis=1)
    return out, chk


def figure(df: pd.DataFrame) -> None:
    import matplotlib.pyplot as plt

    from crashguard.plots import COLORS, save, style

    style()
    d = df[df.perturbation != "baseline"]
    names = list(dict.fromkeys(d.perturbation))
    fig, axes = plt.subplots(1, 2, figsize=(13, 7.5), sharey=True)
    for ax, col, lab in ((axes[0], "d_recall", "Change in system recall (absolute)"), (axes[1], "d_fpr", "Change in system false-alarm rate (absolute)")):
        for i, m in enumerate(MODELS):
            g = d[d.model == m].set_index("perturbation").reindex(names)
            ax.scatter(g[col], np.arange(len(names)) + (i - 1) * 0.2, s=14, color=COLORS[i], label=D.NAMES[m])
        ax.axvline(0, color="gray", lw=0.8)
        ax.set_xlabel(lab)
    axes[0].set_yticks(range(len(names)), names, fontsize=6)
    axes[0].legend(fontsize=7)
    fig.suptitle("Sensor-error robustness (SIMULATED perturbations on VZCrash de-duplicated test events)", fontsize=9)
    save(fig, "robustness_sensor_errors")


def main() -> None:
    from crashguard.results import record_many

    C.TABLES.mkdir(parents=True, exist_ok=True)
    df, chk = run()
    df.to_csv(C.TABLES / "robustness_sensor_errors.csv", index=False)
    ent = [dict(name="robust.check.baseline_trigger_equal", value=int(chk["trigger_equal"]), unit="flag", origin="MEASURED_SOFTWARE", source_file=SRC,
                notes="the unperturbed re-processing triggers on the same events as the main pipeline"),
           dict(name="robust.check.baseline_max_abs_feature_diff", value=chk["max_abs_diff"], unit="feature units", origin="MEASURED_SOFTWARE", source_file=SRC,
                notes=f"unperturbed re-processing against the main pipeline's features on {chk['n_match']} triggered events")]
    for r in df.itertuples():
        base = f"robust.{r.perturbation}.{r.model}"
        for k in ("ap", "sys_recall", "sys_fpr", "trigger_rate", "d_ap", "d_recall", "d_recall_lo", "d_recall_hi", "d_fpr", "d_fpr_lo", "d_fpr_hi"):
            v = getattr(r, k)
            if isinstance(v, float) and np.isnan(v):
                continue
            ent.append(dict(name=f"{base}.{k}", value=round(float(v), 5), unit="fraction", origin="SIMULATED", source_file=SRC,
                            notes="perturbation chosen by us; VZCrash de-duplicated test events; seed 42 models; thresholds from the unperturbed validation split"))
    record_many(ent, purge_prefixes=("robust.",))
    figure(df)


if __name__ == "__main__":
    main()
