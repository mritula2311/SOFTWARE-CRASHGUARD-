"""T1.2 (docs/02_preregistration/PREREGISTRATION_V14.md section 1.2): loss sequences from LoED frame counters.

    python -I -c ... is not needed: this module only reads the CSV files named below (untrusted data, parsed as text by pandas).
    python -m crashguard.r3_t1_extract            # writes data/processed/r3_t1_links.pkl and results/tables/r3_t1_descriptive.json

Rules (fixed before any loss rate was computed): rows with crc_status 1, a data frame counter and an uplink message type are kept; copies of one frame (same device and counter within 2 s) are
merged; link = device (a frame is received if any gateway decoded it); gap d = (g - f) mod 65536 with 1 <= d <= 100 gives d - 1 lost frames; d = 0 is a duplicate; d > 100, or a counter that
decreases from below 60,000, starts a new segment. Split by device: sha256("t1|" + device_address) mod 2 (0 = DEVELOPMENT, 1 = HELD-OUT). Origin: TRACE_DRIVEN (measured link traces).
"""
from __future__ import annotations

import glob
import hashlib
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "t1_loed" / "x" / "LoED_LoRaWAN_at_edge_dataset"
OUT_PKL = ROOT / "data" / "processed" / "r3_t1_links.pkl"
OUT_JSON = ROOT / "results" / "tables" / "r3_t1_descriptive.json"
MAX_GAP = 100
RESET_BELOW = 60000
MIN_FRAMES = 300
MIN_AHEAD = 40
GROUPS = (("L", 0.0, 0.10), ("M", 0.10, 0.40), ("H", 0.40, 1.01))
USE = ["time", "device_address", "gateway", "crc_status", "spreading_factor", "rssi", "snr", "mtype", "fcnt"]


def half_of(dev: str) -> int:
    return int(hashlib.sha256(("t1|" + dev).encode()).hexdigest(), 16) % 2


def read_all(files: list[str]) -> pd.DataFrame:
    parts = []
    for f in files:
        d = pd.read_csv(f, usecols=USE, dtype={"device_address": str, "gateway": str, "mtype": str}, low_memory=False)
        d = d[(d.crc_status == 1) & (d.fcnt >= 0) & (d.device_address != "-1") & d.mtype.isin(["010", "100"])]
        t = pd.to_datetime(d["time"], utc=True, errors="coerce", format="ISO8601")
        d = d.assign(t=t.astype("int64") / 1e9)[["t", "device_address", "gateway", "fcnt", "rssi", "snr", "spreading_factor"]]
        parts.append(d.dropna())
    return pd.concat(parts, ignore_index=True)


def frames_of_device(t: np.ndarray, f: np.ndarray):
    """Union sequence of one device: merge duplicate copies, build segments of 0/1 reception with interpolated times."""
    o = np.argsort(t, kind="stable")
    t, f = t[o], f[o].astype(np.int64)
    keep = np.ones(len(t), bool)
    keep[1:] = (f[1:] != f[:-1]) | (t[1:] - t[:-1] > 2.0)
    t, f = t[keep], f[keep]
    segs, cur_r, cur_t = [], [1], [t[0]] if len(t) else []
    if not len(t):
        return segs
    for i in range(1, len(t)):
        a, b = f[i - 1], f[i]
        if b == a:
            continue
        if b < a:
            if a >= RESET_BELOW:
                d = b + 65536 - a
            else:
                d = MAX_GAP + 1  # counter reset: new segment
        else:
            d = b - a
        if d > MAX_GAP:
            segs.append((np.array(cur_r, np.uint8), np.array(cur_t)))
            cur_r, cur_t = [1], [t[i]]
            continue
        if d > 1:
            miss = d - 1
            cur_r.extend([0] * miss)
            cur_t.extend(list(np.linspace(t[i - 1], t[i], miss + 2)[1:-1]))
        cur_r.append(1)
        cur_t.append(t[i])
    segs.append((np.array(cur_r, np.uint8), np.array(cur_t)))
    return segs


def descriptive(links: dict) -> dict:
    out: dict = {}
    for name, sel in (("dev", 0), ("held", 1), ("all", None)):
        ds = [d for d, v in links.items() if sel is None or v["half"] == sel]
        p = np.array([links[d]["p"] for d in ds])
        n = np.array([links[d]["n"] for d in ds])
        rec = dict(n_devices=len(ds), n_frames=int(n.sum()), loss_quantiles={q: float(np.quantile(p, q)) for q in (0.05, 0.25, 0.5, 0.75, 0.95)} if len(ds) else {},
                   mean_loss=float(p.mean()) if len(ds) else None,
                   groups={g: int(((p >= lo) & (p < hi)).sum()) for g, lo, hi in GROUPS})
        # autocorrelation of the loss indicator (pooled over devices of the half, within segments) and conditional loss probability
        ac = {k: [0.0, 0.0, 0.0, 0.0, 0.0] for k in range(1, 11)}  # sums: n_pairs, sum xy, sum x, sum y, sum x2 (per lag)
        ll = nn = ln = 0
        for d in ds:
            for r, _t in links[d]["segs"]:
                x = 1 - r.astype(np.float64)  # loss indicator
                for k in range(1, 11):
                    if len(x) > k:
                        a, b = x[:-k], x[k:]
                        s = ac[k]
                        s[0] += len(a)
                        s[1] += float((a * b).sum())
                        s[2] += float(a.sum())
                        s[3] += float(b.sum())
                        s[4] += float((a * a).sum())
                if len(x) > 1:
                    a, b = x[:-1], x[1:]
                    ll += int(((a == 1) & (b == 1)).sum())
                    ln += int((a == 1).sum())
                    nn += len(a)
        rec["autocorr"] = {}
        for k, s in ac.items():
            n_, xy, sx, sy, sx2 = s
            if n_ > 0:
                mx, my = sx / n_, sy / n_
                var = sx2 / n_ - mx * mx
                rec["autocorr"][str(k)] = float((xy / n_ - mx * my) / var) if var > 0 else None
        pl = float(np.sum([links[d]["lost"] for d in ds]) / max(np.sum(n), 1))
        rec["pooled_loss"] = pl
        rec["p_loss_given_prev_loss"] = float(ll / ln) if ln else None
        rec["ratio_cond_to_marginal"] = float(ll / ln / pl) if ln and pl > 0 else None
        # burst lengths (runs of lost frames)
        runs = []
        for d in ds:
            for r, _t in links[d]["segs"]:
                z = np.concatenate([[1], r, [1]])
                idx = np.flatnonzero(z == 1)
                runs.extend((np.diff(idx) - 1)[np.diff(idx) > 1].tolist())
        runs = np.array(runs)
        rec["burst_runs"] = dict(n=int(len(runs)), mean=float(runs.mean()) if len(runs) else None, p95=float(np.quantile(runs, 0.95)) if len(runs) else None,
                                 share_ge2=float((runs >= 2).mean()) if len(runs) else None, max=int(runs.max()) if len(runs) else None)
        out[name] = rec
    return out


def main() -> None:
    files = sorted(glob.glob(str(RAW / "*.csv")))
    print("files", len(files), flush=True)
    df = read_all(files)
    print("rows kept", len(df), "devices", df.device_address.nunique(), flush=True)
    summ = dict(n_files=len(files), rows_kept=int(len(df)), devices_seen=int(df.device_address.nunique()),
                rssi_median=float(df.rssi.median()), snr_median=float(df.snr.median()), rssi_q05=float(df.rssi.quantile(0.05)), snr_q05=float(df.snr.quantile(0.05)))
    links: dict = {}
    n_excl_short = n_excl_ahead = 0
    for dev, g in df.groupby("device_address", sort=False):
        segs = frames_of_device(g.t.to_numpy(), g.fcnt.to_numpy())
        n = int(sum(len(r) for r, _ in segs))
        lost = int(sum(int((r == 0).sum()) for r, _ in segs))
        if n < MIN_FRAMES:
            n_excl_short += 1
            continue
        ahead = sum(max(len(r) - MIN_AHEAD, 0) for r, _ in segs)
        if ahead <= 0:
            n_excl_ahead += 1
            continue
        links[dev] = dict(segs=segs, n=n, lost=lost, p=lost / n, half=half_of(dev), rssi=float(g.rssi.median()), snr=float(g.snr.median()))
    summ.update(n_included=len(links), n_excl_fewer_than_300_frames=n_excl_short, n_excl_no_start_positions=n_excl_ahead)
    OUT_PKL.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PKL.open("wb") as fh:
        pickle.dump(links, fh)
    res = dict(summary=summ, stats=descriptive(links), rules="PREREGISTRATION_V14 section 1.2")
    OUT_JSON.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res["summary"]))
    for k in ("dev", "held"):
        r = res["stats"][k]
        print(k, r["n_devices"], r["groups"], {q: round(v, 3) for q, v in r["loss_quantiles"].items()}, "cond/marg", r["ratio_cond_to_marginal"], "ac1", r["autocorr"].get("1"))


if __name__ == "__main__":
    sys.exit(main())
