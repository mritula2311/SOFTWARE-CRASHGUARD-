"""S4 (H-S5): the repository's real security suite on the simulated H4 scenarios (SIMULATED_HW_FORMAT).

Design and criteria: docs/02_preregistration/PREREGISTRATION_V11.md section 2.3, H-S5. Three parts:
(1) the repository's attack suite (`attacks.run_cases`, 48 cases, and `attacks_extra.run_cases`, 10 cases), listed once with a category per case;
(2) the nine simulated scenarios of `security_H4.json` (S01 to S09, 10 attempts each) re-run on the REAL code (`packet`, `verifier.BaseVerifier`, `node_accepts_ack`);
(3) the counter behaviour of the repository's reference verifier after a base reboot, persisted against RAM-only, set beside the S06 and S08 findings of the simulated model.
The ESP32 firmware source is not in this repository, so its counter behaviour is NOT_RUN; the reference verifier and `docs/01_protocol/PACKET_FORMAT.md` state that the counter is persisted.
Keys ``sh.s4.*``.

    python -m crashguard.sh_s4
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pandas as pd
from scipy.stats import binom

from crashguard import attacks as A
from crashguard import attacks_extra as X
from crashguard import packet as P
from crashguard import verifier as V
from crashguard.results import record_many

SRC = "src/crashguard/sh_s4.py"
H4 = Path("data/simulated_hardware/protocol_logs/security_H4.json")
ACCEPTED = (V.ACCEPT, V.ACCEPT_NO_ACK)
# Indices of the base suite (`attacks.run_cases`) that are documented gaps or demonstrations (the case shows a known limit, so "accept" is the expected outcome) and of the property or rejection
# checks that are not single packets. Everything whose expected outcome starts with "reject" is an attack that must fail.
GAP = {32: "base reboot with the counter lost: a recorded alert is accepted again (the documented gap; R1 addresses it)", 33: "flood without a limit exhausts the base ACK budget (the demonstration that motivates the limit)",
       34: "genuine alert during an unlimited flood is accepted without an ACK", 47: "an alert for another node id signed with the shared key is accepted (the shared-key limit; R4 addresses the ACK side)"}
ATTACK_PROPERTY = {12, 20, 35, 36, 37, 38, 39, 41, 42, 45}  # replay leaves state unchanged; forged alert does not advance the counter; flood limits; bit flips; truncation


def categorise_base(cases: list[dict]) -> list[dict]:
    out = []
    for i, c in enumerate(cases):
        if i in GAP:
            cat = "documented gap"
        elif str(c["expected"]).startswith("reject") or i in ATTACK_PROPERTY or c["expected"] == "reack_limited":
            cat = "attack, must fail"
        else:
            cat = "control or format check"
        out.append(dict(suite="base", idx=i, case=c["case"], expected=c["expected"], observed=c["observed"], match=bool(c["match"]), category=cat))
    return out


def categorise_ext(cases: list[dict]) -> list[dict]:
    out = []
    for i, c in enumerate(cases):
        e = str(c["expected"])
        cat = "attack, must fail" if ("reject" in e or "0 accepted" in e) else "control or format check"
        out.append(dict(suite="extension", idx=i, case=c["case"], expected=c["expected"], observed=c["observed"], match=bool(c["match"]), category=cat))
    return out


def real_scenarios(attempts: int = 10) -> list[dict]:
    """S01 to S09 of the simulated H4 file on the real verifier. An attack succeeds only if the base ACCEPTs (processes) an alert it must not, or the car accepts a forged ACK."""
    rows = []

    def alert(ctr, event=1, key=A.KEY):
        return P.encode_alert(A._alert(ctr, event), key)

    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        for a in range(attempts):
            v = A._fresh(d)
            dec, ack = v.handle(alert(a + 1))
            rows.append(dict(scenario="S01 valid alert (control)", attempt=a + 1, decision=dec, attack=False, attack_succeeded=False, ack_valid=ack is not None and V.node_accepts_ack(ack, A.KEY, A.NODE, 1, a + 1)))
            v = A._fresh(d)
            dec, _ = v.handle(alert(a + 1, key=A.OTHER_KEY))
            rows.append(dict(scenario="S02 forged tag (wrong key)", attempt=a + 1, decision=dec, attack=True, attack_succeeded=dec in ACCEPTED))
            v = A._fresh(d)
            raw = bytearray(alert(a + 1))
            raw[18] ^= 1
            dec, _ = v.handle(bytes(raw))
            rows.append(dict(scenario="S03 tampered field", attempt=a + 1, decision=dec, attack=True, attack_succeeded=dec in ACCEPTED))
            v = A._fresh(d)
            v.handle(alert(a + 5, 1))
            v.handle(alert(a + 9, 2))
            dec, _ = v.handle(alert(a + 5, 1))
            rows.append(dict(scenario="S04 replay of an old alert", attempt=a + 1, decision=dec, attack=True, attack_succeeded=dec in ACCEPTED))
            fake = P.encode_ack(P.Ack(A.NODE, 1, a + 1, 1), A.OTHER_KEY)
            ok = V.node_accepts_ack(fake, A.KEY, A.NODE, 1, a + 1)
            rows.append(dict(scenario="S05 spoofed ACK to the car", attempt=a + 1, decision="car accepts ACK" if ok else "car rejects ACK", attack=True, attack_succeeded=bool(ok)))
            # S06: base rebooted. persisted counter -> the old alert is not processed again; RAM-only (the model of a defect) -> accepted
            v = A._fresh(d)
            v.handle(alert(a + 9, 2))
            v2 = V.BaseVerifier(A.KEY, d / "counters.json")  # reboot, same store
            dec, _ = v2.handle(alert(a + 5, 1))
            rows.append(dict(scenario="S06 base reboot, counter persisted", attempt=a + 1, decision=dec, attack=True, attack_succeeded=dec in ACCEPTED))
            v3 = V.BaseVerifier(A.KEY, None)  # RAM only: the counter is lost at reboot
            v3.handle(alert(a + 9, 2))
            v3 = V.BaseVerifier(A.KEY, None)
            dec, _ = v3.handle(alert(a + 5, 1))
            rows.append(dict(scenario="S06m base reboot, counter NOT persisted (model of a defect)", attempt=a + 1, decision=dec, attack=True, attack_succeeded=dec in ACCEPTED, defect_model=True))
            v = A._fresh(d)
            v.handle(alert(a + 1))
            dec, _ = v.handle(alert(a + 1))
            rows.append(dict(scenario="S07 ACK lost, same packet again", attempt=a + 1, decision=dec, attack=False, attack_succeeded=False))
            v = A._fresh(d)
            v.handle(alert(a + 10, 3))
            dec, _ = v.handle(alert(1, 4))
            rows.append(dict(scenario="S08 car counter restarted (availability cost)", attempt=a + 1, decision=dec, attack=False, attack_succeeded=False, availability_loss=dec not in ACCEPTED))
            v = A._fresh(d)
            v.handle(alert(1))
            res = [v.handle(alert(1))[0] for _ in range(20)]
            rows.append(dict(scenario="S09 replay flood, 20 repeats", attempt=a + 1, decision=f"{sum(r in ACCEPTED for r in res)} of 20 accepted", attack=True, attack_succeeded=any(r in ACCEPTED for r in res), n_replays=20))
    return rows


def main() -> None:
    base = categorise_base(A.run_cases())
    ext = categorise_ext(X.run_cases())
    suite = pd.DataFrame(base + ext)
    suite.to_csv("results/tables/sh_s4_suite.csv", index=False)
    n_total = len(suite)
    cat = suite.category.value_counts().to_dict()
    n_match = int(suite.match.sum())
    sc = pd.DataFrame(real_scenarios())
    sc.to_csv("results/tables/sh_s4_scenarios.csv", index=False)
    h4 = json.loads(H4.read_text(encoding="utf-8"))
    simtab = pd.DataFrame(h4["records"]).groupby(["case_id", "scenario"]).base_result.agg(lambda s: "; ".join(f"{k} x{v}" for k, v in s.value_counts().items())).reset_index()
    simtab.to_csv("results/tables/sh_s4_h4_file.csv", index=False)
    defect = sc["defect_model"].eq(True) if "defect_model" in sc else pd.Series(False, index=sc.index)
    atk = sc[sc.attack & ~defect]
    n_atk_attempts = int(atk.n_replays.fillna(1).sum()) + int((suite.category == "attack, must fail").sum())
    n_succ = int(atk.attack_succeeded.sum()) + int(((suite.category == "attack, must fail") & ~suite.match).sum())
    p = float(binom.cdf(n_succ, n_atk_attempts, 0.05))  # P(X <= observed; N, 0.05)
    # persisted counter behaviour of the reference verifier
    pers = sc[sc.scenario.str.startswith("S06 ")]
    ram = sc[sc.scenario.str.startswith("S06m")]
    persisted_ok = bool((~pers.attack_succeeded).all())
    ram_accepts = bool(ram.attack_succeeded.all())
    s08 = sc[sc.scenario.str.startswith("S08")]
    ent: list[dict] = []

    def add(name, value, unit, notes="", origin="SIMULATED_HW_FORMAT"):
        ent.append(dict(name=f"sh.s4.{name}", value=value, unit=unit, origin=origin, source_file=SRC, notes=notes))

    add("suite.total", n_total, "cases", "ONE number: the repository's base suite (48, `attacks.cases_total`) plus the extension suite (10, `attacks_extra`); the nine scenarios of the simulated H4 file are counted separately")
    add("suite.base", len(base), "cases", "attacks.run_cases")
    add("suite.extension", len(ext), "cases", "attacks_extra.run_cases")
    add("suite.matching_expected", n_match, "cases", "cases whose observed outcome equals the expected outcome")
    for k, v in cat.items():
        add(f"suite.category.{k.replace(' ', '_').replace(',', '')}", int(v), "cases", "category assigned in sh_s4 (listed per case in results/tables/sh_s4_suite.csv)")
    add("suite.note_30_and_38", "30 and 38 are not found in any current file or key", "text", "CLAIM_EVIDENCE.md and the README quote 48 (`attacks.cases_total`); no current document or key gives 30 or 38, so those earlier figures cannot be reproduced and are dropped")
    add("scenarios.attempts", int(len(sc)), "attempts", "S01 to S09 on the real verifier, 10 attempts each (plus S06m, the RAM-only defect model)")
    add("scenarios.attack_attempts_counted", n_atk_attempts, "attempts", "attack cases of the suites plus attack attempts of S02 to S06 and S09 (S09 counts 20 replays per attempt); S06m is excluded because it models a defect")
    add("scenarios.attacks_accepted", n_succ, "attempts", "attack attempts that were accepted by the base or by the car")
    add("counter.reference_verifier_persists", int(persisted_ok), "flag", "S06 on `verifier.BaseVerifier` with a counter store: an older alert after a base reboot is not accepted (10 of 10)")
    add("counter.ram_only_accepts_old_alert", int(ram_accepts), "flag", "S06m on a verifier without a store: the older alert is accepted (10 of 10), which is the S06 finding of the simulated model")
    add("counter.car_restart_rejected", int(bool(s08.availability_loss.all())), "flag", "S08: a car whose counter restarts at 1 is rejected by a base that persists its counter (availability cost, 10 of 10)")
    add("counter.firmware", "NOT_RUN", "text", "the ESP32 firmware source is not in this repository; `docs/01_protocol/PACKET_FORMAT.md` and `docs/05_data_code/FIRMWARE_SYNC.md` state that the counter must be persisted in flash, but no code or log shows whether it is",
        origin="NOT_RUN")
    add("h4_file.scenarios", int(h4["records"] and len({r["case_id"] for r in h4["records"]})), "scenarios", "scenarios in the supplied security_H4.json, 10 attempts each; S06 and S08 are model scenarios (a non-persisting base; a restarted car counter)")
    add("hS5.criterion_met", int(n_succ == 0 and persisted_ok), "flag", "zero accepted attacks and the persisted-counter test passes")
    add("hS5.p_raw", float(f"{p:.3e}"), "p", "exact binomial P(X <= observed accepted; N attempts, 0.05)")
    record_many(ent, purge_prefixes=("sh.s4.",))
    print("suite", n_total, cat, "matching", n_match)
    print(sc.groupby("scenario").agg(n=("attempt", "count"), attack_succeeded=("attack_succeeded", "sum"), decision=("decision", lambda s: s.value_counts().to_dict())).to_string())
    print("N", n_atk_attempts, "succ", n_succ, "p", p, "persisted_ok", persisted_ok, "ram accepts", ram_accepts)


if __name__ == "__main__":
    main()
