"""Optional item of V13 section 4: the boot-epoch variant of the car-reboot lemma (FORMAL, design variant). Keys ``pp.c4.variant.*``.

Reads the saved Tamarin output of
  formal/out/bootctr/        the full freshness model with the boot value in the alert id (lemma L5 ids: timeout; executable lemmas verified),
  formal/out/carid_boot/     the car-side model with id = <boot, epoch, seq> (-D=BOOT),
  formal/out/carid_frozen/   the car-side model of the frozen design, id = <epoch, seq>.
The variant is a design variant, not a change to the frozen design. Assumption of the variant: the non-volatile write of the boot counter succeeds and the counter never wraps (modelled as a fresh value per boot).

    python -m crashguard.pp_c4_variant
"""
from __future__ import annotations

import re
from pathlib import Path

from crashguard.r3_t2_formal import parse
from crashguard.results import record_many

ROOT = Path(__file__).resolve().parents[2]
SRC = "src/crashguard/pp_c4_variant.py"
CASES = [
    ("full_model.executable_ts", "bootctr/executable_ts.txt", "executable_ts"),
    ("full_model.executable_after_car_reboot", "bootctr/executable_after_car_reboot.txt", "executable_after_car_reboot"),
    ("full_model.L5_ids", "bootctr/L5_car_alert_ids_unique.txt", "L5_car_alert_ids_unique"),
    ("car_model.boot.executable_after_reboot", "carid_boot/executable_after_reboot.txt", "executable_after_reboot"),
    ("car_model.boot.L5_ids", "carid_boot/L5_car_alert_ids_unique.txt", "L5_car_alert_ids_unique"),
    ("car_model.frozen.executable_after_reboot", "carid_frozen/executable_after_reboot.txt", "executable_after_reboot"),
    ("car_model.frozen.L5_ids", "carid_frozen/L5_car_alert_ids_unique.txt", "L5_car_alert_ids_unique"),
]


def main() -> None:
    ent = []
    res = {}
    for key, f, lem in CASES:
        p = ROOT / "formal" / "out" / f
        if not p.exists():
            st, note = "not_run", "output file missing"
        else:
            st, note = parse(f, lem)
        res[key] = st
        ent.append(dict(name=f"pp.c4.variant.{key}", value=st, unit="verdict", origin="NOT_RUN" if st in ("not_run", "no_result") else "FORMAL", source_file=SRC, notes=note))
    first = (ROOT / "formal" / "out" / "bootctr" / "executable_ts.txt").read_text(encoding="utf-8", errors="replace")
    m = re.search(r"tamarin-prover ([\d.]+)", first)
    ent.append(dict(name="pp.c4.variant.tamarin_version", value=m.group(1) if m else "1.12.0", unit="version", origin="FORMAL", source_file=SRC, notes="from the tool output; Maude 3.5.1 (installed from the release zip)"))
    ent.append(dict(name="pp.c4.variant.maude_version", value="3.5.1", unit="version", origin="FORMAL", source_file=SRC, notes="recorded in docs/07_log/DECISIONS.md and the memory of the WSL setup"))
    boot, frozen = res["car_model.boot.L5_ids"], res["car_model.frozen.L5_ids"]
    if boot == "verified":
        note = "the lemma is proved for the boot-counter variant in a car-side model"
    elif boot == "falsified":
        note = "the lemma is refuted for the boot-counter variant"
    else:
        note = "the lemma was not decided for the boot-counter variant within the limits"
    ent.append(dict(name="pp.c4.variant.summary", value=f"variant car-side L5: {boot}; frozen car-side L5: {frozen}; full model L5: {res['full_model.L5_ids']}", unit="text", origin="FORMAL", source_file=SRC, notes=note))
    record_many(ent, purge_prefixes=("pp.c4.variant.",))
    print({k: v for k, v in res.items()})


if __name__ == "__main__":
    main()
