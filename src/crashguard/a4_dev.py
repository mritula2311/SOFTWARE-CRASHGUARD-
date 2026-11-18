"""Development iterations of A1 (PREREGISTRATION_V15 section 2.4; at most five, each logged). Development data: LoED round-3 HELD-OUT devices (half 1) and ns-3 seeds 101 to 120.

    python -m crashguard.a4_dev trace <it>      # trace replay on the LoED development devices
    python -m crashguard.a4_dev ns3 <it>        # ns-3 development cells (SF9, both settings, losses 0 and 0.3)
    python -m crashguard.a4_dev freeze          # apply the selection rule of V15 2.4 to the logged iterations, write results/tables/a4_frozen.json with the hashes

Nothing here is written to results/results.json.
"""
from __future__ import annotations

import hashlib
import json
import pickle
import sys
from pathlib import Path

import numpy as np

from crashguard import a4_a1 as A
from crashguard import a4_a1_ns3 as N

ROOT = Path(__file__).resolve().parents[2]
LOG = ROOT / "results" / "tables" / "a4_dev_log.json"
ITERS = {  # the only items development may change (V15 2.4); fixed here before the first run
    0: dict(gap=0.0, reserve=4, after_confirm=True),
    1: dict(gap=0.05, reserve=4, after_confirm=True),
    2: dict(gap=0.1, reserve=4, after_confirm=True),
    3: dict(gap=0.0, reserve=4, after_confirm=False),
    4: dict(gap=0.0, reserve=2, after_confirm=True),
}
FROZEN = ROOT / "results" / "tables" / "a4_frozen.json"
SOURCES = ("src/crashguard/a4_a1.py", "src/crashguard/a4_a1_ns3.py", "src/crashguard/a4_a2.py", "src/crashguard/a4_common.py", "src/crashguard/a4_analyse.py", "src/crashguard/a4_dev.py", "xsim/ns3/xsim_alert.cc")


def write_params() -> None:
    N.DEV_PARAMS.write_text(json.dumps({str(k): v for k, v in ITERS.items()}, indent=1), encoding="utf-8")


def log_read() -> dict:
    return json.loads(LOG.read_text(encoding="utf-8")) if LOG.exists() else {}


def log_write(d: dict) -> None:
    LOG.write_text(json.dumps(d, indent=1, default=float), encoding="utf-8")


def dev_a1(it: int) -> None:
    prm = ITERS[it]
    links = pickle.loads((ROOT / "data" / "processed" / "r3_t1_links.pkl").read_bytes())
    sel = sorted(d for d, v in links.items() if v["half"] == 1)  # round-3 HELD-OUT half = DEVELOPMENT here
    cfg = A.Cfg(**prm)
    out = ROOT / "data" / "processed" / f"a4_dev_trace_it{it}.pkl"
    r = A.run(links, sel, 300, out, cfg)
    res = r["res"]
    summ: dict = dict(params=prm, n_links=len(res), inv=r["inv"])
    for g, lo, hi in A.T1.GROUPS:
        idx = [x for x in res if lo <= x["p"] < hi]
        if not idx:
            continue
        pa = np.array([x["acc"]["A1"]["prov_ok"] / max(x["acc"]["A1"]["n_E"], 1) for x in idx])
        pr = np.array([x["acc"]["R3"]["prov_ok"] / max(x["acc"]["R3"]["n_E"], 1) for x in idx])
        sa = sum(x["acc"]["A1"]["two_air"] for x in idx)
        s1 = sum(x["acc"]["A1"]["single_air"] for x in idx)
        sr = sum(x["acc"]["R3"]["two_air"] for x in idx)
        da = sum(x["acc"]["A1"]["two_d"] for x in idx)
        dr = sum(x["acc"]["R3"]["two_d"] for x in idx)
        n_cr = sum(x["acc"]["A1"]["n_cr"] for x in idx)
        summ[g] = dict(n=len(idx), prov_a1=float(pa.mean()), prov_r3=float(pr.mean()), prov_diff=float((pa - pr).mean()), extra_air_a1=sa / s1 - 1, extra_air_r3=sr / s1 - 1, deliv_diff=(da - dr) / max(n_cr, 1))
    pa = np.array([x["acc"]["A1"]["prov_ok"] / max(x["acc"]["A1"]["n_E"], 1) for x in res])
    pr = np.array([x["acc"]["R3"]["prov_ok"] / max(x["acc"]["R3"]["n_E"], 1) for x in res])
    summ["all"] = dict(prov_a1=float(pa.mean()), prov_r3=float(pr.mean()), prov_diff=float((pa - pr).mean()))
    log = log_read()
    log.setdefault(str(it), {})["trace"] = summ
    log_write(log)
    print(json.dumps(summ, indent=1, default=float))


def dev_ns3(it: int) -> None:
    write_params()
    N.dev(it)
    cells = [(9, st, p) for st in N.P1.SETTINGS for p in (0.0, 0.3)]
    o = N.analyse(N.OUT_DEV / f"it{it}", N.OUT_DEV / "base", N.DEV_SEEDS, cells, prefix=f"a4.dev.it{it}.", record=False)
    summ = {}
    for cn, v in o["cells"].items():
        if v:
            c = v["c"]
            summ[cn] = dict(extra_air_a1=c["ratio_pt"], extra_air_r3=c["ratio_r3_pt"], deliv_diff=c["dd_pt"], prov_a1=c["prov_a"], prov_r3=c["prov_t"], inv_late=v["info"]["inv_late"], inv_duty=v["info"]["inv_duty"], runs=c["n"])
    log = log_read()
    log.setdefault(str(it), {})["ns3"] = summ
    log_write(log)
    print(json.dumps(summ, indent=1, default=float))


def sha(path: str) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def freeze() -> None:
    """Selection rule (V15 2.4): among the logged iterations take those whose development provisional delivery (all links) is at least 3 points above R3; of these the one with the lowest development extra airtime
    at SF9 (mean over the ns-3 development cells), ties to the smaller gap; if none qualifies keep iteration 0 (the default of 2.1)."""
    log = log_read()
    cand = []
    for k, v in log.items():
        if "trace" not in v or "ns3" not in v:
            continue
        if v["trace"]["all"]["prov_diff"] >= 0.03:
            ex = float(np.mean([c["extra_air_a1"] for c in v["ns3"].values()]))
            cand.append((ex, ITERS[int(k)]["gap"], int(k)))
    pick = sorted(cand)[0][2] if cand else 0
    prm = ITERS[pick]
    out = dict(a1=prm, chosen_iteration=pick, qualified=[c[2] for c in sorted(cand)], rule="PREREGISTRATION_V15 section 2.4", sources={s: sha(s) for s in SOURCES if (ROOT / s).exists()},
               params_file_sha256=hashlib.sha256(json.dumps(prm, sort_keys=True).encode()).hexdigest())
    FROZEN.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "trace":
        dev_a1(int(sys.argv[2]))
    elif cmd == "ns3":
        dev_ns3(int(sys.argv[2]))
    elif cmd == "freeze":
        freeze()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
