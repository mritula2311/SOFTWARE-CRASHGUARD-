"""R3 (H-R3): two-stage alert. The early-exit rule sends a 14-byte FLASH as the provisional alert; the full-window decision (1,800 ms) sends the full 97-byte alert as the confirmation, or an authenticated
CANCEL (14 bytes, three transmissions) when the full-window forest does not alarm. An event with no early alarm and a full-window alarm is sent as a single-stage alert at 1,800 ms.

Design and criteria: docs/02_preregistration/PREREGISTRATION_V11.md section 4, R3. Data: the per-event decisions of seed 42 on the de-duplicated VZCrash test split (`results/tables/s6_events_seed42_a*.csv`:
triggered, alarm_E, alarm_F, decision time of the early-exit rule), thresholds chosen on validation by `s6_early`; no model is refitted here, and the test events were already scored by `s6_early`, so nothing new is
tuned on them. Link: per-direction iid loss in {0, 0.1, 0.3, 0.6}; a try reaches the base if the uplink succeeds; the car retries after PROC + ACK airtime + margin, at most 4 tries; time on air at SF7
(`lora.airtime_ms`); compute 8 ms. Clauses: (a) the provisional alert reaches the base at least 0.8 s earlier (median of the paired difference over crash events that alarm in both stages) at loss 0 and 0.3;
(b) retractions under 20% of the provisional alerts at the 1% target; (c) extra transmit airtime under 40% and event delivery not worse than single-stage by more than 2 points at every loss.
Timing is SIMULATED (decision time is the window length; no ESP32 timing). Keys ``ar.r3.*``.

    python -m crashguard.ar_r3
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from crashguard import config as C
from crashguard import packet as P
from crashguard.lora import airtime_ms
from crashguard.replay import MARGIN_S, PROC_S
from crashguard.results import record_many

SRC = "src/crashguard/ar_r3.py"
LOSSES = (0.0, 0.1, 0.3, 0.6)
SF = 7
N_BOOT, N_DRAW = 2000, 200
COMPUTE_S = 0.008
FINAL_S = 1.8
TRIES = 4
CANCEL_TX = 3
A_FL, A_AL, A_ACK = (airtime_ms(b, SF) / 1000.0 for b in (14, P.ALERT_LEN, P.ACK_LEN))
WIN = PROC_S + A_ACK + MARGIN_S


def arrival(t0: float, a_msg: float, p: float, rng, n: int) -> np.ndarray:
    """Time (s) at which the first successful uplink reaches the base, for ``n`` draws; inf if all four tries fail. A try that gets no ACK (uplink or downlink lost) is repeated after ``a_msg + WIN``."""
    out = np.full(n, np.inf)
    t = np.full(n, t0)
    alive = np.ones(n, bool)
    for _k in range(TRIES):
        up = rng.random(n) >= p
        dn = rng.random(n) >= p
        hit = alive & up
        out[hit] = t[hit] + a_msg
        alive = alive & ~up & ~(up & dn)
        t = t + a_msg + WIN
    return out


def exp_tries(p: float) -> float:
    q = (1 - p) ** 2
    return float(sum((1 - q) ** k for k in range(TRIES)))


def stage_table(ev: pd.DataFrame) -> dict:
    tr = ev[ev.triggered].copy()
    E, F, y = tr.alarm_E.to_numpy(bool), tr.alarm_F.to_numpy(bool), tr.y.to_numpy(int)
    return dict(tr=tr, E=E, F=F, y=y, t=tr.time_ms.to_numpy(float) / 1000.0)


def clause_values(E, F, y, t, idx, rng, p_list=LOSSES) -> dict:
    """All clause statistics for the events ``idx`` (index array, with repeats for a bootstrap draw)."""
    E_, F_, y_ = E[idx], F[idx], y[idx]
    prov = E_.sum()
    out = {"retraction_share": float((E_ & ~F_).sum() / prov) if prov else float("nan"), "n_prov": int(prov), "n_single": int(F_.sum())}
    for p in p_list:
        # airtime (expected transmit seconds, tries counted)
        tries_fl, tries_al = exp_tries(p), exp_tries(p)
        single = F_.sum() * A_AL * tries_al
        two = ((E_ & F_).sum() * (A_FL * tries_fl + A_AL * tries_al) + (E_ & ~F_).sum() * (A_FL * tries_fl + CANCEL_TX * A_FL) + (~E_ & F_).sum() * A_AL * tries_al)
        out[f"air_ratio_p{p:g}"] = float(two / single - 1.0) if single else float("nan")
        # event delivery over crash events
        cr = y_ == 1
        single_d = (F_ & cr).sum() * (1 - p**TRIES)
        two_d = ((E_ & F_ & cr).sum() * (1 - p ** (2 * TRIES)) + (E_ & ~F_ & cr).sum() * (1 - p**TRIES) * p**CANCEL_TX + (~E_ & F_ & cr).sum() * (1 - p**TRIES))
        n_cr = cr.sum()
        out[f"delivery_single_p{p:g}"] = float(single_d / n_cr)
        out[f"delivery_two_p{p:g}"] = float(two_d / n_cr)
        out[f"delivery_diff_p{p:g}"] = float((two_d - single_d) / n_cr)
    return out


def earlier(E, F, y, t, rng, p: float) -> dict:
    m = np.flatnonzero(E & F & (y == 1))
    d = []
    arr_share = []
    for i in m:
        a1 = arrival(t[i] + COMPUTE_S, A_FL, p, rng, N_DRAW)
        a2 = arrival(FINAL_S + COMPUTE_S, A_AL, p, rng, N_DRAW)
        ok = np.isfinite(a1) & np.isfinite(a2)
        arr_share.append(ok.mean())
        d.append(float(np.mean(a2[ok] - a1[ok])) if ok.any() else np.nan)
    d = np.array(d)
    return dict(per_event=d, idx=m, n=len(m), median=float(np.nanmedian(d)), both_arrive=float(np.mean(arr_share)))


def main() -> None:
    rng = np.random.default_rng(C.SEED)
    ent: list[dict] = []

    def add(name, value, unit, notes="", origin="SIMULATED"):
        ent.append(dict(name=f"ar.r3.{name}", value=value, unit=unit, origin=origin, source_file=SRC, notes=notes))

    res = {}
    for alpha, tag in ((0.01, "a1"), (0.05, "a5")):
        ev = pd.read_csv(f"results/tables/s6_events_seed42_{tag}.csv")
        S = stage_table(ev)
        E, F, y, t = S["E"], S["F"], S["y"], S["t"]
        n = len(E)
        pt = clause_values(E, F, y, t, np.arange(n), rng)
        boot = [clause_values(E, F, y, t, rng.integers(0, n, n), rng) for _ in range(N_BOOT)]
        res[tag] = dict(pt=pt, boot=boot, S=S)
        add(f"{tag}.n_triggered_events", n, "events", f"triggered de-duplicated test events, false-alarm target {alpha:.0%}", "MEASURED_SOFTWARE")
        add(f"{tag}.n_triggered_crash", int((y == 1).sum()), "events", "", "MEASURED_SOFTWARE")
        add(f"{tag}.early_median_ms", float(np.median(t[E & (y == 1)]) * 1000), "ms", "median decision time of the early-exit rule over triggered crash events that alarm (window length)", "MEASURED_SOFTWARE")
        for k, v in pt.items():
            b = np.array([x[k] for x in boot], float)
            add(f"{tag}.{k}", round(v, 5) if isinstance(v, float) else v, "value", "bootstrap of events, 2,000 resamples, seed 42; the interval is below" if not isinstance(v, int) else "")
            if isinstance(v, float) and not np.isnan(v):
                add(f"{tag}.{k}_lo", round(float(np.nanquantile(b, 0.025)), 5), "value", "95% bootstrap interval")
                add(f"{tag}.{k}_hi", round(float(np.nanquantile(b, 0.975)), 5), "value", "95% bootstrap interval")
        for p in (0.0, 0.3):
            r = earlier(E, F, y, t, rng, p)
            m_ = r["median"]
            # bootstrap over events: resample the per-event paired differences
            d = r["per_event"][~np.isnan(r["per_event"])]
            bm = np.array([np.median(d[rng.integers(0, len(d), len(d))]) for _ in range(N_BOOT)])
            res[tag][f"earlier_p{p:g}"] = dict(median=m_, lo=float(np.quantile(bm, 0.025)), hi=float(np.quantile(bm, 0.975)), p=float((bm <= 0.8).mean()), n=r["n"])
            add(f"{tag}.earlier_median_s_p{p:g}", round(m_, 4), "s", f"median over {r['n']} crash events that alarm in both stages of (single-stage arrival minus provisional arrival), 200 link draws per event")
            add(f"{tag}.earlier_median_s_p{p:g}_lo", round(res[tag][f'earlier_p{p:g}']['lo'], 4), "s", "95% bootstrap interval over events")
            add(f"{tag}.earlier_median_s_p{p:g}_hi", round(res[tag][f'earlier_p{p:g}']['hi'], 4), "s", "95% bootstrap interval over events")
            add(f"{tag}.earlier_both_arrive_p{p:g}", round(r["both_arrive"], 4), "fraction", "share of link draws in which both the provisional and the single-stage alert reach the base")
    # H-R3 at the 1% target
    a1 = res["a1"]
    pt, boot = a1["pt"], a1["boot"]
    ca = all(a1[f"earlier_p{p:g}"]["median"] >= 0.8 for p in (0.0, 0.3))
    pa_ = max(a1[f"earlier_p{p:g}"]["p"] for p in (0.0, 0.3))
    cb = pt["retraction_share"] < 0.20
    pb_ = float(np.mean([x["retraction_share"] >= 0.20 for x in boot]))
    cc_air = all(pt[f"air_ratio_p{p:g}"] < 0.40 for p in LOSSES)
    cc_del = all(pt[f"delivery_diff_p{p:g}"] >= -0.02 for p in LOSSES)
    pc_air = max(float(np.mean([x[f"air_ratio_p{p:g}"] >= 0.40 for x in boot])) for p in LOSSES)
    pc_del = max(float(np.mean([x[f"delivery_diff_p{p:g}"] < -0.02 for x in boot])) for p in LOSSES)
    pc_ = max(pc_air, pc_del)
    add("hR3.clause_a.met", int(ca), "flag", "provisional alert at least 0.8 s earlier (median) at loss 0 and at loss 0.3, 1% target")
    add("hR3.clause_a.p", round(pa_, 5), "p", "bootstrap one-sided p of H0: median <= 0.8 s (larger of the two losses)")
    add("hR3.clause_b.met", int(cb), "flag", "retractions under 20% of the provisional alerts at the 1% target")
    add("hR3.clause_b.p", round(pb_, 5), "p", "bootstrap one-sided p of H0: share >= 0.20")
    add("hR3.clause_c.met", int(cc_air and cc_del), "flag", "extra airtime under 40% and event delivery not worse by more than 2 points, at every loss")
    add("hR3.clause_c.p", round(pc_, 5), "p", "largest bootstrap one-sided p over the two parts and the four losses")
    add("hR3.criterion_met", int(ca and cb and cc_air and cc_del), "flag", "all three clauses")
    add("hR3.p_raw", round(max(pa_, pb_, pc_), 5), "p", "largest of the three clause p-values")
    add("airtime.flash_ms", round(A_FL * 1000, 2), "ms", "14-byte FLASH or CANCEL at SF7", "ANALYTICAL")
    add("airtime.alert_ms", round(A_AL * 1000, 2), "ms", "97-byte alert at SF7", "ANALYTICAL")
    record_many(ent, purge_prefixes=("ar.r3.",))
    for tag in ("a1", "a5"):
        r = res[tag]
        print(tag, {k: round(v, 4) if isinstance(v, float) else v for k, v in r["pt"].items() if k in ("retraction_share", "n_prov", "air_ratio_p0", "air_ratio_p0.3", "air_ratio_p0.6", "delivery_diff_p0.3", "delivery_diff_p0.6")},
              {k: (round(v["median"], 3), round(v["p"], 3)) for k, v in r.items() if k.startswith("earlier")})
    print("clauses", ca, pa_, cb, pb_, cc_air, cc_del, pc_)


if __name__ == "__main__":
    main()
