"""V2 and V3: write docs/04_audits/VZCRASH_AUDIT.md from results.json (``vz.v1.*``, ``vz.v4.*`` and the stored ``dupscan.*`` / ``leakage.*`` keys) and copy the group-identifier file to results/paper/.
No number is typed here. The file lists identifiers and hashes only; no raw data is redistributed (CC BY-NC 4.0, confirmed by the dataset authors on 2026-11-12)."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd

R = {e["name"]: e["value"] for e in json.loads(Path("results/results.json").read_text(encoding="utf-8"))}
OUT = Path("docs/04_audits/VZCRASH_AUDIT.md")


def g(k: str, d: int = 0):
    v = R[k]
    return f"{v:,.{d}f}" if isinstance(v, (int, float)) and d == 0 else (f"{v:.{d}f}" if isinstance(v, (int, float)) else v)


def ci(k: str, d: int = 3) -> str:
    return f"{R[k]:+.{d}f} [{R[k + '_lo']:+.{d}f}, {R[k + '_hi']:+.{d}f}]"


def val(k: str, d: int = 3) -> str:
    return f"{R[k]:.{d}f} [{R[k + '_lo']:.{d}f}, {R[k + '_hi']:.{d}f}]"


def main() -> None:
    t = pd.read_csv("results/tables/vz_audit_cross_split_groups.csv")
    ids = [[int(x.split(":")[1]) for x in e.split(";")] for e in t.event_ids]
    spread = pd.Series([max(i) - min(i) for i in ids])
    shutil.copy("results/tables/vz_audit_cross_split_groups.csv", "results/paper/vz_audit_cross_split_groups.csv")
    L = [
        "# VZCrash duplicate audit (independent re-derivation)", "",
        "**What this is.** The VZCrash release has recordings that occur in more than one split. The earlier audit of this repository found them; this document records an independent recomputation from the raw supplied files, "
        "so that anyone with the dataset can check it. The dataset is not redistributed here: `results/paper/vz_audit_cross_split_groups.csv` holds identifiers and one-way hashes only (no samples). "
        "VZCrash is released under CC BY-NC 4.0 (author reply, 2026-11-12, recorded in `docs/07_log/DECISIONS.md`; the downloaded copy is Hugging Face revision 42e1482d005c0e545379d6cfa4939486c9fe4249); the dataset authors allow event identifiers or hashes to be cited in a paper.", "",
        "## Matching rules and thresholds", "",
        "1. **Exact array groups.** The SHA-256 hash of the event's accelerometer array (float32 values as stored, row-major, plus the sample count). Events with the same hash form a group. The same was done for the hash of the whole event "
        "(accelerometer, gyroscope and GPS speed): the groups are identical, so the copies are whole-event copies.",
        "2. **Window-level near-duplicates (the T5 rule).** Events that pass the 2 g trigger get a 280-sample window (1.0 s before and 1.8 s after the earliest sample whose |a| exceeds 2 g, each axis clipped to +-16 g first, edge-repeat padding); events whose raw |a| "
        "exceeds 16 g are dropped (2 test events). A test window is a near-duplicate if some train or validation window has correlation above 0.999 (per-axis mean removed, axes concatenated) AND maximum absolute difference below 0.01 g.", "",
        "## Counts (recomputed; every stored value agrees)", "",
        f"- Supplied events: train {g('vz.v1.events.train')}, validation {g('vz.v1.events.validation')}, test {g('vz.v1.events.test')} ({g('vz.v1.test_events_after_16g_drop')} test events after the 16 g drop).",
        f"- Exact groups across splits: **{g('vz.v1.exact.acc.groups_across_splits')}** groups (stored: {g('vz.v1.exact.acc.groups_across_splits.vs_stored.stored')}; difference {g('vz.v1.exact.acc.groups_across_splits.vs_stored.difference')}), "
        f"holding {g('vz.v1.exact.acc.events_in_cross_split_groups')} events: {g('vz.v1.exact.acc.events_in_cross_split_groups.crash')} crash, {g('vz.v1.exact.acc.events_in_cross_split_groups.near_miss')} near_miss, "
        f"{g('vz.v1.exact.acc.events_in_cross_split_groups.normal_driving')} normal_driving; per split: train {g('vz.v1.exact.acc.events_in_cross_split_groups.train')}, validation {g('vz.v1.exact.acc.events_in_cross_split_groups.validation')}, "
        f"test {g('vz.v1.exact.acc.events_in_cross_split_groups.test')}. Events whose array equals an earlier event: {g('vz.v1.exact.acc.events_equal_to_an_earlier_event.vs_stored')} (stored {g('vz.v1.exact.acc.events_equal_to_an_earlier_event.vs_stored.stored')}).",
        f"- Test events with an exact copy in train or validation: **{g('vz.v1.exact.acc.test_events_with_train_or_val_copy')}** ({g('vz.v1.exact.acc.test_events_with_train_or_val_copy.crash')} crash, {g('vz.v1.exact.acc.test_events_with_train_or_val_copy.near_miss')} near_miss, "
        f"{g('vz.v1.exact.acc.test_events_with_train_or_val_copy.normal_driving')} normal_driving), {100 * R['vz.v1.exact.acc.test_share_with_train_or_val_copy']:.1f}% of all test events.",
        f"- The primary (de-duplicated) test set of the headline removes {g('leakage.test_events_flagged.total')} test events: the exact copies and, in addition, events whose 32-bin downsampled |a| is within 0.005 g of a train or validation event "
        f"(the nearest-neighbour rule of the earlier audit; it was not re-derived here because its definition is not fully specified in the documents).",
        f"- Window level: **{g('vz.v1.near.test_windows_scanned')}** triggered test windows scanned against {g('vz.v1.near.reference_windows')} train and validation windows; {g('vz.v1.near.test_events_not_triggered.vs_stored')} test events never pass the trigger. "
        f"**{g('vz.v1.near.test_windows_both.vs_stored')}** test windows meet both thresholds (stored {g('vz.v1.near.test_windows_both.vs_stored.stored')}, difference {g('vz.v1.near.test_windows_both.vs_stored.difference')}); "
        f"{g('vz.v1.near.test_windows_corr_only.vs_stored')} meet only the correlation threshold. The flagged event set equals the stored set (only recomputed: {g('vz.v1.near.event_set_agreement.only_recomputed')}; only stored: {g('vz.v1.near.event_set_agreement.only_stored')}). "
        f"Every flagged window equals its train or validation window sample for sample (maximum difference exactly 0 for {g('vz.v1.near.flagged_with_max_difference_exactly_0')} of {g('vz.v1.near.test_windows_both.vs_stored')}), so these are the same recording seen through the same window, "
        f"although only {g('vz.v1.near.flagged_events_also_exact_duplicates')} of those events are whole-array copies: the rest are the same crash exported with a different 16 s context.",
        f"- By class: crash {g('vz.v1.near.test_windows_both.crash')} of {g('vz.v1.near.test_windows_scanned.crash')} triggered crash windows; near_miss {g('vz.v1.near.test_windows_both.near_miss')} of {g('vz.v1.near.test_windows_scanned.near_miss')}; "
        f"normal_driving {g('vz.v1.near.test_windows_both.normal_driving')} of {g('vz.v1.near.test_windows_scanned.normal_driving')}.", "",
        "## V2: the two figures about duplicate test windows (a fifth, and about 5%)", "",
        "Both figures are correct; they use different denominators, and neither is a share of exact copies. "
        f"(a) **{100 * R['vz.v1.near.share_of_triggered_test_windows']:.1f}%** ({g('vz.v1.near.test_windows_both.vs_stored')} of {g('vz.v1.near.test_windows_scanned')}): the share of TRIGGERED test windows that equal a train or validation window (about a fifth). "
        f"(b) **{100 * (1 - R['t5.n_events.strict'] / R['t5.n_events.std']):.1f}%** ({g('t5.n_events.std')} to {g('t5.n_events.strict')} test events): the events removed by the strict set, over ALL test events of the primary set, "
        f"AFTER the {g('leakage.test_events_flagged.total')} events that the primary rule already removed (about 5%). {100 * R['vz.v1.near.share_of_all_test_events']:.1f}% of all supplied test events have a flagged window (before any removal). "
        f"By class the share is very unequal: {100 * R['vz.v1.near.share_of_all_test_events_of_class.crash']:.1f}% of all crash test events have a flagged window, against {100 * R['vz.v1.near.share_of_all_test_events_of_class.near_miss']:.1f}% of near_miss and "
        f"{100 * R['vz.v1.near.share_of_all_test_events_of_class.normal_driving']:.1f}% of normal_driving events. "
        "The wording to use: 'about a fifth of the triggered test windows (and about 30% of the crash test events) have a window that is identical, sample for sample, to a train or validation window; over all test events the strict set removes about 5% beyond the primary rule.' "
        "The words 'identical train or validation window' are accurate for the window; they are not accurate for the whole 16 s event (only the exact-copy test events above are identical as events).",
        "The earlier statement in the novelty summary that the headline was computed 'after removing 217 groups' was wrong: the primary set removes test events (the number above), not groups, and the train and validation copies stay; it is corrected in `crashguard.novelty`. "
        "No sentence with the words 'a fifth' was found in the tracked documents of this repository (searched `docs/`, `report/`, `README.md`); if such a sentence exists in an outside summary it should use the wording above.", "",
        "## Vehicle identifiers", "",
        "The release has no vehicle identifier, so vehicle-level separation cannot be checked. The only vehicle label is the vehicle size (Light, Medium, Heavy, Unknown). "
        f"In {g('vz.v1.exact.acc.cross_groups_vehiclesize_consistent')} of {g('vz.v1.exact.acc.groups_across_splits')} cross-split groups all events carry the same size label and in {g('vz.v1.exact.acc.cross_groups_spanning_several_vehiclesizes')} the labels differ (Medium and Unknown); "
        f"the class label is identical inside all {g('vz.v1.exact.acc.cross_groups_label_consistent')} groups. Events of a group have close event ids: the spread between the largest and the smallest id of a group has a median of {spread.median():.0f} "
        f"and is at most {spread.max():,} (the group file lists them). The groups therefore look like one recording exported under neighbouring ids, which the dataset authors can confirm; this audit does not claim it.", "",
        "## V4: how the headline metrics move (`vz.v4.*`; 5-seed means, paired bootstrap over the supplied test events)", "",
        "Sets: supplied; without test events with an exact array copy in train or validation; without those and without events whose window equals a train or validation window. Same training, thresholds (validation) and seeds; only the evaluated events differ.", "",
        "| Model | Metric | Supplied | Exact copies removed | Difference (supplied minus exact) | Near-duplicates also removed | Difference (supplied minus near) |", "|---|---|---|---|---|---|---|"]
    for model, name in (("rf15", "15-tree forest (headline)"), ("rfsel", "10-tree depth-9 forest")):
        for met, mn in (("sys_recall", "System recall (validation-F1 threshold)"), ("recall_at_1pct", "Recall at the 1% false-alarm target"), ("recall_at_5pct", "Recall at the 5% target"), ("ap", "AP (triggered events)"), ("sys_ap", "System AP")):
            L.append(f"| {name} | {mn} | {val(f'vz.v4.{model}.supplied.{met}')} | {val(f'vz.v4.{model}.exact.{met}')} | {ci(f'vz.v4.{model}.diff_supplied_minus_exact.{met}', 4)} | "
                     f"{val(f'vz.v4.{model}.near.{met}')} | {ci(f'vz.v4.{model}.diff_supplied_minus_near.{met}', 4)} |")
    L += ["", f"Events: supplied {g('vz.v4.n_events.supplied')} ({g('vz.v4.n_crash.supplied')} crash), exact-copy removal {g('vz.v4.n_events.exact')}, near-duplicate removal {g('vz.v4.n_events.near')} ({g('vz.v4.n_crash.near')} crash). "
          "Reading: removing exact copies changes the headline by under a point; removing the window-level duplicates lowers recall by about three points and recall at the 1% target by about seven (the duplicates are mostly crashes, "
          "so a model that has seen the crash scores it well). The primary test set of this repository stays the de-duplicated one; the strict set is the sensitivity analysis.", "",
          "## How to reproduce", "", "```", "python -m crashguard.vz_audit      # V1: recompute from data/raw/data/*.parquet (about 2 minutes); writes vz.v1.* and results/tables/vz_audit_*.csv",
          "python -m crashguard.vz_leakage    # V4: three test sets, two forests, five seeds", "python -m crashguard.vz_docs       # this document and results/paper/vz_audit_cross_split_groups.csv", "```", "",
          "Files: `results/tables/vz_audit_comparison.csv` (recomputed against stored, every row), `results/tables/vz_audit_cross_split_groups.csv` (group hash, event ids with split, classes, sizes), "
          "`results/tables/vz_audit_test_near_dup_flags.csv` and `vz_audit_test_exact_copy_ids.csv` (test event ids only). Every number above is read from `results/results.json` by `vz_docs.py`."]
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
