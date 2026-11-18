"""N14 extension (docs/02_preregistration/ALGORITHMS.md, "N14 extension", written before this was run): plain, spline restoration, fill and fill + ridge on four splits.

Splits: O (original test-number rule), G (vehicle group = make, model, year), A (make and model only), R (repeated grouped 5-fold cross-validation, 10 repeats).
Intervals resample whole vehicle groups. Everything is MEASURED_SOFTWARE; the NHTSA reference delta-V is the one of ``severity_study.reference_dv``.
"""
from __future__ import annotations

import dataclasses
import pickle

import numpy as np
import pandas as pd

from crashguard import boot as B
from crashguard import config as C
from crashguard import saturation as SAT
from crashguard import severity as S
from crashguard import severity_study as SS
from crashguard import spline_restore as SPL

RANGES = (16.0, 32.0, 64.0)
FS = float(C.FS_HZ)
RFS = (0.05, 0.1, 0.2)
RF0 = 0.1  # the release fraction in config (tuned earlier); fixed for splits O, G, A
FINAL_FAMILY, FINAL_SAT = "triangle", 0.7  # chosen earlier on the original tuning tests (docs/02_preregistration/ALGORITHMS.md revision log)
ALPHAS = (0.01, 0.1, 1.0, 10.0, 100.0)
METHODS = ("B", "SP", "M", "M+")
NAMES = {"B": "plain", "SP": "spline", "M": "fill", "M+": "fill + ridge"}
PAIRS = (("M+", "SP"), ("M", "SP"), ("M+", "B"), ("SP", "B"))  # (method, reference): difference = method minus reference
N_FOLDS, N_REPEATS = 5, 10
CACHE = C.PROCESSED / "n14x_cells.pkl"


def sp_params(rf: float) -> S.SeverityParams:
    return dataclasses.replace(S.DEFAULT, release_frac=rf)


def meta_of(tests: list[dict]) -> pd.DataFrame:
    rows = []
    for t in tests:
        make, model, year = (t["group"].split("|") + ["", "", ""])[:3]
        rows.append(dict(test_no=t["test_no"], kind=t["kind"], v=t["v"], ref=t["ref_dv"], group=t["group"], group_mm=f"{make}|{model}", make=make, model=model, year=year,
                         peak_g=float(t["sig"]["peak_g"]), peak_g_raw=float(t["sig"]["peak_g_raw"])))
    return pd.DataFrame(rows)


def build_cells(tests: list[dict]) -> dict:
    """Every estimate that any split needs, as arrays aligned with ``tests``: plain delta-V and pulse width per release fraction, fill per (family, level, fraction), spline per (level, fraction)."""
    key = [(t["test_no"], t["kind"]) for t in tests]
    if CACHE.exists():
        try:
            c = pickle.loads(CACHE.read_bytes())
            if c["key"] == key:
                return c
        except Exception:  # noqa: BLE001 - a stale or unreadable cache is just rebuilt
            pass
    n = len(tests)
    cells: dict = {"key": key}
    for rg in RANGES:
        wins = []
        for t in tests:
            y = SS.sensor_signal(t["sig"], rg, FS)
            wins.append(SS._window(y, FS))
        for rf in RFS:
            p = sp_params(rf)
            bdv, pms = np.zeros(n), np.zeros(n)
            for i, (w, trig) in enumerate(wins):
                r = S.severity(w, FS, trig, None, p)
                bdv[i], pms[i] = r["dv_res_kmh"], r["pulse_ms"]
            cells[("b", rg, rf)], cells[("pl", rg, rf)] = bdv, pms
            for sf in SAT.SAT_FRACS:
                sp = np.zeros(n)
                for i, (w, trig) in enumerate(wins):
                    sp[i] = SPL.severity_restored(w, FS, trig, rg, sf, p)[0]["dv_res_kmh"]
                cells[("sp", rg, sf, rf)] = sp
                for fam in SAT.FAMILIES:
                    dv, sh, ap = np.zeros(n), np.zeros(n), np.zeros(n, bool)
                    for i, (w, trig) in enumerate(wins):
                        r, info = SAT.severity_filled(w, FS, trig, rg, fam, p, sf)
                        dv[i], sh[i], ap[i] = r["dv_res_kmh"], info.sat_share, info.applied
                    cells[("m", rg, fam, sf, rf)], cells[("sh", rg, fam, sf, rf)], cells[("ap", rg, fam, sf, rf)] = dv, sh, ap
    C.PROCESSED.mkdir(parents=True, exist_ok=True)
    CACHE.write_bytes(pickle.dumps(cells))
    return cells


def aerr(est: np.ndarray, ref: np.ndarray) -> np.ndarray:
    return np.abs(100.0 * (np.asarray(est) - np.asarray(ref)) / np.asarray(ref))


# ---- splits ----
def holdout_every_third(first_key: dict[str, int]) -> set[str]:
    """Groups sorted by (smallest test number, label); ranks 3, 6, 9, ... (counting from 1) are held out."""
    order = sorted(first_key, key=lambda g: (first_key[g], g))
    return {g for i, g in enumerate(order, 1) if i % 3 == 0}


def split_O(meta: pd.DataFrame) -> np.ndarray:
    """True = held out. Within each kind, tests sorted by test number, ranks 3, 6, 9, ... held out (the original rule)."""
    held = np.zeros(len(meta), bool)
    for kind in ("frontal", "side"):
        idx = meta.index[meta.kind == kind]
        order = sorted(idx, key=lambda i: meta.test_no[i])
        for r, i in enumerate(order, 1):
            held[i] = r % 3 == 0
    return held


def split_by(meta: pd.DataFrame, col: str) -> np.ndarray:
    first = meta.groupby(col).test_no.min().to_dict()
    ho = holdout_every_third(first)
    return meta[col].isin(ho).to_numpy()


# ---- estimators ----
def _alpha_and_fit(X: np.ndarray, y: np.ndarray, groups: np.ndarray, m_tr: np.ndarray, ref_tr: np.ndarray, app_tr: np.ndarray, leave: str) -> tuple[float, SAT.RidgeCorrection]:
    """Ridge strength by leave-one-test-out (leave='test') or leave-one-group-out ('group') on the TRAINING rows; ``X, y, groups`` are the applied training rows,
    ``m_tr`` the fill estimate of ALL training tests (the score is the median absolute error over all of them)."""
    scores = {}
    ug = sorted(set(groups.tolist()))
    for a in ALPHAS:
        pred = np.zeros(len(y))
        if leave == "test":
            for i in range(len(y)):
                m = np.ones(len(y), bool)
                m[i] = False
                pred[i] = SAT.RidgeCorrection(a).fit(X[m], y[m]).predict(X[i : i + 1])[0] if m.sum() >= 4 else 0.0
        else:
            for g in ug:
                te = groups == g
                m = ~te
                if m.sum() >= 4:
                    pred[te] = SAT.RidgeCorrection(a).fit(X[m], y[m]).predict(X[te])
        corr = m_tr.copy()
        corr[app_tr] *= np.exp(pred)
        scores[a] = float(np.median(aerr(corr, ref_tr)))
    best = min(ALPHAS, key=lambda a: (round(scores[a], 9), -a))
    return best, SAT.RidgeCorrection(best).fit(X, y)


def estimates(cells: dict, meta: pd.DataFrame, tr: np.ndarray, te: np.ndarray, rg: float, combo: dict, leave: str = "test") -> tuple[dict, dict]:
    """Estimates on the ``te`` rows for the four methods. ``combo``: B -> rf, SP -> (level, rf), M -> (family, level, rf). Everything fitted uses ``tr`` rows only."""
    ref = meta.ref.to_numpy()
    rf_b, (sp_sf, sp_rf), (fam, sf, rf) = combo["B"], combo["SP"], combo["M"]
    est = {"B": cells[("b", rg, rf_b)][te], "SP": cells[("sp", rg, sp_sf, sp_rf)][te], "M": cells[("m", rg, fam, sf, rf)][te]}
    m_all, ap, sh = cells[("m", rg, fam, sf, rf)], cells[("ap", rg, fam, sf, rf)], cells[("sh", rg, fam, sf, rf)]
    b_all, pl = cells[("b", rg, rf)], cells[("pl", rg, rf)]
    use = tr & ap
    X = np.stack([b_all, sh, pl], axis=1)
    y = np.log(ref / np.maximum(m_all, 1e-6))
    if use.sum() >= 4:
        gcol = meta.group_mm.to_numpy() if leave == "group" else meta.group.to_numpy()
        alpha, corr = _alpha_and_fit(X[use], y[use], gcol[use], m_all[tr], ref[tr], ap[tr], leave)
        f = np.ones(int(te.sum()))
        a_te = ap[te]
        if a_te.any():
            f[a_te] = corr.factor(X[te][a_te])
        est["M+"] = est["M"] * f
    else:
        alpha = float("nan")
        est["M+"] = est["M"].copy()
    return est, dict(alpha=alpha)


def score_over_ranges(cells: dict, meta: pd.DataFrame, tr: np.ndarray, kind: str, args: tuple) -> float:
    ref = meta.ref.to_numpy()[tr]
    vals = []
    for rg in RANGES:
        vals.append(float(np.median(aerr(cells[(kind, rg) + args][tr], ref))))
    return float(np.mean(vals))


def choose_combo(cells: dict, meta: pd.DataFrame, tr: np.ndarray) -> dict:
    """Choices from the training rows only: B -> release fraction; SP -> (level, fraction); M -> (family, level, fraction). Ties: half-sine, higher level, fraction 0.1 then smaller."""
    b = min(RFS, key=lambda rf: (round(score_over_ranges(cells, meta, tr, "b", (rf,)), 9), rf != RF0, rf))
    sp = min(((sf, rf) for sf in SAT.SAT_FRACS for rf in RFS), key=lambda k: (round(score_over_ranges(cells, meta, tr, "sp", k), 9), -k[0], k[1] != RF0, k[1]))
    m = min(((fam, sf, rf) for fam in SAT.FAMILIES for sf in SAT.SAT_FRACS for rf in RFS),
            key=lambda k: (round(score_over_ranges(cells, meta, tr, "m", k), 9), k[0] != "half_sine", -k[1], k[2] != RF0, k[2]))
    return dict(B=b, SP=sp, M=m)


def fixed_combo(cells: dict, meta: pd.DataFrame, tune_G: np.ndarray) -> dict:
    """Settings for splits O, G and A: the earlier choices (triangle, 0.7, release 0.1) and the spline level chosen on G's tuning tests."""
    sp_sf = min(SAT.SAT_FRACS, key=lambda sf: (round(score_over_ranges(cells, meta, tune_G, "sp", (sf, RF0)), 9), -sf))
    return dict(B=RF0, SP=(sp_sf, RF0), M=(FINAL_FAMILY, FINAL_SAT, RF0))


# ---- metrics ----
def _stats(e: np.ndarray) -> dict:
    return dict(median=float(np.median(e)), p90=B.p90(e), w10=float(np.mean(e <= SS.TOL10)), w20=float(np.mean(e <= SS.TOL20)))


def block(e: np.ndarray, groups: np.ndarray) -> dict:
    out = dict(n=len(e), n_groups=len(set(groups.tolist())), **_stats(e))
    for k, f in (("median", np.median), ("p90", B.p90), ("w10", lambda a: np.mean(a <= SS.TOL10)), ("w20", lambda a: np.mean(a <= SS.TOL20))):
        _p, lo, hi = B.ci_grouped(e, groups, f)
        out[k + "_lo"], out[k + "_hi"] = lo, hi
    return out


def paired(ea: np.ndarray, eb: np.ndarray, groups: np.ndarray) -> dict:
    """eb minus ea (method minus reference) on the same tests, groups resampled."""
    m = B.paired_diff_grouped(ea, eb, groups, np.median)
    w = B.paired_diff_grouped((ea <= SS.TOL10).astype(float), (eb <= SS.TOL10).astype(float), groups, np.mean)
    return dict(d_median=m[0], d_median_lo=m[1], d_median_hi=m[2], d_w10=w[0], d_w10_lo=w[1], d_w10_hi=w[2], clears=bool(m[2] < 0), n_worse=int((eb > ea + 1e-9).sum()), n_better=int((eb < ea - 1e-9).sum()))


def run_fixed(cells: dict, meta: pd.DataFrame, held: np.ndarray, combo: dict, split: str) -> tuple[list[dict], list[dict], dict]:
    rows, prow, per = [], [], {}
    ref = meta.ref.to_numpy()
    tr, te = ~held, held
    gcol = meta.group_mm.to_numpy() if split == "A" else meta.group.to_numpy()
    for rg in RANGES:
        est, info = estimates(cells, meta, tr, te, rg, combo, leave="test")
        E = {m: aerr(est[m], ref[te]) for m in METHODS}
        per[rg] = dict(est=est, err=E, alpha=info["alpha"])
        for m in METHODS:
            rows.append(dict(split=split, range_g=rg, method=m, **block(E[m], gcol[te])))
        for a_, b_ in PAIRS:
            prow.append(dict(split=split, range_g=rg, method=a_, reference=b_, **paired(E[b_], E[a_], gcol[te])))
    return rows, prow, per


def run_cv(cells: dict, meta: pd.DataFrame) -> tuple[list[dict], list[dict], dict]:
    """Repeated grouped CV on make/model groups. Returns metric rows, paired rows and the per-test errors E[range][method] of shape (repeats, tests)."""
    n = len(meta)
    ref = meta.ref.to_numpy()
    groups = meta.group_mm.to_numpy()
    ug = sorted(set(groups.tolist()))
    E = {rg: {m: np.zeros((N_REPEATS, n)) for m in METHODS} for rg in RANGES}
    EST = {rg: {m: np.zeros((N_REPEATS, n)) for m in METHODS} for rg in RANGES}
    choices = []
    for rep in range(N_REPEATS):
        rng = np.random.default_rng(C.SEED + rep)
        order = list(rng.permutation(len(ug)))
        fold_of = {ug[j]: k % N_FOLDS for k, j in enumerate(order)}
        fold = np.array([fold_of[g] for g in groups])
        for f in range(N_FOLDS):
            te, tr = fold == f, fold != f
            combo = choose_combo(cells, meta, tr)
            choices.append(dict(repeat=rep, fold=f, B_rf=combo["B"], SP_level=combo["SP"][0], SP_rf=combo["SP"][1], M_family=combo["M"][0], M_level=combo["M"][1], M_rf=combo["M"][2]))
            for rg in RANGES:
                est, _info = estimates(cells, meta, tr, te, rg, combo, leave="group")
                for m in METHODS:
                    EST[rg][m][rep, te] = est[m]
                    E[rg][m][rep, te] = aerr(est[m], ref[te])
    rows, prow = [], []
    stat = {"median": lambda a: float(np.median(a, axis=0).mean()), "p90": lambda a: float(np.quantile(a, 0.9, axis=0).mean()),
            "w10": lambda a: float((a <= SS.TOL10).mean()), "w20": lambda a: float((a <= SS.TOL20).mean())}
    for rg in RANGES:
        for m in METHODS:
            e = E[rg][m]
            row = dict(split="R", range_g=rg, method=m, n=n, n_groups=len(ug))
            for k, f in stat.items():
                p, lo, hi = B.ci_grouped(e.T, groups, f)
                row[k], row[k + "_lo"], row[k + "_hi"] = p, lo, hi
            per_rep = np.median(e, axis=1)
            row["median_rep_min"], row["median_rep_max"], row["median_rep_std"] = float(per_rep.min()), float(per_rep.max()), float(per_rep.std(ddof=1))
            rows.append(row)
        for a_, b_ in PAIRS:
            ea, eb = E[rg][b_].T, E[rg][a_].T
            m = B.paired_diff_grouped(ea, eb, groups, stat["median"])
            w = B.paired_diff_grouped((ea <= SS.TOL10).astype(float), (eb <= SS.TOL10).astype(float), groups, stat["w10"])
            dr = np.median(E[rg][a_], axis=1) - np.median(E[rg][b_], axis=1)
            prow.append(dict(split="R", range_g=rg, method=a_, reference=b_, d_median=m[0], d_median_lo=m[1], d_median_hi=m[2], d_w10=w[0], d_w10_lo=w[1], d_w10_hi=w[2], clears=bool(m[2] < 0),
                             d_median_rep_min=float(dr.min()), d_median_rep_max=float(dr.max()), n_worse=-1, n_better=-1))
    return rows, prow, dict(E=E, EST=EST, choices=pd.DataFrame(choices))


def main() -> None:
    from crashguard.results import record_many

    C.TABLES.mkdir(parents=True, exist_ok=True)
    tests = SS.load_tests()
    if not tests:
        return
    meta = meta_of(tests)
    cells = build_cells(tests)
    held_G = np.array([t["role"] == "heldout" for t in tests])
    held_O, held_A = split_O(meta), split_by(meta, "group_mm")
    combo = fixed_combo(cells, meta, ~held_G)
    src = "results/tables/n14x_metrics.csv"
    ent: list[dict] = []

    def add(name, value, unit, origin="MEASURED_SOFTWARE", notes="", s=src):
        ent.append(dict(name=f"n14x.{name}", value=value, unit=unit, origin=origin, source_file=s, notes=notes))

    add("combo.spline_level", combo["SP"][0], "share of the range", notes="chosen on split G's tuning tests (same rule as the fill's level)")
    add("combo.fill_family", combo["M"][0], "text")
    add("combo.fill_level", combo["M"][1], "share of the range")
    add("combo.release_frac", RF0, "fraction of peak")
    rows, prow = [], []
    held_by = {"O": held_O, "G": held_G, "A": held_A}
    per_by = {}
    for sp, held in held_by.items():
        r, p, per = run_fixed(cells, meta, held, combo, sp)
        rows += r
        prow += p
        per_by[sp] = per
        gcol = "group_mm" if sp == "A" else "group"
        add(f"{sp}.n_tests_tuning", int((~held).sum()), "tests")
        add(f"{sp}.n_tests_heldout", int(held.sum()), "tests")
        add(f"{sp}.n_groups_tuning", int(meta[gcol][~held].nunique()), "groups")
        add(f"{sp}.n_groups_heldout", int(meta[gcol][held].nunique()), "groups")
        for rg in RANGES:
            add(f"{sp}.r{rg:g}.ridge_alpha", per[rg]["alpha"], "strength", notes="chosen by leave-one-test-out on this split's tuning tests")
    add("G.n_groups_alt_make_model_tuning", int(meta.group_mm[~held_G].nunique()), "groups", notes="split G's tuning tests counted as make+model groups")
    add("G.n_groups_alt_make_model_heldout", int(meta.group_mm[held_G].nunique()), "groups")
    add("overlap.A_heldout_in_G_tuning_tests", int((held_A & ~held_G).sum()), "tests", notes="split A held-out tests that were TUNING tests of split G (the settings were chosen on those)")
    add("overlap.O_heldout_in_G_tuning_tests", int((held_O & ~held_G).sum()), "tests")
    r, p, cv = run_cv(cells, meta)
    rows += r
    prow += p
    add("R.n_groups", int(meta.group_mm.nunique()), "groups")
    add("R.folds", N_FOLDS, "folds")
    add("R.repeats", N_REPEATS, "repeats")
    M = pd.DataFrame(rows)
    P = pd.DataFrame(prow)
    M.to_csv(C.TABLES / "n14x_metrics.csv", index=False)
    P.to_csv(C.TABLES / "n14x_paired.csv", index=False)
    cv["choices"].to_csv(C.TABLES / "n14x_cv_choices.csv", index=False)
    ch = cv["choices"]
    for col in ("M_family", "M_level", "M_rf", "SP_level", "B_rf"):
        top = ch[col].value_counts()
        val = top.index[0]
        add(f"R.choice_most_common.{col}", val if isinstance(val, str) else float(val), "text" if isinstance(val, str) else "value", notes=f"chosen in {int(top.iloc[0])} of {len(ch)} folds")
    for r_ in M.itertuples():
        for k in ("n", "n_groups", "median", "median_lo", "median_hi", "p90", "p90_lo", "p90_hi", "w10", "w10_lo", "w10_hi", "w20", "w20_lo", "w20_hi", "median_rep_min", "median_rep_max", "median_rep_std"):
            v = getattr(r_, k, None)
            if v is None or (isinstance(v, float) and np.isnan(v)):
                continue
            add(f"{r_.split}.r{r_.range_g:g}.{r_.method}.{k}", int(v) if k in ("n", "n_groups") else round(float(v), 4), "tests" if k in ("n", "n_groups") else ("fraction" if k.startswith(("w10", "w20")) else "percent"))
    for r_ in P.itertuples():
        nm = f"{r_.split}.r{r_.range_g:g}.paired.{r_.method}_vs_{r_.reference}"
        for k in ("d_median", "d_median_lo", "d_median_hi", "d_w10", "d_w10_lo", "d_w10_hi"):
            add(f"{nm}.{k}", round(float(getattr(r_, k)), 4), "percent" if "median" in k else "fraction", notes="method minus reference; negative d_median = method better; groups resampled")
        add(f"{nm}.clears", int(r_.clears), "flag", notes="1 = the whole interval of d_median is below zero")
    # failure cases at +-16 g
    ref = meta.ref.to_numpy()
    est16 = per_by["G"][16.0]["est"]
    f_g = meta[held_G].copy()
    f_g["est_plain"], f_g["est_fill_ridge"] = est16["B"], est16["M+"]
    f_g["abs_err_pct"] = aerr(est16["M+"], ref[held_G])
    f_g["clipped_share"] = cells[("sh", 16.0, FINAL_FAMILY, FINAL_SAT, RF0)][held_G]
    f_g = f_g.sort_values("abs_err_pct", ascending=False).head(10)
    f_g.to_csv(C.TABLES / "n14x_failure_g16_heldout.csv", index=False)
    f_c = meta.copy()
    f_c["abs_err_pct"] = cv["E"][16.0]["M+"].mean(axis=0)
    f_c["est_fill_ridge_mean"] = cv["EST"][16.0]["M+"].mean(axis=0)
    f_c["clipped_share"] = cells[("sh", 16.0, FINAL_FAMILY, FINAL_SAT, RF0)]
    f_c = f_c.sort_values("abs_err_pct", ascending=False).head(10)
    f_c.to_csv(C.TABLES / "n14x_failure_g16_cv.csv", index=False)
    for nm, f, fn in (("G_heldout", f_g, "heldout"), ("R_cv", f_c, "cv")):
        s_ = f"results/tables/n14x_failure_g16_{fn}.csv"
        add(f"failure16.{nm}.max_abs_err_pct", round(float(f.abs_err_pct.max()), 3), "percent", s=s_)
        add(f"failure16.{nm}.tenth_abs_err_pct", round(float(f.abs_err_pct.iloc[-1]), 3), "percent", s=s_)
        add(f"failure16.{nm}.share_side", round(float((f.kind == "side").mean()), 3), "fraction", s=s_)
        for k, row in enumerate(f.itertuples(), 1):
            for col, unit in (("test_no", "test"), ("make", "text"), ("model", "text"), ("kind", "text"), ("peak_g", "g"), ("peak_g_raw", "g"), ("abs_err_pct", "percent"), ("clipped_share", "fraction")):
                v = getattr(row, col)
                add(f"failure16.{nm}.rank{k}.{col}", v if unit == "text" else (int(v) if col == "test_no" else round(float(v), 3)), unit, s=s_)
    record_many(ent, purge_prefixes=("n14x.",))
    pd.set_option("display.width", 250)
    print(M[["split", "range_g", "method", "n", "n_groups", "median", "median_lo", "median_hi", "p90", "w10", "w20"]].round(2).to_string())
    print(P[["split", "range_g", "method", "reference", "d_median", "d_median_lo", "d_median_hi", "clears"]].round(2).to_string())
    print(f_g[["test_no", "make", "model", "kind", "peak_g", "abs_err_pct", "clipped_share"]].round(2).to_string())
    print(f_c[["test_no", "make", "model", "kind", "peak_g", "abs_err_pct", "clipped_share"]].round(2).to_string())


if __name__ == "__main__":
    main()
