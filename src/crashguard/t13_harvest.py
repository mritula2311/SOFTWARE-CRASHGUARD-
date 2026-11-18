"""T13a, step 1: collect the held-out NHTSA test modes (selection rules in docs/07_log/DECISIONS.md, entry "T13a selection record", written before this ran).

The catalogue of the public NHTSA NRD API is fetched once (test number 3000 and above) and kept in data/processed/. Candidate tests are those of the other modes listed in the record that are not among the
176 tests of N13/N14. Each candidate is downloaded (metadata and ISO MME zip, cached in data/raw/nhtsa/, git-ignored) and passed through the SAME channel and pulse rules as the 176
(``nhtsa.load_test``). Reasons for exclusion are written to results/tables/t13_excluded.csv. Nothing is dropped after looking at an error.
"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

import joblib
import pandas as pd

from crashguard import config as C
from crashguard import nhtsa as N

CATALOG = C.PROCESSED / "nhtsa_catalog.json"
CACHE = C.PROCESSED / "t13_heldout_signals.joblib"
MIN_REF_DV_KMH = 10.0  # fixed in docs/07_log/DECISIONS.md before the run


def fetch_catalog() -> list[dict]:
    if CATALOG.exists():
        return json.loads(CATALOG.read_text(encoding="utf-8"))
    out, page = [], 1
    while True:
        d = N._get(f"{N.API}/by-search?pageNumber={page}&count=100&testNoFrom=3000")
        res = d.get("results") or []
        out += res
        if len(res) < 100 or page > 300:
            break
        page += 1
    C.PROCESSED.mkdir(parents=True, exist_ok=True)
    CATALOG.write_text(json.dumps(out), encoding="utf-8")
    return out


def is_other_mode(t: dict) -> bool:
    c, a = t["testConfiguration"], t.get("impactAngle")
    return (c == "VEHICLE INTO POLE") or (c == "VEHICLE INTO BARRIER" and a != 0) or (c == "VEHICLE INTO VEHICLE") or (c == "IMPACTOR INTO VEHICLE" and a != 270)


def used_176() -> set[int]:
    return set(pd.read_csv(C.TABLES / "nhtsa_tests.csv").test_no.astype(int))


def candidates() -> list[dict]:
    skip = used_176()
    return sorted((t for t in fetch_catalog() if t.get("hasInstrumentationInfo") and is_other_mode(t) and int(t["testNo"]) not in skip), key=lambda t: t["testNo"])


def vehicles_of(t: dict, side: bool) -> list[dict]:
    meta = N.metadata(t["testNo"])
    return [v for v in (meta.get("VEHICLE") or [])
            if ((v.get("VEHSPD") or 0) == 0) == side and not any(w in f"{v.get('MAKED', '')} {v.get('MODELD', '')}".upper() for w in N.NOT_VEHICLE)]


def _download(t: dict) -> tuple[int, str]:
    try:
        meta = N.metadata(t["testNo"])
        N.iso_zip(t["testNo"], meta)
        return t["testNo"], "ok"
    except Exception as e:  # noqa: BLE001 - recorded as the reason
        return t["testNo"], f"download failed ({str(e)[:80]})"


def harvest(workers: int = 8) -> tuple[list[dict], list[dict]]:
    cands = candidates()
    print(f"{len(cands)} candidate tests", flush=True)
    with ThreadPoolExecutor(workers) as ex:
        dl = dict(ex.map(_download, cands))
    found, excl = [], []
    for i, t in enumerate(cands):
        if dl[t["testNo"]] != "ok":
            excl.append(dict(test_no=t["testNo"], role="", mode=f"{t['testConfiguration']} {t.get('impactAngle')}", reason=dl[t["testNo"]]))
            continue
        for side in (False, True):
            vehs = vehicles_of(t, side)
            if not vehs:
                continue
            role = "stationary" if side else "moving"
            sig = N.load_test(t, side)
            angle = t.get("impactAngle")
            mode = f"{t['testConfiguration']} {'unknown' if angle is None else int(angle)}"
            if sig is None or "reason" in sig:
                excl.append(dict(test_no=t["testNo"], role=role, mode=mode, reason=(sig or {}).get("reason", "unknown")))
                continue
            v = vehs[0]
            found.append(dict(test_no=int(t["testNo"]), role=role, mode=mode, config=t["testConfiguration"], angle=float("nan") if angle is None else float(angle), v=float(t["closingSpeed"] or 0.0),
                              make=str(v.get("MAKED")), model=str(v.get("MODELD")), year=int(v.get("YEAR") or 0), sig=sig))
        if i % 100 == 0:
            print(i, len(found), len(excl), flush=True)
    C.PROCESSED.mkdir(parents=True, exist_ok=True)
    joblib.dump(dict(found=found, excluded=excl, n_candidates=len(cands)), CACHE)
    return found, excl


if __name__ == "__main__":
    f, e = harvest()
    C.TABLES.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(e).to_csv(C.TABLES / "t13_excluded.csv", index=False)
    print(len(f), "usable records;", len(e), "excluded")
