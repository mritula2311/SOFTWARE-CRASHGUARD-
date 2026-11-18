"""Figure of R2: burst delivery against time on air for every frame and tag length (SIMULATED delivery, ANALYTICAL time on air). PNG and PDF at 300 dpi, colour-blind-safe (Okabe-Ito), marker shape and colour by tag length.

    python -m crashguard.ar_figs
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

R = {e["name"]: e["value"] for e in json.loads(Path("results/results.json").read_text(encoding="utf-8")) if e["name"].startswith("ar.r2.")}
COL = {4: "#999999", 6: "#56B4E9", 7: "#009E73", 8: "#0072B2", 12: "#D55E00"}
MK = {4: "o", 6: "s", 7: "^", 8: "D", 12: "v"}


def main() -> None:
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    seen = set()
    for k, v in R.items():
        if k.startswith("ar.r2.held.") and k.endswith(".reach10_critical_mean") and "tamang" not in k:
            f, t = (int(x) for x in k.split(".")[3].split("_"))
            air = R[f"ar.r2.held.{f}_{t}.airtime_ms_mean"]
            ax.scatter(air, v, c=COL[t], marker=MK[t], s=46, label=None if t in seen else f"tag {t} bytes", zorder=3)
            seen.add(t)
            ax.annotate(f"{f}", (air, v), textcoords="offset points", xytext=(4, 4), fontsize=7)
    ax.set_xlabel("Mean time on air of the frame at SF8 and SF10 (ms)")
    ax.set_ylabel("Critical reach within 10 s (fraction)")
    ax.set_title("Frame length against burst delivery (labels: frame bytes)", fontsize=10)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.text(0.01, 0.01, "SIMULATED delivery (P4+lbt, 16 held-out burst cells, 30 hours); ANALYTICAL time on air", fontsize=6.5)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    Path("results/figures").mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(f"results/figures/ar_r2_frame_vs_delivery.{ext}", dpi=300)
    print("written")


if __name__ == "__main__":
    main()
