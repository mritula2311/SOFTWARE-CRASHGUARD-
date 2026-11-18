"""Writes docs/05_architecture/FRAME_LAYOUT.md (normative frame layout, working flow, reconciliation of layout, formal models and ns-3 frames) from ``frame_layout.FRAMES`` and the stored keys.

    python -m crashguard.frame_layout_doc

Keys read: vf2.preempt.* (vf2_preempt), r6.b.forge.* (r6_bounds). Writes keys vf3.layout.* (ANALYTICAL: airtime and forgery numbers from formulas).
"""
from __future__ import annotations

import json
from pathlib import Path

from crashguard import frame_layout as FL
from crashguard.lora import airtime_ms
from crashguard.results import record_many

ROOT = Path(__file__).resolve().parents[2]
SRC = "src/crashguard/frame_layout_doc.py"
R = {e["name"]: e["value"] for e in json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))}
ent: list[dict] = []


def A(n: int, sf: int) -> float:
    return airtime_ms(n, sf)


def add(name, v, unit, note):
    ent.append(dict(name=f"vf3.layout.{name}", value=(v if isinstance(v, float) and 0 < abs(v) < 1e-3 else round(v, 6) if isinstance(v, float) else v), unit=unit, origin="ANALYTICAL", source_file=SRC, notes=note))


# (id, what the model or the simulation uses, what the layout has, kind, resolution, what it limits)
ABSTRACTIONS = [
    ("F1", "Vehicle = one name `v` in every model", "32-bit node id in the alert and the ACK; 16-bit short id in the flash and the cancel; a one-byte pending index and no vehicle id in the 8-byte micro frame", "assumption and abstraction",
     "State: uniqueness of the 16-bit short id inside the fleet is an assumption of the layout and is in no model; the model treats the id as an opaque unique value", "Cross-vehicle statements hold only if short ids are unique; a collision is not modelled"),
    ("F2", "Freshness id = one fresh name, or the pair (epoch, sequence), or the triple (boot, epoch, sequence)", "Alert: 32-bit field at offset 10, sequence at offset 42, boot counter at 43 to 46. Flash and cancel: low 16 bits of the field plus a no-time flag. Layout was missing (blocker B5)",
     "document changed", "`FRAME_LAYOUT.md` specifies the fields; the models treat each tuple as one value and do not model byte order or width", "The lemmas say nothing about the reconstruction of the 32-bit field from 16 bits in the flash"),
    ("F3", "Freshness window of two epochs (one or two GPS seconds)", "Window W = 10 s in the simulations and the C ring (`cg_fresh_accept`)", "abstraction", "State: the lemmas (at most once per window) do not use the width, and the statement 'inside the window' is for the model's window", "The 10 s window is not covered by a proof"),
    ("F4", "Seen-set without bound", "Ring of the last R entries (R up to 512), cleared at a base reboot", "abstraction", "State: a replay of an entry that the ring has dropped is outside the model; `ar.r1` measures it by simulation (H-R1b not supported at the held-out burst)", "At-most-once is proved for an unbounded set only"),
    ("F5", "Boot counter: a fresh value per boot, unbounded", "32-bit counter in non-volatile memory; the alert carries 4 bytes, the flash and the cancel carry the low 8 bits (15-byte frame), the micro tag input carries the full 32 bits (big endian)", "document changed and abstraction",
     "Layout adds the byte (15 bytes, airtime unchanged at SF7 and SF9); the model's unbounded value stands for the counter; the 8-bit wrap needs fewer than 256 boots between two frames the base hears", "A car that reboots 256 times or more between two heard frames is outside the rule; not modelled"),
    ("F6", "The freshness lemmas (Tamarin `crash_alert_*`) model the 97-byte alert and the 26-byte ACK only", "Flash and cancel are 14 or 15 bytes", "gap, narrowed",
     "State: the round-6 micro-confirm models (ProVerif and Tamarin) add the flash tag, the micro-confirm and the micro-cancel; no model covers the freshness field of the flash or the cancel", "No formal result for the freshness of the provisional frame"),
    ("F7", "Micro-confirm in the model: `<'MICRO', v, T1, x, m>` carries the vehicle and T1 in clear; the base looks up the pending entry by (v, T1)", "Micro frame (8 bytes) carries a one-byte pending index that the base assigned in the ACK of the provisional frame; the index names the entry (vehicle key, T1, boot counter) and the base verifies the tag under that one entry. ns-3: the 13-byte frame includes the LoRaWAN device address, so ns-3 looks up by address",
     "abstraction", "State: the model's (v, T1) stands for the entry that the index names; the index is outside the MAC input and chosen by the attacker in the model's worst case (the attacker picks (v, T1) already), so it gives the attacker nothing more. The proofs are for lookup by (v, T1); the index lookup has one candidate, so the forgery probability per frame is the single-entry value 2^-40 (section 7). The index variants of the ProVerif and Tamarin models (`formal/proverif/vf3_micro_confirm_index.pv`, `formal/vf3_micro_confirm_index.spthy`, outputs in `formal/out/vf3/`) carry a pending table keyed by the index and an attacker-chosen index: acceptance implies the vehicle sent that micro-confirm, binding to its provisional frame and the micro-cancel property are proved in both tools (`vf3.formal.*`)", "The index lookup itself (a table slot, its reuse after expiry) is not modelled"),
    ("F8", "Micro-cancel separated by the letter 'X' in the MAC input", "Micro-confirm and micro-cancel share the letter 'M'; they differ in bit 7 of byte 0, which is inside the tagged bytes", "abstraction", "State: separation is by a bit that the tag covers, which has the same effect as a letter; the exact encoding is not modelled", "A cross-use of confirm and cancel is excluded by the model, and by the layout through the type bit"),
    ("F9", "Perfect MAC, no truncation", "HMAC-SHA256 truncated to 8 bytes (5 bytes for the micro frame)", "abstraction", "State: forgery bounds 2^-64 and 2^-40 per attempt are ANALYTICAL and separate", "No computational result"),
    ("F10", "Not in a formal model", "ns-3 micro frame: 13 bytes (the smallest LoRaWAN frame) against the 8-byte design", "simulation against design", "State: the 8-byte design is within the evaluated size; at SF7 and SF9 the 13-byte frame has the airtime of the 14-byte flash, so the ns-3 airtime of the micro scheme is higher than the design's (section 7), and the airtime results are conservative for the 8-byte frame; the saving is against the 97-byte confirm only", "ns-3 results are conservative for the micro airtime"),
    ("F11", "Hash ratchet K(i+1) = H(K(i), label), at most 3 steps (ProVerif, Tamarin)", "No frame has a ratchet step field; the keys of the frames are the per-vehicle keys of R4 and the micro tag uses the boot counter, not a ratchet", "gap", "State: forward secrecy is a statement about the symbolic ratchet within three steps; an implementation needs a step index (derived from the boot counter and the count of acknowledged alerts, or a new field)", "No claim of forward secrecy for the frames as laid out"),
    ("F12", "Quarantine: counters per claimed id, alert kinds ok, implausible, repeat; 3 ids, 6 slots, 4 attacker frames per slot", "The claimed id is in clear in every frame except the micro frame; the base code verifies the tag before anything else and has no quarantine counter", "abstraction", "State: the result is for the modelled mechanism (rule A is attackable, rule B holds by construction); counting after verification is a design rule, not an implemented check", "No general result beyond the modelled counters"),
    ("F13", "Per-vehicle key = perfect function kdf(master, v)", "HMAC-SHA256(master, id), cached per new id", "abstraction", "State: symbolic function stands for the HMAC", "No computational result"),
    ("F14", "ACK = <'ACK', v, f, tag>, f one value", "ACK names (node id, acked event id, acked freshness field) and carries a base counter", "abstraction", "State: f stands for the pair (event id, freshness field); the base counter is not modelled and enters no lemma", "None for the lemmas stated"),
    ("F15", "Domain separation by letters ('A', 'ACK', 'F', 'M', 'X', 'P')", "By the type value inside the tagged bytes (alert 1, ACK 2, flash 4, cancel 5 in the nibble) and by lengths; micro: ASCII 'M' and the type bit", "abstraction", "State: each letter stands for the type value of section 3; the round-4 control without a letter (`crash_alert_prov_nodomain`) is falsified as expected", "Separation across frame kinds is proved for the letters, not for the byte encodings"),
    ("F16", "No time in any model", "Confirm due at 1.808 s, retries after the receive windows, hourly allowance", "abstraction", "State: models are untimed; timing results are from simulation and enumeration (`timed` models of round 3)", "No proof about delivery before a deadline"),
]


def table_for(name: str) -> list[str]:
    f = FL.FRAMES[name]
    out = ["| Offset | Size | Field | In the tag | Source | Meaning |", "|---:|---:|---|---|---|---|"]
    for off, size, fld, cov, src, note in f["rows"]:
        out.append(f"| {off} | {size} | {fld} | {'yes' if cov else 'is the tag'} | {src} | {note} |")
    return out


def main() -> None:
    L = ["# Frame layout (normative), working flow and reconciliation", "", "<!-- header:start -->", "<!-- header:end -->", "",
         "Generated by `python -m crashguard.frame_layout_doc` from `src/crashguard/frame_layout.py` (the field tables) and the stored keys. `tests/test_frame_layout.py` checks the CODE rows against `packet.py` and `sct_protocol.py` and the DESIGN rows against the reference functions. "
         "This document closes blocker B5 of the final verification run (the byte layout of the freshness field and the boot counter).", "",
         "**Status of each row.** CODE: an encoder in the repository fixes it (`packet.py`, `sct_protocol.py`, `firmware_rd/cg_rd.c`, `firmware_r6/cg_r6.c`). DESIGN: chosen in the delta verification run to close the gap; no encoder in the repository writes it, no stored result depends on it, and no frame size of an evaluated design changes. "
         "A choice of the author overrides a DESIGN row. The firmware does not implement any of this (no physical hardware was used).", "",
         "**Conventions.** Little-endian for every multi-byte field of every frame. The tag is the leading bytes of HMAC-SHA256 under the per-vehicle key K_vehicle = HMAC(master, vehicle id) (R4), computed over every byte that precedes it, and compared without early exit. "
         "The micro-confirm tag input uses a big-endian boot counter (`cg_micro_tag`); it is a MAC input, not a frame field.", "",
         "## 1. The five frames of the two-stage alert", "", "| Frame | Bytes | Tag bytes | Sent when |", "|---|---:|---:|---|",
         "| Provisional flash | 14 (evaluated) or 15 (with the boot byte, recommended) | 8 | at the early-exit decision |",
         "| Full alert | 97 | 8 | at the full-window decision, or alone when there was no early alarm |",
         "| ACK | 26 | 8 | by the base, for a flash (acked event id 0xFFFFFFFF) or an alert |",
         "| Cancel | 14 or 15 | 8 | at the full-window decision when the full window does not alarm; three transmissions 0.3 s apart (ns-3) without acknowledgement |",
         "| Micro-confirm and micro-cancel | 8 (design); 13 in ns-3 | 5 | after the flash was acknowledged and while the base holds its pending entry (30 s) |", ""]
    for i, (name, title) in enumerate((("ALERT", "Full alert, 97 bytes"), ("ACK", "ACK, 26 bytes"), ("FLASH-14", "Provisional flash, 14 bytes (the evaluated frame)"), ("CANCEL-14", "Cancel, 14 bytes"), ("FLASH-15", "Provisional flash with the boot byte, 15 bytes (recommended)"),
                                      ("CANCEL-15", "Cancel with the boot byte, 15 bytes"), ("MICRO", "Micro-confirm and micro-cancel, 8 bytes"))):
        L += [f"### 2.{i + 1} {title}", ""] + table_for(name) + [""]
    L += ["### 2.8 The freshness field", "",
          "- **Time-stamped form** (the vehicle has a GPS fix): bit 31 = 0; bits 30 to 0 = seconds since 1980-01-06 00:00:00 UTC as the receiver reports them (the base uses the same scale; the window W = 10 s is not affected by the leap-second offset if both sides use one scale). Valid until the year 2116.",
          "- **No-time form** (no fix): bit 31 = 1; bits 30 to 16 = epoch = boot counter modulo 2^15, written once per boot; bits 15 to 0 = counter of alerts since boot.",
          "- **Identifier of an alert** for the freshness rule: the triple (sender, field, sequence in second); with the boot counter, (sender, boot, field, sequence). The base accepts a time-stamped alert if |field - now| <= W and the triple is not in its ring of R entries; this is `cg_fresh_accept(ring, field, seq, now, W, R)`.",
          "- **In the flash and the cancel** only the low 16 bits are sent, with the no-time flag. For a time-stamped frame the base rebuilds the 32-bit value that is congruent to those 16 bits modulo 2^16 and nearest its own clock (`reconstruct_field`; unambiguous while the sender's clock is within 2^15 s of the base's, and W is 10 s). For a no-time frame it uses the epoch it holds for the vehicle.",
          "- **Two flashes of one vehicle inside one GPS second** carry the same 16 bits and no sequence: the second is treated as a repeat of the earlier one and is acknowledged again, not processed again. The full alert carries the sequence, so no alert is lost.",
          "- **Boot counter.** 32 bits in non-volatile memory, increased and written once per boot (the write the boot-epoch design already counts). The alert carries all 32 bits; the 15-byte flash and cancel carry the low 8 bits, and the base rebuilds the 32-bit value as the smallest value not below the last one it holds for the vehicle (`reconstruct_boot`). "
          "The 14-byte frames of the evaluated design carry no boot byte; they are safe only if a reboot takes at least one second (the ProVerif finding, `FORMAL_RERUN.md`).", "",
          "## 3. Tag lengths and domain separation", "", "| Frame | Tag | Separation inside the tagged bytes | Letter in the formal models |", "|---|---|---|---|"]
    for who, how, letter in FL.SEPARATION:
        L.append(f"| {who} | {'5 bytes' if 'micro' in who else '8 bytes'} | {how} | {letter} |")
    L += ["", "The letters of the models are abstractions of the type values and lengths above (row F15 of section 8). Forgery effort per attempt: 2^-64 for an 8-byte tag and 2^-40 for the 5-byte micro tag, which the pending index keeps at one candidate entry (ANALYTICAL; section 7).", "",
          "## 4. Pending table and the lookup of a micro frame", "",
          "The base keeps a pending entry (vehicle key, T1, boot counter) for every provisional frame it acknowledged, for 30 s (the frozen lifetime of R6-1, `r6.r1.ns3.params.pend_s`), in a table slot of one byte. The ACK of the provisional frame returns the slot number in the low byte of its `base counter`; the micro frame carries it as its leading byte. "
          "The base verifies the micro tag under the one entry that the index names (`micro_lookup`), and treats the frame as the confirm or cancel of that entry. A frame whose index is unknown or whose tag fails (an expired entry, a car that rebooted so that the base's boot counter is old, or a changed index) is rejected, and the node's retry then sends the full frame (the fallback of V17 section 3). The 7-byte lookup by trial (`micro_lookup_trial`) was rejected: it costs one tag computation per pending entry and multiplies the forgery probability by their number. The micro frame is a smaller frame, not a different authority: the full alert still carries the content.", "",
          "## 5. The 8-byte design against the 13-byte ns-3 frame", "",
          "The LoRaWAN module of ns-3 sends at least 13 bytes (its header with the 4-byte device address and the message integrity code), so the simulated micro frame has 13 bytes (`R6_MICRO_BYTES`). The design frame has 8 bytes (the 7-byte frame of `cg_micro_pack` behind the index), so it stays within the evaluated size and the airtime results are conservative for it. The airtime in section 7 shows that at SF7 the 13-byte frame costs the airtime of the 14-byte flash, so against the 14-byte flash the micro frame saves nothing in the simulation; the saving is against the 97-byte confirm. The design frame would be shorter: "
          + f"{A(8, 7):.1f} ms against {A(14, 7):.1f} ms at SF7.", ""]
    # airtime table
    L += ["## 6. Working flow of one event, and what happens to an unacknowledged flash", "",
          "1. Trigger at t = 0. The early-exit rule decides at t_E (median 50 ms, mean 112 ms on the held-out events) and, if it alarms, the node queues the flash (ready at t_E + 8 ms).",
          "2. The full window (1.8 s plus 8 ms) decides at T_F = 1.808 s: a confirm (97-byte alert, or the micro-confirm if the flash was acknowledged and the entry is pending) or three cancels (14 bytes, 0.3 s apart, unacknowledged).",
          "3. The base accepts a flash (state PRE: crash reported, severity pending), a confirm (CONFIRMED, with or without a flash) or a cancel (CANCELLED, only if the base holds that event).",
          "", "**What the code does with an unacknowledged flash (read from `xsim_alert.cc` and `r3_t1.py`).** In the evaluated two-stage policies (r3t, r6m) and in the trace replays the node keeps one FIFO queue per event: [flash, confirm] or [flash, cancel, cancel, cancel]. "
          "The flash stays at the head of the queue until its acknowledgement arrives or its 4 tries are used (each try is followed by the two receive windows, 0.32 s in ns-3). Nothing is withdrawn when the full decision is ready. "
          "**For a cancel:** the flash is still retried to the end of its stage and the cancel is sent after it, whether or not the flash was ever delivered (the base rejects a cancel for an event it does not hold). "
          "**For a confirm:** the confirm does not replace the flash; both are sent, the flash stage ahead of the confirm, and in the micro policy r6m the node sends the full 97-byte confirm when the flash was not acknowledged. "
          "**Only the policy r3a** (24-byte provisional frame, V15, not supported) preempts: a ready confirm or cancel takes the radio ahead of the provisional repeats, a due cancel withdraws the queued provisional frames, and the acknowledgement of the confirm ends the provisional repetition.", "",
          "**Design recommendation (not implemented in r3t or r6m): preempt.** When the full decision is ready, withdraw the remaining flash tries and send the decision's frames. "]
    rows = {}
    for sf in (7, 8, 9, 10, 11, 12):
        rows[sf] = (R[f"vf2.preempt.saving.sf{sf}.median.late_flash_tries"], R[f"vf2.preempt.saving.sf{sf}.median.saved_airtime_s"], R[f"vf2.preempt.saving.sf{sf}.median.last_try_end_s"])
    L += ["ANALYTICAL saving, from the time-on-air formula: the flash tries start at s_f + j (A14 + 0.32 s), j = 0 to 3; the tries that start at or after T_F are the ones that preemption removes.", "",
          "| SF | A14 (ms) | tries that start at or after T_F (of 4) | airtime saved per event with an unacknowledged flash (s) | end of the 4th try (s) |", "|---|---:|---:|---:|---:|"]
    for sf, (n, s, e) in rows.items():
        L.append(f"| {sf} | {A(14, sf):.2f} | {n} | {s:.3f} | {e:.3f} |")
    L += ["", "At SF7 to SF9 all four tries end before T_F (the 4th ends at "
          + f"{rows[9][2]:.2f} s at SF9), so preemption saves nothing there and does not change the stored results. From SF10 it removes {rows[10][0]} try (the 4th would end at {rows[10][2]:.2f} s, after T_F), and at SF11 and SF12 {rows[11][0]} tries, which also delays the confirm behind the flash stage.", "",
          "**Formal check (FORMAL, bounded; `python -m crashguard.vf2_preempt`, keys `vf2.preempt.*`).** An untimed model with one event, one base, every try lost, delivered with a lost ACK, or delivered and acknowledged, 1 to 4 flash tries before the decision, a confirm of up to 4 tries or three cancels, enumerated exhaustively for the FIFO node and the preempting node. "
          f"Result: {int(R['vf2.preempt.cases'])} (decision, tries) cases; the set of base states reachable at the end is the same for both nodes (preemption adds no terminal state); a delivered final-stage frame always takes the base out of PRE; "
          "the base can stay in PRE with no further frame **only if every frame of the final stage was lost** (all four confirm tries, or all three unacknowledged cancels), and this holds for the FIFO node as much as for the preempting one. "
          "Preemption therefore cannot leave the base in pre-alert forever by itself; the stuck state is a property of the unconfirmed cancel and of a lost confirm, and a base-side timeout (PRE to EXPIRED when neither confirm nor cancel arrives) removes it in both variants "
          f"(`pre_alert_forever_with_timeout` = {int(R['vf2.preempt.cancel.k2.preempt.pre_alert_forever_with_timeout'])} for the cancel and {int(R['vf2.preempt.confirm.k2.preempt.pre_alert_forever_with_timeout'])} for the confirm). The code has no such timeout; it is a design recommendation. The model does not cover time, duty limits or several vehicles.", "",
          "## 7. Airtime and forgery numbers (ANALYTICAL)", "", "| SF | 7 bytes | 8 bytes | 13 bytes | 14 bytes | 15 bytes | 26 bytes | 97 bytes |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for sf in (7, 8, 9, 10, 11, 12):
        a = {n: A(n, sf) for n in (7, 8, 13, 14, 15, 26, 97)}
        for n, v in a.items():
            add(f"air.sf{sf}.b{n}_ms", v, "ms", f"time on air of {n} bytes at SF{sf}")
        L.append(f"| {sf} | " + " | ".join(f"{a[n]:.2f}" for n in (7, 8, 13, 14, 15, 26, 97)) + " |")
    eq = [sf for sf in (7, 8, 9, 10, 11, 12) if A(13, sf) == A(14, sf) == A(15, sf)]
    add("equal_13_14_15_sfs", ",".join(map(str, eq)), "SF list", "spreading factors at which 13, 14 and 15 bytes have the same airtime")
    L += ["", f"Times in ms (125 kHz, coding rate 4/5, explicit header, CRC, 8 preamble symbols). 13, 14 and 15 bytes have the same airtime at SF{', SF'.join(map(str, eq))}; the 15-byte frame costs more airtime at the other spreading factors. "
          f"The 13-byte ns-3 micro frame is {A(13, 7) / A(8, 7):.2f} times the 8-byte design at SF7 and {A(13, 9) / A(8, 9):.2f} times at SF9.", "",
          "**Forgery with the pending index.** The base verifies one micro frame under one entry, so the chance that a random 5-byte tag passes is 2^-40 per frame, the single-vehicle value. At the attacker's ceiling of 36 s / A8 frames per hour at SF7 (the 1% allowance), the expected years to one accepted forgery are 2^40 / frames per year (the formula of `r6.b.forge.tag5.expected_years`, with the 8-byte frame time). The rejected lookup by trial, for comparison, tests n entries per frame:", "",
          "| Lookup and pending entries n | Probability per frame | Expected years to one forgery |", "|---:|---:|---:|"]
    fr = 36.0 / (A(8, 7) / 1000.0)
    p1 = 2.0 ** -40
    y1 = 1.0 / (p1 * fr * 8766)
    add("forge.index.p_per_frame", p1, "probability", "2^-40: one candidate entry")
    add("forge.index.expected_years", y1, "years", "1 / (2^-40 x frames per year), frames per hour = 36 s / A8 at SF7 (the formula of r6.b.forge.tag5.expected_years with the 8-byte frame time)")
    add("forge.index.frames_per_hour", fr, "frames", "36 s / A8 at SF7")
    L.append(f"| pending index (the design): 1 entry | {p1:.3g} | {y1:,.0f} |")
    for n in (10, 60, 1000):
        p = n * 2.0 ** -40
        yrs = 1.0 / (p * fr * 8766)
        add(f"forge.trial.n{n}.p_per_frame", p, "probability", "n x 2^-40")
        add(f"forge.trial.n{n}.expected_years", yrs, "years", "1 / (n x 2^-40 x frames per year), frames per hour = 36 s / A8 at SF7 (the rejected lookup by trial)")
        L.append(f"| trial lookup (rejected): {n} entries | {p:.3g} | {yrs:,.0f} |")
    L += ["", f"The stored value `r6.b.forge.tag5.expected_years` ({R['r6.b.forge.tag5.expected_years']:,.0f} years) used the 7-byte frame time; the 8-byte frame has {"the same" if all(A(8, g) == A(7, g) for g in (7, 8, 9, 10, 11, 12)) else "a different"} time on air as the 7-byte frame at every spreading factor from 7 to 12 ({A(8, 7):.2f} ms at SF7), so the figure of the design is {y1:,.0f} years (the stored key is not changed). "
          "The pending index restores the single-vehicle value whatever the number of pending entries.", "",
          "## 8. Reconciliation of the layout, the formal models and the ns-3 frames", "",
          "Rule for the paper: the proofs cover the protocol at the level of the stated message structure; the abstractions in this table are the ones that apply. Rows F1 to F5 are the five model-to-frame mismatches listed in `docs/04_audits/FORMAL_FIELD_CHECK.md`, F6 is its gap; F7 to F16 are added here. No stored result was changed: every row is resolved by a change in a document or by a stated abstraction.", "",
          "| ID | In the model or the simulation | In the layout | Kind | Resolution | What it limits |", "|---|---|---|---|---|---|"]
    for r in ABSTRACTIONS:
        L.append("| " + " | ".join(x.replace("|", "/") for x in r) + " |")
    add("abstraction_rows", len(ABSTRACTIONS), "rows", "rows of the abstraction table of FRAME_LAYOUT.md section 8")
    record_many(ent, purge_prefixes=("vf3.layout.",))
    (ROOT / "docs" / "05_architecture" / "FRAME_LAYOUT.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("written", len(L), "lines;", len(ABSTRACTIONS), "abstraction rows")


if __name__ == "__main__":
    main()
