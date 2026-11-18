"""V7.2: greyscale check of the main-text figures: writes results/figures/vf_grey_sheet.png (the eight figures converted to grey) and prints the grey level of each palette colour.
usage: python scripts/vf_grey_check.py"""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
names = ["pp_arch", "vf_audit", "pp_heat", "pp_p4a", "vf_proto", "pp_r3", "vf_sim", "vf_deploy"]
CB = {"blue": "#0072B2", "orange": "#E69F00", "green": "#009E73", "red": "#D55E00", "purple": "#CC79A7", "sky": "#56B4E9", "grey": "#7F7F7F", "black": "#000000"}
for k, v in CB.items():
    r, g, b = (int(v[i:i + 2], 16) for i in (1, 3, 5))
    print(k, round(0.299 * r + 0.587 * g + 0.114 * b))
ims = [Image.open(ROOT / "paper/figures" / f"{n}.png").convert("L") for n in names]
w = 900
ims = [im.resize((w, int(im.height * w / im.width))) for im in ims]
rows = [ims[i:i + 2] for i in range(0, 8, 2)]
H = sum(max(i.height for i in r) for r in rows)
sheet = Image.new("L", (2 * w, H), 255)
y = 0
for r in rows:
    for k, im in enumerate(r):
        sheet.paste(im, (k * w, y))
    y += max(i.height for i in r)
sheet.save(ROOT / "results/figures/vf_grey_sheet.png")
print(sheet.size)
