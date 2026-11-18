"""L6 (docs/02_preregistration/PREREGISTRATION_V16.md section 15.2): crash-weighted gateway placement from real crash locations (MEASURED_SOFTWARE for the crash data, ANALYTICAL for coverage).

    python -m crashguard.r5_l6 freeze      # hash sources and data files
    python -m crashguard.r5_l6 held        # held-out year 2022, once; keys r5.l6.*

Development years 2019 to 2021 place the gateways of method (a) (fatality-weighted greedy maximum coverage of crashes); method (b) places them on GeoNames places of at least 15,000 inhabitants (population-weighted
greedy maximum coverage); method (c) is a uniform grid. A crash is covered if it lies within ``R_COV`` of a gateway (log-distance model of the ns-3 application at SF9, ANALYTICAL; the calibration on LoED data is
NOT_RUN because LoED has no positions). Held-out: share of 2022 crashes covered. Nothing here reads ``data/hardware``.
"""
from __future__ import annotations

import io
import json
import math
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "r5_fars"
DEV_YEARS, HELD_YEAR = (2019, 2020, 2021), 2022
KS = (50, 100, 200, 400)
R_EARTH = 6371.0
SENS_RADII = {"sf7_2.5km": 2.5, "sf11_6km": 6.0}
CELL_DEG = 0.02
SEED, NB = 42, 2000
BBOX = (24.0, 50.0, -125.0, -66.0)
FILES = [f"data/raw/r5_fars/fars{y}.zip" for y in (*DEV_YEARS, HELD_YEAR)] + ["data/raw/r5_fars/cities15000.zip"]
EXPECTED = {"data/raw/r5_fars/fars2019.zip": "0974abb9", "data/raw/r5_fars/fars2020.zip": "b2806902", "data/raw/r5_fars/fars2021.zip": "743c19a1", "data/raw/r5_fars/fars2022.zip": "989448d7", "data/raw/r5_fars/cities15000.zip": "ce7a4055"}  # V16 15.1


def r_cov_km(tx_dbm: float = 14.0, vehicle_loss_db: float = 10.0, sens_dbm: float = -129.0) -> float:
    """Range at which 14 - 10 - (25 + 30 log10 d) = sensitivity (the log-distance model of the ns-3 application, no shadowing)."""
    return float(10 ** ((tx_dbm - vehicle_loss_db - 25.0 - sens_dbm) / 30.0) / 1000.0)


R_COV = 4.0


def xyz(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    la, lo = np.radians(np.asarray(lat, float)), np.radians(np.asarray(lon, float))
    return R_EARTH * np.stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)], axis=1)


def chord(r_km: float) -> float:
    """Straight-line (chord) distance in km that corresponds to the great-circle distance ``r_km`` on the sphere."""
    return 2.0 * R_EARTH * math.sin(r_km / (2.0 * R_EARTH))


def load_crashes(year: int) -> pd.DataFrame:
    z = zipfile.ZipFile(RAW / f"fars{year}.zip")
    name = [n for n in z.namelist() if n.lower().endswith("accident.csv")][0]
    a = pd.read_csv(io.BytesIO(z.read(name)), encoding="latin1", low_memory=False, usecols=["LATITUDE", "LONGITUD", "FATALS"])
    a = a[a.LATITUDE.between(BBOX[0], BBOX[1]) & a.LONGITUD.between(BBOX[2], BBOX[3])]
    return pd.DataFrame(dict(lat=a.LATITUDE.to_numpy(float), lon=a.LONGITUD.to_numpy(float), w=a.FATALS.to_numpy(float)))


def load_places() -> pd.DataFrame:
    z = zipfile.ZipFile(RAW / "cities15000.zip")
    d = pd.read_csv(io.StringIO(z.read("cities15000.txt").decode("utf-8")), sep="\t", header=None, usecols=[4, 5, 8, 14], names=["lat", "lon", "cc", "pop"])
    d = d[(d.cc == "US") & d.lat.between(BBOX[0], BBOX[1]) & d.lon.between(BBOX[2], BBOX[3])]
    return pd.DataFrame(dict(lat=d.lat.to_numpy(float), lon=d.lon.to_numpy(float), w=d["pop"].to_numpy(float)))


def candidate_sites(crashes: pd.DataFrame, places: pd.DataFrame) -> pd.DataFrame:
    """Distinct 0.02-degree cells (centres) that hold at least one crash, plus the places. No held-out information."""
    cell = pd.DataFrame(dict(i=np.floor(crashes.lat / CELL_DEG).astype(int), j=np.floor(crashes.lon / CELL_DEG).astype(int))).drop_duplicates()
    c = pd.DataFrame(dict(lat=(cell.i.to_numpy() + 0.5) * CELL_DEG, lon=(cell.j.to_numpy() + 0.5) * CELL_DEG))
    return pd.concat([c, places[["lat", "lon"]]], ignore_index=True)


def covers(sites_xyz: np.ndarray, targets_xyz: np.ndarray, r_km: float) -> list[np.ndarray]:
    tree = cKDTree(targets_xyz)
    return [np.asarray(x, np.int64) for x in tree.query_ball_point(sites_xyz, chord(r_km))]


def greedy(cover: list[np.ndarray], weights: np.ndarray, k: int) -> list[int]:
    """Greedy maximum weighted coverage with lazy gain updates: the site with the largest uncovered weight first; ties go to the lower index."""
    import heapq

    covered = np.zeros(len(weights), bool)
    heap = [(-float(weights[c].sum()), i) for i, c in enumerate(cover) if len(c)]
    heapq.heapify(heap)
    chosen: list[int] = []
    while heap and len(chosen) < k:
        neg, i = heapq.heappop(heap)
        gain = float(weights[cover[i][~covered[cover[i]]]].sum())
        if heap and gain < -heap[0][0] - 1e-12:
            heapq.heappush(heap, (-gain, i))
            continue
        if gain <= 0:
            break
        chosen.append(i)
        covered[cover[i]] = True
    return chosen


def coverage_flags(gateways_xyz: np.ndarray, targets_xyz: np.ndarray, r_km: float) -> np.ndarray:
    if not len(gateways_xyz):
        return np.zeros(len(targets_xyz), bool)
    d, _ = cKDTree(gateways_xyz).query(targets_xyz, distance_upper_bound=chord(r_km))
    return np.isfinite(d)


def grid_sites(sites: pd.DataFrame, k: int, near_km: float = 100.0) -> np.ndarray:
    """Uniform grid: a regular lattice in latitude and longitude whose spacing gives about ``k`` lattice points within ``near_km`` of a candidate site; each lattice point is placed at the nearest candidate."""
    tree = cKDTree(xyz(sites.lat.to_numpy(), sites.lon.to_numpy()))
    lo, hi = 0.05, 20.0
    pts = None
    for _ in range(40):
        d = (lo + hi) / 2
        la, lo_ = np.meshgrid(np.arange(BBOX[0], BBOX[1] + 1e-9, d), np.arange(BBOX[2], BBOX[3] + 1e-9, d), indexing="ij")
        cand = np.stack([la.ravel(), lo_.ravel()], axis=1)
        dist, idx = tree.query(xyz(cand[:, 0], cand[:, 1]), distance_upper_bound=chord(near_km))
        keep = np.isfinite(dist)
        n = int(len(set(idx[keep].tolist())))
        pts = sorted(set(idx[keep].tolist()))
        if n > k:
            lo = d
        else:
            hi = d
    return np.array(pts[:k] if len(pts) >= k else pts, np.int64)


def _chunks(nb: int, size: int = 100) -> list[int]:
    return [min(size, nb - i) for i in range(0, nb, size)]


def paired_diff_boot(a: np.ndarray, b: np.ndarray, seed: int = SEED, nb: int = NB) -> dict:
    """Mean of the paired 0/1 difference (covered by a minus covered by b) over crashes, 95% interval, one-sided p of H0: difference <= 0."""
    d = np.asarray(a, float) - np.asarray(b, float)
    rng = np.random.default_rng(seed)
    m = np.concatenate([d[rng.integers(0, len(d), (c, len(d)))].mean(1) for c in _chunks(nb)])  # row blocks of the same stream: the same draws as one matrix, less memory
    return dict(pt=float(d.mean()), lo=float(np.quantile(m, 0.025)), hi=float(np.quantile(m, 0.975)), p=float(((m <= 0).sum() + 1) / (nb + 1)), n=int(len(d)))


def criterion(rows: dict) -> tuple[bool, float]:
    """H-L6: for every k the difference is at least 0.10 with a lower limit above 0; p = the largest p over the k."""
    met = all(v["pt"] >= 0.10 and v["lo"] > 0 for v in rows.values())
    return bool(met), float(max(v["p"] for v in rows.values()))


def place_all(r_km: float, ks=KS) -> dict:
    """Gateways of the three methods for every k, from development data only (returns xyz arrays)."""
    dev = pd.concat([load_crashes(y) for y in DEV_YEARS], ignore_index=True)
    places = load_places()
    sites = candidate_sites(dev, places)
    s_xyz = xyz(sites.lat.to_numpy(), sites.lon.to_numpy())
    cov_c = covers(s_xyz, xyz(dev.lat.to_numpy(), dev.lon.to_numpy()), r_km)
    cov_p = covers(s_xyz, xyz(places.lat.to_numpy(), places.lon.to_numpy()), r_km)
    kmax = max(ks)
    order_c = greedy(cov_c, dev.w.to_numpy(), kmax)
    order_p = greedy(cov_p, places.w.to_numpy(), kmax)
    out = {}
    for k in ks:
        out[k] = dict(crash=s_xyz[order_c[:k]], pop=s_xyz[order_p[:k]], grid=s_xyz[grid_sites(sites, k)])
    return out


def _freeze() -> None:
    from crashguard import r5_common as R5
    from crashguard import r5_guard as G

    G.check_data(EXPECTED)
    d = R5.freeze_entry("l6", ["src/crashguard/r5_l6.py"], dict(ks=list(KS), r_cov_km=R_COV, dev_years=list(DEV_YEARS), held_year=HELD_YEAR, cell_deg=CELL_DEG), FILES)
    print("frozen l6", d["params_sha256"][:16])


def _held() -> None:
    from crashguard import r5_common as R5

    R5.check_frozen("l6")
    held = load_crashes(HELD_YEAR)
    h_xyz = xyz(held.lat.to_numpy(), held.lon.to_numpy())
    rec = R5.Rec("r5.l6.", "src/crashguard/r5_l6.py", "MEASURED_SOFTWARE")
    rec.add("held.n_crashes_2022", int(len(held)), "crashes", "FARS 2022 crashes with valid coordinates in the contiguous US (held-out year)")
    rec.add("dev.n_crashes_2019_2021", int(sum(len(load_crashes(y)) for y in DEV_YEARS)), "crashes")
    rec.add("r_cov_km_formula", r_cov_km(), "km", "range of the ns-3 log-distance model at SF9 (-129 dBm), ANALYTICAL assumption; not calibrated on LoED (no positions)", origin="ANALYTICAL")
    main = {}
    for tag, r in (("main", R_COV), *SENS_RADII.items()):
        pl = place_all(r)
        rows = {}
        for k in KS:
            fl = {m: coverage_flags(pl[k][m], h_xyz, r) for m in ("crash", "pop", "grid")}
            rows[k] = paired_diff_boot(fl["crash"], fl["pop"])
            for m in fl:
                rec.add(f"{tag}.k{k}.cov_{m}", float(fl[m].mean()), "fraction", f"share of 2022 crashes within {r:g} km of a gateway; method {m}")
            rec.add(f"{tag}.k{k}.diff_crash_minus_pop", rows[k]["pt"], "fraction", "paired bootstrap over 2022 crashes")
            rec.add(f"{tag}.k{k}.diff_lo", rows[k]["lo"], "fraction")
            rec.add(f"{tag}.k{k}.diff_hi", rows[k]["hi"], "fraction")
            rec.add(f"{tag}.k{k}.p", rows[k]["p"], "p", "one-sided bootstrap p of H0: difference at most 0")
        if tag == "main":
            main = rows
    met, p = criterion(main)
    rec.add("hL6.criterion_met", int(met), "bool", "for every k the crash-weighted minus population-weighted coverage is at least 0.10 with a lower 95% limit above 0")
    rec.add("hL6.p", p, "p", "largest one-sided p over the four k (intersection test)")
    rec.add("road_length_baseline", "NOT_RUN", "text", "no road-length data obtained", origin="NOT_RUN")
    rec.add("loed_calibration", "NOT_RUN", "text", "LoED has no device or gateway positions, so the path-loss model cannot be calibrated on it", origin="NOT_RUN")
    rec.write()
    print(json.dumps({k: {x: round(v[x], 4) for x in ("pt", "lo", "hi", "p")} for k, v in main.items()}, indent=1), met)


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"freeze": _freeze, "held": _held}.get(cmd, lambda: print(__doc__))()


if __name__ == "__main__":
    main()
