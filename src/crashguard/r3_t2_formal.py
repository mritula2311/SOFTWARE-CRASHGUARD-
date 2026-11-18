"""T2.1 (docs/02_preregistration/PREREGISTRATION_V14.md section 2.1): record the Tamarin results (FORMAL) from the stored tool output in ``formal/out``.

The models are ``formal/crash_alert_auth.spthy`` (run for the final design M1 and, with ``-D=M0``, for the earlier shared-key design) and ``formal/crash_alert_fresh.spthy``. The runs are made in WSL by
``scripts/wsl_run_tamarin.sh`` style scripts (Tamarin 1.12.0, Maude 3.5.1, one thread); this module only parses the saved output.

    python -m crashguard.r3_t2_formal
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from crashguard.results import record_many

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "formal" / "out"
SRC = "src/crashguard/r3_t2_formal.py"

# (key, label, file, lemma, model, expected)
CASES = [
    ("M1.executable", "auth", "auth_M1.txt", "executable", "M1", "verified"),
    ("M1.L1", "L1 alert authenticity", "auth_M1.txt", "L1_alert_authenticity", "M1", "verified"),
    ("M1.L2", "L2 ACK authenticity per vehicle", "auth_M1.txt", "L2_ack_authenticity", "M1", "verified"),
    ("M1.L3", "L3 no cross-vehicle suppression", "auth_M1.txt", "L3_no_cross_vehicle_suppression", "M1", "verified"),
    ("M0.L1", "L1 on the shared-key design", "auth_M0.txt", "L1_alert_authenticity", "M0", "falsified"),
    ("M0.L2", "L2 on the shared-key design", "auth_M0.txt", "L2_ack_authenticity", "M0", "falsified"),
    ("M0.L3", "L3' cell-wide ACK suppression found on the shared-key design", "auth_M0.txt", "L3_no_cross_vehicle_suppression", "M0", "falsified"),
    ("fresh.executable_ts", "executable (time-stamped alert accepted)", "fresh_final/executable_ts.txt", "executable_ts", "M1", "verified"),
    ("fresh.executable_after_car_reboot", "executable after a car reboot", "fresh_final/executable_after_car_reboot.txt", "executable_after_car_reboot", "M1", "verified"),
    ("fresh.L4", "L4 replay outside the window", "fresh_final/L4_replay_outside_window.txt", "L4_replay_outside_window", "M1", "verified"),
    ("fresh.L4b", "L4b at most one acceptance while the seen-set is intact", "fresh_final/L4b_at_most_once.txt", "L4b_at_most_once", "M1", "verified"),
    ("fresh.L5_no_double", "L5 no double acceptance with a car reboot", "fresh_final/L5_no_double_accept_with_car_reboot.txt", "L5_no_double_accept_with_car_reboot", "M1", "verified"),
    ("fresh.L5_ids", "L5 alert ids not reused after a car reboot", "fresh_v2/L5_car_alert_ids_unique.txt", "L5_car_alert_ids_unique", "M1", "verified"),
    ("fresh.L5_ids_bounded", "L5 alert ids not reused after a car reboot, at most 3 ticks", "fresh_bound/L5_car_alert_ids_unique.txt", "L5_car_alert_ids_unique", "M1 (3 ticks)", "verified"),
    ("fresh.L6", "L6 replay inside the window after a base reboot", "fresh_final/L6_base_reboot_replay.txt", "L6_base_reboot_replay", "M1", "falsified"),
    ("fresh.L7", "L7 a no-time alert can be accepted epochs after it was sent", "fresh_final/L7_no_time_alert_can_be_stale.txt", "L7_no_time_alert_can_be_stale", "M1", "verified"),
]


def parse(file: str, lemma: str) -> tuple[str, str]:
    t = (OUT / file).read_text(encoding="utf-8", errors="replace")
    m = re.search(rf"{re.escape(lemma)} \((?:all-traces|exists-trace)\): (verified|falsified)[^\n]*", t)
    if m:
        return m.group(1), m.group(0).split(": ", 1)[1].strip()
    m2 = re.search(r"exit code: (\d+) ; wall time (\d+) s", t)
    if m2 and m2.group(1) == "124":
        return "timeout", f"no result within the limit ({m2.group(2)} s wall time)"
    return "no_result", "output has no result line"


def main() -> None:
    ent, rows = [], []
    for key, label, file, lemma, model, expected in CASES:
        res, detail = parse(file, lemma)
        # for an all-traces lemma 'verified' = proved; for an exists-trace lemma 'verified' = a trace exists; 'falsified' = counterexample found
        rows.append(dict(key=key, label=label, model=model, lemma=lemma, result=res, detail=detail, expected=expected, as_expected=(res == expected)))
        ent.append(dict(name=f"r3.t2.sec.{key}", value=res, unit="tamarin result", origin="FORMAL" if res in ("verified", "falsified") else "NOT_RUN", source_file=SRC,
                        notes=f"{label}; model {model}; expected {expected}; {detail}; file formal/out/{file}" if res in ("verified", "falsified") else f"{label}: {detail}; file formal/out/{file}"))
    proved = [r for r in rows if r["key"] in ("M1.L1", "M1.L2", "M1.L3", "fresh.L4", "fresh.L4b", "fresh.L5_no_double")]
    all_proved = all(r["result"] == "verified" for r in proved)
    attack_found = next(r for r in rows if r["key"] == "M0.L3")["result"] == "falsified"
    l6 = next(r for r in rows if r["key"] == "fresh.L6")["result"] == "falsified"
    l5ids = next(r for r in rows if r["key"] == "fresh.L5_ids")["result"]
    ent.append(dict(name="r3.t2.sec.hT2sec.core_proved", value=int(all_proved), unit="flag", origin="FORMAL", source_file=SRC, notes="L1, L2, L3, L4, L4b and the no-double-acceptance lemma with a car reboot are proved on M1"))
    ent.append(dict(name="r3.t2.sec.hT2sec.attack_found_on_M0", value=int(attack_found), unit="flag", origin="FORMAL", source_file=SRC, notes="Tamarin finds the cell-wide ACK suppression on the shared-key design"))
    ent.append(dict(name="r3.t2.sec.hT2sec.l6_refuted_as_expected", value=int(l6), unit="flag", origin="FORMAL", source_file=SRC, notes="replay inside the window after a base reboot is found"))
    ent.append(dict(name="r3.t2.sec.hT2sec.l5_id_uniqueness", value=l5ids, unit="status", origin="NOT_RUN" if l5ids not in ("verified", "falsified") else "FORMAL", source_file=SRC,
                    notes="the lemma that alert ids are not reused after a car reboot did not finish in 294 s (default search) and 421 s (at most 3 ticks): no proof and no counterexample"))
    ent.append(dict(name="r3.t2.sec.hT2sec.criterion_met", value=int(all_proved and attack_found and l6 and l5ids == "verified"), unit="flag", origin="FORMAL", source_file=SRC,
                    notes="V14 H-T2sec needs L1 to L5 proved, the attack found on M0 and L6 refuted; L5 (ids not reused) is not proved, so the criterion is NOT met as written"))
    record_many(ent, purge_prefixes=("r3.t2.sec.",))
    (ROOT / "results" / "tables" / "r3_t2_formal.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    for r in rows:
        print(r["key"], r["result"], "(expected", r["expected"] + ")")


if __name__ == "__main__":
    main()
