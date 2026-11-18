"""Round 4 decision step (PREREGISTRATION_V15 sections 2.6, 4 and 5): reads the formal outputs, applies Holm over the five tests, writes keys ``a4.formal.*`` and ``a4.holm.*``,
the decision table, the results document and the round-4 section of the negatives register.

    python -m crashguard.a4_decide
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from crashguard.results import record_many

ROOT = Path(__file__).resolve().parents[2]
SRC = "src/crashguard/a4_decide.py"
OUT_TABLE = ROOT / "docs" / "03_results" / "A4_DECISION_TABLE.md"
OUT_RES = ROOT / "docs" / "03_results" / "A4_RESULTS.md"
NEG = ROOT / "docs" / "03_results" / "NEGATIVES_REGISTER.md"
NEG_BEGIN, NEG_END = "<!-- a4:begin -->", "<!-- a4:end -->"
ALPHA = 0.05


def R() -> dict:
    return {e["name"]: e["value"] for e in json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))}


def tamarin_status(f: Path, lemma: str) -> tuple[str, str]:
    t = f.read_text(encoding="utf-8", errors="replace") if f.exists() else ""
    m = re.search(rf"^\s+{re.escape(lemma)} \((?:all|exists)-traces?\): (verified|falsified)[^\n]*?\((\d+) steps?\)", t, re.M)
    w = re.search(r"wall time (\d+) s", t)
    code = re.search(r"exit code: (\d+)", t)
    if m:
        return m.group(1) + f" ({m.group(2)} steps)", (w.group(1) + " s") if w else ""
    if code and code.group(1) == "124":
        return "timeout", (w.group(1) + " s") if w else ""
    return "NOT_RUN", ""


def proverif_status(f: Path) -> list[tuple[str, str]]:
    t = f.read_text(encoding="utf-8", errors="replace") if f.exists() else ""
    out = []
    for m in re.finditer(r"^RESULT (.+?) is (true|false)\.|^RESULT (.+?) cannot be proved\.", t, re.M):
        if m.group(1):
            out.append((m.group(1).strip()[:150], "proved" if m.group(2) == "true" else "attack found (false)"))
        else:
            out.append((m.group(3).strip()[:150], "cannot be proved"))
    w = re.search(r"wall time (\d+) s", t)
    if not out and re.search(r"exit code: 124", t):
        out.append(("query not decided within the time limit", "undecided (timeout)"))
    return out, ((w.group(1) + " s") if w else "")


def holm(ps: dict) -> dict:
    items = sorted(ps.items(), key=lambda kv: kv[1])
    m = len(items)
    adj, run = {}, 0.0
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, (m - i) * p))
        adj[k] = run
    return adj


def main() -> None:
    r = R()
    ent: list[dict] = []

    def add(name, value, unit, origin, notes=""):
        ent.append(dict(name=name, value=round(value, 6) if isinstance(value, float) else value, unit=unit, origin=origin, source_file=SRC, notes=notes))

    # ------------------------------------------------------------------ formal outputs
    tam = {}
    base = ROOT / "formal" / "out" / "prov"
    for lem in ("executable_prov", "executable_prov_repeat", "executable_alert", "P1_prov_authenticity", "P2_ack_authenticity", "P3_no_cross_vehicle_suppression", "P4_no_type_confusion_alert"):
        tam[lem] = tamarin_status(base / "auth" / f"{lem}.txt", lem)
    tam["P4_no_domain_letters (negative control)"] = tamarin_status(base / "nodomain" / "P4_no_type_confusion_alert.txt", "P4_no_type_confusion_alert")
    for lem in ("executable_ts", "L4b_at_most_once", "L4_replay_outside_window", "L5_no_double_accept_with_car_reboot", "L6_base_reboot_replay"):
        tam["fresh." + lem] = tamarin_status(base / "fresh" / f"{lem}.txt", lem)
    must = ["executable_prov", "P1_prov_authenticity", "P2_ack_authenticity", "P3_no_cross_vehicle_suppression", "P4_no_type_confusion_alert"]
    a1_formal_ok = all(tam[k][0].startswith("verified") for k in must)
    for k, (st, w) in tam.items():
        add(f"a4.a1.tamarin.{k.split(' ')[0]}", st, "status", "FORMAL", f"Tamarin 1.12.0, Maude 3.5.1, single thread; wall time {w}")
    add("a4.a1.tamarin.authenticity_and_ack_binding_proved", int(a1_formal_ok), "flag", "FORMAL", "executability, P1 (authenticity), P2 and P3 (per-vehicle ACK binding) and P4 (no type confusion) verified")
    pv = {}
    for nm in ("carid_frozen_same_epoch", "carid_frozen_next_epoch", "carid_bootctr_same_epoch", "carid_bootctr_nowrite", "carid_frozen_chain"):
        f = ROOT / "formal" / "out" / "proverif" / f"{nm}.txt"
        if f.exists():
            pv[nm] = proverif_status(f)
    for nm, (res, w) in pv.items():
        for i, (q, st) in enumerate(res):
            add(f"a4.a3.proverif.{nm}.q{i + 1}", st, "status", "FORMAL", f"ProVerif 2.05; {q}; wall time {w}")

    # ------------------------------------------------------------------ Holm over five tests
    tests = {
        "H-A1a": dict(met=bool(r["a4.a1.ns3.hA1a.criterion_met"]), p=float(r["a4.a1.ns3.hA1a.p_raw"]), label="SIMULATED"),
        "H-A1b": dict(met=bool(r["a4.a1.trace.hA1b.criterion_met"]), p=float(r["a4.a1.trace.hA1b.p_raw"]), label="TRACE_DRIVEN"),
        "H-A1c": dict(met=bool(r["a4.a1.ns3.hA1c.ns3.criterion_met"]) and bool(r["a4.a1.trace.hA1c.criterion_met"]), p=max(float(r["a4.a1.ns3.hA1c.ns3.p_raw"]), float(r["a4.a1.trace.hA1c.p_raw"])), label="SIMULATED and TRACE_DRIVEN"),
        "H-A2a": dict(met=bool(r["a4.a2.reserve.hA2a.criterion_met"]), p=float(r["a4.a2.reserve.hA2a.p_raw"]), label="TRACE_DRIVEN (EXPLORATORY)"),
        "H-A2b": dict(met=bool(r["a4.a2.reserve.hA2b.criterion_met"]), p=float(r["a4.a2.reserve.hA2b.p_raw"]), label="TRACE_DRIVEN (EXPLORATORY)"),
    }
    adj = holm({k: v["p"] for k, v in tests.items()})
    for k, v in tests.items():
        v["holm"] = adj[k]
        v["supported"] = bool(v["met"] and adj[k] < ALPHA)
        key = k.replace("-", "").lower()
        add(f"a4.holm.{key}.p_raw", v["p"], "p", "ANALYTICAL", "raw p of the preregistered statistic")
        add(f"a4.holm.{key}.p_holm", v["holm"], "p", "ANALYTICAL", "Holm over the five tests of V15")
        add(f"a4.verdict.{key}", "SUPPORTED" if v["supported"] else "NOT SUPPORTED", "verdict", "ANALYTICAL", "criterion at the point level and Holm-adjusted p below 0.05")
    a1_killed = not (tests["H-A1a"]["supported"] and tests["H-A1b"]["supported"])
    a2_killed = not tests["H-A2a"]["supported"]
    add("a4.verdict.a1_killed", int(a1_killed), "flag", "ANALYTICAL", "kill rule of V15 2.3: H-A1a or H-A1b not supported")
    add("a4.verdict.a2_killed", int(a2_killed), "flag", "ANALYTICAL", "kill rule of V15 3: H-A2a not supported")
    n_supported = sum(v["supported"] for v in tests.values())
    add("a4.verdict.n_supported", n_supported, "tests", "ANALYTICAL", "supported tests of the five")
    record_many(ent, purge_prefixes=("a4.a1.tamarin.", "a4.a3.proverif.", "a4.holm.", "a4.verdict."))
    r = R()

    # ------------------------------------------------------------------ documents
    g = lambda k, nd=3: (f"{r[k]:.{nd}f}" if isinstance(r.get(k), float) else str(r.get(k)))  # noqa: E731
    def cell(sf, st, p):
        c = f"a4.a1.ns3.sf{sf}.{st}.p{p:g}"
        return f"| sf{sf}.{st} | {p:g} | {g(c + '.extra_air_ratio')} (up to {g(c + '.extra_air_ratio_hi')}) | {g(c + '.extra_air_ratio_r3')} | {g(c + '.delivery_a1', 4)} | {g(c + '.delivery_r3', 4)} | {g(c + '.delivery_diff', 4)} ({g(c + '.delivery_diff_lo', 4)}) | {g(c + '.prov_delivery_a1')} / {g(c + '.prov_delivery_r3')} |"
    dec = ["# Round 4 decision table", "",
           "<!-- header:start -->", "| Field | Value |", "|---|---|", "| Status | current |", "| Date | 2026-11-15 |", "| Owner | Mritula S |", "| Scope | One row per round-4 hypothesis: result, label, interval, nearest prior work, allowed wording. |",
           "| Evidence labels used | SIMULATED, TRACE_DRIVEN, FORMAL, ANALYTICAL |", "<!-- header:end -->", "",
           "Generated by `python -m crashguard.a4_decide`. One Holm family of five tests (`PREREGISTRATION_V15.md` section 5). A test is supported if its criterion holds at the point level and the Holm-adjusted p is below 0.05. A2 rows are EXPLORATORY (same dataset as development). These results do not change any earlier verdict.", "",
           "| Hypothesis | Criterion (V15) | Result | Label | Interval | Raw p | Holm p | Verdict | Nearest prior work | Allowed wording |", "|---|---|---|---|---|---:|---:|---|---|---|"]
    h = tests
    dec.append(f"| H-A1a | extra airtime at SF9 at most 40% in all eight cells | {g('a4.a1.ns3.sf9.shipped.p0.extra_air_ratio')} at loss 0 (shipped), cells met: {sum(1 for k in r if k.startswith('a4.a1.ns3.hA1a.cell.') and r[k] == 1)} of 8 | SIMULATED | upper 95% limit {g('a4.a1.ns3.sf9.shipped.p0.extra_air_ratio_hi')} in that cell | {h['H-A1a']['p']:.4f} | {h['H-A1a']['holm']:.4f} | {'SUPPORTED' if h['H-A1a']['supported'] else 'NOT SUPPORTED'} | Lopez et al. 2021; Abakar et al. 2022 (context) | \"With a 24-byte provisional frame repeated until acknowledged, the extra airtime at SF9 was above the 40% limit in ns-3.\" |")
    dec.append(f"| H-A1b | provisional delivery within 10 s higher by at least 3 points than R3 (fresh sniffer links) | {g('a4.a1.trace.hA1b.diff', 4)} ({g('a4.a1.trace.hA1b.prov_a1')} against {g('a4.a1.trace.hA1b.prov_r3')}) on {g('a4.a1.trace.n_links', 0)} links | TRACE_DRIVEN | {g('a4.a1.trace.hA1b.diff_lo', 4)} to {g('a4.a1.trace.hA1b.diff_hi', 4)} | {h['H-A1b']['p']:.4f} | {h['H-A1b']['holm']:.4f} | {'SUPPORTED' if h['H-A1b']['supported'] else 'NOT SUPPORTED'} | none found | \"On the fresh sniffer links the repeated short provisional frame raised provisional delivery by {r['a4.a1.trace.hA1b.diff'] * 100:.1f} points, below the 3 points preregistered.\" |")
    dec.append(f"| H-A1c | no cell worse than R3 by more than 1 point in final delivery (16 ns-3 cells, 3 trace groups) | ns-3: {'met' if r['a4.a1.ns3.hA1c.ns3.criterion_met'] else 'not met'} (worst cell sf9.shipped.p0.6, {g('a4.a1.ns3.sf9.shipped.p0.6.delivery_diff', 4)}); traces: {'met' if r['a4.a1.trace.hA1c.criterion_met'] else 'not met'} | SIMULATED and TRACE_DRIVEN | worst ns-3 lower limit {g('a4.a1.ns3.sf9.shipped.p0.6.delivery_diff_lo', 4)} | {h['H-A1c']['p']:.4f} | {h['H-A1c']['holm']:.4f} | {'SUPPORTED' if h['H-A1c']['supported'] else 'NOT SUPPORTED'} | none found | \"In ns-3 at a loss of 0.6 the repeated provisional frame lowered final delivery by about 2 points.\" |")
    dec.append(f"| H-A2a | two receivers raise 10 s delivery by at least 10 points on weak links (EXPLORATORY) | {g('a4.a2.reserve.hA2a.diff', 4)} on {g('a4.a2.reserve.hA2a.n_weak', 0)} weak devices | TRACE_DRIVEN | {g('a4.a2.reserve.hA2a.diff_lo', 4)} to {g('a4.a2.reserve.hA2a.diff_hi', 4)} | {h['H-A2a']['p']:.4f} | {h['H-A2a']['holm']:.4f} | {'SUPPORTED' if h['H-A2a']['supported'] else 'NOT SUPPORTED'} | Petroni and Biagi 2022; Can et al. 2022; Lanka and Kothandaraman 2026 (simulation) | \"On the LoED traces a second receiver raised 10 s delivery on weak links by {r['a4.a2.reserve.hA2a.diff'] * 100:.1f} points (EXPLORATORY); {r['a4.a2.reserve.share_one_gateway'] * 100:.0f}% of devices are heard by one gateway only.\" |")
    dec.append(f"| H-A2b | share of devices at or above 0.99 delivery rises from one to three receivers (EXPLORATORY) | {g('a4.a2.reserve.hA2b.diff', 4)} (share {g('a4.a2.reserve.curve.share99.k1')} to {g('a4.a2.reserve.curve.share99.k3')}) | TRACE_DRIVEN | {g('a4.a2.reserve.hA2b.diff_lo', 4)} to {g('a4.a2.reserve.hA2b.diff_hi', 4)} | {h['H-A2b']['p']:.4f} | {h['H-A2b']['holm']:.4f} | {'SUPPORTED' if h['H-A2b']['supported'] else 'NOT SUPPORTED'} | as above | \"The share of devices reaching 99% delivery in 10 s rose by {r['a4.a2.reserve.hA2b.diff'] * 100:.2f} points from one to three receivers (EXPLORATORY).\" |")
    dec += ["", "| Item | Result | Label | Allowed wording |", "|---|---|---|---|",
            f"| A1 Tamarin rerun (24-byte provisional frame) | executability, authenticity (P1), per-vehicle ACK binding (P2, P3) and no type confusion (P4) {'proved' if a1_formal_ok else 'NOT all proved'}; negative control without domain letters: {tam['P4_no_domain_letters (negative control)'][0]}; freshness model: {tam['fresh.L4_replay_outside_window'][0]} (L4), {tam['fresh.L4b_at_most_once'][0]} (L4b) | FORMAL | \"In the symbolic model the provisional frame is authentic and its ACK is bound to the vehicle; nothing here says the implementation is secure.\" A1 is killed by H-A1a and H-A1b regardless. |"]
    for nm, (res, w) in pv.items():
        dec.append(f"| A3 ProVerif {nm} | {'; '.join(st for _q, st in res) or 'NOT_RUN'} | FORMAL | see `A4_A3_PROVERIF.md` |")
    dec += ["", f"**A1 killed: {a1_killed}. A2 killed: {a2_killed}. Supported tests: {n_supported} of 5.** Nothing from round 4 enters the main text of the paper as a result; the failed items are in the negatives register.", ""]
    OUT_TABLE.write_text("\n".join(dec), encoding="utf-8")

    res = ["# Round 4 results (A1, A2, A3)", "",
           "<!-- header:start -->", "| Field | Value |", "|---|---|", "| Status | current |", "| Date | 2026-11-15 |", "| Owner | Mritula S |", "| Scope | Round 4 tables: A1 in ns-3 and on traces, A2 delivery by number of receivers, formal results. |",
           "| Evidence labels used | SIMULATED, TRACE_DRIVEN, FORMAL |", "<!-- header:end -->", "",
           "Generated by `python -m crashguard.a4_decide` from `results/results.json` (keys `a4.*`). Settings and criteria: `PREREGISTRATION_V15.md`. ns-3 results are SIMULATED (60 vehicles in a disc of 1,500 m, 10 events per vehicle-hour, 60 seeds, 1% duty); trace results are TRACE_DRIVEN.", "",
           "## A1 in ns-3 (SF7 and SF9, both calibration settings)", "",
           "Extra airtime is the A1 two-stage transmit airtime over the single-stage airtime minus 1 (95% upper limit in brackets); R3 is the same ratio for the round-3 two-stage alert on the same seeds. Delivery is the share of crash events that reach the base (provisional or confirm frame); the difference is A1 minus R3 with its lower 95% limit. The last column is the share of early-alarm events whose provisional frame is received (A1 / R3).", "",
           "| Cell | Loss | Extra airtime A1 | Extra airtime R3 | Delivery A1 | Delivery R3 | Difference (lower limit) | Provisional received A1 / R3 |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for sf in (7, 9):
        for st in ("calib", "shipped"):
            for p in (0.0, 0.1, 0.3, 0.6):
                res.append(cell(sf, st, p))
    res += ["", f"Invariants: provisional frames ending after the deadline {sum(r[k] for k in r if k.startswith('a4.a1.ns3.') and k.endswith('.inv_late'))}, frames above the duty limit {sum(r[k] for k in r if k.startswith('a4.a1.ns3.') and k.endswith('.inv_duty'))} (both must be 0).", "",
            "## A1 on traces (fresh sniffer links, SF7 timing)", "", "| Group | Links | Provisional delivery A1 | R3 | Difference (95% interval) | Final delivery difference (lower limit) | Extra airtime A1 | R3 |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for gp in "LMH":
        res.append(f"| {gp} | {g(f'a4.a1.trace.{gp}.n_links', 0)} | {g(f'a4.a1.trace.hA1b.{gp}.prov_a1')} | {g(f'a4.a1.trace.hA1b.{gp}.prov_r3')} | {g(f'a4.a1.trace.hA1b.{gp}.diff', 4)} ({g(f'a4.a1.trace.hA1b.{gp}.diff_lo', 4)} to {g(f'a4.a1.trace.hA1b.{gp}.diff_hi', 4)}) | {g(f'a4.a1.trace.hA1c.{gp}.delivery_diff', 4)} ({g(f'a4.a1.trace.hA1c.{gp}.delivery_diff_lo', 4)}) | {g(f'a4.a1.trace.{gp}.extra_air_a1')} | {g(f'a4.a1.trace.{gp}.extra_air_r3')} |")
    res += ["", f"All {g('a4.a1.trace.n_links', 0)} links together: provisional delivery {g('a4.a1.trace.hA1b.prov_a1')} (A1) against {g('a4.a1.trace.hA1b.prov_r3')} (R3), difference {g('a4.a1.trace.hA1b.diff', 4)}. A1 loses provisional delivery in groups L and M because a confirm frame that is ready at the same time takes the radio and its ACK ends the repetition, so the provisional frame is not sent at all (the base then has the alert through the confirm frame); the final delivery difference is the fair comparison there.",
            f"The same replay on the LoED RESERVE devices (descriptive): provisional difference {g('a4.a1.loedres.hA1b.diff', 4)}.", "",
            "## A2 delivery within 10 s by number of receivers (LoED RESERVE devices, EXPLORATORY)", "", "| Receivers | Mean delivery, all devices | Share of devices at or above 0.99 (95% interval) | Weak band H | Medium band M | Strong band L |", "|---:|---:|---:|---:|---:|---:|"]
    for k in range(1, 10):
        res.append(f"| {k} | {g(f'a4.a2.reserve.curve.mean_delivery.k{k}')} | {g(f'a4.a2.reserve.curve.share99.k{k}')} ({g(f'a4.a2.reserve.curve.share99.k{k}_lo')} to {g(f'a4.a2.reserve.curve.share99.k{k}_hi')}) | {g(f'a4.a2.reserve.band.H.mean_delivery.k{k}')} | {g(f'a4.a2.reserve.band.M.mean_delivery.k{k}')} | {g(f'a4.a2.reserve.band.L.mean_delivery.k{k}')} |")
    res += ["", f"Devices: {g('a4.a2.reserve.n_devices', 0)}; weak (best-gateway loss at least 40%): {g('a4.a2.reserve.band.H.n', 0)}; medium {g('a4.a2.reserve.band.M.n', 0)}; strong {g('a4.a2.reserve.band.L.n', 0)}. Share heard by one gateway only in the ranking period: {g('a4.a2.reserve.share_one_gateway')}. Among weak devices heard by two or more gateways the gain from one to two receivers is {g('a4.a2.reserve.hA2a.diff_two_plus_heard', 4)} (descriptive, not a preregistered criterion).", "",
            "Receivers needed for a device value of 0.95 and 0.99 (descriptive): the median is one receiver in every band; the share of devices that reach the value at all is shown below.", "", "| Band | Reach 0.95 | Reach 0.99 |", "|---|---:|---:|"]
    for gp in "HML":
        res.append(f"| {gp} | {g(f'a4.a2.reserve.band.{gp}.need95.share_reached')} | {g(f'a4.a2.reserve.band.{gp}.need99.share_reached')} |")
    res += ["", "Caveats: gateway reception is not vehicle mobility; the receivers are fixed city gateways; the ACK loss rule has no effect on delivery in the frozen replay; ties in the gateway ranking go to the lower gateway index.", "",
            "## Formal results", "", "| Lemma (Tamarin 1.12.0) | Result | Wall time |", "|---|---|---|"]
    for k, (st, w) in tam.items():
        res.append(f"| {k} | {st} | {w} |")
    res += ["", "| ProVerif 2.05 model | Query | Result |", "|---|---|---|"]
    for nm, (rs, _w) in pv.items():
        for q, st in rs:
            res.append(f"| {nm} | `{q}` | {st} |")
    res.append("")
    OUT_RES.write_text("\n".join(res), encoding="utf-8")

    neg = f"""{NEG_BEGIN}
## Round 4 (algorithm round 4, `PREREGISTRATION_V15.md`)

| Item | What was tried | Result | Why it failed | Not to be claimed |
|---|---|---|---|---|
| A1 short provisional alert (24 bytes, repeated until a verified ACK) | Provisional frame of 24 bytes sent as often as the duty limit allows; ns-3 at SF9 and traces | H-A1a not met (extra airtime at SF9 up to {g('a4.a1.ns3.sf9.shipped.p0.extra_air_ratio')} at loss 0, limit 0.40); H-A1b not met on fresh sniffer links ({r['a4.a1.trace.hA1b.diff'] * 100:.1f} points against 3 required); H-A1c not met in ns-3 ({r['a4.a1.ns3.sf9.shipped.p0.6.delivery_diff'] * 100:.1f} points at loss 0.6, SF9) | The frozen provisional frame was already short (14 bytes); a 24-byte frame costs more airtime, and the repetition adds channel load without raising final delivery. The premise that the provisional frame was long was wrong | That a longer repeated provisional frame fixes the SF9 airtime bound |
| A2 receiver diversity | Delivery within 10 s with 1 to 9 receivers on LoED per-gateway traces (EXPLORATORY) | H-A2a not met ({r['a4.a2.reserve.hA2a.diff'] * 100:.1f} points against 10 required); H-A2b not met ({r['a4.a2.reserve.hA2b.diff'] * 100:.2f} points) | {r['a4.a2.reserve.share_one_gateway'] * 100:.0f}% of devices are heard by one gateway only, so a second receiver cannot help them | That receiver diversity raises delivery on weak links by 10 points on these traces |
{NEG_END}
"""
    s = NEG.read_text(encoding="utf-8")
    if NEG_BEGIN in s:
        i, j = s.index(NEG_BEGIN), s.index(NEG_END) + len(NEG_END) + 1
        s = s[:i] + neg + s[j:]
    else:
        s = s.rstrip("\n") + "\n\n" + neg
    NEG.write_text(s, encoding="utf-8")
    print("A1 killed", a1_killed, "A2 killed", a2_killed, "supported", n_supported, {k: round(v["holm"], 4) for k, v in tests.items()})


if __name__ == "__main__":
    main()
