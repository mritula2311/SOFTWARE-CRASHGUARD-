"""V7 block A: probe that the simulator output does not change when ``world['pa']`` is absent.

    python scripts/pa_regression_probe.py write FILE     # store the summaries of a fixed set of runs
    python scripts/pa_regression_probe.py check FILE     # compare the current output with the stored one
"""
import json
import math
import sys

from crashguard import fin_g as G
from crashguard import fin_sim as FS
from crashguard import world_sim as W


def runs():
    pairs = G.build_pairs()
    pools = G.to_pools(pairs, None)
    t = FS.tuned()
    out = {}
    for pol in ("P0", "P1+", "P3", "P4"):
        for cell in G.cells_of(G.HELD)[:2]:
            cfg = G.cfg_for(pol, cell, 8000, 3, pools, t, f"g_{cell['name']}")
            r = W.simulate(cfg)
            out[f"{pol}|{cell['name']}"] = {k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in r.items() if isinstance(v, (int, float, str)) and k not in ("suppressed", "suppressed_unrx", "suppressed_share", "event_reach10_critical")}
    return out


if __name__ == "__main__":
    mode, f = sys.argv[1], sys.argv[2]
    cur = runs()
    if mode == "write":
        json.dump(cur, open(f, "w"), indent=1, sort_keys=True)
        print("stored", len(cur))
    else:
        old = json.load(open(f))
        bad = [k for k in old if json.dumps(old[k], sort_keys=True) != json.dumps(cur.get(k), sort_keys=True)]
        print("identical" if not bad else f"DIFFERENT: {bad}")
        sys.exit(1 if bad else 0)
