"""Run the bounded checks of docs/01_protocol/PROTOCOL_MODEL.md, cross-check the abstract base rule against the simulated attack suite, record results (ANALYTICAL) and append the results to the model document."""
from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

from crashguard import config as C
from crashguard import protocol_model as M

DOC = Path("docs/01_protocol/PROTOCOL_MODEL.md")
MARK = "<!-- results:start -->"
END = "<!-- results:end -->"
SRC = "src/crashguard/protocol_model.py"

ATT = M.Bounds(cmax=4, max_events=1, max_tries=3, max_flash=1, max_att=6, max_loss=1, max_inflight=3, max_reboot_base=0, max_reboot_car=0)
REBB = M.Bounds(cmax=4, max_events=1, max_tries=3, max_flash=1, max_att=4, max_loss=1, max_inflight=3, max_reboot_base=1, max_reboot_car=0)
REBC = M.Bounds(cmax=4, max_events=2, max_tries=3, max_flash=1, max_att=4, max_loss=1, max_inflight=3, max_reboot_base=0, max_reboot_car=1)
LIVE = M.Bounds(cmax=4, max_events=2, max_tries=3, max_flash=2, max_att=0, max_loss=2, max_inflight=4, max_reboot_base=0, max_reboot_car=0)

RUNS = [
    ("ATT", "design", ATT, M.Variant("design")),
    ("ATT", "strict_anti_replay", ATT, M.Variant("strict_anti_replay", idempotent=False)),
    ("REBB", "design", REBB, M.Variant("design")),
    ("REBB", "base_no_persistence", REBB, M.Variant("base_no_persistence", base_persist=False)),
    ("REBC", "design", REBC, M.Variant("design", flash=False, cancel=False)),
    ("REBC", "car_no_persistence", REBC, M.Variant("car_no_persistence", car_persist=False, flash=False, cancel=False)),
    ("LIVE", "design", LIVE, M.Variant("design", liveness_env=True, cancel=False)),
    ("LIVE", "strict_anti_replay", LIVE, M.Variant("strict_anti_replay", idempotent=False, liveness_env=True, cancel=False)),
]


def crosscheck() -> list[dict]:
    """Abstract base rule on the sequences of mapped attack cases against the observed outcomes of the reference verifier."""
    att = pd.read_csv(C.TABLES / "attacks.csv")
    b = M.Bounds()
    idx = {n: i for i, n in enumerate(att.case)}

    def obs(prefix: str) -> tuple[int, str]:
        for n, i in idx.items():
            if n.startswith(prefix):
                return i, str(att.observed[i])
        raise KeyError(prefix)

    def run(seq, v=M.Variant("x"), reboot_at=None):
        base, out = (0, 0, (), ()), []
        for k, item in enumerate(seq):
            if item == "reboot":
                base = base if v.base_persist else (0, 0, (), ())
                continue
            d, base, _ack = M.base_rule(base, item, v, b)
            out.append(d)
        return out

    A = lambda c, s=1, ok=True: ("A", c, s, ok)  # noqa: E731
    mapped = [
        ("Valid alert", [A(1)], -1, M.ACCEPT, M.Variant("x")),
        ("Forged tag", [A(1, ok=False)], -1, M.REJECT_TAG, M.Variant("x")),
        ("Replay (same packet again): not processed again", [A(1), A(1)], -1, M.REACK, M.Variant("x")),
        ("Strict verifier (before the fix)", [A(1), A(1)], -1, M.REJECT_COUNTER, M.Variant("x", idempotent=False)),
        ("ACK lost, car retries same packet: re-ACKed", [A(1), A(1)], -1, M.REACK, M.Variant("x")),
        ("Old counter, different content: rejected", [A(3), A(1, s=2)], -1, M.REJECT_COUNTER, M.Variant("x")),
        ("Same counter, different content (event changed): rejected", [A(2), A(2, s=2)], -1, M.REJECT_COUNTER, M.Variant("x")),
        ("Replay of an alert older than the re-ACK window: rejected", [A(1), A(2), A(3), A(1)], -1, M.REJECT_COUNTER, M.Variant("x")),
        ("Retry of the same event with a fresh counter", [A(1), A(2)], -1, M.ACCEPT, M.Variant("x")),
        ("Base reboot, counter persisted: replay not processed again", [A(1), "reboot", A(1)], -1, M.REACK, M.Variant("x", base_persist=True)),
        ("Base reboot, counter lost: replay", [A(1), "reboot", A(1)], -1, M.ACCEPT, M.Variant("x", base_persist=False)),
    ]
    rows = []
    for prefix, seq, pos, _expect, v in mapped:
        i, observed = obs(prefix)
        res = run(seq, v)
        got = res[pos]
        norm = {M.ACCEPT: "accept", M.REACK: "reack", M.REJECT_COUNTER: "reject_counter", M.REJECT_TAG: "reject_tag"}.get(got, got)
        rows.append(dict(case_id=int(i), case=att.case[i], model=norm, reference=observed, agree=norm == observed))
    # car-side ACK checks
    def car_accepts(m, waiting_ctr):
        return m[4] and m[1] == "A" and m[2] == waiting_ctr

    for prefix, msg, wait, expect in (("Spoofed ACK (attacker key)", ("K", "A", 1, 0, False), 1, "reject"), ("Old ACK replayed for a later alert", ("K", "A", 1, 0, True), 2, "reject"),
                                     ("Genuine ACK for the waiting alert", ("K", "A", 1, 0, True), 1, "accept")):
        i, observed = obs(prefix)
        got = "accept" if car_accepts(msg, wait) else "reject"
        rows.append(dict(case_id=int(i), case=att.case[i], model=got, reference=observed, agree=got == observed))
    return rows


def main() -> None:
    from crashguard.results import record_many

    ent: list[dict] = []
    lines = [MARK, "", "## 7. Results (generated by `python -m crashguard.protocol_check`; ANALYTICAL, bounded model check, not a proof of the implementation)", "",
             "| Bounds | Variant | States | Depth | " + " | ".join(p.split("_")[0] for p in M.PROPS) + " |", "|---|---|---|---|" + "---|" * len(M.PROPS)]
    traces: list[str] = []

    def add(name, value, unit, notes=""):
        ent.append(dict(name=f"s12.{name}", value=value, unit=unit, origin="ANALYTICAL", source_file=SRC, notes=notes))

    for bn, vn, b, v in RUNS:
        t = time.time()
        r = M.explore(v, b)
        el = time.time() - t
        base = f"{bn}.{vn}"
        if r["truncated"]:
            add(f"{base}.states", r["states"], "states", "TRUNCATED at the state limit: no property is reported for this run")
            lines.append(f"| {bn} | {vn} | {r['states']:,} (truncated) | {r['depth']} | " + " | ".join(["NOT_RUN (truncated)"] * len(M.PROPS)) + " |")
            continue
        add(f"{base}.states", r["states"], "states", "reachable states of the bounded model (level-by-level, complete unless truncated)" if not r["truncated"] else "TRUNCATED: search stopped at the state limit")
        add(f"{base}.depth", r["depth"], "steps", "longest shortest path from the initial state")
        add(f"{base}.transitions", r["transitions"], "transitions", "")
        cells = []
        for p in M.PROPS:
            pr = r["props"].get(p, {})
            if not pr.get("checked"):
                cells.append("not checked here")
                add(f"{base}.{p}", "NOT_RUN", "", "not checked in this bound set")
                continue
            holds = pr["holds"]
            add(f"{base}.{p}", int(holds), "flag", "1 = holds within the bounds; 0 = a counterexample exists (trace in docs/01_protocol/PROTOCOL_MODEL.md)")
            cells.append("holds" if holds else f"**FAILS** ({len(pr['trace'])} steps)")
            if not holds:
                traces.append(f"**{bn} / {vn} / {p}** (shortest counterexample, {len(pr['trace'])} steps):\n" + "\n".join(f"{k + 1}. {s}" for k, s in enumerate(pr["trace"])))
        lines.append(f"| {bn} | {vn} | {r['states']:,}{' (truncated)' if r['truncated'] else ''} | {r['depth']} | " + " | ".join(cells) + " |")
        print(bn, vn, r["states"], r["depth"], round(el, 1), "s", cells)
    lines += ["", "Property names: S1 replay or forgery accepted as new; S2 spoofed ACK stops retries; S3 repeat not acknowledged or budget exceeded; S4 accepted counters not increasing; L1 no ACK in a terminal state; "
              "C1 CANCEL accepted without a valid signature; C2 send after a valid ACK. 'holds' = no counterexample within the bounds.", "", "### Counterexamples (shortest traces, plain steps)", ""] + traces
    cc = crosscheck()
    n_agree = sum(r["agree"] for r in cc)
    add("crosscheck.cases", len(cc), "cases", "mapped attack cases run through the abstract base rule")
    add("crosscheck.agree", n_agree, "cases", "model decision equals the reference verifier's observed outcome")
    for r in cc:
        add(f"crosscheck.case{r['case_id']:02d}.agree", int(r["agree"]), "flag", f"{r['case']}; model {r['model']}, reference {r['reference']}")
    lines += ["", f"### Cross-check with the attack suite ({n_agree} of {len(cc)} mapped cases agree)", "", "| Case id | Case | Model | Reference (observed) | Agree |", "|---|---|---|---|---|"]
    lines += [f"| {r['case_id']:02d} | {r['case']} | {r['model']} | {r['reference']} | {'yes' if r['agree'] else '**NO**'} |" for r in cc]
    dis = [r for r in cc if not r["agree"]]
    lines += ["", "Disagreements: " + ("; ".join(f"case {r['case_id']:02d} ({r['case']}): the model decides {r['model']}, the reference {r['reference']}" for r in dis) + ". The model has no event id: it keys the re-ACK memory by counter only, while the reference verifier keys it by (node, event, counter). This is an abstraction gap of the model, not a result about the verifier." if dis else "none."), END]
    text = DOC.read_text(encoding="utf-8")
    block = "\n".join(lines)
    if MARK in text:
        text = text[: text.index(MARK)] + block + text[text.index(END) + len(END):]
    else:
        text = text.rstrip("\n") + "\n\n" + block + "\n"
    DOC.write_text(text, encoding="utf-8")
    record_many(ent, purge_prefixes=("s12.",))


if __name__ == "__main__":
    main()
