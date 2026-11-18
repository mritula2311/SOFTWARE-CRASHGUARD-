# A3: ProVerif models of the car-reboot alert-id lemma

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-15 |
| Owner | Mritula S |
| Scope | ProVerif 2.05 models of the car-reboot alert-id lemma for the frozen design and the boot-counter variant, with outputs and the reading of each result. |
| Evidence labels used | none (this file reports no result) |
| Abbreviations | GPS = Global Positioning System; WSL = Windows Subsystem for Linux |
<!-- header:end -->

Tool: ProVerif 2.05 built from the project's source archive (SHA-256 `4871f53c32ab4a04669a060c4886ba5d9080496963fb980a9a62d2c429ceabc4`) in WSL. Models in `formal/proverif/`, outputs in `formal/out/proverif/`, runner `scripts/wsl_proverif.sh`. Keys `a4.a3.proverif.*`. Preregistration: `PREREGISTRATION_V15.md` section 4. The time box of 3 hours was not used up: the four models ran in under a second each; one further formulation did not finish in 300 s.

The property is a correspondence over distinct alert instances: `event(CarSend(v, id, i1)) && event(CarSend(v, id, i2)) ==> i1 = i2` (two different alert instances never carry the same id). The models with a base also check authenticity of acceptance (`event(BaseAccept(v, id)) ==> event(CarSendId(v, id)) || event(Revealed(v))`). The base's seen-set is not modelled (ProVerif has no deletion), so injective agreement is not asked.

| Model | What it models | Query | Result |
|---|---|---|---|
| `carid_frozen_same_epoch.pv` | Frozen design (id = epoch and sequence). The environment chooses the epoch at every boot; any number of boots (replication); a reboot may complete inside the second of an earlier alert | id reuse | **attack found** (false) |
| | | authenticity of acceptance | proved |
| `carid_frozen_next_epoch.pv` | Frozen design with the timing assumption of the Tamarin model (a reboot completes in a later epoch), time as ProVerif phases | id reuse | proved, **bounded**: three epochs, two reboots |
| `carid_bootctr_same_epoch.pv` | Boot-counter variant (id = boot counter, epoch, sequence; one non-volatile write per boot, a fresh name per boot); the same environment as model 1 | id reuse | **proved**, any number of boots, no timing assumption |
| | | authenticity of acceptance | proved |
| `carid_bootctr_nowrite.pv` | Negative control: the variant when the write does not persist (one counter value for every boot) | id reuse | attack found (false) |
| `carid_frozen_chain.pv` | Frozen design, unbounded boots, "later epoch" order built from a successor constructor and a private hand-over channel | id reuse | **undecided**: no result in 300 s (timeout) |

**Attack found on the frozen design (model 1).** ProVerif's trace: the attacker supplies the same epoch value to two copies of the boot process (two boots of one car); both send an alert with the id (epoch, s1), carrying different alert instances. This is the case in which the car reboots inside the GPS second of an earlier alert and the sequence counter, which is lost at a reboot, starts again at s1. The frozen design excludes it only through a timing assumption (the boot lasts at least one GPS second), which the Tamarin model builds in and which neither tool can check against hardware.

**Reading.** (1) The lemma does not hold for the frozen design without the timing assumption; with the assumption it holds, but the proof in model 2 is bounded and follows from distinct epochs, which is the assumption itself, so it adds little. (2) The boot-counter variant removes the dependence on the boot duration: with a counter that persists and never wraps, ids of different boots differ whatever the clock does (model 3); the control (model 4) shows that the result rests on that write assumption. (3) The unbounded ordered-time formulation of the frozen design was tried once (model 5, a successor constructor and a hand-over channel) and did not terminate in 300 s; the reason was not determined, and no other formulation was tried. Tamarin 1.12.0 likewise left its unbounded formulations undecided (`pp.c4.variant.*`, round 3). The question is therefore decided in two ways only: attack found without the timing assumption, proved with a persistent boot counter.

**Consequence for the design.** The frozen design needs either the explicit assumption that a reboot takes at least one GPS second before the next time-stamped alert, or the boot counter. The boot-counter variant is a design recommendation, not part of the frozen design: it costs one non-volatile write per boot and one byte in every frame (the 24-byte provisional frame of A1 would become 25 bytes). Symbolic proofs assume perfect cryptography and a persistent counter; nothing here says an implementation is secure.
