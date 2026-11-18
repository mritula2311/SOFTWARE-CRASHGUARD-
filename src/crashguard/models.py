"""Train and evaluate the five detectors (S2-S5, trigger sweep, vehicle-size robustness).

Rules followed here (CLAUDE.md): splits are the supplied ones, thresholds are chosen on validation only,
each (model, seed) touches the test set once, every number goes to results.json with an origin label.
Two levels are reported: model-level (triggered events only) and system-level (untriggered = predicted negative).
"""
from __future__ import annotations

import os
import warnings
from dataclasses import dataclass

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, precision_recall_curve, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

from crashguard import config as C
from crashguard.data import LABELS
from crashguard.results import record_many
from crashguard.split import leaky_test_ids, load_variant

warnings.filterwarnings("ignore", category=UserWarning)
PRIMARY = f"trig_{C.TRIGGER_G:g}"
MODELS = ("rf15", "rf200", "lr", "gbt", "rule")
PROB_MODELS = ("rf15", "rf200", "lr", "gbt")
MODEL_NAMES = {"rf15": "RF 15 trees, depth 6", "rf200": "RF 200 trees", "lr": "Logistic regression",
               "gbt": "Gradient-boosted trees", "rule": "Rule (peak and duration)"}
ALL_SEEDS = (C.SEED,) + C.SEEDS
KEY_METRICS = ("ap", "f1op_f1", "sys_f1op_recall", "sys_f1op_fpr", "sys_f1op_fpr_near_miss")


def _slog(x):
    return np.sign(x) * np.log1p(np.abs(x))


@dataclass
class RuleDetector:
    """Crash if peak_a >= P and dur_above >= D ms. P and D are tuned on validation only."""

    p: float = 3.0
    d: float = 0.0

    def tune(self, va: pd.DataFrame) -> RuleDetector:
        best = (-1.0, self.p, self.d)
        y = va.y.to_numpy()
        for p in np.arange(2.0, 8.01, 0.25):
            for d in range(0, 301, 10):
                pred = (va.peak_a.to_numpy() >= p) & (va.dur_above.to_numpy() >= d)
                tp = (pred & (y == 1)).sum()
                f1 = 2 * tp / (pred.sum() + (y == 1).sum() + 1e-12)
                if f1 > best[0]:
                    best = (f1, p, d)
        self.p, self.d = best[1], best[2]
        return self

    def score(self, df: pd.DataFrame) -> np.ndarray:
        s = df.peak_a.to_numpy() / self.p
        if self.d > 0:
            s = np.minimum(s, df.dur_above.to_numpy() / self.d)
        return s  # >= 1 means the rule fires


def make_model(name: str, seed: int):
    if name == "rf15":
        return RandomForestClassifier(n_estimators=15, max_depth=6, random_state=seed, n_jobs=-1)
    if name == "rf200":
        return RandomForestClassifier(n_estimators=200, min_samples_leaf=3, random_state=seed, n_jobs=-1)
    if name == "lr":
        return make_pipeline(FunctionTransformer(_slog), StandardScaler(), LogisticRegression(max_iter=2000, random_state=seed))
    if name == "gbt":
        import lightgbm as lgb

        return lgb.LGBMClassifier(n_estimators=300, learning_rate=0.05, num_leaves=31, subsample=0.8, subsample_freq=1,
                                  random_state=seed, verbose=-1, deterministic=True, force_row_wise=True, n_jobs=os.cpu_count())
    raise ValueError(name)


def fit_scorer(name: str, seed: int, cols: list[str], tr: pd.DataFrame, va: pd.DataFrame):
    """Train on ``tr`` (and tune the rule on ``va``). Returns (scorer(df)->score, fitted model or rule)."""
    if name == "rule":
        rule = RuleDetector().tune(va)
        return rule.score, rule
    m = make_model(name, seed)
    m.fit(tr[cols].to_numpy(np.float32), tr.y.to_numpy())
    if hasattr(m, "set_params") and isinstance(m, RandomForestClassifier):
        m.set_params(n_jobs=1)  # predict_proba sums the trees in a thread-dependent order with n_jobs > 1: last-digit differences between runs
    return (lambda d: m.predict_proba(d[cols].to_numpy(np.float32))[:, 1]), m


def op_thresholds(y: np.ndarray, s: np.ndarray) -> tuple[float, float]:
    """(threshold maximising F1, threshold with recall >= 0.95) from validation scores."""
    p, r, t = precision_recall_curve(y, s)
    f1 = 2 * p[:-1] * r[:-1] / (p[:-1] + r[:-1] + 1e-12)
    ok = np.flatnonzero(r[:-1] >= 0.95)
    return float(t[int(np.argmax(f1))]), float(t[ok[-1]] if len(ok) else t[0])


def _rates(pred: np.ndarray, y: np.ndarray, lab: np.ndarray, pre: str) -> dict:
    tp = int((pred & (y == 1)).sum())
    fp = int((pred & (y == 0)).sum())
    pos = int((y == 1).sum())
    prec = tp / (tp + fp) if tp + fp else float("nan")
    rec = tp / pos
    return {f"{pre}precision": prec, f"{pre}recall": rec, f"{pre}f1": 2 * tp / (tp + fp + pos),
            f"{pre}fpr": float(pred[y == 0].mean()), f"{pre}fpr_near_miss": float(pred[lab == 1].mean()),
            f"{pre}fpr_normal": float(pred[lab == 2].mean())}


def level_metrics(y, lab, s, thr_f1, thr_r95, pre: str) -> dict:
    """Metrics at the two validation-chosen thresholds. ``s`` holds -1 for events the trigger did not pass."""
    out = {f"{pre}ap": float(average_precision_score(y, s))}
    out.update(_rates(s >= thr_f1, y, lab, f"{pre}f1op_"))
    out.update(_rates(s >= thr_r95, y, lab, f"{pre}r95op_"))
    return out


def _metrics(te: pd.DataFrame, thr_f1: float, thr_r95: float, prob: bool, pre: str = "") -> dict:
    """Model-level (triggered events) and system-level metrics on a scored test frame."""
    t = te[te.triggered.to_numpy(bool)]
    m = {f"{pre}n_test": len(te), f"{pre}n_test_triggered": len(t), f"{pre}prevalence_triggered": float(t.y.mean()),
         f"{pre}prevalence_all": float(te.y.mean()), f"{pre}roc_auc": float(roc_auc_score(t.y, t.score)),
         f"{pre}brier": float(brier_score_loss(t.y, t.score)) if prob else float("nan")}
    m.update(level_metrics(t.y.to_numpy(), t.label.to_numpy(), t.score.to_numpy(), thr_f1, thr_r95, pre))
    m.update(level_metrics(te.y.to_numpy(), te.label.to_numpy(), te.score.to_numpy(), thr_f1, thr_r95, f"{pre}sys_"))
    return m


def evaluate(scorer, va: pd.DataFrame, te: pd.DataFrame, prob: bool, leaky: set[int]) -> tuple[dict, pd.DataFrame]:
    """Validation thresholds -> single pass over test.

    Primary metrics (no prefix) are on the test set WITHOUT the events that also appear (nearly) in train/validation.
    Metrics with the prefix ``supplied_`` are on the supplied test split, which includes those events.
    Returns (metrics, test frame with scores and a ``leaky`` flag).
    """
    s_va = scorer(va)
    thr_f1, thr_r95 = op_thresholds(va.y.to_numpy(), s_va)
    te = te.copy()
    te["score"] = -1.0
    trig = te.triggered.to_numpy(bool)
    te.loc[trig, "score"] = scorer(te[trig])
    te["leaky"] = te.event_id.isin(leaky)
    m = {"thr_f1": thr_f1, "thr_r95": thr_r95}
    m.update(_metrics(te[~te.leaky], thr_f1, thr_r95, prob))
    m.update(_metrics(te, thr_f1, thr_r95, prob, "supplied_"))
    return m, te


def frames(variant: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df = load_variant(variant)
    df["triggered"] = df.triggered.fillna(False).astype(bool)
    tr = df[(df.split == "train") & df.triggered]
    va = df[(df.split == "validation") & df.triggered]
    te = df[df.split == "test"]
    return tr, va, te


def run_grid(variant: str, models, fsets, seeds, keep: dict | None = None) -> pd.DataFrame:
    """Rows of metrics for every (model, feature set, seed). ``keep`` collects seed-42 artefacts if given."""
    tr, va, te = frames(variant)
    leaky = leaky_test_ids()
    rows = []
    for fs in fsets:
        cols = list(C.FEATURE_SETS[fs])
        for name in models:
            for seed in seeds:
                scorer, mdl = fit_scorer(name, seed, cols, tr, va)
                m, tes = evaluate(scorer, va, te, name in PROB_MODELS, leaky)
                rows.append(dict(variant=variant, fset=fs, model=name, seed=seed, **m))
                if keep is not None and seed == C.SEED:
                    keep[(variant, fs, name)] = (mdl, tes, m)
    return pd.DataFrame(rows)


def summarise(rows: pd.DataFrame) -> pd.DataFrame:
    """Mean and sample std over seeds 0-4, plus the seed-42 value."""
    metrics = [c for c in rows.columns if c not in ("variant", "fset", "model", "seed")]
    out = []
    for (v, fs, mo), g in rows.groupby(["variant", "fset", "model"]):
        rep = g[g.seed.isin(C.SEEDS)]
        s42 = g[g.seed == C.SEED]
        for k in metrics:
            out.append(dict(variant=v, fset=fs, model=mo, metric=k, mean=rep[k].mean(), std=rep[k].std(ddof=1),
                            seed42=float(s42[k].iloc[0]) if len(s42) else np.nan, n_seeds=len(rep)))
    return pd.DataFrame(out)


def to_entries(summary: pd.DataFrame, prefix: str, source: str, only: tuple[str, ...] | None = None) -> list[dict]:
    ent = []
    for r in summary.itertuples():
        if only and r.metric not in only:
            continue
        for stat in ("mean", "std", "seed42"):
            v = getattr(r, stat)
            if v is None or (isinstance(v, float) and np.isnan(v)):
                continue
            ent.append(dict(name=f"{prefix}.{r.variant}.{r.fset}.{r.model}.{r.metric}.{stat}", value=round(float(v), 5),
                            unit="count" if r.metric.startswith(("n_", "supplied_n_")) else "score", origin="MEASURED_SOFTWARE",
                            source_file=source, notes=f"mean and sample std over seeds {C.SEEDS}; seed42 is the single run with seed 42"))
    return ent


def wide(summary: pd.DataFrame, metrics: tuple[str, ...]) -> pd.DataFrame:
    s = summary[summary.metric.isin(metrics)].copy()
    s["val"] = s.apply(lambda r: f"{r['mean']:.4f} ± {r['std']:.4f}", axis=1)
    return s.pivot_table(index=["variant", "fset", "model"], columns="metric", values="val", aggfunc="first").reset_index()


def size_sweep(seeds=C.SEEDS) -> pd.DataFrame:
    """S4: AP against number of tree nodes (MEASURED) and estimated bytes (ANALYTICAL)."""
    tr, va, te = frames(PRIMARY)
    cols = list(C.FEATURES)
    tet = te[te.triggered & ~te.event_id.isin(leaky_test_ids())]
    rows = []
    for depth in (4, 6, 8):
        for n in (1, 3, 5, 10, 15, 30, 60, 100, 200):
            for seed in seeds:
                m = RandomForestClassifier(n_estimators=n, max_depth=depth, random_state=seed, n_jobs=-1)
                m.fit(tr[cols].to_numpy(np.float32), tr.y)
                nodes = int(sum(t.tree_.node_count for t in m.estimators_))
                rows.append(dict(trees=n, depth=depth, seed=seed, nodes=nodes, bytes_est=nodes * C.NODE_BYTES,
                                 ap=float(average_precision_score(tet.y, m.predict_proba(tet[cols].to_numpy(np.float32))[:, 1]))))
    return pd.DataFrame(rows)


def depth_sweep(seeds=C.SEEDS) -> pd.DataFrame:
    """Trees x depth grid scored on the VALIDATION split only: validation AP, node count, estimated flash (ANALYTICAL), C header size.

    The test set is not touched here. The chosen configuration is scored on test once, in ``chosen_test_ap``.
    """
    import tempfile
    from pathlib import Path

    from crashguard.export_c import write_header

    tr, va, _ = frames(PRIMARY)
    cols = list(C.FEATURES)
    rows = []
    with tempfile.TemporaryDirectory() as d:
        for trees in (10, 15, 20):
            for depth in (6, 7, 8, 9, 10):
                for seed in seeds:
                    m = RandomForestClassifier(n_estimators=trees, max_depth=depth, random_state=seed, n_jobs=-1)
                    m.fit(tr[cols].to_numpy(np.float32), tr.y)
                    h = Path(d) / f"h_{trees}_{depth}_{seed}.h"
                    info = write_header(m, h)
                    rows.append(dict(trees=trees, depth=depth, seed=seed, nodes=info["nodes"], flash_est=info["nodes"] * C.NODE_BYTES + 2 * trees,
                                     header_bytes=h.stat().st_size,
                                     ap_val=float(average_precision_score(va.y, m.predict_proba(va[cols].to_numpy(np.float32))[:, 1]))))
    return pd.DataFrame(rows)


def pareto_and_recommend(runs: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Seed-average the grid, mark the Pareto front (higher validation AP, lower flash) and pick one configuration.

    Uses validation AP only. Rule (fixed before looking at any result): among Pareto configurations whose estimated flash is at most
    COMFORT_FRACTION of the app partition, take the smallest one whose validation AP is within AP_TOLERANCE of the best validation AP
    in the grid; if none qualifies, take the highest validation AP under the flash limit.
    """
    g = runs.groupby(["trees", "depth"]).agg(ap_val_mean=("ap_val", "mean"), ap_val_std=("ap_val", "std"), nodes=("nodes", "mean"),
                                             flash_est=("flash_est", "mean"), header_bytes=("header_bytes", "mean")).reset_index()
    g["pareto"] = [not ((g.ap_val_mean >= r.ap_val_mean) & (g.flash_est <= r.flash_est) & ((g.ap_val_mean > r.ap_val_mean) | (g.flash_est < r.flash_est))).any()
                   for r in g.itertuples()]
    limit = C.COMFORT_FRACTION * C.APP_PARTITION_BYTES
    ok = g[g.pareto & (g.flash_est <= limit) & (g.ap_val_mean >= g.ap_val_mean.max() - C.AP_TOLERANCE)]
    pick = (ok.sort_values("flash_est").iloc[0] if len(ok) else g[g.flash_est <= limit].sort_values("ap_val_mean", ascending=False).iloc[0])
    g["recommended"] = (g.trees == pick.trees) & (g.depth == pick.depth)
    return g, dict(trees=int(pick.trees), depth=int(pick.depth), flash_limit=float(limit), fell_back=not len(ok))


def chosen_test_ap(trees: int, depth: int, seeds=C.SEEDS) -> np.ndarray:
    """Test AP (de-duplicated, triggered events) of the configuration chosen on validation. Called once, after the choice."""
    tr, _, te = frames(PRIMARY)
    cols = list(C.FEATURES)
    tet = te[te.triggered & ~te.event_id.isin(leaky_test_ids())]
    out = []
    for seed in seeds:
        m = RandomForestClassifier(n_estimators=trees, max_depth=depth, random_state=seed, n_jobs=-1)
        m.fit(tr[cols].to_numpy(np.float32), tr.y)
        out.append(float(average_precision_score(tet.y, m.predict_proba(tet[cols].to_numpy(np.float32))[:, 1])))
    return np.array(out)


def lovso(models=("rf15", "rf200", "lr", "gbt"), seeds=C.SEEDS) -> pd.DataFrame:
    """Leave one vehicle-size category out. Train/val from the other categories, test = the held-out category."""
    tr0, va0, _ = frames(PRIMARY)
    df = load_variant(PRIMARY)
    df["triggered"] = df.triggered.fillna(False).astype(bool)
    cols = list(C.FEATURES)
    rows = []
    for held in ("Light", "Medium", "Heavy", "Unknown"):
        tr, va = tr0[tr0.vehiclesize != held], va0[va0.vehiclesize != held]
        te = df[df.vehiclesize == held]
        for name in models:
            for seed in seeds:
                scorer, _ = fit_scorer(name, seed, cols, tr, va)
                m, _ = evaluate(scorer, va, te, name in PROB_MODELS, set())
                rows.append(dict(held_out=held, model=name, seed=seed, **{k: m[k] for k in ("ap", "f1op_f1", "sys_f1op_recall", "sys_f1op_fpr", "sys_f1op_fpr_near_miss", "n_test")}))
    return pd.DataFrame(rows)


def category_ap(artifacts: dict) -> pd.DataFrame:
    """AP of the standard test set split by vehicle-size category (same models, seed 42), for comparison with LOVSO."""
    rows = []
    for (v, fs, name), (_, tes, _) in artifacts.items():
        if v != PRIMARY or fs != "all" or name not in PROB_MODELS:
            continue
        t = tes[tes.triggered & ~tes.leaky]
        for cat, g in t.groupby("vehiclesize"):
            rows.append(dict(model=name, category=cat, ap=float(average_precision_score(g.y, g.score)), n=len(g)))
    return pd.DataFrame(rows)


def main() -> None:
    C.TABLES.mkdir(parents=True, exist_ok=True)
    C.PROCESSED.mkdir(parents=True, exist_ok=True)
    art: dict = {}
    entries: list[dict] = []
    tdir = "results/tables"

    # S2 primary comparison (all features) and S3 ablations
    a = run_grid(PRIMARY, MODELS, ["all"], ALL_SEEDS, keep=art)
    b = run_grid(PRIMARY, [m for m in PROB_MODELS], ["no_gyro", "scale_free"], ALL_SEEDS, keep=art)
    s_a, s_b = summarise(a), summarise(b)
    s_a.to_csv(C.TABLES / "s2_model_comparison_long.csv", index=False)
    wide(s_a, ("ap", "roc_auc", "f1op_precision", "f1op_recall", "f1op_f1", "r95op_fpr", "brier")).to_csv(C.TABLES / "s2_model_comparison_model_level.csv", index=False)
    wide(s_a, ("sys_ap", "sys_f1op_recall", "sys_f1op_fpr", "sys_f1op_fpr_near_miss", "sys_f1op_fpr_normal", "sys_r95op_recall", "sys_r95op_fpr", "sys_r95op_fpr_near_miss", "supplied_ap", "supplied_sys_f1op_recall", "supplied_sys_f1op_fpr", "supplied_sys_f1op_fpr_near_miss")).to_csv(C.TABLES / "s2_model_comparison_system_level.csv", index=False)
    entries += to_entries(s_a, "s2", f"{tdir}/s2_model_comparison_long.csv")
    s_ab = pd.concat([s_a[s_a.model.isin(PROB_MODELS)], s_b])
    s_ab.to_csv(C.TABLES / "s3_ablation_long.csv", index=False)
    wide(s_ab, ("ap", "f1op_f1", "sys_f1op_recall", "sys_f1op_fpr")).to_csv(C.TABLES / "s3_ablation.csv", index=False)
    entries += to_entries(s_b, "s3", f"{tdir}/s3_ablation.csv", KEY_METRICS)

    # Derived comparisons used in the report (differences of seed-averaged results from this run)
    mean = {(r.fset, r.model, r.metric): r.mean for r in s_ab.itertuples()}
    for big in ("rf200", "gbt"):
        for met in ("ap", "f1op_f1", "sys_f1op_recall", "sys_f1op_fpr"):
            entries.append(dict(name=f"gap.{big}_minus_rf15.{met}", value=round(float(mean[("all", big, met)] - mean[("all", "rf15", met)]), 5), unit="score",
                                origin="MEASURED_SOFTWARE", source_file=f"{tdir}/s2_model_comparison_long.csv",
                                notes=f"{big} minus the 15-tree forest, seed-averaged, de-duplicated test; the cost of fitting on the ESP32"))
    for mo in PROB_MODELS:
        ap_all, ap_sf = mean[("all", mo, "ap")], mean[("scale_free", mo, "ap")]
        entries.append(dict(name=f"scalefree.{mo}.ap_kept_share", value=round(float(ap_sf / ap_all), 5), unit="fraction", origin="MEASURED_SOFTWARE",
                            source_file=f"{tdir}/s3_ablation_long.csv", notes="AP with the 5 scale-free features divided by AP with all 14"))
        entries.append(dict(name=f"scalefree.{mo}.ap_drop", value=round(float(ap_all - ap_sf), 5), unit="score", origin="MEASURED_SOFTWARE",
                            source_file=f"{tdir}/s3_ablation_long.csv", notes="AP with all 14 minus AP with the 5 scale-free features"))

    # Trigger sweep (RF 15 trees) and the secondary peak-centred window
    sweep = [a[(a.model == "rf15")]] + [run_grid(f"trig_{g:g}", ["rf15"], ["all"], ALL_SEEDS) for g in C.TRIGGER_SWEEP_G if f"trig_{g:g}" != PRIMARY]
    s_sw = summarise(pd.concat(sweep))
    s_sw.to_csv(C.TABLES / "trigger_sweep_long.csv", index=False)
    entries += to_entries(s_sw, "trigger_sweep", f"{tdir}/trigger_sweep_long.csv", KEY_METRICS)
    pk = run_grid("peak", MODELS, ["all"], ALL_SEEDS)
    s_pk = summarise(pk)
    s_pk.to_csv(C.TABLES / "peak_window_long.csv", index=False)
    entries += to_entries(s_pk, "peak_window", f"{tdir}/peak_window_long.csv", KEY_METRICS)

    # S4 size, LOVSO
    sz = size_sweep()
    sz.to_csv(C.TABLES / "s4_size_vs_ap_runs.csv", index=False)
    g = sz.groupby(["depth", "trees"]).agg(nodes=("nodes", "mean"), bytes_est=("bytes_est", "mean"), ap_mean=("ap", "mean"), ap_std=("ap", "std")).reset_index()
    g.to_csv(C.TABLES / "s4_size_vs_ap.csv", index=False)
    for r in g.itertuples():
        base = f"s4.depth{r.depth}.trees{r.trees}"
        entries += [dict(name=f"{base}.ap.mean", value=round(r.ap_mean, 5), unit="score", origin="MEASURED_SOFTWARE", source_file=f"{tdir}/s4_size_vs_ap.csv", notes="model-level test AP, mean over seeds 0-4"),
                    dict(name=f"{base}.ap.std", value=round(r.ap_std, 5), unit="score", origin="MEASURED_SOFTWARE", source_file=f"{tdir}/s4_size_vs_ap.csv"),
                    dict(name=f"{base}.nodes", value=round(r.nodes, 1), unit="nodes", origin="MEASURED_SOFTWARE", source_file=f"{tdir}/s4_size_vs_ap.csv", notes="mean total node count"),
                    dict(name=f"{base}.bytes_est", value=round(r.bytes_est, 1), unit="bytes", origin="ANALYTICAL", source_file=f"{tdir}/s4_size_vs_ap.csv", notes=f"nodes x {C.NODE_BYTES} bytes per node; host estimate, not an ESP32 compile report")]
    ds = depth_sweep()
    ds.to_csv(C.TABLES / "s4b_depth_sweep_runs.csv", index=False)
    dg, rec = pareto_and_recommend(ds)
    dg.to_csv(C.TABLES / "s4b_depth_sweep.csv", index=False)
    srcb = f"{tdir}/s4b_depth_sweep.csv"
    for r in dg.itertuples():
        base = f"s4b.t{r.trees}.d{r.depth}"
        entries += [dict(name=f"{base}.ap_val.mean", value=round(r.ap_val_mean, 5), unit="score", origin="MEASURED_SOFTWARE", source_file=srcb, notes="VALIDATION split, model level, mean over seeds 0-4; the test set is not used for this choice"),
                    dict(name=f"{base}.ap_val.std", value=round(r.ap_val_std, 5), unit="score", origin="MEASURED_SOFTWARE", source_file=srcb),
                    dict(name=f"{base}.nodes", value=round(r.nodes, 1), unit="nodes", origin="MEASURED_SOFTWARE", source_file=srcb),
                    dict(name=f"{base}.flash_est", value=round(r.flash_est, 1), unit="bytes", origin="ANALYTICAL", source_file=srcb, notes=f"nodes x {C.NODE_BYTES} bytes + 2 bytes per tree root; host estimate, not an ESP32 compile report"),
                    dict(name=f"{base}.header_bytes", value=round(r.header_bytes, 1), unit="bytes", origin="MEASURED_SOFTWARE", source_file=srcb, notes="size of the generated C source file (text), not flash"),
                    dict(name=f"{base}.max_comparisons", value=int(r.trees * r.depth), unit="comparisons", origin="ANALYTICAL", source_file=srcb, notes="trees x depth: most feature comparisons in one predict_prob call"),
                    dict(name=f"{base}.pareto", value=bool(r.pareto), unit="bool", origin="MEASURED_SOFTWARE", source_file=srcb, notes="no other configuration has at least the AP and at most the flash, with one strictly better")]
    ct = chosen_test_ap(rec["trees"], rec["depth"])
    entries += [dict(name="s4b.chosen.ap_test.mean", value=round(float(ct.mean()), 5), unit="score", origin="MEASURED_SOFTWARE", source_file=srcb,
                     notes="de-duplicated test, scored once for the configuration chosen on validation, mean over seeds 0-4"),
                dict(name="s4b.chosen.ap_test.std", value=round(float(ct.std(ddof=1)), 5), unit="score", origin="MEASURED_SOFTWARE", source_file=srcb),
                dict(name="s4b.chosen.ap_test.seed_count", value=int(len(ct)), unit="seeds", origin="MEASURED_SOFTWARE", source_file=srcb)]
    entries += [dict(name="s4b.recommended.trees", value=rec["trees"], unit="trees", origin="MEASURED_SOFTWARE", source_file=srcb, notes="recommendation only; the deployed model is unchanged"),
                dict(name="s4b.recommended.depth", value=rec["depth"], unit="depth", origin="MEASURED_SOFTWARE", source_file=srcb),
                dict(name="s4b.flash_comfort_limit", value=rec["flash_limit"], unit="bytes", origin="ANALYTICAL", source_file=srcb,
                     notes=f"{C.COMFORT_FRACTION:g} of an assumed {C.APP_PARTITION_BYTES} byte app partition"),
                dict(name="s4b.rule_fell_back", value=bool(rec["fell_back"]), unit="bool", origin="MEASURED_SOFTWARE", source_file=srcb, notes="true when no Pareto configuration met both the flash and the AP-tolerance condition"),
                dict(name="s4b.ap_tolerance", value=C.AP_TOLERANCE, unit="score", origin="ANALYTICAL", source_file=srcb, notes="selection rule constant")]
    lv = lovso()
    lv.to_csv(C.TABLES / "lovso_runs.csv", index=False)
    lvs = lv.groupby(["held_out", "model"]).agg(**{f"{k}_mean": (k, "mean") for k in KEY_METRICS}, **{f"{k}_std": (k, "std") for k in KEY_METRICS}, n_test=("n_test", "first")).reset_index()
    lvs.to_csv(C.TABLES / "lovso.csv", index=False)
    cat = category_ap(art)
    cat.to_csv(C.TABLES / "ap_by_vehicle_size_standard_test.csv", index=False)
    for r in lvs.itertuples():
        for k in KEY_METRICS:
            for st in ("mean", "std"):
                entries.append(dict(name=f"lovso.{r.held_out}.{r.model}.{k}.{st}", value=round(float(getattr(r, f'{k}_{st}')), 5), unit="score", origin="MEASURED_SOFTWARE",
                                    source_file=f"{tdir}/lovso.csv", notes="held-out vehicle-size category; trained on the others; seeds 0-4"))
    for r in cat.itertuples():
        entries.append(dict(name=f"ap_by_size.{r.category}.{r.model}", value=round(r.ap, 5), unit="score", origin="MEASURED_SOFTWARE", source_file=f"{tdir}/ap_by_vehicle_size_standard_test.csv", notes=f"standard test split, seed 42, {r.n} triggered events"))

    # Seed-42 artefacts: PR curves, calibration, 3-class table, error analysis, saved RF15
    rf_model, rf_te, rf_m = art[(PRIMARY, "all", "rf15")]
    joblib.dump({"model": rf_model, "thr_f1": rf_m["thr_f1"], "thr_r95": rf_m["thr_r95"], "features": list(C.FEATURES)}, C.PROCESSED / "rf15_seed42.joblib")
    curves, calib = [], []
    for name in MODELS:
        _, tes, _ = art[(PRIMARY, "all", name)]
        t = tes[tes.triggered & ~tes.leaky]
        p, r, th = precision_recall_curve(t.y, t.score)
        idx = np.unique(np.linspace(0, len(p) - 1, 400).astype(int))
        curves.append(pd.DataFrame(dict(model=name, precision=p[idx], recall=r[idx])))
        if name in PROB_MODELS:
            fo, mp = calibration_curve(t.y, t.score, n_bins=10, strategy="uniform")
            calib.append(pd.DataFrame(dict(model=name, mean_predicted=mp, fraction_positive=fo)))
    pd.concat(curves).to_csv(C.TABLES / "s2_pr_curves_seed42.csv", index=False)
    pd.concat(calib).to_csv(C.TABLES / "s5_calibration_seed42.csv", index=False)
    te = rf_te[~rf_te.leaky]
    cm = []
    for lab, cname in LABELS.items():
        g = te[te.label == lab]
        nt = int((~g.triggered).sum())
        pp = int((g.triggered & (g.score >= rf_m["thr_f1"])).sum())
        cm.append(dict(true_class=cname, not_triggered=nt, triggered_pred_negative=int(len(g) - nt - pp), triggered_pred_crash=pp))
        for k, v in (("not_triggered", nt), ("triggered_pred_negative", len(g) - nt - pp), ("triggered_pred_crash", pp)):
            entries.append(dict(name=f"confusion3.rf15.{cname}.{k}", value=int(v), unit="events", origin="MEASURED_SOFTWARE", source_file=f"{tdir}/s2_confusion_3class_rf15_seed42.csv",
                                notes="de-duplicated test split, RF15 seed 42, threshold chosen on validation (max F1)"))
    pd.DataFrame(cm).to_csv(C.TABLES / "s2_confusion_3class_rf15_seed42.csv", index=False)
    tt = te[te.triggered]
    fcols = ["event_id", "label", "vehiclesize", "score", "peak_a", "dur_above", "rms_a", "jerk_peak", "gyro_peak"]
    fp = tt[(tt.y == 0)].nlargest(20, "score")[fcols].assign(cls=lambda d: d.label.map(LABELS))
    fn = tt[(tt.y == 1)].nsmallest(20, "score")[fcols].assign(cls=lambda d: d.label.map(LABELS))
    fp.to_csv(C.TABLES / "error_analysis_top20_false_positives.csv", index=False)
    fn.to_csv(C.TABLES / "error_analysis_top20_false_negatives.csv", index=False)
    entries += [dict(name="errors.fp_top20_near_miss_count", value=int((fp.label == 1).sum()), unit="events", origin="MEASURED_SOFTWARE", source_file=f"{tdir}/error_analysis_top20_false_positives.csv", notes="RF15 seed 42, highest-scoring negatives among triggered test events"),
                dict(name="errors.fn_top20_peak_a_median", value=round(float(fn.peak_a.median()), 4), unit="g", origin="MEASURED_SOFTWARE", source_file=f"{tdir}/error_analysis_top20_false_negatives.csv", notes="RF15 seed 42, lowest-scoring triggered crashes"),
                dict(name="errors.crashes_not_triggered_test", value=int((~te[te.y == 1].triggered).sum()), unit="events", origin="MEASURED_SOFTWARE", source_file=f"{tdir}/s2_confusion_3class_rf15_seed42.csv", notes=f"trigger {C.TRIGGER_G:g} g")]
    record_many(entries)
    from crashguard.figures import make_figures

    make_figures()
    print(wide(s_a, ("ap", "f1op_f1", "sys_f1op_recall", "sys_f1op_fpr")).to_string())


if __name__ == "__main__":
    main()
