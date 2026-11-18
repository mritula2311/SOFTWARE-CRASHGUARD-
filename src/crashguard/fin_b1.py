"""B1 (ANALYTICAL; checks the MODEL within its bounds, not the implementation): re-run of the bounded check of T12 with the same bounds EXT and the original properties, for the design and for the proposed change
(pending CANCEL memory); an exploratory two-event bound; the attack cases with the change on (docs/02_preregistration/PREREGISTRATION_V5.md B1). Keys f.b1.*; the tagged keys s12x.* are not touched."""
from __future__ import annotations

import time

from crashguard import attacks as A
from crashguard import attacks_extra as AX
from crashguard import protocol_model_ext as M
from crashguard import sct_protocol as T
from crashguard.fin_common import Entries

SRC = "src/crashguard/fin_b1.py"
EXT = M.Bounds(cmax=4, max_events=1, max_tries=3, max_flash=1, max_att=3, max_loss=1, max_inflight=3, max_reboot_base=0, max_reboot_car=0)
EXT2 = M.Bounds(cmax=4, max_events=2, max_tries=2, max_flash=1, max_att=2, max_loss=1, max_inflight=3, max_reboot_base=0, max_reboot_car=0)
SHOW = ("S1_replay_or_forgery_accepted_as_new", "S2_spoofed_ack_stops_retries", "S3_repeat_not_acked_or_budget_exceeded", "S4_accepted_counters_not_increasing", "C1_cancel_without_valid_signature",
        "C2_send_after_valid_ack", "C3_cancel_lost_by_reordering", "C4_late_ack_restarts_sending", "F1_flash_ack_stops_alert_retries")


def attack_matches(pending: bool) -> dict:
    orig = T.SctBase
    if pending:
        T.SctBase = lambda key, **kw: orig(key, pending_cancel=True, **kw)  # noqa: E731
    try:
        a = A.run_cases()
        x = AX.run_cases()
    finally:
        T.SctBase = orig
    return {"orig": {r["case"]: bool(r["match"]) for r in a}, "extra": {r["id"]: (bool(r["match"]), r["observed"]) for r in x}}


def main() -> None:
    E = Entries("f.b1", SRC)
    trace = None
    for tag, b, runs in (("ext", EXT, (("design", M.Variant("design")), ("pending_cancel", M.Variant("pending_cancel", keep_pending_cancel=True)))), ("ext2", EXT2, (("design", M.Variant("design")), ("pending_cancel", M.Variant("pending_cancel", keep_pending_cancel=True))))):
        for nm, v in runs:
            t0 = time.time()
            r = M.explore(v, b, max_states=3_000_000 if tag == "ext2" else 4_000_000)
            E.add(f"{tag}.{nm}.states", r["states"], "states", "ANALYTICAL", "reachable states" + (" (TRUNCATED at the cap)" if r.get("truncated") else ", complete") + ("; EXPLORATORY bound, not in the preregistered hypotheses" if tag == "ext2" else ""))
            E.add(f"{tag}.{nm}.depth", r["depth"], "steps", "ANALYTICAL")
            if r.get("truncated"):
                continue
            n_chk = 0
            for p in SHOW:
                pr = r["props"][p]
                E.add(f"{tag}.{nm}.{p}", int(pr["holds"]), "flag", "ANALYTICAL", "1 = holds within the bounds; 0 = a counterexample exists")
                n_chk += 1
                if not pr["holds"] and p.startswith("C3") and tag == "ext" and nm == "design":
                    trace = pr["trace"]
            E.add(f"{tag}.{nm}.properties_checked", n_chk, "properties", "ANALYTICAL")
            print(tag, nm, r["states"], r["depth"], {p.split("_")[0]: r["props"][p]["holds"] for p in SHOW}, round(time.time() - t0), "s", flush=True)
    if trace:
        E.add("ext.design.C3_trace", " | ".join(trace), "trace", "ANALYTICAL", "shortest counterexample, bounds EXT")
    base, new = attack_matches(False), attack_matches(True)
    ch = [k for k in new["extra"] if new["extra"][k] != base["extra"][k]]
    E.add("attacks.original_cases", len(base["orig"]), "cases", "SIMULATED", "designed cases of crashguard.attacks")
    E.add("attacks.original_match_before", sum(base["orig"].values()), "cases", "SIMULATED")
    E.add("attacks.original_match_with_change", sum(new["orig"].values()), "cases", "SIMULATED", "SctBase(pending_cancel=True); the original cases use BaseVerifier and are unaffected by construction")
    E.add("attacks.extra_cases", len(base["extra"]), "cases", "SIMULATED", "designed cases of crashguard.attacks_extra")
    E.add("attacks.extra_match_before", sum(v[0] for v in base["extra"].values()), "cases", "SIMULATED")
    E.add("attacks.extra_match_with_change", sum(v[0] for v in new["extra"].values()), "cases", "SIMULATED")
    E.add("attacks.extra_cases_changed", ",".join(ch) or "none", "ids", "SIMULATED", "cases whose observed outcome or match flag changes with the option on")
    E.write()
    print("attack cases changed:", ch, {k: new['extra'][k] for k in ch}, "orig", sum(base["orig"].values()), sum(new["orig"].values()), "extra", sum(v[0] for v in base["extra"].values()), sum(v[0] for v in new["extra"].values()))


if __name__ == "__main__":
    main()
