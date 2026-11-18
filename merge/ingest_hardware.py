"""Hardware ingest and H1-H6 analysis (FR7). Run as ``python merge/ingest_hardware.py``.

The `experiment` column of hw_events.csv uses the minimum-plan IDs H1 to H6 (old E-IDs in older logs are mapped).
- data/hardware/ is read-only: this script never writes there.
- Files that do not exist give NOT_RUN entries; nothing is filled in.
- ``--dummy`` runs the analysis on the synthetic files in tests/dummy/, writes only to tests/dummy/out/ and
  puts a DUMMY DATA watermark on every figure. Its numbers never go to results/.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from crashguard import config as C  # noqa: E402
from crashguard.results import record_many  # noqa: E402

HW = Path("data/hardware")
SIDES = ["F", "R", "L", "Rt", "V"]
SIDE_ANGLE = {"F": 0.0, "L": 90.0, "R": 180.0, "Rt": 270.0}  # ASSUMPTION: angle = atan2 of the horizontal impulse, 0 = front, counter-clockwise
SW_ORDER = ["fl", "fr", "ml", "mr", "rl"]
SW_SIDE = {"fl": "F", "fr": "F", "ml": "L", "mr": "Rt", "rl": "R"}  # ASSUMPTION from the sensor names; check against the mounting

REQUIRED = {
    "hw_events.csv": ["event_id", "experiment", "true_label", "true_side", "distance_m", "walls",
                      "rule_sev", "ml_prob", "pred_side", "angle_deg", "peak_g", "sw_fl", "sw_fr", "sw_ml", "sw_mr", "sw_rl", "sw_first",
                      "sw_pre_edges", "classify_us", "ml_us", "verify_us", "airtime_ms", "ack_rtt_ms", "first_tx_to_ack_ms",
                      "trigger_to_ack_ms", "retries", "delivered", "rssi", "snr"],
    "hw_windows.csv": ["event_id", "t_ms", "ax", "ay", "az", "gx", "gy", "gz"],
    "hw_attacks.csv": ["case", "expected", "observed"],
    "hw_memory.csv": ["item", "bytes"],
}
# Minimum hardware plan. The `experiment` column of hw_events.csv holds these IDs.
EXPERIMENTS = {"H1": "impact side (10 hits x 4 sides + 10 vertical drops)",
               "H2": "crash vs not-crash (H1 hits + 30 non-crashes) and transfer from VZCrash",
               "H3": "LoRa delivery (20 alerts each at 10, 50 and 100 m, optional wall)",
               "H4": "security (forged, tampered, replay, spoofed ACK, base reboot, ACK-lost retry; 3 tries each)",
               "H5": "edge cost (compile report + logged microseconds)",
               "H6": "SW-420 ablation (re-analysis of H1 and H2)"}
# Dropped from the minimum set (limitations): severity against peak g (old E3) and 200 m runs.
ALIAS = {"E1": "H1", "E2": "H2", "E4": "H3", "E5": "H4", "E6": "H5", "E8": "H6"}  # old IDs in older logs


class Sink:
    """Collects entries; writes to results.json only for real data."""

    def __init__(self, dummy: bool, out_dir: Path):
        self.dummy, self.out_dir, self.items = dummy, out_dir, []

    def add(self, name, value, unit, origin, source, notes=""):
        self.items.append(dict(name=name, value=value, unit=unit, origin=origin, source_file=source, notes=notes))

    def hw(self, name, value, unit, source, notes=""):
        v = value.item() if hasattr(value, "item") else value
        self.add(name, v, unit, "HARDWARE", source, notes)

    def not_run(self, name, reason, source="data/hardware"):
        self.add(name, "NOT_RUN", "", "NOT_RUN", source, reason)

    def flush(self):
        if self.dummy:
            self.out_dir.mkdir(parents=True, exist_ok=True)
            (self.out_dir / "dummy_results.json").write_text(json.dumps(self.items, indent=2, default=str), encoding="utf-8")
        else:
            record_many(self.items)


def load(hw: Path, name: str) -> tuple[pd.DataFrame | None, str]:
    """Read one hardware CSV. Returns (frame or None, reason when missing or invalid)."""
    p = hw / name
    if not p.exists():
        return None, f"{name} not found"
    df = pd.read_csv(p)
    missing = [c for c in REQUIRED[name] if c not in df.columns]
    if missing:
        return None, f"{name} is missing columns {missing}"
    return df, ""


def _unit(col: str) -> str:
    for key, u in (("latency", "ms"), ("throughput", "bps"), ("packet_bytes", "bytes"), ("loss", "pct")):
        if key in col:
            return u
    return ""


def ingest_existing(hw: Path, s: Sink) -> None:
    """Author's measured protocol, TCP and LoRa files, copied into results with their HARDWARE label."""
    p = hw / "protocols.csv"
    if p.exists():
        for r in pd.read_csv(p).to_dict("records"):
            for col, v in r.items():
                if col not in ("protocol", "origin", "transport", "port"):
                    s.hw(f"hw.protocol.{r['protocol']}.{col}", v, _unit(col), "data/hardware/protocols.csv")
    p = hw / "tcp.csv"
    if p.exists():
        for r in pd.read_csv(p).to_dict("records"):
            s.hw(f"hw.tcp.{r['metric']}", r["value"], r["unit"], "data/hardware/tcp.csv")
    p = hw / "lora_packets.csv"
    if p.exists():
        for r in pd.read_csv(p).to_dict("records"):
            base = f"hw.lora_packet.{r['kind'].lower()}{r['sequence']}"
            for col, unit in (("bytes", "bytes"), ("rssi_dbm", "dBm"), ("snr_db_min", "dB"), ("snr_db_max", "dB")):
                s.hw(f"{base}.{col}", r[col], unit, "data/hardware/lora_packets.csv")
    p = hw / "lora_gateway.csv"
    if p.exists():
        for r in pd.read_csv(p).to_dict("records"):
            for col in ("uptime_s", "valid", "unique", "duplicate", "invalid", "ack_sent", "ack_fail"):
                s.hw(f"hw.lora_gateway.snapshot{r['snapshot']}.{col}", r[col], "s" if col == "uptime_s" else "frames", "data/hardware/lora_gateway.csv")
    s.not_run("hw.lora_pdr", "the transmitter total is missing, so a delivery ratio cannot be computed", "data/hardware/lora_gateway.csv")


def prf(y: np.ndarray, pred: np.ndarray) -> dict:
    tp, fp, fn = int((pred & y).sum()), int((pred & ~y).sum()), int((~pred & y).sum())
    p = tp / (tp + fp) if tp + fp else float("nan")
    r = tp / (tp + fn) if tp + fn else float("nan")
    return dict(precision=p, recall=r, f1=(2 * tp / (2 * tp + fp + fn)) if (2 * tp + fp + fn) else float("nan"),
                fpr=fp / ((~y).sum()) if (~y).sum() else float("nan"), n=len(y))


def _wm(fig, dummy: bool, name: str, out_dir: Path) -> None:
    from crashguard.plots import save

    save(fig, name, out_dir=out_dir, dummy=dummy)


def h1(ev, s, out, dummy):
    d = ev[ev.experiment == "H1"]
    if d.empty:
        return s.not_run("hw.H1", "no H1 rows in hw_events.csv")
    cm = pd.crosstab(d.true_side, d.pred_side).reindex(index=SIDES, columns=SIDES, fill_value=0)
    cm.to_csv(out / "h1_confusion.csv")
    acc = float((d.true_side == d.pred_side).mean())
    s.hw("hw.H1.side_accuracy", acc, "fraction", "data/hardware/hw_events.csv", f"{len(d)} hits; 5 classes")
    h = d[d.true_side.isin(SIDE_ANGLE)].copy()
    err = np.abs((h.angle_deg - h.true_side.map(SIDE_ANGLE) + 180) % 360 - 180)
    s.hw("hw.H1.angle_error_median_deg", float(err.median()), "deg", "data/hardware/hw_events.csv", "assumed angle convention: 0 front, 90 left, 180 rear, 270 right")
    s.hw("hw.H1.angle_error_p90_deg", float(err.quantile(0.9)), "deg", "data/hardware/hw_events.csv")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(4.8, 4))
    ax.imshow(cm.to_numpy(), cmap="Blues")
    for i in range(5):
        for j in range(5):
            ax.text(j, i, cm.iat[i, j], ha="center", va="center")
    ax.set_xticks(range(5), SIDES)
    ax.set_yticks(range(5), SIDES)
    ax.set_xlabel("Predicted side")
    ax.set_ylabel("True side")
    ax.grid(False)
    _wm(fig, dummy, "h1_direction_confusion", out)


def h2(ev, s, out, dummy, thr):
    d = ev[ev.experiment.isin(["H1", "H2"])]  # H1 hits are the crashes, H2 holds the non-crashes
    if d.empty:
        return s.not_run("hw.H2", "no H1 or H2 rows in hw_events.csv")
    y = (d.true_label == "crash").to_numpy()
    rule = (d.rule_sev.fillna(0) > 0).to_numpy()  # ASSUMPTION: rule_sev > 0 means the rule flagged a crash
    for name, pred in (("rule", rule), ("model", (d.ml_prob >= thr).to_numpy() if thr is not None else None)):
        if pred is None:
            s.not_run(f"hw.H2.{name}", "no model threshold available (run make train)")
            continue
        for k, v in prf(y, pred).items():
            s.hw(f"hw.H2.{name}.{k}", v, "count" if k == "n" else "fraction", "data/hardware/hw_events.csv", f"{int(y.sum())} crashes, {int((~y).sum())} non-crashes")


def h3(ev, s, out, dummy):
    d = ev[ev.experiment == "H3"]
    if d.empty:
        return s.not_run("hw.H3", "no H3 rows in hw_events.csv")
    rows = []
    for (dist, walls), g in d.groupby(["distance_m", "walls"]):
        first = ((g.delivered == 1) & (g.retries == 0)).mean()
        rows.append(dict(distance_m=dist, walls=walls, n=len(g), first_try_pdr=first, final_pdr=(g.delivered == 1).mean(),
                         ack_rtt_ms_median=g.ack_rtt_ms.median(), trigger_to_ack_ms_median=g.trigger_to_ack_ms.median(),
                         rssi_median=g.rssi.median(), snr_median=g.snr.median()))
        base = f"hw.H3.d{dist}.w{walls}"
        for k in ("n", "first_try_pdr", "final_pdr", "ack_rtt_ms_median", "trigger_to_ack_ms_median", "rssi_median", "snr_median"):
            s.hw(f"{base}.{k}", rows[-1][k], {"n": "alerts", "rssi_median": "dBm", "snr_median": "dB"}.get(k, "ms" if k.endswith("ms_median") else "fraction"), "data/hardware/hw_events.csv")
    pd.DataFrame(rows).to_csv(out / "h3_delivery.csv", index=False)
    import matplotlib.pyplot as plt

    t = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=(5.5, 3.8))
    for w, g in t.groupby("walls"):
        ax.plot(g.distance_m, g.final_pdr * 100, marker="o", label=f"walls {w}, final")
        ax.plot(g.distance_m, g.first_try_pdr * 100, marker="s", ls="--", label=f"walls {w}, first try")
    ax.set_xlabel("Distance (m)")
    ax.set_ylabel("Alerts delivered (%)")
    ax.legend(fontsize=7)
    _wm(fig, dummy, "h3_delivery_vs_distance", out)
    # simulation against measurement (figure 3 of EXPERIMENTS.md), SF7 scenario A at 0% loss for orientation only
    sim = Path("results/tables/s9_delivery_summary.csv")
    if sim.exists():
        sm = pd.read_csv(sim)
        sm = sm[(sm.scenario == "A_sf7_normal") & (sm.policy == "fixed3") & (sm["mode"] == "reack")].sort_values("loss")
        fig, ax = plt.subplots(figsize=(5.5, 3.8))
        ax.plot(sm.loss * 100, sm["acked_all.mean"] * 100, marker="o", label="simulation (SIMULATED), ACK received")
        ax.axhline(float((d.delivered == 1).mean() * 100), color="C3", ls="--", label="measured overall final PDR (HARDWARE)")
        ax.set_xlabel("Simulated packet loss per transmission (%)")
        ax.set_ylabel("Alerts delivered (%)")
        ax.legend(fontsize=7)
        _wm(fig, dummy, "h3_simulation_vs_measured", out)


def h4(att, s, out, dummy):
    if att is None:
        return s.not_run("hw.H4", "hw_attacks.csv missing")
    att = att.assign(match=att.expected.astype(str) == att.observed.astype(str))
    att.to_csv(out / "h4_attacks.csv", index=False)
    s.hw("hw.H4.cases", len(att), "cases", "data/hardware/hw_attacks.csv")
    s.hw("hw.H4.cases_matching_expected", int(att.match.sum()), "cases", "data/hardware/hw_attacks.csv")


def h5(ev, mem, s, out, dummy):
    stages = ["classify_us", "ml_us", "verify_us", "airtime_ms", "ack_rtt_ms", "trigger_to_ack_ms"]
    for c in stages:
        x = ev[c].dropna()
        if len(x):
            u = "us" if c.endswith("_us") else "ms"
            for q, nm in ((0.5, "median"), (0.95, "p95"), (1.0, "max")):
                s.hw(f"hw.H5.{c}.{nm}", float(x.quantile(q)), u, "data/hardware/hw_events.csv", f"{len(x)} events")
    if mem is None:
        s.not_run("hw.H5.memory", "hw_memory.csv missing")
    else:
        for r in mem.to_dict("records"):
            s.hw(f"hw.H5.memory.{r['item']}", r["bytes"], "bytes", "data/hardware/hw_memory.csv")
    import matplotlib.pyplot as plt

    med = {c: float(ev[c].median()) for c in ("classify_us", "ml_us", "verify_us") if ev[c].notna().any()}
    med_ms = {"classify": med.get("classify_us", 0) / 1000, "ml": med.get("ml_us", 0) / 1000, "verify": med.get("verify_us", 0) / 1000,
              "airtime": float(ev.airtime_ms.median()), "ACK round trip": float(ev.ack_rtt_ms.median())}
    fig, ax = plt.subplots(figsize=(5.5, 3.6))
    left = 0.0
    for i, (k, v) in enumerate(med_ms.items()):
        if np.isfinite(v):
            ax.barh([0], [v], left=left, label=k, color=f"C{i}")
            left += v
    ax.set_yticks([])
    ax.set_xlabel("Median time per stage (ms), stacked")
    ax.legend(fontsize=7, ncol=2)
    _wm(fig, dummy, "h5_latency_breakdown", out)


def h2_transfer(ev, win, s, out, dummy):
    if win is None:
        return s.not_run("hw.H2.transfer", "hw_windows.csv missing")
    from sklearn.metrics import average_precision_score

    from crashguard.features import compute_features
    from crashguard.models import PRIMARY, fit_scorer, frames, op_thresholds

    lab = ev[ev.experiment.isin(["H1", "H2"])].drop_duplicates("event_id").set_index("event_id").true_label
    xs, ys = [], []
    for eid, g in win.sort_values("t_ms").groupby("event_id"):
        if eid not in lab.index:
            continue
        a, w = g[["ax", "ay", "az"]].to_numpy(np.float32), g[["gx", "gy", "gz"]].to_numpy(np.float32) / C.DEG2RAD  # hw gyro is rad/s
        ip = int(np.linalg.norm(a, axis=1).argmax())
        idx = np.clip(np.arange(ip - C.WIN_N // 2, ip + C.WIN_N // 2), 0, len(a) - 1)
        xs.append(compute_features(a[idx][None], w[idx][None])[0])
        ys.append(lab[eid] == "crash")
    if len(xs) < 10 or len(set(ys)) < 2:
        return s.not_run("hw.H2.transfer", "fewer than 10 labelled windows or only one class")
    X, y = pd.DataFrame(np.array(xs), columns=list(C.FEATURES)), np.array(ys)
    tr, va, _ = frames(PRIMARY)
    for fs in ("all", "scale_free"):
        cols = list(C.FEATURE_SETS[fs])
        scorer, _m = fit_scorer("rf15", C.SEED, cols, tr, va)
        thr, _ = op_thresholds(va.y.to_numpy(), scorer(va))
        sc = scorer(X)
        m = prf(y, sc >= thr)
        s.hw(f"hw.H2.transfer.{fs}.ap", float(average_precision_score(y, sc)), "fraction", "data/hardware/hw_windows.csv", f"RF15 trained on VZCrash only, {len(y)} windows")
        s.hw(f"hw.H2.transfer.{fs}.f1", m["f1"], "fraction", "data/hardware/hw_windows.csv", "VZCrash validation threshold")


def h6(ev, s, out, dummy, thr):
    d = ev[ev.experiment.isin(["H1", "H2"])]
    if d.empty:
        return s.not_run("hw.H6", "no H1 or H2 rows in hw_events.csv")
    sw = d[[f"sw_{k}" for k in SW_ORDER]].fillna(0).to_numpy().astype(int)
    any_sw = sw.sum(axis=1) > 0
    c = d  # H1 hits are the crashes, H2 holds the non-crashes
    if len(c) and thr is not None:
        y = (c.true_label == "crash").to_numpy()
        base = (c.ml_prob >= thr).to_numpy()
        conf = base & (sw.sum(axis=1) > 0)
        for nm, pred in (("without_sw420", base), ("with_sw420_confirmation", conf)):
            for k, v in prf(y, pred).items():
                if k in ("recall", "fpr"):
                    s.hw(f"hw.H6.{nm}.{k}", v, "fraction", "data/hardware/hw_events.csv", "SW-420 confirmation = at least one sensor fired")
    else:
        s.not_run("hw.H6.confirmation", "no H1/H2 rows or no model threshold")
    first = d[d.true_side.isin(SW_SIDE.values()) & d.sw_first.notna()]
    if len(first):
        f = first.sw_first.map(lambda v: SW_ORDER[int(v)] if str(v).lstrip("-").isdigit() and 0 <= int(v) < 5 else str(v))
        s.hw("hw.H6.sw_first_accuracy", float((f.map(SW_SIDE) == first.true_side).mean()), "fraction", "data/hardware/hw_events.csv",
             "sw_first mapped to a side with an assumed sensor layout; the sensors confirm an impact, they do not locate it")
    s.hw("hw.H6.events_with_any_sw_fired", float(any_sw.mean()), "fraction", "data/hardware/hw_events.csv")


def analyse(hw: Path, out: Path, dummy: bool) -> Sink:
    s = Sink(dummy, out)
    out.mkdir(parents=True, exist_ok=True)
    ingest_existing(hw, s)
    ev, why = load(hw, "hw_events.csv")
    win, _ = load(hw, "hw_windows.csv")
    att, _ = load(hw, "hw_attacks.csv")
    mem, _ = load(hw, "hw_memory.csv")
    if ev is not None:
        ev = ev.assign(experiment=ev.experiment.replace(ALIAS))
    if ev is None:
        for k, v in EXPERIMENTS.items():
            if k == "H4" and att is not None:
                h4(att, s, out, dummy)
            elif k == "H5" and mem is not None:
                s.not_run("hw.H5.timings", f"timings need hw_events.csv: {why}")
                for r in mem.to_dict("records"):
                    s.hw(f"hw.H5.memory.{r['item']}", r["bytes"], "bytes", "data/hardware/hw_memory.csv")
            else:
                s.not_run(f"hw.{k}", f"{v}: {why}")
        s.not_run("hw.H2.transfer", f"transfer from VZCrash needs hw_events.csv and hw_windows.csv: {why}")
        s.flush()
        return s
    thr = None
    bundle = C.PROCESSED / "rf15_seed42.joblib"
    if bundle.exists():
        import joblib

        thr = float(joblib.load(bundle)["thr_f1"])
    for fn, args in ((h1, ()), (h2, (thr,)), (h3, ())):
        fn(ev, s, out, dummy, *args)
    h4(att, s, out, dummy)
    h5(ev, mem, s, out, dummy)
    h2_transfer(ev, win, s, out, dummy)
    h6(ev, s, out, dummy, thr)
    s.flush()
    return s


def protocol_figure(out: Path = C.FIGURES) -> None:
    """Hardware protocol comparison next to the analytical LoRa airtime (EXPERIMENTS.md, figure 1)."""
    import matplotlib.pyplot as plt

    from crashguard.lora import airtime_ms
    from crashguard.packet import ALERT_LEN
    from crashguard.plots import COLORS, save, style

    p = HW / "protocols.csv"
    if not p.exists():
        return
    d = pd.read_csv(p)
    style()
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.8))
    ax = axes[0]
    ax.bar(d.protocol, d.latency_ms_max, color=COLORS[0], label="HARDWARE, upper end of logged range")
    ax.bar(d.protocol, d.latency_ms_min, color=COLORS[5], label="HARDWARE, lower end")
    ax.set_xlabel("Wi-Fi protocol (measured on the ESP32)")
    ax.set_ylabel("Latency (ms)")
    ax.legend(fontsize=7)
    ax = axes[1]
    sfs = list(range(7, 13))
    ax.bar([f"SF{x}" for x in sfs], [airtime_ms(ALERT_LEN, x) for x in sfs], color=COLORS[1], hatch="//", label="ANALYTICAL")
    ax.set_yscale("log")
    ax.set_xlabel("LoRa spreading factor (97 B alert)")
    ax.set_ylabel("Time on air (ms)")
    ax.legend(fontsize=7)
    save(fig, "fig1_protocols_vs_lora", out_dir=out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dummy", action="store_true", help="use tests/dummy/ and write only to tests/dummy/out/")
    ap.add_argument("--hw-dir", default=None)
    a = ap.parse_args()
    if a.dummy:
        hw, out = Path("tests/dummy"), Path("tests/dummy/out")
    else:
        hw, out = Path(a.hw_dir or HW), C.TABLES / "hardware"
    s = analyse(hw, out, a.dummy)
    if not a.dummy:
        protocol_figure()
    nr = sum(1 for i in s.items if i["origin"] == "NOT_RUN")
    print(f"{len(s.items)} entries, {nr} NOT_RUN ({'dummy' if a.dummy else 'real'} data)")


if __name__ == "__main__":
    main()
