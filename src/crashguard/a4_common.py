"""Round 4 data builders (docs/02_preregistration/PREREGISTRATION_V15.md sections 1 and 3).

    python -m crashguard.a4_common sniffer     # fresh trace dataset (Zenodo 7919213): links -> data/processed/a4_sniffer_links.pkl, descriptive json
    python -m crashguard.a4_common loed_gw     # LoED per-gateway reception sequences -> data/processed/a4_loed_gw.pkl

Both builders use the V14 section 1.2 rules unchanged (merge copies of one frame within 2 s, counter gaps of 1 to 100 are lost frames, larger gaps and resets start a new segment,
at least 300 frames). The sniffer builder reads only uplink rows; the LoED builder keeps, per frame, the bit mask of the gateways that decoded it. Raw files are untrusted data: they are
read as text by pandas only.
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

from crashguard.r3_t1_extract import MAX_GAP, MIN_AHEAD, MIN_FRAMES, RESET_BELOW, frames_of_device, half_of

ROOT = Path(__file__).resolve().parents[2]
SNIFF = ROOT / "data" / "raw" / "a4_sniffer" / "x"
LOED = ROOT / "data" / "raw" / "t1_loed" / "x" / "LoED_LoRaWAN_at_edge_dataset"
OUT_SNIFF = ROOT / "data" / "processed" / "a4_sniffer_links.pkl"
OUT_SNIFF_J = ROOT / "results" / "tables" / "a4_sniffer_descriptive.json"
OUT_GW = ROOT / "data" / "processed" / "a4_loed_gw.pkl"
LINKS3 = ROOT / "data" / "processed" / "r3_t1_links.pkl"
SITES = ("01_Brno", "02_Liege", "04_Graz", "05_Wien", "07_Brno")
GROUPS = (("L", 0.0, 0.10), ("M", 0.10, 0.40), ("H", 0.40, 1.01))
UP_TYPES = (2, 4)  # 2 unconfirmed data uplink, 4 confirmed data uplink (index 3 of the sniffer CSV)


def group_of(p: float) -> str:
    for g, lo, hi in GROUPS:
        if lo <= p < hi:
            return g
    return "H"


def link_record(segs: list, extra: dict | None = None) -> dict | None:
    """V14 inclusion: at least 300 frames (received and lost) and at least one start position with 40 frames ahead."""
    n = int(sum(len(r) for r, _ in segs))
    lost = int(sum(int((r == 0).sum()) for r, _ in segs))
    if n < MIN_FRAMES or sum(max(len(r) - MIN_AHEAD, 0) for r, _ in segs) <= 0:
        return None
    rec = dict(segs=segs, n=n, lost=lost, p=lost / n)
    rec.update(extra or {})
    return rec


# ------------------------------------------------------------------------------------------------ sniffer (fresh held-out)
def read_sniffer_site(site: str) -> pd.DataFrame:
    d = pd.read_csv(SNIFF / f"{site}_data.csv", header=None, usecols=[1, 3, 5, 6, 11, 13], names=["t", "mtype", "rssi", "snr", "dev", "fcnt"], dtype={"dev": "int64", "fcnt": "int64", "mtype": "int64"})
    d = d[d.mtype.isin(UP_TYPES) & (d.fcnt >= 0) & (d.dev != 0)]
    return d


def build_sniffer() -> dict:
    links: dict = {}
    stats: dict = dict(sites={})
    for site in SITES:
        d = read_sniffer_site(site)
        n_dev = d.dev.nunique()
        kept = 0
        for dev, g in d.groupby("dev", sort=False):
            segs = frames_of_device(g.t.to_numpy(), g.fcnt.to_numpy())
            rec = link_record(segs, dict(site=site, rssi=float(g.rssi.median()), snr=float(g.snr.median())))
            if rec is None:
                continue
            links[f"{site}:{dev}"] = rec
            kept += 1
        stats["sites"][site] = dict(uplink_rows=int(len(d)), devices_seen=int(n_dev), links_included=kept)
        print(site, stats["sites"][site], flush=True)
    p = np.array([v["p"] for v in links.values()])
    stats["n_included"] = len(links)
    stats["groups"] = {g: int(((p >= lo) & (p < hi)).sum()) for g, lo, hi in GROUPS}
    stats["loss_quantiles"] = {str(q): float(np.quantile(p, q)) for q in (0.05, 0.25, 0.5, 0.75, 0.95)} if len(p) else {}
    stats["rules"] = "PREREGISTRATION_V15 section 1.2 (V14 section 1.2 rules)"
    OUT_SNIFF.parent.mkdir(parents=True, exist_ok=True)
    with OUT_SNIFF.open("wb") as fh:
        pickle.dump(links, fh)
    OUT_SNIFF_J.write_text(json.dumps(stats, indent=1), encoding="utf-8")
    return stats


# ------------------------------------------------------------------------------------------------ LoED per-gateway sequences
def frames_of_device_gw(t: np.ndarray, f: np.ndarray, gw: np.ndarray) -> list:
    """Like ``frames_of_device`` but every frame carries the bit mask of the gateways that decoded it (copies of one frame are OR-ed). Segments are (mask uint16 array, time array); a lost frame has mask 0."""
    o = np.argsort(t, kind="stable")
    t, f, gw = t[o], f[o].astype(np.int64), gw[o].astype(np.uint16)
    if not len(t):
        return []
    keep = np.ones(len(t), bool)
    keep[1:] = (f[1:] != f[:-1]) | (t[1:] - t[:-1] > 2.0)
    starts = np.flatnonzero(keep)
    mask = np.bitwise_or.reduceat(gw, starts)
    t, f = t[keep], f[keep]
    segs: list = []
    cur_m, cur_t = [int(mask[0])], [t[0]]
    for i in range(1, len(t)):
        a, b = f[i - 1], f[i]
        if b == a:
            continue
        if b < a:
            d = b + 65536 - a if a >= RESET_BELOW else MAX_GAP + 1
        else:
            d = b - a
        if d > MAX_GAP:
            segs.append((np.array(cur_m, np.uint16), np.array(cur_t)))
            cur_m, cur_t = [int(mask[i])], [t[i]]
            continue
        if d > 1:
            miss = d - 1
            cur_m.extend([0] * miss)
            cur_t.extend(list(np.linspace(t[i - 1], t[i], miss + 2)[1:-1]))
        cur_m.append(int(mask[i]))
        cur_t.append(t[i])
    segs.append((np.array(cur_m, np.uint16), np.array(cur_t)))
    return segs


def build_loed_gw() -> dict:
    links3 = pickle.loads(LINKS3.read_bytes())
    keep_dev = set(links3)
    files = sorted(glob.glob(str(LOED / "*.csv")))
    gws: dict = {}
    parts = []
    use = ["time", "device_address", "gateway", "crc_status", "mtype", "fcnt"]
    for f in files:
        d = pd.read_csv(f, usecols=use, dtype={"device_address": str, "gateway": str, "mtype": str}, low_memory=False)
        d = d[(d.crc_status == 1) & (d.fcnt >= 0) & (d.device_address != "-1") & d.mtype.isin(["010", "100"]) & d.device_address.isin(keep_dev)]
        t = pd.to_datetime(d["time"], utc=True, errors="coerce", format="ISO8601")
        d = d.assign(t=t.astype("int64") / 1e9)[["t", "device_address", "gateway", "fcnt"]].dropna()
        parts.append(d)
        print(Path(f).name, len(d), flush=True)
    df = pd.concat(parts, ignore_index=True)
    for g in sorted(df.gateway.unique()):
        gws[g] = len(gws)
    df["bit"] = np.left_shift(np.uint16(1), df.gateway.map(gws).to_numpy().astype(np.uint16)).astype(np.uint16)
    out: dict = {}
    for dev, g in df.groupby("device_address", sort=False):
        segs = frames_of_device_gw(g.t.to_numpy(), g.fcnt.to_numpy(), g.bit.to_numpy())
        r3 = links3[dev]
        out[dev] = dict(segs=segs, half=r3["half"], p_union=r3["p"], n=r3["n"])
    res = dict(links=out, gateways=gws)
    with OUT_GW.open("wb") as fh:
        pickle.dump(res, fh)
    print("devices", len(out), "gateways", gws)
    return res


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "sniffer":
        st = build_sniffer()
        print(json.dumps({k: v for k, v in st.items() if k != "sites"}))
    elif cmd == "loed_gw":
        build_loed_gw()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()


def _selfcheck_half(dev: str) -> int:  # kept for tests: the V14 split rule
    return int(hashlib.sha256(("t1|" + dev).encode()).hexdigest(), 16) % 2 == half_of(dev)
