# Builds the parts of the profile that never change, so the daily job (today.py) needs no image libraries:
#   card/halo.png    a soft dark shape around the ASCII portrait (card/art.txt), so the rain parts around it
#   card/static.json portrait rows + size, red-eye position, pixel-font runs for the titles
#   card/h-*.svg     the README section banners
# Run locally: py -I card/static.py   (needs Pillow)
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import crt

# ---- ASCII portrait + halo ----
AFS = 13
ACW, ALH = AFS * .6, AFS * 1.25
EYE = (29, 7)                                             # (column, row) of the eye that turns red
art = (HERE / "art.txt").read_text(encoding="utf-8").splitlines()
AW, AH, HP = round(max(map(len, art)) * ACW), round(len(art) * ALH), 24   # HP: halo padding around the art box
m = Image.new("L", (AW + 2 * HP, AH + 2 * HP))
d = ImageDraw.Draw(m)
for y, line in enumerate(art):
    for x, ch in enumerate(line):
        if ch != " ": d.rectangle((HP + x * ACW, HP + y * ALH, HP + (x + 1) * ACW, HP + (y + 1) * ALH), fill=255)
halo = Image.new("RGBA", m.size, crt.BG)
halo.putalpha(m.filter(ImageFilter.MaxFilter(17)).filter(ImageFilter.GaussianBlur(9)))
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
json.dump({"art": {"fs": AFS, "cw": ACW, "lh": ALH, "w": AW, "h": AH, "pad": HP, "rows": art},
           "eye": [round((EYE[0] + .5) * ACW, 1), round((EYE[1] + .62) * ALH, 1)],
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
print("art", AW, "x", AH, "px, halo", (HERE / "halo.png").stat().st_size, "bytes")
