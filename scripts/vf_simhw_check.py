"""V3.5: variants regenerated with `python -m crashguard.hwsim_v2 <dir>` in the fresh clone: hashes against SIMHW_VARIANTS.md, seeds against 20261114 + 1000 i, data_origin SIMULATED in every JSON file.
usage: python scripts/vf_simhw_check.py <regenerated dir>"""
import json
import re
import sys
from pathlib import Path

from crashguard.results import record_many

ROOT = Path(__file__).resolve().parents[1]
regen = Path(sys.argv[1])
doc = (ROOT / "docs/03_results/SIMHW_VARIANTS.md").read_text(encoding="utf-8")
rows = re.findall(r"^\| (\d+) \| (\S+) \| (\d+) \| \S+ \| .*? \| (\d+) \| (\d+) \| `([0-9a-f]{64})` \|$", doc, re.M)
hashes = json.loads((regen / "VARIANT_HASHES.json").read_text(encoding="utf-8"))
sens_doc = dict(re.findall(r"^\| (\S+) \| `([0-9a-f]{64})` \|$", doc, re.M))
sens = json.loads((regen / "SW_SENS_HASHES.json").read_text(encoding="utf-8"))
bad = []
for i, name, seed, _ev, _nf, h in rows:
    ok_seed = int(seed) == 20261114 + 1000 * int(i)
    ok_hash = hashes.get(name) == h
    if not (ok_seed and ok_hash):
        bad.append((name, seed, h[:10], (hashes.get(name) or "")[:10]))
sbad = [(k, v[:10], (sens.get(k) or "")[:10]) for k, v in sens_doc.items() if k in sens and sens[k] != v]
miss = [k for k in sens_doc if k not in sens]
n_json = n_sim = 0
for d in (regen, ROOT / "data" / "simulated_hardware" / "variants", ROOT / "data" / "simulated_hardware"):
    pass
non = []
for p in list((ROOT / "data" / "simulated_hardware" / "variants").rglob("*.json")) + list((ROOT / "data" / "simulated_hardware" / "sensor_logs").rglob("*.json")) + list((ROOT / "data" / "simulated_hardware" / "protocol_logs").rglob("*.json")):
    if p.name in ("VARIANT_HASHES.json", "SW_SENS_HASHES.json"):
        continue
    j = json.loads(p.read_text(encoding="utf-8"))
    n_json += 1
    o = j.get("data_origin", "") if isinstance(j, dict) else ""
    if o.startswith("SIMULATED"):
        n_sim += 1
    else:
        non.append(str(p.relative_to(ROOT)))
print(len(rows), "variants in the table;", len(bad), "mismatch;", len(sens_doc), "sensitivity sets,", len(sbad), "mismatch,", len(miss), "missing;", n_json, "json files,", n_sim, "with data_origin SIMULATED;", non[:5])
src = "scripts/vf_simhw_check.py"
record_many([dict(name="vf.simhw.variants_checked", value=len(rows), unit="variants", origin="ANALYTICAL", source_file=src, notes="regenerated in the fresh clone"),
             dict(name="vf.simhw.variants_hash_mismatch", value=len(bad), unit="variants", origin="ANALYTICAL", source_file=src),
             dict(name="vf.simhw.sens_sets_hash_mismatch", value=len(sbad) + len(miss), unit="sets", origin="ANALYTICAL", source_file=src),
             dict(name="vf.simhw.json_files_checked", value=n_json, unit="files", origin="ANALYTICAL", source_file=src),
             dict(name="vf.simhw.json_without_simulated_origin", value=len(non), unit="files", origin="ANALYTICAL", source_file=src)], purge_prefixes=("vf.simhw.",))
sys.exit(1 if (bad or sbad or miss or non) else 0)
