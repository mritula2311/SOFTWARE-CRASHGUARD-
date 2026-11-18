"""Block 2: sensor-selection result, a buyer's guide (ANALYTICAL part table S1; MEASURED_SOFTWARE study S2; decision rule S3 written in docs/07_log/DECISIONS.md before this ran).

Every configuration (part, full-scale range, output data rate) is run through the same software sensor model as N13 (``severity_study.sensor_signal``): 4th-order zero-phase low-pass at the
datasheet bandwidth, saturation at the range, resampling at the output data rate, white noise at the datasheet density (seed 42, where a density was read), quantisation at the least
significant bit. The reference delta-V is the N13 reference. Primary set: the 176 NHTSA tests (intervals resample make-and-model groups). Confirmation set: the held-out records of T13a.
Fill + ridge (N14, fit on the 176 with the generic chain, applied unchanged) is added where N14 applies: ranges +-16, +-32, +-64 g at 100 Hz.
"""
from __future__ import annotations

import pickle

import numpy as np
import pandas as pd

from crashguard import boot as B
from crashguard import config as C
from crashguard import saturation as SAT
from crashguard import saturation_splits as SPL
from crashguard import severity as S
from crashguard import severity_study as SS
from crashguard.jp_common import Entries
from crashguard.sel_parts import PARTS, Part

TARGET = 0.80
N14_RANGES = (16, 32, 64)
MAX_ODR_HZ = 8000  # the source records are sampled at 10 to 20 kHz; faster output rates would only interpolate
SRC = "results/tables/sel_configs.csv"
CAVEATS = "C1 C2 C3 C4"
CAVEAT_TEXT = ("C1: the output data rate is the datasheet rate, not a measured I2C or SPI read rate on an ESP32 (NOT_RUN, hardware); C2: NHTSA tests are mostly high-speed barrier crashes; "
               "C3: the sensor is a software model (bandwidth, range, rate, resolution); C4: noise is white at the datasheet density where one was read, none otherwise")


def cfg_name(p: Part, rg: float, odr: float) -> str:
    return f"{p.key}.r{rg:g}.f{int(odr)}"


def chain(sig: dict, p: Part, rg: float, odr: float, seed: int, noise: bool = True) -> np.ndarray:
    fe = p.bw_hz(odr)
    y = SS.sensor_signal(sig, float(rg), float(odr), fe_hz=fe, lsb_g=0.0)
    if noise and p.noise_ug_rthz:
        sigma = p.noise_ug_rthz * 1e-6 * np.sqrt(min(fe, 0.5 * odr))
        y = y + np.random.default_rng(seed).normal(0.0, sigma, y.shape)
        y = np.clip(y, -rg, rg)
    lsb = p.mg_per_lsb[rg] / 1000.0
    return np.round(y / lsb) * lsb


def part_dv(sig: dict, p: Part, rg: float, odr: float, seed: int, noise: bool = True) -> float:
    w, trig = SS._window(chain(sig, p, rg, odr, seed, noise), float(odr))
    return S.severity(w, float(odr), trig, None, SPL.sp_params(SPL.RF0))["dv_res_kmh"]


def part_features(sig: dict, p: Part, rg: float, odr: float, seed: int) -> tuple[float, float, float, float, bool]:
    """(plain delta-V, fill delta-V, saturated share, pulse width ms, fill applied) under the part chain."""
    w, trig = SS._window(chain(sig, p, rg, odr, seed), float(odr))
    pp = SPL.sp_params(SPL.RF0)
    r = S.severity(w, float(odr), trig, None, pp)
    rf, info = SAT.severity_filled(w, float(odr), trig, float(rg), SPL.FINAL_FAMILY, pp, SPL.FINAL_SAT)
    return r["dv_res_kmh"], rf["dv_res_kmh"], info.sat_share, r["pulse_ms"], bool(info.applied)


def ridge_models() -> dict:
    """Fill + ridge per range, fit on the 176 with the generic chain exactly as in ``saturation_splits.estimates`` (leave-one-make-model-out strength)."""
    old = SS.load_tests()
    meta = SPL.meta_of(old)
    cells = pickle.loads(SPL.CACHE.read_bytes())
    ref = meta.ref.to_numpy()
    tr = np.ones(len(old), bool)
    out = {}
    for rg in N14_RANGES:
        key = (float(rg),)
        m_all, ap, sh = cells[("m", float(rg), SPL.FINAL_FAMILY, SPL.FINAL_SAT, SPL.RF0)], cells[("ap", float(rg), SPL.FINAL_FAMILY, SPL.FINAL_SAT, SPL.RF0)], cells[("sh", float(rg), SPL.FINAL_FAMILY, SPL.FINAL_SAT, SPL.RF0)]
        b_all, pl = cells[("b", float(rg), SPL.RF0)], cells[("pl", float(rg), SPL.RF0)]
        X = np.stack([b_all, sh, pl], axis=1)
        y = np.log(ref / np.maximum(m_all, 1e-6))
        use = tr & ap
        alpha, corr = SPL._alpha_and_fit(X[use], y[use], meta.group_mm.to_numpy()[use], m_all[tr], ref[tr], ap[tr], "group")
        out[rg] = (alpha, corr)
        del key
    return out


def metrics_of(err_signed: np.ndarray, groups: np.ndarray) -> dict:
    return SPL.block(np.abs(err_signed), groups)


def run_set(tests: list[dict], groups: np.ndarray, frontal: np.ndarray | None, v: np.ndarray, ref: np.ndarray, rid: dict, label: str, noise: bool = True) -> list[dict]:
    rows = []
    for p in PARTS:
        for rg in p.study_ranges:
            for odr in p.odrs_hz:
                if odr > MAX_ODR_HZ:
                    continue
                dv = np.array([part_dv(t["sig"], p, rg, odr, 42 + i, noise) for i, t in enumerate(tests)])
                e = 100.0 * (dv - ref) / ref
                row = dict(part=p.key, range_g=rg, odr_hz=odr, set=label, noise=int(noise), **metrics_of(e, groups))
                if frontal is not None and frontal.any():
                    band = (dv >= v) & (dv <= 2 * v)
                    pb, lo, hi = B.ci_grouped(band[frontal], groups[frontal], np.mean)
                    row.update(band=pb, band_lo=lo, band_hi=hi, n_frontal=int(frontal.sum()))
                if odr == 100 and rg in N14_RANGES and noise:
                    alpha, corr = rid[rg]
                    feats = [part_features(t["sig"], p, rg, odr, 42 + i) for i, t in enumerate(tests)]
                    b_, m_, sh_, pl_, ap_ = (np.array(c) for c in zip(*feats))
                    f = np.ones(len(tests))
                    if ap_.any():
                        f[ap_.astype(bool)] = corr.factor(np.stack([b_, sh_, pl_], 1)[ap_.astype(bool)])
                    em = 100.0 * (m_ * f - ref) / ref
                    bm = SPL.block(np.abs(em), groups)
                    for k in ("median", "median_lo", "median_hi", "p90", "w10", "w10_lo", "w10_hi"):
                        row[f"mp_{k}"] = bm[k]
                    if frontal is not None and frontal.any():
                        bnd = (m_ * f >= v) & (m_ * f <= 2 * v)
                        pb, lo, hi = B.ci_grouped(bnd[frontal], groups[frontal], np.mean)
                        row.update(mp_band=pb, mp_band_lo=lo, mp_band_hi=hi)
                rows.append(row)
        print(label, p.key, "done", flush=True)
    return rows


def main() -> None:
    from crashguard.t13_heldout import build_set

    C.TABLES.mkdir(parents=True, exist_ok=True)
    old = SS.load_tests()
    meta = SPL.meta_of(old)
    rid = ridge_models()
    grp_old = meta.group_mm.to_numpy()
    fr_old = (meta.kind == "frontal").to_numpy()
    rows = run_set(old, grp_old, fr_old, meta.v.to_numpy(), meta.ref.to_numpy(), rid, "n13")
    rows += run_set(old, grp_old, fr_old, meta.v.to_numpy(), meta.ref.to_numpy(), rid, "n13_nonoise", noise=False)
    new, _cnt = build_set()
    mnew = SPL.meta_of(new)
    rows += run_set(new, mnew.group_mm.to_numpy(), None, mnew.v.to_numpy(), mnew.ref.to_numpy(), rid, "heldout")
    R = pd.DataFrame(rows)
    R.to_csv(C.TABLES / "sel_configs.csv", index=False)
    E = Entries("sel", SRC)
    for r in R.itertuples():
        nm = f"cfg.{cfg_name(PARTS_BY[r.part], r.range_g, r.odr_hz)}.{r.set}"
        for k in ("n", "median", "median_lo", "median_hi", "p90", "w10", "w10_lo", "w10_hi", "w20"):
            E.add(f"{nm}.{k}", int(getattr(r, k)) if k == "n" else round(float(getattr(r, k)), 4), "tests" if k == "n" else ("fraction" if k[0] == "w" else "percent"))
        if hasattr(r, "band") and not pd.isna(r.band):
            for k in ("band", "band_lo", "band_hi"):
                E.add(f"{nm}.{k}", round(float(getattr(r, k)), 4), "fraction", notes="share inside v <= delta-V <= 2 v, frontal barrier tests")
        if not pd.isna(getattr(r, "mp_w10", np.nan)):
            for k in ("mp_median", "mp_median_lo", "mp_median_hi", "mp_p90", "mp_w10", "mp_w10_lo", "mp_w10_hi", "mp_band", "mp_band_lo", "mp_band_hi"):
                v = getattr(r, k, np.nan)
                if not pd.isna(v):
                    E.add(f"{nm}.{k}", round(float(v), 4), "fraction" if "w10" in k or "band" in k else "percent", notes="fill + ridge (N14, fit on the 176 with the generic chain) at 100 Hz")
    # S3: decision rule
    n13 = R[R.set == "n13"].copy()
    n13["meets"] = n13.w10_lo >= TARGET
    ho = R[R.set == "heldout"].set_index(["part", "range_g", "odr_hz"])
    n13["meets_heldout"] = [bool(ho.loc[(r.part, r.range_g, r.odr_hz)].w10_lo >= TARGET) for r in n13.itertuples()]
    for r in n13.itertuples():
        E.add(f"s3.meets.{cfg_name(PARTS_BY[r.part], r.range_g, r.odr_hz)}", int(r.meets), "flag", notes="lower 95% bound of the share within 10% on the 176 tests is at least 0.80")
        E.add(f"s3.meets_heldout.{cfg_name(PARTS_BY[r.part], r.range_g, r.odr_hz)}", int(r.meets_heldout), "flag", notes="same rule on the T13a held-out records (confirmation, descriptive)")
    ok = n13[n13.meets]
    E.add("s3.n_configs", int(len(n13)), "configurations")
    E.add("s3.n_meeting", int(len(ok)), "configurations")
    if len(ok):
        best = ok.sort_values(["range_g", "odr_hz"]).iloc[0]
        E.add("s3.smallest_range_g", float(best.range_g), "g", notes="smallest full-scale range among configurations that meet the rule")
        E.add("s3.smallest_range_part", PARTS_BY[best.part].name, "text")
        E.add("s3.smallest_range_odr_hz", float(best.odr_hz), "Hz")
        E.add("s3.smallest_range_w10", round(float(best.w10), 4), "fraction")
        E.add("s3.smallest_range_w10_lo", round(float(best.w10_lo), 4), "fraction")
    else:
        E.add("s3.smallest_range_g", "NOT_RUN", "g", notes="no configuration meets the rule", origin="NOT_RUN")
    for p in PARTS:
        sub = n13[n13.part == p.key]
        E.add(f"s3.part_meets_any.{p.key}", int(sub.meets.any()), "flag", notes="at least one configuration of the part meets the rule on the 176 tests")
        E.add(f"s3.part_meets_any_heldout.{p.key}", int((sub.meets & sub.meets_heldout).any()), "flag", notes="a configuration that meets the rule on the 176 AND on the held-out records")
    # noise sensitivity on the 176
    nn = R[R.set == "n13_nonoise"].set_index(["part", "range_g", "odr_hz"])
    d = [float(r.w10 - nn.loc[(r.part, r.range_g, r.odr_hz)].w10) for r in n13.itertuples()]
    E.add("noise.max_abs_change_w10", round(float(np.max(np.abs(d))), 4), "fraction", notes="largest change in the share within 10% between the run with datasheet noise and the run without noise, 176 tests")
    E.add("noise.n_flag_changes", int(sum(bool(r.meets) != bool(nn.loc[(r.part, r.range_g, r.odr_hz)].w10_lo >= TARGET) for r in n13.itertuples())), "configurations",
          notes="configurations whose S3 verdict differs between the noise and no-noise runs")
    E.add("caveat.esp32_read_rate", "NOT_RUN", "Hz", notes="effective I2C or SPI read rate of each part on an ESP32 was not measured: hardware item; the study uses the datasheet output data rate", origin="NOT_RUN")
    E.flush(("sel.cfg.", "sel.s3.", "sel.noise.", "sel.caveat."))
    pd.set_option("display.width", 250)
    print(n13[["part", "range_g", "odr_hz", "w10", "w10_lo", "w10_hi", "median", "p90", "meets", "meets_heldout"]].round(3).to_string())


PARTS_BY = {p.key: p for p in PARTS}

if __name__ == "__main__":
    main()
