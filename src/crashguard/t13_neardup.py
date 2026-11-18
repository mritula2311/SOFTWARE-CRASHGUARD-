"""T13c: near-duplicate NHTSA pulses across the make-and-model splits, and the N14 headline comparison without them (EXPLORATORY, MEASURED_SOFTWARE).

Rule (the T5 rule, fixed before any run): two pulses are near-duplicates if the correlation (per-axis mean removed, axes concatenated) is above 0.999 AND the maximum absolute difference is below
0.01 g, after alignment at the trigger sample. NHTSA records come at their original sample rate, so the comparison is made on the original-rate record, from 0.005 s before (the shortest pre-trigger record allowed) to 0.19 s after the
trigger (the longest span that every one of the 176 records holds), and only between records that have the same sample rate and the same window length. A pair of tests of the same make and model is never a leak for a
make-and-model split (both go to the same side), so the count that matters is pairs that are split across the training and test sides.
The headline comparison (plain, spline, fill, fill + ridge, as in ``saturation_splits``) is re-run with the flagged tests removed from the EVALUATION only; they stay in training.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from crashguard import boot as B
from crashguard import config as C
from crashguard import nhtsa as N
from crashguard import saturation_splits as SPL
from crashguard import severity_study as SS
from crashguard.jp_common import Entries
from crashguard.neardup import CORR_MIN, MAXDIFF_G

PRE_S, POST_S = 0.005, 0.19
SRC = "results/tables/t13_neardup.csv"


def window(sig: dict) -> np.ndarray | None:
    acc, fs0 = np.asarray(sig["acc"], np.float64), float(sig["fs0"])
    i0 = N.trigger_index(acc + np.array([0, 0, N.GRAVITY_Z_G]), fs0)
    if i0 is None:
        return None
    a, b = i0 - int(round(PRE_S * fs0)), i0 + int(round(POST_S * fs0))
    if a < 0 or b > len(acc):
        return None
    return acc[a:b].astype(np.float32)


def pairs(windows: list[np.ndarray | None], fs: list[float]) -> list[tuple[int, int, float, float]]:
    """All pairs (i < j) with the same sample rate and window length that meet both thresholds."""
    out = []
    keyed: dict[tuple, list[int]] = {}
    for i, w in enumerate(windows):
        if w is not None:
            keyed.setdefault((round(fs[i]), w.shape[0]), []).append(i)
    for idx in keyed.values():
        if len(idx) < 2:
            continue
        W = np.stack([windows[i] for i in idx]).astype(np.float64)
        flat = W.reshape(len(idx), -1)
        c = W - W.mean(axis=1, keepdims=True)
        c = c.reshape(len(idx), -1)
        nrm = np.linalg.norm(c, axis=1, keepdims=True)
        u = np.divide(c, nrm, out=np.zeros_like(c), where=nrm > 1e-12)
        corr = u @ u.T
        for a in range(len(idx)):
            for b in range(a + 1, len(idx)):
                if corr[a, b] > CORR_MIN:
                    md = float(np.abs(flat[a] - flat[b]).max())
                    if md < MAXDIFF_G:
                        out.append((idx[a], idx[b], float(corr[a, b]), md))
    return out


def main() -> None:
    from crashguard.t13_heldout import build_set

    C.TABLES.mkdir(parents=True, exist_ok=True)
    old = SS.load_tests()
    new, _cnt = build_set()
    allt = old + new
    meta = SPL.meta_of(old)
    W = [window(t["sig"]) for t in allt]
    fs = [float(t["sig"]["fs0"]) for t in allt]
    n_old = len(old)
    pr = pairs(W, fs)
    E = Entries("t13.neardup", SRC)
    E.add("rule.corr_min", CORR_MIN, "correlation", notes="the T5 rule, applied to original-rate trigger-aligned records (0.005 s before to 0.19 s after the trigger; the shortest record of the 176 holds 0.194 s after its trigger)", origin="ANALYTICAL")
    E.add("rule.maxdiff_g", MAXDIFF_G, "g", origin="ANALYTICAL")
    E.add("records.windowed_176", int(sum(w is not None for w in W[:n_old])), "tests", notes="records long enough for the window and with a trigger")
    mm = [("|".join(t["group"].split("|")[:2])) for t in allt]
    rows = []
    for i, j, c, d in pr:
        rows.append(dict(test_a=allt[i]["test_no"], test_b=allt[j]["test_no"], set_a="176" if i < n_old else "heldout", set_b="176" if j < n_old else "heldout", make_model_a=mm[i], make_model_b=mm[j],
                         same_make_model=mm[i] == mm[j], corr=c, max_diff_g=d))
    P = pd.DataFrame(rows)
    P.to_csv(C.TABLES / "t13_neardup_pairs.csv", index=False)
    inner = [(i, j) for i, j, _c, _d in pr if i < n_old and j < n_old]
    E.add("pairs.within_176.all", len(inner), "pairs")
    E.add("pairs.within_176.cross_make_model", sum(mm[i] != mm[j] for i, j in inner), "pairs", notes="pairs split across make-and-model groups: the ones that can leak")
    E.add("pairs.heldout_vs_176", sum((i < n_old) != (j < n_old) for i, j, _c, _d in pr), "pairs", notes="a held-out pulse (T13a) with a near-identical pulse among the 176")
    E.add("pairs.within_heldout", sum(i >= n_old and j >= n_old for i, j, _c, _d in pr), "pairs")
    dup_cross = np.zeros(n_old, bool)  # tests with a near-duplicate in ANOTHER make-and-model group (among the 176)
    for i, j in inner:
        if mm[i] != mm[j]:
            dup_cross[i] = dup_cross[j] = True
    E.add("tests.with_cross_group_duplicate", int(dup_cross.sum()), "tests", notes="among the 176")
    ref_new = {j for i, j, _c, _d in pr if i < n_old <= j} | {i for i, j, _c, _d in pr if j < n_old <= i}
    E.add("tests.heldout_with_duplicate_in_176", len(ref_new), "tests", notes="of the T13a held-out records")
    # split-level counts: test-fold pulses with a near-duplicate in the training fold
    held = {"A": SPL.split_by(meta, "group_mm"), "G": np.array([t["role"] == "heldout" for t in old]), "O": SPL.split_O(meta)}
    nb = {i: set() for i in range(n_old)}
    for i, j in inner:
        nb[i].add(j)
        nb[j].add(i)
    flagged: dict[str, np.ndarray] = {}
    for sp, h in held.items():
        f = np.array([bool(h[i]) and any(not h[j] and mm[i] != mm[j] for j in nb[i]) for i in range(n_old)]) if sp != "O" else np.array([bool(h[i]) and any(not h[j] for j in nb[i]) for i in range(n_old)])
        flagged[sp] = f
        E.add(f"split.{sp}.n_heldout", int(h.sum()), "tests")
        E.add(f"split.{sp}.heldout_with_train_duplicate", int(f.sum()), "tests", notes="test-side pulses with a near-identical pulse on the training side" + ("; split O does not group by vehicle" if sp == "O" else ""))
    groups = meta.group_mm.to_numpy()
    ug = sorted(set(groups.tolist()))
    counts = []
    for rep in range(SPL.N_REPEATS):
        rng = np.random.default_rng(C.SEED + rep)
        order = list(rng.permutation(len(ug)))
        fold_of = {ug[j]: k % SPL.N_FOLDS for k, j in enumerate(order)}
        fold_t = np.array([fold_of[g] for g in groups])
        cnt = 0
        for i in range(n_old):
            if any(fold_t[j] != fold_t[i] and mm[i] != mm[j] for j in nb[i]):
                cnt += 1
        counts.append(cnt)
    E.add("split.R.tests_with_cross_fold_duplicate_per_repeat_mean", float(np.mean(counts)), "tests", notes=f"over {SPL.N_REPEATS} repeats of grouped 5-fold; each test is in a test fold once per repeat")
    E.add("split.R.tests_with_cross_fold_duplicate_per_repeat_min", int(min(counts)), "tests")
    E.add("split.R.tests_with_cross_fold_duplicate_per_repeat_max", int(max(counts)), "tests")
    # headline comparison without the flagged tests (evaluation only)
    import pickle

    cells = pickle.loads(SPL.CACHE.read_bytes())
    held_G = held["G"]
    combo = SPL.fixed_combo(cells, meta, ~held_G)
    ref = meta.ref.to_numpy()
    for sp in ("A", "G"):
        h = held[sp]
        gcol = meta.group_mm.to_numpy() if sp == "A" else meta.group.to_numpy()
        keep = ~dup_cross[h]
        E.add(f"headline.{sp}.n_all", int(h.sum()), "tests")
        E.add(f"headline.{sp}.n_kept", int(keep.sum()), "tests", notes="held-out tests without a cross-group near-duplicate")
        for rg in SPL.RANGES:
            est, _info = SPL.estimates(cells, meta, ~h, h, rg, combo, leave="test")
            err = {m: SPL.aerr(est[m], ref[h]) for m in SPL.METHODS}
            for m in SPL.METHODS:
                b = SPL.block(err[m][keep], gcol[h][keep])
                for k in ("median", "median_lo", "median_hi", "p90", "w10", "w10_lo", "w10_hi"):
                    E.add(f"headline.{sp}.r{rg:g}.{m}.{k}", round(float(b[k]), 4), "fraction" if k[0] == "w" else "percent")
            for a_, b_ in (("M+", "SP"), ("M+", "B"), ("SP", "B")):
                pd_ = SPL.paired(err[b_][keep], err[a_][keep], gcol[h][keep])
                nm = f"headline.{sp}.r{rg:g}.paired.{a_}_vs_{b_}"
                for k in ("d_median", "d_median_lo", "d_median_hi"):
                    E.add(f"{nm}.{k}", round(float(pd_[k]), 4), "percent", notes="method minus reference, flagged tests removed from evaluation")
                E.add(f"{nm}.clears", int(pd_["clears"]), "flag")
    r, p, cv = SPL.run_cv(cells, meta)
    keep = ~dup_cross
    ge = groups[keep]
    for rg in SPL.RANGES:
        Em = {m: cv["E"][rg][m][:, keep] for m in SPL.METHODS}
        for m in SPL.METHODS:
            e = Em[m]
            pm, lo, hi = B.ci_grouped(e.T, ge, lambda a: float(np.median(a, axis=0).mean()))
            pw = B.ci_grouped(e.T, ge, lambda a: float((a <= SS.TOL10).mean()))
            E.add(f"headline.R.r{rg:g}.{m}.median", round(pm, 4), "percent")
            E.add(f"headline.R.r{rg:g}.{m}.median_lo", round(lo, 4), "percent")
            E.add(f"headline.R.r{rg:g}.{m}.median_hi", round(hi, 4), "percent")
            E.add(f"headline.R.r{rg:g}.{m}.w10", round(pw[0], 4), "fraction")
        for a_, b_ in (("M+", "SP"), ("M+", "B"), ("SP", "B")):
            d = B.paired_diff_grouped(Em[b_].T, Em[a_].T, ge, lambda a: float(np.median(a, axis=0).mean()))
            nm = f"headline.R.r{rg:g}.paired.{a_}_vs_{b_}"
            for k, v in zip(("d_median", "d_median_lo", "d_median_hi"), d):
                E.add(f"{nm}.{k}", round(float(v), 4), "percent")
            E.add(f"{nm}.clears", int(d[2] < 0), "flag")
    E.add("headline.R.n_kept", int(keep.sum()), "tests")
    E.flush()
    pd.DataFrame([dict(item=i["name"], value=i["value"]) for i in E.items]).to_csv(C.TABLES / "t13_neardup.csv", index=False)
    for i in E.items:
        if not i["name"].split(".")[2].startswith("headline") or "paired" in i["name"] and i["name"].endswith("clears"):
            print(i["name"], i["value"])
    print(P.head(20).to_string() if len(P) else "no near-duplicate pairs")


if __name__ == "__main__":
    main()
