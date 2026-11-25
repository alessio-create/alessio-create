# Photo cutout -> ASCII art. Dark pixel = dense char (hair/beard dense, skin and shirt light).
# Usage: py -I card/ascii.py <photo cutout.png> 56 card/art.txt  (cutout made with rembg)
import sys
from PIL import Image, ImageFilter
src, cols, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
im = Image.open(src).convert("RGBA").crop((140, 95, 720, 640))   # head + shoulders
g = im.convert("L").filter(ImageFilter.UnsharpMask(radius=6, percent=220, threshold=2))
rows = round(cols * im.height / im.width * 0.5)                   # mono cells are ~2x taller than wide
a = im.getchannel("A").resize((cols, rows))
g = g.resize((cols, rows), Image.LANCZOS)
inside = sorted(g.getpixel((x, y)) for y in range(rows) for x in range(cols) if a.getpixel((x, y)) >= 110)
lo, hi = inside[len(inside) * 3 // 100], inside[len(inside) * 97 // 100]   # stretch on the person only
ramp = "@#%*+=-:. "                                                # dark -> light
lines = []
for y in range(rows):
    s = ""
    for x in range(cols):
        if a.getpixel((x, y)) < 110: s += " "; continue
        v = min(1, max(0, (g.getpixel((x, y)) - lo) / (hi - lo)))
        s += ramp[min(len(ramp) - 2, int(v * (len(ramp) - 1)))]   # never blank inside the person
    lines.append(s.rstrip())
open(out, "w", encoding="utf-8").write("\n".join(lines))
print("\n".join(lines)); print(rows, "rows")
