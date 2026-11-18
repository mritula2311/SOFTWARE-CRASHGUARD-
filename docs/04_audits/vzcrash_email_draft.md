# Draft email to the VZCrash authors (NOT SENT)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-13 |
| Owner | Mritula S |
| Scope | Draft email to the VZCrash authors (record only; the author sent the audit package on 2026-11-12). |
| Evidence labels used | none (this file reports no result) |
| Abbreviations | CSV = comma-separated values; SRIHER = Sri Ramachandra Institute of Higher Education and Research |
<!-- header:end -->

Status: SUPERSEDED (2026-11-13). The author sent an audit package by email on 2026-11-12; this draft is kept only as a record and may differ from what was sent (see docs/07_log/DECISIONS.md, entry on the audit package). Nothing was sent from this repository. Attach `results/tables/vzcrash_duplicate_groups.csv` (event IDs only, no signal data).
Suggested recipient: the corresponding author whose address is printed on the title page of the paper (arXiv 2606.06074). Check the address before sending.

---

Notes for the author (not part of the email):
- Split statement, quoted from the paper, Section `III-B` ("Benchmark on the Full VZCrash Dataset"): `"The dataset is partitioned into training (72%), validation (14%), and test (14%) sets. To prevent data leakage, these splits are strictly separated by vehicle, ensuring that telemetry from any given vehicle appears in only one of the subsets. We employ stratified sampling at the vehicle level ..."` We do not claim leakage by vehicle.
- Licence: SUPERSEDED. The dataset authors confirmed CC BY-NC 4.0 on 2026-11-12 (see docs/07_log/DECISIONS.md). This draft was not sent in this form; the audit package that was sent is described in release/vzcrash_audit_for_authors/.

**Subject:** Question about identical recordings across the VZCrash train, validation and test splits

Dear Dr Bianconcini and co-authors,

I am Mritula S, a B.Tech student at SRIHER, India. I am training a small crash detector on VZCrash for a non-commercial academic project. Thank you for releasing the dataset and the paper. We will cite it as the CC BY-NC 4.0 licence on the dataset card asks.

While checking our data setup we found that some recordings are identical across the official splits. For each event we hashed the raw accelerometer array and grouped events with the same hash. 217 groups contain events from more than one split, with 439 events in those groups (426 crash, 2 near_miss and 11 normal_driving). In the test split, 150 events (114 crashes) have an identical or near-identical recording (within 0.005 g on a downsampled signal) in train or validation. No event ID appears twice. We read in Section `III-B` of the paper that the splits are `72/14/14`, "strictly separated by vehicle" and stratified by vehicle size. We are not claiming that vehicles leak across the splits: the release has no vehicle ID, so we cannot check that. We only report that identical recordings appear across the released splits, and we would like to know whether they come from the export.

We would be grateful if you could tell us:
1. Are these likely to be an export artefact, for example one recording stored under several event IDs?
2. If they are genuine repeats, would you advise dropping the duplicates, or only the test copies?
3. Is a vehicle or group identifier available that we could use to confirm the vehicle-level split?

The attached CSV lists the groups (event IDs, split, class, vehicle size and number of samples). On our side the effect is small: with the repeated test events removed, the average precision of our 15-tree forest moves from 0.934 to 0.931. We now report the de-duplicated test set as our main result and the supplied split as a secondary one. We are glad to share our code and to correct anything we have misunderstood.

Thank you for your time. (One more small question: the paper does not state a licence, and the licence we use, CC BY-NC 4.0, comes from the dataset card on Hugging Face. Could you confirm that it also applies to the paper's release?)

Kind regards,
Mritula S
[your institution and contact details]
