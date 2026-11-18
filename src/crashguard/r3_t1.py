"""T1.3 and T1.4 (docs/02_preregistration/PREREGISTRATION_V14.md section 1.3 to 1.4): replay of the frozen retry policies on measured LoRaWAN loss sequences (TRACE_DRIVEN).

    python -m crashguard.r3_t1 dev        # DEVELOPMENT devices only: invariants and a run check (no parameter is chosen)
    python -m crashguard.r3_t1 held       # HELD-OUT devices: device-level delivery per policy and the R3 replay (run once)
    python -m crashguard.r3_t1 analyse    # paired bootstrap over devices, hypotheses H-T1a/b/c (raw p; Holm is applied in r3_decide), results.json keys r3.t1.*

Policies are single-link reductions of the frozen ones (no crowd, no flash frame, no sharing of duty with other vehicles): see the preregistration table. Attempt k of an alert sees the reception state
of frame s + k of the device's sequence. Delivery = reception at the base before the 10 s deadline. Nothing is tuned.
"""
from __future__ import annotations

import hashlib
import json
import math
import pickle
import random
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from crashguard import rd_policy as RP
from crashguard.lora import airtime_ms

ROOT = Path(__file__).resolve().parents[2]
LINKS = ROOT / "data" / "processed" / "r3_t1_links.pkl"
OUT_DEV = ROOT / "data" / "processed" / "r3_t1_dev.pkl"
OUT_HELD = ROOT / "data" / "processed" / "r3_t1_held.pkl"
FROZEN = ROOT / "results" / "tables" / "rd_frozen_A.json"
FROZEN_C = ROOT / "results" / "tables" / "rd_frozen_C.json"
S1 = ROOT / "results" / "tables" / "s6_events_seed42_a1.csv"

SF0 = 9
PROC, MARGIN = 0.1, 0.1
READY0 = 1.8 + 0.05  # config.POST_S + replay.COMPUTE_S
DEADLINE = 10.0
LIMIT_S = 0.01 * 3600.0
N_START = 300
MIN_AHEAD = 40
WARM = 20
POLICIES = ("D1", "quick", "P1", "P4", "P0", "khan", "nessa")
BASELINES = POLICIES[1:]
EXPLORE = ("Z0",)  # EXPLORATORY control, not preregistered and not in any hypothesis: retry at once, no hold, base SF, 12 tries
ALL = POLICIES + EXPLORE
GROUPS = (("L", 0.0, 0.10), ("M", 0.10, 0.40), ("H", 0.40, 1.01))
SEED = 42
INV = {"late_delivery": 0, "duty_exceeded": 0, "frame_overrun": 0}


def air(n: int, sf: int) -> float:
    return airtime_ms(n, sf) / 1000.0


def listen_window(sf: int) -> float:
    return PROC + air(RP.ACK_LEN, sf) + MARGIN


def seeded(*parts) -> random.Random:
    h = hashlib.sha256(("|".join(str(x) for x in parts)).encode()).hexdigest()
    return random.Random(int(h[:16], 16))


def load_params() -> dict:
    fr = json.loads(FROZEN.read_text(encoding="utf-8"))["params"]
    d1 = {k: (tuple(v) if isinstance(v, list) else v) for k, v in fr["d1"].items()}
    nz = json.loads(FROZEN_C.read_text(encoding="utf-8"))["params"]["nessa"]
    return dict(d1=d1, nessa=nz)


class Ctx:
    tab: RP.D1Table | None = None
    d1p: RP.D1Params | None = None
    nessa: dict | None = None


def init_ctx() -> None:
    p = load_params()
    Ctx.d1p = RP.D1Params(**p["d1"])
    Ctx.tab = RP.D1Table(SF0, Ctx.d1p)
    Ctx.nessa = p["nessa"]


# ------------------------------------------------------------------------------------------------ one alert
def replay_alert(pol: str, r: np.ndarray, s: int, rng: random.Random, p_dl: float, used0: float = 0.0, trace: list | None = None) -> tuple[float, int, float]:
    """Returns (time of the earliest reception at the base in s, or inf; transmissions started; airtime used). ``r`` is the 0/1 reception sequence, ``s`` the start frame. Attempt k uses frame s + k."""
    hold = 5.0 if pol in ("P1", "P0") else 0.0
    max_tries = {"P0": 4, "P1": 12, "quick": 12, "P4": 12, "khan": 9, "nessa": 12, "D1": 12, "Z0": 12}[pol]
    t = READY0 + hold
    used = used0  # airtime already used in the sliding hour (0 in every T1 run)
    beta = None
    d1_sf = SF0
    demoted = False
    if pol == "D1":
        P = Ctx.d1p
        beta = RP.BetaLoss(P.n0, P.l0, P.forget)
        for k in range(max(0, s - WARM), s):  # warm-up with the frames before the start: a round fails if the uplink or its ACK is lost
            ok = bool(r[k]) and rng.random() >= p_dl
            beta.update(not ok)
        pk = Ctx.tab.lookup(3, 0, RP.time_left(RP.DEADLINE_S[3], 0.0, t), beta.mean, 0, P.share[3] * max(LIMIT_S - used, 0.0))
        d1_sf = pk[1] if pk else SF0
    n_tx = 0
    for k in range(max_tries):
        if t > DEADLINE:
            break
        if pol in ("quick", "P4"):
            sf = min(12, SF0 + 1) if k >= 2 else SF0
        elif pol == "nessa":
            sf = min(12, SF0 + max(0, (k - 1) // 2))
        elif pol == "D1":
            sf = SF0 if demoted else d1_sf
        else:
            sf = SF0
        a = air(RP.ALERT_LEN, sf)
        if used + a > LIMIT_S + 1e-12:
            INV["duty_exceeded"] += 1
            break
        if s + k >= len(r):
            INV["frame_overrun"] += 1
            break
        used += a
        n_tx += 1
        end = t + a
        if trace is not None:
            trace.append((sf, t, a))
        if r[s + k]:
            if end > DEADLINE:
                return math.inf, n_tx, used
            return end, n_tx, used
        w = listen_window(sf)
        t_win = end + w
        tries = k + 1
        if pol in ("P1", "P0", "Z0"):
            t = t_win
        elif pol == "quick":
            t = t_win + 0.3
        elif pol == "P4":
            t = t_win + 5.0
        elif pol == "khan":
            t = t_win + rng.uniform(1.0, 3.0)
        elif pol == "nessa":
            nz = Ctx.nessa
            t0 = nz["k"] * air(RP.ALERT_LEN, SF0)
            if tries % 2 == 0:
                t = t_win + rng.uniform(0.0, nz["A"])
            else:
                stg = (tries - 1) // 2
                ub = t0 * 2.0**stg
                lb = t0 * 2.0 ** (stg - 1) if stg >= 1 else t0 / 2.0
                t = t_win + max(0.0, rng.uniform(lb, ub) - w)
        else:  # D1
            beta.update(True)
            if demoted:
                t = t_win + 4.0 * 2.0 ** max(tries - 1, 0) * (1.0 + 0.5 * rng.random())
            else:
                bud = Ctx.d1p.share[3] * max(LIMIT_S - used, 0.0)
                pk = Ctx.tab.lookup(3, tries, RP.time_left(RP.DEADLINE_S[3], 0.0, t_win), beta.mean, 0, bud)
                if pk is None:
                    demoted = True
                    t = t_win + 4.0 * 2.0 ** max(tries - 1, 0) * (1.0 + 0.5 * rng.random())
                else:
                    d1_sf = pk[1]
                    t = t_win + pk[0]
    return math.inf, n_tx, used


# ------------------------------------------------------------------------------------------------ two-stage alert (R3 logic on traces)
SF_R3 = 7
A_FL, A_AL, A_ACK = air(14, SF_R3), air(RP.ALERT_LEN, SF_R3), air(RP.ACK_LEN, SF_R3)
WIN3 = PROC + A_ACK + MARGIN
TRIES3 = 4
CANCEL_TX = 3
COMPUTE3 = 0.008
FINAL_S = 1.8


def arrival_trace(r: np.ndarray, s: int, t0: float, a_msg: float, p_dl: float, rng: random.Random) -> tuple[float, int]:
    """First reception time (inf if none in 4 tries) and the number of tries used: the stage ends at the first try whose uplink is received and whose ACK reaches the car (probability 1 - p_dl)."""
    arr = math.inf
    for k in range(TRIES3):
        t_k = t0 + k * (a_msg + WIN3)
        if r[s + k]:
            if arr == math.inf:
                arr = t_k + a_msg
            if rng.random() >= p_dl:
                return arr, k + 1
    return arr, TRIES3


def r3_event(r: np.ndarray, s: int, ev: tuple, p_dl: float, rng: random.Random) -> dict:
    """One event on the link: ev = (E, F, y, t_early_s). Returns sums for the group statistics."""
    E, F, y, te = ev
    out = dict(n_cr=int(y == 1), single_air=0.0, two_air=0.0, single_d=0, two_d=0, diff=None)
    # single stage: the full alert at 1.8 s
    if F:
        arr_s, n_s = arrival_trace(r, s, FINAL_S + COMPUTE3, A_AL, p_dl, rng)
        out["single_air"] = A_AL * n_s
        out["single_d"] = int(y == 1 and math.isfinite(arr_s))
    else:
        arr_s, n_s = math.inf, 0
    # two stage: flash at the early decision, then confirmation or CANCEL
    if E:
        arr_f, n_f = arrival_trace(r, s, te + COMPUTE3, A_FL, p_dl, rng)
        k0 = s + n_f
        if F:
            arr_c, n_c = arrival_trace(r, k0, FINAL_S + COMPUTE3, A_AL, p_dl, rng)
            out["two_air"] = A_FL * n_f + A_AL * n_c
            out["two_d"] = int(y == 1 and (math.isfinite(arr_f) or math.isfinite(arr_c)))
            if y == 1 and math.isfinite(arr_f) and math.isfinite(arr_s):
                out["diff"] = arr_s - arr_f
        else:
            cancel_lost = all(not r[k0 + j] for j in range(CANCEL_TX))
            out["two_air"] = A_FL * n_f + CANCEL_TX * A_FL
            out["two_d"] = int(y == 1 and math.isfinite(arr_f) and cancel_lost)
    elif F:
        arr_c, n_c = arrival_trace(r, s, FINAL_S + COMPUTE3, A_AL, p_dl, rng)
        out["two_air"] = A_AL * n_c
        out["two_d"] = int(y == 1 and math.isfinite(arr_c))
    return out


# ------------------------------------------------------------------------------------------------ per device
def admissible(segs: list) -> list[tuple[int, int]]:
    return [(i, j) for i, (r, _t) in enumerate(segs) for j in range(0, max(len(r) - MIN_AHEAD, 0))]


def device_task(args: tuple) -> dict:
    dev, segs, p_loss, n_start, with_r3, events = args
    if Ctx.tab is None:
        init_ctx()
    inv0 = dict(INV)
    rng0 = seeded("t1s", dev, SEED)
    adm = admissible(segs)
    picks = [adm[rng0.randrange(len(adm))] for _ in range(n_start)]
    deliv = {p: 0 for p in ALL}
    n_tx = {p: 0 for p in ALL}
    air_used = {p: 0.0 for p in ALL}
    d_times = {p: [] for p in ALL}
    r3 = dict(n_cr=0, single_air=0.0, two_air=0.0, single_d=0, two_d=0, diffs=[])
    for q, (si, pos) in enumerate(picks):
        r = segs[si][0]
        for pol in ALL:
            rng = seeded("t1a", dev, q, pol)
            t_rx, n, used = replay_alert(pol, r, pos, rng, p_loss)
            if math.isfinite(t_rx):
                if t_rx > DEADLINE + 1e-9:
                    INV["late_delivery"] += 1
                deliv[pol] += 1
                d_times[pol].append(t_rx)
            n_tx[pol] += n
            air_used[pol] += used
        if with_r3:
            rng = seeded("t1e", dev, q)
            ev = events[rng.randrange(len(events))]
            o = r3_event(r, pos, ev, p_loss, rng)
            for k in ("n_cr", "single_air", "two_air", "single_d", "two_d"):
                r3[k] += o[k]
            if o["diff"] is not None:
                r3["diffs"].append(o["diff"])
    return dict(dev=dev, p=p_loss, n=len(picks), deliv={p: deliv[p] / len(picks) for p in ALL}, mean_tx={p: n_tx[p] / len(picks) for p in ALL},
                mean_air={p: air_used[p] / len(picks) for p in ALL}, median_t={p: (float(np.median(d_times[p])) if d_times[p] else None) for p in ALL},
                r3=r3, inv={k: INV[k] - inv0[k] for k in INV})


def load_events() -> list[tuple]:
    import pandas as pd

    ev = pd.read_csv(S1)
    tr = ev[ev.triggered]
    return [(bool(e), bool(f), int(y), float(t) / 1000.0) for e, f, y, t in zip(tr.alarm_E, tr.alarm_F, tr.y, tr.time_ms)]


def run(half: int, n_start: int, max_dev: int | None, out: Path, workers: int = 14, with_r3: bool = True) -> None:
    links = pickle.loads(LINKS.read_bytes())
    devs = sorted(d for d, v in links.items() if v["half"] == half)
    if max_dev:
        devs = devs[:max_dev]
    events = load_events()
    tasks = [(d, links[d]["segs"], links[d]["p"], n_start, with_r3, events) for d in devs]
    with ProcessPoolExecutor(workers) as ex:
        res = list(ex.map(device_task, tasks, chunksize=8))
    inv = {k: sum(r["inv"][k] for r in res) for k in INV}  # counts over all devices; any non-zero value is a failure
    pickle.dump(dict(res=res, inv=inv, half=half, n_start=n_start), out.open("wb"))
    print("devices", len(res), "invariant counters", inv)


# ------------------------------------------------------------------------------------------------ analysis
def group_of(p: float) -> str:
    for g, lo, hi in GROUPS:
        if lo <= p < hi:
            return g
    return "H"


def boot_idx(n: int, nb: int, rng: np.random.Generator) -> np.ndarray:
    return rng.integers(0, n, size=(nb, n))


def analyse() -> dict:
    from crashguard.results import record_many

    d = pickle.loads(OUT_HELD.read_bytes())
    res = d["res"]
    rng = np.random.default_rng(SEED)
    NB = 2000
    ent: list[dict] = []
    src = "src/crashguard/r3_t1.py"

    def add(name, value, unit, notes="", origin="TRACE_DRIVEN"):
        if isinstance(value, float):
            value = round(value, 6)
        ent.append(dict(name=f"r3.t1.{name}", value=value, unit=unit, origin="NOT_RUN" if value == "NOT_RUN" else origin, source_file=src, notes=notes))

    out: dict = dict(groups={}, hyp={})
    add("n_heldout_devices", len(res), "devices", "included HELD-OUT devices (300 start points each)")
    add("invariants.late_delivery", d["inv"]["late_delivery"], "count", "counted deliveries after the deadline (must be 0)")
    add("invariants.duty_exceeded", d["inv"]["duty_exceeded"], "count", "blocked transmissions above the duty limit (must be 0)")
    add("invariants.frame_overrun", d["inv"]["frame_overrun"], "count", "attempts beyond the sequence (must be 0)")
    for g, lo, hi in GROUPS:
        idx = [i for i, r in enumerate(res) if lo <= r["p"] < hi]
        n = len(idx)
        add(f"{g}.n_devices", n, "devices", f"HELD-OUT devices with loss in [{lo}, {min(hi, 1.0)})")
        out["groups"][g] = dict(n=n)
        if n < 20:
            for h in ("T1a", "T1b", "T1c"):
                if h == "T1b" and g != "H":
                    continue
                add(f"{h}.{g}.status", "NOT_RUN", "status", f"fewer than 20 HELD-OUT devices in group {g}")
            continue
        V = np.array([[res[i]["deliv"][p] for p in POLICIES] for i in idx])  # (n, 7)
        B = boot_idx(n, NB, rng)
        means = V.mean(0)
        bm = V[B].mean(1)  # (NB, 7)
        for j, p in enumerate(POLICIES):
            lo_, hi_ = np.quantile(bm[:, j], [0.025, 0.975])
            add(f"{g}.deliv.{p}", float(means[j]), "fraction", "mean over devices of the device-level delivery before 10 s; 95% interval in _lo, _hi")
            add(f"{g}.deliv.{p}_lo", float(lo_), "fraction", "paired bootstrap over devices, 2,000 resamples, seed 42")
            add(f"{g}.deliv.{p}_hi", float(hi_), "fraction", "paired bootstrap over devices, 2,000 resamples, seed 42")
            add(f"{g}.mean_air_s.{p}", float(np.mean([res[i]["mean_air"][p] for i in idx])), "s", "mean transmit airtime per alert on the replay")
            add(f"{g}.mean_tx.{p}", float(np.mean([res[i]["mean_tx"][p] for i in idx])), "transmissions", "mean transmissions started per alert on the replay (descriptive)")
        for p in EXPLORE:  # EXPLORATORY control, outside the Holm family
            vz = np.array([res[i]["deliv"][p] for i in idx])
            add(f"explore.{g}.deliv.{p}", float(vz.mean()), "fraction", "EXPLORATORY, not preregistered: retry at once, no hold, base SF, 12 tries; shows how much of the D1 gap is the retry spacing")
            add(f"explore.{g}.mean_tx.{p}", float(np.mean([res[i]["mean_tx"][p] for i in idx])), "transmissions", "EXPLORATORY control")
        jb = int(np.argmax(means[1:])) + 1
        best = POLICIES[jb]
        diff = bm[:, jb] - bm[:, 0]
        point = float(means[jb] - means[0])
        ci = np.quantile(diff, [0.025, 0.975])
        p_a = float((diff >= 0.02).mean())
        met_a = bool(ci[1] <= 0.02)
        add(f"T1a.{g}.best_baseline", best, "policy", "baseline with the highest group mean on the same HELD-OUT devices")
        add(f"T1a.{g}.diff", point, "fraction", "best baseline minus D1 (positive: D1 worse)")
        add(f"T1a.{g}.diff_lo", float(ci[0]), "fraction", "95% bootstrap interval")
        add(f"T1a.{g}.diff_hi", float(ci[1]), "fraction", "95% bootstrap interval")
        add(f"T1a.{g}.criterion_met", int(met_a), "flag", "upper 95% limit of (best baseline - D1) at most 0.02")
        add(f"T1a.{g}.p", p_a, "p", "one-sided bootstrap p of H0: best baseline minus D1 at least 0.02")
        out["hyp"][f"T1a.{g}"] = dict(point=point, ci=[float(ci[0]), float(ci[1])], best=best, met=met_a, p=p_a)
        if g == "H":
            dq = bm[:, 0] - bm[:, 1]
            pt = float(means[0] - means[1])
            ci_q = np.quantile(dq, [0.025, 0.975])
            p_b = float((dq <= 0).mean())
            met_b = bool(pt >= 0.02 and ci_q[0] > 0)
            add("T1b.diff", pt, "fraction", "D1 minus quick retries on group H")
            add("T1b.diff_lo", float(ci_q[0]), "fraction", "95% bootstrap interval")
            add("T1b.diff_hi", float(ci_q[1]), "fraction", "95% bootstrap interval")
            add("T1b.criterion_met", int(met_b), "flag", "point difference at least 0.02 and lower 95% limit above 0")
            add("T1b.p", p_b, "p", "one-sided bootstrap p of H0: D1 minus quick at most 0")
            out["hyp"]["T1b"] = dict(point=pt, ci=[float(ci_q[0]), float(ci_q[1])], met=met_b, p=p_b)
        # R3 on traces (T1c): per-device sums, bootstrap over devices
        sums = np.array([[res[i]["r3"][k] for k in ("n_cr", "single_air", "two_air", "single_d", "two_d")] for i in idx], float)
        diffs = [np.array(res[i]["r3"]["diffs"], float) for i in idx]

        def stat(bi: np.ndarray) -> tuple[float, float, float]:
            sm = sums[bi].sum(0)
            ratio = sm[2] / sm[1] - 1.0 if sm[1] > 0 else float("nan")
            dd = (sm[4] - sm[3]) / sm[0] if sm[0] > 0 else float("nan")
            dv = np.concatenate([diffs[k] for k in bi]) if len(bi) else np.array([])
            return float(np.median(dv)) if len(dv) else float("nan"), ratio, dd

        pt_med, pt_ratio, pt_dd = stat(np.arange(n))
        bs = np.array([stat(b) for b in B[:500]])  # 500 resamples: the paired differences are long
        lo_med = float(np.nanquantile(bs[:, 0], 0.025))
        p_med = float((bs[:, 0] <= 0.8).mean())
        hi_air = float(np.nanquantile(bs[:, 1], 0.975))
        p_air = float((bs[:, 1] >= 0.40).mean())
        lo_dd = float(np.nanquantile(bs[:, 2], 0.025))
        p_dd = float((bs[:, 2] < -0.02).mean())
        met_c = bool(pt_med >= 0.8 and hi_air < 0.40 and lo_dd >= -0.02)
        add(f"T1c.{g}.earlier_median_s", pt_med, "s", "median over (device, start) pairs of single-stage arrival minus provisional arrival, crash events that alarm in both stages")
        add(f"T1c.{g}.earlier_median_s_lo", lo_med, "s", "95% bootstrap lower limit over devices (500 resamples)")
        add(f"T1c.{g}.extra_air_ratio", pt_ratio, "fraction", "two-stage transmit airtime over single-stage airtime minus 1")
        add(f"T1c.{g}.extra_air_ratio_hi", hi_air, "fraction", "95% bootstrap upper limit over devices")
        add(f"T1c.{g}.delivery_diff", pt_dd, "fraction", "event delivery of the two-stage scheme minus single-stage over crash events")
        add(f"T1c.{g}.delivery_diff_lo", lo_dd, "fraction", "95% bootstrap lower limit")
        add(f"T1c.{g}.criterion_met", int(met_c), "flag", "median earlier at least 0.8 s, extra airtime under 40%, delivery not lower by more than 2 points")
        add(f"T1c.{g}.p", max(p_med, p_air, p_dd), "p", "largest of the clause p-values of group " + g)
        out["hyp"][f"T1c.{g}"] = dict(median=pt_med, lo=lo_med, air=pt_ratio, air_hi=hi_air, dd=pt_dd, dd_lo=lo_dd, met=met_c, p=float(max(p_med, p_air, p_dd)))
    # H-T1c over the three groups: all groups must meet; p = largest group p
    gs = [g for g in ("L", "M", "H") if f"T1c.{g}" in out["hyp"]]
    if len(gs) == 3:
        add("T1c.criterion_met", int(all(out["hyp"][f"T1c.{g}"]["met"] for g in gs)), "flag", "all three groups meet the clauses")
        add("T1c.p", max(out["hyp"][f"T1c.{g}"]["p"] for g in gs), "p", "largest group p-value (intersection test)")
    record_many(ent, purge_prefixes=("r3.t1.",))
    (ROOT / "results" / "tables" / "r3_t1_summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "dev":
        run(0, 60, 400, OUT_DEV)
    elif cmd == "held":
        run(1, N_START, None, OUT_HELD)
    elif cmd == "analyse":
        o = analyse()
        for k, v in o["hyp"].items():
            print(k, v)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
