"""Round 5 session 2 documents: the novelty-matrix rows L6 to L11 (idempotent, between marker comments) and the query log section for topics 26 to 31.

    python -m crashguard.r5_lit_docs_s2

Reads ``results/tables/r5_lit_queries.json`` (OpenAlex, topics 26 and 27) and ``results/tables/r5_lit_crossref.json`` (Crossref, topics 28 to 31; OpenAlex answered HTTP 429 for those topics). Items are read at the
level of title and metadata (OpenAlex or Crossref record); no full text was read, and no abstract was available for the Crossref items, so nothing below is claimed about their content beyond their titles.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MATRIX = ROOT / "docs" / "06_references" / "NOVELTY_MATRIX_2021PLUS.md"
LOG = ROOT / "docs" / "06_references" / "LIT_QUERIES_ROUND5.md"
BEGIN, END = "<!-- r5s2:begin -->", "<!-- r5s2:end -->"
ABSENCE = "no journal article from 2021 onwards found in the sources checked (OpenAlex and Crossref; IEEE Xplore, Scopus, Google Scholar and TRID not run)"
ROWS = f"""| L6 | Gateway placement that maximises coverage of historical fatal-crash locations (severity weighted) against population-weighted placement | Future Internet 2026 (digital-twin LoRaWAN gateway placement, memetic optimisation and k-coverage); Annals of Telecommunications 2026 (hybrid optimisation for gateway placement); IEEE Access 2026 (joint placement and scheduling); title and metadata level | Gateway placement by coverage, clustering or joint optimisation for sensor networks; none by crash locations in the titles | Placement driven by FARS crash locations, tested on a held-out year | Partial for the placement method (maximum coverage is standard); {ABSENCE} that places gateways by crash locations | Allowed: coverage of held-out crashes under an assumed range, no calibration on LoED (no positions) | Baselines: population-weighted (GeoNames places) and uniform grid |
| L7 | Hash-chain ratchet of per-vehicle alert keys with a look-ahead window and a Tamarin proof of forward secrecy for the alert protocol | Sensors 2021 (key management protocol based on hash-chain key generation for LoRaWAN); IEEE Access 2022 (session key update scheme for LoRaWAN); IJSNET 2025 (key exchange analysis); title and metadata level | Hash chains and session-key updates for LoRaWAN joins and sessions | A forward-secrecy lemma and a window enumeration for the crash-alert frame with the boot counter | Substantial for the idea of a hash-chain key update in LoRaWAN; {ABSENCE} that proves forward secrecy of crash alerts with a ratchet in Tamarin | The ratchet is an application of known chain constructions; the claim is limited to the proved lemmas and the enumeration | Baseline: no ratchet (the frozen per-vehicle key) |
| L8 | Base-side rate limit, plausibility checks and a quarantine state for a compromised vehicle that floods alerts | IEEE Access 2022 (misbehavior detection for position falsification attacks in VANETs); J. Transp. Technol. 2021 (misbehavior detection by time series of vehicle position in V2X); Network 2026 (detecting false alerts in safety messages); title and metadata level | Position-plausibility and learning-based misbehaviour detection in vehicular networks | A bounded exhaustive check of the high-confidence forward count for a single compromised key, with a legitimate-alert replay | Substantial for plausibility checks on position; {ABSENCE} that bounds high-confidence forwards of a crash-alert base with a token bucket and quarantine | Plausibility check is not claimed; the bound and the replay are | Supplement unless H-L8a is FORMAL |
| L9 | Break-even cost ratio between a false dispatch and a minute of delay for acting on a provisional crash alert | Automatic crash notification and injury-prediction papers (IJAT 2022, IET ITS 2021, J. Am. Coll. Surg. 2026 commentary, J. Logistics Inf. Serv. Sci. 2022 two-phase notification); title and metadata level | Injury prediction and notification design; none states a cost ratio in the title | A decision analysis from measured retraction and time gain | {ABSENCE} that gives a break-even ratio for acting on a provisional alert | Descriptive, with stated assumptions for the pre-alert option | No claim of superiority |
| L10 | Duplicate and leakage audit of public accelerometer benchmarks with the window-identity rule of C1 | Sensors 2024 (data leakage in a WiFi CSI benchmark for human action recognition); Applied Sciences 2026 (near-duplicate contamination in a safety-helmet detection benchmark); Electronics 2026 (duplicate-safe evaluation of anomaly detection); Healthcare Analytics 2026 (leakage-free subject-wise framework); title and metadata level | Leakage and duplicate audits of other benchmark families | An audit of two accelerometer benchmarks (UCI HAR, SisFall) with the exact-identity rule | Substantial for the idea of a benchmark duplicate audit (several 2024 to 2026 audits exist for other data types); {ABSENCE} that applies it to UCI HAR or SisFall | Report as an application of an established audit idea to two accelerometer sets; a null result narrows C1 | Baseline: the published splits |
| L11 | Detection of mirror-image axis flips from the agreement of two forward-axis estimates (from a turn and from a speed change) | IEEE Control Systems 2022 (IMU error modelling tutorial); Sensors 2024 (online calibration of inertial sensors); Measurement 2024 (gyro installation error); title and metadata level | IMU error models and calibration; none about handedness detection in the titles | A rotation-invariant agreement test for handedness on real driving signals with synthetic transformations | {ABSENCE} that detects a mirror flip of an IMU from turns in a vehicle | If the criterion is met: an application of the physical relation between yaw rate and lateral acceleration, reported as added after session 1 in its own family | Baseline: L1 alone (about 0.5 side accuracy under a mirror flip) |
"""


def main() -> None:
    s = MATRIX.read_text(encoding="utf-8")
    block = f"{BEGIN}\n{ROWS}{END}\n"
    if BEGIN in s:
        i, j = s.index(BEGIN), s.index(END) + len(END) + 1
        s = s[:i] + block + s[j:]
    else:
        marker = "<!-- r5:end -->\n"
        assert marker in s
        head = "\n## Round 5 rows, session 2 (L6 to L11; L11 added after session 1)\n\nRows written before the held-out run of each algorithm; OpenAlex topics 26 and 27, Crossref topics 28 to 31 (`LIT_QUERIES_ROUND5.md`).\n\n| Key | Claim | Closest 2021+ journal articles seen | What they do | What this work adds | Overlap | Allowed wording | Action |\n|---|---|---|---|---|---|---|---|\n"
        s = s.replace(marker, marker + head + block, 1)
    MATRIX.write_text(s, encoding="utf-8")
    t = LOG.read_text(encoding="utf-8")
    sec = "\n## Session 2 queries (topics 26 to 31)\n\nTopics 26 (L6 gateway placement) and 27 (L7 forward-secure keys) were run on OpenAlex; topics 28 (L8), 29 (L10), 30 (L11) and 31 (L9) were run on Crossref (plain-text queries, journal articles from 2021-01-01, 8 results each) because OpenAlex returned HTTP 429 for them. The record files are `results/tables/r5_lit_queries.json` and `results/tables/r5_lit_crossref.json`. Crossref gave no abstracts for the items used; their rows rest on titles and are worded accordingly.\n"
    if "Session 2 queries" not in t:
        LOG.write_text(t.rstrip() + "\n" + sec, encoding="utf-8")
    print("written")


if __name__ == "__main__":
    main()
