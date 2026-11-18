"""S4: N14 and N13, representativeness and the remaining gap (plan and bin edges fixed in docs/02_preregistration/EXPERIMENTS_EXTRA.md before this was run).

1. Severity strata on split R (repeated grouped cross-validation, all 176 tests): bins of reference delta-V and of closing speed; per bin the number of tests, the share where the saturation test
   fires at +-16, +-32 and +-64 g, and the median absolute error of plain, spline, fill, fill + ridge and M+ capped. Intervals (grouped bootstrap over make and model) only for bins with 10 or more tests.
2. Gap to the N13 target: shares within +-10% and +-20% at +-16 g.
3. M+ capped (EXPLORATORY, thought of after seeing the N14 tail result): the predicted log-correction of the ridge is clipped to the 5th to 95th percentile of the realised
   log-correction log(reference / fill estimate) of the saturated tuning tests; fitted on the tuning groups only. Reported on splits O, G, A and R.
Fill + ridge was named primary after earlier results were seen; NHTSA tests are mostly high-speed barrier tests and are not representative of all real crashes.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from crashguard import boot as B
from crashguard import config as C
from crashguard import saturation as SAT
from crashguard import saturation_splits as SP
from crashguard import severity_study as SS

METHODS5 = SP.METHODS + ("M+c",)
NAMES5 = {**SP.NAMES, "M+c": "fill + ridge, capped"}
DV_EDGES = (30.0, 45.0, 60.0)  # reference delta-V, km/h
SPEED_EDGES = (45.0, 60.0)  # closing speed, km/h
MIN_N_INTERVAL = 10
CAP_Q = (0.05, 0.95)
SRC = "results/tables/s4_n14.csv"


def bin_labels(x: np.ndarray, edges: tuple[float, ...]) -> tuple[np.ndarray, list[str]]:
    names = [f"lt{edges[0]:g}"] + [f"{a:g}to{b:g}" for a, b in zip(edges[:-1], edges[1:])] + [f"ge{edges[-1]:g}"]
    return np.digitize(x, edges), names


DIAG: dict = {}  # (split, range) -> [predictions made on saturated test rows, predictions clipped by the cap]


def estimates5(cells: dict, meta: pd.DataFrame, tr: np.ndarray, te: np.ndarray, rg: float, combo: dict, leave: str, tag: str = "") -> dict:
    """The four existing estimates (unchanged) plus M+ capped on the ``te`` rows."""
    est, info = SP.estimates(cells, meta, tr, te, rg, combo, leave)
    fam, sf, rf = combo["M"]
    ref = meta.ref.to_numpy()
    m_all, ap, sh = cells[("m", rg, fam, sf, rf)], cells[("ap", rg, fam, sf, rf)], cells[("sh", rg, fam, sf, rf)]
    b_all, pl = cells[("b", rg, rf)], cells[("pl", rg, rf)]
    use = tr & ap
    est["M+c"] = est["M+"].copy()
    if use.sum() >= 4 and not np.isnan(info["alpha"]):
        X = np.stack([b_all, sh, pl], axis=1)
        y = np.log(ref / np.maximum(m_all, 1e-6))
        corr = SAT.RidgeCorrection(info["alpha"]).fit(X[use], y[use])
        lo, hi = np.quantile(y[use], CAP_Q)
        f = np.ones(int(te.sum()))
        a_te = ap[te]
        if a_te.any():
            pred = corr.predict(X[te][a_te])
            d = DIAG.setdefault((tag, rg), [0, 0])
            d[0] += int(a_te.sum())
            d[1] += int(((pred < lo) | (pred > hi)).sum())
            f[a_te] = np.exp(np.clip(pred, lo, hi))
        est["M+c"] = est["M"] * f
    return est


def run_fixed5(cells, meta, held, combo, split):
    rows, prow = [], []
    ref = meta.ref.to_numpy()
    tr, te = ~held, held
    gcol = meta.group_mm.to_numpy() if split == "A" else meta.group.to_numpy()
    for rg in SP.RANGES:
        est = estimates5(cells, meta, tr, te, rg, combo, "test", split)
        E = {m: SP.aerr(est[m], ref[te]) for m in METHODS5}
        for m in METHODS5:
            rows.append(dict(split=split, range_g=rg, method=m, **SP.block(E[m], gcol[te])))
        for a_, b_ in SP.PAIRS + (("M+c", "M+"),):
            prow.append(dict(split=split, range_g=rg, method=a_, reference=b_, **SP.paired(E[b_], E[a_], gcol[te]),
                             d_p90=B.paired_diff_grouped(E[b_], E[a_], gcol[te], B.p90)[0], d_p90_lo=B.paired_diff_grouped(E[b_], E[a_], gcol[te], B.p90)[1],
                             d_p90_hi=B.paired_diff_grouped(E[b_], E[a_], gcol[te], B.p90)[2]))
    return rows, prow


def run_cv5(cells, meta):
    n = len(meta)
    ref = meta.ref.to_numpy()
    groups = meta.group_mm.to_numpy()
    ug = sorted(set(groups.tolist()))
    E = {rg: {m: np.zeros((SP.N_REPEATS, n)) for m in METHODS5} for rg in SP.RANGES}
    for rep in range(SP.N_REPEATS):
        rng = np.random.default_rng(C.SEED + rep)
        order = list(rng.permutation(len(ug)))
        fold_of = {ug[j]: k % SP.N_FOLDS for k, j in enumerate(order)}
        fold = np.array([fold_of[g] for g in groups])
        for f in range(SP.N_FOLDS):
            te, tr = fold == f, fold != f
            combo = SP.choose_combo(cells, meta, tr)
            for rg in SP.RANGES:
                est = estimates5(cells, meta, tr, te, rg, combo, "group", "R")
                for m in METHODS5:
                    E[rg][m][rep, te] = SP.aerr(est[m], ref[te])
    stat = {"median": lambda a: float(np.median(a, axis=0).mean()), "p90": lambda a: float(np.quantile(a, 0.9, axis=0).mean()),
            "w10": lambda a: float((a <= SS.TOL10).mean()), "w20": lambda a: float((a <= SS.TOL20).mean())}
    rows, prow = [], []
    for rg in SP.RANGES:
        for m in METHODS5:
            row = dict(split="R", range_g=rg, method=m, n=n, n_groups=len(ug))
            for k, f in stat.items():
                p, lo, hi = B.ci_grouped(E[rg][m].T, groups, f)
                row[k], row[k + "_lo"], row[k + "_hi"] = p, lo, hi
            rows.append(row)
        for a_, b_ in SP.PAIRS + (("M+c", "M+"),):
            ea, eb = E[rg][b_].T, E[rg][a_].T
            m_ = B.paired_diff_grouped(ea, eb, groups, stat["median"])
            w_ = B.paired_diff_grouped((ea <= SS.TOL10).astype(float), (eb <= SS.TOL10).astype(float), groups, stat["w10"])
            p_ = B.paired_diff_grouped(ea, eb, groups, stat["p90"])
            prow.append(dict(split="R", range_g=rg, method=a_, reference=b_, d_median=m_[0], d_median_lo=m_[1], d_median_hi=m_[2], d_w10=w_[0], d_w10_lo=w_[1], d_w10_hi=w_[2],
                             d_p90=p_[0], d_p90_lo=p_[1], d_p90_hi=p_[2], clears=bool(m_[2] < 0)))
    return rows, prow, E


def strata(E, cells, meta, combo_final) -> list[dict]:
    """Per bin on split R: n, saturation-test share per range, median and within-10% share per method, intervals for bins with >= MIN_N_INTERVAL tests."""
    groups = meta.group_mm.to_numpy()
    out = []
    fam, sf, rf = combo_final["M"]
    for scheme, x, edges in (("dv", meta.ref.to_numpy(), DV_EDGES), ("speed", meta.v.to_numpy(), SPEED_EDGES)):
        idx, names = bin_labels(x, edges)
        for b, nm in enumerate(names):
            mask = idx == b
            n = int(mask.sum())
            row = dict(scheme=scheme, bin=nm, n=n, n_groups=int(len(set(groups[mask].tolist()))))
            for rg in SP.RANGES:
                row[f"sat{rg:g}"] = float(cells[("ap", rg, fam, sf, rf)][mask].mean()) if n else float("nan")
                for m in METHODS5:
                    e = E[rg][m][:, mask].T if n else np.zeros((0, SP.N_REPEATS))
                    med = float(np.median(e, axis=0).mean()) if n else float("nan")
                    row[f"r{rg:g}.{m}.median"] = med
                    row[f"r{rg:g}.{m}.w10"] = float((e <= SS.TOL10).mean()) if n else float("nan")
                    if n >= MIN_N_INTERVAL:
                        _p, lo, hi = B.ci_grouped(e, groups[mask], lambda a: float(np.median(a, axis=0).mean()))
                        row[f"r{rg:g}.{m}.median_lo"], row[f"r{rg:g}.{m}.median_hi"] = lo, hi
            out.append(row)
    return out


def main() -> None:
    from crashguard.results import record_many

    C.TABLES.mkdir(parents=True, exist_ok=True)
    tests = SS.load_tests()
    meta = SP.meta_of(tests)
    cells = SP.build_cells(tests)
    held_G = np.array([t["role"] == "heldout" for t in tests])
    held_O, held_A = SP.split_O(meta), SP.split_by(meta, "group_mm")
    combo = SP.fixed_combo(cells, meta, ~held_G)
    ent: list[dict] = []

    def add(name, value, unit, notes="", origin="MEASURED_SOFTWARE"):
        ent.append(dict(name=f"n14s.{name}", value=value, unit=unit, origin=origin, source_file=SRC, notes=notes))

    rows, prow = [], []
    for sp, held in (("O", held_O), ("G", held_G), ("A", held_A)):
        r, p = run_fixed5(cells, meta, held, combo, sp)
        rows += r
        prow += p
    r, p, E = run_cv5(cells, meta)
    rows += r
    prow += p
    M, P = pd.DataFrame(rows), pd.DataFrame(prow)
    M.to_csv(C.TABLES / "s4_n14_metrics.csv", index=False)
    P.to_csv(C.TABLES / "s4_n14_paired.csv", index=False)

    # check: the four existing methods reproduce the stored n14x numbers
    import json
    stored = {e["name"]: e["value"] for e in json.loads(C.RESULTS.read_text(encoding="utf-8"))} if hasattr(C, "RESULTS") else {}
    if not stored:
        stored = {e["name"]: e["value"] for e in json.loads(open("results/results.json", encoding="utf-8").read())}
    mism = 0
    for r_ in M.itertuples():
        if r_.method in SP.METHODS:
            k = f"n14x.{r_.split}.r{r_.range_g:g}.{r_.method}.median"
            if k in stored and abs(float(stored[k]) - round(float(r_.median), 4)) > 1e-3:
                mism += 1
    add("check.mismatch_with_n14x_medians", mism, "cells", "the four existing methods re-run here against the stored n14x medians; 0 = identical")

    for r_ in M.itertuples():
        for k in ("median", "median_lo", "median_hi", "p90", "p90_lo", "p90_hi", "w10", "w10_lo", "w10_hi", "w20", "w20_lo", "w20_hi"):
            v = getattr(r_, k)
            add(f"cap.{r_.split}.r{r_.range_g:g}.{r_.method}.{k}", round(float(v), 4), "fraction" if k.startswith(("w10", "w20")) else "percent",
                "all five methods; M+c = M+ capped (exploratory)" if k == "median" else "")
    for r_ in P[P.method == "M+c"].itertuples():
        nm = f"cap.{r_.split}.r{r_.range_g:g}.paired.Mpc_vs_Mp"
        for k in ("d_median", "d_median_lo", "d_median_hi", "d_p90", "d_p90_lo", "d_p90_hi", "d_w10", "d_w10_lo", "d_w10_hi"):
            add(f"{nm}.{k}", round(float(getattr(r_, k)), 4), "fraction" if "w10" in k else "percent", "M+ capped minus M+; negative = capped is better; groups resampled")
        add(f"{nm}.tail_improves", int(r_.d_p90_hi < 0), "flag", "1 = the whole interval of the 90th-percentile difference is below zero")
        add(f"{nm}.median_changes", int(r_.d_median_hi < 0 or r_.d_median_lo > 0), "flag", "1 = the interval of the median difference excludes zero")

    for (sp_, rg_), (n_app, n_clip) in DIAG.items():
        add(f"cap.{sp_}.r{rg_:g}.n_predictions_on_saturated_tests", n_app, "count", "ridge corrections predicted for saturated test rows (split R: summed over 10 repeats)")
        add(f"cap.{sp_}.r{rg_:g}.n_predictions_clipped", n_clip, "count", "of those, how many the 5th to 95th percentile cap changed")
    fam_sat = SP.FINAL_FAMILY, SP.FINAL_SAT
    S_ = strata(E, cells, meta, combo)
    pd.DataFrame(S_).to_csv(C.TABLES / "s4_strata.csv", index=False)
    for row in S_:
        base = f"strata.{row['scheme']}.{row['bin']}"
        add(f"{base}.n", row["n"], "tests", "tests in the bin")
        add(f"{base}.n_groups", row["n_groups"], "groups", "make and model groups in the bin")
        for rg in SP.RANGES:
            add(f"{base}.sat{rg:g}", round(row[f"sat{rg:g}"], 4), "fraction", f"share of tests where the saturation test fires at +-{rg:g} g ({fam_sat[0]} pulse, level {fam_sat[1]})")
            for m in METHODS5:
                add(f"{base}.r{rg:g}.{m}.median", round(row[f"r{rg:g}.{m}.median"], 3), "percent", "split R: mean over repeats of the median absolute delta-V error of the tests in the bin")
                add(f"{base}.r{rg:g}.{m}.w10", round(row[f"r{rg:g}.{m}.w10"], 4), "fraction", "share within 10% (split R)")
                if f"r{rg:g}.{m}.median_lo" in row:
                    add(f"{base}.r{rg:g}.{m}.median_lo", round(row[f"r{rg:g}.{m}.median_lo"], 3), "percent", "95% interval, make and model groups resampled (bins with 10 or more tests only)")
                    add(f"{base}.r{rg:g}.{m}.median_hi", round(row[f"r{rg:g}.{m}.median_hi"], 3), "percent", "95% interval, make and model groups resampled (bins with 10 or more tests only)")
    add("strata.dv_edges_kmh", ",".join(f"{x:g}" for x in DV_EDGES), "text", "reference delta-V bin edges, fixed before the run")
    add("strata.speed_edges_kmh", ",".join(f"{x:g}" for x in SPEED_EDGES), "text", "closing-speed bin edges, fixed before the run")
    add("gap.target_within10", 0.8, "fraction", "the N13 target: 80% of tests within +-10%", origin="ANALYTICAL")
    pd.set_option("display.width", 250)
    print("mismatch with stored n14x medians:", mism)
    print("cap diagnostics (applied, clipped):", {f"{k[0]}{k[1]:g}": v for k, v in DIAG.items()})
    print(M[M.range_g == 16][["split", "method", "median", "median_lo", "median_hi", "p90", "w10", "w20"]].round(3).to_string())
    print(P[(P.method == "M+c")][["split", "range_g", "d_median", "d_median_lo", "d_median_hi", "d_p90", "d_p90_lo", "d_p90_hi"]].round(3).to_string())
    print(pd.DataFrame(S_)[["scheme", "bin", "n", "sat16", "sat32", "sat64", "r16.B.median", "r16.SP.median", "r16.M.median", "r16.M+.median", "r16.M+c.median"]].round(2).to_string())
    record_many(ent, purge_prefixes=("n14s.",))


if __name__ == "__main__":
    main()
