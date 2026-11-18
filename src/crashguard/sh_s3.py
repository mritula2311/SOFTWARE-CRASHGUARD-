"""S3 (H-S3 and H-S4): simulated link logs and end-to-end latency through the alert-policy simulator (SIMULATED_HW_FORMAT).

Design and criteria: docs/02_preregistration/PREREGISTRATION_V11.md section 2.3 (committed before this ran). The H3 link logs calibrate a per-direction loss (symmetric); the
repository simulator (`world_sim` through `s11_sct.make_cfg`, one car, the method of `t4_clarify.part_b`) runs the severity table (P1), UA-SCT with the fast-path cap (P4) and
fixed 3 retries (P0). Tamang-style and Khan-style baselines are re-implemented here in a minimal single-link replay (ASSUMPTIONS stated in the key notes); they send at once, with no
driver-cancel window, so they are not subject to the 5 to 10 s hold of P0 and P1. Nothing here is a radio measurement. Keys ``sh.s3.*``.

    python -m crashguard.sh_s3
"""
from __future__ import annotations

import functools
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from crashguard import config as C
from crashguard import packet as P
from crashguard import s11_sct as S
from crashguard.lora import airtime_ms
from crashguard.replay import COMPUTE_S, MARGIN_S, PROC_S
from crashguard.results import record_many
from crashguard.sct_sim import SctParams, simulate

SRC = "src/crashguard/sh_s3.py"
EDGE = ("H3-edge-30db", "H3-edge-34db", "H3-edge-38db", "H3-edge-42db")
VARIANT_RADIO = ("V00_base", "L_0", "L_10", "L_30", "I_block")
ROOT = Path("data/simulated_hardware")
VROOT = ROOT / "variants"
SEEDS = 40
EVAL_SEED = 3000
SF = 7
RATE_PER_H = 20.0
POLS = ("P0", "P1", "P4")
N_BOOT, BSEED = 2000, C.SEED


# `s11_sct.make_cfg` re-reads the 35 MB results.json on every call to get the N16 scheduler parameters; cache it (the values do not change within a run)
S.n16_params = functools.lru_cache(maxsize=None)(S.n16_params)


def calibrate(run: dict) -> dict:
    """Round success q = deliveries / attempts (an attempt is a try of the log: retries + 1 for each packet); symmetric per-direction loss p = 1 - sqrt(q)."""
    rec = run["records"]
    attempts = sum(r["retries"] + 1 for r in rec)
    deliv = sum(1 for r in rec if r["delivered"])
    first = sum(1 for r in rec if r["delivered"] and r["retries"] == 0)
    q = deliv / max(attempts, 1)
    lat = [r["ack_rx_ms"] - r["tx_start_ms"] for r in rec if r["delivered"]]
    return dict(n=len(rec), attempts=attempts, delivered=deliv, final_delivery=deliv / len(rec), first_try=first / len(rec), q=q, p_dir=1 - math.sqrt(q),
                lat_p50=float(np.percentile(lat, 50)) if lat else float("nan"), lat_p95=float(np.percentile(lat, 95)) if lat else float("nan"))


def mini_baselines(p: float, pool: np.ndarray, seed: int, n_events: int, sf: int = SF) -> dict:
    """Tamang-style and Khan-style single-link replays. rx-based times from the event; one car; per-direction iid loss p. ASSUMPTIONS: ACK window = PROC_S + ACK airtime + MARGIN_S (as the
    repository simulator); Khan-style: up to 9 transmissions, retry delay window + U(1, 3) s (LoRaWAN class A style ACK timeout); Tamang-style: one transmission in a uniformly random
    one of K = 8 slots (slot = alert airtime + 20 ms guard), no retry, no ACK needed."""
    rng = np.random.default_rng(seed)
    a_al, a_ack = airtime_ms(P.ALERT_LEN, sf) / 1000.0, airtime_ms(P.ACK_LEN, sf) / 1000.0
    win = PROC_S + a_ack + MARGIN_S
    out = {}
    td = rng.choice(pool, n_events) + COMPUTE_S
    # Khan-style
    rx, ack, air = np.full(n_events, np.inf), np.full(n_events, np.inf), np.zeros(n_events)
    for i in range(n_events):
        t = td[i]
        for _k in range(9):
            air[i] += a_al
            up = rng.random() >= p
            dn = rng.random() >= p
            if up and rx[i] == np.inf:
                rx[i] = t + a_al
            if up and dn:
                ack[i] = t + a_al + win
                break
            t += a_al + win + rng.uniform(1.0, 3.0)
    out["khan"] = dict(rx=rx, ack=ack, air=air)
    # Tamang-style
    slot = a_al + 0.02
    start = td + rng.integers(0, 8, n_events) * slot
    up = rng.random(n_events) >= p
    out["tamang"] = dict(rx=np.where(up, start + a_al, np.inf), ack=np.where(up, start + a_al, np.inf), air=np.full(n_events, a_al))
    return out


def boot_p(d: np.ndarray, margin: float, rng) -> tuple[float, float, float, float]:
    d = np.asarray(d, float)
    b = d[rng.integers(0, len(d), (N_BOOT, len(d)))].mean(axis=1)
    return float(d.mean()), float(np.quantile(b, 0.025)), float(np.quantile(b, 0.975)), float((b <= margin).mean())


def sim_policies(p: float, duty: float, pools: dict, t: dict, params: SctParams) -> pd.DataFrame:
    rows = []
    for h in range(SEEDS):
        for pol in POLS:
            phi = t["phi"] if pol == "P4" else None
            cfg = S.make_cfg(pol, 16.0, dict(n=1, p_up=p, p_down=p, sf=SF, duty=duty), False, EVAL_SEED, h, pools, params, phi, f"s3_p{p:.3f}", dict(rate_per_car_h=RATE_PER_H))
            r = simulate(cfg)
            r.update(pol=pol, hour=h)
            rows.append(r)
    return pd.DataFrame(rows)


def h7_decompose(path: Path) -> dict | None:
    if not path.exists():
        return None
    recs = json.loads(path.read_text(encoding="utf-8"))["records"]
    first = [r for r in recs if r["retries"] == 0 and r["t_ack_rx_ms"] is not None]
    lat = np.array([r["t_ack_rx_ms"] - r["t_first_sample_over_trigger_ms"] for r in first], float)
    allok = np.array([r["t_ack_rx_ms"] - r["t_first_sample_over_trigger_ms"] for r in recs if r["t_ack_rx_ms"] is not None], float)
    comp = dict(window_ms=250.0, compute_ms=float(np.median([r["t_decision_ms"] - r["t_first_sample_over_trigger_ms"] - 250 for r in first])) if first else float("nan"),
                wait_tx_ms=float(np.median([r["t_tx_start_ms"] - r["t_decision_ms"] for r in first])) if first else float("nan"),
                alert_air_ms=float(np.median([r["t_tx_done_ms"] - r["t_tx_start_ms"] for r in first])) if first else float("nan"),
                base_turn_ms=float(np.median([r["base_ack_tx_ms"] - r["base_rx_ms"] for r in first])) if first else float("nan"),
                ack_air_ms=float(np.median([r["t_ack_rx_ms"] - r["base_ack_tx_ms"] for r in first])) if first else float("nan"))
    k = int((lat < 500).sum())
    n = len(lat)
    from scipy.stats import binom

    return dict(n_first_try=n, n_events=len(recs), n_acked=len(allok), median_first_try_ms=float(np.median(lat)) if n else float("nan"), p95_first_try_ms=float(np.percentile(lat, 95)) if n else float("nan"),
                median_all_acked_ms=float(np.median(allok)) if len(allok) else float("nan"), p95_all_acked_ms=float(np.percentile(allok, 95)) if len(allok) else float("nan"),
                n_below_500=k, p_sign=float(binom.cdf(k, n, 0.5)) if n else 1.0, **comp)


def main() -> None:
    rng = np.random.default_rng(BSEED)
    pools = S.load_pools()
    t = {e["name"]: e["value"] for e in json.loads(Path("results/results.json").read_text(encoding="utf-8")) if e["name"].startswith("s11.tuned.")}
    t = dict(h_s=float(t["s11.tuned.h_s"]), rho_f=float(t["s11.tuned.rho_f"]), sf_raise=bool(t["s11.tuned.sf_raise"]), phi=float(t["s11.tuned.phi"]))
    params = SctParams(h_s=t["h_s"], rho_f=t["rho_f"], sf_raise=t["sf_raise"])
    ent: list[dict] = []

    def add(name, value, unit, notes="", origin="SIMULATED_HW_FORMAT"):
        ent.append(dict(name=f"sh.s3.{name}", value=value, unit=unit, origin=origin, source_file=SRC, notes=notes))

    sets = {"supplied": {n: json.loads((ROOT / "protocol_logs" / f"{n}.json").read_text(encoding="utf-8")) for n in EDGE}}
    for v in VARIANT_RADIO:
        sets[v] = {n: json.loads((VROOT / v / "protocol_logs" / f"{n}.json").read_text(encoding="utf-8")) for n in EDGE}
    table = []
    hS3_rows = []
    for setname, runs in sets.items():
        for run, js in runs.items():
            cal = calibrate(js)
            tag = f"{setname}.{run}"
            for k, v in cal.items():
                add(f"{tag}.log.{k}", round(v, 5) if isinstance(v, float) else v, "value", "from the link log; q = deliveries / attempts, p_dir = 1 - sqrt(q) (symmetric assumption)")
            for duty in (0.10, 0.01):
                R = sim_policies(cal["p_dir"], duty, pools, t, params)
                mb = mini_baselines(cal["p_dir"], pools["crash_t"], EVAL_SEED, 2000)
                limit = duty * 3600.0
                row_base = dict(set=setname, run=run, duty=duty, p_dir=cal["p_dir"], log_final=cal["final_delivery"], log_first_try=cal["first_try"])
                for pol in POLS:
                    g = R[R.pol == pol].sort_values("hour")
                    r10 = g.reach10_critical.to_numpy(float)
                    ent_row = dict(row_base, policy=pol, reach10_critical=float(np.nanmean(r10)), reach30_critical=float(np.nanmean(g.reach30_critical.to_numpy(float))),
                                   delivered_critical=float(g.delivered_critical.mean()), median_lat_s=float(g.median_lat_s_critical.mean()), p95_lat_s=float(g.p95_lat_s_critical.mean()),
                                   node_air_share=float(g.node_air_share.mean()), node_air_share_max=float(g.node_air_share.max()), max_window_air_over_allowance=float((g.max_window_airtime_s / limit).max()),
                                   air_per_event_s=float(g.node_air_per_event_s.mean()) if "node_air_per_event_s" in g else float("nan"))
                    table.append(ent_row)
                    for k, v in ent_row.items():
                        if isinstance(v, float) and v == v:
                            add(f"{tag}.duty{int(duty * 100)}.{pol}.{k}", round(v, 5), "value", "repository simulator, one car, 40 paired seeds (3000 to 3039)")
                for nm, m in mb.items():
                    fin = np.isfinite(m["rx"])
                    within = lambda x, lim: float(np.mean(m[x] <= lim))  # noqa: E731
                    lat = m["ack"][np.isfinite(m["ack"])]
                    ent_row = dict(row_base, policy=nm, reach10_critical=within("ack", 10.0), reach30_critical=within("ack", 30.0),
                                   delivered_critical=float(fin.mean()), median_lat_s=float(np.median(lat)) if len(lat) else float("nan"), p95_lat_s=float(np.percentile(lat, 95)) if len(lat) else float("nan"),
                                   node_air_share=float(m["air"].mean() * RATE_PER_H / limit), node_air_share_max=float("nan"),
                                   max_window_air_over_allowance=float("nan"), air_per_event_s=float(m["air"].mean()))
                    table.append(ent_row)
                    for k, v in ent_row.items():
                        if isinstance(v, float) and v == v:
                            add(f"{tag}.duty{int(duty * 100)}.{nm}.{k}", round(v, 5), "value", "minimal single-link replay (ASSUMPTIONS in sh_s3.mini_baselines); sends at once, no cancel window")
            # hypothesis input: UA-SCT (P4) minus fixed-3 (P0) critical reach within 10 s, duty 10%
            if setname == "supplied":
                R = sim_policies(cal["p_dir"], 0.10, pools, t, params)
                a = R[R.pol == "P4"].sort_values("hour").reach10_critical.to_numpy(float)
                b = R[R.pol == "P0"].sort_values("hour").reach10_critical.to_numpy(float)
                m_ = ~(np.isnan(a) | np.isnan(b))
                mean, lo, hi, p = boot_p(a[m_] - b[m_], -0.02, rng)
                add(f"hS3.{run}.diff_P4_minus_P0", round(mean, 5), "fraction", "UA-SCT (P4) minus fixed-3 (P0), critical reach within 10 s, duty 10%, paired by seed")
                add(f"hS3.{run}.diff_lo", round(lo, 5), "fraction", "95% bootstrap interval")
                add(f"hS3.{run}.diff_hi", round(hi, 5), "fraction", "95% bootstrap interval")
                add(f"hS3.{run}.p_raw", round(p, 5), "p", "bootstrap one-sided p of H0: difference <= -0.02 (share of resampled means at or below -0.02)")
                hS3_rows.append(dict(run=run, mean=mean, lo=lo, hi=hi, p=p, max_air=float(R.node_air_share.max())))
    T = pd.DataFrame(table)
    T.to_csv("results/tables/sh_s3_policies.csv", index=False)
    sup = T[(T.set == "supplied") & (T.duty == 0.10) & T.policy.isin(POLS)]
    max_air = float(sup.node_air_share_max.max())
    max_win = float(sup.max_window_air_over_allowance.max())
    ok_diff = all(r["mean"] >= -0.02 for r in hS3_rows)
    ok_air = max_air <= 1.0 and max_win <= 1.0
    p_s3 = max(r["p"] for r in hS3_rows)
    add("hS3.max_node_air_share", round(max_air, 5), "fraction", "largest node airtime share of the duty allowance over the supplied edge runs and policies P0, P1, P4 at duty 10% (must be at most 1)")
    add("hS3.max_window_air_over_allowance", round(max_win, 5), "fraction", "largest trailing-window airtime over the allowance (at most 1)")
    add("hS3.criterion_met", int(ok_diff and ok_air and p_s3 < 1.0), "flag", "UA-SCT at least fixed-3 minus 0.02 in all four edge runs and no airtime above the duty allowance")
    add("hS3.p_raw", round(p_s3, 5), "p", "largest over the four edge runs")
    # H7
    h7 = {"supplied": h7_decompose(ROOT / "protocol_logs" / "e2e_latency_H7.json")}
    for v in VARIANT_RADIO:
        h7[v] = h7_decompose(VROOT / v / "protocol_logs" / "e2e_latency_H7.json")
    for k, d in h7.items():
        if d:
            for kk, vv in d.items():
                add(f"h7.{k}.{kk}", round(vv, 4) if isinstance(vv, float) else vv, "value", "first-try deliveries of the simulated H7 file" if k == "supplied" else "variant")
    a_al, a_ack = airtime_ms(P.ALERT_LEN, SF), airtime_ms(P.ACK_LEN, SF)
    add("h7.analytic.lower_bound_ms", round(250.0 + a_al + a_ack, 2), "ms", "ANALYTICAL: 250 ms window + 97-byte alert airtime + 26-byte ACK airtime at SF7, before any compute, wait or base turnaround", origin="ANALYTICAL")
    d = h7["supplied"]
    add("hS4.criterion_met", int(d["median_first_try_ms"] >= 500.0), "flag", "median trigger-to-ACK of first-try deliveries at least 500 ms")
    add("hS4.p_raw", float(f"{d['p_sign']:.3e}"), "p", "exact one-sided sign test of H0: P(latency < 500 ms) >= 0.5")
    record_many(ent, purge_prefixes=("sh.s3.",))
    print(pd.DataFrame(hS3_rows).round(4).to_string())
    print("max air", max_air, max_win, "p_s3", p_s3, "ok", ok_diff, ok_air)
    print(json.dumps(d, indent=1))
    print(sup.round(3)[["run", "policy", "p_dir", "log_final", "reach10_critical", "reach30_critical", "delivered_critical", "node_air_share_max"]].to_string())


if __name__ == "__main__":
    main()
