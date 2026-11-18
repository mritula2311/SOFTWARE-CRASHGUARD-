"""X1 (N17): impact direction from one IMU on real crash-test records (docs/02_preregistration/EXPERIMENTS_EXTRA.md, written before this was run).

The firmware rule: after the sensor model (260 Hz front end, clipping at the range, 40 Hz low-pass, 100 Hz), remove gravity by the pre-trigger mean, sum the horizontal
acceleration over the first W ms after the trigger sample (the impulse J), and take the impact direction as the opposite of the impulse direction (the vehicle accelerates
away from the impact point): theta = atan2(-Jy, -Jx) in CrashGuard axes (X forward, Y left), measured from +X towards +Y.

What the database offers (scan of every impact angle on 2026-11-11): frontal barrier (angle 0), side impactor on the left (270), a 15-degree oblique frontal impactor (345),
poles (285) and sleds. Rear tests have no instrumentation records and every side test strikes the left side (dummies in the left front and left rear seats), so rear and right
are NOT scored. The sign of the lateral axis is calibrated on the left-side tests; the left-against-right decision is therefore not independent and is not claimed.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from crashguard import boot as B
from crashguard import config as C
from crashguard import nhtsa as N
from crashguard import severity as S
from crashguard import severity_study as SS

RANGES = (16.0, 32.0, 64.0)
WINDOWS_MS = (30, 60, 100)
W_DEFAULT = 60
FS = float(C.FS_HZ)
MIN_PER_CLASS = 10  # a class with fewer usable tests is not scored
OBLIQUE_DEG = 15.0  # the oblique tests are 15-degree impacts into the front; the side of the offset is not in the metadata, so only the magnitude is compared
CACHE = C.PROCESSED / "nhtsa_oblique.joblib"


def load_oblique() -> list[dict]:
    """Instrumented tests with a 15-degree oblique impactor into a stationary vehicle (angle 345); the same selection rules as the other NHTSA tests."""
    import joblib

    if CACHE.exists():
        return joblib.load(CACHE)
    found, seen = [], set()
    for t in sorted(N.search(345, "IMPACTOR INTO VEHICLE", 0, 200), key=lambda c: c["testNo"]):
        key = (t["vehicleMake"], t["vehicleModel"], t["modelYear"])
        if key in seen or "FRONT 15 DEGREE" not in str(t.get("testType", "")):
            continue
        sig = N.load_test(t, True)
        if sig is None or "reason" in sig:
            continue
        seen.add(key)
        found.append(dict(test_no=int(t["testNo"]), kind="oblique", v=float(t["closingSpeed"]), sig=sig, group=f"{t['vehicleMake']}|{t['vehicleModel']}|{t['modelYear']}"))
    C.PROCESSED.mkdir(parents=True, exist_ok=True)
    joblib.dump(found, CACHE)
    return found


def struck_side(test_no: int) -> str:
    """Struck side of a side-impact test from the occupant records: dummies in the left front and left rear seats (locations 01 and 04) mean the left side."""
    m = json.loads((N.RAW / f"meta_{test_no}.json").read_text(encoding="utf-8"))
    locs = {o["OCCLOC"] for o in m.get("OCCUPANT", []) if "DUMMY" in str(o.get("OCCTYPD", "")).upper() or "SID" in str(o.get("OCCTYPD", "")).upper()}
    return "left" if locs and locs <= {"01", "04", "03"} else "unknown"


def all_tests() -> list[dict]:
    tests = [dict(test_no=t["test_no"], kind=t["kind"], v=t["v"], sig=t["sig"], group=t["group"]) for t in SS.load_tests()]
    tests += load_oblique()
    for t in tests:
        make, model, _y = (t["group"].split("|") + ["", "", ""])[:3]
        t["group_mm"] = f"{make}|{model}"
        t["truth"] = "front" if t["kind"] in ("frontal", "oblique") else ("side" if struck_side(t["test_no"]) == "left" else "unknown")
    return tests


def impulse(sig: dict, range_g: float, w_ms: int, flip: tuple[int, int]) -> tuple[float, float]:
    """Impulse (g s) of the horizontal acceleration over the first ``w_ms`` after the trigger, in CrashGuard axes (``flip`` = signs applied to the data's X and Y)."""
    y = SS.sensor_signal(sig, range_g, FS)
    w, trig = SS._window(y, FS)
    a = S.remove_baseline(w, trig)
    n = max(int(round(w_ms * FS / 1000.0)), 1)
    seg = a[trig : trig + n, :2]
    j = seg.sum(axis=0) * C.DT
    return float(j[0] * flip[0]), float(j[1] * flip[1])


def native_pulse_mean(sig: dict, ms: float = 100.0) -> tuple[float, float]:
    """Mean longitudinal and lateral acceleration (g) of the raw record over ``ms`` after the trigger (used only for the sign convention check)."""
    acc, fs0 = np.asarray(sig["acc"]), float(sig["fs0"])
    i0 = N.trigger_index(acc + np.array([0, 0, 1.0]), fs0) or 0
    base = acc[: max(i0, 1)].mean(axis=0)
    seg = acc[i0 : i0 + int(ms / 1000.0 * fs0)] - base
    return float(seg[:, 0].mean()), float(seg[:, 1].mean())


def axis_convention(tests: list[dict]) -> dict:
    """Sign check. Frontal tests: the vehicle decelerates, so with X forward the mean longitudinal acceleration is negative. Left-side tests: the vehicle is pushed to the right,
    so with Y left the mean lateral acceleration is negative. The flip is +1 if the data already match and -1 otherwise."""
    fx = [native_pulse_mean(t["sig"])[0] for t in tests if t["kind"] == "frontal"]
    sy = [native_pulse_mean(t["sig"])[1] for t in tests if t["kind"] == "side" and t["truth"] == "side"]
    return dict(frontal_mean_x_median=float(np.median(fx)), frontal_share_negative_x=float(np.mean(np.array(fx) < 0)), n_frontal=len(fx),
                side_mean_y_median=float(np.median(sy)), side_share_negative_y=float(np.mean(np.array(sy) < 0)), n_side=len(sy),
                flip_x=-1 if np.median(fx) > 0 else 1, flip_y=1 if np.median(sy) < 0 else -1)


def theta_deg(jx: float, jy: float) -> float:
    return float(np.degrees(np.arctan2(-jy, -jx)))


def sector(theta: float) -> str:
    a = (theta + 180.0) % 360.0 - 180.0
    return "front" if abs(a) <= 45.0 else ("left" if 45.0 < a <= 135.0 else ("right" if -135.0 <= a < -45.0 else "rear"))


def rows_for(tests: list[dict], conv: dict, w_ms: int) -> pd.DataFrame:
    flip = (conv["flip_x"], conv["flip_y"])
    rows = []
    for t in tests:
        for rg in RANGES:
            jx, jy = impulse(t["sig"], rg, w_ms, flip)
            th = theta_deg(jx, jy)
            rows.append(dict(test_no=t["test_no"], kind=t["kind"], truth=t["truth"], group=t["group"], group_mm=t["group_mm"], range_g=rg, w_ms=w_ms, jx=jx, jy=jy, theta=th, sector=sector(th),
                             pred2="front" if abs(jx) >= abs(jy) else "side", speed=t["v"]))
    return pd.DataFrame(rows)


def balanced_acc(d: pd.DataFrame) -> float:
    """Mean over the scored classes of the share predicted correctly (front against side, sign-free)."""
    rec = [float((g.pred2 == g.truth).mean()) for _t, g in d.groupby("truth") if len(g)]
    return float(np.mean(rec)) if rec else float("nan")


def split_groups(tests: list[dict], col: str) -> dict[str, str]:
    first: dict[str, int] = {}
    for t in tests:
        first[t[col]] = min(first.get(t[col], 10**9), t["test_no"])
    order = sorted(first, key=lambda g: (first[g], g))
    return {g: ("heldout" if i % 3 == 0 else "tuning") for i, g in enumerate(order, 1)}


def evaluate(tests: list[dict], conv: dict, col: str, split_name: str, ent: list, add) -> tuple[pd.DataFrame, int]:
    role = split_groups(tests, col)
    for t in tests:
        t["role"] = role[t[col]]
    scored = [t for t in tests if t["truth"] in ("front", "side")]
    # choose the window on the TUNING groups only
    tune_scores = {}
    for w in WINDOWS_MS:
        d = rows_for([t for t in scored if t["role"] == "tuning"], conv, w)
        tune_scores[w] = float(np.mean([(d[d.range_g == rg].pred2 == d[d.range_g == rg].truth).sum() for rg in RANGES]))  # correctly classified tuning tests, mean over the ranges
        add(f"{split_name}.window_tuning_correct.w{w}", round(tune_scores[w], 2), "tests", notes="correctly classified tuning tests (front against side), mean over the three ranges")
    best = max(WINDOWS_MS, key=lambda w: (round(tune_scores[w], 9), w == W_DEFAULT))
    w_use = best if tune_scores[best] - tune_scores[W_DEFAULT] > 1.0 else W_DEFAULT  # rule fixed in advance: change 60 ms only if another window is better by more than one test
    add(f"{split_name}.window_chosen_ms", w_use, "ms", notes="60 ms unless another window is better on the tuning groups by more than one test")
    held = [t for t in scored if t["role"] == "heldout"]
    d = rows_for(held, conv, w_use)
    add(f"{split_name}.n_groups_tuning", len({t[col] for t in tests if t['role'] == 'tuning'}), "groups")
    add(f"{split_name}.n_groups_heldout", len({t[col] for t in tests if t['role'] == 'heldout'}), "groups")
    for rg in RANGES:
        g = d[d.range_g == rg]
        for cls in ("front", "side"):
            gc = g[g.truth == cls]
            add(f"{split_name}.r{rg:g}.n_{cls}", int(len(gc)), "tests")
            if len(gc) < MIN_PER_CLASS:
                add(f"{split_name}.r{rg:g}.{cls}.acc", "NOT_RUN", "text", origin="NOT_RUN", notes=f"fewer than {MIN_PER_CLASS} held-out tests")
                continue
            p, lo, hi = B.ci_grouped((gc.pred2 == cls).astype(float).to_numpy(), gc[col].to_numpy(), np.mean)
            add(f"{split_name}.r{rg:g}.{cls}.acc", round(p, 4), "fraction")
            add(f"{split_name}.r{rg:g}.{cls}.acc_lo", round(lo, 4), "fraction")
            add(f"{split_name}.r{rg:g}.{cls}.acc_hi", round(hi, 4), "fraction")
            from scipy.stats import beta

            k_ok, n_all = int((gc.pred2 == cls).sum()), len(gc)
            add(f"{split_name}.r{rg:g}.{cls}.acc_exact_lo", round(float(beta.ppf(0.025, k_ok, n_all - k_ok + 1)) if k_ok > 0 else 0.0, 4), "fraction",
                notes="exact binomial lower limit (Clopper-Pearson, 95% two-sided) that ignores grouping; shown because the grouped bootstrap interval is degenerate when there are no errors")
        for tr in ("front", "side"):
            for pr in ("front", "side"):
                add(f"{split_name}.r{rg:g}.conf.true_{tr}.pred_{pr}", int(((g.truth == tr) & (g.pred2 == pr)).sum()), "tests")
        classes_present = [c for c in ("front", "side") if (g.truth == c).sum() >= MIN_PER_CLASS]
        if len(classes_present) == 2:
            ba = lambda idx: float(np.mean([((g.iloc[idx].pred2 == c) & (g.iloc[idx].truth == c)).sum() / max((g.iloc[idx].truth == c).sum(), 1) for c in classes_present]))  # noqa: E731
            mem = B.group_members(g[col].to_numpy())
            draws = np.array([ba(i) for i in B._gidx(mem, B.N_BOOT, B.SEED)])
            p = ba(np.arange(len(g)))
            add(f"{split_name}.r{rg:g}.balanced_acc", round(p, 4), "fraction")
            add(f"{split_name}.r{rg:g}.balanced_acc_lo", round(float(np.quantile(draws, 0.025)), 4), "fraction")
            add(f"{split_name}.r{rg:g}.balanced_acc_hi", round(float(np.quantile(draws, 0.975)), 4), "fraction")
            add(f"{split_name}.r{rg:g}.baseline_balanced_acc", round(1.0 / len(classes_present), 4), "fraction", notes="majority-class baseline: always one class")
        # angle errors
        for kind, ref in (("frontal", 0.0), ("side", 90.0)):
            gk = g[g.kind == kind]
            if len(gk) >= MIN_PER_CLASS:
                err = np.abs((gk.theta - ref + 180.0) % 360.0 - 180.0).to_numpy()
                p, lo, hi = B.ci_grouped(err, gk[col].to_numpy(), np.median)
                add(f"{split_name}.r{rg:g}.angle_err.{kind}.median_deg", round(p, 2), "degrees")
                add(f"{split_name}.r{rg:g}.angle_err.{kind}.median_deg_lo", round(lo, 2), "degrees")
                add(f"{split_name}.r{rg:g}.angle_err.{kind}.median_deg_hi", round(hi, 2), "degrees")
                add(f"{split_name}.r{rg:g}.angle_err.{kind}.p90_deg", round(B.p90(err), 2), "degrees")
        go = g[g.kind == "oblique"]
        if len(go) >= MIN_PER_CLASS:
            err = np.abs(np.abs((go.theta + 180.0) % 360.0 - 180.0) - OBLIQUE_DEG).to_numpy()
            p, lo, hi = B.ci_grouped(err, go[col].to_numpy(), np.median)
            add(f"{split_name}.r{rg:g}.angle_err.oblique_magnitude.median_deg", round(p, 2), "degrees", notes="||theta| - 15|; the offset side is not in the metadata")
            add(f"{split_name}.r{rg:g}.angle_err.oblique_magnitude.median_deg_lo", round(lo, 2), "degrees")
            add(f"{split_name}.r{rg:g}.angle_err.oblique_magnitude.median_deg_hi", round(hi, 2), "degrees")
        else:
            add(f"{split_name}.r{rg:g}.angle_err.oblique_magnitude.median_deg", "NOT_RUN", "text", origin="NOT_RUN", notes=f"{len(go)} held-out oblique tests, fewer than {MIN_PER_CLASS}")
    return d, w_use


def main() -> None:
    from crashguard.results import record_many

    tests = all_tests()
    ent: list[dict] = []
    src = "results/tables/x1_direction.csv"

    def add(name, value, unit, origin="MEASURED_SOFTWARE", notes="", s=src):
        ent.append(dict(name=f"x1.{name}", value=value, unit=unit, origin=origin, source_file=s, notes=notes))

    conv = axis_convention(tests)
    for k, v in conv.items():
        add(f"axis.{k}", round(float(v), 4) if isinstance(v, float) else int(v), "check", notes="sign convention check (frontal: mean X over 100 ms; left-side: mean Y over 100 ms), raw records")
    kinds = pd.Series([t["kind"] + ":" + t["truth"] for t in tests]).value_counts()
    for k, v in kinds.items():
        add(f"n_tests.{k.replace(':', '.')}", int(v), "tests")
    add("n_rear_instrumented", 0, "tests", notes="angle 180 tests have no instrumentation records in the database: rear is NOT scored")
    add("n_right_side", 0, "tests", notes="every side test strikes the left side (dummies in left seats): right is NOT scored")
    all_rows = []
    for col, nm in (("group_mm", "A"), ("group", "G")):
        d, w = evaluate(tests, conv, col, nm, ent, add)
        d = d.assign(split=nm)
        all_rows.append(d)
    out = pd.concat(all_rows)
    C.TABLES.mkdir(parents=True, exist_ok=True)
    out.to_csv(C.TABLES / "x1_direction.csv", index=False)
    # failures on the primary split (A) at each range
    fa = out[(out.split == "A") & (out.pred2 != out.truth) & out.truth.isin(["front", "side"])]
    fa.to_csv(C.TABLES / "x1_failures.csv", index=False)
    for rg in RANGES:
        add(f"A.r{rg:g}.failures", int((fa.range_g == rg).sum()), "tests", s="results/tables/x1_failures.csv")
        for k, row in enumerate(fa[fa.range_g == rg].itertuples(), 1):
            add(f"A.r{rg:g}.failure{k}.test_no", int(row.test_no), "test", s="results/tables/x1_failures.csv")
            add(f"A.r{rg:g}.failure{k}.make_model", str(row.group_mm), "text", s="results/tables/x1_failures.csv")
            add(f"A.r{rg:g}.failure{k}.truth", str(row.truth), "text", s="results/tables/x1_failures.csv")
            add(f"A.r{rg:g}.failure{k}.theta_deg", round(float(row.theta), 1), "degrees", s="results/tables/x1_failures.csv")
    # the 4-sector reading (sign included), for left tests: calibrated, not independent
    a16 = out[(out.split == "A") & (out.range_g == 16.0)]
    sd = a16[a16.truth == "side"]
    add("A.r16.side.sector_left_share", round(float((sd.sector == "left").mean()), 4), "fraction", notes="calibrated sign of the lateral axis: NOT an independent left-against-right result")
    record_many(ent, purge_prefixes=("x1.",))
    print(json.dumps({e["name"]: e["value"] for e in ent if e["name"].startswith(("x1.axis", "x1.A.r16", "x1.A.window", "x1.n_"))}, indent=1)[:4000])


if __name__ == "__main__":
    main()
