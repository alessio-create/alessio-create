# Builds the parts of the profile that never change, so the daily job (today.py) needs no image libraries:
#   static.json      my silhouette as ASCII: dark 'shadow' characters, a bright rim, features faint inside
#   card/halo.png    a soft dark shape around me, so the rain parts around the figure
#   card/static.json figure size, red-eye position, pixel-font runs for the titles
#   card/h-*.svg     the README section banners
# Run locally: py -I card/static.py   (needs Pillow and the cutout .art/cut.png, which stays out of git)
import json, sys
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import crt

# ---- figure ----
CROP, EYE = (190, 95, 690, 695), (432, 224)          # head + shoulders in the cutout; the eye that turns red
FW, FH = 460, 552
cut = Image.open(HERE.parent / ".art/cut.png").convert("RGBA").crop(CROP).resize((FW, FH), Image.LANCZOS)
alpha = cut.getchannel("A").point(lambda a: 255 if a > 100 else 0)
g = ImageOps.grayscale(cut)
inside = sorted(v for v, a in zip(g.tobytes(), alpha.tobytes()) if a)
lo, hi = inside[len(inside) * 2 // 100], inside[len(inside) * 98 // 100]
g = g.point(lambda v: round(255 * min(1, max(0, (v - lo) / (hi - lo))) ** .75))   # stretch on me only, lift mid-tones
g = g.filter(ImageFilter.UnsharpMask(radius=3, percent=160, threshold=2))
# ASCII shadow: one cell per char (10px font: 6 x 11 px). Rim = inside cell touching the outside.
AFS, ACW, ALH = 10, 6, 11
cols, rows = FW // ACW, FH // ALH
a = alpha.resize((cols, rows), Image.BILINEAR).point(lambda v: 255 if v > 127 else 0)
lum = g.resize((cols, rows), Image.LANCZOS)
RAMP, TONES = " .:-=+*#%@", ["s0", "s1", "s2", "s3"]              # darker -> brighter, sparser -> denser
inside = lambda x, y: 0 <= x < cols and 0 <= y and (y >= rows or a.getpixel((x, y)))   # below the card = inside: no rim on the cut
shadow = []
for y in range(rows):
    runs = []
    for x in range(cols):
        if not inside(x, y): ch, cls = " ", ""
        elif not all(inside(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))): ch, cls = "#", "rim"
        else:
            v = .2 + .55 * lum.getpixel((x, y)) / 255                     # squeezed: one shadow, features faint
            ch, cls = RAMP[1 + min(8, int(v * 9))], TONES[min(3, int(v * 4))]
        if runs and runs[-1][1] == cls: runs[-1][0] += ch
        else: runs.append([ch, cls])
    shadow.append(runs)
halo = Image.new("RGBA", (FW, FH), crt.BG)
halo.putalpha(alpha.filter(ImageFilter.MaxFilter(21)).filter(ImageFilter.GaussianBlur(10)))
halo.save(HERE / "halo.png", optimize=True)

# ---- pixel titles: the mono font rendered small, one run of lit pixels per rect ----
FONT = ImageFont.truetype(str(HERE / "mono.ttf"), 13)
def runs(text):
    l, t, r, b = FONT.getbbox(text)
    im = Image.new("L", (r - l + 2, b - t + 2)); ImageDraw.Draw(im).text((1 - l, 1 - t), text, font=FONT, fill=255)
    out = []
    for y in range(im.height):
        x = 0
        while x < im.width:
            if im.getpixel((x, y)) > 110:
                s = x
                while x < im.width and im.getpixel((x, y)) > 110: x += 1
                out.append([s, y, x - s])
            else: x += 1
    return {"runs": out, "size": im.size}

TITLES = {"title": "BUILDER.EXE", "built": "WHAT I'VE BUILT", "build": "HOW I BUILD", "work": "HOW I WORK"}
px = {k: runs(v) for k, v in TITLES.items()}
json.dump({"fig": [FW, FH], "shadow": {"fs": AFS, "cw": ACW, "lh": ALH, "rows": shadow}, "eye": [round((EYE[0] - CROP[0]) * FW / 500, 1), round((EYE[1] - CROP[1]) * FH / 600, 1)],
           "title": px["title"]}, open(HERE / "static.json", "w"))

# ---- README banners ----
BW, BH, S = 1100, 112, 4
for seed, key in enumerate(("built", "build", "work"), 1):
    t = px[key]
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{BW}" height="{BH}" viewBox="0 0 {BW} {BH}" role="img" '
           f'aria-label="{TITLES[key].title()}" font-family="Consolas, Menlo, monospace"><style>{crt.CSS}</style>{crt.DEFS}'
           f'<rect width="100%" height="100%" rx="10" fill="{crt.BG}"/><g class="flick">'
           f'<g opacity=".35">{crt.rain(8, BW, BH, seed=seed, fs=11, lh=13)}</g>'
           f'<rect x="16" y="12" width="{t["size"][0] * S + 40}" height="{BH - 24}" rx="4" fill="{crt.PANEL}" stroke="{crt.DIM}"/>'
           f'{crt.pixel(t, 34, 22, S, "t" + key)}{crt.bar(36, 22 + t["size"][1] * S + 10, t["size"][0] * S)}</g>'
           f'<rect width="100%" height="100%" rx="10" fill="url(#sl)"/></svg>')
    (HERE / f"h-{key}.svg").write_text(svg, encoding="utf-8")
print("shadow", cols, "x", rows, "halo", (HERE / "halo.png").stat().st_size, "bytes")
