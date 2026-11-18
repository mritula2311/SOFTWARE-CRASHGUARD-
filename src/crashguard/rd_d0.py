"""D0: diagnosis of the failed protocol and architecture algorithms (docs/02_preregistration/PREREGISTRATION_V12.md). Keys ``rd.d0.*``.

Data role DIAGNOSIS: only the existing grids (DESIGN_A seed 16000 and HELD_A seed 18000 of ``pa_sim``) and the existing logs (``data/processed/pa_design.pkl``, ``pa_held.pkl``, ``results/results.json``).
The old held-out logs are read here to explain the earlier failures; nothing computed here is used to tune a redesign (the redesigns are tuned on a new grid, ``rd_eval``). The only re-runs are of cells of those
existing grids with per-alert counters switched on (``world_sim.simulate(..., diag=[])``), checked against the stored logs.

    python -m crashguard.rd_d0
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binom

from crashguard import config as C
from crashguard import fin_g as G
from crashguard import fin_sim as FS
from crashguard import pa_sim as PA
from crashguard import world_sim as W
from crashguard.rd_common import Rec, paired_event_test

SRC = "src/crashguard/rd_d0.py"
OUT = C.PROCESSED
METRICS = ("reach10_rx_critical", "reach30_rx_severe", "reach10_critical", "node_air_share")


def load(grid: str) -> pd.DataFrame:
    return pd.read_pickle(OUT / f"pa_{grid}.pkl")


def pair_by_cell(R: pd.DataFrame, a: str, b: str, metric: str) -> pd.DataFrame:
    """b minus a per cell, paired by simulated hour; paired bootstrap interval over hours."""
    rows = []
    for cell, g in R[R.pol.isin([a, b])].groupby("cell"):
        pa_ = g[g.pol == a].sort_values("hour")[metric].to_numpy(float)
        pb_ = g[g.pol == b].sort_values("hour")[metric].to_numpy(float)
        m = ~(np.isnan(pa_) | np.isnan(pb_))
        t = paired_event_test(pb_[m] - pa_[m], 0.0)
        r0 = g.iloc[0]
        rows.append(dict(cell=cell, b=int(r0.b), p=float(r0.p), sf=int(r0.sf), duty=float(r0.duty), a_mean=float(pa_[m].mean()), b_mean=float(pb_[m].mean()), diff=t["pt"], lo=t["lo"], hi=t["hi"]))
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------ A. UA-SCT against the severity table
def part_a(rec: Rec, doc: list[str]) -> None:
    doc.append("## 1. UA-SCT (P4) against the severity table (P1)\n")
    doc.append("Metric: share of Critical alerts that reach the base within 10 s (`reach10_rx_critical`) and of Severe alerts within 30 s (`reach30_rx_severe`); per cell, paired by simulated hour (30 hours per cell); 95% paired bootstrap interval over hours. "
               "Steady = no simultaneous burst (b = 1); burst = 20 (design) or 30 (held-out) cars crashing within 10 s.\n")
    for grid in ("design", "held"):
        R = load(grid)
        for met in ("reach10_rx_critical", "reach30_rx_severe"):
            d = pair_by_cell(R, "P1", "P4", met)
            e = pair_by_cell(R, "P1", "P1e", met)
            for reg, mask in (("steady", d.b == 1), ("burst", d.b > 1)):
                dd, ee = d[mask], e[mask]
                lose = int(((dd.hi < 0)).sum())  # interval wholly below zero
                gain = int(((dd.lo > 0)).sum())
                rec.add(f"a.{grid}.{reg}.{met}.p4_minus_p1.mean", float(dd["diff"].mean()), "fraction", f"mean over {len(dd)} cells of the per-cell paired difference UA-SCT minus severity table, {grid} grid")
                rec.add(f"a.{grid}.{reg}.{met}.p4_minus_p1.cells_lose", lose, "cells", "cells where the 95% interval is wholly below zero")
                rec.add(f"a.{grid}.{reg}.{met}.p4_minus_p1.cells_gain", gain, "cells", "cells where the 95% interval is wholly above zero")
                rec.add(f"a.{grid}.{reg}.{met}.p4_minus_p1.cells", int(len(dd)), "cells")
                rec.add(f"a.{grid}.{reg}.{met}.lowered_minus_p1.mean", float(ee["diff"].mean()), "fraction", "mean over cells of lowered-threshold table (P1e) minus P1")
            if met == "reach10_rx_critical":
                tab = d.merge(e[["cell", "diff"]].rename(columns={"diff": "p1e_minus_p1"}), on="cell")
                tab = tab.rename(columns={"diff": "p4_minus_p1"})
                doc.append(f"\n### {grid} grid, per cell (Critical within 10 s)\n")
                doc.append("| cell | P1 | P4 | P4 minus P1 [95%] | P1e minus P1 |\n|---|---|---|---|---|")
                for _, r in tab.iterrows():
                    doc.append(f"| {r.cell} | {r.a_mean:.3f} | {r.b_mean:.3f} | {r.p4_minus_p1:+.3f} [{r.lo:+.3f}, {r.hi:+.3f}] | {r.p1e_minus_p1:+.3f} |")
                doc.append("")
    # single-car loss sweep from the stored results (t4)
    res = {e["name"]: e["value"] for e in json.loads(open("results/results.json", encoding="utf-8").read()) if e["name"].startswith("t4.b.")}
    doc.append("\n### Single car, 20 alerts per hour, SF7, no collisions (stored `t4.b.*`; Critical within 10 s)\n")
    doc.append("| loss per direction | P0 fixed-3 | P1 severity table | P2 SCT (5 s spacing) | P2 quick (0.3 s spacing) |\n|---|---|---|---|---|")
    for loss in (10, 30, 60):
        v = [res[f"t4.b.loss{loss}.{p}.reach10_critical"] for p in ("P0", "P1", "P2", "P2_quick")]
        doc.append(f"| {loss}% | " + " | ".join(f"{x:.3f}" for x in v) + " |")
        for p, x in zip(("P0", "P1", "P2", "P2_quick"), v):
            rec.add(f"a.single.loss{loss}.{p}.reach10_critical", float(x), "fraction", "stored t4 result (MEASURED earlier, re-read here)", "SIMULATED")
    an = {f"loss{loss}": (res[f"t4.b.analytic.loss{loss}.sct_chances"], res[f"t4.b.analytic.loss{loss}.table_tries"]) for loss in (10, 30, 60)}
    doc.append("\nTries that fit before the 10 s deadline (ANALYTICAL, `t4.b.analytic.*`): SCT with 5 s spacing gets "
               + ", ".join(f"{v[0]} chances at {k}" for k, v in an.items()) + f"; the table, after its 5 s hold, gets {an['loss60'][1]} tries at 60% loss.\n")
    for k, v in an.items():
        rec.add(f"a.analytic.{k}.sct_chances", int(v[0]), "chances", "t4 analytical count of flash and alert transmissions that fit before 10 s with 5 s spacing", "ANALYTICAL")
        rec.add(f"a.analytic.{k}.table_tries", int(v[1]), "tries", "t4 analytical count of table tries that fit before 10 s after the 5 s hold", "ANALYTICAL")


def part_a_sweep(rec: Rec, doc: list[str], hours: int = 30) -> None:
    """Mechanism sweep on the existing DESIGN grid (DIAGNOSIS role): SCT with different retry spacings and spreading-factor raise, point classes, no fast-path cap. Not a tuning of any redesign."""
    t = FS.tuned()
    pools = PA.pools_real()
    variants = {"P1": ("P1", {}), "sct_spacing_5s": ("P2", {}), "sct_spacing_2.5s": ("P2", dict(spacing_crit=2.5, spacing_sev=2.5)), "sct_spacing_1s": ("P2", dict(spacing_crit=1.0, spacing_sev=1.0)),
                "sct_spacing_0.3s": ("P2", dict(spacing_crit=0.3, spacing_sev=0.3)), "sct_spacing_0.3s_no_sf_raise": ("P2", dict(spacing_crit=0.3, spacing_sev=0.3, sf_raise=False))}
    jobs = []
    for cell in PA.cells(PA.DESIGN_A):
        for nm, (pol, over) in variants.items():
            for h in range(hours):
                c = G.cfg_for(pol, cell, PA.DESIGN_A["seed"], h, pools, t, f"g_{cell['name']}", None, over)
                jobs.append((c, dict(cell=cell["name"], p=cell["p"], b=cell["b"], duty=cell["duty"], sf=cell["sf"], pol=nm, hour=h)))
    R = FS.run_jobs(jobs)
    R["regime"] = np.where(R.b > 1, "burst", "steady")
    doc.append("\n### Mechanism sweep on the existing design grid (30 hours per cell, point classes, no fast-path cap)\n")
    doc.append("Mean over the 16 cells of each regime and loss level. Critical within 10 s at the base; Severe within 30 s; node airtime share of the allowance; collided transmissions per hour.\n")
    doc.append("| regime | loss | variant | Critical 10 s | Severe 30 s | airtime share | collided tx per hour |\n|---|---|---|---|---|---|---|")
    g = R.groupby(["regime", "p", "pol"])[["reach10_rx_critical", "reach30_rx_severe", "node_air_share", "al_collided"]].mean().reset_index()
    for _, r in g.iterrows():
        doc.append(f"| {r.regime} | {r.p:.1f} | {r.pol} | {r.reach10_rx_critical:.3f} | {r.reach30_rx_severe:.3f} | {r.node_air_share:.3f} | {r.al_collided:.1f} |")
        rec.add(f"a.sweep.{r.regime}.p{int(r.p * 100)}.{r.pol}.reach10_rx_critical", float(r.reach10_rx_critical), "fraction", "existing DESIGN grid, 30 hours per cell, mean over cells")
        rec.add(f"a.sweep.{r.regime}.p{int(r.p * 100)}.{r.pol}.reach30_rx_severe", float(r.reach30_rx_severe), "fraction", "existing DESIGN grid")
    R.to_pickle(OUT / "rd_d0_sweep.pkl")


# ------------------------------------------------------------------------------------------------ B. OS-DR false suppression
def part_b(rec: Rec, doc: list[str]) -> None:
    R = load("held")
    d = pair_by_cell(R, "P4+lbt", "osdr", "reach10_critical")
    lose = d[d["diff"] < -0.02]
    doc.append("## 2. OS-DR against the best earlier policy (P4 with listen-before-talk)\n")
    doc.append("Metric of H-A1: Critical reach within 10 s as seen by the sender (`reach10_critical`), held-out grid (32 cells), paired by hour. A cell is losing when the point difference is below -0.02.\n")
    rec.add("b.cells", int(len(d)), "cells", "held-out grid")
    rec.add("b.cells_lose2", int(len(lose)), "cells", "OS-DR minus P4+lbt below -0.02 (the earlier count: 8)")
    rec.add("b.cells_gain5", int((d["diff"] >= 0.05).sum()), "cells", "OS-DR minus P4+lbt at least +0.05")
    doc.append(f"Cells with a loss of more than 2 points: **{len(lose)} of {len(d)}**; cells with a gain of at least 5 points: {int((d['diff'] >= 0.05).sum())}.\n")
    doc.append("| cell | burst | P4+lbt | OS-DR | difference [95%] | suppressions per hour | of which on alerts the base never received | share false |\n|---|---|---|---|---|---|---|---|")
    tot_s = tot_u = 0.0
    for _, r in lose.iterrows():
        g = R[(R.cell == r.cell) & (R.pol == "osdr")]
        s, u = float(g.suppressed.mean()), float(g.suppressed_unrx.mean())
        tot_s += s
        tot_u += u
        doc.append(f"| {r.cell} | {'yes' if r.b > 1 else 'no'} | {r.a_mean:.3f} | {r.b_mean:.3f} | {r['diff']:+.3f} [{r.lo:+.3f}, {r.hi:+.3f}] | {s:.1f} | {u:.1f} | {(u / s if s else float('nan')):.2f} |")
        rec.add(f"b.lose.{r.cell}.diff", float(r["diff"]), "fraction", "OS-DR minus P4+lbt, Critical reach within 10 s")
        rec.add(f"b.lose.{r.cell}.suppressed_per_hour", s, "events", "alerts whose retries were stopped by an overheard ACK addressed to another car")
        rec.add(f"b.lose.{r.cell}.suppressed_unrx_per_hour", u, "events", "of those, alerts the base had never received")
    allb = R[(R.pol == "osdr") & (R.b > 1)]
    sup, unrx = float(allb.suppressed.sum()), float(allb.suppressed_unrx.sum())
    rec.add("b.false_suppression_share_burst_cells", unrx / sup if sup else float("nan"), "fraction", "all 16 held-out burst cells: suppressed alerts the base never received over all suppressed alerts")
    rec.add("b.false_suppression_share_losing_cells", tot_u / tot_s if tot_s else float("nan"), "fraction", "losing cells only")
    nb = int((lose.b == 1).sum())
    rec.add("b.losing_cells_without_burst", nb, "cells", "losing cells with no suppression possible (no event cell): the loss there comes from the geometric retry gap of OS-DR, not from suppression")
    doc.append(f"\nAcross all 16 burst cells, **{unrx / sup:.2f}** of suppressed alerts had never been received by the base (false suppression); {nb} of the {len(lose)} losing cells have no burst, so no suppression happened there (its difference is not distinguishable from zero).\n")
    doc.append("**Trigger (from the code, `world_sim.py`, event `ack_heard`):** a vehicle decodes any gateway ACK that is addressed to another vehicle of the same event cell and then removes its own pending Severe and Critical alerts of that cell. The ACK names the other vehicle, not this one, "
               "so it proves nothing about this vehicle's own alert. The ACK is also event-level under one shared key, which is the forgery path found in H-A3.\n")
    doc.append("**Mechanism:** suppression is based on a proxy (another vehicle's ACK) for the state that matters (this vehicle's alert reached the base). In a burst, the early ACKs are heard by everybody, so vehicles whose alerts collided stop and are never delivered. "
               "One losing cell has no burst; there OS-DR never suppresses, its interval reaches zero, and with about 100 Critical events per cell a 30-hour estimate of this size is compatible with noise, so no mechanism is claimed for it.\n")


# ------------------------------------------------------------------------------------------------ C. GS-CA failure causes
def classify(alerts: list[dict], deadline: float = 10.0) -> dict:
    n = dict(n=0, ok=0, late=0, not_sent_duty=0, not_sent_other=0, collided=0, deaf=0, link=0)
    tx = dict(ok=0, collided=0, deaf=0, lost=0)
    for a in alerts:
        if a["kind"] != "crash" or a["true"] != 3:
            continue
        for k in tx:
            tx[k] += a[f"n_{k}"]
        n["n"] += 1
        rx = None if a["t_rx"] is None else a["t_rx"] - a["arrival"]
        if rx is not None and rx <= deadline:
            n["ok"] += 1
        elif rx is not None:
            n["late"] += 1
        elif a["first_tx"] is None or a["first_tx"] - a["arrival"] > deadline:
            n["not_sent_duty" if a["n_duty_wait"] > 0 else "not_sent_other"] += 1
        elif a["n_collided"] >= max(a["n_deaf"], a["n_lost"], 1) and a["n_collided"] >= a["n_deaf"]:
            n["collided"] += 1
        elif a["n_deaf"] > a["n_lost"]:
            n["deaf"] += 1
        else:
            n["link"] += 1
    return dict(alerts=n, tx=tx)


def part_c(rec: Rec, doc: list[str], hours: int = 30) -> None:
    t = FS.tuned()
    pools = PA.pools_real()
    des = json.loads((OUT / "pa_design.json").read_text(encoding="utf-8"))
    specs = PA.held_specs(des)
    specs = {"P4+lbt": dict(kind="P4+lbt"), "gsca": specs["gsca"], "osdr": specs["osdr"], "P1": dict(kind="P1")}
    Rh = load("held")
    cells = [c for c in PA.cells(PA.HELD_A) if c["b"] > 1]
    tot = {k: dict(alerts={}, tx={}) for k in specs}
    mism = 0
    for name, spec in specs.items():
        agg_a: dict = {}
        agg_t: dict = {}
        for cell in cells:
            w = PA.spec_world(spec, cell)
            for h in range(hours):
                diag: list[dict] = []
                c = G.cfg_for(PA.spec_pol(spec), cell, PA.HELD_A["seed"], h, pools, t, f"g_{cell['name']}", w)
                out = W.simulate(c, diag=diag)
                ref = Rh[(Rh.cell == cell["name"]) & (Rh.pol == name) & (Rh.hour == h)]
                if len(ref) and abs(float(ref.iloc[0].reach10_critical) - out["reach10_critical"]) > 1e-12:
                    mism += 1
                r = classify(diag)
                for k, v in r["alerts"].items():
                    agg_a[k] = agg_a.get(k, 0) + v
                for k, v in r["tx"].items():
                    agg_t[k] = agg_t.get(k, 0) + v
        tot[name] = dict(alerts=agg_a, tx=agg_t)
    rec.add("c.rerun_mismatches", mism, "runs", "re-runs of the stored held-out burst cells whose reach10_critical differs from the stored log (must be 0)")
    doc.append("## 3. GS-CA in the 16 held-out burst cells: collisions, link loss or duty-cycle blocking\n")
    doc.append("Re-run of the 16 held-out burst cells (30 hours each) with per-alert counters on; the re-run reproduces the stored `reach10_critical` of every run "
               f"(mismatches: {mism}). Critical alerts only. An alert is a failure when it does not reach the base within 10 s.\n")
    doc.append("**Failed Critical alerts by primary cause** (the transmission outcome that dominates the alert; 'not sent by 10 s' = still waiting for its slot, hold, retry gap or duty-cycle room):\n")
    doc.append("| policy | alerts | reached in 10 s | reached late | collided | gateway deaf (sending an ACK) | link loss | not sent by 10 s (duty wait) | not sent by 10 s (other) |\n|---|---|---|---|---|---|---|---|---|")
    for name, v in tot.items():
        a = v["alerts"]
        doc.append(f"| {name} | {a['n']} | {a['ok'] / a['n']:.3f} | {a['late'] / a['n']:.3f} | {a['collided'] / a['n']:.3f} | {a['deaf'] / a['n']:.3f} | {a['link'] / a['n']:.3f} | {a['not_sent_duty'] / a['n']:.3f} | {a['not_sent_other'] / a['n']:.3f} |")
        for k, x in a.items():
            if k != "n":
                rec.add(f"c.{name}.alerts.{k}_share", x / a["n"], "fraction", "share of all Critical alerts in the 16 held-out burst cells")
        rec.add(f"c.{name}.alerts.n", int(a["n"]), "alerts", "Critical alerts in the 16 held-out burst cells, 30 hours")
    doc.append("\n**Outcome of every transmission of a Critical alert:**\n")
    doc.append("| policy | transmissions | decoded | collided | gateway deaf | link loss |\n|---|---|---|---|---|---|")
    for name, v in tot.items():
        x = v["tx"]
        s = sum(x.values())
        doc.append(f"| {name} | {s} | {x['ok'] / s:.3f} | {x['collided'] / s:.3f} | {x['deaf'] / s:.3f} | {x['lost'] / s:.3f} |")
        for k, y in x.items():
            rec.add(f"c.{name}.tx.{k}_share", y / s, "fraction", "share of transmissions of Critical alerts")
    g = tot["gsca"]
    fail = g["alerts"]["n"] - g["alerts"]["ok"]
    col = (g["alerts"]["collided"] + g["alerts"]["deaf"]) / max(fail, 1)
    rec.add("c.gsca.collision_or_deaf_share_of_failures", col, "fraction", "GS-CA: failures whose dominant cause is a collision or a deaf gateway")
    keep = col >= 0.5
    rec.add("c.gsca.collisions_dominate", int(keep), "flag", "1 if collisions or gateway-deaf periods are at least half of the failed Critical alerts (the condition for redesigning GS-CA in D3)")
    doc.append(f"\nFor GS-CA, **{col:.2f}** of the failed Critical alerts failed mainly through a collision or a deaf gateway. "
               + ("Collisions are the main cause, so a redesign of the slotted access can still help (D3 is kept).\n" if keep else "Collisions are not the main cause, so GS-CA cannot help and is dropped (recorded in DECISIONS.md).\n"))
    txn = {k: sum(v["tx"].values()) / v["alerts"]["n"] for k, v in tot.items()}
    for k, x in txn.items():
        rec.add(f"c.{k}.tx_per_critical_alert", x, "transmissions", "transmissions (flash and alert) per Critical alert in the 16 held-out burst cells")
    doc.append(f"\nTransmissions per Critical alert: GS-CA {txn['gsca']:.1f}, P4+lbt {txn['P4+lbt']:.1f}, OS-DR {txn['osdr']:.1f}, P1 {txn['P1']:.1f}. "
               "GS-CA is built on the severity-table retry rule (immediate retries, up to 12), so it puts about "
               f"{txn['gsca'] / txn['P4+lbt']:.1f} times as many frames on the channel as P4+lbt; its collided share of transmissions is {tot['gsca']['tx']['collided'] / sum(tot['gsca']['tx'].values()):.2f} against "
               f"{tot['P4+lbt']['tx']['collided'] / sum(tot['P4+lbt']['tx'].values()):.2f}. **Mechanism (stated from these counts; the slot-count explanation, K = 4 slots for 30 vehicles, is inferred and was not isolated):** "
               "slotting did not reduce the number of competing frames, and the design-grid choice of 4 slots leaves several vehicles per slot.\n")


# ------------------------------------------------------------------------------------------------ D. power of the R2 sign test
def part_d(rec: Rec, doc: list[str]) -> None:
    n, k_obs = 16, 10
    p_obs = float(binom.sf(k_obs - 1, n, 0.5))
    kc = next(k for k in range(n + 1) if binom.sf(k - 1, n, 0.5) <= 0.05)
    doc.append("## 4. R2 frame size: power of the 16-cell sign test (ANALYTICAL)\n")
    doc.append(f"The effect met the 5-point threshold in {k_obs} of {n} held-out cells; the exact one-sided sign test gives p = {p_obs:.3f}. At level 0.05 the test needs at least {kc} of {n} cells. "
               "Power if each cell independently shows the effect with probability q:\n")
    doc.append("| q | power of the sign test at 0.05 | power at 0.05 with 10 or more cells needed (this was the observed count) |\n|---|---|---|")
    rec.add("d.sign_test.cells", n, "cells", "R2 held-out burst cells", "ANALYTICAL")
    rec.add("d.sign_test.observed_cells", k_obs, "cells", "cells with a gain of at least 5 points", "ANALYTICAL")
    rec.add("d.sign_test.p_observed", p_obs, "p", "exact one-sided binomial P(X >= 10; 16, 0.5)", "ANALYTICAL")
    rec.add("d.sign_test.critical_count", kc, "cells", "smallest count with p <= 0.05", "ANALYTICAL")
    for q in (0.625, 0.75, 0.9, 1.0):
        pw = float(binom.sf(kc - 1, n, q))
        rec.add(f"d.sign_test.power_q{int(q * 1000)}", pw, "probability", f"power of the 16-cell sign test at 0.05 when each cell shows the effect with probability {q}", "ANALYTICAL")
        doc.append(f"| {q} | {pw:.3f} | |")
    doc.append("\nThe observed rate of 10 of 16 (q = 0.625) gives a power of about "
               f"{binom.sf(kc - 1, n, 0.625):.2f}: the test would miss an effect of this size most of the time. The 16 cells are not independent draws of an effect (they share the same 30 simulated hours per grid), "
               "and a sign test discards the size of the effect. D4 therefore uses a paired bootstrap over events, which uses every event.\n")


# ------------------------------------------------------------------------------------------------ E. synthetic generators
def part_e(rec: Rec, doc: list[str]) -> None:
    doc.append("## 5. Synthetic generators\n")
    doc.append("No generator-v3 run and no `GEN_DIAGNOSIS.md` exist in this repository, and its G1 step is not defined in any file here, so the G1 step is NOT_RUN. The earlier diagnosis is in `docs/03_results/PH_INTEGRITY_REPORT.md`: "
               "the physics generators PH-A and PH-B and the refit family generator fail the realism gate in every mode, and the VZCrash-style surrogate fails the discriminator gate (AUC 0.995). "
               "D5 consequence: no generator passed for any mode, so no synthetic data is used in this round.\n")
    rec.add("e.g1_step", "NOT_RUN", "status", "no generator-v3 run or G1 definition exists in the repository; earlier diagnosis in docs/03_results/PH_INTEGRITY_REPORT.md", "NOT_RUN")
    rec.add("e.synthetic_data_used", 0, "flag", "no generator passed the realism gate in any mode (PH_INTEGRITY_REPORT.md); none is used in the redesign round", "ANALYTICAL")


def write_docs(doc_parts: dict[str, list[str]]) -> None:
    hdr = lambda name, scope: (f"# {name}\n\n<!-- header:start -->\n| Field | Value |\n|---|---|\n| Status | current |\n| Date | 2026-11-14 |\n| Owner | Mritula S |\n| Scope | {scope} |\n"  # noqa: E731
                               "| Evidence labels used | SIMULATED, ANALYTICAL, NOT_RUN |\n| Abbreviations | ACK = acknowledgement frame; GS-CA = GPS-slotted critical alerts; LBT = listen before talk; OS-DR = overhear-and-suppress retries with deadlines; SF = spreading factor; "
                               "SCT = severity-classified transmission; UA-SCT = uncertainty-aware SCT |\n<!-- header:end -->\n\n")
    for key, (title, scope) in {"uasct": ("Diagnosis: UA-SCT against the severity table", "Where UA-SCT loses and why (generated by `crashguard.rd_d0`, data role DIAGNOSIS)."),
                                 "osdr": ("Diagnosis: OS-DR false suppression", "Which losing cells involve suppression of an undelivered alert, and what triggers it."),
                                 "gsca": ("Diagnosis: GS-CA burst failures", "Share of burst failures from collisions, link loss and duty-cycle blocking."),
                                 "r2": ("Diagnosis: R2 frame-size sign test", "Power of the 16-cell sign test."),
                                 "synth": ("Diagnosis: synthetic generators", "Status of the generator diagnosis.")}.items():
        body = "\n".join(doc_parts[key])
        (Path("docs/03_results") / f"DIAGNOSIS_{key.upper()}.md").write_text(hdr(title, scope) + body + "\n", encoding="utf-8")


def main() -> None:
    rec = Rec("rd.d0.", SRC)
    parts = {k: [] for k in ("uasct", "osdr", "gsca", "r2", "synth")}
    part_a(rec, parts["uasct"])
    part_a_sweep(rec, parts["uasct"])
    part_b(rec, parts["osdr"])
    part_c(rec, parts["gsca"])
    part_d(rec, parts["r2"])
    part_e(rec, parts["synth"])
    write_docs(parts)
    rec.write()
    print("done", len(rec.ent), "entries")


if __name__ == "__main__":
    main()
