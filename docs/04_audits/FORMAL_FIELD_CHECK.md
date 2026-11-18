# Formal models against the frame layout (V2.4)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-15 |
| Owner | Mritula S |
| Scope | Message fields of every formal model compared with the frame layout, the firmware path and the paper; every mismatch listed. |
| Evidence labels used | ANALYTICAL |
| Abbreviations | ACK = acknowledgement frame; GPS = Global Positioning System; HMAC = hash-based message authentication code; KDF = key derivation function; MAC = message authentication code |
<!-- header:end -->

**Update of the delta verification run (2026-11-16).** The byte layout that this check found missing is now specified in `docs/05_architecture/FRAME_LAYOUT.md`, and its section 8 resolves each mismatch below (five mismatches and one gap) by a document change or a stated abstraction, with ten further rows. The tables below are the record of the check as it was made.

Method. The message terms of every model file in `formal/` were read next to the byte layouts in `src/crashguard/packet.py`, `src/crashguard/sct_protocol.py` and `firmware_rd/cg_rd.h` and `cg_rd.c`. The paper has no frame-layout figure; frame sizes appear in the text and in the architecture figure (`paper/figures/pp_arch.png`): 97-byte alert, 26-byte acknowledgement, 14-byte flash and cancel, 8-byte tag. Those sizes agree with the code (table 1).

## 1. Sizes: code against paper

| Frame | Python reference | C firmware path | Paper | Match |
|---|---|---|---|---|
| Full alert | 97 bytes: 89 body + 8 tag (`ALERT_LEN`, `ALERT_BODY_LEN`, `TAG_LEN`) | 97 / 89 / 8 (`CG_ALERT_LEN`, `CG_ALERT_BODY`, `CG_TAG_LEN`); `cg_encode_alert` writes the same field order | 97 bytes | yes |
| ACK | 26 bytes: 18 body + 8 tag | 26 / 18 | 26 bytes | yes |
| Provisional flash and cancel | 14 bytes: 6 body + 8 tag (`FLASH_LEN`, `FLASH_BODY_LEN`) | no flash encoder in `cg_rd.c` (only the D1 retry logic, the alert and the freshness ring) | 14 bytes | yes (Python only; the flash is not in the C path) |
| Tag | HMAC-SHA256 truncated to 8 bytes over all preceding body bytes | the same (`cg_hmac_sha256`, 8 bytes, constant-time compare) | 8 bytes; 2^-64 per forgery attempt (ANALYTICAL) | yes |

## 2. Fields: models against the layout

| Item | Layout (reference and C path) | Tamarin `crash_alert_auth` (M1 and M0) | Tamarin `crash_alert_fresh` and `_bootctr` | ProVerif `carid_*` | Result |
|---|---|---|---|---|---|
| Alert fields | version, type, node_id (4), event_id (4), counter (4), timestamp_ms (4), 12 payload fields, 47 reserved, tag (8) | `<'ALERT', v, c, cls, mac(key, <'A', v, c, cls>)>`: vehicle, one fresh field, class | same with field `<e, n>` (epoch, sequence) or `<b, e, n>` | `(v, id, mac(kdf(km, v), (v, id)))` | abstraction: every payload field is one value `cls`; event_id, counter and timestamp are one name. Acceptable for the lemmas (the tag covers all bytes). No mismatch of the properties proved |
| ACK fields | version, type = 2, node_id, acked event_id, acked counter, base counter, tag | `<'ACK', v, f, mac(kdf(km, v), <'ACK', v, f>)>` for M1; shared key `kdf(km, 'cell')` for M0 | same ACK | not modelled (car side only) | the base counter is not modelled (it does not enter any lemma); `f` stands for the pair (event_id, counter). M0 and M1 differ as the paper says (key and binding) |
| Per-vehicle key | K_i = HMAC(master, vehicle id), one KDF per new id, cached (`ar_r4.kdf`) | `kdf(km, v)` | `kdf(km, v)` | `kdf(km, v)` | match (a symbolic function stands for the HMAC) |
| Domain-separation letters | message type inside the tagged body (alert 1, ACK 2, flash 4, cancel 5) and different lengths | letters `'A'` (alert) and `'ACK'` | `'A'` | none (one message kind) | match in effect for the alert and the ACK. The ProVerif car-side models have no letter; they model one kind of frame, so no lemma is affected. The round-4 model `crash_alert_prov` adds `'P'`; its control `_nodomain` (one letter for both) is falsified as expected |
| Short node id | the flash carries only the low 16 bits of node_id (`sct_protocol`); the alert carries 32 bits | vehicle `v` is one name | same | same | **mismatch (assumption)**: uniqueness of the 16-bit id within the fleet is an assumption of the layout and is not part of any model |
| Freshness field | `PACKET_FORMAT.md` and `sct_protocol.py`: a persisted 32-bit counter (the flash carries its low 16 bits, rebuilt within +-32,768 of the last value the base has seen). `ar_r1.py`, `ARCHITECTURE.md` (design R1) and the C ring `cg_fresh_accept(field, seq, ...)`: field = GPS seconds, sequence in second, no persisted counter | a fresh name `c` (no ordering) | id `<e, n>`: epoch = GPS second, `n` = 1 to 3 in that second | `mk(e, s1)` | **mismatch (documentation)**: the byte positions of the GPS-second field and of the sequence-in-second are not specified in `PACKET_FORMAT.md`, which still describes the persisted counter. The freshness models and `ar_r1` describe a different frame semantics from `PACKET_FORMAT.md` |
| Window | C path: `cg_fresh_accept(..., W, R)`; the simulation uses W = 10 s (`ar.r1`) | no window | window of two epochs (the current and the previous GPS second) | no window | **mismatch (abstraction)**: the model's window (about 1 to 2 s) is not the simulated W = 10 s. The lemma (at most once per window) does not depend on the width, but the statement "within the window" is for the model's window |
| Seen-set | ring of the last R entries (R up to 512), cleared at reboot | none | unbounded set | none | **mismatch (abstraction, stated in the model file)**: a finite ring is outside the model. A replay of an entry that the ring has dropped is possible for a window longer than the ring covers (`ar.r1` measures the replay rate inside the window; H-R1b was not supported at the held-out burst load) |
| Boot counter | not in any frame layout (the alert has 47 reserved bytes; the flash has none) | none | fresh value per boot in the variant | fresh value per boot in `carid_bootctr_*` | **mismatch**: the paper says the variant costs one byte per frame. The alert has room. The flash would grow from 14 to 15 bytes. Airtime does not change: 13, 14 and 15 bytes take 46.34 ms at SF7 and 164.86 ms at SF9 (`lora.airtime_ms`), so the airtime results hold. The layout change is not specified anywhere |
| 14-byte flash and cancel | `sct_protocol.py` | not in any model of the frozen design | not in any model | not modelled | **gap**: the flash and the cancel frames of the frozen design have no formal model. Only the 24-byte provisional frame of round 4 (`crash_alert_prov*.spthy`) was modelled, and that design was not supported (H-A1a, H-A1b). The flash and the full alert of one event carry the same counter in the layout; the models give each frame its own fresh id |
| Tag length | 8 bytes | perfect MAC (no truncation) | perfect MAC | perfect MAC | stated limit: symbolic model with perfect cryptography; the 2^-64 forgery bound is separate and ANALYTICAL |

## 3. What the paper may say

- The Tamarin results apply to the alert and ACK exchange of the full 97-byte alert and 26-byte ACK, abstracted to (vehicle, freshness id, class, tag).
- No formal result is claimed for the 14-byte flash, the cancel frame, the 16-bit short node id or the finite ring.
- The freshness lemmas are for the GPS-second id of the freshness design, not for the persisted counter of `PACKET_FORMAT.md`; the byte layout of that design is not yet specified.
- The boot-counter variant needs a layout change in the flash frame (14 to 15 bytes, airtime unchanged at SF7 and SF9).

These points are carried into the paper (limits paragraph of the formal section) and into `paper/PLACEHOLDERS.md` where the author must decide the byte layout.
