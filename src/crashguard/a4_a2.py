"""A2: receiver diversity for crash alerts (docs/02_preregistration/PREREGISTRATION_V15.md section 3). EXPLORATORY: same dataset and network as development.

    python -m crashguard.a4_a2 dev         # DEVELOPMENT devices (round-3 HELD-OUT half): check the code and the ranking rule, descriptive tables (no parameter is chosen)
    python -m crashguard.a4_a2 held        # RESERVE devices (round-3 DEVELOPMENT half): delivery for 1 to 9 receivers (once)
    python -m crashguard.a4_a2 analyse     # H-A2a, H-A2b, curves, descriptive tables, keys ``a4.a2.*``

Per frame the set of gateways that decoded it is stored as a bit mask (``a4_common.build_loed_gw``). For each device the earlier half of its frames (in time, over all segments) is the ranking
period: gateways are ranked by the share of those frames they decoded (ties by gateway index; the mean RSSI named in V15 is not stored in the per-gateway file: logged as a deviation). Start points
of the replay come from the later half only. Policy Z0 (zero-spacing control of V14): alert ready at 1.85 s, retry at once after the listen window, base SF 9, up to 12 tries, 1% duty; delivery =
a transmission that ends before 10 s is decoded by at least one gateway of the receiver set. Attempt k sees frame s + k.
"""
from __future__ import annotations

import json
import pickle
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from crashguard import r3_t1 as T1

ROOT = Path(__file__).resolve().parents[2]
SRC = "src/crashguard/a4_a2.py"
GW = ROOT / "data" / "processed" / "a4_loed_gw.pkl"
OUT_DEV = ROOT / "data" / "processed" / "a4_a2_dev.pkl"
OUT_HELD = ROOT / "data" / "processed" / "a4_a2_held.pkl"
K_MAX = 9
N_START = 300
SEED = 42
BANDS = (("L", 0.0, 0.10), ("M", 0.10, 0.40), ("H", 0.40, 1.01))


def ranking(segs: list, n_gw: int = K_MAX) -> dict:
    """Ranking period = the earlier half of the device's frames (over all segments in time order). Returns the ranked heard gateways, the loss rate of the best one and the number of ranking frames."""
    n = int(sum(len(m) for m, _ in segs))
    n_rank = n // 2
    cnt = np.zeros(n_gw, np.int64)
    seen = 0
    for m, _t in segs:
        take = max(0, min(len(m), n_rank - seen))
        if take:
            part = m[:take]
            for g in range(n_gw):
                cnt[g] += int(((part >> g) & 1).sum())
        seen += len(m)
        if seen >= n_rank:
            break
    order = [g for g in sorted(range(n_gw), key=lambda g: (-cnt[g], g)) if cnt[g] > 0]
    share = (cnt / max(n_rank, 1)).tolist()
    loss_best = float(1.0 - (cnt[order[0]] / max(n_rank, 1))) if order else 1.0
    return dict(order=order, share=share, loss_best=loss_best, n_rank=n_rank, n_total=n)


def test_positions(segs: list, n_rank: int) -> list[tuple[int, int]]:
    """Start positions (segment, index) with at least MIN_AHEAD frames ahead in the segment, in the later half of the device's frames."""
    out = []
    off = 0
    for i, (m, _t) in enumerate(segs):
        for j in range(0, max(len(m) - T1.MIN_AHEAD, 0)):
            if off + j >= n_rank:
                out.append((i, j))
        off += len(m)
    return out


def set_mask(order: list[int], k: int) -> int:
    mk = 0
    for g in order[:k]:
        mk |= 1 << g
    return mk


def set_sequence(m: np.ndarray, mask: int) -> np.ndarray:
    """0/1 reception sequence of a receiver set: a frame is received if at least one gateway of the set decoded it."""
    return ((m & mask) != 0).astype(np.uint8)


_RNG = T1.seeded("a2", 0)


def z0_delivered(r: np.ndarray, pos: int) -> bool:
    """Delivery of one alert by policy Z0 on the 0/1 sequence of a receiver set (the frozen replay of V14; Z0 uses no random number and the ACK does not change the delivery)."""
    t, _n, _u = T1.replay_alert("Z0", r, pos, _RNG, 0.0)
    return bool(np.isfinite(t))


def device_task(args: tuple) -> dict | None:
    dev, segs, n_start, all_positions = args
    T1.INV.update(late_delivery=0, duty_exceeded=0, frame_overrun=0)
    rk = ranking(segs)
    if not rk["order"]:
        return None
    if all_positions:  # round-3 start rule (known-answer check only)
        adm = T1.admissible([(m, t) for m, t in segs])
        rng0 = T1.seeded("t1s", dev, T1.SEED)
    else:
        adm = test_positions(segs, rk["n_rank"])
        rng0 = T1.seeded("a2s", dev, SEED)
    if not adm:
        return None
    picks = [adm[rng0.randrange(len(adm))] for _ in range(n_start)]
    ks = list(range(1, K_MAX + 1))
    masks = [set_mask(rk["order"], k) for k in ks]
    rseg = [[set_sequence(m, mk) for m, _t in segs] for mk in masks]
    val = np.zeros(len(ks))
    for si, pos in picks:
        for a in range(len(masks)):
            val[a] += z0_delivered(rseg[a][si], pos)
    val /= len(picks)
    return dict(dev=dev, loss_best=rk["loss_best"], n_heard=len(rk["order"]), value=val.tolist(), n_rank=rk["n_rank"], n_total=rk["n_total"], inv=dict(T1.INV))


def run(half: int, out: Path, max_dev: int | None = None, workers: int = 14) -> dict:
    d = pickle.loads(GW.read_bytes())
    devs = sorted(k for k, v in d["links"].items() if v["half"] == half)
    if max_dev:
        devs = devs[:max_dev]
    tasks = [(k, d["links"][k]["segs"], N_START, False) for k in devs]
    with ProcessPoolExecutor(workers) as ex:
        res = [x for x in ex.map(device_task, tasks, chunksize=8)]
    kept = [x for x in res if x is not None]
    inv = {k: sum(x["inv"][k] for x in kept) for k in T1.INV}
    pickle.dump(dict(res=kept, n_candidates=len(devs), inv=inv, half=half), out.open("wb"))
    print("devices", len(kept), "of", len(devs), "invariants", inv, flush=True)
    return dict(res=kept, inv=inv)


def band_of(p: float) -> str:
    for g, lo, hi in BANDS:
        if lo <= p < hi:
            return g
    return "H"


def analyse() -> dict:
    from crashguard.results import record_many

    out: dict = {}
    ent: list[dict] = []
    rng = np.random.default_rng(SEED)
    NB = 2000

    def add(name, value, unit, notes=""):
        ent.append(dict(name=f"a4.a2.{name}", value=round(value, 6) if isinstance(value, float) else value, unit=unit, origin="NOT_RUN" if value == "NOT_RUN" else "TRACE_DRIVEN", source_file=SRC, notes="EXPLORATORY (same dataset as development). " + notes))

    for tag, f in (("reserve", OUT_HELD), ("dev", OUT_DEV)):
        if not f.exists():
            continue
        d = pickle.loads(f.read_bytes())
        res = d["res"]
        V = np.array([x["value"] for x in res])  # (n, 9)
        lb = np.array([x["loss_best"] for x in res])
        nh = np.array([x["n_heard"] for x in res])
        n = len(res)
        add(f"{tag}.n_devices", n, "devices", f"devices with at least one gateway in the ranking period and at least one start position in the later half (of {d['n_candidates']})")
        add(f"{tag}.share_one_gateway", float((nh == 1).mean()), "fraction", "devices heard by one gateway only in the ranking period (they gain nothing from more receivers)")
        for g, lo, hi in BANDS:
            add(f"{tag}.band.{g}.n", int(((lb >= lo) & (lb < hi)).sum()), "devices", f"loss band {g} of the best gateway in the ranking period")
        B = rng.integers(0, n, size=(NB, n))
        mean_curve = V[B].mean(1)  # (NB, 9)
        share99 = (V >= 0.99).astype(float)
        sh_boot = share99[B].mean(1)
        for k in range(K_MAX):
            add(f"{tag}.curve.mean_delivery.k{k+1}", float(V[:, k].mean()), "fraction", "mean device value of delivery within 10 s, all devices")
            add(f"{tag}.curve.mean_delivery.k{k+1}_lo", float(np.quantile(mean_curve[:, k], 0.025)), "fraction", "95% bootstrap over devices, 2,000 resamples, seed 42")
            add(f"{tag}.curve.mean_delivery.k{k+1}_hi", float(np.quantile(mean_curve[:, k], 0.975)), "fraction", "95% bootstrap over devices")
            add(f"{tag}.curve.share99.k{k+1}", float(share99[:, k].mean()), "fraction", "share of devices with a device value of at least 0.99")
            add(f"{tag}.curve.share99.k{k+1}_lo", float(np.quantile(sh_boot[:, k], 0.025)), "fraction", "95% bootstrap over devices")
            add(f"{tag}.curve.share99.k{k+1}_hi", float(np.quantile(sh_boot[:, k], 0.975)), "fraction", "95% bootstrap over devices")
        for g, lo, hi in BANDS:
            idx = np.flatnonzero((lb >= lo) & (lb < hi))
            if not len(idx):
                continue
            Bg = rng.integers(0, len(idx), size=(NB, len(idx)))
            for k in range(K_MAX):
                add(f"{tag}.band.{g}.mean_delivery.k{k+1}", float(V[idx, k].mean()), "fraction", f"mean device value, band {g}")
                bm = V[idx][Bg][:, :, k].mean(1)
                add(f"{tag}.band.{g}.mean_delivery.k{k+1}_lo", float(np.quantile(bm, 0.025)), "fraction", "95% bootstrap over devices")
                add(f"{tag}.band.{g}.mean_delivery.k{k+1}_hi", float(np.quantile(bm, 0.975)), "fraction", "95% bootstrap over devices")
            for thr in (0.95, 0.99):
                need = np.array([next((k + 1 for k in range(K_MAX) if V[i, k] >= thr), 0) for i in idx])
                ok = need > 0
                add(f"{tag}.band.{g}.need{int(thr*100)}.share_reached", float(ok.mean()), "fraction", f"share of band-{g} devices that reach a device value of {thr} with at most 9 receivers")
                if ok.any():
                    q = np.quantile(need[ok], [0.25, 0.5, 0.75])
                    add(f"{tag}.band.{g}.need{int(thr*100)}.median", float(q[1]), "receivers", f"median smallest number of receivers (devices that reach {thr}); IQR {q[0]:.0f} to {q[2]:.0f}")
        # H-A2a on the weak band
        w = np.flatnonzero(lb >= 0.40)
        if len(w) >= 20:
            Bw = rng.integers(0, len(w), size=(NB, len(w)))
            diff = V[w, 1] - V[w, 0]
            bd = diff[Bw].mean(1)
            pt = float(diff.mean())
            lo_ = float(np.quantile(bd, 0.025))
            met = bool(pt >= 0.10 and lo_ > 0)
            p_ = float((np.count_nonzero(bd <= 0) + 1) / (NB + 1))
            add(f"{tag}.hA2a.n_weak", len(w), "devices", "devices with best-gateway loss of at least 0.40")
            add(f"{tag}.hA2a.diff", pt, "fraction", "delivery with two receivers minus one receiver, weak devices")
            add(f"{tag}.hA2a.diff_lo", lo_, "fraction", "95% bootstrap lower limit")
            add(f"{tag}.hA2a.diff_hi", float(np.quantile(bd, 0.975)), "fraction", "95% bootstrap upper limit")
            add(f"{tag}.hA2a.criterion_met", int(met), "flag", "point difference at least 0.10 and lower 95% limit above 0")
            add(f"{tag}.hA2a.p_raw", p_, "p", "one-sided bootstrap p of H0: difference at most 0")
            sub = w[nh[w] >= 2]
            if len(sub):
                add(f"{tag}.hA2a.diff_two_plus_heard", float((V[sub, 1] - V[sub, 0]).mean()), "fraction", f"same difference over the {len(sub)} weak devices heard by at least two gateways (descriptive)")
            out[f"{tag}.hA2a"] = dict(point=pt, lo=lo_, met=met, p=p_, n=len(w))
        else:
            add(f"{tag}.hA2a.criterion_met", "NOT_RUN", "status", "fewer than 20 weak devices")
        # H-A2b on all devices
        dshare = share99[:, 2] - share99[:, 0]
        bd = dshare[B].mean(1)
        pt = float(dshare.mean())
        lo_ = float(np.quantile(bd, 0.025))
        met = bool(pt >= 0.02 and lo_ > 0)
        p_ = float((np.count_nonzero(bd <= 0) + 1) / (NB + 1))
        add(f"{tag}.hA2b.diff", pt, "fraction", "share of devices at or above 0.99 with three receivers minus one receiver")
        add(f"{tag}.hA2b.diff_lo", lo_, "fraction", "95% bootstrap lower limit")
        add(f"{tag}.hA2b.diff_hi", float(np.quantile(bd, 0.975)), "fraction", "95% bootstrap upper limit")
        add(f"{tag}.hA2b.criterion_met", int(met), "flag", "difference at least 0.02 and lower 95% limit above 0")
        add(f"{tag}.hA2b.p_raw", p_, "p", "one-sided bootstrap p of H0: difference at most 0")
        out[f"{tag}.hA2b"] = dict(point=pt, lo=lo_, met=met, p=p_)
        add(f"{tag}.invariants.late_delivery", d["inv"]["late_delivery"], "count", "must be 0")
        add(f"{tag}.invariants.duty_exceeded", d["inv"]["duty_exceeded"], "count", "must be 0")
    record_many(ent, purge_prefixes=("a4.a2.",))
    (ROOT / "results" / "tables" / "a4_a2_summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "dev":
        run(1, OUT_DEV)
    elif cmd == "held":
        run(0, OUT_HELD)
    elif cmd == "analyse":
        o = analyse()
        for k, v in o.items():
            print(k, v)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
