"""B2 (docs/02_preregistration/PREREGISTRATION_V4.md section 5): requirement calculator data. Share of the 913 pooled records whose PLAIN delta-V (clipped, resampled sensor model of ``sel_parts``) is within +-10% of the reference,
per crash mode and per sensor configuration (part, range, rate), with grouped bootstrap intervals. All records are used (this describes the pooled set; it is not a held-out claim). MEASURED_SOFTWARE.

``build`` writes results/tables/p_b2_flags.npz (flags per configuration and record) and p_b2_table.csv and the ``p.b2.*`` keys; ``requirement`` answers a query for a mode mix.
"""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from crashguard import boot as B
from crashguard import config as C
from crashguard import pp_common as PC
from crashguard import pp_pool as PP
from crashguard import sel_study as SEL
from crashguard.sel_parts import PARTS

FLAGS = C.TABLES / "p_b2_flags.npz"
TOL = 10.0


def configs() -> list[tuple[str, float, int]]:
    return [(p.key, float(rg), int(odr)) for p in PARTS for rg in p.study_ranges for odr in p.odrs_hz if odr <= SEL.MAX_ODR_HZ]


_G: dict = {}


def _init():
    d = PP.load()
    _G["pool"] = d["pool"]


def _cfg(args):
    key, rg, odr = args
    p = next(p for p in PARTS if p.key == key)
    ref = np.array([r["ref"] for r in _G["pool"]])
    dv = np.array([SEL.part_dv(r["sig"], p, rg, odr, 42 + i, True) for i, r in enumerate(_G["pool"])])
    return 100.0 * np.abs(dv - ref) / ref


def draws_matrix(groups: np.ndarray) -> np.ndarray:
    """(1000, n) resample counts of whole groups (seed 42), the draws of ``boot``."""
    mem = B.group_members(groups)
    n = len(groups)
    Wm = np.zeros((B.N_BOOT, n))
    for b, idx in enumerate(B._gidx(mem, B.N_BOOT, B.SEED)):
        Wm[b] = np.bincount(idx, minlength=n)
    return Wm


def mode_shares(flags: np.ndarray, modes: np.ndarray, Wm: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Per configuration: shares (configs, 4) point and draws (configs, 1000, 4)."""
    oh = np.stack([modes == m for m in PC.MODES], axis=1).astype(float)
    pt = (flags.astype(float) @ oh) / oh.sum(0)
    num = np.einsum("bn,cn,nm->cbm", Wm, flags.astype(float), oh)
    den = Wm @ oh
    return pt, num / np.maximum(den[None], 1e-9)


def build() -> None:
    d = PP.load()
    T = PP.table(d)
    cfgs = configs()
    with ProcessPoolExecutor(12, initializer=_init) as ex:
        errs = list(ex.map(_cfg, cfgs, chunksize=1))
    flags = np.stack([e <= TOL for e in errs])
    modes, groups = T["mode"].to_numpy(), T.group.to_numpy()
    np.savez(FLAGS, flags=flags, modes=modes, groups=groups, cfg=np.array([f"{k}|{r:g}|{o}" for k, r, o in cfgs]))
    Wm = draws_matrix(groups)
    pt, dr = mode_shares(flags, modes, Wm)
    allpt = flags.mean(1)
    alld = np.einsum("bn,cn->cb", Wm, flags.astype(float)) / Wm.sum(1)[None]
    E = PC.PEntries("b2", "results/tables/p_b2_table.csv")
    rows = []
    for c, (k, rg, odr) in enumerate(cfgs):
        row = dict(part=k, range_g=rg, odr_hz=odr, all_share=allpt[c], all_lo=float(np.quantile(alld[c], 0.025)))
        for j, m in enumerate(PC.MODES):
            row[f"{m}_share"], row[f"{m}_lo"], row[f"{m}_hi"] = float(pt[c, j]), float(np.quantile(dr[c, :, j], 0.025)), float(np.quantile(dr[c, :, j], 0.975))
        rows.append(row)
    R = pd.DataFrame(rows)
    R.to_csv(C.TABLES / "p_b2_table.csv", index=False)
    for m in PC.MODES:
        n = int((modes == m).sum())
        ok = R[R[f"{m}_lo"] >= 0.80].sort_values(["range_g", "odr_hz", "part"])
        E.add(f"{m}.n_records", n, "records")
        E.add(f"{m}.n_configs_meeting", int(len(ok)), "configurations", "lower end of the 95% grouped interval of the share within +-10% at least 0.80 (plain estimate)")
        if len(ok):
            r = ok.iloc[0]
            E.add(f"{m}.smallest.config", f"{r.part} +-{r.range_g:g} g at {int(r.odr_hz)} Hz", "config", "smallest range, then lowest rate, then part name, among the configurations meeting the rule")
            E.ci(f"{m}.smallest.share", (r[f"{m}_share"], r[f"{m}_lo"], r[f"{m}_hi"]), "fraction", d=4)
        else:
            E.not_run(f"{m}.smallest.config", "config", "no configuration of the 8 parts reaches a lower interval end of 0.80 for this mode")
    ok = R[R.all_lo >= 0.80].sort_values(["range_g", "odr_hz", "part"])
    E.add("all_modes_pooled.n_configs_meeting", int(len(ok)), "configurations", "pooled records, observed mode mix (not a deployment mix)")
    E.flush()
    print(R.round(3).head(), len(R))


def requirement(mix: dict, required: float = 0.80, rule: str = "both") -> pd.DataFrame:
    """Configurations that meet ``required`` as the lower end of the 95% grouped interval, for every mode with weight > 0 ('per_mode'), and for the weighted mix ('mix')."""
    z = np.load(FLAGS, allow_pickle=True)
    flags, modes, groups, cfg = z["flags"], z["modes"], z["groups"], z["cfg"]
    w = np.array([mix.get(m, 0.0) for m in PC.MODES], float)
    w = w / w.sum()
    Wm = draws_matrix(groups)
    pt, dr = mode_shares(flags, modes, Wm)
    mixpt = pt @ w
    mixlo = np.quantile(dr @ w, 0.025, axis=1)
    rows = []
    for c, name in enumerate(cfg):
        part, rg, odr = name.split("|")
        pm_ok = all(np.quantile(dr[c, :, j], 0.025) >= required for j, m in enumerate(PC.MODES) if w[j] > 0)
        rows.append(dict(part=part, range_g=float(rg), odr_hz=int(odr), mix_share=float(mixpt[c]), mix_lower=float(mixlo[c]), meets_mix=bool(mixlo[c] >= required), meets_every_mode=bool(pm_ok)))
    R = pd.DataFrame(rows).sort_values(["range_g", "odr_hz", "part"]).reset_index(drop=True)
    return R


if __name__ == "__main__":
    build()
