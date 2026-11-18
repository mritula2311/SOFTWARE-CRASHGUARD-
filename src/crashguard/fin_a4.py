"""A4: package for the VZCrash authors (identifiers, split, class, matching rule; no raw signal values). Built only from stored audit tables and events_meta (labels, sizes), never from raw arrays.
The package agrees with the one already sent by the author on 2026-11-12; nothing here is sent."""
from __future__ import annotations

import pandas as pd

OUT = "release/vzcrash_audit_for_authors"
REV = "42e1482d005c0e545379d6cfa4939486c9fe4249"
CLS = {0: "crash", 1: "near_miss", 2: "normal_driving"}


def build() -> dict:
    g = pd.read_csv("results/tables/vzcrash_duplicate_groups.csv")  # group_id,event_id,split,class,vehiclesize,n_samples
    meta = pd.read_parquet("data/processed/events_meta.parquet", columns=["event_id", "split", "label", "vehiclesize", "dropped"])
    meta["class"] = meta.label.map(CLS)
    flags = pd.read_csv("results/tables/s2_neardup_test.csv")
    exact_test = set(pd.read_csv("results/tables/vz_audit_test_exact_copy_ids.csv").event_id)
    leaky = set(pd.read_parquet("data/processed/leaky_test_events.parquet").event_id)
    rows = []
    for r in g.itertuples():
        rows.append(dict(event_id=r.event_id, group_id=r.group_id, split=r.split, **{"class": r._4}, vehiclesize=r.vehiclesize, rule="R1_identical_array_group"))
    cmap = meta.set_index("event_id")
    for e in sorted(exact_test):
        rows.append(dict(event_id=e, group_id="", split="test", **{"class": cmap.loc[e, "class"]}, vehiclesize=cmap.loc[e, "vehiclesize"], rule="R1b_test_event_with_identical_array_in_train_or_validation"))
    for e in sorted(leaky - exact_test):
        rows.append(dict(event_id=e, group_id="", split="test", **{"class": cmap.loc[e, "class"]}, vehiclesize=cmap.loc[e, "vehiclesize"], rule="R2_primary_dedup_32bin_linf_below_0.005g"))
    fl = flags[flags["both"]]
    for r in fl.itertuples():
        rows.append(dict(event_id=r.event_id, group_id="", split="test", **{"class": CLS[int(r.label)] if str(r.label).isdigit() else r.label}, vehiclesize=cmap.loc[r.event_id, "vehiclesize"], rule="R3_window_near_duplicate_corr_above_0.999_and_maxdiff_below_0.01g"))
    D = pd.DataFrame(rows).drop_duplicates(["event_id", "rule"]).sort_values(["rule", "event_id"])
    D.to_csv(f"{OUT}/affected_events.csv", index=False)
    cnt = D.groupby(["rule", "split", "class"]).event_id.nunique().reset_index(name="n_events")
    cnt.to_csv(f"{OUT}/counts_per_rule_split_class.csv", index=False)
    summ = dict(groups=int(g.group_id.nunique()), events_in_groups=int(len(g)), test_exact=len(exact_test), primary_removed=len(leaky), window_flagged=int(len(fl)), window_scanned=int(len(flags)),
                events_without_id=int(D.event_id.isna().sum()))
    return summ


if __name__ == "__main__":
    print(build())
