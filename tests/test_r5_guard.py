"""Tests of the run-once and data-hash guards."""
from __future__ import annotations

import json

import pytest

from crashguard import r5_guard as G


def test_check_once_refuses_existing_prefix(tmp_path, monkeypatch):
    (tmp_path / "results").mkdir()
    (tmp_path / "results" / "results.json").write_text(json.dumps([{"name": "r5.l9.rho.act_vs_wait", "value": 1}]))
    monkeypatch.setattr(G, "ROOT", tmp_path)
    with pytest.raises(RuntimeError):
        G.check_once("r5.l9.rho")
    G.check_once("r5.l8.hL8")  # no such key: fine


def test_check_data_compares_hash_prefixes(tmp_path, monkeypatch):
    import hashlib

    f = tmp_path / "d.bin"
    f.write_bytes(b"abc")
    h = hashlib.sha256(b"abc").hexdigest()
    monkeypatch.setattr(G, "ROOT", tmp_path)
    monkeypatch.setattr(G.R5, "ROOT", tmp_path)
    G.check_data({"d.bin": h[:8]})
    with pytest.raises(RuntimeError):
        G.check_data({"d.bin": "00000000"})
    with pytest.raises(FileNotFoundError):
        G.check_data({"missing.bin": "00"})
