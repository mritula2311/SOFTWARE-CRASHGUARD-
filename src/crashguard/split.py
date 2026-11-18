"""Supplied train/validation/test splits, a near-duplicate leakage check, and vehicle-size grouping.

The splits come with VZCrash. There is no vehicle or trip ID, so grouping is UNVERIFIED
(docs/07_log/DECISIONS.md). The near-duplicate check below can only catch repeated recordings, not repeated vehicles.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from crashguard import config as C
from crashguard.data import LABELS
from crashguard.results import record_many

SPLITS = ("train", "validation", "test")
NN_EPS_G = (0.001, 0.005)  # L-infinity distance on the 32-bin downsampled |a| vector


def load_variant(variant: str) -> pd.DataFrame:
    """Events (corrupt ones removed) with window features for one window variant."""
    meta = pd.read_parquet(C.PROCESSED / "events_meta.parquet", columns=["event_id", "split", "label", "vehiclesize", "dropped"])
    feats = pd.read_parquet(C.PROCESSED / "features.parquet")
    feats = feats[feats.variant == variant].drop(columns="variant")
    df = meta[~meta.dropped].merge(feats, on="event_id", how="left").drop(columns="dropped")
    df["y"] = (df.label == 0).astype(int)
    return df.reset_index(drop=True)


def near_duplicate_check() -> pd.DataFrame:
    """Exact-hash and nearest-neighbour checks between test and train+validation. Records results."""
    ds_cols = [f"ds{i}" for i in range(32)]
    meta = pd.read_parquet(C.PROCESSED / "events_meta.parquet")
    meta = meta[~meta.dropped & (meta.hash != "")].reset_index(drop=True)
    src = "data/processed/events_meta.parquet"
    out: list[dict] = []
    rows = []

    h = meta.groupby("hash").split.nunique()
    n_exact = int((h > 1).sum())
    n_within = int(meta.hash.duplicated().sum())
    out.append(dict(name="leakage.exact_hash_groups_across_splits", value=n_exact, unit="hash groups", origin="MEASURED_SOFTWARE",
                    source_file=src, notes="identical raw accelerometer arrays in more than one split"))
    out.append(dict(name="leakage.exact_hash_duplicates_total", value=n_within, unit="events", origin="MEASURED_SOFTWARE",
                    source_file=src, notes="events whose raw accelerometer array equals an earlier event"))

    train = meta[meta.split.isin(["train", "validation"])]
    tree = cKDTree(train[ds_cols].to_numpy(np.float32))
    test = meta[meta.split == "test"]
    dist, _ = tree.query(test[ds_cols].to_numpy(np.float32), k=1, p=np.inf, workers=-1)
    test = test.assign(nn_dist=dist)
    out.append(dict(name="leakage.nn_distance_median", value=round(float(np.median(dist)), 5), unit="g", origin="MEASURED_SOFTWARE",
                    source_file=src, notes="test event to nearest train/validation event, L-infinity on 32 downsampled |a| bins"))
    for eps in NN_EPS_G:
        for lab, name in LABELS.items():
            g = test[test.label == lab]
            n = int((g.nn_dist < eps).sum())
            rows.append(dict(eps_g=eps, cls=name, test_events=len(g), within_eps=n, share=n / len(g)))
            out.append(dict(name=f"leakage.nn_within_{eps:g}g.{name}", value=n, unit="events", origin="MEASURED_SOFTWARE",
                            source_file=src, notes=f"of {len(g)} test events; quiet driving can match by chance near 1 g"))
    trainval_hashes = set(train.hash)
    leaky = test[test.hash.isin(trainval_hashes) | (test.nn_dist < max(NN_EPS_G))]
    leaky[["event_id"]].to_parquet(C.PROCESSED / "leaky_test_events.parquet")
    for lab, name in LABELS.items():
        out.append(dict(name=f"leakage.test_events_flagged.{name}", value=int((leaky.label == lab).sum()), unit="events",
                        origin="MEASURED_SOFTWARE", source_file=src,
                        notes=f"test events with an identical hash or nearest-neighbour distance below {max(NN_EPS_G):g} g in train/validation"))
    out.append(dict(name="leakage.test_events_flagged.total", value=int(len(leaky)), unit="events", origin="MEASURED_SOFTWARE", source_file=src,
                    notes="cross-split duplicates removed from the primary test set"))
    for lab, name in LABELS.items():
        out.append(dict(name=f"leakage.test_events_kept.{name}", value=int((test.label == lab).sum() - (leaky.label == lab).sum()), unit="events",
                        origin="MEASURED_SOFTWARE", source_file=src, notes="primary (de-duplicated) test set"))
    record_many(out)
    return pd.DataFrame(rows)


def leaky_test_ids() -> set[int]:
    return set(pd.read_parquet(C.PROCESSED / "leaky_test_events.parquet").event_id)


def duplicate_groups_table() -> pd.DataFrame:
    """Events whose raw accelerometer array is identical to an event in another split (event IDs only, no signals).

    Written to results/tables/vzcrash_duplicate_groups.csv as the attachment for the email to the dataset authors.
    """
    meta = pd.read_parquet(C.PROCESSED / "events_meta.parquet", columns=["event_id", "split", "label", "vehiclesize", "n", "hash", "dropped"])
    meta = meta[~meta.dropped & (meta.hash != "")]
    nsplit = meta.groupby("hash").split.transform("nunique")
    g = meta[nsplit > 1].copy()
    g["group_id"] = g.groupby("hash").ngroup() + 1
    g["class"] = g.label.map(LABELS)
    g = g.sort_values(["group_id", "split", "event_id"])[["group_id", "event_id", "split", "class", "vehiclesize", "n"]].rename(columns={"n": "n_samples"})
    src = "results/tables/vzcrash_duplicate_groups.csv"
    out = [dict(name="leakage.cross_split_group_events.total", value=int(len(g)), unit="events", origin="MEASURED_SOFTWARE", source_file=src,
                notes="events in groups of identical raw accelerometer arrays that span more than one split")]
    for name in LABELS.values():
        out.append(dict(name=f"leakage.cross_split_group_events.{name}", value=int((g["class"] == name).sum()), unit="events", origin="MEASURED_SOFTWARE", source_file=src))
    record_many(out)
    return g


if __name__ == "__main__":
    C.TABLES.mkdir(parents=True, exist_ok=True)
    t = near_duplicate_check()
    t.to_csv(C.TABLES / "leakage_check.csv", index=False)
    duplicate_groups_table().to_csv(C.TABLES / "vzcrash_duplicate_groups.csv", index=False)
    print(t.to_string())
