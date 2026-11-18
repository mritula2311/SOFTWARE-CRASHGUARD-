"""Shared figure style: colour-blind-safe palette, 300 dpi, PNG and PDF."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from crashguard import config as C  # noqa: E402

# Okabe-Ito
COLORS = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#F0E442", "#000000"]


def style() -> None:
    plt.rcParams.update({
        "figure.dpi": 100, "savefig.dpi": 300, "font.size": 10, "axes.grid": True, "grid.alpha": 0.3,
        "axes.prop_cycle": matplotlib.cycler(color=COLORS), "axes.spines.top": False, "axes.spines.right": False,
    })


def save(fig, name: str, out_dir: Path = C.FIGURES, dummy: bool = False) -> None:
    """Save PNG and PDF. ``dummy=True`` adds the DUMMY DATA watermark (CLAUDE.md rule 8)."""
    if dummy:
        fig.text(0.5, 0.5, "DUMMY DATA", fontsize=48, color="red", alpha=0.25, ha="center", va="center", rotation=30)
    out_dir.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(out_dir / f"{name}.{ext}", dpi=300)
    plt.close(fig)
