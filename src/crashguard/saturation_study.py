"""N14 evaluation: plain delta-V (B), saturation-aware fill (M) and fill plus ridge correction (M+) on the NHTSA tests and on synthetic pulses.

All rules, the split, the metrics and the decision rule are in docs/02_preregistration/ALGORITHMS.md (written before the first run). Tuning tests choose the pulse family and the
ridge strength (leave-one-test-out); the held-out tests are scored once. Intervals: 1,000 bootstrap resamples of tests (seed 42); the comparison with the
baseline is paired on the same tests.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from crashguard import boot as B
from crashguard import config as C
from crashguard import saturation as SAT
from crashguard import severity as S
from crashguard import severity_study as SS

RANGES = (16.0, 32.0, 64.0)
FS = float(C.FS_HZ)
ALPHAS = (0.01, 0.1, 1.0, 10.0, 100.0)
METHODS = ("B", "M", "M+")


def per_test(tests: list[dict], range_g: float) -> pd.DataFrame:
    """For every test: reference, baseline delta-V, and the filled-window delta-V for every (pulse family, saturation level) combination, with the fit information."""
    rows = []
    for t in tests:
        y = SS.sensor_signal(t["sig"], range_g, FS)
        w, trig = SS._window(y, FS)
        base = S.severity(w, FS, trig)
        row = dict(test_no=t["test_no"], kind=t["kind"], role=t["role"], v=t["v"], ref=t["ref_dv"], ref_asi=t["ref_asi"], b_dv=base["dv_res_kmh"], b_asi=base["asi"], b_cls=base["severity_class"],
                   pulse_ms=base["pulse_ms"])
        for fam in SAT.FAMILIES:
            for sf in SAT.SAT_FRACS:
                r, info = SAT.severity_filled(w, FS, trig, range_g, fam, sat_frac=sf)
                k = f"{fam}|{sf:g}"
                row[f"m_dv|{k}"], row[f"m_asi|{k}"], row[f"m_cls|{k}"] = r["dv_res_kmh"], r["asi"], r["severity_class"]
                row[f"app|{k}"], row[f"sat|{k}"], row[f"nsat|{k}"] = bool(info.applied), info.sat_share, info.n_sat
        rows.append(row)
    return pd.DataFrame(rows)


def err(est: np.ndarray, ref: np.ndarray) -> np.ndarray:
    return 100.0 * (np.asarray(est) - np.asarray(ref)) / np.asarray(ref)


def choose_combo(per: dict[float, pd.DataFrame]) -> tuple[tuple[str, float], dict]:
    """(pulse family, saturation level) with the lowest mean over the three ranges of the median absolute error on the TUNING tests. Ties: half-sine, then the higher level."""
    scores = {}
    for fam in SAT.FAMILIES:
        for sf in SAT.SAT_FRACS:
            vals = []
            for rg, d in per.items():
                tune = d[d.role == "tuning"]
                vals.append(float(np.median(np.abs(err(tune[f"m_dv|{fam}|{sf:g}"], tune.ref)))))
            scores[(fam, sf)] = float(np.mean(vals))
    best = min(scores, key=lambda k: (round(scores[k], 9), k[0] != "half_sine", -k[1]))
    return best, scores


def reduce(d: pd.DataFrame, fam: str, sf: float) -> pd.DataFrame:
    """Keep the columns of the chosen combination under fixed names."""
    k = f"{fam}|{sf:g}"
    keep = [c for c in d.columns if "|" not in c]
    out = d[keep].copy()
    out["m_dv"], out["m_asi"], out["m_cls"] = d[f"m_dv|{k}"], d[f"m_asi|{k}"], d[f"m_cls|{k}"]
    out["applied"], out["sat_share"], out["n_sat"] = d[f"app|{k}"], d[f"sat|{k}"], d[f"nsat|{k}"]
    out["saturated"] = out.n_sat > 0
    return out


def ridge_rows(d: pd.DataFrame) -> pd.DataFrame:
    s = d[d.applied].copy()
    s["x1"], s["x2"], s["x3"] = s.b_dv, s.sat_share, s.pulse_ms
    s["y"] = np.log(s.ref / np.maximum(s.m_dv, 1e-6))
    return s


def loto_alpha(d: pd.DataFrame) -> tuple[float, dict]:
    """Ridge strength by leave-one-test-out on the TUNING tests: the strength with the lowest median absolute error of the corrected estimate over all tuning tests."""
    tune = d[d.role == "tuning"]
    rr = ridge_rows(tune)
    X, y = rr[["x1", "x2", "x3"]].to_numpy(), rr.y.to_numpy()
    scores = {}
    for a in ALPHAS:
        pred = np.zeros(len(rr))
        for i in range(len(rr)):
            m = np.ones(len(rr), bool)
            m[i] = False
            pred[i] = SAT.RidgeCorrection(a).fit(X[m], y[m]).predict(X[i : i + 1])[0] if m.sum() >= 4 else 0.0
        corr = tune.m_dv.to_numpy().copy()
        corr[tune.applied.to_numpy()] *= np.exp(pred)
        scores[a] = float(np.median(np.abs(err(corr, tune.ref))))
    best = min(ALPHAS, key=lambda a: (round(scores[a], 9), -a))
    return best, scores


def final_correction(d: pd.DataFrame, alpha: float) -> SAT.RidgeCorrection:
    rr = ridge_rows(d[d.role == "tuning"])
    return SAT.RidgeCorrection(alpha).fit(rr[["x1", "x2", "x3"]].to_numpy(), rr.y.to_numpy())


def estimates(d: pd.DataFrame, corr: SAT.RidgeCorrection) -> pd.DataFrame:
    """Add the columns est_B, est_M, est_M+ (delta-V in km/h)."""
    out = d.copy()
    out["est_B"] = out.b_dv
    out["est_M"] = out.m_dv
    f = np.ones(len(out))
    ap = out.applied.to_numpy()
    if ap.any():
        X = np.stack([out.b_dv.to_numpy()[ap], out.sat_share.to_numpy()[ap], out.pulse_ms.to_numpy()[ap]], axis=1)
        f[ap] = corr.factor(X)
    out["est_M+"] = out.est_M * f
    return out


def metrics_block(d: pd.DataFrame, col: str) -> dict:
    e = np.abs(err(d[col], d.ref))
    fr = d[d.kind == "frontal"]
    inside = ((fr[col] >= fr.v) & (fr[col] <= 2 * fr.v)).to_numpy()
    out = dict(n=len(d), median=float(np.median(e)), p90=B.p90(e), w10=float(np.mean(e <= SS.TOL10)), w20=float(np.mean(e <= SS.TOL20)), band=float(inside.mean()) if len(inside) else float("nan"))
    for k, x, f in (("median", e, np.median), ("p90", e, B.p90), ("w10", e <= SS.TOL10, np.mean), ("w20", e <= SS.TOL20, np.mean)):
        _p, lo, hi = B.ci(x, f)
        out[k + "_lo"], out[k + "_hi"] = lo, hi
    if len(inside):
        _p, lo, hi = B.ci(inside, np.mean)
        out["band_lo"], out["band_hi"] = lo, hi
    return out


def paired_block(d: pd.DataFrame, method: str) -> dict:
    """Method minus baseline on the same tests: difference in median absolute error and in the share within 10%, with 95% intervals."""
    a, b = np.abs(err(d["est_B"], d.ref)), np.abs(err(d[f"est_{method}"], d.ref))
    m = B.paired_diff(a, b, np.median)
    w = B.paired_diff((a <= SS.TOL10).astype(float), (b <= SS.TOL10).astype(float), np.mean)
    return dict(d_median=m[0], d_median_lo=m[1], d_median_hi=m[2], d_w10=w[0], d_w10_lo=w[1], d_w10_hi=w[2], n_worse=int((b > a + 1e-9).sum()), n_better=int((b < a - 1e-9).sum()), n=len(d))


def synthetic(fam: str, sf: float, seeds: int = 3) -> pd.DataFrame:
    """Synthetic pulses with analytic delta-V through clipping at each range: errors of the baseline and of M."""
    from crashguard import severity_synth as Y

    rng = np.random.default_rng(C.SEED)
    rows = []
    for rg in RANGES:
        for shp in Y.SHAPES:
            for A in (20.0, 40.0, 80.0, 150.0):
                for T in (0.04, 0.08, 0.12, 0.16):
                    truth = Y.dv_truth_ms(shp, A, T) * 3.6
                    for _ in range(seeds):
                        acc, trig = Y.make_window(shp, A, T, 0.0, FS, rng, clip_g=rg)
                        if trig < 0:
                            continue
                        b = S.severity(acc, FS, trig)["dv_res_kmh"]
                        m, info = SAT.severity_filled(acc, FS, trig, rg, fam, sat_frac=sf)
                        rows.append(dict(range_g=rg, shape=shp, A_g=A, T_ms=T * 1000, truth=truth, b_dv=b, m_dv=m["dv_res_kmh"], saturated=bool(info.saturated), applied=bool(info.applied)))
    d = pd.DataFrame(rows)
    d["b_err"], d["m_err"] = err(d.b_dv, d.truth), err(d.m_dv, d.truth)
    return d


def main() -> None:
    from crashguard.results import record_many

    C.TABLES.mkdir(parents=True, exist_ok=True)
    tests = SS.load_tests()
    if not tests:
        record_many([dict(name="n14.run", value="NOT_RUN", unit="", origin="NOT_RUN", source_file="results/tables/n14_metrics.csv", notes="no NHTSA tests available")])
        return
    src = "results/tables/n14_metrics.csv"
    ent: list[dict] = []

    def add(name, value, unit, origin="MEASURED_SOFTWARE", notes="", s=src):
        ent.append(dict(name=f"n14.{name}", value=value, unit=unit, origin=origin, source_file=s, notes=notes))

    per = {rg: per_test(tests, rg) for rg in RANGES}
    (fam, sf_chosen), combo_scores = choose_combo(per)
    for (f, sfv), v in combo_scores.items():
        add(f"combo.tuning_mean_median_abs_err_pct.{f}.sat{sfv:g}", round(v, 4), "percent", notes="TUNING tests: mean over the three ranges of the median absolute error; the lowest value is used (ties: half-sine, higher level)")
    add("family.chosen", fam, "text", notes="chosen on the tuning tests only")
    add("sat_frac.chosen", sf_chosen, "share of the range", notes="chosen on the tuning tests only")
    add("n_tuning", int((per[16.0].role == "tuning").sum()), "tests")
    add("n_heldout", int((per[16.0].role == "heldout").sum()), "tests")
    rows, paired_rows, worse = [], [], []
    detail = []
    model = dict(family=fam, sat_frac=sf_chosen, ranges={})
    for rg in RANGES:
        d = reduce(per[rg], fam, sf_chosen)
        alpha, a_scores = loto_alpha(d)
        corr = final_correction(d, alpha)
        e = estimates(d, corr)
        e["range_g"] = rg
        detail.append(e)
        add(f"r{rg:g}.saturated_share", round(float(e.saturated.mean()), 4), "fraction", notes="share of tests whose pulse reaches the range")
        add(f"r{rg:g}.fit_applied_share", round(float(e.applied.mean()), 4), "fraction")
        add(f"r{rg:g}.ridge_alpha", alpha, "strength", notes="chosen by leave-one-test-out on the tuning tests")
        for a_, sc in a_scores.items():
            add(f"r{rg:g}.ridge_loto.alpha{a_:g}.median_abs_err_pct", round(sc, 4), "percent")
        for i, nm in enumerate(("sat_dv", "sat_share", "pulse_ms")):
            add(f"r{rg:g}.ridge_weight.{nm}", round(float(corr.w[i]), 5), "weight", notes="on standardised inputs")
        add(f"r{rg:g}.ridge_bias", round(float(corr.b), 5), "log ratio")
        model["ranges"][f"{rg:g}"] = dict(alpha=alpha, mu=corr.mu.tolist(), sd=corr.sd.tolist(), w=corr.w.tolist(), b=corr.b)
        for part, sub in (("heldout", e[e.role == "heldout"]), ("tuning", e[e.role == "tuning"]), ("all", e)):
            for m in METHODS:
                mb = metrics_block(sub, f"est_{m}")
                rows.append(dict(range_g=rg, part=part, method=m, **mb))
                for k, v in mb.items():
                    add(f"r{rg:g}.{part}.{m}.{k}", round(float(v), 4) if k != "n" else int(v), "fraction" if k.startswith(("w10", "w20", "band")) else ("tests" if k == "n" else "percent"),
                        notes="HELD-OUT tests, scored once" if part == "heldout" else ("tuning tests: M and B have no fitted parameters; M+ is in-sample here, see the LOTO scores" if part == "tuning" else "all tests"))
            for m in ("M", "M+"):
                pb = paired_block(sub, m)
                paired_rows.append(dict(range_g=rg, part=part, method=m, **pb))
                for k, v in pb.items():
                    add(f"r{rg:g}.{part}.paired.{m}.{k}", round(float(v), 4) if not k.startswith("n") else int(v), "percent" if "median" in k else ("tests" if k.startswith("n") else "fraction"),
                        notes="method minus baseline on the same tests; negative d_median = better")
        h = e[e.role == "heldout"]
        for m in ("M", "M+"):
            ab, am = np.abs(err(h.est_B, h.ref)), np.abs(err(h[f"est_{m}"], h.ref))
            for i in np.flatnonzero(am > ab + 1e-9):
                worse.append(dict(range_g=rg, method=m, test_no=int(h.test_no.iloc[i]), kind=h.kind.iloc[i], v=float(h.v.iloc[i]), ref=float(h.ref.iloc[i]), baseline_dv=float(h.est_B.iloc[i]),
                                  method_dv=float(h[f"est_{m}"].iloc[i]), baseline_abs_err_pct=float(ab[i]), method_abs_err_pct=float(am[i]), sat_share=float(h.sat_share.iloc[i])))
    pd.DataFrame(rows).to_csv(C.TABLES / "n14_metrics.csv", index=False)
    pd.DataFrame(paired_rows).to_csv(C.TABLES / "n14_paired.csv", index=False)
    pd.concat(detail).to_csv(C.TABLES / "n14_per_test.csv", index=False)
    wdf = pd.DataFrame(worse, columns=["range_g", "method", "test_no", "kind", "v", "ref", "baseline_dv", "method_dv", "baseline_abs_err_pct", "method_abs_err_pct", "sat_share"])
    wdf.to_csv(C.TABLES / "n14_failure_cases.csv", index=False)
    for rg in RANGES:
        for m in ("M", "M+"):
            g = wdf[(wdf.range_g == rg) & (wdf.method == m)]
            add(f"r{rg:g}.heldout.{m}.worse_tests", int(len(g)), "tests", notes="held-out tests where the method's absolute error is larger than the baseline's (listed in n14_failure_cases.csv)")
            if len(g):
                add(f"r{rg:g}.heldout.{m}.worse_max_extra_abs_err_pct", round(float((g.method_abs_err_pct - g.baseline_abs_err_pct).max()), 4), "percent")

    syn = synthetic(fam, sf_chosen)
    syn.to_csv(C.TABLES / "n14_synthetic.csv", index=False)
    for rg in RANGES:
        for kind, sub in (("matched", syn[(syn.range_g == rg) & syn["shape"].isin(("half_sine", "triangular")) & syn.saturated]), ("mismatched", syn[(syn.range_g == rg) & (syn["shape"] == "square") & syn.saturated])):
            if len(sub):
                for nm, col in (("baseline", "b_err"), ("method", "m_err")):
                    e_ = sub[col].abs().to_numpy()
                    p, lo, hi = B.ci(e_, np.median)
                    add(f"synthetic.r{rg:g}.{kind}.{nm}.median_abs_err_pct", round(p, 4), "percent", "SIMULATED", "saturated synthetic pulses with analytic delta-V; 'matched' = half-sine and triangular, 'mismatched' = square", "results/tables/n14_synthetic.csv")
                    add(f"synthetic.r{rg:g}.{kind}.{nm}.median_abs_err_pct_lo", round(lo, 4), "percent", "SIMULATED", s="results/tables/n14_synthetic.csv")
                    add(f"synthetic.r{rg:g}.{kind}.{nm}.median_abs_err_pct_hi", round(hi, 4), "percent", "SIMULATED", s="results/tables/n14_synthetic.csv")
                add(f"synthetic.r{rg:g}.{kind}.n", int(len(sub)), "windows", "SIMULATED", s="results/tables/n14_synthetic.csv")
    import json

    C.PROCESSED.mkdir(parents=True, exist_ok=True)
    (C.PROCESSED / "n14_model.json").write_text(json.dumps(model, indent=2), encoding="utf-8")
    record_many(ent, purge_prefixes=("n14.",))
    figure(pd.concat(detail), fam)
    print(pd.DataFrame(rows)[lambda x: x.part == "heldout"][["range_g", "method", "n", "median", "median_lo", "median_hi", "w10", "w20", "band"]].round(3).to_string())
    print(pd.DataFrame(paired_rows)[lambda x: x.part == "heldout"].round(3).to_string())


def figure(d: pd.DataFrame, fam: str) -> None:
    import matplotlib.pyplot as plt

    from crashguard.plots import COLORS, save, style

    style()
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2), sharey=True)
    h = d[d.role == "heldout"]
    for ax, rg in zip(axes, RANGES):
        g = h[h.range_g == rg]
        for i, (m, mk) in enumerate((("B", "o"), ("M", "s"), ("M+", "^"))):
            ax.scatter(g.ref, g[f"est_{m}"], s=14, marker=mk, color=COLORS[i], label={"B": "baseline (clipped)", "M": f"fill ({fam})", "M+": "fill + ridge"}[m], alpha=0.8)
        lim = [0, max(g.ref.max(), 1) * 1.1]
        ax.plot(lim, lim, "k--", lw=0.8)
        ax.plot(lim, [0.9 * x for x in lim], "k:", lw=0.6)
        ax.plot(lim, [1.1 * x for x in lim], "k:", lw=0.6)
        ax.set_xlabel("Reference delta-V (km/h)")
        ax.set_title(f"range +-{rg:g} g, held-out tests", fontsize=9)
    axes[0].set_ylabel("Estimated delta-V (km/h)")
    axes[0].legend(fontsize=7)
    fig.suptitle("N14 saturation-aware estimator on NHTSA crash tests (MEASURED_SOFTWARE); dotted lines are +-10%", fontsize=9)
    save(fig, "n14_estimates")


if __name__ == "__main__":
    main()
