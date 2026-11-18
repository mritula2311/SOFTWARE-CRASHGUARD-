"""T13a: the N13 grid and the fixed N14 methods on NHTSA tests of other test modes (selection and decision rules: docs/07_log/DECISIONS.md, entry "T13a selection record").

No method is refitted: plain, spline and fill + ridge are fit on the 176 original tests only (fixed N14 settings: triangle family, level 0.7, release fraction 0.1, spline level from split G's tuning
tests, ridge strength by leave-one-make-and-model-out on the 176). The reference delta-V is the N13 reference. Intervals resample make-and-model groups. MEASURED_SOFTWARE.
"""
from __future__ import annotations

import pickle

import joblib
import numpy as np
import pandas as pd

from crashguard import config as C
from crashguard import saturation as SAT
from crashguard import saturation_splits as SPL
from crashguard import severity as S
from crashguard import severity_study as SS
from crashguard import spline_restore as SR
from crashguard.jp_common import Entries
from crashguard.t13_harvest import CACHE, MIN_REF_DV_KMH

FS = float(C.FS_HZ)
RANGES = (16.0, 32.0, 64.0)
SRC = "results/tables/t13_heldout_metrics.csv"
TARGET = SS.TARGET_SHARE


def build_set() -> tuple[list[dict], dict]:
    """Held-out records after the fixed filters. Returns (tests, counts)."""
    z = joblib.load(CACHE)
    found = z["found"]
    cnt = dict(n_candidates=int(z["n_candidates"]), n_usable_records=len(found), n_excluded_records=len(z["excluded"]))
    rows = []
    for r in found:
        ref, _ = SS.reference_dv(r["sig"])
        rows.append(dict(r, ref_dv=ref))
    cnt["n_below_ref_floor"] = int(sum(r["ref_dv"] < MIN_REF_DV_KMH for r in rows))
    rows = [r for r in rows if r["ref_dv"] >= MIN_REF_DV_KMH]
    best: dict[tuple, dict] = {}
    for r in sorted(rows, key=lambda r: (r["test_no"], r["role"])):
        best.setdefault((r["make"], r["model"], r["year"], r["mode"], r["role"]), r)
    kept = list(best.values())
    cnt["n_dropped_repeat_vehicle"] = len(rows) - len(kept)
    old = SS.load_tests()
    old_mm = {"|".join(t["group"].split("|")[:2]) for t in old}
    tests = []
    for r in sorted(kept, key=lambda r: (r["test_no"], r["role"])):
        mm = f"{r['make']}|{r['model']}"
        tests.append(dict(test_no=r["test_no"], kind="heldout", v=r["v"], sig=r["sig"], role="new", group=f"{mm}|{r['year']}", ref_dv=r["ref_dv"], ref_asi=float("nan"), mode=r["mode"],
                          vrole=r["role"], seen_mm=mm in old_mm))
    cnt["n_used"] = len(tests)
    cnt["n_seen_make_model"] = int(sum(t["seen_mm"] for t in tests))
    cnt["n_groups_mm"] = len({"|".join(t["group"].split("|")[:2]) for t in tests})
    return tests, cnt


def new_cells(tests: list[dict], combo: dict) -> dict:
    """The estimates the fixed N14 settings need for the new tests (same keys and meaning as ``saturation_splits.build_cells``)."""
    rf_b, (sp_sf, sp_rf), (fam, sf, rf) = combo["B"], combo["SP"], combo["M"]
    n = len(tests)
    cells: dict = {}
    for rg in RANGES:
        bdv, pms = np.zeros(n), np.zeros(n)
        spv, mdv, msh, map_ = np.zeros(n), np.zeros(n), np.zeros(n), np.zeros(n, bool)
        for i, t in enumerate(tests):
            w, trig = SS._window(SS.sensor_signal(t["sig"], rg, FS), FS)
            r = S.severity(w, FS, trig, None, SPL.sp_params(rf_b))
            bdv[i], pms[i] = r["dv_res_kmh"], r["pulse_ms"]
            spv[i] = SR.severity_restored(w, FS, trig, rg, sp_sf, SPL.sp_params(sp_rf))[0]["dv_res_kmh"]
            r, info = SAT.severity_filled(w, FS, trig, rg, fam, SPL.sp_params(rf), sf)
            mdv[i], msh[i], map_[i] = r["dv_res_kmh"], info.sat_share, info.applied
        cells[("b", rg, rf_b)], cells[("pl", rg, rf)] = bdv, pms
        cells[("sp", rg, sp_sf, sp_rf)] = spv
        cells[("m", rg, fam, sf, rf)], cells[("sh", rg, fam, sf, rf)], cells[("ap", rg, fam, sf, rf)] = mdv, msh, map_
    return cells


def main() -> None:
    C.TABLES.mkdir(parents=True, exist_ok=True)
    tests, cnt = build_set()
    old = SS.load_tests()
    meta_old = SPL.meta_of(old)
    cells_old = pickle.loads(SPL.CACHE.read_bytes())
    held_G = np.array([t["role"] == "heldout" for t in old])
    combo = SPL.fixed_combo(cells_old, meta_old, ~held_G)
    print("combo", combo, cnt, flush=True)
    meta = pd.concat([meta_old, SPL.meta_of(tests)], ignore_index=True)
    nc = new_cells(tests, combo)
    cells = {k: np.concatenate([np.asarray(cells_old[k]), nc[k]]) for k in nc}
    n_old, n_new = len(old), len(tests)
    tr = np.r_[np.ones(n_old, bool), np.zeros(n_new, bool)]
    te = ~tr
    ref_new = meta.ref.to_numpy()[te]
    grp = meta.group_mm.to_numpy()[te]
    modes = pd.Series([t["mode"] for t in tests])
    sub = {"all": np.ones(n_new, bool), "unseen_make_model": ~np.array([t["seen_mm"] for t in tests])}
    E = Entries("t13.heldout", SRC)
    for k, v in cnt.items():
        E.add(f"count.{k}", int(v), "tests", notes="selection counts; rules in docs/07_log/DECISIONS.md (T13a selection record)")
    for m, c in modes.value_counts().items():
        E.add(f"count.mode.{m.replace(' ', '_')}", int(c), "tests", notes="records used per test mode")
    rows, prow = [], []
    for rg in RANGES:
        est, info = SPL.estimates(cells, meta, tr, te, rg, combo, leave="group")
        E.add(f"r{rg:g}.ridge_alpha", info["alpha"], "strength", notes="leave-one-make-model-out on the 176; NOT_RUN value = no ridge was fit (fewer than 4 clipped training tests at this range), so fill + ridge equals fill")
        err = {m: SPL.aerr(est[m], ref_new) for m in SPL.METHODS}
        for sname, mask in sub.items():
            if mask.sum() < 10:
                continue
            for m in SPL.METHODS:
                rows.append(dict(subset=sname, range_g=rg, method=m, **SPL.block(err[m][mask], grp[mask])))
            for a_, b_ in SPL.PAIRS:
                prow.append(dict(subset=sname, range_g=rg, method=a_, reference=b_, **SPL.paired(err[b_][mask], err[a_][mask], grp[mask])))
        if rg == 16.0:
            pd.DataFrame(dict(test_no=[t["test_no"] for t in tests], mode=modes, make_model=grp, ref_dv=ref_new, **{f"est_{m}": est[m] for m in SPL.METHODS},
                              **{f"abserr_{m}": err[m] for m in SPL.METHODS})).to_csv(C.TABLES / "t13_heldout_tests_r16.csv", index=False)
            err16 = err
    M, P = pd.DataFrame(rows), pd.DataFrame(prow)
    M.to_csv(C.TABLES / "t13_heldout_metrics.csv", index=False)
    P.to_csv(C.TABLES / "t13_heldout_paired.csv", index=False)
    for r_ in M.itertuples():
        for k in ("n", "n_groups", "median", "median_lo", "median_hi", "p90", "p90_lo", "p90_hi", "w10", "w10_lo", "w10_hi", "w20", "w20_lo", "w20_hi"):
            v = getattr(r_, k)
            E.add(f"{r_.subset}.r{r_.range_g:g}.{r_.method}.{k}", int(v) if k in ("n", "n_groups") else round(float(v), 4), "tests" if k in ("n", "n_groups") else ("fraction" if k[0] == "w" else "percent"))
    for r_ in P.itertuples():
        nm = f"{r_.subset}.r{r_.range_g:g}.paired.{r_.method}_vs_{r_.reference}"
        for k in ("d_median", "d_median_lo", "d_median_hi", "d_w10", "d_w10_lo", "d_w10_hi"):
            E.add(f"{nm}.{k}", round(float(getattr(r_, k)), 4), "percent" if "median" in k else "fraction", notes="method minus reference; negative d_median = method better; make-and-model groups resampled")
        E.add(f"{nm}.clears", int(r_.clears), "flag", notes="1 = whole interval of d_median below zero (decision rule 2 of the T13a record)")
    # N13 grid on the new set (generic sensor model of severity_study); rows come back in the order of ``tests``
    grid = SS.grid([dict(t) for t in tests])
    rows_g = []
    for (rg, fs), d in grid.groupby(["range_g", "rate_hz"]):
        e = d.err_pct.abs().to_numpy()
        rows_g.append(dict(range_g=rg, rate_hz=fs, **SPL.block(e, grp)))
    G = pd.DataFrame(rows_g)
    G.to_csv(C.TABLES / "t13_heldout_grid.csv", index=False)
    for r_ in G.itertuples():
        for k in ("median", "median_lo", "median_hi", "p90", "p90_lo", "p90_hi", "w10", "w10_lo", "w10_hi"):
            E.add(f"grid.r{r_.range_g:g}.f{int(r_.rate_hz)}.{k}", round(float(getattr(r_, k)), 4), "fraction" if k[0] == "w" else "percent")
    ok = G[G.w10_lo >= TARGET].sort_values(["range_g", "rate_hz"])
    E.add("grid.criterion.cells_meeting_lower_bound", int(len(ok)), "cells", notes="cells whose lower 95% bound of the share within 10% is at least 0.80")
    E.add("grid.criterion.min_range_g", float(ok.range_g.iloc[0]) if len(ok) else float("nan"), "g", notes="lowest range with a cell meeting the criterion; NOT_RUN value = no cell meets it")
    E.add("grid.criterion.min_rate_hz_at_min_range", float(ok[ok.range_g == ok.range_g.iloc[0]].rate_hz.iloc[0]) if len(ok) else float("nan"), "Hz")
    E.add("grid.criterion.r16_f100_meets", int(bool(G[(G.range_g == 16.0) & (G.rate_hz == 100)].w10_lo.iloc[0] >= TARGET)), "flag")
    mm = pd.DataFrame(dict(mode=modes, B=err16["B"], SP=err16["SP"], MP=err16["M+"]))
    for m, d in mm.groupby("mode"):
        k = m.replace(" ", "_")
        E.add(f"bymode.{k}.n", int(len(d)), "tests")
        for c in ("B", "SP", "MP"):
            E.add(f"bymode.{k}.{c}.median", round(float(d[c].median()), 3), "percent", notes="descriptive, +-16 g 100 Hz")
            E.add(f"bymode.{k}.{c}.w10", round(float((d[c] <= 10).mean()), 3), "fraction", notes="descriptive, +-16 g 100 Hz")
    E.add("ref_dv.median_kmh", round(float(np.median(ref_new)), 2), "km/h")
    E.add("ref_dv.min_kmh", round(float(ref_new.min()), 2), "km/h")
    E.add("ref_dv.max_kmh", round(float(ref_new.max()), 2), "km/h")
    E.add("peak_g.share_above_16", round(float(np.mean([t["sig"]["peak_g"] > 16 for t in tests])), 3), "fraction", notes="peak after the 260 Hz front end")
    E.flush()
    pd.set_option("display.width", 250)
    print(cnt)
    print(M[M.subset == "all"][["range_g", "method", "n", "n_groups", "median", "p90", "w10", "w10_lo", "w10_hi"]].round(3).to_string())
    print(P[P.subset == "all"][["range_g", "method", "reference", "d_median", "d_median_lo", "d_median_hi", "clears"]].round(2).to_string())
    print(G[["range_g", "rate_hz", "median", "p90", "w10", "w10_lo", "w10_hi"]].round(3).to_string())


if __name__ == "__main__":
    main()
