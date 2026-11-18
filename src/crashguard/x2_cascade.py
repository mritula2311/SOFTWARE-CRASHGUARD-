"""X2 (docs/02_preregistration/PREREGISTRATION_V3.md): cheap-trigger cascade, trigger stage only, at an equal non-crash trigger rate. MEASURED_SOFTWARE on VZCrash (events were already selected on the device; second-stage trigger).

Relation to N15 (c): that study chose a similar rule by full-system recall; here the rule is chosen by the stated constraint (non-crash trigger rate not above that of the 2 g threshold) on validation, evaluated on
held-out vehicle-size categories, and compared with the 2 g and 1.5 g thresholds. Stage 1 fires at the earliest sample where p >= P OR (j >= J AND e >= Ee), with p = |a| (each axis clipped to +-16 g),
j = jump of |a| per second, e = mean of (|a| - 1)^2 over the last 10 samples. For each event only whether the rule fires anywhere in the 16 s record matters, which depends on max p and on the 24 flags
'some sample has j >= J and e >= Ee'.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from crashguard import boot as B
from crashguard import config as C
from crashguard.detector_extra import frames_full
from crashguard.jp_common import Entries
from crashguard.vz_audit import RAW, _flat

SRC = "results/tables/x2_cascade.csv"
CACHE = C.PROCESSED / "x2_event_feats.parquet"
PS = (1.2, 1.5, 2.0, 2.5, 3.0)
JS = (25.0, 50.0, 100.0, 200.0)
ES = (0.05, 0.1, 0.25, 0.5, 1.0, 2.0)
SIZES = ("Light", "Medium", "Heavy", "Unknown")


def event_features() -> pd.DataFrame:
    if CACHE.exists():
        return pd.read_parquet(CACHE)
    import glob
    from pathlib import Path

    rows = []
    for f in sorted(glob.glob(str(RAW / "*.parquet"))):
        split = Path(f).name.split("-")[0]
        for batch in pq.ParquetFile(f).iter_batches(batch_size=1000, columns=["event_id", "label", "vehiclesize", "gsensor"]):
            ids = batch.column("event_id").to_numpy()
            size = batch.column("vehiclesize").to_pylist()
            lab = batch.column("label").to_numpy()
            go, gflat = _flat(batch.column("gsensor"))
            for k in range(len(ids)):
                g = np.clip(gflat[3 * go[k] : 3 * go[k + 1]].reshape(-1, 3).astype(np.float64), -16, 16)
                p = np.linalg.norm(g, axis=1)
                j = np.abs(np.diff(p, prepend=p[0])) * C.FS_HZ
                d2 = (p - 1.0) ** 2
                e = np.convolve(d2, np.ones(10) / 10.0, mode="full")[: len(d2)]
                r = dict(split=split, event_id=int(ids[k]), label=int(lab[k]), size=size[k], maxp=float(p.max()), raw_peak=float(np.linalg.norm(gflat[3 * go[k] : 3 * go[k + 1]].reshape(-1, 3), axis=1).max()))
                for ji, jv in enumerate(JS):
                    for ei, ev in enumerate(ES):
                        r[f"f{ji}_{ei}"] = bool(((j >= jv) & (e >= ev)).any())
                rows.append(r)
        print(split, f, len(rows), flush=True)
    df = pd.DataFrame(rows)
    C.PROCESSED.mkdir(parents=True, exist_ok=True)
    df.to_parquet(CACHE)
    return df


def fires(df: pd.DataFrame, P: float, J: int | None, Ee: int | None) -> np.ndarray:
    f = df.maxp.to_numpy() >= P
    if J is not None:
        f = f | df[f"f{J}_{Ee}"].to_numpy(bool)
    return f


def candidates() -> list[tuple]:
    out = [(P, None, None) for P in PS]
    out += [(P, ji, ei) for P in PS for ji in range(len(JS)) for ei in range(len(ES))]
    return out


def select(val: pd.DataFrame) -> tuple:
    y = val.label.to_numpy() == 0
    base = fires(val, 2.0, None, None)
    limit = float(base[~y].mean())
    best = None
    for P, ji, ei in candidates():
        f = fires(val, P, ji, ei)
        nc = float(f[~y].mean())
        if nc > limit + 1e-12:
            continue
        key = (round(float(f[y].mean()), 9), ji is None, P)
        if best is None or key > best[0]:
            best = (key, (P, ji, ei))
    return best[1]


def main() -> None:
    df = event_features()
    df = df[df.raw_peak <= 16.0].copy()
    tr, va, te = frames_full()
    flags = pd.read_csv(C.TABLES / "vz_audit_test_near_dup_flags.csv")
    near = set(flags.event_id[flags.flagged_near_duplicate])
    val = df[(df.split == "validation") & df.event_id.isin(va.event_id)].reset_index(drop=True)
    tst = df[(df.split == "test") & df.event_id.isin(te.event_id)].reset_index(drop=True)
    E = Entries("x.x2", SRC)
    E.add("n_validation", int(len(val)), "events")
    E.add("n_test", int(len(tst)), "events")
    sets = {"dedup": np.ones(len(tst), bool), "strict": ~tst.event_id.isin(near).to_numpy()}
    pass_c, pass_2, pass_15 = np.zeros(len(tst), bool), np.zeros(len(tst), bool), np.zeros(len(tst), bool)
    chosen = {}
    for sz in SIZES:
        v_other = val[val["size"] != sz]
        rule = select(v_other)
        chosen[sz] = rule
        m = (tst["size"] == sz).to_numpy()
        sub = tst[m]
        pass_c[m] = fires(sub, *rule)
        pass_2[m] = fires(sub, 2.0, None, None)
        pass_15[m] = fires(sub, 1.5, None, None)
        P, ji, ei = rule
        E.add(f"rule.heldout_{sz}", f"P={P} g, " + ("no jump term" if ji is None else f"J={JS[ji]} g/s, Ee={ES[ei]}"), "text", "selected on the validation events of the other three size categories")
        E.add(f"n_test.{sz}", int(m.sum()), "events")
    crash = tst.label.to_numpy() == 0  # label 0 is crash in VZCrash
    D = list(B._idx(len(tst), B.N_BOOT, B.SEED))
    rows = []
    for sn, mask in sets.items():
        def share(a, idx, mask=mask):
            sel = idx[mask[idx]]
            c = crash[sel]
            return float(a[sel][c].mean()), float(a[sel][~c].mean())

        for nm, a in (("cascade", pass_c), ("t2g", pass_2), ("t1p5g", pass_15)):
            pt = share(a, np.arange(len(tst)))
            d = np.array([share(a, i) for i in D])
            E.ci(f"{sn}.{nm}.crash_pass", (pt[0], float(np.quantile(d[:, 0], 0.025)), float(np.quantile(d[:, 0], 0.975))), "fraction", d=5)
            E.ci(f"{sn}.{nm}.noncrash_rate", (pt[1], float(np.quantile(d[:, 1], 0.025)), float(np.quantile(d[:, 1], 0.975))), "fraction", d=5)
            rows.append(dict(set=sn, trigger=nm, crash_pass=pt[0], noncrash_rate=pt[1]))
        for ref_nm, ref_a in (("t2g", pass_2), ("t1p5g", pass_15)):
            pc, pr = share(pass_c, np.arange(len(tst))), share(ref_a, np.arange(len(tst)))
            dd = np.array([[share(pass_c, i)[0] - share(ref_a, i)[0], share(pass_c, i)[1] - share(ref_a, i)[1]] for i in D])
            for k, nm in enumerate(("crash_pass_gain", "noncrash_rate_diff")):
                pt = (pc[0] - pr[0], pc[1] - pr[1])[k]
                E.ci(f"{sn}.diff_cascade_minus_{ref_nm}.{nm}", (pt, float(np.quantile(dd[:, k], 0.025)), float(np.quantile(dd[:, k], 0.975))), "fraction", d=5)
                if (sn, ref_nm, nm) == ("dedup", "t2g", "crash_pass_gain"):
                    gain, glo = pt, float(np.quantile(dd[:, 0], 0.025))
                    p_raw = float(max(np.mean(dd[:, 0] <= 0.0), 1.0 / (len(dd) + 1)))
                if (sn, ref_nm, nm) == ("dedup", "t2g", "noncrash_rate_diff"):
                    ncd = pt
    ok = gain >= 0.02 and glo > 0 and ncd <= 0.01
    E.add("hX2.gain", round(gain, 5), "fraction", "crash pass share of the cascade minus that of the 2 g threshold, de-duplicated test events")
    E.add("hX2.gain_lo", round(glo, 5), "fraction")
    E.add("hX2.noncrash_rate_diff", round(ncd, 5), "fraction", "non-crash trigger rate of the cascade minus that of the 2 g threshold on the test events")
    E.add("hX2.p_raw", round(p_raw, 4), "probability", "share of resamples with gain at or below 0; floor 0.001")
    E.add("hX2.criterion_met", int(ok), "flag", "gain at least 2 points with the interval above zero, and the cascade's non-crash trigger rate not more than 1 point above that of 2 g")
    E.flush()
    pd.DataFrame(rows).to_csv(C.TABLES / "x2_cascade.csv", index=False)
    print(pd.DataFrame(rows).round(4).to_string())
    print(chosen)
    print("H-X2", gain, glo, ncd, p_raw, ok)


if __name__ == "__main__":
    main()
