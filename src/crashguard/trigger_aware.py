"""N15: trigger-aware training (docs/02_preregistration/ALGORITHMS.md fixes the rules before any result).

The detector is a second stage behind a trigger. Three ways to design them together are compared with the baseline (fixed 2.0 g trigger + a separately trained
15-tree depth-6 forest) on the de-duplicated VZCrash splits, at system-level false-alarm rates of 1% and 5% of ALL non-crash events:
  a. joint selection of the trigger level and the decision threshold on validation;
  b. cost-sensitive training: crashes that the config trigger discards are added to the training set as positives (their peak-centred windows), weight g;
  c. a learned trigger: a rule on running features (|a|, jerk, short-window energy) that needs no window buffer.
VZCrash events were already selected on the device by threshold heuristics, so the trigger here is a second stage and the results do not apply to continuous driving.
Everything is chosen on validation; the test split is scored once per method and seed.
"""
from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score

from crashguard import boot as B
from crashguard import config as C
from crashguard import detector_extra as D
from crashguard.data import iter_events
from crashguard.features import _align_gyro, _cut, compute_features
from crashguard.split import leaky_test_ids, load_variant

TARGETS = (0.01, 0.05)
TRIGGER_LEVELS = (1.5, 2.0, 2.5, 3.0)
GAMMAS = (0.0, 0.5, 1.0, 2.0)
P_GRID = (2.0, 2.5, 3.0, 4.0)
J_GRID = (50.0, 100.0, 200.0)  # g/s
E_GRID = (0.5, 1.0, 2.0)  # g^2 s
ENERGY_N = 10  # samples in the energy window
SRC = "results/tables/n15_results.csv"


def candidates() -> list[tuple[float, float | None, float | None]]:
    out = [(p, None, None) for p in P_GRID]
    out += [(p, j, e) for p in P_GRID for j in J_GRID for e in E_GRID]
    return out


def cand_name(c) -> str:
    p, j, e = c
    return f"p{p:g}" if j is None else f"p{p:g}_j{j:g}_e{e:g}"


def running_features(mag: np.ndarray, dt: float = C.DT) -> tuple[np.ndarray, np.ndarray]:
    """Jerk (g/s, from the previous |a|) and the energy of the last ENERGY_N samples (g^2 s) at every sample: the only quantities the learned trigger keeps."""
    jerk = np.zeros(len(mag))
    jerk[1:] = np.abs(np.diff(mag)) / dt
    cs = np.concatenate([[0.0], np.cumsum((mag - 1.0) ** 2 * dt)])
    en = np.zeros(len(mag))
    if len(mag) >= ENERGY_N:
        en[ENERGY_N - 1 :] = cs[ENERGY_N:] - cs[: len(mag) - ENERGY_N + 1]
    return jerk, en


def first_fire(mag: np.ndarray, jerk: np.ndarray, en: np.ndarray, c) -> int | None:
    p, j, e = c
    fire = mag > p
    if j is not None:
        fire = fire | ((jerk >= j) & (en >= e))
    hit = np.flatnonzero(fire)
    return int(hit[0]) if len(hit) else None


def trigger_index(mag: np.ndarray, c, dt: float = C.DT) -> int | None:
    """First sample where |a| > p, or jerk >= j and short-window energy >= e (running quantities only: the previous |a|, the last ENERGY_N squared deviations)."""
    jerk, en = running_features(mag, dt)
    return first_fire(mag, jerk, en, c)


def _flush(rows, wins_a, wins_g, parts):
    if not rows:
        return
    f = pd.DataFrame(compute_features(np.stack(wins_a), np.stack(wins_g)), columns=list(C.FEATURES))
    f.insert(0, "cand", [r[1] for r in rows])
    f.insert(0, "event_id", [r[0] for r in rows])
    parts.append(f)
    rows.clear()
    wins_a.clear()
    wins_g.clear()


def _shard(args: tuple[str, list]) -> pd.DataFrame:
    path_str, cands = args
    rows, wins_a, wins_g, parts = [], [], [], []
    for _split, eid, _label, _vs, _hd, acc, gyro, _gps in iter_events(Path(path_str)):
        n = len(acc)
        if n < 2:
            continue
        raw_peak = float(np.linalg.norm(acc, axis=1).max())
        if raw_peak > C.MPU_RANGE_G:
            continue
        a = np.clip(acc, -C.MPU_RANGE_G, C.MPU_RANGE_G)
        g = np.clip(_align_gyro(gyro, n), -C.MPU_GYRO_RANGE_DPS, C.MPU_GYRO_RANGE_DPS)
        mag = np.linalg.norm(a, axis=1)
        jerk, en = running_features(mag)
        for ci, c in enumerate(cands):
            i0 = first_fire(mag, jerk, en, c)
            if i0 is None:
                continue
            s = i0 - C.PRE_N
            rows.append((eid, ci))
            wins_a.append(_cut(a, s, C.WIN_N).astype(np.float32))
            wins_g.append(_cut(g, s, C.WIN_N).astype(np.float32))
        if len(rows) >= 6000:
            _flush(rows, wins_a, wins_g, parts)
    _flush(rows, wins_a, wins_g, parts)
    if not parts:
        return pd.DataFrame(columns=["event_id", "cand", *C.FEATURES])
    return pd.concat(parts, ignore_index=True)


def extract_candidates(cands, workers: int | None = None) -> pd.DataFrame:
    """Window features of every event under every candidate trigger (only events that the candidate fires on). One pass over the data."""
    files = sorted((C.RAW_DIR / "data").glob("*.parquet"))
    with ProcessPoolExecutor(workers or min(8, os.cpu_count() or 1)) as ex:
        parts = list(ex.map(_shard, [(str(f), cands) for f in files]))
    return pd.concat(parts, ignore_index=True)


def _fit(tr: pd.DataFrame, seed: int, weights: np.ndarray | None = None):
    cols = list(C.FEATURES)
    m = RandomForestClassifier(n_estimators=15, max_depth=6, random_state=seed, n_jobs=-1)
    m.fit(tr[cols].to_numpy(np.float32), tr.y.to_numpy(), sample_weight=weights)
    m.set_params(n_jobs=1)  # deterministic summation order in predict_proba (n_jobs > 1 sums the trees in a thread-dependent order)
    return lambda d: m.predict_proba(d[cols].to_numpy(np.float32))[:, 1]


def _scores(scorer, df: pd.DataFrame) -> np.ndarray:
    return D.score_all(scorer, df)


def eval_split(val: pd.DataFrame, test: pd.DataFrame, scorer, target: float) -> dict:
    """Threshold on validation for the target false-alarm rate; validation and test system recall and false-alarm rate; test scores and predictions."""
    s_va, s_te = _scores(scorer, val), _scores(scorer, test)
    thr = D.threshold_for_fpr(val.y.to_numpy(), s_va, target)
    v, t = D.sys_rates(val.y.to_numpy(), s_va, thr), D.sys_rates(test.y.to_numpy(), s_te, thr)
    return dict(thr=thr, val_recall=v["recall"], val_fpr=v["fpr"], test_recall=t["recall"], test_fpr=t["fpr"], s_te=s_te, pred=(s_te >= thr).astype(int))


def sys_ap(y: np.ndarray, s: np.ndarray) -> float:
    return float(average_precision_score(y, s))


def trigger_rate_by_size(test: pd.DataFrame) -> dict:
    c = test[test.y == 1]
    return {k: float(g.triggered.mean()) for k, g in c.groupby("vehiclesize")}


def frames_for(variant: str):
    tr, va, te = D.frames_full(variant)
    return tr, va, te


def build_candidate_frames(feat: pd.DataFrame, cands) -> dict[int, tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]]:
    """For each candidate: (train triggered, validation all events, test all events) in the same row order as the baseline frames."""
    base = load_variant(f"trig_{C.TRIGGER_G:g}")[["event_id", "split", "label", "vehiclesize", "y"]]
    ids_test = ~base.event_id.isin(leaky_test_ids())
    out = {}
    for ci in range(len(cands)):
        f = feat[feat.cand == ci].drop(columns="cand")
        df = base.merge(f, on="event_id", how="left")
        df["triggered"] = df[C.FEATURES[0]].notna()
        tr = df[(df.split == "train") & df.triggered]
        va = df[df.split == "validation"]
        te = df[(df.split == "test") & df.event_id.isin(base.event_id[ids_test])]
        out[ci] = (tr, va, te)
    return out


def run() -> tuple[pd.DataFrame, dict]:
    seeds = (C.SEED,) + C.SEEDS
    base_tr, base_va, base_te = frames_for(f"trig_{C.TRIGGER_G:g}")
    base_va[base_va.triggered]
    test_ids = base_te.event_id.to_numpy()
    y_te = base_te.y.to_numpy()
    results, arrays = [], {}

    def record(method: str, seed: int, target: float, r: dict, extra: dict | None = None, test_frame: pd.DataFrame | None = None):
        row = dict(method=method, seed=seed, target=target, test_recall=r["test_recall"], test_fpr=r["test_fpr"], val_recall=r["val_recall"], val_fpr=r["val_fpr"],
                   sys_ap=sys_ap(y_te, r["s_te"]))
        if test_frame is not None:
            for k, v in trigger_rate_by_size(test_frame).items():
                row[f"crash_trigger_rate_{k}"] = v
        row.update(extra or {})
        results.append(row)
        arrays[(method, seed, target)] = (r["s_te"], r["pred"])

    # ---- baseline
    for seed in seeds:
        scorer = _fit(base_tr, seed)
        for tgt in TARGETS:
            r = eval_split(base_va, base_te, scorer, tgt)
            record("baseline", seed, tgt, r, dict(trigger_g=C.TRIGGER_G), base_te)

    # ---- a. joint selection of the trigger level and the threshold (selection with seed 42, validation only)
    var_frames = {g: frames_for(f"trig_{g:g}") for g in TRIGGER_LEVELS}
    for g, (_tr, _va, te_g) in var_frames.items():
        assert (te_g.event_id.to_numpy() == test_ids).all()
    choice_a = {}
    for tgt in TARGETS:
        best = None
        for g in TRIGGER_LEVELS:
            tr, va, _te = var_frames[g]
            r = eval_split(va, var_frames[g][2], _fit(tr, C.SEED), tgt)
            key = (r["val_recall"], g == C.TRIGGER_G)
            if best is None or key > best[0]:
                best = (key, g)
        choice_a[tgt] = best[1]
    for seed in seeds:
        for tgt in TARGETS:
            g = choice_a[tgt]
            tr, va, te = var_frames[g]
            record("a_joint", seed, tgt, eval_split(va, te, _fit(tr, seed), tgt), dict(trigger_g=g), te)

    # ---- b. cost-sensitive training: discarded crashes as extra positives (weight gamma), chosen on validation
    peak = load_variant("peak")
    all_tr = load_variant(f"trig_{C.TRIGGER_G:g}")
    all_tr = all_tr[all_tr.split == "train"].copy()
    all_tr["triggered"] = all_tr.triggered.fillna(False).astype(bool)
    discarded = all_tr[(all_tr.y == 1) & ~all_tr.triggered].event_id
    extra = peak[peak.event_id.isin(discarded)].copy()
    extra["triggered"] = True
    extra["y"] = 1
    choice_b = {}
    for tgt in TARGETS:
        best = None
        for gm in GAMMAS:
            tr = pd.concat([base_tr, extra], ignore_index=True) if gm > 0 else base_tr
            w = np.concatenate([np.ones(len(base_tr)), np.full(len(extra), gm)]) if gm > 0 else None
            r = eval_split(base_va, base_te, _fit(tr, C.SEED, w), tgt)
            key = (r["val_recall"], gm == 0.0)
            if best is None or key > best[0]:
                best = (key, gm)
        choice_b[tgt] = best[1]
    for seed in seeds:
        for tgt in TARGETS:
            gm = choice_b[tgt]
            tr = pd.concat([base_tr, extra], ignore_index=True) if gm > 0 else base_tr
            w = np.concatenate([np.ones(len(base_tr)), np.full(len(extra), gm)]) if gm > 0 else None
            record("b_cost_sensitive", seed, tgt, eval_split(base_va, base_te, _fit(tr, seed, w), tgt), dict(gamma=gm, discarded_crashes_added=int(len(extra)) if gm > 0 else 0), base_te)

    # ---- c. learned trigger
    cands = candidates()
    feat = extract_candidates(cands)
    cframes = build_candidate_frames(feat, cands)
    choice_c, cand_scores = {}, []
    for tgt in TARGETS:
        best = None
        for ci, c in enumerate(cands):
            tr, va, te = cframes[ci]
            if len(tr) < 500 or tr.y.nunique() < 2:
                continue
            r = eval_split(va, te, _fit(tr, C.SEED), tgt)
            cand_scores.append(dict(target=tgt, cand=cand_name(c), val_recall=r["val_recall"], val_fpr=r["val_fpr"], trigger_rate_val=float(va.triggered.mean())))
            key = (r["val_recall"], c == (C.TRIGGER_G, None, None))
            if best is None or key > best[0]:
                best = (key, ci)
        choice_c[tgt] = best[1]
    for seed in seeds:
        for tgt in TARGETS:
            ci = choice_c[tgt]
            tr, va, te = cframes[ci]
            record("c_learned_trigger", seed, tgt, eval_split(va, te, _fit(tr, seed), tgt), dict(candidate=cand_name(cands[ci]), trigger_rate_all=float(te.triggered.mean())), te)
    meta = dict(choice_a={str(k): v for k, v in choice_a.items()}, choice_b={str(k): v for k, v in choice_b.items()}, choice_c={str(k): cand_name(cands[v]) for k, v in choice_c.items()},
                cand_scores=pd.DataFrame(cand_scores), y_te=y_te, base_te=base_te)
    return pd.DataFrame(results), dict(arrays=arrays, **meta)


def learned_trigger_cost() -> dict:
    """ANALYTICAL: state and operation count of the learned trigger (per sample), counted from the rule; cycle figures use stated assumptions and are NOT measured."""
    state_bytes = 4 + 4 * ENERGY_N + 4 + 1 + 3 * 4  # previous |a|, ring of squared deviations, running sum, ring index, thresholds p, j, e
    ops = dict(mul=3 + 1 + 1 + 1, add=2 + 1 + 1 + 2, compare=3, sqrt=1)  # |a|^2 (3 mul, 2 add), jerk (sub, abs-free compare), deviation square, ring update, 3 comparisons
    cycles = ops["mul"] + ops["add"] + ops["compare"] + 100 * ops["sqrt"]  # ASSUMPTION, unverified: 1 cycle per FPU add, multiply or compare; 100 cycles for a software square root
    return dict(state_bytes=state_bytes, ops=ops, cycles_assumed=cycles, period_cycles_at_240mhz_100hz=240_000_000 // C.FS_HZ)


def main() -> None:
    from crashguard.results import record_many

    C.TABLES.mkdir(parents=True, exist_ok=True)
    res, meta = run()
    res.to_csv(C.TABLES / "n15_results.csv", index=False)
    meta["cand_scores"].to_csv(C.TABLES / "n15_candidate_scores.csv", index=False)
    ent: list[dict] = []

    def add(name, value, unit, origin="MEASURED_SOFTWARE", notes="", s=SRC):
        ent.append(dict(name=f"n15.{name}", value=value, unit=unit, origin=origin, source_file=s, notes=notes))

    y = meta["y_te"]
    arrays = meta["arrays"]
    for method in ("baseline", "a_joint", "b_cost_sensitive", "c_learned_trigger"):
        for tgt in TARGETS:
            t = f"t{int(tgt * 100)}"
            g = res[(res.method == method) & (res.target == tgt) & res.seed.isin(C.SEEDS)]
            for col in ("test_recall", "test_fpr", "sys_ap", "val_recall"):
                add(f"{method}.{t}.{col}.mean", round(float(g[col].mean()), 5), "fraction", notes="mean over seeds 0-4; de-duplicated test; choices made on validation with seed 42")
                add(f"{method}.{t}.{col}.std", round(float(g[col].std(ddof=1)), 5), "fraction")
            s42 = res[(res.method == method) & (res.target == tgt) & (res.seed == C.SEED)].iloc[0]
            for col in ("test_recall", "test_fpr", "sys_ap"):
                add(f"{method}.{t}.{col}.seed42", round(float(s42[col]), 5), "fraction")
            for col in [c for c in res.columns if c.startswith("crash_trigger_rate_")]:
                add(f"{method}.{t}.{col}", round(float(s42[col]), 5), "fraction", notes="share of test crashes that pass the method's trigger (seed 42 model)")
            if method != "baseline":
                s_b, p_b = arrays[("baseline", C.SEED, tgt)]
                s_m, p_m = arrays[(method, C.SEED, tgt)]
                dr = B.paired_diff(p_b[y == 1].astype(float), p_m[y == 1].astype(float), np.mean)
                dfp = B.paired_diff(p_b[y == 0].astype(float), p_m[y == 0].astype(float), np.mean)
                pack_b, pack_m = np.stack([y, s_b], 1), np.stack([y, s_m], 1)
                dap = B.paired_diff(pack_b, pack_m, lambda a: float(average_precision_score(a[:, 0], a[:, 1])), n_boot=300)
                # seed-averaged paired difference (seeds 0 to 4): the same resampled test events for every seed, the mean over seeds of (method - baseline)
                pb = np.stack([arrays[("baseline", sd, tgt)][1] for sd in C.SEEDS]).astype(float)
                pm = np.stack([arrays[(method, sd, tgt)][1] for sd in C.SEEDS]).astype(float)
                diff_cols = (pm - pb)[:, :]  # seeds x events
                for lab, mask in (("recall", y == 1), ("fpr", y == 0)):
                    cols = diff_cols[:, mask].T  # events x seeds
                    pt, lo, hi = B.ci(cols.mean(axis=1), np.mean)
                    add(f"{method}.{t}.paired_seedavg.d_{lab}", round(pt, 5), "fraction", notes="mean over seeds 0-4 of (method - baseline), same test events, 95% bootstrap interval over events; the decision rule uses this one")
                    add(f"{method}.{t}.paired_seedavg.d_{lab}_lo", round(lo, 5), "fraction")
                    add(f"{method}.{t}.paired_seedavg.d_{lab}_hi", round(hi, 5), "fraction")
                for nm, v in (("d_recall", dr), ("d_fpr", dfp), ("d_sys_ap", dap)):
                    add(f"{method}.{t}.paired.{nm}", round(v[0], 5), "fraction", notes="method minus baseline on the same test events; seed 42; 95% bootstrap interval (1,000 resamples; 300 for AP)")
                    add(f"{method}.{t}.paired.{nm}_lo", round(v[1], 5), "fraction")
                    add(f"{method}.{t}.paired.{nm}_hi", round(v[2], 5), "fraction")
    for k, v in meta["choice_a"].items():
        add(f"choice.a_joint.t{int(float(k) * 100)}.trigger_g", v, "g", notes="selected on validation")
    for k, v in meta["choice_b"].items():
        add(f"choice.b_cost_sensitive.t{int(float(k) * 100)}.gamma", v, "weight", notes="selected on validation")
    for k, v in meta["choice_c"].items():
        add(f"choice.c_learned_trigger.t{int(float(k) * 100)}.candidate", v, "text", notes="selected on validation")
    cost = learned_trigger_cost()
    add("learned_trigger.state_bytes", cost["state_bytes"], "bytes", "ANALYTICAL", "previous |a|, ring of 10 squared deviations, running sum, ring index, three thresholds", "src/crashguard/trigger_aware.py")
    for k, v in cost["ops"].items():
        add(f"learned_trigger.ops_per_sample.{k}", v, "operations", "ANALYTICAL", "counted from the rule; no sample buffer is needed", "src/crashguard/trigger_aware.py")
    add("learned_trigger.cycles_per_sample_assumed", cost["cycles_assumed"], "cycles", "ANALYTICAL", "ASSUMPTION, unverified: 1 cycle per FPU add, multiply or compare and 100 cycles for a software square root; the real cost is NOT_RUN (needs the ESP32)", "src/crashguard/trigger_aware.py")
    add("learned_trigger.cycles_share_of_sample_period", round(cost["cycles_assumed"] / cost["period_cycles_at_240mhz_100hz"], 8), "fraction", "ANALYTICAL", "assumed cycles divided by the cycles available per 100 Hz sample at 240 MHz", "src/crashguard/trigger_aware.py")
    base = meta["base_te"]
    add("test_events", int(len(base)), "events", notes="de-duplicated test events")
    add("test_crashes", int((base.y == 1).sum()), "events")
    record_many(ent, purge_prefixes=("n15.",))
    show = res[res.seed == C.SEED][["method", "target", "test_recall", "test_fpr", "sys_ap"]]
    print(show.round(4).to_string(index=False))
    print({k: meta[k] for k in ("choice_a", "choice_b", "choice_c")})


if __name__ == "__main__":
    main()
