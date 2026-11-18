"""Write docs/04_audits/vzcrash_email_draft.md: a draft email to the VZCrash authors about identical recordings across splits.

Nothing is sent. Numbers come from results/results.json. The attachment is results/tables/vzcrash_duplicate_groups.csv
(event IDs, split, class, vehicle size, number of samples; no signal data).
"""
from __future__ import annotations

from pathlib import Path

from crashguard.report import L, R_, Res

OUT = Path("docs/04_audits/vzcrash_email_draft.md")
RF = "s2.trig_2.all.rf15"


def build(r: Res | None = None) -> str:
    r = r or Res()
    return f"""# Draft email to the VZCrash authors (NOT SENT)

Status: draft for the author to review. Nothing has been sent. Attach `results/tables/vzcrash_duplicate_groups.csv` (event IDs only, no signal data).
Suggested recipient: the corresponding author whose address is printed on the title page of the paper (arXiv 2606.06074). Check the address before sending.

---

Notes for the author (not part of the email):
- Split statement, quoted from the paper, Section `III-B` ("Benchmark on the Full VZCrash Dataset"): `"The dataset is partitioned into training (72%), validation (14%), and test (14%) sets. To prevent data leakage, these splits are strictly separated by vehicle, ensuring that telemetry from any given vehicle appears in only one of the subsets. We employ stratified sampling at the vehicle level ..."` We do not claim leakage by vehicle.
- Licence: the paper reports no licence (checked in the full text on `2026-11-11`). The licence in our docs comes from the dataset card: the front matter of the Hugging Face README says `license: cc-by-nc-4.0` and its text says "released under the CC BY-NC 4.0 license" (local copy: `data/raw/card/README.md`).

**Subject:** Question about identical recordings across the VZCrash train, validation and test splits

Dear Dr Bianconcini and co-authors,

I am Mritula S, a B.Tech student at SRIHER, India. I am training a small crash detector on VZCrash for a non-commercial academic project. Thank you for releasing the dataset and the paper. We will cite it as the CC BY-NC 4.0 licence on the dataset card asks.

While checking our data setup we found that some recordings are identical across the official splits. For each event we hashed the raw accelerometer array and grouped events with the same hash. {r.i('leakage.exact_hash_groups_across_splits')} groups contain events from more than one split, with {r.i('leakage.cross_split_group_events.total')} events in those groups ({r.i('leakage.cross_split_group_events.crash')} crash, {r.i('leakage.cross_split_group_events.near_miss')} near_miss and {r.i('leakage.cross_split_group_events.normal_driving')} normal_driving). In the test split, {r.i('leakage.test_events_flagged.total')} events ({r.i('leakage.test_events_flagged.crash')} crashes) have an identical or near-identical recording (within 0.005 g on a downsampled signal) in train or validation. No event ID appears twice. We read in Section `III-B` of the paper that the splits are `72/14/14`, "strictly separated by vehicle" and stratified by vehicle size. We are not claiming that vehicles leak across the splits: the release has no vehicle ID, so we cannot check that. We only report that identical recordings appear across the released splits, and we would like to know whether they come from the export.

We would be grateful if you could tell us:
1. Are these likely to be an export artefact, for example one recording stored under several event IDs?
2. If they are genuine repeats, would you advise dropping the duplicates, or only the test copies?
3. Is a vehicle or group identifier available that we could use to confirm the vehicle-level split?

The attached CSV lists the groups (event IDs, split, class, vehicle size and number of samples). On our side the effect is small: with the repeated test events removed, the average precision of our 15-tree forest moves from {r.f(f'{RF}.supplied_ap.mean')} to {r.f(f'{RF}.ap.mean')}. We now report the de-duplicated test set as our main result and the supplied split as a secondary one. We are glad to share our code and to correct anything we have misunderstood.

Thank you for your time. (One more small question: the paper does not state a licence, and the licence we use, CC BY-NC 4.0, comes from the dataset card on Hugging Face. Could you confirm that it also applies to the paper's release?)

Kind regards,
Mritula S
[your institution and contact details]
"""


def main() -> None:
    OUT.write_text(build().replace(L, "").replace(R_, ""), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
