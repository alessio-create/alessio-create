# Shared CRT look for the profile card and the README banners: colours, scanlines, flicker, binary rain, pixel titles.
# Frame 0 of every animation shows the finished picture: viewers that freeze SVG images still see it.
import random

G, G2, PALE, DIM, DEEP, RED, BG, PANEL = "#39FF6A", "#29B85A", "#C8FFD6", "#1E5A33", "#0E3D1F", "#FF4433", "#050907", "#04100A"

DEFS = ('<defs><pattern id="sl" width="4" height="3" patternUnits="userSpaceOnUse">'
        '<rect width="4" height="1" fill="#000" fill-opacity=".38"/></pattern>'
        '<filter id="glow" x="-200%" y="-200%" width="500%" height="500%"><feGaussianBlur stdDeviation="5" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
        '<filter id="haze" x="-200%" y="-200%" width="500%" height="500%"><feGaussianBlur stdDeviation="14"/></filter></defs>')

CSS = (f".hd{{fill:{PALE}}}"
       ".flick{animation:flick 7s infinite}@keyframes flick{0%,95%,100%{opacity:1}96%{opacity:.7}97%{opacity:1}98%{opacity:.8}}"
       ".fall{animation:fall linear infinite}@keyframes fall{from{transform:translateY(var(--d))}to{transform:none}}"
       ".glitch{animation:glitch 6s infinite}"
       "@keyframes glitch{0%,90%,100%{transform:none}91%{transform:translateX(6px)}93%{transform:translateX(-4px)}95%{transform:none}}"
       ".bar{transform-box:fill-box;transform-origin:left;animation:bar 6s infinite}"
       "@keyframes bar{0%{transform:scaleX(.04);animation-timing-function:steps(24,end)}70%,100%{transform:none}}"
       "@media (prefers-reduced-motion:reduce){.flick,.fall,.glitch,.bar{animation:none}}")


def rain(x0, x1, h, seed, fs=13, lh=16):
    """Columns of 0/1 falling forever. Each column holds its pattern twice and slides by one copy: a seamless loop."""
    rnd, out, n = random.Random(seed), [], -(-h // lh)
    for cx in range(x0, x1, fs + 1):
        alpha, chars = [0.0] * n, [rnd.choice("01") for _ in range(n)]
        for _ in range(rnd.randint(1, 2)):                     # 1-2 trails: bright head, fading tail above it
            head, tail = rnd.randrange(n), rnd.randint(6, 18)
            for k in range(tail):
                alpha[(head - k) % n] = max(alpha[(head - k) % n], 1 - k / tail)
        head_cls = ' class="hd"'
        spans = "".join(f'<tspan x="{cx}" y="{(i + rep * n) * lh}" fill-opacity="{a:.2f}"{head_cls if a == 1 else ""}>{chars[i]}</tspan>'
                        for rep in (0, 1) for i, a in enumerate(alpha) if a > .05)
        dur = rnd.uniform(7, 16)
        out.append(f'<text class="fall" fill="{G}" font-size="{fs}" style="--d:-{n * lh}px;animation-duration:{dur:.1f}s;'
                   f'animation-delay:-{rnd.uniform(0, dur):.1f}s">{spans}</text>')
    return "".join(out)


def pixel(title, x, y, s=4, uid="t"):
    """A pixel-font title (runs from static.json) stacked like an old 3D CRT logo, the top layer glitching now and then."""
    rects = "".join(f'<rect x="{rx * s}" y="{ry * s}" width="{w * s}" height="{s}"/>' for rx, ry, w in title["runs"])
    return (f'<defs><g id="{uid}">{rects}</g></defs><g transform="translate({x},{y})">'
            f'<use href="#{uid}" x="{2 * s}" y="{2 * s}" fill="{DEEP}" fill-opacity=".6"/>'
            f'<use href="#{uid}" x="{s}" y="{s}" fill="{DEEP}"/>'
            f'<use href="#{uid}" class="glitch" fill="{G}"/></g>')


def bar(x, y, w):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="14" fill="none" stroke="{G2}"/>'
            f'<rect class="bar" x="{x + 3}" y="{y + 3}" width="{w - 6}" height="8" fill="{G}"/>')
