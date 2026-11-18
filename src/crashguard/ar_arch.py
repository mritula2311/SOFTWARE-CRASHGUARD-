"""R5: docs/05_architecture/ARCHITECTURE.md and the layered diagram `architecture_layers.svg` (generated; the verdicts of R1 to R4 are read from results.json).

Status words on every element: IMPLEMENTED (code in this repository, run on data), SIMULATED (a simulation or model with stated assumptions), DESIGN-ONLY (written down, not built). Colour is never the
only cue: each status has its own border style and a text tag. Nothing here is measured on hardware.

    python -m crashguard.ar_arch
"""
from __future__ import annotations

import json
from pathlib import Path

R = {e["name"]: e["value"] for e in json.loads(Path("results/results.json").read_text(encoding="utf-8"))}
OUT = Path("docs/05_architecture")

# status -> (fill, stroke, dash, tag)  Okabe-Ito colours; dash and tag carry the meaning as well
STY = {"IMPLEMENTED": ("#cfe3f3", "#0072B2", "", "IMPL"), "SIMULATED": ("#fbe9c4", "#B07800", "6 3", "SIM"), "DESIGN-ONLY": ("#f1dce8", "#A0446F", "2 3", "DESIGN")}
LAYERS = [
    ("Sensing", [("MPU6050 +-16 g, 100 Hz; 6 SW-420 switches", "IMPLEMENTED", "software reads the logs; the sensors were not measured here"), ("simulated hardware-format logs (19 fault variants)", "SIMULATED", "Part S")]),
    ("Edge detector", [("2 g trigger, 2.8 s window, 14 features", "IMPLEMENTED", ""), ("15-tree forest, early-exit rule", "IMPLEMENTED", ""), ("impact side from one IMU", "IMPLEMENTED", "fails under an axis flip and at 10 Hz (S2)")]),
    ("Severity", [("delta-V and ASI estimate, class table", "IMPLEMENTED", ""), ("clipping restoration, conformal class interval (UA-SCT)", "IMPLEMENTED", "narrow evaluations")]),
    ("Alert frame", [("97-byte alert, 26-byte ACK, 14-byte flash and CANCEL", "IMPLEMENTED", ""), ("R2: 24 to 40-byte frames with 7 to 8-byte tags", "SIMULATED", "fields not designed"), ("R3: provisional flash, then confirm or cancel", "SIMULATED", "")]),
    ("Freshness and authentication", [("HMAC-SHA256/64 and a persisted counter", "IMPLEMENTED", "reference verifier; firmware not in the repository"), ("R1: GPS-time freshness field (GTF)", "SIMULATED", "bounded model and Monte Carlo"), ("R4: per-vehicle keys, ACK bound to vehicle and counter", "SIMULATED", "bounded model; ACK bytes tested")]),
    ("MAC and retry policy", [("duty-cycle token bucket, severity table, SCT and UA-SCT", "SIMULATED", "simulator"), ("listen-before-talk, slotted baselines", "SIMULATED", "")]),
    ("Base and ACK", [("reference base verifier, idempotent re-ACK, ACK budget", "IMPLEMENTED", ""), ("base on an ESP32 with SX1278", "DESIGN-ONLY", "built by the author, not measured here")]),
]


def svg() -> str:
    w, h0, pad = 980, 56, 14
    row_h, gap = 74, 10
    lines = []
    y = h0
    boxes = []
    for name, els in LAYERS:
        boxes.append((name, y, els))
        y += row_h + gap
    H = y + 70
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {H}" width="{w}" height="{H}" font-family="Segoe UI, Arial, sans-serif" role="img" aria-label="Layered architecture of CrashGuard with the status of every element">',
           f'<rect width="{w}" height="{H}" fill="#ffffff"/>', '<text x="14" y="28" font-size="18" font-weight="700" fill="#111">CrashGuard layers and the four candidates (R1 to R4)</text>',
           '<text x="14" y="46" font-size="12" fill="#444">Border and tag give the status: IMPL solid, SIM dashed, DESIGN dotted. Nothing here is measured on hardware.</text>']
    for name, y0, els in boxes:
        out.append(f'<text x="{pad}" y="{y0 + 16}" font-size="13" font-weight="700" fill="#111">{name}</text>')
        n = len(els)
        bw = (w - 2 * pad - 150 - (n - 1) * 10) / n
        for i, (txt, st, note) in enumerate(els):
            fill, stroke, dash, tag = STY[st]
            x = pad + 150 + i * (bw + 10)
            da = f' stroke-dasharray="{dash}"' if dash else ""
            out.append(f'<rect x="{x:.1f}" y="{y0}" width="{bw:.1f}" height="{row_h}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="2"{da}/>')
            words = txt.split()
            ln, cur = [], ""
            for wd in words:
                if len(cur) + len(wd) + 1 > int(bw / 6.6):
                    ln.append(cur)
                    cur = wd
                else:
                    cur = (cur + " " + wd).strip()
            ln.append(cur)
            for k, t in enumerate(ln[:3]):
                out.append(f'<text x="{x + 8:.1f}" y="{y0 + 18 + 14 * k}" font-size="12" fill="#111">{t}</text>')
            out.append(f'<text x="{x + bw - 8:.1f}" y="{y0 + row_h - 8}" font-size="10" font-weight="700" fill="{stroke}" text-anchor="end">{tag}</text>')
            if note:
                nt = note if len(note) < int(bw / 5.6) else note[: int(bw / 5.6) - 1] + "."
                out.append(f'<text x="{x + 8:.1f}" y="{y0 + row_h - 8}" font-size="10" fill="#444">{nt}</text>')
    out.append(f'<text x="{pad}" y="{H - 38}" font-size="12" fill="#111">Candidates: R1 freshness (supplement), R2 frame and tag length (supplement), R3 two-stage alert (main paper), R4 per-vehicle ACK keys (main paper).</text>')
    out.append(f'<text x="{pad}" y="{H - 20}" font-size="11" fill="#444">Verdicts: see docs/03_results/COMBINED_VERDICTS.md. Evidence labels: SIMULATED, SIMULATED_HW_FORMAT, ANALYTICAL, MEASURED_SOFTWARE.</text>')
    out.append("</svg>")
    return "\n".join(out + lines)


def doc() -> str:
    v = {k: R[f"ar.holm.{k}.verdict"] for k in ("hr1a", "hr1b", "hr1c", "hr2a", "hr2b", "hr3", "hr4")}
    L = ["# Architecture and protocol layers (combined run)", "", "<!-- header:start -->", "<!-- header:end -->", "",
         "Generated by `python -m crashguard.ar_arch`. The older module and data-flow description is `docs/00_overview/ARCHITECTURE.md`. Every element is marked IMPLEMENTED (code in this repository, run on data), "
         "SIMULATED (a simulation or model with stated assumptions) or DESIGN-ONLY (written down, not built). No element is measured on hardware; Part S uses simulated hardware-format logs (SIMULATED_HW_FORMAT).", "",
         "![Layered architecture](architecture_layers.svg)", "", "## Layers and elements", "", "| Layer | Element | Status | Note |", "|---|---|---|---|"]
    for name, els in LAYERS:
        for txt, st, note in els:
            L.append(f"| {name} | {txt} | {st} | {note} |")
    L += ["", "## What each candidate changes", "",
          "| Candidate | Layer | Change | Verdicts (held-out data, Holm) | Placement |", "|---|---|---|---|---|",
          f"| R1 GTF | Freshness and authentication | the 32-bit freshness field is GPS UTC seconds (a boot-epoch marker plus counter without a fix); the base checks a window and a ring of seen triples; no counter is persisted | H-R1a {v['hr1a']}, H-R1b {v['hr1b']}, H-R1c {v['hr1c']} | supplement; the ring sizing failure is in the negatives register |",
          f"| R2 frame and tag | Alert frame | a 24 to 40-byte frame with a 7 or 8-byte tag instead of 97 bytes | H-R2a {v['hr2a']}, H-R2b {v['hr2b']} | supplement; H-R2a in the negatives register |",
          f"| R3 two-stage | Alert frame and MAC | a 14-byte flash from the early-exit rule about 1.9 s before the full-window alert, then the full alert or an authenticated CANCEL | H-R3 {v['hr3']} | main paper |",
          f"| R4 per-vehicle keys | Freshness and authentication; Base and ACK | K_i = HMAC(master, id); the alert and the ACK of vehicle i use K_i; the ACK names (vehicle, counter): 0 extra bytes, one KDF per new id | H-R4 {v['hr4']} | main paper |", "",
         "R2 figure: `results/figures/ar_r2_frame_vs_delivery.png` (and `.pdf`): burst delivery against time on air for every frame and tag length (SIMULATED delivery, ANALYTICAL time on air).", "",
         "## Which results go where", "",
         "- **Main paper:** R3 and R4 (all their hypotheses are supported), and the statements of Part S that are supported: the latency decomposition (H-S4) and the security suite on the simulated scenarios (H-S5), worded as results on simulated hardware-format logs.",
         "- **Supplement:** R1 and R2 (partly supported), the failure map of the side rule (H-S1), the trigger result (H-S2), the link-policy table (H-S3) and the SW-420 sensitivity (H-S6).",
         "- **Negatives register:** H-S1, H-S2, H-S3, H-S6, H-R1b and H-R2a (`docs/03_results/NEGATIVES_REGISTER.md`).", "",
         "## Reading limits", "",
         "- R1 to R4 are tested in models and simulations, not in firmware. The firmware source is not in this repository, so what the ESP32 persists is NOT_RUN.",
         "- R2 changes only the frame length in the simulator; the fields that would be dropped (position, delta-V detail) were not designed, so the delivery gain is not a design claim.",
         "- R3's timing is the window length of the early-exit rule (SIMULATED), not an ESP32 timing; the single-stage baseline waits for the full window, and an early-exit alert without a cancel path would be as fast.",
         "- R4 is a design correction found by the bounded check (per-device keys are standard in LoRaWAN); a holder of the master key can still stop every vehicle.", ""]
    return "\n".join(L)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "architecture_layers.svg").write_text(svg(), encoding="utf-8")
    (OUT / "ARCHITECTURE.md").write_text(doc(), encoding="utf-8")
    print("written", OUT)


if __name__ == "__main__":
    main()
