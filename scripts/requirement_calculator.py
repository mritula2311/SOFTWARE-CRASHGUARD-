"""Requirement calculator (B2): which accelerometer configuration meets 'lower end of the 95% interval of the share of crashes within +-10% of the reference delta-V >= required' for a crash-mode mix.

Usage:  python scripts/requirement_calculator.py --mix frontal_barrier=0.3,pole=0.4,side=0.1,other=0.2 --required 0.80
Needs results/tables/p_b2_flags.npz (written by ``python -m crashguard.pp_b2``). Data: the 913 pooled NHTSA records, plain delta-V of the clipped signal, 8 parts of docs/05_data_code/SENSOR_DATASHEETS.md.
Configurations are ordered by full-scale range, then output rate, then part name; 'smallest' is the first in that order. This is a software-model result on crash tests (mostly high-speed); it is not a field requirement.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from crashguard.pp_b2 import requirement  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mix", default="frontal_barrier=0.25,pole=0.25,side=0.25,other=0.25", help="mode weights, e.g. frontal_barrier=0.3,pole=0.4,side=0.1,other=0.2")
    ap.add_argument("--required", type=float, default=0.80)
    a = ap.parse_args()
    mix = {k: float(v) for k, v in (kv.split("=") for kv in a.mix.split(","))}
    R = requirement(mix, a.required)
    for label, col in (("for the mix", "meets_mix"), ("in every mode with weight above 0", "meets_every_mode")):
        ok = R[R[col]]
        print(f"\nSmallest configuration that meets the rule {label}: ", end="")
        if len(ok):
            r = ok.iloc[0]
            print(f"{r.part}, +-{r.range_g:g} g, {int(r.odr_hz)} Hz (mix share {r.mix_share:.3f}, lower end {r.mix_lower:.3f}); {len(ok)} of {len(R)} configurations meet it")
        else:
            print(f"none of the {len(R)} configurations")
    print("\nMix:", mix, "required lower end:", a.required)


if __name__ == "__main__":
    main()
