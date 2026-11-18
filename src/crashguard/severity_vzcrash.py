"""Severity measures on VZCrash (descriptive only: VZCrash has NO severity labels, so no accuracy claim is made).

For every event that passes the firmware-style trigger (2.0 g, same windows as features.py) we compute the severity measures from the
clipped window. We report their distributions by class (crash, near_miss, normal_driving), how well delta-V and ASI separate crashes
from the other classes when used alone as a score, their rank correlations, and how delta-V changes if the sensor range were smaller.
"""
from __future__ import annotations

import os
from dataclasses import replace
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from crashguard import config as C
from crashguard import severity as S
from crashguard.data import LABELS, iter_events
from crashguard.features import _cut
from crashguard.results import record_many

RELEASE_VARIANTS_G = (0.5, 1.0, 1.5)  # absolute pulse-release levels (old rule) tried on the same windows; 0.5 g is the rule used before the Phase 2 tuning
CLIP_LEVELS_G = (8.0, 4.0)  # smaller sensor ranges tried on the same windows (VZCrash peaks are far below 16 g, so 16 g changes nothing)
SCORES = ("dv_res_kmh", "asi", "thiv_kmh", "peak_pulse_g", "mean_pulse_g", "specific_energy_j_per_kg", "pulse_ms")
CORR_COLS = ("dv_res_kmh", "asi", "thiv_kmh", "peak_a")


def _shard(path_str: str) -> pd.DataFrame:
    rows = []
    for split, eid, label, vs, hd, acc, gyro, _gps in iter_events(Path(path_str)):
        n = len(acc)
        if n < 2:
            continue
        raw_peak = float(np.linalg.norm(acc, axis=1).max())
        if raw_peak > C.MPU_RANGE_G:  # corrupt events are dropped, as in features.py
            continue
        a = np.clip(acc, -C.MPU_RANGE_G, C.MPU_RANGE_G)
        mag = np.linalg.norm(a, axis=1)
        hit = np.flatnonzero(mag > C.TRIGGER_G)
        row = dict(event_id=eid, split=split, label=label, vehiclesize=vs, triggered=bool(len(hit)))
        if len(hit):
            g = np.clip(gyro if len(gyro) == n else (gyro[:n] if len(gyro) > n else _cut(gyro, 0, n) if len(gyro) else np.zeros((n, 3))),
                        -C.MPU_GYRO_RANGE_DPS, C.MPU_GYRO_RANGE_DPS)
            s0 = int(hit[0]) - C.PRE_N
            wa, wg = _cut(a, s0, C.WIN_N), _cut(g, s0, C.WIN_N)
            r = S.severity(wa, C.FS_HZ, C.PRE_N, wg)
            row.update({k: r[k] for k in ("dvx_kmh", "dvy_kmh", "dv_res_kmh", "pulse_ms", "peak_pulse_g", "mean_pulse_g", "specific_energy_j_per_kg", "asi", "thiv_kmh",
                                          "thiv_hit", "roll_deg", "pitch_deg", "rollover", "severity_class", "rollover_raw", "rollover_corrected", "roll_corrected_applied",
                                          "tilt_deg", "tilt_corrected_deg")})
            row["asi_class"] = r["asi_class"]
            rt = S.severity(wa, C.FS_HZ, C.PRE_N, None, replace(S.DEFAULT, flail_x_m=0.8))  # THIV with the 0.8 m longitudinal flail distance one read source gives (sensitivity)
            row["thiv_kmh_x08"], row["thiv_hit_x08"] = rt["thiv_kmh"], rt["thiv_hit"]
            for rel in RELEASE_VARIANTS_G:
                rr = S.severity(wa, C.FS_HZ, C.PRE_N, None, replace(S.DEFAULT, release_frac=0.0, release_g=rel))
                row[f"dv_res_kmh_rel{rel:g}"] = rr["dv_res_kmh"]
                row[f"pulse_ms_rel{rel:g}"] = rr["pulse_ms"]
            for c in CLIP_LEVELS_G:
                rc = S.severity(np.clip(wa, -c, c), C.FS_HZ, C.PRE_N, wg)
                row[f"dv_res_kmh_clip{c:g}"] = rc["dv_res_kmh"]
                row[f"asi_clip{c:g}"] = rc["asi"]
        rows.append(row)
    return pd.DataFrame(rows)


def test_windows(raw_dir: Path = C.RAW_DIR) -> tuple[np.ndarray, np.ndarray]:
    """Clipped windows (N, WIN_N, 3) of every triggered event of the supplied test split, for the C comparison."""
    wa_all, wg_all = [], []
    for path in sorted((raw_dir / "data").glob("test-*.parquet")):
        for _split, _eid, _label, _vs, _hd, acc, gyro, _gps in iter_events(path):
            n = len(acc)
            if n < 2 or float(np.linalg.norm(acc, axis=1).max()) > C.MPU_RANGE_G:
                continue
            a = np.clip(acc, -C.MPU_RANGE_G, C.MPU_RANGE_G)
            hit = np.flatnonzero(np.linalg.norm(a, axis=1) > C.TRIGGER_G)
            if not len(hit):
                continue
            g = np.clip(gyro if len(gyro) == n else (gyro[:n] if len(gyro) > n else _cut(gyro, 0, n) if len(gyro) else np.zeros((n, 3))),
                        -C.MPU_GYRO_RANGE_DPS, C.MPU_GYRO_RANGE_DPS)
            s0 = int(hit[0]) - C.PRE_N
            wa_all.append(_cut(a, s0, C.WIN_N).astype(np.float32))
            wg_all.append(_cut(g, s0, C.WIN_N).astype(np.float32))
    return np.stack(wa_all), np.stack(wg_all)


def extract(raw_dir: Path = C.RAW_DIR, workers: int | None = None) -> pd.DataFrame:
    files = sorted((raw_dir / "data").glob("*.parquet"))
    with ProcessPoolExecutor(workers or min(8, os.cpu_count() or 1)) as ex:
        parts = list(ex.map(_shard, [str(f) for f in files]))
    return pd.concat(parts, ignore_index=True)


def analyse(df: pd.DataFrame) -> list[dict]:
    from crashguard.split import leaky_test_ids, load_variant

    src = "results/tables/severity_vzcrash_distributions.csv"
    ent: list[dict] = []

    def add(name, value, unit, notes=""):
        ent.append(dict(name=f"severity_vzcrash.{name}", value=value, unit=unit, origin="MEASURED_SOFTWARE", source_file=src,
                        notes=(notes + "; " if notes else "") + "VZCrash has no severity labels: descriptive only, no accuracy claim"))

    t = df[df.triggered].copy()
    feats = load_variant(f"trig_{C.TRIGGER_G:g}")[["event_id", "peak_a"]]
    t = t.merge(feats, on="event_id", how="left")
    t["class_name"] = t.label.map(LABELS)
    add("events_triggered", int(len(t)), "events", "all splits, corrupt events dropped")

    rows = []
    for cname, g in t.groupby("class_name"):
        for col in SCORES + ("peak_a", "roll_deg", "pitch_deg"):
            q = g[col].quantile([0.25, 0.5, 0.75, 0.95])
            rows.append(dict(cls=cname, measure=col, n=len(g), q25=q[0.25], median=q[0.5], q75=q[0.75], p95=q[0.95]))
            for k, v in (("median", q[0.5]), ("q25", q[0.25]), ("q75", q[0.75]), ("p95", q[0.95])):
                add(f"dist.{cname}.{col}.{k}", round(float(v), 4), "see measure")
        cap_ms = C.SEV_MAX_PULSE_MS - 1e-6
        add(f"dist.{cname}.pulse_cap_share", round(float((g.pulse_ms >= cap_ms).mean()), 4), "fraction", "share of pulses that reached the maximum pulse length (release rule never met)")
        for rel in RELEASE_VARIANTS_G:
            add(f"release{rel:g}.{cname}.dv_res_kmh.median", round(float(g[f"dv_res_kmh_rel{rel:g}"].median()), 4), "km/h", f"pulse release threshold {rel:g} g instead of {C.SEV_RELEASE_G:g} g")
            add(f"release{rel:g}.{cname}.pulse_cap_share", round(float((g[f"pulse_ms_rel{rel:g}"] >= cap_ms).mean()), 4), "fraction")
        for nm, share in (("rollover_share", float(g.rollover.mean())), ("thiv_hit_share", float(g.thiv_hit.mean()))):
            add(f"dist.{cname}.{nm}", round(share, 4), "fraction")
        for k in range(4):
            add(f"class_share.{cname}.{C.SEV_NAMES[k]}", round(float((g.severity_class == k).mean()), 4), "fraction", "severity class by the Delta-V / ASI / rollover rules")
        for lv in "ABC":
            add(f"asi_level_share.{cname}.{lv}", round(float((g.asi_class == lv).mean()), 4), "fraction", "EN 1317-2 style level from ASI")
        add(f"asi_level_share.{cname}.above_C", round(float((g.asi_class == ">C").mean()), 4), "fraction")
    pd.DataFrame(rows).to_csv(C.TABLES / "severity_vzcrash_distributions.csv", index=False)

    # delta-V and ASI used alone as a crash score, on the de-duplicated test split (model level, as in the report)
    te = t[(t.split == "test") & ~t.event_id.isin(leaky_test_ids())]
    y = (te.label == 0).astype(int)
    add("score_test_events", int(len(te)), "events", "triggered, de-duplicated test split")
    add("score_test_crash_share", round(float(y.mean()), 4), "fraction", "AP of a useless score equals this")
    srows = []
    for col in SCORES + ("peak_a",):
        ap, auc = float(average_precision_score(y, te[col])), float(roc_auc_score(y, te[col]))
        srows.append(dict(score=col, ap=ap, roc_auc=auc))
        add(f"score.{col}.ap", round(ap, 4), "score")
        add(f"score.{col}.roc_auc", round(auc, 4), "score")
    for rel in RELEASE_VARIANTS_G:
        col = f"dv_res_kmh_rel{rel:g}"
        ap, auc = float(average_precision_score(y, te[col])), float(roc_auc_score(y, te[col]))
        srows.append(dict(score=col, ap=ap, roc_auc=auc))
        add(f"score.{col}.ap", round(ap, 4), "score")
        add(f"score.{col}.roc_auc", round(auc, 4), "score")
    pd.DataFrame(srows).to_csv(C.TABLES / "severity_vzcrash_scores.csv", index=False)

    # rank correlations on all triggered events
    corr = t[list(CORR_COLS)].corr(method="spearman")
    corr.to_csv(C.TABLES / "severity_vzcrash_spearman.csv")
    for i, a in enumerate(CORR_COLS):
        for b in CORR_COLS[i + 1:]:
            add(f"spearman.{a}.{b}", round(float(corr.loc[a, b]), 4), "correlation", "Spearman rank correlation over all triggered events")

    # clipping effect (smaller sensor ranges) on delta-V and ASI
    crows = []
    for c in (C.MPU_RANGE_G,) + CLIP_LEVELS_G:
        if c == C.MPU_RANGE_G:
            ch, ach = np.zeros(len(t)), np.zeros(len(t))
        else:
            ch = 100 * (t[f"dv_res_kmh_clip{c:g}"] - t.dv_res_kmh) / t.dv_res_kmh.where(t.dv_res_kmh > 0)
            ach = 100 * (t[f"asi_clip{c:g}"] - t.asi) / t.asi.where(t.asi > 0)
        ch = pd.Series(ch).fillna(0.0)
        ach = pd.Series(ach).fillna(0.0)
        crows.append(dict(clip_g=c, dv_change_median_pct=float(ch.median()), dv_change_p95_abs_pct=float(ch.abs().quantile(0.95)), dv_over_10pct_share=float((ch.abs() > 10).mean()),
                          asi_change_median_pct=float(ach.median()), crash_dv_change_median_pct=float(ch[t.label.to_numpy() == 0].median())))
        for k, v in crows[-1].items():
            if k != "clip_g":
                add(f"clip{c:g}.{k}", round(v, 4), "fraction" if "share" in k else "percent")
    pd.DataFrame(crows).to_csv(C.TABLES / "severity_vzcrash_clipping.csv", index=False)
    add("events_with_axis_over_sensor_range", int((t.peak_a > C.MPU_RANGE_G).sum()), "events", "kept events never exceed the range (corrupt events above it were dropped)")
    extra_analysis(t, add)
    return ent


def extra_analysis(t: pd.DataFrame, add) -> None:
    """Phase 2 additions: rollover false-alarm check, bootstrap intervals (resampling events), class-limit sensitivity."""
    from crashguard import boot as B
    from crashguard import severity_study as SS

    names = [LABELS[k] for k in (0, 1, 2)]
    t = t.copy()
    t["class_name"] = t.label.map(LABELS)
    cap_ms = C.SEV_MAX_PULSE_MS - 1e-6
    for cname in names:
        g = t[t.class_name == cname]
        for col, nm in (("rollover_raw", "raw"), ("rollover_corrected", "corrected")):
            p, lo, hi = B.ci(g[col].to_numpy(dtype=float), np.mean)
            add(f"rollover.{nm}.{cname}.share", round(p, 5), "fraction", "false-alarm check: VZCrash has no rollover labels")
            add(f"rollover.{nm}.{cname}.share_lo", round(lo, 5), "fraction")
            add(f"rollover.{nm}.{cname}.share_hi", round(hi, 5), "fraction")
        add(f"rollover.corrected_applied.{cname}.share", round(float(g.roll_corrected_applied.mean()), 4), "fraction",
            "share of events whose last 0.3 s was quiet enough to give a gravity vector (the correction is applied only then)")
        p, lo, hi = B.ci(g.pulse_ms.to_numpy() >= cap_ms, np.mean)
        add(f"ci.{cname}.pulse_cap_share", round(p, 4), "fraction")
        add(f"ci.{cname}.pulse_cap_share_lo", round(lo, 4), "fraction")
        add(f"ci.{cname}.pulse_cap_share_hi", round(hi, 4), "fraction")
        for col in ("dv_res_kmh", "asi"):
            p, lo, hi = B.ci(g[col].to_numpy(), np.median)
            add(f"ci.{cname}.{col}.median", round(p, 4), "see measure")
            add(f"ci.{cname}.{col}.median_lo", round(lo, 4), "see measure")
            add(f"ci.{cname}.{col}.median_hi", round(hi, 4), "see measure")
        for k in range(4):
            p, lo, hi = B.ci((g.severity_class.to_numpy() == k), np.mean)
            add(f"ci.class_share.{cname}.{C.SEV_NAMES[k]}", round(p, 4), "fraction")
            add(f"ci.class_share.{cname}.{C.SEV_NAMES[k]}_lo", round(lo, 4), "fraction")
            add(f"ci.class_share.{cname}.{C.SEV_NAMES[k]}_hi", round(hi, 4), "fraction")
    nd = t[t.class_name == "normal_driving"]
    over = float(nd.rollover_corrected.mean()) > 0.005
    add("rollover.corrected.normal_driving_over_0p5pct", int(over), "flag", "1 = the drift-corrected flag still fires on more than 0.5% of normal driving, so it stays out of the class rule")
    add("rollover.tilt.normal_driving.median_deg", round(float(nd.tilt_deg.median()), 3), "degrees", "normal driving: median of the largest integrated tilt (uncorrected)")
    add("rollover.tilt_corrected.normal_driving.median_deg", round(float(nd.tilt_corrected_deg.median()), 3), "degrees", "same after the gravity correction")
    add("rollover.tilt.normal_driving.share_ge90", round(float((nd.tilt_deg >= C.ROLLOVER_DEG).mean()), 5), "fraction", "share of normal driving whose uncorrected tilt reaches 90 degrees")
    for cname in names:
        g = t[t.class_name == cname]
        add(f"thiv_x08.{cname}.median", round(float(g.thiv_kmh_x08.median()), 4), "km/h", "THIV with a 0.8 m longitudinal flail distance (docs/05_data_code/SEVERITY.md: one read source gives 0.8 m, the code uses 0.6 m)")
        add(f"thiv_x08.{cname}.hit_share", round(float(g.thiv_hit_x08.mean()), 4), "fraction")
    # class-limit sensitivity on VZCrash, by class
    rows = []
    for cname in names:
        g = t[t.class_name == cname]
        rows += SS.threshold_table(g.dv_res_kmh.to_numpy(), g.asi.to_numpy(), g.rollover.to_numpy(dtype=bool), f"vzcrash_{cname}")
    pd.DataFrame(rows).to_csv(C.TABLES / "severity_vzcrash_threshold_sensitivity.csv", index=False)
    for r in rows:
        for k in range(4):
            add(f"thr.{r['dataset']}.{r['variant']}.share_{C.SEV_NAMES[k]}", round(r[f"share_{C.SEV_NAMES[k]}"], 4), "fraction")


def figures(df: pd.DataFrame) -> None:
    import matplotlib.pyplot as plt

    from crashguard.plots import COLORS, save, style

    style()
    t = df[df.triggered].copy()
    names = [LABELS[k] for k in (0, 1, 2)]
    t["class_name"] = t.label.map(LABELS)
    fig, axes = plt.subplots(1, 4, figsize=(14, 3.8))
    for ax, col, lab in ((axes[0], "dv_res_kmh", "Resultant delta-V (km/h)"), (axes[1], "asi", "ASI"), (axes[2], "thiv_kmh", "THIV (km/h), UNVERIFIED")):
        data = [t[t.class_name == n][col].clip(lower=1e-3).to_numpy() for n in names]
        parts = ax.violinplot([np.log10(d) for d in data], showmedians=True)
        for i, pc in enumerate(parts["bodies"]):
            pc.set_facecolor(COLORS[i])
            pc.set_alpha(0.6)
        ax.set_xticks([1, 2, 3], names, fontsize=7)
        ax.set_ylabel(f"log10 of {lab}")
    share = t.groupby("class_name").severity_class.value_counts(normalize=True).unstack().reindex(names).fillna(0)
    bottom = np.zeros(len(names))
    for k in range(4):
        v = share[k].to_numpy() if k in share else np.zeros(len(names))
        axes[3].bar(names, v, bottom=bottom, color=COLORS[k], label=C.SEV_NAMES[k])
        bottom += v
    axes[3].set_ylabel("Share of triggered events")
    axes[3].legend(fontsize=7)
    axes[3].tick_params(axis="x", labelsize=7)
    fig.suptitle("VZCrash, triggered events: severity measures by class (no severity labels exist, descriptive only)", fontsize=9)
    save(fig, "severity_vzcrash_distributions")

    sc = pd.read_csv(C.TABLES / "severity_vzcrash_scores.csv")
    corr = pd.read_csv(C.TABLES / "severity_vzcrash_spearman.csv", index_col=0)
    cl = pd.read_csv(C.TABLES / "severity_vzcrash_clipping.csv")
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.8))
    x = np.arange(len(sc))
    axes[0].bar(x - 0.2, sc.ap, 0.4, color=COLORS[0], label="AP")
    axes[0].bar(x + 0.2, sc.roc_auc, 0.4, color=COLORS[1], label="ROC-AUC")
    axes[0].set_xticks(x, sc.score, rotation=40, ha="right", fontsize=7)
    axes[0].set_ylabel("Single measure as a crash score (fraction)")
    axes[0].legend(fontsize=7)
    im = axes[1].imshow(corr.to_numpy(), vmin=-1, vmax=1, cmap="RdBu_r")
    axes[1].set_xticks(range(len(corr)), corr.columns, rotation=40, ha="right", fontsize=7)
    axes[1].set_yticks(range(len(corr)), corr.index, fontsize=7)
    for i in range(len(corr)):
        for j in range(len(corr)):
            axes[1].text(j, i, f"{corr.iat[i, j]:.2f}", ha="center", va="center", fontsize=7)
    axes[1].grid(False)
    fig.colorbar(im, ax=axes[1], fraction=0.046)
    axes[1].set_title("Spearman correlation", fontsize=9)
    axes[2].bar([f"+-{c:g} g" for c in cl.clip_g], cl.dv_change_p95_abs_pct, color=COLORS[3])
    axes[2].set_xlabel("Sensor range (clipping level)")
    axes[2].set_ylabel("95th percentile |delta-V change| (%)")
    save(fig, "severity_vzcrash_scores")


def main() -> None:
    C.TABLES.mkdir(parents=True, exist_ok=True)
    df = extract()
    C.PROCESSED.mkdir(parents=True, exist_ok=True)
    df.to_parquet(C.PROCESSED / "severity_vzcrash.parquet")
    ent = analyse(df)
    record_many(ent)
    figures(df)
    print(f"{int(df.triggered.sum())} triggered events of {len(df)}")


if __name__ == "__main__":
    main()
