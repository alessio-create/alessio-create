# Image -> coloured ASCII in a circle (card/art.json). Bright pixel = dense char, colour from the pixel.
# Saturated green/red cells (the eyes) are flagged: today.py draws them with a pulsing glow.
# Usage: py -I card/ascii_color.py .art/avatar.jpg 56 card/art.json   (delete art.json to go back to art.txt)
import colorsys, json, sys
from PIL import Image, ImageEnhance
src, cols, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
im = Image.open(src).convert("RGB")
rows = round(cols * im.height / im.width * 0.5)                   # mono cells are ~2x taller than wide
small = ImageEnhance.Contrast(im).enhance(1.25).resize((cols, rows), Image.LANCZOS)
lum = small.convert("L")
vals = sorted(lum.tobytes())
lo, hi = vals[len(vals) * 4 // 100], vals[len(vals) * 98 // 100]
ramp = " .:-=+*#%@"                                                # dark -> bright (dark card)

def eye(r, g, b):
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    return s > .6 and v > .6 and (.2 < h < .45 or h > .9 or h < .03)   # vivid green or red

grid = []
for y in range(rows):
    runs = []
    for x in range(cols):
        nx, ny = (x + .5) / cols * 2 - 1, (y + .5) / rows * 2 - 1
        if nx * nx + ny * ny > 1: ch, col, e = " ", None, False   # outside the circle
        else:
            r, g, b = small.getpixel((x, y))
            v = min(1, max(0, (lum.getpixel((x, y)) - lo) / (hi - lo))) ** .7   # lift mid-tones
            ch, e = ramp[min(len(ramp) - 1, 2 + int(v * (len(ramp) - 2)))], eye(r, g, b)  # never sparser than ":"
            h, s, vv = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            if e: s, vv, ch = 1, 1, "@"
            else: s, vv = min(1, s * 1.3), .5 + .5 * vv                            # lift dark tones so they read on a dark card
            col = "#%02X%02X%02X" % tuple(min(255, round(c * 255 / 24) * 24) for c in colorsys.hsv_to_rgb(h, s, vv))
        if runs and runs[-1][1] == col and runs[-1][2] == e: runs[-1][0] += ch
        else: runs.append([ch, col, e])
    grid.append(runs)
json.dump(grid, open(out, "w"), separators=(",", ":"))
print(rows, "rows,", sum(r[2] for row in grid for r in row), "eye runs")
