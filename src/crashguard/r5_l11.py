"""L11 (ADDED-AFTER-SESSION-1; docs/02_preregistration/PREREGISTRATION_V16.md sections 15.7 and 15.9): detection of mirror-image axis flips from turns (MEASURED_SOFTWARE: real VZCrash signals with synthetic transformations).

    python -m crashguard.r5_l11 build       # cache of the normal-driving TRAIN events that are valid under the loosest thresholds -> data/processed/r5_l11_cache.pkl
    python -m crashguard.r5_l11 dev         # development iterations (at most 5) on half 0
    python -m crashguard.r5_l11 freeze
    python -m crashguard.r5_l11 held        # held-out run, once, half 1; keys r5.l11.*

For one event: ``z`` is the unit mean acceleration of the quasi-steady samples (gyro norm below 3 deg/s and |dv/dt| below ``a_long``; all samples if fewer than 50); ``a_h`` the horizontal dynamic acceleration (m/s^2); ``w`` the yaw rate about ``z`` (rad/s); ``v`` the GPS speed (m/s, 1 Hz, linear interpolation). In a
right-handed frame a_h = dv/dt f + v w (z x f). f_L is the direction of the least-squares coefficient of a_h on dv/dt, f_T = l_T x z with l_T the direction of the coefficient of a_h on v w. The agreement
f_T . f_L is rotation-invariant and changes sign under a mirror image. Nothing here reads ``data/hardware``.
"""
from __future__ import annotations

import hashlib
import json
import pickle
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data" / "processed" / "r5_l11_cache.pkl"
FS = 100.0
G = 9.81
N_SEG = 100
N_VALID = 20
QUIET_DPS, QUIET_MIN = 3.0, 50  # quasi-steady samples for the up direction (V16 15.10, S2.2)
SEED, NB = 42, 2000


@dataclass(frozen=True)
class L11Params:
    w_min: float = 10.0  # deg/s (development item)
    v_min: float = 5.0  # m/s (development item)
    a_long: float = 0.3  # m/s^2 (development item)
    theta: float = 0.0  # decision threshold on the mean agreement (development item)
    s0: float = 1.0  # reference sign, set from the development half (S2.1 item 1)


LOOSE = L11Params(w_min=5.0, v_min=5.0, a_long=0.3, theta=0.0)
ITERATIONS = [L11Params(), L11Params(w_min=5.0), L11Params(w_min=15.0), L11Params(v_min=10.0, a_long=0.6), L11Params(theta=0.1)]


def half_l11(event_id) -> int:
    return int(hashlib.sha256(("l11|" + str(int(event_id))).encode()).hexdigest(), 16) % 2


def order_key(event_id) -> str:
    return hashlib.sha256(("l11-order|" + str(int(event_id))).encode()).hexdigest()


# ------------------------------------------------------------------------------------------------ the agreement of one event
def speed_series(gps_kmh: np.ndarray, n: int) -> np.ndarray | None:
    """Speed (m/s) at the n sample times, GPS sample j of k at j (n / 100) / k seconds, linear interpolation; None if the GPS is missing."""
    gps = np.asarray(gps_kmh, float)
    if len(gps) < 2 or not np.isfinite(gps).all():
        return None
    t_g = np.arange(len(gps)) * (n / FS) / len(gps)
    return np.interp(np.arange(n) / FS, t_g, gps / 3.6)


def unit(x: np.ndarray) -> np.ndarray | None:
    nx = float(np.linalg.norm(x))
    return x / nx if nx > 1e-12 else None


def event_agreement(acc: np.ndarray, gyro: np.ndarray, gps_kmh: np.ndarray, prm: L11Params) -> float | None:
    """Agreement f_T . f_L of one event, or None if the event is not valid (no GPS, fewer than ``N_SEG`` turn or longitudinal samples)."""
    n = len(acc)
    v = speed_series(gps_kmh, n)
    if v is None or n < 2 * N_SEG:
        return None
    dvdt = np.gradient(v, 1.0 / FS)
    quiet = (np.linalg.norm(gyro, axis=1) < QUIET_DPS) & (np.abs(dvdt) < prm.a_long)
    m = acc[quiet].mean(axis=0) if quiet.sum() >= QUIET_MIN else acc.mean(axis=0)  # up direction from the quasi-steady samples (S2.2)
    z = unit(m)
    if z is None or np.linalg.norm(m) < 0.5:
        return None
    dyn = (acc - m) * G
    a_h = dyn - np.outer(dyn @ z, z)
    w = np.radians(gyro @ z)
    sl = np.abs(dvdt) > prm.a_long
    st = (np.abs(np.degrees(w)) > prm.w_min) & (v > prm.v_min)
    if sl.sum() < N_SEG or st.sum() < N_SEG:
        return None
    cl = (a_h[sl] * dvdt[sl, None]).sum(0) / (dvdt[sl] ** 2).sum()
    vw = (v * w)[st]
    ct = (a_h[st] * vw[:, None]).sum(0) / (vw**2).sum()
    f_l, l_t = unit(cl), unit(ct)
    if f_l is None or l_t is None:
        return None
    f_t = np.cross(l_t, z)
    return float(f_t @ f_l)


# ------------------------------------------------------------------------------------------------ transformations
def _diag(axis: str) -> np.ndarray:
    d = np.ones(3)
    d["xyz".index(axis)] = -1.0
    return np.diag(d)


def _rz(deg: float) -> np.ndarray:
    c, s = np.cos(np.radians(deg)), np.sin(np.radians(deg))
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def _rx(deg: float) -> np.ndarray:
    c, s = np.cos(np.radians(deg)), np.sin(np.radians(deg))
    return np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]])


I3 = np.eye(3)
# name -> (matrix for the accelerometer, matrix for the gyro, group)
TRANSFORMS: dict[str, tuple[np.ndarray, np.ndarray, str]] = {
    "identity": (I3, I3, "unflipped"), "yaw90": (_rz(90), _rz(90), "unflipped"), "yaw180": (_rz(180), _rz(180), "unflipped"), "tilt25x": (_rx(25), _rx(25), "unflipped"), "rot180x": (_rx(180), _rx(180), "unflipped"),
    "mirror_x": (_diag("x"), _diag("x"), "criterion"), "mirror_y": (_diag("y"), _diag("y"), "criterion"), "mirror_z": (_diag("z"), _diag("z"), "criterion"),
    "acc_only_x": (_diag("x"), I3, "criterion"), "acc_only_y": (_diag("y"), I3, "criterion"),
    "acc_only_z": (_diag("z"), I3, "descriptive"), "gyro_only_x": (I3, _diag("x"), "descriptive"), "gyro_only_y": (I3, _diag("y"), "descriptive"), "gyro_only_z": (I3, _diag("z"), "descriptive"),
}


def transform(acc: np.ndarray, gyro: np.ndarray, name: str) -> tuple[np.ndarray, np.ndarray]:
    Ma, Mg, _g = TRANSFORMS[name]
    return acc @ Ma.T, gyro @ Mg.T


def installation_decision(agreements: list[float], prm: L11Params, n: int = N_VALID) -> bool | None:
    """True = mirror flip declared. Uses the first ``n`` valid agreements (None entries are skipped); None if fewer than ``n`` are valid."""
    v = [a for a in agreements if a is not None][:n]
    if len(v) < n:
        return None
    return bool(prm.s0 * float(np.mean(v)) < prm.theta)


def groups_of(valid_ids: list[int], n: int = N_VALID, cap: int = 100) -> list[list[int]]:
    """Disjoint groups of ``n`` consecutive valid events in ascending order of ``order_key``; at most ``cap`` groups."""
    ids = sorted(valid_ids, key=order_key)
    return [ids[i : i + n] for i in range(0, len(ids) - n + 1, n)][:cap]


def exact_binom_p_greater(k: int, n: int, p0: float) -> float:
    from scipy.stats import binomtest

    return float(binomtest(k, n, p0, alternative="greater").pvalue)


def exact_upper(k: int, n: int, level: float = 0.95) -> float:
    from scipy.stats import beta

    return 1.0 if k >= n else float(beta.ppf(level, k + 1, n - k))


# ------------------------------------------------------------------------------------------------ cache
def _shard(path_str: str) -> tuple[list[dict], list[int]]:
    from crashguard import config as C
    from crashguard import features as F
    from crashguard.data import iter_events

    rows = []
    counts = [0, 0]
    for _sp, eid, label, _vs, _hd, acc, gyro, gps in iter_events(Path(path_str)):
        if label != 2:
            continue
        counts[half_l11(eid)] += 1
        if len(acc) < 2 * N_SEG:
            continue
        if not np.isfinite(acc).all() or float(np.linalg.norm(acc, axis=1).max()) > C.MPU_RANGE_G:
            continue
        g = F._align_gyro(gyro, len(acc))
        if event_agreement(acc, g, np.asarray(gps, float), LOOSE) is None:
            continue
        a32 = acc.astype(np.float32)
        rows.append(dict(id=int(eid), acc=a32, gyro=np.asarray(g, np.float32), gps=np.asarray(gps, np.float32), h=hashlib.md5(a32.tobytes()).hexdigest()))
    return rows, counts


def build() -> None:
    import os
    from concurrent.futures import ProcessPoolExecutor

    from crashguard import config as C

    files = sorted((C.RAW_DIR / "data").glob("train-*.parquet"))
    with ProcessPoolExecutor(min(8, os.cpu_count() or 1)) as ex:
        parts = list(ex.map(_shard, [str(f) for f in files]))
    ev = sorted((r for p, _c in parts for r in p), key=lambda r: r["id"])
    seen, kept = set(), []
    for r in ev:  # exact copies of an acceleration record (same bytes) are kept once: the same event must not sit in both halves (review of session 2)
        if r["h"] in seen:
            continue
        seen.add(r["h"])
        kept.append(r)
    counts = [sum(c[i] for _p, c in parts) for i in (0, 1)]
    meta = dict(n_label2_half0=counts[0], n_label2_half1=counts[1], n_valid_loose=len(ev), n_duplicates_dropped=len(ev) - len(kept))
    CACHE.write_bytes(pickle.dumps(dict(events=kept, meta=meta)))
    print("cache", len(kept), "events valid under the loosest thresholds;", meta)


def load_cache(half: int) -> dict:
    ev = pickle.loads(CACHE.read_bytes())["events"]
    return {e["id"]: e for e in ev if half_l11(e["id"]) == half}


def load_meta() -> dict:
    return pickle.loads(CACHE.read_bytes())["meta"]


def dominant_axis(events: dict, ids: list) -> str:
    """Sensor axis ("x", "y" or "z") that most often carries gravity (largest absolute mean acceleration) over the events of a group; used only for a descriptive table."""
    ax = [int(np.argmax(np.abs(events[i]["acc"].mean(axis=0)))) for i in ids]
    return "xyz"[max(set(ax), key=ax.count)]


# ------------------------------------------------------------------------------------------------ evaluation
def agreements_for(ev: dict, name: str, prm: L11Params) -> float | None:
    a, g = transform(ev["acc"].astype(float), ev["gyro"].astype(float), name)
    return event_agreement(a, g, ev["gps"].astype(float), prm)


def evaluate(events: dict, prm: L11Params, names=None, cap: int = 100) -> dict:
    """Decisions of every installation under every transformation. Installations are formed from the events valid under ``prm`` with the identity transformation."""
    names = names or list(TRANSFORMS)
    valid = [i for i, e in events.items() if agreements_for(e, "identity", prm) is not None]
    gr = groups_of(valid, cap=cap)
    out = {nm: [] for nm in names}
    for g in gr:
        for nm in names:
            out[nm].append(installation_decision([agreements_for(events[i], nm, prm) for i in g], prm))
    return dict(n_valid=len(valid), n_groups=len(gr), decisions=out, groups=gr)


def rates(res: dict) -> dict:
    dec = res["decisions"]
    sens = {nm: (sum(1 for d in v if d) / len(v) if v else float("nan")) for nm, v in dec.items() if TRANSFORMS[nm][2] != "unflipped"}
    un = [d for nm, v in dec.items() if TRANSFORMS[nm][2] == "unflipped" for d in v]
    fd = (sum(1 for d in un if d) / len(un)) if un else float("nan")
    return dict(sens=sens, false_detection=fd, n_unflipped=len(un))


def reference_sign(events: dict, prm: L11Params, cap: int = 100) -> tuple[float, float]:
    """S2.1 item 1: sign and absolute value of the median agreement of the identity installations of the development half."""
    valid = [i for i, e in events.items() if agreements_for(e, "identity", prm) is not None]
    means = [float(np.mean([agreements_for(events[i], "identity", prm) for i in g])) for g in groups_of(valid, cap=cap)]
    med = float(np.median(means)) if means else float("nan")
    return (1.0 if med >= 0 else -1.0), abs(med)


def score(r: dict) -> float:
    crit = [v for nm, v in r["sens"].items() if TRANSFORMS[nm][2] == "criterion"]
    return float(min(crit) - 10.0 * r["false_detection"])


def _dev() -> None:
    from crashguard import r5_common as R5

    ev = load_cache(0)
    log = []
    for it, p0 in enumerate(ITERATIONS):
        s0, med = reference_sign(ev, p0)
        p = L11Params(**{**asdict(p0), "s0": s0})
        r = rates(evaluate(ev, p))
        e = dict(iteration=it, params=asdict(p), median_abs_agreement=med, score=score(r), false_detection=r["false_detection"], sens=r["sens"], n_groups=r["n_unflipped"] // 5)
        log.append(e)
        print(it, asdict(p), round(med, 3), round(e["score"], 3), round(r["false_detection"], 3), {k: round(v, 2) for k, v in r["sens"].items()}, flush=True)
    (R5.TABLES / "r5_l11_dev_log.json").write_text(json.dumps(log, indent=1, default=float), encoding="utf-8")
    best = max(range(len(log)), key=lambda i: (round(log[i]["score"], 9), -i))
    (R5.TABLES / "r5_l11_dev_choice.json").write_text(json.dumps(dict(chosen=best, params=log[best]["params"], median_abs_agreement=log[best]["median_abs_agreement"], rule="V16 15.7: highest min criterion sensitivity minus 10 times the false-detection rate; ties go to the lowest iteration index (the order of the list, with the default first)"), indent=1), encoding="utf-8")
    print("chosen", best)


def _freeze() -> None:
    from crashguard import r5_common as R5

    ch = json.loads((R5.TABLES / "r5_l11_dev_choice.json").read_text(encoding="utf-8"))
    d = R5.freeze_entry("l11", ["src/crashguard/r5_l11.py", "src/crashguard/data.py", "src/crashguard/features.py"], ch["params"], ["data/processed/r5_l11_cache.pkl", "results/tables/r5_l11_dev_choice.json", "results/tables/r5_l11_dev_log.json"])
    ev = load_cache(1)
    ids = sorted(ev)
    (R5.TABLES / "r5_split_hashes_l11.json").write_text(json.dumps(dict(rule="int(sha256('l11|'+id),16) mod 2", n_half0_cached=len(load_cache(0)), n_half1_cached=len(ids), half1_ids_sha256=hashlib.sha256(",".join(map(str, ids)).encode()).hexdigest()), indent=1), encoding="utf-8")
    print("frozen l11", d["params_sha256"][:16], "median |agreement| on development", ch["median_abs_agreement"])


def _held() -> None:
    from crashguard import r5_common as R5

    prm = L11Params(**R5.check_frozen("l11"))
    ch = json.loads((R5.TABLES / "r5_l11_dev_choice.json").read_text(encoding="utf-8"))
    ev = load_cache(1)
    res = evaluate(ev, prm)
    r = rates(res)
    J = res["n_groups"]
    rec = R5.Rec("r5.l11.", "src/crashguard/r5_l11.py", "MEASURED_SOFTWARE")
    rec.add("held.n_events_valid", res["n_valid"], "events", "held-out half: cached normal-driving events valid under the frozen thresholds (real signals; transformations synthetic)")
    rec.add("held.n_installations", J, "installations", "groups of 20 valid events")
    rec.add("dev.median_abs_agreement", ch["median_abs_agreement"], "fraction", "median |agreement| of the identity installations of the development half")
    rec.add("held.s0", prm.s0, "sign", "reference sign from the development half")
    ps = []
    for nm, v in res["decisions"].items():
        grp = TRANSFORMS[nm][2]
        if grp == "unflipped":
            k = sum(1 for d in v if d)
            rec.add(f"held.{nm}.false_detection", k / len(v) if v else float("nan"), "fraction", f"unflipped installation ({nm}); n = {len(v)}")
        else:
            k = sum(1 for d in v if d)
            rec.add(f"held.{nm}.sensitivity", k / len(v) if v else float("nan"), "fraction", f"{grp} transformation; n = {len(v)}")
            if grp == "criterion" and v:
                ps.append(exact_binom_p_greater(k, len(v), 0.95))
    k_fd = sum(1 for d in res["decisions"]["identity"] if d)
    rec.add("held.false_detection", r["false_detection"], "fraction", "pooled over the unflipped installations (the agreement is rotation-invariant, so the five decisions of an installation are the same and the rate is the identity rate)")
    rec.add("held.false_detection_upper95", exact_upper(k_fd, J) if J else float("nan"), "fraction", "exact one-sided upper 95% limit with n = number of installations (not five times that)")
    meta = load_meta()
    rec.add("held.share_valid_events", res["n_valid"] / max(meta["n_label2_half1"], 1), "fraction", "descriptive: held-out normal-driving events that are valid (loose cache, then frozen thresholds) over all normal-driving events of the half")
    rec.add("held.clips_for_20_valid", 20 * meta["n_label2_half1"] / max(res["n_valid"], 1), "clips", "descriptive: clips of 16 s needed on average for 20 valid events")
    rec.add("held.driving_s_for_20_valid", 16.0 * 20 * meta["n_label2_half1"] / max(res["n_valid"], 1), "s", "descriptive: driving time for 20 valid events")
    rec.add("held.n_duplicates_dropped", meta["n_duplicates_dropped"], "events", "exact copies of an acceleration record removed from the cache")
    for nm in ("acc_only_x", "acc_only_y", "acc_only_z"):
        by: dict = {}
        for g, d in zip(res["groups"], res["decisions"][nm]):
            ax = dominant_axis(ev, g)
            by.setdefault(ax, []).append(bool(d))
        for ax, v in by.items():
            rec.add(f"held.by_up_axis.{nm}.{ax}.sensitivity", sum(v) / len(v), "fraction", f"descriptive: installations whose gravity is mostly on sensor axis {ax}; n = {len(v)}")
    testable = J >= 40 and abs(ch["median_abs_agreement"]) >= 0.3
    crit = testable and all(v >= 0.95 for nm, v in r["sens"].items() if TRANSFORMS[nm][2] == "criterion") and r["false_detection"] <= 0.02
    p = max(ps) if ps else 1.0
    rec.add("hL11a.testable", int(testable), "bool", "at least 40 installations and a median agreement of at least 0.3 on development (S2 and S2.1)")
    rec.add("hL11a.criterion_met", int(crit), "bool", "sensitivity at least 0.95 for the five criterion transformations and false detection at most 0.02")
    rec.add("hL11a.p", p, "p", "largest exact one-sided binomial p of H0 sensitivity <= 0.95 over the criterion transformations; own family of one (outside the 13)")
    rec.add("hL11a.supported", int(crit and p < 0.05), "bool", "ADDED-AFTER-SESSION-1; own family")
    rec.add("hL11b.criterion_met", "NOT_RUN", "text", "the simulated side-accuracy part is cut (V16 15.8); L1 keeps its mirror-flip limitation", origin="NOT_RUN")
    rec.write()
    print(json.dumps(dict(n_valid=res["n_valid"], J=J, false_detection=r["false_detection"], sens={k: round(v, 3) for k, v in r["sens"].items()}, p=p, crit=bool(crit)), indent=1))


def main() -> None:
    {"build": build, "dev": _dev, "freeze": _freeze, "held": _held}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: print(__doc__))()


if __name__ == "__main__":
    main()
