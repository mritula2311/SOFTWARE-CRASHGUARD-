"""L3 (docs/02_preregistration/PREREGISTRATION_V16.md section 5 with addendum A1): wake-on-motion with a pre-trigger sensor FIFO (MEASURED_SOFTWARE for detection, ANALYTICAL for energy).

    python -m crashguard.r5_l3 build        # B-arm windows of every triggered VZCrash event and the active shares of the normal-driving validation events -> data/processed/r5_l3_cache.pkl
    python -m crashguard.r5_l3 dev          # development iterations (at most 5) on train (fit) and validation (threshold, selection)
    python -m crashguard.r5_l3 freeze
    python -m crashguard.r5_l3 held         # held-out run, once, on HALF0 of the test split; keys r5.l3.*

Arms. A = always on, accelerometer and gyro at 100 Hz (the repository pipeline). B = accelerometer only in idle (FIFO of 1,024 bytes = 170 samples of 6 bytes), gyro in standby, MCU in light sleep; the motion
interrupt fires at the earliest sample whose deviation of |a| from the mean of the previous 0.5 s exceeds ``T_MOT``; the gyro delivers valid samples ``L_GYRO`` ms after the interrupt (zero before). B100 keeps the
accelerometer at 100 Hz in idle; B25 and B10 hold the idle accelerometer at 25 and 10 Hz (zero-order hold) until the interrupt. An event whose deviation never exceeds ``T_MOT`` up to its 2 g trigger sample is
missed by B. Energy: ``energy_ratio`` below, datasheet currents with page numbers in ``CURRENTS``. Nothing here reads ``data/hardware``.
"""
from __future__ import annotations

import json
import math
import pickle
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from crashguard import config as C

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data" / "processed" / "r5_l3_cache.pkl"
FS = 100
HIST = 50  # samples (0.5 s) of the running mean of the interrupt rule
HOLD = 200  # samples (2 s) the interrupt stays asserted for the active share
FIFO_BYTES, SAMPLE_BYTES_ACC = 1024, 6
FIFO_SAMPLES = FIFO_BYTES // SAMPLE_BYTES_ACC  # 170
SEED, NB = 42, 2000
# (name, accelerometer idle step in samples, T_MOT in g, L_GYRO in ms)
COMBOS = [("b100_t05_l30", 1, 0.5, 30), ("b100_t03_l30", 1, 0.3, 30), ("b100_t10_l30", 1, 1.0, 30), ("b100_t05_l70", 1, 0.5, 70), ("b25_t05_l30", 4, 0.5, 30), ("b10_t05_l30", 10, 0.5, 30)]
T_MOTS = (0.3, 0.5, 1.0)
# Datasheet currents (mA). MPU-6050 Rev 3.3 page 14: gyroscope + accelerometer (DMP disabled) 3.8 mA, accelerometer only 0.5 mA. ESP32 datasheet v5.3 page 30 (Table 4-2): Modem-sleep, 80 MHz, dual-core
# 20 to 31 mA (the CPU running, radio off; the lower value is the primary and the conservative choice for the ratio), Light-sleep 0.8 mA.
CURRENTS = dict(sensor_full=3.8, sensor_acc_only=0.5, mcu_active_lo=20.0, mcu_active_hi=31.0, mcu_light_sleep=0.8)


@dataclass(frozen=True)
class L3Params:
    t_mot: float = 0.5  # development item (g): 0.3, 0.5, 1.0
    l_gyro_ms: int = 30  # development item: 30 (datasheet) or 70
    retrain: bool = True  # development item: B windows scored with a forest retrained on B windows (V16 5.1 default) or with the frozen forest of A
    alpha: float = 0.01


ITERATIONS = [L3Params(), L3Params(t_mot=0.3), L3Params(t_mot=1.0), L3Params(l_gyro_ms=70), L3Params(retrain=False)]


def combo_name(p: L3Params, step: int = 1) -> str:
    return f"b{100 // step}_t{int(round(p.t_mot * 10)):02d}_l{p.l_gyro_ms}"


# ------------------------------------------------------------------------------------------------ the interrupt and the stitched window
def deviation(acc: np.ndarray) -> np.ndarray:
    """Deviation (g) of |a| from the mean of the previous ``HIST`` samples. Sample 0 has no history: its reference is 1 g (the gravity prior), so an event that starts inside the impact still wakes the node
    (a replay rule fixed before the initial development run and recorded in DECISIONS.md; without it the 0.4% of events whose first sample is above 2 g would count as missed for no physical reason)."""
    m = np.linalg.norm(acc, axis=1)
    c = np.concatenate([[0.0], np.cumsum(m)])
    i = np.arange(len(m))
    lo = np.maximum(i - HIST, 0)
    cnt = np.maximum(i - lo, 1)
    prev = (c[i] - c[lo]) / cnt
    d = np.abs(m - prev)
    d[0] = abs(m[0] - 1.0)
    return d


def awake_mask(acc: np.ndarray, t_mot: float, hold: int = HOLD) -> np.ndarray:
    """Samples at which the MCU is awake: the interrupt is asserted (deviation above ``t_mot``) and held for ``hold`` samples after each assertion; then the node is idle again."""
    a = deviation(acc) > t_mot
    if not a.any():
        return np.zeros(len(a), bool)
    last = np.maximum.accumulate(np.where(a, np.arange(len(a)), -10**9))
    return (np.arange(len(a)) - last) < hold


def interrupt_index(acc: np.ndarray, t_mot: float, i0: int, hold: int = HOLD) -> int:
    """Start of the awake period that contains the trigger sample ``i0`` (the wake-up sample of the node for this event), or -1 if the node is idle at ``i0``. A period lasts until ``hold``
    samples after the last assertion, so an earlier bump more than ``hold`` samples before the event does not leave the node awake (review finding 1, fixed before any development run)."""
    m = awake_mask(acc, t_mot, hold)
    if not m[i0]:
        return -1
    j = i0
    while j > 0 and m[j - 1]:
        j -= 1
    return int(j)


def active_share(acc: np.ndarray, t_mot: float, hold: int = HOLD) -> float:
    """Share of the samples at which the MCU is awake (``awake_mask``)."""
    return float(awake_mask(acc, t_mot, hold).mean())


def interrupt_detected(i_m: int, i0: int) -> bool:
    """B detects an event only if its interrupt fired at or before the 2 g trigger sample (a later interrupt is a missed event)."""
    return 0 <= i_m <= i0


def stitch_window(acc: np.ndarray, gyro: np.ndarray, i0: int, i_m: int, step: int, n_gyro: int) -> tuple[np.ndarray, np.ndarray, int]:
    """Detector window (PRE_N + POST_N samples starting at i0 - PRE_N) as the node holds it: accelerometer samples before the interrupt at the idle rate (every ``step``-th sample, zero-order hold),
    100 Hz from the interrupt; gyro samples zero before ``i_m + n_gyro``. Also returns the number of FIFO samples used before the interrupt."""
    n = len(acc)
    j = np.clip(np.arange(i0 - C.PRE_N, i0 - C.PRE_N + C.WIN_N), 0, n - 1)
    a_idx = np.where(j < i_m, (j // step) * step, j)
    wa = acc[a_idx]
    wg = np.where((j >= i_m + n_gyro)[:, None], gyro[j], 0.0)
    fifo_used = int(max(0, min(i_m, i0 + C.POST_N) - (i0 - C.PRE_N)))
    return wa, wg, fifo_used


# ------------------------------------------------------------------------------------------------ cache
def _shard(path_str: str) -> dict:
    from crashguard import features as F
    from crashguard.data import iter_events

    ids, split, label, i0s, imiss, wins_a, wins_g, which, shares = [], [], [], [], [], {n: [] for n, *_ in COMBOS}, {n: [] for n, *_ in COMBOS}, {n: [] for n, *_ in COMBOS}, {}
    for sp, eid, lab, _vs, _hd, acc, gyro, _gps in iter_events(Path(path_str)):
        n = len(acc)
        if n < 2:
            continue
        raw_peak = float(np.linalg.norm(acc, axis=1).max())
        if not np.isfinite(raw_peak) or raw_peak > C.MPU_RANGE_G:
            continue
        a = np.clip(acc, -C.MPU_RANGE_G, C.MPU_RANGE_G)
        if sp == "validation" and lab == 2:
            shares[int(eid)] = [active_share(a, t) for t in T_MOTS]
        hit = np.flatnonzero(np.linalg.norm(a, axis=1) > C.TRIGGER_G)
        if not len(hit):
            continue
        i0 = int(hit[0])
        g = np.clip(F._align_gyro(gyro, n), -C.MPU_GYRO_RANGE_DPS, C.MPU_GYRO_RANGE_DPS)
        ims = {t: interrupt_index(a, t, i0) for t in T_MOTS}
        ids.append(int(eid)), split.append(sp), label.append(int(lab)), i0s.append(i0), imiss.append([ims[t] for t in T_MOTS])
        for name, step, t, lms in COMBOS:
            im = ims[t]
            ok = interrupt_detected(im, i0)
            if ok:
                wa, wg, _f = stitch_window(a, g, i0, im, step, int(math.ceil(lms / 10.0)))
            else:
                wa, wg = np.zeros((C.WIN_N, 3)), np.zeros((C.WIN_N, 3))
            wins_a[name].append(wa.astype(np.float32)), wins_g[name].append(wg.astype(np.float32)), which[name].append(ok)
    feats = {}
    for name, *_ in COMBOS:
        feats[name] = F.compute_features(np.stack(wins_a[name]), np.stack(wins_g[name])).astype(np.float32) if ids else np.zeros((0, len(C.FEATURES)), np.float32)
    return dict(event_id=np.array(ids, np.int64), split=np.array(split), label=np.array(label, np.int8), i0=np.array(i0s), i_m=np.array(imiss), detected={k: np.array(v) for k, v in which.items()}, feats=feats, shares=shares)


def build(workers: int | None = None) -> None:
    import os

    files = sorted((C.RAW_DIR / "data").glob("*.parquet"))
    workers = workers or min(8, os.cpu_count() or 1)
    with ProcessPoolExecutor(workers) as ex:
        parts = list(ex.map(_shard, [str(f) for f in files]))
    out = dict(event_id=np.concatenate([p["event_id"] for p in parts]), split=np.concatenate([p["split"] for p in parts]), label=np.concatenate([p["label"] for p in parts]),
               i0=np.concatenate([p["i0"] for p in parts]), i_m=np.concatenate([p["i_m"] for p in parts]), detected={}, feats={}, shares={})
    for name, *_ in COMBOS:
        out["detected"][name] = np.concatenate([p["detected"][name] for p in parts])
        out["feats"][name] = np.concatenate([p["feats"][name] for p in parts])
    for p in parts:
        out["shares"].update(p["shares"])
    CACHE.write_bytes(pickle.dumps(out))
    print("L3 cache", len(out["event_id"]), "triggered events;", len(out["shares"]), "normal-driving validation events")


def load_cache() -> dict:
    z = pickle.loads(CACHE.read_bytes())
    z["row"] = {int(e): i for i, e in enumerate(z["event_id"])}
    return z


# ------------------------------------------------------------------------------------------------ energy (ANALYTICAL)
def energy_ratio(d: float, mcu_ma: float = CURRENTS["mcu_active_lo"], cur: dict | None = None) -> float:
    """Mean supply current of B over that of A. A: gyro and accelerometer on, MCU running. B: idle (accelerometer only, MCU in light sleep) for the share ``1 - d`` of the time, as A for the share ``d``."""
    c = cur or CURRENTS
    p_a = c["sensor_full"] + mcu_ma
    p_idle = c["sensor_acc_only"] + c["mcu_light_sleep"]
    return float((p_idle * (1.0 - d) + p_a * d) / p_a)


def break_even_share(ratio: float = 0.5, mcu_ma: float = CURRENTS["mcu_active_lo"], cur: dict | None = None) -> float:
    """Active share d at which the ratio equals ``ratio``."""
    c = cur or CURRENTS
    p_a = c["sensor_full"] + mcu_ma
    p_idle = c["sensor_acc_only"] + c["mcu_light_sleep"]
    return float((ratio * p_a - p_idle) / (p_a - p_idle))


def share_bootstrap(sh: np.ndarray, seed: int = SEED, nb: int = NB) -> tuple[float, float, float]:
    sh = np.asarray(sh, float)
    rng = np.random.default_rng(seed)
    m = sh[rng.integers(0, len(sh), (nb, len(sh)))].mean(1)
    return float(sh.mean()), float(np.quantile(m, 0.025)), float(np.quantile(m, 0.975))


# ------------------------------------------------------------------------------------------------ detection
def arm_scores(cache: dict, name: str, ids: np.ndarray, model) -> np.ndarray:
    """Score of every triggered event (``ids``) of an arm: the model's probability on the arm's window features; -1 where the interrupt never fired up to the trigger sample (the event is missed)."""
    rows = np.array([cache["row"][int(e)] for e in ids])
    X = cache["feats"][name][rows]
    ok = cache["detected"][name][rows].astype(bool)
    s = np.full(len(ids), -1.0)
    if ok.any():
        s[ok] = model.predict_proba(X[ok])[:, 1]
    return s


def recall_fa(frame, ids: np.ndarray, s_trig: np.ndarray, thr: float, mask: np.ndarray | None = None) -> dict:
    from crashguard.early import scatter

    full = scatter(frame, ids, s_trig)
    y = frame.y.to_numpy()
    m = np.ones(len(y), bool) if mask is None else mask
    al = full >= thr
    return dict(recall=float(al[(y == 1) & m].mean()), fa=float(al[(y == 0) & m].mean()), alarm=al, full=full)


def forest(X: np.ndarray, y: np.ndarray, seed: int):
    from sklearn.ensemble import RandomForestClassifier

    rf = RandomForestClassifier(n_estimators=15, max_depth=6, random_state=seed, n_jobs=-1)
    rf.fit(X, y)
    rf.set_params(n_jobs=1)
    return rf


def setup(seed: int = SEED):
    from crashguard import r5_det as D

    fr = D.load_frames()
    det = D.fit_seed(seed, fr)
    cache = load_cache()
    model_a = forest(fr["F_tr"][1800].to_numpy(np.float32), det["y_tr"], seed)
    return fr, det, cache, model_a


def evaluate_arm(prm: L3Params, step: int, fr: dict, det: dict, cache: dict, model_a, seed: int, split: str, mask: np.ndarray | None) -> dict:
    """Threshold on validation (the 1% target on all non-crash validation events, as ``threshold_for_fpr``); recall and false-alarm rate of the split ``split`` (validation or test) under ``mask``."""
    from crashguard.detector_extra import threshold_for_fpr

    name = combo_name(prm, step)
    model = model_a
    if prm.retrain:
        rows = np.array([cache["row"][int(e)] for e in det["ids_tr"]])
        ok = cache["detected"][name][rows].astype(bool)
        model = forest(cache["feats"][name][rows][ok], det["y_tr"][ok], seed)
    sv = arm_scores(cache, name, det["ids_va"], model)
    from crashguard.early import scatter

    yv = fr["va"].y.to_numpy()
    thr = threshold_for_fpr(yv, scatter(fr["va"], det["ids_va"], sv), prm.alpha)
    if split == "validation":
        r = recall_fa(fr["va"], det["ids_va"], sv, thr, mask)
    else:
        st = arm_scores(cache, name, det["ids_te"], model)
        r = recall_fa(fr["te"], det["ids_te"], st, thr, mask)
    r["thr"] = thr
    r["n_missed_triggered"] = int(((arm_scores(cache, name, det["ids_va"] if split == "validation" else det["ids_te"], model)) < 0).sum())
    return r


def baseline_arm(fr: dict, det: dict, split: str, mask: np.ndarray | None, alpha: float = 0.01) -> dict:
    from crashguard.detector_extra import threshold_for_fpr
    from crashguard.early import scatter

    yv = fr["va"].y.to_numpy()
    full_v = scatter(fr["va"], det["ids_va"], det["Sv"][:, -1])
    thr = threshold_for_fpr(yv, full_v, alpha)
    frame, ids, s = (fr["va"], det["ids_va"], det["Sv"][:, -1]) if split == "validation" else (fr["te"], det["ids_te"], det["St"][:, -1])
    r = recall_fa(frame, ids, s, thr, mask)
    r["thr"] = thr
    return r


def dev_iteration(prm: L3Params, fr: dict, det: dict, cache: dict, model_a) -> dict:
    a = baseline_arm(fr, det, "validation", None, prm.alpha)
    b = evaluate_arm(prm, 1, fr, det, cache, model_a, SEED, "validation", None)
    sh = np.array([v[T_MOTS.index(prm.t_mot)] for v in cache["shares"].values()])
    d = float(sh.mean())
    return dict(params=asdict(prm), val_recall_a=a["recall"], val_recall_b=b["recall"], val_recall_loss=a["recall"] - b["recall"], val_fa_a=a["fa"], val_fa_b=b["fa"], active_share=d, energy_ratio=energy_ratio(d), missed=b["n_missed_triggered"])


def heldout_stats(alarm_a: np.ndarray, alarm_b: np.ndarray, y: np.ndarray, mask: np.ndarray, seed: int = SEED, nb: int = NB) -> dict:
    """H-L3 recall part: paired bootstrap over the crash events of ``mask`` of the loss (recall of A minus recall of B); one-sided p of H0: loss >= 0.01."""
    crash = (y == 1) & mask
    d = alarm_a[crash].astype(float) - alarm_b[crash].astype(float)
    rng = np.random.default_rng(seed)
    m = d[rng.integers(0, len(d), (nb, len(d)))].mean(1)
    return dict(n_crash=int(crash.sum()), recall_a=float(alarm_a[crash].mean()), recall_b=float(alarm_b[crash].mean()), loss=float(d.mean()), lo=float(np.quantile(m, 0.025)), hi=float(np.quantile(m, 0.975)),
                p=float(((m >= 0.01).sum() + 1) / (nb + 1)), recall_met=bool(d.mean() <= 0.01))


# ------------------------------------------------------------------------------------------------ drivers
def _dev() -> None:
    from crashguard import r5_common as R5

    fr, det, cache, model_a = setup()
    log = []
    for it, prm in enumerate(ITERATIONS):
        e = dev_iteration(prm, fr, det, cache, model_a)
        e["iteration"] = it
        log.append(e)
        print(it, {k: (round(v, 4) if isinstance(v, float) else v) for k, v in e.items() if k != "params"}, e["params"], flush=True)
    (R5.TABLES / "r5_l3_dev_log.json").write_text(json.dumps(log, indent=1), encoding="utf-8")
    best = min(range(len(log)), key=lambda i: (round(log[i]["val_recall_loss"], 9), round(log[i]["active_share"], 9), i))
    (R5.TABLES / "r5_l3_dev_choice.json").write_text(json.dumps(dict(chosen=best, params=log[best]["params"], rule="V16 5.4: lowest validation recall loss against A; ties go to the lower active share"), indent=1), encoding="utf-8")
    print("chosen iteration", best)


def _freeze() -> None:
    from crashguard import r5_common as R5

    ch = json.loads((R5.TABLES / "r5_l3_dev_choice.json").read_text(encoding="utf-8"))
    d = R5.freeze_entry("l3", ["src/crashguard/r5_l3.py", "src/crashguard/r5_det.py", "src/crashguard/detector_extra.py", "src/crashguard/windows_cache.py", "src/crashguard/features.py", "src/crashguard/config.py"], ch["params"],
                        ["data/processed/r5_det_seed42.pkl", "data/processed/r5_l3_cache.pkl"])
    print("frozen l3", d["params_sha256"][:16])


def _held() -> None:
    from crashguard import r5_common as R5

    prm = L3Params(**R5.check_frozen("l3"))
    fr, det, cache, model_a = setup()
    te = fr["te"]
    R5.ensure_split_hashes(te.event_id.to_numpy())
    h0 = R5.halves(te.event_id.to_numpy()) == 0
    a = baseline_arm(fr, det, "test", h0, prm.alpha)
    b = evaluate_arm(prm, 1, fr, det, cache, model_a, SEED, "test", h0)
    st = heldout_stats(a["alarm"], b["alarm"], te.y.to_numpy(), h0)
    rec = R5.Rec("r5.l3.", "src/crashguard/r5_l3.py", "MEASURED_SOFTWARE")
    rec.add("held.n_half0_events", int(h0.sum()), "events", "HALF0 of the de-duplicated test split")
    for k, v in st.items():
        if k not in ("recall_met",):
            rec.add(f"held.hL3.{k}", v, "fraction" if k not in ("n_crash", "p") else ("count" if k == "n_crash" else "p"), "paired bootstrap over crash events of HALF0" if k in ("lo", "hi") else "")
    rec.add("held.a.fa", a["fa"], "fraction", "false-alarm rate on all non-crash events of HALF0, A")
    rec.add("held.b.fa", b["fa"], "fraction", "false-alarm rate, B100")
    rec.add("held.b.missed_triggered", b["n_missed_triggered"], "events", "triggered test events (both halves) whose motion interrupt did not fire up to the trigger sample")
    # sensitivity arms (descriptive)
    for nm, step in (("b25", 4), ("b10", 10)):
        sens = evaluate_arm(L3Params(), step, fr, det, cache, model_a, SEED, "test", h0)
        rec.add(f"held.{nm}.recall", float(sens["alarm"][(te.y.to_numpy() == 1) & h0].mean()), "fraction", "descriptive sensitivity arm: idle accelerometer rate 25 or 10 Hz, defaults T_MOT 0.5 g and L_GYRO 30 ms, frozen forest of A", origin="MEASURED_SOFTWARE")
    # energy
    sh = np.array([v[T_MOTS.index(prm.t_mot)] for v in cache["shares"].values()])
    d, d_lo, d_hi = share_bootstrap(sh)
    for tag, mcu in (("lo", CURRENTS["mcu_active_lo"]), ("hi", CURRENTS["mcu_active_hi"])):
        rec.add(f"energy.ratio_{tag}", energy_ratio(d, mcu), "fraction", f"B over A at the measured active share; MCU running at {mcu:g} mA (ESP32 datasheet v5.3 page 30)", origin="ANALYTICAL")
        rec.add(f"energy.ratio_{tag}_at_upper_d", energy_ratio(d_hi, mcu), "fraction", "at the upper 95% limit of the active share", origin="ANALYTICAL")
        rec.add(f"energy.break_even_share_{tag}", break_even_share(0.5, mcu), "fraction", "active share at which B uses half the current of A", origin="ANALYTICAL")
    rec.add("energy.active_share", d, "fraction", f"share of the time the interrupt is asserted plus a hold of 2 s, normal-driving VZCrash validation events (n = {len(sh)}); 95% interval {d_lo:.4f} to {d_hi:.4f}; the events are dataset clips, so the share is likely high", origin="MEASURED_SOFTWARE")
    rec.add("energy.active_share_lo", d_lo, "fraction", origin="MEASURED_SOFTWARE")
    rec.add("energy.active_share_hi", d_hi, "fraction", origin="MEASURED_SOFTWARE")
    energy_met = bool(energy_ratio(d_hi, CURRENTS["mcu_active_lo"]) <= 0.5)
    rec.add("energy.met", int(energy_met), "bool", "ratio at most 0.50 at the upper 95% limit of the active share, MCU at 20 mA", origin="ANALYTICAL")
    rec.add("hL3.p", st["p"], "p", "one-sided paired bootstrap p of H0: recall loss at least 0.01")
    rec.add("hL3.criterion_met", int(st["recall_met"] and energy_met), "bool", "recall loss at most 0.01 and energy ratio at most 0.50 (also at the upper limit of d)")
    rec.write()
    print(json.dumps(dict(st=st, d=d, d_hi=d_hi, ratio=energy_ratio(d), energy_met=energy_met), indent=1, default=float))


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"build": build, "dev": _dev, "freeze": _freeze, "held": _held}.get(cmd, lambda: print(__doc__))()


if __name__ == "__main__":
    main()
