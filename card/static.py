# Builds the parts of the profile that never change, so the daily job (today.py) needs no image libraries:
#   card/figure.png  my photo as a dithered blue-grey print (transparent around me)
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
dots = g.resize((FW // 2, FH // 2), Image.LANCZOS).convert("1").resize((FW, FH), Image.NEAREST)   # 2px dither dots
fig = Image.new("RGBA", (FW, FH), (157, 189, 204, 255))
fig.putalpha(ImageChops.multiply(dots.convert("L"), alpha))
fig.save(HERE / "figure.png", optimize=True)
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
json.dump({"fig": [FW, FH], "eye": [round((EYE[0] - CROP[0]) * FW / 500, 1), round((EYE[1] - CROP[1]) * FH / 600, 1)],
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
print("figure", (HERE / "figure.png").stat().st_size, "halo", (HERE / "halo.png").stat().st_size, "bytes")
