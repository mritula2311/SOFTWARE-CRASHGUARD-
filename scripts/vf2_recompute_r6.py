"""D1.2: recompute the round-6 numbers the paper quotes and compare them with the stored keys of results/results.json.

    PYTHONPATH=src python scripts/vf2_recompute_r6.py [root]

Run inside the fresh clone of round6-v1. Nothing here writes results.json or a frozen file: the held-out analyses are repeated with the frozen parameters
(checked by hash through ``r6_common.check_frozen``), no choice is made, and the output goes to results/tables/vf2_recompute_r6.json.
Parts: A (R6-1 cells from the stored ns-3 run files), B (R6-2 held-out analysis), C (R6-5 and R6-7 bounds from the formulas, with an independent time-on-air function).
Part D (the footprint) is compared by scripts/vf2_compare_prefix.py after the build script was run again.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from crashguard import r6_common as C6  # noqa: E402

R = {e["name"]: e["value"] for e in json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))}
ROWS: list[dict] = []


def frozen_params(name: str) -> dict:
    """The frozen parameters of round 6 after checking the hashes of the frozen files and of the parameters (the check of ``r6_common.check_frozen`` without its run-once guard)."""
    d = json.loads(C6.FROZEN.read_text(encoding="utf-8"))[name]
    bad = [f for f, h in d["files"].items() if C6.sha256_file(ROOT / f) != h]
    assert not bad, f"frozen files changed: {bad}"
    assert C6.sha256_json(d["params"]) == d["params_sha256"], "frozen parameters changed"
    return d["params"]



def row(group: str, name: str, stored, new, tol: float = 5e-7) -> None:
    ok = (stored == new) if isinstance(stored, (str, bool)) or isinstance(new, (str, bool)) else (abs(float(stored) - float(new)) <= tol)
    ROWS.append(dict(group=group, name=name, stored=stored, recomputed=new, match=bool(ok)))


def part_a() -> None:
    from crashguard import r6_micro as M

    prm = frozen_params("r1")
    pend = prm["pend_s"]
    ev = M.event_table()
    rng = np.random.default_rng(M.SEED)
    for sf in M.SFS:
        for st in M.SETTINGS:
            for p in M.LOSSES:
                fs = [M.fname_new(M.R3OUT, sf, st, p, "r3s", s) for s in M.HELD_SEEDS]
                ft = [M.fname_new(M.R3OUT, sf, st, p, "r3t", s) for s in M.HELD_SEEDS]
                fm = [M.fname_new(M.OUT, sf, st, p, "r6m", s, pend) for s in M.HELD_SEEDS]
                runs = M.cell_runs(fs, ft, fm, ev)
                c = M.boot_cell(runs, rng)
                cn = f"sf{sf}.{st}.p{p:g}"
                k = f"r6.r1.ns3.{cn}."
                row("R6-1", k + "n_runs", R[k + "n_runs"], len(runs))
                row("R6-1", k + "extra_air_ratio (micro vs single-stage)", R[k + "extra_air_ratio"], round(c["ratio_s_pt"], 6))
                row("R6-1", k + "extra_air_ratio_hi", R[k + "extra_air_ratio_hi"], round(M.criterion_a(c)[1], 6))
                row("R6-1", k + "air_over_r3", R[k + "air_over_r3"], round(c["ratio_t_pt"], 6))
                row("R6-1", k + "air_per_delivered_over_r3", R[k + "air_per_delivered_over_r3"], round(c["ratio_pd_pt"], 6))
                row("R6-1", k + "air_per_delivered_over_r3_hi", R[k + "air_per_delivered_over_r3_hi"], round(float(np.quantile(c["ratio_pd"], 0.975)), 6))
                row("R6-1", k + "delivery_r3", R[k + "delivery_r3"], round(c["deliv_t"], 6))
                row("R6-1", k + "delivery_micro", R[k + "delivery_micro"], round(c["deliv_m"], 6))
                row("R6-1", k + "delivery_diff", R[k + "delivery_diff"], round(c["dd_pt"], 6))
                row("R6-1", k + "delivery_diff_lo", R[k + "delivery_diff_lo"], round(M.criterion_b(c)[1], 6))


def part_b() -> None:
    from crashguard import r6_seq as S

    prm = frozen_params("r2")
    D = S.load()
    edges, tables = S.fit_tables(D, prm)
    Lt = S.running_llr(D["St"], edges, tables)
    half = np.array([C6.half6(e) for e in D["ids_te"]]) == 1
    pos = (D["yt"] == 1)[half]
    alarm_s, t_s = S.seq_decisions(Lt[half], prm["A"], prm["B"])
    alarm_f, t_f = D["alarm_ft"][half], D["tt_f"][half]
    prov_f, prov_s = alarm_f & (t_f < S.LENGTHS[-1]), alarm_s & (t_s < S.LENGTHS[-1])
    fa = D["full_alarm_t"][half]
    st = S.boot_stats(t_f, t_s, prov_f, prov_s, pos, fa)
    sel_f, sel_s = prov_f & pos, prov_s & pos
    new = {"held.n_events": int(half.sum()), "held.n_crash": int(pos.sum()), "held.mean_time_fixed_ms": float(t_f[sel_f].mean()), "held.mean_time_seq_ms": float(t_s[sel_s].mean()),
           "held.median_time_fixed_ms": float(np.median(t_f[sel_f])), "held.median_time_seq_ms": float(np.median(t_s[sel_s])), "held.retraction_fixed": S.retraction_share(prov_f, fa),
           "held.retraction_seq": S.retraction_share(prov_s, fa)}
    new.update({f"hR6_2.{k}": v for k, v in st.items()})
    for k, v in new.items():
        row("R6-2", "r6.r2." + k, R["r6.r2." + k], round(v, 6) if isinstance(v, float) else v)


def at(n: int, sf: int) -> float:
    """Semtech time on air (s): 125 kHz, coding rate 4/5, explicit header, CRC on, 8 preamble symbols, low-data-rate optimisation for SF11 and SF12. Independent of crashguard.lora."""
    de = 1 if sf >= 11 else 0
    tsym = (2 ** sf) / 125000.0
    npay = 8 + max(math.ceil((8 * n - 4 * sf + 28 + 16 - 0) / (4 * (sf - 2 * de))) * 5, 0)
    return (8 + 4.25 + npay) * tsym


def part_c() -> None:
    rho = R["ar.r3.a1.retraction_share"]
    row("R6-5", "r6.b.input.retraction_share", R["r6.b.input.retraction_share"], round(rho, 6))
    m_r = R["r6.b.input.transmissions_per_retracted"]  # from the stored ns-3 outputs; recomputed in part D of the report from the raw files
    frames = {"micro": 7, "flash": 14, "ack": 26, "alert": 97}
    allowance = 36.0
    for sf in (7, 8, 9, 10, 11, 12):
        a = {k: at(n, sf) for k, n in frames.items()}
        for k, v in a.items():
            row("R6-5", f"r6.b.air.sf{sf}.{k}_s", R[f"r6.b.air.sf{sf}.{k}_s"], round(v, 6), tol=2e-6)
        tcyc = a["alert"] + 0.2 + a["ack"]
        for d in (10, 30):
            row("R6-5", f"r6.b.attempts.sf{sf}.d{d}.time_limited", R[f"r6.b.attempts.sf{sf}.d{d}.time_limited"], int(math.floor((d - a["alert"]) / tcyc)) + 1)
        for nm in ("alert", "flash", "micro"):
            row("R6-5", f"r6.b.attempts.sf{sf}.{nm}.per_hour_allowance", R[f"r6.b.attempts.sf{sf}.{nm}.per_hour_allowance"], int(math.floor(allowance / a[nm])))
        lb = a["flash"] / a["alert"] * (1.0 + rho * (m_r - 1.0) / (1.0 - rho))
        row("R6-5", f"r6.b.extra.sf{sf}.r3_lower_bound", R[f"r6.b.extra.sf{sf}.r3_lower_bound"], round(lb, 6), tol=2e-6)
        num = (1 - rho) * (a["flash"] + a["micro"]) + rho * (a["flash"] + (m_r - 1) * a["micro"])
        den = (1 - rho) * a["alert"]
        row("R6-5", f"r6.b.extra.sf{sf}.micro_lower_bound", R[f"r6.b.extra.sf{sf}.micro_lower_bound"], round(num / den - 1.0, 6), tol=2e-6)
        r3_tot = (1 - rho) * (a["flash"] + a["alert"]) + rho * m_r * a["flash"]
        row("R6-5", f"r6.b.extra.sf{sf}.micro_over_r3", R[f"r6.b.extra.sf{sf}.micro_over_r3"], round(num / r3_tot, 6), tol=2e-6)
    fr = allowance / at(7, 7)
    row("R6-7", "r6.b.forge.max_frames_per_hour_sf7", R["r6.b.forge.max_frames_per_hour_sf7"], round(fr, 6), tol=2e-4)
    for tb in (4, 5, 6, 8):
        p = 2.0 ** (-8 * tb)
        row("R6-7", f"r6.b.forge.tag{tb}.p_per_year_at_ceiling", R[f"r6.b.forge.tag{tb}.p_per_year_at_ceiling"], round(min(1.0, p * fr * 8766), 6), tol=1e-6)
        row("R6-7", f"r6.b.forge.tag{tb}.expected_years", R[f"r6.b.forge.tag{tb}.expected_years"], round(1.0 / (p * fr * 8766), 6), tol=max(1e-6, 1e-4 * R[f"r6.b.forge.tag{tb}.expected_years"]))
    # R6-7 greedy proposition: attempts that fit in the deadline, per-hour bound; checked above. The SF rule crossing:
    cross = [sf for sf in (7, 8, 9, 10, 11, 12) if R[f"r6.b.extra.sf{sf}.r3_lower_bound"] >= 0.40]
    row("R6-7", "r6.b.rule.sf_where_lower_bound_reaches_40pct", R["r6.b.rule.sf_where_lower_bound_reaches_40pct"], cross[0] if cross else 0)


def main() -> None:
    for f in (part_a, part_b, part_c):
        f()
    out = ROOT / "results" / "tables" / "vf2_recompute_r6.json"
    out.write_text(json.dumps(ROWS, indent=1), encoding="utf-8")
    bad = [r for r in ROWS if not r["match"]]
    by = {}
    for r in ROWS:
        by.setdefault(r["group"], [0, 0])
        by[r["group"]][0] += 1
        by[r["group"]][1] += int(r["match"])
    print("rows", len(ROWS), "mismatches", len(bad), by)
    for r in bad[:40]:
        print("MISMATCH", r)


if __name__ == "__main__":
    main()
