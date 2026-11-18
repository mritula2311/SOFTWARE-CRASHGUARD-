"""Block 2 deliverables: S1 part table (ANALYTICAL), S2 study table, S3 verdicts, the figure and docs/05_data_code/SENSOR_DATASHEETS.md. Reads results/tables/sel_configs.csv (written by ``sel_study``) and
``sel_parts.py``; every table row cites its results.json keys; no number is typed here. Output: results/paper/tab_sel_*.csv and .tex, results/paper/figures/sel_share_vs_range.*"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from crashguard import config as C
from crashguard.jp_common import Entries
from crashguard.paper_tables import OUT, write
from crashguard.plots import COLORS, plt, save, style
from crashguard.sel_parts import PARTS
from crashguard.sel_study import CAVEAT_TEXT, CAVEATS, cfg_name

SRC = "src/crashguard/sel_parts.py"


def fmt(p: float, lo: float, hi: float, d: int = 3) -> str:
    return f"{p:.{d}f} [{lo:.{d}f}, {hi:.{d}f}]"


def s1_entries() -> None:
    E = Entries("sel.part", SRC, "ANALYTICAL")
    for p in PARTS:
        E.add(f"{p.key}.name", p.name, "text", notes="datasheet value, as read from the document named in sel.part.<key>.document")
        E.add(f"{p.key}.url", p.url, "text", notes=f"address opened on {p.opened}")
        E.add(f"{p.key}.opened", p.opened, "date")
        E.add(f"{p.key}.document", p.document, "text")
        E.add(f"{p.key}.ranges_g", ", ".join(f"+-{r:g}" for r in p.ranges_g), "g")
        E.add(f"{p.key}.mg_per_lsb", ", ".join(f"+-{r:g} g: {v:.4g}" for r, v in p.mg_per_lsb.items()), "mg/LSB")
        E.add(f"{p.key}.bits", p.bits, "bits")
        E.add(f"{p.key}.odr_offered", p.odr_offered, "text")
        E.add(f"{p.key}.bandwidth", p.bandwidth, "text")
        E.add(f"{p.key}.noise", p.noise_text, "text")
        E.add(f"{p.key}.interface", p.interface, "text")
        E.add(f"{p.key}.study_odrs_hz", ", ".join(str(o) for o in p.odrs_hz), "Hz", notes="output data rates run in the study (the part offers more)")
        E.add(f"{p.key}.notes", p.notes, "text")
    E.flush(("sel.part.",))


def tables() -> None:
    R = pd.read_csv(C.TABLES / "sel_configs.csv")
    ho = R[R.set == "heldout"].set_index(["part", "range_g", "odr_hz"])
    # S1
    rows = []
    for p in PARTS:
        rows.append({"Part": p.name, "Full-scale ranges (g)": ", ".join(f"+-{r:g}" for r in p.ranges_g), "Resolution": f"{p.bits}; mg/LSB: " + ", ".join(f"{v:.3g}" for v in p.mg_per_lsb.values()),
                     "Output data rates": p.odr_offered, "Bandwidth": p.bandwidth, "Noise (as printed)": p.noise_text.split(" (the unit")[0], "Interface": p.interface,
                     "Configurations in the study": f"ranges {', '.join(str(r) for r in p.study_ranges)}; rates {', '.join(str(o) for o in p.odrs_hz)} Hz", "Origin": "ANALYTICAL",
                     "results.json key": f"sel.part.{p.key}.*"})
    write("tab_sel_parts", pd.DataFrame(rows), "Accelerometers of the sensor-selection study: values read from the data sheets named in tab_sel_sources. No price is given (no vendor page was opened). Caveat: " + CAVEAT_TEXT.split(";")[0])
    rows = [{"Part": p.name, "Data sheet address opened": p.url, "Date opened": p.opened, "Document": p.document, "Origin": "ANALYTICAL", "results.json key": f"sel.part.{p.key}.url; sel.part.{p.key}.document"} for p in PARTS]
    write("tab_sel_sources", pd.DataFrame(rows), "Data sheets opened for the sensor-selection study (address, date, revision). ADXL375: no address was recorded when the copy was opened on 2026-11-11.")
    # S2 compact: best output rate per part and range (largest lower interval end on the 176 tests)
    comp, full = [], []
    for (part, rg), d in R[R.set == "n13"].groupby(["part", "range_g"]):
        best = d.sort_values(["w10_lo", "w10"], ascending=False).iloc[0]
        key = f"sel.cfg.{cfg_name(next(p for p in PARTS if p.key == part), rg, best.odr_hz)}"
        h = ho.loc[(part, rg, best.odr_hz)]
        row = {"Part": next(p.name for p in PARTS if p.key == part), "Range (g)": f"+-{rg:g}", "Rate (Hz)": int(best.odr_hz), "Share within 10%, 176 tests [95% CI]": fmt(best.w10, best.w10_lo, best.w10_hi),
               "Median abs error (%)": round(best["median"], 1), "p90 abs error (%)": round(best.p90, 1)}
        if not pd.isna(best.get("band", float("nan"))):
            row["Share in v<=dV<=2v (frontal)"] = fmt(best.band, best.band_lo, best.band_hi)
        row["Fill + ridge share within 10% [95% CI]"] = fmt(best.mp_w10, best.mp_w10_lo, best.mp_w10_hi) if not pd.isna(best.get("mp_w10", float("nan"))) else ""
        row["Meets (176)"] = "yes" if best.w10_lo >= 0.8 else "no"
        row["Share within 10%, held-out modes [95% CI]"] = fmt(h.w10, h.w10_lo, h.w10_hi)
        row["Meets (held-out)"] = "yes" if h.w10_lo >= 0.8 else "no"
        row["Caveats"] = CAVEATS
        row["Origin"] = "MEASURED_SOFTWARE"
        row["results.json key"] = f"{key}.n13.w10 (+ _lo, _hi); {key}.heldout.w10"
        comp.append(row)
    for r in R[R.set == "n13"].itertuples():
        p = next(p for p in PARTS if p.key == r.part)
        key = f"sel.cfg.{cfg_name(p, r.range_g, r.odr_hz)}"
        h = ho.loc[(r.part, r.range_g, r.odr_hz)]
        full.append({"Part": p.name, "Range (g)": f"+-{r.range_g:g}", "Rate (Hz)": int(r.odr_hz), "Share within 10% [95% CI]": fmt(r.w10, r.w10_lo, r.w10_hi), "Median abs error (%)": round(r.median, 2), "p90 (%)": round(r.p90, 2),
                     "Band share": fmt(r.band, r.band_lo, r.band_hi) if not pd.isna(r.band) else "", "Fill + ridge share": fmt(r.mp_w10, r.mp_w10_lo, r.mp_w10_hi) if not pd.isna(getattr(r, "mp_w10", float("nan"))) else "",
                     "Meets (176)": "yes" if r.w10_lo >= 0.8 else "no", "Held-out share": fmt(h.w10, h.w10_lo, h.w10_hi), "Meets (held-out)": "yes" if h.w10_lo >= 0.8 else "no", "Caveats": CAVEATS, "Origin": "MEASURED_SOFTWARE",
                     "results.json key": f"{key}.n13.w10; {key}.heldout.w10"})
    cap = ("Share of the 176 NHTSA tests whose delta-V is within 10% of the reference, for each accelerometer, range and (best) output data rate; a row meets the requirement if the lower end of its interval is at least 0.80. "
           + CAVEAT_TEXT + ". The held-out columns use the T13a records of other test modes.")
    write("tab_sel_study", pd.DataFrame(comp), cap)
    write("tab_sel_study_all", pd.DataFrame(full), "All configurations of the sensor-selection study (176 NHTSA tests; held-out modes in the last columns). " + CAVEAT_TEXT)


def figure() -> None:
    R = pd.read_csv(C.TABLES / "sel_configs.csv")
    style()
    fig, axes = plt.subplots(2, 1, figsize=(3.5, 4.9), sharex=True)
    marks = ["o", "s", "^", "D", "v", "P", "X", "*"]
    cols = [COLORS[k] for k in (0, 1, 2, 3, 4, 5, 7)] + ["#7F7F7F"]
    for ax, st, ttl in ((axes[0], "n13", "176 NHTSA tests"), (axes[1], "heldout", "T13a held-out modes")):
        for i, p in enumerate(PARTS):
            d = R[(R.set == st) & (R.part == p.key)]
            best = d.sort_values("w10", ascending=False).groupby("range_g").head(1).sort_values("range_g")
            ax.errorbar(best.range_g, best.w10, yerr=[best.w10 - best.w10_lo, best.w10_hi - best.w10], fmt=marks[i % 8] + "-", color=cols[i % 8], ms=4, lw=0.8, capsize=1.5, label=p.name.replace(" (high-g channel)", " (high-g)"))
        ax.axhline(0.8, color="k", lw=0.8, ls="--")
        ax.set_xscale("log")
        ax.set_ylabel("Share within +-10%")
        ax.set_xlim(1.5, 500)
        ax.set_xticks([2, 4, 8, 16, 32, 64, 128, 256])
        ax.set_xticklabels(["2", "4", "8", "16", "32", "64", "128", "256"])
        ax.minorticks_off()
        ax.set_ylim(-0.03, 1.03)
        ax.set_title(ttl, fontsize=8)
    axes[1].set_xlabel("Full-scale range (+-g)")
    axes[0].legend(fontsize=5.5, loc="center left", bbox_to_anchor=(0.0, 0.45), ncol=1, frameon=False)
    fig.text(0.01, 0.005, "Software sensor model, datasheet rates (not read on an ESP32). Best rate per range.", fontsize=5)
    save(fig, "sel_share_vs_range", OUT / "figures")


def datasheet_doc() -> None:
    L = ["# Accelerometer data sheets opened for the sensor-selection study", "",
         "Documents were opened as PDF copies on 2026-11-12 (the ADXL375 copy on 2026-11-11). Local copies are in `data/raw/refs/` and `data/raw/refs/sel/` (git-ignored: redistribution rights were not checked). "
         "Values in `src/crashguard/sel_parts.py` and in `results/paper/tab_sel_parts.*` were read from these documents. No price is given: no vendor page was opened.", "",
         "| Part | Address opened | Date opened | Document | Notes |", "|---|---|---|---|---|"]
    for p in PARTS:
        L.append(f"| {p.name} | {p.url} | {p.opened} | {p.document} | {p.notes} |")
    L += ["", "**Part named in the task but not opened:** LSM6DSV32X (ST). The ST data sheet address timed out. The data sheet that was opened is for the LSM6DSK320X, which has a low-g channel (to +-16 g) and a high-g channel (to +-320 g); it is NOT claimed to be the same part.",
          "", "**Caveats stated in every table row:** " + CAVEAT_TEXT + "."]
    Path("docs/05_data_code/SENSOR_DATASHEETS.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def main() -> None:
    s1_entries()
    tables()
    figure()
    datasheet_doc()
    print(json.dumps({"ok": True}))


if __name__ == "__main__":
    main()
