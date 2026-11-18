"""T7: conformal variants (EXPLORATORY; no preregistration).

Part A, severity class intervals (alpha 0.10, +-16, +-32, +-64 g): the current split-conformal intervals (pooled) against (i) group-wise calibration by test kind (frontal or side; the NHTSA tests have no vehicle size, so
the kind is the available vehicle-class proxy), (ii) a simple widening margin (one class added to the upper end and to the interval), (iii) class-conditional intervals (per predicted class; the primary of the UA-SCT
study). Coverage on held-out vehicles (make and model groups never seen in tuning or calibration), mean width, share of Severe or Critical events assigned below Severe (mis-triage) and escalation.
Part B, the N20 false-alarm guarantee at alpha 1% and 5% (clean calibration pool: validation non-crash events without recording-group or near-duplicate matches): current split-conformal against (i) group-wise
calibration by vehicle-size category, (ii) a simple widening margin alpha_eff = alpha - 2 sqrt(alpha (1 - alpha) / n_cal), and (iii) class-conditional calibration by the negative's own class (near-miss or normal
driving), which is NOT deployable (the class of a test event is unknown) and is shown only as a diagnosis. The guarantee "holds" under the S3 rule: the upper end of the 95% interval is at or below alpha plus one
binomial standard error of the test negatives. MEASURED_SOFTWARE.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from crashguard import boot as B
from crashguard import config as C
from crashguard import ua_core as U
from crashguard.conformal import conformal_threshold
from crashguard.detector_extra import fit, frames_full, score_all
from crashguard.s3_conformal import duplicate_flags

SRC = "results/tables/t7_conformal_variants.csv"
SEEDS = (C.SEED,) + C.SEEDS
CATS = ("Light", "Medium", "Heavy", "Unknown")


def part_a(add) -> None:
    core = U.build()
    refc = U.ref_classes(core)
    grp = core.grp
    sev = refc >= 2
    for rg in (16.0, 32.0, 64.0):
        variants = {"current_pooled": dict(variant="pooled", widen=0), "kind_groupwise": dict(variant="kind", widen=0), "widened_plus1": dict(variant="pooled", widen=1), "class_conditional": dict(variant="cc", widen=0)}
        for nm, kw in variants.items():
            iv = U.interval_classes(core, rg, 0.10, kw["variant"], widen=kw["widen"])
            t = np.broadcast_to(refc[None, :], iv["lo"].shape)
            valid = iv["c_hat"] >= 0
            cover = np.where(valid, ((t >= iv["lo"]) & (t <= iv["hi"])).astype(float), np.nan)
            width = np.where(valid, (iv["hi"] - iv["lo"] + 1).astype(float), np.nan)
            mis, esc = U.mis_esc(iv["up"], refc)
            for k, arr in (("coverage", cover), ("width", width), ("mis_triage", mis), ("escalation", esc)):
                p, lo, hi = U.gmean(arr, grp)
                u = "classes" if k == "width" else "fraction"
                add(f"a.r{rg:g}.{nm}.{k}", round(p, 4), u, "mean over held-out rows; grouped (make and model) bootstrap interval")
                add(f"a.r{rg:g}.{nm}.{k}_lo", round(lo, 4), u, "95% grouped bootstrap interval")
                add(f"a.r{rg:g}.{nm}.{k}_hi", round(hi, 4), u, "95% grouped bootstrap interval")
            add(f"a.r{rg:g}.{nm}.coverage_reaches_90", int(np.nanmean(cover) >= 0.9), "flag", "point coverage at or above the nominal 0.90")
    _ = sev


def part_b(add) -> None:
    tr, va, te = frames_full()
    va_trig = va[va.triggered]
    flags, _cnt = duplicate_flags()
    clean_ids = set(flags.event_id[~flags.flag])
    yv, yt = va.y.to_numpy(), te.y.to_numpy()
    neg_v = (yv == 0) & va.event_id.isin(clean_ids).to_numpy()
    size_v, size_t = va.vehiclesize.to_numpy(), te.vehiclesize.to_numpy()
    lab_v, lab_t = va.label.to_numpy(), te.label.to_numpy()
    n_cal = int(neg_v.sum())
    tn = yt == 0
    add("b.n_calibration_negatives", n_cal, "events", "clean validation non-crash events")
    add("b.n_test_negatives", int(tn.sum()), "events", "de-duplicated test non-crash events")
    res: dict = {}
    for seed in SEEDS:
        scorer, _m = fit("rf15", seed, tr, va_trig)
        sv, st = score_all(scorer, va), score_all(scorer, te)
        for alpha in (0.01, 0.05):
            thr_pool = conformal_threshold(sv[neg_v], alpha)
            out = {"current_pooled": st > thr_pool}
            thr_c = {}
            for c in CATS:
                m = neg_v & (size_v == c)
                thr_c[c] = conformal_threshold(sv[m], alpha) if m.sum() >= 50 else thr_pool
            out["size_groupwise"] = np.array([st[i] > thr_c[size_t[i]] for i in range(len(st))])
            a_eff = max(alpha - 2.0 * np.sqrt(alpha * (1 - alpha) / n_cal), 1.0 / (n_cal + 1))
            out["widened_margin"] = st > conformal_threshold(sv[neg_v], a_eff)
            thr_k = {lab: conformal_threshold(sv[neg_v & (lab_v == lab)], alpha) for lab in (1, 2)}
            out["class_conditional_oracle"] = np.array([st[i] > thr_k.get(lab_t[i], thr_pool) for i in range(len(st))])
            for nm, alarm in out.items():
                res.setdefault((alpha, nm), []).append((alarm[tn].astype(float), float(alarm[yt == 1].mean())))
    for (alpha, nm), lst in res.items():
        fa_seed = np.array([a.mean() for a, _r in lst])
        fa_events = np.stack([a for a, _r in lst], 1)  # (n_test_neg, seeds)
        p, lo, hi = B.ci(fa_events, lambda z: float(z.mean()))
        se = float(np.sqrt(alpha * (1 - alpha) / tn.sum()))
        tag = f"b.a{int(round(alpha * 100))}.{nm}"
        add(f"{tag}.fa_mean", round(p, 5), "fraction", "test false-alarm rate, mean over seeds 42 and 0 to 4; 95% bootstrap interval over test non-crash events")
        add(f"{tag}.fa_mean_lo", round(lo, 5), "fraction", "95% bootstrap interval")
        add(f"{tag}.fa_mean_hi", round(hi, 5), "fraction", "95% bootstrap interval")
        add(f"{tag}.recall", round(float(np.mean([r for _a, r in lst])), 4), "fraction", "system recall at that rule, mean over seeds")
        add(f"{tag}.holds", int(hi <= alpha + se), "flag", "S3 rule: the upper end of the interval is at or below alpha plus one binomial standard error of the test negatives")
        add(f"{tag}.fa_seed_spread", round(float(fa_seed.std(ddof=1)), 5), "fraction", "standard deviation over seeds")


def main() -> None:
    from crashguard.results import record_many

    ent: list[dict] = []

    def add(name, value, unit, notes=""):
        ent.append(dict(name=f"t7.{name}", value=value, unit=unit, origin="MEASURED_SOFTWARE", source_file=SRC, notes="EXPLORATORY; " + notes))

    part_a(add)
    part_b(add)
    pd.DataFrame([dict(name=e["name"], value=e["value"]) for e in ent]).to_csv(C.TABLES / "t7_conformal_variants.csv", index=False)
    record_many(ent, purge_prefixes=("t7.",))
    g = {e["name"]: e["value"] for e in ent}
    for rg in (16, 32, 64):
        for nm in ("current_pooled", "kind_groupwise", "widened_plus1", "class_conditional"):
            print(rg, nm, {k: g[f"t7.a.r{rg}.{nm}.{k}"] for k in ("coverage", "width", "mis_triage", "escalation")})
    for a in (1, 5):
        for nm in ("current_pooled", "size_groupwise", "widened_margin", "class_conditional_oracle"):
            print("alpha", a, nm, g[f"t7.b.a{a}.{nm}.fa_mean"], g[f"t7.b.a{a}.{nm}.fa_mean_hi"], "holds", g[f"t7.b.a{a}.{nm}.holds"], "recall", g[f"t7.b.a{a}.{nm}.recall"])


if __name__ == "__main__":
    main()
