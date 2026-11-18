"""Phase 2 severity hardening on NHTSA crash tests (MEASURED_SOFTWARE, with datasheet values ANALYTICAL).

1. Range and sample-rate study: accelerometer range {16, 32, 64, 100, 200} g x sample rate {100, 200, 400, 800, 1600} Hz, plus a front-end
   bandwidth sweep. Filter model (ours, generic, not a specific part): front end = 4th-order Butterworth low-pass run forward and backward
   (zero phase) at the front-end bandwidth (260 Hz unless stated), saturation at the range, a digital low-pass of the same kind at
   min(0.4 x sample rate, front-end bandwidth), then linear interpolation onto the sample grid. Error = estimate against the reference delta-V.
2. Named parts: range, rate and resolution of parts whose datasheets were opened (MPU-6050, ADXL345, ADXL375, H3LIS331DL) run through the same model.
3. Release rule: the pulse ends when horizontal |a| stays below max(0.5 g, fraction x peak) for 50 ms. The fraction is chosen on the NHTSA TUNING
   split only (objective fixed before the run: median absolute delta-V error at 100 Hz, no clipping, 260 Hz front end) and scored once on HELD-OUT tests.
4. Threshold sensitivity: each class limit moved by plus and minus 20%.

Reference delta-V: maximum over the first 300 ms after the trigger of the resultant of the running integral of the original-rate, unclipped,
baseline-removed longitudinal and lateral acceleration. Split by test number: within each kind, sorted test numbers, ranks 3, 6, 9, ... are
held out (docs/07_log/DECISIONS.md, written before any result was seen).
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd

from crashguard import boot as B
from crashguard import config as C
from crashguard import nhtsa as N
from crashguard import severity as S

RANGES_G = (16.0, 32.0, 64.0, 100.0, 200.0)
RATES_HZ = (100, 200, 400, 800, 1600)
FE_HZ = 260.0
BW_SWEEP_HZ = (50, 100, 260, 500, 1000)
BW_RANGES_G = (16.0, 32.0, 64.0, 200.0)
BW_RATE_HZ = 1600
REF_S = 0.3
REL_FRACS = (0.02, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4)
THR_SCALES = (0.8, 1.2)
TOL10, TOL20 = 10.0, 20.0
TARGET_SHARE = 0.80

# name -> (range g, sample rate Hz, resolution g per count, datasheet note). Values read in the datasheets opened on 2026-11-11 (docs/05_data_code/SEVERITY.md)
PARTS = {
    "MPU-6050 +-16 g, 100 Hz (current setting)": (16.0, 100, 1 / 2048, "MPU-6000/6050 Rev 3.4: +-16 g, 2048 LSB/g"),
    "MPU-6050 +-16 g, 1000 Hz": (16.0, 1000, 1 / 2048, "accelerometer sample rate 1 kHz, DLPF up to 260 Hz"),
    "ADXL345 +-16 g, 100 Hz": (16.0, 100, 0.0039, "3.9 mg/LSB, full resolution"),
    "ADXL345 +-16 g, 3200 Hz": (16.0, 3200, 0.0039, "output data rate up to 3200 Hz"),
    "H3LIS331DL +-100 g, 1000 Hz": (100.0, 1000, 0.049, "49 mg/digit at +-100 g, ODR 1000 Hz"),
    "H3LIS331DL +-200 g, 1000 Hz": (200.0, 1000, 0.098, "98 mg/digit at +-200 g"),
    "ADXL375 +-200 g, 800 Hz": (200.0, 800, 0.049, "49 mg/LSB"),
    "ADXL375 +-200 g, 3200 Hz": (200.0, 3200, 0.049, "output data rate up to 3200 Hz"),
}


# Datasheet values (ANALYTICAL), read in PDFs opened on 2026-11-11 (copies in data/raw/refs/, git-ignored). part -> (max range g, resolution mg per count at the maximum range,
# maximum output data rate Hz, bandwidth rule, noise as stated, document)
DATASHEETS = {
    "MPU-6050": (16.0, 0.488, 1000, "accelerometer low-pass programmable 5 to 260 Hz", "400 ug/sqrt(Hz) (power spectral density)", "InvenSense MPU-6000/MPU-6050 Product Specification, Rev 3.4, 2013-08-19"),
    "ADXL345": (16.0, 3.9, 3200, "bandwidth = ODR / 2", "0.75 LSB rms (x, y) and 1.1 LSB rms (z) at ODR 100 Hz", "Analog Devices ADXL345 data sheet (copy hosted by UBC ECE, opened)"),
    "ADXL375": (200.0, 49.0, 3200, "bandwidth = ODR / 2", "not read", "Analog Devices ADXL375 data sheet (distributor copy, opened)"),
    "H3LIS331DL": (400.0, 195.0, 1000, "bandwidth = ODR / 2 (ODR 50, 100, 400, 1000 Hz)", "not read", "STMicroelectronics H3LIS331DL data sheet (opened; ranges 100, 200, 400 g; 49, 98, 195 mg/digit)"),
}


def role_of(rank: int) -> str:
    """Rank counts from 1 among vehicle groups; every third group is held out."""
    return "heldout" if rank % 3 == 0 else "tuning"


def vehicle_group(t: dict) -> str:
    """Vehicle key from the NHTSA metadata: make, model and model year. All tests of one key go to the same side of the split."""
    return f"{t.get('vehicleMake')}|{t.get('vehicleModel')}|{t.get('modelYear')}"


def load_tests() -> list[dict]:
    raw = []
    for side in (False, True):
        kind = "side" if side else "frontal"
        for t, sig in N.select(side):
            raw.append((kind, t, sig))
    first = {}
    for kind, t, _sig in raw:
        g = vehicle_group(t)
        first[g] = min(first.get(g, 10**9), int(t["testNo"]))
    order = {g: i for i, g in enumerate(sorted(first, key=lambda g: (first[g], g)), 1)}
    out: list[dict] = []
    for kind, t, sig in sorted(raw, key=lambda x: (x[1]["testNo"], x[0])):
        ref, _i0 = reference_dv(sig)
        w, trig = _window(np.asarray(sig["acc"]) + np.array([0, 0, 1.0]), sig["fs0"])
        r0 = S.severity(w, sig["fs0"], trig)
        g = vehicle_group(t)
        out.append(dict(test_no=int(t["testNo"]), kind=kind, v=float(t["closingSpeed"]), sig=sig, role=role_of(order[g]), group=g, ref_dv=ref, ref_asi=r0["asi"]))
    return out


def reference_dv(sig: dict) -> tuple[float, int]:
    acc, fs0 = np.asarray(sig["acc"]), float(sig["fs0"])
    i0 = N.trigger_index(acc + np.array([0, 0, 1.0]), fs0)
    i0 = 0 if i0 is None else i0
    base = acc[: max(i0, 1)].mean(axis=0)
    seg = (acc[i0 : i0 + int(REF_S * fs0), :2] - base[:2]) * C.G0
    v = S.trapz_cumulative(seg, 1.0 / fs0)
    return float(np.hypot(v[:, 0], v[:, 1]).max() * 3.6), i0


def _window(yg: np.ndarray, fs: float) -> tuple[np.ndarray, int]:
    i0 = N.trigger_index(yg, fs)
    i0 = 0 if i0 is None else i0
    pre, post = int(round(C.PRE_S * fs)), int(round(C.POST_S * fs))
    idx = np.clip(np.arange(i0 - pre, i0 + post), 0, len(yg) - 1)
    return yg[idx], pre


def sensor_signal(sig: dict, range_g: float | None, fs: float, fe_hz: float = FE_HZ, lsb_g: float = 0.0) -> np.ndarray:
    """Acceleration (g, gravity added) as our generic sensor model would report it at ``fs`` Hz."""
    t, acc, fs0 = np.asarray(sig["t"]), np.asarray(sig["acc"]), float(sig["fs0"])
    x = N._lowpass(acc, fs0, fe_hz) if fe_hz < 0.45 * fs0 else acc
    if range_g:
        x = np.clip(x, -range_g, range_g)
    dig = min(0.4 * fs, fe_hz)
    if dig < 0.45 * fs0:
        x = N._lowpass(x, fs0, dig)
    tt = np.arange(t[0], t[-1], 1.0 / fs)
    y = np.stack([np.interp(tt, t, x[:, k]) for k in range(3)], axis=1) + np.array([0, 0, N.GRAVITY_Z_G])
    if lsb_g > 0:
        y = np.round(y / lsb_g) * lsb_g
    return y


def estimate(sig: dict, range_g: float | None, fs: float, fe_hz: float = FE_HZ, lsb_g: float = 0.0, p: S.SeverityParams = S.DEFAULT) -> dict:
    y = sensor_signal(sig, range_g, fs, fe_hz, lsb_g)
    w, trig = _window(y, fs)
    return S.severity(w, fs, trig, None, p)


def _rows(tests: list[dict], **kw) -> pd.DataFrame:
    rows = []
    for t in tests:
        r = estimate(t["sig"], **kw)
        rows.append(dict(test_no=t["test_no"], kind=t["kind"], role=t["role"], v=t["v"], ref_dv=t["ref_dv"], ref_asi=t["ref_asi"], dv=r["dv_res_kmh"], asi=r["asi"],
                         pulse_ms=r["pulse_ms"], cls=r["severity_class"]))
    d = pd.DataFrame(rows)
    d["err_pct"] = 100 * (d.dv - d.ref_dv) / d.ref_dv
    d["asi_err_pct"] = 100 * (d.asi - d.ref_asi) / d.ref_asi
    d["in_band"] = (d.dv >= d.v) & (d.dv <= 2 * d.v)
    return d


def metrics(d: pd.DataFrame, with_ci: bool = False) -> dict:
    """Median and 90th-percentile absolute delta-V error, shares within 10% and 20%, share in v <= dv <= 2v (frontal only), median ASI error."""
    e, a = d.err_pct.abs().to_numpy(), d.asi_err_pct.abs().to_numpy()
    fr = d[d.kind == "frontal"].in_band.to_numpy()
    out = dict(n=len(d), dv_abs_err_median_pct=float(np.median(e)), dv_abs_err_p90_pct=B.p90(e), dv_within10=float(np.mean(e <= TOL10)), dv_within20=float(np.mean(e <= TOL20)),
               dv_signed_err_median_pct=float(d.err_pct.median()), band_share=float(fr.mean()) if len(fr) else float("nan"), asi_abs_err_median_pct=float(np.median(a)))
    if with_ci:
        for k, x, f in (("dv_abs_err_median_pct", e, np.median), ("dv_abs_err_p90_pct", e, B.p90), ("dv_within10", e <= TOL10, np.mean), ("dv_within20", e <= TOL20, np.mean),
                        ("asi_abs_err_median_pct", a, np.median)):
            _p, lo, hi = B.ci(x, f)
            out[f"{k}_lo"], out[f"{k}_hi"] = lo, hi
        if len(fr):
            _p, lo, hi = B.ci(fr, np.mean)
            out["band_share_lo"], out["band_share_hi"] = lo, hi
    return out


def grid(tests: list[dict]) -> pd.DataFrame:
    rows = []
    for rg in RANGES_G:
        for fs in RATES_HZ:
            d = _rows(tests, range_g=rg, fs=float(fs))
            d["range_g"], d["rate_hz"] = rg, fs
            rows.append(d)
    return pd.concat(rows, ignore_index=True)


def bandwidth_sweep(tests: list[dict]) -> pd.DataFrame:
    rows = []
    for fe in BW_SWEEP_HZ:
        for rg in BW_RANGES_G:
            d = _rows(tests, range_g=rg, fs=float(BW_RATE_HZ), fe_hz=float(fe))
            d["range_g"], d["fe_hz"] = rg, fe
            rows.append(d)
    return pd.concat(rows, ignore_index=True)


def parts_table(tests: list[dict]) -> pd.DataFrame:
    rows = []
    for name, (rg, fs, lsb, note) in PARTS.items():
        d = _rows(tests, range_g=rg, fs=float(fs), lsb_g=lsb)
        m = metrics(d, with_ci=True)
        rows.append(dict(part=name, range_g=rg, rate_hz=fs, lsb_g=lsb, note=note, **m))
    return pd.DataFrame(rows)


def cells(g: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (rg, fs), d in g.groupby(["range_g", "rate_hz"]):
        rows.append(dict(range_g=rg, rate_hz=fs, **metrics(d, with_ci=True)))
    return pd.DataFrame(rows)


def needed(c: pd.DataFrame) -> dict:
    """Which (range, rate) cells reach TARGET_SHARE within 10% (point estimate and lower interval bound), and the smallest of each (lowest range, then rate)."""
    out: dict = {}
    for key, col in (("point", "dv_within10"), ("ci_lower", "dv_within10_lo")):
        ok = c[c[col] >= TARGET_SHARE].sort_values(["range_g", "rate_hz"])
        out[key] = [(float(r.range_g), int(r.rate_hz)) for r in ok.itertuples()]
    return out


# ---------------------------------------------------------------- release rule
def tune_release(tests: list[dict]) -> dict:
    """Choose the release fraction on TUNING tests (median absolute delta-V error at 100 Hz, no clipping), then score it once on HELD-OUT tests."""
    tune = [t for t in tests if t["role"] == "tuning"]
    held = [t for t in tests if t["role"] == "heldout"]
    cands = {"abs0.5": replace(S.DEFAULT, release_frac=0.0, release_g=0.5), "abs1.0": replace(S.DEFAULT, release_frac=0.0, release_g=1.0),
             "abs1.5": replace(S.DEFAULT, release_frac=0.0, release_g=1.5)}
    for f in REL_FRACS:
        cands[f"frac{f:g}"] = replace(S.DEFAULT, release_frac=f, release_g=0.5)
    tune_scores = {k: float(_rows(tune, range_g=None, fs=100.0, p=p).err_pct.abs().median()) for k, p in cands.items()}
    best_frac = min((k for k in cands if k.startswith("frac")), key=lambda k: tune_scores[k])
    chosen = best_frac if tune_scores[best_frac] < tune_scores["abs0.5"] else "abs0.5"
    base_h = _rows(held, range_g=None, fs=100.0, p=cands["abs0.5"])
    new_h = _rows(held, range_g=None, fs=100.0, p=cands[chosen])
    diff = B.paired_diff(base_h.err_pct.abs().to_numpy(), new_h.err_pct.abs().to_numpy(), np.median)
    base_16 = _rows(held, range_g=C.MPU_RANGE_G, fs=100.0, p=cands["abs0.5"])
    new_16 = _rows(held, range_g=C.MPU_RANGE_G, fs=100.0, p=cands[chosen])
    return dict(tune_scores=tune_scores, chosen=chosen, chosen_frac=cands[chosen].release_frac, base_heldout=metrics(base_h, True), new_heldout=metrics(new_h, True),
                diff_median_abs_err=diff, base_heldout_16g=metrics(base_16, True), new_heldout_16g=metrics(new_16, True),
                n_tuning=len(tune), n_heldout=len(held))


# ---------------------------------------------------------------- class threshold sensitivity
def class_shares(dv: np.ndarray, asi: np.ndarray, rollover: np.ndarray | None = None, dv_lim=C.SEV_DV_KMH, asi_lim=C.ASI_CLASS_LIMITS) -> np.ndarray:
    p = replace(S.DEFAULT, dv_limits_kmh=tuple(dv_lim), asi_limits=tuple(asi_lim))
    ro = np.zeros(len(dv), bool) if rollover is None else rollover
    cls = np.array([S.classify(float(d), float(a), bool(r), p) for d, a, r in zip(dv, asi, ro)])
    return np.array([(cls == k).mean() for k in range(4)])


def threshold_variants() -> dict[str, tuple[tuple, tuple]]:
    """name -> (dv limits, asi limits): the base case and each of the six limits moved by -20% and +20%."""
    out = {"base": (C.SEV_DV_KMH, C.ASI_CLASS_LIMITS)}
    for i, n in enumerate(("dv_low_moderate", "dv_moderate_severe", "dv_severe_critical")):
        for s in THR_SCALES:
            lim = list(C.SEV_DV_KMH)
            lim[i] *= s
            out[f"{n}.x{s:g}"] = (tuple(lim), C.ASI_CLASS_LIMITS)
    for i, n in enumerate(("asi_A_B", "asi_B_C", "asi_C_over")):
        for s in THR_SCALES:
            lim = list(C.ASI_CLASS_LIMITS)
            lim[i] *= s
            out[f"{n}.x{s:g}"] = (C.SEV_DV_KMH, tuple(lim))
    for s in THR_SCALES:
        out[f"all_dv.x{s:g}"] = (tuple(x * s for x in C.SEV_DV_KMH), C.ASI_CLASS_LIMITS)
        out[f"all_asi.x{s:g}"] = (C.SEV_DV_KMH, tuple(x * s for x in C.ASI_CLASS_LIMITS))
    return out


def threshold_table(dv: np.ndarray, asi: np.ndarray, rollover: np.ndarray | None, label: str) -> list[dict]:
    rows = []
    for name, (dvl, asl) in threshold_variants().items():
        sh = class_shares(dv, asi, rollover, dvl, asl)
        rows.append(dict(dataset=label, variant=name, **{f"share_{C.SEV_NAMES[k]}": float(sh[k]) for k in range(4)}))
    return rows


# ---------------------------------------------------------------- figures, results
def figure(c: pd.DataFrame, bw: pd.DataFrame) -> None:
    import matplotlib.pyplot as plt

    from crashguard.plots import save, style

    style()
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.2))
    for ax, col, ttl, fmt, cm in ((axes[0], "dv_abs_err_median_pct", "Median |delta-V error| (%)", "{:.1f}", "viridis_r"),
                                  (axes[1], "dv_within10", "Share of tests within +-10% of the reference", "{:.2f}", "viridis"),
                                  (axes[2], "band_share", "Share of frontal tests with v <= delta-V <= 2 v", "{:.2f}", "viridis")):
        m = c.pivot(index="range_g", columns="rate_hz", values=col).sort_index(ascending=False)
        im = ax.imshow(m.to_numpy(), cmap=cm, aspect="auto")
        ax.set_xticks(range(len(m.columns)), [f"{int(x)}" for x in m.columns])
        ax.set_yticks(range(len(m.index)), [f"{x:g}" for x in m.index])
        ax.grid(False)
        for i in range(m.shape[0]):
            for j in range(m.shape[1]):
                ax.text(j, i, fmt.format(m.iat[i, j]), ha="center", va="center", fontsize=8, color="white")
        ax.set_xlabel("Sample rate (Hz)")
        ax.set_ylabel("Accelerometer range (+-g)")
        ax.set_title(ttl, fontsize=9)
        fig.colorbar(im, ax=ax, fraction=0.046)
    fig.suptitle("NHTSA crash tests: range and sample-rate study, 260 Hz front end (MEASURED_SOFTWARE)", fontsize=9)
    save(fig, "sevstudy_range_rate_heatmap")
    fig, ax = plt.subplots(figsize=(5.5, 3.8))
    for i, rg in enumerate(BW_RANGES_G):
        s = bw[bw.range_g == rg].groupby("fe_hz").err_pct.apply(lambda x: float(np.median(np.abs(x))))
        ax.plot(s.index, s.values, "o-", label=f"+-{rg:g} g")
    ax.set_xscale("log")
    ax.set_xlabel("Front-end bandwidth (Hz)")
    ax.set_ylabel("Median |delta-V error| (%)")
    ax.legend(fontsize=7)
    ax.set_title(f"Bandwidth sweep at {BW_RATE_HZ} Hz sampling", fontsize=9)
    save(fig, "sevstudy_bandwidth")


def main() -> None:
    from crashguard.results import record_many

    C.TABLES.mkdir(parents=True, exist_ok=True)
    tests = load_tests()
    if not tests:
        record_many([dict(name="sevstudy.run", value="NOT_RUN", unit="", origin="NOT_RUN", source_file="results/tables/sevstudy_cells.csv", notes="no NHTSA tests available")])
        return
    src = "results/tables/sevstudy_cells.csv"
    ent: list[dict] = []

    def add(name, value, unit, origin="MEASURED_SOFTWARE", notes=""):
        ent.append(dict(name=f"sevstudy.{name}", value=value, unit=unit, origin=origin, source_file=src, notes=notes))

    add("n_tests", len(tests), "tests")
    add("n_frontal", sum(t["kind"] == "frontal" for t in tests), "tests")
    add("n_side", sum(t["kind"] == "side" for t in tests), "tests")
    add("n_tuning", sum(t["role"] == "tuning" for t in tests), "tests", notes="split by vehicle group (make, model, year): every third group, by smallest test number, is held out")
    add("n_heldout", sum(t["role"] == "heldout" for t in tests), "tests")
    add("n_groups", len({t["group"] for t in tests}), "vehicle groups", notes="make, model and model year")
    add("n_groups_heldout", len({t["group"] for t in tests if t["role"] == "heldout"}), "vehicle groups")
    add("n_groups_tuning", len({t["group"] for t in tests if t["role"] == "tuning"}), "vehicle groups")
    pd.DataFrame([{k: v for k, v in t.items() if k != "sig"} for t in tests]).to_csv(C.TABLES / "sevstudy_tests.csv", index=False)

    g = grid(tests)
    g.to_csv(C.TABLES / "sevstudy_grid_tests.csv", index=False)
    c = cells(g)
    c.to_csv(C.TABLES / "sevstudy_cells.csv", index=False)
    for r in c.itertuples():
        for k, v in r._asdict().items():
            if k in ("Index", "range_g", "rate_hz"):
                continue
            unit = "tests" if k == "n" else "fraction" if ("within" in k or "band" in k) else "percent"
            add(f"grid.r{r.range_g:g}.f{r.rate_hz}.{k}", round(float(v), 4) if k != "n" else int(v), unit, notes="260 Hz front end, our generic sensor model; error against the reference delta-V")
    nd = needed(c)
    add("needed.point.count", len(nd["point"]), "configurations", notes=f"configurations with at least {TARGET_SHARE:.0%} of tests within 10%")
    add("needed.ci_lower.count", len(nd["ci_lower"]), "configurations", notes="same, but the lower 95% bound must also reach the target")
    for key in ("point", "ci_lower"):
        if nd[key]:
            r0, f0 = nd[key][0]
            add(f"needed.{key}.min_range_g", r0, "g", "ANALYTICAL" if False else "MEASURED_SOFTWARE", "lowest range in the grid that reaches the target (with the lowest rate that works at that range)")
            add(f"needed.{key}.min_rate_hz", f0, "Hz")
        else:
            add(f"needed.{key}.min_range_g", "NOT_RUN", "g", "NOT_RUN", "no configuration in the grid reaches the target")
    for kind in ("frontal", "side"):
        ck = cells(g[g.kind == kind])
        ck.to_csv(C.TABLES / f"sevstudy_cells_{kind}.csv", index=False)
        for r in ck.itertuples():
            add(f"grid_{kind}.r{r.range_g:g}.f{r.rate_hz}.dv_within10", round(float(r.dv_within10), 4), "fraction")
            add(f"grid_{kind}.r{r.range_g:g}.f{r.rate_hz}.dv_abs_err_median_pct", round(float(r.dv_abs_err_median_pct), 4), "percent")

    bw = bandwidth_sweep(tests)
    bw.to_csv(C.TABLES / "sevstudy_bandwidth_tests.csv", index=False)
    for (fe, rg), d in bw.groupby(["fe_hz", "range_g"]):
        m = metrics(d)
        add(f"bw.fe{fe}.r{rg:g}.dv_abs_err_median_pct", round(m["dv_abs_err_median_pct"], 4), "percent", notes=f"{BW_RATE_HZ} Hz sampling")
        add(f"bw.fe{fe}.r{rg:g}.dv_within10", round(m["dv_within10"], 4), "fraction")

    pt = parts_table(tests)
    pt.to_csv(C.TABLES / "sevstudy_parts.csv", index=False)
    for i, r in enumerate(pt.itertuples()):
        for k in ("dv_abs_err_median_pct", "dv_abs_err_median_pct_lo", "dv_abs_err_median_pct_hi", "dv_within10", "dv_within10_lo", "dv_within10_hi", "dv_within20", "band_share"):
            add(f"part{i}.{k}", round(float(getattr(r, k)), 4), "fraction" if ("within" in k or "band" in k) else "percent")

    sheet = pd.DataFrame([dict(part=k, max_range_g=v[0], resolution_mg_per_count=v[1], max_odr_hz=v[2], bandwidth=v[3], noise=v[4], document=v[5]) for k, v in DATASHEETS.items()])
    sheet.to_csv(C.TABLES / "sevstudy_datasheets.csv", index=False)
    for k, v in DATASHEETS.items():
        for lab, val, unit in (("max_range_g", v[0], "g"), ("resolution_mg_per_count", v[1], "mg"), ("max_odr_hz", v[2], "Hz")):
            add(f"sheet.{k}.{lab}", val, unit, "ANALYTICAL", f"datasheet value ({v[5]}); not a measurement", )

    tr = tune_release(tests)
    pd.DataFrame([dict(rule=k, tuning_median_abs_err_pct=v) for k, v in tr["tune_scores"].items()]).to_csv(C.TABLES / "sevstudy_release_tuning.csv", index=False)
    for k, v in tr["tune_scores"].items():
        add(f"release.tuning.{k}.median_abs_err_pct", round(v, 4), "percent", notes="TUNING tests only; 100 Hz, no clipping, 260 Hz front end")
    add("release.chosen_frac", float(tr["chosen_frac"]), "fraction of the pulse peak", notes=f"chosen rule: {tr['chosen']} (0 = keep the absolute 0.5 g rule)")
    for lab, key in (("abs", "base_heldout"), ("new", "new_heldout"), ("abs16", "base_heldout_16g"), ("new16", "new_heldout_16g")):
        for k, v in tr[key].items():
            if k != "n":
                add(f"release.heldout.{lab}.{k}", round(float(v), 4), "fraction" if ("within" in k or "band" in k) else "percent", notes="HELD-OUT tests, scored once")
    d0, lo, hi = tr["diff_median_abs_err"]
    add("release.heldout.diff_median_abs_err_pct", round(d0, 4), "percent", notes="new rule minus 0.5 g rule, median |error| on the same held-out tests (paired bootstrap)")
    add("release.heldout.diff_lo", round(lo, 4), "percent")
    add("release.heldout.diff_hi", round(hi, 4), "percent")
    add("release.config_matches_tuning", int(abs(tr["chosen_frac"] - C.SEV_RELEASE_FRAC) < 1e-12), "flag",
        notes="1 = config.SEV_RELEASE_FRAC equals the fraction chosen on the tuning split in this run; 0 means config.py must be updated and the pipeline re-run")
    add("release.n_tuning", tr["n_tuning"], "tests")
    add("release.n_heldout", tr["n_heldout"], "tests")

    # NHTSA class-mix sensitivity (orig = reference signal at the original rate; sensor = 16 g, 100 Hz model)
    r16 = _rows(tests, range_g=C.MPU_RANGE_G, fs=100.0)
    rows = threshold_table(np.array([t["ref_dv"] for t in tests]), np.array([t["ref_asi"] for t in tests]), None, "nhtsa_reference") + \
        threshold_table(r16.dv.to_numpy(), r16.asi.to_numpy(), None, "nhtsa_16g_100hz")
    pd.DataFrame(rows).to_csv(C.TABLES / "sevstudy_threshold_nhtsa.csv", index=False)
    for r in rows:
        for k in range(4):
            add(f"thr.{r['dataset']}.{r['variant']}.share_{C.SEV_NAMES[k]}", round(r[f'share_{C.SEV_NAMES[k]}'], 4), "fraction")

    record_many(ent, purge_prefixes=("sevstudy.",))
    figure(c, bw)
    print(c[["range_g", "rate_hz", "dv_abs_err_median_pct", "dv_within10", "band_share"]].round(3).to_string())
    print("needed:", nd)
    print("release:", tr["chosen"], tr["tune_scores"])


if __name__ == "__main__":
    main()
