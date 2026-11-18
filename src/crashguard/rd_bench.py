"""X4: parser for the two-stage alert bench logs (docs/08_hardware/R3_BENCH_PROTOCOL.md). Turns the car and base logs of the bench run into the same tables as the R3 simulation (`ar_r3.py`): provisional alert earlier than the
confirmation, retraction share, extra airtime of the two-stage scheme, delivery within 10 s.

Log format (one CSV line per event, header ``trial,role,event,t_us,len,sf,rssi,snr,extra``), written by the hooks in ``firmware_rd/bench/cg_bench_log.h``:
  car  : SYNC, TRIGGER, PROV_TX_START, PROV_TX_END, PROV_ACK_RX, CONFIRM_TX_START, CONFIRM_TX_END, CANCEL_TX_START, CANCEL_TX_END, FINAL_ACK_RX, ACK_TIMEOUT
  base : SYNC, PROV_RX, PROV_ACK_TX_START, PROV_ACK_TX_END, CONFIRM_RX, CANCEL_RX, FINAL_ACK_TX_START, FINAL_ACK_TX_END
Both devices log their own micros() (a 32-bit counter that wraps every 71.6 minutes: unwrapped here per device). A wired GPIO pulse at the start of every trial is logged as SYNC on both devices; the
offset of each trial is base SYNC minus car SYNC, so car times are mapped to the base clock with no assumption about the radio path.
``taps.csv``: ``trial,tap,condition`` with tap in {above, below} (the operator's label of the tap against the trigger threshold) and condition in {10m, wall}.

Nothing here reads data/hardware. Until real logs are supplied, the hardware row of the paper is NOT_RUN. Output origin is HARDWARE when real logs are parsed; a fixture in tests/dummy is synthetic and its tables are never written to results/.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import numpy as np

from crashguard.lora import airtime_ms

WRAP = 2**32


def read_log(path: str | Path) -> list[dict]:
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            r["trial"], r["t_us"] = int(r["trial"]), int(r["t_us"])
            for k in ("len", "sf"):
                r[k] = int(r[k]) if r.get(k) not in (None, "") else 0
            for k in ("rssi", "snr"):
                r[k] = float(r[k]) if r.get(k) not in (None, "") else float("nan")
            rows.append(r)
    return rows


def unwrap(rows: list[dict]) -> list[dict]:
    """Make t_us monotone per device (micros() wraps at 2^32)."""
    off, last = 0, None
    for r in rows:
        if last is not None and r["t_us"] + off < last - WRAP // 2:
            off += WRAP
        r["t_us"] += off
        last = r["t_us"]
    return rows


def by_trial(rows: list[dict]) -> dict[int, dict[str, list[dict]]]:
    d: dict = defaultdict(lambda: defaultdict(list))
    for r in rows:
        d[r["trial"]][r["event"]].append(r)
    return d


def read_taps(path: str | Path) -> dict[int, tuple[str, str]]:
    with open(path, newline="", encoding="utf-8") as fh:
        return {int(r["trial"]): (r["tap"], r["condition"]) for r in csv.DictReader(fh)}


def trial_table(car_rows: list[dict], base_rows: list[dict], taps: dict[int, tuple[str, str]], deadline_s: float = 10.0) -> list[dict]:
    car, base = by_trial(unwrap(car_rows)), by_trial(unwrap(base_rows))
    out = []
    for tr, (tap, cond) in sorted(taps.items()):
        c, b = car.get(tr, {}), base.get(tr, {})
        if "SYNC" not in c or "SYNC" not in b:
            out.append(dict(trial=tr, tap=tap, condition=cond, valid=0, reason="no sync pulse on both devices"))
            continue
        off = b["SYNC"][0]["t_us"] - c["SYNC"][0]["t_us"]  # add to a car time to get the base clock
        t = lambda d, k, i=0: (d[k][i]["t_us"] / 1e6) if k in d and len(d[k]) > i else float("nan")  # noqa: E731
        trig = (c["TRIGGER"][0]["t_us"] + off) / 1e6 if "TRIGGER" in c else float("nan")
        prov_rx, conf_rx, canc_rx = t(b, "PROV_RX"), t(b, "CONFIRM_RX"), t(b, "CANCEL_RX")
        sf = (c.get("PROV_TX_START") or c.get("CONFIRM_TX_START") or [dict(sf=0)])[0]["sf"]
        n_canc = len(c.get("CANCEL_TX_START", []))
        prov_len = (c.get("PROV_TX_START") or [dict(len=0)])[0]["len"]
        conf_len = (c.get("CONFIRM_TX_START") or [dict(len=0)])[0]["len"]
        canc_len = (c.get("CANCEL_TX_START") or [dict(len=0)])[0]["len"]
        out.append(dict(
            trial=tr, tap=tap, condition=cond, valid=1, sf=sf, triggered=int("TRIGGER" in c), provisional_sent=int("PROV_TX_START" in c), confirm_sent=int("CONFIRM_TX_START" in c), cancel_sent=int(n_canc > 0),
            prov_rx_after_trigger_s=prov_rx - trig, confirm_rx_after_trigger_s=conf_rx - trig, confirm_minus_prov_rx_s=conf_rx - prov_rx,
            prov_delivered_in_deadline=int(prov_rx - trig <= deadline_s) if not np.isnan(prov_rx) else 0,
            final_delivered_in_deadline=int(conf_rx - trig <= deadline_s) if not np.isnan(conf_rx) else 0,
            prov_rssi=(b.get("PROV_RX") or [dict(rssi=float("nan"))])[0]["rssi"], prov_snr=(b.get("PROV_RX") or [dict(snr=float("nan"))])[0]["snr"],
            two_stage_air_s=sum(airtime_ms(x, sf) / 1000 for x in [prov_len] * len(c.get("PROV_TX_START", [])) + [conf_len] * len(c.get("CONFIRM_TX_START", [])) + [canc_len] * n_canc) if sf else float("nan"),
            single_stage_air_s=(airtime_ms(conf_len, sf) / 1000 * max(len(c.get("CONFIRM_TX_START", [])), 1)) if sf and conf_len else float("nan"), canc_rx_s=canc_rx))
    return out


def summary(rows: list[dict], boot: int = 2000, seed: int = 42) -> list[dict]:
    """Per condition: the quantities of H-R3, with a bootstrap over trials (the unit of the bench run)."""
    rng = np.random.default_rng(seed)
    res = []
    for cond in sorted({r["condition"] for r in rows if r["valid"]}):
        rs = [r for r in rows if r["valid"] and r["condition"] == cond]
        above = [r for r in rs if r["tap"] == "above"]
        both = [r for r in above if r["provisional_sent"] and r["confirm_sent"] and not np.isnan(r["confirm_minus_prov_rx_s"])]
        prov = [r for r in rs if r["provisional_sent"]]
        retr = [r for r in prov if r["cancel_sent"]]

        def med_ci(x):
            x = np.array(x, float)
            if len(x) == 0:
                return float("nan"), float("nan"), float("nan")
            m = np.median(x[rng.integers(0, len(x), (boot, len(x)))], axis=1)
            return float(np.median(x)), float(np.quantile(m, 0.025)), float(np.quantile(m, 0.975))

        e = med_ci([r["confirm_minus_prov_rx_s"] for r in both])
        sa = sum(r["single_stage_air_s"] for r in above if not np.isnan(r["single_stage_air_s"]))
        ta = sum(r["two_stage_air_s"] for r in rs if not np.isnan(r["two_stage_air_s"]))
        res.append(dict(condition=cond, trials=len(rs), taps_above=len(above), taps_below=len(rs) - len(above), provisional_sent=len(prov), retractions=len(retr), retraction_share=(len(retr) / len(prov)) if prov else float("nan"),
                        earlier_median_s=e[0], earlier_lo=e[1], earlier_hi=e[2], earlier_n=len(both), extra_airtime_ratio=(ta / sa - 1.0) if sa > 0 else float("nan"),
                        prov_delivered_share=float(np.mean([r["prov_delivered_in_deadline"] for r in above])) if above else float("nan"), final_delivered_share=float(np.mean([r["final_delivered_in_deadline"] for r in above])) if above else float("nan")))
    return res


def write_tables(trials: list[dict], summ: list[dict], outdir: str | Path) -> None:
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    for name, rows in (("bench_trials.csv", trials), ("bench_summary.csv", summ)):
        keys = sorted({k for r in rows for k in r})
        with open(out / name, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=keys)
            w.writeheader()
            w.writerows(rows)


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 5:
        raise SystemExit("usage: python -m crashguard.rd_bench car.csv base.csv taps.csv outdir")
    trials = trial_table(read_log(sys.argv[1]), read_log(sys.argv[2]), read_taps(sys.argv[3]))
    summ = summary(trials)
    write_tables(trials, summ, sys.argv[4])
    for r in summ:
        print(r)
