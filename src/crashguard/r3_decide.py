"""T6 (docs/02_preregistration/PREREGISTRATION_V14.md section 5): Holm adjustment over the seven preregistered tests and the decision table of round 3. Keys ``r3.holm.*`` and ``r3.decide.*``.

    python -m crashguard.r3_decide

Bootstrap p-values are reported as (count + 1) / (resamples + 1): with 2,000 resamples (500 for the R3 trace resamples) the smallest value is 0.0005 (0.002), which is a resolution limit, not zero.
A test is SUPPORTED if its criterion holds at the point level and the Holm-adjusted p is below 0.05. H-T2sec, H-T2 and H-T3c have no p-value (formal checks and a count rule) and are decided by their stated criteria.
"""
from __future__ import annotations

import json
from pathlib import Path

from crashguard.results import record_many

ROOT = Path(__file__).resolve().parents[2]
SRC = "src/crashguard/r3_decide.py"
RES = ROOT / "results" / "results.json"


def load() -> dict:
    return {e["name"]: e for e in json.loads(RES.read_text(encoding="utf-8"))}


def main() -> None:
    R = load()

    def v(k):
        return R[k]["value"]

    nb = {"T1": 2000, "T1c": 500, "T3": 2000}
    tests = [
        ("H-T1a-L", "r3.t1.T1a.L.criterion_met", "r3.t1.T1a.L.p", nb["T1"]),
        ("H-T1a-M", "r3.t1.T1a.M.criterion_met", "r3.t1.T1a.M.p", nb["T1"]),
        ("H-T1a-H", "r3.t1.T1a.H.criterion_met", "r3.t1.T1a.H.p", nb["T1"]),
        ("H-T1b", "r3.t1.T1b.criterion_met", "r3.t1.T1b.p", nb["T1"]),
        ("H-T1c", "r3.t1.T1c.criterion_met", "r3.t1.T1c.p", nb["T1c"]),
        ("H-T3a", "r3.t3.hT3a.criterion_met", "r3.t3.hT3a.p", nb["T3"]),
        ("H-T3b", "r3.t3.hT3b.criterion_met", "r3.t3.hT3b.p", nb["T3"]),
    ]
    rows = []
    for name, ck, pk, n in tests:
        p_raw = float(v(pk))
        p = max(p_raw, 1.0 / (n + 1))
        rows.append(dict(name=name, met=int(v(ck)), p_raw=p_raw, p=p))
    order = sorted(range(len(rows)), key=lambda i: rows[i]["p"])
    m = len(rows)
    run = 0.0
    for rank, i in enumerate(order):
        adj = min(1.0, rows[i]["p"] * (m - rank))
        run = max(run, adj)
        rows[i]["p_holm"] = run
        rows[i]["supported"] = bool(rows[i]["met"] and run < 0.05)
    ent: list[dict] = []
    for r in rows:
        k = r["name"].lower().replace("-", "")
        ent.append(dict(name=f"r3.holm.{k}.p", value=round(r["p"], 5), unit="p", origin="TRACE_DRIVEN" if "T1" in r["name"] else "MEASURED_SOFTWARE", source_file=SRC, notes="bootstrap p = (count + 1) / (resamples + 1); resolution floor"))
        ent.append(dict(name=f"r3.holm.{k}.p_holm", value=round(r["p_holm"], 5), unit="p", origin="TRACE_DRIVEN" if "T1" in r["name"] else "MEASURED_SOFTWARE", source_file=SRC, notes="Holm over the seven preregistered tests"))
        ent.append(dict(name=f"r3.holm.{k}.verdict", value="SUPPORTED" if r["supported"] else "NOT SUPPORTED", unit="verdict", origin="TRACE_DRIVEN" if "T1" in r["name"] else "MEASURED_SOFTWARE", source_file=SRC, notes="criterion met at the point level and Holm p below 0.05"))
    # no-p hypotheses
    t2 = bool(v("r3.t2.timed.hT2.criterion_met"))
    sec_core = bool(v("r3.t2.sec.hT2sec.core_proved"))
    sec_attack = bool(v("r3.t2.sec.hT2sec.attack_found_on_M0"))
    sec_l6 = bool(v("r3.t2.sec.hT2sec.l6_refuted_as_expected"))
    sec_ids = v("r3.t2.sec.hT2sec.l5_id_uniqueness")
    sec_all = bool(sec_core and sec_attack and sec_l6 and sec_ids == "verified")
    c_custom = bool(v("ar.r3.hR3.clause_a.met"))
    c_trace = all(bool(v(f"r3.t1.T1c.{g}.earlier_median_s") >= 0.8) for g in "LMH")
    c_ns3 = False  # NOT_RUN: the ns-3 application has no two-stage alert
    n_models = int(c_custom) + int(c_trace) + int(c_ns3)
    t3c = n_models >= 2
    ent += [
        dict(name="r3.decide.hT2.verdict", value="SUPPORTED (FORMAL)" if t2 else "REFUTED", unit="verdict", origin="FORMAL", source_file=SRC, notes="D1 worst-case delivery time not longer than quick retries for k = 0..6 and no duty breach, exhaustive enumeration (not UPPAAL)"),
        dict(name="r3.decide.hT2sec.verdict", value="SUPPORTED" if sec_all else "PARTLY SUPPORTED", unit="verdict", origin="FORMAL", source_file=SRC, notes="L1 to L4b and the car-reboot no-double-acceptance lemma proved, the attack found on M0, L6 refuted as expected; L5 id uniqueness not proved within the limits"),
        dict(name="r3.decide.hT3c.models_holding", value=n_models, unit="of 3", origin="MEASURED_SOFTWARE", source_file=SRC, notes="custom simulator (ar.r3 clause a), trace-driven (T1c median earlier, all groups), ns-3 NOT_RUN counted as not holding"),
        dict(name="r3.decide.hT3c.verdict", value="SUPPORTED" if t3c else "NOT SUPPORTED", unit="verdict", origin="MEASURED_SOFTWARE", source_file=SRC, notes="end-to-end earlier arrival in at least two of three link models"),
    ]
    record_many(ent, purge_prefixes=("r3.holm.", "r3.decide."))
    out = dict(holm=rows, hT2=t2, hT2sec=dict(core=sec_core, attack=sec_attack, l6=sec_l6, l5_ids=sec_ids, all=sec_all), hT3c=dict(custom=c_custom, trace=c_trace, ns3=c_ns3, n=n_models, met=t3c))
    (ROOT / "results" / "tables" / "r3_decision.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for r in rows:
        print(r["name"], r["met"], round(r["p"], 5), round(r["p_holm"], 5), "SUPPORTED" if r["supported"] else "NOT SUPPORTED")
    print(out["hT2"], out["hT2sec"], out["hT3c"])


if __name__ == "__main__":
    main()
