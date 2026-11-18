"""P3 (docs/02_preregistration/PREREGISTRATION_V4.md section 3): selective prediction (P3a) and abstain as an escalation signal in the UA-SCT simulator (P3b).

``fit``: reliability score and its choice, the 70% threshold (validation), the factor f of the lowered table (validation); two freezes (P3a, P3b).
``eval``: sealed fold scored once for P3a and once for P3b. Ranges +-16 and +-32 g at 100 Hz (primary: +-16 g). MEASURED_SOFTWARE; the simulator cells are SIMULATED.
"""
from __future__ import annotations

import json
import os
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

from crashguard import config as C
from crashguard import pp_common as PC
from crashguard import pp_models as PM
from crashguard import s11_sct as S
from crashguard.pp_ctx import Ctx
from crashguard.pp_p1 import MODEL_DIR, predict
from crashguard.t1_equal_escalation import tuned_params

RGS = (16.0, 32.0)
FS = 100
KEEP = 0.70
LEVELS = [round(x, 2) for x in np.arange(1.0, 0.2999, -0.05)]
F_GRID = np.round(np.arange(0.30, 1.0001, 0.0025), 4)
SRC = "results/tables/p3_sealed.csv"
EST = ("a", "b", "c")


def err_pct(est: np.ndarray, ref: np.ndarray) -> np.ndarray:
    return 100.0 * np.abs(est - ref) / ref


def estimates(cx: Ctx, rg: float, z: dict) -> dict:
    df, _ = cx.cell(rg, FS)
    return {"a": df.dv_plain.to_numpy(float), "b": z["models"]["b"].predict(df), "c": z["models"]["c"].predict(df)}


def oof_probs(cx: Ctx, df: pd.DataFrame, z: dict) -> np.ndarray:
    """Probability features of the no-mode direct GBM: cross-fitted inside development, the P1 model elsewhere."""
    d0 = z["models"]["d_none"]
    pf = np.zeros((len(df), 2))
    dev = np.flatnonzero(cx.dev)
    for tr, te in GroupKFold(5).split(dev, cx.y[dev], cx.group[dev]):
        m = PM.OrdGBM(d0.leaves, d0.trees, False).fit(df.iloc[dev[tr]], cx.y[dev[tr]], None)
        pf[dev[te]] = PM.prob_feats(m.predict_cum(df.iloc[dev[te]], None))
    rest = np.flatnonzero(~cx.dev)
    pf[rest] = PM.prob_feats(d0.predict_cum(df.iloc[rest], None))
    return pf


def assigned_classes(est: np.ndarray, abstain: np.ndarray) -> np.ndarray:
    c = PC.cls_of(est)
    return np.where(abstain, 3, c)


def fit_stage(cx: Ctx) -> None:
    out = {}
    files = []
    for rg in RGS:
        z = joblib.load(MODEL_DIR / f"p1_{rg:g}_{FS}.joblib")
        df, _ = cx.cell(rg, FS)
        plain = np.maximum(df.dv_plain.to_numpy(float), 1e-6)
        target = np.log(cx.ref / plain)
        pf = oof_probs(cx, df, z)
        rel = {"s1": PM.Reliability(False).fit(df[cx.dev], target[cx.dev]), "s2": PM.Reliability(True).fit(df[cx.dev], target[cx.dev], pf[cx.dev])}
        sc = {"s1": rel["s1"].score(df), "s2": rel["s2"].score(df, pf)}
        est = estimates(cx, rg, z)
        e_c = err_pct(est["c"], cx.ref)
        vals = {}
        for k in ("s1", "s2"):
            thr = float(np.quantile(sc[k][cx.val], KEEP))
            ret = cx.val & (sc[k] <= thr)
            vals[k] = dict(thr=thr, p90_retained=float(np.quantile(e_c[ret], 0.9)), n=int(ret.sum()))
        choice = "s2" if vals["s2"]["p90_retained"] < vals["s1"]["p90_retained"] - 1e-9 else "s1"
        thr = vals[choice]["thr"]
        # factor f: the lowered table escalates as much as A on validation
        ab = sc[choice] > thr
        a_cls = assigned_classes(est["c"], ab)
        non = cx.val & (cx.y <= 1)
        e_target = float(np.mean(a_cls[non] >= 2))
        best = min(F_GRID, key=lambda f: (abs(float(np.mean(PC.cls_of(est["c"][non] / f) >= 2)) - e_target), -f))
        out[f"{rg:g}"] = dict(choice=choice, threshold=thr, val=vals, val_escalation_A=e_target, f=float(best), val_escalation_lowered=float(np.mean(PC.cls_of(est["c"][non] / best) >= 2)))
        joblib.dump(dict(rel={choice: rel[choice]}, choice=choice), MODEL_DIR / f"p3_{rg:g}.joblib")
        files.append(MODEL_DIR / f"p3_{rg:g}.joblib")
        print(rg, out[f"{rg:g}"], flush=True)
    ph = PC.freeze("P3a", dict(per_range=out, note="reliability score, threshold at the 70th percentile of validation scores; sealed fold not used"), files + [MODEL_DIR / f"p1_{rg:g}_{FS}.joblib" for rg in RGS])
    pb = PC.freeze("P3b", dict(per_range={k: dict(f=v["f"], threshold=v["threshold"], val_escalation_A=v["val_escalation_A"], val_escalation_lowered=v["val_escalation_lowered"]) for k, v in out.items()},
                               sim=dict(cells="S.STEADY + S.BURST", seeds="3000 + hour, hours 0..29", params="s11.tuned.*"), note="factor f chosen on validation so the lowered table escalates as A does; no simulated outcome used"), files)
    print("freeze P3a", ph, "P3b", pb)


def rc_curve(err: np.ndarray, y: np.ndarray, cls: np.ndarray, s: np.ndarray) -> list[dict]:
    order = np.argsort(s, kind="stable")
    rows = []
    for r in LEVELS:
        k = int(np.ceil(r * len(s)))
        m = np.zeros(len(s), bool)
        m[order[:k]] = True
        rows.append(dict(retention=r, n=int(m.sum()), p90=float(np.quantile(err[m], 0.9)) if err is not None else float("nan"), under=PC.under_triage(y[m], cls[m]), over=PC.over_triage(y[m], cls[m])))
    return rows


def eval_a(cx: Ctx) -> tuple[dict, dict]:
    fz = json.loads((PC.FREEZE_DIR / "p_freeze_P3a.json").read_text(encoding="utf-8"))
    for f, hsh in fz["model_files"].items():
        assert PC.sha256_file(f) == hsh, f"{f} changed after the freeze"
    h = PC.sealed_gate("P3a")
    fz1 = json.loads((PC.FREEZE_DIR / "p_freeze_P1.json").read_text(encoding="utf-8"))
    E = PC.PEntries("p3a", SRC)
    E.add("freeze_commit", h, "commit", "commit of the freeze of P3a")
    te = cx.test
    y, grp, ref = cx.y[te], cx.group[te], cx.ref[te]
    g = PC.GBoot(grp)
    rows, store = [], {}
    for rg in RGS:
        z = joblib.load(MODEL_DIR / f"p1_{rg:g}_{FS}.joblib")
        p3 = joblib.load(MODEL_DIR / f"p3_{rg:g}.joblib")
        fz_r = fz["per_range"][f"{rg:g}"]
        df, W = cx.cell(rg, FS)
        pf = None
        if p3["choice"] == "s2":
            pf = PM.prob_feats(z["models"]["d_none"].predict_cum(df, None))
        s_all = p3["rel"][p3["choice"]].score(df, pf)
        s = s_all[te]
        est = {k: v[te] for k, v in estimates(cx, rg, z).items()}
        sel = fz1["selection"][f"{rg:g}_{FS}"]
        bd = sel["best_direct"]
        mi = z["modeclf"].predict(df)
        cls = {k: PC.cls_of(v) for k, v in est.items()}
        cls["direct"], _ = predict(bd, z["models"][bd], df[te], W[te], cx.mode_idx[te], mi[te])
        ret = s <= fz_r["threshold"]
        n_ret = int(ret.sum())
        tag = f"r{rg:g}"
        E.add(f"{tag}.score_variant", fz_r["choice"], "variant", "s1 = descriptors only, s2 = descriptors plus class-probability features; chosen on validation")
        E.add(f"{tag}.retained_share_threshold", round(n_ret / len(s), 4), "fraction", "sealed fold, fixed validation threshold")
        sev = y >= 2
        E.add(f"{tag}.abstain_share_of_severe_or_critical", round(float(1 - ret[sev].mean()), 4), "fraction", "share of true Severe or Critical records that abstain")
        E.add(f"{tag}.abstain_share_of_non_severe", round(float(1 - ret[~sev].mean()), 4), "fraction")
        order = np.argsort(s, kind="stable")
        exact = np.zeros(len(s), bool)
        exact[order[: int(np.ceil(KEEP * len(s)))]] = True
        for name, mask in (("threshold", ret), ("exact70", exact)):
            for est_name in ("a", "b", "c", "direct"):
                c = cls[est_name]
                e = err_pct(est[est_name], ref) if est_name != "direct" else None
                if e is not None:
                    pt, d9 = g.stat(lambda i, mask=mask, e=e: float(np.quantile(e[i][mask[i]], 0.9)) if mask[i].any() else float("nan"))
                    E.ci(f"{tag}.{name}.{est_name}.p90_retained", PC.summ(pt, d9), "percent", "p90 absolute delta-V error among retained records")
                    if est_name == "c":
                        store[(rg, name, "p90")] = (pt, d9)
                    E.ci(f"{tag}.{name}.{est_name}.p90_all", g.ci(lambda i, e=e: float(np.quantile(e[i], 0.9))), "percent")
                ut = g.ci(lambda i, mask=mask, c=c: PC.under_triage(y[i][mask[i]], c[i][mask[i]]))
                ua = g.ci(lambda i, c=c: PC.under_triage(y[i], c[i]))
                E.ci(f"{tag}.{name}.{est_name}.under_triage_retained", ut, "fraction")
                E.ci(f"{tag}.{name}.{est_name}.under_triage_all", ua, "fraction")
                pt, d = g.stat(lambda i, mask=mask, c=c: PC.under_triage(y[i][mask[i]], c[i][mask[i]]) / max(PC.under_triage(y[i], c[i]), 1e-9) if np.isfinite(PC.under_triage(y[i][mask[i]], c[i][mask[i]])) else float("nan"))
                E.ci(f"{tag}.{name}.{est_name}.under_triage_ratio", PC.summ(pt, d), "ratio", "retained / unselected under-triage rate; below 1 = abstaining removes under-triage")
                if est_name == "c":
                    store[(rg, name)] = (pt, d)
        for est_name in ("a", "b", "c", "direct"):
            e = err_pct(est[est_name], ref) if est_name != "direct" else None
            for r in rc_curve(e, y, cls[est_name], s):
                rows.append(dict(range_g=rg, estimator=est_name, **r))
        store[(rg, "s")] = s
        store[(rg, "est_c")] = est["c"]
    pd.DataFrame(rows).to_csv(C.TABLES / "p3a_risk_coverage.csv", index=False)
    rg = 16.0
    pt, d = store[(rg, "threshold")]
    p90v, d9 = store[(rg, "threshold", "p90")]
    ratio_hi = float(np.nanquantile(d, 0.975))
    ok_ratio = pt <= 0.5 and ratio_hi < 1.0
    ok_p90 = p90v <= 20.0
    E.add("hP3a.ratio", round(pt, 4), "ratio", "anchored estimator, +-16 g, retained / unselected under-triage")
    E.add("hP3a.ratio_hi", round(ratio_hi, 4), "ratio", "upper end of the 95% grouped interval")
    E.add("hP3a.p90_retained", round(p90v, 3), "percent")
    E.add("hP3a.ratio_condition_met", int(ok_ratio), "flag")
    E.add("hP3a.p90_condition_met", int(ok_p90), "flag")
    E.add("hP3a.criterion_met", int(ok_ratio and ok_p90), "flag")
    pr = PC.p_above(d, 1.0)
    pp = PC.p_above(d9, 20.0)
    E.add("hP3a.p_raw", round(max(pr, pp), 4), "probability", "larger of the share of resamples with ratio at or above 1 and the share with retained p90 error at or above 20%")
    E.flush()
    PC.time_log("P3a sealed", "sealed fold scored once for P3a; freeze commit " + h[:8])
    print("H-P3a ratio", round(pt, 3), "hi", round(ratio_hi, 3), "p90 retained", round(p90v, 2), "met", ok_ratio and ok_p90)
    return store, fz


def sealed_scores(cx: Ctx) -> dict:
    """Reliability scores and anchored estimates of the sealed fold from the frozen models (the part of ``eval_a`` that P3b needs)."""
    te = cx.test
    store = {}
    for rg in RGS:
        z = joblib.load(MODEL_DIR / f"p1_{rg:g}_{FS}.joblib")
        p3 = joblib.load(MODEL_DIR / f"p3_{rg:g}.joblib")
        df, _ = cx.cell(rg, FS)
        pf = PM.prob_feats(z["models"]["d_none"].predict_cum(df, None)) if p3["choice"] == "s2" else None
        store[(rg, "s")] = p3["rel"][p3["choice"]].score(df, pf)[te]
        store[(rg, "est_c")] = estimates(cx, rg, z)["c"][te]
    return store


def eval_b(cx: Ctx, store: dict) -> None:
    fz = json.loads((PC.FREEZE_DIR / "p_freeze_P3b.json").read_text(encoding="utf-8"))
    for f, hsh in fz["model_files"].items():
        assert PC.sha256_file(f) == hsh, f"{f} changed after the freeze"
    h = PC.sealed_gate("P3b")
    E = PC.PEntries("p3b", "results/tables/p3b_cells.csv")
    E.add("freeze_commit", h, "commit", "commit of the freeze of P3b")
    te = cx.test
    y, grp = cx.y[te], cx.group[te]
    g = PC.GBoot(grp)
    pools = S.load_pools()
    params = tuned_params()
    jobs = []
    classes = {}
    for rg in RGS:
        fr = fz["per_range"][f"{rg:g}"]
        s, est = store[(rg, "s")], store[(rg, "est_c")]
        ab = s > fr["threshold"]
        a_cls = assigned_classes(est, ab)
        lowered = PC.cls_of(est / fr["f"])
        point = PC.cls_of(est)
        classes[rg] = dict(A=a_cls, lowered=lowered, point=point)
        tag = f"r{rg:g}"
        for nm, c in (("A", a_cls), ("P1e", lowered), ("P1", point)):
            E.ci(f"{tag}.{nm}.mis_triage", g.ci(lambda i, c=c: PC.mis_triage(y[i], c[i])), "fraction", "sealed fold, pool level, grouped bootstrap")
            E.ci(f"{tag}.{nm}.escalation", g.ci(lambda i, c=c: PC.escalation(y[i], c[i])), "fraction")
        pt, d = g.stat(lambda i: PC.mis_triage(y[i], a_cls[i]) - PC.mis_triage(y[i], lowered[i]))
        E.ci(f"{tag}.mis_triage_A_minus_P1e", PC.summ(pt, d), "fraction", "A (abstain to the fast path) minus the lowered table; negative = A mis-triages less")
        pe, de = g.stat(lambda i: PC.escalation(y[i], a_cls[i]) - PC.escalation(y[i], lowered[i]))
        E.ci(f"{tag}.escalation_A_minus_P1e", PC.summ(pe, de), "fraction", "equal escalation is the aim; this is the gap on the sealed fold")
        # EXPLORATORY: lowered table matched on the sealed fold by interpolation along its curve (evaluation only)
        non = y <= 1
        eA = float(np.mean(a_cls[non] >= 2))
        fs_ = min(F_GRID, key=lambda f: (abs(float(np.mean(PC.cls_of(est[non] / f) >= 2)) - eA), -f))
        lm = PC.cls_of(est / fs_)
        pt2, d2 = g.stat(lambda i: PC.mis_triage(y[i], a_cls[i]) - PC.mis_triage(y[i], lm[i]))
        E.ci(f"{tag}.mis_triage_A_minus_P1e_matched_on_sealed.EXPLORATORY", PC.summ(pt2, d2), "fraction", f"EXPLORATORY: factor {fs_} chosen on the sealed fold to match A's escalation exactly (uses sealed labels, evaluation only)")
        if rg == 16.0:
            lo, hi = float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975))
            ok = pt <= -0.02 and hi < 0
            E.add("hP3b.mis_triage_diff", round(pt, 4), "fraction")
            E.add("hP3b.mis_triage_diff_lo", round(lo, 4), "fraction")
            E.add("hP3b.mis_triage_diff_hi", round(hi, 4), "fraction")
            E.add("hP3b.escalation_gap", round(pe, 4), "fraction", "A minus lowered table on the sealed fold")
            E.add("hP3b.criterion_met", int(ok), "flag", "point at most -0.02 and the interval entirely below zero")
            E.add("hP3b.p_raw", round(PC.p_above(d, -0.0), 4), "probability", "share of resamples with the difference at or above 0; floor 0.001")
            print("H-P3b", round(pt, 4), round(lo, 4), round(hi, 4), "escalation gap", round(pe, 4), "met", ok)
        for sysn, base_pol, cl in (("A", "P3", a_cls), ("P1e", "P1", lowered), ("P2e", "P2", lowered)):
            pl = {"classes": {rg: dict(true=y.astype(int), point=cl.astype(int), upper=cl.astype(int))}, "crash_t": pools["crash_t"], "fa_t": pools["fa_t"]}
            for mode, scen in (("steady", S.STEADY), ("burst", S.BURST)):
                for name, kw in scen:
                    for hr in range(30):
                        jobs.append((S.make_cfg(base_pol, rg, kw, mode == "burst", S.EVAL_SEED, hr, pl, params, None, f"{mode}_{name}"), dict(range_g=rg, mode=mode, scen=name, pol=sysn)))
    sim_csv = C.TABLES / "p3b_cells.csv"
    if os.environ.get("PP_REUSE_SIM") and sim_csv.exists():  # a repeat after a failed write of results.json: the simulated cells are read back, not recomputed
        R = pd.read_csv(sim_csv)
    else:
        R = S.run_jobs(jobs, min(14, os.cpu_count() or 1))
        R.to_csv(sim_csv, index=False)
    mets = ("mis_triage", "escalation", "reach10_critical", "reach30_critical", "p95_lat_s_critical", "node_air_share", "fast_air_share_of_allowance")
    for rg in RGS:
        for grp_name, modes in (("steady", ("steady",)), ("burst", ("burst",))):
            cells = [(rg, m, s_) for m in modes for s_ in sorted(set(R[(R.range_g == rg) & (R["mode"] == m)].scen))]
            for a_, b_ in (("P1e", "A"), ("P2e", "A")):
                for met in mets:
                    p, lo, hi, n = S.agg_diff(R, met, a_, b_, cells, ["range_g", "mode", "scen"])
                    if n:
                        t = f"r{rg:g}.{grp_name}.{b_}_minus_{a_}.{met}"
                        u = "s" if "lat" in met else "fraction"
                        E.add(t, round(p, 5), u, f"mean over {n} cells of the paired seed-mean difference; 30 seeds per cell", "SIMULATED")
                        E.add(t + "_lo", round(lo, 5), u, "95% bootstrap interval over seeds", "SIMULATED")
                        E.add(t + "_hi", round(hi, 5), u, "95% bootstrap interval over seeds", "SIMULATED")
    E.add("sim.runs", int(len(R)), "runs", "simulated runs; every value an assumption of sct_sim", "SIMULATED")
    E.add("sim.runs_exceeding_duty", int(R.duty_exceeded.sum()), "runs", "must be 0", "SIMULATED")
    E.flush()
    PC.time_log("P3b sealed", "sealed fold scored once for P3b; freeze commit " + h[:8])


def main() -> None:
    cx = Ctx()
    if sys.argv[1] == "fit":
        fit_stage(cx)
    elif sys.argv[1] == "evalb":
        eval_b(cx, sealed_scores(cx))
    else:
        store, _ = eval_a(cx)
        eval_b(cx, store)


if __name__ == "__main__":
    main()
