"""S5 (H-S6): IMU only against IMU plus SW-420 confirmation on the simulated hardware-format variants (SIMULATED_HW_FORMAT).

Design and criteria: docs/02_preregistration/PREREGISTRATION_V11.md section 2.3, H-S6. Rule: the IMU trigger (2.0 g) must be followed by at least 2 of the 6 switches firing
within -100 ms to +300 ms of the trigger. Pooled over the 15 sensor variants (paired events); exact one-sided McNemar test on the non-crash events (the confirmed alarms are a subset
of the IMU alarms, so the discordant pairs all go one way). Sensitivity (not in the family): per-unit switch threshold ranges 0.8 to 2.0 g and 3.0 to 6.0 g against the base 1.5 to 4.0 g.
Every gain depends on the simulator's switch model (an ASSUMPTION): the switch fires on the 5 Hz high-passed magnitude, and the simulated crash, bump and tap events were built by us.
Keys ``sh.s5.*``.

    python -m crashguard.sh_s5
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import binom

from crashguard import config as C
from crashguard import hwsim_v2 as H
from crashguard import sh_events as E
from crashguard.results import record_many

SRC = "src/crashguard/sh_s5.py"
SENSOR_VARIANTS = [n for _i, n, _p, k in H.VARIANTS if "sensor" in k]
K_MIN = 2
N_BOOT = 2000


def decisions(events: list[dict]) -> pd.DataFrame:
    rows = []
    for e in events:
        i0 = E.trigger_index(e)
        conf = False
        if i0 is not None:
            t0 = e["t"][i0]
            m = (e["t"] >= t0 - 100) & (e["t"] <= t0 + 300)
            conf = int((e["sw"][m].max(axis=0) > 0).sum()) >= K_MIN
        rows.append(dict(label=e["label"], imu=i0 is not None, both=(i0 is not None) and conf))
    return pd.DataFrame(rows)


def summarise(D: pd.DataFrame, rng) -> dict:
    nc, cr = D[D.label == "non_crash"], D[D.label == "crash"]
    b = int((nc.imu & ~nc.both).sum())
    c = int((~nc.imu & nc.both).sum())
    far_i, far_s = float(nc.imu.mean()), float(nc.both.mean())
    rec_i, rec_s = float(cr.imu.mean()), float(cr.both.mean())
    n_nc, n_cr = len(nc), len(cr)
    idx_n = rng.integers(0, n_nc, (N_BOOT, n_nc))
    idx_c = rng.integers(0, n_cr, (N_BOOT, n_cr))
    red = (nc.imu.to_numpy(float)[idx_n].mean(axis=1) - nc.both.to_numpy(float)[idx_n].mean(axis=1))
    loss = (cr.imu.to_numpy(float)[idx_c].mean(axis=1) - cr.both.to_numpy(float)[idx_c].mean(axis=1))
    return dict(n_noncrash=n_nc, n_crash=n_cr, far_imu=far_i, far_imu_sw=far_s, far_reduction=far_i - far_s, far_reduction_lo=float(np.quantile(red, 0.025)), far_reduction_hi=float(np.quantile(red, 0.975)),
                recall_imu=rec_i, recall_imu_sw=rec_s, recall_loss=rec_i - rec_s, recall_loss_lo=float(np.quantile(loss, 0.025)), recall_loss_hi=float(np.quantile(loss, 0.975)),
                mcnemar_b=b, mcnemar_c=c, p_mcnemar=float(binom.sf(b - 1, b + c, 0.5)) if b + c else 1.0)


def pooled(names_dirs: list, rng) -> tuple[dict, list[dict]]:
    frames, per = [], []
    for name, d in names_dirs:
        D = decisions(E.load_dir(d, relaxed=True))
        frames.append(D)
        per.append(dict(variant=name, **summarise(D, rng)))
    return summarise(pd.concat(frames, ignore_index=True), rng), per


def main() -> None:
    rng = np.random.default_rng(C.SEED)
    ent: list[dict] = []

    def add(name, value, unit, notes=""):
        ent.append(dict(name=f"sh.s5.{name}", value=value, unit=unit, origin="SIMULATED_HW_FORMAT", source_file=SRC, notes=notes))

    out = {}
    arms = {"base_range_1.5_4.0": [(n, E.VARIANT_ROOT / n) for n in SENSOR_VARIANTS]}
    for sw in H.SW_SENS:
        tag = f"range_{sw[0]:g}_{sw[1]:g}"
        arms[tag] = [(n, E.VARIANT_ROOT / f"{n}__sw{sw[0]:g}-{sw[1]:g}") for n in SENSOR_VARIANTS]
    rows = []
    for arm, nd in arms.items():
        pool, per = pooled(nd, rng)
        out[arm] = pool
        for k, v in pool.items():
            add(f"{arm}.pooled.{k}", round(v, 5) if isinstance(v, float) else v, "value", "pooled over the 15 sensor variants; bootstrap 2,000 resamples of events, seed 42" if k.endswith(("_lo", "_hi")) else "")
        for r in per:
            rows.append(dict(arm=arm, **r))
            if arm.startswith("base"):
                for k in ("far_imu", "far_imu_sw", "far_reduction", "recall_imu", "recall_imu_sw", "recall_loss", "mcnemar_b"):
                    add(f"{arm}.{r['variant']}.{k}", round(r[k], 5) if isinstance(r[k], float) else r[k], "value")
    pd.DataFrame(rows).to_csv("results/tables/sh_s5_variants.csv", index=False)
    b = out["base_range_1.5_4.0"]
    ok = b["far_reduction"] >= 0.02 and b["recall_loss"] <= 0.02
    add("hS6.criterion_met", int(ok), "flag", "pooled false-alarm reduction >= 0.02 and crash-recall loss <= 0.02, base switch thresholds")
    add("hS6.p_raw", float(f"{b['p_mcnemar']:.3e}"), "p", "exact one-sided McNemar test on the non-crash events (pooled over variants)")
    for arm in ("range_0.8_2", "range_3_6"):
        o = out[arm]
        add(f"sensitivity.{arm}.criterion_met", int(o["far_reduction"] >= 0.02 and o["recall_loss"] <= 0.02), "flag", "not in the family: threshold-range sensitivity")
    record_many(ent, purge_prefixes=("sh.s5.",))
    for arm, o in out.items():
        print(arm, {k: round(v, 4) if isinstance(v, float) else v for k, v in o.items()})


if __name__ == "__main__":
    main()
