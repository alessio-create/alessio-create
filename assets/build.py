# Builds banner.svg from banner.src.svg: subsets the brand fonts to the glyphs used and embeds them,
# so the banner renders identically on GitHub (which blocks external fonts in SVG images).
# Usage: py assets/build.py
# Fonts (OFL, Google Fonts) go in .fonts-src/ as f1 Bricolage Grotesque 800, f2 IBM Plex Sans 500,
# f3/f4 JetBrains Mono 500/700. Get the .ttf URLs with: curl -A Wget/1.21 "https://fonts.googleapis.com/css2?family=..."
import base64, io, re, sys
from pathlib import Path
from fontTools.subset import Subsetter, Options
from fontTools.ttLib import TTFont

root = Path(__file__).resolve().parent
fonts = root.parent / ".fonts-src"
src = (root / "banner.src.svg").read_text(encoding="utf-8")
FONTS = {"BRICOLAGE": "f1.ttf", "PLEX": "f2.ttf", "MONO": "f3.ttf", "MONOBOLD": "f4.ttf"}

# every character that appears as text in the SVG (plus space)
chars = set(" ".join(re.findall(r">([^<>]+)<", src))) | {" "}

def embed(name):
    f = TTFont(fonts / name)
    opts = Options(); opts.layout_features = ["kern", "liga"]; opts.hinting = False
    s = Subsetter(opts); s.populate(text="".join(chars)); s.subset(f)
    buf = io.BytesIO(); f.save(buf)
    return base64.b64encode(buf.getvalue()).decode()

def width(name, text, size, tracking):
    # advance width of text in px, used to size the yellow highlighter under "Builder"
    f = TTFont(fonts / name); cmap = f.getBestCmap(); hmtx = f["hmtx"]; upm = f["head"].unitsPerEm
    return sum(hmtx[cmap[ord(c)]][0] for c in text) * size / upm + tracking * (len(text) - 1)

out = src.replace("{{HL_W}}", f"{width('f1.ttf', 'Builder', 140, -5) + 8:.0f}")
for key, file in FONTS.items():
    out = out.replace("{{" + key + "}}", embed(file))
assert "{{" not in out, "unreplaced placeholder"
(root / "banner.svg").write_text(out, encoding="utf-8")
print(f"banner.svg {len(out) // 1024} KB")
